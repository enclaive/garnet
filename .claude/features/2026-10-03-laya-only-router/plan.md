---
STATUS: ready-for-impl
HANDOFF: implementer
NEXT: /implementer 2026-10-03-laya-only-router
evidence: cf21cc718c38db59883cfe2b0bee58d811fe1e3f
---

# Plan — laya-only router (drop jev_pick)
Date: 2026-10-03

## Goal
Delete `jev_pick` and all JEV-related code; `laya_pick` becomes the sole model picker.

## What exists (graphify orientation)
- `backend/privacy_proxy/app/router.py` — 100 lines. Two pickers: `jev_pick` (L29-53) and `laya_pick` (L56-83). Shared `_fetch_pool` (L12-26) used by both. `_demo()` (L86-99) currently tests `jev_pick`. `JEV_MODEL` env var read at L6, used only in `_fetch_pool` line-filter (L25) and `jev_pick`.
- `backend/privacy_proxy/app/main.py` — already imports and calls `laya_pick` only (L438-439). No `jev_pick` usage. No changes needed.
- `.env.example` (repo root) — `JEV_ROUTER_MODEL='typesafe/jev-router'` on L10. Must be removed.
- `laya_pick` is clean and complete as-is — no structural changes needed beyond it now being the only picker.

## Approach
Three surgical edits, one file each:

1. `router.py` — three cuts, zero additions:
   - Remove `JEV_MODEL = os.getenv(...)` (L6)
   - In `_fetch_pool`, remove the `and m["id"] != JEV_MODEL` filter from L25 (the pool no longer needs to exclude the jev-router model since we're not using OpenRouter's model picker at all)
   - Delete `jev_pick` function entirely (L29-53)
   - Rewrite `_demo()` to call `laya_pick` instead of `jev_pick`

2. `.env.example` — remove the `JEV_ROUTER_MODEL` line (L10)

3. `main.py` — no change (already uses `laya_pick`)

## Files to touch
- `backend/privacy_proxy/app/router.py` — delete `JEV_MODEL`, `jev_pick`; clean `_fetch_pool` filter; fix `_demo()`
- `.env.example` — remove `JEV_ROUTER_MODEL='typesafe/jev-router'`

## Done when
- [ ] `grep -r "jev_pick\|JEV_MODEL\|JEV_ROUTER" backend/privacy_proxy/` returns nothing
- [ ] `grep "JEV_ROUTER_MODEL" .env.example` returns nothing
- [ ] `python backend/privacy_proxy/app/router.py` runs `_demo()` against `laya_pick` without error (requires `LAYA_URL` reachable or mock)
- [ ] `main.py` import of `laya_pick` still resolves (no name change)

## Risks
- `_fetch_pool` filter removal (dropping `!= JEV_MODEL`) is a no-op in practice since `laya_pick` never routes to OpenRouter's jev-router — safe to remove, keeps pool logic clean.
- If any future code (hooks, tests, docker-compose) references `JEV_ROUTER_MODEL`, it silently becomes a no-op env var — worth a quick `grep -r JEV` at impl time to catch stragglers.
