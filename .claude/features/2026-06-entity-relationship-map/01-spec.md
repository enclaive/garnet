# Spec — Entity Relationship Map
Date: 2026-06-09  ·  Author: Ahmed  ·  Status: draft

## Problem
Users have no way to see which PII entities were detected across a conversation or how they relate to each other. The (i) button on each message shows per-message entity counts, but there is no cross-conversation view. For demos and end users (Julia, customers), this makes the privacy protection feel invisible — they cannot tell at a glance what Garnet is protecting or how entities connect.

## Why now
Demo readiness + end-user visibility. Julia and customers need to see Garnet's privacy protection in action during demos and live use. A visual entity graph makes the pseudonymization tangible and builds trust.

## Users affected
Julia (end user) · customers · Ahmed (dev/demo)

## Desired behavior
- A graph icon button appears in the chat UI once at least one message has been pseudonymized.
- Clicking it opens a modal overlay showing a graph of all PII entities detected in the current conversation.
- Each unique entity token (e.g. `PERSON_cc75010d`) is a node, colored by entity type (PERSON, ORGANIZATION, EMAIL_ADDRESS, etc.) using Garnet's existing color scheme.
- Two entities are connected by an edge if they appeared together in the same message.
- The graph updates in real-time as the conversation grows — new entities and edges appear without reopening the modal.
- The modal closes on Escape or backdrop click.

## Out of scope
- Showing real PII values (e.g. "Max Mustermann") — tokens only in v1; real values require a new proxy endpoint and Seb approval.
- Entity relationship inference beyond co-occurrence (e.g. semantic roles like "employed by").
- Filtering or searching within the graph.
- Persistence across sessions or export.
- Mobile / small-screen layout.

## Acceptance criteria
- [ ] Graph icon button is visible in the chat UI only after at least one message has a pseudonymized prompt.
- [ ] Opening the map shows all unique entity tokens detected in the current conversation as labeled nodes.
- [ ] Two entities that co-occurred in the same message are connected by a visible edge.
- [ ] Nodes are colored by entity type matching the existing Garnet color scheme in `Chat.svelte`.
- [ ] Graph updates in real-time as the conversation grows (new messages add nodes/edges without reopening the modal).
- [ ] Modal closes on Escape keypress or backdrop click.
- [ ] `test_proxy.py` still passes 22/22 (no proxy change).

## Constraints (from Garnet rules)
- Must not remove `body["stream"] = False`
- Must not expose `0.0.0.0`
- Must not log headers
- Seb approval needed? **N** — frontend only, no proxy changes, no touch of `ResponseMessage.svelte`

## Open questions
- [ ] None — all inputs confirmed by Ahmed 2026-06-09
