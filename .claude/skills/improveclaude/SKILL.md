---
name: improveclaude
description: Use when Ahmed says "/improveclaude", "improve claude", "improve claude arch", "improve my claude setup", "what MCP/hook/skill/plugin should I add", "audit .claude", or "improve claude arch". Deep, godmode audit of the CLAUDE ARCHITECTURE ONLY — skills, agents, hooks, MCPs, plugins, marketplaces. Runs on Opus with high thinking. MANDATORY steps: (1) invoke claude-code-setup:claude-automation-recommender plugin, (2) scan installed marketplaces live, (3) WebSearch fresh plugins/MCPs from anthropics/claude-plugins-official, awesome-claude-code, wshobson/agents, modelcontextprotocol/servers. Produces a dated report at .claude/improve/YYYY-MM-DD-improveclaude.md with top MCPs, skills, hooks, plugins to add + redundancies to prune. READ-ONLY. Never edits code or skill files. For project (garnet source) improvements, use improve instead.
---

# improveclaude Skill

> Godmode auditor for the **Claude architecture** (this repo's `.claude/` + installed plugins + MCPs + hooks).
> Read-only. No edits. Ahmed picks what to install after.
> **Scope: Claude setup only. For garnet source improvements → use `improve`.**

---

## Model & effort

- **Model:** Opus 4.7 (`claude-opus-4-7`)
- **Thinking:** high (or max if user opts in)
- **Effort level:** xhigh

If session is not on Opus, tell Ahmed:
> "Switch to Opus for this — `/model` → Opus 4.7. improveclaude wants deep planning."

Do not run on Sonnet. Explain once, wait.

---

## Mandatory pre-audit steps

You MUST do these three things before writing any recommendation. Skipping any = invalid report.

### Step 1 — Invoke `claude-code-setup:claude-automation-recommender`

Call the skill via the Skill tool:

```
Skill(claude-code-setup:claude-automation-recommender,
      args="Analyze /home/ahmedmarz/Desktop/garnet — recommend improvements to the existing Claude Code arch. Focus on what's MISSING or REDUNDANT.")
```

Capture the recommender's output verbatim in the report under "Recommender pass".

### Step 2 — Live scan of installed marketplaces + plugins + hooks

```bash
ls ~/.claude/plugins/marketplaces/                     # marketplaces added
ls ~/.claude/plugins/marketplaces/*/plugins/           # plugins per marketplace
ls ~/.claude/plugins/marketplaces/*/external_plugins/  # external (MCP) plugins
cat ~/.claude/plugins/installed_plugins.json           # what's already installed
ls .claude/skills                                       # project skills
ls .claude/agents                                       # project agents
cat .claude/settings.json .claude/settings.local.json  # hooks + MCPs enabled
```

Every recommendation MUST be checked against this real state. Never suggest installing something already installed.

### Step 3 — WebSearch fresh options

Run at least these searches (adjust query for garnet's real stack: FastAPI + Svelte + Docker→k8s + Harbor + Presidio):

- `site:github.com awesome-claude-code 2026`
- `site:github.com claude-code plugins marketplace 2026`
- `site:github.com claude-code subagents 2026`
- `modelcontextprotocol servers 2026`
- `claude code hooks best practices 2026`
- One stack-specific: `claude code MCP FastAPI Svelte security 2026`

Cite the URLs you actually found. Do NOT invent plugin names.

Optionally WebFetch:
- `https://github.com/anthropics/claude-plugins-official`
- `https://github.com/hesreallyhim/awesome-claude-code`
- `https://github.com/wshobson/agents`
- `https://github.com/VoltAgent/awesome-claude-code-subagents`
- `https://github.com/modelcontextprotocol/servers`

---

## Audit dimensions

For each of the five below, produce concrete findings with **name, source, why (garnet-specific), install command, effort**.

1. **MCPs to add** — external tool integrations that fill a real gap (docs lookup, error tracking, DB, etc.)
2. **Skills to add** — new capabilities not covered by existing skills
3. **Hooks to add** — automation on tool events (format, block secret edits, run tests). Garnet has 2 hooks (both graphify) — usually the biggest gap.
4. **Plugins to add** — packaged bundles beyond superpowers/ponytail
5. **Redundancies to prune** — overlapping skills/agents/plugins. Cite the specific overlap with paths.

Every finding must include:
- **What** — one sentence
- **Source** — `plugin@marketplace` or GitHub URL
- **Why for garnet** — specific gap it fills (privacy proxy? Svelte fork? k8s migration? Harbor? Presidio?)
- **Install** — exact command
- **Effort** — S / M / L
- **Priority** — P0 / P1 / P2

Priority rules:
- **P0** — closes a real risk (unenforced secret rule, missing PR review on proxy) or unblocks in-progress work (k8s migration)
- **P1** — significant DX win, no risk
- **P2** — nice-to-have

---

## Report

Save to:

```
.claude/improve/YYYY-MM-DD-improveclaude.md
```

Use today's date from system clock. If file exists for today, append `-2`, `-3`.

Template:

```markdown
# Claude Arch Improve — <YYYY-MM-DD>

Session model: <opus/sonnet>
Branch: <current branch>
Current arch: <N skills, M agents, K plugins, L MCPs, H hooks>

---

## TL;DR

<3-5 bullets. Top wins. Total finding count by priority.>

---

## Recommender pass (from claude-code-setup)

<verbatim top picks from claude-automation-recommender>

---

## Live state

- Marketplaces: <list>
- Installed plugins: <list from installed_plugins.json>
- Enabled MCPs: <from settings.local.json>
- Hooks configured: <from settings.json>
- Skills: <count + list>
- Agents: <count + list>

---

## P0 — install now

### 1. <plugin/mcp/hook/skill name>
- **What:** <one line>
- **Source:** `plugin@marketplace` or URL
- **Why for garnet:** <specific gap>
- **Install:** `claude plugin install ...` or config snippet
- **Effort:** S

... (each P0)

---

## P1 — worth a sprint

... (each P1)

---

## P2 — when idle

... (each P2, one-liner)

---

## Redundancies to prune

| Overlap | Keep | Delete/merge | Why |
|---|---|---|---|
| ... | ... | ... | ... |

---

## Fresh finds from the internet

| Source | Item | Why interesting |
|---|---|---|
| github.com/... | ... | ... |

---

## Skipped / needs Ahmed's call

<anything ambiguous — e.g. "Sentry MCP: only useful if you already run Sentry">

---

## Verification plan

<how to sanity-check each P0 after install — one line each>
```

---

## Report to Ahmed in chat

After writing the file, in chat print:

- One line: "Wrote `.claude/improve/<date>-improveclaude.md` — N findings (X P0, Y P1, Z P2)."
- The top 3 P0 titles as bullets.
- One clear next action: "Want me to install #1?"

Nothing else.

---

## Rules

- **Read-only.** Never install, never edit skills/agents/settings. Report only.
- **No fabrication.** If a plugin isn't in a real marketplace or GitHub search result, don't list it.
- **Cite sources.** Every fresh find gets a URL.
- **Garnet-specific.** Every "why" must reference actual garnet stack (privacy proxy, Svelte, Docker→k8s, Harbor, Presidio, litellm). Generic reasons get cut.
- **Redundancy first.** Before recommending anything new, list what to prune. New stuff on top of bloat = more bloat.
- **Ponytail applies.** Prefer 1 plugin that covers 3 gaps over 3 plugins each covering 1.
- **Don't repeat past reports.** Glance at last 2 files in `.claude/improve/` — mark carryover items `[carryover]`, drop fixed ones.

---

## Example finding (calibration)

```markdown
### 1. hookify plugin
- **What:** Skill for writing/generating Claude Code hooks
- **Source:** `hookify@claude-plugins-official`
- **Why for garnet:** You have 2 hooks total (both graphify enforcement). CLAUDE.md rules "NEVER commit cosign.key/.env" and "verify fix in running container" are enforced by memory only. Hookify authors these hooks properly.
- **Install:** `claude plugin install hookify@claude-plugins-official`
- **Effort:** S
- **Priority:** P0
```

That's the bar. Nothing softer.
