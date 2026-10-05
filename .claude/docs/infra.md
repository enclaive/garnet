# Infra Reference — Garnet

Single source of truth for all Helm / k8s / helmfile / Harbor infra work.

---

## Repos & roles

| Repo | Local path | GitHub | Purpose |
|------|-----------|--------|---------|
| garnet-helm | `/home/ahmedmarz/Desktop/garnet-helm/` | github.com/enclaive/garnet-helm | OCI Helm chart for the full Garnet stack. Published to Harbor. All k8s workloads are defined here. |
| enclaive-deployment | `/home/ahmedmarz/Desktop/enclaive-deployment/118-garnet/` | (private) | Helmfile that deploys the chart to the `garnet` k8s namespace. Contains all production overrides and image tags. |

---

## Key URLs & names

| Item | Value |
|------|-------|
| k8s namespace | `garnet` |
| Ingress host | `garnet.enclaive.cloud` |
| Harbor chart repo | `oci://harbor.enclaive.cloud/garnet/open-webui` |
| WebUI image | `harbor.enclaive.cloud/garnetdemo/garnet-webui` |
| Privacy-proxy image | `harbor.enclaive.cloud/garnetdemo/privacy-proxy` |
| Dashboard image | `harbor.enclaive.cloud/garnetdemo/garnet-dashboard` |
| imagePullSecret | `garnet-pull-image-secret` |
| Garnet k8s Secret | `garnet-secrets` (pre-existing, managed externally) |

---

## Chart structure

Chart root: `garnet-helm/charts/open-webui/`

| Template file | k8s resource(s) generated |
|---|---|
| `workload-manager.yaml` | `Deployment` or `StatefulSet` for Open WebUI (determined by `workload.kind`; defaults to StatefulSet when `persistence.provider=local`). Includes initContainer `copy-app-data`. |
| `privacy-proxy.yaml` | `Deployment` + `Service` (ClusterIP:8080) for the privacy-proxy. Optionally a `PersistentVolumeClaim`. Gated on `privacyProxy.enabled`. |
| `garnet-dashboard.yaml` | `Deployment` + `Service` (ClusterIP:8081) for garnet-dashboard. Also creates the `garnet-secrets` `Secret` if `garnetSecrets.create=true`. Gated on `garnetDashboard.enabled`. |
| `websocket-redis.yaml` | `Deployment` + `Service` + `PersistentVolumeClaim` for Redis. Gated on `websocket.enabled` and `websocket.redis.enabled`. |
| `ingress.yaml` | `Ingress` (networking.k8s.io/v1) + `Service` (ClusterIP:80→8080) for Open WebUI. Also contains the main Open WebUI `PersistentVolumeClaim`. |
| `pvc.yaml` | Standalone `PersistentVolumeClaim` (overlaps with ingress.yaml; ingress.yaml owns the PVC for Open WebUI). |
| `service-account.yaml` | `ServiceAccount` gated on `serviceAccount.enable` + `serviceAccount.create`. |
| `extra-resources.yaml` | Any arbitrary resources from `extraResources[]`. |
| `managed-cert.yaml` | GKE `ManagedCertificate` (gated on `managedCertificate.enabled`; not used in Garnet prod). |
| `route.yaml` | Gateway API `HTTPRoute` (gated on `route.enabled`; not used in Garnet prod). |
| `garnet-secrets.yaml` | (inline in garnet-dashboard.yaml) `Secret` named `<fullname>-garnet-secrets` when `garnetSecrets.create=true`. |
| `_helpers.tpl` | Template helpers only — no k8s resources. |

---

## `_helpers.tpl` — key helpers

