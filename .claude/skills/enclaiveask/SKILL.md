---
name: enclaiveask
description: Use when Ahmed says "/enclaiveask <question>" or "explain X to teammate". Reads current Garnet context and answers a teammate question in simple human language, copy-paste ready. No jargon.
---

# enclaiveask Skill

> Answer a teammate's question about Garnet in plain language.
> Output is copy-paste ready — no technical jargon.

---

## Steps Claude follows

### 1. Read Garnet context
- `CLAUDE.md` → what Garnet does
- `.claude/docs/proxy.md` → how proxy works
- `.claude/docs/webui.md` → UI layer
- Relevant doc for the question topic

### 2. Identify audience
Who is asking?
- Non-technical → zero code, analogies only
- Technical teammate → can mention components but no deep code
- Seb → max 3-4 lines, paragraph, one ask

### 3. Answer in plain language

Format:
```
<Question restate in one line>

<Answer — 2-5 sentences max>
<Optional: one concrete example>

<If action needed from them: one clear ask>
```

### 4. Examples

Q: "What does the privacy proxy actually do?"
A: "It sits between the chat UI and the AI model. Before your message reaches the AI, it replaces sensitive information — names, emails, company names — with codes. The AI never sees the real data. When the AI responds, the proxy swaps the codes back to the real values before you see the answer."

Q: "Why does Anthropic not work?"
A: "The API key for Anthropic is stored in the chat UI, but all requests go through a privacy proxy first. The proxy doesn't have the Anthropic key, so it can't forward the request. We need to add the key to the proxy's environment."

---

## Rules
- Never use: pseudonymization, depseudonymization, FastAPI, Svelte, Redis, SHA256.
- DO use: "replaces", "codes", "swap back", "sits between", "blocks", "forwards".
- Max 5 sentences.
- Always end with a clear next action if one exists.
