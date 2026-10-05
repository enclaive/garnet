# Demo-2 — Client News (Timm Lüders, 2026-09-02 10:26)

## Status of previous fixes
Customer reviewed all T+5 and T+10 documents. **Most prior issues confirmed fixed:**
- JSON / type preservation
- UUID preservation
- Email pseudonymization
- Streaming + structured output assembly
- Byte-exact rehydration
- Residual marker removal

## New blocker — B1 pre-test PERSON edge case

**Input:** `Anna Müller-Öztürk`
**Proxy produced:** `Anna PERSON_a7842989-Öztürk`
**Problem:** Only `Müller` protected. `Anna` and `Öztürk` visible in sealed `pseudonymized_prompt`.

Customer classifies this as **outside** documented known limitations — parts of the identifying PERSON remain unprotected.

**Gate:** exact B1 case must pass with **no visible name component**, before the 10-case Canary runs.

## What customer wants clarified / delivered

1. **Where partial detection fails** — tokenization? NER span selection? normalization? thresholding? span fusion? marker application?
2. **General fix** must handle multipart, Unicode (ü/ö/ß), and hyphenated names
3. **Add `Anna Müller-Öztürk` as permanent regression test**
4. Run it via existing **pre-provider verification** method
5. Confirm fix does not break: streaming, structured output, preserve values, exact rehydration

## Build proof they need
- Commit SHA / Git tag for corrected build
- Immutable image digest
- One request-bound `[→ LLM]` proof that Strict Structured Output actually routes to `/v1/responses` with `reasoning.effort` and `store: false`
- Clarification on `[IN USER]` raw-text logging: diagnostic-only or permanently on? how to disable / verify? can stdout be retained by orchestration/central logging?

## Deadline
**11 September 2026** — ideally with an immutably identified corrected build.

## Artifacts inbound
Timm forwarding the customer ZIP (synthetic test data only) within ~2 hours of the message.

---

## Our next actions (draft — confirm with Seb)
- [ ] Reproduce `Anna Müller-Öztürk` in the repro harness → identify which stage drops `Anna` and `Öztürk`
- [ ] Root cause likely: hyphenated compound tokenization + short-given-name miss (same family as T4D A1 — `de_core_news_md` + GLiNER threshold)
- [ ] Fix at pseudonymizer stage — span fusion for `TOKEN-TOKEN` compounds where either side is PERSON
- [ ] Add `Anna Müller-Öztürk` (+ variants) to `backend/privacy_proxy/tests/test_t4d_repro.py` (or a new `test_b1_repro.py`)
- [ ] Run pre-provider verification (existing method)
- [ ] Regression-check: streaming, structured output, rehydration
- [ ] Tag build, push image, capture digest
- [ ] Produce the `[→ LLM]` proof log line for Strict Structured Output → `/v1/responses`
- [ ] Answer `[IN USER]` logging question — check current log level flags in proxy
