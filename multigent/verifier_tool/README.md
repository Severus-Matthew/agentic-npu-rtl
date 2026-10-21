# Verifier tool

This directory contains the deterministic, code-owned verification components.
It is a library used by the Architect, Verifier, Debugger, deterministic review
nodes, and cocotb runtime; it is not another LLM agent.

What to require of each kind of consumer to use this tool well, and what the tool
provides to each, is documented per role in
[`GUIDE.md`](GUIDE.md) (human-readable architecture and integration overview),
[`AGENT_EXTENSION_GUIDE_KO.md`](AGENT_EXTENSION_GUIDE_KO.md) (Korean guide to
the exact Architect contract, Verifier coverage, and executable-code boundary
for features absent from the pools),
[`ARCHITECT_INTEGRATION.md`](ARCHITECT_INTEGRATION.md) (contract producer),
[`VERIFIER_INTEGRATION.md`](VERIFIER_INTEGRATION.md) (testbench/reference
generator), [`DEBUGGER_INTEGRATION.md`](DEBUGGER_INTEGRATION.md) (failure-evidence
payload), and [`CONTRACT_REVIEWER_INTEGRATION.md`](CONTRACT_REVIEWER_INTEGRATION.md)
(deterministic contract review). Every subfolder below also has
its own `README.md` with function-level detail; this file only gives the map and the
cross-cutting rules.

Qualification status is tracked by the executable
[`tool_regression/qualification/ledger.json`](tool_regression/qualification/ledger.json)
(the exhaustive protocol, lifecycle, and operation inventory) and the tracked
[`HLS benchmark qualification matrix`](tool_regression/qualification/hls_benchmark_qualification_matrix.md).
Historical working reports live under the ignored `tool_regression/local_reports/`
directory and are not sources of shared truth. A passing unit test or one
passing RTL run is not treated as a strict assertion/checker qualification:
that needs a frozen-contract/generated-TB mutant failing for the intended
reason plus corrected RTL passing every required bin, assertion, and ledger
check. Coverage uses a separate evidence class: real observed DUT hits plus
exact per-bin rejection when an individual hit is removed. Rows earn the
appropriate mark one at a time, so read the matrices for the current state
rather than this file. [`tool_regression/benchmarks/README.md`](tool_regression/benchmarks/README.md)
describes the local runners and benchmark fixtures.

