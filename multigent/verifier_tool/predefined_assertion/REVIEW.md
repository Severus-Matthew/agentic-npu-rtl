# Predefined assertion review

2026-09-14: `my_v` only. `current_v` and saved experiment TBs are unchanged.

```text
Verifier generates reference + stimulus/golden + operation connections
  -> code appends visible protocol assertions, catalog-operation assertions,
     and one snapshot monitor to saved TB
  -> deterministic schema/AST/contract validation
  -> Verifier LLM reviews coverage, assertions, and stimulus-to-feature intent
       APPROVED -> Verilator/cocotb simulation -> existing coverage closure
       VERIFIER_REPAIR_REQUIRED -> counted Verifier repair -> validation -> review
       ARCHITECTURE_CONFLICT -> existing Architect revision path
```

## Scope and ownership

- Review includes frozen external contracts, the selected operation taxonomy,
  deterministic interface coverage plan, operation predicates/bins, independent
  reference checkers, the actual candidate TB source, its declared
  `STIMULUS_COVERAGE_INTENTS`, the visible code-generated protocol block, and an AST view of
  generated assertions (expressions, lexical guards, guarded variable origins,
  augmented counter assignment operators, relevant collection mutations such as
  append/pop/clear/update, observation awaits, return boundaries). Class/helper
  state updates and empty initial containers remain visible. A feature/class being in the pool does not exempt
  its assertions or coverage definitions from review.
- Review statically checks whether each declared stimulus construction plausibly
  targets every required feature. It excludes prior-run stimulus ledgers,
  simulation logs, bin hit counts, RTL source and RTL Generator output. It does
  not claim an antecedent actually occurred; simulation and coverage closure still
  decide actual activation and hits.
- The AST view is not a whole executable TB. Redacted origins and invocation
  schedules are not review defects. Self-review is an LLM heuristic, not proof of
  completeness, and can still miss a bug or raise a false concern.
  The state-update view is a syntactic dependency projection, not a general Python
  dataflow proof. RNG/task expressions, concrete vector arguments, iteration
  schedules and DUT signal writes are redacted/excluded; it does not ask the
  reviewer to optimize stimulus or judge actual activation.
- Interface bins and ready/valid stall assertions are code-owned and embedded in
  the saved TB. Selected catalog operation features also receive the code-owned
  `_contract_record_checked_stimulus` assertion wrapper. The Verifier supplies the
  independent expected result and complete actually observed transaction evidence;
  code compares them before recording the stimulus. Only a feature absent from the
  taxonomy receives an LLM-generated custom assertion.
- The generated TB captures every contract-declared top-level signal once per
  sampling event into one immutable snapshot. Protocol assertions and all
  cocotb-coverage sampling consume that same object; there is no second DUT
  observer. Supported operation points select observation templates via
  literal `OPERATION_SAMPLING_BINDINGS`. Every other operation point requires a
  generated custom observer on the same monitor/backend. Review sees effective bins,
  signal fields/slices, events/guards, type decoding and template implementation.
  It checks semantic connections and full custom observer/helper bodies, not actual
  activation. New-feature predicates and custom observation logic remain generated.
  Details: `OPERATION_SAMPLING.md`.

## Strengthened GEMM properties

- `accepted_operand_accounting`: count real accepted transfers, not producer loops.
- `contract_phase_consumption`: reject wrong-phase or excess consumption only when
  the external contract defines phase restrictions; allow promised interleaving.
- `exact_result_accounting` and `no_unsolicited_stream_output`: keep the output
  checker active across final beat, completion, idle and the next job. Do not stop
  checking immediately at M*N. Respect reset/abort and MMIO retention semantics.
- `stall_stability`: clarify that the fixed check includes the release handshake.
- Generator and review instructions reject always-True fallback assertions such
  as a missing snapshot key silently selecting `else True`.

## Loop, artifacts and cost

- Review is a separate read-only graph node. It cannot edit TB, golden, contract
  or RTL; findings are returned to the existing Verifier repair node.
- Corrections use the existing `max_verifier_revisions` budget. It is not increased.
  Each new valid generated/repaired TB receives one review API call; approval is
  reused across RTL-only repairs when definitions are unchanged. Generation and
  review use the same configured model/API. Review emits findings, not full source.
- Repairs preserve valid stimulus. They may change it only for a concrete missing
  or invalid stimulus-to-feature finding, or when checker wiring requires a small
  integration change. Additional bins/points inside an existing class are
  allowed; new operation concepts use the existing `llm_extension` mechanism.
- A genuine missing/contradictory external expected behavior is a structured
  Architect question. Missing checks, field names, absent stimulus and unpromised
  exact timing are not Architect defects.
- Review results are versioned in the run's `verification/verifier-review-av*-r*-v*.json`;
  API traces are in `logs/agent_traces/verifier-review-*.json`. Existing immutable
  attempt snapshots preserve the candidate and findings before correction.
- Approval is bound to architecture/TB/reference hashes, operation coverage
  definitions, taxonomy YAML and runtime/backend code. `APPROVED` is not simulation
  PASS. A changed definition cannot reuse old approval.
- Saved unreviewed TB checkpoints go to review before simulation. Old experiment
  results are not retroactively relabeled or regenerated.

## Verification

Offline tests cover scope exclusion, real assertion/guard extraction, vacuous
fallback visibility, read-only ownership, approval invalidation, review-repair-review
graph execution, existing budget exhaustion and forwarding an Architect question.
The original implementation was checked offline. A subsequent Sol pilot is saved
under `comparison_runs/my_v/self_review_validation`: official review remained
unapproved before simulation, while a separate diagnostic replay passed assertions
but missed one coverage bin. It is not a production PASS.

2026-09-14 follow-up: checker-state projection includes accepted A/B append guards
in the actual saved GEMM TB. Six new tests cover append/counter provenance,
cross-method helper state, subscript/delete/pop, empty initialization, RNG/vector
redaction and review-envelope integration. Full regression: 248 PASS. No paid API
rerun was made for this projection change; simulation/TB/RTL sources are unchanged.

## Stimulus guidance boundary

Verifier generation receives frozen semantics, the deterministic interface plan,
operation taxonomy starter-bin guidance/property checklists and fixed verification
policy. It generates concrete matrix values, dimensions, gaps, ready scheduling,
directed witnesses and seeded random transactions itself. The policy minimum is
100 randomized transactions. Interface bins specify actual signal situations;
operation starter-bin labels are examples and must be adapted to legal/reachable
contract behavior, not copied indiscriminately. For runtime-bound operation points,
code generates effective bins and reads actual fields; Verifier selects static
connections from the frozen contract. New-feature predicates and custom observer
implementations remain Verifier-owned but receive runtime-read DUT snapshots.

Each required bin needs intentional stimulus. The final TB declares a literal
label-to-obligation mapping, and pre-simulation review checks that mapping against
the actual source. The one TB snapshot feeds interface and operation coverage;
missing-bin
definitions use the effective plan and summary feedback guides counted stimulus
correction. No taxonomy function supplies a prebuilt exhaustive stimulus vector
list. LLM generation can still fail to activate a bin, select a semantically wrong
static source, or write custom observation logic with an incorrect return/qualification
or a planned driver-global dependency. Definition review and real simulation
evidence remain separate. sample_operation values cannot hit any point.
