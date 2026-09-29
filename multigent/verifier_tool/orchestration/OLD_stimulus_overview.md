# Stimulus

> **Historical snapshot.** This document describes the pre-domain-first
> directory layout. Its relative paths and package-ownership wording are not
> current integration guidance. Use [`README.md`](README.md) and the
> `protocol/`, `operation/`, and `lifecycle/` domain READMEs instead.

`stimulus/` is one of the three domain implementations described in
[`../README.md`](../README.md) — `protocol`, `lifecycle`, and `operation` are
each implemented independently under `assertion/`, `coverage/`, and here,
because assertion, coverage, and stimulus are **independent sibling
consumers** of one shared Feature Plan per domain (built in
[`../feature_plans/`](../pool/feature_plans/README.md)), not layers that call each
other. Do not describe `stimulus/operation/` as something `assertion/operation/`
or `coverage/operation/` "calls into," or vice versa — with one documented
exception (`coverage/operation/plan.py` importing
`stimulus.operation.canonical_bin_dispositions`; see
[`operation/README.md`](../operation/README.md)), each domain folder owns its own
generator/checker/sampler over the same canonical semantics.

This folder is also easy to confuse with `operation_metadata/` (singular, no
`stimulus/` prefix), which is a completely different thing: the
Architect-contract-to-canonical-metadata compiler
(`architect_metadata.py`, `canonical.py`, `arithmetic_metadata.py`,
`protocol.py`, `io_metadata.py`; see
[`../operation_metadata/README.md`](../pool/operation_metadata/README.md)).
`stimulus/operation/stimulus_generator.py` *consumes* that compiler's output
(including several of its private helpers — see
[`operation/README.md`](../operation/README.md)); it is not part of it. Wherever
this README or its siblings say "the canonical operation-metadata compiler,"
that means `operation_metadata/`, never the `operation/` domain folder
documented here.

## Directory map

```text
stimulus/
├── __init__.py     re-exports operation + protocol + lifecycle, flat
├── campaign.py     executable code-owned cocotb campaign (composition root)
├── operation/      canonical GEMM stimulus + golden-model evaluation
│   ├── __init__.py
│   └── stimulus_generator.py      see operation/README.md
├── protocol/       channel/handshake/AXI stimulus planning + cocotb drivers
│   ├── __init__.py
│   ├── stimulus_generator.py      see protocol/README.md
│   ├── cocotb.py                  see protocol/README.md
│   └── axi_lite.py                see protocol/README.md
└── lifecycle/      reset/command/job/status stimulus planning + cocotb drivers
    ├── __init__.py
    ├── stimulus_generator.py      see lifecycle/README.md
    └── cocotb.py                  see lifecycle/README.md
```

Each subfolder has its own function-level README:
[`operation/README.md`](../operation/README.md),
[`protocol/README.md`](../protocol/README.md),
[`lifecycle/README.md`](../lifecycle/README.md). This file documents `__init__.py`
and `campaign.py`, which live directly in `stimulus/`, and gives the
domain-wide picture those three don't individually cover.

## Planning vs. driving, across the whole domain

Every subfolder in this domain (and `campaign.py` itself) is one of two kinds
of code. Conflating them is the most common way to misread this domain:

| File | Touches `dut` / imports `cocotb`? | Kind |
|---|---|---|
| `operation/stimulus_generator.py` | No | Canonical-space vector generation + golden model. |
| `protocol/stimulus_generator.py` | No | Declarative interface-wide scenario/plan building. |
| `lifecycle/stimulus_generator.py` | No | Declarative reset/command/job scenario building. |
| `protocol/cocotb.py` | Yes | Generic role-bound drive/collect/reset primitives. |
| `lifecycle/cocotb.py` | Yes | Command-channel + status-read primitives, built on `protocol/cocotb.py`. |
| `protocol/axi_lite.py` | Yes | A complete AXI4-Lite memory-**subordinate** behavioral model, not a driver. |
| `campaign.py` | Yes | The composition root: the only file that actually runs a full checked simulation campaign, using the cocotb-layer primitives from all three subfolders directly. |

