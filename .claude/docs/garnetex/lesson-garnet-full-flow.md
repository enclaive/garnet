# Garnet — Full Flow Lesson (from zero)

> How every byte travels from the browser to the LLM and back, with PII never leaving the system in plain text.

---

## 0. The big picture in one sentence

Garnet sits as a **privacy proxy** between the chat UI and any LLM.
It swaps real names/emails/IBANs for fake tokens before the request leaves, then swaps them back in the response — so the LLM never sees real PII.

---

## 1. Services — what runs where

```
Internet
   │
   ▼
┌──────────────────────────────────────────────────┐
│  caddy  (port 443 / 80)   TLS termination        │
└─────────────────┬────────────────────────────────┘
                  │ http (internal Docker network)
                  ▼
┌──────────────────────────────────────────────────┐
│  open-webui  (port 8080)                         │
│  Garnet's fork of Open WebUI (Svelte + FastAPI)  │
└─────────────────┬────────────────────────────────┘
                  │ http to privacy-proxy:8080
                  ▼
┌──────────────────────────────────────────────────┐
│  privacy-proxy  (port 8080)   ← THE CORE         │
│  FastAPI app — pseudonymizes IN, de-pseudo OUT   │
└──────┬───────────────────────────────────────────┘
       │                          │
       │ ollama:11434             │ external HTTPS
       ▼                          ▼
┌────────────┐     ┌──────────────────────────────┐
│  ollama    │     │  OpenAI / Anthropic / Groq   │
│  (local)   │     │  Gemini / OpenRouter         │
└────────────┘     └──────────────────────────────┘
       │
       ▼
┌────────────┐   ┌────────────────────────────────┐
│  redis     │   │  garnet-dashboard  (port 8081) │
│  mapping   │   │  monitoring UI                 │
│  store     │   └────────────────────────────────┘
└────────────┘
```

**Docker compose file:** `backend/privacy_proxy/docker-compose.yml`

| Service | Image | What it does |
|---|---|---|
| caddy | caddy:2 | TLS cert auto-provisioning, HTTPS→HTTP reverse proxy |
| open-webui | garnetdemo/garnet-webui | Chat UI + backend (OWU fork) |
| privacy-proxy | garnetdemo/privacy-proxy | The pseudonymizer — main subject of this lesson |
| ollama | ollama/ollama | Runs local models (llama3, mistral, etc.) |
| redis | redis:7-alpine | Persists token↔real-value mappings across restarts |
| garnet-dashboard | garnetdemo/garnet-dashboard | Observability, watches Docker socket + Redis |

---

## 2. Files inside the proxy

```
backend/privacy_proxy/app/
├── main.py              ← entry point, all routing logic (732 lines)
├── pseudonymizer.py     ← entity detection + token replacement
├── mapping_store.py     ← in-memory + Redis store (token↔original)
├── custom_recognizers.py← custom Presidio rules (EN + DE)
├── logs.py              ← all print/log helpers
├── depseudonymizer.py   ← reverse lookup helpers
└── models.py            ← Pydantic models
```

---

## 3. The full proxy flow — phase by phase

### PHASE 1 — Request arrives

Open WebUI sends an HTTP POST to `http://privacy-proxy:8080/openai/v1/chat/completions`
(or `/api/chat` for Ollama).

Entry point: `proxy()` in `main.py:332`

```python
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
```

This single function handles **every route**.

---

### PHASE 2 — Route classification

The proxy figures out three things:

```
is_openai  = path starts with "openai/"
is_chat    = path is one of: v1/chat/completions, api/chat, v1/completions, chat/completions
privacy_enabled = body.pop("privacy_proxy", True)   ← UI toggle
```

It also pops `chat_id` from the body (OWU adds it, LLMs reject it).

---

### PHASE 3 — Session ID

Each conversation needs a stable key so the same session uses the same token table.

```python
session_id = (
    body.get("chat_id")                           # best: explicit chat id
    or messages[0].get("id")                      # fallback: first message id
    or md5(first_message_text)[:12]               # last resort: hash of content
)
```

This `session_id` is the key in the MappingStore.

---

### PHASE 4 — Provider routing

