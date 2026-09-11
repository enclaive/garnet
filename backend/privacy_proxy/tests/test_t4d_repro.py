"""
T4D demo-1 reproduction harness.
Feeds the 7 vendor defect cases through pseudonymize() directly and
checks whether each known bug reproduces. Run with:

    cd backend/privacy_proxy
    python -m pytest tests/test_t4d_repro.py -v

or standalone:

    python tests/test_t4d_repro.py
"""

import json
import pathlib
import sys
import os

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
os.environ.setdefault("REDIS_URL", "")

from app.pseudonymizer import pseudonymize

_candidates = [
    pathlib.Path(__file__).parent.parent.parent.parent / ".claude/demo1/vendor_defect_cases.jsonl",
    pathlib.Path("/tmp/vendor_defect_cases.jsonl"),
    pathlib.Path("/app/.claude/demo1/vendor_defect_cases.jsonl"),
]
CASES_PATH = next(p for p in _candidates if p.exists())


def load_cases():
    with open(CASES_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def pseudo_body(body: dict, session_id: str) -> dict:
    """Simulate how the proxy pseudonymizes a JSON body passed as flat text."""
    raw = json.dumps(body, ensure_ascii=False)
    store = {}
    result = pseudonymize(raw, session_id, store)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": result}


def run_case(case: dict) -> dict:
    inp = case["input"]
    session_id = inp.get("case_id", "test")
    result = pseudo_body(inp, session_id)
    return {
        "case_id": case["test_case_id"],
        "finding": case["finding"],
        "input": inp,
        "result": result,
        "expected_upstream": json.loads(case["proxy_reported_upstream"]),
    }


# ── individual bug checks ────────────────────────────────────────────────────

def test_P1B_BP_001_uuid_mutated_and_person_not_protected():
    """UUID should be byte-identical; 'Adelbach' should be PERSON not LOCATION."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-001-V1"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    # UUID must not change
    assert r.get("case_id") == c["input"]["case_id"], (
        f"UUID mutated: {c['input']['case_id']} → {r.get('case_id')}"
    )
    # 'Adelbach' must not appear verbatim in the output text
    assert "Adelbach" not in r.get("text", ""), (
        f"'Adelbach' leaked verbatim in text: {r.get('text')}"
    )


def test_P1B_BP_009_weekday_not_redacted():
    """'Montag' (weekday) must pass through unchanged."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-009-V1"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    assert "Montag" in r.get("text", ""), (
        f"Weekday 'Montag' was over-redacted: {r.get('text')}"
    )


def test_P1B_BP_002_full_person_leak():
    """'Hendrik' must be pseudonymized, not forwarded verbatim."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-002-V2"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    assert "Hendrik" not in r.get("text", ""), (
        f"'Hendrik' leaked verbatim: {r.get('text')}"
    )


def test_P1B_BP_005_partial_person_leak():
    """All components of 'Lasse Farah Marchetti' must be pseudonymized."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-005-V5"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    text = r.get("text", "")
    assert "Lasse" not in text, f"'Lasse' leaked: {text}"
    assert "Farah" not in text, f"'Farah' leaked: {text}"
    assert "Marchetti" not in text, f"'Marchetti' leaked: {text}"


def test_P1B_BP_096_json_structure_intact():
    """keys, id values, and array structure must survive pseudonymization."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-096-V0"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    assert "_parse_error" not in r, f"Result is not valid JSON: {r.get('_raw', '')[:200]}"
    assert isinstance(r.get("items"), list), "items array missing"
    assert len(r["items"]) == 2, f"items length changed: {len(r['items'])}"
    assert "label" in r["items"][1], f"'label' key removed from items[1]: {r['items'][1]}"
    assert r.get("case_id") == c["input"]["case_id"], f"case_id mutated: {r.get('case_id')}"


def test_P1B_BP_030_email_uuid_not_mutated():
    """Email pseudonymized; case_id UUID byte-identical."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-030-V6"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    assert r.get("case_id") == c["input"]["case_id"], (
        f"UUID mutated: {c['input']['case_id']} → {r.get('case_id')}"
    )
    assert "test.user247@example.invalid" not in r.get("text", ""), (
        f"Email not pseudonymized: {r.get('text')}"
    )


def test_P1B_BP_061_neutral_document_unchanged():
    """Neutral doc with no PII must pass through byte-identical."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["P1B-BP-061-V5"]
    r = pseudo_body(c["input"], c["input"]["case_id"])

    for key in ("case_id", "text", "reference_id", "active", "score"):
        assert r.get(key) == c["input"].get(key), (
            f"Neutral field '{key}' changed: {c['input'].get(key)} → {r.get(key)}"
        )


def test_T4D_B1_hyphenated_unicode_person():
    """B1 (T4D 2026-09): 'Anna Müller-Öztürk' must be one PERSON marker; no name component leaks."""
    cases = {c["test_case_id"]: c for c in load_cases()}
    c = cases["T4D-B1-V1"]
    r = pseudo_body(c["input"], "b1-regression")
    name = r.get("name", "")
    for token in ("Anna", "Müller", "Öztürk"):
        assert token not in name, f"'{token}' leaked in name: {name}"
    assert name.startswith("PERSON_"), f"name should be a single PERSON marker: {name}"


def test_T4D_B1_variants_multipart_unicode_hyphenated():
    """General fix must cover multi-part, Unicode, and hyphenated / apostrophe surnames."""
    variants = [
        ("Jean-François Müller", ["Jean", "François", "Müller"]),
        ("José García-López",    ["José", "García", "López"]),
        ("Anne O'Brien",         ["Anne", "Brien"]),
        ("Ahmed Al-Rashid",      ["Ahmed", "Rashid"]),
    ]
    for surface, components in variants:
        r = pseudo_body({"name": surface}, f"variant-{surface[:5]}")
        name = r.get("name", "")
        for token in components:
            assert token not in name, f"'{token}' leaked from '{surface}': {name}"
        assert name.startswith("PERSON_"), f"'{surface}' not a single PERSON marker: {name}"


# ── standalone report ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = load_cases()
    results = []
    passed = 0
    failed = 0

    checks = [
        ("P1B-BP-001-V1", test_P1B_BP_001_uuid_mutated_and_person_not_protected),
        ("P1B-BP-009-V1", test_P1B_BP_009_weekday_not_redacted),
        ("P1B-BP-002-V2", test_P1B_BP_002_full_person_leak),
        ("P1B-BP-005-V5", test_P1B_BP_005_partial_person_leak),
        ("P1B-BP-096-V0", test_P1B_BP_096_json_structure_intact),
        ("P1B-BP-030-V6", test_P1B_BP_030_email_uuid_not_mutated),
        ("P1B-BP-061-V5", test_P1B_BP_061_neutral_document_unchanged),
        ("T4D-B1-V1",     test_T4D_B1_hyphenated_unicode_person),
        ("T4D-B1-VARIANTS", test_T4D_B1_variants_multipart_unicode_hyphenated),
    ]

    print("\n=== T4D REPRO HARNESS ===\n")
    for case_id, fn in checks:
        try:
            fn()
            print(f"  PASS  {case_id}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {case_id}: {e}")
            failed += 1

    total = len(checks)
    print(f"\nResult: {passed}/{total} pass, {failed}/{total} fail")
    print("(All should FAIL on the frozen build — that confirms reproduction.)\n")
    sys.exit(0 if failed > 0 else 1)  # exit 0 if bugs reproduced, 1 if nothing to fix