```text
verifier_tool/
├── __init__.py               single lazy public API
├── protocol/                 protocol-domain ownership
│   ├── assertion/            plan generator, runtime, and protocol assertion_checkers
│   ├── coverage/             protocol coverpoints and obligation planning
│   └── stimulus/             scenario planning + cocotb drivers
│       ├── drivers/            protocol-specific BFMs (axi_lite.py, axi4_outstanding.py,
│       │                       custom_mmio.py, axi_lite_control.py) + shared
│       │                       _bus_binding.py / _completion_scheduler.py
│       ├── adapter/            operation-aware address windows + value packing (OperationMemoryAdapter)
│       └── memory/             raw byte store (re-export of cocotbext.axi.memory.Memory)
├── operation/                 operation-domain ownership
│   ├── assertion/            operation assertion source generator/catalog
│   ├── coverage/             operation families, bins, and DUT sampling
│   └── stimulus/             stimulus_generator + canonical golden-model evaluator
├── lifecycle/                 lifecycle-domain ownership
│   ├── assertion/            plan generator, runtime, and lifecycle assertion_checkers
│   ├── coverage/             reset/command/job/status/abort/purity coverage
│   └── stimulus/             command-channel driving, register-mapped job start/completion
│                             (drive_control_plane_sequence), lifecycle scenario planning
├── orchestration/             cross-cutting code that spans all three domains at once
│   ├── instrumentation.py    immutable generated TB block and validation
│   ├── runtime.py            sampling, bin hits, and coverage reports
│   ├── cocotb_model.py       cocotb-coverage objects
│   ├── history.py            cumulative stimulus ledger/history
│   └── campaign.py           executable code-owned cocotb campaign
├── pool/                      Architect-facing closed taxonomies + shared Feature Plan
│   ├── diagnostics.py           reason codes, categories/owners, feature-level automation records
│   ├── role_pool/               roles, semantics, and exact protocol-field bindings
│   ├── tag_pool/                shared protocol/lifecycle/operation capability tags
│   ├── lifecycle_policy_pool/   supported lifecycle behaviors (incl. control_plane_sequence) + metadata/schema helpers
│   ├── operation_metadata/      contract-to-canonical-I/O compiler, canonical jobs
│   │   ├── architect_metadata_format.yaml  merge-facing Architect metadata contract
│   │   ├── architect_metadata.py           contract-to-canonical-I/O compiler
│   │   ├── arithmetic_metadata.py          tool-owned arithmetic schema/compiler
│   │   ├── arithmetic_metadata.schema.json arithmetic API-facing schema fragment
│   │   ├── io_metadata.py                  explicit object serialization declarations
│   │   ├── packed_encoding.py              packed_encoding serialization: validation + encode engine
│   │   ├── formula.py                      solver compiler shared by formula post-ops and golden evaluation
│   │   ├── protocol.py                     role-bound accepted-value capture adapter (ready/valid, AXI, custom_mmio)
│   │   └── canonical.py                    canonical jobs and classifiers
│   └── feature_plans/
│       ├── protocol_features.yaml   protocol match/assertion/coverage/stimulus source
│       ├── lifecycle_features.yaml  lifecycle match/assertion/coverage/stimulus source
│       ├── operation_features.yaml  operation family/assertion/coverage/stimulus source
│       ├── resolved_feature_plan.schema.json  shared executable resolved-plan format
│       ├── catalog.py / compiler.py / schema.py   catalog loading, branch splitting, plan validation
│       ├── protocol.py           channel and standard-protocol feature matcher
│       ├── lifecycle.py          reset/command/job/status feature matcher
│       ├── operation.py          canonical mathematical-feature matcher
│       └── common.py             shared output schema helpers only
├── extensions/                contract-local missing-feature authoring boundary
│   ├── extension_request.schema.json  Architect-owned observable semantics
│   ├── extension_bundle.schema.json   Verifier-owned assertion/coverage/stimulus
│   ├── examples.yaml                 reusable built-in feature examples
│   └── authoring.py                  schema composition, validation, inert manifest
├── components/                reusable callable registry + compatibility resolver
│   ├── catalog/                      driver/adapter/runtime/golden/solver manifests
│   ├── interfaces.py                 stable component types and invocation ABIs
│   ├── registry.py                   checked-in manifest validation and safe loader
│   └── resolver.py                   exact reuse, residual work, and RAG references
├── contract_review/           deterministic contract preflight + extension reuse resolution
├── tb_validation/
│   ├── validator.py          stable code-only generated-TB validation
│   └── repair.py             bounded local repair application
├── feedback_to_debugger/      Verifier-owned evidence payload for the Debugger handoff
├── tool_regression/           unit, integration, RTL, extension, and benchmark regressions
├── manifest.py               frozen verification manifests and taxonomy release gates
├── qualification.py + qualification_catalog.yaml   finite released-checker catalog
└── feature_plan.py           stable facade re-exporting the three pool/feature_plans/ builders
```

This is a **domain-first** layout: `protocol/`, `operation/`, and `lifecycle/`
each own one verification domain, with
`assertion/coverage/stimulus` nested inside each (an earlier layout had this
inverted — `assertion/coverage/stimulus` at the top, each with its own
`protocol/lifecycle/operation` subfolder — which spread "everything about AXI,"
say, across three unrelated top-level folders). Code that genuinely spans all
three domains at once (rendering the whole generated testbench, the shared
coverage runtime database, the fully-automatic campaign driver) does not belong
to any one of them, so it lives in `orchestration/` instead.

`pool/operation_metadata/` is easy to confuse with the `operation/` domain folder
above — they sound alike but are different things. `pool/operation_metadata/`
is the contract-metadata *compiler*: a "pool" of canonical operation/arithmetic
semantics that sits alongside `pool/role_pool/` (signal roles) and
`pool/lifecycle_policy_pool/` (lifecycle behaviors). All three pools turn a
frozen Architect contract into canonical, code-owned meaning; the `operation/`
(and `protocol/`, `lifecycle/`) domain folders then *consume* that meaning to
generate assertions, coverage, and stimuli. If you are looking for "where
code-owned operation classification happens," that is
`pool/operation_metadata/canonical.py`, not
`operation/assertion/` or `operation/coverage/`.

