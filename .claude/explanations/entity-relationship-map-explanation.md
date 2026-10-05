# 🍼 Baby Explain — Entity Relationship Map

## What is this feature?
When you chat with Garnet, it secretly hides your private info (names, emails, companies) before sending to the AI. This feature adds a **map button** in the chat toolbar. Click it → a popup opens showing ALL the private things Garnet detected, drawn as colored dots — and if two private things appeared in the same message, a line connects them.

## Why are we building it?
Right now Garnet protects your info silently — users can't see what it's doing. Julia and customers watching a demo need to SEE it working. This map makes the protection visible and builds trust.

## How does it work? (simple version)
1. You send a message like "Max Mustermann works at Enclaive, email max@enclaive.io"
2. Garnet's proxy detects the private info and replaces it with codes like `PERSON_cc75010d`
3. These codes get saved quietly on each chat message
4. When you click the ⬡ button → the map reads all those saved codes across your whole conversation
5. Each unique code becomes a colored dot (blue = person, green = company, red = email...)
6. If two codes were in the same message → a line connects them
7. The map updates live as you keep chatting — no need to close and reopen

**Important:** the map never shows real names like "Max Mustermann" — only the codes. Your actual data stays safe.

## The jobs (what needed to be built)

### Job 1 — Build the map component
**What:** A new popup window (called `EntityRelationshipMap.svelte`) that draws the graph as an SVG image inside a dark overlay
**Why:** Without this file there's nothing to show — it's the entire visual feature
**Who does it:** Claude Code
**Hard part:** Making the dots spread out evenly in a circle based on only the detected types — if only 2 types found, they should be on opposite sides, not both squashed at the top

### Job 2 — Read and organize the private codes
**What:** Two functions inside the component that scan all messages, find the codes (`PERSON_abc12345` etc.), count them, and figure out which codes appeared together
**Why:** Without this the map has no data — it wouldn't know what dots to draw or where to draw lines
**Who does it:** Claude Code
**Hard part:** Making it update automatically every time a new message arrives, without Ahmed having to refresh

### Job 3 — Add the ⬡ button to the top bar
**What:** A small hexagon button added to the Navbar (the bar at the top of the chat) next to the existing "private" and "🔍" buttons
**Why:** Users need a way to open the map — the button is the trigger
**Who does it:** Claude Code
**Hard part:** Button should only appear AFTER at least one message has been through the privacy proxy — not on a fresh empty chat

### Job 4 — Wire open/close behavior
**What:** Pressing Escape or clicking the dark area outside the popup closes it
**Why:** Standard modal behavior — users expect this, and without it the popup can only be closed with the ✕ button
**Who does it:** Claude Code
**Hard part:** Listening for keyboard events safely (add listener when popup opens, remove it when it closes — otherwise the listener keeps running forever in the background)

## What could go wrong?
- **Map doesn't update when new messages arrive** → fixed by making the data functions reactive (they re-run automatically when history changes)
- **PERSON dot appears gray instead of blue** → was caused by transparent fill on dark background, fixed by removing opacity
- **All dots crammed at the top** → was caused by using fixed positions for all 7 types even when only 2 are present, fixed by spacing only the detected types evenly
- **The map file gets stripped out of the final build** → fixed by keeping the import at the top of Navbar's code (the build tool won't delete things that are actively referenced)
- **Real names accidentally shown** → impossible by design — the component only reads the coded versions (`PERSON_cc75010d`), never the original text

## What does success look like?
- Send "Max Mustermann works at Enclaive, email max@enclaive.io" with privacy ON → ⬡ button appears in the top bar
- Click ⬡ → popup opens with blue dot (person), green dot (company), red dot (email), lines connecting them
- Send a second message mentioning Max again → a thicker line appears on the PERSON↔ORGANIZATION edge (appeared in 2 messages now) without closing the popup
- Press Escape → popup closes
- Click the dark area outside the popup → popup closes
- Run the proxy tests → still 22/22 passing (nothing in the backend was touched)

## Who needs to approve?
- **Seb: NO** — this is purely visual, doesn't touch the proxy, doesn't change how messages are sent or processed
- **Ion: NO** — no infrastructure changes
- **Nicu: NO** — no Harbor/registry changes

## One line summary
A visual map that shows users all the private info Garnet detected in their conversation, as colored dots with lines between things that appeared together — making the privacy protection visible during demos and real use.
