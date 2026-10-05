# Enclaive Garnet — Technical Reentry Package

Prepared for Tim Lüders / Enclaive on 2026-09-02.

This package is T4D's focused follow-up to Enclaive's T+10 delivery. It documents one
reproducible defect observed while evaluating the delivered Garnet privacy-proxy build
recorded by the T4D harness as
`harbor.enclaive.cloud/garnetdemo/privacy-proxy:04f1c2ee9`.

T4D reviewed the complete original T+5 and T+10 deliveries:

- T+5: `01-reproduction.md` through `06-remediation-answers.md`; source ZIP SHA-256
  `dd58f317760609535880af23f8e9c4e8fc352641836251924cab40d885468214`.
- T+10: `01-delivery.md` through `04-verification.md`; source ZIP SHA-256
  `1548051398a4bd24a990094635b7af1bcc84074ec27a768a6bea2276df9cb6d0`.

All names, email addresses, identifiers and content in this package are synthetic.
The package contains no customer data, production data, credentials, authorization
headers, API keys or secret hashes.

## Finding in one sentence

According to the proxy's sealed `pseudonymized_prompt` self-report, the synthetic
person name `Anna Müller-Öztürk` was only partially protected before the upstream LLM:
`Müller` was replaced, while `Anna` and `Öztürk` remained visible.

## Files

- `01_DEFECT_REPORT.md` — observed behavior, scope and evidence classification.
- `02_SYNTHETIC_B1_INPUT.json` — exact synthetic input used for the test.
- `03_OFFLINE_EVALUATION.json` — deterministic offline evaluation of the capture.
- `04_REENTRY_REQUIREMENTS.md` — requested engineering response and retest contract.
- `B1-response.json` — original sealed SSE response capture, including the proxy
  self-report. This file is synthetic but should still be handled as confidential
  technical test evidence.
- `SHA256SUMS.txt` — hashes for all files in the package except the checksum file and
  the ZIP container itself.

## Important limits

- This is a finding about one synthetic case and one identified build.
- It is not a general security or quality rating of Garnet or Enclaive.
- Evidence about pre-upstream visibility is classified as `proxy_self_report`.
  No independent network-level capture between the proxy and upstream LLM is claimed.
- The client-facing structured output and rehydration passed for this case. The defect
  concerns partial protection on the outbound path.
- Enclaive's documented `/v1/responses` routing approach, strict structured-output client
  contract, rollback baseline and pre-provider evidence procedure are acknowledged.
- Three focused points remain: the B1 partial PERSON exposure; the promised immutable
  digest/commit for the corrected T+10 build is absent from the T+10 files; and the
  production control for raw `[IN USER]` logging remains unclear.
