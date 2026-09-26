# Deterministic Contract Reviewer preflight

This package is the tool-owned validation boundary for the future Contract
Reviewer stage. It makes no model/API call, does not edit contracts, and does not
implement pool promotion.

`review_contract_deterministically(...)` runs the existing authoritative
validators over the frozen architecture and interface contract and returns one
structured report:

```yaml
schema_version: 1
status: PASS | BLOCKED
findings:
  - check_id: signal_roles
    severity: blocking
    owner: architect_contract
    artifact: interface_contract
    paths: []
    message: exact deterministic error
resolved_extension_reuse: {...}
capability_notes:            # non-blocking: valid contracts the tool cannot fully automate,
  - operation_name: gemm     # and defects another validator above already reports
    reason_code: internal_data_object_not_channel_bound
    category: tool_capability          # contract_error | extension_required | tool_capability
    owner: verifier_tool
    affected_domains: [operation_io]
    message: ...
    resolution_hint: ...
    blocked_by: ["gemm:internal_data_object_not_channel_bound"]
```

The `operation_compilation` check compiles every operation
(`build_architect_operation_metadata`) and turns only the defects the Architect
can fix -- and that no earlier check already reports -- into blocking findings
(`ARCHITECT_BLOCKING_REASON_CODES`: an object carried by two same-direction channels,
a `ready_valid` channel missing valid/ready/payload, a `control_plane_sequence`
policy without its declaration, an invalid declaration, ...). A valid contract the
tool cannot automate (for example an operation over an internal intermediate
object) does **not** block: it is listed in `capability_notes` and the status stays
`PASS`. Defects owned by `lifecycle_policy` / `operation_arithmetic` are reported
once, by their own check, and also appear as notes.

The present Architect may use this facade as an early gate. When a dedicated
Contract Reviewer node is merged, that node should call the same public function
from `multigent.verifier_tool`; validation rules must not be copied into the
agent prompt or pipeline node.

The Role Pool exposes only protocol profiles that its current implementation can
handle. Candidate profiles are commented out in its YAML until implemented.
Therefore, `validate_interface_semantics` blocks an unsupported profile before
it can be mistaken for a verified built-in protocol. Contract-local protocol
behavior can still use the `custom` profile and an explicit Verifier extension.
Group targets work with both native `protocol_group` fields and the current
`protocol_group=<name>` metadata tag.

`resolve_extension_reuse(...)` is the complementary reuse resolver. For every
contract-local extension request it:

1. matches the exact target against declared tags, signal roles, semantic
   classes, and protocol profiles;
2. resolves applicable built-in Protocol, Lifecycle, or Operation features;
3. lists the existing assertion checkers, coverage samplers, and stimulus
   strategies that remain tool-owned; and
4. marks only the unsupported residual feature as LLM-owned.

The Verifier receives this resolved result in its extension worklist. Its bundle
must preserve every deterministically resolved feature ID. The same result is
stored in `feature_extension_manifest.yaml`, so later review and eventual
qualification/promotion work can audit what was reused and what was newly
authored without changing today's pools.
