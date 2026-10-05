# localdev.md — Local Dev, SSH Tunnel, Jump Host

## Stack

```
cVM:  root@65.108.38.50 (AMD SEV-SNP, Fedora) — /opt/garnet/docker-compose.yml
      services: open-webui, privacy-proxy, ollama, redis, caddy
local: ~/Desktop/garnet — branch garnet-privacy-proxy (always work here)
k8s:  Ahmed Bouzid manages — helmfile.yaml; images pinned by digest
```

## Workflow

```bash
cd ~/Desktop/garnet && git checkout garnet-privacy-proxy
# proxy: backend/privacy_proxy/app/   webui: backend/open_webui/ + src/lib/components/
git add <files> && git commit -m "fix: ..." && git push origin garnet-privacy-proxy
# pipeline builds → Harbor. Then deploy (see deploy.md).
```

## Access OWU locally via SSH tunnel

cVM runs OWU in Docker behind Caddy → can't hit port 80 directly.
```bash
ssh root@65.108.38.50 "docker inspect garnet-open-webui-1 | grep IPAddress"   # e.g. 172.18.0.5
ssh -L 8080:172.18.0.5:8080 root@65.108.38.50 -N      # keep open
# browser → http://localhost:8080
```

## Test proxy without UI

```bash
# pseudonymize
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 python3 -c \"
from app.pseudonymizer import pseudonymize
print(pseudonymize('Max Mustermann max@test.de, Enclaive GmbH, Buckypaper','test',{}))
\""
# entity detection
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 python3 -c \"
from app.pseudonymizer import detect_entities
t='Max Mustermann, Enclaive GmbH, Buckypaper, Dyneemes'
[print(e['type'], repr(t[e['start']:e['end']])) for e in detect_entities(t)]
\""
```

## Helmfile (how Ahmed Bouzid uses our image)

After Harbor push, update digest:
```yaml
privacyProxy:
  image:
    repository: harbor.enclaive.cloud/garnetdemo/privacy-proxy
    tag: ""
    digest: "sha256:<new_digest>"   ← update after push
```
Then `helmfile apply`. (Get digest from Harbor or build-proxy job output.)

## Branches

```
garnet-privacy-proxy  ← our working branch
feature-button-i      ← older OWU feature
deploy/staging        ← staging deploy
deploy/prod           ← prod deploy
```

## Message templates

To Ahmed Bouzid: `hey ahmed, new proxy image pushed to harbor. can you update the proxy digest in helmfile and apply?`
To Ion: `hey ion, harbor push failing with blob upload invalid. can you restart harbor-registry or check storage?`
To Seb: `hey seb, [change] — [reason]. [impact]. lmk if ok to proceed.`
