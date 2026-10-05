# Data — BRIEF (curator agent auto-updates)

_Last curator refresh: 2026-07-25 (tickets updated)_
_Owner: `curator` agent · Writer: `/data` skill · Consumers: all agents_

> **This file is a 30-second snapshot for other agents.**
> Full entries live in `.claude/docs/data/{tickets,team,docs,images,ideas,config}.md`.
> Agents needing depth: call `curator` agent (QUERY mode) — do NOT grep the section files directly.

---

## Snapshot

| Section | File | Latest entry | Count |
|---|---|---|---|
| 🎫 Tickets | [data/tickets.md](./data/tickets.md) | 2026-07-25 — garnet-i-button — (i) hover shows pseudonymized prompt | 5 |
| 👥 Team notes | [data/team.md](./data/team.md) | 2026-07-21 — Seb — demo-1.garnet.enclaive.cloud customer demo, ahmed.marz owns tests | 1 |
| 📚 Referenced docs | [data/docs.md](./data/docs.md) | 2026-07-25 — Seb/project-spec — Full pseudonymization architecture spec | 2 |
| 🖼️ Images | [data/images.md](./data/images.md) | _none_ | 0 |
| 💡 Ideas & decisions | [data/ideas.md](./data/ideas.md) | 2026-07-09 — idea — API key in Settings/Account for 3rd-party extensions | 1 |
| 🔧 Config / API notes | [data/config.md](./data/config.md) | _none_ | 0 |

**Active hot items to remember:**
- 👥 Seb needs demo-1.garnet.enclaive.cloud tested by ahmed.marz (privacy proxy + search + speed) — 2026-07-21
- 🎫 5 open tickets — biggest: garnet-owu-sync (1822 commits behind OWU, target v0.92)
- 🎫 garnet-cursor-scan + garnet-i-button — user-visible privacy UX (relevant to demo1)
- 🎫 garnet-helm-backend — meta chart Ollama↔vLLM (post-demo scope)
- 💡 Open idea: API key in Settings/Account (may be blocker for BYOK API story)

---

## How to consume

**Other agents / skills:**
- Load THIS file for context (30 lines, always current).
- For depth on any entry → `Agent(subagent_type: "curator", prompt: "QUERY: <question>")`.
- Never load section files directly — curator owns them.

**Ahmed:**
- Add anything → `/data <paste>` (skill classifies + appends to right section file, then curator refreshes this brief).
- Query anything → `curator` agent, or just ask normally — coach will route.

---

## Rules (enforced by curator)

- 6 fixed sections, never renamed, never added
- Append-only (never overwrites, never deletes user content)
- Auto-tidy triggers when any section file > 500 lines: keep newest 10, condense older to one-liners
- This brief refreshes every time `/data` writes or curator runs any mode
