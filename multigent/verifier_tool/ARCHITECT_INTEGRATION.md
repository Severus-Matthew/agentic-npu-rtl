# Architect-side: what to require, and what `verifier_tool` provides

This document is about the part of `verifier_tool` a contract producer
(currently `multigent/agents/architect.py`) works with. It says what the producer
must be required to state in a contract for the tool to work, what the tool
provides to it (schema fragments, validators, prompt renderers, compilers), how
the current code calls them, and where each detail is documented. It does not
describe how any pipeline, stage order, or graph is organized.

## What to require of the Architect

These follow from how the tool resolves a contract; each is checked by a function
named in the tables below.

1. **Use the tool's closed vocabularies.** Every signal has one built-in `role`
   (and a `semantic_class` where the role requires one); every channel has a
   `protocol_profile`; every operation selects a `coverage_family` and its
   `features`. Nothing is inferred from a name. A behavior the closed pools cannot
   express is declared once as an
   `architecture_contract.verification_extensions[]` request (meaning, exact
   target, observations) and, if it needs new roles/tags, under
   `architecture_contract.verification_vocabulary`. The Architect never writes
   checker, coverage, or stimulus code; the Verifier side does.
2. **Declare the tool-owned fields explicitly, with no defaults:**
   `operations[].lifecycle_policy` (every key from the Lifecycle Policy Pool, or an
   `{extension_request: <id>}` reference), `operations[].arithmetic` (a supported
   profile with every numeric and ordered post-operation rule, or `llm_extension`
   with a reason), and `data_objects[].serialization`. Old frozen contracts
   without them are rejected, not migrated.
   For generic channels whose producer must hold VALID low during reset, also
   select `interface_contract.reset_channel_policies` with explicit
   `settle_cycles`; generic ready/valid does not imply this policy, and a
   synchronous reset cannot safely be checked before its active clock edge.
3. **Encode protocol mapping and memory pointers as exact tags.** AXI4 /
   AXI4-Lite / AXI4-Stream / `custom_mmio` channels carry `protocol_group=`,
   `protocol_channel=` in `metadata` and `protocol_field=` in each signal's
   `semantic`; capabilities are `protocol_capability.<key>=<value>`. A memory base
   pointer is a command metadata signal tagged
   `data_object=<object> address_role=base byte_order=little
   address_sequence=contiguous word_stride_bytes=<n>`.
4. **State shapes and layouts that are fixed and exact.** The integer-GEMM profile
   needs fixed, resolvable dimensions; `serialization` states the transfer order
   (`index_order`, or a full `packed_encoding` declaration) rather than letting
   shape imply it; unsupported packing is declared `llm_extension` with the exact
   layout in `description`.
5. **Keep the contract self-consistent** for the reference validators (unique
   names, resolvable references, feature baselines matching the family). The
   validators return concrete strings; they do not repair.
6. **Do not rely on the tool to guess.** If a fact (legal command values, base
   pointer, word stride, response channel) is not stated explicitly, the tool
   reports it unresolved or leaves that operation unautomated.

## What the tool provides

### Schema composers (add tool-owned fields to the Architect response schema)

| Function | Adds |
|---|---|
| `with_lifecycle_policy_schema(schema, *, required=True)` | `operations[].lifecycle_policy` (built from the pool, plus the `{extension_request}` alternative), optional `operations[].lifecycle_control_plane_sequence`, and optional `interface_contract.reset_channel_policies` |
| `with_operation_arithmetic_schema(schema, *, required=True)` | `operations[].arithmetic`; `data_objects[].serialization` (kinds `dense_tensor`, `scalar`, `llm_extension`, `packed_encoding`) |
| `with_architect_extension_request_schema(schema, *, required=False)` | `architecture_contract.verification_extensions`, `architecture_contract.verification_vocabulary` |

Each composer navigates to a fixed JSON path
(`properties.architecture_contract.properties.operations.items`,
`...data_objects.items`, `...architecture_contract.properties`) and raises
(`LifecyclePolicyError` / `ArithmeticMetadataError` / `FeatureExtensionError`)
if it is absent. `required=False` lets old contract shapes still be read.

### Reference validators (return `list[str]` unless noted)

