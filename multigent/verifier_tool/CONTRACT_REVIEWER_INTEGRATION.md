# Contract review: what to require, and what `verifier_tool` provides

This document is about the parts of `verifier_tool` that examine a frozen
contract (`architecture_contract`, `interface_contract`, `module_manifest`,
`acceptance_criteria`) without simulating anything. It says what a component
that reviews contracts must be required to do for the tool to work well, what the
tool provides for it, what the tool needs a contract to state explicitly, and
where each detail is documented. It does not describe how any pipeline, stage
order, or graph is organized; that is decided elsewhere and this surface is used
as-is inside it.

## What to require of whatever reviews a contract

These follow from how the tool resolves contracts:

1. **Use the tool's checks as the authority for deterministic findings.** Call
   `review_contract_deterministically` (or the individual validators below)
   instead of re-implementing role lists, tag grammars, or name heuristics. The
   tool never infers meaning from signal spelling or prose, so a review must not
   either.
2. **Read `capability_notes` (and `unrepresentable_operations`) as well as
   `findings`.** The facade blocks the operation-compilation defects an Architect can
   fix (check `operation_compilation`). A valid contract the tool cannot automate --
   for example an operation over an internal intermediate object -- stays `PASS` and
   is listed in `capability_notes`; that is a capability statement, not a defect.
3. **Keep capability states apart from contract defects.** A `False` from
   `automatic_campaign_support`, an `llm_extension` arithmetic profile, an
   unsupported serialization, or an `unreachable` bin is the tool describing its
   own coverage, not a defect to be fixed in the contract. Only the validators'
   strings/findings are contract defects (list below).
