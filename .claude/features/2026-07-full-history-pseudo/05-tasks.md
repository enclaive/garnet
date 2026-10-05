---
STATUS: ready-for-impl
HANDOFF: implementer
NEXT: /implementer "execute full-history-pseudo"
---

# Tasks — Full History Pseudonymization
Date: 2026-07-12
Based on: 03-design.md
Branch: feature/full-history-pseudo
File touched: `backend/privacy_proxy/app/main.py` (only)

---

## Phase 1 — Cache primitive

### Task 1.1 — Add module-level cache dict
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** Right after `store = MappingStore(ttl=3600)` (line 43), add:
  ```python
  # ponytail: per-session pseudonymize cache. TTL is implicit — same 1h
  # window as store; evicted on process restart, not on session expiry.
  # Add active eviction only if memory becomes measurable.
  pseudo_cache: dict[str, dict[str, str]] = {}
  ```
- **Test:** `python3 -c "from app.main import pseudo_cache; assert pseudo_cache == {}"` (or equivalent import path in container).
- **Depends on:** none
- **Effort:** S
- **Model:** sonnet
- **[parallel]** with 1.2

### Task 1.2 — Add `_pseudo_with_cache` helper
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** Immediately after `rebuild_content` (line ~67), add:
  ```python
  def _pseudo_with_cache(text: str, session_id: str, enabled_types) -> str:
      if not text:
          return text
      h = hashlib.md5(text.encode("utf-8")).hexdigest()
      session_cache = pseudo_cache.setdefault(session_id, {})
      hit = session_cache.get(h)
      if hit is not None:
          return hit
      out = pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)
      session_cache[h] = out
      return out
  ```
- **Test:** Import-time sanity: `python3 -c "from app.main import _pseudo_with_cache; print('ok')"`.
- **Depends on:** 1.1
- **Effort:** S
- **Model:** sonnet
- **[sequential]** after 1.1

---

## Phase 2 — Replace the history-depseudo loop with history-pseudo

### Task 2.1 — Delete the old depseudo-on-history block
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** Delete lines 402-411 (the `for msg in messages[:-1]` block that
  calls `depseudonymize` on assistant messages). Confirm by grep:
  ```bash
  grep -n "for msg in messages\[:-1\]" backend/privacy_proxy/app/main.py
  # must return zero hits after deletion
  ```
- **Test:** `grep -c "depseudonymize(msg\[\"content\"\]" backend/privacy_proxy/app/main.py` returns 0.
- **Depends on:** none
- **Effort:** S
- **Model:** sonnet
- **[sequential]** before 2.2

### Task 2.2 — Add history-pseudo loop in the same spot
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** In place of the deleted block, add a loop that pseudonymizes
  every message except the last, honoring `privacy_enabled` and skipping
  system-prompt-style messages. Insert after `enabled_types = ...` is set
  and BEFORE `last_message = messages[-1]`:
  ```python
  if messages and privacy_enabled:
      hist_pseudo_count = 0
      for msg in messages[:-1]:
          content = msg.get("content")
          text = extract_text_content(content)
          if not text:
              continue
          # RAG/file markers (<context>, <source>) are not PII; pseudonymize
          # will pass them through. No special-casing needed here.
          if any(marker in text for marker in SYSTEM_PROMPT_MARKERS):
              continue  # skip system-style prompts, matches last-msg policy
          out = _pseudo_with_cache(text, session_id, enabled_types)
          if out != text:
              msg["content"] = rebuild_content(content, out)
              hist_pseudo_count += 1
      if hist_pseudo_count > 0:
          log_history_depseudo(hist_pseudo_count)  # reuse existing logger
  ```
- **Test:** With a two-message payload where `messages[0]` contains
  `"Max Mustermann"`, capture outbound body (mock httpx or inspect logs) —
  `messages[0]["content"]` must contain `PERSON_` and NOT `Max`.
- **Depends on:** 1.2, 2.1
- **Effort:** M
- **Model:** sonnet
- **[sequential]** after 2.1

### Task 2.3 — Confirm no double-pseudo on last message
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** Read the last-message block starting ~line 439. Confirm the
  new loop stops at `messages[:-1]` and does not touch `messages[-1]`.
  No code change if correct; add a one-line comment above the new loop:
  `# NOTE: excludes messages[-1]; last message handled by block below.`
- **Test:** Manual reading + `grep -n "messages\[:-1\]"` shows exactly
  ONE occurrence (the new one).
- **Depends on:** 2.2
- **Effort:** S
- **Model:** sonnet
- **[sequential]** after 2.2

