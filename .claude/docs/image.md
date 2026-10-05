# image.md — Image Generation Fix

## Problem
```
ERROR: Unknown parameter: 'response_format'
ERROR: 'StreamingResponse' object is not subscriptable
```

## Root cause
```
user "generate image of a cat"
→ OWU chat_image_generation_handler → generate_image_prompt
  sends stream=False to proxy to get prompt text
→ proxy forced stream=True → returned StreamingResponse
→ OWU did res['choices'][0] → CRASH (StreamingResponse not subscriptable)
```
Three bugs: (1) proxy forced `stream=True` for all OpenAI; (2) no non-streaming return path; (3) image model was `dall-e-3` → doesn't match `^gpt-image` → OWU adds `response_format: b64_json` → `gpt-image-1` rejects it.

## Fixes

### 1. Respect caller's stream (main.py ~285)
```python
# BEFORE: body["stream"] = False if not is_openai else True
caller_wants_stream = body.get("stream", True)
body["stream"] = False if not is_openai else (False if caller_wants_stream is False else True)
```

### 2. Non-streaming return path (before StreamingResponse block)
```python
if not body.get("stream", True):
    async with httpx.AsyncClient(timeout=60.0) as _client:
        _resp = await _client.request(method=request.method, url=url, json=body,
                                      headers=forward_headers, timeout=60.0)
        return ORJSONResponse(content=_resp.json())
```

### 3. Correct model in webui.db
```bash
ssh root@65.108.38.50 "docker exec garnet-open-webui-1 python3 -c \"
import sqlite3,json
conn=sqlite3.connect('/app/backend/data/webui.db')
c=json.loads(conn.execute('SELECT data FROM config').fetchone()[0])
c['image_generation']['model']='gpt-image-1'
conn.execute('UPDATE config SET data=?',[json.dumps(c)]); conn.commit(); conn.close()
print('done')
\""
```

## IMAGE model regex (config.py:3450)
```python
IMAGE_URL_RESPONSE_MODELS_REGEX_PATTERN = '^gpt-image'
```
`gpt-image-1` / `gpt-image-1.5` match → no `response_format` added ✅. `dall-e-3` no match → adds it → error ❌. dall-e-2/3 deprecated May 2026. Always use `gpt-image-1`.

Proxy routing: `IMAGE_MODELS` detection block routes to `/v1/images/generations`; `response_format: b64_json` stripped by proxy for that path.

## Status
stream=False respected ✅ · non-streaming path ✅ · model gpt-image-1 ✅ · Harbor push of proxy image ⏳ (`blob upload invalid` → Nicu restart harbor-registry; temp = sed on container + restart, see deploy.md).

## Test
```bash
ssh root@65.108.38.50 "docker logs garnet-open-webui-1 -f 2>&1 | grep -E 'image|response_format|error|ERROR'"
```
