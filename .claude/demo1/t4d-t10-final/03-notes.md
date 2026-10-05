# Notes on Scope, Guarantees, and Known Limits

Date: 2026-08-19

---

## What was changed

- **JSON structure integrity** — non-string JSON values (keys, UUIDs, numbers, booleans, enums) pass through byte-identical; only string values are analyzed for PII.
- **UUID protection** — UUID fragments are no longer mislabelled as entities, including when line-wrapped by the client.
- **German PERSON detection** — improved; PERSON is no longer overridden by LOCATION on the same span.
- **Weekday over-redaction** — German weekday names (Montag–Sonntag) are no longer treated as entities.
- **Structured Outputs** — OpenAI Strict Structured Outputs (`response_format` / JSON schema) work correctly on streaming responses; multi-token JSON is reassembled without truncation.

---

## What we guarantee

- The `case_id`, `reference_id`, and any other UUID or non-annotated JSON value passes through unchanged.
- The JSON structure (keys, nesting, numbers, booleans) is not modified.
- Detected PII (names, organizations, emails, phone numbers, IBAN, IDs) is replaced with a token before the request reaches the LLM provider, and restored in the response.
- The proxy records the exact pseudonymized payload forwarded to the provider (available for verification per `04-verification.md`).
- Rollback to the pre-fix image restores prior behavior in under five minutes with no data loss.

---

## Known limits

- **Over-redaction** — the NER pipeline errs on the side of protecting more rather than less. Some non-PII tokens (e.g. common German verbs, product terms) may occasionally be replaced with a `PERSON_*` or `ORGANIZATION_*` token. This does not leak data, but T4D may observe extra pseudonymization on some inputs.
- **Context-dependent labels** — for a small number of German surnames that also match place-name patterns (e.g. "Adelbach"), the entity may be labelled `LOCATION_*` instead of `PERSON_*` in some sentences. The value is still protected; only the label class differs.
- **Detection is not deterministic across model releases** — a future model upgrade may shift the exact set of tokens produced. The version pinned in the delivered image is the reference.
