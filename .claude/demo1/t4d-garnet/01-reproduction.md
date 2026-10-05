# Reproduction Confirmation

Date: 2026-08-12
Reference: T4D diagnostic package 2026-08-05
Build under test: commit `dd9a4c29a` · image `sha256:33bbd35ccc84`

All seven cases from the diagnostic package were reproduced against the
configuration active on 2026-08-04.

Reproduction completed: 2026-08-06
Method: live proxy, same provider (Ollama / llama3.2:3b), same session setup.
No customer data, production secrets, or TMS structures were used.

| Case | Result | Finding |
|------|--------|---------|
| P1B-BP-002-V2 | ✅ reproduced | Full PERSON leak — "Hendrik" not detected, forwarded verbatim |
| P1B-BP-001-V1 | ✅ reproduced | UUID mutated + "Adelbach" tagged LOCATION instead of PERSON |
| P1B-BP-005-V5 | ✅ reproduced | Partial PERSON leak — "Lasse" kept, "Farah Marchetti" tagged |
| P1B-BP-009-V1 | ✅ reproduced | "Montag" tagged LOCATION + "Adelbach" tagged LOCATION |
| P1B-BP-096-V0 | ✅ reproduced | JSON structure corrupted, text body truncated |
| P1B-BP-030-V6 | ✅ reproduced | UUID mutated on email case, exact hash match |
| P1B-BP-061-V5 | ✅ reproduced | Neutral control — byte-identical, no entities (expected) |

Hash matches on tokens (e.g. `LOCATION_d1bfe8a1` for "Adelbach",
`LOCATION_b703fc6a` for "Montag") confirm the same code path and
configuration as T4D's original run.

No entity filter was active during T4D's test session — all entity types
including PERSON were enabled. The PERSON leaks are NER failures, not a
filter misconfiguration.
