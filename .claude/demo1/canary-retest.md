# Garnet — T4D Canary Retest
# Full test suite for Aug 19 fixed build

_Environment: demo-1.garnet.enclaive.cloud_
_Log capture: `docker logs garnet-privacy-proxy-1 --tail 30` after each test_

---

## Setup

```bash
# On cVM — capture logs live during session
docker logs -f garnet-privacy-proxy-1 2>&1 | tee /tmp/canary-$(date +%Y%m%d-%H%M%S).log
```

API key for curl tests: set your OWU key as:
```bash
export KEY=<your-owu-api-key>
```

---

## BLOCK 1 — Defect class fixes (7 original cases)

_How to run: paste the JSON into the Garnet chat UI (model: any). Then check `[OUT USER]` in proxy logs._

---

### TEST-01 — P1B-BP-002-V2 — Full PERSON leak (Class A1)

**Input (paste into chat):**
```
{"case_id": "54391f39-8249-5339-881b-b4e2555839c8", "text": "Hendrik übernimmt die Frühschicht."}
```

**Log to check:**
```
[OUT USER] {"case_id": "54391f39-...", "text": "PERSON_xxx übernimmt die Frühschicht."}
```

| Check | Pass condition |
|-------|---------------|
| `case_id` | unchanged — byte-identical |
| `"Hendrik"` | replaced with `PERSON_xxx` |
| No raw name | `"Hendrik"` must NOT appear in `[OUT USER]` |

**PASS / FAIL**

---

### TEST-02 — P1B-BP-005-V5 — Partial PERSON leak (Class A1)

**Input:**
```
{"case_id": "9291d536-c938-5903-af80-043010c3180c", "text": "Lasse Farah Marchetti übernimmt die Frühschicht."}
```

**Log to check:**
```
[OUT USER] {"case_id": "9291d536-...", "text": "PERSON_xxx übernimmt die Frühschicht."}
```

| Check | Pass condition |
|-------|---------------|
| `"Lasse"` | replaced — must NOT appear in `[OUT USER]` |
| `"Farah"` | replaced — must NOT appear in `[OUT USER]` |
| `"Marchetti"` | replaced — must NOT appear in `[OUT USER]` |
| All 3 parts | single `PERSON_xxx` span (or merged) |

**PASS / FAIL**

---

### TEST-03 — P1B-BP-001-V1 — UUID mutated + wrong entity type (Class A2 + B + C)

**Input:**
```
{"case_id": "d401852a-88c5-51ac-ae15-8d31e0e01b78", "text": "Am Montag war Adelbach nicht erreichbar."}
```

**Log to check:**
```
[OUT USER] {"case_id": "d401852a-88c5-51ac-ae15-8d31e0e01b78", "text": "Am Montag war PERSON_xxx nicht erreichbar."}
```

| Check | Pass condition |
|-------|---------------|
| `case_id` | `d401852a-88c5-51ac-ae15-8d31e0e01b78` — byte-identical, NOT `ID_xxx` |
| `"Montag"` | unchanged — must NOT be `LOCATION_xxx` |
| `"Adelbach"` | replaced with `PERSON_xxx`, NOT `LOCATION_xxx` |

**PASS / FAIL**

---

### TEST-04 — P1B-BP-009-V1 — Weekday over-redaction (Class C + A2)

**Input:**
```
{"case_id": "78d3b632-07a8-5fa5-a113-2724712376bb", "text": "Am Montag war Adelbach, Lasse nicht erreichbar."}
```

**Log to check:**
```
[OUT USER] {"case_id": "78d3b632-...", "text": "Am Montag war PERSON_xxx, PERSON_xxx nicht erreichbar."}
```

| Check | Pass condition |
|-------|---------------|
| `"Montag"` | unchanged |
| `"Adelbach"` | `PERSON_xxx` (not LOCATION) |
| `"Lasse"` | `PERSON_xxx` |

**PASS / FAIL**

---

### TEST-05 — P1B-BP-096-V0 — JSON structure corrupted (Class B)

