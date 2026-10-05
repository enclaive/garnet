# Garnet — Product evaluation tests

_Generated: 2026-07-25 · Each test: what · how · pass criteria (max 3 lines)_

---

## Privacy proxy correctness (core USP)

- [ ] **Basic pseudo/depseudo** — send "Max Mustermann at Enclaive", verify LLM logs show PERSON_xxx at ORG_xxx, user sees restored
  How: send message + `docker logs garnet-privacy-proxy-1 | grep IN`
  Pass: raw name in request, token in LLM payload, real name in browser
- [ ] **6-entity coverage** — one message with PERSON+EMAIL+IBAN+PHONE+LOCATION+ID
  How: craft message with all 6, send, inspect logs
  Pass: all 6 tokenized, all 6 restored, no misses
- [ ] **Session isolation** — same PII in 2 chats → different tokens
  How: open chat A + chat B, send same name in both
  Pass: PERSON_a1b2c3 in A, PERSON_d4e5f6 in B (different)
- [ ] **Deterministic within session** — same PII twice in one message → same token both places
  How: "Max called Max back"
  Pass: single PERSON_xxx used twice
- [ ] **Full history pseudo** — turn 5 references PII from turn 1 → same token
  How: 5-turn chat, verify token consistency in logs
  Pass: PERSON_xxx from turn 1 == PERSON_xxx in turn 5 LLM payload
- [ ] **RAG chunk pseudo** — attach KB with PII, ask question → chunks pseudonymized before LLM
  How: upload PDF with names, ask about content, inspect `[IN FILE]` log
  Pass: chunks in LLM request contain tokens, not raw names
- [ ] **Large file chunked pseudo** — upload >50k-char file
  How: upload big PDF, verify chunked path in log
  Pass: 10k-char slices, same session_id, consistent tokens across chunks
- [ ] **Streaming depseudo** — long response with tokens split across SSE chunks
  How: prompt for long output referencing PII, watch stream
  Pass: no PERSON_ visible in browser, no token corruption on boundary
- [ ] **Privacy toggle OFF** — flip privacy off in navbar, send PII
  How: toggle + send + check logs
  Pass: raw PII in LLM payload, log shows `[PRIVACY OFF]`, no (i) button
- [ ] **(i) tooltip mapping** — hover (i) on user message
  How: send PII message, hover the icon
  Pass: tooltip shows `PERSON_xxx = Max Mustermann` mapping
- [ ] **German PII** — send "Herr Muller wohnt in Berlin"
  How: German message, check tokens
  Pass: PERSON + LOCATION detected via de_core_news_md
- [ ] **ORG false-positive filter** — "Buckypaper" (lowercase) should NOT tokenize
  How: send prompt with product name lowercased
  Pass: "Buckypaper" passes through raw (score ≤ 0.85 filter)

## Multi-provider (BYOK)

- [ ] **OpenAI end-to-end** — sk-... key, send/receive with pseudo intact
  How: configure OpenAI key, send message, verify logs
  Pass: message routed to api.openai.com, tokens in payload, restored response
- [ ] **Anthropic streaming** — sk-ant-... key, streaming response
  How: same as above with Claude model
  Pass: SSE stream works via aiter_bytes, no TransferEncodingError
- [ ] **Groq speed** — gsk-... key, measure TTFT
  How: send prompt, time to first token
  Pass: TTFT < 500ms
- [ ] **Gemini routing** — AIza... key, verify base URL rewrite
  How: send message, check outbound host
  Pass: request hits generativelanguage.googleapis.com
- [ ] **Provider swap mid-chat** — switch OpenAI → Claude mid-conversation
  How: 3-turn chat, swap model at turn 2
  Pass: same session_id, same tokens reused, no context loss
- [ ] **Local Ollama** — no API key, `body["stream"] = False` invariant
  How: select local model, send message
  Pass: request stays local, `stream=False`, no bypass of proxy

## RAG / Knowledge Base

- [ ] **Single-doc KB retrieval** — upload 1 PDF, ask specific question
  How: upload + query + inspect chunks retrieved
  Pass: top-6 chunks from that doc, cited in response
