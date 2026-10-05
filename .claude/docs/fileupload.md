# fileupload.md — File Upload, RAG Pseudonymization & Sensitive Counter

> How OWU uploads files and how the proxy pseudonymizes their content.

## OWU file flow

```
1. Upload data.txt → chunk (~1000 chars) → embed (all-MiniLM-L6-v2) → Chroma
2. Send "summarize it" → search Chroma → top_k chunks → RAG template
3. To proxy:
   [{role:"system", content:"### Task:...<context><source>chunks</source></context>"},
    {role:"user",   content:"summarize it"}]
```
OWU uses a SEPARATE internal HTTP client for RAG (not normal chat path) → made debugging hard.

## The bug

Default `RAG_SYSTEM_CONTEXT=False` → OWU injected chunks into `role:user` AFTER pseudonymization ran on the last user message only → RAG content bypassed. Real names/emails/IBANs hit GPT in plaintext.

⚠️ OWU may use `role:developer` instead of `role:system` depending on API version → check `role not in ("user","assistant")`, not exact names.

## Fix

### 1. `RAG_SYSTEM_CONTEXT=True` in docker-compose
Forces chunks into `role:system`. Restart OWU:
```bash
ssh root@65.108.38.50 "cd /opt/garnet && docker compose stop open-webui && docker compose rm -f open-webui && docker compose up -d open-webui"
```

### 2. System-message pseudonymization loop in `main.py`
```python
enabled_header = request.headers.get("x-garnet-entities", "")
enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] or None

last_msg_index = len(messages) - 1
for i, msg in enumerate(messages):
    role = msg.get("role", "")
    content = msg.get("content", "")
    if role == "assistant":
        continue
    if role == "user" and i == last_msg_index:   # actual query — handled elsewhere
        continue
    has_rag_context = "<context>" in content or "{{CONTEXT}}" in content or "<source" in content
    is_internal = not has_rag_context and any(m in content for m in SYSTEM_PROMPT_MARKERS)
    if not is_internal and privacy_enabled:
        msg["content"] = pseudonymize(content, session_id, store.get_store(), enabled_types=enabled_types)
```
Why `has_rag_context`: RAG template starts with `### Task:` (same as internal prompts). Has `<context>`/`<source>` → pseudonymize; only `### Task:` → skip.
Why skip only the LAST user message: Anthropic converts `role:system`→`role:user` before proxy; skipping all user msgs would leak earlier RAG content.

### Verified (before → after)
```
Max Mustermann (CEO), max.mustermann@enclaive.com, IBAN DE89...
→ PERSON_a21e4283 (CEO), EMAIL_ADDRESS_e94c8ab3, IBAN_CODE_7f377fd5
```
Redis mapping holds all tokens → restorable.

---

## Sensitive counter — "📎 N sensitive items detected in file"

Counter = NEW unique PII tokens added to session mapping by that file. Shows only when file uploaded AND privacy ON AND ≥1 entity. Count 0 → nothing (e.g. re-upload same file).

### Data flow
```
main.py: existing = set(store.get_mapping(session_id).keys())
         [loop pseudonymizes] → new = set(after) - existing → file_entity_count
  → first SSE chunk: {type:"pseudonymized_prompt", content:"...", file_entity_count:32}
  → openai.py _stream_with_pseudo_prompt: emit synthetic SSE
     condition: if pseudo_prompt OR file_entity_count   ← emit even if prompt empty
  → middleware.py: init=0, nonlocal, capture, include in done socket event
  → Chat.svelte: destructure + { ...message, file_entity_count: x ?? 0 }
     guard: if (pseudonymized_prompt || file_entity_count > 0)
  → UserMessage.svelte: {#if message.file_entity_count > 0} render
```

### Counting logic
```python
existing_keys_before = set(store.get_mapping(session_id).keys())
# ... loop pseudonymizes system / earlier-user RAG content ...
new_keys = set(store.get_mapping(session_id).keys()) - existing_keys_before
file_entity_count = len(new_keys)   # set diff, not len(after)-len(before) → handles re-uploads
```

### Files changed
`main.py` (count via set diff) · `openai.py` (emit synthetic chunk even if pseudo empty) · `middleware.py` (init+capture+forward) · `Chat.svelte` (destructure+spread) · `UserMessage.svelte` (render >0).

### Bugs faced
1. Agent broke system loop adding Redis stats → clean rewrite. 2. `file_entity_count` undefined in browser → middleware didn't init/forward → +4 lines. 3. File-only upload (no PII in user msg) → `if pseudo_prompt:` skipped chunk → use `or file_entity_count`. 4. Count accumulates → set diff. 5. Anthropic role conversion → skip only last user msg. 6. Prior messages in session → snapshot keys BEFORE loop.

### Test scenarios ✅
normal ON/OFF · file ON/OFF · internal prompts skipped · second upload same file → 0 shown nothing.

### If count seems low
Presidio accuracy, not logic: name+`(CEO)` adjacent · single first names · IDs like `ENC-2024-007823` · repeated company names deduped (same token).

### Rollback
```bash
ssh root@65.108.38.50 "cd /opt/garnet && docker compose up -d --force-recreate open-webui"   # point to prior tag if needed
```

## Debug

```bash
ssh root@65.108.38.50 "docker logs -f garnet-privacy-proxy-1 2>&1 | grep -E 'FILE CONTENT|SYSTEM PSEUDO|FILE PII|MAPPING|PRIVACY'"
ssh root@65.108.38.50 "docker exec garnet-open-webui-1 python3 -c \"import os; print(os.environ.get('RAG_SYSTEM_CONTEXT'))\""
```

## File vault

`file:{file_id}` Redis key pattern; file mappings merged with chat session at depseudo time.
