# Plan: Full History Pseudonymization

## Context
Currently the proxy only pseudonymizes `messages[-1]` (the last user message).
Old user messages and old assistant messages in history are sent to the LLM with **real names**.
This leaks PII from previous turns to the LLM on every subsequent prompt.

Goal: pseudonymize ALL messages in history (user + assistant) before forwarding to the LLM.
Performance guard: cache pseudonymized results by content hash per session so spaCy never re-runs on the same text twice.

---

## File to change
**Only one file:** `backend/privacy_proxy/app/main.py`

---

## What changes

### 1 — Remove history depseudo (lines 403–411)
This step currently restores tokens in old assistant messages back to real names.
With full-history pseudonymization we no longer want real names — delete this block entirely.

```python
# DELETE THIS BLOCK:
restored_count = 0
for msg in messages[:-1]:
    if msg.get("role") == "assistant":
        before = msg["content"]
        msg["content"] = depseudonymize(msg["content"], session_id, store.get_store())
        if msg["content"] != before:
            restored_count += 1
if restored_count > 0:
    log_history_depseudo(restored_count)
```

### 2 — Add module-level cache (top of file, after store = MappingStore)
```python
_pseudo_cache: dict[str, dict[str, str]] = {}  # {session_id: {md5(text): pseudo_text}}
```

### 3 — Add cached pseudonymize helper (after _pseudo_cache declaration)
```python
def _pseudo_cached(text: str, session_id: str, enabled_types) -> str:
    h = hashlib.md5(text.encode()).hexdigest()
    session_cache = _pseudo_cache.setdefault(session_id, {})
    if h in session_cache:
        return session_cache[h]
    result = pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)
    session_cache[h] = result
    return result
```

### 4 — Pseudonymize all history messages (replace history depseudo block, before last message pseudo)
Insert after session_id is built and enabled_types is parsed, before the existing last-message pseudo:

```python
# Pseudonymize full history (user + assistant) with cache
if privacy_enabled and not is_system_prompt:
    for msg in messages[:-1]:
        role = msg.get("role", "")
        if role not in ("user", "assistant", "system", "developer"):
            continue
        content_text = extract_text_content(msg.get("content", ""))
        if not content_text:
            continue
        pseudo = _pseudo_cached(content_text, session_id, enabled_types)
        msg["content"] = rebuild_content(msg["content"], pseudo)
```

### 5 — Last user message pseudo stays unchanged
The existing block that pseudonymizes `messages[-1]` (lines 439–548) stays as-is.
`_pseudo_cached` handles it too so spaCy won't re-run if the text was already seen.

---

## Result — what LLM sees on prompt 5

```
user:      "PERSON_cc75010d works at ORGANIZATION_bd3a68a5"   ← pseudonymized
assistant: "PERSON_cc75010d is an engineer at ORGANIZATION_bd3a68a5"  ← pseudonymized
user:      "what is his email?"                                ← no PII → unchanged
assistant: "his email is EMAIL_ADDRESS_f3a12b99"               ← pseudonymized
user:      "PERSON_cc75010d what else do you know?"            ← pseudonymized
```

---

## Performance

| Turn | Old messages | New messages | spaCy calls |
|------|-------------|--------------|-------------|
| 1    | 0           | 1            | 1           |
| 2    | 2 (cached)  | 1            | 1           |
| 5    | 8 (cached)  | 1            | 1           |
| 10   | 18 (cached) | 1            | 1           |

Always 1 spaCy call per turn regardless of history length.

---

## Verification
1. Start proxy: `docker compose up privacy-proxy`
2. Send 3 messages mentioning a real name
3. Check proxy logs — all messages should show `[IN USER]` / `[OUT USER]` with tokens
4. Check LLM response restores real names correctly via stream depseudo
5. Check `[MAPPING]` log shows growing token count across turns
