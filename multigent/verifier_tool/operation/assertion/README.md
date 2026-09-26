# Assertion / Operation

Code-owned generation of the **one** central golden-result comparison for a
catalog-recognized operation (currently the `matrix_multiply` family — GEMM),
plus the classification comments that attach a catalog feature ID to that
already-checked transaction. This subfolder does not implement the GEMM oracle
itself (that lives in `pool/operation_metadata/canonical.py` and
`operation/stimulus/`); it only renders the runtime wrapper that calls the
oracle comparison and stamps it with taxonomy evidence.

Read this alongside
[`../../feature_plans/README.md`](../../pool/feature_plans/README.md), which
already documents (and links back here) how `operation_features.yaml`
hard-requires every catalog operation concept to share the same three
defaults: `assertion.checker = central_golden_equivalence`,
`coverage.sampler = canonical_classifier`,
`stimulus.strategy = canonical_discriminating_stimuli`. That shared default is
the reason this subfolder has no per-feature checker dispatch: there is
structurally only one operation assertion checker, so `generator.py` never
needs to select among several.

## Two independent catalogs — do not confuse them

| Catalog | File | Loader | Shape | Consumed by |
|---|---|---|---|---|
| Predefined assertion **guidance** (prose) | `operation/assertion/assertions.yaml` (this folder) | `catalog.py::load_operation_assertion_catalog` | `families.<name>.feature_checks` (prose checks per feature) + `families.<name>.required_properties` (prose oracle-level guarantees) | Rendered into the Architect and Verifier LLM prompts only. Never compiled into a Feature Plan and never drives which assertions actually execute. |
| Feature **selection** (machine) | `verifier_tool/pool/feature_plans/operation_features.yaml` (owned by `feature_plans/`, not by this folder) | `feature_plans/catalog.py::load_operation_feature_catalog` | `families.<name>.baseline_concepts` / `optional_concepts` / `feature_groups` | `feature_plan.py::build_operation_feature_plan` → `compile_assertion_feature_plan` → `generator.py::known_operation_features`. This is what actually determines which feature IDs are "code-owned" for a given frozen contract. |

`catalog.py`'s own docstring calls this out explicitly: it loads and renders
"predefined correctness guidance **separately from coverage bins**." A change
to `assertions.yaml` changes only prompt text shown to the LLMs; it has no
effect on `known_operation_features()` or on what
`validate_verifier_authored_structure` (in
[`../../orchestration/instrumentation.py`](../../orchestration/instrumentation.py)) will accept or reject. Conversely,
adding a concept to `operation_features.yaml` without adding matching prose to
`assertions.yaml` is legal but leaves the Architect/Verifier prompt silent
about that feature's intended correctness property.

## `catalog.py`

- `OPERATION_ASSERTION_CATALOG_PATH: Path` — `assertions.yaml` next to this
  module. Not re-exported by the top-level `verifier_tool/__init__.py` facade
  (unlike the other three names below); a caller outside this subpackage that
  needs the raw path must `import` it directly from
  `multigent.verifier_tool.operation.assertion`. No current caller does.

- `load_operation_assertion_catalog() -> dict[str, Any]` — `lru_cache(maxsize=1)`.
  Parses `assertions.yaml` and validates structure: `families` must be a dict;
  each family's `feature_checks` must be a dict of non-empty check-string
  lists; each family's `required_properties` entry must have non-empty
  `applies_when` and `check` strings. Raises `ValueError` on any violation —
  this runs at import/first-call time, so a malformed catalog fails fast
  rather than producing an empty prompt section. Exported from the facade;
  called directly in `multigent/tests/test_operation_coverage.py` (asserts the
  `matrix_multiply` family and its `feature_checks`/`required_properties`
  shape) and internally by `render_operation_assertion_catalog` below.

