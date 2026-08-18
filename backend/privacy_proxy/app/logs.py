from datetime import datetime, timezone

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

def _p(msg): print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} {msg}", flush=True)

def log_sep(): _p(SEP)

# ── identity & correlation ────────────────────────────────────────────────────

def log_garnet(session_id, provider, privacy, model, path):
    _p(f"[GARNET] session={session_id[:8]} provider={provider} privacy={'ON' if privacy else 'OFF'} model={model} path={path}")

def log_session(request_id, user_id, session_id):
    _p(f"[SESSION  ] request={request_id} user={user_id} session={session_id[:8]}")

def log_entity_filter(enabled_types):
    _p(f"[ENTITY FILTER] active → only: {enabled_types}")

# ── user message ─────────────────────────────────────────────────────────────

def log_in_user(text):
    _p(f"[IN  USER] {text[:200]}")

def log_in_user_full(text):
    _p(f"[IN  USER+] {text}")

def log_out_user(text):
    _p(f"[OUT USER] {text[:200]}")

def log_out_user_full(text):
    _p(f"[OUT USER+] {text}")

def log_no_pii():
    _p(f"[NO PII] message unchanged — no entities detected")

def log_pseudo_diff(original_len, pseudo_len, n_replaced, types):
    delta = pseudo_len - original_len
    _p(f"[PSEUDO DIFF] {original_len}→{pseudo_len} chars ({delta:+d}) | {n_replaced} replaced | types={types}")

# ── file / RAG / web content ──────────────────────────────────────────────────

def log_in_file(role, length, text):
    _p(f"[IN  FILE] role={role} len={length} | {text[:200]}")

def log_out_file(text):
    _p(f"[OUT FILE] {text[:200]}")

def log_file_delta(original_len, pseudo_len):
    delta = pseudo_len - original_len
    _p(f"[FILE DELTA] {original_len}→{pseudo_len} chars ({delta:+d})")

def log_large_file(length, n_chunks):
    _p(f"[LARGE FILE] {length} chars → chunked pseudo ({n_chunks} chunks)")

def log_out_file_chunked(n_chunks, total_chars):
    _p(f"[OUT FILE] chunked {n_chunks} parts → {total_chars} chars")

def log_file_scan(count):
    _p(f"[FILE SCAN] {count} RAG chunk(s) processed")

def log_file_pii(count, breakdown):
    _p(f"[FILE PII] {count} new entities detected | breakdown={breakdown or 'in-memory-only'}")

def log_file_pii_duplicate():
    _p(f"[FILE PII] 0 new entities — already in mapping (duplicate upload)")

# ── internal / privacy state ──────────────────────────────────────────────────

def log_internal(internal_type):
    _p(f"[INTERNAL] type={internal_type} → skipped pseudonymization")

def log_privacy_off():
    _p(f"[PRIVACY OFF] forwarding raw → no pseudonymization")

def log_history_depseudo(count):
    _p(f"[HISTORY PSEUDO] pseudonymized {count} message(s) in history")

def log_history_scan(scanned, changed, skipped_empty, skipped_system):
    _p(f"[HISTORY SCAN] scanned={scanned} changed={changed} skipped_empty={skipped_empty} skipped_system={skipped_system}")

def log_ctx_msg(i, role, text_len, has_pseudo, head):
    _p(f"[CTX MSG] i={i} role={role} len={text_len} pseudo_tokens={has_pseudo} head={head!r}")

# ── context / LLM call ────────────────────────────────────────────────────────

def log_context_size(msg_count, total_chars):
    _p(f"[CONTEXT  ] {msg_count} messages → {total_chars} chars to LLM")

def log_to_llm(url, model, elapsed_ms):
    _p(f"[→ LLM   ] {url} | model={model} | pseudo={elapsed_ms}ms")

def log_from_llm(chunk_text, ttft_s):
    _p(f"[← LLM   ] {repr(chunk_text[:200])} | ttft={ttft_s:.2f}s")

def log_llm_tokens(model, input_tokens, output_tokens):
    _PRICES = {
        "claude-opus":   (15.0, 75.0),
        "claude-sonnet": (3.0,  15.0),
        "claude-haiku":  (0.8,   4.0),
        "gpt-4o-mini":   (0.15,  0.6),
        "gpt-4o":        (2.5,  10.0),
        "llama":         (0.0,   0.0),
    }
    pin, pout = next((v for k, v in _PRICES.items() if k in model.lower()), (0.0, 0.0))
    cost = (input_tokens * pin + output_tokens * pout) / 1_000_000
    _p(f"[LLM TOKENS] in={input_tokens} out={output_tokens} total={input_tokens+output_tokens} ~${cost:.4f}")

# ── response & stream ─────────────────────────────────────────────────────────

def log_garnet_out(text):
    _p(f"[GARNET OUT] {text[:300]}")

def log_stream_done(chunks, total_chars):
    _p(f"[STREAM DONE] {chunks} chunks | {total_chars} chars")

def log_to_user(token_count, ttft_s=0.0, total_s=0.0):
    _p(f"[→ USER  ] depseudo complete, {token_count} tokens | ttft={ttft_s:.2f}s total={total_s:.2f}s")

def log_privacy_audit(total_entities, model, ttft_s, total_s):
    _p(f"[PRIVACY AUDIT] entities={total_entities} model={model} | ttft={ttft_s:.2f}s total={total_s:.2f}s")

# ── misc ──────────────────────────────────────────────────────────────────────

def log_mapping(session_id, total_tokens):
    _p(f"[MAPPING] session={session_id[:8]} total_tokens={total_tokens}")

def log_self_loop(resolved_url):
    _p(f"[SELF-LOOP] detected → resolved to {resolved_url}")

def log_responses_api(model):
    _p(f"[RESPONSES API] model={model} → using /responses endpoint")

def log_reasoning_effort(effort):
    _p(f"[REASONING] effort={effort}")

def log_image(model, prompt, url):
    _p(f"[IMAGE] model={model} prompt={prompt[:80]} → {url}")

def log_health():
    _p(f"[HEALTH] ping received → ok")

def log_vault_start(file_id, session_id, enabled_types):
    _p(f"[VAULT START] file_id={file_id} session={session_id} entity_filter={enabled_types or 'ALL'}")

def log_vault_done(file_id, count, report):
    _p(f"[VAULT DONE] file_id={file_id} → {count} new entities | breakdown={report}")

def log_vault_skip(file_id):
    _p(f"[VAULT SKIP] privacy=OFF file_id={file_id}")

def log_vault_error(field):
    _p(f"[VAULT ERROR] missing {field} field")

def log_analyze(language, enabled_types, text):
    _p(f"[ANALYZE] lang={language or 'auto'} filter={enabled_types or 'ALL'} text={text[:100]}")

def log_analyze_result(count, types):
    _p(f"[ANALYZE RESULT] {count} entities found → {types}")

def log_error(msg):
    _p(f"[ERROR] {msg}")

def log_error_passthrough(status, url, body):
    _p(f"[ERROR] passthrough status={status} url={url} body={body[:200]}")
