# Plan — RAG Response-Time Optimization

> Date: 2026-06-09 · Author: Ahmed (with Claude) · Status: draft, awaiting Seb sign-off
> Spec: `.claude/spec/rag-latency.md` · Feature folder: `.claude/features/2026-06-rag-latency/`
> Branch (to create): `feature/rag-latency`

---

## 1. TL;DR

Today a RAG-enabled chat round-trip eats a hard **~7 s before the main LLM ever sees the request**, because `expand_query()` runs a serial `gpt-4o-mini` call (`backend/privacy_proxy/app/main.py:103`, awaited at `main.py:557`). On top of that the proxy serially pseudonymizes every chunk of retrieved context, and OWU runs BM25 + semantic search + reranker on CPU. The user perceives this as "RAG is slow."

This plan cuts the perceived latency in **four stacked moves**, in order of impact:

1. **Overlap `expand_query` with chunk pseudonymization** — start it as soon as we have the question text, await it just before forwarding. Saves `min(expand_time, chunk_pseudo_time)`.
2. **In-process LRU cache for expansion** — identical question = 0 ms instead of 7 s. Big win on follow-ups, demos, eval runs.
3. **Heuristic short-circuit** — skip expansion when the question is extremely short (1–2 word follow-up) or already very long & specific. Saves 7 s on those queries entirely.
4. **Tighter expansion call** — drop `max_tokens` 150→80, lower `temperature` 0.3→0.1 (helps cache hit rate too), 15 s timeout → 6 s. Doesn't make the 7 s go away but trims the tail and improves determinism for caching.

All four are **proxy-only**. Zero OWU, Svelte, Chroma, or pseudonymizer changes. Zero new dependencies. Reversible by header toggle that already exists (`x-garnet-queryexpand`).

Optional follow-ups requiring Seb call (not in V1): swap expansion model to Haiku 4.5, lower reranker `top_k` 15→12, OWU embed cache.

---

## 2. Where the time goes today

End-to-end, with RAG ON, from user click to first streamed token:

```
[ browser ]
  │
  ▼  ~10–50 ms
[ OWU front ]
  │
  ▼  RAG retrieval inside OWU
  │     • embed user query   (all-MiniLM-L6-v2, CPU)        ~50–150 ms
  │     • BM25 + Chroma cos-sim    top_k=15                 ~50–200 ms
  │     • bge-reranker-v2-m3       top_k=15 → 6, CPU        ~400–900 ms
  │     • build <source> system message                     ~5 ms
  ▼
[ Privacy Proxy /v1/chat/completions ]   ← request now has chunks embedded
  │
  ├──  detect has_rag_context (cheap regex)                  <1 ms
  ├──  loop pseudonymize each <source> chunk (spaCy NER)     ~100 ms – 2 s
  │     • for >50 kB total, chunked 10 kB at a time
  ├──  pseudonymize last user message                        ~20–60 ms
  ├──  await expand_query()  → gpt-4o-mini sync call         ~6 000 – 8 000 ms   ← THE BOTTLENECK
  ├──  concat variants → last_message["content"]
  ▼
[ Main LLM (OpenAI / Anthropic / …) ]
  ▼  streaming response
[ Proxy: token-by-token depseudonymize + boundary handling ]
  ▼
[ Browser: SSE → render ]
```

Concrete numbers from running `rag.md` baseline + the code:

| Stage                           | Typical | Worst |
|---|---|---|
| OWU embed + retrieve + rerank   | 0.5 – 1.3 s | 2 s |
| Proxy chunk pseudonymization    | 0.1 – 1.5 s | 5 s (huge KB context) |
| Proxy user-msg pseudonymization | 20 – 60 ms  | 200 ms |
| **`expand_query` (`gpt-4o-mini`)** | **6 – 8 s** | **15 s timeout** |
| Main LLM time-to-first-token    | 0.4 – 1.5 s | 4 s (Opus, cold) |

**Observation**: `expand_query` alone routinely dominates the *entire* pre-LLM time. Everything else combined is usually ≤ 3 s; expansion is ≥ 6 s on its own and runs strictly serial.

---

## 3. Optimization strategies — ranked

For each: impact (S/M/L), risk, blast radius, and whether it's in V1.

