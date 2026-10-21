# Verifier buggy attempts

Only compact, reviewed failures belong here. Raw model output stays ignored.
Each row records the requested domain, the model's concrete mistake, and the
deterministic gate that prevented a false pass. Repeated defects should reuse
the same failure category so paper analysis can aggregate them.

| Attempt | Domain | Failure category | Concise failure | Deterministic disposition |
|---|---|---|---|---|
| `api-eval-2026-09-29-mixed-001` | operation | `unreachable_coverage_bin` | Generated a `negative` bin for `3*ReLU(x)+1`, although the expression is always at least 1. | Rejected because every formula bin must produce a legal solver witness before TB acceptance. |
| `api-eval-2026-09-29-mixed-001` | lifecycle | `unreachable_implementation_claim` | Claimed `busy_watchdog_observation` was an `existing_primitive`, but no callable implementation or runtime dispatch entry existed. | Rejected because residual assertion/coverage branches must be reachable `verifier_python`, and stimulus must be reachable `verifier_python` or `protocol_driver`. |
| `api-eval-2026-09-29-batch10-002` | operation | `unreachable_coverage_bin` | Proposed `below_min_clipped` for `clip(ReLU(x), -8, 8)` even though its input cannot be negative. | Solver witness generation proved the bin unreachable and rejected the candidate. |
| `api-eval-2026-09-29-batch10-004` | protocol | `invalid_generated_source_path` | Named `verification/feature_protocol_bounded_ready_recovery.py` and omitted executable stimulus file/symbol bindings. | Schema and entry-point reachability gates rejected the bundle. |
| `api-eval-2026-09-29-batch10-005` | protocol | `missing_generated_source_file` | Referenced `tests/test_payload_parity_extension.py` for all branches but did not emit that file. | Source-file reachability rejected all three branches. |
| `api-eval-2026-09-29-batch10-006` | protocol | `invalid_generated_source_path` | Put backpressure assertion, coverage, and stimulus under an ungenerated `verification/*.py` path. | Schema and source-file reachability rejected the bundle. |
| `api-eval-2026-09-29-batch10-007` | lifecycle | `invalid_generated_source_path` | Put minimum-busy-duration code under an ungenerated `verification/*.py` path. | Schema and source-file reachability rejected the bundle. |
| `api-eval-2026-09-29-batch10-008` | lifecycle | `missing_module_level_symbols` | Pointed at the main generated test but did not define any of the three named extension functions. | Module-scope symbol reachability rejected the bundle. |
| `api-eval-2026-09-29-batch10-009` | mixed | `missing_extension_entry_points` | Correctly kept `abs(value)` tool-owned, but emitted no reachable implementation for bounded READY recovery. | Schema and entry-point reachability rejected only the residual protocol extension. |
| `api-eval-2026-09-29-batch10-010` | mixed | `incomplete_reuse_manifest` | Omitted six deterministically preserved lifecycle feature IDs and named functions that were not emitted. | Exact resolved-reuse and entry-point reachability gates rejected the bundle. |
| `api-eval-2026-09-29-retry10-004` | protocol | `repair_patch_churn` | Ten attempts alternated among missing symbols, unreachable symbols, protected generated-block edits, no-op patches, and duplicate coverage metadata. | Every draft was rejected; no malformed bounded-ready-recovery TB received credit. |
| `api-eval-2026-09-29-retry10-005` | protocol | `repair_patch_churn` | Defined payload-parity functions but never installed a legal runtime call path, then repeatedly targeted a protected generated block. | Entry-point and protected-block gates rejected all ten attempts. |
| `api-eval-2026-09-29-retry10-006` | protocol | `repair_patch_churn` | Never returned a valid `PATCH_READY` local correction for backpressure-duty assertion, coverage, and stimulus. | Local-patch validation rejected all ten attempts. |
| `api-eval-2026-09-29-retry10-007` | lifecycle | `incomplete_runtime_extension` | Progressed from missing functions to no-op assertion, constant coverage, and missing sampling binding without closing all defects. | Semantic and sampling gates rejected all ten attempts. |
| `api-eval-2026-09-29-retry10-008` | lifecycle | `vacuous_runtime_evidence` | Passed `completion_seen=False`, ignored the checker return, discarded the coverage result, and used a wait-only stimulus. | Manual audit exposed the old false pass; runtime-evidence, result-consumption, and stimulus-effect gates now reject it. |
| `api-eval-2026-09-29-retry10-009` | mixed | `repair_patch_churn` | Preserved tool-owned `abs(value)` but never produced valid bounded-ready-recovery extension wiring. | Extension and local-patch gates rejected all ten attempts. |
| `api-eval-2026-09-29-retry10-010` | mixed | `fabricated_runtime_evidence` | Self-tested reset recovery with literal `release_cycle=10` and `accept_cycle=12` and a Timer-only stimulus instead of DUT evidence. | Manual audit exposed the old false pass; runtime-evidence and stimulus-effect gates now reject it. |
| `api-eval-2026-09-29-targeted-v6` | protocol | `missed_temporal_event` | Called only an undeclared two-cycle schedule, started the READY-recovery monitor after the stall ended, never launched work that could produce output VALID, and decorated the test through an alias imported later. | Manual audit rejected the old false pass; exact-scenario, monitor-overlap, output-activation, and decorator-definition-order gates now reject it. |
| `api-eval-2026-09-30-targeted-v13` | protocol | `data_instead_of_entry_points` | Assigned strings/dicts to the three declared implementation symbol names, then observed bounded recovery only after the campaign had already completed. | Callable-entry-point validation rejected all three symbols; diagnostics now explicitly require `def`/`async def`, and the frozen scenario now describes the concurrently driven command/A-channel sequence. |