| Helper | Returns |
|---|---|
| `open-webui.namespace` | Release namespace, overridable via `namespaceOverride` |
| `open-webui.name` | Chart name, overridable via `nameOverride`, truncated to 63 chars |
| `open-webui.fullname` | `<release>-<chart>` (or `fullnameOverride`), truncated to 63 chars |
| `open-webui.tag` | Image tag: uses `image.tag` if set, else `<appVersion>-slim` if `useSlim`, else `appVersion` |
| `open-webui.url` | `https://<ingress.host>` (http if no TLS) — used to set `WEBUI_URL` env var |
| `open-webui.hasCustomWebUIUrl` | `true` if `WEBUI_URL` already appears in `extraEnvVars` — prevents duplicate injection |
| `ollamaBaseUrls` | Semicolon-separated Ollama URLs combining subchart URL + `ollamaUrls` list |
| `ollamaLocalUrl` | `http://<release>-ollama.<namespace>.svc.cluster.local:11434` |
| `websocket.redis.url` | `redis://<fullname>-redis.<namespace>.svc.cluster.local:6379/0` |
| `garnet.privacyProxyUrl` | `http://<fullname>-privacy-proxy:8080` — used for all proxy env injection |
| `garnet.secretName` | `garnet-secrets` (from `garnetSecrets.existingSecret`) or `<fullname>-garnet-secrets` |
| `garnet.redisUrlKey` | Key name inside the secret for Redis URL (default: `redis-url`) |
| `privacy-proxy.selectorLabels` | Selector labels for the privacy-proxy component |
| `base.labels`, `open-webui.labels`, etc. | Standard Helm label sets (`helm.sh/chart`, `app.kubernetes.io/*`) |
| `logging.componentEnvVar` | Renders a validated `<COMPONENT>_LOG_LEVEL` env var |
| `sso.validateClientSecret` | Fails render if neither `clientSecret` nor `clientExistingSecret` is set for an SSO provider |

---

## Values reference

### Image

| Key | Default (chart) | Helmfile override |
|-----|----------------|-------------------|
| `image.repository` | `harbor.enclaive.cloud/garnetdemo/garnet-webui` | same |
| `image.tag` | `1.0.0.nightly` | `9bc82f159` |
| `image.pullPolicy` | `IfNotPresent` | `IfNotPresent` |
| `imagePullSecrets` | `[]` | `[{name: garnet-pull-image-secret}]` |

### Privacy proxy

| Key | Default (chart) | Helmfile override |
|-----|----------------|-------------------|
| `privacyProxy.enabled` | `true` | `true` |
| `privacyProxy.image.repository` | `harbor.enclaive.cloud/garnetdemo/privacy-proxy` | same |
| `privacyProxy.image.tag` | `""` | `e044d750e` |
| `privacyProxy.image.digest` | `sha256:7b281f1b2f43da866d7e5fc5623fe89fe21feb4ef77d4c0746adc13dc14e65a1` | `sha256:3eebc04cdd95af90e07cc66448ded62c0532f2ce46b99a6408462c7e3e86feb0` |
| `privacyProxy.image.pullPolicy` | `IfNotPresent` | `IfNotPresent` |
| `privacyProxy.ollamaUrl` | `http://{{ .Release.Name }}-ollama:11434` | (not overridden, uses template) |
| `privacyProxy.openaiApiUrl` | `https://api.openai.com/v1` | `https://api.openai.com/v1` |
| `privacyProxy.replicaCount` | `1` | `1` |
| `privacyProxy.service.port` / `containerPort` | `8080` / `8080` | same |
| `privacyProxy.resources.limits` | `10Gi` / `2` CPU | same |
| `privacyProxy.resources.requests` | `512Mi` / `250m` | same |
| `privacyProxy.persistence.enabled` | `false` | `false` |

Privacy proxy container gets `REDIS_URL` from the `garnet-secrets` Secret at key `redis-url`. It does **not** get `OLLAMA_BASE_URLS` injected — that goes to Open WebUI (see privacyProxy.enabled section below).

### Ollama subchart

| Key | Helmfile value |
|-----|---------------|
| `ollama.enabled` | `true` |
| `ollama.image.repository:tag` | `ollama/ollama:0.32.0` |
| `ollama.ollama.models.pull` | `[nomic-embed-text, llama3.2]` |
| `ollama.persistentVolume.size` | `50Gi` / `ceph-rbd-sc` |
| `ollama.resources.limits` | `8Gi` / `4` CPU |
| `ollama.resources.requests` | `1Gi` / `500m` |

### Websocket / Redis

| Key | Helmfile value |
|-----|---------------|
| `websocket.enabled` | `true` |
| `websocket.manager` | `redis` |
| `websocket.existingSecret` | `garnet-secrets` |
| `websocket.existingSecretKey` | `redis-url` |
| `websocket.redis.enabled` | `true` |
| `websocket.redis.image` | `redis:7-alpine` |
| `websocket.redis.command` | `redis-server --appendonly yes` |
| `websocket.redis.resources.limits` | `512Mi` |
| `websocket.redis.resources.requests` | `64Mi` / `50m` |
| `websocket.redis.persistence.enabled` | `true` / `2Gi` / `ceph-rbd-sc` |

