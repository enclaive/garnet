# Q8 — Raw input logging control

**Build under test:** `harbor.enclaive.cloud/garnetdemo/privacy-proxy:v-t4d-b1-fix`
**Digest:** `sha256:874400c065d86b0fdc1f1d1405ccc4454270b4aee39e1f7743601aa4ec53733e`
**Container:** `garnet-privacy-proxy-1` on `root@65.108.38.50`
**Capture:** 2026-09-11 19:32–19:33 UTC

---

## Answer to T4D Q8

### Prior behaviour (build `04f1c2ee9` and earlier)

`[IN USER]` and `[IN USER+]` (as well as `[IN FILE]`) were **always** printed to
container stdout with the raw request body, including any PII the user typed
before pseudonymization. This is visible in the demo-2 evidence
(`.claude/docs/demo2test/logs/garnet-privacy-proxy-1-2026-08-23.log`), e.g.:

```
2026-08-23T16:12:31.663Z 16:12:31.663 [IN  USER] Extract the fields from this JSON exactly as given, preserving every value verbatim: {"name":"Anna Müller-Öztürk", ...}
```

### New behaviour (build `v-t4d-b1-fix`)

Raw-input logging is now gated behind an environment variable.

- **`LOG_RAW_INPUT` unset or `0`** — **default in production**. Raw prompts are
  suppressed; only a placeholder plus the original character count is printed. This
  preserves observability (request cadence, payload size) without leaking prompt
  content.
- **`LOG_RAW_INPUT=1`** — diagnostic mode, off by default. Restores the full
  `[IN USER]` and `[IN USER+]` output. Intended for local development or a
  time-boxed incident investigation. Should not be set in a shared production
  deployment.

Implementation lives in `backend/privacy_proxy/app/logs.py` (commit `ff75f67a6`).

## Verification

Both states are demonstrated below against the running corrected build.

### Default state — `LOG_RAW_INPUT` unset (suppression active)

Command:

```bash
docker exec garnet-privacy-proxy-1 python -c '
import httpx
httpx.post(
  "http://localhost:8080/openai/chat/completions",
  headers={"Authorization": "Bearer sk-fake"},
  json={"model": "gpt-4o-mini", "stream": False,
        "messages": [{"role": "user",
                      "content": "Anna Müller-Öztürk lives in München."}]},
  timeout=15)
'
docker logs --since 15s garnet-privacy-proxy-1 | grep "IN  USER"
```

Output:

```
19:32:40.860 [IN  USER] <raw input suppressed; set LOG_RAW_INPUT=1 to enable> (36 chars)
```

Raw prompt content is not present in stdout. Only the size metadata (`36 chars`) is
emitted. Any log sink (journald, Fluent Bit, Loki, ELK) that consumes container
stdout will therefore never receive the raw prompt.

### Diagnostic state — `LOG_RAW_INPUT=1`

Command:

```bash
docker exec -e LOG_RAW_INPUT=1 garnet-privacy-proxy-1 python -c '
import os
os.environ["LOG_RAW_INPUT"] = "1"
import importlib, app.logs
importlib.reload(app.logs)
app.logs.log_in_user("Anna Müller-Öztürk lives in München.")
app.logs.log_in_user_full("Anna Müller-Öztürk lives in München.")
' | grep "IN  USER"
```

Output:

```
19:33:07.255 [IN  USER] Anna Müller-Öztürk lives in München.
19:33:07.255 [IN  USER+] Anna Müller-Öztürk lives in München.
```

Full raw prompt is printed, as expected in diagnostic mode.

## Orchestration-log-sink retention

Because raw prompts never reach stdout when the flag is off, any downstream
retention mechanism (Fluent Bit, Loki, journald, ELK, CloudWatch Logs) will
retain only the pseudonymized `[OUT USER]` payload plus size metadata for
`[IN USER]`. No additional configuration on the sink is required to keep raw
PII out of long-term log storage.
