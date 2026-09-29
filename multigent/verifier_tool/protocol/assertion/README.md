# Assertion / Protocol

Code-owned per-channel and standardized-bus assertion checkers: ready/valid
stall stability, VALID-low-during-reset, and the complete AXI4 / AXI4-Lite /
AXI4-Stream rule sets. Unlike `operation/assertion/`, this subfolder has no
local YAML catalog — it is backed entirely by two catalogs that live outside
`assertion/`:

| Catalog | Owns | Consumed via |
|---|---|---|
| `verifier_tool/pool/feature_plans/protocol_features.yaml` | Generic per-channel features: handshake arrival order and `stall_stability`; executable definition shared by standard-group and explicit channel-policy `valid_low_during_reset` features | `feature_plan.py::build_protocol_feature_plan` → `compile_assertion_feature_plan` (called from `runtime.py::build_protocol_assertion_plan`) |
| `verifier_tool/pool/role_pool/standard_protocols.yaml` | Per-profile (`axi4`/`axi4_lite`/`axi4_stream`) field catalogs and each profile's `rules:` name list | `role_pool/standard_protocols.py::compile_standard_protocol_plan`, folded into the interface plan's `bindings.standard_groups` before it reaches this subfolder |

No file in this subfolder reads either YAML directly; both arrive pre-compiled
through the interface/feature plan passed into `build_protocol_assertion_plan`.

`valid_low_during_reset` has two non-overlapping applicability paths. Standard
AXI-family/`custom_mmio` groups receive it from their protocol specification.
Generic `ready_valid`/`custom` channels receive it only when the frozen interface
contract explicitly selects `reset_channel_policies[].behavior:
valid_deasserted`. The latter produces
`channel.<channel>.valid_low_during_reset`; it is never inferred merely from a
VALID/READY pair. Its required `settle_cycles` binding controls when that
channel becomes eligible for checking during an asserted reset; standard groups
fall back to the reset signal's existing settle-cycle binding.

## `axi.py` — pure AXI transfer geometry

Shared, side-effect-free burst arithmetic. No cocotb, no snapshot, no
Mapping-of-signals — just address/length/size/burst integers in, byte windows
out.

- `class AXIGeometryError(ValueError)` — raised by all three functions below
  when a descriptor cannot describe a legal AXI4 burst.
- `axi_transfer_windows(descriptor: Mapping[str, int]) -> tuple[tuple[int, int], ...]`
  — one inclusive `(low, high)` byte window per beat. FIXED (`burst=0`) repeats
  the same first window; INCR (`burst=1`) starts at the unaligned first window
  then walks aligned windows; WRAP (`burst=2`) requires an already-aligned
  start and 2/4/8/16 beats, and wraps addresses inside the `beats * 2**size`
  span. Raises `AXIGeometryError` for out-of-domain `addr`/`len`/`size`,
  reserved `burst` encodings, or a non-conforming WRAP beat count/alignment.
- `axi_burst_crosses_4k(descriptor) -> bool` — `True` if any window from
  `axi_transfer_windows` lands in a different 4-KiB page (`>> 12`) than the
  first.
- `axi_lane_mask(window: tuple[int, int], bus_bytes: int) -> int` — the legal
  WSTRB/byte-lane bitmask for one window on a `bus_bytes`-wide data bus;
  raises if the window would need to wrap across the bus width or if
  `bus_bytes` is not a power of two.

**Called from** `protocol/assertion/assertion_checkers.py` (`_check_address`,
`_check_write_pair`) to validate AWLEN/ARLEN geometry and WSTRB lane legality,
and — notably, this is the one place a `coverage/` file imports directly from
`assertion/` rather than through a shared feature plan —
`multigent/verifier_tool/protocol/coverage/runtime.py` imports
`axi_transfer_windows` directly (`from
multigent.verifier_tool.protocol.assertion.axi import axi_transfer_windows`)
to classify observed transfers into the same byte windows for coverage
sampling. This is a shared pure-math utility, not a Feature Plan dependency;
it does not contradict the "assertion/coverage/stimulus never call each
other" rule in [`../../README.md`](../../README.md), which is about feature
*matching*, not arithmetic helpers.

## `assertion_checkers.py` — the executable rules

Internal helpers `_safe` (ID-string sanitizer), `_read` (typed snapshot
lookup, raises `AssertionError` if the bound signal is missing from the
snapshot — a binding bug, not a DUT bug), `_transfer`/`_presented` (VALID·READY
vs. VALID-only), `_field` (named-field lookup with default), and `_fail`
(raises `AssertionError` with `feature=<id>; ...; related_signals=...;
observed=...` — the exact message shape every protocol assertion failure
uses) back every public function below.

