# Root Cause Analysis — T4D Demo-1 Defect Cases

> Based on: code review of `pseudonymizer.py` + `main.py` + live log analysis of the actual T4D test run
> Build: commit `dd9a4c29a`, image `sha256:33bbd35ccc84...`
> T4D test date: 2026-08-04, provider: Ollama / llama3.2:3b
> Date of this analysis: 2026-08-06

---

## Reproduction status

**7/7 cases reproduced via live proxy** (Ollama / llama3.2:3b, same setup as T4D's 2026-08-04 test).
Reproduction completed: 2026-08-06.

| Case | Finding | Method | Key evidence |
|------|---------|--------|-------------|
| P1B-BP-002-V2 | Full PERSON leak — Hendrik | Aug 4 logs + live repro | `[NO PII] message unchanged` — 0 entities detected |
| P1B-BP-001-V1 | UUID mutated + Adelbach as LOCATION | Live proxy | `case_id`: `d401852a` → `ID_32aee100` (exact hash); `Adelbach` → `LOCATION_d1bfe8a1` |
| P1B-BP-005-V5 | Partial PERSON leak — Lasse | Live proxy | `Lasse PERSON_a8698aa4` — exact hash match T4D report |
| P1B-BP-009-V1 | Weekday over-redaction + Adelbach | Live proxy | `Montag` → `LOCATION_b703fc6a`; `Adelbach` → `LOCATION_d1bfe8a1` |
| P1B-BP-096-V0 | JSON structure / text truncation | Live proxy | `Anna Weber` → `PERSON_3302a58d`, text body truncated (JSON flat-text corruption) |
| P1B-BP-030-V6 | UUID mutated (email case) | Live proxy | `case_id`: `e92689f3` → `ID_06461de7` (exact hash); email → `EMAIL_ADDRESS_fa8e7430` (exact hash) |
| P1B-BP-061-V5 | Neutral control — passes | Live proxy | `[NO PII] message unchanged` — byte-identical, no entities detected |

---

## Important clarification — entity filter

During T4D's test (Ollama provider), **no entity filter was active**. The logs show no `[ENTITY FILTER]` line for any T4D session. All entity types including PERSON were enabled.

The `[ENTITY FILTER] active → only: ['ORGANIZATION', 'EMAIL_ADDRESS', 'IBAN_CODE', 'PHONE_NUMBER', 'ID', 'LOCATION']` line seen in current Anthropic sessions is a **separate OWU misconfiguration** for the Anthropic connection (PERSON missing from allowed list). This is a second bug but was NOT active during T4D's test.

**T4D's PERSON leaks are NER failures, not a filter issue.**

---

## Defect Class A — German PERSON name leaks

### Cases
- P1B-BP-002-V2: "Hendrik" → `[NO PII]` — full leak
- P1B-BP-005-V5: "Lasse Farah Marchetti" → "Lasse PERSON_a8698aa4" — partial leak
- P1B-BP-001-V1: "Adelbach" → `LOCATION_d1bfe8a1` — wrong entity type
- P1B-BP-009-V1: "Adelbach" → LOCATION again, "Lasse" → PERSON (caught)

### Root cause 1 — NER model misses short German names

**File:** `backend/privacy_proxy/app/pseudonymizer.py:22`

```python
"models": [{"lang_code": "de", "model_name": "de_core_news_md"}],
```

`de_core_news_md` (medium) fails to detect short/ambiguous German names without context:
- "Hendrik" alone → not detected (0 entities)
- "Hendrik Öztürk" (with surname) → detected correctly as PERSON
- "Lasse" alone → missed; "Farah Marchetti" caught as one span

The large model `de_core_news_lg` (3.7.0) is installed in the container but never loaded.

**Evidence from logs:**
```
[IN  USER] {"case_id":"54391f39-...","text":"Hendrik übernimmt die Frühschicht."}
[NO PII] message unchanged — no entities detected
```
vs same session later:
```
[IN  USER] {"case_id":"bfcb50ea-...","text":"Gestern hat Hendrik Öztürk die Lieferung angenommen."}
[OUT USER] {"text":"Gestern hat PERSON_cd32cb6d die Lieferung angenommen."}
```

### Root cause 2 — LOCATION beats PERSON in overlap resolver

**File:** `backend/privacy_proxy/app/pseudonymizer.py:79`

```python
regex_types = {"EMAIL_ADDRESS", "IBAN_CODE", "PHONE_NUMBER", "ID", "ORGANIZATION", "LOCATION"}
results = sorted(results, key=lambda x: (
    0 if x.entity_type in regex_types else 1,
    -(x.end - x.start)
))
```

`LOCATION` is in `regex_types` (sort priority 0). `PERSON` is not (priority 1). When spaCy fires both on "Adelbach" — a German surname that matches place-name patterns (-bach suffix) — LOCATION always wins.

**Evidence from logs:**
```
"Am Montag war Adelbach nicht erreichbar."
→ "Am LOCATION_b703fc6a war LOCATION_d1bfe8a1 nicht erreichbar."
types=['ID', 'LOCATION']
```
"Adelbach" pseudonymized as LOCATION, not PERSON.

But with "von" prefix giving surname context:
```
"von Adelbach übernimmt die Frühschicht."
→ "von PERSON_d1bfe8a1 übernimmt die Frühschicht."
```
PERSON wins when syntactic context clarifies it's a name.

### Fix A
1. Switch `de_core_news_md` → `de_core_news_lg` in `build_analyzer()` — improves single-name detection
2. Remove `LOCATION` from `regex_types` in `filter_overlaps()` — LOCATION is a spaCy entity, not a regex entity; it should not have override priority over PERSON

---

## Defect Class B — Non-annotated JSON mutation

### Cases
- P1B-BP-001-V1: `case_id` UUID `d401852a-...` → `ID_32aee100-...`
- P1B-BP-030-V6: `case_id` UUID `e92689f3-...` → `ID_06461de7-...`
- P1B-BP-096-V0: `items[1].label` key removed; `items[1].id` value corrupted

### Root cause — pseudonymize() treats the entire serialized JSON as flat text

**File:** `backend/privacy_proxy/app/pseudonymizer.py:198`

```python
def pseudonymize(text: str, ...) -> str:
```

The proxy serializes the entire JSON body to a string and passes it to `pseudonymize()`. The NER pipeline then sees the full string including keys, UUIDs, colons, and brackets as undifferentiated text.

`id_recognizer_de` is registered in the analyzer. It detects UUID-shaped hex-dash patterns as ID entities and replaces them with `ID_<hash>`. The UUID in `"case_id": "d401852a-..."` matches this pattern → mutated.

For the key-removal bug in P1B-BP-096-V0: the substitution token lands mid-JSON-string, shifting offsets and corrupting the surrounding key-value structure when the result is re-parsed as JSON.

**Evidence — exact log match:**
```
[IN  USER]  {"case_id":"d401852a-88c5-51ac-ae15-8d31e0e01b78","text":"Am Montag war Adelbach nicht erreichbar."}
[OUT USER]  {"case_id":"ID_32aee100-88c5-51ac-ae15-8d31e0e01b78","text":"Am LOCATION_b703fc6a war LOCATION_d1bfe8a1 nicht erreichbar."}
```
UUID prefix `d401852a` replaced with `ID_32aee100` — same hash as T4D's report.

### Fix B
Option 1 (recommended): JSON-aware walker — parse the body, pseudonymize only string values at known text-bearing paths (`text`, `messages[].content`, `input`), rebuild JSON. All other fields pass through byte-identical.

Option 2 (minimal): Remove `id_recognizer_de/en` from the recognizer list. UUID detection in free text is low-precision and not needed for Garnet's use case (human-language PII). This alone fixes UUID mutation; does not fix key-removal which needs the JSON walker.

---

## Defect Class C — Weekday over-redaction

### Cases
- P1B-BP-001-V1: "Montag" → `LOCATION_b703fc6a`
- P1B-BP-009-V1: "Montag" → `LOCATION_b703fc6a`

### Root cause — no denylist for German weekdays

`de_core_news_md` tags German weekday names as LOCATION (they match place-name patterns in spaCy's German training data). No post-filter exists to reject known non-PII tokens.

Token `LOCATION_b703fc6a` is the same hash in both cases — confirms it's the same surface "Montag" both times.

### Fix C
Add a post-filter after `analyzer.analyze()` rejecting any result whose surface is a German weekday:
```python
WEEKDAYS_DE = {"Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"}
results = [r for r in results if stripped_text[r.start:r.end] not in WEEKDAYS_DE]
```
7-item constant, no model change needed.

---

## Additional bug (separate from T4D's test) — PERSON excluded from Anthropic connection

**Not part of T4D's finding.** When using the Anthropic/OpenAI model connections in OWU, the proxy receives:
```
[ENTITY FILTER] active → only: ['ORGANIZATION', 'EMAIL_ADDRESS', 'IBAN_CODE', 'PHONE_NUMBER', 'ID', 'LOCATION']
```
PERSON is missing. This is an OWU connection configuration issue — the `x-garnet-entities` header for the Anthropic model is missing PERSON. Must be fixed in OWU admin → model connection settings before any OpenAI/Anthropic production use.

---

## Summary table

| Class | Case(s) | Root cause | File:line | Fix |
|-------|---------|------------|-----------|-----|
| A1 — NER misses short names | 002, 005 | Wrong German model | `pseudonymizer.py:22` | Use `de_core_news_lg` |
| A2 — LOCATION beats PERSON | 001, 009 | Overlap priority bug | `pseudonymizer.py:79` | Remove LOCATION from regex_types |
| B — JSON treated as flat text | 001, 030, 096 | pseudonymize() is string-only | `pseudonymizer.py:198` + main.py | JSON-aware walker |
| C — Weekday over-redaction | 001, 009 | No denylist | `pseudonymizer.py:143` | Add weekday denylist |
| Extra — PERSON filter missing | current Anthropic sessions | OWU misconfiguration | OWU admin panel | Add PERSON to entity filter |

---

## Evidence grade note

T4D's evidence is `proxy_self_report` — the `[OUT USER]` log lines. These are Garnet's own logs of what it forwarded upstream, not an independent network capture. The proxy self-report is confirmed accurate: our `[OUT USER]` log entries exactly match T4D's `proxy_reported_upstream` field including token hashes.

---

*Author: Ahmed Marzougui · 2026-08-06*
*Reviewed against: live proxy logs + vendor_defect_cases.jsonl + pseudonymizer.py source*
