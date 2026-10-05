---
STATUS: ready-for-impl
HANDOFF: implementer
NEXT: /implementer "execute webui-api-key"
---

# Tasks — WebUI API Key

Date: 2026-07-09
Based on: 01-spec.md
Mode: QUICK (no separate 03-design — the change is a config flip, not a
build)

## Ponytail summary

The upstream OWU API-key subsystem is already present in this fork.
Nothing has been stripped. The panel is hidden because `ENABLE_API_KEYS`
defaults to `False` and no env var / .env line sets it. The lazy fix is:
flip the flag, verify, done. No new UI, no new endpoint, no new API
client code.

If, and only if, verification proves the fork DOES strip something and the
panel stays hidden with the flag on → escalate to Task 5 (revert) and
raise it with Ahmed before touching Svelte.

---

## Phase 1 — Turn on the built-in flag

### Task 1.1 — Add `ENABLE_API_KEYS` to `.env.example`
- **File:** `.env.example`
- **What:** append `ENABLE_API_KEYS=True` with a one-line comment
  (`# enables Settings → Account → API keys panel`).
- **Test:** `grep ENABLE_API_KEYS .env.example` returns the line.
- **Depends on:** none.
- **Effort:** S · **Model:** sonnet · **[parallel with 1.2]**

### Task 1.2 — Add `ENABLE_API_KEYS` to `docker-compose.yaml` webui service
- **File:** `docker-compose.yaml` (webui service `environment:` block, ~L23)
- **What:** add `- ENABLE_API_KEYS=${ENABLE_API_KEYS:-True}`.
- **Test:** `docker compose config | grep ENABLE_API_KEYS` shows `True`.
- **Depends on:** none.
- **Effort:** S · **Model:** sonnet · **[parallel with 1.1]**

### Task 1.3 — Add flag to production compose(s) on cVM
- **File(s):** whatever compose file `/opt/garnet/` uses on the cVM
  (Ahmed to identify — likely a merged / overriding compose).
- **What:** same env var.
- **Test:** none in-repo — this is a deploy step, Ahmed handles.
- **Depends on:** 1.2.
- **Effort:** S · **Model:** none (Ahmed manual) · **[sequential]**
- **Note:** if this repo does not track the prod compose, mark this task as
  "handoff to Ahmed" — implementer must NOT ssh to cVM.

---

## Phase 2 — Confirm DB does not shadow the env

**Why:** webui.md warns "OWU writes env to `webui.db` on first boot, then reads
only from DB. DB overrides env." So setting the env var on an
already-initialized container may not take effect.

**Graphify patch (2026-07-09):** The admin API at
`POST /api/v1/auths/admin/config` (auths.py:L995) writes directly to
`app.state.config.ENABLE_API_KEYS` and persists it through OWU's
`PersistentConfig` mechanism. This is the **preferred path** — no SQL, no
restart, immediate effect. Use it instead of sqlite3 unless the container
is down.

### Task 2.1 — Flip the flag via Admin Settings UI (preferred) or sqlite3 fallback

**Preferred path (container running):**
- **Who:** Ahmed (admin credentials required).
- **What:** In the running Garnet UI: Admin → Settings → Auth → enable
  "API Keys" toggle → Save. This calls
  `POST /api/v1/auths/admin/config` with `ENABLE_API_KEYS: true`, writes
  through `PersistentConfig`, and takes effect immediately without restart.
- **Test:** `curl -H "Authorization: Bearer <admin-jwt>" \
  https://garnet.enclaive.cloud/api/v1/auths/admin/config`
  shows `"ENABLE_API_KEYS": true`.

**Fallback (container stopped or DB direct):**
```
sqlite3 /opt/garnet/data/webui.db \
  "UPDATE config SET data = json_set(data, '$.auth.enable_api_keys', json('true'))"
```
- **Test:** `curl .../api/v1/configs/` shows `auth.enable_api_keys: true`.

- **Depends on:** Phase 1.
- **Effort:** S · **Model:** none (Ahmed runs).

---

## Phase 3 — Grant permission to non-admin users (optional)

Blocked on open question 1 (Seb). Do NOT execute without Ahmed confirming
Seb's answer.

### Task 3.1 — If Seb says "all users": flip default in USER_PERMISSIONS
- **File:** Admin UI (`Admin → Settings → Users → Permissions →
  Features → API Keys`) OR `backend/open_webui/config.py` L1497 region
  where `USER_PERMISSIONS_FEATURES_API_KEYS` is defined.
- **What:** flip default to `True`. Prefer admin UI — no code change,
  no rebuild.
- **Test:** log in as a non-admin, open Settings → Account, panel visible.
- **Depends on:** Seb ok.
- **Effort:** S · **Model:** none if admin UI; sonnet if code path.

### Task 3.2 — If Seb says "admin-only": no-op
- Do nothing. Admin already has the panel by role. Task closes.

---

## Phase 4 — Verify end-to-end (mandatory before "done")

### Task 4.1 — curl smoke test
- **What:** as user who has the permission:
  1. Open Settings → Account, confirm "API keys" section visible.
  2. Click "Create new secret key", copy the `sk-...` value.
  3. `curl -H "Authorization: Bearer sk-..." https://garnet.enclaive.cloud/api/models`
     → expect 200 with model list.
- **Test:** both curls return 200.
- **Depends on:** Phase 1 + 2 + (3 if applicable).
- **Effort:** S · **Model:** none (Ahmed runs).

