---
STATUS: ready-for-review
HANDOFF: ahmed
NEXT: review, then say "execute webui-api-key" to hand off to implementer
---

# Spec — WebUI API Key in Settings/Account

Date: 2026-07-09
Mode: QUICK

## Problem

Users cannot generate a personal API token from Settings → Account. Teammates want to
connect third-party tools (VS Code Continue/Cline, browser extensions, custom clients)
to Garnet with a stable Bearer token, without copying the short-lived JWT out of
localStorage.

## Current state (verified via graphify + targeted read)

The Open WebUI fork already ships a complete API-key subsystem — nothing has been
patched out of the fork. The UI is hidden purely by config:

Backend (unchanged from upstream OWU, present in this fork):
- `backend/open_webui/routers/auths.py` L1156-1191 — three endpoints:
  - `POST /api/v1/auths/api_key` (generate)
  - `DELETE /api/v1/auths/api_key` (revoke)
  - `GET /api/v1/auths/api_key` (fetch current)
- `backend/open_webui/utils/auth.py` L264 `create_api_key()`, L383 `get_current_user_by_api_key()`
  — validates `Authorization: Bearer sk-...` on every request.
- `backend/open_webui/config.py` L283 `ENABLE_API_KEYS` — env var, defaults to **`False`**.
- `backend/open_webui/config.py` L1497 per-user permission `features.api_keys`
  (default from `USER_PERMISSIONS_FEATURES_API_KEYS`).
- `backend/open_webui/main.py` L1374 `APIKeyRestrictionMiddleware` — enforces endpoint
  allowlist when `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS` is on. Only fires for `sk-`
  tokens. Also sets `request.state.enable_api_keys` per request at L1453.
- `backend/open_webui/routers/auths.py` L935 `GET /api/v1/auths/admin/config` and
  L995 `POST /api/v1/auths/admin/config` — live admin API that reads and writes
  `ENABLE_API_KEYS` into `app.state.config` (bypasses the DB-shadow problem, takes
  effect immediately without restart). This is the toggle the admin Settings UI calls.
- `backend/open_webui/routers/auths.py` L1158 — the generate endpoint itself also
  guards server-side: `if not request.app.state.config.ENABLE_API_KEYS or ...` — so
  even if the frontend gate is removed the server rejects key generation when flag is
  off.
- `backend/open_webui/main.py` L2052 `get_app_config()` — returns
  `features.enable_api_keys` which the frontend reads as `$config.features.enable_api_keys`.
  This is the exact pipeline: flag on backend → `get_app_config` response → Svelte
  store `$config` → Account.svelte gate.

Frontend (fork-local file, unmodified vs upstream):
- `src/lib/components/chat/Settings/Account.svelte` L112-116 (fetch) and L257, L328
  (render) gate the panel on:
  ```
  ($config?.features?.enable_api_keys ?? true) &&
  (user?.role === 'admin' || (user?.permissions?.features?.api_keys ?? false))
  ```
  Note: the client defaults to `true` when the flag is missing, so if the
  panel is invisible today the backend is actively reporting `false`.
- `src/lib/apis/auths/index.ts` — `getAPIKey`, `createAPIKey`, `deleteAPIKey`
  helpers already exist.

Config wiring (deploy):
- `docker-compose.yaml` env block has no `ENABLE_API_KEYS` line (confirmed line 23).
- `.env.example` has no `ENABLE_API_KEYS` (confirmed).
- OWU writes env to `webui.db` on first boot then reads from DB (see webui.md
  "Config gotcha"). So flipping the env var on an existing container is a
  no-op — must also update the DB row **or** use the admin Settings UI to
  flip `auth.enable_api_keys` (preferred — no SQL, immediate effect via
  `POST /api/v1/auths/admin/config`).

Conclusion: this is a config toggle, not a code change. Ponytail applies.

## Desired behavior

- Logged-in user opens Settings → Account, sees an "API keys" section.
- Clicks "Create new secret key" → gets `sk-...` token, one-click copy.
- `curl -H "Authorization: Bearer sk-..." https://garnet.enclaive.cloud/api/models`
  returns 200 (or the OWU model list).
- Extension (e.g. Continue in VS Code, pointed at Garnet's OpenAI-compatible
  endpoint) authenticates with that token and gets chat completions.
- Requests carrying the API key still route through the privacy-proxy — PII
  interception must NOT be bypassed (see open question 4).

## Out of scope

- New UI. OWU already renders the panel; do not build a parallel one.
- Multiple keys per user. OWU stores ONE `api_key` per user
  (`Users.update_user_api_key_by_id` — single column). Multi-key support = big
  upstream change, not needed now.
- Custom expiry / rotation policy. OWU keys are static until revoked. If Seb
  wants expiry, that's a separate spec.
- Endpoint restrictions (`ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS` /
  `APIKeyRestrictionMiddleware`) — leave off unless Seb asks. Middleware is already
  wired in `main.py`; just keep the flag off.

## Acceptance criteria

