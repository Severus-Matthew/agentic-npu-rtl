# Reusable component registry

This package separates **what the DUT contract means** from **which verifier
implementation can execute that meaning**.

## Ownership boundary

1. Architect writes observable behavior and interface capabilities. It does not
   select Python driver names.
2. Contract Reviewer validates that the frozen contract is internally
   consistent. It does not decide implementation reuse.
3. Verifier Tool resolves reusable components from checked-in manifests.
4. Verifier implements only the unresolved, contract-local behavior. It may use
   retrieved components as examples, but examples never override the contract.

The resolver produces three explicit sets for each extension request:

- `automatic_reuse`: structurally compatible catalog entries that cover a
  requested capability;
- `residual_capabilities`: required behavior not covered by those entries;
- `rag_component_references`: nearby implementations that may be useful as
  shapes but are not compatible enough to call automatically.

Automatic reuse is divided by execution ownership:

- `required_reuse_component_ids` are called explicitly by a reachable generated
  test/helper and must appear in `reuse.helpers`;
- `pipeline_managed_reuse_component_ids` are already installed by the
  contract-generated block and must not be instantiated again by the LLM.

Every selected or retrieved entry includes a generated `call_contract` containing
the normative import, inspected Python signature, required ABI parameters, and
invocation shape for this run. Runtime validation checks explicit reuse against
the exact entrypoint. This prevents an LLM from merely claiming reuse in YAML
while reimplementing or never calling the component.

An ABI may also declare code-owned `semantic_constraints` for non-vacuous use.
The generated call contract exposes them to the Verifier, and structural review
enforces them on the reachable call. For example,
`transaction_completion_payload_v1` requires nonempty independent expected
payloads, forbids disabling activity or completion checks, and requires the
returned `passed` field to be asserted. Mixed request types may additionally
pass a per-request `payload_required` mask; false entries skip only the payload
comparison, not the matching completion requirement. Calling a helper while discarding or
deliberately neutralizing its decision is therefore not counted as reuse.

Contract-bound components may also carry `runtime_bindings`. For the generic
custom-event source driver this lists the exact profile/transaction names and a
generated-block accessor such as
`_contract_protocol_event_transaction('wishbone_b4_pipelined',
'wishbone_request')`. Adding another semantic profile changes data in this list;
it does not require a prompt or resolver branch for that protocol name.

Cross-protocol extensions can name a standard participant in
`related_builtin_features` (for example `axi4`). The resolver accepts that name
as binding context only when the frozen interface actually contains that exact
standard profile. A pure bridge can then reuse
`protocol.driver.axi4_protocol_responder` through a binding such as
`_contract_standard_protocol_group('axi', 'axi4')`; unlike the operation AXI
memory driver, this responder needs no tensor or data-object metadata. The
extension still owns only the residual mapping between the two protocol sides.

The generic source driver and runtime evidence collector are separate on
purpose. `protocol.driver.contract_event_source` returns beats accepted by the
source-side event; it does not claim that those beats are a complete cycle
trace. `protocol.monitor.contract_event_trace` runs concurrently with
contract-local stimulus and returns a stable evidence object containing
`cycle_trace`, `transaction_trace`, and `stimulus_result`. Its optional
`signal_names` argument adds cross-protocol fields to every real DUT snapshot,
so a bridge extension can inspect both boundaries without fabricating an
expected trace. Runtime bindings for the source driver include only
transactions with `source_drive` metadata, while monitor bindings include both
DUT-input and DUT-output transactions. This lets a multi-clock bridge attach
one recorder to each contract-declared clock domain without pretending the
destination side is testbench-driven.

When a resolved monitor component contains more than one runtime binding, use
`capture_protocol_event_traces`. It starts one recorder per binding on that
binding's contract-declared clock, then runs one shared stimulus coroutine.
The returned mapping keeps the per-domain traces separate while proving they
came from the same transaction window. Sequentially replaying a stimulus once
per clock domain is not equivalent and is rejected by structural validation.

