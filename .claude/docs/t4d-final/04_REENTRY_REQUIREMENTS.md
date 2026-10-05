# Requested engineering response and reentry contract

## Original T+5 and T+10 material reviewed

T4D reviewed all six T+5 files and all four T+10 files. The documented old-build root cause,
rollback baseline, internal `/v1/responses` routing approach, strict structured-output
client contract and pre-provider log-inspection procedure are acknowledged. The questions
below concern the new B1 result, the missing corrected-build identity and production logging.

## Focused questions for this new B1 result

1. Please confirm that `Anna PERSON_a7842989-Öztürk` is a defect outside the known limits
   documented in T+10 `03-notes.md`: unlike the stated over-redaction and label ambiguity,
   two identifying components remained unprotected.
2. What specific stage produced this result: tokenization, NER span selection,
   normalization, confidence thresholding, span fusion or marker application?
3. What general remediation will ensure that no identifying component of multi-part,
   Unicode and hyphenated person names remains visible?
4. Can `Anna Müller-Öztürk` be added as a permanent vendor regression case, using the
   pre-provider verification procedure described in T+10 `04-verification.md`?
5. Can you confirm that the correction applies to the streaming and structured-output
   paths described in the T+10 delivery and does not regress strict structured output,
   JSON structure, preservation fields or exact rehydration?
6. T+5 promised the corrected build's immutable digest and commit SHA at T+10, and the T+10
   covering email says `01-delivery.md` contains a Build-ID and Git tag. The supplied file
   contains only the image tag and endpoint. Please provide the promised immutable identity
   for the corrected build.
7. For one strict structured-output regression request, please include the request-bound
   `[→ LLM]` evidence showing that the client-facing `/api/chat/completions` call was routed
   internally to the documented OpenAI `/v1/responses` endpoint, with `reasoning.effort`
   and `store:false` preserved.
8. Please clarify whether raw `[IN USER]` logging is always enabled or only a diagnostic
   option. For a production candidate, provide the configuration and verification method
   that disables raw prompt logging, including orchestration-log-sink retention behavior.

## Required delivery for a TMS retest

- Root-cause explanation.
- New corrected build identified using the same Build-ID, Git-tag, image and endpoint
  fields as T+10 `01-delivery.md`, plus an immutable image digest where available.
- Tokenizer, NER and relevant model versions for the corrected build, or an explicit
  statement that they are unchanged from the T+10 delivery.
- Vendor regression result for the exact B1 input.
- Pre-upstream evidence using the already documented Enclaive verification procedure that
  no name component remains visible.
- Confirmation that structured output and exact rehydration still pass.
- Production logging configuration showing that raw input logging can be disabled; the
  witnessed retest itself may use synthetic `[IN USER]` capture as already proposed.

Threshold tuning against only this disclosed example is not sufficient. The response
should explain the general fix for multi-part, Unicode and hyphenated person names.

## Two-stage retest

### Gate 1

Run only the exact B1 case. Any raw name component results in an immediate NO-GO for that
build. No tuning or retry occurs during the gate.

### Gate 2 — only after Gate 1 passes

Run the existing frozen 10-case TMS corpus with unchanged annotations and evaluator.
Required outcome:

- zero full PERSON leaks;
- zero partial PERSON leaks;
- zero residual or unknown markers;
- exact structure and value-type preservation;
- exact rehydration;
- no retries or tuning during the run.

Even a complete pass is initially a development-candidate result, not a production
approval.

## Requested timing

Please provide an engineering response and, if feasible, an immutable corrected build by
**Friday, 11 September 2026**. If the corrected build cannot be delivered by then, please
provide the root cause, responsible engineering contact and a binding target date by that
date.
