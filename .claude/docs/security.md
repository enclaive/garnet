# security.md — Security Issues & Hardening

> Fix before k8s production. Ask Seb before structural changes. Context: `plan/mission2-k8s.md`.

## 🔴 Critical

### 1. API keys in `webui.db` plaintext
All provider keys unencrypted in `/app/backend/data/webui.db`. Fix: k8s Secrets before prod.

### 2. Redis mappings plaintext
`mapping_store.py` → `garnet:mapping:*` stores `{PERSON_xx: "Max Mustermann", ...}` raw. Fix: AES-256 encrypt values (key in env) or Enclaive vHSM.

### 3. SSRF via `x-openai-base-url`
Attacker can point header at `169.254.169.254` or internal services. Fix: allowlist valid provider URLs. **Seb approval.**

## 🟡 Medium (before customer demo)

### 4. No auth on proxy endpoints
`/health`, `/analyze`, `/vault/scan`, catch-all all open. Fix: restrict to internal Docker network.
```bash
ssh root@65.108.38.50 "docker compose ps | grep privacy-proxy"   # must be 127.0.0.1, not 0.0.0.0
```
### 5. Webui cosign 500
Harbor lacks OCI artifact support → `.sig` can't push for webui. Ask Nicu to enable OCI in `garnetdemo`.
### 6. No k8s image verification policy
`cosign.pub` not in cluster. Ahmed Bouzid: Sigstore Policy Controller + `garnet-image-policy.yaml`.
### 7. SSH as root on cVM
Should be dedicated service account. Blocked/Ion.

## 🟢 Low

- **No rate limit on /analyze** — DoS. `slowapi` `@limiter.limit("60/minute")`.
- **No input size limit** — `MAX_TEXT_LENGTH = 10_000` → 413 if exceeded.
- **No image signing webui** — blocked by #5; uncomment cosign in `build.yml` once OCI enabled.

## Status tracker

| Issue | Sev | Fixed |
|-------|-----|-------|
| API key in logs | 🔴 | ✅ no headers logged (logs.py) |
| API keys in webui.db | 🔴 | ❌ → k8s Secrets |
| Redis plaintext | 🔴 | ❌ |
| SSRF x-openai-base-url | 🔴 | ❌ Seb |
| No proxy auth | 🟡 | ❌ internal network |
| Webui cosign 500 | 🟡 | ❌ Nicu |
| No k8s image policy | 🟡 | ❌ Ahmed Bouzid |
| SSH as root | 🟡 | ❌ Ion |
| Hardcoded key in compose | 🟡 | ✅ moved to .env |
| Network isolation | 🟡 | ✅ 3 networks |
| Rate limit | 🟢 | ❌ |
| Input size limit | 🟢 | ❌ |
| Image signing proxy | 🟢 | ✅ cosign + digest |
| Image signing webui | 🟢 | ❌ blocked |

⚠️ Rotate `IMAGES_OPENAI_API_KEY` on platform.openai.com — was hardcoded in old compose.
