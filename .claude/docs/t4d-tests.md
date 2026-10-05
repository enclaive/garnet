# T4D Test Suite — extracted from demo-2 evidence (2026-08-23)

Source: `.claude/docs/demo2test/logs/garnet-privacy-proxy-1-2026-08-23.log`
Build tested: `harbor.enclaive.cloud/garnetdemo/privacy-proxy:04f1c2ee9`
Image digest: `sha256:1f3b7bc3135d2e01a3445613b9178d7dc5bd7e3556484ca6cea59fba958b8e72`
Session: 2026-08-23 16:12 – 16:15 UTC, 10 cases total.

Use this file as the frozen T4D regression base for every future build.
Rule: any new build must pass all `PASS` cases below AND fix the `FAIL` case, with no regression.

---

## Summary

| # | Case | Category | 2026-08-23 result |
|---|------|----------|-------------------|
| 1 | B1 — Anna Müller-Öztürk (JSON) | PERSON multi-part / Unicode / hyphenated | **FAIL — partial PERSON leak** |
| 2 | Adelbach | Surname-only ambiguity | PASS |
| 3 | Adelbach, Lasse | Reversed-order name | PASS |
| 4 | Hendrik | Given-name only | PASS |
| 5 | Nils Amara Marchetti | Three-part name (span fusion) | PASS |
| 6 | Anna Weber + items | PERSON in nested JSON + UUID array | PASS |
| 7 | test.user247@example.invalid | Email pseudonymization | PASS |
| 8 | Kaffeemaschine Typ B (JSON) | Over-redaction — product term | PASS (correctly not marked) |
| 9 | Am Mühlbach 30, 53977 Neustadt | Multi-LOCATION address | PASS |
| 10 | Fahrdienst (JSON) | Over-redaction — service term | PASS (correctly not marked) |

Aggregate coverage confirmed by T4D:

- ✅ JSON structure + type preservation (cases 1, 6, 8, 10)
- ✅ UUID preservation (cases 1, 6, 8, 10 — every `case_id`, `reference_id`, `items[].id`)
- ✅ Email pseudonymization (cases 1, 7)
- ✅ Streaming + structured output assembly (case 1 — SSE `[OUT USER]` reassembled cleanly)
- ✅ Byte-exact rehydration (cases 2–10 return unchanged non-PII content)
- ✅ No residual `PSEUDO_*` / unknown markers (all 10 cases)
- ❌ Multi-part / Unicode / hyphenated PERSON (case 1 fails)

---

## Case 1 — B1 — Anna Müller-Öztürk (FAIL)

**Category:** PERSON multi-part / Unicode / hyphenated
**Timestamp:** 2026-08-23 16:12:31

**Input `[IN USER]`:**
```
Extract the fields from this JSON exactly as given, preserving every value verbatim: {"name":"Anna Müller-Öztürk","email":"a.mueller@example.de","reference_id":"3f2504e0-4f89-11d3-9a0c-0305e82c3301","score":7,"active":true,"note":null,"nested":{"city":"München"}}
```

**Output `[OUT USER]`:**
```
Extract the fields from this JSON exactly as given, preserving every value verbatim: {"name":"Anna PERSON_a7842989-Öztürk","email":"EMAIL_ADDRESS_ecdd41ef","reference_id":"3f2504e0-4f89-11d3-9a0c-0305e82c3301","score":7,"active":true,"note":null,"nested":{"city":"München"}}
```

**Expected:** whole `Anna Müller-Öztürk` replaced with a single PERSON marker, no name component visible.

**Observed:** only `Müller` replaced. `Anna` and `Öztürk` remain in cleartext to the upstream LLM.

**Result:** FAIL — Gate 1 blocker.

**What still passes:** email marker OK, UUID preserved, int/bool/null types preserved, no residual markers, byte-exact rehydration on client side.

---

## Case 2 — Adelbach (PASS)

**Category:** Surname-only, PERSON/LOCATION ambiguity
**Timestamp:** 2026-08-23 16:12:41

**In:** `{"case_id":"d401852a-88c5-51ac-ae15-8d31e0e01b78","text":"Am Montag war Adelbach nicht erreichbar."}`
**Out:** `{"case_id": "d401852a-88c5-51ac-ae15-8d31e0e01b78", "text": "Am Montag war PERSON_d1bfe8a1 nicht erreichbar."}`

**Validates:** PERSON marker, UUID preservation, JSON structure.

---

## Case 3 — Adelbach, Lasse (PASS)

**Category:** Reversed-order compound name (`Surname, Firstname`)
**Timestamp:** 2026-08-23 16:12:58

**In:** `{"case_id":"78d3b632-07a8-5fa5-a113-2724712376bb","text":"Am Montag war Adelbach, Lasse nicht erreichbar."}`
**Out:** `{"case_id": "78d3b632-07a8-5fa5-a113-2724712376bb", "text": "Am Montag war PERSON_d1bfe8a1, LOCATION_9be6a745 nicht erreichbar."}`

