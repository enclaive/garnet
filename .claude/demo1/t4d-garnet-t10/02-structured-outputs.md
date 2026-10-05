# Structured Outputs via Responses API — Confirmed

Date: 2026-08-19
Reference: T4D question — 19 August build, Strict Structured Outputs, Responses API

---

## Answer

Yes. The 19 August build (`2472723a4`) includes verified support for OpenAI Strict
Structured Outputs via the Responses API, including correct rehydration within
structured JSON responses. This is not delivered separately — it is part of the
build being handed over today.

---

## What was missing and what was fixed

The proxy already routed GPT-5 requests to OpenAI's Responses API (`/v1/responses`).
However, the structured output instruction was being forwarded using the Chat
Completions field name (`response_format`), which the Responses API does not
recognise. OpenAI silently ignored it and returned freeform text.

Fix (commit `5f2dbe7e9`): the proxy now converts `response_format` → `text.format`
before forwarding to the Responses API. This is the correct field name for
structured outputs on that endpoint.

```
Before:  { "response_format": { "type": "json_schema", ... } }  → ignored by OpenAI
After:   { "text": { "format": { "type": "json_schema", ... } } }  → schema enforced
```

---

## End-to-end flow

```
1. Client sends request with response_format: json_schema
2. Proxy pseudonymizes PII in message content
3. Proxy converts response_format → text.format
4. Proxy forwards to OpenAI /v1/responses
5. OpenAI enforces the schema → returns structured JSON with tokens
6. Proxy depseudonymizes → restores real values inside the JSON
7. Client receives clean structured JSON with real names
```

---

## Canary evidence — 2026-08-19

### Pre-provider capture (proxy log)

```
[IN  USER]  Extract: John Doe works at Enclaive, email john@enclaive.io
[OUT USER]  Extract: PERSON_6cea57c2 works at Enclaive, email EMAIL_ADDRESS_7f3dbbcc
[→ LLM   ]  https://api.openai.com/v1/responses | model=gpt-5 | pseudo=1492ms
[→ USER  ]  depseudo complete, 2 tokens
```

No raw PII in `[OUT USER]` — confirmed. Routed to `/v1/responses` — confirmed.

### Response received by client

```json
{"name": "John Doe", "company": "Enclaive", "email": "john@enclaive.io"}
```

Real names restored. Schema shape matches request exactly.

### German PII test

```
[OUT USER]  Extrahiere: PERSON_c0ab03cb arbeitet bei ORGANIZATION_2d539e35, erreichbar unter EMAIL_ADDRESS_cffd818c
```

Response:
```json
{"name": "Hendrik Müller", "company": "Siemens AG", "email": "h.mueller@siemens.de"}
```

---

## Pre-provider capture

The `[OUT USER]` proxy log line constitutes the pre-provider capture for the
synthetic canary. It shows exactly what was forwarded to OpenAI before the
provider received the request, with no raw PII present.

The question of an independent network-level capture for a robust E2E or
certification claim at a later stage will be handled separately and does not
block the canary retest.

---

## Test commands for T4D

```bash
curl -s -X POST https://demo-1.garnet.enclaive.cloud/api/chat/completions \
  -H "Authorization: Bearer <API-KEY>" \
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
            "name": {"type": "string"},
            "company": {"type": "string"},
            "email": {"type": "string"}
          },
          "required": ["name", "company", "email"],
          "additionalProperties": false
        }
      }
    }
  }'
```

Expected response:
```json
{"name": "Anna Müller", "company": "Deutsche Bank", "email": "a.mueller@db.de"}
```

Log to verify on cVM:
```bash
docker logs garnet-privacy-proxy-1 2>&1 | grep -E "OUT USER|→ LLM|ERROR" | tail -5
```
