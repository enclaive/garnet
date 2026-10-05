# Spec — RAG response-time optimization
Date: 2026-06-09  ·  Author: Ahmed  ·  Status: draft
Feature folder: `.claude/features/2026-06-rag-latency/`

## Problem
When the user asks a question with KB / RAG context enabled, end-to-end response time feels noticeably slower than asking without RAG. The single biggest hit is query expansion (`expand_query` in `backend/privacy_proxy/app/main.py:103`), which adds ~7s/request because it runs a sequential `gpt-4o-mini` call before the main LLM call even starts. On top of that, the in-process retrieval pipeline (BM25 + semantic search → bge-reranker-v2-m3 over top-15 → top-6) runs on local CPU and adds further wall-clock time that the user perceives as "RAG is slow".

## Why now
Own observation while testing RAG queries; Query Expansion parallel exec is already listed as "pending Seb" in `.claude/plan/tasks.md`. Belongs to Mission 1 (RAG quality / UX), independent of Mission 2 (k8s migration) — change is proxy-only and ships through normal CI.

## Users affected
Julia (end user — perceives slow chat) · Alexa (KB tester — slow feedback loop) · Ahmed (dev — slow iteration) · Seb (architecture sign-off on any structural change to the proxy request path).

## Desired behavior
- When RAG context is present, the user sees the first streamed token meaningfully sooner than today.
- Query expansion no longer blocks the main LLM call in a strictly serial fashion — it runs concurrently with work that does not depend on it, or is skipped when it cannot help.
- Reranker / retrieval stage stops being the dominant local-CPU cost on every query.
- The (i) tooltip and the query-expansion toggle keep working; user can still turn expansion off.
- Retrieval quality (which chunks reach the LLM) is at least as good as today on the current KB.

## Out of scope
- Re-indexing the KB with a new embedding model (`text-embedding-3-small` / `nomic-embed-text`) — separate roadmap item, requires reindex.
- Semantic chunking — separate roadmap item.
- Post-retrieval pseudonymization (the architectural limit flagged in `.claude/docs/rag.md`).
- Anything that touches OWU Chroma schema or Alexa's uploaded docs.
- Mission 2 (k8s) — this work ships to the current cVM and is forward-portable.
- Changing the LLM provider used for the main answer.

## Acceptance criteria
- [ ] End-to-end "send question → first streamed token" with RAG enabled is reduced by **≥ X%** vs current baseline on a fixed query set (X = open question for Seb, suggested 40%).
- [ ] Query expansion no longer adds its full wall-clock latency to the critical path (measured: time-to-first-token with expansion ON is within **Y ms** of time-to-first-token with expansion OFF; Y = open question, suggested ≤ 1500 ms).
- [ ] On a fixed eval set of ~10 questions, the set of chunk IDs that survive reranking is **unchanged or a superset** of today's — i.e. no quality regression.
- [ ] Query-expansion toggle in the UI still works; (i) tooltip still shows variants when expansion ran.
- [ ] New log lines let us measure each stage: `[QUERY EXPAND] took Xms`, `[RAG RETRIEVE] took Xms`, `[RERANK] took Xms`.
- [ ] `test_proxy.py` still passes 22/22.
- [ ] No regression when RAG is OFF (non-RAG path latency unchanged).

## Constraints (from Garnet rules)
- Must not remove `body["stream"] = False` on Ollama / non-streaming paths.
- Must not expose `0.0.0.0`.
- Must not log headers.
- Must not log raw user content beyond what is already logged.
- Pseudonymization of user message must still happen before anything leaves the proxy toward the main LLM.
- Seb approval needed? **Yes** — for: (a) running `expand_query` concurrently with the pseudonymization/forwarding pipeline; (b) any change to retriever `top_k` / reranker `top_k`; (c) introducing a cache (in-proc or Redis) for expansion results.

## Open questions
- [ ] Seb: target latency reduction number — is 40% end-to-end / 1500 ms expansion overhead the right bar?
- [ ] Seb: is it acceptable to run `expand_query` concurrently with user-message pseudonymization, then await both before forwarding?
- [ ] Seb: OK to switch the expansion model from `gpt-4o-mini` to a faster small model (e.g. Haiku 4.5) if quality of variants stays comparable?
- [ ] Seb: OK to short-circuit expansion when the question is already long/specific (heuristic: length > N chars OR contains a named entity)?
- [ ] Seb: OK to cache expansion results by `(session_id, question_hash)` for the duration of the chat to avoid re-expanding on follow-ups?
- [ ] Seb: should reranker `top_k=15→6` shrink (e.g. 12→6) to cut CPU time, or is the current setting sacred for recall?
- [ ] Ahmed: where do we run the latency baseline — local laptop hitting cVM, or on the cVM itself? Need a fixed 10-question eval set first.