**Input:**
```
{"case_id": "eb1a786c-2cfe-5574-946c-da5561ed8ac0", "text": "Anna Weber arbeitet als Schichtleiterin im Team.", "items": [{"id": "24972596-9a26-513a-b652-5d274ad610cf", "label": "Terminvergabe", "value": 12}, {"id": "722c6b91-b87e-5ddd-be71-5e974d5c5f10", "label": "Rasenmäher Modell R40", "value": 0}], "status": "open"}
```

**Log to check:**
```
[OUT USER] {"case_id": "eb1a786c-...", "text": "PERSON_xxx arbeitet als Schichtleiterin im Team.", "items": [{"id": "24972596-...", "label": "Terminvergabe", "value": 12}, {"id": "722c6b91-...", "label": "Rasenmäher Modell R40", "value": 0}], "status": "open"}
```

| Check | Pass condition |
|-------|---------------|
| `case_id` | unchanged |
| `"Anna Weber"` | replaced with `PERSON_xxx` |
| `items[0].id` | `24972596-9a26-513a-b652-5d274ad610cf` — unchanged |
| `items[1].id` | `722c6b91-b87e-5ddd-be71-5e974d5c5f10` — unchanged |
| `items[1].label` | `"Rasenmäher Modell R40"` — key present, value unchanged |
| `items[0].value` | `12` — unchanged |
| `status` | `"open"` — unchanged |

**PASS / FAIL**

---

### TEST-06 — P1B-BP-030-V6 — UUID mutated, email case (Class B)

**Input:**
```
{"case_id": "e92689f3-f972-552c-897e-154ea940bca6", "text": "Erreichbar unter test.user247@example.invalid."}
```

**Log to check:**
```
[OUT USER] {"case_id": "e92689f3-f972-552c-897e-154ea940bca6", "text": "Erreichbar unter EMAIL_ADDRESS_xxx."}
```

| Check | Pass condition |
|-------|---------------|
| `case_id` | `e92689f3-f972-552c-897e-154ea940bca6` — byte-identical |
| email | replaced with `EMAIL_ADDRESS_xxx` |

**PASS / FAIL**

---

### TEST-07 — P1B-BP-061-V5 — Neutral control (no PII)

**Input:**
```
{"case_id": "98ad7820-39fb-5408-9487-4d7d7e67841f", "text": "Bitte Kaffeemaschine Typ B prüfen.", "reference_id": "81f1de1f-a1d2-52ab-b4e2-4b8d25dcf202", "active": true, "score": 3}
```

**Log to check:**
```
[OUT USER] — identical to input, no changes
[NO PII] message unchanged
```

| Check | Pass condition |
|-------|---------------|
| Entire body | byte-identical to input |
| Log shows | `[NO PII]` or 0 entities replaced |

**PASS / FAIL**

---

## BLOCK 2 — Structured Outputs via Responses API

_These tests require API access (curl). Run from cVM or any machine with network access to Garnet._

---

### TEST-08 — Structured Output request correctly forwarded (GPT-5)

```bash
cat > /tmp/t08.json << 'EOF'
{"model":"gpt-5","messages":[{"role":"user","content":"Extract: John Doe works at Enclaive, email john@enclaive.io"}],"response_format":{"type":"json_schema","json_schema":{"name":"extraction","strict":true,"schema":{"type":"object","properties":{"name":{"type":"string"},"company":{"type":"string"},"email":{"type":"string"}},"required":["name","company","email"],"additionalProperties":false}}}}
EOF
curl -s -X POST http://172.18.0.5:8080/api/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/t08.json
```

**Log to check:**
```
[OUT USER] Extract: PERSON_xxx works at ORGANIZATION_xxx, email EMAIL_ADDRESS_xxx
[→ LLM   ] https://api.openai.com/v1/responses | model=gpt-5
```

**No error line like:**
```
[ERROR] status=400 ... "Unsupported parameter: 'response_format'"
```

