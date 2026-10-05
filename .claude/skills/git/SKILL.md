---
name: git
description: Use when Ahmed says "/git", "/gitwork", "/previous-step", "/updategithubticket", "git status", "what's on the branch", "what's changed", "commit", "commit + push", "wrap what we did", "snapshot", "open PR", "/pr", "create pull request", "create issue", "new issue", "search issue", "post ticket comment", or "post progress to GH". Absorbs gitwork + previous-step + update-github-ticket. Six modes auto-selected by prompt intent: VIEW (read-only status/log/PRs), SNAPSHOT (session summary), COMMIT (stage+commit+push with 3-choice confirm), PR (draft + gh pr create), ISSUE (create/edit/search issues), POST (read data.md 🎫 → draft GH comment → confirm → post). Uses GitHub MCP + gh CLI + git CLI. Reads tickets FROM .claude/docs/data.md 🎫 section — never duplicates ticket data. Falls back to paste-mode if gh auth fails.
---

# git Skill — the git/GitHub pillar in one skill

> ONE skill for anything git or GitHub.
> Absorbs gitwork + previous-step + update-github-ticket.
> Six modes. Reads tickets from `data.md` (never duplicates).

---

## Mode selector — read prompt intent FIRST

State the mode at the top of every reply: `Mode: GIT · <MODE>`.

| Prompt shape | Mode |
|---|---|
| "git status" · "/gitwork" · "what's on branch" · "what's changed" · "diff" | **VIEW** |
| "/previous-step" · "wrap what we did" · "snapshot" · "session summary" | **SNAPSHOT** |
| "commit" · "commit + push" · "save progress" | **COMMIT** |
| "open PR" · "/pr" · "create pull request" · "make a PR" | **PR** |
| "create issue" · "new issue" · "search issue" · "/issue" | **ISSUE** |
| "post ticket comment" · "/updategithubticket" · "post progress to GH" | **POST** |

Ambiguous → ask ONE question then pick.

---

## Universal rules (all modes)

- **State the mode** at the top of every reply.
- **Read CLAUDE.md + `.claude/docs/data.md`** for context (tickets in 🎫 section).
- **Never overwrite `data.md`** — that's the `data` skill's job. Read-only from here.
- **Never push without confirmation** — 3-choice on any write to remote.
- **Never edit code files** — this skill is git/GH ops only.
- **Never post to GitHub silently** — always show draft + confirm.
- **Falls back to paste-mode** if `gh auth status` fails: ask Ahmed to paste output.
- **Auto-detect repo** from `git remote -v` — never hardcode paths.

---

## Mode 1 — VIEW (read-only)

### Steps

Run in parallel:
```bash
git status --short
git log --oneline -10
git diff --stat HEAD
git branch -v
git log origin/$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')..HEAD --oneline 2>/dev/null
gh pr list --state open 2>/dev/null
gh issue list --state open 2>/dev/null
```

### Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GIT STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch:         <current>
Uncommitted:    <N files>
Ahead of main:  <N commits>

Recent commits:
  <hash> <message>
  ...

Changed files:
  <file> (+add/-del)

Open PRs:
  #<N> <title> — <status>

Open issues:
  #<N> <title>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Suggest next action
- Uncommitted → "Say 'commit' to stage + commit."
- Open PR → "PR #N open — check CI: `gh pr checks <N>`"
- Behind main → "Branch N behind main — merge? Ahmed decides."

### Rules
- READ-ONLY. Never `git add`, `commit`, `push`, or `checkout`.

---

## Mode 2 — SNAPSHOT

Session summary — what happened, files changed, next action.

### Steps

```bash
git status --short
git diff --stat HEAD
git log --oneline -5
```

Read the last few conversation turns to infer "last skill/agent used".

### Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION SNAPSHOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Last skill/agent:   <e.g. reviewer FULL mode>
Files changed:      <count>
Branch:             <current>
Unpushed commits:   <count>

Summary (2 lines):
<what was done this session, factual, no fluff>

Next suggested:
- <bullet> — <why>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Save the snapshot

