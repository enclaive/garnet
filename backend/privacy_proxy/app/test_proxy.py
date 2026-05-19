#!/usr/bin/env python3
"""
Garnet Proxy — Manual Test Script
Run on cVM: docker exec -w /service garnet-privacy-proxy-1 python3 app/test_proxy.py
"""

import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8080"
PASS = "✅"
FAIL = "❌"
results = []

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def check(name, condition, got=""):
    status = PASS if condition else FAIL
    msg = f"{status} {name}"
    if not condition:
        msg += f" | got: {got}"
    print(msg)
    results.append((name, condition))


def post(path, payload, headers=None):
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=h)
    try:
        res = urllib.request.urlopen(req, timeout=10)
        return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}


def get(path):
    try:
        res = urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10)
        return json.loads(res.read())
    except Exception as e:
        return {"error": str(e)}


print(SEP)
print("[TEST] Garnet Proxy — starting test suite")
print(SEP)

# ── T01 health ──────────────────────────────────────────
print("\n[T01] Health check")
res = get("/health")
check("health returns ok", res.get("status") == "ok", res)

# ── T02 logs.py import ──────────────────────────────────
print("\n[T02] logs.py import")
try:
    from app.logs import (
        log_health, log_garnet, log_in_user, log_out_user,
        log_file_pii, log_internal, log_privacy_off,
        log_to_llm, log_to_user, log_error, log_sep,
        log_vault_start, log_vault_done, log_analyze,
        log_analyze_result, log_no_pii, log_in_file,
        log_out_file, log_history_depseudo, log_mapping,
        log_self_loop, log_error_passthrough
    )
    check("logs.py imports cleanly", True)
    # call each function to verify no crash
    try:
        log_sep()
        log_health()
        log_garnet("abc12345", "openai", True, "gpt-4o", "/openai/v1/chat/completions")
        log_in_user("test message")
        log_out_user("PERSON_abc12345")
        log_no_pii()
        log_in_file("user", 100, "file content")
        log_out_file("pseudonymized content")
        log_file_pii(2, {"PERSON": 1, "EMAIL_ADDRESS": 1})
        log_internal("title_gen")
        log_privacy_off()
        log_history_depseudo(3)
        log_to_llm("https://api.openai.com/v1", "gpt-4o")
        log_to_user(5)
        log_mapping("abc12345", 5)
        log_self_loop("https://api.openai.com/v1")
        log_vault_start("file-001", "file:file-001", None)
        log_vault_done("file-001", 3, {"PERSON": 2, "EMAIL_ADDRESS": 1})
        log_analyze("de", None, "test text")
        log_analyze_result(2, ["PERSON", "EMAIL_ADDRESS"])
        log_error("test error")
        log_error_passthrough(500, "https://api.openai.com", "error body")
        check("all log functions callable", True)
    except Exception as e:
        check("all log functions callable", False, str(e))
except Exception as e:
    check("logs.py imports cleanly", False, str(e))

# ── T03 analyze — PERSON + ORG ──────────────────────────
print("\n[T03] /analyze — PERSON + ORGANIZATION")
res = post("/analyze", {"text": "Max Mustermann works at Enclaive GmbH"})
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON detected", "PERSON" in types, types)
check("ORGANIZATION detected", "ORGANIZATION" in types, types)

# ── T04 analyze — EMAIL ──────────────────────────────────
print("\n[T04] /analyze — EMAIL_ADDRESS")
res = post("/analyze", {"text": "Contact me at max@enclaive.com"})
types = [e.get("type") for e in res.get("entities", [])]
check("EMAIL_ADDRESS detected", "EMAIL_ADDRESS" in types, types)

# ── T05 analyze — IBAN ───────────────────────────────────
print("\n[T05] /analyze — IBAN_CODE")
res = post("/analyze", {"text": "IBAN: DE89370400440532013000"})
types = [e.get("type") for e in res.get("entities", [])]
check("IBAN_CODE detected", "IBAN_CODE" in types, types)

