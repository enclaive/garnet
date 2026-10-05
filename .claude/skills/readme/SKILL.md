---
name: readme
description: Use when Ahmed says "generate readme", "update readme", "write README for X". Reads CLAUDE.md + docs + docker-compose to generate an accurate, developer-facing README.md. Writes to project root. Never invents details.
---

# readme Skill

> Generate or update the project README.md from real project files.
> Never invents — only writes what's in the code/config.

---

## Steps Claude follows

### 1. Read project reality
In parallel:
- `CLAUDE.md` → project description + architecture
- `docker-compose.yml` → services + ports
- `.env` → env vars needed
- `.claude/docs/deploy.md` → deploy sequence
- `.claude/docs/localdev.md` → local setup
- `README.md` if exists → don't lose existing content

### 2. Ask scope
```
Generate full README or update specific section?
- Full README (replaces existing)
- Update: Architecture / Setup / Deploy / API / Contributing
```

### 3. Generate README

Structure:
```markdown
# Garnet — Privacy-Preserving AI Chat

> One-line description

## What it does
<from CLAUDE.md — plain language>

## Architecture
<ASCII diagram from CLAUDE.md>

## Services
| Service | Image | Purpose |
|---------|-------|---------|
<from docker-compose>

## Setup
### Prerequisites
<from localdev.md>

### Environment variables
| Variable | Required | Description |
|----------|----------|-------------|
<from .env>

### Run
<from deploy.md>

## Development
<from localdev.md>

## Deploy
<from deploy.md — production commands>

## Security
<key rules from security.md — non-technical summary>
```

### 4. Check with Ahmed before writing
Show the README preview. Ask: "Write to README.md? (y/n)"

### 5. Write only if approved

---

## Rules
- Never invent API keys, ports, or service names.
- Source everything from actual files.
- Keep it developer-facing — not marketing.
- If README.md exists → show diff of what changes, not full replacement.
- Max 150 lines — if longer, ask Ahmed what to cut.