Similarly, `feature_plan.py` (singular, a small facade module) sits beside
`feature_plans/` (plural, the package with the actual per-domain catalogs and
matchers) for the same reason `verifier_tool/__init__.py` sits beside the rest of
the package: it is a stable import surface so callers do not need to know which
domain file implements which builder.

Public callers import only from the package facade, regardless of the internal
owner directory:

```python
from multigent.verifier_tool import (
    contract_coverage,
    generate_canonical_stimulus_for_bin,
    install_contract_generated_block,
)
```

`role_pool` describes signal meaning. `operation` turns those roles plus Architect
data-object metadata into accepted canonical jobs. `coverage` records observed bin
hits. `assertion` generates one central golden-result comparison and
code-owned protocol checks. For a known GEMM, verifier_tool owns channel binding,
transaction completeness, and the dimensions/operand/accumulation/post-op/bias/
activation classifiers. The restricted integer sparse-attention profile owns
the exact composed QK/scale/mask/normalization/value golden trace and its
dimension, operand, sparsity-pattern, active-score, stage-handoff, and
output-value classifiers. For the supported
ready/valid code-owned profiles, the
immutable generated cocotb campaign also owns protocol scheduling, accepted-transfer
capture, directed/qualification/random stimuli, exact 1/3/6-cycle channel stalls,
reset in every input/compute/output phase, illegal-command recovery, and post-reset
purity. It recomputes the golden result from the values actually accepted by the DUT.
The Verifier does not reimplement this base profile; it supplies only genuinely
unknown contract-local extension semantics or legacy `llm_extension` observers.
Memory-mapped operations (AXI4-Lite, full AXI4, and the `custom_mmio` profile)
get their own campaign paths in `orchestration/campaign.py`; a
register-started (`control_plane_sequence`) AXI4 operation is dispatched to a
separate multi-port path that runs job-level transport variants but not the
ready/valid sweep listed above (see
[`orchestration/README.md`](orchestration/README.md)).
Each generated directed vector is reclassified before it is returned.
Mathematically impossible, ambiguous-metadata, and novel-semantics cases are exposed
as `unreachable`, `metadata_missing`, or `llm_extension_required` instead of being
silently credited. The Verifier supplies a normalized
assertion/coverage/stimulus bundle only for unknown families or features the tool
cannot classify.

The three domains build independent resolved Feature Plans. They share the
record shape (`bindings`, `assertion`, `coverage`, and `stimulus`) but not
matching rules. Assertion, coverage, and stimulus are sibling consumers of
the resolved feature, so an assertion never selects itself by inspecting a
coverage-template name. A few pure implementation helpers are deliberately
shared after matching — AXI byte-window geometry and operation-bin witness
generation — so the branches cannot disagree on identical arithmetic:

```text
interface bindings  -> Protocol Feature Plan  -> assertion / coverage / stimulus
lifecycle metadata  -> Lifecycle Feature Plan -> assertion / coverage / stimulus
operation metadata  -> Operation Feature Plan -> assertion / coverage / stimulus
```

Each branch is compiled independently. YAML contains machine-readable bin values,
events, ranges, and stimulus schedules; prose `intent` is documentation only.
For example, protocol handshake bins declare their exact `{valid, ready}` values,
arrival-order bins declare observed event tokens, and stall bins declare inclusive
cycle ranges. Python owns reusable checker/sampler/driver primitives, while the
catalog selects a primitive and supplies its parameters. Unknown primitive names
fail catalog loading instead of being guessed.

If one required feature is absent from those closed catalogs, the Architect adds
one structured `verification_extensions` request instead of forcing a whole-TB
fallback or pretending a nearby pool entry is equivalent. The Verifier implements
only that request and returns one matching `feature_extensions` bundle whose
assertion, coverage, and stimulus branches name their exact generated Python
symbols. Supported siblings remain tool-owned. See
[`extensions/README.md`](extensions/README.md). These bundles are saved beside
their immutable requests for later review, but this path implements no pool
mutation, mutant generation, qualification, promotion, or automatic promotion.

