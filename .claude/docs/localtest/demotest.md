# Garnet — Full Demo Test Scenarios

All scenarios run in the UI at https://garnet.enclaive.cloud (or cVM IP).
Check proxy logs after each: `docker compose logs -f privacy-proxy 2>&1 | grep -E 'GARNET|IN USER|OUT USER|IN FILE|OUT FILE|FILE PII|INTERNAL|PRIVACY OFF|→ LLM|← LLM|→ USER|ERROR|AUDIT|PSEUDO|NO PII|HISTORY'`

Status legend: ✅ PASS · ❌ FAIL · 🔄 NOT TESTED · ⚠️ KNOWN GAP

---

## D01 — Basic PII (PERSON + ORG + LOCATION)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · All entities · Anthropic model
**Prompt:**
```
My name is Max Mustermann and I work at Enclaive GmbH in Berlin, Germany.
What are my GDPR rights as an employee?
```
**Expected logs:**
```
[IN  USER+] My name is Max Mustermann...
[OUT USER+] My name is PERSON_xxx and I work at ORGANIZATION_xxx in LOCATION_xxx...
[PSEUDO DIFF] X→Y chars | 3+ replaced | types=[PERSON, ORGANIZATION, LOCATION]
[→ LLM   ] pseudo=Xms
[← LLM   ] ttft=Xs
[→ USER  ] 3+ tokens restored
[PRIVACY AUDIT] entities=3+
```
**Must NOT see:** `[NO PII]`, `[PRIVACY OFF]`

---

## D02 — No PII (clean message)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · All entities
> ⚠️ Use exactly this prompt — "France" triggers LOCATION, "capital" alone does not.
**Prompt:**
```
What is 2+2? Explain what a database is.
```
**Expected logs:**
```
[IN  USER+] What is 2+2?...
[NO PII] message unchanged — no entities detected
[→ LLM   ] pseudo=Xms
[→ USER  ] 0 tokens
[PRIVACY AUDIT] entities=0
```
**Must NOT see:** `[OUT USER+]`, `[PSEUDO DIFF]`, `[HISTORY PSEUDO]`

---

## D03 — Email + Phone + IBAN in one message

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · All entities
**Prompt:**
```
Please contact Anna Schmidt at anna.schmidt@enclaive.io.
Her phone is +49 30 12345678 and IBAN is DE89370400440532013000.
```
**Expected logs:**
```
[OUT USER+] ...EMAIL_ADDRESS_xxx...PHONE_NUMBER_xxx...IBAN_CODE_xxx...
[PSEUDO DIFF] X→Y chars | 4 replaced | types=[PERSON, EMAIL_ADDRESS, PHONE_NUMBER, IBAN_CODE]
[→ USER  ] 4 tokens restored
```

---

## D04 — Entity filter: PERSON only

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Entity filter = PERSON only (toggle EMAIL, ORG off in UI)
**Prompt:**
```
Contact Anna Schmidt at anna@enclaive.com, she works at Enclaive GmbH.
```
**Expected logs:**
```
[OUT USER+] Contact PERSON_xxx at anna@enclaive.com, she works at Enclaive GmbH.
[PSEUDO DIFF] ... | 1 replaced | types=[PERSON]
```
**Must NOT see:** `EMAIL_ADDRESS_xxx`, `ORGANIZATION_xxx` in OUT USER

---

## D05 — Privacy OFF

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy OFF toggle
**Prompt:**
```
My name is Max Mustermann at Enclaive GmbH.
```
**Expected logs:**
```
[GARNET] privacy=OFF
[PRIVACY OFF] forwarding raw → no pseudonymization
[→ LLM   ] pseudo=0ms
[→ USER  ] 0 tokens
```
**Must NOT see:** `[OUT USER+]`, `[PSEUDO DIFF]`, any token like `PERSON_xxx`

---

## D06 — Multi-turn: history re-pseudonymization

**Status: 🔄 NOT TESTED**
**Setup:** Same chat · Privacy ON · Send two messages
**Prompt 1:**
```
My name is Max Mustermann, I work at Enclaive GmbH in Berlin.
```
**Prompt 2 (same chat):**
```
What rights does Max have regarding his personal data?
```
**Expected logs on prompt 2:**
```
[HISTORY PSEUDO] pseudonymized 2 message(s) in history
[IN  USER+] What rights does Max have...
[OUT USER+] What rights does PERSON_xxx have...
[CONTEXT  ] 3+ messages → X chars
```

