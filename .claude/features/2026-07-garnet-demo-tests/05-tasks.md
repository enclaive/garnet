---
STATUS: ready-for-impl
HANDOFF: implementer
NEXT: /implementer "execute garnet-demo-tests"
---

# Tasks — Garnet Demo Test Suite
Date: 2026-07-21
Scope: Seb's 3 demo checks (privacy, RAG, speed) as a single runnable script

---

## Context

Existing file: `backend/privacy_proxy/app/test_proxy.py`
- Already covers T01–T20: health, /analyze, /vault/scan, unit-level pseudonymizer checks
- Does NOT cover: end-to-end chat completion (PII round-trip), RAG, or latency

This task suite adds a second script alongside test_proxy.py — `backend/privacy_proxy/app/test_demo.py`.
It runs the 3 missing checks that Seb needs for the customer demo.
All output goes to stdout → captured by Docker/k8s logs automatically.

---

## Phase 1 — End-to-end privacy check (Seb requirement a)

### Task 1.1 — Write T-PRIV: chat completion pseudonymizes and restores PII
- **File:** `backend/privacy_proxy/app/test_demo.py` (create)
- **What:** POST to `/v1/chat/completions` (the proxy endpoint, same path OWU uses) with a message
  containing a real name + email. Verify: (1) the LLM never saw the real values — check proxy logs
  for `log_out_user` token pattern, (2) the response returned to the caller has the real values
  restored (depseudonymization). Use a mock LLM backend so no real API key is needed at test time.
- **How it works:**
  - Start a tiny `http.server.HTTPServer` in a thread that acts as a fake OpenAI backend.
  - The fake backend captures the request body and returns a canned response that echoes back
    the pseudonymized token (e.g. `"Hello PERSON_cc75010d"`).
  - After the proxy processes the response, the caller should receive the real name restored.
  - The fake backend URL is injected via env var `OPENAI_API_URL=http://localhost:<port>`.
  - Assert: request body received by fake backend does NOT contain the original name/email.
  - Assert: response body returned by proxy DOES contain the original name.
- **Session header:** include `x-session-id: test-priv-001` so mapping store scopes correctly.
- **Log output:** structured line `[DEMO] T-PRIV PASS/FAIL — <detail>`
- **Test:** assertion block at bottom of script, prints PASS/FAIL, exits non-zero on any FAIL
- **Depends on:** none
- **Effort:** M
- **Model:** sonnet
- **[sequential]**

### Task 1.2 — Add privacy-off passthrough variant
- **File:** `backend/privacy_proxy/app/test_demo.py` (same file)
- **What:** Repeat T-PRIV but with `x-garnet-entities: ""` (privacy disabled path). Verify the
  real name passes through unchanged to fake backend and response is returned verbatim. Confirms
  the toggle works for non-PII customers.
- **Log output:** `[DEMO] T-PRIV-OFF PASS/FAIL`
- **Depends on:** Task 1.1 (same fake server)
- **Effort:** S
- **Model:** sonnet
- **[sequential]**

---

## Phase 2 — RAG check (Seb requirement b)

### Task 2.1 — Write T-RAG: upload doc, ask question, get answer from doc
- **File:** `backend/privacy_proxy/app/test_demo.py` (same file)
- **What:** Full RAG round-trip via Open WebUI API (not the proxy directly — RAG lives in OWU).
  Steps:
  1. Authenticate against OWU (`POST /api/v1/auths/signin`) using env vars
     `GARNET_TEST_USER` / `GARNET_TEST_PASS`. Skip T-RAG with a WARN log if creds not set.
  2. Upload a small known text file via `POST /api/v1/files/` (multipart). Content: a 3-sentence
     paragraph with a unique made-up fact (e.g. "The Garnet throughput limit is 42 requests per second.").
  3. Create a knowledge base via `POST /api/v1/knowledge/` and add the file to it.
  4. Create a chat with the knowledge base attached and send the question
     "What is the Garnet throughput limit?" via `POST /api/v1/chats/` or the OWU chat API.
  5. Assert the response contains "42" (the fact from the doc).
  6. Clean up: delete the file and knowledge base via DELETE endpoints.
- **Notes:**
  - OWU base URL from env `GARNET_OWU_URL` (default `http://localhost:3000`).
  - Use `urllib.request` only — no new deps, matching test_proxy.py style.
  - If OWU is unreachable, skip with `[DEMO] T-RAG SKIP — OWU not reachable` and continue.
- **Log output:** `[DEMO] T-RAG PASS/FAIL — <detail>`
- **Depends on:** none (independent of Phase 1)
- **Effort:** M
- **Model:** sonnet
- **[parallel]** (can be written in parallel with Phase 1 tasks)

---

## Phase 3 — Speed check (Seb requirement c)