### Task 2.4 — Verify spaCy is safe on already-tokenized text
- **File(s):** new tiny check, no persistent file — run in container:
  ```bash
  docker exec -it garnet-privacy-proxy python3 -c "
  from app.pseudonymizer import pseudonymize
  from app.mapping_store import MappingStore
  s = MappingStore(ttl=3600)
  txt = 'user talked to PERSON_cc75010d at ORGANIZATION_bd3a68a5'
  out = pseudonymize(txt, 'test-session', s.get_store())
  assert out == txt, f'spaCy re-tokenized: {out!r}'
  print('spaCy safe on tokenized text — ok')
  "
  ```
- **What:** Verify the design assumption. If it FAILS, add a fast-path at
  the top of `_pseudo_with_cache`:
  ```python
  import re
  _TOKEN_RE = re.compile(r'\b(?:PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|ID|LOCATION)_[a-f0-9]{8}\b')
  ```
  and short-circuit: if the entire text is only tokens+whitespace+punct,
  return it unchanged. Simpler alt: pre-scan for `_[a-f0-9]{8}` and if
  found, skip spaCy on assistant messages only.
- **Test:** The docker exec command above must print the `ok` line. If it
  fails, apply the fast-path and re-run.
- **Depends on:** none (can run any time — better to run FIRST)
- **Effort:** S
- **Model:** sonnet
- **[parallel]** with 1.1

---

## Phase 3 — Route last message through the cache

### Task 3.1 — Swap the last-message `pseudonymize` call
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** Find the pseudonymize call for the last user message (in the
  `elif last_message.get("role") in ("user", "system", "developer"):`
  branch, around line 439+). Replace the direct call
  `pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)`
  with `_pseudo_with_cache(text, session_id, enabled_types)`.
  Do NOT touch the chunked file-upload path (that loops `pseudonymize` on
  chunks — leave it alone, chunks are unlikely to repeat and the diff
  stays small).
- **Test:** Send the same last-message text twice in one session, confirm
  the second call is a cache hit (temporarily add a `print("HIT", h)` in
  `_pseudo_with_cache` on hit path during verification; remove before commit).
- **Depends on:** 1.2
- **Effort:** S
- **Model:** sonnet
- **[sequential]** after 1.2

---

## Phase 4 — Documentation-only

### Task 4.1 — Add ponytail comment on cache lifetime
- **File(s):** `backend/privacy_proxy/app/main.py`
- **What:** Already covered by the comment in Task 1.1. Confirm the
  comment mentions the ceiling (unbounded until restart) and the upgrade
  path (add TTL sweep if measurable).
- **Test:** `grep -n "ponytail:" backend/privacy_proxy/app/main.py`
  returns at least one line matching the cache comment.
- **Depends on:** 1.1
- **Effort:** S (verification only)
- **Model:** sonnet
- **[parallel]** with everything else

---

## Global checks (run at end)

- [ ] `docker compose up -d --build privacy-proxy` inside the local dev
      environment (see `.claude/docs/localdev.md`) — container starts clean.
- [ ] Send a 3-turn conversation via curl or WebUI. Capture the outbound
      body on turn 3 (log it, then delete the log line). Verify:
      - Every user PII string is replaced by `<TYPE>_<hex8>` tokens.
      - Every assistant message from turn 1/2 also uses the same tokens.
      - `<context>` / `<source>` / RAG markers are still intact.
- [ ] Same session, repeat the exact turn-1 text as turn-3 — confirm spaCy
      call count did not increase (add temporary counter in
      `pseudonymize`, remove before commit).
- [ ] `is_system_prompt` case: send a payload where a middle message
      contains `### Task:` — that message must pass through untouched.
- [ ] Toggle `privacy_enabled=False` via header — no pseudonymization on
      any message.
- [ ] Response depseudo path: final rendered reply in the browser shows
      the real names, not tokens.
- [ ] Ollama non-streaming still works (`body["stream"] = False` untouched).
- [ ] Grep audit — none of the following patterns appear as new lines:
      - new `except:` bare
      - `0.0.0.0`
      - `print(request.headers` or any header logging
- [ ] `graphify update .` runs cleanly at the end.

---

## Handoff notes

- Implementer: run Task 2.4 FIRST. It's cheap and it determines whether
  Task 1.2 needs the fast-path variant. Do not merge without a green
  result from 2.4.
- All tasks are Sonnet-tier. No Opus needed for implementation.
- Do not deploy. Ahmed deploys manually. When all Global checks pass,
  hand back to `/reviewer` with the diff.
