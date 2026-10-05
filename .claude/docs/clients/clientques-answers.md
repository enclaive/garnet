# Client Questions — Answers
Source: actual proxy code · backend/privacy_proxy/app/main.py + logs.py

---

## Phase 1 — Garnet standalone / proxy

**1. Which models are currently on the Responses API allowlist?**
Default: `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.5-2026-04-23`, `gpt-5.5-pro-2026-04-23`.
These are the only models routed to the newer Responses endpoint instead of the standard chat endpoint.
Additional models can be added via environment variable without any code change or redeployment — for example, adding `gpt-5` requires only a configuration update.

**2. Are any reasoning models included?**
No. The allowlist only contains gpt-5.5 variants — no o1/o3/reasoning models currently.
Adding one requires setting the `RESPONSES_API_MODELS` env var — no code change needed.

**3. If yes, which reasoning model can we configure for the test?**
`o3` is the recommended choice. It can be enabled via a configuration update only — no code change or redeployment required. Once added, `reasoning.effort` is forwarded to OpenAI without modification.

**4. What does Garnet do if a model is requested that is not on the allowlist?**
It routes normally through the standard chat endpoint — no rejection, no error.
The Responses API is only a special path for listed models; everything else falls through to standard chat.

**5. Is the request rejected?**
No. Unknown models are forwarded as-is to the provider. The provider may reject if the model doesn't exist.
Only two things cause a rejection: (1) provider rejects unknown model name, (2) wrong API key. Garnet has no model blocklist.

**6. Or is it passed through unfiltered?**
Passed through with full pseudonymization applied — privacy still works, only the endpoint differs.

**7. If streaming is not used, does rehydration apply to the complete response body?**
Yes — for all providers and all modes. When streaming is used, original values are restored chunk by chunk as the response arrives. When streaming is disabled, Garnet restores original values on the complete response before returning it. Local model responses (Ollama) are always fully restored. No gap exists across any provider or configuration.

**8. Is the replacement consistent within the scope of a single request?**
Yes. Token = `sha256(original_value)[:8]` — deterministic. Same name always produces same token within and across requests in the same session.

**9. Specifically: is the same name replaced with the same placeholder across all JSON fields?**
Yes. The hash is content-based, not position-based. "Max Mustermann" → `PERSON_cc75010d` everywhere it appears.

**10. Can two different people with the same name (e.g. two "Mr. Müller") be distinguished?**
No. Same string = same hash = same token. Garnet cannot distinguish two people who share an identical name string — this is a known limitation of the current design.

**11. Does Garnet accept a supplied name list or custom replacement map per request?**
Not currently. Entity detection runs automatically at request time — names, emails, and organizations are discovered from the message content. There is no mechanism to supply a pre-known list of entities before processing begins. This is a planned capability.

**12. Can Garnet use this to deterministically pseudonymize known stakeholders while NER detects third parties?**
Not supported today. The capability described in Q11 is the prerequisite — once a known entity list can be supplied, Garnet can guarantee deterministic tokens for those stakeholders while automatically detecting any additional third parties mentioned in the conversation. Not yet implemented.

---

## Before production use

**13. Does Garnet support "gpt-5" with "reasoning.effort" on the Responses endpoint?**
Yes. Set `RESPONSES_API_MODELS` env var to include `gpt-5` — Garnet routes it to the `/responses` endpoint and `reasoning.effort` is forwarded as-is. No code change or redeployment required.
Caveat: when using the Garnet web UI (Open WebUI), there is no field to set `reasoning.effort` — the UI sends a standard chat request. This parameter is only available when calling the Garnet API directly.

**14. Can this model and parameter be represented on the allowlist?**
Yes. Both the model and the parameter are fully supported. `gpt-5` can be added to the Responses API allowlist via environment variable, and `reasoning.effort` is forwarded to OpenAI without modification. No redeployment required.

