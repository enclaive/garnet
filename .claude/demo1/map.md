# T4D Demo-1 Remediation Map

> **Owner:** Ahmed (technical) · Sebastian (external comms)
> **Vendor:** T4D · **Package date:** 2026-08-05 · **Observed route date:** 2026-08-04
> **Status:** BLOCKING — current config NOT releasable for TMS integration
> **Source of truth:** `.claude/demo1/vendor_defect_cases.jsonl`, `vendor_questions.md`, `README`, `package_manifest.json`

---

## 1. Goal

Get Garnet through a T4D 10-case canary retest at **10/10 pass** so the 100-case pilot can be scheduled. To do this we must:

1. **Reproduce** all 7 defect cases against a known-frozen Garnet build.
2. **Fix** three defect classes: (a) German PERSON leaks, (b) non-annotated JSON mutation (UUIDs, keys, structure), (c) over-redaction on weekday/place lookalikes.
3. **Answer** all 6 vendor questions with evidence.
4. **Deliver** a frozen versioned config (Garnet + NER + policy + model IDs) with rollback plan.
5. **Meet** the 2 / 5 / 10 working-day deadlines.

---

## 2. Timeline (T = 2026-08-05, working days only)

| Deadline | Working days | Absolute date | Deliverable |
|----------|--------------|---------------|-------------|
| T+2 | Fri 2026-08-07 | acknowledgement + technical owner + ticket reference |
| T+5 | Wed 2026-08-12 | reproduction confirmation + root cause + active versions + Responses-API test plan |
| T+10 | Wed 2026-08-19 | testable fix OR frozen corrected config + delivery plan + rollback |
| T+10..N | after fix | 10-case canary (must be 10/10) → then 100-case pilot separately |

---

## 3. Defect Map — 7 cases → 3 root-cause classes

### Class A — German PERSON leaks (NER coverage)
Cases: **P1B-BP-002-V2 (Hendrik)**, **P1B-BP-005-V5 (Lasse ... Marchetti)**, **P1B-BP-001-V1 (Adelbach → LOCATION)**, **P1B-BP-009-V1 (Adelbach + weekday)**

