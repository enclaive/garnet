# 03 · Design — Layered Cache System

**Depends on:** `01-spec.md` approval

---

## Overview

Replace the single unbounded `pseudo_cache` dict with 3 bounded caches at different granularities. Add cache metrics. Include the two prerequisite fixes (session_id fallback, thread offload) that block the cache from being fully correct.

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 · Model cache             (startup, one-time)       │
│   @lru_cache(maxsize=4) on build_analyzer(language)         │
│   preload GLiNER + spaCy in FastAPI lifespan                │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2 · NLP artifacts cache     (per-text, per-language)  │
│   OrderedDict LRU, 500 entries                              │
│   key = (language, md5(text))                               │
│   value = spaCy Doc object                                  │
│   passed to Presidio via nlp_artifacts param                │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3 · Full pseudonymization cache (per session)         │
│   OrderedDict LRU, 5000 entries                             │
│   key = (session_id, md5(text), enabled_types_hash)         │
│   value = pseudonymized text                                │
│   replaces existing pseudo_cache                            │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ CROSS-CUTTING                                               │
│   • has_pseudo: continue  (skip already-processed messages) │
│   • asyncio.to_thread(pseudonymize, ...)  (unblock loop)    │
│   • secrets.token_hex(6) session_id fallback (P0-9)         │
│   • cache_stats counter + log_cache_stats() every 100 req   │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — Model cache

**File:** `backend/privacy_proxy/app/pseudonymizer.py`

```python
from functools import lru_cache

@lru_cache(maxsize=4)
def build_analyzer(language: str) -> AnalyzerEngine:
    # existing body unchanged
    ...
```

**File:** `backend/privacy_proxy/app/main.py`

```python
from contextlib import asynccontextmanager
from app.pseudonymizer import build_analyzer, preload_gliner

@asynccontextmanager
async def lifespan(app):
    build_analyzer("en")
    build_analyzer("de")
    preload_gliner()
    yield

app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)
```

**File:** `backend/privacy_proxy/app/pseudonymizer.py` — add:

```python
_gliner_model = None

def preload_gliner():
    global _gliner_model
    if _gliner_model is None:
        _gliner_model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")

def get_gliner():
    if _gliner_model is None:
        preload_gliner()
    return _gliner_model
```

**Trade-offs:** LRU of 4 covers EN + DE with room. GLiNER preload adds ~1-2s to pod startup — worth it to fix `/health` lying about readiness.

---

## Layer 2 — NLP artifacts cache

**File:** `backend/privacy_proxy/app/pseudonymizer.py`

```python
from collections import OrderedDict
from presidio_analyzer.nlp_engine import NlpArtifacts

_nlp_doc_cache: "OrderedDict[tuple[str, str], object]" = OrderedDict()
_NLP_MAX = 500

def _get_or_parse_doc(text: str, language: str):
    key = (language, hashlib.md5(text.encode("utf-8")).hexdigest())
    doc = _nlp_doc_cache.get(key)
    if doc is not None:
        _nlp_doc_cache.move_to_end(key)
        return doc
    analyzer = build_analyzer(language)
    nlp = analyzer.nlp_engine.nlp[language]
    doc = nlp(text)
    _nlp_doc_cache[key] = doc
    if len(_nlp_doc_cache) > _NLP_MAX:
        _nlp_doc_cache.popitem(last=False)
    return doc
```

Then in `detect_entities` / `pseudonymize` call sites:

```python
doc = _get_or_parse_doc(text, language)
artifacts = NlpArtifacts.from_doc(doc, language)   # verify Presidio API
results = analyzer.analyze(text=text, language=language, nlp_artifacts=artifacts)
```

**Trade-offs:** 500 entries × ~5KB per Doc ≈ 2.5MB. Presidio API change is the only real risk — validate `nlp_artifacts` param name against installed presidio-analyzer version via context7 during implementation.

---

## Layer 3 — Bounded pseudonymization cache

**File:** `backend/privacy_proxy/app/main.py`

```python
from collections import OrderedDict

_PSEUDO_MAX = int(os.getenv("PSEUDO_CACHE_MAX", "5000"))
pseudo_cache: "OrderedDict[tuple[str, str, str], str]" = OrderedDict()

_cache_stats = {"hit": 0, "miss": 0, "evict": 0, "req": 0}

def _pseudo_with_cache(text: str, session_id: str, enabled_types) -> str:
    if not text:
        return text
    types_key = ",".join(sorted(enabled_types or []))
    key = (session_id, hashlib.md5(text.encode("utf-8")).hexdigest(), types_key)

    hit = pseudo_cache.get(key)
    if hit is not None:
        pseudo_cache.move_to_end(key)
        _cache_stats["hit"] += 1
        return hit

    _cache_stats["miss"] += 1
    out = pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)
    pseudo_cache[key] = out
    if len(pseudo_cache) > _PSEUDO_MAX:
        pseudo_cache.popitem(last=False)
        _cache_stats["evict"] += 1
    return out
```

