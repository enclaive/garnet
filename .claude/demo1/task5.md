# Task 5 — Root Cause Analysis + Fix Plan (per defect class)

> Companion to `rca.md`. Each section: WHAT broke → WHY (with exact file:line) → HOW to fix.
> Source of truth: `backend/privacy_proxy/app/pseudonymizer.py` + `main.py`
> Frozen build: commit `dd9a4c29a`, image `sha256:33bbd35ccc84...`

---

## Defect Class A1 — Short German PERSON names not detected

### What broke
- P1B-BP-002-V2: `"Hendrik"` → forwarded verbatim to LLM (full PII leak)
- P1B-BP-005-V5: `"Lasse Farah Marchetti"` → `"Lasse PERSON_a8698aa4..."` (partial leak, first name kept)

### Why
**File:** `backend/privacy_proxy/app/pseudonymizer.py:22-23`

```python
"models": [{"lang_code": "de", "model_name": "de_core_news_md"}],
```

`de_core_news_md` (medium spaCy model) is too weak on isolated short German given names. It relies heavily on surrounding syntactic context. Single-token `"Hendrik"` at sentence start = 0 entities detected. Same name with a surname (`"Hendrik Öztürk"`) = correctly tagged PERSON.

For `"Lasse Farah Marchetti"`: spaCy tags `"Farah Marchetti"` as one span but drops `"Lasse"` — likely because "Lasse" is a common Danish/Swedish word too.

The container already has `de_core_news_lg` 3.7.0 installed. It's just not being loaded.

### Fix
Change one line: switch model name to `de_core_news_lg`.

```python
"models": [{"lang_code": "de", "model_name": "de_core_news_lg"}],
```

**Verification:** re-run T4D cases 002 + 005 through repro harness → both must return `PERSON_*` tokens with no `"Hendrik"` / `"Lasse"` leaks.

**Risk:** `lg` model is ~500MB vs `md` ~40MB — slower startup, higher memory. Acceptable for accuracy gain on production PII path.

---

## Defect Class A2 — LOCATION beats PERSON when both fire on same span

### What broke
- P1B-BP-001-V1: `"Adelbach"` (a German surname) tagged as `LOCATION_d1bfe8a1` instead of PERSON
- P1B-BP-009-V1: same — `"Adelbach"` → LOCATION

### Why
**File:** `pseudonymizer.py:78-83`

```python
def filter_overlaps(results):
    regex_types = {"EMAIL_ADDRESS", "IBAN_CODE", "PHONE_NUMBER", "ID", "ORGANIZATION", "LOCATION"}
    results = sorted(results, key=lambda x: (
        0 if x.entity_type in regex_types else 1,
        -(x.end - x.start)
    ))
```

When spaCy fires both PERSON and LOCATION on the same span (`"Adelbach"` ends in `-bach` which matches German place-name patterns), this sort assigns LOCATION priority 0 and PERSON priority 1. First-kept-wins → LOCATION always beats PERSON on overlap.

The intent of `regex_types` is "high-confidence deterministic regex hits should beat NER guesses." But LOCATION is not a regex — it's a spaCy prediction. It doesn't belong in this priority set.

### Fix
Remove `"LOCATION"` from `regex_types`:

```python
regex_types = {"EMAIL_ADDRESS", "IBAN_CODE", "PHONE_NUMBER", "ID", "ORGANIZATION"}
```

**Verification:** re-run cases 001 + 009 → `"Adelbach"` must be tagged PERSON.

**Risk:** places that ARE legitimately locations (city names) may now lose to spurious PERSON tags. Mitigate by keeping the WEEKDAYS denylist (Class C) and testing on P1B-BP-061-V5 (neutral control) — should still pass.

---

## Defect Class B — Whole JSON body treated as flat text

### What broke
- P1B-BP-001-V1: `case_id` UUID `"d401852a-..."` → `"ID_32aee100-..."` (UUID prefix mutated)
- P1B-BP-030-V6: same UUID mutation on email case (`e92689f3` → `ID_06461de7`)
- P1B-BP-096-V0: `items[1].label` key vanished, `items[1].id` value corrupted (JSON structure broken)

### Why
**File:** `pseudonymizer.py:198`

```python
def pseudonymize(text: str, session_id: str, store: dict, enabled_types=None) -> str:
```

The proxy serializes the entire request body to a JSON string and passes it to `pseudonymize()`. The NER + regex pipeline sees the whole string — including keys, UUIDs, colons, brackets — as undifferentiated text.