---

## D07 — File upload with PII

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Upload file below, then send prompt
**File to upload (save as employee.txt):**
```
Employee Record
Name: Max Mustermann
Email: max.mustermann@enclaive.io
Phone: +49 30 12345678
IBAN: DE89370400440532013000
Company: Enclaive GmbH, Berlin
```
**Prompt after upload:**
```
Summarize this employee record.
```
**Expected logs:**
```
[VAULT START] file_id=xxx session=file:xxx
[VAULT DONE]  file_id=xxx → 6 new entities
              breakdown={PERSON:1, EMAIL_ADDRESS:1, PHONE_NUMBER:1, IBAN_CODE:1, ORGANIZATION:1, LOCATION:1}
[IN  FILE] role=system len=XXXX
[FILE DELTA] X→Y chars
[FILE PII] 6 new entities detected
[NO PII] message unchanged   ← "Summarize this" has no PII
[→ USER  ] 6 tokens restored
```

---

## D08 — Duplicate file upload (deduplication)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Upload same file twice before sending prompt
**File content:**
```
John Doe, john.doe@example.com, Enclaive GmbH
```
**Expected logs on second upload:**
```
[VAULT START] file_id=xxx (same id as first)
[VAULT DONE]  file_id=xxx → 0 new entities   ← dedup: already scanned
```
**Must NOT see:** duplicate tokens, inflated entity count

---

## D09 — Web search with PII in query

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Enable web search in OWU settings
**Prompt:**
```
What are the latest GDPR fines in Germany in 2024?
Max Mustermann at Enclaive GmbH wants to know.
```
**Expected logs:**
```
[IN  FILE] role=system len=XXXX   ← web results arriving
[FILE DELTA] X→Y chars
[FILE PII] X new entities detected
[IN  USER+] Max Mustermann...
[OUT USER+] PERSON_xxx at ORGANIZATION_xxx...
[→ LLM   ] pseudo=Xms   ← higher than D01 (web content adds latency)
[→ USER  ] X tokens restored
```

---

## D10 — Full stack: file + web + multi-turn

**Status: 🔄 NOT TESTED**
**Setup:** Upload file, enable web search, send prompt, then follow-up
**File content:**
```
Client: Max Mustermann, max@enclaive.io, Enclaive GmbH Berlin
```
**Prompt 1:**
```
Based on the uploaded file, search the web for GDPR rights that apply to Max Mustermann.
```
**Prompt 2 (same chat):**
```
What should Max do first?
```
**Expected logs on prompt 2:**
```
[HISTORY PSEUDO] pseudonymized X message(s) in history
[IN  FILE] role=system   ← web results (if web still active)
[OUT USER+] What should PERSON_xxx do first?
[MAPPING] total_tokens=X   ← cumulative
```

---

## D11 — German text (multilingual NER)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Model with German support
**Prompt:**
```
Mein Name ist Thomas Müller und ich arbeite bei Siemens AG in München.
Welche DSGVO-Rechte habe ich als Angestellter?
```
**Expected logs:**
```
[OUT USER+] Mein Name ist PERSON_xxx und ich arbeite bei ORGANIZATION_xxx in LOCATION_xxx.
[PSEUDO DIFF] ... | 3 replaced | types=[PERSON, ORGANIZATION, LOCATION]
```

---

## D12 — German verb false positive (regression)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON
**Prompt:**
```
Schreibe mir eine E-Mail auf Deutsch.
```
**Expected logs:**
```
[NO PII] message unchanged — no entities detected
```
**Must NOT see:** `PERSON_xxx` replacing "Schreibe"
> ⚠️ Known regression in current build — "Schreibe" being detected as PERSON.

---

## D13 — System prompt NOT pseudonymized

**Status: 🔄 NOT TESTED**
**Setup:** Create a model with a system prompt containing a fake name, then chat
**System prompt (set in model config):**
```
You are an assistant for Hans Gruber at Deutsche Bank.
Always respond in formal German.
```
**Prompt:**
```
Who am I?
```
**Expected logs:**
```
[INTERNAL] type=system_prompt → skipped
```
**Must NOT see:** `[OUT FILE]` pseudonymizing the system prompt, tokens like `PERSON_xxx` in `[CONTEXT]`

---

## D14 — Internal prompts skipped (title/tags/follow_ups)