# ── T06 analyze — PHONE ──────────────────────────────────
print("\n[T06] /analyze — PHONE_NUMBER")
res = post("/analyze", {"text": "Call me at +49 172 99887766"})
types = [e.get("type") for e in res.get("entities", [])]
check("PHONE_NUMBER detected", "PHONE_NUMBER" in types, types)

# ── T07 analyze — German text ────────────────────────────
print("\n[T07] /analyze — German NER")
res = post("/analyze", {"text": "Mein Name ist Thomas Müller von Siemens AG"})
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON detected in German", "PERSON" in types, types)

# ── T08 analyze — entity filter ──────────────────────────
print("\n[T08] /analyze — entity filter (PERSON only)")
res = post(
    "/analyze",
    {"text": "Anna Schmidt, email: anna@test.com"},
    headers={"x-garnet-entities": "PERSON"}
)
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON returned", "PERSON" in types, types)
check("EMAIL_ADDRESS filtered out", "EMAIL_ADDRESS" not in types, types)

# ── T09 analyze — no PII ─────────────────────────────────
print("\n[T09] /analyze — no PII in text")
res = post("/analyze", {"text": "What is the capital of France?"})
entities = res.get("entities", [])
check("no entities detected", len(entities) == 0, entities)

# ── T10 vault/scan ───────────────────────────────────────
print("\n[T10] /vault/scan — pseudonymizes file content")
res = post("/vault/scan", {
    "text": "Anna Schmidt, email: anna@enclaive.com, IBAN: DE89370400440532013000",
    "file_id": "test-file-001",
    "privacy_proxy": True
})
check("entity_count > 0", res.get("entity_count", 0) > 0, res.get("entity_count"))
pseudo_text = res.get("pseudonymized_text", "")
check("pseudonymized_text contains PERSON token", "PERSON_" in pseudo_text, pseudo_text[:100])
check("pseudonymized_text contains EMAIL token", "EMAIL_ADDRESS_" in pseudo_text, pseudo_text[:100])
check("pseudonymized_text contains IBAN token", "IBAN_CODE_" in pseudo_text, pseudo_text[:100])
check("original name not in pseudonymized", "Anna Schmidt" not in pseudo_text, pseudo_text[:100])
check("original email not in pseudonymized", "anna@enclaive.com" not in pseudo_text, pseudo_text[:100])

# ── T11 vault/scan — privacy OFF ─────────────────────────
print("\n[T11] /vault/scan — privacy OFF returns raw text")
original = "Anna Schmidt works at Enclaive"
res = post("/vault/scan", {
    "text": original,
    "file_id": "test-file-002",
    "privacy_proxy": False
})
check("entity_count=0 when privacy OFF", res.get("entity_count") == 0, res.get("entity_count"))
check("text unchanged when privacy OFF", res.get("pseudonymized_text") == original, res.get("pseudonymized_text", "")[:80])

# ── T12 German false positive — verb not PERSON ──────────
print("\n[T12] /analyze — German verb 'Schreibe' not PERSON")
res = post("/analyze", {"text": "Schreibe mir eine E-Mail"})
types = [e.get("type") for e in res.get("entities", [])]
check("'Schreibe' not detected as PERSON", "PERSON" not in types, types)

# ── T13 duplicate upload — deterministic tokens ───────────
print("\n[T13] /vault/scan — duplicate upload same file_id")
text = "John Doe, john.doe@example.com"
res1 = post("/vault/scan", {
    "text": text,
    "file_id": "test-dedup-001",
    "privacy_proxy": True
})
pseudo1 = res1.get("pseudonymized_text", "")
count1 = res1.get("entity_count", 0)

res2 = post("/vault/scan", {
    "text": text,
    "file_id": "test-dedup-001",
    "privacy_proxy": True
})
pseudo2 = res2.get("pseudonymized_text", "")
count2 = res2.get("entity_count", 0)

check("first upload finds entities", count1 > 0, count1)
check("duplicate upload — 0 new entities", count2 == 0, count2)
check("same tokens both uploads", pseudo1 == pseudo2, f"\n  first:  {pseudo1}\n  second: {pseudo2}")