```
path starts with "openai/" ?
│
├── YES → read x-openai-base-url header
│         if that URL points BACK to the proxy (self-loop), auto-detect provider:
│              sk-ant-...  → https://api.anthropic.com/v1
│              AIza / gemini in model name → https://generativelanguage.googleapis.com/...
│              gsk-...  → https://api.groq.com/openai/v1
│              sk-or-... → https://openrouter.ai/api/v1
│              default   → https://api.openai.com/v1
│         final URL = openai_url + "/" + actual_path
│
└── NO  → url = http://ollama:11434/ + path
```

Special case — model needs Responses API (gpt-5.5 family):
```
url = openai_url + "/responses"   (not /chat/completions)
```

---

### PHASE 5 — Stream mode fix

```
OpenAI path: keep caller's stream preference (default True if not set)
Ollama path: ALWAYS body["stream"] = False   ← critical rule, never remove
```

Ollama returns a different response format when streaming. The proxy reads the full response and depseudonymizes it before returning, so streaming is disabled.

---

### PHASE 6 — History pseudonymization

All messages **except the last** are pseudonymized using an MD5 cache:

```python
def _pseudo_with_cache(text, session_id, enabled_types):
    h = md5(text)
    hit = pseudo_cache[session_id].get(h)
    if hit: return hit
    out = pseudonymize(text, session_id, ...)
    pseudo_cache[session_id][h] = out
    return out
```

**System prompts are skipped** — any message containing these markers is left alone:
```
"### Task:", "### Guidelines:", "### Output:", "JSON format:", "follow_ups", "Generate", "Suggest"
```

This is important: OWU injects system prompts automatically (title generation, tags, etc.). The proxy detects and skips them to avoid breaking those internal calls.

---

### PHASE 7 — File / RAG context pseudonymization

If the conversation has uploaded files or RAG results, they appear as messages with:
```
<context>...</context>   or   <source ...>   or   {{CONTEXT}}
```

The proxy finds those messages and pseudonymizes the file content separately, using a `file:` prefixed session key so file entities survive across chat turns.

**Large files** (>50k chars) are chunked:
```
chunk_size = 10 000 chars
overlap    = 200 chars   ← prevents entities split at chunk boundary
```

---

### PHASE 8 — User message pseudonymization (the core step)

The last message (the user's actual question) goes through `pseudonymize()` in `pseudonymizer.py`.

**Step-by-step inside `pseudonymize()`:**

```
1. Detect language (langdetect) → "en" or "de" (defaults to "en")

2. Run EMAIL_REGEX + PHONE_REGEX first (fast, reliable)
   These are replaced with temp tokens IN the text before NLP runs

3. Strip markdown (* _ ` **) to avoid confusing spaCy
   Keeps a pos_map to translate positions back to original text

4. Run Presidio AnalyzerEngine (spaCy NER):
   Entities: PERSON, ORGANIZATION, IBAN_CODE, LOCATION, ID
   Score threshold: 0.5
   Custom recognizers for EN and DE loaded

5. Filter overlaps:
   - Regex types (EMAIL, PHONE, IBAN, ORG, LOCATION) win over NLP PERSON
   - Longest span wins when two overlap

6. For each entity found:
   token = TYPE_sha256(original_value)[:8]
   e.g. "Max Mustermann" → "PERSON_cc75010d"
       "enclaive.io"   → "EMAIL_ADDRESS_bd3a68a5"

7. Replace in text (right-to-left by position to preserve offsets)

8. Store in MappingStore:
   session_mapping["PERSON_cc75010d"] = "Max Mustermann"
```

---

### PHASE 9 — Query expansion (optional)

If the header `x-garnet-queryexpand: true` is set AND there's RAG context:

```
Call gpt-4o-mini with the original (pre-pseudo) question
→ get 3 alternative search queries
→ append them to the pseudonymized message

Result sent to LLM: "pseudonymized question\nalternative1\nalternative2\nalternative3"
```

This enriches the embedding vector for better RAG retrieval. The variants are NOT pseudonymized (known minor leak vector — only goes to embedding model, not main LLM).

---

### PHASE 10 — Forward to LLM

Headers forwarded (whitelist only):
```
authorization, content-type, openai-organization, x-openai-base-url
```

**Anthropic special handling:**
```
Authorization: Bearer sk-ant-...
→ converted to:
x-api-key: sk-ant-...
anthropic-version: 2023-06-01
```

**Image models** (dall-e-3, dall-e-2, gpt-image-1):
Body is re-shaped and sent to `/images/generations` directly.

---

### PHASE 11 — Response & depseudonymization

#### Path A — Ollama (non-streaming)

```
1. Read full response JSON
2. Get content = result["message"]["content"]
3. Build session_mapping = all chat tokens + all file: tokens
4. Replace longest tokens first (sorted by length desc to avoid partial matches)
5. Return JSON with extra fields:
   result["pseudonymized_prompt"] = what was sent to LLM
   result["file_entity_count"]    = how many PII found in files
   result["query_variants"]       = query expansion results