- `check_stall_stability(snapshot, plan, state) -> dict[str, int]` — for each
  `plan["stalls"]` obligation (one per channel with both `valid`+`ready`
  bound and the `stall_stability` coverage tag), requires that once
  `valid ∧ ¬ready` is observed, `valid` stays high and every `content` signal
  (payload/last/keep/etc.) stays bit-identical until the transfer completes.
  Returns `{feature_id: stall_length}` for every stall that completed this
  cycle — `runtime.py::check_protocol_assertions` returns this dict onward,
  and `../../orchestration/instrumentation.py`'s generated `_check_contract_assertions`
  returns it as `completed_stalls` so coverage sampling (outside this folder)
  can bin the stall length without re-deriving it.
- `check_standard_signal_widths(snapshot, group, state)` — one-shot (gated by
  `state["widths_checked"]`) check that every bound VALID/READY is exactly
  1 bit, that fixed-width AXI control fields (LEN=8, SIZE=3, BURST=2, RESP=2,
  etc., per profile) match, that DATA is a power-of-two byte width (8–1024,
  or any byte-multiple for AXI4-Stream), that STRB/KEEP widths equal
  `data_width/8`, and that read/write data widths agree (and are 32 or 64 for
  AXI4-Lite).
- `check_axi4(snapshot, group, state)` — full AXI4 memory-map protocol:
  response-to-request ID matching against
  `state["pending_b"]`/`state["reads"]` (via `_matching_index`), EXOKAY only
  after a matching completed exclusive read (`state["exclusive_reads"]`),
  address-phase geometry via `_check_address` (delegates to `axi.py`), WLAST
  beat-count matching against AWLEN and WSTRB lane legality via
  `_check_write_pair`, and RLAST matching remaining-beat count. All AW/AR/W/B/R
  bookkeeping lives in `state` across calls (one call per sampled cycle).
- `check_axi4_lite(snapshot, group, state)` — the reduced single-beat
  protocol: legal `{OKAY, SLVERR, DECERR}` responses only (no EXOKAY), strict
  in-order AWID/ARID-vs-BID/RID matching against FIFO queues
  (`pending_b`/`pending_r`), and AW/W pairing by count rather than by burst
  framing.
- `check_axi4_stream(snapshot, group, state)` — TSTRB-is-subset-of-TKEEP,
  per-`(TID, TDEST)` open-packet tracking keyed in `state["open_packets"]`,
  and — only when the standard-protocol group's `capabilities.continuous_packets`
  is `True` — the continuous-packet constraints: the stream key cannot change
  mid-packet, every non-terminal beat must present full TKEEP, TSTRB must
  equal TKEEP (no position bytes), and the terminal TKEEP must be a
  contiguous low-byte prefix.
- `finalize_protocol_checker_state(plan, state)` — end-of-test gate. Raises if
  any stall is still open, or (per profile) any AXI4 `aw`/`w_current`/
  `w_bursts`/`pending_b`/`reads`, AXI4-Lite `aw_ids`/`pending_b`/`pending_r`/
  `w_count`, or AXI4-Stream `open_packets` bookkeeping is non-empty — a
  finite cocotb test may not end mid-transaction.
- `check_valid_low_during_reset(snapshot, reset, valid_signals, feature_ids)`
  — requires every bound VALID to be low while the plan's reset is active,
  after any contract-declared `reset_settle_cycles` on the reset signal
  (a signal-level key read by `pool/feature_plans/common.py::resolved_reset`; the
  current Architect response schema does not define it, so only hand-authored
  frozen contracts can set it);
  the feature ID used in the failure message comes from the plan's
  `valid_reset_features` mapping (falls back to
  `protocol.<signal>.valid_low_during_reset` if absent).

### The rule-name string coupling (read this before renaming anything)

