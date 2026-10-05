# Pre-Provider Capture — Verifiable Evidence

Date: 2026-08-12

---

## What is captured

The proxy emits structured log lines for every request. Two lines bracket the
pseudonymization step and together constitute an independent, pre-provider
capture of what was sent to the LLM:

- `[IN  USER]` — the raw user message as received from the client, before any
  processing. This is the plaintext containing PII.

- `[OUT USER]` — the same message after pseudonymization, before it is
  forwarded to the LLM provider. This is the token-substituted version the
  provider actually receives.

The `[→ LLM]` line immediately following confirms the provider endpoint and
model the pseudonymized body was sent to.

## Example from live system

```
12:43:01.823 [IN  USER] Am Montag hat Adelbach einen Termin mit Hendrik Öztürk bei Enclaive.
12:43:01.901 [OUT USER] Am LOCATION_b703fc6a hat PERSON_d1bfe8a1 einen Termin mit PERSON_cc75010d bei ORGANIZATION_bd3a68a5.
12:43:01.902 [→ LLM   ] https://api.openai.com/v1/responses | model=gpt-5 | pseudo=78ms
```

The provider never sees the original names, organisation, or weekday-as-location
false positive — only the pseudonymized tokens. The mapping from token back to
original value is held in the proxy session store and never forwarded.

## How to use this for a canary retest

For each of T4D's 10 retest cases, the `[OUT USER]` log line is the verifiable
pre-provider capture. It shows exactly what left the proxy. T4D can compare:

1. `[IN  USER]` — confirm the input matches the supplied case text
2. `[OUT USER]` — confirm all expected PII tokens are replaced and no raw PII
   appears in the forwarded message
3. `[→ LLM]` — confirm the correct provider and model were used

Logs are written to stdout by the proxy container and are accessible via
the container log stream, or via the orchestration log sink in the target
environment.

## Log retention note

Logs are ephemeral (stdout only, no persistent store). For a witnessed retest,
T4D or Enclaive should capture `docker logs --follow` or pipe to a file during
the test session. No persistent log infrastructure is required — the capture
is operator-initiated per session.
