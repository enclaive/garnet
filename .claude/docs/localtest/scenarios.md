# Garnet Proxy — Local Test Scenarios

Test one by one. Check logs after each.
Expected log lines listed per scenario.

**Run suite:**
```bash
# cVM
docker exec -w /service garnet-privacy-proxy-1 python3 app/test_proxy.py

# k8s cluster
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- python3 /service/app/test_proxy.py
```

---

## Timing Summary (for graphs)

| Scenario | pseudo (ms) | ttft (s) | total (s) | tokens | chunks |
|---|---|---|---|---|---|
| S1 — Normal PII | 905 | 2.28 | 19.69 | 4 | 35 |
| S2 — No PII | 1232 | 2.69 | 2.93 | 0 | 2 |
| S3 turn1 — Multi-turn | 868 | 1.62 | 4.00 | 3 | 6 |
| S3 turn2 — History pseudo | 2839 | 4.58 | 13.98 | 4 | 19 |
| S4 — Web search | 2047 | 3.35 | 10.60 | 9 | 16 |
| S5 — File upload | 1705 | 2.48 | 5.49 | 6 | 7 |
| S6 — Multi PII types | 1168 | 2.79 | 7.19 | 7 | 9 |
| S7 — File + Web + Multi | 2042 | 7.30 | 26.20 | 13 | 39 |
| S8 — Privacy OFF | 0 | 1.19 | 2.27 | 0 | 3 |

**Key observations:**
- pseudo without file/web: ~900ms avg
- pseudo with file/web content: ~2000ms avg (+1100ms per large chunk)
- history re-pseudo adds ~2000ms extra (S3 turn2)
- ttft: 1.6s–4.6s (LLM dependent, not Garnet)
- total dominated by LLM generation, not proxy

---

## S1 — Normal prompt with PII

**Status: ✅ PASS — 22/07/2026 (cVM/claude) + 24/07/2026 (k8s/mistral)**

**Setup:** privacy ON, no files, no web search
**Prompt:**
```
My name is Anna Bauer and I work at Deutsche Bank AG in Munich, Germany.
What are my GDPR rights as an employee?
```
**Expected logs:**
```
[GARNET] session=XXXXXXXX provider=openai privacy=ON model=mistral-small-latest path=chat/completions
[IN  USER] My name is Anna Bauer...
[OUT USER] My name is PERSON_xxx and I work at ORGANIZATION_yyy in LOCATION_aaa, LOCATION_bbb...
[→ LLM   ] https://api.mistral.ai/v1/chat/completions | model=mistral-small-latest
[MAPPING] session=XXXXXXXX total_tokens=4
"POST /openai/chat/completions HTTP/1.1" 200 OK
[← LLM   ] " don't have access"    ← first stream chunk (log_from_llm only logs 1st)
[→ USER  ] depseudo complete, 4 tokens in mapping
```

**Actual results — cluster run 24/07/2026 (mistral-small-latest):**
```
[GARNET] session=b187b2be provider=openai privacy=ON model=mistral-small-latest path=chat/completions
[ENTITY FILTER] active → only: [PERSON, ORGANIZATION, EMAIL_ADDRESS, IBAN_CODE, PHONE_NUMBER, ID, LOCATION]
[IN  USER] My name is Anna Bauer and I work at Deutsche Bank AG in Munich, Germany. What are my GDPR rights as an employee?
[OUT USER] My name is PERSON_55043f9b and I work at ORGANIZATION_2c25860f in LOCATION_45cf9664, LOCATION_80db4ccd. What are my GDPR rights as an employee?
[→ LLM   ] https://api.mistral.ai/v1/chat/completions | model=mistral-small-latest
[MAPPING] session=b187b2be total_tokens=4
"POST /openai/chat/completions HTTP/1.1" 200 OK
[← LLM   ] " don't have access"
[→ USER  ] depseudo complete, 4 tokens in mapping
```

