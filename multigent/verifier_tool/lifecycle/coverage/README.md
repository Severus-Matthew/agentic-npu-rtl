# Coverage: lifecycle domain

This folder builds and samples the **operation-scoped** lifecycle coverage
obligations: whole-job acceptance/retirement (`job_lifecycle`), reset behavior
at each distinguishable job phase (`reset_abort_phase`), and post-reset clean
recovery (`post_reset_purity`). It is the smallest of the three domain folders
by file count, and deliberately so: five other lifecycle-owned templates
(`reset_behavior`, `busy_behavior`, `completion_behavior`, `error_behavior`,
`command_legality`) are plain per-signal/per-channel templates that get
**instantiated** by `../../protocol/coverage/plan.py`'s generic matching loop instead (see
[`../../protocol/coverage/README.md#lifecycle-templates-instantiated-here`](../../protocol/coverage/README.md#lifecycle-templates-instantiated-here)
and the full table in [`../README.md`](../README.md#obligation-templates-instantiated-vs-sampled)).
This folder's `runtime.py`, however, is the one that *samples* `busy_behavior`
and `command_legality` at simulation time, alongside its own three
operation-scoped templates — so read this file together with
`../../protocol/coverage/plan.py`
to get the complete lifecycle picture.

Backing catalog: `multigent/verifier_tool/pool/feature_plans/lifecycle_features.yaml`,
reached through `feature_plans/catalog.py:load_lifecycle_feature_catalog()`. The
path is re-exported here as `LIFECYCLE_COVERAGE_TEMPLATES_PATH`. The YAML has
two relevant sections:

- `features:` — the five signal/channel-scoped templates listed above. This is
  the section `load_lifecycle_coverage_templates()` (below) exposes as
  `"templates"`, and the only section
  `../../protocol/coverage/plan.py` ever merges in.
- `operation_coverage:` — `job_lifecycle`, `reset_abort_phase`,
  `post_reset_purity`. Consumed only inside
  `feature_plans/lifecycle.py:_coverage_obligations()`, reached through
  `build_lifecycle_feature_plan()` (below), **not** through
  `load_lifecycle_coverage_templates()`. `lifecycle_template_names()` (below)
  therefore does not include these three IDs' template names.

## Files

- `__init__.py` — re-exports `LifecycleCoverageMonitor` (from `runtime.py`) and
  `build_lifecycle_coverage_plan`, `lifecycle_template_names`,
  `load_lifecycle_coverage_templates` (from `plan.py`). All four names are also
  re-exported by the top-level facade `multigent.verifier_tool` directly from
  `multigent.verifier_tool.lifecycle.coverage` — no divergence between this
  package's `__init__.py` and the facade here (unlike `../operation/`).
- `plan.py` — static instantiation of the three operation-scoped obligations.
- `runtime.py` — `LifecycleCoverageMonitor`, the temporal/event sampler.

Despite being exported by the facade, `LifecycleCoverageMonitor`,
`lifecycle_template_names`, and `load_lifecycle_coverage_templates` currently
have **no external caller** outside this package and `orchestration/runtime.py` /
`protocol/coverage/plan.py` (grep the repo — only definitions, re-exports, and
the one internal instantiation site). `build_lifecycle_coverage_plan` is the
only name here consumed elsewhere, and only from
`operation/coverage/plan.py:merge_coverage_plans`.

## `plan.py`

### `load_lifecycle_coverage_templates() -> dict[str, Any]`

`@lru_cache(maxsize=1)`. Loads `lifecycle_features.yaml` via
`load_lifecycle_feature_catalog()` and returns
`{**raw, "templates": raw["features"]}` — i.e. it renames the YAML's `features:`
key to `templates` for uniformity with the protocol/operation catalogs, without
touching `operation_features`/`operation_coverage`. Called by
`lifecycle_template_names()` below and by `../protocol/plan.py:load_interface_coverage_templates()`
(the merge described above).

### `lifecycle_template_names() -> frozenset[str]`

Returns the five signal/channel template names as a frozenset. No current
caller anywhere in the repo besides its own export; kept as a stable, tested
surface for whoever next needs "what lifecycle templates exist" without
loading the whole catalog dict.

### `build_lifecycle_coverage_plan(interface: Mapping[str, Any], operation_metadata: Mapping[str, Any]) -> dict[str, Any]`

The only builder among the three domains that requires **two** contracts,
because job/reset-phase/post-reset-purity obligations are inherently
per-operation: they need `operation_metadata["operations"][*].dimensions`,
`.inputs`, `.outputs`, `.lifecycle.job_accept_channels`, and
`.lifecycle.status_bindings` (the canonical, code-owned operation metadata built
by `operation_metadata/architect_metadata.py:build_architect_operation_metadata`,
not the raw Architect contract). Internally:

```python
feature_plan = build_lifecycle_feature_plan(interface, operation_metadata)  # feature_plans/lifecycle.py
return {
    "schema_version": 2,
    "source": "verifier_tool lifecycle taxonomy",
    "feature_plan": feature_plan,
    "compiled_coverage": compile_coverage_feature_plan(feature_plan),
    "obligations": list(feature_plan["coverage_obligations"]),
}
```

Unlike `../../protocol/coverage/plan.py`, where the `obligations` list is built directly and
`feature_plan`/`compiled_coverage` are a secondary re-packaging, here the
**Feature Plan builder itself** (`feature_plans/lifecycle.py:build_lifecycle_feature_plan`
→ `_coverage_obligations`) is the only place these three obligations are ever
assembled — there is no parallel direct-instantiation path. `_coverage_obligations`
requires either exactly one command channel with machine-readable `legal_values`
or a resolved `control_plane_sequence`; an operation with neither executable
start source is skipped. It does **not** look at `classifier_profile`
(source comment: lifecycle coverage depends on observable command/job/status
behavior, not on whether the mathematics has a golden model), so an
`llm_extension` operation with a resolved start path still gets these three
obligations. An operation started through a `control_plane_sequence` (no
command channel, see
[`../../pool/lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md))
therefore receives the same `job_lifecycle`, `reset_abort_phase`, and
`post_reset_purity` obligations when the sequence is fully resolved.
`reset_abort_phase` additionally gets dynamic bins: one `input_<data_object>`
bin per declared input binding, inserted between its fixed `idle` and `output`
bins (`dynamic_bins: input_phases` in YAML, expanded in
`feature_plans/lifecycle.py:_coverage_obligations`).

If one lifecycle policy field is delegated to a contract-local extension,
`_coverage_obligations` removes only bins whose meaning depends on that field.
For example, an error-style extension does not remove the known accepted/active/
retired/aborted job-lifecycle bins, while a reset-behavior extension removes the
abort and post-reset-purity obligations it owns. The Verifier bundle supplies the
missing extension coverage separately.

Called only by `operation/coverage/plan.py:merge_coverage_plans(interface_plan,
operation_plan)`, which supplies `interface_plan["interface_contract"]` and
`operation_plan["operation_metadata"]`. Not called directly by any agent or
orchestration file — they all reach it transitively through `merge_coverage_plans`.
Exercised directly in tests by `multigent/verifier_tool/tool_regression/integration/test_lifecycle_automation.py`.

## `runtime.py`

### `LifecycleCoverageMonitor`

Constructed once per test by `InterfaceCoverageTracker.__init__` as
`self.lifecycle_coverage_monitor`. Filters `plan["obligations"]` to templates
`{busy_behavior, command_legality, job_lifecycle, reset_abort_phase,
post_reset_purity}`, and separately indexes `plan["operation_metadata"]["operations"]`
by `operation_name` for the three operation-scoped templates.

- **`reset()`** — clears `self.state`. Called from `InterfaceCoverageTracker.begin_test`
  and `end_test`.
- **`sample(self, snapshot, *, reset_active: bool) -> list[tuple[str, str]]`** —
  called once per sample (both in-reset and out-of-reset) from
  `InterfaceCoverageTracker.sample_snapshot` and `observe_reset_snapshot`. When
  `reset_active`, it walks every tracked operation's in-flight state: hits
  `reset_abort_phase` with the phase computed by `_phase()` (or `idle` if
  nothing was active), hits `job_lifecycle`'s `aborted` bin if a job was active,
  arms `awaiting_clean_recovery` on that operation's state (clearing
  `ghost_output`/`ghost_completion`/`recovery_job_started`), and clears
  `active`/`counts`. When not in reset, it: (1) samples every `busy_behavior`
  obligation directly off its bound signal, hitting `active`/`idle`, plus
  `retired` on a high→low edge; (2) for every tracked operation, checks each
  declared `job_accept_channels` entry for a fired transfer, classifies the
  payload against `legal_values` to hit the matching `command_legality`
  obligation's `legal`/`illegal` bin, and on a legal command hits
  `job_lifecycle`'s `accepted`+`active` bins and marks the operation `active`.
  For a register-started operation, the same transition comes from the
  resolved control-plane sequence tracker's observed `JOB_START` event;
  (3) counts accepted input/output transfers per declared channel (first
  channel with remaining expected transfers wins ties, via `_expected_transfers`);
  a post-recovery output with the operation not `active` sets `ghost_output`;
  (4) on any declared completion signal rising, or an observed control-plane
  `JOB_COMPLETE` event, hits `job_lifecycle`'s `retired` bin and marks the
  operation inactive; a completion seen before a recovery job actually started
  sets `ghost_completion`.
- **`record_checked_job(self, operation_name: str) -> list[tuple[str, str]]`** —
  called only from `orchestration/runtime.py:InterfaceCoverageTracker.record_stimulus`,
  once per checked job, immediately after that job's independent oracle check
  passes. If the operation's state has `awaiting_clean_recovery` set (i.e. this
  is the first legal job after a reset aborted a prior in-flight job), it hits
  `post_reset_purity`'s `clean_recovery_job` bin, plus `no_ghost_output` /
  `no_ghost_completion` unless the corresponding ghost flag was set during the
  intervening reset-then-recovery window. Clears `awaiting_clean_recovery`.

Private helpers worth knowing about because they encode real domain rules, not
just plumbing: `_expected_elements`/`_expected_transfers` compute how many
physical transfers one logical input/output binding needs from
`binding["dimensions"]` and an optional `memory_mapping.elements_per_word`;
`_obligation(template, operation_name)` returns an obligation id only when the
match is unique (returns `None` — silently skipping that hit — for an
ambiguous or absent match, so a lifecycle plan missing an expected obligation
fails by *not incrementing coverage*, not by raising); `_phase(operation,
current)` decides `input_<object>` vs `output` vs `compute` from the same
transfer counts used for coverage.

## Example: `job_lifecycle` and `post_reset_purity`

From `lifecycle_features.yaml`'s `operation_coverage:` section:

```yaml
job_lifecycle:
  bins:
    - {name: accepted, intent: A legal command starts a job.}
    - {name: active, intent: Accepted work reaches an active busy state.}
    - {name: retired, intent: A legal job retires with its declared completion.}
    - {name: aborted, intent: Reset gives in-flight work an explicit abort disposition.}
post_reset_purity:
  bins:
    - {name: no_ghost_completion, intent: Aborted work emits no completion.}
    - {name: no_ghost_output, intent: Aborted work emits no accepted result.}
    - {name: clean_recovery_job, intent: The next legal job matches only post-reset accepted inputs.}
```

For an operation named `gemm`, `_coverage_obligations` (in
`feature_plans/lifecycle.py`) emits obligation id `operation.gemm.job_lifecycle`
and `operation.gemm.post_reset_purity`. A full "abort-then-recover" scenario
that exercises every bin: accept a legal command (`job_lifecycle.accepted` +
`.active`), assert reset mid-job (`job_lifecycle.aborted`,
`reset_abort_phase.<phase>`, arms recovery tracking), then submit and
successfully check one more legal job with no ghost output/completion in
between (`post_reset_purity.clean_recovery_job` + `.no_ghost_output` +
`.no_ghost_completion`, plus that second job's own `job_lifecycle.accepted`
through `.retired`).

## Cross-links

- [`../README.md`](../README.md) — the lifecycle domain as a whole.
- [`../../orchestration/README.md`](../../orchestration/README.md) — shared
  runtime data flow and `InterfaceCoverageTracker`.
- [`../../protocol/coverage/README.md`](../../protocol/coverage/README.md) — instantiates
  `busy_behavior`/`command_legality`/`reset_behavior`/`completion_behavior`/`error_behavior`.
- [`../../operation/coverage/README.md`](../../operation/coverage/README.md) — `merge_coverage_plans`
  is the sole caller of `build_lifecycle_coverage_plan`.
- [`../../README.md`](../../README.md) — package map and three-domain taxonomy.
- [`../../pool/lifecycle_policy_pool/README.md`](../../pool/lifecycle_policy_pool/README.md) —
  the Architect-selectable policies (`job_acceptance`, `completion_style`,
  `error_style`, etc.) that determine which of these obligations are even
  reachable; this folder assumes the policy has already been resolved into
  `operation_metadata["operations"][*].lifecycle`.
- [`../../pool/operation_metadata/README.md`](../../pool/operation_metadata/README.md) —
  source of the `operation_metadata` argument this file requires.
- [`../../pool/feature_plans/README.md`](../../pool/feature_plans/README.md) — documents
  `lifecycle_features.yaml` and `feature_plans/lifecycle.py`, including
  `_runtime_operations`, `_coverage_obligations`, and
  `build_lifecycle_feature_plan`.
