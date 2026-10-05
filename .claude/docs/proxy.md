# proxy.md — Privacy Proxy Internals

Location: `backend/privacy_proxy/app/`

## Key files

| File | Role |
|------|------|
| `main.py` | FastAPI app — intercepts all requests |
| `logs.py` | 30 structured log functions (extracted from main.py) |
| `pseudonymizer.py` | Presidio + spaCy NER → PII to tokens |
| `depseudonymizer.py` | Tokens back to real values |
| `mapping_store.py` | Session mapping, Redis-backed, 1h TTL |
| `custom_recognizers.py` | Custom: IBAN, PHONE, ID, ORGANIZATION |
| `test_proxy.py` | 22 automated tests, run after deploy |

## Request flow (main.py)

```
1. Request arrives
2. body["stream"] = forced per path (see streaming rules) ← never blindly remove
3. If chat AND privacy ON AND role==user AND not internal prompt:
     pseudonymize last user message
4. Pseudonymize system/RAG messages (file content) — see fileupload.md
5. Forward to provider (OpenAI / Groq / Gemini / Ollama / Anthropic)
6. Depseudonymize response
7. result["pseudonymized_prompt"] = pseudonymized message (or None)
8. Return
```

## Entity types & tokens

Deterministic: SHA-256 of entity value → 8 hex chars. Same value = same token. Session-isolated by `chat_id`.

| Type | Token |
|------|-------|
| PERSON | `PERSON_cc75010d` |
| ORGANIZATION | `ORGANIZATION_bd3a68a5` |
| EMAIL_ADDRESS | `EMAIL_ADDRESS_82a96bff` |
| IBAN_CODE | `IBAN_CODE_7f377fd5` |
| PHONE_NUMBER | `PHONE_NUMBER_cdbb568f` |
| LOCATION / ID | `LOCATION_xxx` / `ID_xxx` |

Languages: English + German (`de_core_news_md` — downgraded from `lg` for image size). Presidio orchestrates.

## Session isolation

```python
import secrets
session_id = (
    body.get("chat_id")
    or (messages[0].get("id") if messages else None)
    or f"anon-{secrets.token_hex(6)}"   # was md5(first_msg) — caused cross-user leak
)
```
`chat_id` always present from OWU → `anon-*` is fallback only. Redis key: `garnet:mapping:{chat_id}`.

## SYSTEM_PROMPT_MARKERS

Skips pseudonymization for OWU internal prompts (title gen, tags, follow-ups):
```python
SYSTEM_PROMPT_MARKERS = ["### Task:", "### Guidelines:", "### Output:",
    "JSON format:", "follow_ups", "Generate", "Suggest"]
```
When skipped: `pseudonymized_user_message = original_content` (keeps (i) button working).
⚠️ RAG template ALSO starts with `### Task:` → must check `<context>`/`<source>` first. See fileupload.md.

## Per-entity filtering — x-garnet-entities header

```
Header: x-garnet-entities: PERSON,EMAIL_ADDRESS,IBAN_CODE
→ only those 3 pseudonymized. No header = all entities.
```
```python
detect_entities(text, language="en", enabled_types=None)
pseudonymize(text, session_id, store, enabled_types=None)
```

## Multi-provider routing

OWU sends real provider URL via `x-openai-base-url` header:
```python
openai_url = request.headers.get("x-openai-base-url", OPENAI_API_URL)
if "privacy-proxy" in openai_url or "localhost:8080" in openai_url:
    openai_url = OPENAI_API_URL   # self-loop protection — CRITICAL
url = f"{openai_url.rstrip('/')}/{actual_path}"
```
Self-loop guard by key prefix: `sk-ant-`→Anthropic, `gsk-`→Groq, `AIza`→Gemini, `sk-or-`→OpenRouter.
Required in `backend/open_webui/routers/openai.py`:
```python
real_provider_url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
headers['x-openai-base-url'] = real_provider_url
```

| Provider | URL |
|----------|-----|
| OpenAI | `https://api.openai.com/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` |
| Ollama | `http://ollama:11434` |

