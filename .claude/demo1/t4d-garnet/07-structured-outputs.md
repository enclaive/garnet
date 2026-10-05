# Structured Outputs via Responses API — Garnet Support

Date: 2026-08-18
Build: commit `5f2dbe7e9` · proxy image `harbor.enclaive.cloud/garnetdemo/privacy-proxy:5f2dbe7e9`

---

## Answer to T4D's question

**Will the 19 August build include verified support for OpenAI Strict Structured Outputs via the Responses API, including correct rehydration within structured JSON responses?**

Yes. This is included in the build delivered on 2026-08-18 (one day ahead of the T+10 deadline).

---

## What was missing and what was fixed

The proxy already routed GPT-5 requests to OpenAI's Responses API (`/v1/responses`). However, the structured output instruction was being forwarded using the Chat Completions field name (`response_format`), which the Responses API does not recognise. OpenAI silently ignored it and returned freeform text.

**Fix:** the proxy now converts `response_format` → `text.format` before forwarding to the Responses API. This is the correct field name for structured outputs on that endpoint.

```
Before fix:  { "response_format": { "type": "json_schema", ... } }  → ignored by OpenAI
After fix:   { "text": { "format": { "type": "json_schema", ... } } }  → schema enforced
```

Change: 7 lines in `backend/privacy_proxy/app/main.py`.

---

## How it works end to end

```
1. T4D TMS sends request to Garnet with response_format: json_schema
2. Garnet proxy pseudonymizes PII in the message content
3. Proxy converts response_format → text.format
4. Proxy forwards to OpenAI /v1/responses
5. OpenAI enforces the schema → returns structured JSON with tokens
6. Proxy depseudonymizes → restores real values in the JSON
7. T4D TMS receives clean structured JSON with real names
```

---

## Live evidence — 2026-08-18

### Request sent to Garnet

```json
{
  "model": "gpt-5",
  "messages": [{"role": "user", "content": "Extract: John Doe works at Enclaive, email john@enclaive.io"}],
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
}
```

### Proxy log — pre-provider capture

```
[IN  USER]  Extract: John Doe works at Enclaive, email john@enclaive.io
[OUT USER]  Extract: PERSON_6cea57c2 works at Enclaive, email EMAIL_ADDRESS_7f3dbbcc
[→ LLM   ]  https://api.openai.com/v1/responses | model=gpt-5 | pseudo=1843ms
[→ USER  ]  depseudo complete, 2 tokens
```

- `[IN USER]` — raw input with PII
- `[OUT USER]` — pseudonymized — this is what OpenAI received, no raw PII
- `[→ LLM]` — confirms routing to `/v1/responses` (Responses API)
- `[→ USER]` — 2 tokens restored in the response

### Response received by T4D TMS (assembled from stream)

```json
{"name": "John Doe", "company": "Enclaive", "email": "john@enclaive.io"}
```

Real names restored. Schema shape matches request exactly.

---

## How T4D can test this

### Prerequisites
- Garnet endpoint: `https://demo-1.garnet.enclaive.cloud`
- OWU API key (from Garnet admin panel → Settings → Account → API Keys)
- Any HTTP client (curl, Postman, OpenAI SDK)

### Test command (curl)

```bash
curl -s -X POST https://demo-1.garnet.enclaive.cloud/api/chat/completions \
  -H "Authorization: Bearer <YOUR-API-KEY>" \
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

### What T4D will receive

The response is a standard OpenAI-compatible streaming response. Each chunk carries a piece of the JSON:

```
data: {"choices":[{"delta":{"content":"{\""}}]}
data: {"choices":[{"delta":{"content":"name"}}]}
data: {"choices":[{"delta":{"content":"\":\"Anna Müller\""}}]}
...
data: [DONE]
```

Assembled result:
```json
{"name": "Anna Müller", "company": "Deutsche Bank", "email": "a.mueller@db.de"}
```

Any OpenAI-compatible SDK assembles the stream automatically. The TMS receives a single JSON object — no manual chunk assembly required.

### What to verify

| Check | How | Pass condition |
|-------|-----|----------------|
| Schema enforced | Response is valid JSON matching schema | No freeform text |
| PII pseudonymized | Check `[OUT USER]` in proxy logs | No raw names in log |
| Real values restored | Response contains real names/email | Not tokens |
| Routed to Responses API | Check `[→ LLM]` in proxy log | Shows `/v1/responses` |

### Log capture during test

```bash
# On cVM, run before sending the request:
docker logs -f garnet-privacy-proxy-1 2>&1 | grep -E "IN  USER|OUT USER|LLM|ERROR"
```

---

## Note on streaming

Garnet uses streaming by default (same as OpenAI). The response arrives as chunks that the client SDK assembles into the final JSON. This is standard OpenAI client behavior — no special handling required on T4D's side.

---

## Immutable build reference

| Field | Value |
|-------|-------|
| Commit | `5f2dbe7e9` |
| Branch | `demo1upgrade` |
| Proxy image | `harbor.enclaive.cloud/garnetdemo/privacy-proxy:5f2dbe7e9` |
| WebUI image | `harbor.enclaive.cloud/garnetdemo/garnet-webui:5f2dbe7e9` |
| Deployed | 2026-08-18 |
