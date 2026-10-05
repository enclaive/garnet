# feature-entity-relationship-map
Date: 2026-06-09  ·  Author: Ahmed  ·  Status: ready-to-build

## Requirement
Show a visual graph of detected PII entities and their co-occurrence relationships across the current conversation, accessible from the chat UI.

## Context
Current state (from `.claude/docs/`):
- `pseudonymized_prompt` is stored per user message in `history.messages[id]` — `Chat.svelte` attaches it after the `done` socket event
- Entity tokens are deterministic: `PERSON_cc75010d` always = same real value, same session
- Token format: `(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|LOCATION|ID)_[a-f0-9]{8}`
- Entity color map already exists in `Chat.svelte` (used for entity highlights)
- `/analyze` endpoint in `main.py` already returns entities per message (used by entity toggle flow)
- No existing visualization of entity relationships across the full conversation

Current behavior: users see per-message entity counts via (i) button tooltip — no cross-conversation view.

Expected behavior: a button opens a modal showing a graph where:
- **Nodes** = unique entity tokens detected across conversation (colored by type)
- **Edges** = co-occurrence (two entities appeared in the same message)
- **Tooltip on hover** = entity token + count of messages it appeared in
- **No proxy change needed** — graph is built client-side from existing `pseudonymized_prompt` fields

⚠️ assumed: v1 shows tokens only (e.g. `PERSON_cc75010d`), not real values — avoids new proxy endpoint and Seb gate  
⚠️ assumed: static SVG layout grouped by entity type (no physics simulation) — simpler, no D3 dependency  
⚠️ assumed: button lives in the chat Navbar area next to the privacy toggle

## Seb approval needed?
N — pure frontend addition. No proxy changes. No structural changes. New component + one button in Navbar/Chat. No touch of `ResponseMessage.svelte`.

## Constraints (always apply)
- [ ] Never remove `body["stream"] = False`
- [ ] Never expose `0.0.0.0`
- [ ] Never log request headers
- [ ] Never commit .env / cosign.key
- [ ] Read files before editing
- [ ] Ahmed deploys — agent changes code only

## Tasks

### Task 1 — Create EntityRelationshipMap.svelte component
**File:** `src/lib/components/chat/EntityRelationshipMap.svelte`  
**Problem:** No component exists for visualizing entity relationships.  
**Change:** New Svelte component that:
1. Accepts `messages` (conversation history) as prop
2. Extracts entity tokens from each message's `pseudonymized_prompt` using regex `/(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|LOCATION|ID)_[a-f0-9]{8}/g`
3. Builds a node list (unique tokens) and edge list (pairs that co-occur in the same message)
4. Groups nodes by entity type into clusters arranged in a circle layout (SVG, no external lib)
5. Draws edges as SVG `<line>` elements with low opacity; nodes as `<circle>` with entity-type color; label on hover via SVG `<title>` or a positioned `<div>`
6. Use the existing entity color map from `Chat.svelte` (copy the map into this component)
7. Renders inside a modal overlay (position:fixed, dark backdrop) with a close button

**Entity color map to replicate** (from `Chat.svelte`):
```
PERSON → blue-ish
ORGANIZATION → green-ish
EMAIL_ADDRESS → purple-ish
PHONE_NUMBER → orange-ish
IBAN_CODE → red-ish
LOCATION → teal-ish
ID → gray-ish
```
(Read exact hex values from `Chat.svelte` before implementing)

**Accept:** Modal opens, nodes render grouped by type, edges visible between co-occurring entities, no console errors

---

### Task 2 — Add "Entity Map" button to Chat UI
**File:** `src/lib/components/chat/Navbar.svelte` (or `Chat.svelte` if Navbar is too constrained)  
**Problem:** No trigger exists to open the map.  
**Change:** Add a small graph icon button that:
- Is only visible when at least one message in history has a truthy `pseudonymized_prompt`
- On click: sets a `showEntityMap = true` boolean that conditionally renders `<EntityRelationshipMap>`
- Import and mount `EntityRelationshipMap.svelte` in the same file
- Pass full `history.messages` (or the filtered array) as prop

**Accept:** Button appears after first pseudonymized message; clicking opens the modal; closing sets flag to false

---

### Task 3 — Wire close + keyboard dismiss
**File:** `src/lib/components/chat/EntityRelationshipMap.svelte`  
**Problem:** Modal needs to be dismissible without only the close button.  
**Change:** Add `keydown` listener on the overlay div: `Escape` → emit `close` event or call the close callback. Backdrop click (on overlay, not inner panel) also closes.

**Accept:** Pressing Escape closes modal; clicking outside the graph panel closes it

---

## New entity type? (if applicable)
No new entity types added. If a new type is added later, sync:
- [ ] `src/lib/components/chat/Controls/Controls.svelte`
- [ ] `src/lib/components/chat/Chat.svelte` color map
- [ ] `backend/privacy_proxy/app/main.py` token list in `split_at_safe_boundary`
- [ ] `backend/privacy_proxy/app/pseudonymizer.py`

## Verify (before deploy)
```bash
# confirm pseudonymized_prompt is populated in history after a chat
# open browser devtools → Application → check history object in Svelte store
# or add a console.warn to EntityRelationshipMap to log extracted nodes/edges

# no proxy tests needed — frontend only change

# build the webui image locally to catch Svelte compile errors:
cd ~/Desktop/garnet
docker build -f backend/open_webui/Dockerfile . --target build 2>&1 | tail -30
```

## Deploy (Ahmed runs)
```bash
cd ~/Desktop/garnet
git add src/lib/components/chat/EntityRelationshipMap.svelte
git add src/lib/components/chat/Navbar.svelte   # or Chat.svelte if button goes there
git commit -m "feat: entity relationship map modal"
git push origin garnet-privacy-proxy
# wait for GitHub Actions to build the webui image, then:
ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull open-webui && docker compose up -d --force-recreate open-webui"
```

## Rollback
```bash
ssh root@65.108.38.50 "cd /opt/garnet && docker compose up -d --force-recreate open-webui"
# point to prior tag if needed via Harbor
```
