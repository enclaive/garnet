---
STATUS: ready-for-impl
HANDOFF: implementer
NEXT: /implementer 2026-10-04-laya-deployment
evidence: cf21cc718c38db59883cfe2b0bee58d811fe1e3f
---

# Plan — Laya inline k8s Deployment + Service
Date: 2026-10-04

---

## BLOCKERS — resolve before touching any file

### BLOCKER 1 — Laya Harbor image path (ask Ahmed Bouzid or check Harbor)
Ahmed must confirm the exact image. Likely one of:
- `harbor.enclaive.cloud/garnetdemo/laya:latest`
- `harbor.enclaive.cloud/garnetdemo/laya:<tag>`

Check with: `curl -u <user>:<pass> https://harbor.enclaive.cloud/api/v2.0/repositories?page_size=50 | jq '.[].name'`
Or log into Harbor UI → garnetdemo project → look for a `laya` repo.

Substitute `<LAYA_IMAGE>` everywhere below once confirmed.

### BLOCKER 2 — OPENROUTER_API_KEY not in garnet-secrets
The key must be in the cluster before the proxy deployment rolls. Handled in Step 1.

---

## Goal
Run Laya as a k8s Deployment+Service in the `garnet` namespace so the privacy-proxy can call `http://laya.garnet.svc:8000/v1/systemone`.

## Approach
- Append Laya Deployment + Service as raw YAML docs (`---`) at the end of the existing helmfile.yaml (no chart changes, no new files)
- Patch `garnet-secrets` to add `OPENROUTER_API_KEY`
- Add two env vars to `privacyProxy.extraEnvVars` in the same helmfile

---

## Files to touch
- `~/Desktop/emcp/enclaive-deployment/118-garnet/helmfile.yaml` — append inline Deployment+Service, add two privacyProxy env vars

---

## Step 1 — Patch garnet-secrets (kubectl, run once)

> Do this BEFORE helmfile apply. The proxy pod reads the secret at startup.

```bash
# Get the existing secret data (base64-encoded values are preserved)
kubectl get secret garnet-secrets -n garnet -o json > /tmp/garnet-secrets-backup.json

# Add OPENROUTER_API_KEY to the secret
kubectl patch secret garnet-secrets -n garnet \
  --type='json' \
  -p='[{"op":"add","path":"/data/openrouter-api-key","value":"'"$(echo -n 'YOUR_KEY_HERE' | base64 -w0)"'"}]'

# Verify
kubectl get secret garnet-secrets -n garnet -o jsonpath='{.data.openrouter-api-key}' | base64 -d
```

Replace `YOUR_KEY_HERE` with the real key. The key name in the secret is `openrouter-api-key` (matches the `secretKeyRef` added in Step 2).

---

## Step 2 — Add env vars to privacyProxy (helmfile.yaml edit)

Under `privacyProxy:` → add an `extraEnvVars:` block. The section currently ends at `persistence: enabled: false` (line 236). Add directly below it:

```yaml
          extraEnvVars:
            - name: LAYA_URL
              value: "http://laya.garnet.svc:8000"
            - name: OPENROUTER_API_KEY
              valueFrom:
                secretKeyRef:
                  name: garnet-secrets
                  key: openrouter-api-key
```

Indentation: 10 spaces (matches the rest of the `privacyProxy:` block in this file).

---

## Step 3 — Append Laya Deployment + Service to helmfile.yaml

Add this at the very end of the file (after line 240, after `garnetDashboard: enabled: false`):

```yaml
---
# Laya model-routing service — inline manifest (not a Helm release)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: laya
  namespace: garnet
  labels:
    app: laya
spec:
  replicas: 1
  selector:
    matchLabels:
      app: laya
  template:
    metadata:
      labels:
        app: laya
    spec:
      imagePullSecrets:
        - name: garnet-pull-image-secret
      containers:
        - name: laya
          image: <LAYA_IMAGE>      # BLOCKER 1: fill in before apply
          ports:
            - containerPort: 8000
          resources:
            limits:
              memory: 1Gi
              cpu: "1"
            requests:
              memory: 256Mi
              cpu: "100m"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: laya
  namespace: garnet
spec:
  selector:
    app: laya
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

> Note: helmfile supports raw YAML docs separated by `---` in the same file. These are applied as-is by `helmfile apply`.
> If helmfile rejects raw manifests, wrap them in a `releases:` entry using `chart: .` with a local chart or use `kubectl apply -f` separately — see Fallback below.

---

## Fallback — if helmfile rejects inline raw manifests

helmfile may not support bare `apiVersion:` docs. If `helmfile diff` errors:

1. Split laya manifests into a separate file: `~/Desktop/emcp/enclaive-deployment/118-garnet/laya-manifests.yaml`
2. Apply with: `kubectl apply -f ~/Desktop/emcp/enclaive-deployment/118-garnet/laya-manifests.yaml`
3. Keep that file in the same git repo so it's tracked.

---

## Step 4 — Deploy

```bash
cd ~/Desktop/emcp/enclaive-deployment/118-garnet/

# Dry run first — check for errors before touching the cluster
helmfile diff

# Apply if diff looks right
helmfile apply
```

---

## Step 5 — Verify

```bash
# All garnet pods running?
kubectl get pods -n garnet

# Laya pod specifically
kubectl get pod -n garnet -l app=laya

# Check laya logs (should show it's listening)
kubectl logs -n garnet -l app=laya --tail=20

# Check privacy-proxy picked up the new env vars
kubectl exec -n garnet \
  $(kubectl get pod -n garnet -l app=privacy-proxy -o jsonpath='{.items[0].metadata.name}') \
  -- env | grep -E 'LAYA_URL|OPENROUTER'

# Smoke-test: proxy calls laya (send a chat request through garnet UI, then check proxy logs)
kubectl logs -n garnet -l app=privacy-proxy --tail=30 | grep -i laya
```

---

## Done when
- [ ] `kubectl get pod -n garnet -l app=laya` shows `Running`
- [ ] Privacy-proxy env shows `LAYA_URL=http://laya.garnet.svc:8000`
- [ ] A chat request through the UI triggers a laya call visible in proxy logs (no exception on `laya_pick`)

## Risks
- Laya image unknown (BLOCKER 1) — plan is on hold until confirmed
- `readinessProbe` path `/health` assumed — verify against actual Laya image; remove probe if endpoint doesn't exist
- helmfile raw-manifest support is version-dependent — Fallback section covers this