A structural fact worth internalizing before reading `campaign.py`:
**the plan-building functions and the campaign are not a pipeline.**
`build_protocol_stimulus_plan()` and `build_lifecycle_stimulus_plan()` are
called once each, by `assertion/instrumentation.py`, purely to *embed* their
output as literals (`CONTRACT_PROTOCOL_STIMULUS_PLAN`,
`CONTRACT_LIFECYCLE_STIMULUS_PLAN`) inside the generated testbench, for
Verifier-authored `llm_extension` code to consult. `campaign.py` never calls
either of them; it drives every channel procedurally using only the raw
`protocol/cocotb.py` and `lifecycle/cocotb.py` primitives plus its own inline
channel-shape construction. See the "Who calls it" notes in
[`protocol/README.md`](../protocol/README.md) and
[`lifecycle/README.md`](../lifecycle/README.md) for the exact evidence.

## `__init__.py`

A flat re-export of all three subpackages:

```python
from .operation import (...)   # CanonicalStimulusGenerationError, evaluate_canonical_operation, ...
from .protocol import (...)    # ProtocolDriveError, drive_protocol_transfers, ...
from .lifecycle import (...)   # LifecycleDriveError, build_lifecycle_stimulus_plan, ...
```

`multigent/verifier_tool/__init__.py` re-exports the same names again, split
back out by originating module path
(`multigent.verifier_tool.operation.stimulus`,
`.stimulus.protocol`, `.stimulus.lifecycle`, and `.stimulus.campaign`) under
its `_EXPORTS` map. Public callers (agents, orchestration nodes, generated
testbenches) should import from `multigent.verifier_tool`. Internally,
`campaign.py` imports from `multigent.verifier_tool.lifecycle.stimulus` and
`multigent.verifier_tool.protocol.stimulus` directly (sibling-package
imports within `stimulus/`, not through the top-level facade), and
`protocol/axi_lite.py` imports `drive_accepted_command` from
`multigent.verifier_tool.lifecycle.stimulus` the same way.

## Guarded by the orchestration review-hash gate

`multigent/orchestration/artifacts.py::review_definition_hashes` hashes a
fixed list of "taxonomy and monitor" source files to bind the RTL-generator's
approval gate to their exact content — if any of them changes, the previous
Verifier-TB approval is invalidated and a fresh review is required before RTL
generation or simulation can proceed. Inside `stimulus/`, only
**`operation/stimulus_generator.py`** is in that list today:

```python
sources = [
    *sorted(verifier_tool.rglob('*.yaml')),
    verifier_tool / 'coverage/runtime.py',
    verifier_tool / 'coverage/cocotb_model.py',
    verifier_tool / 'coverage/operation/plan.py',
    verifier_tool / 'coverage/operation/sampling.py',
    verifier_tool / 'assertion/protocol/generator.py',
    verifier_tool / 'assertion/operation/generator.py',
    verifier_tool / 'assertion/instrumentation.py',
    verifier_tool / 'stimulus/operation/stimulus_generator.py',
]
```

`campaign.py`, `protocol/*.py`, and `lifecycle/*.py` are **not** currently in
this hashed set, even though `campaign.py` is at least as load-bearing for
correctness. If you are merging changes on `blackhole` and this matters to
your change, check `review_definition_hashes` again rather than assuming the
guarded set is symmetric across `stimulus/`.

## `campaign.py`

Module docstring: "Executable deterministic campaign for code-owned
operation/protocol/lifecycle scope." This is the single most important file
in the `stimulus` domain: `run_code_owned_verification_campaign` is the
immutable, executable cocotb campaign the Verifier's generated testbench calls
to run every supported directed/random vector plus reset/illegal-command
lifecycle smoke, entirely without LLM involvement, for the "known" (integer
rank-2 GEMM, `ready_valid`, `axi4_lite`, or full `axi4` I/O) subset of
designs. Nothing in
this file is a plan-builder; every function either drives/collects DUT
signals itself or directly composes functions from `operation/`, `protocol/`,
and `lifecycle/` that do.

`class AutomaticCampaignError(AssertionError)` — the one exception type this
file raises; used both for "this contract cannot be automated" conditions
inside `automatic_campaign_support` (as reason strings, not exceptions) and
for genuine internal-invariant violations during a campaign run.

### `automatic_campaign_support(operation_metadata, architecture_contract=None) -> dict[str, Any]`

