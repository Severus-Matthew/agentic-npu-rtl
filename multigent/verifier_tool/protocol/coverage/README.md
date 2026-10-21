# Coverage: protocol domain

This folder instantiates and samples deterministic coverage obligations for the
**protocol** domain: generic ready/valid channel handshaking, stall stability,
address alignment, and standardized AXI4/AXI4-Lite/AXI4-Stream bus rules. It is
the coverage branch of the domain-first `protocol/` folder (see
[`../README.md`](../README.md) for the protocol domain and
[`../../orchestration/README.md`](../../orchestration/README.md) for the shared
runtime data flow).
Protocol coverage never inspects arithmetic correctness (that is `../operation/`)
and never inspects command/job/busy/completion/error semantics on its own,
although — see "Lifecycle templates instantiated here" below — it physically
builds five lifecycle-owned obligations too, because those happen to be plain
signal/channel-scoped templates.

Backing catalog: `multigent/verifier_tool/pool/feature_plans/protocol_features.yaml`,
reached through `feature_plans/catalog.py:load_protocol_feature_catalog()`. The
path is re-exported here as `INTERFACE_COVERAGE_TEMPLATES_PATH` for callers that
only need the file location; nothing in this folder reads the path itself, since
`load_protocol_feature_catalog()` already resolves it via `feature_plans/catalog.py`.

## Files

- `__init__.py` — re-exports `build_interface_coverage_plan`,
  `load_interface_coverage_templates`, `INTERFACE_COVERAGE_TEMPLATES_PATH` from
  `plan.py`, and `ProtocolCoverageMonitor`, `protocol_runtime_templates` from
  `runtime.py`.
- `plan.py` — turns a frozen interface contract into the `obligations` list
  (static instantiation, no simulation).
- `runtime.py` — turns sampled DUT snapshots into named bin hits for the subset
  of templates that need temporal/cross-signal logic (static instantiation
  alone cannot decide their bins).

## Public API surface

`build_interface_coverage_plan` and `load_interface_coverage_templates` are
re-exported by the top-level facade (`multigent.verifier_tool`) directly from
`protocol.coverage.plan`, matching what this package's own `__init__.py`
re-exports — no divergence here.

`ProtocolCoverageMonitor` and `protocol_runtime_templates`, by contrast, are
**not** in the top-level facade's `_EXPORTS` map at all (see
`multigent/verifier_tool/__init__.py`). They are reachable only via
`multigent.verifier_tool.protocol.coverage` or
`multigent.verifier_tool.protocol.coverage.runtime` directly. In practice the
only production caller is `orchestration/runtime.py` (`InterfaceCoverageTracker.__init__`
constructs one `ProtocolCoverageMonitor(self.plan)`); the only other consumer is
`multigent/verifier_tool/tool_regression/integration/test_standard_axi_protocols.py`, which imports
`ProtocolCoverageMonitor` directly from `multigent.verifier_tool.protocol.coverage.runtime`
to unit-test AXI bin classification without a full `InterfaceCoverageTracker`.

## `plan.py`

### `load_interface_coverage_templates() -> dict[str, Any]`

`@lru_cache(maxsize=1)`. Loads `protocol_features.yaml` via
`load_protocol_feature_catalog()` and **merges in** every lifecycle template from
`lifecycle.coverage.plan.load_lifecycle_coverage_templates()["templates"]` into
one combined `templates` dict (`catalog["features"] | lifecycle_templates`).
Validates every template's `scope` is one of `signal`, `channel`,
`standard_channel`, `standard_group`, `standard_field`, that `match` is a
mapping, and that `coverage.bins` is a non-empty list. This is why lifecycle's
`reset_behavior`, `busy_behavior`, `completion_behavior`, `error_behavior`, and
`command_legality` templates get instantiated from *this* file's generic
signal/channel matching loop rather than from `lifecycle/coverage/plan.py` — see
"Lifecycle templates instantiated here" below. Called by
`build_interface_coverage_plan` (below) and re-exported through the facade for
any caller that wants the raw template catalog (e.g. prompt rendering).

### `build_interface_coverage_plan(interface: Mapping[str, Any]) -> dict[str, Any]`

