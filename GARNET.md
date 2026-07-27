# Garnet

> Privacy-preserving AI chat — PII never leaves your infrastructure.

[![CI](https://github.com/enclaive/garnet/actions/workflows/build.yml/badge.svg)](https://github.com/enclaive/garnet/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-compose-ready-blue)](docker-compose.yml)

<!-- SCREENSHOT 1: full chat window showing a message with PII, the response, and the sensitive items badge -->
<!-- replace the line below with: ![Garnet demo](docs/screenshots/hero.png) -->

Garnet wraps [Open WebUI](https://github.com/open-webui/open-webui) with a privacy proxy. Every message is pseudonymized before it reaches the LLM — real names, emails, and IBANs never leave your server.

```
You type:     "Max Mustermann at Enclaive, email max@enclaive.io"
LLM receives: "PERSON_cc75010d at ORGANIZATION_bd3a68a5, email EMAIL_ADDRESS_2162ce1b"
You see:      "Max Mustermann at Enclaive, email max@enclaive.io"   ← restored
```

---

## Quick start

```bash
git clone https://github.com/enclaive/garnet.git
cd garnet
cp .env.example .env          # add your API keys
docker compose up -d
```

Open `https://localhost` — done.

---

## How it works

```
Browser
  │
  ▼
Open WebUI          ← chat UI, RAG, web search
  │  forces all traffic through proxy
  ▼
Garnet Proxy        ← pseudonymize → forward → depseudonymize
  │
  ├── OpenAI · Anthropic · Gemini · Groq · OpenRouter
  └── Ollama (local, fully air-gapped)
```

Every request goes through three stages:

**1 — Pseudonymize**
PII is detected (regex + spaCy NER) and replaced with deterministic tokens before the request leaves your server. The same value always produces the same token within a session.

**2 — Forward**
The anonymized request is forwarded to the configured LLM provider. The provider never sees real names, emails, or IBANs.

**3 — Depseudonymize**
Tokens in the streaming response are replaced with the original values in real time. The user sees the real names — the provider never did.

<!-- SCREENSHOT 2: (i) tooltip open showing PERSON_xxx = Max Mustermann mapping -->
<!-- replace the line below with: ![Token mapping tooltip](docs/screenshots/tooltip.png) -->

---

## Privacy toggle

<!-- SCREENSHOT 3: two screenshots side by side — privacy ON (badge visible) vs OFF (no badge) -->
<!-- replace with: ![Privacy toggle](docs/screenshots/toggle.png) -->

The shield icon in the navbar toggles privacy on/off per session. With privacy **off**, raw PII is forwarded to the LLM with no interception — useful to demonstrate the difference Garnet makes.

---

## Control which entities are protected

<!-- SCREENSHOT 5: the entity toggle panel open — showing checkboxes for PERSON, EMAIL, IBAN, PHONE, LOCATION, ORG with some checked/unchecked -->
<!-- replace with: ![Entity controls](docs/screenshots/entity-controls.png) -->

Garnet lets you choose exactly which PII types to pseudonymize. Open the entity settings panel in the chat to enable or disable individual types:

| Toggle | Effect |
|---|---|
| **PERSON** | Pseudonymizes names (`PERSON_xxx`) |
| **ORGANIZATION** | Pseudonymizes company names (`ORGANIZATION_xxx`) |
| **EMAIL** | Pseudonymizes email addresses (`EMAIL_ADDRESS_xxx`) |
| **IBAN** | Pseudonymizes bank account numbers (`IBAN_CODE_xxx`) |
| **PHONE** | Pseudonymizes phone numbers (`PHONE_NUMBER_xxx`) |
| **LOCATION** | Pseudonymizes cities, countries, addresses (`LOCATION_xxx`) |

Only the selected types are intercepted — everything else passes through raw. This is useful when, for example, you want location names to reach the LLM for context but still protect personal identities.

---

## Protected entity types

| Type | Token | Detection |
|---|---|---|
| Person name | `PERSON_cc75010d` | spaCy NER |
| Organization | `ORGANIZATION_bd3a68a5` | spaCy NER |
| Email address | `EMAIL_ADDRESS_2162ce1b` | Presidio regex |
| IBAN | `IBAN_CODE_7f377fd5` | Presidio regex |
| Phone number | `PHONE_NUMBER_cdbb568f` | Presidio regex |
| Location | `LOCATION_dad114b6` | spaCy NER |

Languages: English + German (same pipeline, language auto-detected per message).

---

## Pseudonymization pipeline

```
 ① Read body & pop Garnet fields (chat_id, privacy flag)
 ② Classify message — skip OWU internal prompts (title gen, tags)
 ③ Detect language (langdetect)
 ④ Regex pass — emails, IBANs, phones (Presidio)
 ⑤ Strip markdown → spaCy NER → persons, orgs, locations
 ⑥ Filter overlaps + ORG false-positive filter (score ≤ 0.85)
 ⑦ Generate SHA-256 tokens + replace right-to-left
 ⑧ Rebuild message content (string or multimodal list)
 ⑨ Forward to LLM provider
 ⑩ Stream response → depseudonymize each SSE chunk in real time
```

Session mapping (token → real value) is stored in Redis per `chat_id` with a 1-hour TTL. The proxy is stateless for pseudonymization — tokens are deterministic. Redis is used only for the reverse lookup at depseudo time, and survives proxy restarts.

---

## File & Knowledge Base protection

<!-- SCREENSHOT 4: file upload — chat message showing the sensitive items badge after uploading a PDF with PII -->
<!-- replace with: ![File upload protection](docs/screenshots/fileupload.png) -->

Uploaded files and Knowledge Base documents are scanned on upload. Retrieved chunks are pseudonymized before they reach the LLM — the same pipeline applies to RAG context as to chat messages.

**Recommended OWU settings** (Admin → Documents):

| Setting | Value |
|---|---|
| Top K | 15 |
| Hybrid search | ON |
| Reranking model | `BAAI/bge-reranker-v2-m3` |
| Reranker Top K | 6 |
| Full context mode | OFF |

---

## Provider support

| Provider | Auth detection | Notes |
|---|---|---|
| OpenAI | `sk-...` | streaming |
| Anthropic | `sk-ant-...` | auth header converted automatically |
| Gemini | `AIza...` | streaming |
| Groq | `gsk-...` | streaming |
| OpenRouter | `sk-or-...` | streaming |
| Ollama | path prefix `ollama/` | local, no API key, stream forced off |

All providers receive only pseudonymized content. Provider switching mid-chat preserves the session token mapping.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `FORCE_OPENAI_BASE_URL` | — | Forces all OWU OpenAI traffic through the proxy |
| `FORCE_OLLAMA_BASE_URL` | — | Forces all OWU Ollama traffic through the proxy |
| `REDIS_URL` | `redis://redis:6379` | Session mapping store |
| `OPENAI_API_URL` | `https://api.openai.com/v1` | Default provider fallback |

---

## Architecture

```
backend/
├── open_webui/           Fork of Open WebUI
│   ├── utils/middleware.py     RAG injection, web search, request enrichment
│   └── routers/openai.py       Forces traffic to proxy, sets x-openai-base-url
└── privacy_proxy/app/
    ├── main.py                 FastAPI proxy — full pipeline
    ├── pseudonymizer.py        Presidio + spaCy NER
    ├── depseudonymizer.py      Token → real value (streaming-safe)
    ├── mapping_store.py        Redis-backed session store
    └── custom_recognizers.py   IBAN, phone, ID patterns
```

---

## License

See [LICENSE](LICENSE) and [LICENSE_HISTORY](LICENSE_HISTORY).
