# Assertion

> **Historical snapshot.** This document describes the pre-domain-first
> directory layout. Its relative paths and package-ownership wording are not
> current integration guidance. Use [`README.md`](README.md) and the
> `protocol/`, `operation/`, and `lifecycle/` domain READMEs instead.

Code-owned assertion generation for all three verification domains
(`protocol`, `lifecycle`, `operation`) plus the machinery that embeds their
output into every cocotb testbench the Verifier LLM writes. This directory is
one of three independent sibling consumers of the per-domain Resolved Feature
Plans built in `verifier_tool/feature_plans/` — `coverage/` and `stimulus/`
are the other two (see [`../README.md`](../README.md) and
[`../feature_plans/README.md`](../pool/feature_plans/README.md)). Nothing in
`assertion/` calls into `coverage/` or `stimulus/` to decide what to assert;
where it does share code with them (e.g. AXI burst geometry), that is
documented explicitly in the relevant subfolder README as pure-math reuse,
not a domain dependency.

```text
assertion/
├── __init__.py             empty (docstring only) — no package-level re-exports
├── protocol/                plan generator, runtime, and protocol assertion_checkers
├── lifecycle/                plan generator, runtime, and lifecycle assertion_checkers
├── operation/                operation assertion source generator/catalog
└── instrumentation.py       immutable generated TB block and validation
```

`__init__.py` is a docstring-only module (`"""Code-owned operation and
protocol assertions."""`); it re-exports nothing. Every name documented below
and in the three subfolder READMEs is imported either directly from its
owning submodule (internally, by `instrumentation.py`) or from the top-level
`multigent.verifier_tool` facade (externally, by agents/tests) — never from
`multigent.verifier_tool.assertion` itself.

| Subfolder | Backing catalog | README |
|---|---|---|
| `protocol/` | `feature_plans/protocol_features.yaml` + `role_pool/standard_protocols.yaml` (no local YAML) | [`protocol/README.md`](../protocol/README.md) |
| `lifecycle/` | `feature_plans/lifecycle_features.yaml` + `lifecycle_policy_pool/lifecycle_policies.yaml` (no local YAML) | [`lifecycle/README.md`](../lifecycle/README.md) |
| `operation/` | `operation/assertions.yaml` (local, prose guidance) **and** `feature_plans/operation_features.yaml` (machine feature selection) | [`operation/README.md`](../operation/README.md) |

Each subfolder follows the same three-file split described in
[`../README.md`](../README.md): `generator.py` renders the literal Python
lines embedded in the TB, `runtime.py` orchestrates one sampled cycle
(`build_*_assertion_plan` / `check_*_assertions` / `finalize_*_assertions`),
and `assertion_checkers.py` (`axi.py` too, for protocol) holds the actual
executable checking logic, independent of simulation plumbing.

## `instrumentation.py` — the contract-generated block

This is the largest and most load-bearing file in the assertion domain
(~3,500 lines). It does not itself implement any protocol/lifecycle/operation
rule — it **renders and validates** the single immutable block that the three
subfolders' output is assembled into, and it **audits** the hand-written
Verifier source the block gets appended to. Every generated cocotb test file
in this pipeline has the shape:

```text
<Verifier-authored Python: imports, @cocotb.test() functions, helpers>

# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ===   }
...STIMULUS_COVERAGE_INTENTS literal + "# STIMULUS [...]" }  optional; only
...comments normalized from the Verifier's own declaration }  when present
# === END PIPELINE-GENERATED VERIFIER ANNOTATIONS ===      }

# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ===   }
...CONTRACT_* constants, assertion/monitor/campaign   }  always present,
...functions rendered from protocol/lifecycle/        }  always the final
...operation feature plans                            }  block in the file
# === END CONTRACT-GENERATED PROTOCOL MONITOR ===      }
```

