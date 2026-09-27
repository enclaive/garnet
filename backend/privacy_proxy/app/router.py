import os
import random
import httpx

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
JEV_MODEL = os.getenv("JEV_ROUTER_MODEL", "typesafe/jev-router")

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


async def jev_rank(messages: list, client: httpx.AsyncClient) -> list[str]:
    """Return ranked list of models best->worst for OpenRouter fallback chain."""
    pool = await _fetch_pool(client)
    if not pool:
        raise RuntimeError("OpenRouter model pool empty — check OPENROUTER_API_KEY")
    shortlist = random.sample(pool, min(6, len(pool)))
    last = messages[-1] if messages else {}
    content = last.get("content", "")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    q = (
        f"Rank these models best-to-worst for the user's prompt. "
        f"Return ONLY the model names, one per line, no numbering, no commentary.\n"
        f"Models:\n{chr(10).join(shortlist)}\n"
        f"Prompt: {str(content)[:2000]}"
    )
    try:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={"model": JEV_MODEL, "messages": [{"role": "user", "content": q}]},
            timeout=10.0,
        )
        raw = r.json()["choices"][0]["message"]["content"]
        ranked = [ln.strip() for ln in raw.splitlines() if ln.strip() in shortlist]
    except Exception:
        ranked = []
    # append any shortlist entries Jev dropped so the fallback chain is always complete
    return ranked + [m for m in shortlist if m not in ranked]


# kept for callers wanting single pick
async def jev_pick(messages: list, client: httpx.AsyncClient) -> str:
    return (await jev_rank(messages, client))[0]


def _demo():
    import asyncio
    async def run():
        async with httpx.AsyncClient() as c:
            pool = await _fetch_pool(c)
            assert len(pool) > 0, "empty pool"
            ranked = await jev_rank([{"role": "user", "content": "solve x^2+3x+2=0"}], c)
            assert len(ranked) == 6, ranked
            assert all(m in pool for m in ranked)
            print(f"ok: pool={len(pool)}, ranked={ranked}")
    asyncio.run(run())


if __name__ == "__main__":
    _demo()
