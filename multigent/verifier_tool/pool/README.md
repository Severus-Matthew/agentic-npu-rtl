# Pool

The three Architect-facing metadata pools plus the shared Feature Plan compiler.
Built-in pool entries are selected rather than invented, and the resolved record
shape is consumed by all three verification domains
([`../protocol/`](../protocol/README.md), [`../lifecycle/`](../lifecycle/README.md),
[`../operation/`](../operation/README.md)) consume:

- [`role_pool/`](role_pool/README.md) — signal roles, semantic classes,
  protocol profiles, and the exact AXI4/AXI4-Lite/AXI4-Stream/custom_mmio
  field-binding compiler (`standard_protocols.py`).
- [`lifecycle_policy_pool/`](lifecycle_policy_pool/README.md) — the closed
  set of lifecycle behavior choices (`job_acceptance`, `busy_behavior`,
  `completion_style`, etc.) and which are actually implemented.
- [`operation_metadata/`](operation_metadata/README.md) — the canonical
  operation/arithmetic metadata compiler: turns a frozen contract into
  machine-readable operation metadata, including
  `ReadyValidCaptureAdapter`, the protocol capture engine every memory-mapped
  operation binding is interpreted through.
- [`feature_plans/`](feature_plans/README.md) — the shared Resolved Feature
  Plan schema/compiler each of the three verification domains builds from
  independently.

[`diagnostics.py`](diagnostics.py) is the one small module the pools share: the
vocabulary for *why* an operation could not be compiled or automated. Each defect
carries a `reason_code` set where it is detected; `REASONS` maps it to a category
(`contract_error` — the Architect can fix it; `extension_required` — a Verifier
extension must supply it; `tool_capability` — a valid contract the tool cannot
automate), a default owner, the affected domains (`operation_io`, `arithmetic`,
`lifecycle`) and a resolution hint, and marks the few codes that go back to the
Architect (`ARCHITECT_BLOCKING_REASON_CODES`). It also defines the feature-level
`automation` record (`code_owned` | `verifier_extension_required` |
`tool_capability_required` | `contract_error`) and `summarize_feature_automation`,
which rolls feature records up to a per-domain `ready` / `partial` / `blocked`
state. It imports nothing from the pools, so every pool can use it without cycles.

Contract-local behavior absent from these built-ins belongs in
[`../extensions/`](../extensions/README.md), not in a runtime pool mutation.
That package preserves a normalized request and Verifier implementation bundle
for possible future qualification; it does not promote anything into this folder.

**Not a verification domain implementation.** Nothing here generates
assertions, coverage, or stimulus itself — that is what
[`../protocol/`](../protocol/README.md), [`../operation/`](../operation/README.md),
and [`../lifecycle/`](../lifecycle/README.md) do, each consuming what these
four pools compile. See [`../README.md`](../README.md) for how a frozen
contract flows through the pools into the three domains.