`id_recognizer_de` (registered at `pseudonymizer.py:25`) detects UUID hex-dash patterns as `ID` entities. The UUID in `"case_id": "d401852a-88c5-..."` matches → replaced with `ID_<hash>`.

For the key-removal bug in case 096: token replacement mid-JSON-string shifts byte offsets. When the resulting string is re-parsed as JSON, the shifted quotation marks land in the wrong place → keys and values swap or disappear.

**Evidence — exact hash reproduction:**
```
[IN  USER] {"case_id":"d401852a-...","text":"Am Montag war Adelbach nicht erreichbar."}
[OUT USER] {"case_id":"ID_32aee100-...","text":"Am LOCATION_b703fc6a war LOCATION_d1bfe8a1 nicht erreichbar."}
```

### Fix
**Option 1 (recommended) — JSON-aware walker:**
Parse the body, pseudonymize **only string values at known text-bearing paths** (`text`, `messages[].content`, `input`, `prompt`), rebuild JSON. All other fields (keys, UUIDs, numbers, booleans, arrays) pass through byte-identical.

Add helper in `pseudonymizer.py`:
```python
def pseudonymize_json(body: dict, session_id: str, store: dict, text_paths: list[str], enabled_types=None) -> dict:
    """Walk body, pseudonymize only string values at text_paths, rest byte-identical."""
    # implementation: recursive walk, only mutate strings at whitelisted paths
```

Call from `main.py` proxy() around line 632 instead of the current flat-string approach.

**Option 2 (minimal — 1 line):**
Remove `id_recognizer_de/en` from the recognizer list at `pseudonymizer.py:25, 31`. UUID detection in free text is low-precision and not needed for Garnet (human-language PII, not identifier scrubbing).

This alone fixes UUID mutation but does NOT fix the key-removal bug in 096 — that still needs the JSON walker.

**Recommendation:** ship both — remove `id_recognizer` (Option 2) as a quick safety net + implement JSON walker (Option 1) as the proper structural fix.

**Verification:** re-run cases 001, 030, 096 → all UUIDs and JSON keys byte-identical. Only text-bearing fields pseudonymized.

---

## Defect Class C — German weekdays tagged as LOCATION

### What broke
- P1B-BP-001-V1: `"Montag"` → `LOCATION_b703fc6a`
- P1B-BP-009-V1: `"Montag"` → `LOCATION_b703fc6a` (same hash)

Same token hash both times confirms it's the same surface text producing the same false positive.

### Why
`de_core_news_md` (and likely `lg` too) tags German weekday names as LOCATION — they match place-name patterns in spaCy's German training data. No post-NER filter rejects known non-PII tokens.

### Fix
Add a denylist filter in `detect_entities()` at `pseudonymizer.py:145` (right after `analyzer.analyze()`, before `trim_org_results`):

```python
WEEKDAYS_DE = {"Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"}
results = [r for r in results if stripped_text[r.start:r.end] not in WEEKDAYS_DE]
```

7-item constant, no model change, no runtime cost.

**Verification:** re-run cases 001 + 009 → `"Montag"` must appear unchanged in output.

**Risk:** none — weekdays are never PII.

---

## Summary — one-line-per-fix

| Class | File:line | Fix | Complexity |
|-------|-----------|-----|-----------|
| A1 | `pseudonymizer.py:23` | `de_core_news_md` → `de_core_news_lg` | 1 line |
| A2 | `pseudonymizer.py:79` | Remove `"LOCATION"` from `regex_types` | 1 line |
| B  | `pseudonymizer.py:198` + `main.py:632` | JSON-aware walker (+ remove `id_recognizer`) | ~30 lines |
| C  | `pseudonymizer.py:~146` | Add `WEEKDAYS_DE` denylist | 2 lines |

**Total real diff:** ~35 lines across 2 files. All 4 fixes covered by existing repro harness (`test_t4d_repro.py`).

---

## Execution order (safe path)

1. **Class C** first (weekday denylist) — smallest, zero-risk, unblocks cases 001+009
2. **Class A2** (remove LOCATION from priority set) — fixes Adelbach cases
3. **Class A1** (switch to lg model) — improves general PERSON coverage, needs container rebuild verification
4. **Class B** last — biggest change, needs new unit tests for JSON path enumeration

After each fix, re-run `pytest backend/privacy_proxy/tests/test_t4d_repro.py` — expect one more test to pass per fix.

---

*Author: Ahmed Marzougui · 2026-08-06*
