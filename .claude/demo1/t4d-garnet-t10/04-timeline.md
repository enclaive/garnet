# Canary Retest — Timeline and Instructions

Date: 2026-08-19
Build: commit `2472723a4` · tag `t4d-canary-1`

---

## Proposed timeline

| Step | Date | Owner |
|------|------|-------|
| Fixed build delivered | 2026-08-19 | Enclaive |
| T4D canary retest window | 2026-08-20 to 2026-08-22 | T4D |
| Results communicated to Enclaive | 2026-08-22 | T4D |
| 100-case pilot scheduling (if canary passes) | TBD | Joint |

---

## Canary retest — what T4D needs

**Endpoint:** `https://demo-1.garnet.enclaive.cloud`

**API key:** available from Garnet admin panel → Settings → Account → API Keys

**Model:** `gpt-5`

**Log capture (for [OUT USER] pre-provider evidence):**
```bash
# Run on cVM before each test
docker logs -f garnet-privacy-proxy-1 2>&1 | grep -E "IN  USER|OUT USER|→ LLM|ERROR"
```

---

## Pass criteria

| Check | Pass condition |
|-------|---------------|
| `case_id` and `reference_id` values | byte-identical to input — not replaced |
| German given names (Hendrik, Lasse, etc.) | replaced with `PERSON_xxx` |
| Weekday names (Montag, etc.) | unchanged — not tagged |
| JSON structure (keys, numbers, booleans) | intact — not mutated |
| Email addresses | replaced with `EMAIL_ADDRESS_xxx` |
| `[OUT USER]` log | no raw PII visible |
| Structured output response | valid JSON matching requested schema, real names restored |

---

## Technical fallback

If any canary case fails, Enclaive will revert the cVM to the pre-fix build
within 5 minutes by redeploying the frozen 2026-08-04 image:

```
harbor.enclaive.cloud/garnetdemo/privacy-proxy@sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d
```

No data loss. No configuration changes required. T4D will be notified immediately
and a revised timeline will follow.
