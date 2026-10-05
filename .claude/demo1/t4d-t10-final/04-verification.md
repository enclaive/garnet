# How T4D Can Verify the Fix

Date: 2026-08-19

---

## Test channels

**Defect cases (JSON pasted into chat)** — use the Open WebUI at `https://demo-1.garnet.enclaive.dev`. Log in, select `gpt-5`, paste each test case, submit.

**Structured Outputs** — API-only. Use curl or any OpenAI-compatible client as shown in `02-structured-outputs.md`.

---

## What "pass" looks like — from the response

For each defect case, T4D checks the response the client received:

| Check | Pass condition |
|-------|---------------|
| `case_id` / `reference_id` / any UUID | byte-identical to the input |
| JSON structure (keys, numbers, booleans, nesting) | unchanged |
| PII values (names, emails) | either restored to original in the model's answer, or absent from the response body |

---

## What "pass" looks like — from the proxy log (pre-provider evidence)

For each request the proxy records the raw input, the pseudonymized payload actually forwarded to the provider, and the provider endpoint. Together these prove no raw PII left the container.

T4D confirms:
- The pseudonymized payload contains no raw PII (names, emails, etc. all replaced with tokens).
- The provider endpoint is the expected one for the selected model.
- No error is recorded in the same request window.

Enclaive provides the excerpts during a witnessed session or through the read-only access below.

---

## Access to the cVM for log inspection

Enclaive can grant T4D access to the demo-1 cVM for the duration of the canary retest so the logs can be inspected directly. Two options:

1. **Witnessed session** — Enclaive engineer streams the proxy logs while T4D issues the test cases from their side. Both sides watch the same output in real time.
2. **Read-only SSH** — an SSH key from T4D is added to a scoped read-only account on the cVM (log access only, no container control). Preferred if T4D wants unassisted access during the retest window.

Excerpts from either channel can be copied verbatim into the canary result report.