### A — Overlap `expand_query` with chunk pseudonymization · L impact · Low risk · V1 ✅
Currently the proxy does, in order:
```
for msg in messages: pseudonymize chunks (slow)
pseudonymize user message
await expand_query()           ← 7 s, only depends on raw user text
inject variants → forward
```
`expand_query` only needs `original_content_text`, which is known at `main.py:415`. We can launch it as `asyncio.create_task` right after `has_rag_context` is detected (line 426) and `await` it just before the variants get injected (line 557). That overlaps the LLM call with all the spaCy NER passes.

**Savings**: `min(expand_time, sum(chunk_pseudo + user_pseudo))`. In practice that's ~500 ms – 2 s back, basically free. For very large KBs (5 s of chunk pseudo) it's bigger.

**Risk**: standard async exception handling; the existing function already swallows errors and returns `[]`, so `asyncio.gather(..., return_exceptions=True)` covers it.

### B — In-process LRU cache for expansion · L impact (on repeats) · Low risk · V1 ✅
Variants are a deterministic function of the question. Cache key = `sha256(question.strip().lower())`. Value = `list[str]`. Bounded LRU (e.g. `functools.lru_cache(maxsize=256)` wrapped around a sync helper, or `cachetools.TTLCache` with `maxsize=256`, `ttl=3600`).

Hit rate in normal use is low-ish, but in three scenarios it's huge:
- Alexa / Ahmed running the same eval-set queries while tuning → ~100 % hits after first round.
- Multi-turn chats where the user re-asks a slightly-rephrased question.
- Demos.

**Risk**: zero data sensitivity — variants are a generic search reformulation of the question; the question itself is not stored (only its hash). No session_id in key → variants are pooled across users, which is correct because variants are not user-specific. Worst case under a hash collision the user gets someone else's irrelevant variants, which `expand_query` already tolerates (returns `[]` semantics).

**Note**: this is *in-process*, not Redis. We do not need cross-pod sharing for v1; the cVM has one proxy replica. If/when k8s scales replicas, swap to Redis (Mission 2 follow-up, not blocking).

### C — Heuristic skip · M impact (on those queries) · Low risk · V1 ✅
Skip expansion when:
- `len(question.strip()) < 25` chars → likely a follow-up like "and?", "in German?", "what about pricing"; the chat history already constrains retrieval semantically.
- `len(question.strip()) > 240` chars AND question contains ≥ 2 capitalized proper-noun-shaped tokens (cheap regex) → user already wrote a specific, terminology-rich query; reformulations add noise.

**Both skips honor the user toggle.** If `x-garnet-queryexpand=true` is set, the skip is silent and logged; if `false`, nothing runs anyway.

**Risk**: minor — could skip in a case where expansion would have helped. We accept this because retrieval has already happened in OWU; variants only affect what the main LLM sees as the question (see §6 architectural note). The two heuristic windows are deliberately conservative.

