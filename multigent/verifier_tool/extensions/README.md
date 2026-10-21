# Verifier-authored feature extensions

## Structure-aware RAG

Unsupported features receive same-domain analogues retrieved from the checked-in
protocol, lifecycle, operation, and lifecycle-policy pools. Exact ID/tag matching
still runs first. Retrieval ranks only the residual extension by scope, temporal
behavior, evidence terminology, and reusable implementation shape. Retrieved
entries are advisory and cannot change the frozen contract or earn coverage credit.
See [`retrieval/README.md`](retrieval/README.md).

Executable reuse is resolved separately by the checked-in
[`components/`](../components/README.md) registry. The extension worklist names
the compatible driver, adapter, monitor, golden, or solver entrypoints that must
be called, the capabilities they cover, and the residual behavior that remains
Verifier-authored. This makes partial reuse explicit instead of regenerating a
whole testbench or accepting a YAML-only reuse claim.

This folder is the contract-local authoring boundary for behavior absent from the
closed Protocol, Lifecycle, or Operation pools. It does **not** implement mutation
testing, qualification, pool promotion, or automatic promotion.

Not every unfamiliar spelling needs an extension. Use a built-in pool entry when
the semantics already match. For a known integer-GEMM pipeline with a new scalar
post-operation, declare an arithmetic `kind: llm_defined` DAG stage and let the
Contract Reviewer attempt solver compilation. A successful compilation keeps the
tool-owned golden path; a failed formula is revised by the Architect. Create a
`verification_extensions[]` request only when the Architect explicitly declares
that the behavior is not solver-representable. This decision order keeps the
LLM-authored surface as small as possible.

The Architect declares only an `architecture_contract.verification_extensions[]`
request: stable identity, owning domain, exact target, parameters, observable
semantics, and why existing pools cannot express it. The Verifier answers each
request with exactly one `feature_extensions[]` bundle containing three sibling
branches: assertion, coverage, and stimulus.

Extension coverage is part of the normal verification closure. After bundle
validation, `extensions.coverage.build_extension_coverage_plan(...)` converts
every declared bin into the required obligation `extension.<request_id>` with a
minimum hit count of one. The generated classifier must pass the exact observed
bin names to
`_contract_record_extension_coverage("<request_id>", hits)`. The trusted runtime
rejects undeclared names and samples accepted names into the same
`cocotb-coverage` model and required denominator as protocol, lifecycle, and
operation coverage. Merely asserting a local Python return value no longer earns
extension coverage credit.

The reachable classifier may be factored into a generated `reference/*.py`
module and called through a thin `tests/*.py` wrapper. Structural review follows
that cross-file call graph when checking exact declared bin names, so reusable
reference semantics do not need duplicated string literals in the cocotb file.
The reachable test must still assert real trigger/activity evidence and record
the returned hits into the shared required denominator; helper separation does
not relax the anti-vacuity rules.

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

The canonical bundle keeps `bindings`, branch `parameters`, bin `predicate`, and
scenario `parameters` as normal JSON objects. At the OpenAI strict-structured
output boundary only, those dynamic-key objects travel as JSON strings because
the provider schema requires statically named object properties. The Verifier
decodes them immediately, validates the ordinary canonical bundle schema, and
persists only the canonical object form. This transport detail never appears in
the saved extension manifest.

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

The authoring validator also applies an anti-placeholder gate to
`verifier_python` and `protocol_driver` implementations. A custom assertion must
contain an observable decision, a coverage sampler must return data-dependent
evidence, and stimulus must be async and await executable work. For actual Verifier
output, the stricter `require_runtime_evidence` mode additionally rejects fabricated
literal observations, ignored Boolean checker returns, discarded coverage samples,
unused behavior-shaping parameters, and stimulus that only waits on a trigger without
driving the DUT or delegating to a real driver. Temporal requests must consume a
simulator-derived cycle trace/counter or implement a stateful monitor; reading one
instantaneous snapshot is insufficient. Coverage code must classify the exact bin
names declared in the bundle, and a reachable test must require a declared bin from
observed evidence rather than merely checking the sampler's return type. Temporal
stimulus must use its declared cycle/window parameter to shape a schedule; assigning a
parameter to `_` is treated as unused. Every declared scenario must be called with its
exact parameter values. A temporal DUT monitor must start concurrently before the
stimulus, and an output-channel extension must start a code-owned campaign/driver (or
drive the required non-target inputs) so the DUT can produce the observed VALID. A
standalone cocotb extension test must start every independently driven Clock it uses
(directly or through a reachable helper), and temporal bin credit requires
explicit trigger/nonzero-event evidence so an idle trace cannot pass vacuously.
Driver delegation may be either a direct `await driver(...)` or the normal concurrent
cocotb form `task = cocotb.start_soon(driver(...)); await task`; a scheduled passive
trigger alone is not stimulus. When an assigned reusable background driver remains
alive across multiple checked scenarios, its declared transport directions remain
eligible evidence only between its scheduling line and an explicit `kill`, `cancel`,
or await boundary. This prevents both losing real responder activity at the second
record and crediting traffic after the task has ended. Checker enforcement may unpack a returned decision and
assert that decision, and named-bin enforcement may use a statically literal scenario
table whose loop variable resolves to exact declared bin names.
`capture_protocol_event_trace(...)` is the one intentional coroutine-delegation
boundary: pass its stimulus coroutine unawaited so the helper can start observation
before it awaits the stimulus. The structural validator recognizes that exact awaited
capture call without treating the stimulus as dropped work. It also validates reusable
trace access in ordinary loops and comprehensions across both `tests/*.py` and called
`reference/*.py` support code. Transaction records expose `event` and `signals`; cycle
records expose `events` and `signals`. Invented top-level fields such as `kind`, a DUT
signal name, or a derived payload field are rejected before simulation. Transaction
`event` has the closed code-owned vocabulary `accepted`, `success`, `error`,
`completed`, and `cancelled`; compound aliases such as `request_accepted` or
`response_success` are not emitted and are rejected statically. Because capture ends
after its observer's final Cocotb `ReadOnly` sample, a caller must await a writable
scheduling boundary (for example `FallingEdge(clock)` or `Timer(...)`) before directly
assigning another DUT input.
For a multi-clock interface, one source-clock trace is not evidence for events
in another clock domain. The component worklist therefore exposes every exact
contract-local profile/transaction binding selected for the extension, including
DUT-output transactions. Generated verification must start a separate capture
on each declared clock and may correlate the traces only afterward. If a
DUT-output transaction completes through testbench-owned ACK/ERR-style inputs,
the reachable stimulus must also contain a responder that can assert at least
one of those completion inputs; initializing all of them to zero is rejected as
a guaranteed timeout.
Decorator names must be imported before decorated tests are defined. This catches `return None`, constant coverage,
vacuous self-tests, generic `sampled=True` markers, and Timer-only bundles before persistence.
It is not a correctness proof: actual simulation, observed evidence, and negative
controls remain necessary.