Two *different* Verifier-authored literal comment lines are also required
inside the hand-written region itself (checked by substring/AST presence, not
by the marker-pair machinery below): `STIMULUS_SECTION =
"# === STIMULUS AND COVERAGE INTENT ==="` (module constant, **not** exported
by the facade) marks where the Verifier's own `STIMULUS_COVERAGE_INTENTS`
declaration belongs, and `OPERATION_ASSERTION_SECTION =
"# === LLM-GENERATED OPERATION ASSERTIONS ==="` (also not exported) marks
where the Verifier may write asserts for taxonomy-missing operation features.
Do not confuse these two section-header strings with the four marker-pair
constants below: the section headers are just required literal text inside
Verifier-owned source, while the marker pairs delimit regions this file
manages by string search/splice.

### Module-level constants

| Name | Value | Exported by facade |
|---|---|---|
| `BEGIN_MARKER` | `"# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ==="` | yes |
| `END_MARKER` | `"# === END CONTRACT-GENERATED PROTOCOL MONITOR ==="` | yes |
| `AUDIT_BEGIN_MARKER` | `"# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ==="` | yes |
| `AUDIT_END_MARKER` | `"# === END PIPELINE-GENERATED VERIFIER ANNOTATIONS ==="` | yes |
| `STIMULUS_SECTION` | `"# === STIMULUS AND COVERAGE INTENT ==="` | no |
| `OPERATION_ASSERTION_SECTION` | `"# === LLM-GENERATED OPERATION ASSERTIONS ==="` | no |
| `_RESERVED_NAMES` | set of ~35 identifiers (`CONTRACT_*`, `_contract_*`, `_check_contract_*`, `_finalize_contract_*`, ...) | internal only |
| `_PROTECTED_PUBLIC_RUNTIME_NAMES` | the 10 facade names a generated block imports (`capture_contract_snapshot`, `check_protocol_assertions`, ...) | internal only |

`_RESERVED_NAMES` is every top-level identifier the generated block itself
defines or imports; `_assert_reserved_names_are_free` (below) forbids the
Verifier's own source from declaring any of them, so installing the generated
block can never silently shadow or be shadowed by hand-written code.
`_PROTECTED_PUBLIC_RUNTIME_NAMES` is the subset of *facade* names whose
trusted behavior a Verifier must not import directly and wrap/monkeypatch;
`_assert_authority_boundary` (below) enforces this.

### Functions, in the order a TB moves through them

