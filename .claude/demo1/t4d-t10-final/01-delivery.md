# T+10 Delivery

Date: 2026-08-19

---

## Testable fix — frozen corrected configuration

| Field | Value |
|-------|-------|
| Proxy image | `harbor.enclaive.cloud/garnetdemo/privacy-proxy:04f1c2ee9` |
| Endpoint | `https://demo-1.garnet.enclaive.dev` |

---

## Timeline

Ready for T4D's 10-case canary retest from 2026-08-20.

Per the agreed procedure, the retest must pass 10 out of 10. If it does, the 100-case pilot will be scheduled separately.

---

## Technical fallback

If the retest identifies a regression, the proxy can be reverted to the prior frozen image within five minutes. No configuration changes required. No data loss.
