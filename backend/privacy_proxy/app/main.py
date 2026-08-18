# ci: trigger build
import os
import re
import time
import uuid
import hashlib
import httpx
import orjson
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from app.pseudonymizer import pseudonymize, detect_entities
from app.mapping_store import MappingStore
from app.logs import (
    log_sep, log_garnet, log_entity_filter,
    log_in_user, log_out_user, log_no_pii,
    log_in_file, log_out_file, log_large_file, log_out_file_chunked,
    log_file_scan, log_file_pii, log_file_pii_duplicate,
    log_internal, log_privacy_off, log_history_depseudo, log_history_scan, log_ctx_msg,
    log_to_llm, log_from_llm, log_to_user, log_mapping,
    log_self_loop,
    log_health, log_vault_start, log_vault_done, log_vault_skip, log_vault_error,
    log_analyze, log_analyze_result,
    log_error, log_error_passthrough,
    log_session, log_in_user_full, log_out_user_full, log_pseudo_diff,
    log_context_size, log_llm_tokens, log_garnet_out, log_stream_done,
    log_privacy_audit, log_file_delta,
    log_reasoning_effort,
)

RESPONSES_API_MODELS = {"gpt-5", "gpt-5.5-pro", "gpt-5.6-luna"}

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")

SYSTEM_PROMPT_MARKERS = [
    "### Task:", "### Guidelines:", "### Output:",
    "JSON format:", "follow_ups",
    "Generate a concise",
    "Generate 1-3 broad tags",
    "categorizing the main themes",
    "Generate a hypothetical",
    "Suggest 3-5 relevant follow-up",
]


class ORJSONResponse(Response):
    media_type = "application/json"
    def render(self, content) -> bytes:
        return orjson.dumps(content)


app = FastAPI(default_response_class=ORJSONResponse)
store = MappingStore(ttl=3600)
# ponytail: per-session pseudonymize cache. TTL is implicit — same 1h window as store;
# evicted on process restart, not on session expiry. Add active eviction if memory becomes measurable.
pseudo_cache: dict[str, dict[str, str]] = {}


def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return str(content)


def rebuild_content(original_content, pseudonymized_text: str):
    if isinstance(original_content, str):
        return pseudonymized_text
    if isinstance(original_content, list):
        result = []
        for block in original_content:
            if isinstance(block, dict) and block.get("type") == "text":
                result.append({"type": "text", "text": pseudonymized_text})
            else:
                result.append(block)
        return result
    return pseudonymized_text


def _pseudo_with_cache(text: str, session_id: str, enabled_types) -> str:
    if not text:
        return text
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    session_cache = pseudo_cache.setdefault(session_id, {})
    hit = session_cache.get(h)
    if hit is not None:
        return hit
    out = pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)
    session_cache[h] = out
    return out


def split_at_safe_boundary(buffer: str):
    TOKEN_NAMES = ['PERSON', 'ORGANIZATION', 'EMAIL_ADDRESS', 'IBAN_CODE', 'PHONE_NUMBER', 'ID', 'LOCATION']
    partial_pattern = r'(PERSON|ORGANIZATION|EMAIL_ADDRESS|IBAN_CODE|PHONE_NUMBER|ID|LOCATION)_[a-f0-9]{0,7}$'

    for token in TOKEN_NAMES:
        for length in range(1, len(token) + 1):
            prefix = token[:length]
            if buffer.endswith(prefix):
                safe = buffer[:-len(prefix)]
                return safe, buffer[len(safe):]

    if re.search(partial_pattern, buffer):
        match = re.search(partial_pattern, buffer)
        safe = buffer[:match.start()]
        return safe, buffer[match.start():]

    return buffer, ""


def detect_internal_type(content: str) -> str:
    if "follow_ups" in content:
        return "follow_ups"
    if "Generate a concise" in content and "title" in content:
        return "title_gen"
    if "Generate 1-3 broad tags" in content or "categorizing the main themes" in content:
        return "tags_gen"
    if "search_query" in content or "Generate a hypothetical" in content:
        return "search_query"
    return "internal"


