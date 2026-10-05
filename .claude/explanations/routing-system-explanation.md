# 🍼 Baby Explain — Garnet Routing System

**Generated:** 2026-07-11 16:45:00

## What is this?
When you type a message in the chat and press send, your message travels
through several rooms before the AI answers. This explains every room it
passes through and what happens in each one.

---

## The journey of your message (step by step)

### Step 1 — You type a prompt in Open WebUI
You're on the chat screen. You pick a model (like Claude Opus) and type something.
WebUI knows where to send it because you configured a **connection** in the Admin Panel.

---

### Step 2 — Admin Panel connection settings decide what happens next

In **Admin Panel → Settings → Connections**, you have an OpenAI-compatible connection.
It has two fields that matter:

| Field | What it does |
|-------|-------------|
| **URL** | Where WebUI sends the message. Should point to the proxy: `http://privacy-proxy:8080` |
| **API Key** | A password WebUI puts on every message. The proxy reads this to know which AI to use |

**This is the key insight:** the proxy doesn't know which AI you want by looking at
the model name alone. It looks at the API key prefix to decide where to send your message.

---

### Step 3 — Message arrives at the Privacy Proxy

The proxy is a middleman (FastAPI app) that:
1. Hides your private info before sending to the AI
2. Sends the message to the real AI
3. Puts your private info back in the answer

When your message arrives, the proxy checks the path:
- Path starts with `openai/` → it's going to an OpenAI-compatible AI (Claude, Gemini, Groq, OpenAI)
- Path starts with `api/` → it's going to Ollama (local models like Llama, Mistral)

---

### Step 4 — Proxy detects which AI to use (the routing logic)

For OpenAI-compatible requests, the proxy looks at the **Authorization header**
(the API key WebUI sent). It reads the first few characters:

```
API key starts with sk-ant-  →  send to Anthropic (Claude)
API key starts with AIza     →  send to Google (Gemini)
API key starts with gsk-     →  send to Groq
API key starts with sk-or-   →  send to OpenRouter
anything else                →  send to OPENAI_API_URL (default, usually real OpenAI)
```

So if you want Claude Opus → the API key field in Admin Panel must be your real
Anthropic key (`sk-ant-...`). That's how the proxy knows to call Anthropic.

---

### Step 5 — Proxy pseudonymizes your message

Before sending to the AI, the proxy scans your message for private info:
- Names → replaced with `PERSON_abc123`
- Emails → replaced with `EMAIL_def456`
- Phone numbers → replaced with `PHONE_ghi789`
- etc.

So if you typed "Call Max Mustermann at max@company.com", the AI receives:
"Call PERSON_abc123 at EMAIL_def456"

The real values are saved in a private map (stored by session ID).

---

### Step 6 — Proxy sends to the real AI

The proxy forwards the pseudonymized message to the real AI
(Anthropic, Google, Groq, etc.) with your API key.

The AI never sees your real private data. It sees only the tokens.

---

### Step 7 — AI responds

The AI sends back an answer with the tokens in it, like:
"Sure, I'll contact PERSON_abc123 at EMAIL_def456 tomorrow."

---

### Step 8 — Proxy depseudonymizes the response

The proxy swaps the tokens back to real values using the saved map:
"Sure, I'll contact Max Mustermann at max@company.com tomorrow."

You see the real names. The AI never knew them.

---

### Step 9 — Response arrives in WebUI

WebUI shows you the final answer. To you it looks totally normal.

---

## Why the 401 error happens (your current bug)

```
WebUI sends key → proxy sees sk-ant- → routes to Anthropic
                                              ↓
                                       Anthropic says 401
                                       (key is invalid/expired)
```

The proxy routing worked correctly. The problem is Anthropic rejected the key.
Fix: go to **Admin Panel → Connections** → update the API key to a valid `sk-ant-...` key.

---

## What the Admin Panel settings actually control

| Setting | What it controls in the routing |
|---------|--------------------------------|
| Connection URL | Which machine receives your message first (should be the proxy) |
| API Key | Which AI the proxy routes to (detected from key prefix) |
| Model selected in chat | What you're asking the AI to use — must be a model that AI actually has |

---

## One line summary
Your message goes: WebUI → Privacy Proxy (hides private info) → Real AI (Claude/Gemini/etc.) → Privacy Proxy (restores private info) → back to you.
