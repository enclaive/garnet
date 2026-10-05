# webui.md — Open WebUI Fork (Svelte)

Repo `enclaive/garnet`, branch `garnet-privacy-proxy` (older: `feature-button-i`). Local `~/Desktop/garnet`.

## Changed files

| File | What changed |
|------|-------------|
| `src/lib/components/chat/Navbar.svelte` | `private` toggle next to model selector |
| `src/lib/components/chat/Chat.svelte` | animation + pseudonymized_prompt + entity filtering + file_entity_count |
| `src/lib/components/chat/Messages/UserMessage.svelte` | (i) button + sensitive counter |
| `src/lib/components/chat/Messages/ResponseMessage.svelte` | ⚠️ REVERTED to original — do not touch (Seb gate) |
| `src/lib/components/chat/Controls/Controls.svelte` | Garnet entity toggles (last section, `<hr>` before) |
| `src/lib/components/chat/Settings/Garnet.svelte` | created but NOT used — reference only |
| `src/lib/components/chat/ModelSelector.svelte` | `showSetDefault = false` after save |
| `src/lib/apis/privacy/index.ts` | `analyzeMessageEntities` — sends `x-garnet-entities` |
| `src/lib/apis/openai/index.ts` | `generateOpenAIChatCompletion` — sends `x-garnet-entities` |
| `backend/open_webui/routers/openai.py` | forwards `x-garnet-entities` + `x-openai-base-url` |
| `backend/open_webui/routers/ollama.py` | extracts `pseudonymized_prompt` from proxy |
| `backend/open_webui/main.py` | passes `pseudonymized_prompt` through done socket |
| `backend/open_webui/middleware.py` | init + capture + forward `file_entity_count` |

## (i) button flow

```
proxy returns pseudonymized_prompt in JSON
→ middleware extracts → emits in chat:completion done socket
→ Chat.svelte attaches to history.messages[userMessageId]
→ UserMessage.svelte renders (i) when message.pseudonymized_prompt truthy
→ hover → position:fixed black tooltip, white monospace
```

## Entity toggle flow

```
Controls → Garnet section → dropdown On/Off per entity
→ saved localStorage: garnet_entity_toggles
→ on send: openai/index.ts builds x-garnet-entities header
→ frontend → OWU backend → get_headers_and_cookies() → proxy
→ proxy filters; /analyze uses same header for highlight
```

## Multi-provider header flow

```
User picks Groq model
→ Chat.svelte → generateOpenAIChatCompletion(token, body, url)
  url = WEBUI_BASE_URL/api  (always same, not provider URL)
→ openai.py reads real URL from OPENAI_API_BASE_URLS[idx]
→ sets x-openai-base-url = https://api.groq.com/openai/v1
→ proxy forwards to Groq
```
Key fix in `openai.py` (~line 1140): `headers['x-openai-base-url'] = OPENAI_API_BASE_URLS[idx]`.

## ⚠️ Critical Svelte rules — read every time

| Rule | Why |
|------|-----|
| `console.warn` not `console.log` | Vite strips `log`/`error` in prod builds |
| `position:fixed` + `getBoundingClientRect()` for tooltip | `absolute` clipped by `overflow:hidden` parents |
| `history.messages[id] = { ...message }` | spread required — Svelte won't react to new fields |
| `entity.type ?? entity.entity_type` | proxy returns `type`, some code expects `entity_type` |
| `garnet_entity_toggles[type] !== false` | `undefined` = ON — never check `=== true` |
| ResponseMessage fast-path (line 128) | new fields must be in fast-path condition or no re-render |
| `structuredClone` at mount | ResponseMessage clones once — updates only on fast-path match |
| keep `let _ref = analyzeMessageEntities` at module level | else Vite tree-shakes `privacy/index.ts` out of bundle |
| `{@const}` only inside `{#each}` | Svelte rule |

## Config gotcha — OWU writes env to DB

OWU writes env vars to `webui.db` on first boot, then reads only from DB. DB overrides env. `loadChat()` overwrites `selectedModels` with last chat's model (runs after `initNewChat()`).

## Problems + fixes

| Problem | Fix |
|---------|-----|
| Tooltip invisible | `position:fixed` + `getBoundingClientRect()` |
| Svelte not re-rendering | `{ ...message }` spread |
| `privacy/index.ts` not in bundle | module-level ref in Chat.svelte |
| Entity toggle no effect | forward `x-garnet-entities` in openai.py |
| Debug logs missing in prod | use `console.warn` |
| Groq/Gemini routes to OpenAI | forward `x-openai-base-url` in openai.py |
