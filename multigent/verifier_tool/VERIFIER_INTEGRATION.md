# Verifier-side: what to require, and what `verifier_tool` provides

This document is about the part of `verifier_tool` a testbench/reference
generator (currently `multigent/agents/verifier.py`) works with. It says what a
generator must be required to do for the tool's checks to pass, what the tool
provides to it, what the tool checks on the result, and where each detail is
documented. It does not describe how any pipeline, stage order, or graph is
organized.

## What to require of a Verifier-side generator

Each item is enforced (or consumed) by a `verifier_tool` function named beside it.

1. **Work from the frozen contract only.** The context must carry
   `user_request`, `verification_policy`, `frozen_architecture` with all four
   artifacts (`architecture_contract`, `interface_contract`, `module_manifest`,
   `acceptance_criteria`), and `provenance` with
   `includes_generated_rtl: false` and `includes_rtl_generator_output: false`
   (`VerifierAgent._validate_context`). `verification_policy` keys the checks
   read: `randomized_transactions_minimum` and
   `regression_wall_timeout_seconds_minimum`. The taxonomy of that contract must
   already be valid (roles, semantics, operation features, extension requests).
2. **Emit flat Python files under the two owned roots:** `reference/<file>.py`
   and `tests/<file>.py` (no absolute paths, no `..`), every test file in the
   `full` regression group, and a `verification_plan` whose `test_modules` are
   exactly the generated test modules.
3. **Leave the code-owned block alone.** The tool installs one generated block as
   the final block of a test file (`install_contract_generated_block`);
   `validate_contract_generated_block` rejects any edit or omission (exact
   comparison). The generator's own code must not define any of the block's
   reserved names, import trusted-runtime names from `multigent.verifier_tool`,
   assign into `multigent.verifier_tool`/`sys.modules`, call reflective builtins
   (`eval`, `exec`, `compile`, `__import__`, `globals`, `locals`), or
   `setattr`/`delattr` tool modules.
4. **Drive and observe through the tool-owned primitives.** Checked stimulus must
   come from the block's drive/collect helpers so accepted transfers, not copied
   literals, are what get compared (`validate_verifier_authored_structure` and
   the instrumentation validators reject copied expected values, unawaited
   drivers, and similar patterns). Use only the public facade
   (`from multigent.verifier_tool import ...`).
5. **Declare coverage exactly.** A module-level `COVERAGE_OBLIGATIONS` literal
   must equal the structured `coverage_obligations` field of the same file, and,
   together with the obligations the automatic campaign already owns, must equal
   the deterministic plan (no missing and no unknown IDs).
6. **For operation features the tool cannot classify** (`llm_extension`), supply
   `operation_coverage` entries and a static `OPERATION_SAMPLING_BINDINGS` literal
   binding each point to a sampling template or custom observer. Points added
   after the declared scope was fixed are rejected (`validate_operation_coverage`,
   `validate_frozen_operation_scope`). See
   [`operation/coverage/README.md`](operation/coverage/README.md).
7. **When the automatic campaign does not cover everything**
   (`automatic_campaign_support(...)["supported"]` is `False`), also provide the
   auditable hand-written structure: exactly one static, non-empty
   `STIMULUS_COVERAGE_INTENTS` literal per test file, runtime coverage
   instrumentation, and required-signal coverage. When it covers everything none
   of that is required because nothing is hand-authored.
8. **Answer contract-local extension requests one-to-one.** Every Architect
   `verification_extensions[]` request needs exactly one `feature_extensions[]`
   bundle; every required observation needs a binding; every named
   implementation symbol must exist at module level in `reference/*.py` or
   `tests/*.py` and be reachable from a generated test entry point, and the
   bundle must preserve the built-in feature IDs the tool resolved for that
   target (`validate_verifier_extension_bundles`). See
   [`extensions/README.md`](extensions/README.md).
9. **Avoid the forbidden constructs** the agent-side phase-safety check enforces
   (imports/calls such as `os`, `subprocess`, `socket`, `open`, `exec`, `eval`);
   this check lives in `verifier.py`, not in `verifier_tool`.

## What the tool provides