```

#### Path B — OpenAI streaming (main path)

`stream_with_depseudo()` is an async generator:

```
1. FIRST yield — metadata chunk (before any LLM tokens):
   {type: "pseudonymized_prompt", content: ..., file_entity_count: ..., garnet_breakdown: ..., query_variants: [...]}
   → OWU reads this to show the Garnet sidebar stats

2. For each SSE chunk from LLM:
   - Parse: choices[0].delta.content
   - Append to buffer

3. split_at_safe_boundary(buffer):
   Checks if buffer ENDS with a partial token name like "PERSON" or "PERSON_cc7"
   → if yes, hold that part back as "remainder"
   → only flush the "safe" part
   This prevents a token being split across two chunks and failing to depseudonymize

4. Replace all tokens in safe part → yield as SSE chunk

5. After loop — flush remaining buffer with replacements

6. Yield: data: [DONE]
```

---

## 4. The MappingStore

```
MappingStore (TTL 1h)
│
├── _store: dict
│    ├── "chat_abc123": {"PERSON_cc75010d": "Max Mustermann", ...}
│    ├── "file:upload_xyz": {"EMAIL_ADDRESS_bd3a68a5": "max@enclaive.io", ...}
│    └── ...
│
└── _RedisAwareStore (wrapper)
     ├── get(session_id) → check memory first, then Redis
     ├── __setitem__ → write to memory + Redis (setex with TTL)
     └── flush(session_id) → force sync memory→Redis
```

Redis key format: `garnet:mapping:{session_id}` with 1h TTL.

If Redis is not configured (no `REDIS_URL`), it runs memory-only. Mappings are lost on restart.

---

## 5. Special routes (not chat)

| Route | What it does |
|---|---|
| `GET /health` | Health check — used by Docker healthcheck |
| `POST /vault/scan` | Pre-scan a file before it enters conversation — returns pseudonymized text + entity report |
| `POST /analyze` | Detect entities in text without replacing — used by OWU to show PII highlights |
| `GET /openai/api/tags` | Proxy for Ollama model list |

---

## 6. End-to-end example

```
User types: "What can you tell me about Max Mustermann at Enclaive?"

─── PHASE 8 ───────────────────────────────────────────────────────
pseudonymizer detects:
  "Max Mustermann" → PERSON_cc75010d
  "Enclaive"       → ORGANIZATION_bd3a68a5

mapping stored:
  PERSON_cc75010d       = Max Mustermann
  ORGANIZATION_bd3a68a5 = Enclaive

─── PHASE 10 ──────────────────────────────────────────────────────
sent to LLM:
  "What can you tell me about PERSON_cc75010d at ORGANIZATION_bd3a68a5?"

─── LLM responds ──────────────────────────────────────────────────
  "PERSON_cc75010d is a software engineer at ORGANIZATION_bd3a68a5..."

─── PHASE 11 ──────────────────────────────────────────────────────
proxy replaces tokens in stream:
  "Max Mustermann is a software engineer at Enclaive..."

User sees: real names. LLM never saw them.
```

---

## 7. Key rules (never break)

| Rule | Where | Why |
|---|---|---|
| `body["stream"] = False` for Ollama | main.py:378 | Ollama streaming format is different; proxy reads full response to depseudonymize |
| Never expose proxy on 0.0.0.0 | docker-compose | Proxy has no auth — LAN access = direct LLM access bypassing privacy |
| Never log request headers | logs.py | Would log API keys |
| Longest token replaced first | depseudo step | Prevents `PERSON_cc7` matching inside `PERSON_cc75010d` |
| System prompt markers are skipped | main.py:425 | OWU internal calls (title gen, tags, follow-ups) must not be pseudonymized |
