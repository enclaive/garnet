# 01 · Spec — Cache Rework

**Date:** 2026-08-23
**Branch:** demo1upgrade
**Owner:** Ahmed
**Status:** Draft — awaiting Seb approval

---

## Problem

Proxy freezes for the whole request queue around chat message 5-6. Users report "stuck after 5 prompts." Root cause is a stack of three issues, but the cache layer is the biggest contributor and the easiest to fix without touching Redis/uvicorn/httpx.

## Current state

One cache exists: `pseudo_cache: dict[str, dict[str, str]]` at `main.py:56`.

- Global, per-session, keyed by `md5(text)` → pseudonymized text
- Never evicted (memory leak → OOM → GC pauses → visible stalls)
- No `enabled_types` in cache key (wrong output when entity filter changes mid-session)
- Cross-user leak when two users share the MD5 session_id fallback
- No metrics — can't tell hit rate or size
- No cache for spaCy analyzer construction (rebuilt per request)
- No cache for spaCy `nlp_artifacts` (Presidio re-tokenizes same text)
- Already-pseudonymized history messages still hit the cache lookup unnecessarily

## Goals

1. Bounded memory — pod RSS stable under sustained traffic
2. Eliminate the "stuck after 5" symptom in staging load test
3. Zero data-migration — no Redis schema change, no proxy-restart migration
4. Observable — cache hit/miss/evict counters logged periodically
5. Correct — cache keys include all inputs that affect output

## Non-goals

- Multi-tier promotion/demotion policies (premature)
- Distributed cache (memcached/hazelcast) — single-node covers all realistic load
- Semantic/embedding cache — GLiNER output is exact-match, not fuzzy
- Rewriting MappingStore (separate concern, tracked in improvement report)

## Success criteria

- 10 concurrent 20-turn conversations complete without freeze (currently: hangs turn 5-6)
- Pod RSS stable ±10% over a 30-min load test (currently: monotonic growth)
- Cache hit rate ≥ 60% after 3-turn warmup, logged every 100 requests
- No regression in T4D vendor defect tests
- p50 chat latency drops ≥ 100ms on turn ≥ 3 (from cached history skips)

## Constraints

- Ahmed deploys manually — no auto-deploy
- Must land on `demo1upgrade` branch
- Must not touch `body["stream"] = False` paths
- No new dependencies unless justified (stdlib preferred)

## Out of scope for this feature

Fixes tracked separately in `.claude/docs/improvements/2026-08-22-improve.md`:
- P0-1 async Redis (cross-cutting, needed for full "stuck after 5" fix)
- P0-3 shared httpx client
- P0-4 uvicorn workers + `asyncio.to_thread`
- P0-9 session_id fallback (blocks cross-user leak in cache)

**Note:** Without P0-4 and P0-9 the cache fix alone won't fully eliminate the stuck symptom. Recommend bundling P0-4 into this feature — it's a 1-line change with big payoff. P0-9 is a prerequisite for cache correctness and should be included.