| Function | Checks |
|---|---|
| `validate_interface_signal_roles(interface, *, role_extensions=...)` | roles, channel binding, direction |
| `validate_interface_semantics(interface, *, role_extensions=..., semantic_class_extensions=...)` | semantic classes, protocol profiles |
| `validate_architect_extension_requests(architecture, interface)` | request identity, domain, target, semantics, replacement paths, vocabulary |
| `validate_architecture_operation_features(architecture)` | family and feature baselines |
| `validate_architecture_lifecycle_policies(architecture, *, require_policy=True, previous_architecture=None)` | explicit, complete, supported policy selections; a previously declared one cannot be removed |
| `validate_interface_reset_channel_policies(interface)` | generic-channel reset policy vocabulary, reset/VALID bindings, channel references, and non-duplication with standard protocol ownership |
| `validate_architecture_operation_arithmetic(architecture, *, require_arithmetic=True, previous_architecture=None)` | arithmetic declarations and every `data_objects[].serialization` (including `packed_encoding`) |
| `validate_standard_protocol_bindings(interface)` | exact AXI / custom_mmio tag binding |
| `validate_contract_vocabulary(architecture, interface)` | contract-local roles, semantic classes, tags |

### Prompt renderers (live catalogs, so the prompt matches the current tool)

`render_signal_role_catalog`, `render_interface_semantic_catalog`,
`render_operation_coverage_catalog`, `render_operation_assertion_catalog`,
`render_architect_metadata_format` (the static
`pool/operation_metadata/architect_metadata_format.yaml` text plus the live-rendered
lifecycle policy pool, arithmetic schema, and serialization schema), and
`render_architect_extension_request_guide`. `render_standard_protocol_metadata_format`
also exists but is not called by the current Architect prompt.

### Compilers and one-call review

`build_architect_operation_metadata(architecture, interface)` compiles the
contract into canonical per-operation metadata; an operation it cannot compile is
recorded in `unrepresentable_operations` (with a reason code, category, owner, every
defect found and a planning shell) instead of raising.
`validate_operation_compilation(architecture, interface)` returns the subset of those
defects only the Architect can fix (`operation 'x' [reason_code]: message -- hint`);
the two sides of that split are `blocking_compilation_errors(metadata)` and
`compilation_capability_notes(metadata)`.
`review_contract_deterministically(...)` and `resolve_extension_reuse(...)` are
described in [`CONTRACT_REVIEWER_INTEGRATION.md`](CONTRACT_REVIEWER_INTEGRATION.md).

## How the current Architect code calls it

`ArchitectAgent` (`multigent/agents/architect.py`):

- `load_output_schema` composes
  `with_architect_extension_request_schema(with_operation_arithmetic_schema(with_lifecycle_policy_schema(base)))`
  for the Architect output schema only.
- `_build_architecture_task` renders the catalogs above into the prompt.
- `_validate_contract_references(result, *, require_lifecycle_policy=True,
  require_operation_arithmetic=True)` runs, after the inline uniqueness/reference
  checks:

  ```python
  extension_errors = validate_architect_extension_requests(arch, interface)
  role_extensions, semantic_extensions = interface_vocabulary_extensions(arch)
  errors.extend(validate_interface_signal_roles(interface, role_extensions=role_extensions))
  errors.extend(validate_interface_semantics(interface, role_extensions=role_extensions,
                                             semantic_class_extensions=semantic_extensions))
  errors.extend(validate_architecture_operation_features(arch))
  errors.extend(validate_architecture_lifecycle_policies(arch, require_policy=require_lifecycle_policy))
  errors.extend(validate_interface_reset_channel_policies(interface))
  errors.extend(validate_architecture_operation_arithmetic(arch, require_arithmetic=require_operation_arithmetic))
  errors.extend(extension_errors)
  ```

  All errors are joined into one `ContractValidationError` that carries the
  offending candidate. `ArchitectAgent.run` passes both flags as `True`; no code
  in the repository passes `False` (only tests and the preflight's own keywords
  do).
- For a local revision (`multigent/orchestration/architect_node.py`) the patched
  contract is checked against a schema composed with `required=False`, then
  `validate_architecture_lifecycle_policies` and
  `validate_architecture_operation_arithmetic` run with
  `previous_architecture=` the prior contract (their `require_*` defaults stay
  `True`), then `_validate_contract_references` runs with its `True` defaults. A
  revised contract therefore still needs explicit `lifecycle_policy`, `arithmetic`,
  and `serialization` declarations.

## Field-by-field requirements