## Batch `batch_2026_09_29_retry10`

- Scope: the same 10 scenarios, each allowed up to 10 counted Verifier calls.
- API usage: 68 calls. Three operation cases passed; symmetric clip required one
  solver-directed repair. Five scenarios exhausted all 10 calls.
- Old automated verdict: 5 PASS / 5 REJECTED.
- Manual TB audit: the two extension-bearing automated PASS results were invalid.
  One used a vacuous completion condition and ignored its checker result; the
  other used fabricated cycle constants. The reviewed result is therefore
  **3 PASS / 7 REJECTED**.
- Permanent response: generated extension validation now requires simulator-derived
  evidence, enforced assertion returns, consumed coverage samples, and stimulus
  that drives the DUT or delegates to a real driver. Revalidating the saved files
  accepts the three tool-owned formula cases and rejects both false passes.
- Safety: no invalid extension TB received final reviewed credit, and raw API
  artifacts remain ignored.

## Batch `batch_2026_09_29_10`

- Scope: 10 first-attempt Verifier-only calls over one frozen GEMM contract with
  its existing protocol, lifecycle, operation, and golden campaign preserved.
- Mix: three operation formulas, three protocol extensions, two lifecycle
  extensions, and two formula-plus-extension cases.
- Reviewed outcome: 2 PASS and 8 deterministic rejections.
- Operation success: `abs(value)` and sign-dependent gain reused the existing
  campaign, introduced no extension bundle, and produced only solver-witnessed
  bins. The symmetric-clip attempt was correctly rejected for an unreachable
  lower-saturation bin under its upstream ReLU.
- Residual-extension result: none of the seven protocol/lifecycle-bearing
  attempts emitted three reachable assertion/coverage/stimulus entry points.
  One also omitted six exact preserved lifecycle feature IDs.
- Safety result: no malformed response was accepted, no built-in sibling was
  silently replaced, and no raw model artifact is committed.
- Prompt/schema response: implementation paths are now structurally restricted
  to emitted one-level `tests/*.py` or `reference/*.py` files, and authoring
  instructions explicitly require module-level reachability and exact reuse-list
  copying. These changes have local regression coverage but were not re-tested
  with additional API calls in this batch.

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
