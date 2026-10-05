---
name: improve
description: Use when Ahmed says "/improve", "improve project", "improve garnet", "make garnet better", "audit garnet", "brilliant ideas", or "find what to fix in the project". Deep, godmode-planning audit across security, performance/endurance, correctness, DX, and UX. Runs on Opus with max thinking. Reads project state via graphify + real source, produces a dated improvement report in .claude/docs/improvements/ with prioritized, concrete fixes (file:line, why, effort). Never changes code — this skill only plans; Ahmed decides what to build after. For Claude arch improvements (skills/agents/hooks/MCPs/plugins), use improveclaude instead.
---

# improve Skill

> Godmode planner. Reads the **project** (Garnet) end to end and returns a **prioritized improvement report** — security holes, performance bottlenecks, correctness bugs, dead code, DX/UX gaps.
> Read-only. No edits. Ahmed picks what to build after.
> **Scope: garnet source only. For Claude arch → use `improveclaude`.**

---

## Model & effort

- **Model:** Opus 4.7 (`claude-opus-4-7`)
- **Thinking:** max / ultra
- **Effort level:** high

If the current session is not on Opus, tell Ahmed:
> "Switch to Opus for this — `/model` → Opus 4.7. Improve wants deep planning."

Do not run the audit on Sonnet. Explain why once, then wait.

---

## Steps Claude follows

### 1. Read Garnet state

Grounded, in this order:

1. `CLAUDE.md` → what Garnet does, current branch, rules
2. `.claude/plan/tasks.md` and `.claude/plan/mission2-k8s.md` → active work, blockers
3. `graphify query "privacy proxy pseudonymize detect entities session"` → hot path
4. `graphify explain "<god node>"` for each of the top 5 god nodes in `graphify-out/GRAPH_REPORT.md`
5. Only then read specific source files: `backend/privacy_proxy/app/*.py` and the two or three most-connected frontend files.

Do **not** read every file. Trust graphify to scope; read for line numbers when citing a fix.

### 2. Audit across five dimensions

For each dimension, find at least 2 concrete findings. Each finding must include:

- **What** — one sentence
- **Where** — `file:line`
- **Why it matters** — the actual user-visible or security-relevant consequence
- **Fix** — the minimal change (code snippet if under 10 lines)
- **Effort** — S / M / L
- **Priority** — P0 / P1 / P2

Dimensions:

1. **Security** — PII leaks, header logging, secret exposure, weak hashing/tokens, injection surfaces, missing validation on the trust boundary (`/proxy`, `/analyze`, `/vault_scan`).
2. **Performance / endurance** — hot-path allocations, uncached model loads, redundant work, sync blocking calls in async paths, memory growth per session (`MappingStore`), unbounded caches.
3. **Correctness** — token collisions, off-by-ones in position mapping, langdetect fallbacks, streaming boundary bugs, race conditions between depseudo and mapping writes.
4. **DX (developer experience)** — dead code, duplicated logic, missing tests on the privacy hot path, unclear names, silent `except:`, log noise vs signal.
5. **UX** — chat streaming smoothness, error surfacing to the user, feature flags (`x-garnet-queryexpand`), sensitive-file upload feedback, model routing surprises.

### 3. Priority rules

- **P0** — data leak, silent correctness bug on the privacy path, or a fix < 10 lines with > 10× perf impact
- **P1** — significant perf or DX win, no user-visible risk
- **P2** — polish, dead code, style

If you find fewer than 3 P0 items, don't inflate — say so.

### 4. Write the report

Save to:

```
.claude/docs/improvements/YYYY-MM-DD-improve.md
```

Use today's date from the system. If the file already exists for today, append a `-2`, `-3`, etc.

Report template:

```markdown
# Garnet Improve — <YYYY-MM-DD>

Branch: <current branch>
Commit: <short sha>
Scope: <what was audited — e.g. "backend/privacy_proxy/, src/lib/apis/">

---

## TL;DR

<3-5 bullets. Top wins. Total finding count by priority.>

---

## P0 — do these now

### 1. <short title>
- **Where:** `file:line`
- **Why:** <user-visible impact>
- **Fix:**
  ```py
  # minimal patch
  ```
- **Effort:** S

... (each P0)

---

## P1 — worth a sprint

... (each P1, same structure)

---

## P2 — when idle

... (each P2, one-liner is fine)

---

## Skipped / needs Ahmed's call

<anything ambiguous that needs a product decision before it can be fixed>

---

## Verification plan

<how to test that each P0 fix actually improved things — one line each>
```

### 5. Report to Ahmed in chat

After writing the file, in chat:

- One line: "Wrote `.claude/docs/improvements/YYYY-MM-DD-improve.md` — N findings (X P0, Y P1, Z P2)."
- The top 3 P0 titles as bullets.
- One clear next action: "Want me to implement #1?"

Nothing else. No essay. Ahmed reads the file if he wants detail.

---

## Rules

- **Never edit code from this skill.** Plan only. Handoff to `implement-feature` when Ahmed says go.
- **Every finding has a file:line.** No vague "consider refactoring".
- **Cite graphify output, not gut feeling.** If a claim isn't in the graph or the source, drop it.
- **Ponytail applies:** favor the smallest fix that works. If a P0 finding needs 200 lines, split it into "quick guard now" + "proper fix later" and label both.
- **Don't repeat past reports.** Before writing, glance at the two most recent files in `.claude/docs/improvements/` — if a finding was already reported and not fixed, mark it `[carryover]` and move on. If it was fixed, don't re-report it.

---

## Example finding (calibration)

```markdown
### 1. build_analyzer() rebuilt on every request
- **Where:** `backend/privacy_proxy/app/pseudonymizer.py:139`
- **Why:** spaCy model reload on every message. ~200-500ms added latency per chat turn. User-visible slowness.
- **Fix:**
  ```py
  from functools import lru_cache

  @lru_cache(maxsize=2)
  def build_analyzer(language: str) -> AnalyzerEngine:
      ...
  ```
- **Effort:** S
- **Priority:** P0
```

That level of specificity is the bar. Nothing softer.