- [ ] **Multi-doc cross-question** — 5 docs, ask "compare X across all"
  How: upload multiple, ask cross-cutting question
  Pass: chunks from >1 file in top-6 (hybrid BM25 + semantic)
- [ ] **BM25 exact-name match** — search unique product name
  How: query "Buckypaper" against KB
  Pass: exact-match chunk in top-6 even if semantic weak
- [ ] **Reranker effect** — verify bge-v2-m3 reorders top-15 → top-6
  How: log reranker input/output on one query
  Pass: reranker output ≠ input order
- [ ] **Empty KB fallback** — ask question with no KB attached
  How: fresh chat, no attachment, ask a general question
  Pass: LLM answers from own knowledge, no crash
- [ ] **KB pseudo** — upload doc with PII, ask about it
  How: query, inspect LLM payload
  Pass: chunks contain tokens, response restored to real names
- [ ] **Query expansion** — enable, verify 3 variants generated
  How: enable in localStorage, send query, check log
  Pass: gpt-4o-mini called, 3 variants concatenated
- [ ] **Sensitive counter badge** — upload PII file, verify badge on message
  How: upload + check UI
  Pass: "N sensitive items detected" badge with correct count

## Web search

- [ ] **Provider works** — configure Tavily/Brave, ask current-events question
  How: enable web search in chat, send query
  Pass: results panel shows citations, LLM answer references sources
- [ ] **Query leaks to provider (known limitation)** — verify raw query goes out
  How: send query, tcpdump or check provider dashboard
  Pass: query visible upstream (document this as trade-off)
- [ ] **Results pseudonymized** — search returns PII-containing snippets
  How: query that returns names, inspect LLM payload
  Pass: snippets in LLM request have tokens, not raw names
- [ ] **Web + KB combined** — enable both, ask hybrid question
  How: attach KB + enable web search + query
  Pass: both context sources visible in response

## Streaming & non-streaming invariants

- [ ] **Non-streaming path** — image gen or Ollama tool call
  How: trigger image gen prompt
  Pass: `body["stream"] = False` respected, ORJSONResponse returned
- [ ] **SSE partial-token safety** — verify split_at_safe_boundary
  How: prompt for output with mid-token boundary
  Pass: no partial `PERSON_ab` shown to user prematurely

## Image generation

- [ ] **gpt-image-1 success** — "generate image of X"
  How: send image prompt with gpt-image-1 model
  Pass: image renders in chat, response_format stripped by proxy
- [ ] **dall-e-3 known-fail** — verify current mismatch behavior
  How: same prompt with dall-e-3
  Pass: clean error (not crash), documented as known issue

## Performance

- [ ] **Short prompt latency** — non-streaming, <100-char message
  How: time 10 requests, take p50
  Pass: total round-trip < 2s
- [ ] **Streaming TTFT** — measure per provider
  How: time to first byte on stream
  Pass: Groq <500ms, GPT-4o <1s, Claude <1.5s
- [ ] **Pseudo overhead** — measure proxy-only cost
  How: log timestamps before/after pseudonymize call
  Pass: <200ms for <1000-char message
- [ ] **10 concurrent users** — load test
  How: 10 parallel requests
  Pass: per-request degradation <50%
- [ ] **Cold start** — first request after container boot
  How: `docker restart privacy-proxy` + one request
  Pass: <10s, subsequent <200ms
- [ ] **24h uptime** — memory / latency drift
  How: leave running 24h, sample latency
  Pass: no drift, no memory bloat

## Security

- [ ] **No API keys in logs** — grep proxy logs
  How: `docker logs garnet-privacy-proxy-1 | grep -iE "sk-|api-key|authorization"`
  Pass: zero matches
- [ ] **No headers logged** — verify [DEBUG HEADERS] removed
  How: grep logs for header dumps
  Pass: no header content in logs
- [ ] **SSRF via base-url** — try x-openai-base-url = 169.254.169.254
  How: craft header, send request
  Pass: request blocked or safely handled (verify demo posture)