**15. Does Garnet support Anthropic Messages API passthrough?**
Claude is supported for standard chat — messages are pseudonymized and restored correctly. However, Garnet currently routes Claude through the OpenAI-compatible endpoint, not Anthropic's native Messages API. This means Anthropic-specific features such as extended thinking, PDF processing, citations, prompt caching, and beta headers are not available. Standard Claude conversations work without any additional configuration. Full native Anthropic API support is planned as a future enhancement.

**16. Does the Claude path work without additional deployment if the provider can be configured per AI function?**
Yes — Claude works today without any additional deployment. It can be configured as a connection in the Open WebUI settings by providing the Anthropic endpoint and API key. No extra infrastructure is required.

**17. Does Garnet rehydrate all textual fields of the response envelope?**
Garnet restores original values in the message content field — which is where the AI's reply appears. This applies to all providers and both streaming and non-streaming modes. Metadata fields such as `finish_reason`, `usage`, model identifiers, and tool call arguments are not rehydrated as they do not contain user data from the conversation.

**18. Or does Garnet only rehydrate plain text blocks?**
Correct — only plain text content fields. Structured fields, tool calls, and JSON values inside content are not rehydrated.

**19. How does this behave with structured outputs (OpenAI JSON vs Anthropic response format)?**
Two risks apply. First, if the user sends sensitive data embedded inside structured JSON (e.g. a JSON object with a name field), Garnet's entity detection may not identify it — spaCy is trained on natural language, not JSON format. Second, if the AI returns structured JSON in its response, token replacement works in simple cases but is not guaranteed for complex or deeply nested structures. Plain text conversations are fully covered. Structured input/output use cases should be tested before production use.

**20. Do cleartext names appear in the proxy logs?**
Yes, currently. The first 200 characters of each message are logged before pseudonymization to support issue detection during the testing phase. This logging is intentionally kept for now to help identify edge cases and validate correct behavior. It will be removed before production deployment.

**21. Does the mapping table appear in the proxy logs?**
No. `log_mapping()` only logs the session ID and token count: `[MAPPING] session=abc123xx total_tokens=3`. The actual token↔value pairs are never printed.

**22. If yes, can this be disabled?**
N/A — the mapping table is never logged, so there is nothing to disable. The token-to-value pairs exist in memory only and are never written to any log file. Mapping logging could technically be added but would expose all pseudonymized values in plain text, defeating the privacy guarantee — it is therefore not provided. The cleartext input logging from Q20 will be removed before production.

**23. Which token format is used for attestation?**
Not applicable at proxy level. Token format for pseudonymization: `TYPE_sha256(value)[:8]` e.g. `PERSON_cc75010d`. Attestation (vHSM/TLS) is handled at the infrastructure layer by Enclaive, not the proxy.

**24. Can a vHSM release policy be bound to the runtime measurement?**
Yes — this is an Enclaive infrastructure feature (Nitride/vHSM), independent of the proxy. The proxy runs inside the confidential VM; the release policy binds to the cVM measurement.

**25. Does the attestation prove the actual runtime environment and not only supply-chain or build artifacts?**
Yes. Enclaive's attestation is hardware-rooted — the CPU itself generates a measurement of what is actually running at that moment. This goes beyond build-time verification: it proves the exact code running inside the confidential VM, the hardware environment it runs on, and guarantees that no hypervisor or host OS can access the memory. 

**26. What do the data processing agreement and pricing look like for production use?**
This information is not available at this stage. Commercial terms, data processing agreements, and pricing for production use will be communicated separately.

**27. Are there reliable figures from pilot installations regarding proxy overhead?**
No measured figures are available yet. The primary source of latency is the entity detection step (spaCy NER), which processes each message to identify names, emails, and organizations. Based on standard spaCy benchmarks, this adds approximately 20–150ms depending on message length and language. These are estimates only — no production telemetry or pilot measurements have been collected to date.

**28. Is a P95 overhead below 300 ms realistic?**
This is plausible for typical business messages. The main latency source is entity detection, which adds approximately 20–150ms depending on message length. Token replacement and HTTP forwarding add negligible overhead. For standard conversational messages, a P95 below 300ms is achievable. For very long inputs or documents, this threshold may be exceeded. Confirmed figures require dedicated benchmarking, which has not been conducted yet.