Reports whether an operation set has a fully automatable code-owned campaign
path — **`False` is a capability report, not a contract conflict** (see
[`../CONTRACT_REVIEWER_INTEGRATION.md`](../CONTRACT_REVIEWER_INTEGRATION.md),
where this exact function is listed as one of the Contract Reviewer's
required deterministic preflight checks). Builds a `reasons: list[str]` by
checking, per operation: any Verifier-declared `feature_extensions` concept
not in `operation_metadata.supported_code_owned_concepts` (only when
`architecture_contract` is supplied) → `"{name}:llm_extension_features=[...]"`;
`arithmetic.classifier_profile != "integer_matrix_multiply"` →
`"{name}:operation_profile_not_executable"`; any I/O binding whose
serialization `operation_metadata.io_metadata.require_supported_serialization`
rejects; a mixed or unsupported I/O profile — must be uniformly
`"ready_valid"`, or uniformly `"axi4_lite"` **or** uniformly `"axi4"` with
every binding's `memory_mapping` resolved and its `protocol_capabilities`
covering `max_outstanding`, `read_write_concurrency`, `address_bins`,
`write_strobe_bins`, `protection_bins`, `write_order_bins` (the same gate,
reused identically for both profiles); anything other than exactly one
serialized output; and anything other than exactly one command channel with
machine-readable `legal_values`. Returns `{"supported": not reasons,
"status": "supported" | "llm_extension_required", "reasons": [...]}`.
`custom_mmio` bindings still always fail this gate (`{"axi4_lite"}`/
`{"axi4"}` are the only automatable profile sets) — a capture engine exists
for it (`operation_metadata/protocol.py`) but no driving adapter does yet.

**Who calls it.** `multigent/agents/verifier.py` calls it at three points
(lines ~883, ~1554, ~2181 in that file): two are in the post-generation
test-file install path, where the result decides whether
`synthesize_code_owned_operation_coverage` should replace LLM-declared
coverpoints with code-owned ones and whether `include_automatic_campaign=True`
should be passed to `install_contract_generated_block` (see below); the third
(line ~2181) is inside `_build_task(context)`, the Verifier prompt/task-text
builder, where it gates whether a `code_owned_coverage_seed` YAML block is
rendered into the materials handed to the Verifier LLM. Directly unit-tested in
`multigent/verifier_tool/tool_regression/integration/test_lifecycle_automation.py`,
`multigent/verifier_tool/tool_regression/unit/test_canonical_operation.py`, and
`multigent/verifier_tool/tool_regression/unit/test_operation_arithmetic_metadata.py`.

### `initialize_testbench_owned_signals(dut, interface) -> None`

Drives every non-clock `direction: input` interface signal to `0`, raising
`AutomaticCampaignError` if the DUT is missing a signal the frozen interface
declares. **Who calls it.** Only `run_code_owned_verification_campaign`,
once, immediately before starting the clock and issuing the first reset —
nothing else in the campaign assumes signals are pre-initialized except
through this call having already run.

### `run_code_owned_axi_lite_operation_case(dut, interface, operation, case, *, base_variant="interior", ready_modes=None, stop_after=None, read_error_at=None, write_error_at=None, timeout_cycles=262_144) -> str | None`

Resolves the operation's one DUT-manager AXI4-Lite group via the private
`_axi_lite_group` (which calls `role_pool.standard_protocols.compile_standard_protocol_plan`
and matches on the group names referenced by the operation's bindings'
`memory_mapping.protocol_group`), then runs `protocol/axi_lite.py::execute_axi_lite_memory_job`.
Unless this is a deliberate partial probe (`stop_after`/`read_error_at`/
`write_error_at` given, in which case it returns `None` immediately), it then
waits for the completion status pulse via the private `_wait_status_pulse`
and records the checked job via the private `_record_case`, returning the new
`stimulus_id`.

**Who calls it.** Exclusively the private `_run_axi_lite_operation_campaign`
(below) — eight call sites in the source, several inside loops, covering
every reset-abort phase probe, the first post-abort recovery job, six
arrival-order/stall `ready_modes` combinations, four address-variant
(`base_variant`) jobs, every case in the
generated suite, and both read/write error-injection probes.

### `run_code_owned_operation_case(dut, clock_name, operation_metadata, case, *, output_initial_stall_cycles=None, input_ready_lead_cycles=0, command_reset_release=None, timeout_cycles=16384) -> str`