### Task 3.1 — Write T-SPEED: measure time-to-first-token vs baseline
- **File:** `backend/privacy_proxy/app/test_demo.py` (same file)
- **What:** Send a chat completion request through the full proxy stack (real LLM backend, streaming)
  and measure wall-clock time from request send to first SSE `data:` chunk received.
  - Use env var `GARNET_TEST_API_KEY` for the LLM API key. Skip with WARN if not set.
  - Use env var `GARNET_TEST_MODEL` (default `gpt-4o-mini`) — cheap, fast, representative.
  - Proxy URL: `GARNET_PROXY_URL` (default `http://localhost:11435`).
  - Send a short neutral prompt: "Say hello in one sentence."
  - Measure TTFT using `time.monotonic()` around the streaming read.
  - Threshold: TTFT < 8 seconds → PASS (ChatGPT UI p90 is ~3-5s; 8s allows network + pseudo overhead).
  - Also log total response time and token count (count `data:` lines in SSE stream).
  - Print: `[DEMO] T-SPEED TTFT=<ms>ms total=<ms>ms tokens=<n> PASS/FAIL`
- **Threshold rationale:** 8s is deliberately loose for a demo environment. Seb can tighten it.
  Add a comment: `# ponytail: TTFT_THRESHOLD_MS = 8000 — tighten for prod SLA`
- **Depends on:** none (can run standalone)
- **Effort:** S
- **Model:** sonnet
- **[parallel]**

---

## Phase 4 — Script shell, runner, summary

### Task 4.1 — Wire all tests into one runnable script with summary block
- **File:** `backend/privacy_proxy/app/test_demo.py` (finalize)
- **What:**
  - All three test phases run in order when `python3 app/test_demo.py` is executed.
  - Summary block at bottom (matching test_proxy.py style):
    ```
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    [DEMO RESULT] 3/3 passed — 0 failed
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ```
  - Exit code: `sys.exit(1)` if any FAIL, `sys.exit(0)` on all PASS/SKIP.
  - SKIPs do not count as failures (missing creds or OWU down = skip, not fail).
- **Depends on:** Tasks 1.1, 1.2, 2.1, 3.1
- **Effort:** S
- **Model:** sonnet
- **[sequential]**

### Task 4.2 — Add one-liner run commands to script docstring
- **File:** `backend/privacy_proxy/app/test_demo.py` (top docstring)
- **What:** Add the exact commands Ahmed runs, covering both deploy modes:
  ```python
  """
  Garnet Demo Test Suite — covers Seb's 3 demo requirements:
    (a) Privacy: PII pseudonymized before LLM, restored in response
    (b) RAG: upload doc, ask question, get answer from doc
    (c) Speed: TTFT < 8s vs ChatGPT baseline

  Docker Compose:
    docker exec garnet-privacy-proxy-1 python3 app/test_demo.py

  Kubernetes:
    kubectl exec -n garnet deploy/privacy-proxy -- python3 app/test_demo.py

  With real LLM + RAG (full check):
    GARNET_TEST_API_KEY=sk-... GARNET_TEST_USER=admin GARNET_TEST_PASS=... \
    docker exec -e GARNET_TEST_API_KEY -e GARNET_TEST_USER -e GARNET_TEST_PASS \
      garnet-privacy-proxy-1 python3 app/test_demo.py

  Env vars:
    GARNET_PROXY_URL    proxy base URL         (default: http://localhost:11435)
    GARNET_OWU_URL      Open WebUI base URL    (default: http://localhost:3000)
    GARNET_TEST_API_KEY LLM API key for T-SPEED (required for speed test)
    GARNET_TEST_MODEL   LLM model              (default: gpt-4o-mini)
    GARNET_TEST_USER    OWU admin user email   (required for T-RAG)
    GARNET_TEST_PASS    OWU admin password     (required for T-RAG)
  """
  ```
- **Depends on:** Task 4.1
- **Effort:** S
- **Model:** sonnet
- **[sequential]**

---

## Phase 5 — Verify existing test_proxy.py still passes

### Task 5.1 — Smoke-run test_proxy.py and confirm no regressions
- **File:** none (verification step only)
- **What:** Run existing test_proxy.py inside the container after test_demo.py is added.
  Confirm all T01–T20 still pass. Fix anything broken by the new file (unlikely — no shared state).
- **Command:**
  ```bash
  docker exec garnet-privacy-proxy-1 python3 app/test_proxy.py
  ```
- **Pass criterion:** `[RESULT] 20/20 passed — 0 failed` (or current passing count)
- **Depends on:** Task 4.1
- **Effort:** S
- **Model:** sonnet
- **[sequential]**

---

## Global checks (run at end)

- [ ] `docker exec garnet-privacy-proxy-1 python3 app/test_proxy.py` — existing suite passes
- [ ] `docker exec garnet-privacy-proxy-1 python3 app/test_demo.py` — new demo suite runs
- [ ] T-PRIV PASS without any real API key (uses fake backend)
- [ ] T-RAG SKIP (not FAIL) when `GARNET_TEST_USER` not set
- [ ] T-SPEED SKIP (not FAIL) when `GARNET_TEST_API_KEY` not set
- [ ] All output lines visible in `docker logs garnet-privacy-proxy-1`
- [ ] Exit code 0 when all pass/skip, exit code 1 when any fail

---

## What is NOT in scope (ponytail)

- pytest / test framework — `urllib.request` + `assert` only, matching test_proxy.py style
- CI integration — separate task, not needed for demo
- Parallel test execution — sequential is fine for a demo script
- Performance regression baseline storage — print to logs, human reads it
- Load testing / sustained throughput — T-SPEED is one request, not a benchmark
