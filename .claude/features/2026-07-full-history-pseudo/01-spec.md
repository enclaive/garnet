---
STATUS: reviewed
HANDOFF: planner
NEXT: design already drafted in 03-design.md
---

# Spec — Full History Pseudonymization
Date: 2026-07-12
Branch: feature/full-history-pseudo

## Problem
The Garnet proxy currently pseudonymizes only `messages[-1]` (the newest user
message) before forwarding to the LLM. Every prior message in the history —
user AND assistant — is sent to the LLM with **real PII** intact.

Concrete leak path today:
1. Turn 1: user writes `"Max Mustermann called"` → last-message pseudo runs →
   LLM sees `PERSON_cc75010d`, replies with the token → depseudo restores
   `"Max Mustermann"` in the browser.
2. Turn 2: browser sends back the full chat history. The assistant's
   restored `"Max Mustermann"` reply and any older user turns are in
   `messages[:-1]`. Only the newest user turn gets pseudonymized. Everything
   older ships to the LLM in cleartext.

The existing `messages[:-1]` loop (lines 402-411 of `main.py`) does the
**opposite** of what we need: it *depseudonymizes* assistant tokens back to
real PII before forwarding. That block is the source of the leak.

## Why now
Ahmed flagged this while auditing multi-turn behavior. The single-message
pseudo path was the MVP; multi-turn was the known follow-up. Also a
prerequisite for anything downstream that relies on "the LLM never saw real
PII" (audit logs, on-prem policy claims, contract clauses with users).

## Users affected
- All Garnet users on multi-turn chats (Ahmed, Seb, Alexa, Julia, every
  future tenant).
- Every provider: Ollama, OpenAI, Anthropic, Groq, Gemini — the leak is
  provider-agnostic because it happens before the outbound POST.

## Desired behavior (post-change)
- Every message in `messages` (all indices, both user and assistant roles)
  is pseudonymized before the outbound request.
- Tokens produced in earlier turns are reused via `store` — a name seen in
  turn 1 gets the SAME token in turn 5.
- Assistant text that already contains tokens (e.g. `PERSON_cc75010d`) is a
  no-op through `pseudonymize()` (spaCy will not re-detect our own tokens as
  entities — verified informally, must be re-checked in verification).
- Per-session **MD5 hash cache** short-circuits repeat work: if the same
  message text was pseudonymized this session already, return the cached
  result; do not re-run spaCy.
- Cache is scoped to `session_id`. Different sessions never share cached
  outputs (they have different mapping stores).
- Cache lifetime = same TTL as the mapping store (1h). No new eviction code.
- The **last message** path (line 439 onward) stays unchanged in behavior
  — it may benefit from the same cache but no other logic changes.
- `is_system_prompt` messages are **not** pseudonymized (existing rule for
  the last message extends to history: same check per message).
- If `privacy_enabled=False` for the request, no pseudonymization runs at
  all (history included). Existing gate stays.

## Out of scope
- No change to depseudonymize on the response path.
- No change to file-upload / RAG chunk pseudonymization.
- No change to streaming machinery.
- No cache persistence across restarts. In-memory only, same as `store`.
- No cache metrics/telemetry beyond a debug print if trivially cheap.
- No new dependency.
- No refactor of `extract_text_content` / `rebuild_content`.

## Acceptance criteria
- [ ] After the change, a multi-turn conversation sends **zero** real PII
      strings for `PERSON | ORGANIZATION | EMAIL_ADDRESS | IBAN_CODE |
      PHONE_NUMBER | ID | LOCATION` to the LLM (verify by capturing the
      outbound body on turn 3+ and grepping for the plaintext name).
- [ ] A token seen in turn 1 (e.g. `PERSON_cc75010d`) is the exact same
      token in turn 5 for the same session (mapping reuse works).
- [ ] Pseudonymizing the same message text twice in one session runs spaCy
      exactly once (cache hit on the second call — verified by log or by
      timing).
- [ ] `is_system_prompt` history messages pass through untouched.
- [ ] `privacy_enabled=False` → no pseudonymization on any message.
- [ ] `body["stream"]` handling unchanged.
- [ ] Response depseudonymize still works end-to-end (browser sees real
      names again).
- [ ] All existing acceptance for the last-message path still passes
      (image, RAG, system prompt, Responses API, Ollama non-streaming).

## Constraints (garnet rules)
- Must not remove `body["stream"] = False` anywhere.
- Must not expose `0.0.0.0`.
- Must not log headers.
- Only one file changes: `backend/privacy_proxy/app/main.py`.
- No new dependency. `hashlib` already imported (line 3).
- Seb approval NOT required (behavior-preserving improvement to an existing
  gate — no new service, no API change, no key distribution).

## Open questions
- [ ] Do we cache the *depseudonymized* history-loop output too? — Answer
      in design: no. That loop is being removed. Cache is only for
      pseudonymize direction.
- [ ] Cache key: MD5 of the plaintext, or MD5 of `(session_id, plaintext)`?
      — Answer in design: cache is stored per-session, so plaintext hash
      alone is sufficient as long as the cache dict lives under
      `session_id`. Simpler.
