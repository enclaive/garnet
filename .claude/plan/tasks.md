# tasks.md — Current Work & Coordination

> Update when you start/finish. Read `mission2-k8s.md` first — Mission 2 = priority.

## 🔴 In progress

| Task | Owner | Where |
|------|-------|-------|
| demo-1 live product testing (7/7 core tests done) | Ahmed | `demo1` branch, `demo-1.garnet.enclaive.cloud` |
| PR #1 review (monorepo) | Ahmed + Ahmed Bouzid | `garnet-privacy-proxy` |
| Webui cosign 500 | — | pending Nicu |
| deploy-proxy failing in PR checks | Ahmed | Actions logs |

## ⏳ Todo — Mission 2 (priority)

| # | Task | Owner |
|---|------|-------|
| 1 | Webui cosign 500 → enable OCI in Harbor garnetdemo | Nicu |
| 2 | Fix deploy-proxy in PR checks | Ahmed |
| 3 | Add PR reviewer Ahmed Bouzid (org membership first) | Ion |
| 4 | Merge PR #1 | Ahmed Bouzid |
| 5 | Create `garnet_helm` repo + chart | Ahmed |
| 6 | k8s deploy via Helm | Ahmed Bouzid |
| 7 | Add PII mapping Redis to Helm chart | Ahmed |
| 8 | Alexa re-upload KB docs to k8s Chroma | Alexa |
| 9 | Migrate webui.db + Redis to PVC | Ahmed |
| 10 | Swap domain to cluster | Ion |
| 11 | webui lint step (`npm run lint`) | Ahmed |
| 12 | cosign k8s policy (needs cosign.pub) | Ahmed Bouzid |

## ⏳ Todo — Mission 1 (lower)

| Task | Owner |
|------|-------|
| `/analyze` customer-journey animation | — |
| Keycloak OAuth | Ion |
| Redis encryption at rest | ask Seb |
| Proxy endpoint auth | ask Seb |
| Query Expansion parallel exec (~7s) | pending Seb |

## 🚧 Blocked

| Task | By | Ask |
|------|----|----|
| Webui cosign | Harbor OCI off | Nicu |
| Ahmed Bouzid PR reviewer | not in org | Ion |
| Keycloak | infra | Ion |
| Redis encryption | architecture | Seb |
| k8s access | admin perms | Ahmed Bouzid |
| Semgrep SAST | runner vsh-ecl-runner-dind | Ion |
| vLLM migration | GPU hardware + approval | Seb |

## ✅ Done

**Mission 2:** monorepo · combined `build.yml` · version/tag detection · Trivy both images · cosign proxy · buildx cache · compose network isolation · logs.py · spaCy md · sentence-transformers removed · CVE fixes · 22 tests.
**Mission 1:** proxy extracted to repo · proxy CI/CD · orjson CVE · session isolation (`chat_id`) · multi-provider routing · per-entity toggles · (i) button · Groq/Gemini · Ollama stream=False · German false-positive · file upload pseudo · sensitive counter · RAG ORG false-positive · Opus large-context chunking · image gen fix · Query Expansion.
**demo1 fixes (2026-07-26):** `await rag_template` (3 sites in middleware.py) · `privacy_proxy` field restored to proxy after Pydantic pop in main.py (commit `26b9e5f38`).
**Cache rework (2026-08-23):** asyncio.to_thread on all pseudonymize calls · bounded LRU pseudo_cache (5000 entries, OrderedDict) · has_pseudo skip in history loop · @lru_cache on build_analyzer · async Redis flush · shared httpx client · scan_iter + in-memory file token index · secrets.token_hex session_id fallback. Commits `d4859e3fc` + `26a67c672` on `demo1upgrade`.

## Spec — /analyze endpoint
```
POST /analyze  input {text, language}  header x-garnet-entities
output {entities:[{start,end,type}]}
colors: PERSON blue · EMAIL red · ORG green · others yellow
```

## How to use
1. Check 🔴 before starting. 2. Move ⏳→🔴 + your name when starting. 3. Move →✅ + key files when done.
