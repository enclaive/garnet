---
STATUS: reviewed
HANDOFF: planner
NEXT: proceed to 03-design.md
---

# Spec review — Full History Pseudonymization
Date: 2026-07-12
Reviewer: planner self-review (7-criterion rubric)

## Score: 9/10

## Criterion checks
1. **Problem clear** — YES. Concrete leak path traced turn-by-turn, exact
   line range named (402-411). +1
2. **Success measurable** — YES. "grep plaintext name in outbound body",
   "same token across turns", "spaCy runs once per unique text". Every
   criterion is runnable. +1
3. **Scope tight** — YES. Explicit out-of-scope list covers: depseudo,
   RAG, streaming, persistence, metrics, deps. +1
4. **Constraints listed** — YES. All garnet rules named, Seb-approval
   decision explicit ("not required, here's why"). +1
5. **Trade-offs shown** — PARTIAL. Cache key trade-off called out. Missing:
   memory cost of the cache in worst case (very long chat, many unique
   messages). Design must address. -0.5
6. **Rollback exists** — IMPLICIT. Single-file change, revert commit works.
   Should still be one line in design. -0.5
7. **Handoff clean** — YES. Implementer knows exact file, exact lines,
   exact call signatures, cache location. +1

## Strengths
- Names the exact block that must be replaced (402-411) — no ambiguity.
- Distinguishes cache scope (per-session) from key derivation cleanly.
- Notes the assistant-token no-op assumption and flags it for verification
  instead of hand-waving.

## Gaps to fix in design
- Address worst-case cache memory. Cap or acknowledge unbounded growth is
  fine because TTL evicts and typical chat has <100 unique messages.
- One-line rollback plan.
- Decide: does the cache live inside `MappingStore` or as a sibling dict
  in `main.py`? (Prefer sibling — smaller diff, `MappingStore` is shared
  code, ponytail says don't touch it if a local dict works.)

## Suggested next
Proceed to design. All gaps are small and addressable in the design
document — no need to redo the spec.