The generated authoring prompt also gives the Verifier a mechanical pre-return
checklist for the most common integration failures: bind every required observation
by exact name, use three distinct executable branch functions, declare only parameters
that the corresponding function consumes, execute every scenario exactly, and
consume/assert runtime results from one reachable cocotb test. This is general
extension guidance; it contains no benchmark-specific feature names or signal maps.
Exact scenario parameters may be written inline or assigned once to a literal
local variable, including inside a `try` block, before the reachable stimulus
call. The validator resolves that safe local constant form but still rejects
dynamic, ambiguous, or branch-dependent substitutions.
Source repair must preserve the single non-empty literal
`STIMULUS_COVERAGE_INTENTS` list when an unrelated extension branch changes; mapping,
empty, and omitted forms are rejected with the canonical list shape in feedback.
For assertion wrappers, that checklist recommends a direct `assert` plus a `True`
return that the cocotb entry point also asserts. A mapping such as
`{"passed": ok}` is evidence data, not enforcement. Coverage has the analogous rule:
the entry point must require an exact declared bin and explicit trigger/nonempty
evidence rather than merely consuming a returned object.

When `capture_protocol_event_trace` supplies extension evidence, pass the stimulus
coroutine itself; do not await the stimulus inside that argument. The capture helper
starts its observer first and awaits the coroutine internally. Its stable trace schema
is also code-owned: transaction records expose `event`, `signals`, `cycle`, and
outstanding counts, while cycle records expose `events`, `signals`, and `cycle`.
Signal values are nested under `record["signals"]`; generated extensions may not
invent top-level `kind` or signal fields. The structural validator follows direct
dictionary access, comprehensions, and small accessor helpers such as
`_get(record, key)`, including Verifier-owned reference files. When a frozen
interface contract is available, nested `record["signals"]` access is also limited
to actual captured DUT signal names; semantic correlation state must be derived
from the canonical event/cycle timeline rather than inserted as virtual signals.
Local repair removes pipeline-owned audit
syntax but restores the exact prior `STIMULUS_COVERAGE_INTENTS` mapping so an
unrelated source correction cannot silently erase semantic coverage intent.

The three residual branches cannot be satisfied by merely naming an
`existing_primitive`. Built-in helpers may be reused inside generated code, but
the new behavior still needs a reachable `verifier_python` assertion and coverage
wrapper plus a reachable `verifier_python` or `protocol_driver` stimulus wrapper.
No runtime dispatcher currently turns an inert helper name in the manifest into
an executable extension; forbidding that form prevents false readiness.

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
   symbol exists and is wired into the generated test call path. The path must
   pass simulator-derived observations, enforce the assertion result, consume
   the coverage result through `_contract_record_extension_coverage`, and execute
   stimulus with a real effect.
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

`multigent/verifier_tool/tool_regression/extensions/rtl/test_extension_scenario_matrix.py` keeps ten intentionally
diverse local examples at this boundary: compositional GEMM stages, fully
LLM-owned arithmetic, APB, credit-based flow control, contract-local sideband
vocabulary, lifecycle replacement/addition, and a mixed three-domain contract.
`multigent/verifier_tool/tool_regression/extensions/unit/test_extension_scenario_matrix_additional.py` adds fifteen
non-overlapping cases: runtime shapes, sparse serialization, convolution,
attention, Wishbone, TileLink, Avalon-MM, Avalon-ST, a contract-local handshake
role, lifecycle additions and replacements, sibling-operation isolation, and a
large mixed contract. Together these 25 cases use synthetic Verifier-owned
Python artifacts and never call an external model.

Those structural cases are paired with the executable fixture in
`multigent/verifier_tool/tool_regression/extensions/fixtures/feature_extensions/`. Its fifteen cocotb TB cases
drive real reference-RTL signals, derive coverage from observed evidence, and
corrupt one observation per case to prove the checker rejects a false result.
The fixture README records the direct source/timing audit and the defects found
on its first simulator run.

## Explicit non-goals

There is no catalog mutation, mutant generation, qualification gate, promotion,
or automatic promotion in this package. `promotion: not_implemented` in the saved
manifest is deliberate. A future stage can consume the stable manifest without
changing today's generation path.