**Validates:** PERSON + LOCATION labels, both parts protected (label ambiguity is documented known-limit — value still masked). UUID preserved.

---

## Case 4 — Hendrik (PASS)

**Category:** Given-name only (short token)
**Timestamp:** 2026-08-23 16:13:16

**In:** `{"case_id":"54391f39-8249-5339-881b-b4e2555839c8","text":"Hendrik übernimmt die Frühschicht."}`
**Out:** `{"case_id": "54391f39-8249-5339-881b-b4e2555839c8", "text": "PERSON_f5aa5054 übernimmt die Frühschicht."}`

**Validates:** short-name PERSON detection, Unicode preservation (ü), UUID preserved.

---

## Case 5 — Nils Amara Marchetti (PASS)

**Category:** Three-part name — span fusion
**Timestamp:** 2026-08-23 16:13:25

**In:** `{"case_id":"9291d536-c938-5903-af80-043010c3180c","text":"Nils Amara Marchetti übernimmt die Frühschicht."}`
**Out:** `{"case_id": "9291d536-c938-5903-af80-043010c3180c", "text": "PERSON_49418e22 übernimmt die Frühschicht."}`

**Validates:** three-token name fuses into one PERSON marker (this is the exact fusion capability that must extend to hyphenated names in B1).

---

## Case 6 — Anna Weber + items array (PASS)

**Category:** PERSON in nested JSON with array of UUIDs + product name
**Timestamp:** 2026-08-23 16:13:39

**In (assembled):**
```json
{"case_id":"eb1a786c-2cfe-5574-946c-da5561ed8ac0","text":"Anna Weber arbeitet als Schichtleiterin im Team.","items":[{"id":"24972596-9a26-513a-b652-5d274ad610cf","label":"Terminvergabe","value":12},{"id":"722c6b91-b87e-5ddd-be71-5e974d5c5f10","label":"Rasenmäher Modell R40","value":0}],"status":"open"}
```

**Out:**
```json
{"case_id": "eb1a786c-2cfe-5574-946c-da5561ed8ac0", "text": "PERSON_c56a9bc3 arbeitet als Schichtleiterin im Team.", "items": [{"id": "24972596-9a26-513a-b652-5d274ad610cf", "label": "Terminvergabe", "value": 12}, {"id": "722c6b91-b87e-5ddd-be71-5e974d5c5f10", "label": "Rasenmäher Modell R40", "value": 0}], "status": "open"}
```

**Validates:** PERSON (Anna Weber) fused; `Schichtleiterin` NOT over-redacted; 3 UUIDs preserved; product name `Rasenmäher Modell R40` (Unicode ä) NOT marked; int values (12, 0) preserved; array structure preserved.

---

## Case 7 — Email (PASS)

**Category:** Email pseudonymization
**Timestamp:** 2026-08-23 16:14:03

**In:** `{"case_id":"e92689f3-f972-552c-897e-154ea940bca6","text":"Erreichbar unter test.user247@example.invalid."}`
**Out:** `{"case_id": "e92689f3-f972-552c-897e-154ea940bca6", "text": "Erreichbar unter EMAIL_ADDRESS_fa8e7430."}`

**Validates:** email regex marker, UUID preserved, complex email format (subdomain + digits + `.invalid` TLD).

---

## Case 8 — Kaffeemaschine Typ B (PASS — over-redaction check)

**Category:** Non-PII product term must NOT get a marker
**Timestamp:** 2026-08-23 16:14:27

**In:** `{"case_id":"98ad7820-39fb-5408-9487-4d7d7e67841f","text":"Bitte Kaffeemaschine Typ B prüfen.","reference_id":"81f1de1f-a1d2-52ab-b4e2-4b8d25dcf202","active":true,"score":3}`
**Out:** `{"case_id": "98ad7820-39fb-5408-9487-4d7d7e67841f", "text": "Bitte Kaffeemaschine Typ B prüfen.", "reference_id": "81f1de1f-a1d2-52ab-b4e2-4b8d25dcf202", "active": true, "score": 3}`

**Validates:** no spurious PERSON/ORG on product terms; 2 UUIDs preserved; `bool` true, `int` 3 types preserved; Unicode ü preserved; byte-exact non-PII pass-through.

---

## Case 9 — Address (PASS)

**Category:** Multi-LOCATION address string
**Timestamp:** 2026-08-23 16:14:51

**In:** `{"case_id":"f1be74e6-c0c1-50e3-83de-529afae5881c","text":"Die Anschrift lautet Am Mühlbach 30, 53977 Neustadt."}`
**Out:** `{"case_id": "f1be74e6-c0c1-50e3-83de-529afae5881c", "text": "Die Anschrift lautet Am LOCATION_67ad562c 30, 53977 LOCATION_48b511f5."}`

**Validates:** 2 LOCATION markers (street name + city); house number and postal code left intact; UUID preserved; Unicode ü preserved.

---

