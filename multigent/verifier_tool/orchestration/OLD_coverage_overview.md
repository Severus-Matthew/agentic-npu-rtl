# Coverage

> **Historical snapshot.** This document describes the pre-domain-first
> directory layout. Its relative paths and package-ownership wording are not
> current integration guidance. Use [`README.md`](README.md) and the
> `protocol/`, `operation/`, and `lifecycle/` domain READMEs instead.

This is the **coverage** implementation of `verifier_tool`'s three-domain
taxonomy (`protocol`, `lifecycle`, `operation` — see
[`../README.md`](../README.md) for the full architecture narrative). Coverage
is one of three independent sibling consumers of each domain's resolved
Feature Plan (the others are `../assertion/` and `../stimulus/`); it does not
call into and is not called by either of them at the plan-building level. What
it owns: turning a frozen contract into a concrete set of coverage
**obligations** (functional-coverage bins with machine-readable applicability),
materializing those obligations as real `cocotb_coverage` objects, sampling
every declared signal on every clock edge during simulation, and writing the
durable JSON report and stimulus ledger that `../feedback_to_debugger/` later
reads.

```text
coverage/
├── __init__.py            re-exports plan.py-level names from all three domains + runtime.py + NOT history.py
├── cocotb_model.py         obligation -> cocotb_coverage CoverPoint/CoverCross objects
├── runtime.py              InterfaceCoverageTracker: per-test sampling, reports, stimulus ledger
├── history.py              durable cross-run stimulus ledger merge (independent of any one test run)
├── protocol/               see protocol/README.md — channel/handshake/AXI coverage
├── lifecycle/              see lifecycle/README.md — reset/command/job/busy/completion/error coverage
└── operation/              see operation/README.md — arithmetic/data coverage + DUT sampling wiring
```

Read [`protocol/README.md`](../protocol/README.md), [`lifecycle/README.md`](../lifecycle/README.md),
and [`operation/README.md`](../operation/README.md) for the three domain-specific
plan builders. This file documents the three domain-agnostic files
(`cocotb_model.py`, `runtime.py`, `history.py`) that consume whatever those
three builders produce, plus the shared obligation shape and runtime data flow
that ties everything together.

## Shared obligation-record shape

Every domain's `build_*_coverage_plan()` returns a dict with an `obligations`
list. Every obligation (regardless of which of the three `plan.py` files built
it) has at minimum:

```python
{
    "id": str,              # e.g. "channel.cmd.handshake_states", "operation.gemm.dimensions"
    "template": str,        # selects a builder in cocotb_model.py and/or a sampler below
    "scope": str,            # "signal" | "channel" | "operation" | "protocol_group" | "protocol_field" | ...
    "scope_name": str,
    "description": str,
    "bindings": {...},      # template-specific: signal names, channel roles, concept, sampling config, ...
    "bins": [
        {
            "name": str,
            "intent": str,                 # prose only, never machine-read
            "required": bool,               # default True
            "applicability": {"status": ..., "basis": ...},  # e.g. required_reachable, proven_unreachable, inapplicable
            "minimum_hits": int,            # default 1
            # template-specific machine-readable bin selector, one of:
            "values": {"valid": 0|1, "ready": 0|1},   # handshake_states
            "event": str,                               # handshake_arrival_order
            "range": [int, int | None],                 # stall_stability
            "predicate": {"op": str, "args": [...]},    # operation_coverpoint
        },
        ...
    ],
}
```

A top-level plan dict produced by `merge_coverage_plans()`
(`operation/plan.py`) additionally carries `interface_contract`,
`standard_protocol_plan`, `operation_metadata`, `monitor` (`clock`, `reset`,
`signals`), `verification_manifest` / `verification_manifest_hash`, and
`requirements` (currently just `randomized_transactions_minimum`, attached by
the orchestration caller, not by `merge_coverage_plans` itself). This is
exactly the dict `InterfaceCoverageTracker` is constructed with — see
"Runtime data flow" below.

## Obligation templates: instantiated vs. sampled

Directory layout suggests each domain's `plan.py` instantiates its own
templates and its own `runtime.py` samples them. That is true for `operation/`
and mostly true for `protocol/`, but **five lifecycle-owned templates are
physically instantiated by `protocol/plan.py`**, because
`protocol/plan.py:load_interface_coverage_templates()` merges lifecycle's
signal/channel templates into its own generic matching loop. Sampling
responsibility is split further still. This table is the authoritative map;
the three subfolder READMEs link back here instead of repeating it in full.

