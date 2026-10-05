# OpenAI Responses API — Approach

Date: 2026-08-12

---

## Routing decision

The proxy detects the target model on every request. When the model is `gpt-5`,
`gpt-5.5-pro`, or `gpt-5.6-luna` and the destination is `api.openai.com`, the
proxy automatically routes to the Responses API endpoint (`/v1/responses`)
instead of the standard Chat Completions endpoint (`/v1/chat/completions`).
No configuration change or client-side flag is required.

## Request translation

Because the Responses API uses a different request schema than Chat Completions,
the proxy rewrites the outgoing request body before forwarding:

- The `messages` array is split: system-role messages are extracted and placed
  in the `instructions` field; all other messages are placed in the `input` field.
- The token limit parameter is renamed from `max_completion_tokens` to
  `max_output_tokens`, as required by the Responses API.
- The flat `reasoning_effort` field sent by the client is nested into
  `reasoning: { effort: <value> }`, which is the format the Responses API expects.
- Parameters not accepted by the Responses API (`top_p`, `frequency_penalty`,
  `presence_penalty`, `logprobs`, `n`, `tools`, `tool_choice`, etc.) are stripped
  before the request leaves the proxy.

## Pseudonymization

Pseudonymization runs on the message content before the routing decision is made.
The privacy pipeline is provider-agnostic: the same NER → token replacement →
depseudonymization logic applies on the Responses API path as on any other path.
No special handling is required for this endpoint.

## Streaming

The Responses API uses a different SSE event format than Chat Completions.
The proxy includes a stream adapter that normalises Responses API events back
into the standard delta format expected by Open WebUI, so streaming works
transparently for the user.

## Confirmed parameters

| Parameter | Status |
|-----------|--------|
| `reasoning.effort` | Confirmed working — verified live 2026-08-12 |
| `store: false` | Supported — passed through if set by the client |
| Strict Structured Outputs | To be confirmed  |
