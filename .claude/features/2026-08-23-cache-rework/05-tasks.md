# 05 · Tasks — Cache Rework

**Depends on:** `03-design.md` approval
**Total estimated effort:** ~1 day for T1-T7, +1 day for T8-T10

Ordered by impact/effort. Ship top-to-bottom. Each task is independently mergeable — do NOT batch into one PR.

---

## T1 · Bounded LRU on pseudo_cache (P0-2 fix)

**File:** `backend/privacy_proxy/app/main.py`
**Effort:** S (~30 min)
**Depends on:** —

- [ ] Replace `pseudo_cache: dict` with `OrderedDict`
- [ ] Change key from `session_id → md5(text)` nested dict to flat tuple `(session_id, md5, types_key)`
- [ ] Add `_PSEUDO_MAX = int(os.getenv("PSEUDO_CACHE_MAX", "5000"))`
- [ ] In `_pseudo_with_cache`: `.get()` + `.move_to_end()` on hit; append + `.popitem(last=False)` on miss overflow
- [ ] Include `enabled_types_hash` in cache key
- [ ] Write test: send 6000 unique messages, assert `len(pseudo_cache) <= 5000`
- [ ] Write test: same text with different `enabled_types` produces different cache entries

**Verify:** RSS stable across 10 000 unique messages in load test

---

## T2 · has_pseudo skip (P1-15 fix)

**File:** `backend/privacy_proxy/app/main.py` history loop (~line 517)
**Effort:** S (2 min)
**Depends on:** —

- [ ] Add `if has_pseudo: continue` after existing `has_pseudo` computation and log_ctx_msg call
- [ ] Write test: message with `"PERSON_abc123"` in content is not re-processed on second pass (assert cache_stats miss count doesn't increment)

**Verify:** cache miss rate drops significantly on turn ≥ 2 in staging logs

---

## T3 · @lru_cache on build_analyzer (P0-6 fix)

**File:** `backend/privacy_proxy/app/pseudonymizer.py`
**Effort:** S (5 min)
**Depends on:** —

- [ ] Add `from functools import lru_cache`
- [ ] Decorate `build_analyzer` with `@lru_cache(maxsize=4)`
- [ ] Write test: `build_analyzer("en")` called 100 times, assert only one AnalyzerEngine instance created (identity check)

**Verify:** second call to `/analyze` with same language completes in <10ms warm (was 200-500ms)

---

## T4 · Secure session_id fallback (P0-9 fix, cache correctness prereq)

**File:** `backend/privacy_proxy/app/main.py:401-405`
**Effort:** S (5 min)
**Depends on:** —

- [ ] `import secrets`
- [ ] Replace `hashlib.md5(first_msg.encode()).hexdigest()[:12]` with `f"anon-{secrets.token_hex(6)}"`
- [ ] Write test: two requests with `first_msg="Hi"` produce different session_ids
- [ ] Write test: cache entries under `anon-*` sessions do not cross-contaminate

**Verify:** manually — send same first message from two curl instances, verify separate session logs

---

## T5 · asyncio.to_thread around pseudonymize (P0-4 partial fix)

**File:** `backend/privacy_proxy/app/main.py` — 4 call sites
**Effort:** M (30 min)
**Depends on:** T1 (cache changes shouldn't clash)

- [ ] Refactor `_pseudo_with_cache` to `async def`
- [ ] In `_pseudo_with_cache` cache-miss path: `out = await asyncio.to_thread(pseudonymize, ...)`
- [ ] Update all callers to `await _pseudo_with_cache(...)`
- [ ] Wrap direct `pseudonymize()` calls at main.py:572, 630 in `asyncio.to_thread(...)`
- [ ] Write test: long-running pseudonymize call doesn't block a concurrent `/health` request

**Verify:** with one 8-turn chat in progress, a second chat responds to `/health` in <10ms

---

## T6 · Cache metrics + logging

**File:** `backend/privacy_proxy/app/main.py`, `logs.py`
**Effort:** S (30 min)
**Depends on:** T1

- [ ] Add `_cache_stats = {"hit": 0, "miss": 0, "evict": 0, "req": 0}` at module scope
- [ ] Increment counters in `_pseudo_with_cache`
- [ ] Add `log_cache_stats(hit, miss, evict, req, size)` in `logs.py`
- [ ] Call every 100 requests: `if _cache_stats["req"] % 100 == 0: log_cache_stats(...)`
- [ ] Add `/cache/stats` endpoint returning current counters as JSON (optional, debug convenience)

**Verify:** logs show `[CACHE] req=100 hit=X miss=Y evict=Z rate=N% size=M` after 100 requests

---

## T7 · Model preload in lifespan (P1-24 fix)

**File:** `backend/privacy_proxy/app/main.py`, `pseudonymizer.py`
**Effort:** S (20 min)
**Depends on:** T3

- [ ] Add `preload_gliner()` and `get_gliner()` in pseudonymizer.py
- [ ] Add `lifespan` context manager in main.py
- [ ] Preload EN + DE analyzers and GLiNER at startup
- [ ] Change existing lazy GLiNER load to route through `get_gliner()`
- [ ] Write test: first request after startup completes in <500ms (currently ~1-3s cold)

**Verify:** startup log shows `[INIT] GLiNER ready` before `/health` returns 200

---

## T8 · spaCy nlp_artifacts cache (P2-31 fix)

**File:** `backend/privacy_proxy/app/pseudonymizer.py`
**Effort:** M (2 h)
**Depends on:** T3

- [ ] Verify Presidio `NlpArtifacts.from_doc` API via context7 for installed version
- [ ] Add `_nlp_doc_cache` OrderedDict with `_NLP_MAX = 500`
- [ ] Implement `_get_or_parse_doc(text, language)`
- [ ] Refactor `detect_entities` to use cached Doc via `nlp_artifacts` param
- [ ] Fallback: if API mismatch, skip Layer 2 and log warning — do not block T1-T7 ship
- [ ] Write test: same text scanned twice, spaCy tokenizer called once

**Verify:** profile a history-heavy request — spaCy tokenize time roughly halves

---

## T9 · Integration test — "stuck after 5" reproduction

**File:** `backend/privacy_proxy/tests/test_load_stuck5.py` (new)
**Effort:** M (2 h)
**Depends on:** T1-T7 merged

- [ ] Script 10 concurrent async clients, each sending 20 chat turns
- [ ] Assert all conversations complete within 20 × (LLM budget + 500ms)
- [ ] Assert pod RSS growth < 100MB over the test
- [ ] Assert no request exceeds 10s wall time
- [ ] Compare with baseline: pre-cache-rework tag should fail this test

**Verify:** test passes on `demo1upgrade` branch after T1-T7, fails on `main`

---

## T10 · Deploy + monitor

**Owner:** Ahmed (manual deploy per team convention)
**Depends on:** T9 green

- [ ] Merge to `demo1upgrade`
- [ ] Deploy to cVM (Docker Compose)
- [ ] Watch `[CACHE]` log line for first hour — hit rate should climb past 60% after warmup
- [ ] Watch RSS via `docker stats privacy-proxy` — should plateau within 20 min
- [ ] Rollback if: hit rate <20% after 500 req, or RSS grows past 3GB, or T4D tests regress

---

## Handoff notes

- After T1-T7 merge, invoke `reviewer` agent in FULL mode against `main.py` + `pseudonymizer.py` diff
- After T9 passes, invoke `infra` agent for deployment safety review (compose changes, if any)
- Do NOT combine with async Redis (P0-1) work — that's a separate feature folder

**STATUS:** spec drafted 2026-08-23 · awaiting Seb approval before T1 kickoff