`check_axi4`/`check_axi4_lite`/`check_axi4_stream` do **not** dispatch per
compiled feature — they unconditionally run every rule for their `profile`
string. The per-rule feature IDs that `feature_plans/protocol.py`'s matcher
generates (one `standard_protocol_rule` feature per name in
`role_pool/standard_protocols.yaml`'s per-profile `rules:` list — see
[`../../feature_plans/README.md`](../../pool/feature_plans/README.md)) are joined
back to this file only by **spelling**: e.g. the YAML's `axi4` profile lists
`no_4k_boundary_crossing`, `wrap_length_and_alignment`,
`write_strobe_within_active_lanes`, `response_after_request`,
`response_id_matches_request`,
`exclusive_access_restrictions`, `exclusive_response_consistency`,
`write_last_matches_length`, `read_last_matches_length`,
`legal_burst_encoding`, `legal_burst_length`, and
`transfer_size_within_data_bus` — and every one of those exact strings
reappears as the final segment of an `f"{feature_root}.<name>"` literal passed
to `_fail(...)` in `_check_address`/`check_axi4`. `standard_signal_widths` and
`valid_low_during_reset` instead match by dedicated function name
(`check_standard_signal_widths`, `check_valid_low_during_reset`).
**Nothing statically enforces this pairing.** Renaming a rule in
`standard_protocols.yaml` without updating the matching string literal here
does not raise an error; it silently breaks obligation-ID matching used by
coverage/obligation bookkeeping and by
`orchestration/instrumentation.py:validate_verifier_authored_structure`'s
`required_obligations` check.

Two former AXI4 entries intentionally do not appear in `rules:`.
`legal_response_encoding` was vacuous because RESP is two bits and all four
AXI4 encodings are legal; AXI4-Lite retains the meaningful
`legal_lite_response_encoding` rule that rejects EXOKAY.
`response_order_preserved_per_id` is a `driver_invariants:` entry instead:
identical same-ID write responses are not passively correlatable, while the
tool-owned `RandomCompletionScheduler` can and does serialize them.

`ready_valid_stability` is intentionally not a second group-level rule: the
resolved channel-level `stall_stability` feature is its executable form and
owns the concrete VALID/READY/content bindings. Full AXI's two-bit RESP also
has no `legal_response_encoding` target because all four encodings are defined;
AXI4-Lite keeps the distinct `legal_lite_response_encoding` rule, where EXOKAY
is forbidden. The feature-plan builder additionally omits read/write rules
when the resolved group lacks the corresponding channels and omits the
optional-ID rule when no response ID is physically bound.

## `runtime.py`

- `build_protocol_assertion_plan(interface_plan: Mapping[str, Any]) -> dict[str, Any]`
  — builds the inert plan embedded in the generated TB. Calls
  `feature_plan.py::build_protocol_feature_plan` then
  `compile_assertion_feature_plan`; extracts the `stall_stability` entries
  into a flat `stalls` list (`id`/`valid`/`ready`/`content` bindings only —
  the checker never re-reads the feature plan itself), resolves the reset
  binding's `signal`/`active_value`, builds `valid_reset_features` (signal →
  feature ID) from every `valid_low_during_reset` entry, and copies
  `bindings.standard_groups` through unchanged. Returns
  `{schema_version: 2, feature_plan, compiled_assertions, reset,
  reset_active_value, reset_settle_cycles, valid_signals, valid_reset_features,
  valid_reset_settle_cycles, stalls,
  standard_groups, features}`. **Called from**
  `../../orchestration/instrumentation.py:render_contract_generated_block` (via
  `protocol_assertion_metadata`, see `generator.py` below) and directly in
  `multigent/verifier_tool/tool_regression/unit/test_feature_plans.py` and
  `multigent/verifier_tool/tool_regression/integration/test_standard_axi_protocols.py`.
- `check_protocol_assertions(snapshot, plan, state) -> dict[str, int]` — the
  one per-cycle entry point. If the plan's reset is active, clears temporal
  state and runs `check_valid_low_during_reset` only after the declared
  settling cycles. The generated monitor also sends a reset-only rising-edge
  snapshot; that snapshot does not count as another output-sampling cycle.
  Otherwise it runs
  `check_stall_stability` (always) and, for every `plan["standard_groups"]`
  entry, `check_standard_signal_widths` plus the matching `check_axi4*`
  function selected by `group["profile"]`. **Called from**
  `../../orchestration/instrumentation.py`'s generated `_check_contract_assertions` (as
  `_contract_check_protocol_assertions`) inside `_contract_generated_monitor`,
  and directly in `multigent/verifier_tool/tool_regression/integration/test_standard_axi_protocols.py`.
- `finalize_protocol_assertions(plan, state)` — thin wrapper over
  `finalize_protocol_checker_state`. **Called from** the generated
  `_finalize_contract_assertions` (as `_contract_finalize_protocol_assertions`),
  itself invoked by `orchestration/runtime.py`'s per-test coverage wrapper after
  the `@cocotb.test()` body returns (it looks up
  `_finalize_contract_assertions`, falling back to
  `_finalize_contract_protocol_assertions`, from the test function's module
  globals).