Symptoms:
- Given name "Hendrik" forwarded verbatim → **full leak**
- "Lasse Farah Marchetti" → only middle+surname pseudonymized, "Lasse" stays clear → **partial leak**
- "Adelbach" (surname) tagged as `LOCATION_*` not `PERSON_*` → **wrong label** (still redacted, but wrong entity class + fails vendor's expected_action="protect as PERSON")

Suspect code:
- `backend/privacy_proxy/app/pseudonymizer.py` → `detect_entities()`, `build_analyzer()`, `filter_overlaps()`, `custom_recognizers.py`
- Presidio German model + custom recognizers config
- `filter_overlaps()` may be resolving PERSON vs LOCATION in the wrong direction when spans collide

### Class B — Non-annotated JSON mutation (structure integrity)
Cases: **P1B-BP-001-V1 (case_id → ID_<mutated>)**, **P1B-BP-030-V6 (case_id mutated on email case)**, **P1B-BP-096-V0 (label key dropped, product name split across id field)**

Symptoms:
- UUID `case_id` gets `ID_` prefix + tail rewritten → NER treats UUID as a token to pseudonymize
- `items[].label` key **removed entirely** from output → the pseudonymizer's replace-in-string logic is walking JSON as flat text, replacing the value substring and dropping the surrounding key structure
- `items[].id` value gets a `PERSON_` token spliced into it because product name "Rasenmäher" was misdetected as PERSON and the substitution crossed field boundaries

Suspect code:
- `backend/privacy_proxy/app/main.py:378` `proxy()` — how the request body is walked before/after pseudonymize
- `backend/privacy_proxy/app/pseudonymizer.py` → `pseudonymize()` — likely operates on serialized JSON text rather than field-by-field on JSON values only

**This is the highest-severity class.** It's not just a false positive — the wire contract is being broken. T4D's Q3 asks for a testable guarantee this cannot happen.

### Class C — Over-redaction on non-PII lookalikes
Cases: **P1B-BP-001-V1**, **P1B-BP-009-V1** (both: "Montag" → LOCATION)

Symptoms:
- German weekday "Montag" tagged as LOCATION
- Adelbach (person) tagged as LOCATION (also Class A, but same root)

Suspect code:
- `pseudonymizer.py::trim_org_results()`, `has_org_context()`, `strip_markdown()` — heuristic layers that decide what to keep
- Presidio LOCATION recognizer confidence threshold in German model

### ✅ Positive control — P1B-BP-061-V5 (Kaffeemaschine)
Neutral doc unchanged. Proves the pass path works when NER doesn't false-fire. **Keep this as regression check.**

---

## 4. Vendor questions → answer plan

| Q | Question | Answer source | Task |
|---|----------|---------------|------|
| Q1 | Can you reproduce the 7 cases? | Task 1 | Run repro harness on frozen build, produce diff report |
| Q2 | Garnet/NER/policy/model versions active on 2026-08-04? | Task 2 | Freeze commit SHA, image digest, Presidio version, spaCy model version, policy file hash |
| Q3 | Can you constrain processing to annotated JSON values only? | Task 5 (fix) + Task 8 (test proof) | Byte-identical guarantee test suite |
| Q4 | Root cause for German PERSON leaks + fix? | Task 3 (RCA) + Task 6 (fix) | Written RCA per defect class + patch |
| Q5 | Independent pre-provider capture / verifiable evidence for retest? | Task 9 | Enable network-capture tap between proxy and upstream (mitmproxy or tcpdump), hash + timestamp captures |
| Q6 | Immutable version ID for canary + timeline + rollback plan? | Task 10 | Signed image digest, git tag, rollback = redeploy prior image digest via ArgoCD |

---

## 5. Task breakdown

### Phase 1 — Ack & Freeze (by T+2, Fri 2026-08-07)

#### Task 1: Freeze the "active on 2026-08-04" build
**Files:** none (git + registry ops)
**Interfaces:** produces `FROZEN_BUILD_ID = <commit_sha>@<image_digest>`
- [ ] Identify commit deployed on cVM `65.108.38.50` on 2026-08-04 (SSH → `docker inspect garnet-proxy | jq '.Config.Labels'` or `git log --before=2026-08-05` on `demo1`)
- [ ] Record image digest from Harbor (`harbor.enclaive.cloud/garnetdemo/privacy-proxy@sha256:...`)
- [ ] Record Presidio + spaCy model versions from image (`pip show presidio-analyzer spacy` inside container)
- [ ] Record policy file hash (`sha256sum backend/privacy_proxy/app/policies/*.yml` or wherever policy lives)
- [ ] Write findings to `.claude/demo1/frozen_build.md`

#### Task 2: Draft T+2 acknowledgement to T4D
**Files:** `.claude/demo1/response_ack.md`
- [ ] Draft 3-paragraph acknowledgement: (a) confirm receipt + package hashes verified, (b) name Ahmed as technical owner + Seb as escalation, (c) internal ticket ref (create GitHub issue `enclaive/garnet#<N>` for tracking), (d) commit to T+5 and T+10 dates
- [ ] Get Seb approval before sending (external comm)

#### Task 3: Create GitHub tracking issue
**Files:** none
- [ ] `gh issue create --title "T4D demo-1 remediation" --body-file .claude/demo1/README --label bug,security,customer`
- [ ] Capture issue number → use as ticket ref in Task 2

---

### Phase 2 — Reproduce & Root Cause (by T+5, Wed 2026-08-12)

#### Task 4: Build local repro harness
**Files:**
- Create: `backend/privacy_proxy/tests/test_t4d_repro.py`
- Read: `backend/privacy_proxy/app/pseudonymizer.py`, `backend/privacy_proxy/app/main.py`
- Test data: `.claude/demo1/vendor_defect_cases.jsonl` (7 cases)

**Interfaces:** produces `repro_report.json` with per-case pass/fail + diff

- [ ] **Step 4.1** — Load 7 cases from JSONL, extract `input.text` + `input.case_id` (and nested items where present)
- [ ] **Step 4.2** — For each case, call the proxy pseudonymize path directly (import from `pseudonymizer`, no HTTP round-trip) — feed as JSON body when the case has nested structure
- [ ] **Step 4.3** — Compare actual output vs `proxy_reported_upstream` from the case: assert bug reproduces
- [ ] **Step 4.4** — Emit `.claude/demo1/repro_report.json` with `{case_id, reproduced: bool, diff, evidence}`
- [ ] **Step 4.5** — Commit: `test(demo1): add T4D 7-case reproduction harness`

**Expected outcome:** all 7 cases reproduce on `FROZEN_BUILD_ID`. If any don't reproduce, root-cause the delta (config drift? Presidio version change?) before proceeding.

#### Task 5: Root-cause analysis document
**Files:** `.claude/demo1/rca.md`
- [ ] **Step 5.1** — For Class A (PERSON leaks): trace `detect_entities()` on "Hendrik" — is it in spaCy German model's PER whitelist? Check score threshold. Document: is the miss due to (a) model not knowing the name, (b) score below threshold, (c) `trim_org_results()` filtering it out, (d) `filter_overlaps()` letting a lower-priority label win?
- [ ] **Step 5.2** — For Class B (JSON mutation): trace `proxy()` in `main.py:378` — is the request body being serialized to string, pseudonymized as text, then re-parsed? That would explain UUID mutation AND key dropping. Confirm by reading `main.py` lines 378–450 and following where `pseudonymize()` is called.
- [ ] **Step 5.3** — For Class C (over-redaction): trace "Montag" — which recognizer fires? Presidio LOCATION default? Custom recognizer? Document confidence score.
- [ ] **Step 5.4** — Write RCA doc with: symptom → suspect file:line → confirmed cause → proposed fix per class

#### Task 6: Capture versions & config for Q2
**Files:** `.claude/demo1/active_config.md`
- [ ] Record: Garnet commit SHA, Docker image digest, Presidio version, spaCy model + version, policy file(s) + SHA-256, environment variables affecting NER (score thresholds, disabled recognizers), log level
- [ ] Note explicitly: was `x-owu-auth` or any user-token routing active? (relevant to Q5)

#### Task 7: Send T+5 update to T4D
**Files:** `.claude/demo1/response_t5.md`
- [ ] Structure: (a) reproduction confirmed X/7 cases, (b) RCA summary per defect class, (c) active versions from Task 6, (d) plan for OpenAI Responses API test (see Q4 of client's list — `gpt-5` model ID + `reasoning.effort` + `store:false` + Strict Structured Outputs)
- [ ] Get Seb approval before sending

---

### Phase 3 — Fix (by T+10, Wed 2026-08-19)

#### Task 8: Fix Class B — Field-scoped pseudonymization
**Files:**
- Modify: `backend/privacy_proxy/app/main.py:378` (proxy body handling)
- Modify: `backend/privacy_proxy/app/pseudonymizer.py::pseudonymize()`
- Test: `backend/privacy_proxy/tests/test_json_integrity.py`

**Fix approach:** pseudonymize walks JSON tree, applies detect+substitute **only to string values at annotated paths** (per the incoming request's contract — for OWU chat flow that's `messages[].content`). All other fields (UUIDs, keys, numbers, booleans, arrays, nested objects) pass through byte-identical.

- [ ] **Step 8.1** — Write failing test: byte-identical roundtrip on `P1B-BP-096-V0` (nested JSON with `case_id`, `items[]`, `status`) with only `text` field pseudonymized
- [ ] **Step 8.2** — Write failing test: `case_id` UUID passes through unchanged in `P1B-BP-001-V1` and `P1B-BP-030-V6`
- [ ] **Step 8.3** — Implement JSON-tree walker in `pseudonymize()` that receives (body: dict, allowed_paths: list[str]) and only mutates string values at those paths
- [ ] **Step 8.4** — Update `proxy()` in `main.py` to call the tree-walker with OWU's known text-bearing paths (`messages[*].content`, `input`, `prompt` — enumerate exhaustively; add unit test per path)
- [ ] **Step 8.5** — Run all Task 4 repro cases → Class B cases should now pass
- [ ] **Step 8.6** — Commit: `fix(proxy): field-scoped pseudonymization preserves JSON structure`

#### Task 9: Fix Class A — German PERSON coverage
**Files:**
- Modify: `backend/privacy_proxy/app/pseudonymizer.py` (or `custom_recognizers.py`)
- Test: `backend/privacy_proxy/tests/test_german_person_ner.py`

**Fix approach:** depends on RCA (Task 5). Likely one of:
- Lower German PERSON score threshold if misses are score-based
- Add custom recognizer for common German given names ("Hendrik", "Lasse", "Adelbach" as surname)
- Fix `filter_overlaps()` if PERSON is losing to LOCATION on ambiguous spans
- Upgrade spaCy German model if underlying model is stale

- [ ] **Step 9.1** — Failing tests: `Hendrik`, `Lasse Farah Marchetti` (all 3 components), `Adelbach` (as surname, not location) all → PERSON pseudonymized
- [ ] **Step 9.2** — Apply chosen fix from RCA
- [ ] **Step 9.3** — Run Task 4 harness → Class A cases pass
- [ ] **Step 9.4** — Commit: `fix(ner): improve German PERSON coverage per T4D demo-1 findings`

#### Task 10: Fix Class C — Weekday/place lookalikes
**Files:**
- Modify: `backend/privacy_proxy/app/pseudonymizer.py::custom_recognizers.py` or add a stopword denylist
- Test: extend `test_german_person_ner.py`

**Fix approach:** add German weekday denylist to LOCATION recognizer (Montag, Dienstag, Mittwoch, Donnerstag, Freitag, Samstag, Sonntag) — reject any of these tokens even if the base model fires.

- [ ] **Step 10.1** — Failing test: "Am Montag" → "Montag" not tagged as any entity
- [ ] **Step 10.2** — Add denylist / recognizer override
- [ ] **Step 10.3** — Run Task 4 harness → Class C cases pass
- [ ] **Step 10.4** — Commit: `fix(ner): denylist weekdays from LOCATION recognizer`

#### Task 11: Disable plaintext logging (Q5)
**Files:**
- Read: `backend/privacy_proxy/app/logs.py`, all callers of `_p()` / `log_no_pii()`
- Modify: wherever a plaintext-first-200-chars log call exists

**Fix approach:** grep for the 200-char preview logs, guard behind `DEBUG_PLAINTEXT_LOG` env var (default OFF in prod image). Verify existing prod image has it OFF.

- [ ] **Step 11.1** — `grep -rn "200" backend/privacy_proxy/app/logs.py backend/privacy_proxy/app/main.py` to find all previews
- [ ] **Step 11.2** — Confirm guard exists / add guard
- [ ] **Step 11.3** — Document verification method (env var check + log-line pattern grep on running container)
- [ ] **Step 11.4** — Document existing-log handling (log rotation + retention policy — is this already handled by cVM's docker logging driver? If not, note as accepted risk in RCA)

---

### Phase 4 — Frozen retest config (by T+10)

#### Task 12: Build frozen release candidate
**Files:** none (build + tag)
- [ ] Build proxy image from HEAD after Tasks 8–11 commits
- [ ] Push to Harbor with immutable tag: `harbor.enclaive.cloud/garnetdemo/privacy-proxy:t4d-canary-1`
- [ ] Record image digest → this is the immutable version ID for T4D
- [ ] Sign with cosign
- [ ] Write `.claude/demo1/frozen_release.md`: image digest, git tag `v-t4d-canary-1`, Presidio version, spaCy model version, policy hash, exact env vars

#### Task 13: Enable independent pre-provider capture (Q5)
**Files:** cVM ops
- [ ] Add mitmproxy or tcpdump tap between garnet-proxy container and upstream (OpenAI/Anthropic/Groq) — capture request bodies pre-provider
- [ ] Hash + timestamp each capture; store in append-only location for retest
- [ ] Document tap location + verification method in `.claude/demo1/evidence_tap.md`
- [ ] **Note for Seb approval:** capture of request bodies is a privacy-sensitive op; may need explicit scope + retention rules

#### Task 14: Run internal 10-case dress rehearsal
**Files:** `.claude/demo1/canary_dryrun.json`
- [ ] Deploy `t4d-canary-1` image to a staging cVM (or local docker-compose)
- [ ] Run T4D's 7 defect cases + 3 additional synthetic cases (matching the 6 defect classes covered)
- [ ] Require 10/10 pass before T+10 send-off
- [ ] Emit report

#### Task 15: T+10 delivery to T4D
**Files:** `.claude/demo1/response_t10.md`
- [ ] Structure: (a) frozen version ID (image digest + git tag), (b) fix summary per defect class, (c) delivery timeline for canary run, (d) rollback plan (redeploy prior image digest via ArgoCD or docker-compose), (e) evidence tap enabled per Q5, (f) plaintext logging status per Q5
- [ ] Seb approval before send

---

### Phase 5 — Canary retest & pilot (post T+10)

#### Task 16: T4D 10-case canary retest
- [ ] T4D runs their canary against `t4d-canary-1` image
- [ ] Must be 10/10; anything less = back to Phase 3 with new RCA
- [ ] If 10/10 → schedule 100-case pilot separately (per T4D's process — pilot approval is separate ask)

#### Task 17: Rollback drill (once, before canary)
- [ ] Practice: `kubectl set image ...` or `docker compose up -d --image <prior_digest>` — confirm rollback restores prior behavior in < 5 min
- [ ] Document exact command in `frozen_release.md`

---

## 6. Answering Q4 (OpenAI Responses API)

Vendor asks:
- Can a versioned test config be provided using the `gpt-5` model ID used by TMS?
- Can it be shown the request actually went through Responses API not chat fallback?
- Are `reasoning.effort`, `store:false`, and Strict Structured Outputs supported?

**Investigation task (add if in scope):**
- [ ] Check `backend/privacy_proxy/app/main.py` for Responses API routing — is there a code path that forwards to `/v1/responses` vs `/v1/chat/completions`?
- [ ] Recent commit `dd9a4c29a fix(proxy): match RESPONSES_API_MODELS by prefix to support dated model variants` — this is directly relevant. Confirm which model IDs match, whether `gpt-5` matches, and whether the path enforces Responses API (or falls back to chat on error).
- [ ] Confirm `reasoning.effort`, `store:false`, Strict Structured Outputs are passed through un-mangled.
- [ ] Add evidence in `response_t5.md` — cite commit SHA + code path.

---

## 7. Open questions for Seb (raise before T+2)

1. Approve external comms plan (drafts sent for review before each of T+2, T+5, T+10).
2. Approve enabling network-capture tap on cVM (Q5) — privacy scope + retention.
3. Approve creating public GitHub issue for tracking, or keep internal only (T4D said "development finding" not incident).
4. Approve Ahmed as technical owner name for external attribution.

---

## 8. What could go wrong (accepted risks)

- **Frozen build reproduction fails** → config drift on cVM between 2026-08-04 and repro. Mitigation: get exact `docker inspect` output for that day; if drift is unrecoverable, note as caveat in T+5 response and proceed with best-effort repro from `demo1` HEAD as of 2026-08-04 commit.
- **NER upgrade breaks positive controls** → any change to German PERSON recognizer risks new false positives. Mitigation: keep P1B-BP-061-V5 as gate; add 5–10 more neutral controls before shipping.
- **JSON tree walker misses an OWU code path** → some request shape not in the whitelist gets forwarded without pseudonymization. Mitigation: default-fail if unknown top-level key contains a string > N chars; log for investigation.
- **T+10 slips** → notify T4D at T+7 with revised timeline, don't wait until T+10.

---

## 9. File layout after remediation

```
.claude/demo1/
├── README                    (T4D-provided, do not modify)
├── vendor_defect_cases.jsonl (T4D-provided, do not modify)
├── vendor_questions.md       (T4D-provided, do not modify)
├── package_manifest.json     (T4D-provided, do not modify)
├── map.md                    (this file)
├── frozen_build.md           (Task 1)
├── response_ack.md           (Task 2)
├── repro_report.json         (Task 4)
├── rca.md                    (Task 5)
├── active_config.md          (Task 6)
├── response_t5.md            (Task 7)
├── frozen_release.md         (Task 12)
├── evidence_tap.md           (Task 13)
├── canary_dryrun.json        (Task 14)
└── response_t10.md           (Task 15)

backend/privacy_proxy/tests/
├── test_t4d_repro.py         (Task 4)
├── test_json_integrity.py    (Task 8)
└── test_german_person_ner.py (Tasks 9, 10)
```

---

## 10. Execution order (critical path)

```
Task 1 (freeze build) ─┬─> Task 4 (repro) ─> Task 5 (RCA) ─┬─> Task 8 (fix Class B) ─┐
Task 2 (ack draft)  ───┤                    Task 6 (versions)  Task 9 (fix Class A) ──┤
Task 3 (issue)      ───┘                                       Task 10 (fix Class C) ─┼─> Task 12 (build) ─> Task 14 (dryrun) ─> Task 15 (deliver) ─> Task 16 (canary)
                                                               Task 11 (logging)   ───┤
                                                               Task 13 (tap)       ───┘
                        └─> Task 7 (T+5 update) ──────────────────────────────────────┘

Phase 1 by T+2 (Fri Aug 7) | Phase 2 by T+5 (Wed Aug 12) | Phase 3+4 by T+10 (Wed Aug 19)
```

---

## 11. Definition of done

- All 7 T4D defect cases pass in `test_t4d_repro.py`
- Byte-identical guarantee test passes for arbitrary nested JSON with only whitelisted string paths mutated
- Plaintext logging OFF in shipped image (verified)
- Frozen image digest + git tag + policy hash recorded and signed
- T4D 10-case canary passes 10/10
- Rollback drill executed successfully
- All 6 vendor questions answered in `response_t10.md` with evidence citations

---

*Last updated: 2026-08-05. Update the checkboxes as tasks complete; do not restructure without Seb approval.*
