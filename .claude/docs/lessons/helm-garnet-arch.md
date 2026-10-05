# Helm for Garnet — the short lesson

> Ahmed, read this once. It maps the 3 helm pieces and the exact flow
> from `git push` to a pod running the new image.

---

## 1. The recipe / instance / config triangle

| Word | What it is | Analogy |
|------|------------|---------|
| **Chart** | A folder of `.yaml` templates + a default `values.yaml`. Reusable, versioned. | A cooking recipe |
| **Values** | Real numbers you plug into the recipe (image, replicas, host, resources) | Your grocery list |
| **Release** | The result of installing a chart with a specific set of values into a namespace | The actual meal on the plate |

One chart -> many releases (staging, prod, dev). Same recipe, different inputs.

---

## 2. How rendering works

```
templates/*.yaml   +   values.yaml   +   your override values   =   real k8s manifests
     (Go text/template)                                              (Deployment, Service, ...)
```

Anything wrapped in `{{ ... }}` is a placeholder. `helm template` (or `helm install`) walks the templates, substitutes values, and spits out normal k8s YAML.

Order of precedence (last wins):

1. Chart's own `values.yaml` (defaults)
2. `-f overrides.yaml` (helmfile / your file)
3. `--set key=value` CLI flags

If a template does NOT reference a value, that value is silently ignored. This is exactly how today's bug happened (see section 6).

---

## 3. Garnet's helm architecture — where each piece lives

| Piece | Path | Role |
|-------|------|------|
| Chart source (dev) | `/home/ahmedmarz/Desktop/helmprojects/garnet-helm/charts/open-webui/` | The recipe you edit |
| Chart metadata | `charts/open-webui/Chart.yaml` | Name + version (currently `14.7.1`) |
| Chart defaults | `charts/open-webui/values.yaml` | Sane defaults, mostly overridden |
| Chart templates | `charts/open-webui/templates/*.yaml` | The k8s YAML with `{{ }}` holes |
| Release CI | `.github/workflows/helm-release.yml` | Packages + pushes chart to Harbor on merge to `main` |
| Chart registry | `oci://harbor.enclaive.cloud/garnet/open-webui` | Where the packaged chart lives |
| Deployment config | `/home/ahmedmarz/Desktop/emcp/enclaive-deployment/118-garnet/helmfile.yaml` | Which chart version + which image + all real values |
| ArgoCD app | `enclaive-deployment/118-garnet/` is wrapped by an ArgoCD `Application` upstream | Watches this folder, syncs to cluster |

Two sub-charts pulled in as dependencies (declared in `Chart.yaml`):
- `ollama` from `otwld.github.io/ollama-helm/`
- `pipelines` from `helm.openwebui.com` (currently disabled)

---

## 4. How `118-garnet` consumes the chart (helmfile pattern)

`enclaive-deployment/118-garnet/helmfile.yaml` is short. It says:

```yaml
releases:
  - name: garnet
    namespace: garnet
    chart: oci://harbor.enclaive.cloud/garnet/open-webui
    version: 14.7.1
    values:
      - image:
          repository: harbor.enclaive.cloud/garnetdemo/garnet-webui
          digest: "sha256:82b60812..."
          pullPolicy: IfNotPresent
        # ... hundreds of lines of real overrides
```

Translate:
- `chart:` -> pull recipe `open-webui` version `14.7.1` from Harbor OCI
- `values:` -> here are my real ingredients, plug them into the templates
- `namespace:` -> install into `garnet` namespace

ArgoCD watches this folder. When you commit + push a change to `helmfile.yaml`, ArgoCD renders it with helmfile, diffs against the cluster, and applies.

---

## 5. The full flow — code fix all the way to a running pod

Real end-to-end, 6 hops:

| # | You do | What happens | Where |
|---|--------|--------------|-------|
| 1 | `git push` code fix on garnet monorepo | CI builds new webui image, tags with SHA, pushes to Harbor | `harbor.enclaive.cloud/garnetdemo/garnet-webui` |
| 2 | Grab the new digest from Harbor UI | (copy `sha256:...`) | Harbor |
| 3 | Fix chart template if the chart doesn't respect the new value | edit `charts/open-webui/templates/*.yaml`, bump `Chart.yaml` version, PR to `garnet-helm` | `helmprojects/garnet-helm` |
| 4 | Merge to `main` on `garnet-helm` | `helm-release.yml` runs: `helm package` + `helm push` to `oci://harbor.enclaive.cloud/garnet` | GitHub Actions |
| 5 | Update `helmfile.yaml`: bump `version:` and paste new `image.digest` | commit + push | `enclaive-deployment/118-garnet/helmfile.yaml` |
| 6 | ArgoCD notices new commit -> syncs -> pod restarts with new image | done | cluster `garnet` ns |

If you skip step 3 when a template doesn't handle your new value, step 5 lies to you — helmfile happily takes the value and the template ignores it. Silent no-op.

---

## 6. Why today's bug happened (the teaching example)

**Symptom:** Bumped `image.digest` in `helmfile.yaml`, argocd synced, pod kept running the old image.

**Root cause:** The chart template `charts/open-webui/templates/workload-manager.yaml` was rendering the image with only `repository + tag`. It never looked at `.digest`. So when helmfile passed `image.digest: sha256:...`, the template silently dropped it and stayed on the tag.

Compare: the privacy-proxy template already did it right (`privacy-proxy.yaml:60`):

```yaml
image: "{{ .Values.privacyProxy.image.repository }}{{- if .Values.privacyProxy.image.digest }}@{{ .Values.privacyProxy.image.digest }}{{- else }}:{{ .Values.privacyProxy.image.tag }}{{- end }}"
```

Two-line fix on branch `fix/webui-image-digest-support`, commit `f203918`:

- `charts/open-webui/templates/workload-manager.yaml:61` (initContainer)
- `charts/open-webui/templates/workload-manager.yaml:104` (main container)

Both now render:
```
image: "{{ .repository }}{{- if .digest }}@{{ .digest }}{{- else }}:{{ include "open-webui.tag" $ }}{{- end }}"
```

Lesson: **if helm renders successfully but nothing changes on the cluster, the value you passed is probably not referenced by any template.** Run `helm template . -f values.yaml | grep <thing>` to prove it before blaming argocd.

---

## 7. What still has to happen for today's fix to land in prod

- [ ] Open PR on `garnet-helm` from `fix/webui-image-digest-support` -> `main`
- [ ] Get review + merge (triggers `helm-release.yml`)
- [ ] Bump `Chart.yaml:version` from `14.7.1` -> `14.7.2` in the same PR (helm registry rejects same-version re-push)
- [ ] Verify GH Actions run pushed `open-webui-14.7.2.tgz` to `harbor.enclaive.cloud/garnet`
- [ ] Update `enclaive-deployment/118-garnet/helmfile.yaml`: bump `version: 14.7.2`, keep the digest you wanted
- [ ] Commit + push `enclaive-deployment`
- [ ] Watch ArgoCD sync the `118-garnet` app, confirm pod description shows `image: ...@sha256:82b6...`
- [ ] `kubectl -n garnet describe pod <webui-pod> | grep Image:` — must show digest, not tag

If any step fails: `helm template` locally against the new chart with the helmfile values to reproduce before touching the cluster.