Operation catalogs can organize optional leaf features under `feature_groups`.
For GEMM, `post_processing` contains `bias`, `activation`, and `quantization`; it has no executable
assertion, coverage bin, or stimulus target of its own. In particular, the old
parent `enabled/identity` bins duplicated ReLU region coverage and are removed.
Architect selects the applicable leaf names in `feature_extensions`. Resolved
leaf plans retain `bindings.feature_group: post_processing`, while IDs such as
`operation.gemm.bias` remain stable. An old frozen `features: [..., post_processing]`
is accepted as an inert group marker, without selecting any undeclared children;
the deterministic compiler drops obsolete parent coverpoints. New group bins are
rejected by coverage validation. Novel-family features with the same spelling are
not affected. None of this changes arithmetic: `arithmetic.post_operations`
(a DAG of named stages, each naming its own predecessor) still determines
computation order via that declared graph. Catalog nesting neither reorders
stages nor adds support for new activation functions.

`lifecycle_policy_pool/lifecycle_policies.yaml` defines the Architect-selectable
lifecycle behaviors separately from `feature_plans/lifecycle_features.yaml`, which
defines how to verify those behaviors. Explicit selections are validated before
building the shared assertion/coverage/stimulus plan. The pool currently supports
job acceptance by either one command handshake or a declared register
`control_plane_sequence` (e.g. an HLS `ap_ctrl_chain` AXI4-Lite control bus), one
in-flight job, busy tracking the active job, completion either on the next
sample after retirement or `observed_via_poll` (only for the register path,
where the completion wire is a black box), reset abort, and pulse or
sticky-until-reset errors. It does not claim arbitrary completion timing or job
overlap. For generic `ready_valid`/`custom` channels, the same pool also exposes
an optional interface-level `valid_deasserted` reset policy; without that explicit
selection, the tool makes no reset assumption from the handshake alone. Standard
AXI-family channels keep their standard-owned reset rule. See
[`lifecycle_policy_pool/README.md`](pool/lifecycle_policy_pool/README.md)
for the selection format and the effective Architect schema integration. New
Architect outputs must select these policies explicitly; the schema is composed
from the pool rather than maintaining a second copy of the enums.

Within the protocol and lifecycle assertion domains, `generator.py` renders the bound assertion plan,
`runtime.py` orchestrates each sampled cycle, and `assertion_checkers.py` contains
the executable assertion logic. This keeps simulation integration separate from
the assertion implementations.

The LLM may call these functions but may not patch either `verifier_tool` source or
the generated TB block. A Debugger diagnosis that identifies a code-owned helper,
golden model, classifier, or protocol assertion as the cause is a terminal
tool-owned verification error; it must not be converted into an LLM TB rewrite or
an RTL repair.

The effective Architect response schema requires `operations[].arithmetic`,
`operations[].lifecycle_policy`, and `data_objects[].serialization` (kinds
`dense_tensor`, `scalar`, `llm_extension`, and the generic `packed_encoding`),
and optionally accepts `verification_extensions` and `verification_vocabulary`.
Tool-owned schema composers add these fields without duplicating enums in the
pipeline's base schema. The same composed schema optionally accepts
`interface_contract.reset_channel_policies` and
`interface_contract.protocol_semantics`. The latter is the machine-readable
escape-hatch boundary for a new protocol profile: Architect declares boolean
events, transactions, stable fields, flow control, ordering, cancellation, and
residual custom rules; Contract Review compiles them into a safe data AST; the
Verifier reuses tool-owned handshake/stall/accounting features and implements
only custom rules linked to a real extension request. Descriptive prose is never
the executable authority. The register-sequence declaration
(`operations[].lifecycle_control_plane_sequence`) is an optional property of that
schema (required exactly when a lifecycle policy field is `control_plane_sequence`,
enforced by the compile); a reset signal's `reset_settle_cycles` is honored by the
metadata compiler but is not part of the Architect schema, so today only
hand-authored frozen contracts carry it. An operation `architect_metadata.py`
cannot compile is no longer lost: it is recorded with a reason code, a category
(`contract_error` / `extension_required` / `tool_capability`) and an owner, its
contract-required lifecycle obligations stay in the coverage plan as required bins,
and only the defects an Architect can fix are sent back to it
(`validate_operation_compilation`; see
[`pool/operation_metadata/README.md`](pool/operation_metadata/README.md)).
`architect_metadata.py` resolves declared references into canonical
metadata; it no longer infers an accumulator from the result type, ReLU from an
activation label, conversions from overflow prose, or transfer order from shape.
Missing fields in old frozen contracts are errors, not compatibility defaults.
Full `operation.verification_metadata` remains an external input form and is
validated against the same arithmetic rules. Unsupported mathematics must be
explicitly selected as `llm_extension`, with its precise specification; this is
not a code-owned verification guarantee. See [operation metadata](pool/operation_metadata/README.md).

