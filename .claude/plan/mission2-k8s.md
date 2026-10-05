# mission2-k8s.md — Production Kubernetes Migration

> Source: Sebastian, Mattermost, May 2026. **Read before any task.**

## Goal
Move Garnet from cVM (Docker Compose) → production k8s. Make it a deployable Enclaive service (like Mattermost, Nextcloud).

## Tasks (in order)

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | Build pipelines (UI + proxy + security checks) | Ahmed | ✅ |
| 2 | Create Helm chart in `garnet_helm` repo | Ahmed | ⏳ |
| 3 | Deploy via Helm/GitOps to prod cluster | Ahmed Bouzid | ⏳ admin perms |
| 4 | Migrate VM state → k8s (Redis + secrets) | Ahmed | ⏳ |
| 5 | Swap domain `garnet.enclaive.cloud` → cluster | Ahmed Bouzid | ⏳ |
| 6 | 1-week grace (both run parallel) | — | ⏳ |
| 7 | Kill cVM `65.108.38.50` | Sebastian | ⏳ |

## Monorepo ✅

Proxy moved into `enclaive/garnet` (branch `garnet-privacy-proxy`):
```
backend/privacy_proxy/app/  (main.py, logs.py, pseudonymizer.py, depseudonymizer.py,
                             mapping_store.py, custom_recognizers.py, test_proxy.py)
backend/open_webui/   src/   version/VERSION ("1.0.0")
docker-compose.yml  .env (never commit)  .github/workflows/build.yml
```
PR #1: `garnet-privacy-proxy` → `feature-button-i`. Reviewer Ahmed Bouzid (needs enclaive org — ask Ion).

## Pipeline ✅ (`build.yml`)

```
get-meta → build-proxy / build-webui → trivy → cosign → deploy
```
get-meta outputs: version (VERSION/tag), tag (branch), revision (SHA), proxy_changed, webui_changed.
Tag detection: `deploy/staging`→staging, `deploy/prod`→prod, `v*`→latest, else SHA.
4 Harbor tags/image: branch · version · SHA · gh-run.
Security: Trivy CRITICAL/HIGH ignore-unfixed ✅ · cosign proxy digest-based ✅ · cosign webui ❌ 500 (Harbor OCI → Nicu) · buildx cache ✅.
Cosign keys: `~/Desktop/cosign.key`+`.pub`; secrets `COSIGN_PRIVATE_KEY`+`COSIGN_PASSWORD`(empty). `cosign.pub` → Ahmed Bouzid for k8s policy.
Pending: webui cosign 500 (Nicu) · webui lint (`npm run lint`) · cosign k8s policy · deploy-proxy failing after 7s in PR #1.

## Docker Compose ✅
API key → `.env`. 3 networks: frontend (caddy+webui), backend (webui+proxy+dashboard), internal (proxy+redis+ollama). ⚠️ Rotate `IMAGES_OPENAI_API_KEY` (was hardcoded).

## Proxy improvements ✅
logs.py (30 fns) · spaCy lg→md (saves ~1GB) · sentence-transformers removed (~1.5GB) · CVE fixes libcap2/libsystemd0/libudev1 · 22 tests (test_proxy.py). Image: ~4-5GB → ~800MB.
```bash
ssh root@65.108.38.50 "docker exec -w /service garnet-privacy-proxy-1 python3 app/test_proxy.py"
```

## State migration (cVM → k8s)

| State | Now | k8s |
|-------|-----|-----|
| Redis mappings | garnet-redis-1 | Redis PVC / managed |
| webui.db | /app/backend/data/ | PVC |
| API keys | .env | Secrets |
| env vars | .env | ConfigMap + Secrets |

Steps: `redis-cli dump` `garnet:mapping:*` → copy webui.db to PVC → `.env`→Secrets → health check before domain swap.
⚠️ Open k8s gaps: PII mapping Redis doesn't exist yet (`garnet-secrets` points to cVM Redis); ChromaDB KB empty (Alexa re-uploads); OWU SQLite config still default (needs `kubectl exec` + Seb).

## Helm chart spec (`garnet_helm`) ⏳
```yaml
privacyProxy: {image: .../privacy-proxy:latest, replicas: 1, memory: 10Gi, port: 8080}
openWebUI:    {image: .../garnet-webui:latest, replicas: 1, port: 8080}
redis:   {enabled: true, ttl: 3600}
ollama:  {enabled: true}
ingress: {host: garnet.enclaive.cloud, tls: true}
keycloak:{enabled: false}
cosign:  {enabled: true, publicKey: <cosign.pub>}
```

## Critical rules
NEVER remove `body["stream"]=False` · NEVER expose `0.0.0.0` · NEVER log headers · NEVER commit cosign.key/.env · ALWAYS ask Seb before structural changes · ALWAYS verify in running container before done.

## On the horizon
vLLM migration (beats Ollama under load; pending GPU + Seb; only renames `OLLAMA_URL`) · Query Expansion parallel exec (~7s→pending Seb) · Keycloak SSO (Ion; needs realm/client/redirect) · Semgrep SAST (stuck on runner `vsh-ecl-runner-dind` — Ion restart) · Harbor OCI + auto-scan SBOM (Nicu) · semantic release (deferred).

## Contacts
admin k8s → Ahmed Bouzid · DNS/domain → Ion · Harbor OCI → Nicu · GitHub org → Ion/Nicu · architecture → Sebastian.