## `generator.py`

- `protocol_assertion_metadata(interface_plan) -> tuple[dict[str, Any], tuple[str, ...]]`
  — thin wrapper: `(build_protocol_assertion_plan(interface_plan),
  plan["features"])`. **Called only from**
  `../../orchestration/instrumentation.py:render_contract_generated_block`.
- `render_protocol_assertion_lines(interface_plan, *, reset, obligations) -> list[str]`
  — renders `CONTRACT_PROTOCOL_ASSERTION_PLAN = <literal dict>`, one
  `# PROTOCOL ASSERTION [<feature>]` comment per obligation feature (audit
  trail only), and the two module-level wrapper functions
  `_check_contract_protocol_assertions(snapshot)` /
  `_finalize_contract_protocol_assertions()` that delegate straight into
  `check_protocol_assertions`/`finalize_protocol_assertions` imported from the
  facade. `interface_plan` and `reset` are accepted but unused (`del`d
  immediately) — the obligations mapping already carries everything needed;
  the parameters exist so the call site in
  `../../orchestration/instrumentation.py:render_contract_generated_block` can pass the same
  shape it passes to the lifecycle equivalent.
- `render_protocol_monitor_lines(*, clock, reset, assertion_callback="_check_contract_protocol_assertions") -> list[str]`
  — renders `_contract_generated_monitor(dut)`, the **single** cocotb
  coroutine that samples the interface once per clock edge and feeds both
  assertions and coverage from that one snapshot (the top-level README's "one
  clock observer shared by assertions and coverage"). On a falling/non-rising
  edge it takes a reset-only snapshot and calls
  `observe_contract_reset_snapshot`; on a rising edge it takes the full
  `CONTRACT_SIGNAL_NAMES` snapshot via `capture_contract_snapshot` and calls
  `sample_contract_snapshot(snapshot, assertion_callback)`. In the generated
  block, `assertion_callback` is bound to the combined
  `_check_contract_assertions` (protocol **and** lifecycle), not to this
  module's own `_check_contract_protocol_assertions` — the default parameter
  value only matters for direct unit-testing of this function. **Called only
  from** `../../orchestration/instrumentation.py:render_contract_generated_block`.

## Example: one `stall_stability` feature end to end

`feature_plans/protocol_features.yaml`:

```yaml
stall_stability:
  scope: channel
  match: {coverage_tag: stall_stability, required_roles: [valid, ready]}
  assertion: {checker: stall_stability}
  coverage:
    sampler: completed_stall_length
    bins:
      - {name: one_cycle_stall, range: [1, 1]}
      - {name: short_stall, range: [2, 4]}
      - {name: long_stall, range: [5, null]}
```

For channel `m_axi_ar`, this compiles (via `compile_assertion_feature_plan`)
to an entry with `id: channel.m_axi_ar.stall_stability`,
`implementation: stall_stability`, and `bindings: {valid: ..., ready: ...,
content: [...]}`. `build_protocol_assertion_plan` filters compiled entries by
`implementation == "stall_stability"` into
`plan["stalls"] = [{"id": "channel.m_axi_ar.stall_stability", "valid":
"m_axi_arvalid", "ready": "m_axi_arready", "content": ("m_axi_araddr", ...)}]`.
Every sampled cycle, `check_stall_stability` reads that one entry and raises
`AssertionError("feature=channel.m_axi_ar.stall_stability; producer-owned
content changed during stall or release; ...")` the instant `m_axi_araddr`
changes while `m_axi_arvalid=1 ∧ m_axi_arready=0`.

## See also

- [`../README.md`](../README.md) — the protocol domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — the
  generated TB block this subfolder's output is embedded into.
- [`../../lifecycle/assertion/README.md`](../../lifecycle/assertion/README.md),
  [`../../operation/assertion/README.md`](../../operation/assertion/README.md) — the other two
  assertion domains.
- [`../../feature_plans/README.md`](../../pool/feature_plans/README.md) — the
  Protocol Feature Plan matcher (`protocol.py`) and the shared resolved-plan
  shape every entry here is compiled from.
- [`../../operation_metadata/README.md`](../../pool/operation_metadata/README.md)
  — standard-protocol metadata (`channel.protocol_group`,
  `signal.protocol_field`) originates in the Architect contract compiled
  there, not in this subfolder.