### D — Tighter `expand_query` call · S impact · Low risk · V1 ✅
Inside `expand_query` (`main.py:130-138`):
- `max_tokens`: 150 → **80** (three short queries fit easily; 150 was generous).
- `temperature`: 0.3 → **0.1** (better cache hits, less variance, still enough diversity for query rewrite).
- `timeout`: 15 s → **6 s** (15 s was a worst-case; if `gpt-4o-mini` hasn't responded in 6 s the user is better off without expansion).

**Risk**: marginal. Lower `max_tokens` could truncate the third variant — accepted, we still cache & inject the first two. Tighter timeout could cause early returns when OpenAI is degraded — also accepted, we already return `[]` on timeout.

### E — Per-stage timing logs · S impact (visibility only) · Zero risk · V1 ✅
Add structured timing prints:
```
[TIMING] query_expand=6342ms  cache=miss
[TIMING] chunk_pseudo=812ms   n=4
[TIMING] user_pseudo=43ms
[TIMING] proxy_total=7280ms   first_token_ms=1180
```
Lets us measure A–D wins in `docker logs` without adding Prometheus. Hooks into `logs.py`.

### F — Swap expansion model to Haiku 4.5 · M–L impact · Medium risk · **V2, needs Seb**
`claude-haiku-4-5-20251001` typically responds in 1–2 s for a 150-token completion vs 6–8 s for `gpt-4o-mini`. Requires (a) Seb's call on whether the variants from Haiku are quality-equivalent for retrieval, (b) auth header logic (we already detect Anthropic via `sk-ant-`), (c) keeping the OpenAI fallback. Defer to V2.

### G — Reranker `top_k` 15 → 12 · S impact · Medium risk · **V2, needs Seb**
That's an OWU config (`webui.db`), not a proxy change. Saves ~150–300 ms of reranker CPU. Recall risk on edge questions. Out of scope for V1; can be A/B'd with the eval set after V1 lands.

### H — Async/background pre-warm of `expand_query` from the WebUI · L impact · High risk · **Out of scope**
Theoretically, OWU could fire the expansion request the moment the user *stops typing* (not on submit). Saves the full 7 s on the perceived path. Requires Svelte changes, debouncing, and a wasted-call budget. Explicitly out of scope; revisit after V1 if Seb wants more.

### I — Cache OWU's retrieval results · L impact · High risk · **Out of scope**
Requires OWU patch, schema, invalidation logic on KB upload. Not proxy territory; not V1.

---

## 4. Recommended V1 — what we ship

Bundle: **A + B + C + D + E** in one proxy commit, one PR, one Helm/Compose redeploy. All four code changes touch the same hot block in `main.py` and one new helper file; total ~120 LoC.

**Why bundle vs split**: each piece individually moves the needle modestly; together they hit the spec's acceptance bar. Splitting forces three CI cycles and three rounds of measurement on the same surface. Per Ahmed's stated preference (memory: "one bundled PR over many small ones" for refactors in the same area), bundle.

### 4.1 Concrete code changes

#### Change 1 — new module `backend/privacy_proxy/app/expand_cache.py`
A small, dependency-free cache with TTL. ~25 LoC.

```python
import hashlib
import time
from collections import OrderedDict
from typing import Optional

_MAXSIZE = 256
_TTL_SEC = 3600

class _LRU:
    def __init__(self) -> None:
        self._d: "OrderedDict[str, tuple[float, list[str]]]" = OrderedDict()

    def get(self, key: str) -> Optional[list[str]]:
        item = self._d.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.time():
            self._d.pop(key, None)
            return None
        self._d.move_to_end(key)
        return value

    def set(self, key: str, value: list[str]) -> None:
        self._d[key] = (time.time() + _TTL_SEC, value)
        self._d.move_to_end(key)
        if len(self._d) > _MAXSIZE:
            self._d.popitem(last=False)

_cache = _LRU()

def key_for(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()

def get(question: str) -> Optional[list[str]]:
    return _cache.get(key_for(question))

def put(question: str, variants: list[str]) -> None:
    if variants:
        _cache.set(key_for(question), variants)
```

#### Change 2 — `expand_query()` in `main.py:103-160`
- Add cache check at the top:
  ```python
  cached = expand_cache.get(question)
  if cached is not None:
      print(f"[QUERY EXPAND] cache hit ({len(cached)} variants)")
      return cached
  ```
- Tighten params: `max_tokens=80`, `temperature=0.1`, `timeout=6.0`.
- After successful parse, call `expand_cache.put(question, variants)` before returning.

#### Change 3 — heuristic skip helper in `main.py` (above `expand_query`)
```python
_PROPER_NOUN_RE = re.compile(r"\b[A-ZÄÖÜ][a-zäöüß]{2,}\b")

def should_skip_expansion(question: str) -> Optional[str]:
    q = question.strip()
    if len(q) < 25:
        return "too_short"
    if len(q) > 240 and len(_PROPER_NOUN_RE.findall(q)) >= 2:
        return "long_and_specific"
    return None
```

#### Change 4 — overlap expansion with pseudonymization (`main.py` around line 426)
Right after `has_rag_context` is computed (~line 426), launch the task; await it where the variants are needed (~line 557).

```python
# Kick off expansion as early as possible (before chunk pseudo loop).
expand_task = None
skip_reason = None
if query_expand and has_rag_context and last_message.get("role") in ("user", "system", "developer"):
    skip_reason = should_skip_expansion(original_content_text)
    if skip_reason:
        print(f"[QUERY EXPAND] skipped: {skip_reason}")
    else:
        auth_header = request.headers.get("authorization", "")
        _expand_url = (openai_url if is_openai else OPENAI_API_URL)
        expand_task = asyncio.create_task(
            expand_query(original_content_text, _expand_url, auth_header)
        )
```

Then at the existing injection point (~line 553–571), replace the `await expand_query(...)` line with:
```python
if expand_task is not None:
    try:
        variants = await expand_task
    except Exception as e:
        print(f"[QUERY EXPAND] task failed: {type(e).__name__}: {e}")
        variants = []
    if variants:
        enriched = pseudonymized_user_message + "\n" + "\n".join(variants)
        last_message["content"] = rebuild_content(original_content, enriched)
        print(f"[QUERY EXPAND] enriched query injected → {len(pseudonymized_user_message)} → {len(enriched)} chars")
    else:
        print(f"[QUERY EXPAND] no variants generated → using original query only")
```

Important: keep the existing `elif query_expand and not has_rag_context: print(...)` branch.

#### Change 5 — per-stage timing in `logs.py`
Add one helper:
```python
def log_timing(stage: str, ms: float, **extras) -> None:
    extra = " ".join(f"{k}={v}" for k, v in extras.items())
    print(f"[TIMING] {stage}={ms:.0f}ms {extra}".rstrip())
```
Wrap the chunk-pseudo loop, the user-pseudo block, and the expansion `await` with `t = time.perf_counter()` / `log_timing("...", (perf_counter()-t)*1000)`. Five sites total.

#### Change 6 — `test_proxy.py`
Add three tests (all sync, no real HTTP — see existing `test_proxy.py` patterns):
1. `test_expand_cache_hit_returns_same_variants` — call cache `put` then `get`, assert equality.
2. `test_expand_cache_ttl_expires` — monkeypatch `time.time()`, assert eviction.
3. `test_should_skip_expansion_heuristic` — table-driven: short → `"too_short"`, long+specific → `"long_and_specific"`, normal → `None`.

No new test for the asyncio overlap (would require an httpx mock for the gpt-4o-mini call; we already test the happy path via the proxy's main test).

### 4.2 Files touched

| File | Change | Risk |
|---|---|---|
| `backend/privacy_proxy/app/expand_cache.py` (new) | LRU cache, 25 LoC | low |
| `backend/privacy_proxy/app/main.py` | tighten `expand_query`, add overlap + heuristic skip + timing | medium — touches hot path |
| `backend/privacy_proxy/app/logs.py` | add `log_timing` helper | low |
| `backend/privacy_proxy/app/test_proxy.py` | 3 new unit tests | low |

No frontend / OWU / pseudonymizer changes. No new pip deps.

---

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| `asyncio.create_task` exception isolation — if `expand_query` raises before the await, the event loop logs an "unawaited exception" warning. | We always `await` the task in the join block; on exception we catch and fall back to `variants=[]`. |
| Cache key collision pollutes results across users. | SHA-256 over 64-char hex; collision probability negligible. Even on collision, irrelevant variants degrade gracefully (the original question is preserved). |
| Cache grows in long-running container. | LRU bound + TTL; max 256 entries × ~1 KB ≈ 256 KB RSS. |
| Heuristic skip wrongly drops expansion for queries that need it. | Bound conservatively (25 chars / 240 chars + 2 proper-nouns). Toggle still wins; user can disable header to never skip. |
| Tighter `gpt-4o-mini` `max_tokens=80` truncates third variant. | We already filter `len(v) > 3` and slice `[:3]`; truncation removes only the third variant, not the second. |
| Overlap re-orders side effects. | `expand_query` is pure (network call, returns list[str]); has no side effects on the proxy state. Order doesn't matter. |
| Breaks the `(i)` tooltip in WebUI. | `stream_with_depseudo` (`main.py:163-170`) still emits the `query_variants` field on first SSE — unchanged. |

**Rollback**: revert one commit. Header toggle (`x-garnet-queryexpand=false`) already disables expansion entirely without code change.

---

## 6. Architectural note worth flagging to Seb

Comment at `main.py:551` says: *"variants from gpt-4o-mini are NOT pseudonymized; they reach the embedding model in OWU only, not the main LLM."* The code at `main.py:566` writes the enriched (variants-concatenated) string into `last_message["content"]`, which is then forwarded to the main LLM. By the time the proxy runs, OWU has already done retrieval — the chunks are *already* in the message. So variants ride to the main LLM as extra context on the user's question, not into OWU's embed step.

This means **variants are currently helping the main LLM disambiguate the question, not improving Chroma retrieval**. If that's not the intended design, the bigger lever is moving expansion *into OWU's retrieval hook*, not optimizing the proxy. Worth a 3-line Seb confirm before V2. Does not block V1 — V1 just makes the current call cheaper and faster.

---

## 7. Measurement & validation

### Baseline (Ahmed runs once, before V1)
Build a fixed 10-question set hitting the existing KB:
- 3 short follow-ups (≤25 chars) — eg. "and pricing?"
- 4 medium questions (50–150 chars) — eg. "What are Garnet's main privacy guarantees?"
- 2 long+specific questions (>240 chars, named entities)
- 1 cold first-of-session question

For each: with RAG ON, `x-garnet-queryexpand=true`, capture `[TIMING] proxy_total` and time-to-first-token (browser DevTools network panel). Run 3× and median. Save CSV to `.claude/features/2026-06-rag-latency/baseline.csv`.

### Post-V1 verification
Same 10 questions, same procedure, capture into `post-v1.csv`. Acceptance:
- median proxy_total drops by ≥ 40 % on medium questions
- short follow-ups drop to ≤ 1 s proxy_total (skip path)
- repeat-of-same-question drops to ≤ 100 ms proxy_total (cache hit)
- chunk-id-set returned to the main LLM unchanged on ≥ 9/10 questions (sanity: log the chunk hashes pre/post)

### Tests
- `test_proxy.py` 22/22 still pass.
- Three new tests added in §4.1 pass.
- One smoke test on the live cVM after deploy:
  ```
  docker logs garnet-privacy-proxy-1 --since 5m | grep -E "^\[TIMING\]|cache (hit|miss)"
  ```
  must show `cache miss` then `cache hit` on a repeated question.

### Negative path
- With `x-garnet-queryexpand=false`, no `[QUERY EXPAND]` logs appear.
- With RAG OFF (no `<source>` in message), no `[QUERY EXPAND]` or `[TIMING] chunk_pseudo` logs.

---

## 8. Rollout

| Step | Who | Command |
|---|---|---|
| 1. Branch + commit | Ahmed | `git checkout -b feature/rag-latency` |
| 2. Implementation (agents) | Claude | follow Tasks list in §9 |
| 3. Local unit tests | Ahmed | `cd backend/privacy_proxy && python -m pytest app/test_proxy.py -v` |
| 4. Push + PR | Ahmed | `git push -u origin feature/rag-latency` then `gh pr create …` |
| 5. PR review | Ahmed Bouzid | bundle review with the rest of Mission 1 work |
| 6. Merge | Ahmed Bouzid | squash merge |
| 7. CI builds & cosigns image | GitHub Actions | tagged `privacy-proxy:<sha>` in Harbor |
| 8. Deploy on cVM | Ahmed | `ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull privacy-proxy && docker compose up -d --force-recreate privacy-proxy"` |
| 9. Run 10-question eval | Ahmed | capture `post-v1.csv` |
| 10. Update `tasks.md` and `rag.md` roadmap | Ahmed | mark "Query Expansion parallel exec" ✅ |

k8s/Mission 2 forward-portability: nothing here depends on Compose specifics; the image is the same, env vars unchanged, no new volumes.

---

## 9. Tasks (for the SDD `05-tasks.md` slot)

### Agent prompts — code only (one prompt per change)

#### T1 — Expansion cache module
**File:** `backend/privacy_proxy/app/expand_cache.py` (new)
**Problem:** We re-pay 6–8 s on every `expand_query` call even when the exact same question repeats. Need an in-process, bounded, TTL'd cache keyed by `sha256(question.strip().lower())`.
**Acceptance:** New module exposes `get(question)`, `put(question, variants)`. Bounded to 256 entries, 1 h TTL, no external deps. Unit tests `test_expand_cache_hit_returns_same_variants` and `test_expand_cache_ttl_expires` pass.

#### T2 — Tighten and cache-wire `expand_query`
**File:** `backend/privacy_proxy/app/main.py:103-160`
**Problem:** `expand_query` calls `gpt-4o-mini` with `max_tokens=150`, `temperature=0.3`, `timeout=15.0`. We want `max_tokens=80`, `temperature=0.1`, `timeout=6.0`, and a cache lookup before the HTTP call + a cache write after a successful parse.
**Acceptance:** On cache hit, function returns within <5 ms without an HTTP call and logs `[QUERY EXPAND] cache hit`. On miss, behaves as today but with the new params. Existing failure paths (`status != 200`, timeout, exception, empty parse) remain and still return `[]`.

#### T3 — Heuristic skip helper
**File:** `backend/privacy_proxy/app/main.py` (add near `expand_query` definition)
**Problem:** Expansion is wasteful for very short follow-ups (<25 chars) and for already-specific long queries (>240 chars with ≥2 proper-noun-shaped capitalized tokens).
**Acceptance:** New `should_skip_expansion(question) -> Optional[str]` returns `"too_short"`, `"long_and_specific"`, or `None`. Table-driven unit test passes.

#### T4 — Overlap expansion with pseudonymization
**File:** `backend/privacy_proxy/app/main.py` (around line 426 and around line 553–571)
**Problem:** Today `await expand_query(...)` blocks for 6–8 s strictly *after* chunk pseudonymization. We want expansion launched as soon as `has_rag_context` is known and the last message is a user/system message, and only awaited at the variant-injection point.
**Acceptance:** `expand_task` is created via `asyncio.create_task` at the early site (line 426 area) when expansion is wanted and not skipped by heuristic. At the injection site, variants are obtained from `await expand_task` inside a try/except that falls back to `variants=[]`. The existing `[QUERY EXPAND] no variants generated` and `[QUERY EXPAND] skipped — no RAG context` log lines are preserved. No regressions in the existing test_proxy suite.

#### T5 — Per-stage timing logs
**File:** `backend/privacy_proxy/app/logs.py` and `backend/privacy_proxy/app/main.py`
**Problem:** We can't measure A–D wins from current logs.
**Acceptance:** New `log_timing(stage, ms, **extras)` in `logs.py`. Five `time.perf_counter()` brackets in `main.py`: chunk-pseudo loop, user-pseudo block, expansion-await, full-proxy-pre-LLM, end-to-end. Each emits one `[TIMING] stage=Xms …` line. Format is grep-friendly.

#### T6 — Unit tests
**File:** `backend/privacy_proxy/app/test_proxy.py`
**Problem:** Need T1 / T3 covered and existing 22 tests must still pass.
**Acceptance:** Three new tests as named above. `python -m pytest app/test_proxy.py -v` → 25/25 pass.

Each task is independent except T4 depends on T2 + T3 (it references the cache and the heuristic). Run T1 → T2 → T3 → T5 in any order, then T4, then T6.

### Deploy / verify commands (Ahmed runs)

```bash
# build
cd ~/Desktop/garnet
git add backend/privacy_proxy/app/expand_cache.py \
        backend/privacy_proxy/app/main.py \
        backend/privacy_proxy/app/logs.py \
        backend/privacy_proxy/app/test_proxy.py
git commit -m "feat: rag latency optimization (cache, overlap, heuristic, timing)"
git push -u origin feature/rag-latency
# wait for Actions to build + cosign

# deploy
ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull privacy-proxy && docker compose up -d --force-recreate privacy-proxy"

# in-container sanity
ssh root@65.108.38.50 "docker exec garnet-privacy-proxy-1 grep -n 'expand_cache\|should_skip_expansion\|\\[TIMING\\]' /service/app/main.py | head"
ssh root@65.108.38.50 "docker exec -w /service garnet-privacy-proxy-1 python3 -m pytest app/test_proxy.py -v"

# live timing check (ask one question with RAG on, then re-ask it)
ssh root@65.108.38.50 "docker logs garnet-privacy-proxy-1 --tail=200 | grep -E '\\[TIMING\\]|\\[QUERY EXPAND\\]'"
# expect: first request → 'cache miss' + expand ~6-8s
#         repeat       → 'cache hit'  + expand <5ms
```

---

## 10. Open questions (for Seb review)

- [ ] Target latency reduction — is **≥ 40 % median proxy_total** the right acceptance bar?
- [ ] OK to bundle A+B+C+D+E into one PR vs split?
- [ ] OK to launch `expand_query` with `asyncio.create_task` and join later (changes request-path control flow slightly)?
- [ ] Tighten `gpt-4o-mini` params (`max_tokens 150→80`, `temp 0.3→0.1`, `timeout 15s→6s`) — any quality concern?
- [ ] Cache scope: in-process for V1, Redis later when k8s scales? Or skip Redis entirely?
- [ ] Heuristic skip thresholds — 25 chars / 240 chars / 2 proper-nouns. Tune?
- [ ] Architectural note in §6: are variants supposed to feed OWU retrieval (currently they don't)? Affects V2 direction, not V1 code.
- [ ] V2: swap to Haiku 4.5 for expansion? Reranker top_k 15→12?

---

## 11. What does NOT change

- Pseudonymizer behavior, entity types, ORG/PERSON filtering rules.
- OWU config: chunk_size, overlap, hybrid weight, top_k, reranker model, relevance threshold.
- Chroma schema or KB data — no reindex.
- Svelte UI: (i) tooltip wiring already consumes `query_variants` from the SSE first frame; we preserve that field.
- Header contract: `x-garnet-queryexpand`, `x-garnet-entities`, etc. unchanged.
- `body["stream"] = False` paths (Ollama).
- Any networking exposure surface.
- Mission 2 / k8s migration timeline.