**Status: 🔄 NOT TESTED**
**Setup:** Normal chat — internal auto-calls fire automatically after first assistant reply
**Prompt:**
```
My name is Max Mustermann, what is machine learning?
```
**Expected logs (after main response):**
```
[INTERNAL] type=title_gen → skipped
[INTERNAL] type=follow_ups → skipped
[INTERNAL] type=tags_gen → skipped
```
**Must NOT see:** internal prompts going through pseudonymization

---

## D15 — Query expansion (RAG enhancement)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Knowledge base enabled
**Prompt:**
```
What documents mention Max Mustermann from Enclaive?
```
**Expected logs:**
```
[QUERY EXPAND] header detected → expansion ON
[OUT USER+] ...PERSON_xxx from ORGANIZATION_xxx...
[→ LLM   ] pseudo=Xms   ← higher due to expansion
```

---

## D16 — RAG: knowledge base retrieval with PII

**Status: 🔄 NOT TESTED**
**Setup:** Upload KB doc with PII, enable RAG, then query
**KB document content:**
```
Contract: Anna Müller (anna@enclaive.io) signed on 2024-01-15.
```
**Prompt:**
```
Who signed the contract?
```
**Expected logs:**
```
[IN  FILE] role=system len=XXXX   ← RAG retrieval result
[FILE DELTA] X→Y chars
[FILE PII] X new entities
[→ USER  ] X tokens restored
```
**Verify:** response shows "Anna Müller" (restored), not `PERSON_xxx`

---

## D17 — Image generation (no pseudonymization)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Select image generation model (DALL-E / Stable Diffusion)
**Prompt:**
```
Generate an image of a sunset over Berlin.
```
**Expected logs:**
```
[INTERNAL] type=image_gen → passthrough
```
**Must NOT see:** `LOCATION_xxx` replacing "Berlin" in the image prompt
> Garnet skips pseudonymization for image generation paths.

---

## D18 — Ollama local model (stream=False path)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Select Ollama model (if configured)
**Prompt:**
```
My name is Klaus Weber, summarize GDPR in 2 sentences.
```
**Expected logs:**
```
[GARNET] provider=http://ollama:11434
[OUT USER+] My name is PERSON_xxx...
[→ LLM   ] pseudo=Xms
[→ USER  ] 1 token restored
```
**Must NOT see:** raw tokens in response (Ollama uses stream=False — no chunk boundary risk)

---

## D19 — Mistral routing

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Select Mistral model
**Prompt:**
```
My email is test@example.com. What is quantum computing?
```
**Expected logs:**
```
[GARNET] provider=https://api.mistral.ai/v1 privacy=ON
[OUT USER+] My email is EMAIL_ADDRESS_xxx...
[→ LLM   ] provider=http://privacy-proxy:8080
[→ USER  ] 1 token restored
```
**Verify:** request goes through proxy (not directly to Mistral) — check `x-openai-base-url` header

---

## D20 — Groq routing

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Select Groq model (llama-3 or similar)
**Prompt:**
```
Contact max@example.com about the meeting.
```
**Expected logs:**
```
[GARNET] provider=https://api.groq.com/openai/v1 privacy=ON
[OUT USER+] Contact EMAIL_ADDRESS_xxx about the meeting.
[→ USER  ] 1 token restored
```

---

## D21 — Session isolation (two different chats)

**Status: 🔄 NOT TESTED**
**Setup:** Open chat A and chat B simultaneously (different tabs)
**Chat A prompt:**
```
My name is Max Mustermann, remember this.
```
**Chat B prompt (different tab):**
```
Who am I?
```
**Expected:** Chat B should NOT know about "Max Mustermann" from chat A.
**Verify in logs:** different `session=` IDs, separate Redis keys
```
[GARNET] session=AAAA...
[GARNET] session=BBBB...   ← different
```

---

## D22 — Long message (chunk boundary safety)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Anthropic Opus (large context)
**Prompt:** Send a message longer than 512 chars with PII near the end:
```
This is a very long paragraph about various topics in technology, science, and business.
[... repeat filler text to reach ~600 chars ...]
The contact person is Anna Schmidt at anna@enclaive.com.
```
**Expected:** Token at chunk boundary NOT split — full `PERSON_xxx` and `EMAIL_ADDRESS_xxx` restored
**Must NOT see:** `PERSON_` or `EMAIL_` appearing raw in the response (partial token)

---

