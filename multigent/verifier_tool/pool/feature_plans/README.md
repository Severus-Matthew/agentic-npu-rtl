# Feature Plans

`feature_plans/` is where the three verification domains — `protocol`,
`lifecycle`, `operation` — turn a frozen Architect contract (plus, for
`operation`, the compiled canonical metadata from
[`../operation_metadata/`](../operation_metadata/README.md)) into a single
**Resolved Feature Plan**: a flat list of "features," each one independently
selecting an assertion checker, a coverage sampler, and a stimulus strategy.
`assertion/`, `coverage/`, and `stimulus/` are then three **independent
sibling consumers for feature selection**: each filters the plan down to its
own branch and never selects behavior by inspecting another branch's output.
Small implementation utilities may still be shared explicitly (for example,
operation coverage asks the operation stimulus generator whether a bin has a
constructible witness, and protocol coverage reuses pure AXI address geometry).
This is the concrete
mechanism behind the top-level README's claim that "the three domains build
independent resolved Feature Plans... they do not share matching rules."

Do not confuse this package (plural, `feature_plans/`, the actual catalogs and
matchers) with the top-level [`../../feature_plan.py`](../../feature_plan.py)
(singular) — that file is only a three-line stable facade re-exporting
`build_lifecycle_feature_plan` / `build_operation_feature_plan` /
`build_protocol_feature_plan` from this package, the same way
`verifier_tool/__init__.py` is a facade over the whole tool.

## Files

| File | Role |
|---|---|
| `protocol_features.yaml` | Declarative catalog: channel/protocol-rule features, their match conditions, and default assertion/coverage/stimulus wiring |
| `lifecycle_features.yaml` | Declarative catalog: reset/command/job/status features and `operation_coverage` lifecycle-vs-operation cross bins |
| `operation_features.yaml` | Declarative code-owned catalog: currently only integer `matrix_multiply` with three baseline concepts and the supported bias, ReLU, and per-tensor affine-quantization extensions; other operations require contract-local extensions |
| `resolved_feature_plan.schema.json` | JSON Schema every domain's *output* must satisfy — the one shape `assertion`/`coverage`/`stimulus` all trust |
| `catalog.py` | Loads + structurally validates the three YAML catalogs above |
| `common.py` | Shared helpers: id-safety, reset lookup, interface/standard-plan unwrapping, one `feature_record()` constructor |
| `compiler.py` | Splits one resolved plan into its `assertion`/`coverage`/`stimulus` branch |
| `protocol.py` | The Protocol Feature Plan matcher |
| `lifecycle.py` | The Lifecycle Feature Plan matcher |
| `operation.py` | The Operation Feature Plan matcher |
| `schema.py` | Loads `resolved_feature_plan.schema.json` and validates a plan against it |

## The "feature" record shape

Every feature in every domain is built by `common.py::feature_record(...)` into
the same shape (this is the contract `resolved_feature_plan.schema.json`
enforces):

```python
{
  "id": "channel.m_axi_ar.stall_stability",      # stable, globally unique within the plan
  "domain": "protocol",                           # "protocol" | "lifecycle" | "operation"
  "kind": "stall_stability",                      # catalog feature name / concept name
  "scope": "channel",                             # what this feature is attached to
  "scope_name": "m_axi_ar",
  "bindings": {...},                              # exact signal/object names, never re-derived downstream
  "assertion": {"checker": "stall_stability"},    # or {"checker": None} = no assertion for this feature
  "coverage": {"sampler": ..., "bins": [...], "obligation_ids": (...)},
  "stimulus": {"strategy": ..., ...},
  "automation": {...},                            # OPTIONAL; absent = plainly code-owned (see below)
}
```

`automation` is set only for a feature the tool cannot own end to end:
`{"status": "contract_error" | "tool_capability_required" |
"verifier_extension_required", "owner", "reason_code", "blocked_by": [...]}`
(vocabulary in [`../diagnostics.py`](../diagnostics.py); `feature_automation(f)` /
`is_code_owned(f)` read it, treating a missing record as `code_owned`, and
`summarize_feature_automation(plans)` rolls the records up to a per-domain
`ready` / `partial` / `blocked` state — there is no plan-level status of its own).
Today only the lifecycle planner emits it, for operations that failed to compile.

