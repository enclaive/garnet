---
name: data
description: Use when Ahmed says "/data", "add to data", "data: <paste>", "save this for context", "remember this", "ingest ticket X", "save teammate note", "save doc", "save this image ref", or wants to persist any external context (tickets, team notes from Seb/Ion/Nicu/Ahmed B, referenced docs, image paths, ideas, config snippets) that ALL agents should later know. THIN WRITE ENTRY — delegates to `curator` agent (WRITE mode) which classifies input into 1 of 6 fixed section files under .claude/docs/data/, appends dated entry, refreshes .claude/docs/data.md brief, auto-tidies any section > 500 lines. Never overwrites, always appends. Never deletes user content.
---

# data Skill — write entry to the curator

> Files: `.claude/docs/data.md` (brief) + `.claude/docs/data/{tickets,team,docs,images,ideas,config}.md` (sections)
> Writer: this skill (Ahmed's fast trigger) → delegates to `curator` agent WRITE mode
> Readers: every agent, every skill — via `curator` agent (never direct grep)
> Six fixed sections. Auto-tidy at 500 lines per section.

---

## How this works now

`/data` is the fast trigger Ahmed types. It CLASSIFIES the input inline (Step 1 below) and then calls the `curator` agent to execute the WRITE. The curator owns the files, refreshes the brief, and reports back. Ahmed's UX is unchanged.

For QUERY / BRIEF / HYDRATE / TIDY on stored context → call the `curator` agent directly, not this skill.

---

## When to trigger

Ahmed says:
- "/data" / "add to data" / "data: <paste>"
- "save this for context" / "remember this"
- "ingest ticket <ref>" / "save the ticket <ref>"
- "save teammate note" / "seb said ..." / "ion told me ..."
- "save this doc" / "reference this"
- "save image ref" / "add screenshot ref"
- "add this idea" / "note this decision"
- "save this config" / "note this API"

---

## The files

Brief: `.claude/docs/data.md` (30-line snapshot — refreshed after every write)

Six section files (never rename, never add new):

| # | Section | Icon | File | For |
|---|---|---|---|---|
| 1 | Tickets | 🎫 | `.claude/docs/data/tickets.md` | GitHub issues, Linear tasks, JIRA tickets |
| 2 | Team notes | 👥 | `.claude/docs/data/team.md` | Instructions/notes from Seb, Ion, Nicu, Ahmed B, Alexa, Julia |
| 3 | Referenced docs | 📚 | `.claude/docs/data/docs.md` | Pasted external docs, RFCs, spec extracts |
| 4 | Images / screenshots | 🖼️ | `.claude/docs/data/images.md` | Diagram paths + what they show |
| 5 | Ideas & decisions | 💡 | `.claude/docs/data/ideas.md` | Not-yet-features + team decisions |
| 6 | Config / API notes | 🔧 | `.claude/docs/data/config.md` | Model IDs, endpoints, env vars, API quirks |

---

## Steps

### Step 1 — Classify the input

Look at the pasted content. Pick 1 of 6 sections:

| Signal | Section |
|---|---|
| GitHub URL, "issue #", "PR #", ticket ref, acceptance criteria language | 🎫 Tickets |
| Person name (Seb/Ion/Nicu/Ahmed B/Alexa/Julia/Sebastian) + instruction/opinion | 👥 Team notes |
| URL to external docs, RFC number, "https://docs...", pasted API reference | 📚 Referenced docs |
| Image path, "screenshot", `.png` / `.jpg`, "see attached", diagram reference | 🖼️ Images |
| "I want to ...", "we should ...", "decided to ...", "brainstorm ...", not tied to a ticket | 💡 Ideas & decisions |
| Model IDs (claude-*, gpt-*), env var, endpoint URL, config key, API quirk | 🔧 Config / API |

**If ambiguous → ask ONE question:**

```
Which section?
[1] 🎫 Tickets
[2] 👥 Team notes
[3] 📚 Referenced docs
[4] 🖼️ Images
[5] 💡 Ideas & decisions
[6] 🔧 Config / API notes
```

Wait for number.

### Step 2 — Extract metadata

From the content, derive:
- **Date:** today's system date (YYYY-MM-DD)
- **Ref / person / source:** the primary identifier
  - Tickets → ticket number or title
  - Team → person's name
  - Docs → source (e.g. "enclaive.cloud/docs")
  - Images → filename or slug
  - Ideas → auto slug from first sentence
  - Config → target (e.g. "Groq", "OLLAMA_URL")
- **One-line summary:** ≤ 80 chars, human-readable

### Step 3 — Append the entry to the section file

Open the matching section file (e.g. `.claude/docs/data/team.md` for 👥).

Format:

```markdown
### YYYY-MM-DD — <ref/person/source> — <one-line summary>

<the actual content, preserved verbatim — code blocks kept, quotes kept>

<optional: `Cited by: <where Ahmed found it>` if given>
```

Append IMMEDIATELY UNDER the top comment/format line, ABOVE any `_none yet_` placeholder (which you delete on first real entry).

Preserve chronological order — newest at the top of the section file.

### Step 4 — Refresh the brief

Update `.claude/docs/data.md`:
- Change `_Last curator refresh: <date>_` to today.
- Update the snapshot table row for the touched section: latest entry summary + count.
- If the new entry is high-signal (from Seb, or an active ticket, or a decision), add it to the "Active hot items" list (max 5 items).

### Step 5 — Check tidy threshold

```bash
wc -l .claude/docs/data/<touched_section>.md
```

If > 500 lines → run auto-tidy (Step 6) on THAT section only.
Else → done.

### Step 6 — Auto-tidy (only when a section > 500 lines)

For the section file that crossed 500:
1. Keep the last 10 entries verbatim
2. For older entries: replace with a one-line summary format:
   ```
   ### <date> — <ref> — <summary> _(condensed)_
   ```
3. Preserve the condensed summaries chronologically at the bottom of the section file

**Never delete a user entry outright. Only compress old ones.**

After tidy, add a comment at the top of the section file:

```markdown
_Tidied YYYY-MM-DD — <N> old entries condensed_
```

For deeper multi-section tidy or scheduled cleanup → delegate to `curator` agent (TIDY mode).

### Step 7 — Report

```
✅ Added to <icon> <section name>
Section file: .claude/docs/data/<section>.md
Entry: <date> — <ref> — <summary>
Brief refreshed: .claude/docs/data.md
Section size: <N> lines (tidy at 500)
```

---

## Rules

- **Never overwrite.** Always append. `str_replace` on the placeholder `_none yet_` for first entry.
- **Never rename sections.** Six is the schema. If Ahmed wants a new section, tell him — don't invent.
- **Never delete entries.** Auto-tidy compresses, never removes.
- **Preserve content verbatim.** If Ahmed pasted code, keep the code block. If he pasted a quote, keep the quote.
- **One entry per invocation.** If Ahmed pastes 3 things, ask if they should be 3 entries or 1.
- **Never post to external systems.** No GitHub API calls, no Slack, no email. Local file only.
- **Never load or interpret images.** If Ahmed adds an image ref, store the path + description. Don't OCR or analyze.

---

## Boundary vs adjacent tools

| Tool | Does what | data does what |
|---|---|---|
| `update-github-ticket` | Tracks progress vs current ticket, writes ticket-update.md | Stores ticket text/context for agents to read |
| `clean-comments` | Tidies comments.md (progress log) | Different file — data.md self-tidies |
| `enclaivetech` / `owudocs` | Fetch external docs live via WebFetch | Stores pasted external content locally |
| `enclaiveask` | Answers teammate questions in plain language | Stores teammate notes for that answer to draw from |
| `previous-step` | Session snapshot + commit | Not related — data.md persists between sessions |

No overlap with any existing tool.

---

## Consumers (via curator, not direct read)

Other agents MUST NOT grep the section files directly. Route through `curator` agent:

| Consumer | Call | Curator mode |
|---|---|---|
| reviewer | `Agent(subagent_type: "curator", prompt: "BRIEF for reviewer")` | BRIEF |
| planner | `Agent(subagent_type: "curator", prompt: "BRIEF for planner")` | BRIEF |
| implementer | `Agent(subagent_type: "curator", prompt: "BRIEF for implementer")` | BRIEF |
| infra | `Agent(subagent_type: "curator", prompt: "BRIEF for infra")` | BRIEF |
| coach | `Agent(subagent_type: "curator", prompt: "BRIEF")` | BRIEF |
| Any agent needing a specific fact | `Agent(subagent_type: "curator", prompt: "QUERY: <question>")` | QUERY |

The 30-line brief at `.claude/docs/data.md` is safe to load directly for a snapshot.
Depth (a specific entry, live ticket status, all Seb notes) → curator.

---

## Example — ingesting a Seb approval

Ahmed: "data: seb approved the vllm migration, said we should keep ollama fallback for 2 weeks"

```
Mode: DATA · classify

Section: 👥 Team notes (person = Seb + instruction)

Adding:

### 2026-07-07 — Seb — vLLM migration approved, keep Ollama fallback 2 weeks

seb approved the vllm migration, said we should keep ollama fallback for 2 weeks

File: .claude/docs/data.md now at 47 lines.
```

---

## Example — ingesting a ticket

Ahmed: "/data #47 https://github.com/enclaive/garnet/issues/47 — add prometheus metrics for PII"

```
Mode: DATA · classify

Section: 🎫 Tickets (URL + issue #)

Ref: #47
Summary: add prometheus metrics for PII

Adding:

### 2026-07-07 — #47 — add prometheus metrics for PII

https://github.com/enclaive/garnet/issues/47

<full ticket body if Ahmed pastes it>

File: .claude/docs/data.md now at 53 lines.
```

---

## Example — ambiguous input

Ahmed: "data: OLLAMA_URL should be http://ollama:11434, not localhost"

```
Mode: DATA · classify

Ambiguous — could be config (🔧) or a team decision (💡).

Which section?
[5] 💡 Ideas & decisions
[6] 🔧 Config / API notes
```

Ahmed picks. Skill adds under chosen section.
