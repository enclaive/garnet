---
name: baby-explain
description: Use when Ahmed says "explain easily", "baby mode", "ELI5", "explain X simply", "i don't get X". Reads any feature/plan/spec file and outputs a simple human explanation with all tasks, jobs and why — saved to .claude/explanations/. Includes generation date/time.
---

# baby-explain Skill

> Use when Ahmed says "explain easily", "baby mode", "ELI5", "explain X simply", "i don't get X".
> Takes any feature/plan/spec file → outputs simple explanation + all tasks + why each one.
> No technical jargon. No fluff. Like explaining to a smart friend who doesn't code.

---

## When to trigger

Phrases: "explain easily", "baby mode", "ELI5", "explain X simply", "baby explain X", "i don't get X"

---

## Steps Claude follows

### 1. Find input file
Check in order:
1. Ahmed named a feature → `.claude/features/<name>/feature-<name>.md` + `05-tasks.md`
2. Ahmed said "the plan" → `.claude/plan/tasks.md`
3. Ahmed said "mission" → `.claude/plan/mission.md`
4. Ahmed said "the spec" → latest `01-spec.md` in features/
5. Ambiguous → ask: "which feature or plan to explain?"

### 2. Read ALL files in that feature folder
Read every file present: feature-*.md, 01-spec.md, 03-design.md, 05-tasks.md, plan.md, 06-build.md.
More context = better explanation.

### 3. Output format (strict)

```markdown
# 🍼 Baby Explain — <feature name>

**Generated:** <YYYY-MM-DD HH:MM:SS>

## What is this feature?
2-3 sentences. What it does for the user. No code words.
Example: "This adds a map that shows you all the private info
Garnet found in your chat, and draws lines between info
that appeared together — so you can SEE what was protected."

## Why are we building it?
1-2 sentences. The real reason. User problem it solves.

## How does it work? (simple version)
Step by step, like a story:
1. User sends a message → Garnet finds private info (names, emails...)
2. Those become dots on a map
3. If two private things were in the same message → a line connects them
4. User opens map → sees exactly what Garnet protected

## The jobs (what needs to be built)

### Job 1 — <name in plain words>
**What:** what gets built, in plain words
**Why:** why this job exists, what breaks without it
**Who does it:** Ahmed / Claude Code / Ion / Nicu
**Hard part:** the tricky bit (one line, simple)

### Job 2 — ...

## What could go wrong?
Simple list of risks in plain words:
- "if Svelte doesn't detect the new message, graph won't update"
  → fix: use spread operator { ...message }
- ...

## What does success look like?
Exactly what Ahmed sees/does to confirm it works:
- "send a message with a name → graph icon appears in navbar"
- "open graph → see colored dots connected by lines"
- "press Escape → modal closes"

## Who needs to approve?
Seb: Y/N — why
Ion: Y/N — why
Nicu: Y/N — why

## One line summary
<feature in one sentence a non-technical person understands>
```

### 4. Save file
Save to: `.claude/explanations/<feature-name>-explanation.md`
Tell Ahmed: "Saved to .claude/explanations/<name>-explanation.md (generated <date> <time>)"

---

## Rules

- **Generated date/time is mandatory** — first line of the output, right
  under the title. Use the actual current date and time, format
  `YYYY-MM-DD HH:MM:SS`.
- Zero jargon. If a technical word is unavoidable → explain it in brackets.
  Example: "Svelte (the tool that builds the chat interface)"
- Every job gets a WHY. Never skip it.
- "Hard part" must be honest — not "it's complex", but the specific real challenge.
- Risks in plain words — not "Svelte reactivity issue" but "the map might not update when new messages arrive"
- Success criteria = what Ahmed physically sees/clicks/reads to confirm it works
- Max reading level: smart 16-year-old with no coding background
- **If re-running on same feature** → overwrite the file (this is a snapshot
  explanation, not a history log) but update the Generated timestamp to
  reflect the new run.