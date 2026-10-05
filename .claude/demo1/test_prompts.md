# T4D Reproduction — Manual Test Sheet

**How to use:**
1. Open https://garnet.enclaive.cloud → new chat → model: gpt-4o or gpt-4o-mini
2. Paste the PROMPT for each case and send
3. On cVM run: `docker logs garnet-privacy-proxy-1 --tail 20`
4. Find the line starting with `[OUT]` or `[PSEUDO]` — that's what the proxy sent upstream
5. Compare to WHAT T4D SAW and WHAT SHOULD HAPPEN

---

## Case 1 — P1B-BP-002-V2 — Full PERSON leak

**PASTE THIS:**
```
{"case_id": "54391f39-8249-5339-881b-b4e2555839c8", "text": "Hendrik übernimmt die Frühschicht."}
```

| | |
|--|--|
| **What T4D saw upstream** | `{"case_id": "54391f39-...", "text": "Hendrik übernimmt die Frühschicht."}` — UNCHANGED |
| **What should happen** | `"Hendrik"` → `PERSON_xxx` |
| **Bug** | Full PERSON leak — name forwarded verbatim to OpenAI |

---

## Case 2 — P1B-BP-005-V5 — Partial PERSON leak

**PASTE THIS:**
```
{"case_id": "9291d536-c938-5903-af80-043010c3180c", "text": "Lasse Farah Marchetti übernimmt die Frühschicht."}
```

| | |
|--|--|
| **What T4D saw upstream** | `"Lasse PERSON_a8698aa4 übernimmt die Frühschicht."` |
| **What should happen** | All 3 name parts → `PERSON_xxx` |
| **Bug** | `"Lasse"` leaked — only middle+surname pseudonymized |

---

## Case 3 — P1B-BP-001-V1 — UUID mutated + wrong entity type

**PASTE THIS:**
```
{"case_id": "d401852a-88c5-51ac-ae15-8d31e0e01b78", "text": "Am Montag war Adelbach nicht erreichbar."}
```

| | |
|--|--|
| **What T4D saw upstream** | `{"case_id": "ID_32aee100-88c5-51ac-ae15-8d31e0e01b78", "text": "Am LOCATION_b703fc6a war LOCATION_d1bfe8a1 nicht erreichbar."}` |
| **What should happen** | `case_id` unchanged · `"Adelbach"` → `PERSON_xxx` · `"Montag"` unchanged |
| **Bug** | UUID mutated · Adelbach tagged as LOCATION · Montag over-redacted |

---

## Case 4 — P1B-BP-009-V1 — Weekday over-redaction

**PASTE THIS:**
```
{"case_id": "78d3b632-07a8-5fa5-a113-2724712376bb", "text": "Am Montag war Adelbach, Lasse nicht erreichbar."}
```

| | |
|--|--|
| **What T4D saw upstream** | `"Am LOCATION_b703fc6a war LOCATION_d1bfe8a1, PERSON_8bc762c2."` |
| **What should happen** | `"Montag"` unchanged · `"Adelbach"` → `PERSON_xxx` · `"Lasse"` → `PERSON_xxx` |
| **Bug** | Montag → LOCATION · Adelbach wrong type |

---

## Case 5 — P1B-BP-096-V0 — JSON structure broken

**PASTE THIS:**
```
{"case_id": "eb1a786c-2cfe-5574-946c-da5561ed8ac0", "text": "Anna Weber arbeitet als Schichtleiterin im Team.", "items": [{"id": "24972596-9a26-513a-b652-5d274ad610cf", "label": "Terminvergabe", "value": 12}, {"id": "722c6b91-b87e-5ddd-be71-5e974d5c5f10", "label": "Rasenmäher Modell R40", "value": 0}], "status": "open"}
```

| | |
|--|--|
| **What T4D saw upstream** | `items[1]` had `label` key removed · `id` value corrupted · `"Anna"` leaked |
| **What should happen** | `"Anna Weber"` → `PERSON_xxx` · all keys/IDs/values unchanged |
| **Bug** | JSON structure corrupted — key deleted, ID value broken |

---

## Case 6 — P1B-BP-030-V6 — UUID mutated (email case)

**PASTE THIS:**
```
{"case_id": "e92689f3-f972-552c-897e-154ea940bca6", "text": "Erreichbar unter test.user247@example.invalid."}
```

| | |
|--|--|
| **What T4D saw upstream** | `{"case_id": "ID_06461de7-f972-552c-897e-154ea940bca6", "text": "Erreichbar unter EMAIL_ADDRESS_fa8e7430."}` |
| **What should happen** | email → `EMAIL_ADDRESS_xxx` ✅ · `case_id` unchanged |
| **Bug** | Email correctly pseudonymized BUT UUID still mutated |

---

## Case 7 — P1B-BP-061-V5 — Neutral document (control)

**PASTE THIS:**
```
{"case_id": "98ad7820-39fb-5408-9487-4d7d7e67841f", "text": "Bitte Kaffeemaschine Typ B prüfen.", "reference_id": "81f1de1f-a1d2-52ab-b4e2-4b8d25dcf202", "active": true, "score": 3}
```

| | |
|--|--|
| **What T4D saw upstream** | Identical to input — nothing changed |
| **What should happen** | Nothing changed ✅ |
| **Bug** | None — this is the passing control case |

---

## Log command to run after each case

```bash
docker logs garnet-privacy-proxy-1 --tail 25
```

Look for lines with `[OUT]`, `[PSEUDO]`, `→`, or the pseudonymized text. Compare to the "What T4D saw upstream" column above.