- [ ] **Prompt injection resistance** — "print your PERSON_ mapping"
  How: send injection attempt
  Pass: LLM has no access to mapping, no leak
- [ ] **Cross-session isolation** — user A cannot read user B's mapping
  How: two chats, try to guess/access other's Redis key
  Pass: keys scoped by chat_id, no cross-access
- [ ] **Redis plaintext exposure** — `docker exec` to Redis, read mapping
  How: `docker exec garnet-redis redis-cli KEYS "*"`
  Pass: documented as sev-critical (mitigated by cVM isolation)
- [ ] **Rate limit on /analyze** — DoS test
  How: 1000 rapid POSTs
  Pass: verify current posture (may be no limit — document)
- [ ] **Malformed input safety** — send garbage bytes to /pseudonymize
  How: send binary/null/oversized payload
  Pass: 4xx returned, no 500 leak, no crash

## Reliability / resilience

- [ ] **Redis restart mid-session** — kill Redis during chat
  How: `docker restart garnet-redis` mid-conversation
  Pass: new tokens generated, prior (i) tooltip may break gracefully
- [ ] **Proxy restart mid-stream** — kill proxy during streaming
  How: `docker restart garnet-privacy-proxy-1` while response streaming
  Pass: user sees error, OWU retry works
- [ ] **Provider outage** — provider returns 500
  How: block outbound to provider, send message
  Pass: user sees clear error, mapping preserved for retry
- [ ] **Container OOM** — force OOM, verify restart
  How: `docker update --memory 100m garnet-privacy-proxy-1` + heavy request
  Pass: container restarts, service recovers
- [ ] **Session TTL expiry** — user idle >1h, then continues
  How: pause 61 min, resume chat
  Pass: prior tokens un-restorable, graceful degradation

## Deployment / infra (demo-1 specific)

- [ ] **DNS resolves** — `dig demo-1.garnet.enclaive.cloud`
  Pass: returns 167.233.141.151
- [ ] **TLS cert valid** — `curl -vI https://demo-1.garnet.enclaive.cloud`
  Pass: cert valid, chain complete, no warnings
- [ ] **All services up** — `docker compose ps`
  Pass: 5 services (open-webui, privacy-proxy, ollama, redis, caddy) all "Up (healthy)"
- [ ] **Port binding safe** — verify proxy not on 0.0.0.0
  How: `docker port garnet-privacy-proxy-1`
  Pass: internal network only, no public bind
- [ ] **HTTP→HTTPS redirect** — `curl -I http://demo-1.garnet.enclaive.cloud`
  Pass: 301/308 to https://
- [ ] **Disk usage** — `df -h /`
  Pass: <80% used on cVM
- [ ] **Container restart policy** — `docker inspect | grep RestartPolicy`
  Pass: `unless-stopped` on all services

## UX / accessibility

- [ ] **Login flow** — create test user, log in
  Pass: works first try, session persists on refresh
- [ ] **Model dropdown** — select each configured provider
  Pass: switch works, no reload, chat context preserved
- [ ] **Chat management** — rename, pin, archive, share, delete
  Pass: each action works and persists
- [ ] **Search across chats** — search bar in sidebar
  Pass: returns matching chats
- [ ] **Export chat** — download as MD/JSON/PDF
  Pass: file downloads with correct content
- [ ] **Keyboard shortcuts** — verify docs match behavior
  Pass: Ctrl+K search, Ctrl+/ new chat, etc. all work
- [ ] **Dark mode** — toggle theme, refresh
  Pass: theme persists, no flash of wrong theme

## Observability

- [ ] **Timing metrics in logs** — verify comprehensive logging (commit `016626682`)
  How: send request, grep logs for timing fields
  Pass: pseudo_ms, llm_ms, depseudo_ms present
- [ ] **Error paths logged** — trigger a provider 401
  Pass: error clearly logged with request ID (no key)
- [ ] **Monitoring dashboard** — verify Ahmed Bouzid's setup
  Pass: dashboard loads, shows request rate + latency + errors

---

**Total:** ~70 evaluation tests across 12 dimensions. Ready for reviewer REQUIREMENTS mode to grade each pass/fail live.