async def expand_query(question: str, openai_url: str, auth_header: str) -> list[str]:
    """
    Calls gpt-4o-mini to generate 3 short search query variants.
    Used to enrich embedding vector for better Chroma retrieval.
    Returns [] on any failure — expansion never breaks the main request.
    """
    if not question or not auth_header:
        print(f"[QUERY EXPAND] skipped: missing question or auth")
        return []

    prompt = (
        "You are a search query generator for a private company knowledge base.\n"
        "The user asked the question below. Generate 3 short alternative search queries "
        "that would help retrieve relevant documents from the knowledge base.\n"
        "Do NOT answer the question. Do NOT add explanations.\n"
        "Return ONLY 3 queries, one per line, no numbering, no bullets, no quotes.\n\n"
        f"Question: {question}"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{openai_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 150
                },
                timeout=15.0
            )

        if resp.status_code != 200:
            print(f"[QUERY EXPAND] LLM call failed status={resp.status_code} body={resp.text[:200]}")
            return []

        result = orjson.loads(resp.content)
        text = result["choices"][0]["message"]["content"].strip()
        variants = [v.strip("-•* \t\"'") for v in text.split("\n") if v.strip()]
        variants = [v for v in variants if v and len(v) > 3][:3]

        if not variants:
            print(f"[QUERY EXPAND] LLM returned empty variants, raw={text[:200]}")
            return []

        return variants

    except httpx.TimeoutException:
        print(f"[QUERY EXPAND] timeout after 15s")
        return []
    except Exception as e:
        print(f"[QUERY EXPAND] exception: {type(e).__name__}: {e}")
        return []


async def stream_with_depseudo(response_stream, mapping, pseudonymized_prompt, session_id, url, model, file_entity_count=0, garnet_breakdown=None, variants=None, t0=None):
    yield orjson.dumps({
        "type": "pseudonymized_prompt",
        "content": pseudonymized_prompt or "",
        "file_entity_count": file_entity_count,
        "garnet_breakdown": garnet_breakdown or {},
        "query_variants": variants or []
    }) + b"\n\n"

    buffer = ""
    first_chunk = True
    first_out = True
    ttft_s = 0.0
    chunk_count = 0
    total_out_chars = 0
    input_tokens = 0
    output_tokens = 0
    async for raw_chunk in response_stream:
        for chunk in raw_chunk.split(b"\n"):
            if not chunk:
                continue
            if chunk.startswith(b"data: "):
                raw = chunk[6:].strip()
            else:
                raw = chunk.strip()

            if raw == b"[DONE]":
                break

            try:
                parsed = orjson.loads(raw)
                # capture token usage — OpenAI, Anthropic OpenAI-compat, and Anthropic native formats
                usage = parsed.get("usage") or {}
                if usage.get("input_tokens"):
                    input_tokens = usage["input_tokens"]
                if usage.get("output_tokens"):
                    output_tokens = usage["output_tokens"]
                if usage.get("prompt_tokens"):
                    input_tokens = usage["prompt_tokens"]
                if usage.get("completion_tokens"):
                    output_tokens = usage["completion_tokens"]
                # Anthropic native: message_start carries input_tokens in message.usage
                chunk_type = parsed.get("type", "")
                if chunk_type == "message_start":
                    msg_usage = parsed.get("message", {}).get("usage", {})
                    if msg_usage.get("input_tokens"):
                        input_tokens = msg_usage["input_tokens"]
                # Anthropic native: message_delta carries output_tokens in usage
                if chunk_type == "message_delta":
                    delta_usage = parsed.get("usage", {})
                    if delta_usage.get("output_tokens"):
                        output_tokens = delta_usage["output_tokens"]

                chunk_text = parsed["choices"][0]["delta"].get("content", "")
                if not chunk_text:
                    continue
            except Exception:
                continue

            if first_chunk:
                ttft_s = (time.perf_counter() - t0) if t0 else 0.0
                log_from_llm(chunk_text, ttft_s)
                first_chunk = False

            buffer += chunk_text
            safe, remainder = split_at_safe_boundary(buffer)

            if safe:
                for token in sorted(mapping.keys(), key=len, reverse=True):
                    safe = safe.replace(token, mapping[token])
                chunk_count += 1
                total_out_chars += len(safe)
                if first_out:
                    log_garnet_out(safe)
                    first_out = False
                yield b"data: " + orjson.dumps({
                    "choices": [{"delta": {"content": safe}}]
                }) + b"\n\n"

            buffer = remainder

    if buffer:
        for token in sorted(mapping.keys(), key=len, reverse=True):
            buffer = buffer.replace(token, mapping[token])
        chunk_count += 1
        total_out_chars += len(buffer)
        if first_out:
            log_garnet_out(buffer)
        yield b"data: " + orjson.dumps({
            "choices": [{"delta": {"content": buffer}}]
        }) + b"\n\n"

    log_stream_done(chunk_count, total_out_chars)
    if input_tokens or output_tokens:
        log_llm_tokens(model, input_tokens, output_tokens)
    log_to_user(len(mapping), ttft_s, (time.perf_counter() - t0) if t0 else 0.0)
    log_privacy_audit(len(mapping), model, ttft_s, (time.perf_counter() - t0) if t0 else 0.0)
    log_sep()
    yield b"data: [DONE]\n\n"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/vault/scan")
