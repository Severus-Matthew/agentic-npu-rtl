# Verifier buggy attempts

Only compact, reviewed failures belong here. Raw model output stays ignored.
Each row records the requested domain, the model's concrete mistake, and the
deterministic gate that prevented a false pass. Repeated defects should reuse
the same failure category so paper analysis can aggregate them.

| Attempt | Domain | Failure category | Concise failure | Deterministic disposition |
|---|---|---|---|---|
| `api-eval-2026-09-29-mixed-001` | operation | `unreachable_coverage_bin` | Generated a `negative` bin for `3*ReLU(x)+1`, although the expression is always at least 1. | Rejected because every formula bin must produce a legal solver witness before TB acceptance. |
| `api-eval-2026-09-29-mixed-001` | lifecycle | `unreachable_implementation_claim` | Claimed `busy_watchdog_observation` was an `existing_primitive`, but no callable implementation or runtime dispatch entry existed. | Rejected because residual assertion/coverage branches must be reachable `verifier_python`, and stimulus must be reachable `verifier_python` or `protocol_driver`. |

## `api-eval-2026-09-29-mixed-001`

- Frozen request: solver-compiled `triple_plus_one(value) = value * 3 + 1`
  after ReLU, plus additive `lifecycle.busy_watchdog_observation` at 12 busy
  cycles.
- What was correct: the formula remained in the tool-owned DAG; the Verifier
  did not create an operation extension bundle; exactly one lifecycle bundle
  was returned.
- What was wrong: one formula bin was mathematically unreachable, and all three
  lifecycle implementation branches merely named supposed existing helpers
  without providing reachable code.
- Why the initial response looked valid: formula-bin solving was previously
  deferred until campaign stimulus generation, and the old extension schema
  allowed unregistered `existing_primitive` names.
- Permanent gates added: pre-TB solver witness validation for every formula bin;
  no inert `existing_primitive` implementation claims for residual branches.
- Revalidation: the saved response is rejected with the exact unreachable bin
  and all three invalid implementation kinds identified.
