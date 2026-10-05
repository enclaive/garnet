# Garnet — Live test results

_Environment: demo-1.garnet.enclaive.cloud (Hetzner cVM, Docker Compose)_
_Started: 2026-07-25 · Re-run: 2026-07-25_

Each test shows what we checked, why it matters for you, and the result.

---

## ✅ Test 1 — Sensitive data never leaves your control

**What we checked:** Sent a message with a name, company, and email to an LLM.

**Why it matters:** Anything you type normally goes straight to the AI provider — including private data. Garnet replaces it with anonymous tokens before it leaves.

**Result:** ✅ PASS
_We sent a message with a name, company, and email — the LLM received anonymous tokens, the user saw real names in the reply._
- All 3 entities intercepted: `PERSON_dddfab9b` · `ORGANIZATION_bd3a68a5` · `EMAIL_ADDRESS_2162ce1b`
- Real names restored in the browser response. Sensitive counter badge: "3 sensitive items".

---

## ✅ Test 2 — Full conversation stays protected

**What we checked:** Asked follow-up questions in the same chat referencing private data from earlier messages ("what email did I give you?", "what company do I work at?").

**Why it matters:** Most privacy filters only clean the newest message. Garnet re-anonymizes the entire conversation history on every turn — including the AI's own replies.

**Result:** ✅ PASS
_We asked two follow-up questions — the LLM answered correctly using only tokens, and the real values were restored only in the browser._
- 4 turns scanned and re-pseudonymized each time; token count stayed at 3 (no duplicates — same PII, same token).
- The LLM's own reply containing the real email was caught and anonymized before being sent back as context.

---

## ✅ Test 3 — Each conversation is isolated

**What we checked:** Opened a brand-new chat and sent the same name/company/email again. Verified the new conversation lives in its own sealed context, separate from the first chat.

**Why it matters:** Two of your team members should never accidentally see or influence each other's private data through Garnet. Each conversation must be self-contained — one chat can never restore or read another chat's data.

**Result:** ✅ PASS
_We opened a second chat and sent the same message — Garnet assigned a fresh session, completely separate from the first._
- New session `875bbbff` vs `e4feadf1` — two isolated mapping tables, one per chat.
- Tokens are the same (deterministic by design) but the reverse-mapping is sealed per session — Chat 1 cannot restore Chat 2's data.

---

## ✅ Test 4 — Private documents stay protected

**What we checked:** Uploaded a PDF with employee names, emails, IBANs, and phone numbers. Asked a question about the document.

**Why it matters:** Chat privacy alone isn't enough — most real work involves files. Garnet scans every uploaded document and pseudonymizes its contents before any chunk reaches the LLM.

**Result:** ✅ PASS
_We uploaded a confidential HR report — Garnet scanned it on upload, pseudonymized all 21 entities in the retrieved chunks, and the LLM never saw any real personal data._
- 21 entities detected on upload: 7 PERSON · 4 EMAIL · 4 LOCATION · 3 PHONE · 2 IBAN · 1 ORG.
- Chunks pseudonymized before LLM context: `[FILE DELTA] 2340→2390 chars (+50)` — 22 entities replaced with tokens.
- Response depseudonymized: 102 tokens restored. Real employee names visible in browser.
- Note: LLM answer quality depends on which chunks the retrieval engine selects — that is a retrieval concern, not a privacy concern. Garnet's protection applies to all retrieved content regardless.

**⚙️ Required configuration:** In Admin Panel → Documents → **set these before using RAG:**
- **Top K** → `15` (retrieve enough candidates for the reranker)
- **Recherche hybride** → `ON` (BM25 + semantic — catches exact names and meaning)
- **Reranking model** → `BAAI/bge-reranker-v2-m3` (local, no API key, re-scores top-15 → best 6)
- **Reranker Top K** → `6`

_Without these, retrieval quality drops significantly — exact names and IBANs may be missed, and the reranker has too few candidates to work effectively._

---

## ✅ Test 5 — You can turn privacy off and see the difference

**What we checked:** Toggled the privacy switch OFF and sent the same message — raw PII went straight to the LLM with no interception.

**Why it matters:** This is the "before/after" comparison. Without Garnet, every name, email, and company goes directly to the AI provider unprotected. The toggle lets you see exactly what Garnet is preventing.

**Result:** ✅ PASS
_With privacy OFF, the proxy forwarded raw names to the LLM — no tokens, no badge, no restore step. With privacy ON, all three entities were intercepted._
- `privacy=OFF` confirmed in proxy logs — zero pseudonymization applied.
- Side-by-side: same message, two outcomes. The difference is Garnet.

---

## ✅ Test 6 — Works in German too

**What we checked:** Sent a message in German with a location, company name, and phone number.

**Why it matters:** Your team doesn't only type in English. Garnet uses language-aware detection — the same protection applies to German, French, and other European languages out of the box.

**Result:** ✅ PASS
_German message with Berlin, Siemens AG, and a German phone number — all three intercepted and pseudonymized before the LLM._
- `LOCATION_dad114b6` · `ORGANIZATION_2d539e35` · `PHONE_NUMBER_85e518b2` — all restored in browser.
- Note: person name detection in German is weaker without full context (title-only format). Full names are reliably detected.

