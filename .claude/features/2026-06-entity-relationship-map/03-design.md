# Design — Entity Relationship Map
Date: 2026-06-09  ·  Status: draft  ·  Blocks: 01-spec.md acceptance criteria

## Approach
Build entirely client-side. Parse `pseudonymized_prompt` strings already stored on each `history.messages[id]` object in Chat.svelte — no proxy call, no new endpoint. Construct nodes (unique entity tokens) and edges (co-occurrence in same message) in a reactive Svelte declaration so the graph updates automatically as the conversation grows. Render as a pure SVG grouped-ring layout (no D3, no external lib). Trigger button lives in `Navbar.svelte`, which already receives `history` as a prop.

## Alternatives considered
| Option | Pros | Cons | Why not |
|--------|------|------|---------|
| Call `/analyze` per message | Fresh entity data | Extra network round-trips, adds latency, same data already in `pseudonymized_prompt` | Redundant |
| D3 force simulation | Organic layout | Adds ~80KB dep, complex setup | Overkill for v1 |
| New proxy endpoint `/entity-graph` | Could return semantic relationships | Structural proxy change → Seb gate, not needed for co-occurrence | Out of scope |
| Button in Chat.svelte instead of Navbar | Simpler state management | Navbar already has `history` prop + is where other Garnet toggles live | Navbar is the right home |

## Files changed
| File | What changes | Risk |
|------|-------------|------|
| `src/lib/components/chat/EntityRelationshipMap.svelte` | **New file** — full graph component (SVG modal) | Low — isolated new file |
| `src/lib/components/chat/Navbar.svelte` | Add import + button (~line 149) + conditional render of modal | Low — additive only |

No proxy files touched. No `ResponseMessage.svelte` touched.

## Data flow
```
history.messages (already in Navbar via prop)
  → filter: messages where pseudonymized_prompt is truthy
  → for each message: regex-extract all entity tokens
     pattern: /(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|LOCATION|ID)_[a-f0-9]{8}/g
  → build nodes: Map<token, { type, messageCount }>
  → build edges: Map<`${tokenA}|${tokenB}`, count>
     (for each message: all pairs of tokens in that message → edge++)
  → SVG render:
     groups arranged in a ring by entity type (7 types = 7 positions on circle)
     nodes placed in small cluster around group center
     edges as <line> elements with opacity proportional to count
     node label: short token (e.g. "PERSON_cc75")
     node hover: full token + "seen in N messages"
```

## Entity color map (exact hex from Chat.svelte lines 1990–1996)
| Type | Color |
|------|-------|
| PERSON | `#3b82f6` (blue) |
| EMAIL_ADDRESS | `#ef4444` (red) |
| ORGANIZATION | `#22c55e` (green) |
| LOCATION | `#a855f7` (purple) |
| PHONE_NUMBER | `#f97316` (orange) |
| IBAN_CODE | `#eab308` (yellow) |
| ID | `#ec4899` (pink) |
| default | `#6b7280` (gray) |

## Real-time update strategy
`history` is an object — Svelte won't detect deep mutations. Use:
```svelte
$: messages = Object.values(history?.messages ?? {})
$: nodes = buildNodes(messages)   // pure function
$: edges = buildEdges(messages)   // pure function
```
`buildNodes` and `buildEdges` are pure functions that take the messages array → reactive declarations re-run whenever `messages` reference changes. Chat.svelte already does `history.messages[id] = { ...message }` (spread) on each new message, which triggers Svelte reactivity correctly.

## SVG layout
- **Viewport**: 600×400px, centered in modal
- **Group ring**: 7 entity types placed at equal angles on a circle (radius 150px from center)
- **Node placement**: within each group, nodes arranged in a small arc (radius 40px from group center). If only 1 node in group, it sits at the group center.
- **Edges**: `<line>` between node centers, `stroke-opacity: 0.3 + (count/maxCount)*0.5`, `stroke: #9ca3af`
- **Nodes**: `<circle r="14">` filled with entity color, `<text>` label below (font-size 9px, truncated to 12 chars)
- **Hover**: SVG `<title>` for native tooltip (full token + message count) — no extra DOM

## Navbar button placement
After queryExpand button, before `{/if}` at line 150 of `Navbar.svelte`:
```
[private toggle] [🔍 queryExpand] [graph icon button]  ← new
```
Button visibility condition:
```svelte
$: hasPseudonymized = Object.values(history?.messages ?? {}).some(m => m.pseudonymized_prompt)
```
Only render button when `hasPseudonymized` is true.

## Modal structure (EntityRelationshipMap.svelte)
```
position:fixed overlay (z-50, dark backdrop)
  └── centered panel (white/dark, rounded, shadow)
       ├── header: "Entity Map" + close ✕ button
       ├── <svg> graph
       └── legend: colored dots + type labels
```
Dismiss: backdrop click (check `event.target === overlayDiv`) + `keydown` Escape on `window`.

## Sync points (if adding entity type)
Not applicable for this feature — no new entity types added.

## Risks
- **Svelte reactivity on `history`**: if Chat.svelte ever mutates `history.messages[id]` in-place (without spread), the graph won't update. Mitigation: verified Chat.svelte line 1723 already uses `{ ...message }` spread — safe.
- **Large conversations**: many nodes → SVG overlap. Mitigation: v1 uses abbreviated labels; if >50 nodes, nodes shrink to r=8. Add note in `07-validate.md` to test with 20+ entity-rich messages.
- **Rollback**: deleting `EntityRelationshipMap.svelte` + reverting the 3-line Navbar change is sufficient — zero proxy impact.

## Seb approval items
None — no structural proxy changes, no `ResponseMessage.svelte` touch.

## Test plan
- Unit: `test_proxy.py` must still pass 22/22 (no proxy change → baseline check only)
- Manual UI:
  1. Send a message with "Max Mustermann at Enclaive" — confirm button appears in Navbar
  2. Open modal — confirm PERSON + ORGANIZATION nodes visible, colored correctly
  3. Send a second message with same PERSON + a new EMAIL — confirm graph updates without reopening
  4. Press Escape — confirm modal closes
  5. Click backdrop — confirm modal closes
- Logs: `console.warn('[GARNET MESSAGE SET]', ...)` already fires on new pseudonymized message — confirm node count increments in modal
