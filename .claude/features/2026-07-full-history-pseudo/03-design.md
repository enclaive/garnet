---
STATUS: reviewed
HANDOFF: planner
NEXT: proceed to 05-tasks.md
---

# Design — Full History Pseudonymization
Date: 2026-07-12
Model used: Opus 4.7 (max thinking)
Based on: 01-spec.md

## Architecture summary

Single file (`backend/privacy_proxy/app/main.py`), inside `proxy()`, replace
the leaking history-depseudo loop (lines 402-411) with a history-pseudo
loop that runs the exact same pseudonymize path the last message uses,
guarded by a per-session MD5 cache to keep spaCy from re-running on
repeated text.

Zero new files, zero new deps, zero API changes. The cache is a sibling
module-level dict in `main.py` — same lifetime discipline as `store` (a
`MappingStore(ttl=3600)` module-level singleton). We do **not** touch
`MappingStore` because a local dict is enough and touching shared code is
gratuitous — ponytail rung 2 (reuse what's already there) → rung 7 (minimum
code that works).

### Data flow (post-change)

```
proxy() receives body
  ├─ privacy_enabled? no  → forward untouched (unchanged)
  ├─ privacy_enabled? yes
  │   ├─ FOR msg in messages (ALL, not [:-1]):
  │   │   ├─ role=assistant AND content already contains our tokens?
  │   │   │   → pseudonymize is a no-op but still hits cache (cheap)
  │   │   ├─ is_system_prompt(msg)? → skip
  │   │   ├─ text = extract_text_content(msg["content"])
  │   │   ├─ h = md5(text)
  │   │   ├─ cache hit? → msg["content"] = rebuild_content(orig, cached)
  │   │   ├─ cache miss? → out = pseudonymize(text, session_id, store...)
  │   │   │                cache[session_id][h] = out
  │   │   │                msg["content"] = rebuild_content(orig, out)
  │   ├─ last message: existing block runs (already pseudonymizes; may
  │   │   share the same cache trivially by wrapping the call)
  │   └─ POST to LLM with fully-pseudonymized messages
```

## Phases (ordered)

### Phase 1 — Cache primitive
- **What changes:** add `pseudo_cache: dict[str, dict[str, str]] = {}` at
  module scope near `store = MappingStore(ttl=3600)` (line 43). Add a tiny
  helper `_pseudo_with_cache(text, session_id, enabled_types)` that
  encapsulates: md5 → cache lookup → pseudonymize on miss → store → return.
- **Files:** `backend/privacy_proxy/app/main.py`
- **Risk:** low. Pure addition, no call sites yet.
- **Estimated effort:** S

### Phase 2 — Replace the history-depseudo loop with history-pseudo
- **What changes:** delete lines 402-411 (the `for msg in messages[:-1]`
  depseudo block). Replace with a full-history pseudo loop that runs on
  ALL messages except the last (the last is handled by the existing block
  starting at line 439). Reuse `_pseudo_with_cache`. Honor
  `is_system_prompt` per message. Honor `privacy_enabled`.
- **Files:** `backend/privacy_proxy/app/main.py`
- **Risk:** medium. This is the behavior change. Wrong condition ordering
  could either double-pseudonymize or skip a legitimate message.
- **Estimated effort:** S

### Phase 3 — Route last message through the same cache (optional but free)
- **What changes:** at the last-message pseudonymize call (~line 439-ish
  block, wherever `pseudonymize(...)` is invoked for the newest user
  message), swap the raw call for `_pseudo_with_cache`. This gives us a
  cache hit if the user re-sends the same last message (edit/retry).
- **Files:** `backend/privacy_proxy/app/main.py`
- **Risk:** low. Behavior-identical; only difference is cache lookup.
- **Estimated effort:** S

