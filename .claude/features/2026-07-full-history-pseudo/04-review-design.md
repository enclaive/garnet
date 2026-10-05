---
STATUS: reviewed
HANDOFF: planner
NEXT: proceed to 05-tasks.md
---

# Design review — Full History Pseudonymization
Date: 2026-07-12
Reviewer: planner self-review (7-criterion rubric)

## Score: 9/10

## Criterion checks
1. **Problem clear** — YES (inherited from spec, restated in arch summary).
2. **Success measurable** — YES. Each phase has an observable outcome.
3. **Scope tight** — YES. Four phases, all in one file, phase 4 is
   explicitly a "no code" phase (comment only). Nothing gold-plated.
4. **Constraints listed** — YES. Ponytail applied explicitly at 3 decision
   points (rung 1, rung 2, rung 7). `body["stream"]` untouched, no new dep.
5. **Trade-offs shown** — YES. Five trade-offs documented with the
   discarded option and why.
6. **Rollback exists** — YES. One-line revert, deployment path named.
7. **Handoff clean** — YES. Implementer has line numbers, call signatures,
   the assumption to verify, and a decision tree if the assumption fails.

## Strengths
- Correctly identified the old depseudo loop as the leak, not just a
  missing pseudo call — this is the root cause fix, not a symptom patch.
- Phase 3 (route last message through cache) is optional but included
  because the cost is one line and the benefit is real on
  edit/regenerate.
- Phase 4 explicitly deferred with a `ponytail:` comment — no invisible
  debt.
- Named the risky assumption (spaCy behavior on already-tokenized text)
  and gave the fallback (regex short-circuit) in the same table.

## Gaps
- Assumption about spaCy on tokenized text is a runtime risk. Task list
  MUST include an assert-level check for this before the multi-turn test
  passes. -0.5
- No explicit statement on ordering vs. the RAG/file-scan loop that also
  iterates `messages` (starts around line 460 in the last-message block).
  We must confirm our new loop runs BEFORE the RAG detection or the RAG
  detection reads already-pseudonymized `<context>` markers. **Answer:**
  RAG detection scans for literal `<context>` / `<source` — those aren't
  PII, `pseudonymize` won't touch them. Safe. Add a comment in the loop
  to that effect. -0.5

## Suggested next
Proceed to 05-tasks.md. Both gaps translate into concrete tasks (one
verification test, one code comment).
