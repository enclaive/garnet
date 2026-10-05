# Garnet — Trade-offs

> Decisions made during design/build that have real consequences.
> Updated as we go through client questions.

## Background: OpenAI has two APIs

| | `/chat/completions` (old) | `/responses` (new) |
|---|---|---|
| Status | Still works, all models | Recommended for new projects |
| Reasoning models | Basic use only | Full support + `reasoning.effort` |
| Agentic tools | No | Built-in (web_search, code_interpreter) |

Garnet defaults to `/chat/completions` — works for all providers including Claude. Models are promoted to `/responses` via `RESPONSES_API_MODELS` env var when needed.

---

## 1. One unified pipeline (OpenAI-compat) vs. native provider APIs

**What we chose:** All providers (OpenAI, Anthropic, Groq, Gemini, Ollama) go through the same `/chat/completions` format. One pseudonymize → one depseudo. Done.

**What we lose:**
- Anthropic native features: extended thinking, PDF processing, citations, prompt caching, strict tool use JSON
- OpenAI Responses API agentic tools (web_search, code_interpreter built-in) not available for non-allowlisted models

**Why:** Adding a second pipeline (e.g. `/v1/messages` for Anthropic) means separate streaming parsers, separate depseudo logic, separate test surface. The unified path keeps the codebase small and all providers working out of the box.

**When to revisit:** If a client specifically needs Claude extended thinking or Anthropic prompt caching in production.

---

## 2. Hardcoded Responses API allowlist → now env-var configurable

**What it was:** `RESPONSES_API_MODELS` was a hardcoded Python set — adding a model required a code change + redeploy.

**What we changed:** Now reads from `RESPONSES_API_MODELS` env var, falls back to the same defaults. No code change to add a model.

**Trade-off accepted:** Defaults still ship with gpt-5.5 family only. Anyone using reasoning models (o3, gpt-5) with `reasoning.effort` needs to set the env var manually — it won't work out of the box.

---

## 3. Reasoning models: `/chat/completions` vs `/responses`

**What we chose:** Reasoning models (o1, o3) are not in the allowlist by default → they go to `/chat/completions`.

**What we lose:** `reasoning.effort` parameter is silently ignored — OpenAI only accepts it on `/responses`. Basic prompt/response works, advanced reasoning control does not.

**Why:** The Responses API response format differs from chat/completions. Depseudo only knows one format. Routing a model to `/responses` without testing the payload shape risks broken responses.

**When to revisit:** When a client wants o3 with `reasoning.effort` — add the model to `RESPONSES_API_MODELS` env var and test the response format first.

---

## 4. stream=false gap on cloud models ✅ FIXED

~~Non-streaming cloud models were not depseudonymized.~~ Fixed this session — sync depseudo now runs on `choices[0].message.content` before returning.

---

## 5. reasoning.effort not exposed in Open WebUI

**Gap:** OWU sends standard chat requests — no field for `reasoning.effort`. Only available when calling Garnet API directly.

**When to revisit:** If a client wants reasoning control from the UI — add a dropdown to OWU's model params panel.

---

## 6. Structured JSON input: PII may not be detected

**Gap:** spaCy is trained on natural language sentences, not JSON format. If a user sends sensitive data embedded in a JSON structure (e.g. `{"name": "Max Mustermann"}`), entity detection may miss it — the name is never pseudonymized before reaching the LLM.

**When to revisit:** If clients use Garnet with structured input payloads or tool-use patterns that embed PII in JSON fields.

---

## 7. Structured JSON output: token replacement not guaranteed

**Gap:** Garnet does plain string replacement on the response content field. Simple JSON responses are restored correctly. Complex or deeply nested JSON structures may have tokens unrestored if the replace misses escaped or nested values.

**When to revisit:** If clients use structured outputs or function calling and need guaranteed PII restoration in all JSON fields.

---

## 8. Hash-based tokens: no disambiguation of same-name entities

**What we chose:** Token = `sha256(value)[:8]` — deterministic. Same string always → same token.

**What we lose:** Two people with the same name (e.g. two "Mr. Müller") get the same token. Garnet cannot tell them apart.

**Why:** Deterministic hashing is stateless, cheap, and consistent across sessions. Context-aware disambiguation (e.g. position in org chart) would require a named entity resolution layer that doesn't exist.

**When to revisit:** If a client's use case involves multiple people with identical names in the same conversation and disambiguation matters.