- `strip_contract_generated_block(source: str) -> str` — removes an existing
  `BEGIN_MARKER…END_MARKER` block. Raises `ValueError` if the markers are
  unpaired/reversed, or if anything non-whitespace follows `END_MARKER`
  (the generated block must be the file's final content). Returns the source
  unchanged (rstripped) if no block is present yet. This is the shared
  precondition step for almost every other function in this file.
- `strip_pipeline_generated_annotations(source: str) -> str` — same idea for
  `AUDIT_BEGIN_MARKER…AUDIT_END_MARKER`, but does **not** require the block to
  be final (the contract-generated block comes after it).
- `install_pipeline_generated_annotations(source: str) -> str` — normalizes
  the Verifier's own semantic intent into a deterministic, visible annotation
  block. Strips any existing contract-generated block, calls
  `extract_stimulus_coverage_intents` to read the Verifier's literal
  `STIMULUS_COVERAGE_INTENTS`, strips any existing audit block and any
  `STIMULUS_SECTION`/`# STIMULUS [...]` lines left over in the body, then
  rebuilds and appends a fresh audit block: the literal preamble comment
  (`"This literal and the following comments are emitted by the deterministic verification tool."`), the
  `STIMULUS_SECTION` header, the re-serialized `STIMULUS_COVERAGE_INTENTS`
  literal, and one `# STIMULUS [<label>] targets=(...)` comment inserted
  directly above every matching `_contract_record_checked_stimulus(...,
  label=<label>)` call site found via AST walk. **Called from**
  `multigent/agents/verifier.py:VerifierAgent._with_contract_generated_blocks`,
  guarded by `if "STIMULUS_COVERAGE_INTENTS" in str(item["content"])` — i.e.
  only once the Verifier has actually declared the list — immediately before
  `install_contract_generated_block` runs on the same file.
- `_assert_reserved_names_are_free(source: str) -> None` (internal, but
  load-bearing) — parses top-level `def`/`class`/assignment/import names and
  raises `ValueError` if any collides with `_RESERVED_NAMES`.
- `_assert_authority_boundary(source: str) -> None` (internal, load-bearing)
  — a deliberately bounded static rule, not a full sandboxing proof (its own
  docstring says so): rejects `from multigent.verifier_tool... import
  <protected name>`, `from cocotb_coverage.coverage import coverage_db`,
  assignment/`del` into any `multigent.verifier_tool*`/`verifier_tool*`/
  `sys.modules` attribute or subscript, calls to
  `eval`/`exec`/`compile`/`__import__`/`globals`/`locals`, and
  `setattr`/`delattr` targeting trusted-runtime module paths.
- `render_contract_generated_block(interface_plan, architecture_contract=None, *, include_automatic_campaign=False, randomized_transactions_minimum=0) -> str`
  — the actual renderer; see "Anatomy of a rendered block" below. **Called
  from** `install_contract_generated_block` and `validate_contract_generated_block`
  (both below), and directly by most of `multigent/verifier_tool/tool_regression/integration/test_tb_instrumentation.py`,
  `test_runtime_coverage.py`, `test_lifecycle_automation.py`,
  `test_operation_sampling.py`, `test_standard_axi_protocols.py`, and
  `test_canonical_operation.py` to `exec()` a block in isolation.
- `install_contract_generated_block(source, interface_plan, architecture_contract=None, *, include_automatic_campaign=False, randomized_transactions_minimum=0) -> str`
  — strips any existing block, runs both `_assert_reserved_names_are_free`
  and `_assert_authority_boundary` against the **remaining Verifier source**,
  then appends a freshly rendered block. This is the only function that
  actually mutates a TB file's saved content. **Called from**
  `multigent/agents/verifier.py:VerifierAgent._with_contract_generated_blocks`
  for every prepared test file, with `include_automatic_campaign` true only
  for `index == 0` when the automatic ready/valid campaign is supported.
- `validate_contract_generated_block(source, interface_plan, architecture_contract=None, *, include_automatic_campaign=False, randomized_transactions_minimum=0) -> None`
  — re-derives the expected block from scratch and requires the saved
  `source` to match **exactly** (byte-for-byte after newline normalization);
  raises `ValueError` on any mismatch. This is how the pipeline catches a
  Verifier edit (or corruption) of the supposedly immutable block after the
  fact, independent of whatever `install_contract_generated_block` already
  did. **Called from**
  `multigent/agents/verifier.py:VerifierAgent._validate_prepared_result`,
  once per test file, immediately after checking for duplicate filenames and
  `full`-regression-group membership.
- `extract_stimulus_coverage_intents(source: str) -> list[dict[str, Any]]` —
  reads the Verifier's own literal `STIMULUS_COVERAGE_INTENTS` assignment
  (via `ast.parse` + `_static_value`, which only evaluates inert
  constant/list/tuple/set/dict/`+`/`list()`/`tuple()`/`set()`/`sorted()`
  expressions — anything else raises `ValueError`, so the declaration must be
  literally inspectable, not computed). Requires exactly one such assignment,
  a non-empty list of `{"label": str, "targets": [str, ...]}` entries with no
  duplicate target within an entry and no duplicate label across entries.
  **Called from**
  `multigent/agents/verifier.py:VerifierAgent._apply_review_patch` (to read
  the current intents before applying a Verifier-proposed stimulus-intent
  edit) and from `install_pipeline_generated_annotations` above; also called
  directly in `multigent/verifier_tool/tool_regression/integration/test_verifier_revision_patch.py`.
- `validate_verifier_authored_structure(sources, required_obligations, architecture_contract=None, interface_contract=None, *, randomized_transactions_minimum=0, code_owned_obligations=frozenset()) -> None`
  — the structural audit gate; see below. **Called from**
  `multigent/agents/verifier.py:VerifierAgent._validate_prepared_result`,
  guarded by `if not automatic_campaign_supported` — a DUT profile whose
  automatic ready/valid campaign covers all required obligations skips this
  entirely, since there is then no Verifier-authored test logic to audit.

### `validate_verifier_authored_structure` — what it actually enforces

Raises one aggregated `ValueError` joining every distinct finding it collects
across **all** `sources` (deduplicated, `"; "`-joined) rather than failing on
the first problem. The checks fall into five groups:

1. **Section presence.** Every source must contain the literal
   `STIMULUS_SECTION` and `OPERATION_ASSERTION_SECTION` text, and must parse
   as valid Python.
2. **Stimulus-coverage-intent bookkeeping.** `STIMULUS_COVERAGE_INTENTS`
   targets (unioned across all sources) must equal exactly
   `required_obligations - code_owned_obligations` — no missing ID, no
   unknown one — and every label passed to a literal
   `_contract_record_checked_stimulus(..., label=...)` call must match a
   declared intent label, and vice versa.
3. **Randomized-transaction proof**, only when `architecture_contract` has
   catalog-owned operation features and complete operation I/O: either
   `_static_randomized_record_count` can statically prove at least
   `randomized_transactions_minimum` unconditional, literal
   `for i in range(N):`-nested checked-stimulus calls, or at minimum one
   literal `stimulus_kind='randomized'` call must exist at all — generating
   random vectors while mislabeling them `'directed'` is rejected explicitly.
4. **Operation-assertion-comment bookkeeping.** Every bare `assert` (outside
   `_contract_record_checked_stimulus`) needs an immediately preceding
   `# (LLM-GENERATED )?(OPERATION|PROTOCOL) ASSERTION [<id>]` comment; an
   `OPERATION`-kind comment naming a feature already in
   `known_operation_features(architecture_contract)` (i.e. pipeline-owned) is
   rejected as a forbidden duplicate; the full set of
   `OPERATION`-kind `operation.*` comments actually present must exactly
   equal `required_llm_operation_features` — the architecture's selected
   features that have **no** catalog concept (computed via
   `feature_plans/catalog.py::operation_feature_selections` +
   `coverage/operation/plan.py::canonical_operation_obligation_id`).
5. **Static proof helpers** (each returns a list of error strings, folded
   into the aggregate; each takes the parsed `ast.Module` plus a
   `source_index` for error attribution, and most additionally take
   `interface_contract` since they reason about specific bound signals):

   | Helper | Rejects |
   |---|---|
   | `_static_randomized_record_count` | (see group 3 above) |
   | `_missing_claimed_channel_drives` | a stimulus-intent label claiming a ready/valid channel obligation whose test file never drives that channel's DUT-side control signal (`valid` for an input channel, `ready` for an output channel) |
   | `_unadvanced_checked_stimulus_records` | a second checked-stimulus record in the same straight-line block with no intervening await of DUT time |
   | `_overlapping_unqueued_command_starts` | a second command start while a non-queued (or IDLE-only) command job is still outstanding, per the channel's `semantic_class=command` metadata |
   | `_unrecorded_full_operation_loops` | a looped full DUT operation with no unconditional ledger record inside the loop |
   | `_late_command_pulse_reads` | reading a proven one-cycle command pulse one active edge later than it was asserted |
   | `_reset_abort_operation_records_without_relaunch` | attributing a pre-reset-aborted job to a canonical operation record without an intervening relaunch |
   | `_vacuous_single_bit_signal_assertions` | an `assert <known 1-bit output signal> in {0, 1}`-style tautology that proves nothing |
   | `_unused_passed_helper_parameters` | a keyword argument passed to a uniquely-named local helper whose body never reads that parameter (a no-op feature flag) |
   | `_unchecked_stall_replays` | a `*stall*`-named async helper that drives `valid` through an active edge without reading `ready`, then replays the same value (possible duplicate handshake) |
   | `_nonprogressing_receiver_ready_loops` | a `while` loop awaiting `valid and ready` whose `ready` was set once before the loop and never re-driven inside it (permanent backpressure, not a finite stall) |
   | `_uninitialized_contract_inputs` | a `@cocotb.test()` that never drives one of the contract's declared DUT inputs before its first `await` |
   | `_invalid_cocotb_time_units` | a `Timer(...)`/`cocotb.test(timeout_unit=...)` literal unit outside `{step, fs, ps, ns, us, ms, sec}` |
   | `_unsettled_post_rising_output_reads` | reading a handshake output's `.value` in the same statement/condition that triggers a rising edge, before the NBA/update region has settled |

   Six more are pure AST-shape primitives with no `source_index`/error-list of
   their own, used *by* the checks above rather than being independent
   findings: `_standalone_awaited_trigger`, `_dut_output_value_reads`,
   `_literal_mapping_shape` (proves a dict literal's top-level keys and
   simple value-kinds, used to compare `expected`/`observed` shapes across
   calls), `_name_is_unobserved_literal_alias` and `_name_aliases_name`
   (prove a local name is only an unmodified alias of a literal or of another
   name — catches passing the expected value back in as if it were observed),
   and the shared parsing primitives `_static_value` and
   `_top_level_definitions` (also used by `extract_stimulus_coverage_intents`
   and `install_pipeline_generated_annotations`).

None of these helpers claim full soundness — several docstrings say so
explicitly (e.g. `_missing_claimed_channel_drives`: "this intentionally
checks only a strong, static fact"; `_unused_passed_helper_parameters`: "this
conservative rule catches no-op feature flags without inferring intent").
They are static, conservative, single-purpose proofs, each named after the
one specific bad pattern it can prove exists — not a general TB linter.

### Anatomy of a rendered block

`render_contract_generated_block` builds, per interface/architecture
contract, in this order:

1. `protocol_assertion_metadata(interface_plan)`,
   `known_operation_features(architecture_contract)`,
   `build_architect_operation_metadata(architecture_contract, interface_contract)`
   (imported from **the canonical operation-metadata compiler**,
   `operation_metadata/architect_metadata.py` — not from any `operation/`
   domain folder), `build_protocol_stimulus_plan`, `build_lifecycle_stimulus_plan`,
   and `lifecycle_assertion_metadata(interface_plan, operation_metadata)`.
2. A fixed facade import block (`capture_contract_snapshot`,
   `observe_contract_reset_snapshot`, `sample_contract_snapshot`,
   `normalize_verification_value`, `record_stimulus`, `sample_operation`,
   `check_protocol_assertions`, `finalize_protocol_assertions`,
   `check_lifecycle_assertions`, `finalize_lifecycle_assertions`,
   `drive_protocol_transfers`, `drive_protocol_field_values`,
   `collect_protocol_transfers`, `collect_protocol_field_values`,
   `drive_protocol_reset`, `generate_canonical_stimulus_for_bin`,
   `generate_random_canonical_stimuli`,
   `generate_canonical_discriminating_stimuli`, `contract_coverage`,
   `run_code_owned_verification_campaign`), each aliased to a
   `_contract_*`-prefixed name reserved in `_RESERVED_NAMES`.
3. Literal `CONTRACT_SIGNAL_NAMES` / `CONTRACT_PROTOCOL_ASSERTION_FEATURES` /
   `CONTRACT_OPERATION_ASSERTION_FEATURES` / `CONTRACT_LIFECYCLE_ASSERTION_FEATURES`
   / `CONTRACT_OPERATION_METADATA` / `CONTRACT_PROTOCOL_STIMULUS_PLAN` /
   `CONTRACT_LIFECYCLE_STIMULUS_PLAN` / `CONTRACT_AUTOMATIC_CAMPAIGN_CONFIG`
   assignments (all `repr()`-literal, via the module's `_literal` helper),
   plus fresh empty `_CONTRACT_PROTOCOL_STATE`/`_CONTRACT_LIFECYCLE_STATE`
   dicts.
4. Thin wrapper functions over the canonical-operation-metadata stimulus
   generators (`_contract_generate_operation_stimulus`,
   `_contract_generate_random_operation_stimuli`,
   `_contract_generate_operation_qualification_stimuli`) and over the
   protocol stimulus plan (`_contract_protocol_scenarios`,
   `_contract_protocol_channel`) — these are the functions a Verifier's
   hand-written test body actually calls to get stimulus.
5. `render_operation_assertion_lines`, `render_protocol_assertion_lines`, and
   `render_lifecycle_assertion_lines` output (see the three subfolder
   READMEs), then a combined `_check_contract_assertions`/
   `_finalize_contract_assertions` pair that calls both the protocol and
   lifecycle checkers.
6. `render_protocol_monitor_lines` — the single `_contract_generated_monitor`
   coroutine.
7. If `include_automatic_campaign`: an `@cocotb.test(...)` /
   `@_contract_coverage()`-decorated `_contract_automatic_verification_campaign`
   that calls `run_code_owned_verification_campaign` with the compiled
   protocol/operation/lifecycle plans — the fully automatic path for the
   supported ready/valid integer-GEMM profile, requiring no Verifier-authored
   test body at all.

Every literal is produced by `_literal = repr`, so the block is always valid,
directly `exec`-able Python with no f-string/templating surprises — this is
also exactly why `validate_contract_generated_block` can require byte-exact
equality against a freshly re-rendered copy.

## Who calls this directory, end to end

`multigent/agents/verifier.py:VerifierAgent` is the only agent that touches
this domain directly (Architect and Debugger do not import from
`assertion/` at all — Architect only renders the operation assertion
*catalog* text via `operation/README.md`'s `render_operation_assertion_catalog`,
which lives one level down):

1. `_build_task` embeds `render_operation_assertion_catalog()` in the
   Verifier's own task prompt.
2. `_with_contract_generated_blocks` calls
   `install_pipeline_generated_annotations` (conditionally) then
   `install_contract_generated_block` (always) on every prepared test file.
3. `_apply_review_patch` calls `extract_stimulus_coverage_intents` when
   applying a Verifier-proposed stimulus-intent edit.
4. `_patch_touches_generated_block` (static helper) compares a proposed
   patch's span directly against `BEGIN_MARKER`/`END_MARKER` and
   `AUDIT_BEGIN_MARKER`/`AUDIT_END_MARKER` to reject any local patch that
   would touch code-owned regions.
5. `_validate_prepared_result` calls `validate_contract_generated_block` per
   test file, then (when the automatic campaign does not already cover
   `required_obligations`) `validate_verifier_authored_structure` once across
   all test files.

`multigent/verifier_tool/coverage/runtime.py`'s per-test coverage wrapper
looks up `_finalize_contract_assertions` (falling back to
`_finalize_contract_protocol_assertions`) from the executed test module's
globals after the `@cocotb.test()` body returns — this is how the generated
block's finalizers actually run inside a simulation, without `coverage/`
importing anything from `assertion/` at import time.

Tests exercising this file directly: `multigent/verifier_tool/tool_regression/integration/test_tb_instrumentation.py`
(the primary suite — marker installation/validation, every structural-audit
rejection case), plus `test_runtime_coverage.py`, `test_lifecycle_automation.py`,
`test_operation_sampling.py`, `test_standard_axi_protocols.py`,
`test_canonical_operation.py`, and `test_verifier_revision_patch.py`.

## See also

- [`../README.md`](../README.md) — overall architecture, the three-domain
  taxonomy, and the code-owned/LLM-owned boundary this file enforces.
- [`protocol/README.md`](../protocol/README.md),
  [`lifecycle/README.md`](../lifecycle/README.md),
  [`operation/README.md`](../operation/README.md) — the three domain
  subfolders whose output this file assembles.
- [`../feature_plans/README.md`](../pool/feature_plans/README.md) — the Resolved
  Feature Plan shape and the three domain matchers that produce it.
- [`../operation_metadata/README.md`](../pool/operation_metadata/README.md) — the
  canonical operation-metadata compiler (`build_architect_operation_metadata`,
  `architect_metadata.py`, `canonical.py`); referenced from
  `render_contract_generated_block` but owned entirely outside this
  directory. Do not confuse it with `assertion/operation/`.
