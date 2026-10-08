import os
import time
import random
import httpx

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
LAYA_URL = os.getenv("LAYA_URL", "http://laya:8000")
ROUTER_URL = os.getenv("ROUTER_URL", "https://openrouter.ai/api/v1/systemone")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "~typesafe/jev-latest")
OPEN_WEBUI_URL = os.getenv("OPEN_WEBUI_URL", "http://open-webui:8080")
OPEN_WEBUI_API_KEY = os.getenv("OPEN_WEBUI_API_KEY", "")

# ponytail: skip the router for OWU-internal chat completions (title/tags/follow-ups) — they would waste calls
_INTERNAL_MARKERS = ("### Task:\nGenerate", "### Task:\nSuggest", "### Guidelines:", "concise, 3-5 word title", "1-3 broad tags")
_INTERNAL_FALLBACK = os.getenv("ROUTER_INTERNAL_MODEL", "")  # if set, forced for internal calls; else first pool entry

_smart_router_cache: dict[str, str] = {}  # {id: description}
_smart_router_cache_ts: float = 0.0
_SMART_ROUTER_TTL = 300  # refresh every 5 min

_openrouter_cache: list[str] = []

_owu_connections_cache: list[tuple[str, str]] = []
_owu_connections_ts: float = 0.0
_OWU_CONN_TTL = 300

# ponytail: anthropic/groq/gemini all expose OpenAI-compat /v1/chat/completions — same shape, just route to their native base
_DIRECT_PROVIDER_HINTS = {
    "openai": "openai.com",
    "mistral": "mistral.ai",
    "deepseek": "deepseek.com",
    "anthropic": "anthropic.com",
    "groq": "groq.com",
    "gemini": "googleapis.com",
    "google": "googleapis.com",
}


async def _fetch_owu_connections(client: httpx.AsyncClient) -> list[tuple[str, str]]:
    global _owu_connections_cache, _owu_connections_ts
    now = time.monotonic()
    if _owu_connections_cache and now - _owu_connections_ts < _OWU_CONN_TTL:
        return _owu_connections_cache
    if not OPEN_WEBUI_API_KEY:
        return []
    try:
        r = await client.get(
            f"{OPEN_WEBUI_URL}/openai/config",
            headers={"Authorization": f"Bearer {OPEN_WEBUI_API_KEY}"},
            timeout=5.0,
        )
        data = r.json()
        urls = data.get("OPENAI_API_BASE_URLS") or []
        keys = data.get("OPENAI_API_KEYS") or []
        _owu_connections_cache = [(u.strip(), k.strip()) for u, k in zip(urls, keys)]
        _owu_connections_ts = now
    except Exception as e:
        print(f"[ROUTER CONN] fetch failed: {e}", flush=True)
    return _owu_connections_cache


_model_conn_cache: dict[str, tuple[str, str]] = {}
_model_conn_ts: float = 0.0


async def _fetch_model_connection_map(client: httpx.AsyncClient) -> dict[str, tuple[str, str]]:
    """model_id → (base_url, api_key) using OWU's own per-model urlIdx. Single source of truth."""
    global _model_conn_cache, _model_conn_ts
    now = time.monotonic()
    if _model_conn_cache and now - _model_conn_ts < _OWU_CONN_TTL:
        return _model_conn_cache
    conns = await _fetch_owu_connections(client)
    if not conns or not OPEN_WEBUI_API_KEY:
        return {}
    try:
        r = await client.get(
            f"{OPEN_WEBUI_URL}/api/models",
            headers={"Authorization": f"Bearer {OPEN_WEBUI_API_KEY}"},
            timeout=5.0,
        )
        out: dict[str, tuple[str, str]] = {}
        for m in r.json().get("data", []):
            mid, idx = m.get("id"), m.get("urlIdx")
            if mid and isinstance(idx, int) and 0 <= idx < len(conns) and conns[idx][1]:
                out[mid] = conns[idx]
        _model_conn_cache = out
        _model_conn_ts = now
    except Exception as e:
        print(f"[ROUTER MODELS] fetch failed: {e}", flush=True)
    return _model_conn_cache


async def resolve_provider(model_id: str, client: httpx.AsyncClient) -> tuple[str, str] | None:
    """Jev picked model_id — route to its real OWU-configured provider.
    Returns (base_url, api_key) or None (caller falls back to OR)."""
    model_map = await _fetch_model_connection_map(client)
    if model_id in model_map:
        base_url, key = model_map[model_id]
        print(f"[ROUTER RESOLVE] {model_id} → {base_url} (owu urlIdx)", flush=True)
        return base_url, key
    # fallback: hint-based match for ids not in OWU's model list
    connections = await _fetch_owu_connections(client)
    if "/" in model_id:
        hint = _DIRECT_PROVIDER_HINTS.get(model_id.split("/")[0])
        if hint:
            for base_url, key in connections:
                if hint in base_url and key:
                    print(f"[ROUTER RESOLVE] {model_id} → {base_url} (hint fallback)", flush=True)
                    return base_url, key
    return None


