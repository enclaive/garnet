# Garnet Proxy — Cluster Test Scenarios

Same scenarios as `test_proxy.py`, adapted for the production cluster.

**Run full suite:**
```bash
kubectl exec -n garnet deploy/garnet-open-webui-privacy-proxy -- python3 /service/app/test_proxy.py
```

---

## T01 — Health check
**Input:** `GET /health`
**Expect:** `{"status":"ok"}`

## T02 — logs.py import + all functions callable
**Input:** in-process import of all log functions
**Expect:** no crash, all 20+ log functions execute cleanly

## T03 — PERSON + ORGANIZATION
**Input:** `POST /analyze` `{"text":"Max Mustermann works at Enclaive GmbH"}`
**Expect:** `PERSON` and `ORGANIZATION` in entities

## T04 — EMAIL_ADDRESS
**Input:** `POST /analyze` `{"text":"Contact me at max@enclaive.com"}`
**Expect:** `EMAIL_ADDRESS` in entities

## T05 — IBAN_CODE
**Input:** `POST /analyze` `{"text":"IBAN: DE89370400440532013000"}`
**Expect:** `IBAN_CODE` in entities

## T06 — PHONE_NUMBER
**Input:** `POST /analyze` `{"text":"Call me at +49 172 99887766"}`
**Expect:** `PHONE_NUMBER` in entities

## T07 — German NER
**Input:** `POST /analyze` `{"text":"Mein Name ist Thomas Müller von Siemens AG"}`
**Expect:** `PERSON` detected in German text

## T08 — Entity filter header
**Input:** `POST /analyze` with header `x-garnet-entities: PERSON` on text `"Anna Schmidt, email: anna@test.com"`
**Expect:** `PERSON` returned, `EMAIL_ADDRESS` absent

## T09 — No PII
**Input:** `POST /analyze` `{"text":"What is the capital of France?"}`
**Expect:** `entities: []`

## T10 — vault/scan full pseudonymization
**Input:** `POST /vault/scan` `{"text":"Anna Schmidt, anna@enclaive.com, IBAN: DE89370400440532013000","file_id":"test-file-001","privacy_proxy":true}`
**Expect:**
- `entity_count > 0`
- `pseudonymized_text` contains `PERSON_`, `EMAIL_ADDRESS_`, `IBAN_CODE_` tokens
- Original values not present in output

## T11 — vault/scan privacy OFF
**Input:** `POST /vault/scan` `{"text":"Anna Schmidt works at Enclaive","file_id":"test-file-002","privacy_proxy":false}`
**Expect:** `entity_count=0`, `pseudonymized_text` identical to input

## T12 — German false positive guard
**Input:** `POST /analyze` `{"text":"Schreibe mir eine E-Mail"}`
**Expect:** `PERSON` NOT in entities

## T13 — Duplicate file_id upload
**Input:** `POST /vault/scan` same `file_id` and same text twice
**Expect:** first upload → `entity_count > 0`; second upload → `entity_count=0`, same tokens both times

## T14 — LOCATION
**Input:** `POST /analyze` `{"text":"I live in Berlin, Germany"}`
**Expect:** `LOCATION` in entities

## T15 — entity_breakdown field
**Input:** `POST /vault/scan` `{"text":"Hans Müller, hans@test.de, +49 30 12345678","file_id":"test-breakdown-001","privacy_proxy":true}`
**Expect:** `entity_breakdown` has `PERSON` and `EMAIL_ADDRESS` keys

## T16 — split_at_safe_boundary
**Input:** in-process unit calls
**Expect:**

| buffer | safe | remainder |
|--------|------|-----------|
| `"Hello PERSON"` | `"Hello "` | `"PERSON"` |
| `"Hello PERSON_abc123ef"` | `"Hello "` | `"PERSON_abc123ef"` |
| `"Hello world"` | `"Hello world"` | `""` |
| `"Call EMAIL_ADDRESS_cc75010d please"` | contains full token | `""` |

## T17 — All 5 entity types in one text
**Input:** `POST /analyze` `{"text":"Max Mustermann, max@test.de, +49 89 12345, DE89370400440532013000, Siemens AG"}`
**Expect:** `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `IBAN_CODE`, `ORGANIZATION` all present

## T18 — preview field in vault/scan
**Input:** `POST /vault/scan` `{"text":"Test User test@example.com","file_id":"test-preview-001","privacy_proxy":true}`
**Expect:** `preview.before` contains original, `preview.after` contains pseudonymized

## T19 — Missing file_id → error
**Input:** `POST /vault/scan` `{"text":"Some text","privacy_proxy":true}` (no `file_id`)
**Expect:** `error` or `detail` in response

## T20 — Empty text
**Input:** `POST /analyze` `{"text":""}`
**Expect:** `entities: []`