### Persistence (Open WebUI)

| Key | Helmfile value |
|-----|---------------|
| `persistence.enabled` | `true` |
| `persistence.size` | `10Gi` |
| `persistence.storageClass` | `ceph-rbd-sc` |
| `persistence.accessModes` | `[ReadWriteOnce]` |
| `persistence.provider` | `local` |

### Resources (Open WebUI)

| | Requests | Limits |
|-|----------|--------|
| CPU | `250m` | `2` |
| Memory | `512Mi` | `4Gi` |

### Ingress

| Key | Helmfile value |
|-----|---------------|
| `ingress.enabled` | `true` |
| `ingress.class` | `public` |
| `ingress.host` | `garnet.enclaive.cloud` |
| `ingress.tls` | `true` |
| `ingress.annotations` | `cert-manager.io/cluster-issuer: letsencrypt` |

### Garnet dashboard

| Key | Helmfile value |
|-----|---------------|
| `garnetDashboard.enabled` | `true` |
| `garnetDashboard.image` | `harbor.enclaive.cloud/garnetdemo/garnet-dashboard:latest` |
| `garnetDashboard.service.port` | `8081` |
| `garnetDashboard.dockerSocket.enabled` | `true` (mounts `/var/run/docker.sock`) |
| `garnetDashboard.resources.limits` | `256Mi` / `500m` |

### Garnet secrets

| Key | Helmfile value |
|-----|---------------|
| `garnetSecrets.create` | `false` (secret is pre-existing, externally managed) |
| `garnetSecrets.existingSecret` | `garnet-secrets` |
| `garnetSecrets.keys.redisUrl` | `redis-url` |

### extraEnvVars set in helmfile

These are injected directly into the Open WebUI container:

| Name | Value |
|------|-------|
| `ENABLE_IMAGE_GENERATION` | `True` |
| `IMAGE_GENERATION_ENGINE` | `openai` |
| `IMAGE_GENERATION_MODEL` | `gpt-image-1` |
| `IMAGES_OPENAI_API_BASE_URL` | `https://api.openai.com/v1` |
| `WEBUI_NAME` | `Garnet` |
| `BYPASS_MODEL_ACCESS_CONTROL` | `true` |
| `RAG_SYSTEM_CONTEXT` | `True` |
| `CONTENT_EXTRACTION_ENGINE` | `default` |
| `ENABLE_API_KEYS` | `True` |

---

## How `privacyProxy.enabled` works

When `privacyProxy.enabled: true`, `workload-manager.yaml` **automatically overrides** four env vars on the Open WebUI container, regardless of what `ollamaUrls` or `openaiBaseApiUrl` are set to:

```yaml
# from workload-manager.yaml lines ~112-119
{{- if .Values.privacyProxy.enabled }}
- name: "OLLAMA_BASE_URLS"
  value: {{ include "garnet.privacyProxyUrl" . | quote }}
- name: "OPENAI_API_BASE_URL"
  value: {{ printf "%s/openai" (include "garnet.privacyProxyUrl" .) | quote }}
- name: "FORCE_OLLAMA_BASE_URL"
  value: {{ include "garnet.privacyProxyUrl" . | quote }}
- name: "FORCE_OPENAI_BASE_URL"
  value: {{ printf "%s/openai" (include "garnet.privacyProxyUrl" .) | quote }}
{{- end }}
```

`garnet.privacyProxyUrl` resolves to `http://<fullname>-privacy-proxy:8080`.

With `release=garnet`, this becomes `http://garnet-privacy-proxy:8080`.

So in production:
- Open WebUI sends all model traffic → `http://garnet-privacy-proxy:8080` (Ollama path) and `http://garnet-privacy-proxy:8080/openai` (OpenAI path)
- Privacy proxy receives it, pseudonymizes, forwards to the real Ollama (`http://garnet-ollama:11434`) or OpenAI API
- The proxy's own `OLLAMA_URL` env var comes from `privacyProxy.ollamaUrl` (template default: `http://{{ .Release.Name }}-ollama:11434`)