`/v1/responses` path used for GPT models needing Responses API (`instructions`, `max_output_tokens`).

## Streaming

- `aiter_bytes()` (not `aiter_lines()` — fixed Anthropic `TransferEncodingError`).
- `split_at_safe_boundary()` holds partial tokens across SSE chunks.
- Non-streaming path forces `stream=False` and has its own return branch BEFORE `StreamingResponse` (see image.md for why).
- Fake streaming (re-stream after depseudo) NOT implemented — tell Seb first.

## ORGANIZATION false-positive filter

spaCy flagged product names ("Buckypaper", "Dyneemes") + lowercase phrases as ORG.
```python
results = [r for r in results if not (
    r.entity_type == "ORGANIZATION" and (
        stripped_text[r.start].islower() or r.score <= 0.85
    )
)]
```
Result: lowercase start filtered, weak score filtered, "Enclaive GmbH" (upper + 0.90) kept.

## Chunked pseudonymization (large content)

Content >50k chars → split into 10k pieces (200-char overlap), same `session_id` so tokens stay consistent. Replaces old `[SKIP]` block that leaked raw text to Anthropic. See rag.md / archive for full story.

## ⚠️ Critical route order

`/analyze` and `/health` MUST be defined BEFORE `@app.api_route("/{path:path}")`. Catch-all returns 405 for anything after it.

## Problems + fixes

| Problem | Fix |
|---------|-----|
| Tokens visible in response | force `stream=False` on non-stream path |
| System prompts pseudonymized | add to `SYSTEM_PROMPT_MARKERS` |
| Entity filter no effect | forward `x-garnet-entities` in `get_headers_and_cookies()` (openai.py) |
| Route 405 | move `/analyze`,`/health` above catch-all |
| Proxy forwards to itself | self-loop check on `x-openai-base-url` |
| Groq/Gemini 401 | `x-openai-base-url` not forwarded → fix openai.py |
| Session always "default" | check body has `chat_id` |
| Double pseudonymization | corrupted Redis → `redis-cli flushall` |
| Proxy missing from `docker ps` | syntax error → `docker compose up privacy-proxy` for traceback |
| **Stuck after 5 prompts / pod restart** | event loop blocked by sync GLiNER + Redis → see Performance section below |
| Two users share same session | old md5 fallback collided → fixed: `secrets.token_hex(6)` |
| Container fails: No space left on `/tmp` | torch cache fills disk → `docker image prune -a -f` on cVM |

## Performance architecture (2026-08-23)

All fixes on branch `demo1upgrade`, commits `d4859e3fc` + `26a67c672`.

| Fix | File | What it does |
|-----|------|-------------|
| `asyncio.to_thread(pseudonymize, ...)` | `main.py` — 5 call sites | GLiNER/spaCy run in thread pool, event loop stays free |
| `has_pseudo: continue` in history loop | `main.py:535` | Skips already-pseudonymized messages — turn 6 costs 1 model call not 6 |
| Bounded LRU `pseudo_cache` (5000 entries) | `main.py:57` | `OrderedDict`, key=(session_id, md5, types_key), evicts oldest on overflow |
| `@lru_cache(maxsize=4)` on `build_analyzer` | `pseudonymizer.py:36` | spaCy AnalyzerEngine built once per language, not per request |
| `async flush()` via `redis.asyncio` | `mapping_store.py:91` | Redis SETEX non-blocking — event loop yields during network wait |
| Shared `_http_client` | `main.py:56` | One `httpx.AsyncClient` reused — no TCP handshake per request |
| `scan_iter` + in-memory file token index | `main.py` | Zero Redis scans during normal chat turns |

**Env var:** `PSEUDO_CACHE_MAX` (default 5000) — override cache size without rebuild.

## Add a new entity type — 4 places must sync

`Controls.svelte` · `Chat.svelte` color map · `main.py` token list in `split_at_safe_boundary` · `pseudonymizer.py`.

## Known limitations (Presidio accuracy, not logic)

Name + `(CEO)` adjacent confuses NER · single first names missed · custom IDs like `ENC-2024-007823` not caught.
