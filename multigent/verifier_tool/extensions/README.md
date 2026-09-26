# Verifier-authored feature extensions

This folder is the contract-local authoring boundary for behavior absent from the
closed Protocol, Lifecycle, or Operation pools. It does **not** implement mutation
testing, qualification, pool promotion, or automatic promotion.

Not every unfamiliar spelling needs an extension. Use a built-in pool entry when
the semantics already match. For a known integer-GEMM pipeline with a new scalar
post-operation that fits the closed formula grammar, use an arithmetic
`kind: llm_defined` DAG stage; the tool-owned golden trace can then keep handling
the known operation. Create a `verification_extensions[]` request only for the
remaining behavior that the closed pools and formula grammar cannot represent.
This decision order keeps the LLM-authored surface as small as possible.

The Architect declares only an `architecture_contract.verification_extensions[]`
request: stable identity, owning domain, exact target, parameters, observable
semantics, and why existing pools cannot express it. The Verifier answers each
request with exactly one `feature_extensions[]` bundle containing three sibling
branches: assertion, coverage, and stimulus.

`extension_request.schema.json` and `extension_bundle.schema.json` are the stable
formats. `examples.yaml` renders existing built-in protocol/lifecycle/operation
features in the same conceptual shape so the Verifier can copy a proven pattern
instead of inventing an entire TB. `authoring.py` composes these schemas into the
Architect and Verifier API schemas, validates exact request/bundle correspondence,
confirms any named Verifier Python symbol really exists in the generated
artifact, and rejects symbols that are not reachable from a generated test
entry point. Protocol-group targets are resolved through the same compiled
standard-protocol metadata used by the drivers, so a group declared through
canonical `protocol_group=...` channel metadata is a valid exact target even
when it is not duplicated as a literal top-level channel key.

Plural local vocabulary is declared once under
`architecture_contract.verification_vocabulary`, rather than copying one role or
semantic definition into every request. It may contain local signal roles,
semantic classes, and tags. Tags come from the central
[`../pool/tag_pool/`](../pool/tag_pool/README.md) registry whenever an existing
meaning applies; genuinely new tags must declare their domain, scope, and
observable meaning. The old per-request `contract_vocabulary` form remains
readable for frozen-contract compatibility.

Before the Verifier authors new code,
`contract_review.resolve_extension_reuse(...)` resolves applicable built-in
features and helper names from the exact target and its tags/roles/classes/profile.
The generated worklist therefore tells the Verifier which siblings are immutable
and leaves only the residual unsupported feature for LLM implementation. With an
interface contract supplied, bundle validation requires those resolved feature
IDs in `reuse.based_on_features`; the persisted extension manifest includes the
same tool-owned resolution.

The authoring validator also applies a deliberately small anti-placeholder
gate to `verifier_python` implementations. A custom assertion must contain an
observable decision, a coverage sampler must return data-dependent evidence,
and stimulus must be async and await executable work. This catches
`return None`/constant-coverage/no-await bundles at the request boundary. It is
not a correctness proof: actual simulation, observed evidence, and negative
controls remain necessary.

Bundles remain Verifier-owned artifacts under `workspace/verification`; they do
not modify `verifier_tool`, its catalogs, or any pool. Their format intentionally
contains the information a future qualification/promotion stage would need, but
that stage is outside the current scope.

## Current flow

1. Architect uses every supported pool entry normally.
2. Only a missing behavior becomes one `verification_extensions[]` request. A
   request freezes its domain, exact target, structured observable semantics,
   parameters, required observations, and related built-in examples.
3. Verifier receives a request-specific worklist. It must preserve all supported
   sibling features and return exactly one matching `feature_extensions[]` bundle.
4. The bundle separates assertion, measured coverage, and real stimulus. New code
   is written only in Verifier-owned `reference/*.py` or `tests/*.py`; a bundle
   names each exact module-level symbol, and deterministic validation confirms the
   symbol exists and is wired into the generated test call path.
5. The runtime persists `feature_extensions.yaml` and
   `feature_extension_manifest.yaml`. The latter keeps the immutable Architect
   request beside the Verifier implementation for later review.

For a lifecycle policy missing from the closed pool, only that policy field uses
`{extension_request: <id>}`. The lifecycle Feature Plan removes checkers,
coverage bins, and scenarios that depend on that field while preserving unaffected
ones. For example, a new three-cycle error indication does not replace the known
AXI driver, GEMM golden model, busy checker, or completion checker.
Validation checks this ownership link in both directions: a policy sentinel must
name a matching request, and every lifecycle request that claims a
`replaces_contract_paths` policy field must be referenced by that exact field.
An additive lifecycle extension may omit replacement paths and leaves all
built-in lifecycle behavior enabled.
For a `reset_behavior` extension, the runtime also preserves that operation's
in-flight state across the reset sample rather than silently applying the
built-in `abort_inflight` transition. This keeps field-level delegation true at
runtime, not only in the generated plan.

Unsupported operation arithmetic and object serialization may carry the same
kind of exact ownership edge without turning the whole operation into an
unstructured fallback:

- `operations[].arithmetic.extension_request` is valid only with
  `classifier_profile: llm_extension` and must name an operation-domain request
  targeting that exact operation.
- `data_objects[].serialization.extension_request` is valid only with
  `kind: llm_extension` and must name an operation-domain request targeting
  that exact data object.

The fields are optional only for compatibility with older coarse
`llm_extension` contracts. New contracts should include them, because they make
the unsupported fragment mechanically traceable while known protocol,
lifecycle, family, and sibling-operation plans remain independently usable.

`multigent/tests/test_extension_scenario_matrix.py` keeps ten intentionally
diverse local examples at this boundary: compositional GEMM stages, fully
LLM-owned arithmetic, APB, credit-based flow control, contract-local sideband
vocabulary, lifecycle replacement/addition, and a mixed three-domain contract.
`multigent/tests/test_extension_scenario_matrix_additional.py` adds fifteen
non-overlapping cases: runtime shapes, sparse serialization, convolution,
attention, Wishbone, TileLink, Avalon-MM, Avalon-ST, a contract-local handshake
role, lifecycle additions and replacements, sibling-operation isolation, and a
large mixed contract. Together these 25 cases use synthetic Verifier-owned
Python artifacts and never call an external model.

Those structural cases are paired with the executable fixture in
`multigent/tests/fixtures/feature_extensions/`. Its fifteen cocotb TB cases
drive real reference-RTL signals, derive coverage from observed evidence, and
corrupt one observation per case to prove the checker rejects a false result.
The fixture README records the direct source/timing audit and the defects found
on its first simulator run.

## Explicit non-goals

There is no catalog mutation, mutant generation, qualification gate, promotion,
or automatic promotion in this package. `promotion: not_implemented` in the saved
manifest is deliberate. A future stage can consume the stable manifest without
changing today's generation path.
