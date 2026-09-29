# Lifecycle Policy Pool

This pool defines **how a job behaves**. The Lifecycle Feature Catalog defines
**how that behavior is verified**. Signal names still come from role bindings.

The YAML is the source of supported choices. `policies.py` provides validation,
the JSON Schema fragment, prompt rendering, and explicit policy validation.
All public imports are available from `multigent.verifier_tool`.

## Architect selection

The required field for new Architect outputs is `operations[].lifecycle_policy`:

```yaml
lifecycle_policy:
  job_acceptance: valid_ready_handshake
  job_overlap: single_inflight
  busy_behavior: tracks_active_job
  completion_style: pulse
  completion_timing: next_cycle_after_retirement
  illegal_command_behavior: error_without_start
  error_style: pulse # or sticky_until_reset
  error_timing: next_cycle_after_error_event
  reset_behavior: abort_inflight
```

When supplying the complete `operation.verification_metadata`, put the selection
at `verification_metadata.lifecycle.policy` instead. Do not declare two sources.
The compiler checks for disagreement if both are supplied.

Every policy key is required in an explicit selection. Each value is either an
implemented built-in choice or an exact contract-local reference:

```yaml
error_style:
  extension_request: lifecycle.error_three_cycle_pulse
```

The referenced item must exist in
`architecture_contract.verification_extensions[]`, belong to the lifecycle
domain, target this same operation, and list the exact replaced policy path.
Unknown bare strings and conflicts with command acceptance or reset disposition
remain errors. Busy/completion/error policies govern the corresponding status
signal when that role is bound; choosing a policy does not invent a missing
signal.

### Channel behavior during reset

A generic `ready_valid` or `custom` channel does not, by itself, say what its
producer does during reset. When the contract requires reset quiescence, the
Architect states it explicitly in the interface contract:

```yaml
reset_channel_policies:
  - channels: [result, status_stream]
    behavior: valid_deasserted
    settle_cycles: 1  # synchronous reset; use 0 when the contract guarantees async clearing
```

`with_lifecycle_policy_schema()` exposes this optional
`interface_contract.reset_channel_policies` field from the same lifecycle pool.
`resolve_reset_channel_policies()` then checks that every channel exists, has
exactly one `valid` role binding, is listed at most once, and that the interface
has one reset signal with explicit active-high/active-low semantics. The resolved
protocol feature is channel-scoped and uses the existing
`valid_low_during_reset` checker and `reset_assert_release` stimulus strategy.
`settle_cycles` is mandatory because observation on the first asserted-reset
snapshot may precede the active clock edge for a synchronous reset. The checker
therefore begins only after the declared number of sampled reset cycles.

AXI4, AXI4-Lite, AXI4-Stream, and `custom_mmio` already define this behavior in
their standard protocol rule set. Listing one of their channels here is rejected
as duplicate ownership, which prevents duplicate assertions and preserves the
existing `protocol.<group>.valid_low_during_reset` diagnostics. Omitting the field
for a plain `ready_valid` channel makes no reset assumption.

## Implemented choices

`lifecycle_policies.yaml` is the source of supported values; `policies.py`'s
`_IMPLEMENTED_CHOICES` is a second, code-side guard that fails pool loading if
the YAML exposes a value with no implemented behavior. Current values:

| Policy | Values |
|---|---|
| `job_acceptance` | `valid_ready_handshake`, `control_plane_sequence` |
| `job_overlap` | `single_inflight` |
| `busy_behavior` | `tracks_active_job` |
| `completion_style` | `pulse`, `control_plane_sequence` |
| `completion_timing` | `next_cycle_after_retirement`, `observed_via_poll` |
| `illegal_command_behavior` | `error_without_start` |
| `error_style` | `pulse`, `sticky_until_reset` |
| `error_timing` | `next_cycle_after_error_event` |
| `reset_behavior` | `abort_inflight` |

The pool also currently exposes one interface-level channel reset behavior:
`valid_deasserted`.

The three completion-transport fields are a coherent tuple, not independent
mix-and-match enums. Built-in behavior accepts exactly these combinations:

- `valid_ready_handshake` + `pulse` + `next_cycle_after_retirement`
- `control_plane_sequence` + `control_plane_sequence` + `observed_via_poll`

`resolve_lifecycle_policy()` rejects every other all-built-in combination as
`lifecycle_metadata_contradiction`. If any of the three fields is an
`extension_request`, that field's Verifier-owned bundle is responsible for the
new relationship and the built-in tuple check does not guess it.

## `control_plane_sequence` — register-started jobs on a black-box control bus

`job_acceptance: control_plane_sequence` (and its companions
`completion_style: control_plane_sequence`, `completion_timing:
observed_via_poll`) describe an accelerator with **no** ready/valid command
channel and **no** dedicated completion pin: the job is started, and its
completion is observed, only through AXI4-Lite register transactions (for
example a Vitis HLS `ap_ctrl_chain` block, whose `ap_start`/`ap_done` are
internal wires). Such an operation must also carry a
`control_plane_sequence` declaration beside `policy`; `resolve_lifecycle_policy()`
raises if it is missing when either `job_acceptance` or `completion_style`
selects the value, and raises if it is present when neither does.