async def vault_scan(request: Request):
    body = await request.json()
    text = body.get("text", "")
    file_id = body.get("file_id")
    privacy_enabled = body.get("privacy_proxy", True)

    if not text:
        log_vault_error("text")
        return ORJSONResponse({"error": "text required"})
    if not file_id:
        log_vault_error("file_id")
        return ORJSONResponse({"error": "file_id required"})

    if not privacy_enabled:
        log_vault_skip(file_id)
        return ORJSONResponse({
            "file_id": file_id,
            "session_id": f"file:{file_id}",
            "pseudonymized_text": text,
            "entity_count": 0,
            "entity_breakdown": {},
            "preview": {"before": text[:500], "after": text[:500]}
        })

    enabled_header = request.headers.get("x-garnet-entities", "")
    enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] if enabled_header else None

    session_id = f"file:{file_id}"
    log_vault_start(file_id, session_id, enabled_types)

    existing_keys_before = set(store.get_store().get(session_id, {}).keys())
    pseudonymized = pseudonymize(text, session_id, store.get_store(), enabled_types=enabled_types)
    new_keys = set(store.get_store().get(session_id, {}).keys()) - existing_keys_before

    report = {}
    for token in new_keys:
        prefix = token.rsplit("_", 1)[0]
        report[prefix] = report.get(prefix, 0) + 1

    log_vault_done(file_id, len(new_keys), report)

    return ORJSONResponse({
        "file_id": file_id,
        "session_id": session_id,
        "pseudonymized_text": pseudonymized,
        "entity_count": len(new_keys),
        "entity_breakdown": report,
        "preview": {"before": text[:500], "after": pseudonymized[:500]},
    })


@app.post("/analyze")
async def analyze(request: Request):
    body = await request.json()
    text = body.get("text", "")
    language = body.get("language")

    if not text:
        return JSONResponse({"entities": []})

    enabled_header = request.headers.get("x-garnet-entities", "")
    enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] if enabled_header else None

    log_analyze(language, enabled_types, text)
    entities = detect_entities(text, language, enabled_types=enabled_types)
    log_analyze_result(len(entities), [e.get("type") for e in entities])

    return JSONResponse({"entities": entities})


