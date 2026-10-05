# Pseudonymization Course — Progress Log

Example used: `"what is Max Mustermann email max@enclaive.io?"`
Model: claude-opus-4-5 · Provider: Anthropic · chat_id: "abc123"

## Done

- Step 1 — proxy reads raw body (`await request.json()`)
- Step 2 — pops `privacy_proxy` → `privacy_enabled`, pops `chat_id` → `session_id`
- Step 3 — extracts `messages[]`, fixes stream mode (cloud=True, Ollama=False)
- Step 4 — classifies last message: `has_rag_context`, `is_system_prompt`
- Step 5 — OWU system prompts explained (title gen, tags, follow-ups — skipped by proxy)
- Step 6 — calls `pseudonymize(text, session_id, store, enabled_types)`
- Step 7 — language detect → "en" → loads `en_core_web_md`
- Step 8 — regex pass (EMAIL + PHONE replaced in copy before NLP)
- Step 9 — strip markdown + build `pos_map` for position translation
- Step 10 — Presidio/spaCy NER → PERSON/ORG/IBAN/LOCATION/ID, score threshold 0.5
- Step 11 — filter overlaps (regex beats NLP, longest span wins)
- Step 12 — generate tokens (`TYPE_sha256[:8]`), replace right-to-left, store in MappingStore
- Step 13 — `rebuild_content()` puts pseudonymized text back into `last_message["content"]`
- Step 14 — forward to LLM (header whitelist, Anthropic Bearer→x-api-key conversion)

## Next session starts here

**Step 15 — LLM responds with tokens → depseudonymization**

- proxy receives stream from LLM
- `stream_with_depseudo()` generator
- first yield: metadata chunk (pseudonymized_prompt, file_entity_count, garnet_breakdown)
- buffer accumulates chunks
- `split_at_safe_boundary(buffer)` — holds back partial token names at buffer edge
- replace tokens longest-first → yield safe part to client
- final flush after `[DONE]`
- Ollama path: sync replace on full response JSON instead