| What the Architect declares | Where | Owned by | Checked by |
|---|---|---|---|
| `signals[].role`, `signals[].semantic_class`, `channels[].protocol_profile` | `interface_contract` | [`pool/role_pool/`](pool/role_pool/README.md) (`interface_signal_roles.yaml`, `interface_semantic_classes.yaml`, `interface_protocol_profiles.yaml`) | `validate_interface_signal_roles`, `validate_interface_semantics` |
| `channels[].metadata` / `signals[].semantic` standard-protocol tags | `interface_contract` | [`pool/role_pool/`](pool/role_pool/README.md) (`standard_protocols.yaml`) | `validate_standard_protocol_bindings` (not called by `ArchitectAgent`; see gaps) |
| `operations[].coverage_family`, `coverage_family_source`, `features`, `feature_extensions` | `architecture_contract` | `operation/coverage/plan.py` families + [`pool/feature_plans/`](pool/feature_plans/README.md) | `validate_architecture_operation_features` |
| `operations[].lifecycle_policy` | `architecture_contract` | [`pool/lifecycle_policy_pool/`](pool/lifecycle_policy_pool/README.md) | `validate_architecture_lifecycle_policies` |
| `operations[].arithmetic` | `architecture_contract` | [`pool/operation_metadata/`](pool/operation_metadata/README.md) (`arithmetic_metadata.py`) | `validate_architecture_operation_arithmetic` |
| `data_objects[].serialization` | `architecture_contract` | [`pool/operation_metadata/`](pool/operation_metadata/README.md) (`io_metadata.py`, `packed_encoding.py`) | `validate_architecture_operation_arithmetic` (`declared_serialization`) |
| `verification_extensions[]` | `architecture_contract` | [`extensions/`](extensions/README.md) | `validate_architect_extension_requests` |
| `verification_vocabulary` (optional local `tags`, `signal_roles`, `semantic_classes`) | `architecture_contract` | [`pool/tag_pool/`](pool/tag_pool/README.md) | `validate_contract_vocabulary` (called inside `validate_architect_extension_requests` and the preflight) |

### Signal roles and semantics

One built-in `role` per signal from `pool/role_pool/interface_signal_roles.yaml`;
a `semantic_class` from `interface_semantic_classes.yaml` when the role is
`payload` or `metadata`; a `protocol_profile` per channel from
`interface_protocol_profiles.yaml`; an explicit `active-high` / `active-low`
reset semantic. A genuinely missing role, class, or tag is declared under
`architecture_contract.verification_vocabulary` (the older
per-request `contract_vocabulary` is still read for frozen contracts); it is
validated locally and never mutates a pool. See
[`pool/role_pool/README.md`](pool/role_pool/README.md).

### Operation feature taxonomy

`coverage_family` + `coverage_family_source` (`catalog` or `novel`) select a known
family (whose complete baseline must appear in `features`; `feature_extensions`
adds optional concepts whose `applies_when` the contract actually satisfies) or
declare a new family with explicit `features`. `operations[].feature_extensions`
(optional catalog concepts) is distinct from
`architecture_contract.verification_extensions` (behavior absent from the pools).

### Lifecycle policy

A complete `lifecycle_policy` per operation: `job_acceptance`, `job_overlap`,
`busy_behavior`, `completion_style`, `completion_timing`,
`illegal_command_behavior`, `error_style`, `error_timing`, `reset_behavior`; each
either a pool value or `{extension_request: <id>}` naming a lifecycle-domain
request that targets the same operation and lists that exact path in
`replaces_contract_paths`. `job_acceptance` / `completion_style:
control_plane_sequence` (with `completion_timing: observed_via_poll`) also need an
`operations[].lifecycle_control_plane_sequence` declaration -- an optional property of
the effective Architect schema, required exactly when either field is the string
`control_plane_sequence` (an `{extension_request: ...}` value neither demands nor
satisfies it), forbidden otherwise, and needing an AXI4-Lite *subordinate* (control)
channel group in the interface. Its shape (`registers`, `job_start.actions`,
`job_complete.actions`; actions `write_reg` / `write_field` / `read_reg` /
`poll_field`) is rendered into the prompt; the rules and reason codes are in
[`pool/lifecycle_policy_pool/README.md`](pool/lifecycle_policy_pool/README.md).

### Operation I/O binding

Each operation input/output must be carried by exactly one channel of the matching
direction: a memory-mapped (AXI4 / AXI4-Lite / `custom_mmio`) object is listed only on
its data channel (`read_data` / `write_data`), never on the address or response
channel of its group. Each `ready_valid` data channel needs exactly one `valid`,
`ready` and `payload`; the contract binds at most one `busy`, `completion` and `error`
signal; and an object an operation consumes or produces must be external (channel-
carried). Violations are returned by `validate_operation_compilation` and reject the
contract in `_validate_contract_references`. An operation over an *internal*
intermediate object is not an Architect error: it is a valid contract the tool cannot
automate (`tool_capability`), reported in `unrepresentable_operations` and the
preflight's `capability_notes`; an operation whose inputs and outputs are all
channel-carried is what the tool can bind.

### Arithmetic

