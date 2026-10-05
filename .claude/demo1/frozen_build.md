# Frozen Build — T4D Canary Baseline

> This is the configuration that was active on the cVM on **2026-08-04** when T4D ran their diagnostic tests.
> Do NOT redeploy or overwrite this until the T+10 fix is ready and T4D has signed off on the retest image.

---

## Git

| Field | Value |
|-------|-------|
| Commit SHA | `dd9a4c29a` |
| Branch | `demo1` |
| Commit message | `fix(proxy): match RESPONSES_API_MODELS by prefix to support dated model variants` |

---

## Container image

| Field | Value |
|-------|-------|
| Registry | `harbor.enclaive.cloud/garnetdemo/privacy-proxy` |
| Image digest | `sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d` |
| Short ID (docker ps) | `33bbd35ccc84` |
| Container name on cVM | `garnet-privacy-proxy-1` |
| Uptime on 2026-08-05 | "Up 9 days" → deployed approx 2026-07-27 |

---

## NER / pseudonymizer dependencies

| Package | Version |
|---------|---------|
| `presidio-analyzer` | `2.2.364` |
| `spacy` | `3.7.5` |
| German model (large) | `de-core-news-lg` `3.7.0` |
| German model (medium) | `de-core-news-md` `3.7.0` |
| English model | `en-core-web-md` `3.7.1` |

---

## Other containers (for reference)

| Container | Image | Status |
|-----------|-------|--------|
| `garnet-caddy-1` | `caddy:2.11.4` | Up 9 days |
| `garnet-open-webui-1` | `36e89e2e286d` | Up 9 days |
| `garnet-privacy-proxy-1` | `33bbd35ccc84` | Up 9 days |
| `garnet-garnet-dashboard-1` | `83bc9c8de061` | Up 13 days |
| `garnet-redis-1` | `redis:8.0.2-alpine3.23` | Up 13 days |
| `garnet-ollama-1` | `ollama/ollama:0.32.2` | Up 5 days |

---

## Immutable reference for T4D (Q6 answer)

When communicating with T4D, reference:

> **Garnet commit:** `dd9a4c29a` (branch `demo1`)
> **Proxy image digest:** `sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d`
> **Presidio:** `2.2.364` · **spaCy:** `3.7.5`
> **German NER models:** `de-core-news-lg 3.7.0` · `de-core-news-md 3.7.0`
> **English NER model:** `en-core-web-md 3.7.1`

---

*Captured: 2026-08-05*
