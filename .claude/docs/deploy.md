# deploy.md — Deploy & cVM Reference

> Commands that CHANGE cVM live here. Commands that READ cVM (logs/diagnosis) → `debug.md`.
> Pipeline structure = Mission 2 (`plan/mission2-k8s.md`).

---

## cVM access

```
ssh root@65.108.38.50          # Fedora, Docker Compose at /opt/garnet/
```
Service names: `garnet-open-webui-1`, `garnet-privacy-proxy-1`, `garnet-ollama-1`, `garnet-redis-1`, `garnet-caddy-1`.

---

## Deploy sequence (monorepo, branch `garnet-privacy-proxy`)

Pipeline auto-builds + pushes to Harbor on push. No manual docker build.

### Proxy
```bash
cd ~/Desktop/garnet
git add backend/privacy_proxy/
git commit -m "fix: your message"
git push origin garnet-privacy-proxy
# Actions: get-meta → build-proxy → trivy → cosign → deploy-proxy → tests
ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull privacy-proxy && docker compose up -d --force-recreate privacy-proxy"
```

### WebUI
```bash
cd ~/Desktop/garnet
git add src/ backend/open_webui/
git commit -m "fix: your message"
git push origin garnet-privacy-proxy
ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull open-webui && docker compose up -d --force-recreate open-webui"
```

### Force rebuild (no code change)
```bash
git commit --allow-empty -m "ci: force rebuild" && git push origin garnet-privacy-proxy
```
Watch: `https://github.com/enclaive/garnet/actions`

⚠️ Always add `--remove-orphans` on full compose deploys. `--force-recreate` on one service can drop others from the auto-named `<folder>_default` network.

---

## Digest pinning (k8s / stale-tag safety)

Harbor can serve stale `:latest` after disk-full events → pin by SHA256.
- compose: digest in `repository` field, `tag: ""`.
- Harbor UI → identify latest digest.
- `IMAGE_TAG` env var does NOT persist across SSH `&&` chains → inline per command.

---

## Rollback

```bash
ssh root@65.108.38.50 "cd /opt/garnet && IMAGE_TAG=v1.0.0 docker compose up -d --force-recreate privacy-proxy"
ssh root@65.108.38.50 "cd /opt/garnet && IMAGE_TAG=a7cf0ae docker compose up -d --force-recreate privacy-proxy"
```

---

## Harbor tags per image

```
privacy-proxy:dev / staging / prod   ← branch
privacy-proxy:1.0.0.nightly          ← VERSION file
privacy-proxy:a7cf0ae                ← short SHA
privacy-proxy:gh-run-xxx             ← pipeline run
privacy-proxy:latest                 ← git tag v*
```
`deploy/prod`→`prod`, `git tag v1.0.0`→`latest`.

---

## CI/CD pipeline (`build.yml`)

```
get-meta → build-proxy / build-webui → trivy → cosign → deploy
```
- Stops at Harbor push (deploy jobs removed per team request).
- Python checks fail builds: ruff, bandit, mypy (no `--exit-zero` / `|| true`).
- `pip-audit` pinned `2.7.3` (avoids `KeyError: 'ranges'`).
- cosign sign step `continue-on-error: true` (Rekor connectivity).
- `v*` tags protected by `protect-release-tags` ruleset (DevOps only).

### Enclaive org action restrictions
Non-Enclaive / non-allowlisted actions BLOCKED (`actions/checkout`, `aquasecurity/trivy-action`, `actions/upload-artifact`).
```yaml
# checkout → git clone
- run: git clone --branch ${{ github.ref_name }} https://x-access-token:${{ secrets.GH_TOKEN }}@github.com/enclaive/garnet.git .
# trivy → curl installer
- run: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
       trivy image --exit-code 1 --severity CRITICAL,HIGH --ignore-unfixed harbor.../image:tag
# artifact upload → scp to cVM instead
```

### Required GitHub secrets

| Secret | Owner |
|--------|-------|
| `GH_TOKEN` (repo scope) | Ion/Nicu |
| `HARBOR_USERNAME` / `HARBOR_PASSWORD` | Ion/Nicu |
| `SSH_PRIVATE_KEY` / `CVM_HOST` | Ion |
| `COSIGN_PRIVATE_KEY` / `COSIGN_PASSWORD` (empty) | Ahmed |

---

## Manual deploy (fallback only — pipeline broken)

```bash
cd ~/Desktop/garnet/backend/privacy_proxy
docker build -t harbor.enclaive.cloud/garnetdemo/privacy-proxy:latest .
docker push harbor.enclaive.cloud/garnetdemo/privacy-proxy:latest
ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull privacy-proxy && docker compose up -d --force-recreate privacy-proxy"
```

---

## Verify correct image running

```bash
ssh root@65.108.38.50 "docker image inspect harbor.enclaive.cloud/garnetdemo/garnet-webui:latest --format '{{.Created}}' && docker inspect garnet-open-webui-1 --format '{{.State.StartedAt}}'"
# image Created must be BEFORE container StartedAt
ssh root@65.108.38.50 "curl -s http://localhost:8080/health"
ssh root@65.108.38.50 "docker exec -w /service garnet-privacy-proxy-1 python3 app/test_proxy.py"
```

---

## Harbor push blocked? (`blob upload invalid`)

1. Delete old tags in Harbor UI → `garnetdemo/privacy-proxy`
2. Administration → Garbage Collection → Run GC Now
3. Still failing → ping Nicu to restart harbor-registry pod

Temp workaround (apply fix directly on container, no rebuild):
```bash
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 sed -i 's/old/new/' /service/app/main.py"
ssh root@65.108.38.50 "docker compose -f /opt/garnet/docker-compose.yml restart privacy-proxy"
```