- [ ] `ENABLE_API_KEYS=True` set in cVM env AND persisted (env change survives
      OWU's DB write-on-boot behavior, or admin toggles via admin Settings UI).
- [ ] Non-admin user role has `features.api_keys=true` in USER_PERMISSIONS
      (or admin explicitly grants it via admin panel).
- [ ] Non-admin logs in, opens Settings → Account, sees "API keys" section
      with a Create button.
- [ ] Generating a key returns an `sk-...` string, saved on the user record.
- [ ] `curl -H "Authorization: Bearer <key>" https://garnet.enclaive.cloud/api/models`
      returns HTTP 200 with model list.
- [ ] Same curl to a chat completion endpoint gets a response AND that
      response was pseudonymized-then-depseudonymized (verify proxy logs show
      the request went through pseudonymizer).
- [ ] One 3rd-party client (VS Code Continue or plain curl script) works
      end-to-end with the token.
- [ ] Existing JWT-based browser flow still works (regression).

## Constraints (Garnet rules)

- Must not remove `body["stream"] = False` on non-streaming paths.
- Must not expose proxy on `0.0.0.0`.
- Must not log the API key (headers stay unlogged — CLAUDE.md rule).
- API-key traffic must traverse the pseudonymizer (open question 4).
- `APIKeyRestrictionMiddleware` is already mounted — do not remove it. Keep
  `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS=False` (default) so it passes all paths.
- Seb approval needed: **YES** — this exposes a new inbound auth surface and
  a new pathway for third-party clients into Garnet. Seb should confirm
  whether he wants this available to all users or admin-only for now.

## Open questions

- [ ] **Seb — scope:** should `features.api_keys` default `True` for all
      registered users, or admin-only until we see who actually needs it?
      (Ponytail default: admin-only, promote later.)
- [ ] **Seb — expiry:** OWU keys are eternal until revoked. Acceptable for
      demo/internal? If not, needs upstream patch.
- [ ] **Ahmed — endpoint restrictions:** `APIKeyRestrictionMiddleware` is wired
      at `main.py:L1416`. Leave `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS=False`
      (all endpoints allowed) or lock to `/api/chat/completions`, `/api/models`?
      Off is simpler; restrict later if abuse surfaces.
- [ ] **Seb — pseudonymizer path:** API-key requests hit OWU backend →
      `openai.py` router → privacy-proxy. Same path as browser. Confirmed
      pseudonymization still applies (proxy is transparent to auth method).
      Verify in acceptance test 6. If a client hits the proxy DIRECTLY
      (skipping OWU), pseudonymization still runs but there is no OWU auth
      check — is that OK, or should the proxy also require an OWU-issued
      token? (Recommend: for now, only expose `/api/*` via OWU;
      privacy-proxy stays internal.)
- [ ] **Ion — k8s:** for mission2, the `ENABLE_API_KEYS=True` env needs to
      land in the Helm values, not just docker-compose. Flag in tasks.

## Handoff

Review this spec, then run `/implementer "execute webui-api-key"` to build.

---

## Graphify + context7 patch — 2026-07-09

**What was added:**

1. `APIKeyRestrictionMiddleware` (`main.py:L1374`) — graphify surfaced this node,
   which was invisible to the previous grep-based scan. It is already mounted at
   `main.py:L1416` and runs for every `sk-` token request. Its behavior is gated by
   `ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS` (off by default). Added to Current State
   and Constraints so the implementer knows not to remove it or accidentally enable
   the restrictions flag.

2. `request.state.enable_api_keys` set at `main.py:L1453` — per-request middleware
   copies the flag value into request state. Not a new constraint but documents a
   second enforcement layer beyond the UI gate.

3. Admin toggle API path (`auths.py:L935/L995`) — graphify's `AdminConfig` node led
   to reading these endpoints. They let an admin flip `ENABLE_API_KEYS` live via
   `POST /api/v1/auths/admin/config` without an env var restart. This is the
   **preferred approach for the existing cVM** (avoids SQL and sidesteps the
   DB-shadow problem). Updated Current State and Task 2.1 in 05-tasks.md to
   prefer admin UI over sqlite3.

4. Server-side guard at `auths.py:L1158` — confirmed the generate endpoint checks
   the flag itself; the UI gate is not the only protection. Added for completeness.

5. `get_app_config()` pipeline (`main.py:L2052`) — confirmed the exact data path:
   `app.state.config.ENABLE_API_KEYS` → `features.enable_api_keys` in the config
   response → `$config.features.enable_api_keys` in Svelte. This closes the loop
   on how flipping the flag via admin API immediately makes the frontend panel appear
   (no rebuild needed).

**context7 MCP status:** CLI invocation syntax mismatch (not available as CLI tool
in this environment). Flag name `ENABLE_API_KEYS` confirmed correct via direct grep
of `config.py:L283-286`. No rename detected.

**What was corrected:** Out of scope section updated to name `APIKeyRestrictionMiddleware`
explicitly. Constraints section updated to note the middleware must stay mounted.
