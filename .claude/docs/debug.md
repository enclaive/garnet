# debug.md — Diagnostics, Logs & Read-Only Inspection

> READ-only cVM commands. Anything that changes state → `deploy.md`.

---

## Step 1 — what's running

```bash
ssh root@65.108.38.50 "cd /opt/garnet && docker compose ps"
```

## Live structured logs

```bash
ssh root@65.108.38.50 "docker compose -f /opt/garnet/docker-compose.yml logs -f privacy-proxy 2>&1 | grep -E 'GARNET|IN USER|OUT USER|IN FILE|OUT FILE|FILE PII|INTERNAL|PRIVACY OFF|→ LLM|← LLM|→ USER|ERROR'"
```
Filtered views: `IN FILE|OUT FILE|FILE PII` (uploads) · `→ LLM` (routing) · `GARNET` (sessions).

## Log format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[GARNET] session={id} provider={url} privacy=ON/OFF
[IN  USER] raw user message[:200]
[OUT USER] pseudonymized message[:200]      ← privacy ON + PII found
[IN  FILE] len=N | file content[:200]       ← file uploaded
[OUT FILE] pseudonymized file content[:200]
[FILE PII] N new entities detected
[→ LLM   ] provider url | model=xxx
[← LLM   ] first chunk[:200]
[→ USER  ] depseudo complete, N tokens in mapping
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
Internal prompt: `[INTERNAL] type=title_gen/follow_ups/tags_gen/search_query → skipped`.
Privacy off: `[PRIVACY OFF] forwarding raw → no pseudonymization`.
Startup: `[MAPPING STORE]` Redis connection status.

Removed logs (noise / security): `[DEBUG HEADERS]` 🔴 leaked API key, `[DEBUG CONTENT]`, `[BODY *]`, `[REQUEST PATH]`, `[IS_CHAT]`, per-chunk `[DEPSEUDO OUT]`. Use the structured block instead.

## WebUI logs

```bash
ssh root@65.108.38.50 "cd /opt/garnet && docker compose logs --tail=50 open-webui | grep -i 'GARNET\|error\|model\|openai\|connect'"
```

## Verify code in JS bundle

```bash
ssh root@65.108.38.50 "grep -r 'garnet_entity_toggles' /app/build/_app/immutable/ 2>/dev/null | head -3"
ssh root@65.108.38.50 "grep -r 'x-garnet-entities'   /app/build/_app/immutable/ 2>/dev/null | head -3"
ssh root@65.108.38.50 "grep -r 'pseudonymized_prompt' /app/build/_app/immutable/ 2>/dev/null | head -3"
```

## Disk space (cVM)

Container fails with `OSError: No space left on device /tmp/torchinductor_appuser` = disk full, not `/tmp` issue.

```bash
df -h                        # check all partitions
docker system df             # docker images/volumes usage
docker image prune -a -f     # remove ALL unused images (frees most space)
docker system prune -a -f    # nuclear: removes images + stopped containers + cache
```

## Verify fix in running container

```bash
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 grep -n 'your_fix' /service/app/main.py"
```

## Test proxy directly

```bash
# entity filter — only PERSON returns
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 python3 -c \"
import urllib.request, json
data = json.dumps({'text':'Max Mustermann works at Enclaive GmbH, email max@enclaive.com'}).encode()
req = urllib.request.Request('http://localhost:8080/analyze', data=data,
  headers={'Content-Type':'application/json','x-garnet-entities':'PERSON'})
print(urllib.request.urlopen(req).read().decode())
\""
ssh root@65.108.38.50 "curl -s http://localhost:8080/health"
```

## Check Redis

```bash
ssh root@65.108.38.50 "docker exec garnet-redis-1 redis-cli keys 'garnet:mapping:*'"
ssh root@65.108.38.50 "docker exec garnet-redis-1 redis-cli get 'garnet:mapping:SESSION_ID'"
ssh root@65.108.38.50 "docker exec garnet-redis-1 redis-cli ttl 'garnet:mapping:SESSION_ID'"
ssh root@65.108.38.50 "docker exec garnet-redis-1 redis-cli flushall"   # only if double-pseudo corruption
```

## Check OWU DB config (requests bypass proxy?)

```bash
ssh root@65.108.38.50 "docker exec garnet-open-webui-1 python3 -c \"
import sqlite3, json
conn=sqlite3.connect('/app/backend/data/webui.db')
c=json.loads(conn.execute('SELECT data FROM config').fetchone()[0])
print(json.dumps(c.get('openai',{}),indent=2)); conn.close()
\""
```

## cVM health

```bash
ssh root@65.108.38.50 "df -h / && free -h"
```

## Common failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Tokens in response (`PERSON_xxx` visible) | stream=True somewhere | force `body["stream"]=False` |
| System prompts pseudonymized | missing marker | add to `SYSTEM_PROMPT_MARKERS` |
| Entity toggle no effect | header stripped | add `x-garnet-entities` to `get_headers_and_cookies()` |
| (i) button missing | `pseudonymized_prompt` tree-shaken | module-level ref in Chat.svelte |
| 405 on `/analyze`,`/health` | route after catch-all | move above `/{path:path}` |
| Requests bypass proxy | DB overrides env | check `webui.db` openai config |
| Ollama bypasses proxy | WebSocket on | `ENABLE_WEBSOCKET_SUPPORT=False` |
| New image not loading | Action cache | empty commit → force rebuild |
| Container has old code | image older than container | `pull` + `--force-recreate` |
| Proxy loops to itself | `x-openai-base-url` = proxy URL | self-loop check |
| Groq/Gemini 401 | URL not forwarded | `real_provider_url` in openai.py |
| Session always "default" | no `chat_id` in body | check body keys |
| Double pseudonymization | corrupted Redis | `redis-cli flushall` |
| Proxy missing from `docker ps` | syntax error | `docker compose up privacy-proxy` for traceback |
| Anthropic/OpenAI 401, no response | proxy container has no volume → DB wiped on recreate, keys lost | add `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` to proxy env in docker-compose; or give proxy a `proxy-data:/app/backend/data` volume and re-configure keys once |

---

## Local dev dashboard (future, not built)

Spec: `garnet-dashboard` service, `127.0.0.1:8081` only, reads Docker socket (ro) + Redis. Panels: live logs, Redis viewer, entity stats (`garnet:stats:*` via `hincrby` — not implemented), file upload audit. FastAPI + single HTML + SSE + Chart.js CDN. Never expose externally, never in Caddyfile. Status: spec done, build todo.