# ── T14 vault/scan — LOCATION detected ───────────────────
print("\n[T14] /analyze — LOCATION detected")
res = post("/analyze", {"text": "I live in Berlin, Germany"})
types = [e.get("type") for e in res.get("entities", [])]
check("LOCATION detected", "LOCATION" in types, types)

# ── T15 vault/scan — breakdown correct ───────────────────
print("\n[T15] /vault/scan — entity_breakdown correct")
res = post("/vault/scan", {
    "text": "Hans Müller, hans@test.de, +49 30 12345678",
    "file_id": "test-breakdown-001",
    "privacy_proxy": True
})
breakdown = res.get("entity_breakdown", {})
check("PERSON in breakdown", "PERSON" in breakdown, breakdown)
check("EMAIL_ADDRESS in breakdown", "EMAIL_ADDRESS" in breakdown, breakdown)

# ── T16 chunk boundary — token not split ─────────────────
print("\n[T16] split_at_safe_boundary — token prefix held back")
import sys
sys.path.insert(0, "/service")
try:
    from app.main import split_at_safe_boundary
    safe, remainder = split_at_safe_boundary("Hello PERSON")
    check("'PERSON' prefix held in remainder", remainder == "PERSON", f"safe={safe!r} remainder={remainder!r}")

    safe, remainder = split_at_safe_boundary("Hello PERSON_abc123ef")
    check("partial hash held in remainder", "PERSON_abc123ef" in remainder, f"safe={safe!r} remainder={remainder!r}")

    safe, remainder = split_at_safe_boundary("Hello world")
    check("no token — full buffer returned safe", safe == "Hello world" and remainder == "", f"safe={safe!r} remainder={remainder!r}")

    safe, remainder = split_at_safe_boundary("Call EMAIL_ADDRESS_cc75010d please")
    check("complete token in safe buffer passes through", "EMAIL_ADDRESS_cc75010d" in safe, f"safe={safe!r}")
except Exception as e:
    check("split_at_safe_boundary import", False, str(e))

# ── T17 analyze — multiple entities same text ─────────────
print("\n[T17] /analyze — multiple entity types in one text")
res = post("/analyze", {
    "text": "Max Mustermann, max@test.de, +49 89 12345, DE89370400440532013000, Siemens AG"
})
types = [e.get("type") for e in res.get("entities", [])]
check("PERSON found", "PERSON" in types, types)
check("EMAIL_ADDRESS found", "EMAIL_ADDRESS" in types, types)
check("PHONE_NUMBER found", "PHONE_NUMBER" in types, types)
check("IBAN_CODE found", "IBAN_CODE" in types, types)
check("ORGANIZATION found", "ORGANIZATION" in types, types)

# ── T18 vault/scan — preview field present ───────────────
print("\n[T18] /vault/scan — response has preview field")
res = post("/vault/scan", {
    "text": "Test User test@example.com",
    "file_id": "test-preview-001",
    "privacy_proxy": True
})
preview = res.get("preview", {})
check("preview.before present", "before" in preview, preview)
check("preview.after present", "after" in preview, preview)
check("preview.before contains original", "Test User" in preview.get("before", ""), preview.get("before", ""))

# ── T19 vault/scan — missing file_id returns error ────────
print("\n[T19] /vault/scan — missing file_id")
res = post("/vault/scan", {
    "text": "Some text without file_id",
    "privacy_proxy": True
})
check("error returned when file_id missing", "error" in res, res)

# ── T20 analyze — empty text ─────────────────────────────
print("\n[T20] /analyze — empty text")
res = post("/analyze", {"text": ""})
entities = res.get("entities", [])
check("empty text returns empty entities", len(entities) == 0, entities)

# ── SUMMARY ──────────────────────────────────────────────
print(f"\n{SEP}")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"[RESULT] {passed}/{len(results)} passed — {failed} failed")
if failed:
    print("[FAILED TESTS]")
    for name, ok in results:
        if not ok:
            print(f"  {FAIL} {name}")
print(SEP)