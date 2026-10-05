# Partial PERSON exposure in Garnet privacy proxy

## Delivery and tested build

| Field | Value |
|---|---|
| Image tag | `harbor.enclaive.cloud/garnetdemo/privacy-proxy:04f1c2ee9` |
| Endpoint | `/api/chat/completions` |
| Transport | `text/event-stream` (SSE) |
| Delivery context | Enclaive T+10 delivery (`01-delivery.md` through `04-verification.md`) |
| Separate Build-ID | Not present in the four T+10 files |
| Git tag/commit | Not present in the four T+10 files |
| Image digest | Not present in the four T+10 files |
| Tokenizer/NER/model versions | Not present in the four T+10 files |

The T4D harness and T+10 `01-delivery.md` agree on the image tag. Contrary to the covering
email's description, the supplied `01-delivery.md` contains only the image tag and endpoint,
not a separate Build-ID or Git tag. A mutable tag is therefore the only build binding in the
files available to T4D.

T+5 `06-remediation-answers.md` explicitly promised that the corrected build's immutable
image digest and commit SHA would be supplied at T+10. The older rollback baseline is fully
identified (`dd9a4c29a`, digest
`sha256:33bbd35ccc8496b5d8526311a77b8b876d0c33b004a6d28eb33d3f0ebe5e6e3d`);
the missing identity concerns the new corrected build, not the rollback build.

## Exact synthetic case

Input:

```json
{
  "name": "Anna Müller-Öztürk",
  "email": "a.mueller@example.de",
  "reference_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "score": 7,
  "active": true,
  "note": null,
  "nested": { "city": "München" }
}
```

The proxy's own `pseudonymized_prompt` reported this outbound representation:

```json
{
  "name": "Anna PERSON_a7842989-Öztürk",
  "email": "EMAIL_ADDRESS_ecdd41ef",
  "reference_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
  "score": 7,
  "active": true,
  "note": null,
  "nested": { "city": "München" }
}
```

## Evaluation

| Observation | Result |
|---|---|
| `Müller` replaced with a PERSON marker | Pass for this component |
| `Anna` remained visible | Fail — partial PERSON exposure |
| `Öztürk` remained visible | Fail — partial PERSON exposure |
| Email fully replaced | Pass |
| UUID preserved | Pass |
| Client-facing JSON structure and types | Pass |
| Exact client-facing rehydration | Pass |
| Residual/unknown markers in final output | None |

## Evidence classification

The pre-upstream finding is **provider-visible according to the sealed proxy
self-report**. The evidence source is the `pseudonymized_prompt` field emitted by the
proxy. We do not claim an independent wire capture between the proxy and the upstream
LLM.

The outbound defect and the successful return path must be evaluated separately: exact
rehydration does not compensate for raw identifying name components being exposed on the
outbound path.

## Relation to the T+10 guarantees and known limits

T+10 `03-notes.md` guarantees that the `[OUT USER]` log contains the exact provider-bound
payload "with no raw PII present". The sealed B1 self-report contains the raw components
`Anna` and `Öztürk`, so this case contradicts that guarantee.

The documented known limits cover over-redaction and PERSON/LOCATION label ambiguity where
the value remains protected. B1 is different: two components remained unprotected. It is
therefore not described by the stated known limits. T+5 identified earlier PERSON failures
as short-name context sensitivity and overlap-priority defects, with a planned switch to
`de_core_news_lg`. B1 shows that the corrected configuration still does not fully protect
this multi-part hyphenated surface.

T+5 `04-responses-api.md` documents internal routing to OpenAI `/v1/responses`, including a
stream adapter, and reports live verification for `reasoning.effort`. T+10
`02-structured-outputs.md` demonstrates the client-facing `/api/chat/completions` contract
with strict `response_format`. For the retest, the remaining requirement is not another
general API explanation but request-bound evidence that this strict-output call was
actually forwarded on the documented internal `/v1/responses` route.

## Raw input logging remains an independent production question

T+5 `05-evidence.md` and T+10 `04-verification.md` state that every request emits or records
the raw `[IN USER]` content before pseudonymization. Stdout may be ephemeral at the
application level, but it can be retained by an orchestration log sink. This is useful for
a witnessed synthetic retest, but it does not answer T4D's original production requirement
to disable raw PII logging. The retest can proceed with synthetic data; production use
requires a documented disablement or tightly controlled diagnostic mode.

## Current TMS decision

This identified build remains a NO-GO for the TMS pilot. This is a build- and case-specific
decision, not a general claim about Garnet or Enclaive.

Enclaive offered to run the frozen ten-case Canary. T4D uses a two-stage gate: this exact
B1 case must pass first. Because B1 is currently red, the ten-case run has deliberately not
been started and no additional vendor request budget was consumed.