Path: `.claude/skills/git/snapshots/<YYYY-MM-DD-HHMM>.md`

Create parent dir if missing. One file per invocation.

### Offer commit

```
Ready to commit?
[1] YES — I stage + commit + push
[2] STAGE ONLY — I stage + commit, Ahmed pushes
[3] NO — just the snapshot
Reply 1/2/3.
```

If 1 or 2 → transition to COMMIT mode with the drafted message.

### Rules
- SNAPSHOT is read-only unless Ahmed picks 1 or 2.
- Never invent files "changed" — trust `git status`.
- Snapshot files never overwritten (timestamp in filename).

---

## Mode 3 — COMMIT

Stage + commit + push. 3-choice confirm.

### Steps

1. Draft commit message from actual diff:
   - Type: `feat` / `fix` / `docs` / `refactor` / `chore` / `test`
   - Scope: main area touched (e.g. `proxy`, `webui`, `claude`)
   - Subject: ≤ 72 chars, imperative

2. Show draft:
```
Draft commit:

  <type>(<scope>): <subject>

  <body — 1-3 lines describing what and why>

  Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>

Files to stage: <list>
```

3. Confirm:
```
[1] YES — stage + commit + push to origin/<branch>
[2] STAGE ONLY — commit, no push
[3] EDIT — let me change the message
[4] NO — cancel
Reply 1/2/3/4.
```

4. Execute:
```bash
git add <files>
git commit -m "$(cat <<'EOF'
<message>
EOF
)"
# Only if 1:
git push origin <branch>
```

### Rules

- **Never use `--amend`** unless Ahmed explicitly asks.
- **Never `--no-verify`** — respect hooks.
- **Never force-push.**
- **Never stage `.env`, `cosign.key`, `*.pem`, `secrets/`** — refuse and flag.
- **Never rebase / reset / clean** in COMMIT mode.
- Always show final `git status` after commit.

---

## Mode 4 — PR

Create or update a pull request. Called standalone or by `implementer` PR mode.

### Steps

1. Verify prerequisites:
```bash
git status              # clean tree required
git log origin/main..HEAD --oneline    # need at least 1 commit ahead
gh auth status
```

If prerequisites fail → tell Ahmed what to fix, do not proceed.

2. Read context:
   - `.claude/docs/data.md` 🎫 Tickets section — is there an active ticket to reference?
   - Recent commits on branch — for PR body

3. Draft PR:
```markdown
## Summary
<1-3 bullets from commits>

## Changes
- <bullet per key file>

## Ticket
Closes #<N>   ← only if data.md has an active ticket, ask Ahmed to confirm

## Test plan
- [ ] <bullet>
- [ ] <bullet>

🤖 Generated with Claude Code
```

4. Confirm:
```
Draft PR:

Title: <auto title from lead commit>
Base: <detected default branch>
Head: <current branch>

Body:
<the draft above>

[1] YES — open PR now (`gh pr create`)
[2] EDIT — let me change title/body
[3] DRAFT — open as draft PR
[4] NO — cancel
Reply 1/2/3/4.
```

5. Execute via `gh pr create` (using HEREDOC for body).

6. Return URL.

### Rules

- Title ≤ 70 chars.
- Body uses HEREDOC format for exact rendering.
- Never target `main` directly if the repo has a staging branch — check + ask.
- Never open PR without at least 1 commit ahead.
- If ticket referenced → verify #N exists via `gh issue view <N>`.

---

## Mode 5 — ISSUE

Create / list / edit / search issues.

### Sub-flows

#### 5a. Create issue
Ask ONE question if info missing:
> "Issue title? (I'll draft body from data.md 🎫 if there's a related idea)"

Draft:
```markdown
## Summary
<from Ahmed's prompt or data.md idea>

## Steps to reproduce (if bug)
1. ...
2. ...

## Expected / Actual
- Expected: ...
- Actual: ...
```

Confirm before `gh issue create --title ... --body ...`.

#### 5b. List / search
```bash
gh issue list --state open --limit 20
gh issue list --search "<query>"
```