- `render_operation_assertion_catalog() -> str` — flattens the loaded catalog
  into human-readable lines: one `- <family> predefined assertions:` header,
  then one `  - <feature>: checks=<check> | <check> | ...` line per feature,
  then one `  - property <name>: applies_when=<...>; check=<...>` line per
  required property. **Called from**
  `multigent/agents/architect.py:ArchitectAgent._build_architecture_task`
  (concatenated after `render_operation_coverage_catalog()` into the Architect
  task prompt) and from
  `multigent/agents/verifier.py:VerifierAgent._build_task`
  (same concatenation, into the Verifier task prompt). Both agents show the
  LLM the same rendered text, so the Architect knows what will later be
  code-owned and the Verifier knows what it must *not* re-assert.

## `generator.py`

- `known_operation_features(architecture_contract: Mapping[str, Any] | None) -> dict[str, tuple[str, ...]]`
  — the actual (machine) feature-selection path. Calls
  `feature_plan.py::build_operation_feature_plan(architecture_contract)`, then
  `feature_plans/compiler.py::compile_assertion_feature_plan(feature_plan)`,
  then groups the compiled entries' `id` strings by
  `bindings.operation_name`. Returns e.g.
  `{"gemm0": ("operation.gemm0.dimensions", "operation.gemm0.bias", ...)}`.
  An operation whose `coverage_family_source` is `"novel"` (not a recognized
  catalog family) contributes no entries here — by construction, not by a
  special case — because `build_operation_feature_plan` never emits features
  for it (see
  [`../../feature_plans/README.md`](../../pool/feature_plans/README.md#operationpybuild_operation_feature_planarchitecture_contract)).
  **Called from** `../../orchestration/instrumentation.py:render_contract_generated_block`
  (to embed `CONTRACT_OPERATION_ASSERTION_FEATURES` and to build the
  `operation_features` argument passed to `render_operation_assertion_lines`
  below) and from `../../orchestration/instrumentation.py:validate_verifier_authored_structure`
  (to compute `pipeline_owned_operation_features`, the set a Verifier-authored
  assertion comment must *not* duplicate, and to derive
  `required_llm_operation_features` — the contract-selected features that have
  **no** catalog concept, i.e. must be asserted by the Verifier under
  `# === LLM-GENERATED OPERATION ASSERTIONS ===`).

That legacy taxonomy-missing comment path is separate from the normalized
contract-local `architecture_contract.verification_extensions[]` flow. The
latter is validated as an exact request/bundle pair by `extensions/authoring.py`
and names its own assertion, coverage, and stimulus implementations; it is not
silently inserted into the built-in Operation Feature Plan.

- `render_operation_assertion_lines(operation_features: Mapping[str, tuple[str, ...]]) -> list[str]`
  — renders the literal Python source of
  `_contract_record_checked_stimulus(stimulus_kind, stimulus, expected, observed, *, operations, label)`,
  the single function every checked DUT transaction (directed, random, or
  qualification) is funneled through. Its body:
  1. Normalizes `expected`/`observed` via
     `normalize_verification_value` (imported into the generated block as
     `_contract_normalize_verification_value`).
  2. Emits **one** `assert observed_value == expected_value` under the fixed
     comment `# OPERATION ASSERTION [central_golden_equivalence]` — this is
     the entire operation correctness check; it is never repeated per
     feature.
  3. For each `(operation, features)` pair, emits
     `if <operation> in operations:` followed by one
     `# OPERATION ASSERTION [<feature>] (central comparison; classified evidence)`
     comment per feature and a `pass` — these are audit labels only, not
     additional assertions, because (per the docstring) "catalog features are
     classifications of the already checked transaction," so repeating
     `observed == expected` per feature "would only create misleading
     duplicate assertions."
  4. Forwards the recorded stimulus to
     `record_stimulus`/`sample_operation` (imported as
     `_contract_runtime_record_stimulus` / `_contract_runtime_sample_operation`)
     so coverage sampling and the stimulus ledger see the same transaction.

  **Called only from** `../../orchestration/instrumentation.py:render_contract_generated_block`.
  Not called directly by any agent or test; its output is exercised indirectly
  by every test in `multigent/tests/test_canonical_operation.py`,
  `test_operation_sampling.py`, and `test_tb_instrumentation.py` that execs a
  rendered block and then invokes `_contract_record_checked_stimulus`.

## `assertions.yaml`

One taxonomy, currently one family (`matrix_multiply`), under
`taxonomy: {name: accelerator_operation_predefined_assertions, version: "0.1", ...}`.
Its `required_properties` are prose guidance, not separately executable
checkers or evidence that an unsupported GEMM option has automatic support.
The executable concept catalog is the narrowed
`pool/feature_plans/operation_features.yaml`.

```yaml
families:
  matrix_multiply:
    feature_checks:
      bias: [the one supported per-output-column bias vector is indexed and added at its declared DAG stage]
      activation: [ReLU is applied at its declared DAG stage]
    required_properties:
      oracle_equivalence:
        applies_when: always
        check: Every transferred logical result element equals an independent
          matrix multiplication oracle after all contract defined numeric and
          post processing stages.
```

### From catalog entry to generated line

Given a frozen operation named `gemm0` of family `matrix_multiply` with
`feature_extensions: [bias]` selected, the *machine* catalog
(`feature_plans/operation_features.yaml`) resolves a feature with
`id: operation.gemm0.bias` (built by
`operation/coverage/plan.py::canonical_operation_obligation_id("gemm0", "bias")`,
which returns `f"operation.{operation_id}.{local_id}"`) and
`assertion: {checker: central_golden_equivalence}` (the family default).
`known_operation_features()` then returns
`{"gemm0": ("operation.gemm0.bias", ...)}`, and
`render_operation_assertion_lines` emits:

```python
    if 'gemm0' in operations:
        # CATALOG OPERATION [gemm0]
        # OPERATION ASSERTION [operation.gemm0.bias] (central comparison; classified evidence)
        pass
```

Separately, and only for prompt text, the *prose* catalog's
`families.matrix_multiply.feature_checks.bias` entry is rendered by
`render_operation_assertion_catalog()` as:

```text
  - bias: checks=the one supported per-output-column bias vector is indexed and added at its declared DAG stage
```

Nothing ties these two `bias` occurrences together at runtime — the ID string
`operation.gemm0.bias` and the prose word `bias` line up only because both
YAML files happen to spell the concept the same way. Renaming a concept in one
catalog without the other silently desynchronizes the rendered guidance from
the actual code-owned ID.

## Who else touches this subfolder

- `../../orchestration/instrumentation.py` imports `known_operation_features` and
  `render_operation_assertion_lines` at module scope and is the only caller of
  either.
- `multigent/agents/architect.py` and `multigent/agents/verifier.py` call only
  `render_operation_assertion_catalog` (prompt text), never
  `known_operation_features` or `render_operation_assertion_lines` directly —
  those stay behind the instrumentation boundary.
- `multigent/tests/test_operation_coverage.py` exercises `catalog.py` directly.
  `test_canonical_operation.py`, `test_operation_sampling.py`, and
  `test_tb_instrumentation.py` exercise `generator.py` only indirectly, through
  `render_contract_generated_block`/`install_contract_generated_block`.

## See also

- [`../README.md`](../README.md) — the operation domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — how this
  subfolder's output is embedded into the generated TB block.
- [`../../lifecycle/assertion/README.md`](../../lifecycle/assertion/README.md),
  [`../../protocol/assertion/README.md`](../../protocol/assertion/README.md) — the other two assertion
  domains; unlike this one, both are backed entirely by a `feature_plans/*.yaml`
  catalog with no local YAML of their own.
- [`../../feature_plans/README.md`](../../pool/feature_plans/README.md) — the
  Operation Feature Plan matcher and the shared resolved-feature-plan shape.
- [`../../operation_metadata/README.md`](../../pool/operation_metadata/README.md) —
  where the GEMM arithmetic classification and golden semantics this oracle
  ultimately checks against are actually defined.