4. **Require the explicit items the tool resolves from** (section "What a contract
   has to state"): standard-protocol tags, base-pointer mappings, complete
   `lifecycle_policy`, `arithmetic`, `serialization`, and so on. Anything the
   tool cannot resolve unambiguously from those items is reported, never guessed.
5. **Route contract-local behavior through the extension mechanism.** Behavior
   absent from the closed pools is declared as a `verification_extensions[]`
   request (and local vocabulary under `verification_vocabulary`); the Architect
   side declares meaning and target only, and checker/coverage/stimulus code is
   Verifier-authored (see [`extensions/README.md`](extensions/README.md)). A review
   should not ask for checker code from the contract.

## Entry points

| Public name (from `multigent.verifier_tool`) | What it does | Documented in |
|---|---|---|
| `review_contract_deterministically(architecture, interface, module_manifest=None, acceptance_criteria=None, *, require_lifecycle_policy=True, require_operation_arithmetic=True)` | Runs the existing validators once and returns one structured report (below). No model call; never edits a contract. | [`contract_review/README.md`](contract_review/README.md) |
| `resolve_extension_reuse(architecture, interface)` | For every contract-local extension request, resolves which built-in features/helpers already exist for its exact target. | [`contract_review/README.md`](contract_review/README.md), [`extensions/README.md`](extensions/README.md) |
| the individual validators and compilers (table below) | The checks the facade is built from, usable separately. | per-row links |

## `review_contract_deterministically`

```python
{
  "schema_version": 1,
  "status": "PASS" | "BLOCKED",           # BLOCKED iff at least one finding
  "findings": [
    {
      "check_id": "standard_protocol_bindings",   # which check produced it
      "severity": "blocking",
      "owner": "architect_contract",
      "artifact": "interface_contract",
      "paths": [],                                 # currently always empty
      "message": "exact deterministic error text",
    },
  ],
  "resolved_extension_reuse": {...},              # resolve_extension_reuse output
  "capability_notes": [                           # never blocking; may be empty
    {"operation_name", "reason_code", "category", "owner", "affected_domains",
     "message", "resolution_hint", "blocked_by"},
  ],
}
```

Checks it runs, in order (`contract_review/preflight.py`): `contract_vocabulary`,
`extension_requests`, `signal_roles`, `interface_semantics`,
`standard_protocol_bindings`, `operation_features`, `lifecycle_policy`,
`operation_arithmetic`, `standard_protocol_plan`, `interface_coverage_plan`,
`operation_metadata` (catches a compile that raises), `operation_compilation` (the
blocking compile defects, one finding each); then `module_manifest_identity` (`module_manifest.top` must
name exactly one declared module) and `acceptance_criteria_shape` (a mapping or a
list) when those artifacts are passed; then `extension_reuse` and `extension_match`
(a request whose declared `match` requirements its exact target does not meet).
Findings are de-duplicated by `(artifact, message)`. A validator returning
`list[str]` yields one finding per string; one that raises
`ValueError`/`AssertionError`/`KeyError`/`TypeError` yields one finding with the
exception text.

Verified by running it, not only by reading it:

- **What `operation_compilation` blocks.** `build_architect_operation_metadata`
  compiles each operation as independent fragments and records every defect with a
  reason code, category and owner (see
  [`pool/operation_metadata/README.md`](pool/operation_metadata/README.md)). Only the
  codes in `ARCHITECT_BLOCKING_REASON_CODES` become findings: a data object carried
  by two same-direction channels (`ambiguous_transport_binding`) or only by the
  opposite direction (`data_object_channel_direction_mismatch`); a repeated
  `valid`/`ready`/`payload` on a data channel (`ambiguous_channel_signal_role`); a
  `ready_valid` data channel missing one of those roles
  (`missing_ready_valid_signal_roles`); two base pointers for one object, or an object
  on the wrong kind of memory channel (`ambiguous_base_pointer`,
  `memory_channel_kind_mismatch`); two `busy`/`completion`/`error` signals
  (`ambiguous_status_binding`); conflicting command-metadata tags
  (`conflicting_semantic_tags`); and every `control_plane_sequence` defect (policy
  without declaration, declaration nothing selects, an invalid declaration, no AXI4-Lite
  subordinate group to drive it). Each message reads `operation 'x' [reason_code]:
  ... -- <resolution hint>`. Before this check they surfaced only as an unrepresentable
  operation: the facade turns only list/exception results into findings, and the
  Architect's own reference validation never compiled operations.
- **What it does not block, and where it shows up instead.**
  - `tool_capability` causes (an operation over an internal, non-external data
    object; a repeated sideband role on a data channel) are valid contracts the tool
    cannot automate: `PASS`, listed in `capability_notes`.
  - A missing/invalid `lifecycle_policy` and arithmetic/serialization failures keep
    their own checks (`lifecycle_policy`, `operation_arithmetic`, with the
    `require_*` tolerance) and additionally appear as notes.
  - An unknown data object or data type, and an external object carried by no channel,
    are reported only by `ArchitectAgent._validate_contract_references` (the
    Architect's relational validator, which the facade does not run); the facade lists
    them as `contract_error` notes but does not block on them.
- **Not run by the facade:** the lifecycle plan builders and
  `automatic_campaign_support` (a blocked operation's lifecycle obligations are
  planned from its compile `shell`, see
  [`pool/feature_plans/README.md`](pool/feature_plans/README.md)).
- The two `require_*` keywords are passed to the lifecycle-policy and arithmetic
  validators. With `False`, an operation that has not declared the field is not an
  error; the facade never passes `previous_architecture`, so it does not check
  that a previously declared field was kept.
- Today only
  [`multigent/tests/test_tag_pool_and_contract_preflight.py`](../tests/test_tag_pool_and_contract_preflight.py)
  and `benchmark/frozen_contract_qualification.py` call the facade.

## `resolve_extension_reuse`

Returns `{schema_version: 1, entries: [...], diagnostics: [...]}`. Per request an
entry carries `request_id`, `domain`, `target`, `target_tags`,
`target_capabilities` (`roles`, `semantic_classes`, `protocol_profiles`, `tags`
available at that exact target), `match` / `match_satisfied` /
`missing_match_requirements` (`tags`, `roles`, `semantic_classes`,
`protocol_profiles`), `preserved_feature_ids` (resolved built-in features plus the
request's own `related_builtin_features`), `resolved_features` (id, kind, scope,
scope_name, tags), `helpers` (existing assertion checkers, coverage samplers, and
stimulus strategies among them), and `llm_owns_only_residual_feature: True`. A
domain that fails to build is reported in `diagnostics` rather than guessed.

## The individual checks

| Check | Public function | Result |
|---|---|---|
| signal role / direction / channel binding | `validate_interface_signal_roles(interface, *, role_extensions=...)` | `list[str]`, each a contract defect |
| semantic class / protocol profile | `validate_interface_semantics(interface, *, role_extensions=..., semantic_class_extensions=...)` | `list[str]` |
| contract-local vocabulary | `validate_contract_vocabulary(architecture, interface)` | `list[str]` (built-in collisions, unknown/unused local tags, domain/scope mismatches) |
| contract-local extension requests | `validate_architect_extension_requests(architecture, interface)` | `list[str]` |
| AXI4 / AXI4-Lite / AXI4-Stream / `custom_mmio` binding | `validate_standard_protocol_bindings(interface)` | `list[str]` |
| complete protocol plan | `compile_standard_protocol_plan(interface)` | plan; raises `ValueError` when incomplete or ambiguous |
| operation family / features | `validate_architecture_operation_features(architecture)` | `list[str]` |
| lifecycle policy selection | `validate_architecture_lifecycle_policies(architecture, *, require_policy=True, previous_architecture=None)` | `list[str]` |
| arithmetic and serialization declarations | `validate_architecture_operation_arithmetic(architecture, *, require_arithmetic=True, previous_architecture=None)` | `list[str]` (includes `packed_encoding` validation) |
| canonical operation metadata | `build_architect_operation_metadata(architecture, interface)` | `{operations, unrepresentable_operations, ...}`; per-operation failures are recorded (reason code, category, owner, every defect, and a planning `shell`), not raised |
| Architect-blocking compile defects | `validate_operation_compilation(architecture, interface)`; `blocking_compilation_errors(metadata)`; `compilation_capability_notes(metadata)` | `list[str]` / `list[dict]`; the facade's `operation_compilation` check and `capability_notes` are built from these |
| interface coverage derivability | `build_interface_coverage_plan(interface)` | plan; raises when obligations cannot be generated |
| lifecycle plans | `build_lifecycle_assertion_plan(interface_plan, metadata)`, `build_lifecycle_coverage_plan(interface, metadata)`, `build_lifecycle_stimulus_plan(interface, metadata)` | plans; a `control_plane_sequence` operation has no command channel, so its stimulus plan carries a `metadata_blocker` scenario and it gets no lifecycle coverage obligations |
| known-campaign capability | `automatic_campaign_support(metadata, architecture)` | capability report: per operation `supported`, `reasons`, `arithmetic_reasons`, `protocol_lifecycle_supported`; top level `supported`, `status`, `reasons`, `any_operation_supported` |
| frozen operation scope | `validate_frozen_operation_scope(architecture, specs)` | `list[str]` (a coverage obligation added after the declared scope was fixed) |

## Contract defect versus capability state

- **Reported as a contract defect** (validator strings / facade findings): unknown
  or duplicate signal role, a nonexistent channel reference, an incomplete AXI
  channel set, a missing or conflicting standard-protocol tag, a feature baseline
  that does not match the declared catalog family, a missing or partial
  `lifecycle_policy`, a malformed `arithmetic` or `serialization`, an extension
  request that does not match its target.
- **Reported as a capability state:**
  `automatic_campaign_support(...)["supported"] is False`;
  `arithmetic.classifier_profile: llm_extension` (`support_status:
  llm_extension_required`); a serialization the wire adapter cannot drive
  (`require_supported_serialization`); a drive-critical lifecycle extension field;
  canonical bins reported as `unreachable`, `metadata_missing`, or
  `llm_extension_required`.
- **Between the two:** `unrepresentable_operations` — the operation could not be
  compiled, so it gets not even the protocol/lifecycle smoke traffic an
  arithmetic-blocked operation gets. Its entry says which of the two it is:
  `category: contract_error` (owner `architect_contract`) or `tool_capability` (owner
  `verifier_tool`). Its contract-required lifecycle obligations stay in the coverage
  plan as required bins, so it can never pass silently.

## What a contract has to state for the tool to resolve it

- **Roles, semantic classes, protocol profiles:** one built-in role per signal, a
  semantic class where the role requires one, a profile per channel, all from the
  closed pools or from contract-local vocabulary under
  `architecture_contract.verification_vocabulary`. See
  [`pool/role_pool/README.md`](pool/role_pool/README.md) and
  [`pool/tag_pool/README.md`](pool/tag_pool/README.md).
- **Standard-protocol mapping (no name inference):** channel `metadata` carries
  `protocol_group=<group>` and `protocol_channel=<write_address|write_data|write_response|read_address|read_data|stream>`
  (`custom_mmio`: `request|data|response`); each mapped signal's `semantic`
  carries `protocol_field=<addr|len|size|burst|data|strb|last|resp|id|lock|cache|prot|qos|region|user|keep|dest>`;
  capabilities are `protocol_capability.<key>=<value>` (sets `a|b|c`, booleans
  `true|false`, integers literal). The current Architect JSON schema has no native
  `protocol_group` / `protocol_channel` / `protocol_field` property, so the tags
  are the carrying form; `enrich_standard_protocol_metadata` promotes them. A
  native value that differs from its tag, or two channels of one group declaring
  different values for one capability, is a blocking binding error. Details:
  `pool/role_pool/standard_protocols.py` / `.yaml`.
- **Operation semantics (integer GEMM profile):** resolvable M/N/K, data-object
  roles and canonical dimensions, product/accumulator/result types, reduction
  order and conversions, bias broadcast, the post-operation DAG, and an explicit
  `serialization` per data object. See
  [`pool/operation_metadata/README.md`](pool/operation_metadata/README.md).
- **Memory-mapped base pointers:** a command metadata signal tagged
  `data_object=<object> address_role=base byte_order=little
  address_sequence=contiguous word_stride_bytes=<n>`, or — for a
  `control_plane_sequence` operation with no command channel — a `write_reg`
  action in `operations[].lifecycle_control_plane_sequence.job_start.actions` with
  `value_from: {data_object, address_role: base, half: low|high|whole}` (the
  capture adapter needs a `low` and a `high` write per object).
- **`packed_encoding` objects:** `traversal`, optional `derived_axes`, and the
  `packed_encoding` block must reproduce the real wire layout; the encoder is
  input-only. See the `packed_encoding.py` section of
  [`pool/operation_metadata/README.md`](pool/operation_metadata/README.md).
- **Operation I/O binding:** every operation input/output is carried by exactly one
  channel of the matching direction (a memory-mapped object is listed only on its
  data channel, never on the address or response channel of its group); each
  `ready_valid` data channel has exactly one `valid`, `ready` and `payload`; at most one
  `busy`, `completion` and `error` signal; and the object is *external*. An operation
  over an internal intermediate object is a valid contract the tool reports as
  `tool_capability`, not an error.
- **Lifecycle:** a complete `lifecycle_policy` (every key a pool value or an
  `{extension_request: <id>}` reference whose request is in the lifecycle domain,
  targets the operation, and lists `/operations/<name>/lifecycle_policy/<field>`
  in `replaces_contract_paths`), plus a command channel with explicit integer
  `legal_values` and a representable `illegal_value`, or a
  `control_plane_sequence` declared as `operations[].lifecycle_control_plane_sequence`
  (an optional Architect-schema property, required exactly when `job_acceptance` or
  `completion_style` is the string `control_plane_sequence`, forbidden otherwise, and
  needing an AXI4-Lite subordinate group in the interface). Status signals are optional; their policies apply only
  when bound. See
  [`pool/lifecycle_policy_pool/README.md`](pool/lifecycle_policy_pool/README.md) and
  [`lifecycle/assertion/README.md`](lifecycle/assertion/README.md).
- **Reset timing:** an optional `reset_settle_cycles` on the reset signal delays
  the reset-output checks. The current Architect JSON schema has no such property,
  so only hand-authored frozen contracts carry it.

## Where the rest is documented

- Per-agent metadata surfaces: [`ARCHITECT_INTEGRATION.md`](ARCHITECT_INTEGRATION.md),
  [`VERIFIER_INTEGRATION.md`](VERIFIER_INTEGRATION.md),
  [`DEBUGGER_INTEGRATION.md`](DEBUGGER_INTEGRATION.md).
- Extension boundary and manifests: [`extensions/README.md`](extensions/README.md).
- How assertions, coverage, and stimulus are derived from a resolved contract:
  [`pool/feature_plans/README.md`](pool/feature_plans/README.md).
- Tool overview and ownership rules: [`README.md`](README.md).