async def _fetch_smart_router_pool(client: httpx.AsyncClient) -> dict[str, str]:
    """Fetch models with smart_router capability from OWU, returning {id: description|id}."""
    global _smart_router_cache, _smart_router_cache_ts
    now = time.monotonic()
    if _smart_router_cache and now - _smart_router_cache_ts < _SMART_ROUTER_TTL:
        return _smart_router_cache
    if not OPEN_WEBUI_API_KEY:
        return {}
    try:
        r = await client.get(
            f"{OPEN_WEBUI_URL}/api/v1/models/base",
            headers={"Authorization": f"Bearer {OPEN_WEBUI_API_KEY}"},
            timeout=5.0,
        )
        models = r.json()
        _smart_router_cache = {
            m["id"]: ((m.get("meta") or {}).get("description") or m["id"])
            for m in models
            if (m.get("meta") or {}).get("capabilities") and m["meta"]["capabilities"].get("smart_router")
        }
        _smart_router_cache_ts = now
    except Exception:
        pass
    return _smart_router_cache


async def _fetch_openrouter_pool(client: httpx.AsyncClient) -> list[str]:
    # ponytail: lazy-init, refresh on restart. Fallback when no smart_router models configured.
    global _openrouter_cache
    if _openrouter_cache:
        return _openrouter_cache
    if not OPENROUTER_KEY:
        return []
    r = await client.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        timeout=10.0,
    )
    data = r.json().get("data", [])
    _openrouter_cache = [
        m["id"] for m in data
        if m.get("id") and ":batch" not in m["id"]
    ]
    return _openrouter_cache


async def _fetch_pool(client: httpx.AsyncClient) -> dict[str, str]:
    pool = await _fetch_smart_router_pool(client)
    if pool:
        return pool
    return {m: m for m in await _fetch_openrouter_pool(client)}


async def laya_pick(messages: list, client: httpx.AsyncClient, pool=None, session_id: str = "") -> tuple[str, list[str]]:
    """Return (picked_model, fallback_candidates sorted by Jev probability desc)."""
    smart_pool = await _fetch_smart_router_pool(client)
    if pool is None:
        pool_dict = smart_pool or await _fetch_pool(client)
    elif isinstance(pool, list):
        pool_dict = {m: smart_pool.get(m, m) for m in pool}
    else:
        pool_dict = pool
    if not pool_dict:
        raise RuntimeError("Laya pool empty — enable Smart Router on models in OWU or check OPENROUTER_API_KEY")
    # ponytail: use OWU model description as semantic criteria for Laya (not opaque ids)
    ids = list(pool_dict.keys())
    if not smart_pool:
        ids = random.sample(ids, min(6, len(ids)))
    criteria = {i: pool_dict[i] for i in ids}
    last = messages[-1] if messages else {}
    content = last.get("content", "")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))

    # skip router for OWU-internal calls (title/tags/follow-ups)
    if any(m in content for m in _INTERNAL_MARKERS):
        fallback = _INTERNAL_FALLBACK if _INTERNAL_FALLBACK in criteria else ids[0]
        print(f"[ROUTER PICK] internal call detected → {fallback} (no router call)", flush=True)
        return fallback, [m for m in ids if m != fallback]

    body = {
        "state": {"body": str(content)[:2000], "chars": len(content), "turns": len(messages)},
        "questions": {
            "model": {
                "type": "choice",
                "instructions": "Which model handles this task?",
                "criteria": criteria,
            }
        },
    }
    if session_id:
        body["session_id"] = session_id[:256]
    headers = {}
    if "openrouter.ai" in ROUTER_URL:
        # ponytail: prefer OR key from OWU connections (single source of truth); fall back to env var
        or_key = OPENROUTER_KEY
        connections = await _fetch_owu_connections(client)
        for base_url, key in connections:
            if "openrouter.ai" in base_url and key:
                or_key = key
                break
        headers["Authorization"] = f"Bearer {or_key}"
        body["model"] = ROUTER_MODEL
    else:
        body["lang"] = "en"  # local Laya hint
    print(f"[ROUTER PICK] via={ROUTER_MODEL or 'laya-local'} prompt={str(content)[:80]!r} options={len(criteria)}", flush=True)
    try:
        r = await client.post(ROUTER_URL, headers=headers, json=body, timeout=10.0)
        ans = r.json()["answers"]["model"]
        choice = ans["choice"]
        probs = ans.get("probabilities", {})
        picked = choice if choice in criteria else ids[0]
        # fallbacks: all other candidates sorted by Jev probability (highest next-best first)
        fallbacks = [m for m, _ in sorted(probs.items(), key=lambda kv: kv[1], reverse=True) if m != picked and m in criteria]
        # include any pool model Jev didn't rank, at the end
        for m in ids:
            if m != picked and m not in fallbacks:
                fallbacks.append(m)
        print(f"[ROUTER PICK] → {picked} (conf={ans.get('confidence', 0):.2f}) fallbacks={fallbacks[:3]}", flush=True)
        return picked, fallbacks
    except Exception as e:
        print(f"[ROUTER PICK] FAILED fallback={ids[0]} err={e}", flush=True)
        return ids[0], [m for m in ids if m != ids[0]]
