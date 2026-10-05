---
name: web
description: Use when Ahmed says "/web", "/fetch", "fetch this <url>", "search for X", "find articles about X", "docs of X", "how does X do Y", "owu docs", "openwebui docs", "/owudocs", "crawl <url>", or pastes a URL for extraction. Absorbs owudocs. Five modes auto-selected by prompt intent — FETCH (URL → clean markdown via Firecrawl/WebFetch), SEARCH (semantic query via Exa/WebSearch), CRAWL (multi-page site via Firecrawl), DOC (library/product docs — tries context7 first, then Exa docs search), OWU (docs.openwebui.com shortcut with sitemap). Offers to save to `.claude/docs/data.md` 📚 section via data skill. Never invents content — always cites source URL.
---

# web Skill

> One skill for anything web: fetch URLs, semantic search, crawl sites, docs lookup.
> Absorbs `owudocs`. Uses installed MCPs: Firecrawl, Exa, context7. Falls back to WebFetch/WebSearch.

---

## Mode selector

State: `Mode: WEB · <MODE>`.

| Prompt | Mode |
|---|---|
| Prompt is a URL, or "fetch <url>", "grab this page" | **FETCH** |
| "search for X", "find articles about X", "articles on Y" | **SEARCH** |
| "crawl <url>", "grab all pages from X docs" | **CRAWL** |
| "docs of X", "how does X do Y", "X API reference" | **DOC** |
| "owu docs", "openwebui docs", "/owudocs", "how does OWU do X" | **OWU** |

Ambiguous → ask one question.

---

## Mode 1 — FETCH

Try Firecrawl MCP → WebFetch fallback.

```
Firecrawl scrape(url) → clean markdown
  ↓ if fails
WebFetch(url, prompt="extract main content")
```

Output: markdown of page + URL cite.
Ask: **"Save to `data.md` 📚? [y/n]"** — if y, dispatch `/data` skill.

---

## Mode 2 — SEARCH

Try Exa MCP → WebSearch fallback.

```
Exa search(query, num_results=5) → ranked results
  ↓ if fails
WebSearch(query)
```

Output: 3-5 ranked results with title + URL + snippet.
Ask: **"Fetch #N?"** → drop to FETCH mode on chosen result.

---

## Mode 3 — CRAWL

Firecrawl multi-page: `crawl(url, max_pages=10)`.

Output: list of pages fetched + first-line summary per page.
Ask: **"Save all to `data.md` 📚? [y/n]"**.

Never crawl > 20 pages without explicit confirm.

---

## Mode 4 — DOC

For library/product docs (FastAPI, Svelte, Presidio, litellm, etc.):

```
context7 MCP (if known library) → live docs
  ↓ else
Exa search "site:docs.<lib> <query>" → top hit
  ↓ else
Firecrawl the official docs URL
```

Cross-check against local install: `pip show <pkg>` or `npm ls <pkg>` for version.

---

## Mode 5 — OWU (docs.openwebui.com)

Sitemap-first — never guess the URL.

| Topic | URL |
|---|---|
| Install / quick start | `https://docs.openwebui.com/getting-started/quick-start/` |
| Env vars (full ref) | `https://docs.openwebui.com/getting-started/env-configuration` |
| Updating | `https://docs.openwebui.com/getting-started/updating` |
| Features overview | `https://docs.openwebui.com/features/` |
| Models config | `https://docs.openwebui.com/features/models/` |
| Chat features | `https://docs.openwebui.com/features/chat-features/` |
| RAG / knowledge | `https://docs.openwebui.com/features/rag` |
| Web search | `https://docs.openwebui.com/features/web-search` |
| Images | `https://docs.openwebui.com/features/images` |
| Audio (STT/TTS) | `https://docs.openwebui.com/features/audio` |
| Tools/functions | `https://docs.openwebui.com/features/plugin/tools/` |
| Pipelines | `https://docs.openwebui.com/pipelines/` |
| OpenAPI servers | `https://docs.openwebui.com/openapi-servers/` |
| Filters | `https://docs.openwebui.com/features/plugin/functions/filter` |
| Pipes | `https://docs.openwebui.com/features/plugin/functions/pipe` |
| Actions | `https://docs.openwebui.com/features/plugin/functions/action` |
| API endpoints | `https://docs.openwebui.com/getting-started/api-endpoints` |
| SSO / OAuth / LDAP | `https://docs.openwebui.com/features/sso` |
| Permissions/RBAC | `https://docs.openwebui.com/features/workspace/permissions` |
| Troubleshooting | `https://docs.openwebui.com/troubleshooting/` |
| Logging | `https://docs.openwebui.com/troubleshooting/logging` |
| HTTPS/Caddy/Nginx | `https://docs.openwebui.com/tutorials/https-encryption/` |

Not in sitemap → `https://docs.openwebui.com/search?q=<keywords>`.

After answering: **cross-check** with `grep -rn "<symbol>" backend/open_webui/ | head -5` — if fork diverges, flag it.

Answer format:
```
OWU DOCS — <question>
Answer: <2-5 sentences>
Source: <URL>
Fork note: <if diverges>
```

Max 3 parallel fetches per question. Cache reusable answers via **"Save to `data.md` 📚?"**.

---

## Rules

- **State the mode** every reply.
- **Never invent** — cite the URL. If MCPs fail + WebFetch fails → say "unknown, no source".
- **Ask before saving** to `data.md` — never auto-save.
- **Max 3 parallel fetches** per call.
- **Never re-fetch** the same URL in one session — reuse.
- **Fork check** for OWU mode: always grep local `backend/open_webui/` after.

---

## Boundary

| Tool | Difference |
|---|---|
| `data` | STORES pasted content · `web` FETCHES fresh (then offers to save) |
| `enclaivetech` | Enclaive product docs (vHSM/Vault/Nitride) — keep separate for stack-specific knowledge |
| `graphify` | Local codebase — no overlap |
| `context7` MCP | Called BY `web` DOC mode — not a competitor |