| Check | Pass condition |
|-------|---------------|
| No 400 error | `response_format` rejected error must NOT appear |
| PII pseudonymized | `[OUT USER]` shows tokens, not raw names |
| Routed to Responses API | `[→ LLM]` shows `/v1/responses` |
| Response is JSON | curl output is valid JSON with `name`, `company`, `email` keys |

**PASS / FAIL**

---

### TEST-09 — Rehydration in structured JSON response (GPT-5)

_Same request as TEST-08. Check the response body._

**Expected curl response (after depseudo):**
```json
{"name": "John Doe", "company": "Enclaive", "email": "john@enclaive.io"}
```

| Check | Pass condition |
|-------|---------------|
| `name` field | `"John Doe"` — real name restored, NOT `PERSON_xxx` |
| `company` field | `"Enclaive"` — real org restored |
| `email` field | `"john@enclaive.io"` — real email restored |
| JSON valid | response is parseable JSON, no extra text |

**PASS / FAIL**

---

### TEST-10 — Structured Output with German PII (GPT-5)

```bash
cat > /tmp/t10.json << 'EOF'
{"model":"gpt-5","messages":[{"role":"user","content":"Extrahiere: Hendrik Müller arbeitet bei Siemens AG, erreichbar unter h.mueller@siemens.de"}],"response_format":{"type":"json_schema","json_schema":{"name":"person","strict":true,"schema":{"type":"object","properties":{"name":{"type":"string"},"company":{"type":"string"},"email":{"type":"string"}},"required":["name","company","email"],"additionalProperties":false}}}}
EOF
curl -s -X POST http://172.18.0.5:8080/api/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/t10.json
```

| Check | Pass condition |
|-------|---------------|
| `[OUT USER]` | no raw German names — all replaced with tokens |
| Response `name` | `"Hendrik Müller"` restored |
| Response `email` | `"h.mueller@siemens.de"` restored |
| JSON valid | parseable, correct keys |

**PASS / FAIL**

---

## BLOCK 3 — Regression (must still pass)

---

### TEST-11 — Normal chat still works (no structured output)

```bash
cat > /tmp/t11.json << 'EOF'
{"model":"gpt-5","messages":[{"role":"user","content":"What is 2+2?"}]}
EOF
curl -s -X POST http://172.18.0.5:8080/api/chat/completions \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/t11.json
```

| Check | Pass condition |
|-------|---------------|
| Response received | non-empty content |
| No error | no 400/500 status |

**PASS / FAIL**

---

### TEST-12 — Privacy toggle OFF still works

In Garnet UI: toggle privacy OFF → send a message with a name.

| Check | Pass condition |
|-------|---------------|
| Log shows | `[PRIVACY OFF]` |
| `[OUT USER]` | raw names forwarded (no tokens) |
| Response | normal LLM reply |

**PASS / FAIL**

---

## Log capture reference

After each test:
```bash
docker logs garnet-privacy-proxy-1 2>&1 | tail -25
```

Key lines to read:
```
[IN  USER]   — raw input (with PII)
[OUT USER]   — pseudonymized (what LLM sees)
[→ LLM   ]   — provider URL + model
[ERROR]      — any upstream error (should be empty)
[→ USER  ]   — depseudo complete, tokens restored count
```

---

## Pass criteria summary

| Test | Defect class | Must pass |
|------|-------------|-----------|
| TEST-01 | A1 | Hendrik → PERSON_xxx |
| TEST-02 | A1 | Lasse + Farah + Marchetti → PERSON_xxx |
| TEST-03 | A2 + B + C | UUID intact · Adelbach → PERSON · Montag unchanged |
| TEST-04 | C + A2 | Montag unchanged · Adelbach → PERSON |
| TEST-05 | B | JSON structure intact · Anna Weber → PERSON |
| TEST-06 | B | UUID intact · email → EMAIL_ADDRESS |
| TEST-07 | — | Neutral doc byte-identical |
| TEST-08 | new | No 400 error · routed to /v1/responses |
| TEST-09 | new | Structured JSON response with real names restored |
| TEST-10 | new | German PII in structured output restored |
| TEST-11 | regression | Normal chat unaffected |
| TEST-12 | regression | Privacy OFF still works |