Abridged illustration (the full real sequence, which also writes `ap_continue`
before the pointer registers, is in
`benchmark/int8_gemm_hls_golden/architecture_contract.yaml`, key
`operations[].lifecycle_control_plane_sequence`):

```yaml
control_plane_sequence:
  registers:                        # name -> address (+ optional bit fields)
    ap_ctrl: {address: 0x00, fields: {ap_start: {bit: 0}, ap_done: {bit: 1}}}
    a_ptr_low:  {address: 0x10}
    a_ptr_high: {address: 0x14}
  job_start:
    actions:                        # ends in write_reg / write_field
      - {op: write_reg, register: a_ptr_low,  value_from: {data_object: A_matrix, address_role: base, half: low}}
      - {op: write_reg, register: a_ptr_high, value_from: {data_object: A_matrix, address_role: base, half: high}}
      - {op: write_field, register: ap_ctrl, field: ap_start, value: 1}
  job_complete:
    actions:                        # exactly one poll_field, and it is last
      - {op: poll_field, register: ap_ctrl, field: ap_done, expected: 1}
```

The vocabulary is closed (`control_plane_sequence.py`): only `write_reg`,
`write_field`, `read_reg`, and `poll_field` exist, with no eval/exec and no
LLM-authored code. `validate_control_plane_sequence()` enforces: unique
register addresses and unique bit positions within a register; every action
names a declared register (and declared field, for `write_field`/`poll_field`);
each `write_reg.value_from.data_object` must be one of that operation's own
input/output objects (skipped only when the caller passes
`known_data_objects=None`); `job_start.actions` must end in a `write_reg` or
`write_field` (the completing transaction is what fires the JOB_START event,
never a poll); and `job_complete.actions` must contain exactly one
`poll_field` and end with it (its success fires JOB_COMPLETE).
`value_from.half` is `low`, `high`, or `whole`.

Consequences elsewhere in the tool (all verified in code, not aspirational):