| Need | Public functions (`multigent.verifier_tool`) | Details |
|---|---|---|
| Prompt-side catalogs | `render_signal_role_catalog`, `render_interface_semantic_catalog`, `derive_interface_coverage_seed`, `build_interface_coverage_plan`, `render_operation_coverage_catalog`, `render_operation_assertion_catalog`, `render_operation_sampling_catalog` (Verifier-only), `render_extension_authoring_guide`, `render_requested_extension_worklist` | [`pool/role_pool/README.md`](pool/role_pool/README.md), [`operation/coverage/README.md`](operation/coverage/README.md), [`extensions/README.md`](extensions/README.md) |
| Capability report | `build_architect_operation_metadata`, `automatic_campaign_support` (per operation `supported`, `reasons`, `arithmetic_reasons`, `protocol_lifecycle_supported`; top level `supported`, `any_operation_supported`; an operation that could not be compiled also appears per operation with `compile_blocked`, `category`, `owner`, `reason_code`, and in a top-level `blocked_operations`) | [`orchestration/README.md`](orchestration/README.md) |
| Code-owned TB block | `render_contract_generated_block`, `install_contract_generated_block`, `validate_contract_generated_block`, `install_pipeline_generated_annotations`, `extract_stimulus_coverage_intents`, `validate_verifier_authored_structure` | [`orchestration/README.md`](orchestration/README.md), [`orchestration/OLD_stimulus_overview.md`](orchestration/OLD_stimulus_overview.md) (historical layout) |
| Coverage plans and validation | `build_interface_coverage_plan`, `synthesize_code_owned_operation_coverage`, `operation_plan_for_tests`, `merge_coverage_plans`, `effective_operation_coverage`, `validate_operation_coverage`, `validate_frozen_operation_scope`, `canonical_operation_obligation_id`, `canonicalize_operation_obligation_claim`, `code_owned_obligations_for_supported_operations`, `extract_operation_sampling_bindings`, `normalize_operation_sampling_bindings` | [`protocol/coverage/README.md`](protocol/coverage/README.md), [`operation/coverage/README.md`](operation/coverage/README.md) |
| Golden model and stimulus | `evaluate_canonical_operation`, `generate_canonical_stimulus_suite`, `generate_canonical_stimulus_for_bin`, the protocol/lifecycle drivers | [`operation/stimulus/README.md`](operation/stimulus/README.md), [`protocol/stimulus/README.md`](protocol/stimulus/README.md), [`lifecycle/stimulus/README.md`](lifecycle/stimulus/README.md) |
| Deterministic review | `review_verifier_artifacts(context, candidate)` → `{"status": "APPROVED" \| "VERIFIER_REPAIR_REQUIRED", "summary", "findings": [{category, requirement, evidence, recommended_change}]}`; no model call | [`deterministic/README.md`](deterministic/README.md) |
| Local repair primitives | `apply_operation_coverage_metadata_edits`, `finding_scope`, `findings_from_coverage`, `findings_from_validation_error`, `synchronize_test_coverage_metadata`, `coverage_obligation_mapping_diff` | [`deterministic/README.md`](deterministic/README.md) |
| Extension support | `validate_verifier_extension_bundles`, `build_feature_extension_manifest`, `with_verifier_extension_bundle_schema` | [`extensions/README.md`](extensions/README.md) |
| Runtime evidence | `get_coverage_tracker` / the generated block's monitor, `record_stimulus`, `sample_operation`, `rebuild_stimulus_history` | [`orchestration/README.md`](orchestration/README.md) |

## Operations that could not be compiled

An operation `build_architect_operation_metadata` could not compile is not driven,
checked or sampled by any code-owned component, and it is no longer invisible:

- `automatic_campaign_support(...)["supported"]` is `False` for the contract (the
  hand-authored-structure checks in items 7 and 9 below therefore apply), and the
  operation is listed with `compile_blocked: True` and its `category` /`owner`
  (`contract_error` → `architect_contract`; `tool_capability` → `verifier_tool`).
- Its contract-required lifecycle obligations (`operation.<name>.job_lifecycle`,
  `reset_abort_phase`, `post_reset_purity`) stay in the deterministic plan as
  **required** bins and are *not* code-owned, so the obligation comparison expects
  them in `COVERAGE_OBLIGATIONS` like any other non-code-owned obligation.
- They are sampled only by tool-owned monitors for compiled operations, and no public
  API records a hit for them from Verifier-authored code; an unhit bin fails the run.
  The report's `unmet_by_blocker` names the blocker (`"<operation>:<reason_code>"`)
  and so its owner. A Verifier should list the gap in `known_verification_gaps` rather
  than invent coverage, and cannot resolve a `contract_error` (only the Architect
  can) or a `tool_capability` (only tool support can). The prompt built by
  `VerifierAgent._build_task` states this per operation with the reason code, owner,
  resolution hint and the feature IDs affected.
- The operation-domain concepts the Architect declared for it are, as before, not
  code-owned (there is no metadata to classify them), so they are Verifier-supplied
  `operation_coverage` like any other non-code-owned concept.

## What the tool checks on a candidate, in the order it runs them

`VerifierAgent._validate_prepared_result` is where the current checks are
sequenced (it is agent code that calls the functions above). For a
`VERIFICATION_READY` result:

1. `validate_verifier_extension_bundles` (see item 8 above).
2. Reference files (`_validate_python_content`); then
   `build_architect_operation_metadata` and `automatic_campaign_support`. Their
   two flags gate what follows: `supported` selects the conditional checks in
   steps 7 and 9; `any_operation_supported` selects whether the executable
   campaign is embedded in the first test file.
3. Per test file: `validate_contract_generated_block(...,
   include_automatic_campaign=any_operation_supported and first file)`,
   `_validate_python_content`, and the `COVERAGE_OBLIGATIONS` equality check.
4. `operation_plan_for_tests(...)` (raises on invalid
   `OPERATION_SAMPLING_BINDINGS`), then `validate_operation_coverage` and
   `validate_frozen_operation_scope` over `effective_operation_coverage(...)`.
5. Plan consistency: `test_modules`, `randomized_test_count` and `timeout_seconds`
   against policy minimums, and the `full` group covering every module.
6. `build_interface_coverage_plan` + `merge_coverage_plans` give the deterministic
   obligation set; `code_owned_obligations_for_supported_operations` credits what
   the automatic campaign drives; `canonicalize_operation_obligation_claim`
   normalizes claimed operation points into the canonical ID space; the
   missing/unknown comparison follows.
7. (Only when `supported` is `False`.) `validate_verifier_authored_structure`.
8. `_validate_cocotb_phase_safety` (always; agent-side).
9. (Only when `supported` is `False`.) `_validate_runtime_coverage_instrumentation`,
   `_validate_required_signal_coverage`, `_validate_operation_coverage_sampling`.

Any failure surfaces as an `AgentRuntimeError` from that method;
`review_verifier_artifacts` turns the same exception into structured `findings`.

## Runtime requirements of the generated TB

The block's coverage runtime (`get_coverage_tracker`) needs environment variables
supplied by whatever runs the simulation: `NPU_FUNCTIONAL_COVERAGE_CONFIG` (path to
the merged coverage-plan JSON, shaped like `merge_coverage_plans(...)` output) and
`NPU_FUNCTIONAL_COVERAGE_REPORT` (path the report is written to), plus an
optional `NPU_STIMULUS_LEDGER_REPORT`. Without the first two the test raises
`CoverageRuntimeError` before any stimulus. `multigent/tools/cocotb_runner.py`
sets them today. A failing report additionally carries `unmet_by_blocker` when an
unhit required bin belongs to a blocked operation's restored obligation. The shape of
the resulting files is described in
[`orchestration/README.md`](orchestration/README.md) and the 4x4x4 benchmark
README shows a standalone example.

## How the current code calls the tool

- `VerifierAgent._build_task` renders the catalogs above into the prompt;
  `_validate_context` / `_validate_prepared_result` run the checks; the persist
  step (`persist_validated_result`) first, per test file
  (`_with_contract_generated_blocks`), normalizes `OPERATION_SAMPLING_BINDINGS`,
  installs the generated annotations (only when the file declares
  `STIMULUS_COVERAGE_INTENTS`) and the generated block, then synchronizes test
  coverage metadata, runs the validation above, and only then writes `reference/*.py` and
  `tests/*.py` plus `verification_plan.yaml`, `interface_coverage_plan.yaml`,
  `operation_sampling_bindings.yaml`, `operation_coverage_plan.yaml`,
  `feature_extensions.yaml`, `feature_extension_manifest.yaml`,
  `combined_coverage_plan.yaml`, and `verifier_result.json` under `verification/`.
- `multigent/orchestration/verifier_review_node.py` calls
  `review_verifier_artifacts` after rebuilding the context from frozen inputs and
  checking the candidate files against what is saved on disk.
- `multigent/orchestration/verification_tools_node.py` (and `artifacts.py`) call
  `build_interface_coverage_plan`, `merge_coverage_plans`,
  `operation_plan_for_tests`, and `rebuild_stimulus_history` around a simulation.

## Watch-outs

- `deterministic/review.py::_canonical_validator` lazily imports
  `multigent.agents.verifier.VerifierAgent` and calls its `_validate_context` and
  `_validate_prepared_result`, so the tool-side review has no separate copy of
  the checks: changing what those methods verify changes what
  `review_verifier_artifacts` reports, and its imports cannot be moved without
  updating that lazy reference.
- The generated block must stay the final block of a test file
  (`strip_contract_generated_block` raises otherwise).
- `render_operation_sampling_catalog` is intentionally Verifier-only.
- Per-operation known-scope results (`known_scope_campaign_supported`) let a
  contract with one unsupported operation still run the campaign for the others;
  do not collapse the report to its top-level boolean.
- Every `compile_blocked` entry means the contract as frozen cannot be fully verified
  by this tool: `contract_error` needs an Architect correction, `tool_capability` needs
  tool support. Neither is a Verifier-authored fix.
