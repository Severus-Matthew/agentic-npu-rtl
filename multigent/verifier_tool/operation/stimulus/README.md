# Stimulus — Operation Domain

This is the `operation` leg of the three-domain stimulus taxonomy described in
[`../README.md`](../README.md) and [`../../README.md`](../../README.md). It is
the canonical, code-owned directed/randomized vector generator and golden-model
evaluator for the known integer-GEMM, raw integer-QK-score, and restricted
integer sparse-attention profiles. It is a sibling of
`operation/assertion/` and `operation/coverage/`. All three select features
independently from the Operation Feature Plan built by
`build_operation_feature_plan()` (see
[`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md)).
Coverage planning does call this generator's witness/disposition API before it
excludes an unreachable bin; that explicit reachability query does not change
feature selection.

Everything here works entirely in canonical data-object space (Python lists of
`int` keyed by `data_object` name). Nothing in this folder imports `cocotb` or
touches a `dut` handle; protocol-level serialization onto DUT pins is a
separate concern owned by `../../orchestration/campaign.py` and
`../../protocol/`. Do not confuse this folder with
`../../pool/operation_metadata/` — that
is the Architect-contract-to-canonical-metadata compiler (`architect_metadata.py`,
`canonical.py`, `arithmetic_metadata.py`, `protocol.py`, `io_metadata.py`; see
[`../../operation_metadata/README.md`](../../pool/operation_metadata/README.md)).
This folder *consumes* that compiler's output, including several of its
private helpers; it does not replace it.

## Files

- `__init__.py` — re-exports the public names below.
- `stimulus_generator.py` — the entire implementation.

## `__init__.py`

Re-exports `canonical_bin_dispositions`, `CanonicalStimulusGenerationError`,
`evaluate_canonical_operation`, `generate_canonical_discriminating_stimuli`,
`generate_canonical_stimulus_for_bin`, `generate_canonical_stimulus_suite`,
`generate_random_canonical_stimuli`, `reachable_canonical_bins_for_concept`.
`multigent/verifier_tool/__init__.py` re-exports them at the package facade
under the "Canonical operation stimulus and golden evaluation" heading.
Public callers import from that facade; internal orchestration and coverage
code may import this domain package directly to avoid a facade cycle.

## `stimulus_generator.py`

Module docstring: "The generator works in canonical data-object space. It
deliberately does not drive DUT signals... Every directed vector is evaluated
by the code-owned golden model and then fed back through the existing
classifier before it is returned." That round trip — construct, evaluate,
classify, verify the classification actually landed in the requested bin — is
the discipline behind every public function below, and is why each one can
fail with a `CanonicalStimulusGenerationError` instead of silently returning a
vector that does not test what it claims to.

The module reaches three packages up to import both public and private names
from `pool/operation_metadata/canonical.py`, including the shared
`integer_matrix_multiply_events` and `integer_sparse_attention_events` trace
engines. Each profile uses one trace for both golden evaluation and coverage
classification, so those computations cannot drift into independent copies:

```python
from ...pool.operation_metadata.canonical import (
    CanonicalOperationError,
    _binding_by_role,
    _dtype,
    _integer_bounds,
    assemble_canonical_job,
    canonical_bins_for_concept,
    classify_operation_job,
    integer_sparse_attention_events,
    integer_matrix_multiply_events,
    supported_code_owned_concepts,
)
```

This module's own package is `multigent.verifier_tool.operation.stimulus`, so
`...` steps up through `stimulus` and `operation` to `multigent.verifier_tool`,
and `...pool.operation_metadata.canonical` resolves to
`multigent/verifier_tool/pool/operation_metadata/canonical.py`. Verified at runtime
in this repo's `.venv`: `assemble_canonical_job.__module__ ==
"multigent.verifier_tool.pool.operation_metadata.canonical"`, and the facade's
`multigent.verifier_tool.evaluate_canonical_operation` is the identical
function object defined below. Three of the nine imported names
(`_binding_by_role`, `_dtype`, `_integer_bounds`) are private to
`canonical.py` — this file has a load-bearing dependency on
`pool/operation_metadata/canonical.py` internals, not just its public surface,
so a signature change to any of those three (or to `integer_matrix_multiply_events`)
must be checked against this file too.

### Error taxonomy

```python
_ERROR_CODES = {
    "unreachable",
    "metadata_missing",
    "unsupported_known_feature",
    "generation_inconclusive",
    "llm_extension_required",
}
```

`class CanonicalStimulusGenerationError(ValueError)` is constructed as
`(code, reason, *, operation_name="", concept="", bin_name="")` and rejects any
`code` outside the set above. `.as_dict()` returns
`{operation_name, concept, bin_name, code, reason}` — exactly the shape
collected into `generate_canonical_stimulus_suite()["exceptions"]`. What each
code means, from how the file actually raises it:

- `unreachable` — mathematically impossible under the contract's declared
  integer widths/signedness/dimensions (e.g. a requested accumulator value
  outside the type's `[low, high]`, or a negative activation region when the
  accumulator is unsigned and wrapping is enabled).
  `../../orchestration/campaign.py::run_code_owned_verification_campaign`
  treats this code alone as benign when it appears in a suite's
  `exceptions`; every other code aborts the campaign.
- `metadata_missing` — the contract lacks fields needed to construct a
  witness (unresolved dimensions, an unbindable bias object, invalid or
  absent integer data-type fields).
- `unsupported_known_feature` — the classifier profile is
  `integer_matrix_multiply` but the shape or post-op combination is one this
  generator does not implement (rank != 2, non-column-broadcast bias, an
  unknown stage kind, an invalid `llm_defined` formula, or duplicate
  `bias_add`/`wrap`/`relu`/`affine_quantize` stages). The declared DAG order itself is not
  restricted.
- `generation_inconclusive` — the target is within the legal numeric range
  but the general Z3 witness search in `_reduction_query`
  (`operation_metadata/canonical.py`'s `integer_matrix_multiply_events` is the
  arithmetic it solves over) proved `unsat`, or timed out without a verdict —
  this is a genuine "no witness" result, not "the search didn't happen to try
  the right combination" the way the constructive `_distribute_sum`/
  `_factor_pair` search it replaced could produce.
- `llm_extension_required` — `arithmetic.classifier_profile` is neither
`integer_matrix_multiply`, `integer_qk_score`,
`fixed_point_attention_scale`, `binary_attention_mask`, nor
`integer_sparse_attention`; this generator has
  no code-owned model for the operation.

### `_GemmModel` and `_gemm_model(operation)` (private, load-bearing)

`_GemmModel` is a frozen dataclass carrying everything every other function in
this file needs: `operation`, `operation_name`, `dimensions`, `left`, `right`,
`result` (I/O bindings by role), `bias` (optional), `accumulator_dtype`,
`post_operations`, `resolved_stage_order`, and the resolved `m`, `n`, `k`
extents. `_gemm_model(operation)` is the sole constructor: it re-derives
`left_operand_matrix` /
`right_operand_matrix` / `result_matrix` bindings via
`operation_metadata.canonical._binding_by_role`, validates rank-2 shapes and
`K` agreement, caps total tensor size at `_MAX_CANONICAL_ELEMENTS_PER_CASE =
1_000_000`, verifies `resolved_stage_order` names every declared DAG stage,
accepts `bias_add`, `wrap`, `relu`, and `affine_quantize` in any resolved dependency order, and
also accepts any number of `llm_defined` stages whose formulas pass the same
solver-compilation gate used by Contract Review in
`pool/operation_metadata/formula.py`. It resolves at most one
`bias_add` to an input bound as a per-output-column vector (shape `(n,)` only
— row or full-matrix bias is rejected as `unsupported_known_feature`) and
rejects any input/output object not accounted for by left/right/bias/result.
Every public function below calls this first, so every failure mode documented
here is a failure mode of all of them.

### `_SparseAttentionModel` and `_sparse_attention_model(operation)`

The second code-owned model resolves exactly one `query_matrix`, `key_matrix`,
`value_matrix`, `attention_mask`, and `attention_result`. It accepts fixed
rank-2 shapes `Q[Q,D]`, `K[S,D]`, `V[S,DV]`, `mask[Q,S]`, `Y[Q,DV]` and the
`integer_sparse_attention` arithmetic profile. The supported formula is exact
unnormalized binary-masked attention assembled from explicit stage boundaries:

```text
score[q,s] = sum_d Q[q,d] * K[s,d]
Y[q,v]     = sum_s (mask[q,s] ? score[q,s] * V[s,v] : 0)
```

The stage order is shared QK, identity scale, binary mask, normalization bypass,
then weighted V reduction. The mask must contain only `0` and `1`. Softmax,
non-identity score scaling, top-k pruning,
approximate arithmetic, and runtime-variable shapes are deliberately outside
this base profile; a contract must select a separate supported profile or an
explicit extension rather than silently inheriting guessed semantics.

### `_AttentionScaleModel` and `_attention_scale_model(operation)`

The scale-only model resolves `attention_score_matrix[Q,S]` to
`scaled_attention_score_matrix[Q,S]` for the
`fixed_point_attention_scale` profile. Directed bins are solved by Z3 over one
representative signed score and then checked through the concrete canonical
event trace. The trace performs exact multiplication by the contract-derived
coefficient, positive-power-of-two floor division (matching signed `>>>`), and
the declared result conversion. Coverage includes score extrema, positive and
negative discarded fractions, output sign, zero preservation, and attenuation.

### `_AttentionMaskModel` and `_attention_mask_model(operation)`

The mask-only model resolves matching
`scaled_attention_score_matrix[Q,S]`, `attention_mask[Q,S]`, and
`masked_attention_score_matrix[Q,S]` tensors for the
`binary_attention_mask` profile. Z3 generates witnesses for both mask values,
all four row sparsity patterns, score extrema/sign, masked output sign, active
preservation, and inactive nonzero zeroing. The concrete golden trace remains
the final authority for every witness.

### `evaluate_canonical_operation(operation_metadata, stimulus, *, operation_name=None) -> dict[str, list[int]]`

The golden reference implementation. Assembles a `CanonicalOperationJob` via
`operation_metadata.canonical.assemble_canonical_job(operation, stimulus, {},
{})`, then delegates the entire per-output-element arithmetic — reduction
(honoring `reduction_conversion`), the resolved post-op DAG walk (`bias_add`
honoring `bias_conversion`, `wrap`, `relu`, and per-tensor affine
quantization), and the output's
`result_conversion` — to the matching shared event engine in
`operation_metadata.canonical`. Sparse attention similarly evaluates score
reductions, binary mask filtering, score×V reduction, and result conversion
through `integer_sparse_attention_events`, which calls the same
`integer_qk_score_events` evaluator used by the standalone QK profile and then
records every downstream handoff.

### `generate_solver_compiled_stimulus_for_bin(operation_metadata, concept, bin_spec, *, operation_name=None)`

This is the bridge between Verifier-owned coverage intent and Architect-owned
formula semantics. `concept` names a formula-defined DAG stage and `bin_spec` is
the Verifier's normal declarative `{name, intent, predicate}` object. The helper
symbolically compiles the GEMM reduction and every stage up to that formula,
asks Z3 for legal A/B/bias values satisfying the predicate, reconstructs the
canonical tensors, and then runs the witness forward through the independent
golden model and classifier. An unsatisfiable predicate is reported as
`unreachable`; a timeout is `generation_inconclusive`. No Architect coverage
bins and no Verifier-authored mathematical observer are required.
and returns each event's `result_value`. This function does **not** carry its
own copy of that arithmetic: it is the same walk
`_classify_integer_matrix_multiply` (in `canonical.py`) calls to build
classification evidence, so the golden value and the classifier's trace can
never silently diverge into two independently-maintained implementations.
Raises `unsupported_known_feature` (translated from the shared walk's
`CanonicalOperationError`) for any conversion value other than `"exact"`,
`wrap_twos_complement_after_each_add`/`wrap_twos_complement_after_add`, and
`wrap_twos_complement`.

**Who calls it.** This is the GEMM oracle used wherever a "what should the DUT
have produced" answer is needed for a code-owned job.
`multigent/verifier_tool/orchestration/runtime.py`'s
`InterfaceCoverageTracker.sample_operation` calls it
directly on the values *actually accepted* by the DUT (`accepted_stimulus`,
not whatever the TB claims it drove) to compute a `trusted_expected` result
and cross-check it against the checked job's claimed expected/observed pair —
the coverage domain does not trust a Verifier-authored expected value for a
code-owned concept, it recomputes the truth itself from this function. Inside
this file it is also called by `_case`, `generate_random_canonical_stimuli`,
and `generate_canonical_discriminating_stimuli` to self-check every vector
before returning it. It is exercised directly by
`multigent/verifier_tool/tool_regression/unit/test_canonical_operation.py`,
`multigent/verifier_tool/tool_regression/unit/test_operation_feature_groups.py`, and
`multigent/verifier_tool/tool_regression/unit/test_operation_arithmetic_metadata.py` as the GEMM reference
oracle.

### `generate_canonical_stimulus_for_bin(operation_metadata, concept, bin_name, *, operation_name=None) -> dict[str, Any]`

Generates and self-checks one directed vector for a target `(concept,
bin_name)` pair. Rejects a `concept` that names a feature group rather than
an implemented leaf (`canonical_bins_for_concept(...) is None`) with
`unsupported_known_feature`. GEMM delegates to the private
`_target_stimulus(model, concept, bin_name)` path, whose arithmetic targets use
the bounded Z3 reduction solver. Sparse attention delegates to
`_target_sparse_attention_stimulus`, which symbolically compiles one complete
representative output trace (all keys and all feature-axis terms), constrains
the requested bin, and asks Z3 for a legal Q/K/V/mask witness. Then the private
`_case(...)` evaluates the vector, classifies it with
`operation_metadata.canonical.classify_operation_job`, and checks the
classifier's evidence for `concept` actually satisfies the bin's declared
`predicate` (`eq`/`between`/`one_of`), raising `generation_inconclusive` if
not. Returns `{operation_name, kind: "directed", label:
f"canonical_{concept}_{bin_name}", target: {concept, bin}, stimulus, expected,
evidence}`. Sparse-attention directed cases also carry
`solver_origin: code_owned_predicate_over_symbolic_sparse_attention_trace`.

Activation vectors follow the resolved DAG order. When affine quantization
precedes ReLU, the generator approximately inverts the declared scale and
zero-point for the negative/zero/positive pre-ReLU regions, then accepts a
candidate only after the shared golden classifier confirms its actual bin.
Likewise, when bias is **after** ReLU, the activation witness targets the
unbiased dot product, not `dot+bias`; otherwise a nominal negative-region
vector can actually enter ReLU as zero.
It does not assume raw reduction values `-1/0/+1` still have those meanings
after quantization. The `ReLU → bias` ordering has no generated-TB/RTL
fault-fix evidence recorded in the current executable qualification ledger
([`../../tool_regression/qualification/ledger.json`](../../tool_regression/qualification/ledger.json));
the DAG-order behavior itself is exercised by unit tests such as
`multigent/verifier_tool/tool_regression/unit/test_operation_arithmetic_metadata.py`.

**Who calls it.** Embedded directly into every generated cocotb testbench:
`multigent/verifier_tool/orchestration/instrumentation.py` imports it through the
facade aliased as `_contract_generate_canonical_stimulus_for_bin` and wraps it
in a generated helper, `_contract_generate_operation_stimulus(operation_name,
concept, bin_name)`, that closes over the embedded `CONTRACT_OPERATION_METADATA`
literal — that wrapper, not this function's real name, is what
Verifier-authored `llm_extension` test code actually calls inside a generated
TB. Also called in a loop, once per declared bin of every supported concept,
by `generate_canonical_stimulus_suite` below, and directly by
`multigent/verifier_tool/tool_regression/unit/test_canonical_operation.py` and
`multigent/verifier_tool/tool_regression/unit/test_operation_feature_groups.py`.

### `generate_random_canonical_stimuli(operation_metadata, count, *, operation_name=None, seed=0) -> list[dict[str, Any]]`

Reproducible randomized vectors using stdlib `random.Random(seed)` — not
`cocotb`'s RNG, so results are stable independent of simulation scheduling.
For every input element, with probability 0.35 the generator picks one of the
type's representable edge values (`{low, high, 0, -1, 1}` filtered to the
legal range), otherwise it draws uniformly from `[low, high]`. Every vector is
evaluated and classified before being returned (`kind: "randomized"`, `label:
f"canonical_random_{index:04d}"`, `target: None`).

**Who calls it.** Embedded in the generated TB as
`_contract_generate_random_operation_stimuli(operation_name, count, *,
seed=0)`. Reached at campaign run time through
`generate_canonical_stimulus_suite`'s `randomized_count` parameter, which
`../../orchestration/campaign.py::run_code_owned_verification_campaign` passes straight through
from its own `randomized_count` argument — itself sourced from
`CONTRACT_AUTOMATIC_CAMPAIGN_CONFIG['randomized_transactions_minimum']`, which
is threaded all the way from
`context["verification_policy"]["randomized_transactions_minimum"]` in
`multigent/agents/verifier.py`. Directly unit-tested in
`multigent/verifier_tool/tool_regression/unit/test_canonical_operation.py`.

### `generate_canonical_discriminating_stimuli(operation_metadata, *, operation_name=None) -> list[dict[str, Any]]`

Four fixed, hand-designed "qualification" vectors, each tagged with a
`qualification_purpose` string naming the TB bug class it targets:
`canonical_one_hot_coordinate` (wrong row/column/K indexing or dropped
terms), `canonical_asymmetric_matrix` (transpose, neighbor-swap, or
job-association errors — every element distinct so no accidental symmetry
hides a bug), `canonical_exact_cancellation` (signed-reduction/cancellation
errors; only emitted when `k >= 2` and both `+1`/`-1` are representable), and
`canonical_zero_after_nonzero` (must run immediately after the asymmetric case
in the same suite to expose stale registered state left over from the
previous job). All four are evaluated and classified like any other case
(`kind: "directed"`, `target: None`).

**Who calls it.** Embedded in the generated TB as
`_contract_generate_operation_qualification_stimuli(operation_name)`. Also
feeds `generate_canonical_stimulus_suite`'s `"qualification"` list directly in
this file, which `run_code_owned_verification_campaign` concatenates into its
case list — so the campaign always runs these four, in order, immediately
after the directed bins, for every code-owned operation.

### `generate_canonical_stimulus_suite(operation_metadata, *, operation_name=None, concepts=None, randomized_count=0, seed=0) -> dict[str, Any]`

The aggregate entry point. Resolves the concept set from
`operation_metadata.canonical.supported_code_owned_concepts` (or a
caller-supplied `concepts` override), then for every declared bin of every
concept calls `generate_canonical_stimulus_for_bin`, sorting successes into
`directed` and failures (as `.as_dict()`) into `exceptions`. Also attaches
`randomized` (via `generate_random_canonical_stimuli`) and `qualification`
(via `generate_canonical_discriminating_stimuli`). Returns `{schema_version:
1, operation_name, directed, randomized, qualification, exceptions}`.

**Who calls it.** `../../orchestration/campaign.py::run_code_owned_verification_campaign` is
the one production call site: for every non-`llm_extension` operation it
builds `cases = [*suite["directed"], *suite["qualification"],
*suite["randomized"]]` and treats any `exceptions` entry whose `code` is not
`"unreachable"` as a hard `AutomaticCampaignError` that aborts the whole
campaign. Also directly tested in
`multigent/verifier_tool/tool_regression/unit/test_operation_feature_groups.py` and
`multigent/verifier_tool/tool_regression/unit/test_canonical_operation.py`.

### `reachable_canonical_bins_for_concept(operation_metadata, concept) -> list[dict[str, Any]] | None`

Filters `canonical_bin_dispositions` (below) down to bins whose `status` is
`"required_reachable"`, returning their raw bin specs. Returns `None` only
when `concept` is not a recognized leaf at all — distinct from an empty list,
which means "recognized concept, nothing currently reachable." The docstring
explicitly defers to `canonical_bin_dispositions` "when the reason for
exclusion matters."

**Who calls it.** No non-test caller exists in this repository outside the
re-export chain (`../__init__.py`, `verifier_tool/__init__.py`). Used directly
by `multigent/verifier_tool/tool_regression/unit/test_canonical_operation.py` to enumerate the bins a
contract fixture expects to be reachable.

### `canonical_bin_dispositions(operation_metadata, concept) -> list[dict[str, Any]] | None`

For every catalog bin of `concept` (from
`operation_metadata.canonical.canonical_bins_for_concept`), attempts
`generate_canonical_stimulus_for_bin` and records one row: `{bin, status,
reason, witness}`. `status` is `"required_reachable"` on success, or the
generation error's `.code` on failure, except `"unreachable"` is renamed to
`"proven_unreachable"`. `witness` carries `{label, digest_input}` for
reachable bins, `None` otherwise. Returns `None` if `concept` has no
code-owned canonical bin compiler at all.

**Who calls it.** This is the concrete mechanism behind the top-level
[`../../README.md`](../../README.md)'s claim that "mathematically
impossible... cases are exposed as unreachable... instead of being silently
credited." `multigent/verifier_tool/operation/coverage/plan.py` imports it
directly (`from multigent.verifier_tool.operation.stimulus import
canonical_bin_dispositions` — a same-repo internal import, not through the
top-level facade) in two functions: `synthesize_code_owned_operation_coverage()`
and `operation_plan_for_tests()`. Both call it per code-owned concept to
decide which coverage bins are legitimately excludable
(`proven_unreachable`/`inapplicable`) versus must remain required
obligations, and raise `ValueError` if any bin's disposition is anything else
unresolved. This is the one place in the codebase where one domain folder
directly imports another domain folder's stimulus internals rather than only
sharing the resolved Feature Plan record shape — the coverage domain's plan
builder asks the stimulus domain's generator "can you actually hit this bin?"
before agreeing to exclude it from the required coverage set.

## Cross-references

- [`../README.md`](../README.md) — the operation domain as a whole.
- [`../../README.md`](../../README.md) — full `verifier_tool` architecture and
  the three-domain taxonomy.
- [`../../operation_metadata/README.md`](../../pool/operation_metadata/README.md) —
  the canonical operation-metadata compiler this file depends on
  (`canonical.py`, `architect_metadata.py`, `arithmetic_metadata.py`).
- [`../../feature_plans/README.md`](../../pool/feature_plans/README.md) — the
  Operation Feature Plan/catalog (`operation_features.yaml`,
  `feature_plans/operation.py`) that `operation/assertion/` and
  `operation/coverage/` build independently from the same Architect metadata
  this folder consumes.
- [`../../lifecycle/stimulus/README.md`](../../lifecycle/stimulus/README.md),
  [`../../protocol/stimulus/README.md`](../../protocol/stimulus/README.md) — the other two stimulus
  domains.
