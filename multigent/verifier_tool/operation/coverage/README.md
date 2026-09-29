# Coverage: operation domain

This folder validates, instantiates, and samples functional/data coverage for
the **operation** domain — arithmetic and data-object correctness (code-owned
integer GEMM, or Verifier-authored extensions for other math), as opposed to
`../protocol/` (bus rules) or
`../lifecycle/` (command/job/busy/completion/error). Do not confuse this folder
with `multigent/verifier_tool/pool/operation_metadata/`: that package compiles
an Architect contract into canonical
arithmetic/I-O metadata (`architect_metadata.py`, `canonical.py`); *this*
folder consumes that metadata to build and sample coverage obligations. See
[`../../README.md`](../../README.md) for the full disambiguation.

Two independent YAML catalogs back this folder, and they are not
interchangeable:

- `multigent/verifier_tool/pool/feature_plans/operation_features.yaml` — the catalog
  of code-owned operation **families** (currently only `matrix_multiply`, aliases `gemm`,
  `matmul`, etc.), their baseline/optional/grouped **concepts**, and starter
  bin names. Reached via `feature_plans/catalog.py:load_operation_feature_catalog()`.
  `plan.py`'s `OPERATION_COVERAGE_FAMILIES_PATH` is only an alias for
  `feature_plans.catalog.OPERATION_FEATURES_PATH` — nothing in this folder
  reads that path directly; it exists so external callers do not need to know
  the catalog physically lives under `feature_plans/`.
- `sampling_templates.yaml` (this folder, next to `sampling.py`) — a genuinely
  separate, local catalog of eight reusable **DUT-wiring templates**
  (`custom`, `dimension`, `integer_operand`, `boolean_mode`, `discrete_mode`,
  `tile_shape`, `channel_stall`, `integer_add_overflow`) that describe *how to
  read a coverage point's value off real signals*, independent of which
  operation family or concept it belongs to.

