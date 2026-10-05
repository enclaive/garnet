---
name: clean-comments
description: Use when Ahmed says "clean comments", "tidy comments.md", "clean up progress log". Reads .claude/docs/comments/comments.md, removes duplicates, condenses old entries, keeps last 10 meaningful bullets. Never loses recent entries.
---

# clean-comments Skill

> Tidy up `.claude/docs/comments/comments.md`.
> Condense old entries. Keep recent ones intact.

---

## Steps Claude follows

### 1. Read comments.md
Path: `.claude/docs/comments/comments.md`

If empty or missing → say "Nothing to clean. File is empty."

### 2. Analyze entries
- Count total entries
- Find duplicates (same date or same content)
- Find very old entries (>30 days) that can be compressed
- Identify the 10 most recent entries → never touch these

### 3. Compress old entries
Group entries older than 30 days into a single summary block:
```markdown
## Archive — before <DATE>
<N> entries condensed:
- <key milestone 1>
- <key milestone 2>
- <key milestone 3>
```

### 4. Show diff before writing
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMENTS CLEANUP PREVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before: <N> entries (<size>)
After:  <N> entries + 1 archive block

Removed (duplicates): <list>
Compressed (old):     <N> entries → archive

Recent entries kept:  <N> (untouched)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apply? (y/n)
```

### 5. Write cleaned file only if Ahmed says yes

---

## Rules
- NEVER delete the 10 most recent entries.
- NEVER lose dates.
- Always show preview before writing.
- If fewer than 15 total entries → say "File is already clean, nothing to do."