### Phase 4 — Session TTL sweep for the cache
- **What changes:** piggyback on `MappingStore._cleanup`. When a session
  expires from `store`, its cache entry should go too. Simplest: in
  `_pseudo_with_cache`, when we detect the session is not in
  `store.get_store()` yet, we already create a fresh sub-dict; when a
  session goes away, its cache leaks until process restart. Since TTL is
  1h and typical proc uptime between deploys is small, **document and
  skip.** Add a `ponytail:` comment naming the ceiling.
- **Files:** `backend/privacy_proxy/app/main.py`
- **Risk:** none — this is a deliberate non-change.
- **Estimated effort:** S (comment only)

## Library decisions (with research)

| Decision | Chosen | Why | Source |
|---|---|---|---|
| Hash function | `hashlib.md5` | Already imported line 3; keys are internal, not adversarial → cryptographic strength irrelevant; MD5 is the fastest stdlib option for short strings. | Python stdlib `hashlib` (installed, verified in pre-work). |
| Cache structure | `dict[session_id][md5_hex] -> pseudo_text` | Sibling to `store`, matches its per-session sharding. No `MappingStore` mutation. | Existing code pattern in main.py L43. |
| Cache eviction | None active; process-scoped, TTL-implicit via mapping-store TTL | New dep for LRU is overkill; typical chat has <100 unique message texts × <100 sessions × few KB each = negligible memory. | Ponytail rung 1 — deferred until measurably needed. |
| Assistant tokens re-detection safety | Rely on spaCy not tagging `PERSON_[0-9a-f]{8}` as PERSON | Empirical assumption. Must be **verified** in Phase 5 (task-list stage). If wrong, add a pre-check `if TOKEN_RE.search(text): return text`. | Existing regex `TOKEN_NAMES` list in `split_at_safe_boundary` gives us the pattern for free. |

## Trade-offs considered

- **Sibling dict vs. embed cache inside `MappingStore`** — chose sibling.
  `MappingStore` is shared with tests and other proxy code. Adding a
  second responsibility to it violates single-purpose. A 2-line module-
  level dict is smaller than a class refactor. Trade-off cost: cache and
  store TTL are not literally coupled; acceptable per Phase 4.

- **MD5 vs. sha1 vs. sha256 vs. built-in `hash()`** — chose MD5.
  `hash()` is fine per-process but not stable across restarts (irrelevant
  here since cache is in-memory anyway, but MD5 is a nicer log line if we
  ever debug). SHA-256 wastes cycles for zero adversarial-security
  benefit — cache keys don't cross a trust boundary.

- **Cache per-session vs. global with `(session_id, hash)` compound key**
  — chose per-session. Cheaper eviction ("del cache[session_id]"), matches
  `store` shape, one less concat/encode per lookup.

- **Bail-out for tokenized assistant text** — considered a regex short-
  circuit before hashing. Skipped: hashing is O(len), pseudonymize on
  already-tokenized text is fast too, and the cache means we only do it
  once per unique message anyway. If profiling shows spaCy is still
  running on token strings and it hurts, add the regex fast-path
  (ponytail: add when measurable).

- **Replace the depseudo loop vs. keep it AND add pseudo** — chose
  replace. The depseudo loop actively converts tokens back to real PII
  before the outbound POST, which is the exact leak. Keeping it would
  cancel the new pseudo work. Removing it is safe because the response
  path already depseudonymizes for the browser; the LLM never needs real
  names in old assistant turns.

## Rollback plan

`git revert <commit-sha>` on `feature/full-history-pseudo` — restores
lines 402-411, deletes the cache dict and helper, deletes any call-site
swap in the last-message block. One file, one commit, one revert. If
already merged: cherry-revert onto `garnet-privacy-proxy`, redeploy image.

## Open questions

- [ ] Verify empirically: does `pseudonymize("PERSON_cc75010d", ...)`
      leave the text unchanged? Answered in Task 2.4 (test).
- [ ] Should we log a per-request `cache_hits=N/M` line? Deferred — add if
      profiling later shows spaCy is a bottleneck we care about.