The single entry point for this file. Takes a frozen `interface_contract` (the
Architect's `signals`/`channels`/`clock`/`reset` declaration) and returns a
coverage plan dict:

```python
{
    "schema_version": 2,
    "source": "frozen interface contract + protocol_features.yaml",
    "interface_contract": {...},          # copied through verbatim
    "standard_protocol_plan": {...},      # from compile_standard_protocol_plan()
    "monitor": {"clock": ..., "reset": ..., "signals": [...]},
    "obligations": [...],                 # the actual coverage obligations
    "feature_plan": {...},                # see "feature_plan / compiled_coverage" below
    "compiled_coverage": {...},
}
```

Algorithm: loads templates and `role_pool.interface_semantics` protocol-profile
tags; for every `scope: signal` template, matches contract signals by exact
field equality (`_signal_matches`) — with one special case, `address_alignment`
is skipped for non-standard profiles unless the matched channel's protocol
profile carries the `alignment` coverage tag (an arbitrary index register is not
an addressable memory channel just because a signal is tagged `semantic_class:
address`); for every non-signal, non-`standard_*` template, matches contract
channels by `coverage_tag`/`protocol_profile` and required roles/semantic
classes (`_channel_role_index`, `_channel_class_index`); standardized-bus
templates (`scope` starting with `standard_`) are instantiated separately by
`_append_standard_obligations` against `compile_standard_protocol_plan(interface)`
(from `role_pool/standard_protocols.py`). Every generated obligation goes
through `_obligation(...)`, which fills in `id = f"{scope}.{safe(scope_name)}.{template_name}"`,
copies `coverage.bins` from the template, and defaults each bin's
`applicability` to `required_reachable` unless the bin was explicitly marked
`required: false` in YAML.

Capability-based bin restriction (private helpers `_capability_bins`,
`_restrict_to_capability_bins`, `_diagnostic_bin`): several AXI obligations have
bins that are only reachable for some declared protocol capability set (e.g.
`axi_lite_outstanding_depth`'s `multiple` bin and AXI4's multiple-request
bins are downgraded to `applicability.status: inapplicable` when
`capabilities.max_outstanding <= 1`;
`axi4_transfer_size`'s `narrow` bin is dropped when the data bus is ≤16 bits;
`axis_stall_position`'s `last_beat` bin is dropped when the stream has no
`TLAST`). A downgraded bin still appears in the obligation's `bins` list (so
`InterfaceCoverageTracker.report()` never expects a hit for it) but is excluded
from the `hit_bins`/`total_bins` percentage. Testbench-is-source channels
(`channel.direction == "input"`, including generic `ready_valid`) receive an
ownership restriction: only the completed `handshake_states.transfer` bin is
universally required. READY is DUT-owned, so a legal sink may raise it early,
hold it high, or wait for VALID; no particular arrival-order or stall-length
bin can be mandatory from role and profile metadata alone. Those bins remain
observable diagnostics. This avoids falsely failing a legal
READY-only-when-VALID RTL. A future explicit channel capability may opt in to
stronger required timing bins.

Generic `address_alignment` observations are bound to the address channel's
unique VALID/READY pair and are sampled only on a real accepted transfer
outside reset. An idle/default bus value or a stalled address no longer earns
coverage credit. The four legacy address partitions still need explicit legal
range/alignment metadata before they can be treated as a complete custom-MMIO
campaign; the current sampler's width maximum and 4-byte alignment are not
proof of the legal memory window for an arbitrary contract.

Called by: `multigent/agents/verifier.py` (persists `interface_coverage_plan.yaml`
and gates `VERIFICATION_READY`), `multigent/orchestration/verification_tools_node.py`
and `multigent/orchestration/artifacts.py` (build the coverage plan handed to
`run_cocotb_regression`), `multigent/scripts/build_taxonomy_release.py` (release
gate), `multigent/verifier_tool/protocol/stimulus/stimulus_generator.py`, and
`operation/coverage/plan.py:merge_coverage_plans` (as the `interface_plan`
half of the merge). Also called directly (bypassing the facade) by several
`multigent/verifier_tool/tool_regression/` tests.

### `feature_plan` / `compiled_coverage` fields

`build_interface_coverage_plan` also calls
`feature_plan.build_protocol_feature_plan(plan)` (the `feature_plans/protocol.py`
matcher) and `feature_plans.compiler.compile_coverage_feature_plan(...)`, storing
the results at `plan["feature_plan"]` / `plan["compiled_coverage"]`. Reading
`feature_plans/protocol.py` shows this matcher mostly **re-packages the
obligations already built above** into the shared cross-domain Feature Plan
record shape (`bindings`/`assertion`/`coverage`/`stimulus`) rather than
re-deriving bins independently — it iterates `interface_plan.get("obligations",
[])` and wraps each one via `feature_record(...)`. These two fields are
currently read only by `multigent/verifier_tool/tool_regression/unit/test_feature_plans.py`; neither
`InterfaceCoverageTracker`, `ProtocolCoverageMonitor`, nor
`manifest.py:compile_verification_manifest` ever reads `plan["feature_plan"]` or
`plan["compiled_coverage"]` — both only read `plan["obligations"]` directly. If
you are tracing "what actually drives simulation," follow `obligations`, not
`feature_plan`. See
[`../../feature_plans/README.md`](../../pool/feature_plans/README.md) for the
Feature Plan schema itself.