Format as table: `#N | title | labels | assignee`.

#### 5c. Edit
```bash
gh issue edit <N> --add-label bug
gh issue comment <N> --body "<text>"
```

Confirm before every edit.

### Rules
- Never close an issue automatically.
- Never assign to someone other than Ahmed without confirmation.
- Never delete issues.

---

## Mode 6 — POST (post progress to GH)

Read latest ticket entries from `data.md` → draft comment → post to GH after confirm.

### Steps

1. Read `.claude/docs/data.md` 🎫 Tickets section.
2. Identify the active ticket (most recent entry, or ask Ahmed if ambiguous).
3. Collect all entries under that ticket since the last POST run (marked in `.claude/skills/git/last-post.md` if exists).
4. Draft the GH comment:

```markdown
## Progress update — <YYYY-MM-DD>

### ✅ Done since last update
- <entry>

### ⏳ In progress
- <entry>

### ❌ Blocked / needs decision
- <entry>

<optional — Ahmed adds free text>
```

5. Show draft + confirm:
```
Ready to post to issue #<N>?

<the draft above>

[1] YES — post via gh issue comment
[2] EDIT — let me tweak the text
[3] NO — cancel

Reply 1/2/3.
```

6. Execute:
```bash
gh issue comment <N> --body "$(cat <<'EOF'
<comment>
EOF
)"
```

7. Update `.claude/skills/git/last-post.md` with the timestamp of the newest data.md entry we included.

### Rules

- **Never post without confirmation.**
- **Never duplicate ticket text** — this mode reads from data.md; never writes ticket content back to data.md.
- **Rank ⏳ items by priority** based on data.md ideas + team notes.
- **If no active ticket in data.md** → tell Ahmed: "No ticket found in `data.md` 🎫 section. Run `/data ingest ticket #N` first."

---

## Boundary vs adjacent tools

| Tool | Does what | git skill does what |
|---|---|---|
| `data` | Stores ticket text, team notes, ideas in `data.md` | Reads 🎫 section (never writes) |
| `implementer` PR mode | Coordinates when to open PR | Delegates the actual `gh pr create` to git PR mode |
| `infra` BUILD mode | Writes `.github/workflows/` YAML (CI files) | Doesn't touch CI YAML — that's an infra artifact |
| `reviewer` PR mode | Reviews a specific PR (read + report) | Different verb (create vs review) |
| GitHub MCP | API access | Optional path — falls back to `gh` CLI |

Zero overlap with any other tool.

---

## Files this skill writes

| Path | Written in mode | Notes |
|---|---|---|
| `.claude/skills/git/snapshots/<date-time>.md` | SNAPSHOT | One file per snapshot |
| `.claude/skills/git/last-post.md` | POST | Timestamp of last GH comment posted |

No other writes.

---

## MCPs used

| MCP | Modes | Fallback |
|---|---|---|
| **GitHub MCP** (installed ✅) | PR, ISSUE, POST | `gh` CLI |

If GitHub MCP down + `gh auth status` fails → paste-mode:
```
🖇️ Please paste output:
$ <exact command>
```

---

## Example flows

### `/git status`
```
Mode: GIT · VIEW
[reads git + gh in parallel]
[outputs summary block]
Next: uncommitted changes — say "commit" to stage.
```

### `/previous-step`
```
Mode: GIT · SNAPSHOT
[collects state, reads recent conversation]
[outputs snapshot, saves file]
Ready to commit? [1/2/3]
```

### "commit + push"
```
Mode: GIT · COMMIT
Draft: feat(proxy): add per-session PII counter

[1] YES  [2] STAGE ONLY  [3] EDIT  [4] NO
```

### "open PR"
```
Mode: GIT · PR
[verifies prereqs, drafts body from commits + data.md ticket #47]
Draft PR above. [1/2/3/4]
```

### "/updategithubticket"
```
Mode: GIT · POST
Active ticket from data.md: #47 (add prometheus metrics for PII)
Drafting comment from last 3 progress entries...

[shows draft]
[1] YES post  [2] EDIT  [3] NO
```