## D23 — (i) button shows pseudonymized prompt

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON · Send any message with PII
**Prompt:**
```
My name is Max Mustermann.
```
**UI action:** After response, hover over the (i) button next to the user message
**Expected:** Tooltip appears showing:
```
My name is PERSON_xxx.
```
**Must NOT see:** Empty tooltip, no tooltip rendered, raw `Max Mustermann` in tooltip

---

## D24 — Code block with PII (should pseudonymize)

**Status: 🔄 NOT TESTED**
**Setup:** New chat · Privacy ON
**Prompt:**
```
Here is a config file:
name: Max Mustermann
email: max@enclaive.com
company: Enclaive GmbH
Can you help me parse this YAML?
```
**Expected:** PII inside the message (even if formatted as code) gets pseudonymized
```
[OUT USER+] ...PERSON_xxx...EMAIL_ADDRESS_xxx...ORGANIZATION_xxx...
```

---

## D25 — Self-loop protection

**Status: 🔄 NOT TESTED**
**Setup:** Manually set `openai.api_base_urls` in DB to the proxy URL itself
**Verify in logs:**
```
[SELF-LOOP] detected → rejected
```
**Must NOT see:** request looping infinitely, 500 error without explanation

---

## D26 — Large history (10+ turns) performance

**Status: 🔄 NOT TESTED**
**Setup:** Same chat · 10 back-and-forth messages with PII
**Monitor:** `[HISTORY PSEUDO]` timing should not grow unboundedly
**Expected:** History re-pseudo completes in < 5s even at 10 messages
**Log to watch:**
```
[HISTORY PSEUDO] pseudonymized 10 message(s) in history
[→ LLM   ] pseudo=Xms   ← X should be < 5000
```

---

## D27 — Privacy ON → OFF → ON within same chat

**Status: 🔄 NOT TESTED**
**Setup:** Toggle privacy mid-chat
**Turn 1 (ON):** `My name is Max Mustermann.`
**Turn 2 (OFF):** `What is my name?`
**Turn 3 (ON):** `And my email is max@enclaive.com.`
**Expected:**
- Turn 1: pseudonymized
- Turn 2: raw forwarded
- Turn 3: pseudonymized, history of turn 1 re-pseudonymized

---

## D28 — Sensitive file counter in UI

**Status: 🔄 NOT TESTED**
**Setup:** Upload a file with PII while privacy ON
**Expected UI:** Counter badge showing number of PII entities found in uploaded file
**Verify:** Badge updates after `[VAULT DONE]` log appears

---

## Log checklist per scenario

| Log line | D01 | D02 | D03 | D04 | D05 | D06 | D07 | D08 | D09 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `[IN  USER+]` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - | ✓ | ✓ |
| `[NO PII]` | - | ✓ | - | - | - | - | ✓ | - | - | - |
| `[OUT USER+]` | ✓ | - | ✓ | ✓ | - | ✓ | - | - | ✓ | ✓ |
| `[PSEUDO DIFF]` | ✓ | - | ✓ | ✓ | - | ✓ | - | - | ✓ | ✓ |
| `[IN  FILE]` | - | - | - | - | - | - | ✓ | - | ✓ | ✓ |
| `[FILE DELTA]` | - | - | - | - | - | - | ✓ | - | ✓ | ✓ |
| `[VAULT START]` | - | - | - | - | - | - | ✓ | ✓ | - | ✓ |
| `[VAULT DONE]` | - | - | - | - | - | - | ✓ | ✓ | - | ✓ |
| `[HISTORY PSEUDO]` | - | - | - | - | - | ✓ | - | - | - | ✓ |
| `[PRIVACY OFF]` | - | - | - | - | ✓ | - | - | - | - | - |
| `[INTERNAL]` | ✓ | ✓ | ✓ | ✓ | - | ✓ | ✓ | - | ✓ | ✓ |
| `[PRIVACY AUDIT]` | ✓ | ✓ | ✓ | ✓ | - | ✓ | ✓ | - | ✓ | ✓ |

---

## Known gaps / out of scope

| Gap | Scenario | Note |
|-----|----------|------|
| Street address not masked | D03, D06 | Presidio detects city/country, not "Torstraße 1" |
| "Schreibe" false positive | D12 | German verb at sentence start misdetected as PERSON |
| `/responses` endpoint no pseudo | D17 | o1/o3 models use `/responses` — no pseudo wrap yet |
| Image gen prompt exposed | D17 | DALL-E prompt sent raw |
| Partial token hash length | internal | `split_at_safe_boundary` pattern uses `{0,7}` but hash is 8 chars |