### Lifecycle templates instantiated here

Because `load_interface_coverage_templates()` merges lifecycle's signal/channel
templates in, this file — not `lifecycle/coverage/plan.py` — is what actually
instantiates five lifecycle-owned obligations. Their *sampling*, however, is
split between here and `lifecycle/coverage/runtime.py`; see the full table in
[`../README.md`](../README.md#obligation-templates-instantiated-vs-sampled).

| template | instantiated by (this file) | sampled by |
| --- | --- | --- |
| `reset_behavior` | generic signal loop | `InterfaceCoverageTracker._sample_reset` (`orchestration/runtime.py`) |
| `completion_behavior` | generic signal loop | `InterfaceCoverageTracker._sample_completion` |
| `error_behavior` | generic signal loop | `InterfaceCoverageTracker._sample_error` |
| `busy_behavior` | generic signal loop | `LifecycleCoverageMonitor.sample` (`lifecycle/coverage/runtime.py`) |
| `command_legality` | generic channel loop | `LifecycleCoverageMonitor.sample` |

`job_lifecycle`, `reset_abort_phase`, and `post_reset_purity` are **not** in
this list: they are operation-scoped and need `operation_metadata`, which this
file's `build_interface_coverage_plan(interface)` never receives. They are
instantiated separately by `lifecycle/coverage/plan.py:build_lifecycle_coverage_plan`
and only appear in a plan after `operation/coverage/plan.py:merge_coverage_plans`
concatenates them in.

## `runtime.py`

### `protocol_runtime_templates() -> frozenset[str]`

Returns `_SPECIAL_TEMPLATES`, the frozen set of template names this monitor
handles (every AXI4/AXI4-Lite/AXI4-Stream template plus
`handshake_arrival_order`). Not called anywhere outside this module today
(no production or test call site); it exists as the documented boundary of
what `ProtocolCoverageMonitor` owns versus what plain `handshake_states` /
`stall_stability` sampling (done directly in `orchestration/runtime.py` and
`cocotb_model.py`) owns.

### `ProtocolCoverageMonitor`

Constructed once per test by `InterfaceCoverageTracker.__init__` as
`self.protocol_coverage_monitor`, and reset every test via
`InterfaceCoverageTracker.begin_test`/`end_test`/on every reset pulse (temporal
cross-signal state — outstanding-transaction lists, AW/W arrival order queues,
AXI-Stream beat counters — must not leak across cocotb tests or through a DUT
reset). Filters `plan["obligations"]` down to just the ones whose `template` is
in `_SPECIAL_TEMPLATES`.

`sample(self, snapshot: Mapping[str, Any]) -> list[tuple[str, str]]` is the only
public method. Called once per non-reset clock sample from
`InterfaceCoverageTracker.sample_snapshot`. Increments an internal cycle
counter, dispatches every owned obligation to one private per-template handler
below, and returns `(obligation_id, bin_name)` pairs that the caller feeds to
`ContractCocotbCoverageModel.sample_bin` via `InterfaceCoverageTracker._hit`.

Dispatch table (all private; documented here because another engineer touching
AXI coverage will need to find these by template name, not by reading the whole
file top to bottom):

| template(s) | handler | logic |
| --- | --- | --- |
| `handshake_arrival_order` | `_handshake_order` | Tracks whether VALID or READY was raised first using one-cycle memory (`self.state["arrival:<id>"]`); emits `simultaneous`/`valid_before_ready`/`ready_before_valid` only at the cycle a transfer actually fires. |
| `axi4_4k_boundary`, `axi4_burst_type`, `axi4_burst_length`, `axi4_transfer_size`, `axi4_alignment` | `_address_hits` | Reads `addr`/`len`/`size`/`burst` on a fired transfer; `axi4_4k_boundary` calls `assertion.protocol.axi.axi_transfer_windows(...)` (shared with the code-owned AXI assertion checkers) to get per-beat address windows. |
| `axi4_write_strobe`, `axi_lite_write_strobe` | `_strobe_hits` | Classifies the `strb` field as `all_zero`/`full`/`sparse` against the declared or elaborated strobe width. |
| `axi4_write_channel_order`, `axi_lite_write_channel_order` | `_write_order` | Queues AW/W fire cycles per obligation and pairs them off FIFO-style into `same_cycle`/`address_first`/`data_first`. |
| `axi4_response_code`, `axi_lite_response_code` | `_response_hits` | Maps the `resp` field to `okay`/`exokay`(AXI4 only)/`slverr`/`decerr`. |
| `axi4_outstanding_depth` | `_outstanding` | Maintains a list of `(kind, id)` in-flight transactions, matched off on B/R completion, to classify `one`/`multiple_same_id`/`multiple_ids`. |
| `axi_lite_read_write_concurrency` | `_lite_concurrency` | Same-cycle AW vs AR firing → `simultaneous`/`write_only_cycle`/`read_only_cycle`. |
| `axi_lite_address_partition` | `_lite_address_hits` | Classifies `addr` as `zero`/`aligned`/`unaligned`/`page_edge` relative to the inferred data-bus byte width. |
| `axi_lite_outstanding_depth` | `_lite_outstanding` | A simpler counter (no ID tracking, since AXI4-Lite has none) → `one`/`multiple`. |
| `axi4_sideband_partition`, `axi_lite_protection_partition` | `_field_partition_hits` | A single bound signal → `zero`/`nonzero`. |
| `axis_packet_length`, `axis_keep_pattern`, `axis_stall_position`, `axis_back_to_back_packets`, `axis_sideband_partition` | `_axis_hits` | Per-`(id, dest)` stream-key state tracks beat counts and last-fire cycle to classify packet length, `KEEP` fullness, stall position within a packet, and inter-packet gaps. |

`reset()` clears `self.state` and `self.cycle`; called from
`InterfaceCoverageTracker.begin_test`, `end_test`, and every time a reset pulse
is observed active in `sample_snapshot`/`observe_reset_snapshot` (protocol
coverage is intentionally not sampled while reset is active).

AXI4 sideband applicability may be declared per channel with
`protocol_capabilities.sideband_bins_by_channel`, keyed by canonical channel kind
and then protocol field. For example, fixed write ID 0 and fixed read ID 1 use
`write_address.id: [zero]`, `write_response.id: [zero]`,
`read_address.id: [nonzero]`, and `read_data.id: [nonzero]`. The coverage compiler
uses this channel-specific declaration before the legacy group-wide `id_bins`.

## Example: `handshake_states` → obligation → cocotb-coverage

From `protocol_features.yaml`:

```yaml
handshake_states:
  scope: channel
  match: {coverage_tag: handshake, required_roles: [valid, ready]}
  coverage:
    sampler: valid_ready_cross
    bins:
      - {name: idle, values: {valid: 0, ready: 0}, intent: valid=0 and ready=0}
      - {name: receiver_ready, values: {valid: 0, ready: 1}, intent: valid=0 and ready=1}
      - {name: backpressured, values: {valid: 1, ready: 0}, intent: valid=1 and ready=0}
      - {name: transfer, values: {valid: 1, ready: 1}, intent: valid=1 and ready=1}
```

For a channel named `cmd`, `build_interface_coverage_plan` emits obligation id
`channel.cmd.handshake_states` with those four bins copied through verbatim.
This obligation is **not** sampled here in `protocol/coverage/runtime.py` — `handshake_states`
is not in `_SPECIAL_TEMPLATES`. Instead `InterfaceCoverageTracker.sample_snapshot`
handles it directly (`elif template == "handshake_states":
self.coverage_model.sample_handshake(obligation_id, valid, ready)`), which
calls into `cocotb_model.py:ContractCocotbCoverageModel._build_handshake`'s
generated `CoverPoint`/`CoverCross` pair — see
[`../../orchestration/README.md`](../../orchestration/README.md).

## Cross-links

- [`../README.md`](../README.md) — the protocol domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — shared
  runtime data flow, `InterfaceCoverageTracker`, and `cocotb_model.py`.
- [`../../lifecycle/coverage/README.md`](../../lifecycle/coverage/README.md) — `LifecycleCoverageMonitor`,
  which samples `busy_behavior`/`command_legality` instantiated here.
- [`../../operation/coverage/README.md`](../../operation/coverage/README.md) — the sibling domain;
  `merge_coverage_plans` there combines this file's plan with the operation and
  lifecycle plans.
- [`../../README.md`](../../README.md) — `verifier_tool` package map and the
  three-domain taxonomy.
- [`../../pool/role_pool/`](../../pool/role_pool) — `interface_semantics.py` (coverage
  tags per protocol profile) and `standard_protocols.py` (`STANDARD_PROFILES`,
  `compile_standard_protocol_plan`) that this file depends on.
- [`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md) — documents
  `protocol_features.yaml`, `feature_plans/protocol.py`, and
  `compile_coverage_feature_plan`.
- [`../../pool/operation_metadata/README.md`](../../pool/operation_metadata/README.md) —
  not used directly by this folder, but consumed by `orchestration/runtime.py` to
  build the `ReadyValidCaptureAdapter` that captures the same channels this
  folder's obligations describe.