The `FORCE_*` vars are Garnet-specific additions that lock the URL even if the user tries to change it in the UI.

---

## Deploy flow

### Typical image tag update

1. Build and push new image via CI to Harbor (tag = short git SHA)
2. Edit `enclaive-deployment/118-garnet/helmfile.yaml`:
   - For WebUI: change `image.tag`
   - For privacy-proxy: change `privacyProxy.image.tag` **and** `privacyProxy.image.digest`
3. Apply:
   ```bash
   cd /home/ahmedmarz/Desktop/enclaive-deployment/118-garnet/
   helmfile apply
   ```
4. Verify rollout:
   ```bash
   kubectl rollout status statefulset/garnet -n garnet
   kubectl rollout status deployment/garnet-privacy-proxy -n garnet
   ```

### Full helmfile apply

```bash
# dry-run first
helmfile diff

# apply
helmfile apply

# or target one release
helmfile apply --selector name=garnet
```

### Package and push a new chart version to Harbor

```bash
cd /home/ahmedmarz/Desktop/garnet-helm/

# bump version in charts/open-webui/Chart.yaml first, then:
helm package charts/open-webui

# push to Harbor OCI registry
helm push open-webui-<version>.tgz oci://harbor.enclaive.cloud/garnet/

# pin the new version in helmfile.yaml:
#   version: <new-version>
```

### Current pinned versions (as of last helmfile read)

| Component | Image | Tag / Digest |
|-----------|-------|-------------|
| Open WebUI | `harbor.enclaive.cloud/garnetdemo/garnet-webui` | `9bc82f159` |
| Privacy proxy | `harbor.enclaive.cloud/garnetdemo/privacy-proxy` | tag `e044d750e` / digest `sha256:3eebc04...` |
| Ollama | `ollama/ollama` | `0.32.0` |
| Redis | `redis` | `7-alpine` |
| Garnet dashboard | `harbor.enclaive.cloud/garnetdemo/garnet-dashboard` | `latest` |
| Helm chart | `oci://harbor.enclaive.cloud/garnet/open-webui` | `14.7.1` |

---

## Workload summary

| Workload | Kind | Replicas | Port | PVC |
|----------|------|----------|------|-----|
| `garnet` (Open WebUI) | StatefulSet | 1 | 8080 | 10Gi `ceph-rbd-sc` |
| `garnet-privacy-proxy` | Deployment | 1 | 8080 | none |
| `garnet-dashboard` | Deployment | 1 | 8081 | none (docker.sock hostPath) |
| `garnet-ollama` | (subchart) | 1 | 11434 | 50Gi `ceph-rbd-sc` |
| `garnet-redis` | Deployment | 1 | 6379 | 2Gi `ceph-rbd-sc` |

All workloads in namespace `garnet`. All probes hit `/health` (proxy/ollama) or `/` (webui/dashboard).

---

## Secrets

| Secret name | How it exists | Keys |
|-------------|--------------|------|
| `garnet-secrets` | Pre-existing, externally managed (`garnetSecrets.create: false`) | `redis-url` |
| `garnet-pull-image-secret` | Pre-existing | Harbor registry credentials |

The chart will **not** create `garnet-secrets` — it must exist before `helmfile apply`. Both the privacy-proxy and garnet-dashboard read `redis-url` from it. Open WebUI reads `REDIS_URL` and `WEBSOCKET_REDIS_URL` from it via `websocket.existingSecret`.

---

## Notes / gotchas

- **Privacy-proxy image prefers digest over tag.** The template in `privacy-proxy.yaml` uses `@<digest>` when `privacyProxy.image.digest` is set, ignoring the tag. Always update both fields in helmfile.
- **StatefulSet vs Deployment.** Open WebUI runs as a StatefulSet because `persistence.provider=local` and `workload.kind=StatefulSet` is explicit. Rolling updates use `updateStrategy` not `strategy`.
- **garnetDashboard mounts docker.sock.** This is a privileged hostPath mount. Acceptable on the cVM/node but worth noting for security reviews.
- **`FORCE_OLLAMA_BASE_URL` / `FORCE_OPENAI_BASE_URL`** are Garnet-custom env vars that prevent the WebUI from letting users override the proxy endpoint.
- **`garnetSecrets.create: false`** means `helm install` will fail if `garnet-secrets` does not exist in the namespace first.
