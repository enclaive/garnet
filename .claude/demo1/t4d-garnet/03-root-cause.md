# Root Cause Analysis

Date: 2026-08-06
Build: commit `dd9a4c29a` · image `sha256:33bbd35ccc84`

---

## Class A1 — Short German PERSON names not detected

**Cases:** P1B-BP-002-V2 ("Hendrik"), P1B-BP-005-V5 ("Lasse Farah Marchetti")

**Cause:**
`de_core_news_md` (medium spaCy model) was active. This model relies heavily
on surrounding syntactic context. Isolated short given names at sentence start
produce zero entities. "Hendrik" alone → 0 detections. "Hendrik Öztürk" → correctly
tagged. The large model (`de_core_news_lg`) was installed in the container but
not loaded — one line in the configuration pointed to the medium model.

---

## Class A2 — LOCATION overrides PERSON on overlapping spans

**Cases:** P1B-BP-001-V1, P1B-BP-009-V1 ("Adelbach")

**Cause:**
The overlap resolver sorted entity types by a priority set. LOCATION was
incorrectly included alongside high-confidence deterministic types (EMAIL,
IBAN, PHONE). When spaCy fired both PERSON and LOCATION on the same span
(German surnames ending in place-name patterns), LOCATION always won.
"Adelbach" → `LOCATION_d1bfe8a1` instead of PERSON on every occurrence.

---

## Class B — JSON body processed as flat text

**Cases:** P1B-BP-001-V1, P1B-BP-030-V6 (UUID mutation), P1B-BP-096-V0 (structure corruption)

**Cause:**
The proxy serialized the entire request body to a plain string before passing
it to the NER pipeline. The pipeline processed JSON keys, UUID values, colons,
and brackets alongside free text. The ID recognizer matched UUID hex-dash
patterns as ID entities and replaced them. Replacement shifted byte offsets;
on re-parse the mutated string produced broken JSON — keys disappeared, values
were truncated.

Evidence: `"case_id": "d401852a-..."` → `"case_id": "ID_32aee100-..."` with
exact hash reproducibility across runs.

---

## Class C — German weekdays tagged as LOCATION

**Cases:** P1B-BP-001-V1, P1B-BP-009-V1 ("Montag")

**Cause:**
spaCy's German model tags weekday names as LOCATION due to training data
patterns. No post-NER filter existed to reject known non-PII tokens.
"Montag" → `LOCATION_b703fc6a` on every occurrence (same hash confirms
same surface form, same code path).

---
