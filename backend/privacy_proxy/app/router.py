import os
import random
import httpx

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
JEV_MODEL = os.getenv("JEV_ROUTER_MODEL", "typesafe/jev-router")
LAYA_URL = os.getenv("LAYA_URL", "http://laya:8000")

_model_cache: list[str] = []


async def _fetch_pool(client: httpx.AsyncClient) -> list[str]:
    # ponytail: lazy-init cache, refreshed on process restart. Upgrade path: TTL refresh if needed.
    global _model_cache
    if _model_cache:
        return _model_cache
    if not OPENROUTER_KEY:
        return []
    r = await client.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        timeout=10.0,
    )
    data = r.json().get("data", [])
    _model_cache = [m["id"] for m in data if m.get("id") and m["id"] != JEV_MODEL]
    return _model_cache


async def jev_pick(messages: list, client: httpx.AsyncClient) -> str:
    pool = await _fetch_pool(client)
    if not pool:
        raise RuntimeError("OpenRouter model pool empty — check OPENROUTER_API_KEY")
    shortlist = random.sample(pool, min(6, len(pool)))
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


async def laya_pick(messages: list, client: httpx.AsyncClient, pool: list[str] | None = None) -> str:
    if not pool:
        pool = await _fetch_pool(client)
    if not pool:
        raise RuntimeError("Model pool empty — check OPENROUTER_API_KEY or add Smart Router models")
    shortlist = random.sample(pool, min(6, len(pool)))
    last = messages[-1] if messages else {}
    content = last.get("content", "")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    try:
        r = await client.post(
            f"{LAYA_URL}/v1/systemone",
            json={
                "state": str(content)[:2000],
                "questions": {
                    "model": {
                        "type": "choice",
                        "instructions": "Which model best fits this user prompt?",
                        "criteria": {m: m for m in shortlist},
                    }
                },
            },
            timeout=5.0,
        )
        choice = r.json()["answers"]["model"]["choice"]
        return choice if choice in shortlist else shortlist[0]
    except Exception:
        return shortlist[0]


def _demo():
    import asyncio
    async def run():
        async with httpx.AsyncClient() as c:
            pool = await _fetch_pool(c)
            assert len(pool) > 0, "empty pool"
            got = await jev_pick([{"role": "user", "content": "hi"}], c)
            assert got in pool, got
            print(f"ok: pool={len(pool)}, picked={got}")
    asyncio.run(run())


if __name__ == "__main__":
    _demo()