The plain `ready_valid` (non-AXI4-Lite) equivalent of the function above.
Starts a `collect_protocol_transfers` task on the single output channel, then
starts one `drive_protocol_transfers` task per input channel, each one
gated on a `cocotb.triggers.Event` (`phase_events[index]`) that only fires
once the *previous* phase's transfer is accepted — `phase_events[0]` fires
when the job's command is accepted, `phase_events[1]` when input 0's transfer
is accepted, and so on — so input channels present their first beat strictly
in declared order, one phase-acceptance apart. The command itself is driven
after the input tasks are scheduled, via plain `lifecycle.drive_accepted_command`
or — if `command_reset_release=(reset_name, active_value)` is given — via
`lifecycle.drive_accepted_command_on_reset_release`, which is what actually
fires `phase_events[0]` and lets the pre-scheduled input-0 task proceed. The
function then awaits every input task and the output collector, waits for the
completion pulse, and records the case.

**Who calls it.** Only `run_code_owned_verification_campaign` itself, at four
call sites: the post-abort recovery job (with `command_reset_release` set —
the one case exercising `drive_accepted_command_on_reset_release`), one job
with `input_ready_lead_cycles=1` (closing the "receiver exposes READY one full
cycle before VALID" arrival-order bin on every input), the main per-case loop
over the generated suite (with the first four cases getting
`output_initial_stall_cycles` fixed to `0, 1, 3, 6`), and one final recovery
job immediately after the illegal-command probe (run unconditionally with no
special arguments, to prove recovery whether the preceding error was pulsed or
required a reset to clear). The input-stall and command-stall probes below
deliberately do **not** call this function — they inline their own sequencing
because they need to interleave a delayed input/command with the rest of the
job in ways this function's fixed phase-event chain does not support.

### Internal orchestration helpers (private, load-bearing)

These are not part of the public API, but a merge into this file needs to
know they exist:

- `_axi_lite_group`, `_axi_command_metadata`, `_memory_transfer_count` —
  AXI4-Lite-specific resolution helpers feeding the two functions above.
- `_run_axi_lite_operation_campaign(dut, interface, operation, cases, *, timeout_cycles) -> int` —
  the entire AXI4-Lite sub-campaign for one operation: reset-abort probes per
  input/compute/output phase, one recovery job, six `ready_modes` combinations
  (simultaneous; valid-before-ready at 1/3/6 cycles; two mixed
  ready-before-valid/valid-before-ready combinations across address vs. data
  channels), four `base_variant` address-partition jobs, every generated
  suite case, then illegal-command and misaligned-address error probes and
  read/write response-error probes — each followed by a reset. Returns the
  count of checked jobs it completed.
- `_channel(binding) -> dict` — builds the generic `{name, direction, valid,
  ready, fields}` channel shape (see
  [`protocol/README.md`](../protocol/README.md)) from one operation I/O binding.
  Independent of, and simpler than, `protocol/stimulus_generator.py`'s
  interface-wide channel builders — this one only ever describes a single
  already-known binding.
- `_wire_value(value, dtype)` / `_logical_value(value, dtype)` — convert
  between a logical signed/unsigned Python `int` and the DUT's raw unsigned
  wire encoding, masking to `dtype["width_bits"]` and sign-extending in
  `_logical_value` when `dtype["signed"]`. `_beats` uses `_wire_value` when
  building drive beats; `_record_case` uses `_logical_value` when unpacking
  observed beats before comparison/recording.
- `_expected_elements(binding, dimensions) -> int` — product of the binding's
  bound dimension extents (or `1` for a scalar); raises
  `AutomaticCampaignError` on unresolved dimensions. A third, independent
  implementation of the same idea as `protocol/axi_lite.py::_elements` and
  `operation/stimulus_generator.py::_shape`'s size check — not shared code.
- `_beats(binding, values) -> list[dict[str, int]]` — wraps each logical value
  into a `{"payload": wire_value, "last"?: 0|1}` beat, setting `last` on the
  final beat only if the binding has a mapped `last` field.
- `_wait_active_edges(dut, clock_name, count)` — awaits `count` rising edges.
  This is campaign.py's own private edge-waiter; it does **not** reuse
  `lifecycle/cocotb.py::wait_clock_cycles` even though the two are behaviorally
  identical (see [`lifecycle/README.md`](../lifecycle/README.md) — that public
  function currently has no callers anywhere in this repository).
- `_drive_after_event`, `_drive_command_after_edges`, `_drive_binding_after_edges` —
  small "wait, then drive" wrappers used by `run_code_owned_operation_case`'s
  phase-event chain and by `_run_case_with_input_stall`/`_probe_command_stall`
  below.
- `_wait_status_pulse(dut, clock_name, status_bindings, role, *, timeout_cycles)` —
  polls the one signal bound to `status_bindings[role]` (`"completion"` or
  `"error"`) once every clock cycle via a `Timer(2, unit="ps")` +
  rising/falling-edge loop until it reads high. This is campaign.py's own
  status-wait primitive; it does not call
  `lifecycle/cocotb.py::assert_lifecycle_status` (which, per
  [`lifecycle/README.md`](../lifecycle/README.md), has no callers anywhere in
  this repository).
- `_record_case(operation, case, observed_beats) -> str` — the exact point
  where a checked job crosses from the stimulus domain into the coverage
  domain's ledger: unpacks `observed_beats` to logical values, then calls
  `multigent.verifier_tool.orchestration.runtime.record_stimulus(...)` to log the
  stimulus/expected/observed triple and obtain a `stimulus_id`, then
  `coverage.runtime.sample_operation(operation_name, {}, kind, stimulus_id)`
  to associate the operation with it. Every `run_code_owned_*_case` function
  ends by calling this.
- `_run_case_with_input_stall(dut, clock_name, operation, case, target_index, stall_cycles, *, timeout_cycles) -> str` —
  presents one specific input channel's first beat exactly `stall_cycles`
  cycles before its "natural" phase start (using `_drive_command_after_edges`
  for input `0`, `_drive_binding_after_edges` for later inputs), then drives
  the rest of the job normally and golden-checks it. Called from
  `run_code_owned_verification_campaign` for every input index times `stall_cycles
  in (1, 3, 6)`.
- `_abort_operation_at_phase(dut, interface, operation, case, phase, *, timeout_cycles)` —
  the actual reset-abort-at-every-phase implementation (`"idle"`,
  `"input_<name>"` per input, `"compute"`, `"output"`), independent of (and
  not driven by) `lifecycle/stimulus_generator.py::build_lifecycle_stimulus_plan`'s
  `reset_abort` scenario list — see
  [`lifecycle/README.md`](../lifecycle/README.md) for why those two do not feed
  each other.
- `_probe_command_stall(dut, interface, operation, case, stall_cycles, *, timeout_cycles) -> str` —
  golden-checks a job while a *second* command is concurrently held pending
  and only accepted `stall_cycles - 1` edges after the job's second-to-last
  output beat, then confirms via `_wait_status_pulse` that the completion
  pulse (and this function's golden comparison) happens strictly before that
  held next command is actually accepted. The docstring/comment is explicit
  that "the protocol perturbation is part of the functional test," not
  incidental timing noise.
- `_collect_after_edges(dut, clock_name, binding, edges, *, timeout_cycles)` —
  waits `edges` cycles then collects exactly one more beat; used only by
  `_probe_command_stall`.

### `run_code_owned_verification_campaign(dut, interface, operation_metadata, lifecycle_plan, *, randomized_count, seed=0, clock_period_ns=10, timeout_cycles=16384) -> dict[str, Any]`

The top-level orchestrator, and the only function in this file meant to be
called as a `cocotb.test`. Docstring: "Run every supported base-operation
vector plus reset/illegal lifecycle smoke. The campaign is intentionally
independent of Verifier-authored test logic. Unknown operation profiles
remain explicit LLM extensions; they are never approximated." Sequence:
`initialize_testbench_owned_signals`, start the clock
(`cocotb.clock.Clock(..., clock_period_ns, unit="ns")`), one initial
`drive_protocol_reset`, then for every operation whose
`arithmetic.classifier_profile != "llm_extension"`:

1. `generate_canonical_stimulus_suite(operation, randomized_count=randomized_count,
   seed=seed)` — see [`operation/README.md`](../operation/README.md) — and hard-fail
   (`AutomaticCampaignError`) on any suite exception whose `code` is not
   `"unreachable"`.
2. Dispatch on I/O profile: if uniformly `axi4_lite`, delegate the entire
   operation to `_run_axi_lite_operation_campaign`; if uniformly `axi4`,
   delegate to `_run_axi4_operation_campaign` (narrower than the AXI4-Lite
   path -- see `protocol/README.md`'s `axi4_outstanding.py` section for the
   acknowledged gap). Otherwise (plain `ready_valid`): run one
   `_abort_operation_at_phase` probe per phase, one
   `run_code_owned_operation_case` with `command_reset_release` set (recovery
   + simultaneous command/reset-release proof), one with
   `input_ready_lead_cycles=1`, then `_run_case_with_input_stall` for every
   input index times `stall_cycles in (1, 3, 6)`, then every case in
   `[*directed, *qualification, *randomized]` via `run_code_owned_operation_case`
   (the first four getting fixed `output_initial_stall_cycles` of `0, 1, 3,
   6`), then — only if the command channel declares an `illegal_value` — one
   illegal-command probe (resetting first only if
   `operation["lifecycle"]["policy"]["error_style"] ==
   "sticky_until_reset"`) followed by one recovery job, then three
   `_probe_command_stall` runs at `stall_cycles in (1, 3, 6)`.

Returns `{"completed_checked_jobs": completed, "randomized_count":
randomized_count}`; a `finally` block always cancels the clock task.

**Who calls it.** Not called directly anywhere in this repository — it is
reached exclusively through the generated testbench.
`multigent/verifier_tool/assertion/instrumentation.py::render_contract_generated_block`
imports it aliased `_contract_run_code_owned_verification_campaign` and, only
when its own `include_automatic_campaign` parameter is `True`, emits a
`@cocotb.test`-decorated wrapper, `_contract_automatic_verification_campaign(dut)`,
that awaits it with the embedded `CONTRACT_PROTOCOL_STIMULUS_PLAN['interface_contract']`,
`CONTRACT_OPERATION_METADATA`, and `CONTRACT_LIFECYCLE_STIMULUS_PLAN` literals.
`include_automatic_campaign` is set by
`multigent/agents/verifier.py` (`install_contract_generated_block(...,
include_automatic_campaign=(automatic_campaign_supported and index == 0), ...)`)
— note **only the first generated test file** (`index == 0`) ever gets the
automatic-campaign test embedded, even when a verification attempt produces
multiple test files. `randomized_transactions_minimum` (→ this function's
`randomized_count`) is threaded from
`context["verification_policy"]["randomized_transactions_minimum"]` in the
same agent code. Directly introspected (via `inspect.getsource`, not executed)
by `multigent/verifier_tool/tool_regression/integration/test_lifecycle_automation.py`, and exercised end-to-end
through `render_contract_generated_block(...,
include_automatic_campaign=True, ...)` plus `compile(source, ..., "exec")`
in both `test_lifecycle_automation.py` and `test_canonical_operation.py` to
prove the generated block is syntactically valid and wires the campaign in
exactly once.

## Cross-references

- [`../README.md`](../README.md) — full `verifier_tool` architecture, the
  three-domain taxonomy, the facade pattern, and the code-owned/LLM-owned
  boundary.
- [`../feature_plans/README.md`](../pool/feature_plans/README.md) — the per-domain
  Feature Plan catalogs and matchers (`protocol_features.yaml`,
  `lifecycle_features.yaml`, `operation_features.yaml`) that every
  `build_*_stimulus_plan`/`build_*_feature_plan` function in this domain
  compiles from.
- [`../operation_metadata/README.md`](../pool/operation_metadata/README.md) — the
  canonical operation-metadata compiler (`canonical.py`,
  `architect_metadata.py`, `arithmetic_metadata.py`, `io_metadata.py`) that
  `operation/stimulus_generator.py` and `campaign.py` both consume.
- [`../lifecycle_policy_pool/README.md`](../pool/lifecycle_policy_pool/README.md) —
  the Architect-selectable lifecycle behaviors (`error_style`, etc.) that
  both `lifecycle/stimulus_generator.py` and `campaign.py` read as resolved
  metadata.
- [`../CONTRACT_REVIEWER_INTEGRATION.md`](../CONTRACT_REVIEWER_INTEGRATION.md) —
  documents `automatic_campaign_support` and `build_lifecycle_stimulus_plan`
  as required Contract Reviewer deterministic preflight checks, and the
  "capability report, not a contract conflict" distinction for a `False`
  result.
- [`operation/README.md`](../operation/README.md),
  [`protocol/README.md`](../protocol/README.md),
  [`lifecycle/README.md`](../lifecycle/README.md) — the three subfolders this
  file summarizes and composes.
