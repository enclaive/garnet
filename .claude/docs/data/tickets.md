# 🎫 Tickets

_Managed by: `curator` agent · Written via: `/data` skill_
_Format: `### YYYY-MM-DD — <ticket ref> — <one-line title>`_

<!-- GitHub issues, Linear tasks, JIRA tickets Ahmed wants agents to know about -->

### 2026-07-25 — garnet-api-key-settings — Settings/Account doesn't allow enabling API key for 3rd-party extensions

**Problem:** Settings/Account does not allow to enable an API key.
**Rationality:** Need API token to connect 3rd party extension.
**Status:** open

---

### 2026-07-25 — garnet-owu-sync — Sync with OWU upstream (1822 commits behind, target v0.92)

**Goal:** Establish Sync with Open WebUI upstream.
**Problem:** We are 1822 commits behind, version v0.92 is out, we are 0.8xx.

**Tasks:**
- Research sync structure (merge / rebase / rebase from patch)
- Implement the strategy
- Add tests for enclaive add-ons
- Add strategy to CI/CD: push container only if tests succeed
- Add security testing to CI/CD (sync w/ @ahmedbouzid07 on security code testing we do)
- Add proper version and release notes

---

### 2026-07-25 — garnet-helm-backend — Meta helm chart to toggle Ollama vs vLLM backend + GPU operator

**Goal:** Meta helm chart allowing choosing between Ollama and vLLM backend.

**Tasks:**
- Update helm to support backend toggle (Ollama / vLLM)
- Add NVIDIA GPU operator (sync on GPU and CC-GPU w/ @ahmedbouzid07)
- Update version
- Update readme

---

### 2026-07-25 — garnet-cursor-scan — /analyze endpoint + cursor scan animation highlighting sensitive words

**Goal:** Before sending prompt to LLM, animate a cursor scan that highlights sensitive words.

**Architecture:**
```
React UI → Preview API (Python, detection only) → return spans → frontend animation → final API call (with pseudonymization)
```
Key idea: Split detection and pseudonymization into 2 steps.

**Two endpoints to define:**
- `/analyze` — returns positions of sensitive words (detection only, no replacement)
- `/pseudonymize` — actually replaces data before forwarding to ChatGPT (already implemented)

**Important:** `/pseudonymize` and `/analyze` must hit the same words. Avoid tokenization mismatch — backend works on character positions, frontend splits on words.

**Frontend implementation (React):**
1. `tokenize(text)` — split on whitespace, keep spaces
2. `markTokens(tokens, entities)` — map entity char spans → tokens
3. Cursor animation via `useState(cursorIndex)` + `setTimeout` at 40ms/token
4. Render: tokens up to cursor shown, sensitive tokens highlighted bold
5. Optional color coding: PERSON=blue, EMAIL=red, LOCATION=green
6. Tooltip: `title={t.entityType}`

**Remark:** Similar to (i) button logic — difference is /analyze runs BEFORE sending to ChatGPT API, (i) button shows pseudonymized prompt AFTER.

---

### 2026-07-25 — garnet-i-button — (i) hover button shows pseudonymized prompt sent to model

**Goal:** Give user control to see what actual pseudonymized prompt was sent to model.

**Task:**
- Implement (i) button under the prompt input
- On-hover: display black bubble with white font showing the pseudonymized prompt

**Success criteria:**
If model = remote AND private = on → actual prompt shown should contain pseudonymized tokens:
`PERSON_1a2b3c likely works at ORG_4d5e6f`

**Status:** open