### Task 4.2 — Pseudonymization regression check
- **What:** curl a chat completion with a PII-loaded prompt using the API
  key. Read privacy-proxy logs on cVM.
- **Test:** proxy logs show `pseudonymize` fired for the prompt AND the
  response body contains the real name, not the token (depseudonymized).
  This proves API-key path == browser path through the proxy.
- **Depends on:** 4.1.
- **Effort:** S · **Model:** none (Ahmed runs).
- **Critical:** if pseudonymizer is bypassed, STOP and raise with Seb.
  The whole point of Garnet is PII interception.

### Task 4.3 — Third-party client check
- **What:** point one real client at Garnet. Recommend VS Code Continue
  extension: set `apiBase: https://garnet.enclaive.cloud/api`,
  `apiKey: sk-...`, model: any Garnet-enabled model. Send a chat.
- **Test:** completion returns, proxy logs show pseudonymization.
- **Depends on:** 4.2.
- **Effort:** S · **Model:** none (Ahmed runs).

### Task 4.4 — Confirm APIKeyRestrictionMiddleware is NOT blocking (new)
- **What:** confirm `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS` is `False`
  (the default). The middleware at `main.py:L1374` is always mounted; it
  only blocks requests when the restrictions flag is on. With it off, the
  middleware is a no-op for the `sk-` path. Verify the admin config curl
  from Task 2.1 shows `"ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS": false`.
- **Test:** admin config response confirms flag is off. If it is `true`,
  either turn it off via admin UI or check `API_KEYS_ALLOWED_ENDPOINTS`
  includes `/api/chat/completions` and `/api/models`.
- **Depends on:** 4.1.
- **Effort:** S · **Model:** none (Ahmed runs).

---

## Phase 5 — ONLY IF Phase 4.1 fails with flag on (fork stripped the panel)

Do not execute unless verification proves the fork removed something.
Given the file reads confirmed the gate is intact in Account.svelte,
this phase should not fire.

### Task 5.1 — Diff Account.svelte vs upstream OWU
- **What:** `git log --all --follow --oneline src/lib/components/chat/Settings/Account.svelte`
  → find any Garnet commit that touched the api-key section. If found,
  identify what was removed. Bring back to Ahmed before reverting.
- **Effort:** M · **Model:** sonnet.
- **Escalate:** any change here needs Seb sign-off.

---

## Global checks (run at end)

- [ ] `npm run build` succeeds (Svelte fork rebuild not needed for pure env
      changes, but run once if anything under `src/` was touched).
- [ ] Existing browser flow still works (regression): log in normally,
      send a chat — pseudonymization still fires, response streams.
- [ ] `pytest backend/open_webui/test/apps/webui/routers/test_auths.py -v`
      passes (upstream tests for api_key endpoints).
- [ ] No API key value written to any log line (`grep -i "sk-" logs/`
      returns nothing).
- [ ] `.env.example` line does not accidentally include a real key.
- [ ] k8s Helm values note added for mission2 (Ion): flag must land in
      Helm values.yaml under the webui env block. Add to
      `.claude/plan/mission2-k8s.md` as a follow-up if not already there.
- [ ] Admin config curl confirms `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS`
      is `false` (Task 4.4).

---

## Handoff to reviewer

When Phase 4 passes, hand off with:

```
/reviewer "vibe check webui-api-key — confirm no key leaks in logs,
no pseudonymizer bypass, no over-engineering beyond env-flag flip,
APIKeyRestrictionMiddleware not blocking valid requests"
```

## Handoff to implementer (starting point)

/implementer "execute webui-api-key"

Implementer:
1. Read 01-spec.md and this file.
2. Execute Phase 1 (code-only tasks 1.1, 1.2 in parallel).
3. Stop at Task 1.3 and hand back for Ahmed to deploy.
4. Ahmed runs Task 2.1 (admin UI toggle preferred over sqlite3).
5. Return to run Phase 3 based on Seb's answer.
6. Ahmed runs Phase 4 verification (including new Task 4.4).
7. Do NOT touch Svelte unless Phase 5 fires.

---

## Graphify + context7 patch — 2026-07-09

**What was added:**

1. **Task 4.4 (new)** — `APIKeyRestrictionMiddleware` check. Graphify surfaced
   `APIKeyRestrictionMiddleware` at `main.py:L1374` as a distinct node that was
   invisible to the previous grep scan. It is mounted unconditionally at L1416
   and runs for every `sk-` token. It blocks requests when
   `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS=True`. Since the plan leaves that flag
   off, the middleware should be a no-op — but it needs an explicit verification
   step so the implementer isn't surprised if paths are blocked after deployment.

2. **Task 2.1 — preferred path rewritten.** Graphify surfaced `AdminConfig`
   (auths.py:L963) and its `POST` endpoint at L995. Reading those lines confirmed
   a live admin API for flipping `ENABLE_API_KEYS` without restarting the container
   or writing SQL. The previous plan's Task 2.1 buried the admin UI mention in a
   note and led with sqlite3. Now admin UI is the primary path; sqlite3 is the
   fallback.

3. **Global checks** — added `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS` confirmation
   as a final checklist item.

**context7 MCP status:** CLI not available in this environment. Flag name
`ENABLE_API_KEYS` confirmed via direct grep of `config.py:L283-286`. No rename.

**Task count:** Phase 1: 3 tasks. Phase 2: 1 task. Phase 3: 2 conditional tasks.
Phase 4: 4 tasks (was 3 — added 4.4). Phase 5: 1 contingency task.
Total actionable tasks: 11 (9 real + 2 conditional). Previous count: 10.