`compiler.py::compile_feature_branch(feature_plan, branch)` (branch =
`"assertion"|"coverage"|"stimulus"`) simply walks `features[]`, reads
`feature[branch][selector]` (selector is `"checker"`/`"sampler"`/`"strategy"`
per `_SELECTORS`), and drops any feature whose selector is empty/`None` for
that branch — i.e. a feature can be "coverage-only" or "assertion-only" by
simply leaving the other branch's selector unset in the catalog. It also drops
every feature whose `automation.status` is not `code_owned`: such a feature
stays in the plan (with its obligations) but has no tool-owned checker, sampler
or strategy to compile. It does
**not** re-run any domain matching logic — that already happened when the
resolved plan was built. `compile_assertion_feature_plan` /
`compile_coverage_feature_plan` / `compile_stimulus_feature_plan` are just
`compile_feature_branch` pinned to one branch, and are the exact functions
each of `assertion/`, `coverage/`, and `stimulus/` calls to get "only my
features, in my shape."

## `catalog.py` — loading and validating the three YAML catalogs

- `load_protocol_feature_catalog()` / `load_lifecycle_feature_catalog()` /
  `load_operation_feature_catalog()` — each `lru_cache`d, each parses its YAML,
  applies `feature_defaults` (assertion/coverage/stimulus fields a feature can
  omit and inherit), and validates that every feature's `checker`/`sampler`/
  `strategy` name is one of the small closed sets hardcoded at the top of this
  file (`_PROTOCOL_CHECKERS`, `_LIFECYCLE_STRATEGIES`, etc.) — an unknown
  implementation name is a `ValueError` raised at catalog-load time, not a
  silent no-op at runtime. `load_operation_feature_catalog` additionally hard-
  requires the operation catalog's defaults to be exactly
  `checker=central_golden_equivalence`, `sampler=canonical_classifier`,
  `strategy=canonical_discriminating_stimuli` — i.e. every catalog operation
  concept is checked against one shared central oracle, not a per-feature
  bespoke assertion (see
  [`../../operation/assertion/README.md`](../../operation/assertion/README.md)).
- `operation_optional_concepts(family) -> dict` — merges a family's flat
  `optional_concepts` with the concepts nested inside its `feature_groups`
  (e.g. GEMM's `post_processing` group contains `bias`, `activation`, and
  `quantization`),
  raising on any name collision between baseline concepts, group names, and
  concept names. This is why a `feature_groups` **parent** name (like
  `post_processing`) is never itself a selectable leaf feature.
- `operation_feature_groups(operation) -> dict` — returns `{}` for a
  `coverage_family_source == "novel"` operation (groups only exist for
  catalog-backed families); otherwise looks up the operation's declared
  `coverage_family` in `load_operation_coverage_families()` (note: that loader
  lives in `../../operation/coverage/plan.py`, not here — the *family* catalog
  with baseline/optional concepts and coverage bins is coverage-owned, while
  *this* module only owns the assertion/coverage/stimulus **wiring defaults**
  for the `operation` domain as a whole).
- `operation_feature_selections(operation) -> (baseline, extensions)` —
  filters the Architect's declared `features`/`feature_extensions` lists down
  to concept leaves, silently dropping any name that is actually a group
  marker. This is the deterministic implementation of the top-level README's
  "old frozen `features: [..., post_processing]` is accepted as an inert group
  marker" rule.

## The three matchers

Each matcher is a `build_*_feature_plan(...)` function with a genuinely
different signature and applicability rule — this is intentional; the three
domains are declared independent on purpose so that, e.g., a protocol-only bug
fix can never accidentally change lifecycle matching.

### `protocol.py::build_protocol_feature_plan(interface_plan)`

Takes either a raw `interface_contract` or an already-compiled plan
(`common.py::interface_parts` unwraps either — if a `feature_plan` matching
`domain == "protocol"` is already embedded in the input, it is returned as-is
instead of rebuilt, so a resolved plan is idempotent to re-pass through this
function). Produces four kinds of protocol features:

1. One feature per coverage `obligation` whose `template` matches a catalog
   feature name (skips `stall_stability`, which is handled specially since its
   applicability is per-channel and doesn't come from an obligation template).
2. One `stall_stability` feature per channel whose protocol-profile
   `coverage_tags` include the catalog's `stall_stability.match.coverage_tag`
   and which has both required roles (`valid`+`ready`) bound — never inferred
   from a coverage-template name existing, only from the taxonomy tag.
3. One `valid_low_during_reset` feature per compiled standard protocol group,
   if a reset signal with a resolved active value exists.
4. One `standard_protocol_rule` feature per rule name in each standard
   group's catalog `rules` list (from `role_pool/standard_protocols.yaml`),
   excluding `valid_low_during_reset` (already emitted with richer bindings in
   step 3).

### `lifecycle.py::build_lifecycle_feature_plan(interface_or_plan, operation_metadata)`

The only matcher that needs *both* the interface and the compiled operation
metadata (from
[`../operation_metadata/architect_metadata.py`](../operation_metadata/README.md)),
because lifecycle features are scoped **per operation**, not per channel.
Internally: `_runtime_operations(...)` re-resolves each operation's lifecycle
policy (`resolve_lifecycle_policy`, from `../lifecycle_policy_pool/`), computes
each output's expected logical element count from its dimensions, and — if
an output's `memory_mapping` names a `response_channel` — records a
`memory_write_response` retirement kind instead of a plain `output_transfer`.
The required count is bus words (`ceil(elements / elements_per_word)`). For
AXI4, the retirement entry also carries a `count_mode`, the AW request, W data
(with strobe), and B response signals (`response_signal`): the runtime counts
accepted W beats (or accepted WSTRB bytes when the group's `transfer_size_bins`
is not `full_width`, in which case `expected_count` is multiplied by the bus
width in bytes), tracks outstanding AW requests, and retires at the final
successful B response only after all expected W beats and responses complete.
One B response per burst is **not** one output word; that former assumption
incorrectly rejected a valid 16-beat output burst.
For an operation whose resolved lifecycle carries a `control_plane_sequence`,
each runtime operation additionally gets `control_plane_sequence` (the
declaration) and `control_plane_signals`, flattened by `_control_plane_signals`
from the first AXI4-Lite **subordinate** protocol group's write_address /
write_data / write_response / read_address / read_data channels
(`{kind: {valid, ready, addr|data}}`). The metadata compile already requires that
group for any operation declaring a `control_plane_sequence`
(`control_plane_requires_axi4_lite_subordinate`), so plan building raises
`ValueError` only for hand-built metadata that skipped the compile. The lifecycle assertion runtime consumes
these through
[`../../lifecycle/assertion/README.md`](../../lifecycle/assertion/README.md).
`common.py::resolved_reset` also forwards the reset signal's optional
`reset_settle_cycles` as `settle_cycles` in the plan's `reset` binding.
`_coverage_obligations(...)` additionally emits `operation.<op>.<template>`
lifecycle-crossed-with-operation coverage obligations (e.g. "reset while
loading operand A") for every operation with one resolved command channel and
legal command values, independently of its arithmetic classifier (so a
`control_plane_sequence` operation, which has no command channel, currently
gets none of these obligations). Thus an
`llm_extension` operation still keeps deterministic accepted/active/retired/
reset coverage when its protocol and lifecycle are known. The obligations use
`lifecycle_features.yaml`'s `operation_coverage` section — including a
`dynamic_bins: input_phases` mechanism that expands one templated bin per
input data object. The plan returns `bindings.operations` (the fully resolved
per-operation lifecycle facts) alongside `features` and `coverage_obligations`
— the coverage obligations are a *separate* top-level key from `features`
because they feed `../../lifecycle/coverage/README.md`'s obligation-based
sampling, not the assertion/stimulus feature list.

**Operations that could not be compiled.** `operation_metadata["unrepresentable_operations"]`
entries carry a `shell` (the fragments that did compile, see
[`../operation_metadata/README.md`](../operation_metadata/README.md)). For each one
(deduplicated by name, and never for a name that compiled),
`_blocked_operations` builds a *planning-only* runtime operation from the shell
(`_shell_runtime_operation`) and the planner emits, exactly as for a compiled
operation (same `_operation_feature_kinds`, same extension-field filtering, same
`_coverage_obligations`):

- the operation's `lifecycle.<op>.<kind>` features, each with an `automation`
  record and no checker, sampler or stimulus strategy (`assertion.checker: None`,
  `coverage.sampler: None`, `stimulus.strategy: "not_automated"`), so no compiled
  branch, assertion plan or stimulus plan ever includes them;
- the operation's `operation.<op>.job_lifecycle` / `reset_abort_phase` /
  `post_reset_purity` obligations with **every bin `required_reachable`** (never
  `inapplicable` — a tool limit must not shrink the denominator) and an
  `automation` record on the obligation; the bin `applicability.basis` names the
  blockers. The obligation and feature sets equal what the operation would have
  had if it had compiled (a parity test pins it), so blocking only ever adds
  required bins;
- `bindings.blocked_operations` (only when non-empty): per operation its
  `automation`, `fragments`, `feature_ids`, `obligation_ids`. `bindings.operations`
  never contains a shell, so runtime checkers and drivers cannot see one.

The obligations enter the merged coverage plan like any other and are **not**
code-owned (`code_owned_obligations_for_supported_operations` credits only supported
operations), so the ordinary hit-based gate decides: unhit means FAIL, hit by
anyone means covered. If the lifecycle fragment itself failed (for example
conflicting command tags) there is no command channel to plan obligations from:
the features are still emitted, the obligations are not, and the run cannot pass
silently because the operation is reported unsupported.

### `operation.py::build_operation_feature_plan(architecture_contract)`

The simplest matcher: for every operation whose `coverage_family_source ==
"catalog"` and whose `coverage_family` is a known family (from
`../../operation/coverage/plan.py::load_operation_coverage_families`), emit one
feature per selected baseline+extension concept (via
`operation_feature_selections`), every single one wired to the same three
catalog defaults (`central_golden_equivalence` / `canonical_classifier` /
`canonical_discriminating_stimuli`). A `novel`-sourced operation contributes
**zero built-in features here** because it has no catalog concept to resolve.
Its unsupported behavior must be named explicitly by a contract-local
verification extension and implemented by the matching Verifier bundle (or by
the older coarse `llm_extension` path where that contract form is still used);
the matcher never guesses a replacement catalog feature. See
[`../../operation/assertion/README.md`](../../operation/assertion/README.md).

Contract-local extension requests are intentionally outside the shared resolved
plan schema. For lifecycle, a policy field delegated through
`{extension_request: ...}` suppresses only the built-in features, bins, and
scenarios that depend on that field; unrelated sibling features remain in this
plan. The matching Verifier bundle is validated separately by `extensions/` and
never injected into a global catalog at runtime.

## `schema.py` / `resolved_feature_plan.schema.json` — the shared output contract

`validate_resolved_feature_plan(plan)` is called at the end of all three
`build_*_feature_plan` functions before they return. It JSON-schema-validates
against `resolved_feature_plan.schema.json`, then adds two semantic checks the
schema alone cannot express: every `feature["id"]` is unique within the plan,
and every `feature["domain"]` matches the plan's own top-level `domain`. This
is the actual enforcement mechanism behind "assertion, coverage, and stimulus
are sibling consumers of the resolved feature" — a plan that mixed domains or
had colliding ids could not pass this gate, so `compile_feature_branch` never
has to defend against it.

Every resolved feature also carries normalized `tags`. The shared Tag Pool
validates that each tag exists and permits the plan's domain. Protocol tags are
derived from concrete profiles/roles/semantic classes; lifecycle and operation
tags annotate policy- and family-resolved features. These tags let the Contract
Reviewer resolve reusable sibling helpers for an extension, but do not replace
the domain-specific matching rules described above.

## Who calls this package

- Each domain's `{operation,protocol,lifecycle}/assertion/`, `.../coverage/`,
  `.../stimulus/` calls the matching `build_*_feature_plan` (directly or via a
  domain-specific `plan.py`) and then
  `compile_{assertion,coverage,stimulus}_feature_plan` to get their own
  branch.
- `../role_pool/standard_protocols.py::compile_standard_protocol_plan` is
  called *from* `common.py::interface_parts`, not the other way around —
  feature plans sit one layer above the role pool.
- `operation_metadata/architect_metadata.py`'s compiled metadata is a required
  *input* to `lifecycle.py`'s matcher (lifecycle policy, command channels,
  memory mappings) but feature_plans never calls back into
  `operation_metadata` to build that metadata itself; the caller (ultimately
  `multigent/agents/verifier.py` or a test) is responsible for building
  operation metadata once and passing it to whichever domain needs it.