- There is no command opcode, so legal/illegal command values do not exist for
  this source. `job_accept_channels` is built from the interface (a channel whose
  payload has the `command` semantic class); for the HLS benchmark interface it
  is empty. When it is empty, the metadata compiler synthesizes each memory
  object's base-pointer fields (`byte_order: little`, `address_sequence:
  contiguous`, `word_stride_bytes` = bus width in bytes) from
  `job_start.actions[].value_from` instead
  (`architect_metadata.py::_control_plane_sequence_pointer_fields`).
- Lifecycle event detection is the stateful AXI4-Lite tracker in
  `lifecycle/assertion/control_plane_sequence_tracker.py`; stimulus is
  `lifecycle/stimulus/cocotb.py::drive_control_plane_sequence`.
- `observed_via_poll` is intentionally weaker than
  `next_cycle_after_retirement`: completion is known only at the granularity of
  a register read. The lifecycle checker compensates externally — a successful
  `job_complete` poll is a failure if it occurs before the declared output
  beats **and** their final successful write response have retired
  (`completion_matches_final_output`; see
  [`../../lifecycle/assertion/README.md`](../../lifecycle/assertion/README.md)).
- `feature_plans/lifecycle.py::_coverage_obligations` and
  `lifecycle/stimulus/stimulus_generator.py` both require exactly one command
  channel with legal values, so a control-plane operation currently receives
  **no** `job_lifecycle` / `reset_abort_phase` / `post_reset_purity` coverage
  obligations, and its lifecycle stimulus plan reports a `metadata_blocker`
  scenario ("operation needs exactly one command-accept channel"). Its
  lifecycle *assertions* are still selected and run; the command-legality
  checkers among them simply have no command events to observe.
- The automatic campaign path is
  `orchestration/campaign.py::run_code_owned_axi4_operation_case_via_control_plane_sequence`
  (see [`../../orchestration/README.md`](../../orchestration/README.md)).

**Where it can be declared.** `resolve_lifecycle_policy(lifecycle, signals=(),
*, data_object_names=None)` reads `lifecycle.control_plane_sequence`. The
compact form is `operations[].lifecycle_control_plane_sequence`, which
`architect_metadata.py::_attach_lifecycle_policy` copies into that key (a
disagreement with `verification_metadata.lifecycle.control_plane_sequence` is
an error). The Architect can now supply it: `with_lifecycle_policy_schema` composes an
**optional** `operations[].lifecycle_control_plane_sequence` property (the
tool-owned `control_plane_sequence_schema()`, with a description saying when to
use it) beside `lifecycle_policy`. It is optional in the JSON schema because
"required iff a policy field equals `control_plane_sequence`" cannot be expressed
in a provider-safe schema, so the compile enforces it (`architect_blocking` codes,
reported by `validate_operation_compilation`, which
`ArchitectAgent._validate_contract_references` calls, and by
`review_contract_deterministically` through the same `blocking_compilation_errors`
split):

| Situation | Reason code |
|---|---|
| `job_acceptance` or `completion_style` is exactly `control_plane_sequence`, declaration absent | `control_plane_sequence_required_but_missing` |
| declaration present, but neither field selects `control_plane_sequence` | `control_plane_sequence_unused` |
| declaration violates the schema (missing/extra key, unknown action op, wrong type, empty list) | `control_plane_sequence_schema_violation` (message names the offending field per action variant) |
| two registers share an address, or two fields of one register share a bit | `control_plane_sequence_address_collision` |
| an action names an undeclared register/field, or `value_from.data_object` is not one of the operation's own inputs/outputs | `control_plane_sequence_unknown_reference` |
| `job_start` does not end in `write_reg`/`write_field` | `control_plane_sequence_bad_start_action` |
| `job_complete` does not have exactly one `poll_field`, as its last action | `control_plane_sequence_bad_completion_poll` |
| valid declaration but the interface has no AXI4-Lite **subordinate** (control) group | `control_plane_requires_axi4_lite_subordinate` |

"Exactly `control_plane_sequence`" means the string: an `{extension_request: ...}`
reference is a different value, so it neither demands nor satisfies the
declaration. The action variants are expressed with `anyOf`, not `oneOf`
(provider structured-output schemas reject `oneOf`); they are mutually exclusive
through their `op` value (a one-value `enum`, so the fragment adds no JSON-schema
keyword the rest of the Architect schema does not already use), and a fuzz test
pins that acceptance is identical to the old `oneOf` schema. `ControlPlaneSequenceError` and `LifecyclePolicyError` carry a
`reason_code` set at each raise site (see [`../diagnostics.py`](../diagnostics.py)).
The compact form and `verification_metadata.lifecycle.control_plane_sequence` may
not disagree (`lifecycle_policy_conflict`, hand-authored contracts only).

One consequence to know about: the Architect's *local revision* patch can flip a
scalar policy choice but cannot add or remove a whole object, so a revision that
selects `control_plane_sequence` without an existing declaration is rejected with
`control_plane_sequence_required_but_missing` rather than repaired in place.

## Connection to execution

`build_architect_operation_metadata()` validates the selection and stores it in
`lifecycle.policy`. `build_lifecycle_feature_plan()` carries the resolved policy
and provenance into all three compiled branches. Runtime assertions use the
selected error style; stimulus planning distinguishes pulse recovery from reset
clearing, and the cocotb campaign resets before retrying after a sticky error.
The built-in choices currently each have one implemented behavior, enforced by
the existing lifecycle checkers. A contract-local reference delegates only the
dependent assertion, coverage, and stimulus work to the Verifier; unaffected
sibling lifecycle features stay tool-owned. Drive-critical extensions such as
job acceptance or completion timing disable the automatic lifecycle drive path
for that operation, while non-drive-critical extensions preserve the safe known
campaign scope.

Existing frozen contracts without an explicit policy are rejected. The old legacy
adapter and its default policy map have been removed. `resolve_lifecycle_policy()`
only accepts explicit selections; it never guesses sticky error behavior from prose.

## Architect schema integration

The Architect uses `with_lifecycle_policy_schema()` when loading its response
schema. The built-in choices, the `{extension_request: ...}` alternative, and
the optional `interface_contract.reset_channel_policies` field are injected
directly from the pool into the schema used to validate the response.
They are not copied into the base `architect_output.schema.json` file. The shared
runtime exposes a generic `load_output_schema()` hook; only Architect composes
this extension.

```python
from multigent.verifier_tool import with_lifecycle_policy_schema

effective_schema = with_lifecycle_policy_schema(base_architect_schema)
```

New initial output must include every policy field. Architect's reference check
also calls `validate_architecture_lifecycle_policies()` before persisting READY.
Local revision schema composition permits reading old shapes, but semantic
validation requires explicit policies before acceptance. Missing, unsupported,
and incomplete selections fail. This does not expand the local
patch permissions or change pipeline routing.

`render_architect_metadata_format()` includes the policy pool automatically, using
the existing prompt integration. The prompt now requires the compact field and
explains the explicit-declaration requirement for initial outputs and revisions.
To validate a candidate's canonical bindings without simulation,
call `build_architect_operation_metadata(architecture_contract, interface_contract)`.

## Extending supported policies

Adding a YAML value alone does not implement a new built-in behavior. Add its
assertion, observed-event coverage, and stimulus behavior, test valid and invalid
traces, then expose the choice in the pool. For one contract, use a normalized
extension request and Verifier bundle instead. The saved bundle is deliberately
contract-local: mutation testing, qualification, and pool promotion are future
work and are not performed automatically.
