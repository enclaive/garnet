# Fixed Build Reference — T+10 Delivery

Date: 2026-08-19
Reference: T4D diagnostic package 2026-08-05

---

## Immutable build identifier

| Field | Value |
|-------|-------|
| Git commit | `2472723a4` |
| Git tag | `t4d-canary-1` |
| Branch | `demo1upgrade` |
| Proxy image | `harbor.enclaive.cloud/garnetdemo/privacy-proxy:2472723a4` |
| Image digest | `sha256:165e8bfc` |
| Pushed to Harbor | 2026-08-19 11:57 |

This is the build against which T4D should run the 10-case canary retest.

---

## What changed from the T+5 baseline

The T+5 baseline was commit `dd9a4c29a` (image `sha256:33bbd35ccc84`).

The following commits are included in the T+10 build on top of that baseline:

| Commit | Fix |
|--------|-----|
| `5f2dbe7e9` | Structured Outputs: convert `response_format` → `text.format` for Responses API |
| `0b6c95dc1` | GLiNER zero-shot NER added for German person/location disambiguation |
| `2472723a4` | UUID fragment protection: raise GLiNER threshold to 0.5, skip UUID hex spans in entity detection |

---

## Technical fallback

If the canary retest identifies a regression, the cVM can be reverted to the pre-fix state by redeploying the frozen 2026-08-04 image:

| Field | Value |
|-------|-------|
| Fallback image | `harbor.enclaive.cloud/garnetdemo/privacy-proxy@sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d` |
| Rollback command | `docker compose pull && docker compose up -d` with prior digest pinned |
| Estimated time | < 5 minutes |
| Data impact | None — no persistent state in the proxy container |
