---
name: coach
description: Use when Ahmed runs /coach or starts a new task without knowing which skill/agent to use. THREE phases — (1) SELF-CHECK all skills/agents/MCPs are 100% functional, (2) ASK Ahmed one question about what he wants to build/fix/audit, (3) ROUTE by recommending the right skill/agent path with reasoning. Reads tasks.md, mission files, and data.md 🎫 for context. Never asks "want me to plan?" — asks WHAT so it can route right. Every recommendation cites the target agent's exact mode/trigger.
---

# coach Skill

> Three phases: **SELF-CHECK → ASK → ROUTE**
> Verify infra is healthy → understand what Ahmed wants → suggest the right tool.

---

## Phase 1 — SELF-CHECK (always first)

Verify the Claude arch is functional before recommending anything.

### 1.1 Skills registered
```bash
ls .claude/skills/*/SKILL.md 2>/dev/null | wc -l
```
Expect ≥ 14. Any skill dir without SKILL.md → broken → flag.

### 1.2 Agents registered
```bash
ls .claude/agents/*.md 2>/dev/null | wc -l
```
Expect ≥ 8. Any `.md` missing frontmatter (`grep -L "^name:" .claude/agents/*.md`) → broken → flag.

### 1.3 MCPs connected
```bash
claude mcp list 2>&1 | grep -E "✓|✗|Needs"
```
Note: which MCPs are ✓ Connected vs ✗ Failed. Never block on failed MCPs — the agents fall back to CLI/paste-mode.

### 1.4 Report health in one block
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Claude arch health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Skills:   N/14 ✓
Agents:   N/8 ✓
MCPs:     N connected / N configured
Broken:   <list — or "none">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If broken items → tell Ahmed which + suggest fix (usually: `rm dir` OR `claude plugin install <name>`). Do not proceed to Phase 2 until acknowledged.

---

## Phase 2 — ASK

If Ahmed's `/coach` message included the task → skip to Phase 3.
Else ask ONE question:

> **What do we want to do?**
> Examples: "add a feature X", "fix bug Y", "plan a pipeline", "review the proxy", "deploy to k8s", "audit the arch", "explain X to a teammate".

Wait for answer. Never guess.

---

## Phase 3 — ROUTE

Read context in parallel:
- `.claude/plan/tasks.md` → in progress / blocked
- `.claude/plan/mission2-k8s.md` → active mission
- `.claude/docs/data.md` 🎫 Tickets + 👥 Team + 💡 Ideas

Match Ahmed's answer against this routing table:

| Ahmed said | Route |
|---|---|
| "plan / spec / design / brainstorm X" | → `planner` agent (BRAINSTORM → SPEC → DESIGN → TASKS) |
| "add a feature / build X / i want to add" | → `planner` QUICK → then `implementer` EXECUTE |
| "implement / code / build the plan" | → `implementer` agent (reads 05-tasks.md) |
| "review / vibe check / write tests / debug / security check / review PR" | → `reviewer` agent (auto-picks mode) |
| **"make a pipeline / CI / workflow / build image / cosign"** | → `infra` agent BUILD mode |
| "deploy / rollout / sync argocd / push to prod" | → `infra` agent DEPLOY mode |
| "why is X crashing / pod failing / CI failing" | → `infra` DIAGNOSE OR `reviewer` DEBUG |
| "migrate docker-compose to k8s" | → `infra` MIGRATE mode |
| "commit / open PR / create issue / post progress" | → `git` skill |
| "fetch this URL / search for X / crawl X / owu docs" | → `web` skill |
| "save this / ingest ticket / remember this" | → `data` skill |
| "audit garnet / find bugs / brilliant ideas" | → `improve` skill |
| "audit .claude / improve arch" | → `improveclaude` skill |
| "3-lens debate / council / decide between X and Y" | → `council` agent |
| "brainstorm ideas across project" | → `creative` agent |
| "logical completeness / all scenarios" | → `logic` agent |
| "vHSM / vault / nitride / attestation / buckypaper" | → `enclaivetech` skill |
| "explain X to a teammate" | → `enclaiveask` skill |
| "explain X to me simply / ELI5" | → `baby-explain` skill |
| "sync docs / update CLAUDE.md" | → `update-project` skill |
| "generate README / network map" | → `readme` OR `network-map` skill |
| "bootstrap arch for a new project" | → `ahmedclaudeskill` agent |

### Output format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: <one line — what Ahmed said>

Route:
1. <skill/agent> — <mode/reason>
2. <skill/agent> — <mode/reason>   (if multi-step)

Model / effort per step:
  Step 1: <model>, <effort>   ← reason
  Step 2: <model>, <effort>   ← reason

Blocking items (from data.md 🎫 / tasks.md):
  <list — or "none">

Start with: "<exact trigger phrase for step 1>"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Model/effort guide
| Step type | Model | Effort |
|---|---|---|
| Planning / architecture / DESIGN mode | opus | max |
| Infra REVIEW / DEPLOY / MIGRATE | sonnet | high |
| Code changes | sonnet | mid |
| Debug / diagnose | sonnet | mid |
| Simple explain / docs | haiku | low |
| Reviewer FULL / SECURITY | opus | high |

---

## Rules

- **Never skip Phase 1.** Even if Ahmed is impatient — 10 sec check now beats routing to a broken skill.
- **One question in Phase 2.** No interrogation.
- **Cite the exact mode** for multi-mode tools (e.g. `infra BUILD`, not just `infra`).
- **Never say "which do you want?"** — coach recommends, Ahmed says yes/no.
- **Flag blocked items** from tasks.md / data.md 🎫 before recommending a next step.

---

## Example

Ahmed: `/coach`
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Claude arch health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Skills:   14/14 ✓
Agents:   8/8 ✓
MCPs:     6 connected / 9 configured (kubernetes/helm/argocd offline — paste-mode OK)
Broken:   none
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What do we want to do?
```

Ahmed: `I want to make a pipeline for the healthdetector image`
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: build a CI pipeline for healthdetector image

Route:
1. infra agent — BUILD mode — writes .github/workflows/build.yml with 4-tag scheme, cosign digest sign, SBOM. Enclaive-org policy blocks actions/checkout → uses git clone.

Model / effort:
  Step 1: sonnet, mid   ← pattern known, no design needed

Blocking items: none.

Start with: "/infra build a CI workflow for healthdetector"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
