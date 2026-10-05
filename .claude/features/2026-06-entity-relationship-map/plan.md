# Plan: Entity Relationship Map
Date: 2026-06-09  ·  Input: `01-spec.md` + `03-design.md`  ·  Mission: 1

## Summary
Add a visual entity relationship graph to the Garnet chat UI — a modal showing all PII tokens detected across the conversation as colored nodes with co-occurrence edges. This is a Mission 1 demo + end-user feature that makes Garnet's privacy protection visible to Julia and customers without touching the proxy or any structural code. Pure frontend, 2 files, no Seb gate.

## Phases

### Phase 1 — Component scaffold + data layer
Goal: Build the pure data-extraction layer (no rendering yet) so we can verify `buildNodes` and `buildEdges` produce correct output from real conversation history before investing in SVG.

| Step | Action | File/Service | Effort | Owner | Depends on |
|------|--------|-------------|--------|-------|------------|
| 1.1 | Create `EntityRelationshipMap.svelte` with `export let history`, empty `<div>` modal shell using `position:fixed` overlay + centered panel | `src/lib/components/chat/EntityRelationshipMap.svelte` (new) | S | Ahmed | — |
| 1.2 | Implement pure function `buildNodes(messages)` → returns `Map<token, {type, count}>` using regex `/(PERSON\|ORGANIZATION\|EMAIL_ADDRESS\|IBAN_CODE\|PHONE_NUMBER\|LOCATION\|ID)_[a-f0-9]{8}/g` on each `pseudonymized_prompt` | same file | S | Ahmed | 1.1 |
| 1.3 | Implement pure function `buildEdges(messages)` → for each message, all token pairs → `Map<'tokenA\|tokenB', count>` (alphabetical pair key so order-independent) | same file | S | Ahmed | 1.2 |
| 1.4 | Add reactive declarations `$: messages = Object.values(history?.messages ?? {})`, `$: nodes = buildNodes(messages)`, `$: edges = buildEdges(messages)` + `console.warn('[GARNET MAP]', nodes.size, edges.size)` for debug | same file | S | Ahmed | 1.3 |

### Phase 2 — SVG rendering
Goal: Render the graph as a self-contained 600×400px SVG inside the modal panel — no external lib, no D3, deterministic layout.

| Step | Action | File/Service | Effort | Owner | Depends on |
|------|--------|-------------|--------|-------|------------|
| 2.1 | Add SVG viewport (600×400) + helper `getGroupCenter(type)` returning `{x, y}` for each of 7 entity types placed on a circle (radius 150, center 300,200, equal angles) | `src/lib/components/chat/EntityRelationshipMap.svelte` | S | Ahmed | 1.4 |
| 2.2 | Add helper `getNodePosition(token, groupCenter, indexInGroup, totalInGroup)` → arc placement around group center (radius 40, or shrink if `totalInGroup > 6`) | same file | S | Ahmed | 2.1 |
| 2.3 | Render edges as `<line>` between node centers, `stroke: #9ca3af`, `stroke-opacity: 0.3 + (count/maxCount)*0.5` | same file | S | Ahmed | 2.2 |
| 2.4 | Render nodes as `<circle r="14">` filled with entity color (hardcoded color map from `Chat.svelte` lines 1990–1996, PERSON `#3b82f6` etc.) + `<text>` label truncated to 12 chars + `<title>` for hover tooltip ("full token · seen in N messages") | same file | S | Ahmed | 2.3 |
| 2.5 | Add legend below SVG (colored dots + entity type labels) and header "Entity Map" + ✕ close button | same file | S | Ahmed | 2.4 |

### Phase 3 — Navbar integration + dismiss
Goal: Wire the modal into the Navbar so it can be opened, closed, and shows the button only when there's something to display.

| Step | Action | File/Service | Effort | Owner | Depends on |
|------|--------|-------------|--------|-------|------------|
| 3.1 | Add `import EntityRelationshipMap from '../chat/EntityRelationshipMap.svelte'` to top of `<script>` block + `let showEntityMap = false` + `$: hasPseudonymized = Object.values(history?.messages ?? {}).some(m => m.pseudonymized_prompt)` | `src/lib/components/chat/Navbar.svelte` (~line 31, ~line 60) | S | Ahmed | 2.5 |
| 3.2 | Add button after queryExpand toggle (~line 149) — same Tailwind classes as existing toggles, hexagon/network icon as inline SVG, only render when `hasPseudonymized` is true | `src/lib/components/chat/Navbar.svelte` | S | Ahmed | 3.1 |
| 3.3 | Mount `{#if showEntityMap}<EntityRelationshipMap {history} on:close={() => showEntityMap = false} />{/if}` after the button | `src/lib/components/chat/Navbar.svelte` | S | Ahmed | 3.2 |
| 3.4 | In `EntityRelationshipMap.svelte`: add `window` keydown listener for Escape → `dispatch('close')` + backdrop click handler (`event.target === overlayEl`) → `dispatch('close')`. Use `onMount`/`onDestroy` to add/remove listeners safely | `src/lib/components/chat/EntityRelationshipMap.svelte` | S | Ahmed | 3.3 |

