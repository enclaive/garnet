---
name: update-project
description: Use when Ahmed says "update project", "sync docs", "update claude files". Asks about chat context first, then diffs .claude/ against reality and makes surgical updates. Never overwrites, only str_replace. Flags orphan docs.
---

# update-project Skill

> Syncs .claude/ docs against the actual codebase state.
> Surgical edits only — never full overwrites.

---

## Steps Claude follows

### 1. Ask context first (mandatory)
Before reading anything:
```
What changed since last update?
- New features added?
- Files moved/renamed?
- New env vars / services?
- Rules changed?
```

### 2. Read current state
In parallel:
- `CLAUDE.md` → current router
- `.claude/plan/tasks.md` → current work
- `.claude/docs/` → all doc files
- `docker-compose.yml` → services (might have changed)
- `.env` → env vars

### 3. Diff against reality
Check for drift:
- New files in proxy/webui not documented in `proxy.md` / `webui.md`
- New env vars not in `deploy.md`
- Services in docker-compose not in `debug.md`
- New common failures discovered but not in `debug.md` table
- CLAUDE.md Load table missing new doc files

### 4. Output drift report
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DRIFT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Outdated:
- <file>: <what's wrong>

Missing:
- <doc>: <what to add>

Orphan files (in .claude/ but not referenced):
- <file>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fix these? (y/n per item)
```

### 5. Apply approved fixes
Use str_replace only — never rewrite whole files.
One change at a time. Confirm each before next.

---

## Rules
- ALWAYS ask context before reading.
- str_replace only — no full file rewrites.
- Never touch skill files (those are maintained separately).
- Flag but don't auto-delete orphan files — Ahmed decides.
- Update CLAUDE.md Load table if new doc files added.
