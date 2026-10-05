# Remediation Questions — Direct Answers

Date: 2026-08-12
Reference: T4D diagnostic package 2026-08-05
Build under test: commit `dd9a4c29a` · image `sha256:33bbd35ccc84`

---

## Q1 — Can you reproduce all seven cases against the configuration active on 2026-08-04?

Yes. All seven cases were reproduced against the frozen configuration active on
2026-08-04 (commit `dd9a4c29a`, image `sha256:33bbd35ccc84`). Reproduction was
completed on 2026-08-06 using the live proxy with the same provider (Ollama /
llama3.2:3b) and the same session setup. No customer data or TMS structures
were used.

| Case | Result | Finding |
|------|--------|---------|
| P1B-BP-002-V2 | Reproduced | Full PERSON leak — "Hendrik" not detected, forwarded verbatim |
| P1B-BP-001-V1 | Reproduced | UUID mutated + "Adelbach" tagged LOCATION instead of PERSON |
| P1B-BP-005-V5 | Reproduced | Partial PERSON leak — "Lasse" kept, "Farah Marchetti" tagged |
| P1B-BP-009-V1 | Reproduced | "Montag" tagged LOCATION + "Adelbach" tagged LOCATION |
| P1B-BP-096-V0 | Reproduced | JSON structure corrupted, text body truncated |
| P1B-BP-030-V6 | Reproduced | UUID mutated on email case, exact hash match |
| P1B-BP-061-V5 | Reproduced | Neutral control — byte-identical, no entities (expected) |

Token hashes (`LOCATION_d1bfe8a1` for "Adelbach", `LOCATION_b703fc6a` for
"Montag") match T4D's original run exactly, confirming the same code path and
configuration.

---

## Q2 — Which Garnet, NER, policy and language-model versions and thresholds were active?

| Component | Version |
|-----------|---------|
| Git commit | `dd9a4c29a` |
| Branch | `demo1` |
| Proxy image digest | `sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d` |
| presidio-analyzer | 2.2.364 |
| spaCy | 3.7.5 |
| German NER model | de-core-news-md 3.7.0 |
| English NER model | en-core-web-md 3.7.1 |

No entity filter was active during T4D's test session. All entity types were
enabled: PERSON, ORGANIZATION, EMAIL_ADDRESS, IBAN_CODE, PHONE_NUMBER, ID,
LOCATION. No confidence threshold was configured — all detected entities were
accepted.

---

## Q3 — Can processing be constrained to annotated JSON values so that keys, UUIDs, identifiers, enums, numbers and booleans remain byte-identical?

Yes. The root cause is that the proxy serialized the entire request body to a
flat string before passing it to the NER pipeline. The pipeline processed JSON
keys, UUID values, colons, and brackets as undifferentiated text, causing UUID
hex patterns to be matched as ID entities and replaced. Replacement shifted byte
offsets and broke JSON structure on re-parse.

The fix is a JSON-aware walker that pseudonymizes only string values at known
text-bearing fields (`text`, `messages[].content`, `input`, `prompt`). All
other fields — keys, UUIDs, identifiers, numbers, booleans, enums — pass
through byte-identical. This fix is targeted for delivery at T+10 (2026-08-19).

---

## Q4 — What root cause explains the complete and partial German PERSON leaks, and which fix addresses them?

Three distinct causes produced the PERSON leaks:

**A1 — Short German given names not detected**
The active German NER model (`de_core_news_md`) relies heavily on surrounding
syntactic context. Isolated short given names at sentence start produce zero
entities: "Hendrik" alone → 0 detections. "Hendrik Öztürk" → correctly tagged.
The fix is to switch to `de_core_news_lg`, which is already installed in the
container and handles short isolated names correctly. Change is one line in the
pseudonymizer configuration.

**A2 — LOCATION overrides PERSON on overlapping spans**
The overlap resolver assigned higher priority to LOCATION than to PERSON. When
spaCy fired both PERSON and LOCATION on the same span (German surnames ending
in place-name patterns such as "-bach"), LOCATION always won. "Adelbach" was
tagged `LOCATION_d1bfe8a1` instead of PERSON on every occurrence. The fix is
to remove LOCATION from the high-priority set, so PERSON is no longer
overridden. Change is one line.

**C — German weekdays tagged as LOCATION**
spaCy's German model tags weekday names as LOCATION due to training data
patterns. "Montag" → `LOCATION_b703fc6a` on every occurrence. The fix is a
seven-entry denylist applied after NER analysis that rejects known non-PII
tokens. No model change required.

All three fixes are targeted for delivery at T+10 (2026-08-19).

---

## Q5 — What independent pre-provider capture or equivalent verifiable evidence can be enabled for a retest?

The proxy emits two structured log lines per request that together constitute
a pre-provider capture:

- `[IN  USER]` — the raw user message as received from the client, before any
  processing. Contains the original PII.
- `[OUT USER]` — the pseudonymized message after the privacy pipeline, before
  it is forwarded to the LLM provider. Contains only tokens, no raw PII.

The `[→ LLM]` line confirms the provider endpoint and model the pseudonymized
body was sent to.

Example from live system:

```
[IN  USER] Am Montag hat Adelbach einen Termin mit Hendrik Öztürk bei Enclaive.
[OUT USER] Am LOCATION_b703fc6a hat PERSON_d1bfe8a1 einen Termin mit PERSON_cc75010d bei ORGANIZATION_bd3a68a5.
[→ LLM   ] https://api.openai.com/v1/responses | model=gpt-5 | pseudo=78ms
```

For each canary case, T4D can verify from the `[OUT USER]` line that no raw PII
appears in what was forwarded to the provider. Logs are written to container
stdout and captured via `docker logs --follow` during a witnessed test session.

---

## Q6 — Immutable version identifier, delivery timeline, and rollback plan

**Delivery timeline:** T+10 — 2026-08-19

The fixed build will include all four defect class fixes (A1, A2, B, C). Once
built and pushed to Harbor, the immutable image digest and commit SHA will be
provided to T4D as the canary retest baseline.

The frozen baseline for rollback is the configuration active on 2026-08-04:
commit `dd9a4c29a`, image `sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d`.
If the canary retest on the fixed build identifies a regression, the cVM can
be reverted to this exact image by pulling the pinned digest from Harbor and
restarting the container. No configuration changes are required for rollback.

The fixed build identifier will be confirmed in the T+10 delivery mail
(2026-08-19).
