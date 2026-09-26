# Verifier Tool: Human-Readable Integration Guide

This guide explains the design of `multigent/verifier_tool` without requiring the
reader to first understand every checker, schema, or test file. It is intended for
people integrating the tool into the multi-agent pipeline, especially the
Architect, contract-review, Verifier, simulation, and Debugger stages.

For exact APIs and field-level rules, follow the links in
[Where to read next](#where-to-read-next). This guide describes the mental model
and the ownership boundaries.

## 1. The idea in one minute

The Verifier agent should not repeatedly invent verification logic for behavior
the project already understands. The tool therefore keeps reusable,
deterministic knowledge in Python and YAML catalogs, while the Architect writes a
machine-readable contract describing the particular design.

The tool divides verification into three independent domains:

| Domain | Question it answers | Typical examples |
|---|---|---|
| **Protocol** | Were values transferred legally? | ready/valid handshakes, backpressure, stable payload while stalled, AXI channel and response rules |
| **Lifecycle** | Did the accelerator job behave legally over time? | start acceptance, busy behavior, completion, reset abort, illegal commands, error timing |
| **Operation** | Was the externally visible mathematical result correct? | GEMM accumulation, overflow conversion, bias, ReLU, quantization, output shape and completeness |

This separation is deliberate. A new protocol rule should not force regeneration
of the golden arithmetic model. A new activation function should not replace the
existing AXI or reset verification. When only one feature is unsupported, only
that residual feature is assigned to an LLM extension.

```text
Reusable pools/catalogs                     Design-specific declaration
-----------------------                     ---------------------------
Role + protocol pool ----\
Lifecycle policy pool ----+---------------> Frozen Architect contracts
Operation feature catalog-/                         |
                                                    v
                                      Deterministic contract preflight
                                                    |
                         +--------------------------+--------------------------+
                         |                          |                          |
                         v                          v                          v
                  Protocol plan              Lifecycle plan              Operation plan
              assertion/coverage/         assertion/coverage/         assertion/coverage/
                    stimulus                    stimulus                    stimulus
                         \_________________________|__________________________/
                                                    |
                                                    v
                                      Generated cocotb verification
                                                    |
                                                    v
                              Assertions + coverage + stimulus ledger
                                                    |
                                                    v
                                      Structured Debugger evidence
```

`verifier_tool` is a code-owned library used by the agents and runtime. It is not
another agent and it does not call an LLM.

## 2. What the Architect must declare

The Architect is responsible for meaning. The tool is responsible for compiling
that meaning into deterministic verification. The tool must not infer important
facts from a signal name such as `m_axi_rdata` or `done`.

The frozen contracts must state the following information explicitly.

### Interface and protocol metadata

For every interface channel and signal, the contract identifies:

- the protocol profile and protocol instance/group;
- the protocol channel and standard field, where applicable;
- the signal role, semantic class, direction, and width;
- capabilities such as burst support or maximum outstanding transactions;
- which data object or control field a transfer represents.

The Role Pool provides the shared vocabulary. A `role` says what a signal does in
the transfer, while a `semantic_class` says what its value means. For example,
`payload` is a role and `address` is a semantic class. Protocol metadata then
places that signal in a concrete channel such as an AXI write-address channel.

### Lifecycle metadata

Signal roles cannot determine lifecycle semantics by themselves. A signal tagged
as completion does not say whether completion is a one-cycle pulse, a sticky bit,
or a polled control register. Each operation therefore selects explicit values
from the Lifecycle Policy Pool, including:

- job acceptance and overlap behavior;
- busy behavior;
- completion style and timing;
- illegal-command behavior;
- error style and timing;
- reset behavior;
- a control-plane register sequence when start and completion are accessed by
  reads and writes rather than direct pins.

### Operation metadata

For each operation and data object, the contract declares:

- operation family and selected features;
- fixed dimensions and operand/result data types;
- mathematical accumulation and conversion behavior;
- post-processing stages and their dependency order;
- the output stage;
- the exact serialization of each logical object into physical transfers,
  including packed encodings where necessary.

The post-operation declaration is DAG-shaped: every named stage declares its
predecessor through `depends_on`, and `post_output` names the final value. The
current built-in primitives are unary stages, so executable built-in graphs
resolve to one dependency chain, for example:

```text
accumulator -> bias_add -> relu -> affine_quantize -> result
```

This order is part of the mathematical contract. It must not be guessed from the
order of YAML or JSON keys.

### Why this metadata matters

The same contract fields drive all three verification branches:

- real DUT signal binding for monitors and drivers;
- selection of applicable assertions and coverage obligations;
- legal stimulus generation;
- canonical data serialization and reconstruction;
- golden-output and golden-trace evaluation;
- precise ownership when a fact is missing or unsupported.

The schema composers in the public `multigent.verifier_tool` facade add these
required fields to the Architect output schema. The Architect prompt also receives
live renderings of the pools, so the schema and vocabulary are not separately
hand-copied into the agent prompt.

## 3. From a frozen contract to three resolved feature plans

The contract is first checked by deterministic preflight. This validates roles,
semantics, standard protocol bindings, lifecycle policies, operation arithmetic,
serialization, references, and extension declarations.

The result distinguishes three kinds of problem:

| Category | Meaning | Owner |
|---|---|---|
| `contract_error` | The contract is missing or contradicts a fact it could express | Architect / contract revision |
| `tool_capability` | The contract is valid, but the deterministic tool lacks that implementation | `verifier_tool` development |
| extension request | The design intentionally introduces behavior outside the built-in pools | Verifier-authored contract-local extension |

The tool then builds one resolved feature plan per domain. A catalog entry is a
generic rule. A resolved plan binds that rule to the actual operation, channel,
signals, parameters, and stable feature IDs in this contract. Features that the
contract explicitly does not support are marked inapplicable; required behavior
is never silently removed merely because the tool cannot automate it.

Each resolved feature has three sibling branches:

1. **Assertion** — which runtime checker to call and with which bindings.
2. **Coverage** — which sampler, predicates, and bins constitute evidence.
3. **Stimulus** — which reusable strategy and scenarios target those bins.

The YAML catalogs choose named Python primitives and parameters. Human-readable
`intent` text documents the rule, but prose is not executed as verification logic.

## 4. What each domain generates

### Protocol

Protocol matching begins with the declared scope, tags, roles, standard fields,
and capabilities. For a stall-stability feature, for example, the resolved plan
may bind:

```text
valid   -> m_axi_wvalid
ready   -> m_axi_wready
content -> m_axi_wdata, m_axi_wstrb
```

The same resolved feature can then:

- drive one-cycle, short, and long stalls through a reusable channel schedule;
- assert that producer-owned content remains stable during `valid && !ready`;
- sample the completed stall length and send it to cocotb-coverage.

Protocol drivers are separated from data meaning. The driver implements wire
behavior; the operation memory adapter maps addresses and bytes to logical data
objects; the raw memory model only stores bytes. This keeps AXI, custom MMIO, and
future drivers from duplicating operation packing logic.

### Lifecycle

Lifecycle uses the same resolved-feature structure, but matches both signal
bindings and the selected Lifecycle Policy Pool values. It checks temporal facts
such as accepted start, completion timing, overlap, reset abort, and sticky or
pulsed status behavior.

This is why lifecycle cannot be derived only from `start`, `busy`, `done`, and
`error` roles. The policy states what those signals or control registers are
supposed to mean over time.

### Operation

Operation verification works in a canonical logical representation. A matrix is
represented as logical integer elements with a known shape, independent of
whether the DUT receives it in K-major order, adjacent-column packing, AXI beats,
or another physical layout.

The serialization adapter performs the boundary conversion:

```text
canonical logical tensors
        |
        v
serialize and pack -> protocol transfers -> DUT
        |
        v
reconstruct accepted transfers -> canonical accepted tensors
```

Keeping canonical arithmetic separate from transport is what lets the same
golden model verify different protocols and physical encodings.

## 5. Tool-owned golden model and golden trace

For supported integer GEMM operations, one arithmetic event walk computes both
the expected result and the evidence used for coverage classification. The core
implementation is `integer_matrix_multiply_events`.

Its trace contains facts such as:

- each product term;
- mathematical and converted reduction prefixes;
- the final accumulator value;
- bias and other post-operation values;
- pre-activation and quantization values;
- the final converted result.

This shared walk is important. If correctness used one implementation while
coverage independently reimplemented the arithmetic, they could disagree. Here,
the final result and intermediate golden trace come from the same semantics.

At runtime the tool does not blindly trust the arrays the test intended to send.
It reconstructs what the DUT actually accepted through protocol activity and then
re-evaluates the model:

```text
trusted_expected = golden(actual_accepted_inputs)
```

The run checks, as applicable:

- intended input versus accepted input;
- testbench expected value versus the tool-owned expected value;
- observed DUT output versus the tool-owned expected value;
- expected and observed transaction counts, coordinates, shape, and duplicates.

Operation coverage is classified from the same accepted-input golden trace. For
example, a reduction prefix above the declared maximum can hit a positive
overflow condition even though the internal RTL accumulator is not visible. A
scenario hit records that the intended mathematical condition occurred; the run
still fails if the DUT result is incorrect.

## 6. Directed stimulus and constraint solving

Known operation features use deterministic generators rather than asking an LLM
to invent vectors. The generator includes explicit constructions for common
cases and a Z3-backed reduction query for exact product-sum witnesses.

For a requested accumulator boundary, the solver:

1. creates bounded integer variables for the operand elements and optional bias;
2. constrains them to the declared data-type ranges;
3. adds the exact reduction target or target range;
4. asks Z3 for a satisfying assignment;
5. runs the assignment forward through the complete golden model;
6. accepts the vector only if the coverage classifier confirms the requested bin.

This final forward check prevents a solver witness from receiving credit when a
later conversion or post-operation changes its meaning.

Z3 is currently used for specific integer-reduction constraints. It is not a
universal symbolic executor for every arbitrary new formula. Unsupported inverse
problems still need a new reusable strategy or an extension implementation.
Generation failure, unreachable conditions, and missing metadata are represented
explicitly; they are not converted into false coverage hits.

## 7. How LLM-defined behavior is isolated

There are two extension levels.

### Closed-form post-operation

If a new operation stage can be expressed as a pure scalar formula, the Architect
can declare an `llm_defined` post-operation stage in the DAG. The formula uses a
closed grammar (`value`, integer literals, arithmetic, comparisons, `min`, `max`,
`abs`, and `clip`). It is parsed through an AST whitelist, never Python `eval` or
`exec`.

After validation, the stage runs inside the same tool-owned golden event walk.
This preserves the existing GEMM, serialization, protocol, lifecycle, and trace
logic instead of asking the Verifier to rewrite all of them.

### Contract-local verification extension

Genuinely unsupported behavior is declared once by the Architect under
`verification_extensions[]`. A request contains a stable ID, one domain, the
exact target, observable semantics, parameters, required observations, and the
reason an extension is needed. New local vocabulary is declared once under
`verification_vocabulary` when required.

The contract reviewer resolves reusable building blocks by comparing the request
with existing tags, roles, semantic classes, profiles, features, checkers,
samplers, and stimulus strategies. The Verifier then supplies exactly one
`feature_extensions[]` bundle for that request, with separate assertion,
coverage, and stimulus branches.

The tool validates that:

- every request has exactly one answer and no answer is unsolicited;
- known sibling feature IDs are preserved;
- required observations are bound;
- referenced Python files and module-level symbols exist;
- the symbols are reachable from a generated test;
- assertion, coverage, and stimulus do not collapse into placeholder logic.

The extension is local to that frozen contract and is saved with a manifest. It
does **not** mutate or automatically promote itself into a global pool. Automatic
mutation and promotion are intentionally future work.

The important rule is residual ownership:

```text
GEMM + AXI4 + known lifecycle + unknown activation
  -> GEMM/AXI4/lifecycle remain tool-owned
  -> only the unknown activation is extension-owned
```

The LLM is not allowed to patch `verifier_tool` source or modify the immutable
code-owned block in the generated testbench.

## 8. Generated cocotb testbench and runtime evidence

The Verifier writes only its owned reference and test files. The pipeline then
installs a code-owned block generated from the frozen contract. Exact validation
rejects edits to that block.

During simulation:

- reusable async drivers apply protocol, lifecycle, and operation stimulus;
- monitors take immutable snapshots of observed DUT activity;
- assertion checkers evaluate temporal and mathematical requirements;
- cocotb-coverage records bins selected by the runtime samplers;
- the stimulus ledger records which scenario was attempted and what happened;
- the combined report requires every applicable required bin to be hit.

The cocotb runner must provide the generated coverage-plan and report paths through
`NPU_FUNCTIONAL_COVERAGE_CONFIG` and `NPU_FUNCTIONAL_COVERAGE_REPORT`; the ledger
path is optional but strongly recommended.

The final evidence is structured before it reaches the Debugger. A Debugger should
receive the failed feature ID, assertion or bin, signal bindings, stimulus record,
accepted transaction evidence, expected/observed values, and ownership. If the
evidence points to a code-owned golden model, classifier, adapter, or checker, the
problem belongs to the verification tool; it must not be disguised as an RTL fix
or an LLM rewrite of the protected testbench block.

## 9. Feedback produced at each boundary

The tool does not return one generic error string. It produces different feedback
for different consumers so that a contract defect, Verifier defect, RTL defect,
and tool-capability gap are not repaired by the wrong component.

### Contract-review feedback to the Architect and pipeline

`review_contract_deterministically(...)` returns a plain-data report before the
Verifier is allowed to generate a testbench:

```text
schema_version
status: PASS | BLOCKED
findings[]
resolved_extension_reuse
capability_notes[]
```

Each blocking finding contains:

- `check_id` — which deterministic check failed, such as signal roles, standard
  protocol binding, lifecycle policy, arithmetic, serialization, or extension
  matching;
- `severity` — currently `blocking`;
- `owner` — `architect_contract` for a contract-correctable defect;
- `artifact` — the contract artifact that must be inspected;
- `paths` — reserved for precise machine-readable locations;
- `message` — the exact violation.

The report also carries two non-error outputs:

- `resolved_extension_reuse` tells the Verifier which existing features,
  checkers, samplers, strategies, roles, and tags can be reused for every
  extension request;
- `capability_notes` records valid contract behavior that the present
  deterministic tool cannot automate. A capability note does not justify asking
  the Architect to change a correct design.

The reviewer never edits the contract. The pipeline may send Architect-owned
findings into a contract-revision step, but tool-capability gaps must remain owned
by the tool or an explicit extension.

### Deterministic feedback to the Verifier

`review_verifier_artifacts(...)` replaces the old open-ended Reviewer loop. It
returns:

```text
status: APPROVED | VERIFIER_REPAIR_REQUIRED
summary
findings[]:
  category
  requirement
  evidence
  recommended_change
```

This feedback is intentionally local and actionable:

- `category` groups the defect, for example generated-block integrity, stimulus,
  assertion, coverage declaration, runtime instrumentation, extension bundle, or
  plan consistency;
- `requirement` states the deterministic rule that was violated;
- `evidence` identifies the exact missing, duplicated, malformed, or conflicting
  artifact;
- `recommended_change` tells the Verifier the smallest Verifier-owned correction
  to make.

The repair loop keeps the original finding set and checks those findings again.
It does not invite a new model reviewer to continuously invent additional review
criteria. The Verifier may repair its own reference code, tests, declared
coverage, or contract-local extension symbols; it may not edit the frozen
contract or the code-owned generated block.

### Runtime feedback from cocotb

The simulation produces several complementary artifacts rather than only
`PASS`/`FAIL`:

| Evidence | What it contains | Why it matters |
|---|---|---|
| Assertion failures | Feature/checker identity, message, related signals, and an observed snapshot | Identifies the violated rule and the values seen when it failed |
| Failure records | Structured assertion and runtime failures in occurrence order | Preserves more context than a final exception string |
| Coverage report | Required/applicable bins, hit counts, percent, status, and unhit obligations | Separates unexercised behavior from incorrect behavior |
| `unmet_by_blocker` | Blocked operation/reason code mapped to still-unhit required bins | Prevents an unsupported feature from disappearing from the required denominator |
| Operation sampling | Accepted canonical job, golden classification evidence, sampled feature/bin | Explains why an operation bin did or did not hit |
| Last observed snapshot | Most recent immutable signal/value snapshot | Gives temporal context near the failure |
| Stimulus ledger | Scenario, parameters, intended target, observed result, and status | Shows what was actually attempted, not just what the plan contained |
| Accepted-transfer evidence | Counts, values, addresses/coordinates, and reconstructed objects | Detects driver, packing, capture, omission, and duplication errors |

Coverage hits are measured runtime evidence. A scenario name such as
`positive_overflow` does not itself earn the overflow bin. The accepted inputs
must produce that condition in the golden trace, and correctness is evaluated
separately against the DUT output.

Compile failure, simulation failure, simulation timeout, and coverage failure are
kept distinct. A generic timeout can show that a run did not finish, but it is not
automatically credited as proof that a named lifecycle assertion detected the
fault.

### Verifier feedback to the Debugger

The `feedback_to_debugger` package selects and bounds the relevant evidence. The
pipeline first loads the run artifacts, then calls
`build_failed_run_artifacts(...)`, followed by
`build_verifier_debugger_feedback(...)`.

The resulting Verifier-owned payload contains:

```text
schema_version: 1
source: verifier_tool
verification_status:
  COMPILE_FAILURE | SIMULATION_FAILURE | SIMULATION_TIMEOUT | COVERAGE_FAILURE
failure_class
verification_evidence
failed_run_artifacts:
  coverage_plan
  coverage_report:
    status
    coverage_percent
    assertion_failures
    failure_records
    last_observed_snapshot
    operation_sampling
  stimulus_ledger:
    status
    most_recent_checked_stimuli
frozen_verifier:
  reference
  tests
  verification_plan
  operation_coverage
provenance:
  deterministic_evidence_authoritative: true
  verifier_artifacts_frozen: true
  coverage_hits_are_measured: true
```

Long values are bounded for the handoff while preserving both ends of the text;
the complete evidence remains in the run artifacts. The most recent eight ledger
records and at most the latest 128 list entries are retained in the bounded
payload.

The Verifier payload deliberately excludes `current_rtl`, frozen Architect state,
prior Debugger decisions, repair iteration, and RTL feedback. The pipeline may
place those beside this payload when constructing the Debugger input, but they
are not Verifier-owned facts. This boundary prevents stale diagnosis or mutable
RTL from being presented as measured verification evidence.

The payload does **not** decide the root cause and does not prescribe an RTL edit.
It supplies authoritative observations so the Debugger can choose among:

- RTL behavior violates a valid contract;
- Architect contract is inconsistent or underspecified;
- Verifier-authored extension/test logic is defective;
- a code-owned checker, adapter, classifier, solver, or golden model is defective;
- the environment or simulation infrastructure failed.

At the time of writing, the feedback builder and validator are implemented and
tested, but the main Debugger agent does not yet import this package directly.
The pipeline integration must wire this payload into the future
Architect → contract reviewer → RTL Generator and Verifier → Debugger flow.

### Ownership routing summary

| Evidence points to | Correct recipient | Incorrect reaction |
|---|---|---|
| Missing/contradictory contract metadata | Architect or contract revision | Asking Verifier to guess the missing semantics |
| Invalid Verifier-owned test, coverage declaration, or extension symbol | Verifier repair | Modifying RTL |
| Valid but unsupported deterministic behavior | Tool development or explicit extension | Marking the required feature inapplicable |
| Assertion/golden mismatch with valid frozen verification | Debugger, then RTL repair if diagnosed as RTL | Editing the protected generated block |
| Code-owned golden/checker/adapter defect | `verifier_tool` repair | Asking the LLM Verifier to override it locally |
| Compile/runtime infrastructure failure | Runner/environment owner | Reporting functional coverage success |

## 10. Integration responsibilities

| Pipeline component | Required integration |
|---|---|
| **Architect** | Compose the tool schemas into its output schema; render current pools in its prompt; emit explicit lifecycle, arithmetic, serialization, signal, and extension metadata; run the reference validators. |
| **Contract reviewer** | Run deterministic preflight; separate contract defects from tool-capability gaps; resolve extension reuse; send only Architect-owned contradictions back for revision. |
| **Verifier** | Import only from the public `multigent.verifier_tool` facade; use resolved plans and code-owned helpers; implement only residual extension bundles; preserve the generated block and exact coverage obligations. |
| **Simulation runner** | Supply coverage/report environment paths, compile and run cocotb, retain reports and the stimulus ledger. |
| **Debugger** | Consume structured Verifier evidence; distinguish RTL failures, contract errors, Verifier-extension errors, and tool-owned verification errors. |

Internal folders may move. Pipeline code should therefore import public functions
from `multigent.verifier_tool`, not implementation submodules.

## 11. Current scope and honest limitations

The strongest built-in operation path today is fixed-shape integer GEMM with the
supported serialization and post-operation primitives (`bias_add`, `wrap`,
`relu`, `affine_quantize`, and validated `llm_defined` scalar stages). Protocol
and lifecycle catalogs are broader, but support and strict RTL qualification are
not the same thing; consult the qualification matrices before claiming a feature
is fully verified.

The following are current implementation or integration limitations, not merely
features omitted from a pool.

### Pipeline wiring and ownership

- The deterministic contract-review facade exists, but the final independent
  Contract Reviewer stage is not yet the sole gate in the production graph. Some
  checks are still called directly by the current Architect. Integration must run
  `review_contract_deterministically` on the frozen artifacts before Verifier
  generation.
- The Verifier-to-Debugger evidence builder is implemented and tested, but the
  main Debugger agent does not yet import it. Until the pipeline adapter wires it,
  the Debugger will not automatically receive the bounded coverage report,
  ledger, frozen Verifier artifacts, and provenance described above.
- Contract preflight does not itself call every Architect-agent relational check.
  In particular, some unknown data-object/data-type references and external
  objects carried by no channel are blocked by the Architect validator while the
  preflight reports their compilation result as a note. Both layers currently
  remain necessary.
- Preflight does not receive `previous_architecture`, so it does not by itself
  prove that a revision retained every previously declared lifecycle or arithmetic
  field. The current Architect revision path performs those retention checks.

### Architect schema and prompt

- The effective Architect schema has no native `protocol_group`,
  `protocol_channel`, or `protocol_field` properties. These values currently use
  validated `key=value` tags in existing metadata/semantic strings and are
  promoted into native fields on a detached compiled copy.
- `reset_settle_cycles` is honored by the protocol checker when present, but it is
  not exposed by the current Architect response schema. Only a hand-authored
  frozen contract can select a non-default settling interval today.
- The standard-protocol binding validator and exact standard-protocol format
  renderer are available, but the current Architect's local reference validator
  and prompt do not call both directly. The deterministic preflight must therefore
  remain mandatory; otherwise malformed AXI/custom-MMIO tags may surface only
  during later plan compilation.
- The live arithmetic/serialization schema supports `packed_encoding`, but some
  static Architect prompt prose still describes only the older coarse
  serialization forms. The live-rendered schema is authoritative.
- The current leaf-oriented Architect revision patch can change scalar values but
  cannot safely add or remove an entire object or list entry. A structural repair,
  such as adding a missing control-plane sequence, needs full contract
  regeneration rather than a local patch.
- Strict-schema acceptance of every newly composed Architect field has not yet
  been exercised through a live provider call in the final integrated flow.

### Protocol and lifecycle execution

- The register-started `control_plane_sequence` campaign has a strong happy path
  and transport variants, but it does not yet run all reset-abort,
  illegal-command, and error-injection sweeps used by the direct ready/valid-start
  AXI4 path.
- A control-plane operation whose arithmetic is delegated to `llm_extension` can
  be judged protocol/lifecycle-drivable, but the current arithmetic-blocked smoke
  dispatcher calls the ready/valid AXI4 runner instead of the control-plane
  runner. That path is expected to fail and has not been qualified.
- Lifecycle coverage obligations and the generic lifecycle stimulus plan currently
  depend on a resolved command channel. A pure control-plane-sequence operation
  has no such channel, so those generic lifecycle obligations are not generated;
  control-register evidence currently covers only the dedicated path.
- Protocol rule IDs in the standard-protocol YAML and failure IDs in the Python
  checker are coupled by exact spelling. No static check currently proves every
  string pair, so a careless rule rename can break diagnostic/obligation identity
  without breaking Python import or syntax.

### Operation, serialization, and solving

- The strongest automatic mathematical backend is fixed-shape, rank-2 integer
  matrix multiplication. Dynamic shapes and a completely different operation
  family need additional canonical metadata and evaluator support.
- Built-in bias stimulus currently supports scalar or column broadcast; row and
  full-matrix bias are rejected by the automatic generator even if a broader
  mathematical contract could describe them.
- Built-in affine quantization is per-tensor with integer scale/shift,
  nearest-ties-to-even rounding, and clamp saturation. Per-axis, stochastic,
  floating-scale, or alternative rounding schemes require an extension.
- Automatic `dense_tensor` transport requires the canonical declared index order
  and regular little-endian lane packing (several narrow elements may share one
  bus word). Other dense index orders are valid metadata but not automatically
  driven. Generic `packed_encoding` is supported for inputs, but packed outputs
  cannot yet be decoded by the code-owned adapter.
- For packed encodings, `padding_value: dont_care` is accepted as metadata but the
  current encoder emits zero padding; it does not randomize or classify alternate
  don't-care patterns.
- The post-operation representation is DAG-shaped, but supported stages are unary
  and every stage must lie on the single chain ending at `post_output`. Branches
  and merges are not executable yet.
- The `llm_defined` formula grammar intentionally excludes division, modulo,
  bitwise operations, exponentiation, lookup tables, transcendental functions,
  state, and arbitrary calls. Such behavior remains a full extension.
- Z3 currently solves bounded integer reduction/product-sum witnesses and selected
  preimages. It is not general symbolic inversion for every extension formula or
  stateful/temporal operation.
- If an operation uses `classifier_profile: llm_extension`, end-to-end golden
  output is unknown. The tool can preserve supported sibling protocol/lifecycle
  work, but it cannot award operation correctness or trace-derived coverage until
  the extension supplies the missing semantics.

### Extensions and qualification

- Contract-local extension schemas, reuse resolution, symbol reachability, and
  executable fixtures are tested. Arbitrary LLM-authored extensions have not yet
  received the same real-agent and mutant qualification as the built-in path.
- Extensions remain local artifacts. Automatic mutation of global pools,
  automatic promotion after successful runs, and trust transfer from one contract
  to another are deliberately not implemented.
- A declared pool/catalog value is not automatically qualified. Strict support
  requires a generated-TB negative/positive RTL pair with the intended named
  diagnostic. Many inventory rows still await that evidence.
- The real HLS benchmark tests require the external local `gemm_golden/` RTL tree.
  It is intentionally not part of this verifier-tool commit, and those tests skip
  when the tree is absent.

The qualification rule is intentionally strict: a feature is qualified only when
a frozen contract generates the testbench, an intentionally faulty RTL or
environment fails for the intended feature-specific reason, and the corrected RTL
passes all required assertions, bins, and ledger checks. A unit test or an
unclassified timeout is useful evidence, but not full feature qualification.

## 12. Practical integration checklist

1. Import the public facade, not internal tool modules.
2. Compose lifecycle, arithmetic/serialization, and extension schemas into the
   Architect response schema.
3. Put live pool renderings in the Architect prompt.
4. Run deterministic contract preflight before invoking the Verifier.
5. Persist the frozen contracts and their compiled operation metadata.
6. Build all three resolved feature plans and retain required blocked obligations.
7. Give the Verifier only residual extension requests and reuse recommendations.
8. Install and validate the immutable code-owned testbench block.
9. Pass the combined coverage plan and output paths to the cocotb runner.
10. Persist assertion results, coverage report, stimulus ledger, accepted
    transactions, and extension manifest.
11. Bind that evidence to the exact frozen contract and generated artifacts before
    giving it to the Debugger.
12. Use the qualification matrices, not a generic simulation pass, when reporting
    what is supported.

## 13. Where to read next

- [`README.md`](README.md) — package map and cross-cutting rules.
- [`ARCHITECT_INTEGRATION.md`](ARCHITECT_INTEGRATION.md) — exact Architect fields,
  schema composers, validators, and current call sites.
- [`CONTRACT_REVIEWER_INTEGRATION.md`](CONTRACT_REVIEWER_INTEGRATION.md) —
  deterministic preflight and extension-reuse resolution.
- [`VERIFIER_INTEGRATION.md`](VERIFIER_INTEGRATION.md) — generated artifact rules,
  immutable block, obligation validation, and runtime environment.
- [`DEBUGGER_INTEGRATION.md`](DEBUGGER_INTEGRATION.md) — structured failure
  evidence and ownership routing.
- [`extensions/README.md`](extensions/README.md) — request and bundle schemas,
  validation, manifests, and current extension tests.
- [`pool/operation_metadata/README.md`](pool/operation_metadata/README.md) —
  canonical jobs, arithmetic DAG, serialization, formulas, and golden trace.
- [`pool/role_pool/README.md`](pool/role_pool/README.md) — roles, semantic classes,
  protocol profiles, standard fields, and binding rules.
- [`pool/lifecycle_policy_pool/README.md`](pool/lifecycle_policy_pool/README.md) —
  lifecycle choices and extension sentinels.
- [`pool/feature_plans/README.md`](pool/feature_plans/README.md) — feature catalogs
  and resolved-plan compilation.
- [`orchestration/README.md`](orchestration/README.md) — automatic campaign,
  generated block, runtime monitor, reports, and ledger.
- [`FULL_POOL_QUALIFICATION_MATRIX.md`](FULL_POOL_QUALIFICATION_MATRIX.md) and
  [`HLS_GOLDEN_BENCHMARK_MATRIX.md`](HLS_GOLDEN_BENCHMARK_MATRIX.md) — current
  qualification inventory and benchmark evidence.