**Cluster-run notes:**
- 4 entities pseudonymized (PERSON, ORGANIZATION, LOCATION x2) ✅
- Response arrived in UI with real names restored ✅
- Some log lines from cVM baseline are missing in cluster build: `[PSEUDO DIFF]`, `[CONTEXT]`, `[STREAM DONE]`, `[PRIVACY AUDIT]`, and `pseudo=Xms` on `[→ LLM]`. Not a functional bug — deployed image has older signatures.
- `mistral-large-latest` intermittent due to Mistral per-second rate limit (429) when 4 parallel OWU calls fire; `mistral-small-latest` handled the burst.
- Fix used: disabled OWU auto-features (Génération automatique des titres / questions de suivi / tags) → 4 parallel calls dropped to 1–2 → no more 429.

**Baseline (cVM, claude-opus-4-7 22/07/2026):** pseudo=905ms | ttft=2.28s | total=19.69s | 4 tokens depseudonymized

---

## S2 — No PII (clean message)

**Status: ✅ PASS — 22/07/2026 (cVM/claude) + 24/07/2026 (k8s/mistral-small)**

**Cluster-run actual (24/07/2026):**
```
[GARNET] session=a5cba45f provider=openai privacy=ON model=mistral-small-latest path=chat/completions
[IN  USER] What is 2+2? Explain what a database is.
[NO PII] message unchanged — no entities detected   ✅
[→ LLM   ] https://api.mistral.ai/v1/chat/completions | model=mistral-small-latest
[MAPPING] session=a5cba45f total_tokens=0
"POST /openai/chat/completions HTTP/1.1" 200 OK
[← LLM   ] '2 + 2'
[→ USER  ] depseudo complete, 0 tokens in mapping
```
- No `[OUT USER]`, no `[HISTORY PSEUDO]` — confirmed clean fresh-chat behavior ✅

**Setup:** privacy ON, no files, **NEW chat** (fresh session)
**Prompt:**
```
What is 2+2? Explain what a database is.
```
> ⚠️ Do NOT use "What is the capital of France?" — "France" is detected as LOCATION.
> ⚠️ Must be a NEW chat — otherwise history pseudo fires and contaminates the test.

**Expected logs:**
```
[IN  USER+] What is 2+2?...
[NO PII] message unchanged — no entities detected
[CONTEXT  ] 1 messages → X chars
[→ LLM   ] ... | pseudo=Xms
```
**Must NOT see:** `[PSEUDO DIFF]`, `[OUT USER+]`, `[HISTORY PSEUDO]`

**Actual results (22/07/2026 — same chat as S1, wrong prompt):**
```
[HISTORY PSEUDO] pseudonymized 2 message(s) in history  ← S1 history still active
[IN  USER+] What is the capital of France?
[OUT USER+] What is the capital of LOCATION_7a1ca4ef?   ← France = LOCATION entity
[PSEUDO DIFF] 30→41 chars (+11) | 1 replaced | types=['LOCATION']
[→ LLM   ] ... | pseudo=2835ms  ← higher because history re-pseudonymization
[→ USER  ] depseudo complete, 6 tokens | ttft=7.57s total=11.62s
```
**Note:** "France" is a valid LOCATION entity — Presidio correctly detected it.

**Retry actual result (new chat, "What is 2+2?"):**
```
[IN  USER+] What is 2+2?
[NO PII] message unchanged — no entities detected   ✅
[CONTEXT  ] 1 messages → 12 chars
[→ LLM   ] ... | pseudo=1232ms
[STREAM DONE] 2 chunks | 9 chars
[→ USER  ] depseudo complete, 0 tokens | ttft=2.69s total=2.93s
[PRIVACY AUDIT] entities=0 model=claude-opus-4-7 | ttft=2.69s total=2.93s
```
**Timing:** pseudo=1232ms | ttft=2.69s | total=2.93s (fastest test — tiny response)

---

## S3 — Multi-turn with PII (history re-pseudonymization)

**Status: ✅ PASS — 22/07/2026**