---

## ✅ Test 7 — Works with a fully local model (zero data leaves your server)

**What we checked:** Switched to a local Ollama model (llama3.2:3b) and sent the same German message — no cloud provider involved at all.

**Why it matters:** Some clients cannot send any data externally, even pseudonymized tokens. With a local model, Garnet + Ollama keeps everything inside your own infrastructure. No API key, no internet, no provider.

**Result:** ✅ PASS
_Same pseudonymization pipeline — LOCATION, ORG, PHONE intercepted — but the request went to `http://ollama:11434` on the local network. Nothing left the server._
- `provider=ollama` · `http://ollama:11434/api/chat` — fully air-gapped inference.
- Garnet's privacy layer is identical regardless of whether the model is local or cloud.

---

## ✅ Test 8 — Your session survives a server restart

**What we checked:** Sent a message with a name, company, and email — then restarted the privacy proxy completely — then asked a follow-up question in the same chat.

**Why it matters:** Servers restart. Containers are updated. If a restart wiped your session, the next message would show raw tokens instead of real names. Garnet uses Redis as a persistent backup so your active session is never lost during routine maintenance.

**Result:** ✅ PASS
_We restarted the proxy mid-conversation — the follow-up question came back with real names, not tokens. The session was fully restored from Redis with zero user impact._
- Proxy started cold with empty memory → loaded session `e43b090d` from Redis automatically.
- History re-pseudonymized, LLM answered correctly, real email restored in browser.
- Session window: 1 hour of inactivity before a session expires naturally.

---

## ✅ Test 9 — Web search works with privacy protection

**What we checked:** Enabled web search, asked a current-events question ("messi trophy"), and verified that search results were injected into the LLM context before the reply.

**Why it matters:** Web search lets the LLM answer questions about recent events it wasn't trained on. Without it, the model answers from training data only. Garnet's privacy layer must not interfere with this — search results should reach the LLM, and any PII in the query or results should still be pseudonymized.

**Result:** ✅ PASS
_Web search injected live results into the LLM context. The proxy scanned and pseudonymized both the user query AND the search results — the LLM never saw any real names._
- DDGS (Bing backend) ran without an API key — no external credentials required.
- `[IN FILE]` 5048 chars of search context → `[FILE PII] 9 entities detected` → `[FILE DELTA] +180 chars` (tokens replacing real names).
- User query "ronaldo trophys" → `PERSON_04eea3e2` before reaching the LLM.
- `2 messages → 5243 chars to LLM` — full pseudonymized context delivered; real names restored in the browser.

**⚙️ Required configuration:** In Admin Panel → Models → mistral-large-latest → Advanced Params → **Function Calling**, set to **`legacy`** (not `default` or `native`).

_Why:_ After the upstream OWU sync, `default` auto-resolves to `native` for Mistral models. With `native`, OWU expects the model to call a web search tool on its own — Garnet's proxy does not handle tool call round-trips, so the search never fires. Setting `legacy` makes OWU run the search itself and inject results directly into the prompt, which the proxy handles correctly.

---

## ✅ Test 10 — Follow-up questions in a RAG chat stay protected

**What we checked:** Asked a follow-up question in the same chat referencing an employee's email from the uploaded document — verifying that session token mapping is reused across turns.

**Why it matters:** On every turn, the proxy re-pseudonymizes the entire conversation history from scratch — including the LLM's own previous replies. If the session mapping broke between turns, the LLM would receive inconsistent tokens and the user would see raw tokens instead of real names in the response.

**Result:** ✅ PASS
_We asked "What was the email address of the first employee mentioned?" as a follow-up in the same RAG chat — the proxy re-pseudonymized the full history, reused the same tokens from turn 1, and restored the real email in the browser._
- `[HISTORY SCAN] scanned=3 changed=1` — 3 messages scanned, LLM's previous reply re-anonymized.
- `[HISTORY PSEUDO] pseudonymized 1 message(s)` — assistant reply containing real names caught and cleaned.
- Same session `7d4f9fd5` · same token map · 102 tokens · real email restored in browser.
- Pseudonymization is stateless (SHA256 deterministic) — Redis stores only the reverse map for depseudo at response time.

---

## ✅ Test 11 — Knowledge Base (permanent KB) stays protected

**What we checked:** Created a permanent Knowledge Base in Workspace → Knowledge, uploaded the HR PDF, then queried it from a new chat.

**Why it matters:** File attachments are per-chat only. A Knowledge Base is reusable across all chats and all users. Garnet must protect KB content the same way — chunks retrieved from a permanent KB must be pseudonymized before reaching the LLM, regardless of how they were stored.

**Result:** ✅ PASS
_We uploaded the HR report to a permanent KB and queried it from a fresh chat — same pseudonymization pipeline applied. The LLM never saw any real personal data._
- 19 entities detected on upload: 4 PERSON · 4 EMAIL · 3 PHONE · 2 IBAN · 5 LOCATION · 1 ORG.
- `[FILE DELTA] 2123→2209 chars (+86)` — 19 entities replaced with tokens in retrieved chunk.
- 119 tokens restored in browser. Real names, emails, IBANs visible in response.
- Confirmed: KB and file-attach use the same RAG pipeline — privacy protection is identical.
