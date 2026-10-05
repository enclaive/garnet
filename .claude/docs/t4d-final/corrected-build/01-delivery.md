# Corrected build — delivery identity

**Date:** 2026-09-11
**Response to:** T4D reentry package (2026-09-02), Q6.
**Format:** mirrors T+10 `01-delivery.md`, with the immutable digest that T+5
`06-remediation-answers.md` had promised for T+10.

---

## Build identity

| Field | Value |
|---|---|
| Git commit SHA | `8ca75b607` |
| Git tag | `v-t4d-b1-fix` |
| Branch | `demo1upgrade` |
| Image name | `harbor.enclaive.cloud/garnetdemo/privacy-proxy` |
| Image tags | `:v-t4d-b1-fix`, `:8ca75b607`, `:1.0.0.nightly`, `:gh-run-34634862456-1-168` |
| Image digest | `sha256:874400c065d86b0fdc1f1d1405ccc4454270b4aee39e1f7743601aa4ec53733e` |
| Client-facing endpoint | `/api/chat/completions` |
| Internal outbound endpoint (Responses-API models) | `/v1/responses` (proof: `04-routing-proof.md`) |
| Transport | `text/event-stream` (SSE) for streaming, `application/json` for non-streaming |

## Model / analyzer versions

| Component | Version | Change vs T+10 |
|---|---|---|
| GLiNER model | `urchade/gliner_multi_pii-v1` | unchanged |
| GLiNER revision | `1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d` | **newly pinned** — was floating on `main` |
| spaCy German | `de_core_news_lg` | unchanged |
| spaCy English | `en_core_web_md` | unchanged |
| Presidio Analyzer | `presidio-analyzer` (from `requirements.txt` at commit `8ca75b607`) | unchanged |
| Tokenizer | HF Transformers auto-tokenizer for `mdeberta-v3-base` (loaded by GLiNER) | unchanged |
| Python runtime | 3.11 (from Dockerfile base) | unchanged |