**Setup:** privacy ON, send two messages in the same chat
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
**Actual results:**

Turn 1 (session=47b31e2d):
```
[IN  USER+] My name is Max Mustermann, I work at Enclaive GmbH in Berlin.
[OUT USER+] My name is PERSON_dddfab9b, I work at ORGANIZATION_bd3a68a5 in LOCATION_dad114b6.
[PSEUDO DIFF] 61→81 chars (+20) | 3 replaced
[→ LLM   ] ... | pseudo=868ms
[→ USER  ] depseudo complete, 3 tokens | ttft=1.62s total=4.00s
```
Turn 2 (same session):
```
[HISTORY PSEUDO] pseudonymized 2 message(s) in history  ✅
[IN  USER+] What rights does Max have regarding his personal data?
[OUT USER+] What rights does PERSON_a1a5936d have regarding his personal data?
[PSEUDO DIFF] 54→66 chars (+12) | 1 replaced | types=['PERSON']
[CONTEXT  ] 3 messages → 584 chars
[→ LLM   ] ... | pseudo=2839ms  ← higher: history re-pseudonymization adds time
[MAPPING] session=47b31e2d total_tokens=4
[→ USER  ] depseudo complete, 4 tokens | ttft=4.58s total=13.98s
```
**⚠️ Note:** "Max" → PERSON_a1a5936d vs "Max Mustermann" → PERSON_dddfab9b — same person, different token. MD5 hash based on detected text span, not semantic identity. Expected behavior.

---

## S4 — Web search

**Status: ✅ PASS — 22/07/2026**

**Setup:** enable web search in OWU settings, privacy ON
**Prompt:**
```
What are the latest GDPR fines in Germany in 2024?
Max Mustermann at Enclaive GmbH wants to know.
```
**Expected logs:**
```
[IN  FILE] role=system len=XXXX  ← web results arriving
[FILE DELTA] X→Y chars (+Z)
[FILE PII] X new entities detected
[IN  USER+] Max Mustermann...
[OUT USER+] PERSON_xxx...
[PSEUDO DIFF] ...
[→ LLM   ] ... | pseudo=Xms  ← higher (web content to pseudonymize)
```
**Actual results:**
```
[IN  FILE] role=system len=4549
[FILE DELTA] 4549→4818 chars (+269)
[FILE PII] 7 new entities detected
[IN  USER+] What are the latest GDPR fines in Germany in 2024? Max Mustermann at Enclaive GmbH...
[OUT USER+] ...in LOCATION_80db4ccd... PERSON_dddfab9b at ORGANIZATION_bd3a68a5...
[PSEUDO DIFF] 97→116 chars (+19) | 3 replaced | types=[LOCATION, PERSON, ORGANIZATION]
[CONTEXT  ] 2 messages → 4934 chars
[→ LLM   ] ... | pseudo=2047ms
[← LLM   ] ttft=3.35s
[STREAM DONE] 16 chunks | 1552 chars
[→ USER  ] depseudo complete, 9 tokens | ttft=3.35s total=10.60s
```
**Timing:** pseudo=2047ms | ttft=3.35s | total=10.60s
**9 tokens** = 7 from web content + 3 from user message (overlapping entities counted once)

---

## S5 — File upload with PII

**Status: ✅ PASS — 22/07/2026**

**Setup:** upload a text file containing the content below, then ask about it
**File content to upload:**
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
[VAULT START] file_id=xxx session=file:xxx entity_filter=ALL
[VAULT DONE] file_id=xxx → X new entities | breakdown={...}
[IN  FILE] role=system len=XXXX
[FILE DELTA] X→Y chars (+Z)
[FILE PII] X new entities detected
```
**Actual results:**
```
[VAULT START] file_id=5e49756a... session=file:5e49756a... entity_filter=ALL
[VAULT DONE]  file_id=5e49756a... → 6 new entities
              breakdown={EMAIL_ADDRESS:1, LOCATION:1, PERSON:1, IBAN_CODE:1, PHONE_NUMBER:1, ORGANIZATION:1}  ✅
