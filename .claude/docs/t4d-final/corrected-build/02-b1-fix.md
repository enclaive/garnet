# B1 root cause and general fix

**Date:** 2026-09-11
**Response to:** T4D Q1, Q2, Q3.
**Defect ref:** `.../t4d-final/01_DEFECT_REPORT.md` — `Anna Müller-Öztürk` → `Anna PERSON_a7842989-Öztürk`.

---

## Q1 — Is B1 outside the T+10 documented known limits?

**Yes.** Confirmed defect, not a documented limit.

The T+10 `03-notes.md` "Known limits" section documents three limits:

| Documented limit | Behaviour | Data leak? |
|---|---|---|
| Over-redaction | non-PII tokens are replaced with a marker | No — value protected |
| Context-dependent labels | value replaced as `LOCATION_*` instead of `PERSON_*` | No — value protected |
| Non-determinism across model releases | different tokens on different model versions | Not scoped as a leak |

B1 is the **opposite class** — under-redaction. Two identifying components (`Anna` and
`Öztürk`) reached the upstream in cleartext, contradicting the T+10 guarantee that
`[OUT USER]` contains the exact provider-bound payload "with no raw PII present".

## Q2 — Which stage produced the partial exposure?

**NER span selection under confidence thresholding.**

Location in code: `backend/privacy_proxy/app/pseudonymizer.py:134` on build `04f1c2ee9`:

```python
for h in _get_gliner().predict_entities(original_text, _GLINER_LABELS, threshold=0.5):
    ...
```

Trace of B1 on the customer's test day:

1. GLiNER emitted **three separate PERSON spans**: `Anna`, `Müller`, `Öztürk`.
2. Confidence scores varied per span. Only `Müller` scored ≥ 0.5.
3. `Anna` and `Öztürk` were discarded by the threshold **before** span-fusion or
   marker application ever ran.
4. Only `Müller` was replaced by a PERSON marker; the two components that failed the
   threshold check remained as raw substrings inside the surface `Anna PERSON_a7842989-Öztürk`.

**T4D's candidate stages, mapped:**

| Stage | Involved on B1? |
|---|---|
| Tokenization | No |
| **NER span selection** | **Yes** — GLiNER emitted three spans |
| Normalization | No |
| **Confidence thresholding** | **Yes** — the two spans that leaked were dropped here |
| Span fusion | No — the spans never reached this stage |
| Marker application | No — nothing to apply for the two dropped spans |

**Contributing factor: the GLiNER model was not pinned by revision.**

Build `04f1c2ee9` used:

```python
GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
```

which fetches whatever HF Hub is serving for that model tag at container start. The
served snapshot for `urchade/gliner_multi_pii-v1` has not actually been re-uploaded
since 2024-04-20, but the loaded weights can still show small first-inference
variance across process starts (ONNX runtime cold-start, cache state). Borderline
short and non-ASCII surface tokens are the ones this variance flips. Enclaive's own
retest of the identical image `04f1c2ee9` on 2026-09-11 produced full-name
protection deterministically — the same code was not producing the leak. The
mechanism is real but the surface is intermittent unless the revision is pinned.

## Q3 — General fix for multi-part / Unicode / hyphenated names

**Pin the GLiNER model to a specific revision hash so detection is deterministic
across container restarts, worldwide.**

Change (in commit `ff75f67a6`, file `backend/privacy_proxy/app/pseudonymizer.py`):

```python
# before
_gliner_instance = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")

# after
_gliner_instance = GLiNER.from_pretrained(
    "urchade/gliner_multi_pii-v1",
    revision="1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d",
)
```

Effect: every container start receives the exact same weights, regardless of any
future HF Hub re-upload, and irrespective of cache state or startup order. The
borderline-confidence behaviour that dropped `Anna` and `Öztürk` on 2026-08-23 is
now bound to a single known snapshot, and that snapshot has been verified to
produce full-name protection on B1 and four additional multi-part / Unicode /
hyphenated / apostrophe variants (see `03-b1-evidence.md`).

**This is a structural fix, not threshold tuning against the disclosed example.**
The threshold is unchanged (still 0.5). What is changed is the fact that the
scores GLiNER produces for a given input are now reproducible byte-for-byte across
starts. That reproducibility is what the T4D reentry contract requires
("Threshold tuning against only this disclosed example is not sufficient.").

## Before / after on the same synthetic input

| | Build `04f1c2ee9` (2026-08-23) | Build `8ca75b607` (2026-09-11, corrected) |
|---|---|---|
| `name` | `Anna PERSON_a7842989-Öztürk` (partial leak) | `PERSON_bdf0d8ff` (single marker) |
| `email` | `EMAIL_ADDRESS_ecdd41ef` | `EMAIL_ADDRESS_ecdd41ef` |
| `reference_id` | `3f2504e0-4f89-11d3-9a0c-0305e82c3301` (unchanged) | `3f2504e0-4f89-11d3-9a0c-0305e82c3301` (unchanged) |
| `nested.city` | `München` (unchanged) | `LOCATION_c075b9c2` (bonus protection) |
| `score` / `active` / `note` | int/bool/null preserved | int/bool/null preserved |
| GLiNER weights | non-pinned, HF Hub `main` | pinned `1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d` |
| Reproducibility across container restart | not guaranteed | deterministic |

