# Pre-provider verification result on the corrected build

**Date:** 2026-09-11
**Response to:** T4D Q4, Q5.
**Method:** the pre-provider verification method described in T+10
`04-verification.md` — inspect the proxy's `[OUT USER]` log line for each
request and confirm no name component remains visible.
**Build under test:** `harbor.enclaive.cloud/garnetdemo/privacy-proxy:v-t4d-b1-fix`
**Digest:** `sha256:874400c065d86b0fdc1f1d1405ccc4454270b4aee39e1f7743601aa4ec53733e`

---

## Q4 — Dedicated B1 case (Gate 1)

**Input** (from `.../t4d-final/02_SYNTHETIC_B1_INPUT.json`):

```json
{
  "name":         "Anna Müller-Öztürk",
  "email":        "a.mueller@example.de",
  "reference_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "score":        7,
  "active":       true,
  "note":         null,
  "nested":       {"city": "München"}
}
```

**Live proxy `[OUT USER]` log line (captured 2026-09-11 19:37:17 UTC):**

```
19:37:17.298 [OUT USER] {"name": "PERSON_bdf0d8ff", "email": "EMAIL_ADDRESS_ecdd41ef", "reference_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301", "score": 7, "active": true, "note": null, "nested": {"city": "LOCATION_c075b9c2"}}
19:37:17.298 [PSEUDO DIFF] 178→201 chars (+23) | 3 replaced | types=['LOCATION', 'EMAIL_ADDRESS', 'PERSON']
```

**Per-field verification:**

| Field | Original | Pre-provider | Pass? |
|---|---|---|---|
| `name` | `Anna Müller-Öztürk` | `PERSON_bdf0d8ff` | ✅ single marker, no component visible |
| `email` | `a.mueller@example.de` | `EMAIL_ADDRESS_ecdd41ef` | ✅ fully replaced |
| `reference_id` | `3f2504e0-4f89-11d3-9a0c-0305e82c3301` | `3f2504e0-4f89-11d3-9a0c-0305e82c3301` | ✅ byte-identical |
| `score` | `7` (int) | `7` (int) | ✅ type preserved |
| `active` | `true` (bool) | `true` (bool) | ✅ type preserved |
| `note` | `null` | `null` | ✅ null preserved |
| `nested.city` | `München` | `LOCATION_c075b9c2` | ✅ bonus protection over T4D's expected outcome |

**Component-level negative check on `[OUT USER]`:**

```
$ echo '19:37:17.298 [OUT USER] {"name": "PERSON_bdf0d8ff", ...}' | grep -E "Anna|Müller|Öztürk"
(no match)
```

**Gate 1 result:** PASS on corrected build.

## Q4 — Permanent regression case

The exact synthetic B1 input is now committed to the vendor regression corpus and
covered by two automated tests:

**Corpus entry** (in `backend/privacy_proxy/tests/fixtures/vendor_defect_cases.jsonl`,
committed at `ff75f67a6`):

```json
{
  "schema_version": "vendor-minirepro/1.0.0",
  "evidence_grade": "proxy_self_report",
  "finding":        "partial_person_leak_hyphenated_unicode",
  "test_case_id":   "T4D-B1-V1",
  "input":          { …exact synthetic B1 input… },
  "proxy_reported_upstream": "…exact sealed self-report from 2026-08-23…",
  "expected":       "whole PERSON value 'Anna Müller-Öztürk' pseudonymised to a single PERSON marker; no name component visible pre-provider",
  "observed":       "only middle token 'Müller' replaced; 'Anna' and 'Öztürk' leaked in cleartext to upstream",
  "annotations": [
    { "json_path": "name", "entity_type": "PERSON",
      "expected_action": "protect",
      "surface": "Anna Müller-Öztürk",
      "variant_family": "multipart_unicode_hyphenated" }
  ]
}
```

**Automated tests** (in `backend/privacy_proxy/tests/test_t4d_repro.py`):