[IN  FILE] role=system len=1681
[FILE DELTA] 1681→1693 chars (+12)
[FILE PII] 6 new entities detected | breakdown=in-memory-only
[NO PII] message unchanged     ← "Summarize this" has no PII ✅
[CONTEXT  ] 2 messages → 1706 chars
[→ LLM   ] ... | pseudo=1705ms
[→ USER  ] depseudo complete, 6 tokens | ttft=2.48s total=5.49s
```
**Note:** vault scan runs at upload time (separate from chat). Chat request sees file entities already in mapping.

---

## S6 — Multiple PII types in one message

**Status: ✅ PASS — 22/07/2026**

**Setup:** privacy ON, entity filter ALL
**Prompt:**
```
Please contact Max Mustermann at max.mustermann@enclaive.io
His phone is +49 30 12345678 and IBAN is DE89370400440532013000.
He works at Enclaive GmbH, Torstraße 1, Berlin.
```
**Expected logs:**
```
[PSEUDO DIFF] X→Y chars | 6+ replaced | types=[PERSON, EMAIL_ADDRESS, PHONE_NUMBER, IBAN_CODE, ORGANIZATION, LOCATION]
```
**Actual results:**
```
[IN  USER+] Please contact Max Mustermann at max.mustermann@enclaive.io...
[OUT USER+] Please contact PERSON_dddfab9b at EMAIL_ADDRESS_2162ce1b
            His phone is PHONE_NUMBER_85e518b2 and IBAN is IBAN_CODE_faf7e1c0.
            He works at ORGANIZATION_bd3a68a5, Torstraße 1, LOCATION_dad114b6.