@app.get("/openai/api/tags")
async def ollama_tags():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=30.0)
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type="application/json",
    )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    t0 = time.perf_counter()
    request_id = uuid.uuid4().hex[:8]
    user_id = request.headers.get("x-garnet-user-id", "anon")
    body = None
    if request.method in ("POST", "PUT"):
        body = await request.json()

    is_openai = path.startswith("openai/")
    actual_path = path[len("openai/"):] if is_openai else path
    is_chat = actual_path in ("v1/chat/completions", "api/chat", "v1/completions", "chat/completions")

    privacy_enabled = True
    pseudonymized_user_message = None
    session_id = "default"
    file_entity_count = 0
    garnet_breakdown = {}
    query_expand = request.headers.get("x-garnet-queryexpand", "").lower() == "true"
    variants = []

    if body:
        privacy_enabled = body.pop("privacy_proxy", True)

    if is_openai:
        openai_url = request.headers.get("x-openai-base-url", OPENAI_API_URL)
        if "privacy-proxy" in openai_url or "localhost:8080" in openai_url:
            auth = request.headers.get("authorization", "")
            model_name = (body or {}).get("model", "").lower()
            if "sk-ant-" in auth:
                openai_url = "https://api.anthropic.com/v1"
            elif "AIza" in auth or "gemini" in model_name:
                openai_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            elif "gsk-" in auth or "groq" in model_name:
                openai_url = "https://api.groq.com/openai/v1"
            elif "sk-or-" in auth:
                openai_url = "https://openrouter.ai/api/v1"
            else:
                openai_url = OPENAI_API_URL
            log_self_loop(openai_url)
        url = f"{openai_url.rstrip('/')}/{actual_path}"
    else:
        url = f"{OLLAMA_URL}/{actual_path}"

    if is_chat and body:
        if is_openai:
            caller_wants_stream = body.get("stream", True)
            body["stream"] = caller_wants_stream if caller_wants_stream is False else True
        else:
            body["stream"] = False

        messages = body.get("messages", [])
        model = body.get("model", "unknown")
        first_msg = extract_text_content(messages[0].get("content", "")) if messages else ""

        session_id = (
            body.get("chat_id")
            or (messages[0].get("id") if messages else None)
            or (hashlib.md5(first_msg.encode()).hexdigest()[:12] if first_msg else "default")
        )
        body.pop("chat_id", None)

        if is_openai and "api.openai.com" in url:
            if "max_tokens" in body:
                body["max_completion_tokens"] = body.pop("max_tokens")
            if body.get("tools") and "reasoning_effort" in body:
                body.pop("reasoning_effort")

        use_responses_api = is_openai and "api.openai.com" in url and any(model.startswith(m) for m in RESPONSES_API_MODELS)
        if use_responses_api:
            url = url.replace("/v1/chat/completions", "/v1/responses")
            msgs = body.pop("messages", [])
            system_parts = [m for m in msgs if m.get("role") == "system"]
            if system_parts:
                body["instructions"] = system_parts[0].get("content", "")
            def _remap_content(content):
                if not isinstance(content, list):
                    return content
                out = []
                for block in content:
                    t = block.get("type") if isinstance(block, dict) else None
                    if t == "text":
                        out.append({**block, "type": "input_text"})
                    elif t == "image_url":
                        url = block.get("image_url", {}).get("url", "")
                        out.append({"type": "input_image", "image_url": url})
                    else:
                        out.append(block)
                return out
            body["input"] = [{**m, "content": _remap_content(m.get("content", ""))} for m in msgs if m.get("role") != "system"]
            body.pop("max_completion_tokens", None)
            if "max_tokens" in body:
                body["max_output_tokens"] = body.pop("max_tokens")
            # ponytail: Responses API wants reasoning.effort nested, not flat reasoning_effort
            if "reasoning_effort" in body:
                effort = body.pop("reasoning_effort")
                body["reasoning"] = {"effort": effort}
                log_reasoning_effort(effort)
            if "response_format" in body:
                rf = body.pop("response_format")
                if rf.get("type") == "json_schema":
                    js = rf.get("json_schema", {})
                    body["text"] = {"format": {
                        "type": "json_schema",
                        "name": js.get("name", "output"),
                        "schema": js.get("schema", {}),
                        "strict": js.get("strict", True),
                    }}
            for f in ("stream_options", "top_p", "frequency_penalty", "presence_penalty",
                      "logprobs", "top_logprobs", "n", "tools", "tool_choice", "reasoning_effort"):
                body.pop(f, None)

        if "groq" in url:
            provider_label = "groq"
        elif "gemini" in url or "googleapis" in url:
            provider_label = "gemini"
        elif "ollama" in url or "11434" in url:
            provider_label = "ollama"
        elif "anthropic" in url:
            provider_label = "anthropic"
        else:
            provider_label = "openai"

        log_sep()
        log_garnet(session_id, provider_label, privacy_enabled, model, actual_path)
        log_session(request_id, user_id, session_id)
        if query_expand:
            print(f"[QUERY EXPAND] header detected → expansion ON")

        enabled_header = request.headers.get("x-garnet-entities", "")
        enabled_types = [e.strip() for e in enabled_header.split(",") if e.strip()] if enabled_header else None
        if enabled_types:
            log_entity_filter(enabled_types)

        # NOTE: excludes messages[-1]; last message handled by block below.
        if messages and privacy_enabled:
            hist_pseudo_count = 0
            skipped_empty = 0
            skipped_system = 0
            scanned = 0
            for i, msg in enumerate(messages[:-1]):
                scanned += 1
                content = msg.get("content")
                text = extract_text_content(content)
                _text = text or ""
                has_pseudo = any(tok in _text for tok in ("PERSON_", "ORGANIZATION_", "EMAIL_ADDRESS_", "IBAN_CODE_", "PHONE_NUMBER_", "LOCATION_", "ID_"))
                log_ctx_msg(i, msg.get("role"), len(_text), has_pseudo, _text[:120])
                if not text:
                    skipped_empty += 1
                    continue
                if any(marker in text for marker in SYSTEM_PROMPT_MARKERS):
                    skipped_system += 1
                    continue
                out = _pseudo_with_cache(text, session_id, enabled_types)
                if out != text:
                    msg["content"] = rebuild_content(content, out)
                    hist_pseudo_count += 1
            log_history_scan(scanned, hist_pseudo_count, skipped_empty, skipped_system)
            if hist_pseudo_count > 0:
                log_history_depseudo(hist_pseudo_count)

        if messages:
            last_message = messages[-1]
            original_content = last_message["content"]
            original_content_text = extract_text_content(original_content)

            has_rag_context = (
                "<context>" in original_content_text or
                "<source" in original_content_text or
                "{{CONTEXT}}" in original_content_text or
                any(
                    "<source" in str(m.get("content", "")) or
                    "<context>" in str(m.get("content", ""))
                    for m in messages
                )
            )
            is_system_prompt = not has_rag_context and any(marker in original_content_text for marker in SYSTEM_PROMPT_MARKERS)

            if not privacy_enabled:
                log_privacy_off()

            elif is_system_prompt:
                internal_type = detect_internal_type(original_content_text)
                log_internal(internal_type)
                pseudonymized_user_message = original_content_text

            elif last_message.get("role") in ("user", "system", "developer"):
                log_in_user(original_content_text)
                log_in_user_full(original_content_text)

                existing_keys_before = set(store.get_store().get(session_id, {}).keys())

                last_msg_index = len(messages) - 1
                file_msgs_scanned = 0
                for i, msg in enumerate(messages):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "assistant":
                        continue
                    if role == "user" and i == last_msg_index:
                        continue
                    content_text = extract_text_content(content)
                    has_rag = "<context>" in content_text or "{{CONTEXT}}" in content_text or "<source" in content_text
                    if not has_rag:
                        continue

                    log_in_file(role, len(content_text), content_text)

                    if len(content_text) > 50000:
                        chunk_size = 10000
                        overlap = 200
                        chunks = [
                            content_text[max(0, i - overlap):i + chunk_size]
                            for i in range(0, len(content_text), chunk_size)
                        ]
                        log_large_file(len(content_text), len(chunks))
                        pseudo_chunks = [
                            pseudonymize(c, session_id, store.get_store(), enabled_types=enabled_types)
                            for c in chunks
                        ]
                        pseudo = "".join(pseudo_chunks)
                        msg["content"] = rebuild_content(msg["content"], pseudo)
                        log_out_file_chunked(len(chunks), len(pseudo))
                        continue

                    try:
                        pseudonymized_text = pseudonymize(
                            content_text, session_id, store.get_store(), enabled_types=enabled_types
                        )
                        msg["content"] = rebuild_content(content, pseudonymized_text)
                        log_out_file(pseudonymized_text)
                        log_file_delta(len(content_text), len(pseudonymized_text))
                        file_msgs_scanned += 1
                    except Exception as e:
                        log_error(f"file pseudonymization failed: {e} — skipping chunk")
                        continue

                if file_msgs_scanned > 0:
                    store.get_store().flush(session_id)
                    log_file_scan(file_msgs_scanned)

                new_keys = set(store.get_store().get(session_id, {}).keys()) - existing_keys_before
                file_entity_count = len(new_keys)

                if file_entity_count == 0:
                    seen_tokens = set()
                    for key, mapping in store._store.items():
                        if key.startswith("file:"):
                            seen_tokens.update(mapping.keys())
                    if not seen_tokens:
                        try:
                            from app.mapping_store import _redis_client
                            if _redis_client:
                                for rkey in _redis_client.keys("garnet:mapping:file:*"):
                                    raw = _redis_client.get(rkey)
                                    if raw:
                                        import json
                                        mapping = json.loads(raw)
                                        seen_tokens.update(mapping.keys())
                        except Exception:
                            pass
                    file_entity_count = len(seen_tokens)

                garnet_breakdown = {}
                try:
                    from app.mapping_store import _redis_client
                    if _redis_client:
                        for rkey in _redis_client.keys("garnet:mapping:file:*"):
                            raw = _redis_client.get(rkey)
                            if raw:
                                import json as _json
                                for token in _json.loads(raw).keys():
                                    prefix = token.rsplit("_", 1)[0]
                                    garnet_breakdown[prefix] = garnet_breakdown.get(prefix, 0) + 1
                except Exception:
                    pass

                if file_entity_count > 0:
                    log_file_pii(file_entity_count, garnet_breakdown)
                else:
                    if file_msgs_scanned > 0:
                        log_file_pii_duplicate()

                try:
                    pseudonymized_text = pseudonymize(
                        original_content_text, session_id, store.get_store(), enabled_types=enabled_types
                    )
                    last_message["content"] = rebuild_content(original_content, pseudonymized_text)
                    pseudonymized_user_message = pseudonymized_text
                    if pseudonymized_user_message != original_content_text:
                        log_out_user(pseudonymized_user_message)
                        log_out_user_full(pseudonymized_user_message)
                        _n_replaced = sum(1 for t in store.get_store().get(session_id, {}) if t in pseudonymized_user_message)
                        _types = list({t.rsplit("_", 1)[0] for t in store.get_store().get(session_id, {}) if t in pseudonymized_user_message})
                        log_pseudo_diff(len(original_content_text), len(pseudonymized_user_message), _n_replaced, _types)
                    else:
                        log_no_pii()
                    store.get_store().flush(session_id)
                except Exception as e:
                    log_error(f"user pseudonymization failed: {e} — forwarding raw")
                    pseudonymized_user_message = original_content_text
                    last_message["content"] = original_content

                # Query expansion — enrich the question for better RAG retrieval
                # NOTE: variants from gpt-4o-mini are NOT pseudonymized; they reach
                # the embedding model in OWU only, not the main LLM (known minor leak vector).
                if query_expand and has_rag_context:
                    print(f"[QUERY EXPAND] starting → question='{original_content_text[:100]}'")
                    auth_header = request.headers.get("authorization", "")
                    _expand_url = (openai_url if is_openai else OPENAI_API_URL)
                    variants = await expand_query(original_content_text, _expand_url, auth_header)

                    if variants:
                        print(f"[QUERY EXPAND] {len(variants)} variants generated:")
                        for i, v in enumerate(variants, 1):
                            print(f"  [{i}] {v}")

                        # Concatenate: pseudonymized original + variants → richer embed vector
                        enriched = pseudonymized_user_message + "\n" + "\n".join(variants)
                        last_message["content"] = rebuild_content(original_content, enriched)
                        print(f"[QUERY EXPAND] enriched query injected → {len(pseudonymized_user_message)} → {len(enriched)} chars")
                    else:
                        print(f"[QUERY EXPAND] no variants generated → using original query only")
                elif query_expand and not has_rag_context:
                    print(f"[QUERY EXPAND] skipped — no RAG context in this message")

        if body:
            _msgs = body.get("messages", [])
            _total_chars = sum(len(extract_text_content(m.get("content", ""))) for m in _msgs)
            log_context_size(len(_msgs), _total_chars)
        log_to_llm(url, model, int((time.perf_counter() - t0) * 1000))

    if is_openai:
        forward_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() in ("authorization", "content-type", "openai-organization", "x-openai-base-url")
        }
        if "anthropic.com" in url:
            auth = forward_headers.pop("authorization", "")
            api_key = auth.removeprefix("Bearer ").strip()
            forward_headers["x-api-key"] = api_key
            forward_headers.setdefault("anthropic-version", "2023-06-01")
    else:
        forward_headers = {}

    if is_chat and body and not is_openai:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=url,
                json=body,
                headers=forward_headers,
                timeout=120.0
            )
        try:
            result = orjson.loads(response.content)
            content = result.get("message", {}).get("content", "")

            session_mapping = dict(store.get_store().get(session_id, {}))
            if privacy_enabled:
                for key, mapping in store._store.items():
                    if key.startswith("file:"):
                        session_mapping.update(mapping)

            for token in sorted(session_mapping.keys(), key=len, reverse=True):
                content = content.replace(token, session_mapping[token])

            result["message"]["content"] = content
            result["pseudonymized_prompt"] = pseudonymized_user_message or ""
            result["file_entity_count"] = file_entity_count
            result["query_variants"] = variants or []

            log_to_user(len(session_mapping), 0.0, time.perf_counter() - t0)
            log_sep()
            return ORJSONResponse(content=result)

        except Exception as e:
            log_error(f"Ollama depseudo failed: {e} | raw={response.content[:200]}")
            return Response(content=response.content, status_code=response.status_code)

    if is_chat and body:
        async def response_stream():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    method=request.method,
                    url=url,
                    json=body,
                    headers=forward_headers,
                    timeout=120.0
                ) as resp:
                    if resp.status_code != 200:
                        err_body = await resp.aread()
                        log_error(f"status={resp.status_code} provider={url} body={err_body[:500]}")
                    if "anthropic.com" in url:
                        async for chunk in resp.aiter_bytes():
                            if chunk:
                                yield chunk
                    else:
                        async for chunk in resp.aiter_bytes():
                            if chunk:
                                yield chunk

        session_mapping = dict(store.get_store().get(session_id, {}))
        if privacy_enabled:
            for key, mapping in store._store.items():
                if key.startswith("file:"):
                    session_mapping.update(mapping)

        model = body.get("model", "unknown")
        log_mapping(session_id, len(session_mapping))

        if not body.get("stream", True):
            async with httpx.AsyncClient(timeout=60.0) as _client:
                _resp = await _client.request(
                    method=request.method,
                    url=url,
                    json=body,
                    headers=forward_headers,
                    timeout=60.0,
                )
                result = _resp.json()
                try:
                    content = result["choices"][0]["message"]["content"] or ""
                    for token in sorted(session_mapping.keys(), key=len, reverse=True):
                        content = content.replace(token, session_mapping[token])
                    result["choices"][0]["message"]["content"] = content
                except (KeyError, IndexError, TypeError):
                    pass
                log_to_user(len(session_mapping), 0.0, time.perf_counter() - t0)
                return ORJSONResponse(content=result)

        async def convert_responses_stream(source):
            async for chunk in source:
                if not chunk:
                    continue
                for line in chunk.decode("utf-8", errors="replace").split("\n"):
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        yield b"data: [DONE]\n\n"
                        return
                    try:
                        ev = orjson.loads(raw)
                        ev_type = ev.get("type", "")
                        if ev_type == "response.output_text.delta":
                            delta = ev.get("delta", "")
                            payload = orjson.dumps({"choices": [{"delta": {"content": delta}, "index": 0}]})
                            yield f"data: {payload.decode()}\n\n".encode()
                        elif ev_type in ("response.completed", "response.done"):
                            yield b"data: [DONE]\n\n"
                            return
                    except Exception:
                        pass

        src = convert_responses_stream(response_stream()) if use_responses_api else response_stream()
        return StreamingResponse(
            stream_with_depseudo(
                src, session_mapping, pseudonymized_user_message,
                session_id, url, model, file_entity_count, garnet_breakdown,
                variants=variants, t0=t0
            ),
            media_type="text/event-stream"
        )

    # strip response_format for image generation (gpt-image-1 rejects it)
    if body and "images/generations" in str(url):
        body.pop("response_format", None)
        print(f"[IMAGE GEN] stripped response_format → forwarding to {url}")

    async with httpx.AsyncClient() as client:
        if body:
            response = await client.request(
                method=request.method,
                url=url,
                json=body,
                headers=forward_headers,
                timeout=120.0
            )
        else:
            response = await client.request(
                method=request.method,
                url=url,
                headers=forward_headers,
                timeout=120.0
            )

    if response.status_code != 200:
        log_error_passthrough(response.status_code, url, response.text)

    excluded_headers = {"content-encoding", "content-length", "transfer-encoding"}
    filtered_headers = {
        k: v for k, v in response.headers.items()
        if k.lower() not in excluded_headers
    }
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=filtered_headers
    )