In other words: `operation_features.yaml` says *what must be covered*
(a `matrix_multiply` operation must cover `dimensions`, `operand_values`, and
`accumulation`); `sampling_templates.yaml` says *how a declared coverage point
gets its runtime value* (e.g. read a `dimension` field and bin it against the
contract's declared minimum/maximum). `plan.py` owns the former;
`sampling.py` owns the latter.

## Files

- `__init__.py` — re-exports only `plan.py`'s public names.
- `plan.py` (712 lines) — catalog loading/validation, Architect-feature
  validation, deterministic code-owned coverpoint synthesis, and coverage-plan
  assembly.
- `sampling.py` (653 lines) — static (AST-only, never executed) extraction of
  Verifier-authored `OPERATION_SAMPLING_BINDINGS`, their validation/compilation
  against `sampling_templates.yaml`, and the runtime `OperationSamplingMonitor`.
- `sampling_templates.yaml` — the seven DUT-wiring templates described above.

## Public API surface: `__init__.py` vs. the top-level facade

`operation/coverage/__init__.py` re-exports **only** `plan.py`'s names:
`OPERATION_COVERAGE_FAMILIES_PATH`, `build_operation_coverage_plan`,
`load_operation_coverage_families`, `merge_coverage_plans`, `operation_family`,
`render_operation_coverage_catalog`, `synthesize_code_owned_operation_coverage`,
`validate_architecture_operation_features`, `validate_operation_coverage`
(and, unlike the top facade, **not** `validate_frozen_operation_scope` or
`operation_plan_for_tests` — those two are defined in `plan.py` but missing
from this package's own `__all__`/import list, a small inconsistency worth
knowing about if you go looking for them here instead of at the top facade).

`sampling.py`'s public names — `OperationSamplingError`,
`effective_operation_coverage`, `extract_operation_sampling_bindings`,
`normalize_operation_sampling_bindings`, `operation_observer_views`,
`render_operation_sampling_catalog` — are **not** re-exported by this package's
`__init__.py` at all. The top-level facade
(`multigent/verifier_tool/__init__.py`) imports them directly from
`multigent.verifier_tool.operation.coverage.sampling`, bypassing this package.
Practical consequence: `from multigent.verifier_tool.operation.coverage import
OperationSamplingError` fails; you need either
`from multigent.verifier_tool import OperationSamplingError` or
`from multigent.verifier_tool.operation.coverage.sampling import OperationSamplingError`.

Fully internal (not in the top facade, not in this package's `__init__.py`):
`attach_operation_sampling`, `OperationSamplingMonitor`,
`load_operation_sampling_templates`, `TEMPLATES_PATH`, `operation_plan_for_tests`'s
and `build_operation_coverage_plan`'s in-function `from ... import` of each
other's private helpers, and every `_`-prefixed function in both files.
`operation_plan_for_tests` and `validate_frozen_operation_scope` **are** in the
top-level facade despite the `__init__.py` gap noted above.

## `plan.py`

### `canonical_operation_obligation_id(operation_name, point_or_claim_id) -> str`

Returns `f"operation.{safe(operation_name)}.{safe(local_id)}"`, stripping any
number of redundant `operation_<name>_` prefixes a structured-output retry may
have doubled onto the local id (the docstring explains this defends against
the LLM copying the fully-qualified prefix into the local field on a semantic
retry). This is the canonical identity function for every operation obligation
in the codebase — used by `validate_operation_coverage`,
`synthesize_code_owned_operation_coverage`, `build_operation_coverage_plan`,
`operation_plan_for_tests`, and, from `sampling.py`, every binding-identity
lookup (`attach_operation_sampling`, `effective_operation_coverage`,
`operation_observer_views`, `OperationSamplingMonitor.bind_observers`). Also
called directly from `multigent/agents/verifier.py` and tested in
`multigent/verifier_tool/tool_regression/integration/test_operation_coverage.py`.

### `canonicalize_operation_obligation_claim(claim, operation_names) -> str`

Strips a literal `operation.<name>.` prefix (if `<name>` is in
`operation_names`) and re-derives the canonical id through the function above;
otherwise returns the claim unchanged. Called only from
`multigent/agents/verifier.py` when reconciling an LLM-declared
`COVERAGE_OBLIGATIONS` set against the deterministic plan.

### `load_operation_coverage_families() -> dict[str, Any]`

`@lru_cache(maxsize=1)`. Loads `operation_features.yaml` via
`load_operation_feature_catalog()` and re-validates structural invariants
specific to this folder's consumption: every family needs non-empty `aliases`
and `baseline_concepts` with no duplicates; `starter_bins` must have exactly
one entry per baseline concept, each a non-empty list of distinct bin names;
`optional_concepts` (flattened through `operation_feature_groups`/
`operation_optional_concepts` in `feature_plans/catalog.py`, so group children
are included) must not collide with baseline concepts, and each optional
concept needs a non-empty `applies_when` string and non-empty distinct
`starter_bins`. Called by nearly every other function in this file.

### `render_operation_coverage_catalog() -> str`

Renders the family/concept/starter-bin catalog as indented plain text for LLM
prompts, explicitly warning that feature groups are organizational only and
must not be selected wholesale. Called by `multigent/agents/architect.py`
(prompt construction) and `multigent/agents/verifier.py` (prompt + revision
construction); tested directly in `test_operation_coverage.py` and
`test_operation_feature_groups.py`.

### `operation_family(kind: object) -> str | None`

Normalizes `kind` (lowercase, non-alphanumeric collapsed to `_`) and looks it
up against every family's `aliases` (also normalized). Returns `None` for an
unrecognized kind — the novel-family path. Called by
`validate_architecture_operation_features` and `validate_operation_coverage`
to cross-check the Architect's declared `coverage_family` against what the
`kind` string implies.

### `validate_architecture_operation_features(architecture_contract) -> list[str]`

Pure validation (returns error strings, raises nothing) over
`architecture_contract["operations"]`. Enforces: `coverage_family` is declared;
`coverage_family_source` is `catalog` or `novel` and agrees with whether
`operation_family(kind)` actually recognizes the family; `features` and
`feature_extensions` are each duplicate-free and disjoint from each other;
for a catalog family, the declared `features` set equals exactly that family's
`baseline_concepts` (feature groups excluded from the "unknown" check via
`operation_feature_groups`). Called by `multigent/agents/architect.py` (contract
freeze validation) and `multigent/agents/verifier.py`.

### `validate_operation_coverage(architecture_contract, specs) -> list[str]`

The heavier validator, run over Verifier-declared `specs` (one dict per
operation: `{"operation_name", "family", "coverpoints": [...]}`). Checks, per
operation: it references a known operation and isn't duplicated; its `family`
matches the contract's `coverage_family` and the kind-implied family; every
coverpoint has a unique canonical id, a `concept` that is not itself a feature
group, non-empty distinct bin names, and (via `_validate_predicate`) a
structurally valid predicate (`eq`/`neq`/`lt`/`lte`/`gt`/`gte` take 1 arg;
`between`/`mod_eq`/`mod_ne` take 2; `truthy`/`falsy` take 0; `one_of` takes
≥1); no bin's `intent` text contains a "this isn't really covered" marker word
(`inapplicable`, `not sampled`, `unreachable`, `impossible`, `placeholder`) —
every declared bin must represent at least one legal, reachable transaction;
no two bins under one coverpoint share byte-identical predicates. It then
recomputes, per operation, the required concept set (`baseline ∪
feature_extensions ∪ solver-compiled formula-stage names`) and checks every
required concept is implemented by a coverpoint whose `source` field matches
its expected origin (`baseline`, `architect_extension`, or `llm_extension` for
anything else) — a concept
implemented with the wrong `source` label is an error even if the concept
itself is present. Finally checks every contract operation has *some* coverage
entry. Called by `multigent/agents/verifier.py` (gating `VERIFICATION_READY`,
fed `effective_operation_coverage(...)` output, not the raw LLM `specs`) and
directly in `test_operation_coverage.py`/`test_operation_feature_groups.py`.

### `validate_frozen_operation_scope(architecture_contract, specs) -> list[str]`

A narrower, later-stage check: for every spec, computes the operation's frozen
allowed-concept set (`operation_feature_selections` — baseline plus
`feature_extensions`, groups excluded) and rejects any coverpoint whose
`concept` is not in that set. This is what stops a Verifier revision from
quietly adding new "required" coverage concepts after the Architect contract
froze — the docstring is explicit that a Verifier-proposed risk may still be
reported *diagnostically*, just not as a release-gating bin. Called by
`multigent/agents/verifier.py` at both initial generation and revision time.

### `synthesize_code_owned_operation_coverage(specs, architecture_contract, operation_metadata) -> list[dict]`

The mechanism that makes known-family coverage **deterministic instead of
LLM-authored**. For every contract operation, computes which selected concepts
are `supported_code_owned_concepts(operation_metadata)` (from
`operation_metadata/canonical.py` — currently `dimensions`, `operand_values`,
`accumulation` for `integer_matrix_multiply`, plus
`bias`/`activation`/`quantization` when
those post-op stages are present). For each such concept, calls
`operation.stimulus.canonical_bin_dispositions(metadata, concept)` and requires
every returned bin to already be resolved to `required_reachable`,
`proven_unreachable`, or `inapplicable` — an unresolved bin is a hard
`ValueError`, not a silent skip. Only `required_reachable` bins become actual
coverpoint bins. Non-code-owned coverpoints from the LLM's previous `specs` are
preserved untouched (filtered by concept not being in `code_owned` or a feature
group). The returned list always has `coverpoints` for `code_owned` concepts
first, preserved ones after. Called by `multigent/agents/verifier.py`
(`_with_contract_generated_blocks`, unconditionally after canonical metadata is
available because synthesis is per concept rather than all-or-nothing — this
overwrites only code-owned portions of `result["operation_coverage"]` before it
is persisted) and by
`multigent/scripts/build_taxonomy_release.py` (release gate, called with an
**empty** `specs` list since the release gate has no LLM output to preserve
anything from).

### `build_operation_coverage_plan(specs, *, sampling_bindings=None, architecture=None, interface=None) -> dict[str, Any]`

Turns validated `specs` into the `obligations` list: one
`operation_coverpoint`-template obligation per coverpoint, id via
`canonical_operation_obligation_id`, `bindings` carrying
`operation_name`/`family`/`field`/`concept`/`source`/(`feature_group` if the
concept is an optional child of a group). Raises if a `spec["coverpoints"]`
entry's `concept` is itself a feature-group name (groups cannot create bins —
this mirrors the check in `validate_operation_coverage` but is enforced again
here as a last line of defense right before instantiation). Every obligation
also carries an always-empty `"checks": []` field — nothing in this codebase
populates it; treat it as a vestigial placeholder, not a hook to wire into.
If `sampling_bindings` is given, calls `sampling.py:attach_operation_sampling`
(local import, to avoid a module-level cycle between `plan.py` and
`sampling.py`, which import each other's helpers both ways) to bind DUT
sampling metadata onto each obligation before returning. Returns
`{"schema_version": 1, "source": "verifier operation coverage", "obligations":
[...]}`.

Note: unlike `../../lifecycle/coverage/plan.py` and
`../../protocol/coverage/plan.py`, this
function attaches **no** `feature_plan`/`compiled_coverage` keys — it never
calls `feature_plans/operation.py:build_operation_feature_plan` at all. That
function is only ever called from `operation/assertion/generator.py` (a
sibling consumer in the assertion domain); operation coverage and operation
assertion generation each derive their own coverage points independently, per
the "sibling consumers, not layers" rule in [`../../README.md`](../../README.md).
Called by `multigent/verifier_tool/tool_regression/unit/test_operation_feature_groups.py`,
`test_operation_sampling.py`, `test_operation_coverage.py` directly, and
transitively (through `operation_plan_for_tests`) by all production callers.

### `operation_plan_for_tests(specs, contents, architecture, interface) -> dict[str, Any]`

The real production entry point (not `build_operation_coverage_plan` directly).
Builds the canonical `metadata` via `operation_metadata.build_architect_operation_metadata`,
computes `code_owned` concepts and solver-compiled formula concepts, and —
critically — computes `canonical_ids` (the set of obligation ids whose concept
is code-owned or formula-backed) so that
`extract_operation_sampling_bindings(contents)` (static AST scan of the
Verifier's generated test file sources) can be filtered down to `llm_bindings`:
only bindings for **non**-code-owned points are passed through to
`build_operation_coverage_plan`. It then builds the plan and, for every
code-owned obligation, re-derives its bins from
`stimulus.operation.canonical_bin_dispositions(metadata_by_operation[name],
concept)` (raising `OperationSamplingError` if anything is unresolved) and
stamps `bindings["sampling"] = {"template": "canonical_job", "origin":
"verifier_tool"}`. For every formula-backed obligation it also calls
`generate_solver_compiled_stimulus_for_bin` on **every Verifier-declared bin
before the TB is accepted**. A satisfiable bin receives its concrete witness
and canonical-job sampling binding; an unreachable, unsupported, or
inconclusive bin rejects the plan immediately so failure cannot be deferred to
simulation. These bindings are the markers `InterfaceCoverageTracker.sample_operation`
and `OperationSamplingMonitor` use to recognize a point whose *value* comes
from the checked-job classifier rather than a per-cycle DUT read. Also calls
`sampling.py:operation_observer_views(contents, ignored_ids=canonical_ids)`
purely to validate LLM-owned custom observer function bodies without
executing them (return value discarded — validation-only call). Finally
asserts every obligation ended up with a `sampling` binding, raising
`OperationSamplingError` listing the missing ones otherwise. This is the
function `multigent/agents/verifier.py`, `multigent/orchestration/artifacts.py`,
`multigent/orchestration/verification_tools_node.py`, and
`multigent/scripts/build_taxonomy_release.py` all actually call — not
`build_operation_coverage_plan` directly.

### `merge_coverage_plans(interface_plan, operation_plan) -> dict[str, Any]`

The final assembly point for a complete coverage plan. Builds
`lifecycle_plan = build_lifecycle_coverage_plan(interface_plan["interface_contract"],
operation_plan["operation_metadata"])` (see [`../../lifecycle/coverage/README.md`](../../lifecycle/coverage/README.md)),
concatenates all three domains' `obligations` lists, asserts no id collisions,
sorts by id, and calls `manifest.py:compile_verification_manifest(interface_plan,
operation_plan, lifecycle_plan)` — reading only each plan's `obligations`, not
its `feature_plan`/`compiled_coverage` — to produce
`verification_manifest`/`verification_manifest_hash`. This is the plan shape
`InterfaceCoverageTracker` actually consumes at simulation time (see
[`../README.md`](../README.md)). Called by `multigent/agents/verifier.py`,
`multigent/orchestration/artifacts.py`, `multigent/orchestration/verification_tools_node.py`,
and `multigent/scripts/build_taxonomy_release.py` — always as
`merge_coverage_plans(build_interface_coverage_plan(interface),
operation_plan_for_tests(...))`.

## `sampling.py`

### Static-only reading (`_static_binding_value`, `_binding_syntax`)

The foundation of this whole file: Verifier-authored test modules are **parsed,
never imported or executed**, to read the literal
`OPERATION_SAMPLING_BINDINGS = [...]` module constant. `_binding_syntax(content)`
walks the module's top-level `ast.Assign`/`ast.AnnAssign` nodes, recording every
name binding and flagging the (at most one permitted) `OPERATION_SAMPLING_BINDINGS`
declaration. `_static_binding_value(node, definitions, resolving)` recursively
resolves only `ast.Constant`, `ast.List`/`ast.Tuple`, `ast.Dict`, and
`ast.Name` references to another top-level literal (cycle-guarded via
`resolving`) — anything else (a function call, an f-string, an imported
constant) raises. This is why the top-level docstring can promise "never
execute generated Python."

### `load_operation_sampling_templates() -> dict[str, Any]`

`@lru_cache(maxsize=1)`. Loads `sampling_templates.yaml` and asserts its
`templates` keys exactly equal the hardcoded `_SAMPLERS` set — a template
present in one but not the other is a load error, not a silent mismatch.
Purely internal (no facade export); called by `render_operation_sampling_catalog`
and `_compile`.

### `render_operation_sampling_catalog() -> str`

Renders the seven templates' required fields, metadata keys, bin rule, and
description as plain text. Called only by `multigent/agents/verifier.py`
(prompt construction, `sampling_catalog = render_operation_sampling_catalog()`).

### `extract_operation_sampling_bindings(contents: list[str]) -> list[dict[str, Any]]`

Public static-extraction entry point: for each source string, parses it,
requires at most one `OPERATION_SAMPLING_BINDINGS` declaration, resolves it via
`_static_binding_value`, and requires the result to be a list of dicts.
Concatenates across all `contents`. Called by `plan.py:operation_plan_for_tests`
and `multigent/agents/verifier.py` (both to filter code-owned bindings out and
to snapshot `operation_sampling_bindings.yaml` to disk for audit).

### `normalize_operation_sampling_bindings(content, *, code_owned_ids=None, all_points_code_owned=False) -> str`

Rewrites a module's source text in place (returns new text, does not touch the
filesystem). If every point in the module is code-owned, replaces the entire
declaration(s) with a single `OPERATION_SAMPLING_BINDINGS = []` — even a
malformed LLM declaration is safely discardable in that case, since no
semantic connection choice remains for the LLM to make. Otherwise requires
exactly one declaration, resolves it, and (if `code_owned_ids` given) filters
out bindings whose canonical id is code-owned, then replaces the source line
range with `repr(bindings)`. Called only by `multigent/agents/verifier.py`
when persisting a candidate whose declared bindings need code-owned entries
stripped before the file is written to `tests/`.

### `operation_observer_views(contents, *, ignored_ids=None) -> list[dict[str, Any]]`

For every `template: custom` binding not in `ignored_ids`, locates the named
observer function by AST, requires it to be a plain synchronous
`def observer(values, state):` (no decorators, no `*args`/`**kwargs`/defaults),
then transitively collects every same-module function it calls (via
`ast.walk`/`ast.Call` name matching) as `helpers`, and returns
`{"observer": name, "source": <unparsed source>, "helpers": [...]}` per
observer — a read-only view for review/prompting, not a validator that
prevents bad code from loading (that happens later, at bind time, in
`OperationSamplingMonitor.bind_observers`). Called by
`plan.py:operation_plan_for_tests` purely for its side-effect of raising on a
malformed observer signature (return value discarded there).

### `_compile(raw, architecture, interface) -> tuple[dict, list]`

The heart of template validation — not exported, but the single place that
knows what each of the seven templates means. Validates the binding's keys are
all recognized, resolves the `channel` (via `_channel`, requiring exactly one
`valid`/`ready`-role signal each) for `event: transfer` bindings (or forbids a
channel for `event: clock`), resolves `fields` (via `_field`, which accepts
either an explicit `signal` name or a `channel`+`role` pair and validates any
declared `lsb`/`width` fit within the signal's literal declared width), and
then branches per template:

| template | requires | derives bins from |
| --- | --- | --- |
| `custom` | `observer` (identifier), `field_types` mapping fields to contract data types | none — bins are LLM-owned; `bins = None` preserves whatever the caller already declared |
| `dimension` | `dimension` (a contract `dimensions[]` entry) | `_bound_bins(minimum, maximum)`: `fixed` if min==max, else `minimum`/`interior`(if a gap exists)/`maximum` |
| `integer_operand` | `data_type` | `zero`, `positive`/`negative` (if reachable), `minimum`, `maximum` from `_dtype()`'s signed/unsigned bounds |
| `boolean_mode` / `discrete_mode` | `legal_values` (distinct nonnegative ints; boolean restricted to `{0,1}`) | one `enabled`/`disabled` (boolean) or `mode_<n>` (discrete) bin per legal value |
| `tile_shape` | `tile_parameters` mapping each dimension field to a contract `parameters[]` entry with a positive literal default | `full_tile` bin included if every axis has a reachable tile-aligned value between its minimum and maximum; `partial_tile` bin included if any axis can also take a non-tile-aligned value in range (`minimum != maximum` with `tile > 1`, or `minimum` itself isn't tile-aligned) |
| `channel_stall` | nothing beyond the channel; forbids `guards` | copied verbatim from YAML's `bins:` (the four fixed stall-length bins) |
| `integer_add_overflow` | `operand_types` (`a`,`b`) and `result_type` | `no_overflow`/`overflow` depending on whether the operand range and result range actually overlap/exceed |

`integer_operand`/`boolean_mode` may omit `fields.value` entirely when the
channel has exactly one `payload`-role signal whose literal declared
width/signedness exactly match the concept (`_certain_whole_payload` — this is
the one place a *missing* Verifier declaration is still code-bound, per the
YAML's own stated rule that "a missing field may be code-bound only to the
unique whole payload... when literal width and signedness exactly match").
Every numeric field/guard is checked against `_check_unsigned_encoding` to
reject an encoding wider than the field can represent.

### `attach_operation_sampling(plan, bindings, architecture, interface) -> dict`

Deep-copies `plan`, indexes its obligations by id, and for each raw binding:
computes its canonical identity, rejects a second **conflicting** declaration
of the same identity (identical repeats are tolerated — "several TB modules
may repeat the same connection metadata"), rejects a binding for an
undeclared/mismatched-operation obligation, compiles it via `_compile`
(wrapping any stray `TypeError`/`KeyError`/`ValueError` as
`OperationSamplingError`, since malformed static metadata is meant to surface
as a counted Verifier correction, not an uncaught Python exception), and
overwrites the obligation's `bins` (if the template produced any — `custom`
does not) and `bindings["sampling"]`. Called only from
`plan.py:build_operation_coverage_plan`.

### `effective_operation_coverage(specs, plan) -> list[dict]`

Deep-copies `specs` and, for every coverpoint whose obligation has a
`sampling` binding attached, overwrites that coverpoint's `bins` with the
authoritative runtime bins from `plan`. The docstring is blunt about why this
exists: "expose authoritative runtime bins to validation/review, not ignored
draft bins" — i.e. `validate_operation_coverage`/`validate_frozen_operation_scope`
must never validate against the LLM's stale draft bin list once a template or
canonical classifier has determined the real ones. Called by
`multigent/agents/verifier.py` (wrapping every `validate_operation_coverage`/
`validate_frozen_operation_scope` call) and tested directly.

### `OperationSamplingMonitor`

Constructed once per test by `InterfaceCoverageTracker.__init__` as
`self.operation_monitor = OperationSamplingMonitor(self.plan, self._signal,
self._signal_width)`. Raises `OperationSamplingError` up front if any
`operation_coverpoint` obligation lacks a `sampling` binding (surfaced by the
tracker as `CoverageRuntimeError`).

- **`bind_observers(module_globals)`** — called once per test by the
  `contract_coverage()` decorator (`orchestration/runtime.py`), reading the test
  module's own `OPERATION_SAMPLING_BINDINGS` global to activate *only* the
  `custom` observers this specific test module declares (a `canonical_job`
  point is silently skipped — it needs no observer function; any other
  mismatch is an error). This is what lets multiple test modules coexist
  without one module's custom observer function shadowing another's.
- **`sample(dut, sample_value, *, reset_active, completed_stalls)`** — called
  once per non-reset sample from `InterfaceCoverageTracker.sample_snapshot`.
  Skips `canonical_job` points entirely (those are only ever fed values from
  `record_stimulus`'s classifier evidence, never from per-cycle DUT reads).
  For every other point: evaluates `guards` (an equality check on another
  field) first; for `event: transfer` templates requires the bound channel's
  `valid`/`ready` to indicate a fired transfer (or, for `channel_stall`
  specifically, requires `valid && !ready`, i.e. an active stall, not a
  transfer); then computes the template-specific value (custom observer call,
  the `completed_stalls` lookup for `channel_stall`, direct field read for
  `integer_operand`, the tile-alignment boolean for `tile_shape`, the
  overflow boolean for `integer_add_overflow`, or a plain field read
  otherwise) and calls `sample_value(identity, value)` — which is
  `ContractCocotbCoverageModel.sample_operation`, wired in by the tracker.
  A custom observer that raises is re-wrapped as `OperationSamplingError`; one
  that returns a non-scalar (not `str`/`int`/`float`/`bool`, or a non-finite
  float) is rejected outright — "never a claimed hit collection."
- **`report()`** — returns one row per sampled point with `origin`
  (`checked_canonical_job` vs `runtime_dut_observation`), `implementation`
  (`verifier_tool_classifier` / `llm_custom_observer` / `reusable_template`),
  sample/last-value counts. Embedded in `InterfaceCoverageTracker.report()`
  under `"operation_sampling"`.

## Example: `channel_stall` template end to end

From `sampling_templates.yaml`:

```yaml
channel_stall:
  required_fields: []
  bin_rule: released_stall_length
  bins:
    - {name: none, predicate: {op: eq, args: [0]}}
    - {name: one_cycle, predicate: {op: eq, args: [1]}}
    - {name: short, predicate: {op: between, args: [2, 4]}}
    - {name: long, predicate: {op: gte, args: [5]}}
```

A Verifier test declares
`OPERATION_SAMPLING_BINDINGS = [{"operation": "gemm", "point": "input_stall",
"template": "channel_stall", "channel": "a_in"}]`. `_compile` requires a
matching `stall_stability` obligation to already exist on channel `a_in` (this
template "reuses the code-owned protocol assertion's completed stall length,"
per the YAML's own description) and copies the four bins verbatim. At runtime,
`orchestration/runtime.py:InterfaceCoverageTracker.sample_snapshot` builds
`completed_by_channel` from the TB's own protocol-assertion return value for
every `stall_stability` obligation, and passes it into
`OperationSamplingMonitor.sample(..., completed_stalls=completed_by_channel)`,
whose `channel_stall` branch looks up `completed_stalls[(valid_signal,
ready_signal)]` — connecting a protocol-domain runtime measurement to an
operation-domain coverage bin.

## Cross-links

- [`../README.md`](../README.md) — the operation domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — shared
  runtime coverage, `InterfaceCoverageTracker`, and
  `ContractCocotbCoverageModel.sample_operation`.
- [`../../protocol/coverage/README.md`](../../protocol/coverage/README.md) — `stall_stability`, the
  obligation `channel_stall` sampling depends on.
- [`../../lifecycle/coverage/README.md`](../../lifecycle/coverage/README.md) — `merge_coverage_plans`
  (defined in this folder's `plan.py`) is what pulls the lifecycle plan in.
- [`../../pool/operation_metadata/README.md`](../../pool/operation_metadata/README.md) —
  `build_architect_operation_metadata`, `supported_code_owned_concepts`,
  canonical classification; this folder's deterministic-synthesis path exists
  entirely to defer to that package for known families.
- [`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md) — documents
  `operation_features.yaml` and
  `feature_plans/operation.py:build_operation_feature_plan` (used only by
  `operation/assertion/generator.py`, not by this folder).
- [`../../README.md`](../../README.md) — package map, three-domain taxonomy,
  and the code-owned vs. LLM-extension boundary this folder enforces.