[PSEUDO DIFF] 172→190 chars (+18) | 6 replaced | types=[ORGANIZATION, LOCATION, IBAN_CODE, EMAIL_ADDRESS, PHONE_NUMBER, PERSON]  ✅
[→ LLM   ] ... | pseudo=1168ms
[→ USER  ] depseudo complete, 7 tokens | ttft=2.79s total=7.19s
```
**⚠️ Gap:** "Torstraße 1" (street address) NOT masked — Presidio detects city/country only, not street addresses.

---

## S7 — Multi-turn + file + web search (full stack)

**Status: ✅ PASS — 22/07/2026**

**Setup:** upload a file with PII, enable web search, then ask
**File content:**
```
Client: Max Mustermann, max@enclaive.io, Enclaive GmbH Berlin
```
**Prompt:**
```
Based on the uploaded file, search the web for GDPR rights
that apply to Max Mustermann as an employee.
```
**Expected logs:**
```
[VAULT DONE] ...
[IN  FILE] role=system   ← web results
[FILE DELTA] ...
[IN  FILE] role=system   ← uploaded file content
[FILE DELTA] ...
[IN  USER+] Max Mustermann...
[OUT USER+] PERSON_xxx...
```
**Actual results:**
```
[VAULT DONE] 6 new entities {EMAIL, LOCATION, PERSON, IBAN, PHONE, ORGANIZATION}  ✅
[IN  FILE] role=system len=4795    ← web search results
[FILE DELTA] 4795→4823 (+28)       ✅ web content pseudonymized
[FILE PII] 12 new entities
[OUT USER+] ...PERSON_dddfab9b as an employee.
[PSEUDO DIFF] 103→104 (+1) | 1 replaced | types=[PERSON]
[CONTEXT  ] 2 messages → 4927 chars
[MAPPING] session=XXXXXXXX total_tokens=13
[→ LLM   ] ... | pseudo=2042ms
[← LLM   ] ttft=7.30s
[STREAM DONE] 39 chunks | 4025 chars
[→ USER  ] depseudo complete, 13 tokens | ttft=7.30s total=26.20s  ✅ all 13 restored
```

---

## S8 — Privacy OFF

**Status: ✅ PASS — 22/07/2026**

**Setup:** send privacy_proxy=false via API or toggle in UI
**Prompt:**
```
My name is Max Mustermann at Enclaive GmbH.
```
**Expected logs:**
```
[GARNET] session=XXXXXXXX ... privacy=OFF ...
[PRIVACY OFF] forwarding raw → no pseudonymization
[→ LLM   ] ... | pseudo=0ms
```
**Must NOT see:** `[OUT USER+]`, `[PSEUDO DIFF]`

**Actual results:**
```
[GARNET] ... privacy=OFF                      ✅
[PRIVACY OFF] forwarding raw → no pseudonymization  ✅
[CONTEXT  ] 1 messages → 42 chars
[→ LLM   ] ... | pseudo=0ms                  ✅ zero overhead
[→ USER  ] depseudo complete, 0 tokens | ttft=1.19s total=2.27s  ✅
[PRIVACY AUDIT] entities=0 model=claude-opus-4-7 | ttft=1.19s total=2.27s  ✅
```
**Timing:** pseudo=0ms | ttft=1.19s | total=2.27s ← pure LLM speed, zero Garnet overhead

---

## S9 — 3-turn context pseudonymization proof

**Status: ⏳ PENDING**

**Goal:** prove that on turn 3+, PII from **all prior turns** (not just the current message) is still pseudonymized in the context sent to the LLM.

**Setup:** privacy ON, same chat for all 3 turns, no files, no web

**Turn 1:**
```
My name is Max Mustermann.
```
**Turn 2:**
```
I work at Enclaive GmbH in Berlin.
```
**Turn 3:**
```
Based on what I told you before, tell me my full name, company, and city — repeat them exactly.
```

**Expected logs on Turn 3:**
```
[HISTORY PSEUDO] pseudonymized 4 message(s) in history   ← turn1 user + turn1 assistant + turn2 user + turn2 assistant
[IN  USER] Based on what I told you before...
[→ LLM   ] ... | model=mistral-small-latest
[← LLM   ] "Your name is PERSON_dddfab9b..."   ← Mistral echoes pseudo tokens because that's ALL it ever saw
[→ USER  ] depseudo complete, 3 tokens in mapping
```

**Proof of full-context pseudonymization:**
- `[HISTORY PSEUDO] pseudonymized 4 message(s)` → all prior turns went through the pseudonymizer, not just the current
- `[← LLM]` chunks contain `PERSON_xxx`, `ORGANIZATION_yyy`, `LOCATION_zzz` → Mistral literally cannot produce "Max Mustermann" because it never received those bytes
- **UI shows real names restored** → depseudo mapping applies to entire response

**How to run:**
```bash
kubectl logs -n garnet deploy/garnet-open-webui-privacy-proxy -f | grep -E "HISTORY PSEUDO|OUT USER|← LLM"
```

**Verdict pass criteria:**
1. `[HISTORY PSEUDO] pseudonymized N message(s)` fires with N ≥ 2 on turn 3
2. `[← LLM]` chunks contain at least one pseudo token (`PERSON_`, `ORGANIZATION_`, or `LOCATION_`)
3. UI final message shows real names, not pseudo tokens

---

## Log checklist per test

| Log line | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 |
|---|---|---|---|---|---|---|---|---|
| `[IN  USER+]` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `[NO PII]` | - | ✓ | - | - | - | - | - | - |
| `[PSEUDO DIFF]` | ✓ | - | ✓ | ✓ | - | ✓ | ✓ | - |
| `[IN  FILE]` | - | - | - | ✓ | ✓ | - | ✓ | - |
| `[FILE DELTA]` | - | - | - | ✓ | ✓ | - | ✓ | - |
| `[HISTORY PSEUDO]` | - | - | ✓ | - | - | - | - | - |
| `[VAULT START/DONE]` | - | - | - | - | ✓ | - | ✓ | - |
| `[PRIVACY OFF]` | - | - | - | - | - | - | - | ✓ |
| `[PRIVACY AUDIT]` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
