# Garnet — Production Cluster Test Scenarios

**Run the full suite:**
```bash
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- \
  python3 /service/app/test_proxy.py
```

**Run with live logs in a second terminal:**
```bash
kubectl logs -n garnet deploy/garnet-open-webui-privacy-proxy -f
```

---

## T01 — Health check
```bash
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- \
  curl -s http://localhost:8080/health
```
**Expect:** `{"status":"ok"}`
**Logs:** `[HEALTH] ping received → ok`

---

## T02 — logs.py import + all functions callable
Covered by `test_proxy.py` T02 — runs in-process, no HTTP.
**Expect:** no crash, all 20+ log functions callable.

---

## T03 — PERSON + ORGANIZATION (English)
```bash
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- \
  curl -s -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Max Mustermann works at Enclaive GmbH"}'
```
**Expect:** `entities` contains `PERSON` and `ORGANIZATION`
**Logs:** `[ANALYZE]` + `[ANALYZE RESULT] 2 entities found`

---

## T04 — EMAIL_ADDRESS
```bash
-d '{"text":"Contact me at max@enclaive.com"}'
```
**Expect:** `EMAIL_ADDRESS` in entities

---

## T05 — IBAN_CODE
```bash
-d '{"text":"IBAN: DE89370400440532013000"}'
```
**Expect:** `IBAN_CODE` in entities

---

## T06 — PHONE_NUMBER
```bash
-d '{"text":"Call me at +49 172 99887766"}'
```
**Expect:** `PHONE_NUMBER` in entities

---

## T07 — German NER
```bash
-d '{"text":"Mein Name ist Thomas Müller von Siemens AG"}'
```
**Expect:** `PERSON` detected despite German text

---

## T08 — Entity filter header
```bash
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- \
  curl -s -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -H "x-garnet-entities: PERSON" \
  -d '{"text":"Anna Schmidt, email: anna@test.com"}'
```
**Expect:** `PERSON` returned, `EMAIL_ADDRESS` absent (filtered)
**Logs:** `[ENTITY FILTER] active → only: PERSON`

---

## T09 — No PII
```bash
-d '{"text":"What is the capital of France?"}'
```
**Expect:** `entities: []`
**Logs:** `[NO PII] message unchanged`

---

## T10 — vault/scan full pseudonymization
```bash
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- \
  curl -s -X POST http://localhost:8080/vault/scan \
  -H "Content-Type: application/json" \
  -d '{"text":"Anna Schmidt, anna@enclaive.com, IBAN: DE89370400440532013000","file_id":"test-prod-001","privacy_proxy":true}'
```
**Expect:**
- `entity_count > 0`
- `pseudonymized_text` contains `PERSON_`, `EMAIL_ADDRESS_`, `IBAN_CODE_`
- Original values not present in output

**Logs:**
```
[VAULT START] file_id=test-prod-001 ...
[FILE PII] 3 new entities detected | breakdown={...}
[VAULT DONE] file_id=test-prod-001 → 3 new entities
```

---

## T11 — vault/scan privacy OFF
```bash
-d '{"text":"Anna Schmidt works at Enclaive","file_id":"test-prod-002","privacy_proxy":false}'
```
**Expect:** `entity_count=0`, `pseudonymized_text` == original
**Logs:** `[VAULT SKIP] privacy=OFF file_id=test-prod-002`

---

## T12 — German false positive guard
```bash
-d '{"text":"Schreibe mir eine E-Mail"}'
```
**Expect:** `PERSON` NOT in entities (verb "Schreibe" must not trigger)

---

## T13 — Duplicate file_id upload
Upload same `file_id` twice.
**Expect:**
- First: `entity_count > 0`, tokens assigned
- Second: `entity_count = 0` (already in mapping), same tokens returned

**Logs:** `[FILE PII] 0 new entities — already in mapping (duplicate upload)`

---

## T14 — LOCATION
```bash
-d '{"text":"I live in Berlin, Germany"}'
```
**Expect:** `LOCATION` in entities

---

## T15 — entity_breakdown field
```bash
-d '{"text":"Hans Müller, hans@test.de, +49 30 12345678","file_id":"test-bd-001","privacy_proxy":true}'
```
**Expect:** `entity_breakdown` contains `PERSON` and `EMAIL_ADDRESS` keys

---

## T16 — split_at_safe_boundary (chunk safety)
Covered by `test_proxy.py` T16 — in-process unit check.

| Input | Expected safe | Expected remainder |
|-------|--------------|-------------------|
| `"Hello PERSON"` | `"Hello "` | `"PERSON"` |
| `"Hello PERSON_abc123ef"` | `"Hello "` | `"PERSON_abc123ef"` |
| `"Hello world"` | `"Hello world"` | `""` |
| `"Call EMAIL_ADDRESS_cc75010d please"` | contains full token | `""` |

---

## T17 — All 5 entity types in one text
```bash
-d '{"text":"Max Mustermann, max@test.de, +49 89 12345, DE89370400440532013000, Siemens AG"}'
```
**Expect:** `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `IBAN_CODE`, `ORGANIZATION` all present

---

## T18 — preview field in vault/scan
```bash
-d '{"text":"Test User test@example.com","file_id":"test-preview-001","privacy_proxy":true}'
```
**Expect:** response has `preview.before` (original) and `preview.after` (pseudonymized)

---

## T19 — Missing file_id → error
```bash
-d '{"text":"Some text","privacy_proxy":true}'
```
**Expect:** `error` or `detail` field in response
**Logs:** `[VAULT ERROR] missing file_id field`

---

## T20 — Empty text
```bash
-d '{"text":""}'
```
**Expect:** `entities: []`, no crash

---

## Timing reference (healthy cluster)

| Endpoint | Expected p50 | Concern if > |
|----------|-------------|--------------|
| `/health` | < 5ms | 50ms |
| `/analyze` (short text) | 50–200ms | 500ms |
| `/analyze` (German NER) | 100–300ms | 800ms |
| `/vault/scan` (3 entities) | 100–400ms | 1s |
| `/vault/scan` (duplicate) | < 50ms | 200ms |

---

## Live log tailing during test

```bash
# terminal 1 — run tests
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- \
  python3 /service/app/test_proxy.py

# terminal 2 — watch logs
kubectl logs -n garnet deploy/garnet-open-webui-privacy-proxy -f \
  | grep -E "\[GARNET\]|\[ANALYZE\]|\[VAULT\]|\[ERROR\]|\[→ LLM\]|\[PRIVACY AUDIT\]"
```