| template | scope | YAML source | instantiated by | sampled by |
| --- | --- | --- | --- | --- |
| `handshake_states` | channel | `protocol_features.yaml` | `protocol/plan.py` | `InterfaceCoverageTracker.sample_snapshot` → `cocotb_model.py:ContractCocotbCoverageModel.sample_handshake` |
| `handshake_arrival_order` | channel | `protocol_features.yaml` | `protocol/plan.py` | `protocol/runtime.py:ProtocolCoverageMonitor` |
| `stall_stability` | channel | `protocol_features.yaml` | `protocol/plan.py` | `InterfaceCoverageTracker.sample_snapshot` (reads the TB's own `completed_stalls`) → `cocotb_model.py:sample_stall_length` |
| `address_alignment` | signal | `protocol_features.yaml` | `protocol/plan.py` | `InterfaceCoverageTracker._sample_address` |
| `axi4_*` / `axi_lite_*` / `axis_*` (`standard_*` scopes) | standard channel/group/field | `protocol_features.yaml` | `protocol/plan.py:_append_standard_obligations` | `protocol/runtime.py:ProtocolCoverageMonitor` |
| `reset_behavior` | signal | `lifecycle_features.yaml` (`features`) | `protocol/plan.py` (merged-in template) | `InterfaceCoverageTracker._sample_reset` |
| `completion_behavior` | signal | `lifecycle_features.yaml` | `protocol/plan.py` (merged-in) | `InterfaceCoverageTracker._sample_completion` |
| `error_behavior` | signal | `lifecycle_features.yaml` | `protocol/plan.py` (merged-in) | `InterfaceCoverageTracker._sample_error` |
| `busy_behavior` | signal | `lifecycle_features.yaml` | `protocol/plan.py` (merged-in) | `lifecycle/runtime.py:LifecycleCoverageMonitor` |
| `command_legality` | channel | `lifecycle_features.yaml` | `protocol/plan.py` (merged-in) | `lifecycle/runtime.py:LifecycleCoverageMonitor` |
| `job_lifecycle`, `reset_abort_phase`, `post_reset_purity` | operation | `lifecycle_features.yaml` (`operation_coverage`) | `lifecycle/plan.py:build_lifecycle_coverage_plan` | `lifecycle/runtime.py:LifecycleCoverageMonitor` |
| `operation_coverpoint` | operation | `feature_plans/operation_features.yaml` families, or Verifier `llm_extension` | `operation/plan.py:build_operation_coverage_plan` | `operation/sampling.py:OperationSamplingMonitor` → `cocotb_model.py:sample_operation` |

Any obligation whose template is not in this table (there should be none in a
valid plan) falls back to `cocotb_model.py`'s generic
`_build_event_coverpoint`/string-label sampler.

## Runtime data flow

1. **Plan assembly** — an orchestration or agent caller builds
   `coverage_plan = merge_coverage_plans(build_interface_coverage_plan(interface),
   operation_plan_for_tests(...))` (see `operation/README.md`) and attaches
   `coverage_plan["requirements"]`. Real call sites:
   `multigent/orchestration/verification_tools_node.py:verification_tools_node`,
   `multigent/agents/verifier.py`, `multigent/scripts/build_taxonomy_release.py`.
2. **Handoff to the simulator process** — the caller passes `coverage_plan` to
   `multigent/tools/cocotb_runner.py:run_cocotb_regression(coverage_plan=...,
   coverage_report_path=..., stimulus_ledger_report_path=...)`, which writes the
   plan to a JSON file and sets three environment variables for the cocotb
   subprocess: `NPU_FUNCTIONAL_COVERAGE_CONFIG` (plan JSON path),
   `NPU_FUNCTIONAL_COVERAGE_REPORT` (report output path),
   `NPU_STIMULUS_LEDGER_REPORT` (ledger output path).
3. **Tracker construction** — inside the cocotb process, the generated
   testbench decorates every test with `@contract_coverage()`
   (`runtime.py`). The first call to `get_coverage_tracker()` reads those three
   env vars, loads the plan JSON, and constructs the process-wide singleton
   `InterfaceCoverageTracker(plan, report_path, ledger_path)`, registering
   `atexit.register(tracker.close)`.
4. **Per-test lifecycle** — `contract_coverage()`'s wrapper calls
   `tracker.begin_test(name)`, binds any custom operation observers declared in
   that test module, starts the generated `_contract_generated_monitor`
   background task, runs the test body, requires and calls the generated
   assertion finalizer, calls `tracker.end_test()`, then unconditionally writes
   the report in a `finally` block.
5. **Per-edge sampling** — the generated monitor task calls
   `capture_contract_snapshot(dut, CONTRACT_SIGNAL_NAMES)` every sampled edge
   and feeds the immutable `ContractSnapshot` to `sample_contract_snapshot(...)`
   (module-level wrapper → `tracker.sample_snapshot(...)`), or
   `observe_contract_reset_snapshot(...)` for a mid-half-cycle reset pulse.
   `sample_snapshot` fans out to `cocotb_model.py`, `protocol/runtime.py`,
   `lifecycle/runtime.py`, and `operation/sampling.py` per the table above.
6. **Checked jobs** — after a generated test's own oracle comparison succeeds,
   it calls a code-owned wrapper (never `record_stimulus`/`sample_operation`
   directly — `multigent/agents/verifier.py` statically forbids that) that
   ultimately calls `record_stimulus(...)` (cross-validates against the
   code-owned `ReadyValidCaptureAdapter` capture and
   `operation_metadata`'s golden re-evaluation, then appends to the stimulus
   ledger) and `sample_operation(...)` (links a checked job's already-classified
   evidence to its `operation_coverpoint` bins).
7. **Report + ledger on disk** — `tracker.write_report()` writes the JSON
   report (`report()`) plus a `cocotb_coverage.export_to_yaml(...)` sibling
   file; `tracker.write_stimulus_ledger()` writes
   `stimulus-ledger-<tag>.json`, flushed after every `record_stimulus`/
   `sample_operation` call so a mid-run timeout does not lose evidence.
8. **Cross-run history** — after the regression finishes, the orchestration
   caller calls `rebuild_stimulus_history(verification_dir)`
   (`history.py`, below) to fold every `stimulus-ledger-*.json` in the
   verification directory (across all prior runs, not just this one) into one
   durable `stimulus-history.json`.
9. **Debugger feedback** — on a failing run,
   `multigent/orchestration/artifacts.py` calls `rebuild_stimulus_history` and
   `verifier_stimulus_history_view` again to build a bounded, summary-only
   `coverage_closure_review`/`stimulus_summary` payload for the next Verifier
   repair prompt; see [`../feedback_to_debugger/README.md`](../feedback_to_debugger/README.md).

## `__init__.py`

Re-exports, from the three domain `plan.py` files:
`build_interface_coverage_plan`, `load_interface_coverage_templates`,
`INTERFACE_COVERAGE_TEMPLATES_PATH` (protocol); `build_operation_coverage_plan`,
`load_operation_coverage_families`, `merge_coverage_plans`, `operation_family`,
`render_operation_coverage_catalog`, `synthesize_code_owned_operation_coverage`,
`validate_architecture_operation_features`, `validate_frozen_operation_scope`,
`validate_operation_coverage`, `OPERATION_COVERAGE_FAMILIES_PATH` (operation —
note lifecycle's own subpackage is not re-exported here at all, and
`operation_plan_for_tests` is defined in `operation/plan.py` but **not**
re-exported by this file either, even though the top-level facade exports it);
and from `runtime.py`: `CoverageRuntimeError`, `InterfaceCoverageTracker`,
`contract_coverage`, `get_coverage_tracker`, `normalize_verification_value`,
`record_stimulus`, `sample_operation`.

Notably absent from this file (present only via the top-level facade, which
imports directly from the leaf module): `history.py`'s `HISTORY_FILE`,
`LEDGER_GLOB`, `rebuild_stimulus_history`, `verifier_stimulus_history_view`
(this file does not import `history.py` at all); `runtime.py`'s
`ContractSnapshot`, `capture_contract_snapshot`, `observe_contract_reset_snapshot`,
`sample_contract_snapshot`; and every `operation/sampling.py` name (see
[`operation/README.md`](../operation/README.md)). If you need one of those, import
from `multigent.verifier_tool` (the top facade) or the leaf module directly —
not from `multigent.verifier_tool.coverage`.

## `cocotb_model.py`

The coverage-backend boundary: turns a frozen obligation into a real
[`cocotb_coverage`](https://github.com/mciepluc/cocotb-coverage) `CoverPoint`/
`CoverCross` object. Nothing here is re-exported by the top-level facade —
it is reached exclusively through `InterfaceCoverageTracker.__init__`, which
constructs exactly one `ContractCocotbCoverageModel` per test-process tracker.

### `predicate_matches(value: Any, predicate: Mapping[str, Any]) -> bool`

Evaluates one predicate: `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `between`
(inclusive, 2 args), `one_of` (membership), `mod_eq`/`mod_ne`
(`value % args[0] == / != args[1]`), `truthy`, `falsy`. Raises
`CocotbCoverageModelError` for an unrecognized op — the same set
`operation/plan.py:_validate_predicate` validates statically before this ever
runs. Called by `ContractCocotbCoverageModel._build_operation`'s `relation()`
closure (the actual cocotb-coverage `rel=` callback) and by
`ContractCocotbCoverageModel.sample_operation` (to compute its — currently
unused by callers, see below — return value).

### `ContractCocotbCoverageModel`

`__init__(self, plan: Mapping[str, Any], namespace: str)` — indexes
`plan["obligations"]` by id, then dispatches each to one of four builders by
`template`: `"handshake_states"` → `_build_handshake`, `"stall_stability"` →
`_build_stall`, `"operation_coverpoint"` → `_build_operation`, anything else
(`reset_behavior`, `completion_behavior`, `error_behavior`, `address_alignment`,
and any other plain named-bin template) → `_build_event_coverpoint`. Every
cocotb-coverage point name is namespaced `f"{namespace}.{obligation_id}.coverpoint"`
(or `.valid`/`.ready`/`.valid_x_ready` for handshake groups), where `namespace`
is `f"contract_runtime_{next(_TRACKER_IDS)}"` — a process-wide counter, so two
trackers in one process never collide in `cocotb_coverage.coverage.coverage_db`.

- **`_labels(obligation) -> list[str]`** (staticmethod) — extracts and
  validates bin names (non-empty, unique). Used by every builder.
- **`_build_event_coverpoint(obligation_id, obligation)`** — one `CoverPoint`
  whose bins *are* the string labels themselves (`bins=labels`), `inj=True`
  (injective: one sample hits exactly one bin). This is the default/fallback
  builder.
- **`_build_operation(obligation_id, obligation)`** — one `CoverPoint` over
  integer bin indices with `bins_labels=labels` and `rel=relation` calling
  `predicate_matches`; `inj=False` because operation bins may legitimately
  overlap (a boundary value can be both `positive` and `maximum`).
- **`_build_stall(obligation_id, obligation)`** — validates every bin has an
  integer `[low, high|None]` `range`, then one `CoverPoint` whose `rel` checks
  `low <= length <= high`; `inj=True`.
- **`_build_handshake(obligation_id, obligation)`** — validates every bin has
  binary `values.valid`/`values.ready`; builds two component `CoverPoint`s
  (`.valid`, `.ready`, each `bins=[0,1]`/`bins_labels=["low","high"]`) plus one
  `CoverCross` over both, composed as
  `valid_point(ready_point(cross_point(sample_handshake)))` so both components
  sample before the cross reads their current hits. Records
  `_handshake_cross_bins[obligation_id]`, a label → `("low"|"high",
  "low"|"high")` map used later to translate cocotb-coverage's own cross-bin
  keys back into the obligation's declared bin names.
- **`sample_bin(obligation_id, bin_name)`** — the generic string-label
  sampler for `_build_event_coverpoint`-built points. Called by
  `InterfaceCoverageTracker._hit` (i.e. from `_sample_reset`,
  `_sample_completion`, `_sample_error`, `_sample_address`, and from
  `lifecycle/runtime.py`/`protocol/runtime.py`'s returned `(id, bin)` hits).
- **`sample_handshake(obligation_id, valid, ready)`** /
  **`sample_stall_length(obligation_id, length)`** — template-checked
  samplers called only from `InterfaceCoverageTracker.sample_snapshot`.
- **`sample_operation(obligation_id, value) -> list[str]`** — samples the
  point and independently recomputes (via `predicate_matches`) which bin names
  `value` matches. **This return value is currently discarded by every
  caller** — both `OperationSamplingMonitor.sample` (via the `sample_value`
  callback parameter) and `InterfaceCoverageTracker.sample_operation` (which
  computes its own `matched_bins` by diffing `_bin_hit_counts()` before/after
  instead) ignore it. Treat it as informational/testable, not load-bearing.
- **`detailed_coverage(obligation_id) -> dict[str, int]`** — bin name → hit
  count; for a handshake obligation, translates through
  `_handshake_cross_bins`, otherwise reads the cocotb-coverage object's own
  `.detailed_coverage` attribute directly. Called by
  `InterfaceCoverageTracker._bin_hit_counts` and `.report()`.
- **`manifest() -> list[dict[str, Any]]`** — the build-time description of
  every generated cocotb-coverage object (which template, which underlying
  coverpoint/cross names, sampling origin for operation points). Embedded
  verbatim in `InterfaceCoverageTracker.report()["coverage_model"]`.

## `runtime.py`

The largest and most central file in the coverage domain (~1300 lines). Owns
the per-test sampling orchestration, the process-wide tracker singleton, the
JSON coverage report, and the stimulus ledger. Everything under "Public API"
in `verifier_tool/__init__.py`'s `coverage.runtime` block is re-exported by
both this package's `__init__.py` and the top facade identically — no gap here.

### Module-level helpers

- **`CoverageRuntimeError(AssertionError)`** — the umbrella runtime exception.
  Subclasses `AssertionError` deliberately, so a coverage/protocol violation
  surfaces to cocotb/pytest exactly like a failed `assert`. Caught only in
  tests (`multigent/tests/test_*coverage*.py`); production code lets it
  propagate and fail the cocotb test.
- **`ContractSnapshot`** — `@dataclass(frozen=True)`, implements
  `Mapping[str, int]` over `data` plus a `signal_widths` mapping exposed as
  `.widths`. One instance = one immutable, same-event observation of every
  declared top-level DUT signal.
- **`_integer(handle, signal_name) -> int`** — reads a cocotb signal handle,
  preferring `.value.to_unsigned()` when present, wrapping any failure as
  `CoverageRuntimeError`.
- **`capture_contract_snapshot(dut, signal_names) -> ContractSnapshot`** — the
  only place DUT signals are actually read into a snapshot. Requires every
  named signal to exist as a top-level `dut` attribute; records each signal's
  elaborated `len()` as its width (`0` if unavailable, e.g. a plain Python
  test double). Called from generated TB monitor code
  (`assertion/protocol/generator.py` renders the literal call) and directly by
  several `multigent/tests/test_*.py` files building a snapshot without cocotb.
- **`_evidence_snapshot(snapshot) -> dict`** — JSON-safe copy of a snapshot for
  embedding in the report/ledger; values over 128 bits become a `0x...` hex
  string (full precision kept; only the *presentation* is bounded, for the
  Debugger's separate string-shortening logic to work on without losing either
  end of the value).
- **`_signal_names_from_bindings(obligations) -> tuple[str, ...]`** — fallback
  signal-name deriver used only when `plan["monitor"]["signals"]` is empty
  (e.g. a hand-built plan in a unit test); walks every obligation's
  `bindings` for known signal-shaped keys, including nested
  `operation_coverpoint` sampling `fields`/`guards`/`channel`.
- **`_related_signal_names(detail, snapshot) -> list[str]`** — extracts a
  `related_signals=(...)` marker (written into assertion-failure messages by
  generated TB assertion code) via regex + `ast.literal_eval`; falls back to
  every signal name in the snapshot. Used only by `_assertion_failure`.

### `InterfaceCoverageTracker`

Instantiated once per cocotb test **process** (not once per test function —
see `begin_test`/`end_test`) by `get_coverage_tracker()`. Constructor
`__init__(self, plan, report_path=None, stimulus_ledger_path=None)` builds, in
order: `self.coverage_model = ContractCocotbCoverageModel(plan, namespace)`
(elaborates every cocotb-coverage object up front — "the direct equivalent of
elaborating SystemVerilog covergroups," per the source comment);
`self.operation_monitor = OperationSamplingMonitor(plan, self._signal,
self._signal_width)`; `self.protocol_adapter =
ReadyValidCaptureAdapter(plan["interface_contract"])` (from
`operation_metadata/protocol.py` — captures accepted payloads on role-bound
ready/valid channels, independent of coverage); `self.protocol_coverage_monitor
= ProtocolCoverageMonitor(plan)`; `self.lifecycle_coverage_monitor =
LifecycleCoverageMonitor(plan)`. Cross-validates that every `channel_stall`
operation-sampling point's bound channel has a matching `stall_stability`
obligation, raising `CoverageRuntimeError` up front otherwise (a plan with a
dangling `channel_stall` binding fails at construction, not at first sample).

- **`begin_test(test_name=None)`** — clears per-test-only *temporal* state
  (sub-monitor `reset()` calls, `_previous_values`, `_error_seen`,
  `_recent_snapshots`, `_last_snapshot`) but deliberately **not** cumulative
  counters or coverage hits, which the docstring says "intentionally remain
  process-wide." Called by `contract_coverage()`'s wrapper at the start of
  every decorated test.
- **`end_test()`** — raises `CoverageRuntimeError` if no sample happened since
  `begin_test` (a vacuous monitor interval — the generated monitor task never
  actually ran) or if `protocol_adapter.snapshot()` still holds an accepted
  transfer on a channel bound to a known operation's input/output (a
  functional job reached the golden checker's channel but was never finalized
  through `record_stimulus`). Called at the end of `contract_coverage()`'s
  wrapper, after the test body and the assertion finalizer both succeed.
- **`_hit(obligation_id, bin_name)`** — forwards to
  `coverage_model.sample_bin`.
- **`_signal(snapshot, name)` / `_signal_width(snapshot, name,
  declared_width=0)`** (staticmethods) — read through a `ContractSnapshot`,
  raising `CoverageRuntimeError` for an undeclared name. Width resolution
  prefers the snapshot's elaborated width (from `capture_contract_snapshot`'s
  `len(handle)`) over any literal contract width string, since contracts may
  declare parameterized widths like `$clog2(FIR_TAPS)` that only simulation
  can resolve.
- **`sample_snapshot(snapshot, protocol_assertions)`** — the main per-edge
  entry point, called once per non-reset (and, via `observe_reset_snapshot`,
  per in-reset) sample. In order: runs the TB's own generated protocol
  assertion callback (its `AssertionError`, if any, is captured by
  `_assertion_failure` — which records the failure and then **re-raises** as
  `CoverageRuntimeError`, so this is not a swallowed exception) and captures
  its returned `completed_stalls` mapping; determines `reset_active` via
  `_reset_is_active` and bumps `self.reset_epoch` on a rising reset edge;
  samples `lifecycle_coverage_monitor.sample(snapshot, reset_active=...)`
  unconditionally; resets `operation_monitor`/`protocol_adapter`/
  `protocol_coverage_monitor` while in reset, or calls
  `protocol_adapter.observe(...)` while not; for every obligation, dispatches
  `handshake_states` (skipped during reset) /
  `stall_stability` (skipped during reset; requires the length to be
  `> 0`) / `reset_behavior` / `completion_behavior` / `error_behavior` /
  `address_alignment` to the tracker's own per-template methods below; then,
  off-reset only, samples `protocol_coverage_monitor.sample(snapshot)`; then
  unconditionally `operation_monitor.sample(snapshot, coverage_model.sample_operation,
  reset_active=..., completed_stalls=<stall lengths keyed by (valid,ready) signal pair>)`.
- **`observe_reset_snapshot(snapshot, protocol_assertions)`** — a second entry
  point for a reset pulse that occurs strictly between two of the normal
  per-edge samples (a legal synchronous reset shorter than the normal sampling
  cadence must still be seen). Only reads the reset input, runs the TB
  protocol-assertion callback (return value discarded here — no stalls are
  finalized mid-reset), resets the three sub-monitors, samples lifecycle
  coverage with `reset_active=True`, and dispatches only `reset_behavior`
  obligations to `_sample_reset`.
- **`_reset_is_active(snapshot) -> bool`** — reads the bound signal of the
  (expected to be singular) `reset_behavior` obligation against its declared
  `active_value`.
- **`sample_operation(operation_name, fields, stimulus_kind, stimulus_id=None)`**
  — the tracker's operation-linking method (distinct from the module-level
  `sample_operation()` function below and from
  `cocotb_model.py:ContractCocotbCoverageModel.sample_operation`). Caller
  `fields` are explicitly documented as never hitting bins — they exist only
  for source-compatibility with older generated TBs. Given a `stimulus_id`,
  looks up its record; a repeat call for an already-sampled `operation_name`
  on the same record is silently a no-op (safe against a generated TB calling
  the checked-stimulus wrapper more than once). Otherwise walks
  `stimulus_record["operation_evidence"][operation_name]` — per-concept value
  lists already computed by `operation_metadata.canonical.classify_checked_operations`
  inside `record_stimulus` — and feeds each value through
  `coverage_model.sample_operation` for every `canonical_job`-sampled point of
  that operation. Computes `matched_bins` by diffing `_bin_hit_counts()`
  before/after (see the `cocotb_model.sample_operation` return-value note
  above). Appends to `stimulus_record["operation_samples"]` and rewrites the
  ledger.
- **`record_stimulus(stimulus_kind, stimulus, expected, label=None,
  operation_evidence=None, operation_metadata=None, operations=(),
  observed=None) -> str`** — persists one checked DUT job. JSON-normalizes
  `stimulus`/`expected`/`observed` via `_json_value`. When `operation_metadata`
  and `operations` are both supplied (a real functional job, not a bare
  protocol-only record), it cross-validates hard: the code-owned
  `protocol_adapter`'s actually-captured input/output transfers must be
  non-empty when a planned job exists; the accepted-transfer-derived canonical
  job's `.inputs` must equal the TB-supplied stimulus's canonical job
  `.inputs` (`assemble_canonical_job`, from `operation_metadata/canonical.py`);
  the accepted command must be exactly one role-bound event in the *current*
  reset epoch; `stimulus.operation.evaluate_canonical_operation` (the
  independent golden re-evaluator) run on the *accepted* stimulus must equal
  both the TB's claimed `expected` and the adapter's captured `accepted`
  output, and the TB's claimed `observed` must equal the accepted output too;
  output framing must assert `LAST` only on the final accepted beat; exactly
  one new completion event must have occurred since the previous recorded
  job. Any mismatch raises `CoverageRuntimeError`. Only after all checks pass
  does it compute a sha256 `digest` (over kind/stimulus/expected/
  operation_evidence/accepted channel payloads & events/reset_epoch — used by
  `history.py` to detect duplicate executions across runs), append the
  record, flush the ledger (`write_stimulus_ledger`), and reset
  `protocol_adapter` for the next job.
- **`_bin_hit_counts() -> dict[str, int]`** — flattens every obligation's bins
  into `"<obligation_id>.<bin_name>" -> count`. Used for before/after diffing
  in `sample_operation` and `record_stimulus`.
- **`_sample_reset` / `_sample_completion` / `_sample_error` /
  `_sample_address`** — the tracker's own direct per-template samplers (see
  the "Obligation templates" table above for which templates route here).
  `_sample_completion` additionally hits a `back_to_back` bin on the second and
  later consecutive rising edge without an intervening reset. `_sample_error`
  hits `recovered` only after having previously seen the error asserted.
  `_sample_address` hits up to four bins per sample
  (`minimum`/`aligned_interior`/`maximum`/`boundary_neighbor`) — these are not
  mutually exclusive.
- **`_sample_axi_boundary`** — defined but **never called** from
  `sample_snapshot`'s dispatch (which recognizes only `reset_behavior`/
  `completion_behavior`/`error_behavior`/`address_alignment`) or anywhere else
  in the repository. Dead code, superseded by
  `protocol/runtime.py:ProtocolCoverageMonitor._address_hits`'s
  `axi4_4k_boundary` branch, which performs the equivalent
  would-cross/ends-at/ends-before boundary classification through the
  `_SPECIAL_TEMPLATES` dispatch path instead. Worth knowing before either
  deleting it as unreachable or assuming it is wired to something.
- **`_assertion_failure(obligation_id, detail, *, snapshot=None)`** — appends
  to `assertion_failures`/`failure_records` (with `_related_signal_names`, the
  current snapshot, and up to the last 8 recent snapshots from
  `self._recent_snapshots` as bounded Debugger evidence), calls
  `write_report()` immediately (so a report exists even if the process is
  killed right after), then re-raises as `CoverageRuntimeError`. The sole
  place these two lists are populated.
- **`report() -> dict[str, Any]`** — assembles the full JSON coverage report:
  per-obligation bin rows, `missing_bins`/`covered_bins`, `bin_hits`, the "five
  verdicts" (`mathematical_correctness`, `protocol_correctness`,
  `transaction_completeness`, `scenario_coverage`, `structural_tb_validity`),
  `unresolved_obligations` (from `plan["verification_manifest"]`), and a
  randomized-transaction-count check against
  `plan["requirements"]["randomized_transactions_minimum"]` — counted from
  `directed_stimuli`/`randomized_stimuli` when a stimulus ledger path is
  configured, else from `randomized_operation_samples` (the metric's source
  changes depending on whether ledger-based recording is wired up for this
  run). Also fails `scenario_coverage`-relevant `missing` if any known
  (non-`llm_extension`) operation exists but zero stimulus records were ever
  written. Embeds `coverage_model.manifest()` and `operation_monitor.report()`
  verbatim.
- **`write_report()`** — writes the JSON report plus a
  `cocotb_coverage.coverage.coverage_db.export_to_yaml(...)` sibling file
  (same path, `.cocotb-coverage.yml` suffix) — the library's own raw dump,
  kept alongside this module's higher-level JSON.
- **`write_stimulus_ledger()`** — writes `{schema_version, stimulus_count,
  directed_stimuli, randomized_stimuli, records}` to `stimulus_ledger_path`.
  Called after every `record_stimulus` and every ledger-linked
  `sample_operation` call, not just at test end.
- **`close()`** — idempotent (`self._closed` guard); calls `write_report()`
  and `write_stimulus_ledger()`. Registered via
  `atexit.register(tracker.close)` in `get_coverage_tracker()`.

### Remaining module-level functions

- **`_json_value(value, description) -> Any`** / **`normalize_verification_value(value,
  description) -> Any`** (public alias for the same function) — recursively
  normalizes `Mapping`/`list`/`tuple`/`None`/`str`/`int`/`float`/`bool`/
  numpy-like values (anything with `.tolist()` or `.item()`) into plain JSON
  data, rejecting anything else or a non-finite float. `record_stimulus` uses
  it internally on `stimulus`/`expected`/`observed`/`operation_evidence`;
  `normalize_verification_value` is exposed so a generated TB can pre-normalize
  a value the identical way before comparing it itself.
- **`get_coverage_tracker() -> InterfaceCoverageTracker`** — the process-wide
  singleton accessor. Reads `NPU_FUNCTIONAL_COVERAGE_CONFIG`/
  `NPU_FUNCTIONAL_COVERAGE_REPORT`/`NPU_STIMULUS_LEDGER_REPORT` (set by
  `multigent/tools/cocotb_runner.py:run_cocotb_regression`), loads the plan
  JSON, constructs the tracker, registers `atexit.register(tracker.close)`.
  Raises `CoverageRuntimeError` if the two required env vars are missing —
  i.e. any code path calling into coverage sampling outside a runner-managed
  cocotb subprocess fails loudly rather than silently no-op'ing.
- **`sample_contract_snapshot(snapshot, protocol_assertions)`** /
  **`observe_contract_reset_snapshot(snapshot, protocol_assertions)`** — thin
  wrappers forwarding to `get_coverage_tracker().sample_snapshot(...)` /
  `.observe_reset_snapshot(...)`. These (not the tracker methods) are the
  literal names generated TB monitor code imports and calls
  (`assertion/protocol/generator.py` renders the call sites).
- **`sample_operation(...)` / `record_stimulus(...)`** (module level) — thin
  wrappers forwarding to the tracker's methods of the same name. These two
  specific names are the ones `multigent/agents/verifier.py`'s static AST
  review statically forbids the Verifier LLM from calling directly ("do not
  import or call sample_operation or raw record_stimulus yourself") — a
  generated TB must instead call a code-owned wrapper
  (`_contract_record_checked_stimulus`, rendered by
  `assertion/instrumentation.py` / `assertion/operation/generator.py`) that
  performs the independent oracle comparison first and calls these on the
  LLM's behalf. `multigent/tools/diagnostic.py` (Debugger diagnostic reruns)
  statically strips `sample_operation`/`record_stimulus` calls and the
  `@contract_coverage()` decorator from a copied test before re-running it,
  since a diagnostic rerun has no trusted `NPU_FUNCTIONAL_COVERAGE_CONFIG`
  environment and must not count coverage or append to the ledger.
- **`contract_coverage()`** — the decorator factory generated tests apply to
  every `@cocotb.test()`. The returned wrapper: gets the tracker, calls
  `begin_test(test_function.__name__)`, calls
  `tracker.operation_monitor.bind_observers(test_function.__globals__)`,
  requires the test module to define `_contract_generated_monitor` (started as
  a background `cocotb.start_soon` task) and `CONTRACT_SIGNAL_NAMES` (must
  equal `tracker.signal_names` exactly — a generated TB whose declared signal
  list has drifted from the runner-owned plan fails before the test body runs)
  and `_CONTRACT_PROTOCOL_STATE` (cleared before and after); runs the test
  body; if the background monitor task already finished with an exception,
  re-raises it; requires and calls the generated assertion finalizer
  (`_finalize_contract_assertions`, or the older name
  `_finalize_contract_protocol_assertions`); calls `tracker.end_test()`; and in
  a `finally` block cancels the monitor task, clears protocol state, and
  unconditionally calls `tracker.write_report()`.

## `history.py`

A **durable, cross-run** ledger, deliberately separate from
`InterfaceCoverageTracker`'s per-test-process bookkeeping. The tracker knows
only about stimuli recorded during its own process's lifetime (one
`stimulus-ledger-<tag>.json` per regression run/tag); `history.py` knows about
every ledger file that has ever accumulated in the verification directory,
across every architecture/repair/PPA/verifier-revision iteration.

- **`HISTORY_FILE = "stimulus-history.json"`** / **`LEDGER_GLOB =
  "stimulus-ledger-*.json"`** — the merged-output filename and the glob
  pattern matching every per-run ledger `InterfaceCoverageTracker.write_stimulus_ledger`
  has ever written into a verification directory.
- **`rebuild_stimulus_history(verification_dir: Path) -> dict[str, Any]`** —
  globs and sorts every `stimulus-ledger-*.json` in `verification_dir`
  (lexical sort — ledger filenames embed the tag, e.g.
  `av2-r1-p0-v3`, so this is not strictly chronological if tags are not
  zero-padded consistently), silently skipping unreadable/malformed files.
  For each run, tags every record with a synthetic `history_id` (
  `f"run{run_number:04d}:{index:06d}"`), `source_ledger`, and `source_tag`, and
  accumulates a `unique_digests` set from each record's `digest` (the sha256
  `record_stimulus` computed) to compute `duplicate_execution_count` — the
  same logical stimulus (identical stimulus/expected/operation_evidence/
  accepted-transfer capture/reset epoch) re-executed across separate repair
  iterations is counted as a duplicate, not double-credited. Writes
  `verification_dir/HISTORY_FILE` and returns the same dict. Called by
  `multigent/orchestration/verification_tools_node.py` after every regression
  (success or failure) and by `multigent/orchestration/artifacts.py` when
  building Debugger repair context.
- **`verifier_stimulus_history_view(history, *, history_path: Path) -> dict[str, Any]`**
  — a **summary-only** projection of the merged history for LLM prompts.
  Explicitly documented (`payload_mode: "SUMMARY_ONLY"`,
  `exact_payloads_in_prompt: False`) to never place exact stimulus/expected
  payloads in a prompt — those remain on disk at `history_path` for audit/replay
  only. Computes `kind_counts`, `label_counts`, `covered_bin_execution_counts`
  (how many times each bin id was newly covered across all runs — not the same
  as a single run's hit count), and per-operation `operation_samples` field
  summaries via `_summarize_values`. Called by
  `multigent/orchestration/artifacts.py` to build `coverage_closure_review.stimulus_summary`
  in the repair prompt fed back to the Verifier.
- **`_summarize_values(values: list[Any]) -> dict[str, Any]`** — for one
  operation field's accumulated values across history: splits scalar vs.
  composite (list/dict) observations, computes a value-count histogram capped
  at the 16 most common distinct values (`value_counts_truncated` flags when
  more exist), and numeric `numeric_min`/`numeric_max` when applicable. This
  is the actual mechanism that keeps `verifier_stimulus_history_view`'s output
  prompt-sized regardless of how many runs have accumulated.

## Cross-links

- [`protocol/README.md`](../protocol/README.md),
  [`lifecycle/README.md`](../lifecycle/README.md),
  [`operation/README.md`](../operation/README.md) — the three domain plan
  builders this file's runtime consumes.
- [`../README.md`](../README.md) — `verifier_tool` package map, the
  three-domain taxonomy, and the code-owned vs. LLM-owned boundary this
  domain enforces at `record_stimulus`/`sample_operation`.
- [`../feedback_to_debugger/README.md`](../feedback_to_debugger/README.md) —
  the downstream consumer of the coverage report and stimulus ledger this
  folder produces.
- [`../operation_metadata/README.md`](../pool/operation_metadata/README.md) —
  `ReadyValidCaptureAdapter`, `assemble_canonical_job`,
  `classify_checked_operations` (used by `runtime.py:record_stimulus`/
  `sample_operation`) and `supported_code_owned_concepts` (used by
  `operation/plan.py`).
- [`../feature_plans/README.md`](../pool/feature_plans/README.md) — not yet
  written; would document the `protocol_features.yaml`/`lifecycle_features.yaml`/
  `operation_features.yaml` catalogs and the `feature_plans/compiler.py`
  branch-selection logic that `protocol/plan.py` and `lifecycle/plan.py` (but
  not `operation/plan.py`) call into.
- [`../lifecycle_policy_pool/README.md`](../pool/lifecycle_policy_pool/README.md) —
  the Architect-selectable behaviors that determine which lifecycle
  obligations in the table above are even reachable.
