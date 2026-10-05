Phase 1 — Garnet standalone / proxy

1. Which models are currently on the Responses API allowlist?
2. Are any reasoning models included?
3. If yes, which reasoning model can we configure for the test?
4. What does Garnet do if a model is requested that is not on the allowlist?
5. Is the request rejected?
6. Or is it passed through unfiltered?
7. If streaming is not used, does rehydration apply to the complete response body?
8. Is the replacement consistent within the scope of a single request?
9. Specifically: is the same name replaced with the same placeholder across all JSON fields?
10. Can two different people with the same name, for example two different “Mr. Müller”, be distinguished?
11. Does Garnet accept a supplied name list or custom replacement map per request?
12. Can Garnet use this to deterministically pseudonymize known stakeholders, while the NER additionally detects freely mentioned third parties?

Before production use — not a blocker for Phase 1

13. Does Garnet support "gpt-5" with "reasoning.effort" on the Responses endpoint?
14. Can this model and parameter be represented on the allowlist?
15. Does Garnet support Anthropic Messages API passthrough?
16. Does the Claude path work without an additional deployment if the provider can be configured per AI function?
17. Does Garnet rehydrate all textual fields of the response envelope?
18. Or does Garnet only rehydrate plain text blocks?
19. How does this behave with structured outputs, especially OpenAI JSON versus the Anthropic-specific response format?
20. Do cleartext names appear in the proxy logs?
21. Does the mapping table appear in the proxy logs?
22. If yes, can this be disabled?
23. Which token format is used for attestation?
24. Can a vHSM release policy be bound to the runtime measurement?
25. Does the attestation prove the actual runtime environment and not only supply-chain or build artifacts?
26. What do the data processing agreement and pricing look like for production use?
27. Are there reliable figures from pilot installations regarding proxy overhead?
28. Is a P95 overhead below 300 ms realistic?