`protocol.assertion.transaction_completion_payload` is the protocol-independent
completion-data checker selected when an extension requires response/completion
payload semantics. It consumes the code-owned transaction trace, FIFO-pairs each
`accepted` request with a selected completion event (FIFO by default, or by an
optional request/completion key for out-of-order protocols), and compares the payload
sampled in that same completion record against independently computed expected
payloads. It rejects zero-activity/vacuous evidence, completion without a request,
missing same-cycle payload, payload mismatch, expected-count mismatch, and an
accepted request left incomplete. Ordinary campaign timeout remains responsible
for the separate “no response ever arrived” failure; this component does not add
a second timeout mechanism.

## Manifest format

Catalog YAML files live in `catalog/`. Each component declares:

```yaml
- id: protocol.driver.role_bound_source
  component_type: protocol_source_driver
  abi: role_bound_channel_source_v1
  entrypoint: multigent.verifier_tool.protocol.stimulus.cocotb:drive_protocol_transfers
  execution_owner: verifier_extension
  domains: [protocol, lifecycle]
  supported_profiles: ['*']
  required_roles: [valid]
  supported_directions: [input]
  capabilities: [handshake, request_grant, backpressure, stall_schedule]
  auto_reuse: true
  requires_protocol_semantics: false
  requires_protocol_event_relations: false
```

Manifests are code-owned. Their IDs, component types, ABIs, entrypoints, and
list fields are validated before selection. Entrypoints are restricted to the
`multigent.verifier_tool` package.

`required_architecture_sections` prevents an operation-oriented driver or adapter
from being selected for a protocol-only contract that cannot supply its ABI. For
example, the AXI memory-job driver requires nonempty operation metadata; it remains
a RAG reference for a pure bridge contract rather than becoming false automatic
reuse.

`protocol.driver.axi4_protocol_responder` is the complementary pure-protocol
component. It accepts explicit bounded read/write request counts, configurable
response data/codes, optional repeating request-channel pause patterns, and
returns handshake-derived evidence. The pause patterns let generated tests
exercise read-address, write-address, and write-data backpressure without
directly driving READY signals already owned by the responder. It is selected for
an AXI4 participant only when the interface has a complete compiled manager
group; it never fabricates an operation or address-object mapping.

`requires_protocol_semantics: true` guards the generic custom-event driver and
transaction-accounting checker. A wildcard profile is not sufficient for
automatic reuse: the targeted protocol group must have a
Contract-Reviewer-compilable `protocol_semantics` profile. This prevents a
prose-only custom protocol from selecting a callable whose event bindings do
not exist.

`requires_protocol_event_relations: true` similarly limits the generic causal
event checker to an extension target actually touched by at least one compiled
`interface_contract.protocol_event_relations[]` declaration. Merely mentioning
latency, cancellation, or correlation in prose cannot make the resolver claim
that the pipeline already checks it.

## Exact, partial, and unsupported cases

- **Exact reuse:** all requested mechanics are covered. The generated test calls
  the selected entrypoints and adds no duplicate local implementation.
- **Partial reuse:** compatible drivers, monitors, adapters, or solvers are
  either called explicitly or preserved by the pipeline; only
  `residual_capabilities` are implemented in the extension bundle.
- **Unsupported:** no callable component is selected. Ranked references are
  supplied to the Verifier, which writes a contract-local implementation.

Contract-local implementations receive derived component descriptors in the
feature-extension manifest. They are never promoted automatically. Promotion
and global pool mutation remain future work.

## Adding a reusable component

When a new implementation conforms to an existing ABI:

1. implement and test the callable;
2. add one catalog entry with exact compatibility requirements;
3. run `tool_regression/unit/test_component_registry.py`.

No resolver branch or prompt edit is required. Core resolver code changes only
when the component needs a genuinely new invocation ABI or new compatibility
dimension.

## Registered component families

The registry covers protocol source/sink/memory drivers, lifecycle drivers,
memory models, memory and serialization adapters, assertion checkers, coverage
samplers, runtime monitors, operation stimulus strategies, golden operations,
and constraint solvers. Existing feature-plan retrieval remains responsible for
feature-level analogies; this registry handles executable building blocks.