### Phase 4 — Deploy + validate
Goal: Ship to cVM, confirm no regression in proxy tests, walk through the manual UI test sequence in `05-tasks.md`.

| Step | Action | File/Service | Effort | Owner | Depends on |
|------|--------|-------------|--------|-------|------------|
| 4.1 | Local Svelte compile check: `docker build -f backend/open_webui/Dockerfile . --target build` — confirm no Svelte errors | local | S | Ahmed | 3.4 |
| 4.2 | Commit + push: `git commit -m "feat: entity relationship map modal"`, push to `garnet-privacy-proxy` | local → GitHub | S | Ahmed | 4.1 |
| 4.3 | Wait for GitHub Actions to build webui image, then on cVM: `docker compose pull open-webui && docker compose up -d --force-recreate open-webui` | cVM `65.108.38.50` | S | Ahmed | 4.2 |
| 4.4 | Browser test sequence: send "Max Mustermann at Enclaive, max@enclaive.io" → confirm button → open modal → confirm 3 nodes (PERSON/ORG/EMAIL_ADDRESS) → send "Call Max at +49…" → confirm PHONE_NUMBER node + edge added live → Escape closes → backdrop closes → run `test_proxy.py` to confirm 22/22 | browser + cVM | S | Ahmed | 4.3 |

## Seb approval gates
None. This feature stays clear of every Seb-gated area: no proxy changes, no `ResponseMessage.svelte`, no streaming changes, no new entity type, no new API endpoint, no key distribution. The 3-line summary already sent to him in design review is sufficient.

## Blocked steps
| Step | Blocked by | Who to ask |
|------|-----------|------------|
| — | — | — |

Nothing blocked. No external dependency on Ion, Nicu, Ahmed Bouzid, or Seb.

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Vite tree-shakes `EntityRelationshipMap.svelte` out of bundle (webui.md warns this happens for unused imports) | Low | High — feature silently absent in prod | Keep import at top of `<script>` block; `{#if showEntityMap}` keeps live reference. Confirm in built bundle: `docker exec garnet-open-webui-1 grep -r EntityRelationshipMap /app/build` |
| `console.log` debug calls stripped by Vite in prod | Medium | Low — only loses debug visibility | Always use `console.warn` for debug (per webui.md rule) |
| Svelte does not re-render on deep `history.messages` mutation | Low | High — graph stays empty | Chat.svelte line 1723 already uses `{ ...message }` spread → `Object.values(history.messages)` returns a new array reference on each new message → reactive `$:` re-runs. Verified in design. |
| SVG node overlap with >6 entities of same type | Medium | Medium — visually unreadable | Step 2.2 shrinks node radius dynamically when group > 6 |
| Modal styling broken in OWU dark theme | Medium | Low — readability only | Use Tailwind `dark:` variants matching existing Garnet UI (e.g. `bg-white dark:bg-gray-900`) |
| Token regex misses a new entity type added later | Low | Medium — silent omission from graph | Document the regex in the file header comment; sync-points checklist in feature folder reminds devs to update it |
| Real PII values accidentally leaked into the map | Very low | Critical | Component only ever reads `pseudonymized_prompt` (already tokenized by proxy). It never touches raw user content or the response body. Verified by file scope. |

## Critical path
Phase 1 (1.1 → 1.2 → 1.3 → 1.4) → Phase 2 (2.1 → 2.2 → 2.3 → 2.4 → 2.5) → Phase 3 (3.1 → 3.2 → 3.3 → 3.4) → Phase 4 (4.1 → 4.2 → 4.3 → 4.4)

Linear chain, no parallelism possible inside a phase because each step builds on the previous. But the whole feature is short enough (~2-3 hours total work) that this is fine.

## Garnet constraints checklist
- [x] No `body["stream"] = False` removal — no proxy changes
- [x] No `0.0.0.0` exposure — frontend only
- [x] No header logging — no network calls
- [x] Seb gates identified — none triggered
- [x] Ahmed deploys — agent code only (Phase 4.2–4.3 are Ahmed's commands)
- [x] `test_proxy.py` must pass after each phase — baseline check in Phase 4.4; no proxy code touched so 22/22 expected

## Next action for Ahmed
→ Say "build phase 1" to start with Step 1.1 (create the empty `EntityRelationshipMap.svelte` skeleton with the prop and modal shell).
