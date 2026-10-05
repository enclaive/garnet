# Smart Router — Research & Next Steps

Date: 2026-09-29
Status: Jev (via OpenRouter) live in prod. Laya (local CPU alt) evaluated, not yet built.

---

## What's live today

- Model = "Auto Router" (`openrouter/auto`) in OWU triggers Jev routing in `privacy_proxy/app/router.py`.
- Pool = OWU models with **Smart Router** capability toggle ON (read via OWU API, 5min TTL cache).
- Fallback = if no smart_router models configured, random OpenRouter sample.
- Selected model name now displays under each response (fixed 2026-09-28 in `openai.py:_stream_with_pseudo_prompt` — `picked_model` was being dropped when synthesizing the metadata SSE event).

## How Jev works (brief)

Small LLM trained specifically to read (prompt + model list) → output ranked list. ~200ms/call, closed weights, API-only via OpenRouter. Cost: per-call.

**Gain we get:** cheaper models per query = same token budget covers more requests.

---

## Local alternative: Laya

421M encoder from Convai Innovations. Apache 2.0. Same API shape as Jev (`POST /v1/systemone`). Runs on CPU.

**Install:**
```
pip install "laya[serve]"
laya-serve  # http://localhost:8000
```

**Resources needed:**
| | RAM | CPU | Latency |
|---|---|---|---|
| Laya 421M | ~1 GB | any x86/ARM (RPi works) | ~33ms local |
| Jev (baseline) | — | — | ~270ms API |

**Benchmarks (Laya vs Jev):**
| Metric | Jev | Laya |
|---|---|---|
| General accuracy | 0.73 | 0.77 (fine-tuned) |
| Large pool (77+) | 0.87 | 0.43 ⚠️ |
| Throughput | 3.2/sec | 86/sec |
| Cost | per call | free |

**Catch:** Laya splits a fixed token budget across all options → degrades past ~20 models in the pool. For our pool of 5–10 it's fine.

---

## Integration path (not yet built)

Replace OpenRouter call in `router.py:jev_rank()` with local POST to `http://localhost:8000/v1/systemone`. Same input (prompt + pool), same output (ranked list). Kill `OPENROUTER_API_KEY` dependency for routing.

Sidecar in `docker-compose.yml`:
```yaml
laya:
  image: <build from convaiinnovations/laya>
  ports: ["127.0.0.1:8000:8000"]
```

**Skipped:** actual test run, sidecar Dockerfile, benchmark on our real pool. Add when we commit to migrating.

---

## Open questions

- Which local — Laya (best) or OpenJev/SemIf 0.6B (3.5GB RAM, ~1s)? → Laya wins on every metric for CPU use.
- Manual pool extension (add OpenRouter model IDs to a config list without exposing them in OWU model editor) — nice-to-have, not built.
- Fine-tuning Laya on our own routing decisions — deferred until we have logs.

## Sources

- [Jev on OpenRouter](https://openrouter.ai/typesafe/jev-router)
- [Laya on HuggingFace](https://huggingface.co/convaiinnovations/laya)
- [Laya install guide](https://laya-ai.com/guides/install-laya)
- [Laya vs Jev benchmark](https://www.orcarouter.ai/blog/jev-vs-laya)
- [Honest Laya benchmark](https://flowtivity.ai/blog/laya-open-source-jev-alternative/)
