# Assertion / Lifecycle

Code-owned checkers for reset, command acceptance, busy/active tracking,
completion, and error behavior — the taxonomy category the top-level README
defines as "reset/abort, legal and illegal commands, global busy state,
completion/error, job retirement, recovery, and post-reset purity." Like
`protocol/assertion/`, this subfolder has no local YAML: it is backed by
`verifier_tool/pool/feature_plans/lifecycle_features.yaml` (the catalog of
reset/command/job/status features and their default assertion/coverage/
stimulus wiring) and by
`verifier_tool/pool/lifecycle_policy_pool/lifecycle_policies.yaml` (the
Architect-selectable behaviors — completion timing, error style, reset
disposition — that this subfolder's checkers enforce). See
[`../../lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md)
for the policy selection format.

## Architectural asymmetry vs. `protocol/assertion/`

Protocol dispatches independent checker functions by implementation name.
Lifecycle keeps one shared temporal state machine because command acceptance,
active-job state, retirement, completion, and error timing depend on the same
history. It is still feature-selective: `runtime.py` compiles
`enabled_by_operation` from the resolved assertion branch, and
`check_lifecycle_operations` gates each property by its selected checker name.
Therefore, a contract-local lifecycle policy extension can remove only its
dependent built-in checker while preserving busy, completion, reset, or command
checks that remain applicable. The generated `features` tuple is both an audit
trail and the source of this enablement; it is no longer documentation-only.

## `assertion_checkers.py`

Internal helpers: `_read` (typed snapshot lookup, raises if the bound signal
is absent), `_transfer` (valid∧ready), `_status_signal` (returns a status
role's bound signal name, or `""` if the role has zero or more-than-one
binding — an unbound status role is silently skipped, never invented), `_fail`
(raises `AssertionError("feature=<id>; <detail>")`).

- `is_lifecycle_reset_active(snapshot, reset: Mapping[str, Any]) -> bool` —
  true when the bound reset signal's sampled value equals its declared
  `active_value` (`0` or `1`). **Called from** `runtime.py:check_lifecycle_assertions`.
- `check_reset_outputs(snapshot, reset_outputs: Mapping[str, Any])` — while
  reset is active and after the reset signal's optional
  `reset_settle_cycles`, every signal named in the contract's declared
  `reset_outputs` mapping must equal its declared value; unbound signals are
  skipped rather than failed. Reset-only rising-edge snapshots clear temporal
  state but do not advance this full-output settling counter.
- `check_lifecycle_operations(snapshot, operations, state,
  enabled_by_operation=None, job_start_by_operation=None,
  job_complete_by_operation=None)`
  — the core per-operation state machine. For each bound operation it keeps
  (in `state["operations"][name]`) `active`, `completion_due`,
  `previous_completion`, `previous_error`, `error_due`, `error_due_sources`,
  `error_seen`, `last_error_source`, `retirement_count`,
  `outstanding_write_requests`, and `final_output_retired`, plus the frozen
  enabled checker set, and enforces only selected properties per sampled cycle.
  `job_start_by_operation` / `job_complete_by_operation` carry this cycle's
  already-abstracted JOB_START / JOB_COMPLETE events for operations whose policy
  selects `control_plane_sequence` (produced by
  `control_plane_sequence_tracker.py`, below). A JOB_START event has the same
  effect as an accepted legal command (`active` set, retirement counters
  cleared); a JOB_COMPLETE event has the same effect as a final retirement
  transfer (`active` cleared; `completion_due` armed when a completion status
  signal is bound and `completion_matches_final_output` is enabled).
  Everything after that point consumes only `active`, so it does not care
  whether the event came from a ready/valid command or a register sequence. For
  a control-plane operation, the final output retirement does **not** clear
  `active` by itself — only JOB_COMPLETE does. Enforced properties:
  - **`<op>.status_pulses_are_one_cycle`** — `completion`, and (for
    `error_style == "pulse"`) `error`, may not read high on two consecutive
    sampled cycles.
  - **`<op>.completion_matches_final_output`** — a final retirement transfer
    (see below) must be followed by `completion` on the very next sample, and
    `completion` may never occur without a preceding final transfer. When
    completion is missing, the failure includes the accepted retirement
    count and outstanding write-request count to distinguish premature
    output retirement from a genuinely late completion pulse. For a
    register-mapped `control_plane_sequence`, the successful `job_complete`
    poll is instead forbidden until all declared output beats **and** their
    final successful write response have retired. The monitor retains the
    active job after the last write response until that poll succeeds; an
    early `ap_done` readback fails this same feature with the observed
    retirement and outstanding-request counts. This uses external AXI4 and
    AXI4-Lite handshakes, not an internal HLS `ap_done` wire.
  - **`<op>.illegal_command_errors_without_start`** — an accepted illegal
    command must produce `error` on the next sample; `error` may not occur
    unprompted (except a still-asserted `sticky_until_reset` error). The
    response-error checker below owns error timing for non-OKAY memory
    responses, so its failures do not masquerade as illegal-command failures.
  - **`<op>.response_error_follows_nonokay`** — an accepted non-OKAY memory
    read or write response must produce `error` on the next sample. This
    checker is selected only when the resolved operation has response
    channels; either error checker enforces an applicable sticky error until
    reset.
  - **`<op>.legal_command_starts_one_job`** — an accepted legal command while
    a job is already active is a failure, *unless* the command's payload
    fails a declared base-address word-stride check (`metadata_fields` with
    `address_role: base` and `word_stride_bytes`), in which case it is
    reclassified as an error condition rather than a second job start.
  - **`<op>.no_output_without_active_job`** — any accepted output transfer
    while no job was active before this cycle is a failure.
  - **`<op>.busy_tracks_active_job`** — the bound `busy` status signal (if
    any) must be high exactly while a legal job is active.
  - Retirement counting: each accepted retirement transfer increments
    `retirement_count`; if the retirement channel carries `last`, that bit
    must coincide exactly with reaching the operation's declared
    `expected_count`; a job's active/completion-due state clears on the final
    retirement, and `retirement_count` resets to `0` on the next accepted
    legal command. Full-width AXI4 counts accepted W beats and waits for the
    final successful B response. A narrow/byte AXI4 contract instead counts
    accepted WSTRB bytes against the output's canonical byte count, still
    waiting for all B responses; two or four narrow beats must not retire a
    complete s32 output early. The plan's retirement entry selects this with
    `count_mode` (`accepted_data_beats_after_all_write_responses` when the
    output's `transfer_size_bins` is `full_width`, else
    `accepted_data_bytes_after_all_write_responses`); it also carries the AW
    request, W data (incl. strobe), and B response signals, so the checker
    increments `outstanding_write_requests` per accepted AW, decrements it per
    accepted B, ignores a non-OKAY B as a final retirement, and sets
    `final_output_retired` only when the count is exact **and** no request is
    outstanding.
  - `error_responses` entries (a response channel with a `resp` field) with a
    nonzero response arm the response-specific error check and clear `active`.
    Concurrent illegal-command and response faults retain both causes.
- `finalize_lifecycle_checker_state(plan, state)` — end-of-test gate: raises
  if any operation is left with `active`, `completion_due`, or `error_due`
  still set — a finite test may not end with a job in flight or a required
  completion/error still pending.

## `runtime.py`

- `build_lifecycle_assertion_plan(interface_plan, operation_metadata) -> dict[str, Any]`
  — builds the inert plan embedded in the generated TB. Calls
  `feature_plan.py::build_lifecycle_feature_plan(interface_plan,
  operation_metadata)` (the only one of the three domain matchers that needs
  *both* the interface plan and compiled operation metadata — lifecycle
  features are scoped per operation, not per channel; see
  [`../../feature_plans/README.md`](../../pool/feature_plans/README.md)), then
  `compile_assertion_feature_plan`. Returns `{schema_version: 2, feature_plan,
  compiled_assertions, reset, reset_outputs, operations,
  enabled_by_operation, features}`, where
  `reset`/`reset_outputs`/`operations` are copied straight from
  `feature_plan["bindings"]` — the exact mapping `check_lifecycle_operations`
  consumes. **Called from**
  `../../orchestration/instrumentation.py:render_contract_generated_block` (via
  `lifecycle_assertion_metadata`, see `generator.py` below) and directly in
  `multigent/tests/test_canonical_operation.py`,
  `multigent/tests/test_lifecycle_automation.py`,
  `multigent/tests/test_lifecycle_policy_pool.py`, and
  `multigent/tests/test_feature_plans.py`.
- `check_lifecycle_assertions(snapshot, plan, state)` — per-cycle entry point.
  If `is_lifecycle_reset_active`, it counts reset-active output samples, runs
  `check_reset_outputs` only once more than the reset signal's
  `reset_settle_cycles` (plan key `reset.settle_cycles`, default 0) samples
  have elapsed, then clears `state` (keeping only `_reset_active_samples`,
  `reset_seen = True`, and — for an operation whose `reset_behavior` is a
  contract-local extension — that operation's in-flight state with its status
  history reset). Otherwise, for each operation carrying a
  `control_plane_sequence` it first calls `advance_control_plane_sequence`
  (using that operation's `control_plane_signals`) to obtain the cycle's
  JOB_START / JOB_COMPLETE booleans, then runs `check_lifecycle_operations`
  with them. `reset_settle_cycles` is a signal-level key that the compiled
  plan honors when a frozen interface contract carries it; the current
  Architect response schema has no such signal property (signals are
  `additionalProperties: false`), so only hand-authored contracts set it.
  **Called from**
  `../../orchestration/instrumentation.py`'s generated `_check_contract_assertions` (as
  `_contract_check_lifecycle_assertions`) inside `_contract_generated_monitor`.
- `finalize_lifecycle_assertions(plan, state)` — thin wrapper over
  `finalize_lifecycle_checker_state`. **Called from** the generated
  `_finalize_contract_assertions` (as `_contract_finalize_lifecycle_assertions`),
  itself invoked by `orchestration/runtime.py`'s per-test coverage wrapper after
  the `@cocotb.test()` body returns.

## `control_plane_sequence_tracker.py`

`advance_control_plane_sequence(snapshot, control_signals, sequence, state) ->
(job_start_fired, job_complete_fired)` turns one sampled AXI4-Lite control-bus
snapshot into the two abstract events for an operation whose policy selects
`control_plane_sequence`. Unlike a ready/valid command (a pure function of one
snapshot), a register transaction spans several cycles, so the tracker is
stateful per operation, stored in the same persistent `state` dict the other
lifecycle checkers use:

- A write completes when AW and W have each been accepted (either order) and B
  is then accepted; a read completes on an accepted AR followed by an accepted
  R. Only the declared control channel's valid/ready/addr/data signals are read
  (`control_plane_signals`, flattened from the one AXI4-Lite *subordinate* group
  by `pool/feature_plans/lifecycle.py::_control_plane_signals`).
- Each completed transaction is compared, in order, against the next declared
  action: `write_reg`/`read_reg` match on register address; `write_field` /
  `poll_field` additionally require the observed bit to equal the declared
  `value` / `expected`. A non-matching transaction does not advance or reset
  the index.
- JOB_START fires when the last `job_start.actions` entry is matched;
  JOB_COMPLETE fires when the last `job_complete.actions` entry (the single
  `poll_field`) is matched with its expected bit. Both indices rearm to 0 after
  firing.

The tracker knows nothing about accelerators or register spellings beyond the
declared `registers` map. Its stimulus-side counterpart is
`lifecycle/stimulus/cocotb.py::drive_control_plane_sequence`; the two consumers
must agree on the contract's action order. The ordering check between a
successful poll and output retirement lives in `check_lifecycle_operations`
(`completion_matches_final_output`, above), not here.

## `generator.py`

- `lifecycle_assertion_metadata(interface_plan, operation_metadata) -> tuple[dict[str, Any], tuple[str, ...]]`
  — thin wrapper: `(build_lifecycle_assertion_plan(interface_plan,
  operation_metadata), plan["features"])`. **Called only from**
  `../../orchestration/instrumentation.py:render_contract_generated_block`.
- `render_lifecycle_assertion_lines(plan: Mapping[str, Any]) -> list[str]` —
  renders `CONTRACT_LIFECYCLE_ASSERTION_PLAN = <literal dict>`, one
  `# LIFECYCLE ASSERTION [<feature>]` audit comment per compiled feature, and
  the two wrapper functions `_check_contract_lifecycle_assertions(snapshot)` /
  `_finalize_contract_lifecycle_assertions()` delegating to
  `check_lifecycle_assertions`/`finalize_lifecycle_assertions` imported from
  the facade. **Called only from**
  `../../orchestration/instrumentation.py:render_contract_generated_block`.

## Example: `busy_behavior` end to end

`feature_plans/lifecycle_features.yaml`:

```yaml
busy_behavior:
  category: lifecycle
  scope: signal
  match: {role: busy}
  assertion: {checker: busy_tracks_active_job}
  coverage:
    bins:
      - {name: idle, intent: Observe busy low with no active legal job.}
      - {name: active, intent: Observe busy high after an accepted legal job.}
      - {name: retired, intent: Observe busy return low after legal retirement.}
```

Unlike protocol's `stall_stability`, this checker name does not select a
separate Python function. Instead, `runtime.py` places
`busy_tracks_active_job` in this operation's `enabled_by_operation` set, and
the shared state machine evaluates the busy/active relationship only when that
checker is enabled. The YAML entry therefore selects assertion behavior as well
as its sibling coverage and stimulus branches. The actual enforcement remains
the literal
`if active_before and not busy: _fail(f"{root}.busy_tracks_active_job", "busy is low while a legal job is active")`
in `assertion_checkers.py:check_lifecycle_operations`.

Reset state transitions follow the same field-ownership boundary. With the
built-in `reset_behavior: abort_inflight`, `runtime.py` clears the lifecycle
state machine at active reset. When `reset_behavior` is an
`extension_request`, the operation's in-flight state is preserved instead:
the built-in abort transition, reset-specific checker, coverage, and stimulus
are all withheld so the contract-local extension is the sole authority for
that behavior. Independent reset-output checks and status-history epoch
boundaries remain enabled.

## See also

- [`../README.md`](../README.md) — the lifecycle domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — the
  generated TB block this subfolder's output is embedded into.
- [`../../protocol/assertion/README.md`](../../protocol/assertion/README.md),
  [`../../operation/assertion/README.md`](../../operation/assertion/README.md) — the other two
  assertion domains.
- [`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md) — the
  Lifecycle Feature Plan matcher (`lifecycle.py`), including how it resolves
  each operation's lifecycle policy and computes retirement counts.
- [`../../pool/lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md)
  — the Architect-selectable `lifecycle_policy` enums
  (`completion_style`, `error_style`, `reset_behavior`, etc.) that
  `check_lifecycle_operations` reads off each operation's `policy` binding.
- [`../../pool/operation_metadata/README.md`](../../pool/operation_metadata/README.md)
  — `build_architect_operation_metadata` is the compiled `operation_metadata`
  argument `build_lifecycle_assertion_plan` requires.
