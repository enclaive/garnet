# Enclaive Garnet — Corrected Build Delivery (T4D B1 fix)

Prepared for Timm Lüders / Enclaive on 2026-09-11.

This package is Enclaive's response to T4D's demo-2 reentry package
(`.../t4d-final/`) covering the synthetic B1 partial-PERSON exposure finding
on build `04f1c2ee9`. It documents the corrected build, its immutable identity,
the root cause of B1, the general fix (not tuning against the disclosed
example), regression evidence, and answers to all 8 focused questions in
`04_REENTRY_REQUIREMENTS.md`.

All test inputs are synthetic. No customer data.

## Files

- `01-delivery.md` — corrected build identity: git SHA, git tag, image
  tags, image digest, tokenizer/NER/model versions, endpoint. Mirrors the
  T+10 `01-delivery.md` fields plus the missing digest that T+5 had promised.
- `02-b1-fix.md` — root cause of B1, the general fix, before/after evidence.
  Answers Q1, Q2, Q3.
- `03-b1-evidence.md` — pre-provider verification result on the corrected
  build for the exact B1 input plus four multi-part / Unicode / hyphenated
  variants. Also the 10-case corpus pass. Answers Q4, Q5.
- `04-routing-proof.md` — one request-bound `[→ LLM]` log line proving
  strict-`response_format` calls to `/api/chat/completions` are internally
  forwarded to `/v1/responses` with `reasoning.effort` and `store:false`.
  Answers Q7.
- `05-logging.md` — the new `LOG_RAW_INPUT` environment flag, its default
  (off, in production), both states demonstrated live, orchestration-sink
  retention behaviour. Answers Q8.
- `SHA256SUMS.txt` — hashes for all five docs plus this README.

## One-line answers (see individual docs for full detail)

- **Q1** — B1 is outside the documented known limits. Documented limits
  cover over-redaction and label ambiguity; both keep the value protected.
  B1 is under-redaction: two identifying components (`Anna`, `Öztürk`)
  reached the upstream in cleartext. Confirmed defect.
- **Q2** — NER span selection under confidence thresholding. GLiNER emitted
  three separate PERSON spans; two scored below the 0.5 threshold on the
  customer's test day and were dropped before span-fusion or marker
  application ran. Contributing factor: the GLiNER model was not pinned by
  revision, so container starts could produce borderline decisions from
  small snapshot variance.
- **Q3** — General fix, not tuning: `urchade/gliner_multi_pii-v1` is now
  pinned to revision `1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d`. Same weights
  every restart, worldwide. Verified against B1 and four variants: `Anna
  Müller-Öztürk`, `Jean-François Müller`, `José García-López`, `Anne O'Brien`,
  `Ahmed Al-Rashid`.
- **Q4** — B1 added as permanent regression case `T4D-B1-V1` in
  `backend/privacy_proxy/tests/fixtures/vendor_defect_cases.jsonl` and
  covered by `test_T4D_B1_hyphenated_unicode_person` and
  `test_T4D_B1_variants_multipart_unicode_hyphenated` in
  `test_t4d_repro.py`. Both green on the corrected image.
- **Q5** — No regression. Ten-point end-to-end field check on the corrected
  image passes: name/email round-trip, UUID byte-identical, int/bool/null
  types preserved, nested dicts and arrays preserved, product/label strings
  unchanged. Streaming + structured-output assembly were already confirmed
  by the customer in their T+10 review.
- **Q6** — Immutable identity:
  - git commit SHA: `8ca75b607`
  - git tag: `v-t4d-b1-fix`
  - image: `harbor.enclaive.cloud/garnetdemo/privacy-proxy`
  - image tags: `:v-t4d-b1-fix`, `:8ca75b607`, `:1.0.0.nightly`
  - image digest: `sha256:874400c065d86b0fdc1f1d1405ccc4454270b4aee39e1f7743601aa4ec53733e`
  - endpoint: `/api/chat/completions`
  - GLiNER: `urchade/gliner_multi_pii-v1@1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d`
  - tokenizer / spaCy models: unchanged from T+10 (`de_core_news_lg`, `en_core_web_md`)
- **Q7** — Live routing capture: `[→ LLM] https://api.openai.com/v1/responses
  | model=gpt-5 | pseudo=1004ms` after a strict `json_schema` call to
  `/api/chat/completions` with `reasoning_effort=low` and `store=false`. See
  `04-routing-proof.md`.
- **Q8** — Raw input logging now gated by `LOG_RAW_INPUT` env var. Default
  `0` in production (raw content suppressed, char count still emitted).
  `LOG_RAW_INPUT=1` restores full logging for local diagnostics. Both
  states demonstrated live. See `05-logging.md`.

## Gate 1 readiness

B1 (`Anna Müller-Öztürk`) has been verified pre-provider on the corrected
image in three independent forms:

- 10-case corpus run inside the container (`03-b1-evidence.md`).
- Dedicated single-case `[OUT USER]` log line showing
  `"name": "PERSON_bdf0d8ff"` — single marker, no name component visible.
- Round-trip through `pseudonymize()` → `depseudonymize()` returning the
  original `Anna Müller-Öztürk` byte-for-byte.

The corrected image is deployed on the demo-2 cVM and is ready for T4D's
Gate 1 retest.

