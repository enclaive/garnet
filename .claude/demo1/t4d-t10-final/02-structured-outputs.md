# OpenAI Strict Structured Outputs — Confirmed

Date: 2026-08-19

---

## Answer

Yes. The delivered build supports OpenAI Strict Structured Outputs via the Responses API, including correct rehydration of pseudonymized values within the structured JSON response. This is part of the delivery — not a separate future item.

---

## How to test

Structured Outputs is an API-only feature (the `response_format` parameter is not exposed in the Open WebUI chat interface). To verify, T4D can issue a direct API call using any OpenAI-compatible client or curl.

**Endpoint:** `https://demo-1.garnet.enclaive.dev/api/chat/completions`
**Auth:** `Authorization: Bearer <api-key>` — an API key can be issued on request or created via the Garnet admin UI under Settings → Account → API Keys.
**Model:** `gpt-5`

**Example request:**

```bash
curl -s -X POST https://demo-1.garnet.enclaive.dev/api/chat/completions \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role": "user", "content": "Extract: Anna Müller works at Deutsche Bank, email a.mueller@db.de"}],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "extraction",
        "strict": true,
        "schema": {
          "type": "object",
          "properties": {
            "name":    {"type": "string"},
            "company": {"type": "string"},
            "email":   {"type": "string"}
          },
          "required": ["name", "company", "email"],
          "additionalProperties": false
        }
      }
    }
  }'
```

**Expected response (streamed, assembled by the OpenAI-compatible client):**

```json
{"name": "Anna Müller", "company": "Deutsche Bank", "email": "a.mueller@db.de"}
```

Pre-provider verification (that the payload actually forwarded to OpenAI contained no raw PII) is covered separately in `04-verification.md`.
