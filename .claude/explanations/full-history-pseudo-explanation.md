# Baby Explain — Full History Pseudonymization

**Generated:** 2026-07-12 22:00:00

---

## What is this feature?

Right now Garnet hides your private info (names, emails...) **only in the message you just typed**. All your old messages — and the AI's old replies — get sent to the cloud LLM **with real names visible**. This feature fixes that: every message in the conversation gets masked before leaving your network.

---

## Why are we building it?

If you say "Max works at Enclaive" in message 1, then ask "what does he do?" in message 5 — the LLM sees "Max" in the history. The privacy protection only covered message 5. Messages 1–4 leaked.

---

## How does it work? (simple version)

Imagine a post office that blacks out names on every letter before mailing it.

**Before (broken):**
```
Turn 1 user:      "Max works at Enclaive"        ← real name, sent to cloud ❌
Turn 1 assistant: "Max is an engineer"            ← real name, sent to cloud ❌
Turn 2 user:      "what does he do?"              ← no name, fine ✓
Turn 3 user:      "tell me more about Max"        ← masked ✓  (only this one)
```

**After (fixed):**
```
Turn 1 user:      "PERSON_cc75010d works at ORGANIZATION_bd3a68a5"  ✓
Turn 1 assistant: "PERSON_cc75010d is an engineer"                  ✓
Turn 2 user:      "what does he do?"                                ✓
Turn 3 user:      "tell me more about PERSON_cc75010d"              ✓
```

The LLM still understands the conversation — it sees the same token everywhere. When it replies with that token, Garnet swaps it back to "Max" before showing you.

**The speed trick (cache):** Masking text is slow (spaCy AI scan). Turn 1's text gets masked and saved. Turn 2 reuses the saved result — no re-scan. No matter how long the conversation, only **1 new scan per message**.

---

## The jobs

### Job 1 — Add a memory box (cache)
**What:** One small dictionary (like a notebook) next to the existing one. Stores: "this text was already masked → here's the masked version."
**Why:** Without it, every new prompt would re-scan ALL previous messages. A 20-turn chat would run spaCy 20 times per prompt instead of once.
**Hard part:** None — it's 2 lines of code.

### Job 2 — Add the masking helper function
**What:** A small function `_pseudo_with_cache` — checks the notebook first, if found returns the saved result, if not runs the mask scan and saves it.
**Why:** Reusable in all places that need to mask text.
**Hard part:** Making sure an empty string doesn't crash it.

### Job 3 — Delete the old broken code
**What:** Remove lines 402–411 from `main.py`. These lines were actively **un-masking** old AI replies (restoring real names) before sending to the cloud. The exact opposite of what we want.
**Why:** It was the root cause of the leak. Delete, not patch.
**Hard part:** Nothing — it's a deletion.

### Job 4 — Add the new history masking loop
**What:** Loop over all old messages (not the latest one), mask each one using the helper, skip ones that look like system instructions.
**Why:** This is the actual fix — all history gets masked before leaving.
**Hard part:** Getting the conditions right so we don't double-mask or accidentally skip a message.

### Job 5 — Safety check (run FIRST)
**What:** Test if the AI scanner (spaCy) accidentally re-tags already-masked tokens like `PERSON_cc75010d` as a new person name.
**Why:** If it does, we'd get `PERSON_aaaabbbb` instead of `PERSON_cc75010d` — breaking the conversation flow.
**Hard part:** If it fails, a 2-line guard is already designed: "if text already has tokens → skip scanning".

### Job 6 — Route the last message through the same cache too
**What:** The latest message (the one you just typed) also uses the cache now. If you resend the same message, no re-scan.
**Why:** Free performance improvement, zero behavior change.
**Hard part:** None.

---

## What could go wrong?

- **spaCy re-tags already-masked tokens** → Job 5 catches this before anything ships. If it fails, a 2-line fix is already designed.
- **Middle message is a system instruction** (contains `### Task:`) → it gets skipped, not masked. Same rule as the last message already uses.
- **Double-masking** → the loop only touches `messages[:-1]`, the existing block handles `messages[-1]`. No overlap.

---

## What does success look like?

1. Send 3 messages — message 1 contains "Max Mustermann"
2. Check proxy logs — all 3 messages show `PERSON_` tokens, not "Max"
3. The AI's reply in the browser still shows "Max Mustermann" (Garnet restored it)
4. Send the exact same message again — proxy log shows "cache hit", not a new spaCy scan

---

## Who needs to approve?

**Seb: YES** — this changes how all conversation history is handled before sending to the LLM. Structural proxy change.
**Ion / Nicu: NO** — no infra or registry changes.

---

## One line summary

Garnet now hides private info in ALL messages of a conversation before sending to the cloud AI, not just the message you just typed.