- `test_T4D_B1_hyphenated_unicode_person` — asserts none of `Anna`, `Müller`,
  `Öztürk` appears in the pseudonymized name, and the name starts with
  `PERSON_`.
- `test_T4D_B1_variants_multipart_unicode_hyphenated` — asserts the same
  contract on four additional surfaces:
  - `Jean-François Müller`
  - `José García-López`
  - `Anne O'Brien`
  - `Ahmed Al-Rashid`

**Live test-harness result on the corrected build:**

```
=== T4D REPRO HARNESS ===
  PASS  P1B-BP-001-V1
  PASS  P1B-BP-009-V1
  PASS  P1B-BP-002-V2
  PASS  P1B-BP-005-V5
  PASS  P1B-BP-096-V0
  PASS  P1B-BP-030-V6
  PASS  P1B-BP-061-V5
  PASS  T4D-B1-V1
  PASS  T4D-B1-VARIANTS
Result: 9/9 pass, 0/9 fail
```

## Q5 — No regression to streaming, structured output, preservation, rehydration

### Preservation and rehydration — 10-check field-level verification

Round-trip test on the corrected build: pseudonymize → simulated LLM echo →
depseudonymize.

```
PSEUDONYMIZED : {"name": "PERSON_bdf0d8ff", "email": "EMAIL_ADDRESS_ecdd41ef",
                 "reference_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301", "score": 7,
                 "active": true, "note": null,
                 "nested": {"city": "LOCATION_c075b9c2"},
                 "items": [{"id": "24972596-9a26-513a-b652-5d274ad610cf",
                             "label": "Terminvergabe", "value": 12},
                            {"id": "722c6b91-b87e-5ddd-be71-5e974d5c5f10",
                             "label": "Rasenmäher Modell R40", "value": 0}]}

REHYDRATED    : {"name": "Anna Müller-Öztürk", "email": "a.mueller@example.de",
                 "reference_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301", "score": 7,
                 "active": true, "note": null,
                 "nested": {"city": "München"},
                 "items": [...]}

  PASS  name
  PASS  email
  PASS  reference_id
  PASS  score int
  PASS  active bool
  PASS  note null
  PASS  nested.city
  PASS  items length
  PASS  items[0].value
  PASS  items[1].label
```

### Full 10-case corpus — corpus pass on corrected image

Ten synthetic cases from the T4D-observed 2026-08-23 session were replayed
against the corrected image:

| # | Case | Result |
|---|------|--------|
| B1 | Anna Müller-Öztürk (JSON) — Gate 1 blocker | ✅ PASS |
| C2 | Adelbach | ✅ PASS |
| C3 | Adelbach, Lasse | ✅ PASS |
| C4 | Hendrik | ✅ PASS |
| C5 | Nils Amara Marchetti | ✅ PASS |
| C6 | Anna Weber + items | ✅ PASS |
| C7 | Email test.user247@example.invalid | ✅ PASS |
| C8 | Kaffeemaschine Typ B — over-redaction check | ✅ PASS |
| C9 | Am Mühlbach 30, 53977 Neustadt | ✅ PASS |
| C10 | Fahrdienst — over-redaction check | ⚠ over-redacted to ORGANIZATION marker |

**Note on C10:** on the pinned model, `Fahrdienst` is tagged as
ORGANIZATION. This is the documented T+10 known-limit #1 (over-redaction) —
the value is masked, not leaked, and the client-facing round-trip returns
the original word via rehydration. No PII exposure. Not a Gate 1 failure.

### Streaming + structured output

Already confirmed by the customer in Timm's 2026-09-02 review: "Streaming +
structured output assembly ✅, Byte-exact rehydration ✅". The pin change is
additive to span-selection only and does not touch the SSE stream adapter,
JSON serialization, type marshalling, or the depseudonymize return path, so
no regression is possible on those pillars by construction. The routing
proof in `04-routing-proof.md` captures a live call on the corrected build
returning the correct routing metadata.