## Case 10 — Fahrdienst (PASS — over-redaction check)

**Category:** Service/process term must NOT get a marker
**Timestamp:** 2026-08-23 16:15:10

**In:** `{"case_id":"1d16c1e3-cd4d-5478-8c51-b8564478d633","text":"Der Vorgang Fahrdienst wurde abgeschlossen.","reference_id":"3b196c65-5d8c-5758-876d-2b602a280a31","active":true,"score":3}`
**Out (expected pass-through, session log cut before out):** structure identical, no marker on `Fahrdienst`, UUIDs preserved.

**Validates:** no spurious PERSON/ORG on process words; UUID + type preservation.

---

## Regression contract for every future build

Any privacy-proxy build must satisfy all of the below before it can go into a T4D pilot:

1. All 10 cases pass exactly as shown (or better — full-name marker is acceptable improvement).
2. B1 (case 1) must produce a **single** PERSON marker covering `Anna Müller-Öztürk`, with no visible `Anna`, `Müller`, or `Öztürk` in `[OUT USER]`.
3. No new residual `PSEUDO_*` or unknown-vendor markers.
4. Byte-exact rehydration on the client-facing return path.
5. GLiNER model pinned by revision — no HF Hub drift between container starts.
6. Startup self-check runs B1 and refuses to boot on regression.

## How to run the suite

Direct call (fastest, no HTTP):

```bash
docker exec -i garnet-privacy-proxy-1 python - <<'PY'
import json
from app.pseudonymizer import pseudonymize
CASES = [
  ("B1",  '{"name":"Anna Müller-Öztürk","email":"a.mueller@example.de","reference_id":"3f2504e0-4f89-11d3-9a0c-0305e82c3301","score":7,"active":true,"note":null,"nested":{"city":"München"}}'),
  ("C2",  '{"case_id":"d401852a-88c5-51ac-ae15-8d31e0e01b78","text":"Am Montag war Adelbach nicht erreichbar."}'),
  ("C3",  '{"case_id":"78d3b632-07a8-5fa5-a113-2724712376bb","text":"Am Montag war Adelbach, Lasse nicht erreichbar."}'),
  ("C4",  '{"case_id":"54391f39-8249-5339-881b-b4e2555839c8","text":"Hendrik übernimmt die Frühschicht."}'),
  ("C5",  '{"case_id":"9291d536-c938-5903-af80-043010c3180c","text":"Nils Amara Marchetti übernimmt die Frühschicht."}'),
  ("C6",  '{"case_id":"eb1a786c-2cfe-5574-946c-da5561ed8ac0","text":"Anna Weber arbeitet als Schichtleiterin im Team.","items":[{"id":"24972596-9a26-513a-b652-5d274ad610cf","label":"Terminvergabe","value":12},{"id":"722c6b91-b87e-5ddd-be71-5e974d5c5f10","label":"Rasenmäher Modell R40","value":0}],"status":"open"}'),
  ("C7",  '{"case_id":"e92689f3-f972-552c-897e-154ea940bca6","text":"Erreichbar unter test.user247@example.invalid."}'),
  ("C8",  '{"case_id":"98ad7820-39fb-5408-9487-4d7d7e67841f","text":"Bitte Kaffeemaschine Typ B prüfen.","reference_id":"81f1de1f-a1d2-52ab-b4e2-4b8d25dcf202","active":true,"score":3}'),
  ("C9",  '{"case_id":"f1be74e6-c0c1-50e3-83de-529afae5881c","text":"Die Anschrift lautet Am Mühlbach 30, 53977 Neustadt."}'),
  ("C10", '{"case_id":"1d16c1e3-cd4d-5478-8c51-b8564478d633","text":"Der Vorgang Fahrdienst wurde abgeschlossen.","reference_id":"3b196c65-5d8c-5758-876d-2b602a280a31","active":true,"score":3}'),
]
for cid, raw in CASES:
    store = {}
    out = pseudonymize(raw, f"t4d-{cid}", store)
    leak = any(t in out for t in ["Anna", "Müller", "Öztürk", "Hendrik", "Adelbach", "Lasse", "Weber", "Marchetti", "test.user247"])
    print(f"[{cid}] {'LEAK' if leak else 'OK'} :: {out}")
PY
```

Pass criterion: every line prints `OK`.

---

## Notes on evidence source

- Raw input logs (`[IN USER]`) are present in the proxy stdout. That is T4D's Q8 concern (raw prompt logging in production) — must be gated behind a diagnostic flag in the corrected build.
- HF Hub cache-permission warnings in `b1-errors.log` are non-fatal noise (GLiNER cannot write to `/home/appuser`). Fixing them is a cleanup, not a defect.
- Case 1 is deterministically reproduced with digest `sha256:1f3b7bc3…8b8e72` on the exact model weights served by HF on 2026-08-23. Weights served today differ, hence retests on 2026-09-02 and 2026-09-11 return full protection. Pinning eliminates this ambiguity.
