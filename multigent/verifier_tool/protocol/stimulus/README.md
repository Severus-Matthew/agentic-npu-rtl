# Stimulus — Protocol Domain

This is the `protocol` leg of the three-domain stimulus taxonomy described in
[`../README.md`](../README.md) and [`../../README.md`](../../README.md). It
covers channel/handshake/bus-level traffic: generic role-bound ready/valid
channels plus the standard AXI4, AXI4-Lite, and AXI4-Stream profiles. It is a
sibling of `protocol/assertion/` and `protocol/coverage/`, not a dependency of
either — all three independently consume the Protocol Feature Plan built by
`build_protocol_feature_plan()` (see
[`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md)).

This folder contains two clearly different kinds of code, and the task of
documenting it is mostly the task of keeping them apart:

| File/folder | Touches `dut`? | Kind |
|---|---|---|
| `stimulus_generator.py` | No | Builds a declarative scenario/plan data structure from a frozen interface contract. Pure Python, no `cocotb` import. |
| `cocotb.py` | Yes | Generic, protocol-agnostic cocotb primitives that toggle exact bound signals on an actual `dut` handle. |
| `memory/` | No | The **memory** layer of the memory/adapter/driver split: a thin re-export of the `cocotbext-axi` dependency's plain `Memory` class — raw byte-addressable storage, nothing else. |
| `adapter/` | No | The **adapter** layer: `OperationMemoryAdapter` — operation-contract-aware address windows and canonical-value word packing/unpacking, built on `memory/`. No `cocotb` import — pure, synchronous Python, shared by every driver below. |
| `drivers/` | Yes | The **driver** layer: `axi_lite.py` (AXI4-Lite memory subordinate), `axi4_outstanding.py` (full AXI4, multi-outstanding, out-of-order), `custom_mmio.py` (LLM-declared memory-like custom protocol, both directions, reusing the shared completion scheduler unmodified), and `axi_lite_control.py` (non-destructive register probes on an AXI4-Lite *control* subordinate) — built on `cocotbext-axi`'s primitives and consuming `adapter/` for everything address/object-related. Shared helpers: `_bus_binding.py`, `_completion_scheduler.py`. |

`build_protocol_stimulus_plan` never touches a `dut`; `drive_protocol_transfers`
and `collect_protocol_transfers` never look at a feature catalog or a YAML
file. Nothing in `stimulus_generator.py` calls anything in `cocotb.py`, and
`../../orchestration/campaign.py` (the one thing that actually runs a
simulation) does not call `build_protocol_stimulus_plan` at all — see the
note at the end of the `stimulus_generator.py` section below.

For multi-port AXI4/control-plane jobs, `resolved_operation_transport_variants`
compiles the required protocol feature plan into reusable timing and address
parameters (a list of `{stall_cycles, simultaneous, tail_beats}` dicts, some
with an extra key): first-transfer stalls, simultaneous presentation,
short-burst page splits (`tail_beats` 1 or 8, only when the matching
`axi4_burst_length` bins are required), a delayed-W variant
(`write_data_stall_cycles: 8`) when an `address_first` write-order bin is
required, and a `write_address_one_cycle_probe: True` variant when a required
`one_cycle_stall` bin exists on a full-AXI4 manager write-address channel. Only
`orchestration/campaign.py::_run_axi4_control_plane_operation_campaign` calls it
today; it passes those parameters to `execute_axi4_memory_job` (READY stalls,
simultaneous first transfer, the one-cycle write-address probe,
`aligned_tail_beats` bases) and to
`drive_control_plane_sequence` (`response_stall_cycles`, applied to the AXI4-Lite
master's response sinks). It does not duplicate any handshake implementation.
`execute_axi4_memory_job` waits for the final B handshake before disposing the
per-job channel objects, and cancels their cocotbext-axi `_run` tasks. Without
that cleanup, an old job's sink continued driving READY during later jobs,
which made the stall waveform and coverage nondeterministic. Completion-pulse
observation is armed before the final B response because a one-cycle pulse may
coincide with that handshake.
The shared address-base helper accepts `aligned_tail_beats`; it derives the
offset from each object's word count and bus width. This preserves the logical
tensor while forcing an AXI4 burst converter to exercise legal 4-KiB splitting
and short bursts;
coverage is still sampled from accepted RTL addresses, not from the planned
variant label.

`resolved_control_plane_probe_plan` selects required AXI4-Lite address,
strobe, and read/write-concurrency cases from the same resolved coverage plan;
it returns booleans (`unaligned_write`, `unaligned_read`, `sparse_strobe`,
`zero_strobe`, `concurrent_read_write`, `multiple_outstanding`) plus a
`response_stall_lengths` mapping (`write_response` / `read_data` → the subset of
`(1, 8)` cycles whose `one_cycle_stall` / `long_stall` bin is required on that
control-bus response channel).
`drivers/axi_lite_control.py` executes them through the existing AXI4-Lite
master after job completion; each requested response stall holds the master's
B or R sink not-ready, issues a pointer-register write (WSTRB=0) or read, waits
for the response VALID, holds that many further cycles, then releases READY. Its pointer-register probe is non-destructive:
partial writes repeat the existing byte, zero-strobe writes have no effect,
and concurrent reads/writes use the declared pointer address. No HLS signal
name or fixed address is embedded in this driver. The planner does not assume
that arbitrary unmapped addresses are safe.

## Files

- `__init__.py` — re-exports the public names below.
- `stimulus_generator.py` — declarative scenario planning.
- `cocotb.py` — generic role-bound cocotb drivers/collectors.
- `memory/` — thin re-export of `cocotbext.axi.memory.Memory`.
- `adapter/operation_memory_adapter.py` — `OperationMemoryAdapter`, `build_address_windows`, `find_window_mapping`, `pack_words`/`unpack_words`.
- `drivers/axi_lite.py` — the AXI4-Lite memory-subordinate model.
- `drivers/axi4_outstanding.py` — the full-AXI4 out-of-order memory-subordinate model (also serves one single-capability read-only or write-only manager port, see below).
- `drivers/custom_mmio.py` — the LLM-declared custom memory-like protocol driver, both directions.
- `drivers/axi_lite_control.py` — `drive_axi_lite_control_probes`, non-destructive AXI4-Lite control-bus probes (see the `resolved_control_plane_probe_plan` paragraph above); not re-exported from `drivers/__init__.py`.
- `drivers/_bus_binding.py` — shared `cocotbext-axi` `Bus` construction (`bind_signal_bus`, `bind_channel_bus`), used by the AXI drivers and custom_mmio.
- `drivers/_completion_scheduler.py` — the protocol-neutral `RandomCompletionScheduler`.

## `__init__.py`

Re-exports `ProtocolStimulusGenerationError`, `build_protocol_stimulus_plan`,
`generate_random_protocol_scenarios` (from `stimulus_generator.py`);
`ProtocolDriveError`, `collect_protocol_field_values`,
`collect_protocol_transfers`, `drive_protocol_field_values`,
`drive_protocol_reset`, `drive_protocol_transfers` (from `cocotb.py`); and
`AxiLiteMemoryDriveError`, `default_axi_lite_memory_bases`,
`execute_axi_lite_memory_job`, the full-AXI4/custom-MMIO driver symbols
(`Axi4OutstandingDriveError`, `CustomMmioDriveError`, `execute_axi4_memory_job`,
`execute_custom_mmio_read_job`/`execute_custom_mmio_write_job`,
`RandomCompletionScheduler`), `resolved_control_plane_probe_plan` and
`resolved_operation_transport_variants` (from `stimulus_generator.py`), the
shared memory adapter (`OperationMemoryAdapter`, `OperationMemoryAdapterError`),
and `Memory`. `multigent/verifier_tool/__init__.py`
re-exports the supported public surface. Public callers should import from
`multigent.verifier_tool`; the exceptions inside this codebase are
`../../orchestration/campaign.py` and `lifecycle/stimulus/cocotb.py`, which import straight
from `multigent.verifier_tool.protocol.stimulus` (and, for `axi_lite.py`,
`multigent.verifier_tool.lifecycle.stimulus` imports `drive_accepted_command`
from lifecycle *into* `axi_lite.py` — a rare case of `protocol/` depending on
`lifecycle/` within this same `stimulus` package, needed because driving an
AXI4-Lite job-accept command is a lifecycle-owned action even though it has to
run concurrently with protocol-owned bus traffic).

## `stimulus_generator.py` — planning only, no DUT

Module docstring: "Generate legal, role-bound protocol scenarios without
interpreting names." Everything here reads a frozen `interface` contract (or
the coverage-domain-resolved `interface_plan`/`coverage_plan` derived from it)
and a small YAML-backed scenario catalog, and returns nested dictionaries. No
`cocotb` import anywhere in this file.

`class ProtocolStimulusGenerationError(ValueError)` — raised whenever the
frozen interface cannot produce a safe standard-protocol stimulus (e.g. an
unbound `valid`/`ready` pair, a role mapped more than once, a negative
`count`).

### `build_protocol_stimulus_plan(interface: Mapping[str, Any]) -> dict[str, Any]`

The main entry point. Calls
`protocol.coverage.plan.build_interface_coverage_plan(interface)` to resolve
role bindings (a coverage-domain function reused here purely as the shared
upstream binding resolver, not for its obligation/sampling logic), then
`build_protocol_feature_plan(coverage_plan)` and
`compile_stimulus_feature_plan(feature_plan)` to pull the declarative stimulus
branch out of the resolved Protocol Feature Plan. For every standard group in
`coverage_plan["standard_protocol_plan"]["groups"]` it dispatches on
`group["profile"]` to one of `_axi4_scenarios`, `_axi_lite_scenarios`, or
`_axis_scenarios` (below), then separately compiles one `_generic_ready_valid_group`
for any interface channel declared `protocol_profile: ready_valid` that isn't
part of a standard group, plus one `reset_sequence` scenario per
`reset_behavior` obligation in the coverage plan. Returns:

```python
{
    "schema_version": 2,
    "source": "verifier_tool role-bound protocol stimulus generator",
    "feature_plan": {...},           # the resolved Protocol Feature Plan
    "compiled_stimulus": {...},      # compile_stimulus_feature_plan(feature_plan)
    "interface_contract": {...},     # the frozen interface, verbatim
    "global_scenarios": [...],       # reset sequences
    "groups": [
        {"name", "profile", "endpoint_role", "channels", "scenarios": [...]},
        ...
    ],
    "execution_contract": [...],     # prose invariants any driver must uphold
}
```

**Who calls it.** `multigent/verifier_tool/orchestration/instrumentation.py`
imports it directly (`from multigent.verifier_tool.protocol.stimulus import
build_protocol_stimulus_plan`) and calls it once per generated testbench, at
*generation* time (not simulation time), to embed its return value verbatim as
the `CONTRACT_PROTOCOL_STIMULUS_PLAN` literal in the generated code-owned
block. That block exposes two thin accessor wrappers over the embedded
literal, `_contract_protocol_scenarios(protocol_group=None)` and
`_contract_protocol_channel(protocol_group, protocol_channel)`, which is how
Verifier-authored `llm_extension` test code is meant to read scenarios and
exact channel bindings out of it. **`../../orchestration/campaign.py` does not call this
function at all** — the automatic code-owned campaign drives every operand and
command channel procedurally, using only the raw primitives in `cocotb.py`
below plus its own inline channel-shape construction
(`campaign.py::_channel`), never by replaying entries from this plan's
`groups[*]["scenarios"]`. The rich scenario catalog built here therefore exists
for the generated TB's Verifier-authored extension code and for direct
inspection/testing, not for the immutable campaign. Also called directly by
`multigent/tests/test_standard_axi_protocols.py` and
`multigent/tests/test_feature_plans.py`.

### `generate_random_protocol_scenarios(interface, count, *, seed=0) -> list[dict[str, Any]]`

Builds on `build_protocol_stimulus_plan(interface)` and, per group, generates
`count` reproducible (`random.Random(seed)`) legal traffic parameter sets —
AXI4 gets random burst type/size/length/address (4-KiB-safe for `INCR`),
AXI4-Lite gets random address/data/strobe-pattern/order, AXI4-Stream gets
random beat count/partial-last/stall positions — plus a random
`stall_cycles`. Returns `{id, kind: f"{profile}_random", protocol_group,
parameters}` per generated case; does not evaluate or classify anything (there
is no golden model at the protocol layer — correctness here is "legal
per the standard," not "produces a specific value").

**Who calls it.** No non-test caller exists in this repository outside the
re-export chain. Used directly by `multigent/tests/test_standard_axi_protocols.py`.
It is not embedded into the generated TB block (`orchestration/instrumentation.py`
does not import it) and `../../orchestration/campaign.py` does not call it either — the
campaign's own randomized coverage comes from
`operation/stimulus/stimulus_generator.py::generate_random_canonical_stimuli` instead, which
randomizes canonical operand *values*, not protocol-level timing/addressing.

### Private scenario builders (load-bearing, but not part of the public API)

These are the functions `build_protocol_stimulus_plan` dispatches to; they are
worth knowing about because they are where the exact directed test vectors
live, but nothing outside this file calls them directly.

- `_targets(plan, *, group, templates) -> list[str]` — collects coverage
  obligation IDs whose `template` is in `templates` and whose scope matches
  `group`, so every generated scenario can carry an accurate
  `coverage_targets` list back to the coverage domain's obligation IDs.
- `_common_channel_scenarios(group, plan)` — for every channel in a standard
  group, reads the shared `handshake_states` / `handshake_arrival_order` /
  `stall_stability` scenario templates out of the Protocol Feature Catalog
  (`load_protocol_feature_catalog()`) and instantiates one `channel_schedule`
  scenario per declared `{name, schedule}` pair, skipping arrival-order/stall
  schedules on channels with no `ready` signal (they cannot be scheduled).
  This is shared by all standard profiles below, including custom MMIO.
- `_axi_address_cases(group, channel_kind) -> list[dict]` — a fixed table of
  eleven literal `{addr, len, size, burst}` tuples per address channel: narrow
  vs. full transfer size, `FIXED`/`INCR`/`WRAP` bursts, max burst length,
  unaligned start address, and one address chosen so the burst ends exactly at
  a 4-KiB boundary. Read the source for the exact literals; do not
  re-derive them from prose.
- `_axi4_scenarios(group, plan)` — `_common_channel_scenarios` plus one
  `axi4_transaction` per `_axi_address_cases` entry on each address channel
  (write strobe variants `full`/`sparse`/`all_zero` on writes), three
  `axi4_write_channel_order` cases (`address_first`/`data_first`/`same_cycle`),
  and `axi4_outstanding` cases for repeated-ID and (if an `id` field exists)
  distinct-ID outstanding requests.
- `_axi_lite_scenarios(group, plan)` — three write orders times three strobe
  patterns; if both address channels exist, three read/write concurrency
  modes, five address partitions per channel (`zero`/`aligned`/`unaligned`/
  `page_edge_low`/`page_edge_high`, plus `prot` values `[0, 1, 7]` when a
  `prot` field is bound), and one multi-outstanding read+write case.
- `_axis_scenarios(group, plan)` — full/partial-`KEEP` packets, and (only if
  the stream has a `ready` signal) stall-first/middle/last/long-stall
  variants, sideband ID/DEST/USER value pairs, and back-to-back packet
  spacing (`no_gap`/`with_gap`) when `last` is bound.
- A `custom_mmio` group uses `_common_channel_scenarios` only. The declarative
  planner must not treat it as AXI4-Stream or invent packet fields; operation
  jobs use the separate custom-MMIO memory driver. Unknown standard profile
  dispatch fails explicitly. Random custom-MMIO scenarios likewise use only
  generic handshake timing parameters, not AXI-Stream packet lengths.
- `_generic_ready_valid_group(interface, plan) -> dict | None` — compiles
  every interface channel declared `protocol_profile: ready_valid` (i.e. not a
  standard AXI variant) into the same `{name, profile: "ready_valid",
  endpoint_role: "mixed", channels: {...}, scenarios: [...]}` shape as a
  standard group, requiring exactly one `valid` and one `ready` role per
  channel. **This is independent of `../../orchestration/campaign.py::_channel`**, which builds
  the same conceptual "one bound channel" shape directly from one operation's
  I/O binding at campaign run time rather than from the whole interface's
  declared channels — the two constructors exist for different callers
  (interface-wide scenario catalog vs. one operation's binding at simulation
  time) and are not meant to be unified, but both must keep producing a shape
  `cocotb.py`'s primitives accept (see below).

## `cocotb.py` — generic role-bound execution primitives

Module docstring: "The primitives deliberately know only the machine-readable
binding. Protocol groups decide which side the testbench owns;
operation-specific sequencing stays outside this module." Every function here
takes a `channel: Mapping[str, Any]` argument shaped
`{"direction": "input"|"output", "valid": signal_name, "ready":
signal_name|None|"", "fields": {field_name: signal_name}, "name"?: str}`. This
exact shape recurs, independently constructed, in at least four places in this
domain: `_common_channel_scenarios`/`_generic_ready_valid_group` above,
`../../orchestration/campaign.py::_channel`, and `lifecycle/stimulus/cocotb.py::_command_channel`
— there is no shared constructor function, only a shared informal contract.

`class ProtocolDriveError(AssertionError)` — the base drive-time error for
this module. `lifecycle/stimulus/cocotb.py`'s `LifecycleDriveError` subclasses
it directly. `axi_lite.py`'s `AxiLiteMemoryDriveError` plays an equivalent
role for AXI4-Lite memory jobs but does **not** subclass it — see `axi_lite.py`
below — it subclasses `AssertionError` directly instead, so `except
ProtocolDriveError` will not catch an `AxiLiteMemoryDriveError`.

### `drive_protocol_transfers(dut, clock_name, channel, beats, *, timeout_cycles=4096, settle_timer_ps=1, accepted_event=None) -> list[dict[str, int]]`

Acts as the channel **source** (requires `channel["direction"] == "input"`
relative to the DUT). For each beat: waits for a falling edge, drives every
mapped field plus `VALID=1` on the first attempt only, waits `settle_timer_ps`
for combinational settling, samples `READY` in that stable pre-active-edge
window, advances to the rising edge, and either records the beat as accepted
(if `READY` was high) or repeats (holding the same values — never re-drives
already-stable fields) until `timeout_cycles` is exhausted. After the last
beat, if `accepted_event` is given it is `.set()` **before** the trailing
`FallingEdge`, specifically so a coroutine waiting on that event can drive its
own first beat on the very next falling edge and create a true simultaneous
`VALID`/`READY` arrival on a downstream channel with no spurious one-cycle
gap. Deasserts `VALID` and clears fields on exit.

**Who calls it.** By far the most heavily used primitive in the whole
`stimulus` domain: `../../orchestration/campaign.py` calls it directly at eleven call sites —
driving each GEMM operand channel in its normal phase order
(`run_code_owned_operation_case`'s `_drive_after_event`), presenting inputs up
to a reset-abort phase (`_abort_operation_at_phase`), the delayed/early-phase
input drives in the input-stall probe (`_run_case_with_input_stall`,
`_drive_binding_after_edges`), and the input drives in the command-stall probe
(`_probe_command_stall`) — and indirectly through
`lifecycle/stimulus/cocotb.py::drive_accepted_command` (command channels,
including every AXI4-Lite job's command, are just another
`drive_protocol_transfers` call with a one-beat payload). Embedded in the
generated TB aliased `_contract_drive_protocol_transfers`. Directly
unit-tested (via monkeypatch, no simulator) in
`multigent/tests/test_standard_axi_protocols.py`.

### `drive_protocol_field_values(dut, clock_name, channel, field, values, *, timeout_cycles=4096, settle_timer_ps=1) -> list[int]`

A single-field convenience wrapper: packs each scalar in `values` into a
one-field beat, delegates entirely to `drive_protocol_transfers`, and unpacks
the one named field back out of each accepted beat.

**Who calls it.** Embedded in the generated TB aliased
`_contract_drive_protocol_field_values`; not called anywhere else in this
repository outside tests. `multigent/tests/test_standard_axi_protocols.py::test_logical_field_transfer_wrappers_own_beat_packing_and_unpacking`
verifies the pack/unpack behavior by monkeypatching `drive_protocol_transfers`
itself, without cocotb or a simulator.

### `collect_protocol_transfers(dut, clock_name, channel, *, count=None, until_last=False, ready_pattern=(1,), initial_valid_stall_cycles=None, timeout_cycles=4096, settle_timer_ps=1) -> list[dict[str, int]]`

Acts as the channel **sink** (requires `channel["direction"] == "output"`).
Completion needs either a `count` or `until_last=True` (a mapped `last`
field). Drives `READY` from `ready_pattern` (cycled) unless
`initial_valid_stall_cycles` is given, in which case `READY` is held low until
the first `VALID` is actually observed and then held low for exactly that
many further cycles before going high — this is what produces an exact,
reproducible first-beat stall length (0 = simultaneous arrival) independent of
whatever cycle `VALID` happens to first assert on. Samples all mapped fields
in the same pre-edge window it samples `VALID`, and only records a beat when
both `VALID` and `READY` were high going into the active edge.

**Who calls it.** Called directly by `../../orchestration/campaign.py` at five call sites: the
main output-channel collector in `run_code_owned_operation_case`, the
equivalent collector in the input-stall variant
(`_run_case_with_input_stall`), the reset-abort output-phase probe
(`_abort_operation_at_phase`), and two sites inside the command-stall probe
(`_probe_command_stall`'s own prefix collector, plus the final-beat collector
inside its private helper `_collect_after_edges`). Embedded in the generated
TB aliased `_contract_collect_protocol_transfers`.
Directly unit-tested (via monkeypatch) in
`multigent/tests/test_standard_axi_protocols.py`.

### `collect_protocol_field_values(dut, clock_name, channel, field, *, count=None, until_last=False, ready_pattern=(1,), initial_valid_stall_cycles=None, timeout_cycles=4096, settle_timer_ps=1) -> list[int]`

The sink-side mirror of `drive_protocol_field_values`: delegates to
`collect_protocol_transfers` and unpacks one named field.

**Who calls it.** Embedded in the generated TB aliased
`_contract_collect_protocol_field_values`; otherwise only exercised by
`multigent/tests/test_standard_axi_protocols.py` (monkeypatched, no
simulator).

### `drive_protocol_reset(dut, clock_name, reset_name, active_value, *, asserted_cycles=2) -> None`

Asserts `reset_name = active_value` one picosecond after a falling edge, holds
it across `asserted_cycles` active rising edges, then deasserts. The small
offset lets the generated falling-edge monitor finish observing the pre-reset
state before reset becomes active; a synchronous DUT then gets its first legal
reset edge before any full-interface snapshot is checked as reset-active.
The helper does not touch any other signal — clearing `VALID`/state on other
channels is each caller's responsibility (see
`../../orchestration/campaign.py::initialize_testbench_owned_signals` for the
pre-reset defaulting step that makes this safe).

**Who calls it.** `../../orchestration/campaign.py` calls it at twenty-nine call
sites (AST count): in `_run_axi4_operation_campaign`,
`_run_custom_mmio_operation_campaign`, `_run_axi_lite_operation_campaign`,
`_abort_operation_at_phase`, `_probe_command_stall`, and
`run_code_owned_verification_campaign` — before each abort/error probe, between
jobs, and after each illegal-command/error probe — with `asserted_cycles=2`,
except `_run_axi4_control_plane_operation_campaign`, which uses
`asserted_cycles=5` followed by five extra rising edges (HLS-style register
control and the cocotbext AXI4-Lite master need several sampled edges after
reset release before the first register write). Embedded in the generated TB
aliased `_contract_drive_protocol_reset`.

## `drivers/axi_lite.py` — a full AXI4-Lite memory-subordinate model

Module docstring: "Executable AXI4-Lite memory-subordinate model for
code-owned operations." This file **behaves like a piece of hardware** (an
AXI4-Lite memory) for the duration of one job, reacting to whatever
address/data/order the DUT (the AXI4-Lite *manager* in this relationship)
actually issues. It now has **two serving paths**, chosen automatically per
job by `execute_axi_lite_memory_job` (see below):

1. **The default path, `_serve_via_cocotbext_axi`** — used whenever
   `ready_modes` is unset or trivial (every case except one specific
   coverage sweep). Composes `cocotbext-axi`'s own `AxiLiteSlaveWrite`/
   `AxiLiteSlaveRead` (WSTRB splitting, address alignment, RRESP/BRESP
   construction, VALID/READY queueing are all the library's, not
   hand-rolled) with `_FaultInjectingTarget` — a thin wrapper around
   `adapter.OperationMemoryAdapter` that raises on the Nth read/write to
   trigger the library's own already-correct SLVERR construction, and
   records every accepted write in order (`output_beats`). `stop_after` is
   implemented by counting real `RVALID`/`BVALID` wire events (never
   `target.read`/`write` call counts — those fire on *acceptance*, a cycle
   or more before the response reaches the wire), holding the accepted
   response through the following quiet falling edge, and only then killing the
   library's internal `_process_write_cr`/`_process_read_cr` coroutines
   (undocumented but the only handle available) plus forcing VALID/READY
   signals low for a clean job boundary.
2. **The hand-rolled fallback** — the original manual cycle-by-cycle loop,
   used only when a genuinely custom `ready_modes` is given. Its exact
   per-cycle `_ReadyPolicy` timing was proven correct long before the
   library path existed, and retargeting it onto the library's `.pause`
   property was judged not worth the risk of subtly breaking
   `../../orchestration/campaign.py`'s ready-mode coverage sweep without a
   way to verify cycle-exact equivalence here — see the code comment at the
   branch point for the exact reasoning.

Both paths share the same setup (bases, `OperationMemoryAdapter.load`,
command validation) and the same public contract.

`class AxiLiteMemoryDriveError(AssertionError)` — note this does **not**
subclass `ProtocolDriveError` (unlike `LifecycleDriveError`), even though it
plays an equivalent role for this file.

### `default_axi_lite_memory_bases(operation, *, variant="interior", aligned_tail_beats=None) -> dict[str, int]`

Assigns each input/output object one of four fixed 64-KiB-aligned base
addresses (`0x0001_0000`, `0x0002_0000`, `0x0003_0000`, `0x0004_0000`, in
input-then-output order), then applies a named override: `"read_zero"` /
`"write_zero"` move the first input's / first output's base to address `0`;
`"read_page_edge"` / `"write_page_edge"` calculate the base from the
contract's word count, stride, and bus width so the **last transferred byte**
ends at `...FFF`. A fixed `0x0000_0F00` base only worked for a 64-word object
and did not hit this bin for smaller tensors. A layout that cannot fit or
align at the page edge raises. Any other `variant` raises.

**Who calls it.** `../../orchestration/campaign.py::_axi_command_metadata` calls it once per
AXI4-Lite job to build the `{base_signal_name: base_address}` metadata passed
to `drive_accepted_command`, and `execute_axi_lite_memory_job` (below) calls
it again internally with the same `base_variant`. `../../orchestration/campaign.py` sweeps all
five variants (`interior`, `read_zero`, `write_zero`, `read_page_edge`,
`write_page_edge`) as separate checked jobs specifically to close AXI4-Lite
address-partition coverage bins.

### `execute_axi_lite_memory_job(dut, clock_name, group, operation, case, *, base_variant="interior", ready_modes=None, stop_after=None, read_error_at=None, write_error_at=None, timeout_cycles=262_144) -> list[dict[str, int]]`

Serves one complete memory job for a DUT that is the AXI4-Lite **manager**
(`_group_channels` requires `group["profile"] == "axi4_lite"` and
`group["endpoint_role"] == "manager"`, and that all five channels —
`write_address`, `write_data`, `write_response`, `read_address`, `read_data`
— are present). Builds an `adapter.OperationMemoryAdapter` from the case's
canonical input stimulus, then branches on whether `ready_modes` is trivial:

- **Default (`_serve_via_cocotbext_axi`)** — composes `cocotbext-axi`'s own
  `AxiLiteSlaveWrite`/`AxiLiteSlaveRead` (bound via `_bus_binding.bind_channel_bus`,
  the same helper `axi4_outstanding.py` uses) with `_FaultInjectingTarget`, a
  thin wrapper around the adapter that (a) enforces full-width writes, (b)
  raises on the `read_error_at`/`write_error_at`-th call so the library's own
  try/except-driven RRESP/BRESP construction produces SLVERR without any
  reimplementation of that logic here, and (c) records every accepted write
  in order as `output_beats`. `stop_after` and normal completion are both
  detected by counting real `RVALID`/`RREADY` and `BVALID`/`BREADY` wire
  events directly (never `target.read`/`write` call counts, which fire on
  *acceptance* rather than when the response reaches the wire — a real bug
  caught while building this). Teardown happens on the following quiet falling
  edge before the library's internal
  `_process_write_cr`/`_process_read_cr` coroutines are killed and
  VALID/READY forced low for a clean job boundary before the next job binds
  fresh models to the same signals.
- **Fallback (the original hand-rolled loop)** — used only when a genuinely
  custom `ready_modes` is given (`../../orchestration/campaign.py`'s one
  ready-mode-timing coverage sweep). Every falling edge: computes
  `AWREADY`/`WREADY`/`ARREADY` from three independent `_ReadyPolicy`
  instances (`ready_before_valid` by default, or `simultaneous`/
  `valid_before_ready` with a configurable stall count) — **only the first
  transfer on each channel is subject to the configured policy**; presents
  queued read/write responses ready-before-valid on the response side;
  requires the DUT to present a full-width `WSTRB`; injects SLVERR and
  supports `stop_after` via the same counters as before. Kept byte-for-byte
  as originally written specifically to avoid any risk to this coverage
  sweep — see the code comment at the branch point.

Returns the list of accepted write-data beats as `output_beats` (used by
`../../orchestration/campaign.py::_record_case` as the "observed" side of
the checked job).

**Who calls it.** `../../orchestration/campaign.py::run_code_owned_axi_lite_operation_case`
is the only caller, which is itself called at every AXI4-Lite phase/protocol-mode/
address-variant/error-injection probe inside
`../../orchestration/campaign.py::_run_axi_lite_operation_campaign` — the
AXI4-Lite equivalent of the plain ready/valid path's
`run_code_owned_operation_case`. Not embedded in the generated TB block
(`orchestration/instrumentation.py` does not import anything from
`axi_lite.py`) — AXI4-Lite memory jobs are only ever exercised through the
automatic campaign, never directly by Verifier-authored `llm_extension` code.

### Private helpers worth knowing about

- `_handle(dut, name)` — signal-handle getter with a clear
  `AxiLiteMemoryDriveError` on a missing pin. Independently duplicated (not
  shared) from `cocotb.py`'s own private `_handle`.
- `_elements(binding, dimensions)` — computes element count from bound
  dimensions; a third independent implementation of the same idea as
  `../../orchestration/campaign.py::_expected_elements` and
  `../../operation/stimulus/stimulus_generator.py::_shape`'s size check — not shared, so
  a change to dimension-resolution semantics must be made in all three
  places. (`adapter.expected_elements` is the *fourth*, shared one every
  driver actually uses for windowing; this one is kept only for
  `default_axi_lite_memory_bases`'s own bookkeeping.)
- `_ReadyPolicy` — see above; the controllable arrival-order/stall state
  machine for the manager-facing address/data channels, used only by the
  hand-rolled fallback path.
- `_group_channels(group)` — validates and returns the five required
  AXI4-Lite channel bindings from a standard-protocol group.
- `_FaultInjectingTarget` — see above; the library-facing error-injection
  wrapper around `adapter.OperationMemoryAdapter`.

## `memory/` and `adapter/` — the reusable, protocol-agnostic layers

Added alongside `axi4_outstanding.py` when the `cocotbext-axi` dependency was
introduced specifically to give full-AXI4 driving a real out-of-order
completion mechanism, and later split into two packages (`memory/`
vs. `adapter/`) once `axi_lite.py`'s default path also started composing
`cocotbext-axi` and needed the exact same address-window logic
`axi4_outstanding.py` had been keeping private to itself.

- **`memory/`** — a thin re-export of `cocotbext.axi.memory.Memory`. Nothing
  else: no operation awareness, no canonical values, no windows. If this
  package ever needs more than a re-export (e.g. a shared backing store
  spanning multiple DUT instances), that is the only kind of change that
  belongs here.
- **`adapter/operation_memory_adapter.py`** — everything that needs to know
  about *this tool's* operation contracts, built on top of `memory/`:
  - `OperationMemoryAdapter` — `.load(operation, case, bases)` preloads every
    input object's canonical stimulus at its base address *and* precomputes
    both directions' address windows (`.input_windows`/`.output_windows`);
    `.read_words`/`.write_word` serve canonical full-width words; AXI4's
    narrow BFM calls `.read_bus_word` and `.write_strobed_bus_word` to preserve
    the actual address-selected byte lanes without corrupting neighboring
    bytes. `.read_output_values(binding, dimensions, bases)` reads one output
    object back out **in correct logical (address) order**, never wire
    arrival order (a genuinely concurrent driver's write bursts need not
    complete in the order they were issued); `.mapping_for_input_address(addr)`/
    `.mapping_for_output_address(addr)` are what `axi4_outstanding.py` uses
    to resolve an accepted AR/AW address to its bound object's
    `memory_mapping` — this exact pair of methods used to be
    `axi4_outstanding.py`'s own private `_find_window`/`_memory_windows`;
    moving them here is what makes them available, unchanged, to
    `custom_mmio.py` (below) instead of growing a third copy — proven, not
    just intended: `custom_mmio.py`'s read driver reuses both this adapter
    and the shared `drivers/_completion_scheduler.py` implementation with
    zero modifications.
  - `build_address_windows`/`find_window_mapping` — the free functions
    `OperationMemoryAdapter` calls internally; also directly usable by a
    driver that does not want the full adapter object.
  - `pack_words`/`unpack_words` — the same word-packing semantics as
    `pool/operation_metadata/protocol.py`'s private `_decode_words`, promoted
    to one shared, public implementation `axi_lite.py` now also imports
    rather than keeping its own copy.

No `cocotb` import anywhere in either package — every function is
synchronous and testable without a simulator.

## `drivers/axi4_outstanding.py` — full-AXI4, multi-outstanding, out-of-order drive

Module docstring explains the scope in detail; summary: this is the
**driver** layer of the memory/adapter/driver split (`../../pool/operation_metadata/README.md`'s
custom_mmio section), for full AXI4 specifically. Unlike `axi_lite.py`'s
default path, it is built on `cocotbext-axi`'s **low-level** channel
primitives (`AxiAWSink`/`AxiWSink`/`AxiBSource`/`AxiARSink`/`AxiRSource` from
`cocotbext.axi.axi_channels`), not that library's own `AxiSlave`/`AxiRam`
convenience models — those service one accepted request fully before
starting the next (legal AXI4, but strictly in issue order despite carrying
an ID), which would defeat the entire point of this module.

- `_bind_channel_bus` — re-exported from the shared `_bus_binding.bind_channel_bus`
  (used by `axi_lite.py` too): wraps one compiled channel's exact
  `field -> signal name` mapping as a `cocotb_bus.bus.Bus` with `name=None`,
  so cocotbext-axi's channel classes bind to this tool's actual contract
  signal names, never an assumed AXI naming convention.
- `RandomCompletionScheduler` — owned by the protocol-neutral
  `drivers/_completion_scheduler.py` module and re-exported here for
  compatibility. `await schedule(id,
  action)` runs `action()` once every earlier same-`id` `schedule()` call has
  finished and a seeded-random extra delay (in clock edges) has elapsed.
  Same-id calls are strictly FIFO; different ids race, seeded by
  `random.Random(seed)` for reproducibility. This is the actual mechanism
  proven against real RTL by
  `multigent/tests/test_axi4_outstanding_drive.py` (seed `6` makes a request
  issued *second* complete *first*, deterministically).
- `execute_axi4_memory_job(dut, clock_name, group, operation, case, bases, *, seed=None, max_extra_cycles=4, read_error_at=None, write_error_at=None, abort_signal_name=None, reset_signal_name=None, reset_active_value=0, stop_after=None, first_transfer_simultaneous=False, initial_sink_stall_cycles=0, initial_sink_stall_cycles_by_kind=None, write_address_one_cycle_probe=False, timeout_cycles=262_144) -> list[dict[str, int]]`
  — the group may be a single-capability manager port: the call derives
  `needs_read = bool(operation["inputs"])` / `needs_write =
  bool(operation["outputs"])` and only requires (and only builds sinks/sources
  for) the channels that direction needs, so a read-only `gmem_a`-style port and
  a write-only `gmem_c`-style port can each be served by their own call with an
  operation narrowed to one object. `initial_sink_stall_cycles_by_kind`
  (`write_address` / `write_data` / `read_address` → cycles) overrides the
  uniform `initial_sink_stall_cycles` per sink; the ID-field requirement is only
  enforced for the channel kinds actually required. `write_address_one_cycle_probe`
holds the write-address sink not-ready until the DUT presents VALID, then
releases READY after exactly one sampled stalled cycle; it is exclusive with
`first_transfer_simultaneous`. The function returns the
  output objects' values **already decoded per element** through
  `OperationMemoryAdapter.read_output_values` (each list entry is
  `{"payload": <canonical element>}`), not raw bus words.
  It spawns one independent worker per accepted AR/AW (`cocotb.start_soon`),
  each of which reads/writes `adapter.OperationMemoryAdapter` synchronously
  (resolving which bound object an address belongs to via
  `.mapping_for_input_address`/`.mapping_for_output_address`) and then calls
  `RandomCompletionScheduler.schedule` before sending its response. Progress
  toward the job's expected read/write word counts is tracked from **direct
  wire observation** (`RVALID`/`RREADY` sampled every clock edge), never from
  `AxiRSource.send()` returning — `send()` only enqueues, it does not wait
  for the item to actually reach the wire, and trusting it as if it meant
  "transferred" was a real bug caught while building the real-simulator test
  (the job would stop one cycle before the last read genuinely completed).
  Unlike `execute_axi_lite_memory_job`, this function does **not** drive the
  job-acceptance command itself; the caller composes it with the job start:
  `../../orchestration/campaign.py::run_code_owned_axi4_operation_case` runs it
  concurrently with `drive_accepted_command`, while
  `run_code_owned_axi4_operation_case_via_control_plane_sequence` starts one
  call per bound protocol group (each narrowed to one data object) concurrently
  with `drive_control_plane_sequence` and then polls for completion while those
  calls are still running.
  Completion waits for all expected output bytes (counted from accepted
  WSTRB lanes) and one B response per accepted AW **burst**, not one B per
  output word. `stop_after=("write_data", 1)`
  permits a genuine output-phase reset abort after the first W beat even
  when a burst has not yet produced B. On early exit, a stalled TB-owned
  response VALID stays asserted until reset and drops on the reset
  transition; cleanup must not create an illegal pre-reset withdrawal.
- Scope, stated plainly in the module docstring: `id` must be bound on the
  address channels *and* on the response/read-data channels. Aligned
  `FIXED`/`INCR` and legal-length `WRAP` bursts use the same exact transfer
  windows as the protocol checkers. Aligned byte and halfword transfers on a
  wider bus, plus legal unaligned INCR starts, preserve address-selected
  RDATA/WDATA lanes. An unaligned start that would leave an object byte
  unread/unwritten is rejected by the capture adapter, not credited.
- `../../orchestration/campaign.py::_run_axi4_operation_campaign` (a shared
  AXI4 manager group plus a ready/valid command) resets the DUT between
  probes and runs: early-stop (`stop_after`) jobs, each followed by a reset,
  stopped at the first read response of each successive input object, at
  the end of all reads, and at the first accepted write beat; every
  generated case with `seed=index`, where `run_code_owned_axi4_operation_case`
  selects a first-transfer sink stall of `(0, 2, 4, 7)[seed % 4]` cycles and
  makes the first transfer simultaneous when `seed == 0`; a `seed=6`
  out-of-order-completion case when the operation has two or more inputs;
  `read_page_edge` / `write_page_edge` base variants; an illegal command
  followed by the error pulse; and injected read and write response errors.
  These are **observed** coverage hits, not mere planned scenarios. For a
  register-started (`control_plane_sequence`) operation the dispatch is
  instead `_run_axi4_control_plane_operation_campaign`, which runs the
  transport variants described near the top of this file and does **not**
  replay the reset-abort / illegal-command / error-injection probes above.
  Real-RTL fault/fix pair tests for AXI4 read and write features are
  `multigent/tests/test_axi4_read_rtl_feature_matrix.py` and
  `test_axi4_write_rtl_feature_matrix.py`. Earlier per-run coverage figures
  that this section used to quote (e.g. an 85/104-bin single-beat probe, a
  86/86 "truthful capability" contract, and several bin families listed as
  qualified) were removed because they were not re-derived and are **not**
  treated as qualification: under the current policy
  a strict pass needs a frozen-contract/generated-TB mutant that fails for the
  intended reason plus corrected RTL passing every required bin, and rows are
  marked one at a time. Current status lives in
  [`../../SUPPORT_VALIDATION_MATRIX.md`](../../SUPPORT_VALIDATION_MATRIX.md),
  which points to `FULL_POOL_QUALIFICATION_MATRIX.md`.

## `drivers/custom_mmio.py` — an LLM-declared custom memory-like protocol, both directions

The **driver** layer for the `custom_mmio` protocol profile
(`../../pool/operation_metadata/README.md`'s custom_mmio section): a closed,
generic `request`(`addr`,+`id`,+`len`)/`data`(`data`,+`id`,`last`,`resp`,`strb`)/
`response`(`resp`,+`id`, optional) channel vocabulary an Architect can declare
for a genuinely custom protocol that is still structurally memory-like, so it
gets the same automatic capture/drive this tool gives AXI4/AXI4-Lite instead
of falling back to the opaque `custom` profile's handshake-only coverage. A
group is one direction only — unlike AXI4's single combined group, a design
wanting both directions declares two `custom_mmio` groups — so reads and
writes are two separate public functions, each taking its own group.

This is the concrete proof the memory/adapter/driver split pays off: neither
`adapter.OperationMemoryAdapter` nor `drivers._completion_scheduler.RandomCompletionScheduler`
was written with this driver in mind, and neither needed to change to serve
it. The custom driver only constructs a bare `field -> signal name` mapping;
the low-level `Bus(..., name=None)` construction and cocotbext-axi
`_optional_signals` compatibility handling live once in
`_bus_binding.bind_signal_bus`, shared with the AXI-prefixed
`bind_channel_bus` path. `_stream_classes` then calls
`cocotbext.axi.stream.define_stream` — the same generic stream-primitive
factory AXI's own channel classes are themselves built from — parameterized
by whatever fields the compiled channel actually declared, not a fixed AXI
field set.

- `execute_custom_mmio_read_job(dut, clock_name, group, operation, case, bases, *, seed=None, max_extra_cycles=4, read_error_at=None, timeout_cycles=262_144) -> None`
  — `group` must cover the operation's *inputs*. `id` is optional throughout:
  bound, requests complete out of issue order exactly like full AXI4 via the
  shared scheduler; unbound, every request lands in the same `None`-keyed FIFO
  and completes strictly in issue order. `len` on `request` is optional too:
  bound, it sizes a read burst exactly like AXI4's ARLEN (`len` beats plus
  one, with `last` set on the final beat); unbound, every read is a single
  beat — this is the same generic "length" semantic class already used
  elsewhere, no new taxonomy needed. Progress is tracked from direct wire
  observation, the same discipline `axi4_outstanding.py` uses and for the
  same reason (`DataSource.send()` only enqueues).
- `execute_custom_mmio_write_job(dut, clock_name, group, operation, memory, *, seed=None, max_extra_cycles=4, write_error_at=None, timeout_cycles=262_144) -> list[dict[str, int]]`
  — `group` must cover the operation's *outputs*; `memory` is a caller-supplied
  `OperationMemoryAdapter`, shared with the read job's own instance so a job
  needing both directions writes into and reads from one consistent image.
  Request/data pairing is strict FIFO by acceptance order (like AXI4's AW/W),
  never by id — id only correlates a `response` to its `request`, exactly as
  on the read side. The `response` channel is genuinely optional, unlike
  AXI4's always-present BRESP: if the group declares one, a write completes
  only once it fires; if not, acceptance onto `data` itself is completion
  (matching how `pool/operation_metadata/protocol.py`'s capture engine already
  interprets a missing response channel), and `write_error_at` is rejected
  outright when there is no response channel to signal an error on. Returns
  accepted beats in **wire acceptance order** — a caller driving concurrently
  writing groups should read back through `OperationMemoryAdapter.read_output_values`
  instead for a logical-order guarantee, exactly like `axi4_outstanding.py`'s
  own docstring warns.
- **Campaign wiring**: `../../orchestration/campaign.py::run_code_owned_custom_mmio_operation_case`
  resolves the read group from the operation's inputs and the write group
  from its outputs (`_custom_mmio_group`), builds one `OperationMemoryAdapter`
  for the write job, and runs `execute_custom_mmio_read_job`/
  `execute_custom_mmio_write_job` concurrently alongside `drive_accepted_command`
  — composed the same way `run_code_owned_axi4_operation_case` composes
  `execute_axi4_memory_job` with the command driver.
  `_run_custom_mmio_operation_campaign` mirrors `_run_axi4_operation_campaign`
  exactly (same reset-between-cases loop, same explicit seed-`6`
  out-of-order-completion close when the operation has 2+ inputs), since both
  protocols share the same underlying `RandomCompletionScheduler`.
- Proven against real Verilator simulation:
  `multigent/tests/test_custom_mmio_burst_and_write.py` (read burst via `len`,
  two outstanding writes acking out of order) and
  `multigent/tests/test_custom_mmio_campaign.py` (the full campaign wiring
  above — command accepted, three inputs read genuinely out of order over one
  group, one output written over a second group, completion observed, value
  read back through the shared adapter).

## Cross-references

- [`../README.md`](../README.md) — the protocol domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — the
  automatic campaign, which is the production caller of most execution
  primitives documented here.
- [`../../README.md`](../../README.md) — full `verifier_tool` architecture,
  the three-domain taxonomy, and the AXI4/AXI4-Lite/AXI4-Stream binding rules
  (`channel.protocol_group`/`protocol_channel`, `signal.protocol_field`).
- [`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md) — the
  Protocol Feature Plan/catalog (`protocol_features.yaml`,
  `feature_plans/protocol.py`) that `build_protocol_stimulus_plan` compiles
  from, and that `protocol/assertion/` and `protocol/coverage/` build
  independently from the same bindings.
- [`../../pool/role_pool/README.md`](../../pool/role_pool/README.md) —
  `compile_standard_protocol_plan` (in `role_pool/standard_protocols.py`),
  used by `../../orchestration/campaign.py::_axi_lite_group` to resolve the exact AXI4-Lite
  group `../../orchestration/campaign.py` drives.
- [`../../lifecycle/stimulus/README.md`](../../lifecycle/stimulus/README.md) — `drive_accepted_command`,
  used both directly by `../../orchestration/campaign.py` and internally by
  `execute_axi_lite_memory_job` above.
- [`../../operation/stimulus/README.md`](../../operation/stimulus/README.md) — the canonical GEMM
  stimulus/golden-model generator whose output `../../orchestration/campaign.py` serializes
  through the primitives documented here.