`classifier_profile: integer_matrix_multiply` with the full compact declaration
(`post_operations` is a DAG of named stages; built-in stages may be combined
with formula-defined `llm_defined` stages that the Contract Reviewer must
successfully compile into solver IR), or
`classifier_profile: llm_extension` with `reason` and a top-level
`operation.semantics`. Exclusive with a full `verification_metadata` on the same
operation. See
[`pool/operation_metadata/README.md`](pool/operation_metadata/README.md#example-compact-declaration).

The Architect owns the mathematical formula and DAG order, not coverage bins.
If solver compilation fails, revise the formula. Use `llm_extension` only when
the operation is intentionally outside the deterministic solver model.

### Object serialization

`kind` is `scalar`, `dense_tensor`, `llm_extension`, or `packed_encoding`;
`index_order` (all kinds but `packed_encoding`) and `description` are required.
`packed_encoding` instead declares `traversal`, `packed_encoding`, and optional
`derived_axes`. The executable wire adapter is stricter than the schema: canonical
order dense tensors, scalars, and the generic `packed_encoding` engine are driven
and captured automatically; another declared order forces `llm_extension_required`
for that binding. A `packed_encoding` object can be encoded for input only. See
[`pool/operation_metadata/README.md`](pool/operation_metadata/README.md#io_metadatapy--explicit-serialization-never-inferred-from-shape).

### Standard-protocol tags and base pointers

`protocol_group=<group> protocol_channel=<kind>` on channel `metadata`;
`protocol_field=<field>` on signal `semantic`; optional
`protocol_capability.<key>=<value>`. `custom_mmio` reuses the grammar with the
kinds `request` / `data` / `response`. A base pointer is a command metadata
signal tagged as in item 3 above; for a `control_plane_sequence` operation with no
command channel the compiler derives the same facts from the declared
`job_start.actions[].value_from`. See
[`pool/role_pool/README.md`](pool/role_pool/README.md) and
[`pool/operation_metadata/README.md`](pool/operation_metadata/README.md#architect_metadatapy--the-compiler).

## Known gaps between the tool and the current Architect schema/prompt

- `validate_standard_protocol_bindings` is not called from
  `_validate_contract_references`; tag errors surface when something calls
  `compile_standard_protocol_plan` (or the preflight's `standard_protocol_bindings`
  check). `render_standard_protocol_metadata_format` is not rendered into the
  prompt.
- The effective Architect response schema exposes `lifecycle_policy` and the optional
  `operations[].lifecycle_control_plane_sequence` property, but has no
  `reset_settle_cycles` signal property and no native `protocol_group` /
  `protocol_channel` / `protocol_field` properties. The metadata compiler honors
  `reset_settle_cycles` when present in a hand-authored contract, and promotes the
  protocol tags. The provider call sends the schema with `strict: true`; the new
  property uses the same constructs the schema already contains (`anyOf`, an object
  map, optional properties) and no `oneOf`, but acceptance by a live provider has not
  been exercised here (no API call was made).
- The prompt prose in `_build_architecture_task` still describes `serialization` as
  `kind` / `index_order` / `description` with `llm_extension` for unsupported
  packing, while the live-rendered schema also offers `packed_encoding`. The static
  `architect_metadata_format.yaml` text likewise predates it
  (`kinds: [dense_tensor, scalar, llm_extension]`); it does now describe the
  control-plane declaration and renders its schema.

## Watch-outs

- The three composers hardcode the JSON paths above; a restructured Architect
  schema makes them raise rather than skip.
- A new value in `lifecycle_policies.yaml` is refused at load time unless
  `policies.py::_IMPLEMENTED_CHOICES` also lists it; a pool value only counts once
  its checker, sampler, driver, and tests exist.
- `build_architect_operation_metadata` reports an uncompilable operation through
  `unrepresentable_operations`, not an exception; callers that need to fail on it
  must read that key. The defects an Architect can fix (channel/data-object binding,
  `control_plane_sequence` declaration) are additionally rejected by
  `_validate_contract_references` and the preflight; a `tool_capability` cause is not.
  A revision is validated by the same gate, so a frozen contract that carried such a
  defect silently now fails any revision -- including a no-edit confirmation.
- The local-revision patch can flip a scalar leaf but can neither add nor remove a
  whole object or list entry. A compile defect whose only fix is structural (add the
  missing `lifecycle_control_plane_sequence`, remove an object from a channel's
  `data_objects`) is therefore reported precisely but cannot be repaired by a patch;
  it needs a full regeneration.
- Operation names must stay unique: two operations with one name produce duplicate
  feature IDs in any lifecycle plan, compiled or not.
- The prompt renderers only render data; the surrounding instructions live in
  `ArchitectAgent._build_architecture_task` and
  `Skills/npu_multiagent_skills/skills/architect/SKILL.md`.
