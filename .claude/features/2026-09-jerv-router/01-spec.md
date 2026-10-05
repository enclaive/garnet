# JERV — Prompt-scored auto model routing

**Date:** 2026-09-27
**Owner:** Ahmed
**Status:** Spec — awaiting Seb approval (structural proxy change)

---

## Idea

User picks pseudo-model `jerv/auto` in OWU. Proxy runs the raw prompt through a **cheap local scorer** (Ollama `llama3.2:1b`), gets back a JSON score vector (complexity, reasoning, creativity, speed), applies a rules table → picks the real model + provider, rewrites the request, forwards.

```
"what date today?" → {complexity:0.05, reasoning:0.02, creativity:0.01, speed:0.95}
                   → speed>0.8 → llama3.2:1b @ Ollama
                   → forward
```

---

## Current setup (confirmed by graphify + read)

| File | Role in flow | Line |
|---|---|---|
| `backend/privacy_proxy/app/main.py` | `proxy()` — single entry point | L385 |
| Provider URL selection (key prefix + `body["model"]` sniff) | L408–423 |
| `body["model"]` extracted | L436 |
| Pseudonymize last user message | L~445 onward |
| Forward to chosen provider URL | end of `proxy()` |
| `backend/open_webui/routers/openai.py` | OWU forwards real provider URL via `x-openai-base-url` header | — |

**Everything OWU sends today:** `body["model"]`, `body["messages"]`, `Authorization`, `x-openai-base-url`, `x-garnet-*`.

JERV needs to rewrite three of those before pseudonymization runs: `body["model"]`, `x-openai-base-url`, `Authorization`.

---

## Delta — what JERV adds

**One new file** — `backend/privacy_proxy/app/jerv.py`:

```python
async def score_and_route(prompt: str, cfg: JervConfig) -> RouteChoice:
    """Score prompt via scorer_model, apply rules, return (model, url, api_key_env)."""
```

**One new config** — `backend/privacy_proxy/app/jerv.yaml`:

```yaml
scorer_model: "llama3.2:1b"
scorer_url:   "http://ollama:11434/v1/chat/completions"
criteria:
  complexity: "Is this a complex multi-part question?"
  reasoning:  "Does this need deep step-by-step reasoning?"
  creativity: "Does this need creative or open-ended writing?"
  speed:      "Is this a simple factual lookup where speed matters?"
rules:
  # first match wins
  - if: "speed > 0.8"      then: { model: "llama3.2:1b",     provider: "ollama"    }
  - if: "reasoning > 0.7"  then: { model: "claude-opus-4",   provider: "anthropic" }
  - if: "creativity > 0.6" then: { model: "gpt-4o",          provider: "openai"    }
  - default:                    { model: "gpt-4o-mini",      provider: "openai"    }
providers:
  ollama:    { url: "http://ollama:11434",                          auth_env: null              }
  anthropic: { url: "https://api.anthropic.com/v1",                 auth_env: "ANTHROPIC_KEY"   }
  openai:    { url: "https://api.openai.com/v1",                    auth_env: "OPENAI_KEY"      }
cache_ttl_seconds: 300
```

**Injection point** — `main.py` right after `body["model"]` is read (L436, before pseudonymize):

```python
model = body.get("model", "unknown")
if model == "jerv/auto":
    choice = await jerv.score_and_route(first_msg, JERV_CFG)
    body["model"] = choice.model
    openai_url    = choice.provider_url
    url           = f"{openai_url.rstrip('/')}/{actual_path}"
    request.headers.__dict__["_list"].append(  # or pass headers dict downstream
        (b"authorization", f"Bearer {os.environ[choice.auth_env]}".encode())
    )
    log_jerv(first_msg, choice)
```

**Scoring call** — OpenAI-compatible JSON mode on Ollama:

```python
resp = await http.post(cfg.scorer_url, json={
    "model": cfg.scorer_model,
    "messages": [
        {"role": "system", "content": "Score each dimension 0.0–1.0. Reply JSON only."},
        {"role": "user",   "content": f"Prompt: {prompt}\nDimensions: {list(cfg.criteria)}"}
    ],
    "response_format": {"type": "json_object"},
    "stream": False,
})
scores = json.loads(resp.json()["choices"][0]["message"]["content"])
```

---

## Cache

`OrderedDict` LRU keyed by `sha256(prompt)`, TTL 5 min, max 1000 entries. Same as `pseudo_cache` pattern (`main.py:57`). No new dep.

---

## Frontend

Add `"jerv/auto"` as a virtual model in OWU model selector list. No proxy-side detection needed beyond the string match. UI change lives in `src/lib/components/chat/ModelSelector/Selector.svelte` — add one hard-coded entry at top.

---

## Failure modes

| Failure | Behavior |
|---|---|
| Scorer model down / timeout (>2s) | Fall back to `default` rule model. Log `jerv_scorer_timeout`. |
| Scorer returns invalid JSON | Same fallback. |
| Selected provider `auth_env` unset | 500 with clear message, don't leak env-var name to user. |
| Prompt empty / no user message | Skip JERV, forward as-is (default model). |

---

## Test plan

1. **Unit** — `test_jerv.py`: score_and_route() with mocked scorer returning canned JSON — assert 4 rule branches hit correct model.
2. **Integration** — send POST to proxy with `model: "jerv/auto"` and prompt `"what date today?"` — assert forwarded URL is Ollama.
3. **Regression** — send POST with any other model — assert JERV path skipped, no scorer call.
4. **Ponytail self-check** — assert() in a `if __name__ == "__main__"` block in `jerv.py` covering the 4 rules.

---

## Ponytail notes

- `# ponytail: first-match rules, no weighted combining. Upgrade to weighted score if a rule can't cleanly separate two providers.`
- `# ponytail: sha256(prompt) cache key, no session_id. Same prompt = same route regardless of chat. Upgrade to (session_id, prompt) if per-user policy needed.`
- `# ponytail: scorer runs on Ollama in-cluster, no separate service. Upgrade to dedicated scorer pod if latency or contention shows up.`

---

## Diagram

Draw.io flow lives at `flow.drawio` (open in https://app.diagrams.net). Overview:

```
User → OWU (picks jerv/auto) → Caddy → Privacy Proxy
                                          │
                                          ▼
                                 body["model"] == "jerv/auto"?
                                    ├─ no  → normal flow (existing)
                                    └─ yes ▼
                                       cache hit? ─── yes ─┐
                                          │                │
                                          no               │
                                          ▼                │
                                 Scorer (Ollama llama3.2:1b)
                                          │                │
                                          ▼                │
                                {complexity,reasoning,creativity,speed}
                                          │                │
                                          ▼                │
                                 rules table → (model, provider, key)
                                          │◄───────────────┘
                                          ▼
                             rewrite body["model"], url, Authorization
                                          ▼
                             pseudonymize (existing)
                                          ▼
                             forward → LLM provider
                                          ▼
                             depseudonymize → user
```

---

## Open questions for Seb

1. OK to add virtual model `jerv/auto` to OWU selector, or should it be a per-user toggle in Settings?
2. Should the rules table be per-tenant (Enclaive customer) or global for now?
3. Is `llama3.2:1b` acceptable as the scorer, or must it stay CPU-friendly (e.g. quantized 0.5B)?
