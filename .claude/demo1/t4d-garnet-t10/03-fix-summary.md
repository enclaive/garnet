# Fix Summary — T+10 Delivery

Date: 2026-08-19
Build: commit `2472723a4` · tag `t4d-canary-1`

---

## Defect class A1 — Short German given names not detected (full PERSON leak)

Cases: P1B-BP-002-V2 (Hendrik), P1B-BP-005-V5 (Lasse Farah Marchetti)

Root cause: the active German NER model (`de_core_news_md`) relied on syntactic
context. Isolated short given names at sentence start produced zero detections.

Fix: switched to `de_core_news_lg` + added GLiNER zero-shot transformer NER
(`urchade/gliner_multi_pii-v1`) as a second detection layer. GLiNER runs before
Presidio and handles isolated names, partial names, and multi-token spans that
the spaCy model misses.

Result: "Hendrik" → `PERSON_xxx`, "Lasse Farah Marchetti" → `PERSON_xxx` (all
three components replaced as a single span).

---

## Defect class A2 — LOCATION overrides PERSON on overlapping spans

Cases: P1B-BP-001-V1, P1B-BP-009-V1 (Adelbach)

Root cause: the overlap resolver assigned higher priority to LOCATION than PERSON.
When both labels fired on the same span, LOCATION always won.

Fix: GLiNER correctly classifies ambiguous German surnames as PERSON. The overlap
resolver now uses GLiNER output as the primary signal, with Presidio spaCy as
fallback. LOCATION no longer overrides a PERSON label on the same span.

Result: "Adelbach" → `PERSON_xxx`.

---

## Defect class B — UUID and JSON structure mutation

Cases: P1B-BP-001-V1, P1B-BP-030-V6, P1B-BP-096-V0

Root cause: the proxy serialised the full request body to a flat string before
passing it to the NER pipeline. UUID hex patterns were matched as ID or PERSON
entities and replaced, shifting byte offsets and corrupting JSON structure.

Additionally, OWU line-wraps long strings at render time, inserting real newlines
mid-UUID. This caused `json.loads()` to fail, falling back to flat
pseudonymization where UUID fragments were again detected as PERSON.

Fix (two layers):
1. JSON-aware tree walker — pseudonymization operates on string values only.
   Keys, UUIDs, numbers, booleans, and enums pass through byte-identical.
2. UUID fragment filter — any entity span whose text matches a UUID hex pattern
   (with whitespace normalization) is excluded from the entity list before
   replacement. Applied to both GLiNER and Presidio outputs.

Result: all `case_id` and `reference_id` values pass through byte-identical.
JSON structure intact across all nested cases.

---

## Defect class C — German weekdays tagged as LOCATION

Cases: P1B-BP-001-V1, P1B-BP-009-V1 (Montag)

Root cause: spaCy's German model tags weekday names as LOCATION due to training
data patterns.

Fix: hardcoded denylist of all seven German weekdays applied after NER analysis.
Any entity span matching a weekday name is removed regardless of the model's
label or confidence score.

Result: "Montag", "Dienstag", etc. → unchanged in all cases.

---

## Summary table

| Defect class | Cases affected | Status |
|--------------|---------------|--------|
| A1 — PERSON full leak | P1B-BP-002-V2, P1B-BP-005-V5 | Fixed |
| A2 — PERSON/LOCATION overlap | P1B-BP-001-V1, P1B-BP-009-V1 | Fixed |
| B — UUID/JSON mutation | P1B-BP-001-V1, P1B-BP-030-V6, P1B-BP-096-V0 | Fixed |
| C — Weekday over-redaction | P1B-BP-001-V1, P1B-BP-009-V1 | Fixed |
| Structured Outputs (Responses API) | — | Fixed — see 02-structured-outputs.md |
| Neutral control P1B-BP-061-V5 | — | Unchanged — passes as before |
