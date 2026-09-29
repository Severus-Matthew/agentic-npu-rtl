# Stimulus — Lifecycle Domain

This is the `lifecycle` leg of the three-domain stimulus taxonomy described in
[`../README.md`](../README.md) and [`../../README.md`](../../README.md). It
covers reset/command-legality/job/busy/completion/error/recovery behavior. It
is a sibling of `lifecycle/assertion/` and `lifecycle/coverage/`, not a
dependency of either — all three independently consume the Lifecycle Feature
Plan built by `build_lifecycle_feature_plan()` (see
[`../../feature_plans/README.md`](../../pool/feature_plans/README.md)). That plan
is a different thing from
[`../../lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md):
the policy pool defines **which behaviors an Architect contract may select**
(`job_acceptance`, `busy_behavior`, `error_style`, etc.); the Lifecycle
Feature Plan defines **how the selected behavior is verified**. This folder
reads the *resolved* policy (`operation["lifecycle"]["policy"]` /
`operation["policy"]`) but does not itself validate or enumerate policy
choices — that is `lifecycle_policy_pool/policies.py`.

As with `protocol/`, this folder splits cleanly into planning and execution:

| File | Touches `dut`? | Kind |
|---|---|---|
| `stimulus_generator.py` | No | Builds a declarative scenario list from a frozen interface + operation metadata. No `cocotb` import. |
| `cocotb.py` | Yes | A small set of role-bound cocotb primitives, built on top of `protocol/stimulus/cocotb.py`, for driving one command channel, reading status signals, and (for `control_plane_sequence` operations) executing a register-mapped job start/completion sequence over an AXI4-Lite control bus. |

**These two files are not a direct pipeline.** `build_lifecycle_stimulus_plan`
never calls anything in `cocotb.py`. The automatic campaign consumes the
resolved reset signal/polarity and the applicable `reset_abort` scenario
phases, then drives those phases procedurally using `cocotb.py` primitives.
Other scenario kinds remain declarative inputs for inspection/extensions; they
are not generically interpreted one by one.

## Files

- `__init__.py` — re-exports the public names below.
- `stimulus_generator.py` — declarative scenario planning.
- `cocotb.py` — role-bound cocotb primitives.

## `__init__.py`

Re-exports `LifecycleStimulusGenerationError`, `build_lifecycle_stimulus_plan`
(from `stimulus_generator.py`) and `LifecycleDriveError`,
`assert_lifecycle_status`, `drive_accepted_command`,
`drive_accepted_command_on_reset_release`, `drive_control_plane_sequence`,
`wait_clock_cycles` (from `cocotb.py`). `../__init__.py` and `multigent/verifier_tool/__init__.py`
re-export the same names further up the facade chain.
`../../protocol/stimulus/drivers/axi_lite.py`
imports `drive_accepted_command` directly from
`multigent.verifier_tool.lifecycle.stimulus` (a `protocol/` file depending on
a `lifecycle/` file within this same `stimulus` package) because accepting an
AXI4-Lite job's start command is a lifecycle-owned action that has to run
concurrently with protocol-owned bus traffic.

## `stimulus_generator.py` — planning only, no DUT

`class LifecycleStimulusGenerationError(ValueError)` — raised when a lifecycle
scenario cannot be resolved safely from frozen metadata; today the only raise
site is an interface with more than one `role: reset` signal. An operation with
anything other than exactly one command-accept channel does **not** raise: it
yields a `metadata_blocker` scenario (see below).

`_safe(value: object) -> str` (private) — slugifies a value into
`[a-z0-9_]+` for use inside scenario/coverage-target IDs (e.g. turns a
data-object name into `input_<safe_name>` for a phase ID). Used only inside
this file.

### `build_lifecycle_stimulus_plan(interface, operation_metadata) -> dict[str, Any]`

Rejects more than one `role: reset` signal on the interface. Calls
`build_lifecycle_feature_plan(interface, operation_metadata)` (the shared
domain matcher — see [`../../README.md`](../../README.md)) and
`compile_stimulus_feature_plan(feature_plan)` to pull the declarative stimulus
branch out of the resolved plan, then independently builds a `scenarios` list
by hand from `feature_plan["bindings"]`:

- One `reset_idle` scenario if a reset is bound.
- Per operation, command handling is decided as follows (all verified in the
  source):
  - `job_acceptance` is a contract-local extension → one
    `verifier_extension` marker scenario, no command drive is guessed.
  - Otherwise, if the operation does not have **exactly one** command-accept
    channel (including zero, which is what every `control_plane_sequence`
    operation has) → a `lifecycle.<op>.command.unresolved` `metadata_blocker`
    scenario (`"operation needs exactly one command-accept channel"`), and the
    operation is then skipped entirely — it gets no reset-abort or
    post-reset-purity scenarios either. This is a hard signal that the
    operation cannot be lifecycle-automated by this plan, not a silent skip.
  - If there is one command channel but its legal values are not
    machine-readable → a `command.legality_unresolved` `metadata_blocker`; the
    reset-abort scenarios below are still emitted.
- Otherwise: `legal_command`, `illegal_command`, and
  `illegal_then_legal_recovery` (whose `clear_error_before_legal_job` field is
  `"reset"` when `operation["policy"]["error_style"] ==
  "sticky_until_reset"`, else `"pulse_deassertion"` — this is the one place in
  this file that reads the resolved lifecycle policy).
- Per operation, one `reset_abort` scenario per reachable phase — `idle`, one
  `input_<safe(data_object)>` per input, `compute`, and `output` only when at
  least two output transfers exist. A one-transfer result retires on its only
  accepted beat, so it has no distinct “accepted output but still active”
  phase. Each scenario carries a
  `requirements` list stating the two invariants a reset abort must uphold
  ("no completion is attributable to reset-aborted work",
  "no accepted pre-reset transfer is associated with a post-reset job").
- Per operation, one closing `abort_then_clean_job` (`kind:
  "abort_then_clean_job"`) scenario asserting the next job after any abort
  must match the golden model and produce no ghost output.

Contract-local policy extensions prune only dependent scenarios. A
`job_acceptance` extension emits a `verifier_extension` marker instead of
guessing a command drive. Error-related extensions retain legal jobs but omit
illegal/error-recovery scenarios. A `reset_behavior` extension omits reset-abort
and post-reset-purity scenarios. All unaffected sibling scenarios remain
tool-owned.

Returns `{schema_version: 1, source, feature_plan, compiled_stimulus, reset:
{signal, active_value}, scenarios: [...], execution_contract: [...]}`.

**Who calls it.** `multigent/verifier_tool/orchestration/instrumentation.py`
imports it directly (`from multigent.verifier_tool.lifecycle.stimulus import
build_lifecycle_stimulus_plan`) and calls it once per generated testbench, at
*generation* time, to embed the return value verbatim as the
`CONTRACT_LIFECYCLE_STIMULUS_PLAN` literal in the generated code-owned block.
It is also listed among the contract-level checks in
`../../CONTRACT_REVIEWER_INTEGRATION.md` (it is a separate call, not one of the
checks `review_contract_deterministically` runs) — there it is
called purely to see whether it raises (i.e. "is command/reset/status
resolvable at all"), not for its scenario content. Directly unit-tested by
`multigent/verifier_tool/tool_regression/integration/test_lifecycle_automation.py` and
`multigent/verifier_tool/tool_regression/integration/test_lifecycle_policy_pool.py`.

**How `../../orchestration/campaign.py` consumes it.**
`run_code_owned_verification_campaign(dut, interface, operation_metadata,
lifecycle_plan, ...)` reads the reset binding:

```python
reset = lifecycle_plan.get("reset", {})
reset_name = str(reset.get("signal", ""))
active_value = reset.get("active_value")
```

It also selects this operation's `kind: reset_abort` scenarios and executes
their resolved phase names. This keeps the driver aligned with reachability
decisions made by the Lifecycle Feature Plan; in particular, it never creates
an unrecorded completed job by attempting an impossible output-phase abort on
a one-transfer result. For a `control_plane_sequence` operation, the generated
campaign uses the same AXI4 memory driver as a normal checked job, stops only
after observed read/write progress reaches each declared phase, applies the
resolved reset, and requires the next accepted start to make clean progress.
Illegal-command and recovery probes are still driven by the campaign's
dedicated code rather than by a generic scenario interpreter.

## `cocotb.py` — role-bound execution primitives

Module docstring: "Small role-bound cocotb primitives used by the lifecycle
campaign." Everything here is a thin, lifecycle-specific layer over
`protocol/stimulus/cocotb.py`.

`class LifecycleDriveError(ProtocolDriveError)` — subclasses the protocol
domain's drive error (contrast with `protocol/stimulus/drivers/axi_lite.py`'s
`AxiLiteMemoryDriveError`, which does not subclass it).

`_command_channel(command: Mapping[str, Any]) -> dict[str, Any]` (private) —
translates a lifecycle "command" binding
(`{channel, signals: {valid, ready, payload}, metadata_fields: [{signal}, ...]}`)
into the generic `{name, direction: "input", valid, ready, fields: {payload,
...metadata_fields}}` shape `protocol/stimulus/cocotb.py`'s primitives expect.
This is the lifecycle-domain analogue of
`../../protocol/stimulus/stimulus_generator.py::_generic_ready_valid_group`'s per-channel
binding and `../../orchestration/campaign.py::_channel` — a third independent constructor of
the same informal "channel" contract (see
[`../../protocol/stimulus/README.md`](../../protocol/stimulus/README.md)).

### `drive_accepted_command(dut, clock_name, command, value, *, metadata_values=None, timeout_cycles=4096, accepted_event=None) -> int`

Validates every key in `metadata_values` is actually one of `command`'s
declared `metadata_fields`, then drives exactly one beat
(`{payload: value, **metadata_values}`) through
`protocol/stimulus/cocotb.py::drive_protocol_transfers` via `_command_channel`,
asserting exactly one beat came back accepted, and returns the accepted
payload as `int`.

**Who calls it.** The most-used lifecycle primitive: `../../orchestration/campaign.py` calls it
directly at twelve call sites (counted from the AST, by enclosing function):
`run_code_owned_operation_case` (the plain `ready_valid` path's normal per-job
command), `_run_case_with_input_stall` and its helper `_drive_command_after_edges`,
`_abort_operation_at_phase` (reset-abort-phase probe), `_probe_command_stall`
(two sites: the initial command and the concurrently held *next* command), the
illegal-command probe in `run_code_owned_verification_campaign`,
`run_code_owned_axi4_operation_case` (a full-AXI4 job's command),
`_run_axi4_operation_campaign` (its illegal-command probe),
`run_code_owned_custom_mmio_operation_case`, and — for the AXI4-Lite path — the
illegal-command and misaligned-address error probes inside
`_run_axi_lite_operation_campaign`. Note that a *normal* AXI4-Lite job's command
is not driven from any of these sites:
`../../protocol/stimulus/drivers/axi_lite.py::execute_axi_lite_memory_job` calls
this function separately (two sites, one per serving path), as a concurrent
`cocotb.start_soon` task, to accept the job-start command with the chosen
memory-base metadata while its memory-subordinate event loop simultaneously
serves bus traffic. A `control_plane_sequence` job never calls it — it has no
command channel; see `drive_control_plane_sequence` below.

### `drive_accepted_command_on_reset_release(dut, clock_name, reset_name, reset_active_value, command, value, *, metadata_values=None, asserted_cycles=2, settle_timer_ps=1, accepted_event=None) -> int`

Unlike every other driver in this domain, this one does **not** call
`drive_protocol_transfers` — it manipulates `dut` signal handles directly
because it is testing one exact timing corner: command `VALID` arriving in
the *same* sampling window as reset release. Reset assertion is offset by
`settle_timer_ps` from the preceding falling edge so the generated monitor
finishes sampling the pre-reset interface before a synchronous DUT receives
its first reset edge. It then drives
`VALID=0`/payload/metadata to `0` for `asserted_cycles`, then in the same
statement sequence sets the command payload/metadata, raises `VALID=1`, and
deasserts reset, waits `settle_timer_ps`, and immediately asserts `READY` was
already high (`if not int(ready.value): raise LifecycleDriveError(...)`) —
a one-shot check, not a retry loop, because the whole point of this function
is to prove the acceptance happens on the very first legal edge.

**Who calls it.** `../../orchestration/campaign.py::run_code_owned_operation_case` uses it
when its `command_reset_release` parameter is given. The AXI4-Lite
subcampaign also calls it directly to close simultaneous command/READY
arrival before its command-stall probes. The generic call is made from
`run_code_owned_verification_campaign`, immediately after the per-phase
reset-abort loop, specifically "to make command VALID and READY arrive
together on reset release" and prove post-abort recovery. Confirmed by
`multigent/verifier_tool/tool_regression/integration/test_lifecycle_automation.py::test_automatic_campaign_executes_a_golden_checked_simultaneous_command_job`,
which asserts the exact string
`"command_reset_release=(reset_name, int(active_value))"` appears in
`inspect.getsource(run_code_owned_verification_campaign)` and that
`"drive_accepted_command_on_reset_release"` appears in
`inspect.getsource(run_code_owned_operation_case)`.

### `drive_control_plane_sequence(dut, clock_name, control_group, sequence, actions, *, resolve_value_from, response_stall_cycles=0, protocol_probe_plan=None, timeout_cycles=262_144) -> None`

Executes one `control_plane_sequence` action list (`job_start.actions` or
`job_complete.actions`; see
[`../../pool/lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md))
over the operation's AXI4-Lite control bus. It builds a `cocotbext-axi`
`AxiLiteMaster` from `control_group`'s compiled write_address / write_data /
write_response / read_address / read_data channels (through
`protocol/stimulus/drivers/_bus_binding.py::bind_channel_bus`). The
accelerator is the *subordinate* on this bus — the opposite role from the
AXI4-Lite memory-serving driver in `protocol/stimulus/drivers/axi_lite.py`, so
that driver does not apply here. Per action:

- `write_reg` — writes `resolve_value_from(action["value_from"])` (a data
  object's base address, `low`/`high`/`whole` half chosen by the campaign) as
  one little-endian bus word.
- `write_field` — writes one full word with only the declared bit set to the
  declared value (`(value & 1) << bit`). It is a whole-register write, not a
  read-modify-write; other bits are written as 0.
- `read_reg` — one read, value ignored.
- `poll_field` — reads the register, checks the declared bit against
  `expected`, and on a mismatch waits one rising clock edge and reads again,
  up to `timeout_cycles` attempts, then raises `LifecycleDriveError`. There is
no artificial delay beyond that one edge; completion is still only known to
the granularity of a register read (the RTL is a black box here).

Anything else raises `LifecycleDriveError`. `response_stall_cycles > 0` pauses
the master's B sink (if the list contains `write_reg`/`write_field`) and/or R
sink (if it contains `read_reg`/`poll_field`), counts that many falling edges
only after the subordinate raises its response VALID, then releases READY — so
the requested hold starts only after VALID regardless of when the RTL responds;
actual stall-bin credit still comes from the runtime's observed handshake length.
A negative value
raises. `protocol_probe_plan` (from
`protocol/stimulus/stimulus_generator.py::resolved_control_plane_probe_plan`)
runs `protocol/stimulus/drivers/axi_lite_control.py::drive_axi_lite_control_probes`
after the actions (unaligned/sparse/zero-strobe/concurrent probes and any
`response_stall_lengths` in the plan), using the first `job_start` `write_reg`
with `half: low` and a `data_object` as the non-destructive pointer register;
it raises if the sequence has none. Note the gate: probes run only when
`any(protocol_probe_plan.values())` is truthy — and because
`resolved_control_plane_probe_plan` always includes a two-key
`response_stall_lengths` dict (truthy even when both tuples are empty), a plan
produced by it always passes this gate (an all-false plan then simply performs
no probe transaction).

**Who calls it.** Only
`../../orchestration/campaign.py::run_code_owned_axi4_operation_case_via_control_plane_sequence`
(three sites: `job_start`; `job_complete`, started as soon as the start
transaction completes so it runs concurrently with the AXI4 memory drivers; and
an empty-action call that carries the post-job protocol probes). Exported as
`multigent.verifier_tool.drive_control_plane_sequence`. Its event-side
counterpart is `../assertion/control_plane_sequence_tracker.py`.

### `wait_clock_cycles(dut, clock_name, cycles) -> None`

Awaits `cycles` rising edges on `clock_name`. Trivial and self-contained.

**Who calls it: nobody, currently.** Outside its own definition and the
`__init__.py`/facade re-export chain, there is no call site anywhere in this
repository — not `campaign.py`, not the generated-TB instrumentation, not any
test. It is public API surface (exported through
`multigent.verifier_tool.wait_clock_cycles`) with no current consumer; treat
it as available for `llm_extension` test code or future use, not as evidence
that generic cycle-waiting is how the automatic campaign paces itself
(it isn't — the campaign always waits on specific protocol events instead).

### `assert_lifecycle_status(dut, bindings, **expected: int) -> None`

Looks up each keyword's role name in `bindings` (must resolve to exactly one
signal), reads it off the DUT, and raises `LifecycleDriveError` with a
`role=... expected=... observed=... signal=...` message on mismatch.

**Who calls it: nobody, currently.** Same situation as `wait_clock_cycles` —
zero call sites anywhere in this repository outside the re-export chain. Do
not confuse this with how lifecycle correctness is actually checked in a
generated testbench: that is owned entirely by
`multigent/verifier_tool/lifecycle/assertion/` (`check_lifecycle_assertions`/
`finalize_lifecycle_assertions`, embedded in every generated monitor via
`orchestration/instrumentation.py`), a sibling domain folder with its own
independent implementation, not this function. `../../orchestration/campaign.py` itself waits
for status pulses with its own private `_wait_status_pulse` helper (polling
the bound signal directly against a `Timer`/edge loop), not with
`assert_lifecycle_status`.

## Cross-references

- [`../README.md`](../README.md) — the lifecycle domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — the
  automatic campaign, the production caller of `drive_accepted_command`.
- [`../../README.md`](../../README.md) — full `verifier_tool` architecture and
  the three-domain taxonomy.
- [`../../pool/lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md) —
  the Architect-selectable behaviors (`job_acceptance`, `error_style`, etc.)
  this folder reads as already-resolved metadata.
- [`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md) — the
  Lifecycle Feature Plan/catalog (`lifecycle_features.yaml`,
  `feature_plans/lifecycle.py`) that `lifecycle/assertion/` and
  `lifecycle/coverage/` build independently from the same bindings.
- [`../../protocol/stimulus/README.md`](../../protocol/stimulus/README.md) — `drive_protocol_transfers`,
  the primitive `drive_accepted_command` is built on.
- [`../../operation/stimulus/README.md`](../../operation/stimulus/README.md) — the other stimulus
  domain most often driven through the same checked job as a lifecycle
  command.
