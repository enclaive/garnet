# Task: Port Garnet to OWU v0.11.4

**Branch to create:** `sync/owu-v0.11.4`
**Base:** `main` (fork, currently at OWU v0.8.12 + all Garnet work)
**Target:** OWU v0.11.4 tag
**Goal:** Update all 24 Garnet-modified files to OWU v0.11.4 while preserving Garnet logic

---

## Approach (file-by-file, not full merge)

Full `git merge v0.11.4` = 3000+ conflicts. Instead:
1. `git checkout v0.11.4 -- <file>` → take OWU latest per file
2. Re-apply Garnet-specific lines (see diff vs v0.8.12 per file)
3. Commit per file
4. Test with docker compose at end
5. PR `sync/owu-v0.11.4` → `main` + squash-merge

---

## File checklist

### Backend (9 files) — all conflict with OWU v0.11.4

- [ ] `backend/open_webui/utils/middleware.py` — SSE: pseudonymized_prompt, garnet_breakdown, file_entity_count, query_variants (4 insertion points)
- [ ] `backend/open_webui/utils/chat.py`
- [ ] `backend/open_webui/utils/payload.py`
- [ ] `backend/open_webui/utils/response.py`
- [ ] `backend/open_webui/main.py` — proxy routing hooks
- [ ] `backend/open_webui/routers/openai.py`
- [ ] `backend/open_webui/routers/ollama.py`
- [ ] `backend/open_webui/routers/files.py`
- [ ] `backend/open_webui/functions.py`

### Frontend (15 files) — all conflict with OWU v0.11.4

- [ ] `src/lib/components/chat/Settings/Garnet.svelte` — pure Garnet, doesn't exist in OWU → just add back after checkout
- [ ] `src/lib/components/workspace/Models/Capabilities.svelte` — add privacy_enforce field
- [ ] `src/lib/components/admin/Settings/Models/ModelMenu.svelte` — privacy toggle UI
- [ ] `src/lib/components/admin/Settings/Models.svelte`
- [ ] `src/lib/components/chat/Controls/Controls.svelte` — screening speed
- [ ] `src/lib/components/chat/ModelSelector.svelte` — privacy_enforce
- [ ] `src/lib/components/chat/Navbar.svelte`
- [ ] `src/lib/components/chat/SettingsModal.svelte` — Garnet tab
- [ ] `src/lib/components/chat/Chat.svelte` — largest file, proxy hooks
- [ ] `src/lib/components/chat/Messages/UserMessage.svelte`
- [ ] `src/lib/components/chat/ChatPlaceholder.svelte`
- [ ] `src/lib/components/chat/Placeholder.svelte`
- [ ] `src/lib/components/chat/EntityRelationshipMap.svelte`
- [ ] `src/lib/components/common/FileItem.svelte`
- [ ] `src/lib/components/layout/Sidebar.svelte`

---

## Per-file workflow

```bash
# 1. See what Garnet added
git diff v0.8.12..main -- <file>

# 2. Pull OWU v0.11.4 version
git checkout v0.11.4 -- <file>

# 3. Re-add Garnet logic manually

# 4. Commit
git add <file>
git commit -m "feat: port <file> Garnet logic to OWU v0.11.4"
```

---

## Setup (run at start of session)

```bash
git checkout main && git pull
git fetch upstream --tags           # ensure v0.11.4 tag is present
git checkout -b sync/owu-v0.11.4
```

---

## Test (run when all files done)

```bash
docker compose down && docker compose up --build
# send PII message → verify pseudonymization works
# verify privacy toggle, screening speed UI works
```

---

## Notes from analysis session (2026-09-26)

- Fork is at OWU v0.8.12 base
- Full merge attempt → 421 conflicted files (abort was correct)
- Real Garnet-modified files: 24 (16 backend/proxy + 8 pure Garnet OWU touches)
- middleware.py: OWU v0.11.4 already uses Config.get() (no app.state.config) — only Garnet SSE additions needed
- Garnet.svelte: pure Garnet file, does not exist in OWU — restore from main after checkout
- Also clean up: delete `.github/workflows/docker.yaml` + `docker-build.yaml` (OWU duplicates, trigger on v*)