AXI4, AXI4-Lite, and AXI4-Stream are compiled only from explicit standard
metadata. `channel.protocol_group` associates the complete interface,
`channel.protocol_channel` selects AW/W/B/AR/R/stream semantics, and
`signal.protocol_field` selects addr/len/size/burst/data/strb/keep/last/id/dest/
resp/sideband meaning. Names and prose are never parsed. The staged schema and
field catalog live in `pool/role_pool/standard_protocols.yaml` and
`pool/operation_metadata/architect_metadata_format.yaml`; this is deliberately separate from
the frozen Architect schema for a later conflict-free merge.

For a nonstandard protocol whose VALID/READY equivalents are expressions rather
than individual signals, `protocol_semantics.py` supplies a second deterministic
path. Its expression language is intentionally limited to declared signal/event
names, `!`, `&&`, `||`, `==`, `!=`, `0`, and `1`; Python evaluation and arbitrary
code are forbidden. Contract Review rejects unknown references and cycles, then
inlines event dependencies. The resolved Feature Plan can consequently use the
same `handshake_states`, `handshake_arrival_order`, `stall_stability`, and
`transaction_accounting` runtime primitives for Wishbone-like or future custom
profiles. When one observable event must cause another across protocol boundaries,
`interface_contract.protocol_event_relations` additionally declares the exact
cause/effect bindings, bounded cycle latency, FIFO correlation, outstanding depth,
and cancellation behavior. Contract Review compiles this data and the generated
monitor invokes the code-owned event-correlation checker; a registered response is
therefore not rewritten as an incorrect same-cycle LLM assertion. Only residual
payload transformation, keyed identity, or other semantics absent from these IRs
remain Verifier-authored extensions.

The compiled input transaction includes presented, post-accept, and idle drive
states plus a completion mode. The generic custom-event source driver can thus
hold a Wishbone-like cycle open until every accepted request completes without
hardcoding Wishbone names. Component resolution selects this driver and the
pipeline-owned transaction-accounting checker only when the targeted group has
validated protocol semantics; otherwise they remain unavailable rather than
being guessed from prose.

The generated TB block embeds immutable operation, protocol, and lifecycle plans and exposes
`_contract_protocol_scenarios()` and `_contract_protocol_channel()`. Executable
custom-event bindings are exposed by
`_contract_protocol_event_transaction(profile_name, transaction_name)`.
Executable
`_contract_drive_protocol_transfers`, `_contract_collect_protocol_transfers`, and
`_contract_drive_protocol_reset` helpers own the cocotb edge/hold/accept loop, so
the Verifier does not recreate handshake drivers. All temporal implementation remains in the
tool: common VALID/READY stability, reset clearing, AXI burst/size/wrap/4-KiB/
LAST/strobe/response/ID/order rules, AXI4-Lite response and AW/W pairing rules,
and AXI4-Stream KEEP/STRB and packet-sideband rules. Coverage is sampled only on
observed transfers, and scenario labels never credit bins.

The taxonomy has three owners. `operation` owns mathematical/data semantics;
`protocol` owns per-channel transfer, framing, backpressure, and standardized bus
rules; `lifecycle` owns reset/abort, legal and illegal commands, global busy state,
completion/error, job retirement, recovery, and post-reset purity. `busy` may appear
in a cross-invariant with command READY, but its owning category remains lifecycle.

`review_verifier_artifacts(context, candidate)` is the single integration point for
the pre-simulation gate. It makes no LLM call. It enforces code-owned deterministic
rules and intentionally trusts the semantics of Verifier-authored `llm_extension`
features.