**Key change from current:** cache key includes `enabled_types_hash`. Fixes silent wrong-output bug when a session changes its entity filter mid-conversation.

---

## Cross-cutting fixes

### C1 — has_pseudo skip (already in the file, one-line fix)

**File:** `main.py` history loop around line 517-533

```python
for i, msg in enumerate(messages[:-1]):
    text = extract_text_content(msg.get("content"))
    _text = text or ""
    has_pseudo = any(tok in _text for tok in ("PERSON_", "ORGANIZATION_", "EMAIL_ADDRESS_", "IBAN_CODE_", "PHONE_NUMBER_", "LOCATION_", "ID_"))
    log_ctx_msg(i, msg.get("role"), len(_text), has_pseudo, _text[:120])
    if not text:
        continue
    if has_pseudo:
        continue                                 # ← new
    if any(m in text for m in SYSTEM_PROMPT_MARKERS):
        continue
    out = _pseudo_with_cache(text, session_id, enabled_types)
    ...
```

### C2 — asyncio.to_thread on pseudonymize (P0-4 partial)

**File:** `main.py` — wherever `pseudonymize(...)` is called from an async handler:

```python
import asyncio

out = await asyncio.to_thread(pseudonymize, text, session_id, store.get_store(), enabled_types=enabled_types)
```

Applied at 4 call sites (main.py:499, 572, 630, and _pseudo_with_cache internally requires refactor to async).

**Trade-off:** `_pseudo_with_cache` becomes `async def` → all callers become `await`. Small ripple, mechanical change.

### C3 — session_id fallback (P0-9)

**File:** `main.py:401-405`

```python
import secrets

session_id = (
    body.get("chat_id")
    or (messages[0].get("id") if messages else None)
    or f"anon-{secrets.token_hex(6)}"                # was: MD5(first_msg)[:12]
)
```

**Impact:** anonymous sessions no longer collide. Downside: same anonymous user across two connections gets two sessions (acceptable — they had no persistent identity anyway).

### C4 — metrics

**File:** `main.py` — after the request handler completes

```python
_cache_stats["req"] += 1
if _cache_stats["req"] % 100 == 0:
    log_cache_stats(**_cache_stats, size=len(pseudo_cache))
```

**File:** `logs.py` — new helper

```python
def log_cache_stats(hit, miss, evict, req, size):
    total = hit + miss
    rate = (hit / total * 100) if total else 0
    print(f"[CACHE] req={req} hit={hit} miss={miss} evict={evict} rate={rate:.1f}% size={size}")
```

---

## Files touched

| File | Change |
|---|---|
| `backend/privacy_proxy/app/main.py` | pseudo_cache rewrite, has_pseudo skip, to_thread wrapping, session_id fallback, lifespan, stats logging |
| `backend/privacy_proxy/app/pseudonymizer.py` | `@lru_cache` on build_analyzer, preload_gliner(), _nlp_doc_cache, _get_or_parse_doc |
| `backend/privacy_proxy/app/logs.py` | log_cache_stats() helper |
| `backend/privacy_proxy/tests/test_proxy.py` | new test cases (see 05-tasks.md) |

Approx ~120 lines added, ~30 lines changed. No file deletions. No new dependencies.

---

## Risks & open questions

- **Presidio `NlpArtifacts.from_doc` API** — verify version compat via context7 before Layer 2 lands
- **GLiNER preload latency** — pod startup +1-2s, may affect rolling deploy readiness
- **Cache warming after restart** — first 3-turn user sees full latency; acceptable for now, Redis-mirror is Layer 6 future work
- **Memory bound** — 5000 pseudo × ~500B + 500 nlp × ~5KB ≈ 5MB total, well under compose 10G

## Rollback plan

Every layer is independently reversible. If metrics show regression:
- Layer 3 → restore `pseudo_cache = {}` and `_pseudo_with_cache` body
- Layer 2 → drop `nlp_artifacts` param from analyzer call
- Layer 1 → remove `@lru_cache` decorator, remove lifespan preload

No data migration = no rollback data risk.
