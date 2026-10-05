# Q7 — Request-bound `[→ LLM]` routing proof

**Build under test:** `harbor.enclaive.cloud/garnetdemo/privacy-proxy:v-t4d-b1-fix`
**Digest:** `sha256:874400c065d86b0fdc1f1d1405ccc4454270b4aee39e1f7743601aa4ec53733e`
**Container:** `garnet-privacy-proxy-1` on `root@65.108.38.50`
**Capture:** 2026-09-11 19:30 UTC

---

## Request

A single strict-`response_format` (`json_schema` with `strict: true`) request was sent to
the client-facing `/chat/completions` endpoint using model `gpt-5`, with
`reasoning_effort=low` and `store=false`. The user message contains the B1 case name so
the same trace also proves the pseudonymizer runs.

```json
POST http://localhost:8080/openai/chat/completions
Authorization: Bearer sk-fake-test-only    <-- fake by design, see note below
Content-Type: application/json

{
  "model": "gpt-5",
  "stream": false,
  "reasoning_effort": "low",
  "store": false,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "extraction",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "name":  {"type": "string"},
          "email": {"type": "string"}
        },
        "required": ["name", "email"],
        "additionalProperties": false
      }
    }
  },
  "messages": [
    {"role": "system", "content": "Extract the fields exactly."},
    {"role": "user",   "content": "{\"name\":\"Anna Müller-Öztürk\",\"email\":\"a.mueller@example.de\"}"}
  ]
}
```

## Proxy log (verbatim)

```
19:30:04.783 [REASONING] effort=low
19:30:04.783 [GARNET] session=anon-9be provider=openai privacy=ON model=gpt-5 path=chat/completions
19:30:05.785 [OUT USER] {"name": "PERSON_bdf0d8ff", "email": "EMAIL_ADDRESS_ecdd41ef"}
19:30:05.785 [OUT USER+] {"name": "PERSON_bdf0d8ff", "email": "EMAIL_ADDRESS_ecdd41ef"}
19:30:05.787 [→ LLM   ] https://api.openai.com/v1/responses | model=gpt-5 | pseudo=1004ms
```

## What each line proves

| T4D requirement | Line | Evidence |
|---|---|---|
| Client-facing endpoint is `/chat/completions` | `[GARNET] path=chat/completions` | Yes |
| Model is a Responses-API model | `[GARNET] model=gpt-5` | Matches `RESPONSES_API_MODELS = {"gpt-5", ...}` |
| `reasoning_effort` preserved (nested as `reasoning.effort`) | `[REASONING] effort=low` | Emitted by `pseudonymizer` right before body remap: `body["reasoning"] = {"effort": effort}` (main.py:481) |
| **Internal outbound routing** to `/v1/responses` | `[→ LLM   ] https://api.openai.com/v1/responses` | This is the outbound URL the proxy actually hit — `main.py:455` `url.replace("/v1/chat/completions", "/v1/responses")` |
| `store: false` preserved | Sent in request, forwarded unchanged in body | Not explicitly logged; not modified by the Responses-API remap code (main.py:493-495 lists fields that ARE dropped; `store` is not in that list) |
| B1 name protected pre-provider | `[OUT USER] {"name": "PERSON_bdf0d8ff", ...}` | No `Anna`, `Müller`, or `Öztürk` in outbound payload |

## Note on the fake API key

The request intentionally uses `sk-fake-test-only`. OpenAI rejected the call with
`401 invalid_api_key` — expected. The proxy's routing decision, `reasoning.effort`
translation, and `[→ LLM]` log line all fire **before** the outbound request completes.
The evidence is the log line, not the LLM's response body. This method avoids consuming
production quota during a verification-only test.

