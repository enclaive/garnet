import os
import time
import random
import httpx

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
JEV_MODEL = os.getenv("JEV_ROUTER_MODEL", "typesafe/jev-router")
OPEN_WEBUI_URL = os.getenv("OPEN_WEBUI_URL", "http://open-webui:8080")
OPEN_WEBUI_API_KEY = os.getenv("OPEN_WEBUI_API_KEY", "")

_smart_router_cache: list[str] = []
_smart_router_cache_ts: float = 0.0
_SMART_ROUTER_TTL = 300  # refresh every 5 min

_openrouter_cache: list[str] = []


async def _fetch_smart_router_pool(client: httpx.AsyncClient) -> list[str]:
    """Fetch models with smart_router capability from OWU."""
    global _smart_router_cache, _smart_router_cache_ts
    now = time.monotonic()
    if _smart_router_cache and now - _smart_router_cache_ts < _SMART_ROUTER_TTL:
        return _smart_router_cache
    if not OPEN_WEBUI_API_KEY:
        return []
    try:
        r = await client.get(
            f"{OPEN_WEBUI_URL}/api/models",
            headers={"Authorization": f"Bearer {OPEN_WEBUI_API_KEY}"},
            timeout=5.0,
        )
        models = r.json().get("data", [])
        _smart_router_cache = [
            m["id"] for m in models
            if m.get("meta", {}).get("capabilities", {}).get("smart_router")
        ]
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
        if m.get("id") and m["id"] != JEV_MODEL and ":batch" not in m["id"]
    ]
    return _openrouter_cache


async def _fetch_pool(client: httpx.AsyncClient) -> list[str]:
    pool = await _fetch_smart_router_pool(client)
    if pool:
        return pool
    return await _fetch_openrouter_pool(client)


async def laya_pick(messages: list, client: httpx.AsyncClient, pool: list[str] | None = None) -> str:
    if not pool:
        pool = await _fetch_pool(client)
    if not pool:
        raise RuntimeError("Laya pool empty — enable Smart Router on models in OWU or check OPENROUTER_API_KEY")
    smart_pool = await _fetch_smart_router_pool(client)
    shortlist = pool if smart_pool else random.sample(pool, min(6, len(pool)))
    last = messages[-1] if messages else {}
    content = last.get("content", "")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    q = (
        f"Question: Which model best fits this user prompt? "
        f"Options: {', '.join(shortlist)}. Answer only with the exact option name.\n"
        f"Prompt: {str(content)[:2000]}"
    )
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={"model": JEV_MODEL, "messages": [{"role": "user", "content": q}]},
            timeout=10.0,
        )
        ans = r.json()["choices"][0]["message"]["content"].strip()
        return ans if ans in shortlist else shortlist[0]
    except Exception:
        return shortlist[0]
