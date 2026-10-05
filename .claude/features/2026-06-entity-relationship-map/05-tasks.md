# Tasks — Entity Relationship Map

## Agent prompts (code only)

### Task 1 — Create EntityRelationshipMap.svelte
**File:** `src/lib/components/chat/EntityRelationshipMap.svelte` (new file)

**Problem:** No component exists to visualize entity co-occurrence across the conversation.

**Context:**
- `history.messages` is an object keyed by message ID; each message may have a `pseudonymized_prompt` string (set by Chat.svelte line 1723)
- Entity tokens follow the pattern `/(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|LOCATION|ID)_[a-f0-9]{8}/g`
- Color map (from Chat.svelte lines 1990–1996):
  - PERSON → `#3b82f6`, EMAIL_ADDRESS → `#ef4444`, ORGANIZATION → `#22c55e`
  - LOCATION → `#a855f7`, PHONE_NUMBER → `#f97316`, IBAN_CODE → `#eab308`
  - ID → `#ec4899`, default → `#6b7280`

**What to build:**
1. Accept one prop: `history` (same shape as Chat.svelte's `history`)
2. Reactive declarations:
   ```
   $: messages = Object.values(history?.messages ?? {})
   $: nodes = buildNodes(messages)   // Map<token, { type, count }>
   $: edges = buildEdges(messages)   // Map<tokenA|tokenB, count>
   ```
3. `buildNodes`: for each message with truthy `pseudonymized_prompt`, extract all tokens → accumulate count
4. `buildEdges`: for each message, take all token pairs → increment edge count
5. SVG layout — 600×400px viewBox:
   - Place entity-type group centers on a circle (radius 150px, centered at 300,200)
   - Within each group, arrange nodes in a small arc (radius 40px from group center)
   - Draw `<line>` edges between node centers (`stroke: #9ca3af`, `stroke-opacity: 0.3`)
   - Draw `<circle r="14">` nodes filled with entity color
   - Add `<text>` label below each node (font-size 9px, truncate token to 12 chars)
   - Add `<title>` inside each circle for native hover tooltip (full token + "seen in N messages")
6. Modal wrapper: `position:fixed` overlay, z-index 50, dark semi-transparent backdrop, centered white/dark panel with header "Entity Map", close ✕ button
7. Dismiss on backdrop click (`event.target === overlayEl`) and `window` keydown Escape
8. If a group has >6 nodes, reduce circle radius to r=8 to avoid overlap

**Acceptance:** Component mounts without errors; after a pseudonymized conversation, nodes render colored by type; edges visible between co-occurring entities; Escape closes modal.

DO NOT deploy. Ahmed deploys.

---

### Task 2 — Wire button in Navbar.svelte
**File:** `src/lib/components/chat/Navbar.svelte`

**Problem:** No trigger exists to open the entity map modal.

**Context:**
- `history` is already a prop on Navbar (line 54)
- Existing Garnet buttons are at lines 125–149 (private toggle, queryExpand toggle) — add after them, before the `{/if}` at line 150
- Import EntityRelationshipMap at top of `<script>` block alongside other imports

**What to add:**
1. Import `EntityRelationshipMap` from `'../chat/EntityRelationshipMap.svelte'`
2. Reactive visibility check:
   ```svelte
   $: hasPseudonymized = Object.values(history?.messages ?? {}).some(m => m.pseudonymized_prompt)
   ```
3. Local state: `let showEntityMap = false`
4. Button (after queryExpand button, ~line 149):
   - Only render when `hasPseudonymized` is true
   - Same button style as the existing Garnet toggles (`px-2.5 py-1 rounded-lg text-xs`)
   - Label: `⬡` or a simple graph icon character — use `🕸` emoji or a plain `<svg>` network icon (3 dots + 2 lines, inline)
   - `on:click={() => showEntityMap = true}`
5. Mount `<EntityRelationshipMap {history} on:close={() => showEntityMap = false} />` conditionally: `{#if showEntityMap}`

**Acceptance:** Button appears in Navbar after first pseudonymized message; clicking opens the modal; modal closes correctly.

DO NOT deploy. Ahmed deploys.

---

## Deploy commands (Ahmed runs)

```bash
cd ~/Desktop/garnet
git add src/lib/components/chat/EntityRelationshipMap.svelte
git add src/lib/components/chat/Navbar.svelte
git commit -m "feat: entity relationship map modal"
git push origin garnet-privacy-proxy
# wait for GitHub Actions to build the webui image, then:
ssh root@65.108.38.50 "cd /opt/garnet && docker compose pull open-webui && docker compose up -d --force-recreate open-webui"
```

## Verify commands

```bash
# confirm webui container is up
ssh root@65.108.38.50 "docker ps | grep open-webui"

# confirm no build errors in webui container logs
ssh root@65.108.38.50 "docker logs garnet-open-webui-1 --tail=30"

# proxy tests unaffected (no proxy change — baseline check)
ssh root@65.108.38.50 "docker exec -w /service garnet-privacy-proxy-1 python3 app/test_proxy.py"
```

## Manual UI test sequence (Ahmed runs in browser)

1. Open Garnet chat, send: `"Max Mustermann works at Enclaive, email max@enclaive.io"`
2. Confirm ⬡ button appears in Navbar (next to queryExpand toggle)
3. Click button → modal opens with PERSON, ORGANIZATION, EMAIL_ADDRESS nodes visible, colored blue/green/red
4. Send second message: `"Call Max at +49 123 456789"` → confirm PHONE_NUMBER node appears + edge from PERSON to PHONE_NUMBER (without closing/reopening modal)
5. Press Escape → modal closes
6. Reopen → click backdrop outside panel → modal closes
7. `test_proxy.py` passes 22/22
