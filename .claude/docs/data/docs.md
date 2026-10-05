# 📚 Referenced docs

_Managed by: `curator` agent · Written via: `/data` skill_
_Format: `### YYYY-MM-DD — <source> — <one-line topic>`_

<!-- Pasted external docs, RFCs, API references, spec extracts -->

### 2026-07-25 — Seb/project-spec — Full pseudonymization architecture spec (Presidio, deterministic tokens, session mapping)

**Goal:** Privacy-preserving chatbot that pseudonymizes PII before sending to LLM, restores in response.

**Example:**
```
Input:   Max Mustermann from Enclaive emailed anna@company.com
Pseudo:  PERSON_1a2b3c from ORG_4d5e6f emailed EMAIL_7g8h9i
Output:  Max Mustermann from Enclaive emailed anna@company.com
```

**Architecture:**
```
[ Open WebUI ] → [ Privacy Proxy (FastAPI) ] → [ Ollama / OpenAI ]
```

**Stack:**
- Microsoft Presidio for PII detection
- Deterministic pseudonyms: `sha256(value)[:8]` → `PERSON_a1b2c3`
- Session mapping store (Redis-ready, add TTL ~1h)
- Offset-based replacement (sorted reverse to avoid corruption)
- De-pseudonymize: replace longer tokens first (avoid partial overlaps)

**Data structures:**
```python
@dataclass
class EntityMapping:
    placeholder: str
    original: str
    entity_type: str

def generate_token(entity_type: str, value: str) -> str:
    h = hashlib.sha256(value.encode()).hexdigest()[:8]
    return f"{entity_type}_{h}"
```

**Pipeline:**
```
Original Prompt → [Pseudonymizer] → Sanitized Prompt → LLM → Sanitized Response → [De-pseudonymizer] → Final Response
```

**Entity coverage:** PERSON, ORGANIZATION, LOCATION, EMAIL, PHONE, IBAN (custom), IDs (custom)

**Multilingual:** Presidio weak on German — add spaCy `de_core_news_lg` + fastText language detector + custom regex for IBAN/phone

**Security:**
- Never send mapping to model
- Post-filter model leakage: if "refers to" in response → flag/block
- Replace in-memory dict with Redis (TTL ~1h) in production
- Never log request headers (API key leak)

---

### 2026-07-13 — platform.openai.com + docs.anthropic.com — OpenAI Responses API vs Chat Completions, Anthropic compat path

**OpenAI Responses API vs Chat Completions**
Source: https://platform.openai.com/docs/guides/migrate-to-responses

OpenAI is migrating away from Chat Completions toward the Responses API.

| | /chat/completions | /responses |
|---|---|---|
| Format | messages array | items (richer types) |
| Reasoning models | Limited — from GPT-5.4+, tool calling NOT supported | Full support + reasoning.effort |
| Cost | Standard | 40–80% better cache utilization |
| State | Stateless | Can persist context (store: true) |
| Tools | Manual | Agentic (web_search, code_interpreter, MCP built-in) |

OpenAI recommends Responses API for all new projects, especially reasoning models.

**Anthropic: Native Messages API vs OpenAI-compatible**
Source: https://docs.anthropic.com/en/api/openai-sdk

Garnet uses the OpenAI-compatible path for Claude. Anthropic explicitly says this is for testing only, NOT production. What you lose on the compat path:
- Extended thinking (Claude's step-by-step reasoning)
- PDF processing + citations
- Prompt caching
- Guaranteed schema conformance for tool use

For full Claude features, need Anthropic's native Messages API (/v1/messages).

Relevant to Garnet client Q15: Claude works via compat path but with limitations. Full Anthropic support would require native Messages API integration.
