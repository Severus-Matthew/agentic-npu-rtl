"""Generate the code-owned contract instrumentation embedded in cocotb TBs.

The generated block is deliberately visible in every saved testbench. It owns
reusable protocol/lifecycle assertions, catalog-operation result assertions, the
one clock observer, and (for an executable known profile) a complete automatic
campaign. Only genuinely unknown operation semantics remain Verifier-authored.
"""

from __future__ import annotations

import ast
import copy
from difflib import get_close_matches
import re
from typing import Any, Mapping, Sequence

from multigent.verifier_tool.operation.assertion import (
    known_operation_features,
    render_operation_assertion_lines,
)
from multigent.verifier_tool.operation.coverage.plan import (
    canonical_operation_obligation_id,
)
from multigent.verifier_tool.protocol.assertion import (
    protocol_assertion_metadata,
    render_protocol_assertion_lines,
    render_protocol_monitor_lines,
)
from multigent.verifier_tool.lifecycle.assertion import (
    lifecycle_assertion_metadata,
    render_lifecycle_assertion_lines,
)
from multigent.verifier_tool.pool.operation_metadata import build_architect_operation_metadata
from multigent.verifier_tool.pool.feature_plans.catalog import operation_feature_selections
from multigent.verifier_tool.protocol.stimulus import build_protocol_stimulus_plan
from multigent.verifier_tool.lifecycle.stimulus import build_lifecycle_stimulus_plan


BEGIN_MARKER = "# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ==="
END_MARKER = "# === END CONTRACT-GENERATED PROTOCOL MONITOR ==="
AUDIT_BEGIN_MARKER = "# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ==="
AUDIT_END_MARKER = "# === END PIPELINE-GENERATED VERIFIER ANNOTATIONS ==="
STIMULUS_SECTION = "# === STIMULUS AND COVERAGE INTENT ==="
OPERATION_ASSERTION_SECTION = "# === LLM-GENERATED OPERATION ASSERTIONS ==="
_RESERVED_NAMES = {
    "CONTRACT_SIGNAL_NAMES",
    "CONTRACT_PROTOCOL_ASSERTION_FEATURES",
    "CONTRACT_PROTOCOL_ASSERTION_PLAN",
    "CONTRACT_OPERATION_ASSERTION_FEATURES",
    "CONTRACT_OPERATION_METADATA",
    "CONTRACT_PROTOCOL_STIMULUS_PLAN",
    "CONTRACT_LIFECYCLE_STIMULUS_PLAN",
    "CONTRACT_LIFECYCLE_ASSERTION_FEATURES",
    "CONTRACT_LIFECYCLE_ASSERTION_PLAN",
    "_CONTRACT_PROTOCOL_STATE",
    "_CONTRACT_LIFECYCLE_STATE",
    "_contract_generate_operation_stimulus",
    "_contract_generate_random_operation_stimuli",
    "_contract_generate_operation_qualification_stimuli",
    "_contract_generate_canonical_stimulus_for_bin",
    "_contract_generate_random_canonical_stimuli",
    "_contract_protocol_scenarios",
    "_contract_protocol_channel",
    "_contract_standard_protocol_group",
    "_contract_protocol_event_transaction",
    "_contract_drive_protocol_field_values",
    "_contract_drive_protocol_transfers",
    "_contract_collect_protocol_field_values",
    "_contract_collect_protocol_transfers",
    "_contract_drive_protocol_reset",
    "_contract_record_checked_stimulus",
    "_contract_runtime_record_checked_stimulus",
    "_contract_runtime_record_stimulus",
    "_contract_runtime_sample_operation",
    "_contract_record_extension_coverage",
    "_check_contract_protocol_assertions",
    "_check_contract_lifecycle_assertions",
    "_check_contract_assertions",
    "_finalize_contract_protocol_assertions",
    "_finalize_contract_lifecycle_assertions",
    "_finalize_contract_assertions",
    "_contract_generated_monitor",
    "_contract_cocotb",
    "_contract_coverage",
    "_contract_run_code_owned_verification_campaign",
    "_contract_automatic_verification_campaign",
    "CONTRACT_AUTOMATIC_CAMPAIGN_CONFIG",
}
_PROTECTED_PUBLIC_RUNTIME_NAMES = {
    "capture_contract_snapshot",
    "check_protocol_assertions",
    "check_lifecycle_assertions",
    "finalize_protocol_assertions",
    "finalize_lifecycle_assertions",
    "get_coverage_tracker",
    "normalize_verification_value",
    "observe_contract_reset_snapshot",
    "record_stimulus",
    "sample_contract_snapshot",
    "sample_extension_coverage",
}


def _literal(value: object) -> str:
    return repr(value)


def _gemm_formula_comment_lines(operation: Mapping[str, Any]) -> list[str]:
    """Describe exactly the product -> reduction -> post-op DAG ->
    result-conversion pipeline `integer_matrix_multiply_events` computes for
    `operation`, one numbered stage per line, so a human can check the
    formula against intent without reading the raw arithmetic metadata dict.
    """

    arithmetic = operation.get("arithmetic", {})
    reduction_conversion = str(arithmetic.get("reduction_conversion", "exact"))
    reduction_note = (
        "wrapped to the accumulator width after every partial add"
        if reduction_conversion == "wrap_twos_complement_after_each_add"
        else "exact, no wrap"
    )
    lines = [f"#   1. reduction: Y = sum_k(A[m,k] * B[k,n])  [{reduction_note}]"]
    post_operations = arithmetic.get("post_operations", {})
    resolved_stage_order = arithmetic.get("resolved_stage_order", [])
    step = 2
    for stage_name in resolved_stage_order:
        stage = post_operations.get(stage_name, {})
        kind = stage.get("kind")
        if kind == "bias_add":
            bias_conversion = str(arithmetic.get("bias_conversion", "exact"))
            note = (
                "wrapped to the accumulator width after the add"
                if bias_conversion == "wrap_twos_complement_after_add"
                else "exact, no wrap"
            )
            lines.append(f"#   {step}. bias_add ({stage_name!r}): Y = Y + bias[n]  [{note}]")
        elif kind == "wrap":
            lines.append(f"#   {step}. wrap ({stage_name!r}): Y = wrap_to_accumulator_width(Y)")
        elif kind == "relu":
            lines.append(f"#   {step}. relu ({stage_name!r}): Y = max(0, Y)")
        else:
            lines.append(f"#   {step}. {kind} ({stage_name!r})")
        step += 1
    result_conversion = arithmetic.get("result_data_type", {}).get("conversion", "exact")
    if result_conversion == "wrap_twos_complement":
        lines.append(f"#   {step}. result_conversion: Y = wrap_to_result_dtype_width(Y)")
    else:
        lines.append(f"#   {step}. result_conversion: Y = Y  [exact, no wrap]")
    return lines


def _numeric_stage_events_comment_lines(case: Mapping[str, Any]) -> list[str]:
    """Render one case's `numeric_stage_events` (the classifier's own trace
    of the shared golden-model walk) as one comment line per output cell, so
    a human can confirm the golden model produced the value the DUT check
    will actually compare against -- product terms, the reduction result,
    the value relu saw, and the final golden output, in one place.
    """

    evidence = case.get("evidence", {})
    events = evidence.get("numeric_stage_events", [])
    expected = case.get("expected", {})
    result_values = next(iter(expected.values()), []) if expected else []
    lines = []
    for index, event in enumerate(events):
        row, column = event.get("coordinate", [0, 0])
        golden = result_values[index] if index < len(result_values) else None
        lines.append(
            f"#     Y[{row},{column}]: products={event.get('product_terms', [])} "
            f"-> reduction={event.get('reduction_final')} "
            f"-> pre_activation={event.get('pre_activation')} -> golden={golden}"
        )
    return lines


def render_operation_golden_model_comment_lines(
    operation_metadata: Mapping[str, Any]
) -> list[str]:
    """Human-readable golden-model formula and worked-trace comments for
    every integer_matrix_multiply operation, rendered here once at
    TB-generation time from the same arithmetic metadata and the same
    `integer_matrix_multiply_events` walk that `evaluate_canonical_operation`
    (golden values) and `classify_operation_job` (classification evidence)
    already share -- so this comment cannot silently drift from what the DUT
    check actually computes, and a human can audit the formula and one
    concrete worked example without running the simulator.
    """

    from multigent.verifier_tool.operation.stimulus import (
        CanonicalStimulusGenerationError,
        generate_canonical_discriminating_stimuli,
    )

    lines: list[str] = []
    for operation in operation_metadata.get("operations", []):
        if operation.get("arithmetic", {}).get("classifier_profile") != "integer_matrix_multiply":
            continue
        name = str(operation.get("operation_name", ""))
        lines.append(
            f"# {name}: golden model formula "
            "(pool/operation_metadata/canonical.py::integer_matrix_multiply_events)"
        )
        lines.extend(_gemm_formula_comment_lines(operation))
        try:
            cases = generate_canonical_discriminating_stimuli(
                {"operations": [operation]}, operation_name=name
            )
        except CanonicalStimulusGenerationError:
            # Metadata for this operation is not fully resolved yet (e.g. an
            # in-progress architect contract) -- the formula above is still
            # accurate for what is declared so far, there just isn't a legal
            # worked example to compute yet.
            cases = []
        if cases:
            example = cases[0]
            lines.append(
                f"#   worked example ({example.get('label', '')}): "
                f"{example.get('qualification_purpose', '')}"
            )
            lines.extend(_numeric_stage_events_comment_lines(example))
    return lines


def strip_contract_generated_block(source: str) -> str:
    """Remove an earlier code-owned block before installing the current one."""

    start = source.find(BEGIN_MARKER)
    end = source.find(END_MARKER)
    if start < 0 and end < 0:
        return source.rstrip() + "\n"
    if start < 0 or end < start:
        raise ValueError("Malformed contract-generated protocol monitor markers")
    end += len(END_MARKER)
    if source[end:].strip():
        raise ValueError("Contract-generated protocol monitor must be the final TB block")
    return source[:start].rstrip() + "\n"


def strip_pipeline_generated_annotations(source: str) -> str:
    """Remove the code-owned audit block before rebuilding it."""

    start = source.find(AUDIT_BEGIN_MARKER)
    end = source.find(AUDIT_END_MARKER)
    if start < 0 and end < 0:
        return source.rstrip() + "\n"
    if start < 0 or end < start:
        raise ValueError("Malformed pipeline-generated verifier annotation markers")
    end += len(AUDIT_END_MARKER)
    return (source[:start] + source[end:]).rstrip() + "\n"


def verifier_owned_source_for_repair(source: str) -> str:
    """Remove pipeline syntax while preserving Verifier-owned intent semantics.

    ``install_pipeline_generated_annotations`` canonicalizes the Verifier's
    label-to-target mapping into the code-owned audit block. A later local repair
    must not lose that mapping when it removes the audit wrapper before sending
    source back to the Verifier. Restore one ordinary literal declaration so the
    next repair round receives the exact prior semantic choice.
    """

    if AUDIT_BEGIN_MARKER not in source and AUDIT_END_MARKER not in source:
        return source.rstrip() + "\n"
    intents = extract_stimulus_coverage_intents(source)
    stripped = strip_pipeline_generated_annotations(source)
    return (
        stripped.rstrip()
        + "\n\n"
        + STIMULUS_SECTION
        + "\nSTIMULUS_COVERAGE_INTENTS = "
        + _literal(intents)
        + "\n"
    )


def _static_value(
    node: ast.AST, definitions: Mapping[str, ast.AST], resolving: set[str] | None = None
) -> Any:
    """Evaluate only inert container expressions used by verifier audit metadata."""

    resolving = set() if resolving is None else set(resolving)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_static_value(item, definitions, resolving) for item in node.elts]
        return values if isinstance(node, ast.List) else tuple(values) if isinstance(node, ast.Tuple) else set(values)
    if isinstance(node, ast.Dict):
        return {
            _static_value(key, definitions, resolving): _static_value(value, definitions, resolving)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.Name) and node.id in definitions and node.id not in resolving:
        return _static_value(definitions[node.id], definitions, resolving | {node.id})
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Add)
    ):
        return _static_value(node.left, definitions, resolving) + _static_value(
            node.right, definitions, resolving
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"list", "tuple", "set", "sorted"}
        and len(node.args) == 1
        and not node.keywords
    ):
        value = _static_value(node.args[0], definitions, resolving)
        return {
            "list": list,
            "tuple": tuple,
            "set": set,
            "sorted": sorted,
        }[node.func.id](value)
    raise ValueError("metadata expression is not statically resolvable")


def _top_level_definitions(tree: ast.Module) -> dict[str, ast.AST]:
    definitions: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    definitions[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            definitions[node.target.id] = node.value
    return definitions


def install_pipeline_generated_annotations(source: str) -> str:
    """Normalize LLM semantic intent into deterministic visible TB annotations."""

    source = strip_contract_generated_block(source)
    intents = extract_stimulus_coverage_intents(source)
    source = strip_pipeline_generated_annotations(source)
    tree = ast.parse(source)
    declarations = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "STIMULUS_COVERAGE_INTENTS" for target in node.targets)
        )
        or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "STIMULUS_COVERAGE_INTENTS"
        )
    ]
    lines = source.splitlines()
    for node in reversed(declarations):
        del lines[node.lineno - 1 : node.end_lineno]
    cleaned = [
        line
        for line in lines
        if line.strip() != STIMULUS_SECTION
        and not re.fullmatch(r"\s*# STIMULUS \[[^\]]+\](?:\s+targets=.*)?", line)
    ]
    cleaned_source = "\n".join(cleaned).rstrip() + "\n"
    cleaned_tree = ast.parse(cleaned_source)
    intents_by_label = {item["label"]: item["targets"] for item in intents}
    insertions: list[tuple[int, str]] = []
    cleaned_lines = cleaned_source.splitlines()
    for node in ast.walk(cleaned_tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_contract_record_checked_stimulus"
        ):
            continue
        label_nodes = [item.value for item in node.keywords if item.arg == "label"]
        if (
            len(label_nodes) == 1
            and isinstance(label_nodes[0], ast.Constant)
            and isinstance(label_nodes[0].value, str)
            and label_nodes[0].value in intents_by_label
        ):
            label = label_nodes[0].value
            indentation = cleaned_lines[node.lineno - 1][
                : len(cleaned_lines[node.lineno - 1]) - len(cleaned_lines[node.lineno - 1].lstrip())
            ]
            insertions.append(
                (
                    node.lineno - 1,
                    f"{indentation}# STIMULUS [{label}] targets={_literal(tuple(intents_by_label[label]))}",
                )
            )
    for line_index, comment in sorted(insertions, reverse=True):
        cleaned_lines.insert(line_index, comment)
    audit = [
        AUDIT_BEGIN_MARKER,
        "# This literal and the following comments are emitted by the deterministic verification tool.",
        "# The Verifier chooses semantic label-to-target mappings; code owns syntax.",
        STIMULUS_SECTION,
        f"STIMULUS_COVERAGE_INTENTS = {_literal(intents)}",
    ]
    audit.append(AUDIT_END_MARKER)
    return "\n".join(cleaned_lines).rstrip() + "\n\n" + "\n".join(audit) + "\n"


def _assert_reserved_names_are_free(source: str) -> None:
    tree = ast.parse(source)
    declared: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            declared.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    declared.add(target.id)
        elif isinstance(node, ast.ImportFrom):
            declared.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            declared.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
    conflict = sorted(declared & _RESERVED_NAMES)
    if conflict:
        raise ValueError(
            "Verifier source may not define code-owned protocol monitor names: "
            + ", ".join(conflict)
        )


def _assert_authority_boundary(source: str) -> None:
    """Reject supported-subset attempts to mutate or bypass trusted runtime state.

    This is deliberately a bounded static rule, not a claim that arbitrary Python
    can be proven honest.  Generated TBs that need dynamic import/reflection are
    outside the supported execution boundary.
    """

    tree = ast.parse(source)
    errors: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if module.startswith("multigent.verifier_tool"):
                forbidden = sorted(
                    alias.name
                    for alias in node.names
                    if alias.name in _PROTECTED_PUBLIC_RUNTIME_NAMES
                )
                if forbidden:
                    errors.append(
                        f"line {node.lineno}: direct trusted-runtime imports {forbidden} are forbidden"
                    )
            if module == "cocotb_coverage.coverage" and any(
                alias.name == "coverage_db" for alias in node.names
            ):
                errors.append(
                    f"line {node.lineno}: direct coverage_db access is forbidden"
                )
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
                if hasattr(node, "target")
                else node.targets
            )
            for target in targets:
                if isinstance(target, (ast.Attribute, ast.Subscript)):
                    text = ast.unparse(target)
                    if text.startswith(("multigent.verifier_tool", "verifier_tool", "sys.modules")):
                        errors.append(
                            f"line {node.lineno}: mutation of trusted module state is forbidden"
                        )
        if isinstance(node, ast.Call):
            called = ast.unparse(node.func)
            if called in {"eval", "exec", "compile", "__import__", "globals", "locals"}:
                errors.append(
                    f"line {node.lineno}: reflective call {called} is outside the supported TB subset"
                )
            if called in {"setattr", "delattr"} and node.args:
                target = ast.unparse(node.args[0])
                if target.startswith(("multigent.verifier_tool", "verifier_tool")):
                    errors.append(
                        f"line {node.lineno}: trusted runtime monkey-patching is forbidden"
                    )
    if errors:
        raise ValueError(
            "Generated TB violates the trusted runtime authority boundary: "
            + "; ".join(errors)
        )


def _protocol_clock_domains(
    interface_plan: Mapping[str, Any],
    assertion_plan: Mapping[str, Any],
    *,
    primary_clock: str,
) -> dict[str, dict[str, Any]]:
    """Partition custom-protocol assertions and bins by declared clock.

    Standard protocols without an explicit semantic clock remain on the primary
    interface clock. Contract-defined profiles carry their own clock binding and
    must never be sampled through another domain merely because all signals are
    visible from the same simulator handle.
    """

    semantics = (
        assertion_plan.get("feature_plan", {})
        .get("bindings", {})
        .get("protocol_semantics", {})
    )
    profiles = [
        item
        for item in semantics.get("profiles", [])
        if isinstance(item, Mapping)
        and isinstance(item.get("clock"), Mapping)
        and str(item.get("clock", {}).get("signal", ""))
    ]
    clocks = {str(item["clock"]["signal"]) for item in profiles}
    if primary_clock:
        clocks.add(primary_clock)
    if len(clocks) <= 1:
        return {}

    prefixes_by_clock: dict[str, tuple[str, ...]] = {}
    all_prefixes: list[str] = []
    for clock_name in sorted(clocks):
        prefixes = tuple(
            f"protocol_transaction.{str(item['name'])}."
            for item in profiles
            if str(item["clock"]["signal"]) == clock_name
        )
        prefixes_by_clock[clock_name] = prefixes
        all_prefixes.extend(prefixes)

    def belongs(identity: str, prefixes: tuple[str, ...]) -> bool:
        return any(identity.startswith(prefix) for prefix in prefixes)

    feature_ids = tuple(map(str, assertion_plan.get("features", ())))
    obligation_ids = tuple(
        str(item.get("id", ""))
        for item in interface_plan.get("obligations", [])
        if isinstance(item, Mapping) and item.get("id")
    )
    result: dict[str, dict[str, Any]] = {}
    for clock_name in sorted(clocks):
        prefixes = prefixes_by_clock[clock_name]
        primary = clock_name == primary_clock
        selected_features = {
            identity
            for identity in feature_ids
            if belongs(identity, prefixes)
            or (primary and not belongs(identity, tuple(all_prefixes)))
        }
        selected_obligations = tuple(
            identity
            for identity in obligation_ids
            if belongs(identity, prefixes)
            or (primary and not belongs(identity, tuple(all_prefixes)))
        )
        plan = copy.deepcopy(dict(assertion_plan))
        compiled = dict(plan.get("compiled_assertions", {}))
        compiled["entries"] = [
            item
            for item in compiled.get("entries", [])
            if str(item.get("id", "")) in selected_features
        ]
        plan["compiled_assertions"] = compiled
        for field in ("stalls", "transaction_accounting"):
            plan[field] = [
                item
                for item in plan.get(field, [])
                if str(item.get("id", "")) in selected_features
            ]
        plan["event_correlations"] = [
            item
            for item in plan.get("event_correlations", [])
            if str(item.get("feature_id", "")) in selected_features
        ]
        if not primary:
            plan["standard_groups"] = []
        plan["features"] = tuple(
            identity for identity in feature_ids if identity in selected_features
        )
        plan["valid_reset_features"] = {
            signal: identity
            for signal, identity in plan.get("valid_reset_features", {}).items()
            if identity in selected_features
        }
        plan["valid_reset_settle_cycles"] = {
            signal: value
            for signal, value in plan.get("valid_reset_settle_cycles", {}).items()
            if signal in plan["valid_reset_features"]
        }
        plan["valid_signals"] = tuple(sorted(plan["valid_reset_features"]))
        result[clock_name] = {
            "assertion_plan": plan,
            "obligation_ids": selected_obligations,
            "sample_shared_domains": primary,
        }
    return result


def render_contract_generated_block(
    interface_plan: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
    *,
    include_automatic_campaign: bool = False,
    randomized_transactions_minimum: int = 0,
) -> str:
    """Render one deterministic, contract-bound observer/assertion block."""

    monitor = interface_plan.get("monitor", {})
    signal_names = tuple(map(str, monitor.get("signals", [])))
    clock = str(monitor.get("clock", ""))
    reset = str(monitor.get("reset", ""))
    assertion_plan, feature_ids = protocol_assertion_metadata(interface_plan)
    protocol_clock_domains = _protocol_clock_domains(
        interface_plan, assertion_plan, primary_clock=clock
    )
    operation_features = known_operation_features(architecture_contract)
    operation_metadata = build_architect_operation_metadata(
        architecture_contract or {"operations": [], "data_objects": [], "data_types": [], "dimensions": [], "parameters": []},
        interface_plan.get("interface_contract", {}),
    ) if interface_plan.get("interface_contract") else {"schema_version": 2, "operations": []}
    protocol_stimulus_plan = build_protocol_stimulus_plan(
        interface_plan.get("interface_contract", {})
    )
    lifecycle_stimulus_plan = build_lifecycle_stimulus_plan(
        interface_plan.get("interface_contract", {}), operation_metadata
    )
    lifecycle_assertion_plan, lifecycle_feature_ids = lifecycle_assertion_metadata(
        interface_plan, operation_metadata
    )

    lines = [
        BEGIN_MARKER,
        "# This block is emitted by the deterministic verification tool from the frozen interface contract.",
        "# It is not authored or repaired by the LLM.",
        "from multigent.verifier_tool import (",
        "    capture_contract_snapshot,",
        "    observe_contract_reset_snapshot,",
        "    sample_contract_snapshot,",
        "    normalize_verification_value as _contract_normalize_verification_value,",
        "    record_stimulus as _contract_runtime_record_stimulus,",
        "    sample_operation as _contract_runtime_sample_operation,",
        "    sample_extension_coverage as _contract_record_extension_coverage,",
        "    check_protocol_assertions as _contract_check_protocol_assertions,",
        "    finalize_protocol_assertions as _contract_finalize_protocol_assertions,",
        "    check_lifecycle_assertions as _contract_check_lifecycle_assertions,",
        "    finalize_lifecycle_assertions as _contract_finalize_lifecycle_assertions,",
        "    drive_protocol_transfers as _contract_drive_protocol_transfers,",
        "    drive_protocol_field_values as _contract_drive_protocol_field_values,",
        "    collect_protocol_transfers as _contract_collect_protocol_transfers,",
        "    collect_protocol_field_values as _contract_collect_protocol_field_values,",
        "    drive_protocol_reset as _contract_drive_protocol_reset,",
        "    generate_canonical_stimulus_for_bin as _contract_generate_canonical_stimulus_for_bin,",
        "    generate_random_canonical_stimuli as _contract_generate_random_canonical_stimuli,",
        "    generate_canonical_discriminating_stimuli as _contract_generate_canonical_discriminating_stimuli,",
        "    contract_coverage as _contract_coverage,",
        "    run_code_owned_verification_campaign as _contract_run_code_owned_verification_campaign,",
        ")",
        "import cocotb as _contract_cocotb",
        "from cocotb.triggers import Edge, ReadOnly, Timer",
        "",
        f"CONTRACT_SIGNAL_NAMES = {_literal(signal_names)}",
        f"CONTRACT_PROTOCOL_ASSERTION_FEATURES = {_literal(feature_ids)}",
        f"CONTRACT_OPERATION_ASSERTION_FEATURES = {_literal(operation_features)}",
        f"CONTRACT_LIFECYCLE_ASSERTION_FEATURES = {_literal(lifecycle_feature_ids)}",
        f"CONTRACT_OPERATION_METADATA = {_literal(operation_metadata)}",
        "",
        *render_operation_golden_model_comment_lines(operation_metadata),
        "",
        f"CONTRACT_PROTOCOL_STIMULUS_PLAN = {_literal(protocol_stimulus_plan)}",
        f"CONTRACT_LIFECYCLE_STIMULUS_PLAN = {_literal(lifecycle_stimulus_plan)}",
        f"CONTRACT_AUTOMATIC_CAMPAIGN_CONFIG = {_literal({'randomized_transactions_minimum': int(randomized_transactions_minimum), 'seed': 0})}",
        "_CONTRACT_PROTOCOL_STATE = {}",
        "_CONTRACT_LIFECYCLE_STATE = {}",
        "",
        "def _contract_generate_operation_stimulus(operation_name, concept, bin_name):",
        "    \"\"\"Return one self-checked code-owned canonical directed vector.\"\"\"",
        "    return _contract_generate_canonical_stimulus_for_bin(",
        "        CONTRACT_OPERATION_METADATA, concept, bin_name, operation_name=operation_name",
        "    )",
        "",
        "def _contract_generate_random_operation_stimuli(operation_name, count, *, seed=0):",
        "    \"\"\"Return reproducible self-checked randomized canonical vectors.\"\"\"",
        "    return _contract_generate_random_canonical_stimuli(",
        "        CONTRACT_OPERATION_METADATA, count, operation_name=operation_name, seed=seed",
        "    )",
        "",
        "def _contract_generate_operation_qualification_stimuli(operation_name):",
        "    \"\"\"Return bounded indexing/sign/cancellation/stale-state witnesses.\"\"\"",
        "    return _contract_generate_canonical_discriminating_stimuli(",
        "        CONTRACT_OPERATION_METADATA, operation_name=operation_name",
        "    )",
        "",
        "def _contract_protocol_scenarios(protocol_group=None):",
        "    \"\"\"Return code-owned directed protocol scenarios and exact bindings.\"\"\"",
        "    if protocol_group == '__global__':",
        "        return tuple(CONTRACT_PROTOCOL_STIMULUS_PLAN['global_scenarios'])",
        "    groups = CONTRACT_PROTOCOL_STIMULUS_PLAN['groups']",
        "    if protocol_group is None:",
        "        return tuple(groups)",
        "    matches = tuple(item for item in groups if item['name'] == protocol_group)",
        "    assert len(matches) == 1, f'unknown or ambiguous protocol_group={protocol_group!r}'",
        "    return tuple(matches[0]['scenarios'])",
        "",
        "def _contract_protocol_channel(protocol_group, protocol_channel):",
        "    \"\"\"Return one exact channel binding for executable tool drivers.\"\"\"",
        "    groups = tuple(item for item in CONTRACT_PROTOCOL_STIMULUS_PLAN['groups'] if item['name'] == protocol_group)",
        "    assert len(groups) == 1, f'unknown or ambiguous protocol_group={protocol_group!r}'",
        "    channels = groups[0]['channels']",
        "    assert protocol_channel in channels, f'unknown protocol_channel={protocol_channel!r}'",
        "    return channels[protocol_channel]",
        "",
        "def _contract_standard_protocol_group(protocol_group, protocol_profile=None):",
        "    \"\"\"Return one exact compiled standard-protocol group binding.\"\"\"",
        "    groups = tuple(item for item in CONTRACT_PROTOCOL_STIMULUS_PLAN['groups'] if item['name'] == protocol_group)",
        "    if protocol_profile is not None:",
        "        groups = tuple(item for item in groups if item['profile'] == protocol_profile)",
        "    assert len(groups) == 1, f'unknown or ambiguous standard protocol group={protocol_group!r} profile={protocol_profile!r}'",
        "    return groups[0]",
        "",
        "def _contract_protocol_event_transaction(profile_name, transaction_name):",
        "    \"\"\"Return one compiled custom-protocol monitor binding.\"\"\"",
        "    semantics = CONTRACT_PROTOCOL_STIMULUS_PLAN['feature_plan']['bindings']['protocol_semantics']",
        "    profiles = tuple(item for item in semantics['profiles'] if item['name'] == profile_name)",
        "    assert len(profiles) == 1, f'unknown or ambiguous protocol profile={profile_name!r}'",
        "    transactions = tuple(item for item in profiles[0]['transactions'] if item['name'] == transaction_name)",
        "    assert len(transactions) == 1, f'unknown or ambiguous protocol transaction={transaction_name!r}'",
        "    return profiles[0], transactions[0]",
        "",
    ]
    lines += render_operation_assertion_lines(operation_features)
    lines += [""]
    lines += render_protocol_assertion_lines(
        interface_plan,
        reset=reset,
        obligations=assertion_plan,
        clock_domains=protocol_clock_domains,
    )
    lines += [""]
    lines += render_lifecycle_assertion_lines(lifecycle_assertion_plan)
    lines += [
        "",
        "def _check_contract_assertions(snapshot, clock_name=None):",
        "    completed_stalls = _check_contract_protocol_assertions(snapshot, clock_name)",
        "    domain = CONTRACT_PROTOCOL_CLOCK_DOMAINS.get(clock_name)",
        "    if domain is None or domain['sample_shared_domains']:",
        "        _check_contract_lifecycle_assertions(snapshot)",
        "    return completed_stalls",
        "",
        "def _finalize_contract_assertions():",
        "    _finalize_contract_protocol_assertions()",
        "    _finalize_contract_lifecycle_assertions()",
    ]
    lines += [""]
    lines += render_protocol_monitor_lines(
        clock=clock,
        reset=reset,
        assertion_callback="_check_contract_assertions",
        clock_domains=protocol_clock_domains,
    )
    if include_automatic_campaign:
        lines += [
            "",
            "@_contract_cocotb.test(timeout_time=3600, timeout_unit='sec')",
            "@_contract_coverage()",
            "async def _contract_automatic_verification_campaign(dut):",
            "    \"\"\"Execute all code-owned operation/protocol/lifecycle scope.\"\"\"",
            "    return await _contract_run_code_owned_verification_campaign(",
            "        dut,",
            "        CONTRACT_PROTOCOL_STIMULUS_PLAN['interface_contract'],",
            "        CONTRACT_OPERATION_METADATA,",
            "        CONTRACT_LIFECYCLE_STIMULUS_PLAN,",
            "        randomized_count=CONTRACT_AUTOMATIC_CAMPAIGN_CONFIG['randomized_transactions_minimum'],",
            "        seed=CONTRACT_AUTOMATIC_CAMPAIGN_CONFIG['seed'],",
            "    )",
        ]
    lines += ["", END_MARKER, ""]
    return "\n".join(lines)


def install_contract_generated_block(
    source: str,
    interface_plan: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
    *,
    include_automatic_campaign: bool = False,
    randomized_transactions_minimum: int = 0,
) -> str:
    """Replace the final generated block with the current deterministic version."""

    verifier_source = strip_contract_generated_block(source)
    _assert_reserved_names_are_free(verifier_source)
    _assert_authority_boundary(verifier_source)
    return verifier_source.rstrip() + "\n\n" + render_contract_generated_block(
        interface_plan,
        architecture_contract,
        include_automatic_campaign=include_automatic_campaign,
        randomized_transactions_minimum=randomized_transactions_minimum,
    )


def validate_contract_generated_block(
    source: str,
    interface_plan: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
    *,
    include_automatic_campaign: bool = False,
    randomized_transactions_minimum: int = 0,
) -> None:
    """Reject edits or omissions of the code-owned block."""

    verifier_source = strip_contract_generated_block(source)
    expected = verifier_source.rstrip() + "\n\n" + render_contract_generated_block(
        interface_plan,
        architecture_contract,
        include_automatic_campaign=include_automatic_campaign,
        randomized_transactions_minimum=randomized_transactions_minimum,
    )
    normalized = source if source.endswith("\n") else source + "\n"
    if normalized != expected:
        raise ValueError("Saved TB contains a modified contract-generated protocol monitor")


def extract_stimulus_coverage_intents(source: str) -> list[dict[str, Any]]:
    """Read the literal Verifier-authored stimulus-to-feature declaration."""

    verifier_source = strip_contract_generated_block(source)
    tree = ast.parse(verifier_source)
    definitions = _top_level_definitions(tree)
    declarations: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "STIMULUS_COVERAGE_INTENTS"
            for target in node.targets
        ):
            declarations.append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "STIMULUS_COVERAGE_INTENTS"
        ):
            declarations.append(node.value)
    if len(declarations) != 1:
        raise ValueError(
            "Every test file needs exactly one literal STIMULUS_COVERAGE_INTENTS declaration"
        )
    try:
        value = _static_value(declarations[0], definitions)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "STIMULUS_COVERAGE_INTENTS must use statically resolvable metadata"
        ) from exc
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("STIMULUS_COVERAGE_INTENTS must be a non-empty list")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"label", "targets"}:
            raise ValueError("Each stimulus intent needs exactly label and targets")
        label = item["label"]
        targets = item["targets"]
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Stimulus intent labels must be non-empty strings")
        if not isinstance(targets, (list, tuple)) or not targets or not all(
            isinstance(target, str) and target for target in targets
        ):
            raise ValueError("Stimulus intent targets must be non-empty string lists")
        if len(targets) != len(set(targets)):
            raise ValueError(f"Stimulus intent {label!r} repeats a target")
        result.append({"label": label, "targets": list(targets)})
    labels = [item["label"] for item in result]
    if len(labels) != len(set(labels)):
        raise ValueError("Stimulus intent labels must be unique within a test file")
    return result


def _axi4_protocol_responder_transfer_calls(
    tree: ast.AST,
    parents: Mapping[ast.AST, ast.AST],
    interface_contract: Mapping[str, Any] | None,
) -> list[tuple[ast.Call, str, str]]:
    """Resolve exact channel traffic performed by the reusable AXI4 responder.

    An imported verifier_tool driver is opaque to local assignment tracing. Credit
    only the read/write directions whose literal ``request_counts`` are nonzero
    and only for a statically resolved standard AXI4 group. A read-only call must
    never become evidence for write-response stimulus.
    """

    if not isinstance(interface_contract, Mapping):
        return []

    group_variables: dict[str, tuple[str, str]] = {}
    for assignment in ast.walk(tree):
        if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
            continue
        value = assignment.value
        if not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "_contract_standard_protocol_group"
            and len(value.args) >= 2
            and all(
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
                for argument in value.args[:2]
            )
        ):
            continue
        binding = (str(value.args[0].value), str(value.args[1].value))
        targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
        for target in targets:
            if isinstance(target, ast.Name):
                group_variables[target.id] = binding

    def group_binding(node: ast.AST | None) -> tuple[str, str] | None:
        if isinstance(node, ast.Name):
            return group_variables.get(node.id)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_contract_standard_protocol_group"
            and len(node.args) >= 2
            and all(
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
                for argument in node.args[:2]
            )
        ):
            return (str(node.args[0].value), str(node.args[1].value))
        return None

    def channel_binding(channel: Mapping[str, Any]) -> tuple[str, str] | None:
        group = str(channel.get("protocol_group", ""))
        protocol_channel = str(channel.get("protocol_channel", ""))
        for item in channel.get("metadata", []):
            text = str(item)
            if not group and (match := re.search(r"(?:^|\s)protocol_group=([^\s]+)", text)):
                group = match.group(1)
            if not protocol_channel and (
                match := re.search(r"(?:^|\s)protocol_channel=([^\s]+)", text)
            ):
                protocol_channel = match.group(1)
        return (group, protocol_channel) if group and protocol_channel else None

    channels_by_group: dict[tuple[str, str], dict[str, str]] = {}
    for item in interface_contract.get("channels", []):
        if not isinstance(item, Mapping) or str(item.get("protocol_profile", "")) != "axi4":
            continue
        binding = channel_binding(item)
        if binding is None:
            continue
        group, protocol_channel = binding
        channels_by_group.setdefault((group, "axi4"), {})[protocol_channel] = str(
            item.get("name", "")
        )

    events: list[tuple[ast.Call, str, str]] = []

    def executes_async_call(call: ast.Call) -> bool:
        parent = parents.get(call)
        if isinstance(parent, ast.Await):
            return True
        if not (
            isinstance(parent, ast.Call)
            and (
                (isinstance(parent.func, ast.Name) and parent.func.id in {"create_task", "ensure_future"})
                or (
                    isinstance(parent.func, ast.Attribute)
                    and parent.func.attr in {"start_soon", "create_task", "ensure_future"}
                )
            )
        ):
            return False
        current: ast.AST = parent
        enclosing: ast.AsyncFunctionDef | None = None
        while current in parents:
            current = parents[current]
            if isinstance(current, ast.AsyncFunctionDef):
                enclosing = current
                break
        return bool(
            enclosing is not None
            and any(
                isinstance(node, ast.Await)
                and getattr(node, "lineno", 0) > getattr(parent, "lineno", 0)
                for node in ast.walk(enclosing)
            )
        )

    for call in ast.walk(tree):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "serve_axi4_protocol_transactions"
            and executes_async_call(call)
        ):
            continue
        keywords = {
            keyword.arg: keyword.value
            for keyword in call.keywords
            if keyword.arg is not None
        }
        group_node = keywords.get("group") or (call.args[2] if len(call.args) >= 3 else None)
        counts_node = keywords.get("request_counts") or (
            call.args[3] if len(call.args) >= 4 else None
        )
        binding = group_binding(group_node)
        try:
            counts = ast.literal_eval(counts_node) if counts_node is not None else None
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            counts = None
        if binding is None or not isinstance(counts, dict):
            continue
        group_channels = channels_by_group.get(binding, {})
        requested_protocol_channels: list[tuple[str, str]] = []
        if int(counts.get("read", 0)) > 0:
            requested_protocol_channels.extend(
                [("read_address", "collector_transport"), ("read_data", "driver_transport")]
            )
        if int(counts.get("write", 0)) > 0:
            requested_protocol_channels.extend(
                [
                    ("write_address", "collector_transport"),
                    ("write_data", "collector_transport"),
                    ("write_response", "driver_transport"),
                ]
            )
        for protocol_channel, kind in requested_protocol_channels:
            channel_name = group_channels.get(protocol_channel)
            if channel_name:
                events.append((call, channel_name, kind))
    return events


def _scheduled_task_active_interval(
    call: ast.Call,
    tree: ast.AST,
    parents: Mapping[ast.AST, ast.AST],
) -> tuple[int, int] | None:
    """Return the lexical lifetime of an assigned background coroutine task.

    A reusable responder started with ``start_soon`` can legitimately serve more
    than one checked scenario.  Its transport effect remains active until the
    assigned task is explicitly killed, cancelled, or awaited.  This bounded AST
    rule deliberately requires an assigned task name and a recognized scheduler;
    it does not infer lifetime for arbitrary fire-and-forget coroutines.
    """

    scheduler = parents.get(call)
    if not (
        isinstance(scheduler, ast.Call)
        and (
            (
                isinstance(scheduler.func, ast.Name)
                and scheduler.func.id in {"create_task", "ensure_future"}
            )
            or (
                isinstance(scheduler.func, ast.Attribute)
                and scheduler.func.attr in {"start_soon", "create_task", "ensure_future"}
            )
        )
    ):
        return None
    assignment = parents.get(scheduler)
    if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
        return None
    targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
    task_names = [target.id for target in targets if isinstance(target, ast.Name)]
    if len(task_names) != 1:
        return None
    task_name = task_names[0]

    current: ast.AST = assignment
    function: ast.AsyncFunctionDef | ast.FunctionDef | None = None
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.AsyncFunctionDef, ast.FunctionDef)):
            function = current
            break
    if function is None:
        return None

    end_line = int(getattr(function, "end_lineno", assignment.lineno)) + 1
    for node in ast.walk(function):
        line = int(getattr(node, "lineno", 0))
        if line <= assignment.lineno:
            continue
        terminates = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"kill", "cancel"}
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == task_name
        ) or (
            isinstance(node, ast.Await)
            and isinstance(node.value, ast.Name)
            and node.value.id == task_name
        )
        if terminates:
            end_line = min(end_line, line)
    return assignment.lineno, end_line


def validate_verifier_authored_structure(
    sources: list[str],
    required_obligations: set[str],
    architecture_contract: Mapping[str, Any] | None = None,
    interface_contract: Mapping[str, Any] | None = None,
    *,
    randomized_transactions_minimum: int = 0,
    code_owned_obligations: set[str] | frozenset[str] = frozenset(),
    support_sources: Sequence[str] = (),
) -> None:
    """Require auditable sections and complete declared stimulus intent coverage."""

    captured_signal_names = (
        {
            str(signal.get("name"))
            for signal in interface_contract.get("signals", [])
            if isinstance(signal, Mapping) and signal.get("name")
        }
        if isinstance(interface_contract, Mapping)
        else None
    )

    pipeline_owned_operation_features = {
        feature
        for features in known_operation_features(architecture_contract).values()
        for feature in features
    }
    required_llm_operation_features: set[str] = set()
    for operation in (architecture_contract or {}).get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        operation_name = str(operation.get("name", ""))
        baseline, extensions = operation_feature_selections(operation)
        for feature in [*baseline, *extensions]:
            feature_id = canonical_operation_obligation_id(
                operation_name, str(feature)
            )
            if feature_id not in pipeline_owned_operation_features:
                required_llm_operation_features.add(feature_id)
    errors: list[str] = []
    declared_targets: set[str] = set()
    known_labels: set[str] = set()
    used_labels: set[str] = set()
    stimulus_kinds: set[str] = set()
    statically_proven_randomized_records = 0
    unprovable_randomized_records: list[str] = []
    support_trace_parameter_hints: dict[str, dict[int, str]] = {}
    record_shapes: dict[
        str, tuple[dict[str, str | None] | None, dict[str, str | None] | None, dict[str, str | None] | None]
    ] = {}
    record_operations: dict[str, set[str]] = {}
    operation_io = {
        str(operation.get("name", "")): (
            {str(name) for name in operation.get("inputs", [])},
            {str(name) for name in operation.get("outputs", [])},
        )
        for operation in (architecture_contract or {}).get("operations", [])
        if isinstance(operation, Mapping) and operation.get("name")
    }
    interface_signals = [
        item
        for item in (interface_contract or {}).get("signals", [])
        if isinstance(item, Mapping)
    ]
    interface_channels = [
        item
        for item in (interface_contract or {}).get("channels", [])
        if isinstance(item, Mapping)
    ]
    operation_output_signals: dict[str, set[str]] = {}
    operation_input_channels: dict[str, set[str]] = {}
    operation_output_channels: dict[str, set[str]] = {}
    operation_job_start_channels: dict[str, set[str]] = {}
    code_owned_operation_names: set[str] = set()
    for operation in (architecture_contract or {}).get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        outputs = set(map(str, operation.get("outputs", [])))
        inputs = set(map(str, operation.get("inputs", [])))
        operation_name = str(operation.get("name", ""))
        if operation.get("coverage_family_source") == "catalog":
            code_owned_operation_names.add(operation_name)
        operation_input_channels[operation_name] = {
            str(channel.get("name", ""))
            for channel in interface_channels
            if channel.get("direction") == "input"
            and inputs & set(map(str, channel.get("data_objects", [])))
        }
        operation_output_channels[operation_name] = {
            str(channel.get("name", ""))
            for channel in interface_channels
            if channel.get("direction") == "output"
            and outputs & set(map(str, channel.get("data_objects", [])))
        }
        operation_output_signals[operation_name] = {
            str(signal.get("name", ""))
            for channel in interface_channels
            if channel.get("direction") == "output"
            and outputs & set(map(str, channel.get("data_objects", [])))
            for signal in interface_signals
            if signal.get("channel") == channel.get("name")
            and signal.get("role") == "payload"
        }
    if (architecture_contract or {}).get("data_objects"):
        try:
            compiled_operation_metadata = build_architect_operation_metadata(
                architecture_contract or {}, interface_contract or {}
            )
        except (KeyError, ValueError):
            compiled_operation_metadata = {"operations": []}
        for operation in compiled_operation_metadata.get("operations", []):
            if not isinstance(operation, Mapping):
                continue
            lifecycle = operation.get("lifecycle", {})
            operation_job_start_channels[str(operation.get("operation_name", ""))] = {
                str(item.get("channel", ""))
                for item in lifecycle.get("job_accept_channels", [])
                if isinstance(item, Mapping) and item.get("channel")
            }
    has_complete_operation_io = any(
        inputs and outputs for inputs, outputs in operation_io.values()
    )
    llm_operation_feature_comments: set[str] = set()
    for source_index, source in enumerate(sources):
        try:
            verifier_source = strip_contract_generated_block(source)
        except ValueError as exc:
            errors.append(f"test source {source_index}: {exc}")
            continue
        if STIMULUS_SECTION not in verifier_source:
            errors.append(f"Test source is missing {STIMULUS_SECTION}")
        if OPERATION_ASSERTION_SECTION not in verifier_source:
            errors.append(f"Test source is missing {OPERATION_ASSERTION_SECTION}")
        try:
            tree = ast.parse(verifier_source)
        except SyntaxError as exc:
            errors.append(f"test source {source_index} has syntax error: {exc.msg}")
            continue
        for function_name, parameter_hints in (
            _called_protocol_trace_parameter_hints(tree).items()
        ):
            merged = support_trace_parameter_hints.setdefault(function_name, {})
            for index, trace_name in parameter_hints.items():
                existing = merged.get(index)
                if existing is None or existing == trace_name:
                    merged[index] = trace_name
                else:
                    merged.pop(index, None)
        shell_escaped_keys = _shell_escaped_subscript_keys(tree)
        if shell_escaped_keys:
            errors.append(
                "Generated Python contains shell-quoting artifacts inside dict "
                f"subscript keys; source={source_index}, occurrences="
                f"{[(line, repr(value)) for line, value in shell_escaped_keys]}. "
                "Write ordinary Python keys such as result['expected']; do not "
                "preserve command-shell quote splicing in emitted source."
            )
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        local_functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        def enclosing_function(node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
            current = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return current
            return None

        def enclosing_loops(node: ast.AST) -> frozenset[ast.AST]:
            result: set[ast.AST] = set()
            current = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.For, ast.AsyncFor, ast.While)):
                    result.add(current)
            return frozenset(result)

        channel_variables: dict[str, str] = {}
        for candidate in ast.walk(tree):
            if not isinstance(candidate, (ast.Assign, ast.AnnAssign)):
                continue
            value = candidate.value
            if not (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "_contract_protocol_channel"
                and len(value.args) == 2
                and isinstance(value.args[1], ast.Constant)
                and isinstance(value.args[1].value, str)
            ):
                continue
            targets = candidate.targets if isinstance(candidate, ast.Assign) else [candidate.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    channel_variables[target.id] = value.args[1].value

        def resolved_channel(argument: ast.AST) -> str | None:
            if isinstance(argument, ast.Name):
                return channel_variables.get(argument.id)
            if (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Name)
                and argument.func.id == "_contract_protocol_channel"
                and len(argument.args) == 2
                and isinstance(argument.args[1], ast.Constant)
                and isinstance(argument.args[1].value, str)
            ):
                return argument.args[1].value
            return None

        tool_driven_channels: set[str] = set()
        tool_collected_channels: set[str] = set()
        valid_transfer_calls: list[tuple[ast.Call, str, str]] = []
        for candidate in ast.walk(tree):
            if not (
                isinstance(candidate, ast.Call)
                and isinstance(candidate.func, ast.Name)
                and candidate.func.id
                in {
                    "_contract_drive_protocol_transfers",
                    "_contract_collect_protocol_transfers",
                    "_contract_drive_protocol_field_values",
                    "_contract_collect_protocol_field_values",
                }
            ):
                continue
            is_driver = candidate.func.id.startswith("_contract_drive_")
            is_field_values = candidate.func.id.endswith("_field_values")
            minimum_args = (
                3 if is_field_values
                else 4 if is_driver
                else 3
            )
            channel = (
                resolved_channel(candidate.args[2])
                if len(candidate.args) >= 3
                else None
            )
            clock_is_literal = (
                len(candidate.args) >= 2
                and isinstance(candidate.args[1], ast.Constant)
                and isinstance(candidate.args[1].value, str)
            )
            keyword_values = {
                keyword.arg: keyword.value
                for keyword in candidate.keywords
                if keyword.arg is not None
            }
            field_node = (
                candidate.args[3]
                if len(candidate.args) >= 4
                else keyword_values.get("field")
            )
            field_is_literal = not is_field_values or (
                isinstance(field_node, ast.Constant)
                and isinstance(field_node.value, str)
            )
            has_values = (
                not (is_driver and is_field_values)
                or len(candidate.args) >= 5
                or "values" in keyword_values
            )
            is_awaited = isinstance(parents.get(candidate), ast.Await)
            allowed_keywords = (
                {"field", "values", "timeout_cycles", "settle_timer_ps"}
                if is_driver and is_field_values
                else {"timeout_cycles", "settle_timer_ps"}
                if is_driver
                else {
                    "count",
                    "until_last",
                    "ready_pattern",
                    "timeout_cycles",
                    "settle_timer_ps",
                    *({"field"} if is_field_values else set()),
                }
            )
            invalid_keywords = {
                keyword.arg
                for keyword in candidate.keywords
                if keyword.arg is not None
            } - allowed_keywords
            if (
                len(candidate.args) < minimum_args
                or channel is None
                or not clock_is_literal
                or not field_is_literal
                or not has_values
                or not is_awaited
                or invalid_keywords
            ):
                example = (
                    "await _contract_drive_protocol_field_values("
                    "dut, 'clk', channel, 'payload', values)"
                    if is_driver and is_field_values
                    else "await _contract_drive_protocol_transfers("
                    "dut, 'clk', channel, [{'payload': value} for value in values])"
                    if is_driver
                    else "await _contract_collect_protocol_field_values("
                    "dut, 'clk', channel, 'payload', count=expected_count)"
                    if is_field_values
                    else "await _contract_collect_protocol_transfers("
                    "dut, 'clk', channel, count=expected_count)"
                )
                errors.append(
                    f"source={source_index}, line={candidate.lineno}: "
                    f"{candidate.func.id} is not an executable tool-owned transfer "
                    "call; it must be awaited and use the exact exported signature "
                    f"with the resolved channel as positional argument 3. Use {example}. "
                    f"invalid_keywords={sorted(invalid_keywords)}"
                )
                continue
            no_transfer = False
            if is_driver:
                beats_or_values = (
                    candidate.args[4]
                    if is_field_values and len(candidate.args) >= 5
                    else keyword_values.get("values")
                    if is_field_values
                    else candidate.args[3]
                    if len(candidate.args) >= 4
                    else None
                )
                try:
                    literal_values = ast.literal_eval(beats_or_values)
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    no_transfer = bool(
                        isinstance(beats_or_values, ast.Name)
                        and _name_is_unobserved_literal_alias(
                            tree, candidate, beats_or_values.id
                        )
                    )
                else:
                    no_transfer = isinstance(
                        literal_values, (list, tuple, set, dict)
                    ) and not literal_values
            else:
                count_node = keyword_values.get("count")
                until_last_node = keyword_values.get("until_last")
                no_transfer = (
                    isinstance(count_node, ast.Constant)
                    and count_node.value == 0
                    and not (
                        isinstance(until_last_node, ast.Constant)
                        and bool(until_last_node.value)
                    )
                )
            if no_transfer:
                continue
            if is_driver:
                tool_driven_channels.add(channel)
                valid_transfer_calls.append(
                    (
                        candidate,
                        channel,
                        "driver" if is_field_values else "driver_transport",
                    )
                )
            else:
                tool_collected_channels.add(channel)
                valid_transfer_calls.append(
                    (
                        candidate,
                        channel,
                        "collector" if is_field_values else "collector_transport",
                    )
                )

        # Imported reusable responders are opaque to local signal-assignment
        # tracing. Resolve their normative call contract into the same channel
        # event representation used by contract-generated transfer helpers.
        responder_transfer_calls = _axi4_protocol_responder_transfer_calls(
            tree, parents, interface_contract
        )
        valid_transfer_calls.extend(responder_transfer_calls)

        # Summarize fixed-channel tool calls through local wrapper helpers, then
        # project each awaited helper invocation back into its caller.  This lets
        # the audit credit a small reusable collector without turning a single
        # call elsewhere in the file into proof for every checked job.
        function_channel_summary: dict[str, set[tuple[str, str]]] = {
            name: set() for name in local_functions
        }
        for call, channel, kind in valid_transfer_calls:
            function = enclosing_function(call)
            if function is not None:
                function_channel_summary[function.name].add((channel, kind))
        changed = True
        while changed:
            changed = False
            for function_name, function in local_functions.items():
                expanded = set(function_channel_summary[function_name])
                for call in ast.walk(function):
                    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                        continue
                    callee = local_functions.get(call.func.id)
                    if callee is None or callee is function:
                        continue
                    if isinstance(callee, ast.AsyncFunctionDef) and not _async_call_is_consumed(
                        call, parents
                    ):
                        continue
                    expanded.update(function_channel_summary[callee.name])
                if expanded != function_channel_summary[function_name]:
                    function_channel_summary[function_name] = expanded
                    changed = True

        transfer_events: list[
            tuple[str, int, frozenset[ast.AST], str, str]
        ] = []
        for call, channel, kind in valid_transfer_calls:
            function = enclosing_function(call)
            if function is not None:
                transfer_events.append(
                    (function.name, call.lineno, enclosing_loops(call), channel, kind)
                )
        active_transfer_intervals: list[tuple[str, int, int, str, str]] = []
        for call, channel, kind in responder_transfer_calls:
            function = enclosing_function(call)
            interval = _scheduled_task_active_interval(call, tree, parents)
            if function is not None and interval is not None:
                active_transfer_intervals.append(
                    (function.name, interval[0], interval[1], channel, kind)
                )
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                continue
            callee = local_functions.get(call.func.id)
            caller = enclosing_function(call)
            if callee is None or caller is None or callee is caller:
                continue
            summary = function_channel_summary.get(callee.name, set())
            if not summary:
                continue
            if isinstance(callee, ast.AsyncFunctionDef) and not _async_call_is_consumed(
                call, parents
            ):
                errors.append(
                    f"source={source_index}, line={call.lineno}: asynchronous "
                    f"transfer helper {callee.name!r} must be awaited or no DUT "
                    "traffic/observation occurs"
                )
                continue
            for channel, kind in summary:
                transfer_events.append(
                    (caller.name, call.lineno, enclosing_loops(call), channel, kind)
                )
        proven_count, unprovable = _static_randomized_record_count(tree, parents)
        statically_proven_randomized_records += proven_count
        unprovable_randomized_records.extend(
            f"source={source_index}, line={line}" for line in unprovable
        )
        errors.extend(_unadvanced_checked_stimulus_records(tree, source_index, verifier_source))
        errors.extend(_preawaited_protocol_evidence_stimulus(tree, source_index))
        errors.extend(
            _dut_writes_after_protocol_evidence_capture(tree, source_index)
        )
        errors.extend(
            _invalid_protocol_evidence_record_accesses(
                tree,
                source_index,
                captured_signal_names,
            )
        )
        errors.extend(_unused_passed_helper_parameters(tree, source_index))
        errors.extend(_unchecked_stall_replays(tree, source_index))
        errors.extend(
            _overlapping_unqueued_command_starts(
                tree, source_index, interface_contract
            )
        )
        errors.extend(
            _unrecorded_full_operation_loops(
                tree, source_index, interface_contract
            )
        )
        errors.extend(
            _vacuous_single_bit_signal_assertions(
                tree, source_index, interface_contract
            )
        )
        errors.extend(
            _late_command_pulse_reads(
                tree, source_index, interface_contract
            )
        )
        errors.extend(
            _reset_abort_operation_records_without_relaunch(
                tree, source_index, verifier_source, interface_contract
            )
        )
        errors.extend(
            _uninitialized_contract_inputs(
                tree, source_index, interface_contract
            )
        )
        errors.extend(
            _nonprogressing_receiver_ready_loops(
                tree, source_index, interface_contract
            )
        )
        errors.extend(_invalid_cocotb_time_units(tree, source_index))
        errors.extend(
            _unsettled_post_rising_output_reads(
                tree, source_index, interface_contract
            )
        )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_contract_record_checked_stimulus"
            ):
                errors.append(
                    "Qualified _contract_record_checked_stimulus calls are invalid; "
                    f"source={source_index}, line={node.lineno}. "
                    "contract_coverage._contract_record_checked_stimulus(...) is not "
                    "the code-owned helper and does not satisfy a stimulus intent. "
                    "Replace it with the bare wrapper-provided call "
                    "_contract_record_checked_stimulus(stimulus_kind, stimulus, "
                    "expected, observed, operations=(\"exact_operation\",), "
                    "label=\"case\") using four positional arguments plus exactly "
                    "the operations and label keywords. Do not import or define the "
                    "private helper."
                )
        file_used_labels: set[str] = set()
        record_nodes: dict[str, ast.Call] = {}
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_contract_record_checked_stimulus"
            ):
                continue
            keyword_names = [item.arg for item in node.keywords]
            if (
                len(node.args) != 4
                or any(name is None for name in keyword_names)
                or sorted(keyword_names) != ["label", "operations"]
            ):
                errors.append(
                    "Every _contract_record_checked_stimulus call must use exactly "
                    "_contract_record_checked_stimulus(stimulus_kind, stimulus, "
                    "expected, observed, operations=(\"exact_operation\",), "
                    f"label=\"case\"); source={source_index}, line={node.lineno}. "
                    "Do not pass dut/info or omit the complete expected/observed mappings."
                )
                continue
            for argument_index, argument_name in (
                (1, "stimulus"), (2, "expected"), (3, "observed")
            ):
                argument = node.args[argument_index]
                if isinstance(argument, (ast.Constant, ast.List, ast.Tuple, ast.Set)):
                    errors.append(
                        f"_contract_record_checked_stimulus {argument_name} must be a "
                        "mapping, not a literal "
                        f"{type(argument).__name__.removeprefix('AST').lower()}; "
                        f"source={source_index}, line={node.lineno}. Use a dict literal "
                        "or a mapping variable containing the real transaction fields."
                    )
            if isinstance(parents.get(node), ast.Await):
                errors.append(
                    "_contract_record_checked_stimulus is a synchronous code-owned "
                    f"helper and must not be awaited; source={source_index}, "
                    f"line={node.lineno}. Call it directly after DUT observation."
                )
            label_nodes = [item.value for item in node.keywords if item.arg == "label"]
            if len(label_nodes) != 1 or not isinstance(label_nodes[0], ast.Constant) or not isinstance(label_nodes[0].value, str):
                errors.append(
                    "Every _contract_record_checked_stimulus call needs one literal "
                    f"label; source={source_index}, line={node.lineno}"
                )
                continue
            operations_nodes = [
                item.value for item in node.keywords if item.arg == "operations"
            ]
            try:
                literal_operations = ast.literal_eval(operations_nodes[0])
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError, IndexError):
                errors.append(
                    "Every _contract_record_checked_stimulus operations keyword must "
                    "be a literal tuple/list of exact operation names; "
                    f"source={source_index}, line={node.lineno}"
                )
                literal_operations = ()
            if not (
                isinstance(literal_operations, (tuple, list))
                and all(isinstance(value, str) for value in literal_operations)
            ):
                errors.append(
                    "Every _contract_record_checked_stimulus operations keyword must "
                    "be a literal tuple/list of exact operation names; "
                    f"source={source_index}, line={node.lineno}"
                )
                literal_operations = ()
            stimulus_kind_node = node.args[0]
            if (
                not isinstance(stimulus_kind_node, ast.Constant)
                or stimulus_kind_node.value not in {"directed", "randomized"}
            ):
                errors.append(
                    "_contract_record_checked_stimulus stimulus_kind must be the "
                    "literal 'directed' or 'randomized'; "
                    f"source={source_index}, line={node.lineno}. Labels describe "
                    "protocol/reset/operation scenarios separately."
                )
            else:
                stimulus_kinds.add(stimulus_kind_node.value)
            try:
                literal_expected = ast.literal_eval(node.args[2])
                literal_observed = ast.literal_eval(node.args[3])
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                pass
            else:
                if isinstance(literal_expected, dict) and literal_expected == literal_observed:
                    errors.append(
                        "_contract_record_checked_stimulus expected/observed are "
                        f"identical literal values; source={source_index}, line={node.lineno}, "
                        "label=" + repr(label_nodes[0].value) + "; observed must come "
                        "from a DUT observation, not a copied expected constant"
                    )
            expected_shape = _literal_mapping_shape(node.args[2])
            observed_shape = _literal_mapping_shape(node.args[3])
            if isinstance(node.args[2], ast.Dict) and isinstance(node.args[3], ast.Dict):
                expected_values = {
                    key.value: value
                    for key, value in zip(node.args[2].keys, node.args[2].values)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                observed_values = {
                    key.value: value
                    for key, value in zip(node.args[3].keys, node.args[3].values)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                aliased_fields = []
                for key in sorted(set(expected_values) & set(observed_values)):
                    expected_value = expected_values[key]
                    observed_value = observed_values[key]
                    if (
                        isinstance(expected_value, ast.Name)
                        and isinstance(observed_value, ast.Name)
                        and (
                            expected_value.id == observed_value.id
                            or _name_aliases_name(
                                tree,
                                node,
                                observed_value.id,
                                expected_value.id,
                            )
                        )
                    ):
                        aliased_fields.append(key)
                if aliased_fields:
                    errors.append(
                        "_contract_record_checked_stimulus observed values alias the "
                        "expected values instead of a DUT observation; "
                        f"source={source_index}, line={node.lineno}, "
                        f"label={label_nodes[0].value!r}, fields={aliased_fields}. "
                        "Collect the role-bound DUT output and pass that independently."
                    )
            if expected_shape is not None and observed_shape is not None:
                expected_keys = set(expected_shape)
                observed_keys = set(observed_shape)
                if expected_keys != observed_keys:
                    errors.append(
                        "_contract_record_checked_stimulus expected/observed mappings "
                        f"must have identical keys; source={source_index}, line={node.lineno}, "
                        f"missing_observed={sorted(expected_keys - observed_keys)}, "
                        f"unexpected_observed={sorted(observed_keys - expected_keys)}"
                    )
                for key in sorted(expected_keys & observed_keys):
                    expected_kind = expected_shape[key]
                    observed_kind = observed_shape[key]
                    if (
                        expected_kind is not None
                        and observed_kind is not None
                        and expected_kind != observed_kind
                    ):
                        errors.append(
                            "_contract_record_checked_stimulus expected/observed value "
                            f"types differ for key {key!r}; source={source_index}, "
                            f"line={node.lineno}, expected={expected_kind}, observed={observed_kind}"
                        )
            if isinstance(node.args[3], ast.Dict):
                literal_observed_fields: list[str] = []
                for key_node, value_node in zip(
                    node.args[3].keys, node.args[3].values, strict=True
                ):
                    if key_node is None:
                        continue
                    try:
                        key = ast.literal_eval(key_node)
                    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                        continue
                    try:
                        ast.literal_eval(value_node)
                    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                        if not (
                            isinstance(value_node, ast.Name)
                            and _name_is_unobserved_literal_alias(tree, node, value_node.id)
                        ):
                            continue
                    literal_observed_fields.append(str(key))
                if literal_observed_fields:
                    errors.append(
                        "_contract_record_checked_stimulus observed mapping contains "
                        "literal constants instead of DUT-derived observations; "
                        f"source={source_index}, line={node.lineno}, "
                        f"label={label_nodes[0].value!r}, "
                        f"fields={sorted(literal_observed_fields)}. Capture each value "
                        "while monitoring the DUT and record a variable that is actually "
                        "updated by that observation. Renaming or aliasing [], 0, or "
                        "another constant does not create observed evidence."
                    )
            file_used_labels.add(label_nodes[0].value)
            record_nodes[label_nodes[0].value] = node
            record_operations[label_nodes[0].value] = set(literal_operations)
            record_shapes[label_nodes[0].value] = (
                _literal_mapping_shape(node.args[1]),
                expected_shape,
                observed_shape,
            )
        used_labels.update(file_used_labels)

        try:
            intents = extract_stimulus_coverage_intents(source)
        except ValueError as exc:
            errors.append(f"test source {source_index}: {exc}")
            intents = []
        for item in intents:
            label = item["label"]
            if label in known_labels:
                errors.append(f"Stimulus intent label {label!r} is duplicated across files")
            known_labels.add(label)
            declared_targets.update(item["targets"])
            if label not in file_used_labels:
                errors.append(
                    f"Stimulus intent {label!r} is declared in STIMULUS_COVERAGE_INTENTS but "
                    f"no _contract_record_checked_stimulus(..., label={label!r}) call exists "
                    "anywhere in this file. This is a missing implementation, not a missing "
                    "comment: write the actual stimulus construction, DUT drive, and the "
                    "_contract_record_checked_stimulus call for it. Do not add the "
                    f"'# STIMULUS [{label}]' comment by itself; the runtime derives and "
                    "restores that comment automatically only once a real call with this "
                    "literal label exists."
                )
            if f"# STIMULUS [{label}]" not in verifier_source:
                errors.append(f"Stimulus {label!r} needs a # STIMULUS [{label}] comment")
            label_driven_channels: set[str] = set()
            label_collected_channels: set[str] = set()
            label_transport_driven_channels: set[str] = set()
            label_transport_collected_channels: set[str] = set()
            record_node = record_nodes.get(label)
            if record_node is not None:
                record_function = enclosing_function(record_node)
                if record_function is not None:
                    prior_record_line = max(
                        (
                            other.lineno
                            for other in record_nodes.values()
                            if other is not record_node
                            and enclosing_function(other) is record_function
                            and other.lineno < record_node.lineno
                        ),
                        default=record_function.lineno,
                    )
                    required_loops = enclosing_loops(record_node)
                    for function_name, line, loops, channel, kind in transfer_events:
                        if (
                            function_name != record_function.name
                            or not (prior_record_line < line < record_node.lineno)
                            or not required_loops.issubset(loops)
                        ):
                            continue
                        if kind.startswith("driver"):
                            label_transport_driven_channels.add(channel)
                        if kind.startswith("collector"):
                            label_transport_collected_channels.add(channel)
                        if kind == "driver":
                            label_driven_channels.add(channel)
                        if kind == "collector":
                            label_collected_channels.add(channel)
                    for function_name, start_line, end_line, channel, kind in active_transfer_intervals:
                        if (
                            function_name != record_function.name
                            or not (start_line < record_node.lineno < end_line)
                        ):
                            continue
                        if kind.startswith("driver"):
                            label_transport_driven_channels.add(channel)
                        if kind.startswith("collector"):
                            label_transport_collected_channels.add(channel)
            errors.extend(
                _missing_claimed_channel_drives(
                    tree, label=label, targets=item["targets"],
                    interface_contract=interface_contract,
                    tool_owned_channels=(
                        label_transport_driven_channels
                        | label_transport_collected_channels
                    ),
                )
            )
            claimed_operations = {
                parts[1]
                for target in item["targets"]
                if len(parts := target.split(".")) >= 3 and parts[0] == "operation"
            }
            recorded_operations = record_operations.get(label, set())
            if code_owned_operation_names and recorded_operations != claimed_operations:
                errors.append(
                    f"Stimulus {label!r} operation attribution must exactly match its "
                    "coverage intent; "
                    f"missing_record_operations={sorted(claimed_operations - recorded_operations)}, "
                    f"unexpected_record_operations={sorted(recorded_operations - claimed_operations)}. "
                    "A protocol/error/reset-only scenario must use operations=(). Move "
                    "an operation coverage target to a fully accepted, completed, and "
                    "drained legal job before naming it in operations=(...)."
                )
            if claimed_operations:
                shapes = record_shapes.get(label)
                if shapes is None or any(shape is None for shape in shapes):
                    errors.append(
                        f"Stimulus {label!r} claims operation coverage for "
                        f"{sorted(claimed_operations)} but its checked record does not "
                        "use statically auditable dict mappings for stimulus, expected, "
                        "and observed. Pass literal top-level dicts at the wrapper call "
                        "so the deterministic tool can prove canonical operation I/O "
                        "binding; values inside those dicts may be variables."
                    )
                else:
                    stimulus_shape, expected_shape, observed_shape = shapes
                    assert stimulus_shape is not None
                    assert expected_shape is not None
                    assert observed_shape is not None
                    for operation_name in sorted(claimed_operations):
                        required_io = operation_io.get(operation_name)
                        if required_io is None:
                            continue
                        required_inputs, required_outputs = required_io
                        # Legacy contracts may identify an operation family without
                        # declaring canonical data-object I/O.  There is no exact
                        # field mapping to prove in that case; runtime/LLM checks
                        # remain responsible until Architect metadata is available.
                        if not required_inputs or not required_outputs:
                            continue
                        missing_inputs = sorted(required_inputs - set(stimulus_shape))
                        missing_expected = sorted(required_outputs - set(expected_shape))
                        missing_observed = sorted(required_outputs - set(observed_shape))
                        extra_expected = sorted(set(expected_shape) - required_outputs)
                        extra_observed = sorted(set(observed_shape) - required_outputs)
                        if (
                            missing_inputs
                            or missing_expected
                            or missing_observed
                            or extra_expected
                            or extra_observed
                        ):
                            errors.append(
                                f"Stimulus {label!r} claims operation {operation_name!r} "
                                "but its central golden record does not isolate canonical data "
                                f"objects: missing_stimulus_inputs={missing_inputs}, "
                                f"missing_expected_outputs={missing_expected}, "
                                f"missing_observed_outputs={missing_observed}, "
                                f"extra_expected_fields={extra_expected}, "
                                f"extra_observed_fields={extra_observed}. Record "
                                "the complete accepted operation inputs and the complete "
                                "golden/observed DUT outputs using the exact Architect "
                                "data-object field names. Keep accepted/error/completion and "
                                "other protocol/status checks in their dedicated assertions; "
                                "mixing them into central golden equality can reject a correct "
                                "operation because they have different event timing."
                            )
                collector_used = any(
                    isinstance(candidate, ast.Call)
                    and isinstance(candidate.func, ast.Name)
                    and candidate.func.id
                    in {
                        "_contract_collect_protocol_transfers",
                        "_contract_collect_protocol_field_values",
                    }
                    for candidate in ast.walk(tree)
                )
                loaded_dut_signals = {
                    candidate.value.attr
                    for candidate in ast.walk(tree)
                    if isinstance(candidate, ast.Attribute)
                    and candidate.attr == "value"
                    and isinstance(candidate.value, ast.Attribute)
                    and isinstance(candidate.value.value, ast.Name)
                    and candidate.value.value.id == "dut"
                    and isinstance(candidate.ctx, ast.Load)
                }
                for operation_name in sorted(claimed_operations):
                    required_signals = operation_output_signals.get(operation_name, set())
                    if (
                        required_signals
                        and not collector_used
                        and not (required_signals & loaded_dut_signals)
                    ):
                        errors.append(
                            f"Stimulus {label!r} claims operation {operation_name!r} "
                            "but the TB never reads any role-bound DUT output payload; "
                            f"required_output_signals={sorted(required_signals)}. "
                            "Collect accepted output transfers from the DUT before the "
                            "central golden record."
                        )
                    if operation_name in code_owned_operation_names:
                        missing_drivers = sorted(
                            operation_input_channels.get(operation_name, set())
                            - label_driven_channels
                        )
                        missing_collectors = sorted(
                            operation_output_channels.get(operation_name, set())
                            - label_collected_channels
                        )
                        missing_job_starts = sorted(
                            operation_job_start_channels.get(operation_name, set())
                            - label_driven_channels
                        )
                        if missing_drivers or missing_collectors or missing_job_starts:
                            errors.append(
                                f"Checked stimulus {label!r} for known operation "
                                f"{operation_name!r} must use the tool-owned role-bound "
                                "transfer primitives for every logical I/O channel in "
                                "this record's own execution segment and, when the record "
                                "is looped, inside that same loop iteration; "
                                f"missing_driver_channels={missing_drivers}, "
                                f"missing_collector_channels={missing_collectors}, "
                                f"missing_job_start_channels={missing_job_starts}. "
                                "Resolve each channel with "
                                "_contract_protocol_channel('contract_ready_valid', "
                                "'<exact_channel>'), submit all logical scalar elements "
                                "with _contract_drive_protocol_field_values, and collect "
                                "every accepted scalar result with "
                                "_contract_collect_protocol_field_values. These wrappers "
                                "own beat packing/unpacking; do not cast the raw beat dict. "
                                "Drive one accepted command scalar on every listed job-start "
                                "channel before sending that job's operation inputs. Empty "
                                "values/count=0 calls intentionally receive no credit."
                            )

        source_lines = verifier_source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            preceding = source_lines[node.lineno - 2].strip() if node.lineno >= 2 else ""
            match = re.fullmatch(
                r"# (?:LLM-GENERATED )?(OPERATION|PROTOCOL) ASSERTION \[([^\]]+)\]",
                preceding,
            )
            if not match:
                errors.append(
                    f"Every Verifier-authored assert needs a feature comment immediately above it; line {node.lineno}"
                )
                continue
            assertion_kind, feature_id = match.groups()
            if assertion_kind == "OPERATION" and feature_id.startswith("operation."):
                llm_operation_feature_comments.add(feature_id)
            if feature_id in pipeline_owned_operation_features:
                errors.append(
                    f"Verifier must not duplicate pipeline-owned catalog assertion "
                    f"{feature_id!r}; only taxonomy-missing feature assertions "
                    "belong in the LLM section"
                )

    for source_index, source in enumerate(support_sources, start=len(sources)):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # Python syntax diagnostics for support files are reported by the
            # Verifier's ordinary source validation with the exact filename.
            continue
        errors.extend(
            _invalid_protocol_evidence_record_accesses(
                tree,
                source_index,
                captured_signal_names,
                support_trace_parameter_hints,
            )
        )

    unknown_targets = sorted(declared_targets - required_obligations)
    missing_targets = sorted(
        required_obligations - set(code_owned_obligations) - declared_targets
    )
    if unknown_targets or missing_targets:
        errors.append(
            "Stimulus coverage intent must target every exact coverage obligation; "
            f"missing={missing_targets}, unknown={unknown_targets}"
        )
    if used_labels != known_labels:
        errors.append(
            "STIMULUS_COVERAGE_INTENTS labels must match "
            "_contract_record_checked_stimulus labels; "
            f"unused={sorted(known_labels - used_labels)}, undeclared={sorted(used_labels - known_labels)}"
        )
    if architecture_contract is not None:
        if (
            pipeline_owned_operation_features
            and has_complete_operation_io
            and randomized_transactions_minimum > 0
            and statically_proven_randomized_records < randomized_transactions_minimum
        ):
            errors.append(
                "Catalog operation verification cannot statically prove the required "
                f"{randomized_transactions_minimum} randomized checked DUT transactions; "
                f"proven_maximum={statically_proven_randomized_records}, "
                f"conditional_or_dynamic_calls={unprovable_randomized_records}. Put the "
                "literal stimulus_kind='randomized' checked-record call directly and "
                "unconditionally inside a literal for range(N) loop after each completed "
                "DUT observation. Metadata randomized_test_count is not execution evidence."
            )
        elif pipeline_owned_operation_features and "randomized" not in stimulus_kinds:
            errors.append(
                "Catalog operation verification has no literal 'randomized' "
                "_contract_record_checked_stimulus call. Generating random vectors "
                "while recording them as 'directed' cannot satisfy the tool-owned "
                "randomized transaction minimum. Record each completed randomized "
                "DUT transaction inside its loop with stimulus_kind='randomized'; "
                "coverage feedback will report the remaining exact count."
            )
        missing_llm_features = sorted(
            required_llm_operation_features - llm_operation_feature_comments
        )
        unknown_llm_features = sorted(
            llm_operation_feature_comments - required_llm_operation_features
        )
        if missing_llm_features or unknown_llm_features:
            errors.append(
                "Verifier-authored operation assertion feature comments must match "
                "the exact taxonomy-missing contract feature set; "
                f"missing={missing_llm_features}, unknown={unknown_llm_features}"
            )
    if errors:
        # AST walks can reach the same malformed construct through overlapping
        # conservative analyses.  One precise finding is more useful to the
        # Verifier than repeated copies of identical feedback.
        raise ValueError("; ".join(dict.fromkeys(errors)))


def _static_randomized_record_count(
    tree: ast.AST, parents: Mapping[ast.AST, ast.AST]
) -> tuple[int, list[int]]:
    """Return a conservative proven execution count for randomized records.

    Only unconditional calls in literal ``for range(...)`` loops are counted by
    their loop cardinality. Conditional, while, async-for, and dynamic-range
    placements are deliberately unprovable and must fall back to runtime coverage.
    """

    def range_count(loop: ast.For) -> int | None:
        iterator = loop.iter
        if not (
            isinstance(iterator, ast.Call)
            and isinstance(iterator.func, ast.Name)
            and iterator.func.id == "range"
            and not iterator.keywords
            and 1 <= len(iterator.args) <= 3
        ):
            return None
        values: list[int] = []
        for argument in iterator.args:
            try:
                value = ast.literal_eval(argument)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                return None
            if not isinstance(value, int):
                return None
            values.append(value)
        try:
            return len(range(*values))
        except ValueError:
            return None

    total = 0
    unprovable: list[int] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_contract_record_checked_stimulus"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "randomized"
        ):
            continue
        multiplier = 1
        provable = True
        child: ast.AST = node
        while child in parents:
            parent = parents[child]
            if isinstance(parent, ast.For):
                count = range_count(parent)
                if count is None:
                    provable = False
                    break
                multiplier *= count
            elif isinstance(parent, (ast.While, ast.AsyncFor, ast.If, ast.IfExp)):
                provable = False
                break
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                break
            child = parent
        if provable:
            total += multiplier
        else:
            unprovable.append(node.lineno)
    return total, unprovable


def _missing_claimed_channel_drives(
    tree: ast.AST,
    *,
    label: str,
    targets: list[str],
    interface_contract: Mapping[str, Any] | None,
    tool_owned_channels: set[str] | None = None,
) -> list[str]:
    """Prove when a claimed interface scenario never drives its DUT-side control.

    Interface coverage points and signal bindings are code-owned.  A label cannot
    honestly claim a ready/valid channel when its test file never asserts the
    control signal driven into the DUT (``valid`` for an input channel, ``ready``
    for an output channel).  This intentionally checks only a strong, static fact;
    temporal transfer/stall behavior remains measured by the runtime monitor.
    """

    if not isinstance(interface_contract, Mapping):
        return []
    tool_owned_channels = tool_owned_channels or set()
    channels = {
        re.sub(r"[^a-zA-Z0-9_]+", "_", str(item.get("name", ""))).strip("_").lower(): item
        for item in interface_contract.get("channels", [])
        if isinstance(item, Mapping)
    }
    signals = [
        item for item in interface_contract.get("signals", []) if isinstance(item, Mapping)
    ]
    claimed = {
        match.group(1)
        for target in targets
        if (match := re.fullmatch(r"channel\.([^.]+)\.(?:handshake_states|stall_stability)", target))
    }
    if not claimed:
        return []

    asserted: set[str] = set()
    helper_drives: dict[str, set[int]] = {}
    helper_parameters: dict[str, list[ast.arg]] = {}
    helper_functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    dynamic_keyword_drivers: set[str] = set()
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        parameters = [
            *function.args.posonlyargs,
            *function.args.args,
        ]
        helper_parameters[function.name] = parameters
        helper_functions[function.name] = function
        if function.args.kwarg is not None and any(
            isinstance(target, ast.Attribute)
            and target.attr == "value"
            and isinstance(target.value, ast.Call)
            and isinstance(target.value.func, ast.Name)
            and target.value.func.id == "getattr"
            for assignment in ast.walk(function)
            if isinstance(assignment, (ast.Assign, ast.AnnAssign))
            for target in (
                assignment.targets
                if isinstance(assignment, ast.Assign)
                else [assignment.target]
            )
        ):
            dynamic_keyword_drivers.add(function.name)
        driven_indices: set[int] = set()
        for assignment in ast.walk(function):
            if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
                continue
            if isinstance(assignment.value, ast.Constant) and not bool(assignment.value.value):
                continue
            assignment_targets = (
                assignment.targets if isinstance(assignment, ast.Assign)
                else [assignment.target]
            )
            for target in assignment_targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "value"
                    and isinstance(target.value, ast.Name)
                ):
                    driven_indices.update(
                        index for index, parameter in enumerate(parameters)
                        if parameter.arg == target.value.id
                    )
        if driven_indices:
            helper_drives[function.name] = driven_indices

    # Propagate direct drives through local wrapper helpers. For example,
    # ``send_vec(..., valid_sig, ...)`` may delegate to
    # ``send_beat(..., valid_sig, ...)``, where only send_beat assigns
    # ``valid_sig.value = 1``. This fixed point remains deliberately narrow:
    # it follows only local calls and exact parameter-to-parameter bindings.
    changed = True
    while changed:
        changed = False
        for function_name, function in helper_functions.items():
            parameters = helper_parameters[function_name]
            parameter_indices = {
                parameter.arg: index for index, parameter in enumerate(parameters)
            }
            propagated = set(helper_drives.get(function_name, set()))
            for call in ast.walk(function):
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                    continue
                callee = call.func.id
                callee_parameters = helper_parameters.get(callee, [])
                if callee in dynamic_keyword_drivers:
                    for keyword in call.keywords:
                        if keyword.arg is not None or not isinstance(keyword.value, ast.Dict):
                            continue
                        for key_node, value_node in zip(
                            keyword.value.keys, keyword.value.values, strict=True
                        ):
                            if (
                                isinstance(key_node, ast.Name)
                                and key_node.id in parameter_indices
                                and not (
                                    isinstance(value_node, ast.Constant)
                                    and not bool(value_node.value)
                                )
                            ):
                                propagated.add(parameter_indices[key_node.id])
                for driven_index in helper_drives.get(callee, set()):
                    argument: ast.expr | None = None
                    if driven_index < len(call.args):
                        argument = call.args[driven_index]
                    elif driven_index < len(callee_parameters):
                        parameter_name = callee_parameters[driven_index].arg
                        argument = next(
                            (
                                keyword.value
                                for keyword in call.keywords
                                if keyword.arg == parameter_name
                            ),
                            None,
                        )
                    if isinstance(argument, ast.Name) and argument.id in parameter_indices:
                        propagated.add(parameter_indices[argument.id])
            if propagated != helper_drives.get(function_name, set()):
                helper_drives[function_name] = propagated
                changed = True
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            for index in helper_drives.get(node.func.id, set()):
                if index >= len(node.args):
                    continue
                argument = node.args[index]
                if (
                    isinstance(argument, ast.Attribute)
                    and isinstance(argument.value, ast.Name)
                    and argument.value.id == "dut"
                ):
                    asserted.add(argument.attr)
                elif isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    asserted.add(argument.value)
            if node.func.id in dynamic_keyword_drivers:
                for keyword in node.keywords:
                    if (
                        keyword.arg is not None
                        and not (
                            isinstance(keyword.value, ast.Constant)
                            and not bool(keyword.value.value)
                        )
                    ):
                        asserted.add(keyword.arg)
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and not bool(value.value):
            continue
        assignment_targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in assignment_targets:
            # dut.<signal>.value = 1 (or any non-literal expression that may assert it)
            if not (
                isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Attribute)
            ):
                continue
            asserted.add(target.value.attr)

    errors: list[str] = []
    for safe_channel in sorted(claimed):
        channel = channels.get(safe_channel)
        if not isinstance(channel, Mapping):
            continue
        channel_name = str(channel.get("name", ""))
        if channel_name in tool_owned_channels:
            continue
        direction = str(channel.get("direction", ""))
        driven_role = "valid" if direction == "input" else "ready" if direction == "output" else ""
        driven_signals = {
            str(signal.get("name", ""))
            for signal in signals
            if signal.get("channel") == channel_name
            and signal.get("role") == driven_role
            and signal.get("direction") == "input"
        }
        if driven_signals and asserted.isdisjoint(driven_signals):
            errors.append(
                f"Stimulus {label!r} claims channel {channel_name!r} coverage but "
                f"the test source never drives its DUT-input {driven_role} signal "
                f"asserted ({sorted(driven_signals)}); add real channel stimulus "
                "and await the observed handshake before recording the checked stimulus"
            )
    return errors


def _unadvanced_checked_stimulus_records(
    tree: ast.AST, source_index: int, source: str
) -> list[str]:
    """Reject a second ledger entry with no opportunity for DUT time to advance.

    This is intentionally local to a straight-line statement block. Branches and
    loops are inspected independently, so the check does not guess execution order.
    A genuinely new scenario must await DUT progress before it can be checked.
    """

    errors: list[str] = []
    try:
        targets_by_label = {
            item["label"]: item["targets"]
            for item in extract_stimulus_coverage_intents(source)
        }
    except ValueError:
        # The caller reports malformed intents separately; this check can still
        # reject an impossible second record without relying on that metadata.
        targets_by_label = {}

    def record_call(statement: ast.stmt) -> ast.Call | None:
        value = (
            statement.value
            if isinstance(statement, (ast.Expr, ast.Assign, ast.AnnAssign))
            else None
        )
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "_contract_record_checked_stimulus"
        ):
            return value
        return None

    def label(call: ast.Call) -> str:
        for keyword in call.keywords:
            if keyword.arg == "label" and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
        return "<unknown>"

    def scan(
        body: list[ast.stmt], incoming: set[ast.Call] | None = None
    ) -> set[ast.Call]:
        previous = set(incoming or ())
        for statement in body:
            call = record_call(statement)
            if call is not None:
                for prior in sorted(previous, key=lambda item: item.lineno):
                    targets = targets_by_label.get(label(call), [])
                    target_detail = (
                        f" Its declared targets are {targets!r}." if targets else ""
                    )
                    errors.append(
                        f"Stimulus {label(call)!r} records a new checked stimulus at "
                        f"source={source_index}, line={call.lineno} with no await since "
                        f"stimulus {label(prior)!r} at line={prior.lineno}; "
                        "this reuses the prior DUT observation. Add real DUT-driven "
                        "traffic and await its observation before recording this "
                        "later label; do not reuse the earlier expected/observed values."
                        + target_detail
                    )
                previous = {call}
                continue
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                scan(statement.body)
                continue
            if any(isinstance(node, ast.Await) for node in ast.walk(statement)):
                # Await can appear in a control-flow test (for example
                # ``if await handshake():``), so clear incoming observations before
                # descending into that statement's branches or loop body.
                previous.clear()
            if isinstance(statement, ast.If):
                body_tail = scan(statement.body, previous)
                else_tail = scan(statement.orelse, previous) if statement.orelse else set(previous)
                previous = body_tail | else_tail
                continue
            if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                body_tail = scan(statement.body, previous)
                executes_at_least_once = (
                    isinstance(statement, ast.While)
                    and isinstance(statement.test, ast.Constant)
                    and statement.test.value is True
                )
                loop_tail = (
                    body_tail
                    if executes_at_least_once
                    else set(previous) | body_tail  # other loops may execute zero times
                )
                previous = scan(statement.orelse, loop_tail) if statement.orelse else loop_tail
                continue
            if isinstance(statement, (ast.With, ast.AsyncWith)):
                previous = scan(statement.body, previous)
                continue
            if isinstance(statement, ast.Try):
                tails = [scan(statement.body, previous)]
                tails.extend(scan(handler.body, previous) for handler in statement.handlers)
                merged = set().union(*tails)
                if statement.orelse:
                    merged = scan(statement.orelse, merged)
                if statement.finalbody:
                    merged = scan(statement.finalbody, merged)
                previous = merged
                continue
        return previous

    scan(getattr(tree, "body", []))
    return errors


def _preawaited_protocol_evidence_stimulus(
    tree: ast.AST, source_index: int
) -> list[str]:
    """Reject consuming a stimulus before the concurrent observer starts."""

    errors: list[str] = []
    for call in ast.walk(tree):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "capture_protocol_event_trace"
        ):
            continue
        stimulus = call.args[3] if len(call.args) >= 4 else next(
            (
                keyword.value
                for keyword in call.keywords
                if keyword.arg == "stimulus"
            ),
            None,
        )
        if isinstance(stimulus, ast.Await):
            errors.append(
                "capture_protocol_event_trace must receive the unawaited stimulus "
                "coroutine so its observer starts before DUT traffic; "
                f"source={source_index}, line={call.lineno}. Remove await from the "
                "stimulus argument; await only capture_protocol_event_trace itself"
            )
    return errors


def _dut_writes_after_protocol_evidence_capture(
    tree: ast.AST, source_index: int
) -> list[str]:
    """Reject DUT writes before leaving capture's final ReadOnly phase.

    ``capture_protocol_event_trace`` deliberately finishes its observer after a
    ReadOnly sample.  Cocotb resumes the caller in that same simulator phase, so
    a direct ``dut.<signal>.value = ...`` before another await is illegal.
    """

    errors: list[str] = []

    def statement_roots(statement: ast.stmt) -> list[ast.AST]:
        if isinstance(statement, (ast.If, ast.While)):
            return [statement.test]
        if isinstance(statement, (ast.For, ast.AsyncFor)):
            return [statement.iter]
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            return [item.context_expr for item in statement.items]
        if isinstance(
            statement,
            (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            return []
        return [statement]

    def is_capture_await(node: ast.AST) -> bool:
        return bool(
            isinstance(node, ast.Await)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "capture_protocol_event_trace"
        )

    def awaited_call_name(node: ast.AST) -> str:
        if not isinstance(node, ast.Await) or not isinstance(node.value, ast.Call):
            return ""
        function = node.value.func
        if isinstance(function, ast.Name):
            return function.id
        if isinstance(function, ast.Attribute):
            return function.attr
        return ""

    def dut_write_signals(statement: ast.stmt) -> set[str]:
        names: set[str] = set()
        for assignment in (
            [statement]
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            else []
        ):
            targets = (
                assignment.targets
                if isinstance(assignment, ast.Assign)
                else [assignment.target]
            )
            for target in targets:
                if not (
                    isinstance(target, ast.Attribute)
                    and target.attr == "value"
                    and isinstance(target.value, ast.Attribute)
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "dut"
                ):
                    continue
                names.add(target.value.attr)
        return names

    def scan(statements: Sequence[ast.stmt], read_only_after_capture: bool = False) -> None:
        read_only = read_only_after_capture
        for statement in statements:
            roots = statement_roots(statement)
            capture_awaits = [
                node
                for root in roots
                for node in ast.walk(root)
                if is_capture_await(node)
            ]
            awaits = [
                node
                for root in roots
                for node in ast.walk(root)
                if isinstance(node, ast.Await)
            ]
            if read_only:
                writes = dut_write_signals(statement)
                if writes:
                    errors.append(
                        "DUT input is written immediately after awaited "
                        "capture_protocol_event_trace returns in Cocotb's ReadOnly "
                        f"phase; source={source_index}, line={statement.lineno}, "
                        f"signals={sorted(writes)}. Await a writable scheduling "
                        "boundary such as FallingEdge(clock) or Timer(...) before "
                        "the next DUT assignment"
                    )
                    read_only = False
                elif capture_awaits:
                    errors.append(
                        "A new capture_protocol_event_trace stimulus is started "
                        "immediately after a previous capture returned in Cocotb's "
                        f"ReadOnly phase; source={source_index}, "
                        f"line={capture_awaits[0].lineno}. Await a writable scheduling "
                        "boundary such as FallingEdge(clock) or Timer(...) before "
                        "starting the next capture, because its stimulus coroutine "
                        "may write DUT inputs before its first await"
                    )
                elif awaits and not all(
                    awaited_call_name(node)
                    in {"ClockCycles", "Edge", "FallingEdge", "ReadWrite", "RisingEdge", "Timer"}
                    for node in awaits
                ):
                    errors.append(
                        "A coroutine is awaited immediately after "
                        "capture_protocol_event_trace returned in Cocotb's ReadOnly "
                        f"phase; source={source_index}, line={statement.lineno}, "
                        f"calls={sorted(filter(None, (awaited_call_name(node) for node in awaits)))}. "
                        "The coroutine may write DUT inputs before its first await. "
                        "Await a writable scheduling boundary such as FallingEdge(clock) "
                        "or Timer(...) before calling another driver or helper"
                    )
                    read_only = False
                elif awaits:
                    read_only = False
            if capture_awaits:
                read_only = True
            for field in ("body", "orelse", "finalbody"):
                nested = getattr(statement, field, None)
                if isinstance(nested, list):
                    scan(nested, read_only)
            handlers = getattr(statement, "handlers", None)
            if isinstance(handlers, list):
                for handler in handlers:
                    scan(handler.body, read_only)

    for definition in ast.walk(tree):
        if isinstance(definition, ast.AsyncFunctionDef):
            scan(definition.body)
    return sorted(set(errors))


def _async_call_is_consumed(
    call: ast.Call, parents: Mapping[ast.AST, ast.AST]
) -> bool:
    """Return true when an async helper is awaited directly or by evidence capture.

    ``capture_protocol_event_trace`` deliberately accepts an unawaited stimulus
    coroutine so it can start its observer before awaiting the stimulus.  Treating
    that fourth argument as a dropped coroutine contradicts the capture API and
    makes deterministic repair oscillate between "add await" and "remove await".
    This helper recognizes only that exact, awaited delegation boundary; arbitrary
    unawaited coroutine arguments remain invalid.
    """

    parent = parents.get(call)
    if isinstance(parent, ast.Await):
        return True

    capture_call: ast.Call | None = None
    if isinstance(parent, ast.Call):
        capture_call = parent
        positional_stimulus = (
            capture_call.args[3] if len(capture_call.args) >= 4 else None
        )
        if positional_stimulus is not call:
            return False
    elif isinstance(parent, ast.keyword) and parent.arg == "stimulus":
        candidate = parents.get(parent)
        if isinstance(candidate, ast.Call):
            capture_call = candidate
        else:
            return False
    else:
        return False

    return bool(
        isinstance(capture_call.func, ast.Name)
        and capture_call.func.id == "capture_protocol_event_trace"
        and isinstance(parents.get(capture_call), ast.Await)
    )


def _invalid_protocol_evidence_record_accesses(
    tree: ast.AST,
    source_index: int,
    allowed_signal_names: set[str] | frozenset[str] | None = None,
    function_parameter_traces: Mapping[str, Mapping[int, str]] | None = None,
) -> list[str]:
    """Reject top-level fields absent from reusable protocol trace records."""

    allowed = {
        "transaction_trace": {
            "cycle", "event", "signals", "outstanding_before", "outstanding_after"
        },
        "cycle_trace": {"cycle", "signals", "events"},
    }
    transaction_event_values = {
        "accepted",
        "success",
        "error",
        "completed",
        "cancelled",
    }
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    # Verifier-authored reference files often hide dictionary access behind a
    # small helper such as ``_get(record, key, default=0)``.  Treat that helper
    # exactly like ``record.get(key)``; otherwise an invented trace field can
    # silently evaluate to the helper's default and pass structural review.
    # Only recognize helpers whose own AST proves that one parameter indexes or
    # calls ``get`` on another parameter, so unrelated functions that merely
    # accept a record and a string are not over-classified as accessors.
    helper_accessors: dict[str, tuple[int, int]] = {}
    for definition in ast.walk(tree):
        if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        positional_parameters = [
            *definition.args.posonlyargs,
            *definition.args.args,
        ]
        parameter_positions = {
            parameter.arg: index
            for index, parameter in enumerate(positional_parameters)
        }
        for node in ast.walk(definition):
            record_parameter: str | None = None
            key_parameter: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in parameter_positions
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in parameter_positions
            ):
                record_parameter = node.func.value.id
                key_parameter = node.args[0].id
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in parameter_positions
                and isinstance(node.slice, ast.Name)
                and node.slice.id in parameter_positions
            ):
                record_parameter = node.value.id
                key_parameter = node.slice.id
            if record_parameter is not None and key_parameter is not None:
                helper_accessors[definition.name] = (
                    parameter_positions[record_parameter],
                    parameter_positions[key_parameter],
                )
                break
    parameter_traces = function_parameter_traces or {}
    trace_loops: list[tuple[str, str, ast.AST]] = []
    for loop in ast.walk(tree):
        if isinstance(loop, ast.For):
            target, iterator, scope = loop.target, loop.iter, loop
        elif isinstance(loop, ast.comprehension):
            target, iterator = loop.target, loop.iter
            scope = parents.get(loop, loop)
        else:
            continue
        iterator_name: str | None = None
        record_target: ast.Name | None = target if isinstance(target, ast.Name) else None
        if isinstance(iterator, ast.Name):
            iterator_name = iterator.id
        elif (
            isinstance(iterator, ast.Call)
            and isinstance(iterator.func, ast.Name)
            and iterator.func.id == "enumerate"
            and iterator.args
            and isinstance(iterator.args[0], ast.Name)
        ):
            iterator_name = iterator.args[0].id
            if (
                isinstance(target, (ast.Tuple, ast.List))
                and len(target.elts) == 2
                and isinstance(target.elts[1], ast.Name)
            ):
                record_target = target.elts[1]
        if record_target is None or iterator_name is None:
            continue
        trace_name = iterator_name if iterator_name in allowed else None
        if trace_name is None:
            current: ast.AST = scope
            definition: ast.FunctionDef | ast.AsyncFunctionDef | None = None
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    definition = current
                    break
            if definition is not None:
                positional_parameters = [
                    *definition.args.posonlyargs,
                    *definition.args.args,
                ]
                for index, parameter in enumerate(positional_parameters):
                    if parameter.arg == iterator_name:
                        trace_name = parameter_traces.get(definition.name, {}).get(index)
                        break
        if trace_name in allowed:
            trace_loops.append((record_target.id, trace_name, scope))

    errors: list[str] = []
    for record_name, trace_name, scope in trace_loops:
        signal_aliases: set[str] = set()
        event_aliases: set[str] = set()
        for assignment in ast.walk(scope):
            if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
                continue
            value = assignment.value
            is_signal_mapping = (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == "get"
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == record_name
                and value.args
                and isinstance(value.args[0], ast.Constant)
                and value.args[0].value == "signals"
            ) or (
                isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == record_name
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "signals"
            )
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            target_names = {
                target.id for target in targets if isinstance(target, ast.Name)
            }
            if is_signal_mapping:
                signal_aliases.update(target_names)

            is_event_access = (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == "get"
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == record_name
                and value.args
                and isinstance(value.args[0], ast.Constant)
                and value.args[0].value == "event"
            ) or (
                isinstance(value, ast.Subscript)
                and isinstance(value.value, ast.Name)
                and value.value.id == record_name
                and isinstance(value.slice, ast.Constant)
                and value.slice.value == "event"
            )
            if is_event_access:
                event_aliases.update(target_names)

        def is_transaction_event_access(expression: ast.AST) -> bool:
            if trace_name != "transaction_trace":
                return False
            if isinstance(expression, ast.Name):
                return expression.id in event_aliases
            if (
                isinstance(expression, ast.Call)
                and isinstance(expression.func, ast.Attribute)
                and expression.func.attr == "get"
                and isinstance(expression.func.value, ast.Name)
                and expression.func.value.id == record_name
                and expression.args
                and isinstance(expression.args[0], ast.Constant)
            ):
                return expression.args[0].value == "event"
            if (
                isinstance(expression, ast.Subscript)
                and isinstance(expression.value, ast.Name)
                and expression.value.id == record_name
                and isinstance(expression.slice, ast.Constant)
            ):
                return expression.slice.value == "event"
            if (
                isinstance(expression, ast.Call)
                and isinstance(expression.func, ast.Name)
                and expression.func.id in helper_accessors
            ):
                record_position, key_position = helper_accessors[expression.func.id]
                return bool(
                    len(expression.args) > max(record_position, key_position)
                    and isinstance(expression.args[record_position], ast.Name)
                    and expression.args[record_position].id == record_name
                    and isinstance(expression.args[key_position], ast.Constant)
                    and expression.args[key_position].value == "event"
                )
            return False

        def literal_strings(expression: ast.AST) -> set[str]:
            if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
                return {expression.value}
            if isinstance(expression, (ast.List, ast.Tuple, ast.Set)):
                return {
                    item.value
                    for item in expression.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                }
            return set()

        for node in ast.walk(scope):
            key: str | None = None
            signal_key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == record_name
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == record_name
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in helper_accessors
            ):
                record_position, key_position = helper_accessors[node.func.id]
                if (
                    len(node.args) > max(record_position, key_position)
                    and isinstance(node.args[record_position], ast.Name)
                    and node.args[record_position].id == record_name
                    and isinstance(node.args[key_position], ast.Constant)
                    and isinstance(node.args[key_position].value, str)
                ):
                    key = node.args[key_position].value
                elif (
                    len(node.args) > max(record_position, key_position)
                    and isinstance(node.args[record_position], ast.Name)
                    and node.args[record_position].id in signal_aliases
                    and isinstance(node.args[key_position], ast.Constant)
                    and isinstance(node.args[key_position].value, str)
                ):
                    signal_key = node.args[key_position].value
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in signal_aliases
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                signal_key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in signal_aliases
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                signal_key = node.slice.value
            if key is not None and key not in allowed[trace_name]:
                signal_guidance = ""
                if allowed_signal_names:
                    candidates = get_close_matches(
                        key, sorted(allowed_signal_names), n=3, cutoff=0.45
                    )
                    signal_guidance = (
                        " Actual frozen-contract signal candidates: "
                        + repr(candidates)
                        + "."
                        if candidates
                        else " This alias is not a captured DUT signal name."
                    )
                errors.append(
                    f"{trace_name} record has no top-level field {key!r}; "
                    f"source={source_index}, line={node.lineno}. Use record['event'] "
                    "for accepted/completed transaction outcomes, record['events'] "
                    "for cycle predicates, or record['signals'][<exact frozen-contract "
                    "signal name>] for sampled DUT signals; do not move a semantic "
                    f"alias into record['signals'] under the same invented key."
                    f"{signal_guidance}"
                )
            if (
                signal_key is not None
                and allowed_signal_names is not None
                and signal_key not in allowed_signal_names
            ):
                errors.append(
                    f"{trace_name} record['signals'] has no captured DUT signal "
                    f"{signal_key!r}; source={source_index}, line={node.lineno}. "
                    "Use only frozen-contract signal names in record['signals']; "
                    "derive semantic events and correlation state from the canonical "
                    "event/cycle timeline rather than inventing helper fields"
                )
            if isinstance(node, ast.Compare) and trace_name == "transaction_trace":
                operands = [node.left, *node.comparators]
                for left, right in zip(operands, operands[1:]):
                    event_side: ast.AST | None = None
                    literal_side: ast.AST | None = None
                    if is_transaction_event_access(left):
                        event_side, literal_side = left, right
                    elif is_transaction_event_access(right):
                        event_side, literal_side = right, left
                    if event_side is None or literal_side is None:
                        continue
                    invalid_values = sorted(
                        literal_strings(literal_side) - transaction_event_values
                    )
                    if invalid_values:
                        errors.append(
                            "transaction_trace record['event'] uses unsupported "
                            f"literal value(s) {invalid_values!r}; source={source_index}, "
                            f"line={node.lineno}. The reusable trace emits only "
                            f"{sorted(transaction_event_values)!r}; use 'accepted' for "
                            "request acceptance and 'success'/'error'/'completed' for "
                            "response outcomes instead of inventing compound event names"
                        )
    return sorted(set(errors))


def _called_protocol_trace_parameter_hints(
    tree: ast.AST,
) -> dict[str, dict[int, str]]:
    """Infer trace-typed arguments passed from tests into support helpers.

    Extension assertions commonly filter ``transaction_trace`` into local
    ``accepted``/``retired`` lists before passing those records to a reference
    oracle. Preserve the canonical record type across that call boundary so an
    oracle cannot read invented fields merely because the list was renamed.
    """

    hints: dict[str, dict[int, str]] = {}
    for definition in ast.walk(tree):
        if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        aliases: dict[str, str] = {}
        for parameter in [*definition.args.posonlyargs, *definition.args.args]:
            if parameter.arg.endswith("transaction_trace"):
                aliases[parameter.arg] = "transaction_trace"
            elif parameter.arg.endswith("cycle_trace"):
                aliases[parameter.arg] = "cycle_trace"

        changed = True
        while changed:
            changed = False
            for assignment in ast.walk(definition):
                if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
                    continue
                value = assignment.value
                trace_name: str | None = None
                if isinstance(value, ast.Name):
                    trace_name = aliases.get(value.id)
                elif isinstance(value, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                    iterator_names = [
                        generator.iter.id
                        for generator in value.generators
                        if isinstance(generator.iter, ast.Name)
                    ]
                    iterator_types = {
                        aliases[name] for name in iterator_names if name in aliases
                    }
                    if len(iterator_types) == 1:
                        trace_name = next(iter(iterator_types))
                if trace_name is None:
                    continue
                targets = (
                    assignment.targets
                    if isinstance(assignment, ast.Assign)
                    else [assignment.target]
                )
                for target in targets:
                    if isinstance(target, ast.Name) and aliases.get(target.id) != trace_name:
                        aliases[target.id] = trace_name
                        changed = True

        for call in ast.walk(definition):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
            ):
                continue
            for index, argument in enumerate(call.args):
                if not isinstance(argument, ast.Name) or argument.id not in aliases:
                    continue
                trace_name = aliases[argument.id]
                existing = hints.setdefault(call.func.id, {}).get(index)
                if existing is None or existing == trace_name:
                    hints[call.func.id][index] = trace_name
                else:
                    hints[call.func.id].pop(index, None)
    return hints


def _overlapping_unqueued_command_starts(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Reject a second start while a non-queued command job is still outstanding.

    This deliberately relies on Architect-owned interface metadata: the command
    channel must contain a ``semantic_class=command`` payload and explicitly say
    that commands are not queued or are accepted only in IDLE.  A checked record
    or reset is treated as the boundary of the earlier scenario.  The check is
    intentionally conservative and only follows source-ordered events inside each
    cocotb test; it does not infer arbitrary protocol state from helper names.
    """

    contract = interface_contract or {}
    channels = {
        str(channel.get("name", "")): channel
        for channel in contract.get("channels", [])
        if isinstance(channel, Mapping) and channel.get("name")
    }
    signals = [
        signal
        for signal in contract.get("signals", [])
        if isinstance(signal, Mapping)
    ]
    command_channels = {
        str(signal.get("channel"))
        for signal in signals
        if signal.get("semantic_class") == "command" and signal.get("channel")
    }
    serialized_command_channels = {
        name
        for name in command_channels
        if isinstance(channels.get(name), Mapping)
        and (
            "no queue" in str(channels[name].get("ordering", "")).lower()
            or "only accepted in idle"
            in " ".join(
                str(channels[name].get(field, ""))
                for field in ("ordering", "backpressure")
            ).lower()
        )
    }
    command_valid_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("channel") in serialized_command_channels
        and signal.get("role") == "valid"
        and signal.get("direction") == "input"
    }
    if not command_valid_signals:
        return []

    reset_values = {
        str(signal.get("name")): str(signal.get("reset_value", "0"))
        for signal in signals
        if signal.get("role") == "reset"
        and signal.get("direction") == "input"
        and signal.get("name")
    }
    operation_output_channels = {
        name
        for name, channel in channels.items()
        if channel.get("direction") == "output" and channel.get("data_objects")
    }
    operation_output_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("channel") in operation_output_channels
        and signal.get("direction") == "output"
        and signal.get("role") in {"valid", "payload", "last"}
    }
    definitions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def dut_value_assignment(node: ast.AST) -> tuple[str, ast.AST] | None:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            return None
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "dut"
            ):
                return target.value.attr, value
        return None

    def statically_asserted(value: ast.AST) -> bool:
        try:
            return bool(ast.literal_eval(value))
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return True

    def helper_starts_command(helper: ast.AST) -> bool:
        for node in ast.walk(helper):
            assignment = dut_value_assignment(node)
            if (
                assignment is not None
                and assignment[0] in command_valid_signals
                and statically_asserted(assignment[1])
            ):
                return True
        return False

    def helper_applies_reset(helper: ast.AST) -> bool:
        for node in ast.walk(helper):
            assignment = dut_value_assignment(node)
            if assignment is None or assignment[0] not in reset_values:
                continue
            try:
                value = ast.literal_eval(assignment[1])
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                continue
            if str(value) == reset_values[assignment[0]]:
                return True
        return False

    def helper_observes_operation_output(helper: ast.AST) -> bool:
        return any(
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and node.attr == "value"
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "dut"
            and node.value.attr in operation_output_signals
            for node in ast.walk(helper)
        )

    errors: list[str] = []
    for function in tree.body if isinstance(tree, ast.Module) else []:
        if not isinstance(function, ast.AsyncFunctionDef):
            continue
        if not any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "cocotb"
            and decorator.func.attr == "test"
            for decorator in function.decorator_list
        ):
            continue

        pending_line: int | None = None
        events: list[tuple[int, int, str, str | None, bool]] = []
        for statement in function.body:
            for node in ast.walk(statement):
                assignment = dut_value_assignment(node)
                if assignment is not None:
                    signal_name, value = assignment
                    if signal_name in command_valid_signals and statically_asserted(value):
                        events.append((node.lineno, node.col_offset, "start", None, False))
                    elif signal_name in reset_values:
                        try:
                            reset_value = ast.literal_eval(value)
                        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                            pass
                        else:
                            if str(reset_value) == reset_values[signal_name]:
                                events.append((node.lineno, node.col_offset, "clear", None, False))
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                    continue
                if node.func.id == "_contract_record_checked_stimulus":
                    events.append((node.lineno, node.col_offset, "clear", None, False))
                    continue
                helper = definitions.get(node.func.id)
                if helper is None:
                    continue
                if helper_applies_reset(helper):
                    events.append((node.lineno, node.col_offset, "clear", None, False))
                if helper_starts_command(helper):
                    events.append(
                        (
                            node.lineno,
                            node.col_offset,
                            "helper_start",
                            node.func.id,
                            helper_observes_operation_output(helper),
                        )
                    )

        for line, _column, kind, helper_name, helper_completes in sorted(events):
            if kind == "clear":
                pending_line = None
            elif kind == "start":
                pending_line = line
            elif kind == "helper_start":
                if pending_line is not None:
                    errors.append(
                        f"Cocotb test {function.name!r} starts serialized command "
                        f"channel {sorted(serialized_command_channels)!r} again via "
                        f"helper {helper_name!r} at source={source_index}, line={line}, "
                        f"while the command started at line={pending_line} has no "
                        "intervening reset or completed checked-stimulus record. The "
                        "interface contract says this command is IDLE-only/no-queue, "
                        "so the helper can wait forever for ready. Remove the duplicate "
                        "command start and let one full-transaction helper own the job, "
                        "or completely feed, drain, and record the earlier job first."
                    )
                pending_line = None if helper_completes else line
    return errors


def _unrecorded_full_operation_loops(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Require one unconditional ledger record per looped full DUT operation."""

    contract = interface_contract or {}
    channels = {
        str(channel.get("name", "")): channel
        for channel in contract.get("channels", [])
        if isinstance(channel, Mapping) and channel.get("name")
    }
    signals = [
        signal
        for signal in contract.get("signals", [])
        if isinstance(signal, Mapping)
    ]
    command_channels = {
        str(signal.get("channel"))
        for signal in signals
        if signal.get("semantic_class") == "command" and signal.get("channel")
    }
    command_valid_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("channel") in command_channels
        and signal.get("role") == "valid"
        and signal.get("direction") == "input"
    }
    output_channels = {
        name
        for name, channel in channels.items()
        if channel.get("direction") == "output" and channel.get("data_objects")
    }
    output_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("channel") in output_channels
        and signal.get("direction") == "output"
        and signal.get("role") in {"valid", "payload", "last"}
    }
    if not command_valid_signals or not output_signals:
        return []

    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    definitions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def dut_value_assignment(node: ast.AST) -> tuple[str, ast.AST] | None:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            return None
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "dut"
            ):
                return target.value.attr, node.value
        return None

    def asserted_command(node: ast.AST) -> bool:
        assignment = dut_value_assignment(node)
        if assignment is None or assignment[0] not in command_valid_signals:
            return False
        try:
            return bool(ast.literal_eval(assignment[1]))
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return True

    def observes_output(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and node.attr == "value"
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "dut"
            and node.value.attr in output_signals
        )

    command_helpers = {
        name
        for name, helper in definitions.items()
        if any(asserted_command(node) for node in ast.walk(helper))
    }
    output_helpers = {
        name
        for name, helper in definitions.items()
        if any(observes_output(node) for node in ast.walk(helper))
    }

    def enclosing_cocotb_test(node: ast.AST) -> ast.AsyncFunctionDef | None:
        current = node
        while current in parents:
            current = parents[current]
            if not isinstance(current, ast.AsyncFunctionDef):
                continue
            if any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "cocotb"
                and decorator.func.attr == "test"
                for decorator in current.decorator_list
            ):
                return current
            return None
        return None

    def named_calls(node: ast.AST) -> set[str]:
        return {
            child.func.id
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }

    errors: list[str] = []
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.AsyncFor)):
            continue
        test = enclosing_cocotb_test(loop)
        if test is None:
            continue
        loop_nodes = [node for statement in loop.body for node in ast.walk(statement)]
        calls = set().union(*(named_calls(statement) for statement in loop.body))
        starts_job = any(asserted_command(node) for node in loop_nodes) or bool(
            calls & command_helpers
        )
        completes_job = any(observes_output(node) for node in loop_nodes) or bool(
            calls & output_helpers
        )
        if not starts_job or not completes_job:
            continue

        records = [
            node
            for node in loop_nodes
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_contract_record_checked_stimulus"
        ]
        conditional_lines: list[int] = []
        unconditional_records: list[ast.Call] = []
        for record in records:
            current: ast.AST = record
            conditional = False
            while current in parents and parents[current] is not loop:
                current = parents[current]
                if isinstance(current, (ast.If, ast.IfExp, ast.While, ast.Try, ast.Match)):
                    conditional = True
            if conditional:
                conditional_lines.append(record.lineno)
            else:
                unconditional_records.append(record)
        if unconditional_records:
            continue
        errors.append(
            f"Cocotb test {test.name!r} has a full-operation loop at "
            f"source={source_index}, line={loop.lineno} that starts a command and "
            "observes the operation output, but does not execute an unconditional "
            "_contract_record_checked_stimulus call for every iteration; "
            f"conditional_record_lines={sorted(conditional_lines)}. Every completed "
            "DUT job must enter the checked-stimulus ledger. Remove redundant jobs, "
            "or move the record after the completed DUT observation and outside any "
            "per-iteration if/try branch."
        )
    return errors


def _late_command_pulse_reads(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Reject a proven one-cycle command pulse read one active edge too late."""

    signals = [
        signal
        for signal in (interface_contract or {}).get("signals", [])
        if isinstance(signal, Mapping)
    ]
    command_channels = {
        str(signal.get("channel"))
        for signal in signals
        if signal.get("semantic_class") == "command" and signal.get("channel")
    }
    command_valid_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("channel") in command_channels
        and signal.get("role") == "valid"
        and signal.get("direction") == "input"
    }
    pulse_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("direction") == "output"
        and "one-cycle pulse" in str(signal.get("semantic", "")).lower()
        and "command acceptance" in str(signal.get("semantic", "")).lower()
    }
    if not command_valid_signals or not pulse_signals:
        return []

    definitions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def drives_command(helper: ast.AST) -> bool:
        for node in ast.walk(helper):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not (
                    isinstance(target, ast.Attribute)
                    and target.attr == "value"
                    and isinstance(target.value, ast.Attribute)
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "dut"
                    and target.value.attr in command_valid_signals
                ):
                    continue
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    return True
                if bool(value):
                    return True
        return False

    def awaited_trigger(await_node: ast.Await) -> str | None:
        value = await_node.value
        if not isinstance(value, ast.Call):
            return None
        if isinstance(value.func, ast.Name):
            return value.func.id
        if isinstance(value.func, ast.Attribute):
            return value.func.attr
        return None

    command_helpers: set[str] = set()
    for name, helper in definitions.items():
        triggers = sorted(
            (
                (node.lineno, awaited_trigger(node))
                for node in ast.walk(helper)
                if isinstance(node, ast.Await) and awaited_trigger(node) is not None
            ),
            key=lambda item: item[0],
        )
        if drives_command(helper) and triggers and triggers[-1][1] in {"RisingEdge", "FallingEdge"}:
            command_helpers.add(name)

    def names_required_high(function: ast.AsyncFunctionDef) -> set[str]:
        result: set[str] = set()
        for node in ast.walk(function):
            if not isinstance(node, ast.Assert):
                continue
            if isinstance(node.test, ast.Name):
                result.add(node.test.id)
                continue
            if not isinstance(node.test, ast.Compare) or len(node.test.ops) != 1:
                continue
            if not isinstance(node.test.ops[0], ast.Eq) or len(node.test.comparators) != 1:
                continue
            pairs = [(node.test.left, node.test.comparators[0]), (node.test.comparators[0], node.test.left)]
            for candidate, expected in pairs:
                if not isinstance(candidate, ast.Name):
                    continue
                try:
                    value = ast.literal_eval(expected)
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    continue
                if value == 1 or value is True:
                    result.add(candidate.id)
        return result

    def read_assignment(node: ast.AST) -> tuple[str, str] | None:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            return None
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [target.id for target in targets if isinstance(target, ast.Name)]
        if len(names) != 1:
            return None
        for child in ast.walk(node.value):
            if (
                isinstance(child, ast.Attribute)
                and isinstance(child.ctx, ast.Load)
                and child.attr == "value"
                and isinstance(child.value, ast.Attribute)
                and isinstance(child.value.value, ast.Name)
                and child.value.value.id == "dut"
                and child.value.attr in pulse_signals
            ):
                return names[0], child.value.attr
        return None

    def contains_high_literal(node: ast.AST) -> bool:
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False

        def contains(value: object) -> bool:
            if isinstance(value, Mapping):
                return any(contains(item) for item in value.values())
            if isinstance(value, (list, tuple, set, frozenset)):
                return any(contains(item) for item in value)
            return value == 1 or value is True

        return contains(value)

    def recorded_high_pulse(node: ast.Call) -> str | None:
        if not (
            isinstance(node.func, ast.Name)
            and node.func.id == "_contract_record_checked_stimulus"
            and len(node.args) >= 4
            and contains_high_literal(node.args[2])
        ):
            return None
        for child in ast.walk(node.args[3]):
            if (
                isinstance(child, ast.Attribute)
                and isinstance(child.ctx, ast.Load)
                and child.attr == "value"
                and isinstance(child.value, ast.Attribute)
                and isinstance(child.value.value, ast.Name)
                and child.value.value.id == "dut"
                and child.value.attr in pulse_signals
            ):
                return child.value.attr
        return None

    errors: list[str] = []
    for function in tree.body if isinstance(tree, ast.Module) else []:
        if not isinstance(function, ast.AsyncFunctionDef):
            continue
        if not any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "cocotb"
            and decorator.func.attr == "test"
            for decorator in function.decorator_list
        ):
            continue
        required_high = names_required_high(function)
        events: list[tuple[int, int, str, str | None, str | None]] = []
        for statement in function.body:
            for node in ast.walk(statement):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in command_helpers:
                    events.append((node.lineno, node.col_offset, "command", node.func.id, None))
                elif isinstance(node, ast.Call) and (recorded_signal := recorded_high_pulse(node)) is not None:
                    events.append((node.lineno, node.col_offset, "read", "checked-record observed", recorded_signal))
                elif isinstance(node, ast.Await) and awaited_trigger(node) == "RisingEdge":
                    events.append((node.lineno, node.col_offset, "rising", None, None))
                else:
                    read = read_assignment(node)
                    if read is not None and read[0] in required_high:
                        events.append((node.lineno, node.col_offset, "read", read[0], read[1]))

        command_line: int | None = None
        helper_name: str | None = None
        crossed_rising_line: int | None = None
        for line, _column, kind, name, signal_name in sorted(events):
            if kind == "command":
                command_line = line
                helper_name = name
                crossed_rising_line = None
            elif kind == "rising" and command_line is not None and crossed_rising_line is None:
                crossed_rising_line = line
            elif kind == "read" and command_line is not None and crossed_rising_line is not None:
                errors.append(
                    f"Cocotb test {function.name!r} reads one-cycle command pulse "
                    f"signal {signal_name!r} into {name!r} at source={source_index}, "
                    f"line={line} after helper {helper_name!r} returned following the "
                    f"acceptance cycle (call line={command_line}) and another RisingEdge "
                    f"was crossed at line={crossed_rising_line}. The later assertion "
                    "requires this sample to be high, but that active edge can already "
                    "clear the pulse. Capture the pulse inside the command helper after "
                    "the acceptance edge settles, return the observed value, or sample "
                    "it before awaiting the next RisingEdge."
                )
                command_line = None
                crossed_rising_line = None

        # Inline command drivers can perform the acceptance loop directly in
        # the test instead of calling a helper.  A later polling loop that first
        # crosses another active edge cannot recover the acceptance-cycle pulse.
        for loop in function.body:
            if not isinstance(loop, (ast.For, ast.While)):
                continue
            loop_pulse_signals = {
                child.value.attr
                for child in ast.walk(loop)
                if isinstance(child, ast.Attribute)
                and isinstance(child.ctx, ast.Load)
                and child.attr == "value"
                and isinstance(child.value, ast.Attribute)
                and isinstance(child.value.value, ast.Name)
                and child.value.value.id == "dut"
                and child.value.attr in pulse_signals
            }
            if not loop_pulse_signals:
                continue
            high_assignments = {
                target.id
                for child in ast.walk(loop)
                if isinstance(child, (ast.Assign, ast.AnnAssign))
                for target in (
                    child.targets if isinstance(child, ast.Assign) else [child.target]
                )
                if isinstance(target, ast.Name)
                and target.id in required_high
                and (
                    (lambda value: value == 1 or value is True)(
                        ast.literal_eval(child.value)
                    )
                    if isinstance(child.value, ast.Constant)
                    else False
                )
            }
            if not high_assignments:
                continue
            pulse_line = min(
                child.lineno
                for child in ast.walk(loop)
                if isinstance(child, ast.Attribute)
                and isinstance(child.value, ast.Attribute)
                and isinstance(child.value.value, ast.Name)
                and child.value.value.id == "dut"
                and child.value.attr in loop_pulse_signals
            )
            prior_triggers = [
                awaited_trigger(child)
                for child in ast.walk(loop)
                if isinstance(child, ast.Await) and child.lineno < pulse_line
            ]
            if "RisingEdge" not in prior_triggers or "FallingEdge" in prior_triggers:
                continue
            preceding_nodes = [
                child
                for statement in function.body
                if statement.lineno < loop.lineno
                for child in ast.walk(statement)
            ]
            last_record_line = max(
                (
                    child.lineno
                    for child in preceding_nodes
                    if isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "_contract_record_checked_stimulus"
                ),
                default=-1,
            )
            direct_start_lines: list[int] = []
            for child in preceding_nodes:
                if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                if not any(
                    isinstance(target, ast.Attribute)
                    and target.attr == "value"
                    and isinstance(target.value, ast.Attribute)
                    and isinstance(target.value.value, ast.Name)
                    and target.value.value.id == "dut"
                    and target.value.attr in command_valid_signals
                    for target in targets
                ):
                    continue
                try:
                    asserted = bool(ast.literal_eval(child.value))
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    asserted = True
                if asserted:
                    direct_start_lines.append(child.lineno)
            candidate_starts = [line for line in direct_start_lines if line > last_record_line]
            if not candidate_starts:
                continue
            errors.append(
                f"Cocotb test {function.name!r} starts an inline command at "
                f"source={source_index}, line={max(candidate_starts)}, then begins "
                f"monitoring one-cycle command pulse signal(s) {sorted(loop_pulse_signals)} "
                f"in loop line={loop.lineno} only after another RisingEdge. The "
                f"high-observation variable(s) {sorted(high_assignments)} can miss the "
                "entire acceptance-cycle pulse. Start the pulse monitor before driving "
                "the command, or capture the settled pulse immediately after the "
                "acceptance edge and before awaiting the next RisingEdge."
            )
    return errors


def _reset_abort_operation_records_without_relaunch(
    tree: ast.AST,
    source_index: int,
    source: str,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Do not attribute an aborted pre-reset job to a canonical operation record."""

    contract = interface_contract or {}
    signals = [
        signal
        for signal in contract.get("signals", [])
        if isinstance(signal, Mapping)
    ]
    reset_values = {
        str(signal.get("name")): str(signal.get("reset_value", "0"))
        for signal in signals
        if signal.get("role") == "reset" and signal.get("name")
    }
    command_channels = {
        str(signal.get("channel"))
        for signal in signals
        if signal.get("semantic_class") == "command" and signal.get("channel")
    }
    command_valid_signals = {
        str(signal.get("name"))
        for signal in signals
        if signal.get("channel") in command_channels
        and signal.get("role") == "valid"
        and signal.get("direction") == "input"
    }
    raw_handshake_rules = contract.get("global_handshake_rules", {})
    if isinstance(raw_handshake_rules, Mapping):
        reset_rules = str(raw_handshake_rules.get("stall_behavior", "")).lower()
    else:
        # Older and extension-owned interface contracts legitimately use one
        # descriptive string here.  Such a contract has no structured reset
        # discard policy to enforce, but it must never crash TB validation.
        reset_rules = str(raw_handshake_rules).lower()
    if not reset_values or not command_valid_signals or "non-attributable discard" not in reset_rules:
        return []
    try:
        intents = {
            item["label"]: set(item["targets"])
            for item in extract_stimulus_coverage_intents(source)
        }
    except ValueError:
        return []

    definitions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def assignment(node: ast.AST) -> tuple[str, ast.AST] | None:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            return None
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "dut"
            ):
                return target.value.attr, node.value
        return None

    command_helpers = {
        name
        for name, helper in definitions.items()
        if any(
            (item := assignment(node)) is not None
            and item[0] in command_valid_signals
            and (
                bool(ast.literal_eval(item[1]))
                if isinstance(item[1], ast.Constant)
                else True
            )
            for node in ast.walk(helper)
        )
    }
    errors: list[str] = []
    for record in ast.walk(tree):
        if not (
            isinstance(record, ast.Call)
            and isinstance(record.func, ast.Name)
            and record.func.id == "_contract_record_checked_stimulus"
        ):
            continue
        label_nodes = [keyword.value for keyword in record.keywords if keyword.arg == "label"]
        if len(label_nodes) != 1 or not isinstance(label_nodes[0], ast.Constant):
            continue
        label = str(label_nodes[0].value)
        targets = intents.get(label, set())
        claims_reset = any(
            target.startswith("signal.") and target.endswith(".reset_behavior")
            for target in targets
        )
        claims_operation = any(target.startswith("operation.") for target in targets)
        if not claims_reset or not claims_operation:
            continue

        resets: list[int] = []
        command_starts: list[int] = []
        for node in ast.walk(tree):
            if getattr(node, "lineno", record.lineno) >= record.lineno:
                continue
            item = assignment(node)
            if item is not None and item[0] in reset_values:
                try:
                    value = ast.literal_eval(item[1])
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    pass
                else:
                    if str(value) == reset_values[item[0]]:
                        resets.append(node.lineno)
            if item is not None and item[0] in command_valid_signals:
                try:
                    asserted = bool(ast.literal_eval(item[1]))
                except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                    asserted = True
                if asserted:
                    command_starts.append(node.lineno)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in command_helpers
            ):
                command_starts.append(node.lineno)
        if not resets:
            continue
        latest_reset = max(resets)
        if any(latest_reset < line < record.lineno for line in command_starts):
            continue
        errors.append(
            f"Stimulus {label!r} combines reset-abort coverage with canonical "
            f"operation coverage at source={source_index}, record line={record.lineno}, "
            f"but no new command is started after the latest reset assertion at "
            f"line={latest_reset}. The interface contract defines an aborted job as "
            "a non-attributable discard, so pre-reset partial operands must not be "
            "turned into an expected operation output. Keep the abort check in "
            "reset/error/completion protocol assertions, or launch, fully feed, drain, "
            "and record a new post-reset operation."
        )
    return errors


def _shell_escaped_subscript_keys(tree: ast.AST) -> list[tuple[int, str]]:
    """Find shell-quoting fragments accidentally embedded in Python dict keys.

    Model-authored source can preserve the shell escape sequence used to splice a
    single quote. Python accepts it as adjacent string literals, but the resulting
    key contains quote characters and fails only at simulation time.
    """

    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            continue
        value = node.slice.value
        if (
            len(value) >= 4
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
            and {"'", '"'} <= set(value)
        ):
            findings.append((getattr(node, "lineno", 0), value))
    return findings


def _vacuous_single_bit_signal_assertions(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Reject assertions that merely state a known one-bit signal is zero or one."""

    one_bit_signals = {
        str(signal.get("name"))
        for signal in (interface_contract or {}).get("signals", [])
        if isinstance(signal, Mapping)
        and str(signal.get("width", "")) == "1"
        and signal.get("direction") == "output"
    }
    if not one_bit_signals:
        return []
    errors: list[str] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.In)
            and len(node.test.comparators) == 1
        ):
            continue
        try:
            domain = ast.literal_eval(node.test.comparators[0])
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            continue
        if not isinstance(domain, (list, tuple, set, frozenset)) or set(domain) != {0, 1}:
            continue
        signal_names = {
            child.value.attr
            for child in ast.walk(node.test.left)
            if isinstance(child, ast.Attribute)
            and isinstance(child.ctx, ast.Load)
            and child.attr == "value"
            and isinstance(child.value, ast.Attribute)
            and isinstance(child.value.value, ast.Name)
            and child.value.value.id == "dut"
            and child.value.attr in one_bit_signals
        }
        if not signal_names:
            continue
        errors.append(
            f"Verifier assertion at source={source_index}, line={node.lineno} is "
            f"vacuous: one-bit DUT signal(s) {sorted(signal_names)} are asserted to "
            "be in the complete binary domain (0, 1), which can never establish "
            "the required behavior. Assert the contract-required value/event and "
            "sample it at the correct protocol cycle."
        )
    return errors


def _unused_passed_helper_parameters(tree: ast.AST, source_index: int) -> list[str]:
    """Reject local stimulus-control keywords that cannot change helper behavior.

    Only uniquely named local helpers and explicit keyword calls are considered.
    A parameter read anywhere in the helper body is treated as potentially used;
    this conservative rule catches no-op feature flags without inferring intent.
    """

    definitions: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.setdefault(node.name, []).append(node)
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        matches = definitions.get(node.func.id, [])
        if len(matches) != 1:
            continue
        helper = matches[0]
        if not isinstance(helper, ast.AsyncFunctionDef):
            # This rule is specifically about behavior-shaping stimulus controls.
            # A synchronous checker/classifier may accept several observed values
            # and legitimately decide that one is irrelevant to a particular
            # contract-local predicate; extension authoring validates its own
            # branch parameters separately.
            continue
        params = {
            arg.arg
            for arg in (
                *helper.args.posonlyargs,
                *helper.args.args,
                *helper.args.kwonlyargs,
            )
        }
        reads = {
            name.id
            for statement in helper.body
            for name in ast.walk(statement)
            if isinstance(name, ast.Name) and isinstance(name.ctx, ast.Load)
        }
        for keyword in node.keywords:
            if keyword.arg in params and keyword.arg not in reads:
                errors.append(
                    f"Stimulus helper {helper.name!r} never reads passed keyword "
                    f"{keyword.arg!r}; source={source_index}, call line={node.lineno}, "
                    f"helper line={helper.lineno}. This argument cannot change DUT "
                    "stimulus. Implement real DUT driving and observation controlled "
                    "by it, or remove the unsupported stimulus claim"
                )
    return errors


def _unchecked_stall_replays(tree: ast.AST, source_index: int) -> list[str]:
    """Catch a stall helper that may transfer a beat before sending it again.

    This is limited to clearly named stall helpers with a local valid/ready pair.
    It does not infer latency or claim a bin hit: driving valid through an active
    edge without reading ready, then replaying the same valid argument, is enough
    to prove a possible duplicate handshake.
    """

    errors: list[str] = []
    for helper in ast.walk(tree):
        if not isinstance(helper, ast.AsyncFunctionDef) or "stall" not in helper.name.lower():
            continue
        params = {
            arg.arg
            for arg in (*helper.args.posonlyargs, *helper.args.args, *helper.args.kwonlyargs)
        }
        valid_params = {name for name in params if "valid" in name.lower()}
        ready_params = {name for name in params if "ready" in name.lower()}
        if not valid_params or not ready_params:
            continue
        for index, statement in enumerate(helper.body):
            if not isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                continue
            loop_nodes = list(ast.walk(statement))
            driven_valids = {
                target.value.id
                for node in loop_nodes
                if isinstance(node, (ast.Assign, ast.AnnAssign))
                and isinstance(node.value, ast.Constant)
                and node.value.value == 1
                for target in (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                if isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Name)
                and target.value.id in valid_params
            }
            crosses_edge = any(
                isinstance(node, ast.Await)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, (ast.Name, ast.Attribute))
                and (
                    node.value.func.id if isinstance(node.value.func, ast.Name)
                    else node.value.func.attr
                ) == "RisingEdge"
                for node in loop_nodes
            )
            reads_ready = any(
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id in ready_params
                for node in loop_nodes
            )
            if not driven_valids or not crosses_edge or reads_ready:
                continue
            for later in helper.body[index + 1:]:
                for node in ast.walk(later):
                    if not isinstance(node, ast.Call):
                        continue
                    passed = {
                        arg.id for arg in node.args if isinstance(arg, ast.Name)
                    }
                    replayed = driven_valids & passed
                    if replayed and ready_params & passed:
                        errors.append(
                            f"Stimulus stall helper {helper.name!r} may transfer a beat "
                            f"before replay; source={source_index}, loop line={statement.lineno}, "
                            f"replay line={node.lineno}, valid={sorted(replayed)}, "
                            f"ready={sorted(ready_params & passed)}. It holds valid=1 "
                            "across a rising edge without checking ready, then sends "
                            "the same beat again. Measure each ready/valid handshake "
                            "exactly once and do not replay an accepted beat"
                        )
                        break
                else:
                    continue
                break
    return errors


def _nonprogressing_receiver_ready_loops(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Reject an output wait loop whose receiver-ready value cannot make progress.

    A common Verifier mistake is to choose ``ready = 0`` before ``while True``
    and then wait for ``valid and ready`` without ever changing ready in the
    loop.  That is not a finite stall: it is permanent backpressure and the test
    can only end through its global timeout.  This check intentionally requires
    a strong local pattern: a DUT-driven output-channel ready assignment directly
    preceding a loop, a read of the same ready in that loop, and no re-drive of
    ready inside the loop.
    """

    if not isinstance(interface_contract, Mapping):
        return []
    output_ready_signals: set[str] = set()
    signals = [
        item for item in interface_contract.get("signals", []) if isinstance(item, Mapping)
    ]
    for channel in interface_contract.get("channels", []):
        if not isinstance(channel, Mapping):
            continue
        channel_signals = channel.get("signals", {})
        if not isinstance(channel_signals, Mapping):
            continue
        ready_name = channel_signals.get("ready")
        if not ready_name:
            continue
        ready_meta = next(
            (item for item in signals if item.get("name") == ready_name), None
        )
        if isinstance(ready_meta, Mapping) and ready_meta.get("direction") == "input":
            output_ready_signals.add(str(ready_name))
    if not output_ready_signals:
        return []

    def driven_dut_signal(node: ast.AST) -> str | None:
        if not (
            isinstance(node, ast.Attribute)
            and node.attr == "value"
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "dut"
        ):
            return None
        return node.value.attr

    def assignment_parts(statement: ast.stmt) -> list[tuple[str, ast.AST]]:
        if isinstance(statement, ast.Assign):
            return [
                (name, statement.value)
                for target in statement.targets
                if (name := driven_dut_signal(target)) is not None
            ]
        if isinstance(statement, ast.AnnAssign):
            name = driven_dut_signal(statement.target)
            return [(name, statement.value)] if name is not None and statement.value else []
        return []

    def definitely_one(value: ast.AST) -> bool:
        return isinstance(value, ast.Constant) and value.value in (1, True)

    errors: list[str] = []

    def inspect_block(statements: list[ast.stmt]) -> None:
        for index, statement in enumerate(statements):
            if isinstance(statement, ast.While) and index:
                prior = assignment_parts(statements[index - 1])
                for ready_name, value in prior:
                    if ready_name not in output_ready_signals or definitely_one(value):
                        continue
                    reads_ready = any(
                        isinstance(node, ast.Attribute)
                        and node.attr == ready_name
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "dut"
                        for node in ast.walk(statement)
                    )
                    redrives_ready = any(
                        driven_dut_signal(target) == ready_name
                        for node in ast.walk(statement)
                        if isinstance(node, (ast.Assign, ast.AnnAssign))
                        for target in (
                            node.targets if isinstance(node, ast.Assign) else [node.target]
                        )
                    )
                    if reads_ready and not redrives_ready:
                        errors.append(
                            f"Output receiver ready {ready_name!r} may be 0 before an "
                            f"unbounded handshake wait and is never changed inside it; "
                            f"source={source_index}, assignment line={statements[index - 1].lineno}, "
                            f"loop line={statement.lineno}. This creates permanent "
                            "backpressure and a simulation timeout, not a finite stall. "
                            "Drive ready high after an explicit bounded number of cycles "
                            "inside the loop (or use ready=1 when no stall is intended)."
                        )
            for child_block in (
                getattr(statement, "body", None),
                getattr(statement, "orelse", None),
                getattr(statement, "finalbody", None),
            ):
                if isinstance(child_block, list):
                    inspect_block(child_block)
            if isinstance(statement, ast.Try):
                for handler in statement.handlers:
                    inspect_block(handler.body)

    inspect_block(getattr(tree, "body", []))
    return errors


def _uninitialized_contract_inputs(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Require each cocotb test to initialize all monitored DUT inputs.

    The contract monitor samples every declared signal from the first clock edge.
    A fresh simulator instance does not inherit initialization from another
    ``@cocotb.test`` function, so every test must drive each non-clock DUT input
    to a known value before its first await can cross time.
    """

    if not isinstance(interface_contract, Mapping):
        return []
    required = {
        str(signal.get("name", ""))
        for signal in interface_contract.get("signals", [])
        if isinstance(signal, Mapping)
        and signal.get("direction") == "input"
        and signal.get("role") != "clock"
        and signal.get("name")
        and "reset_value" in signal
    }
    if not required:
        return []

    def is_cocotb_test(function: ast.AsyncFunctionDef) -> bool:
        for decorator in function.decorator_list:
            call = decorator if isinstance(decorator, ast.Call) else None
            target = call.func if call is not None else decorator
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "test"
                and isinstance(target.value, ast.Name)
                and target.value.id == "cocotb"
            ):
                return True
        return False

    errors: list[str] = []
    for function in tree.body:
        if not isinstance(function, ast.AsyncFunctionDef) or not is_cocotb_test(function):
            continue
        initialized: set[str] = set()
        for statement in function.body:
            if any(isinstance(node, ast.Await) for node in ast.walk(statement)):
                break
            for node in ast.walk(statement):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                for target in (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                ):
                    if not (
                        isinstance(target, ast.Attribute)
                        and target.attr == "value"
                        and isinstance(target.value, ast.Attribute)
                        and isinstance(target.value.value, ast.Name)
                        and target.value.value.id == "dut"
                    ):
                        continue
                    initialized.add(target.value.attr)
        missing = sorted(required - initialized)
        if missing:
            errors.append(
                f"Cocotb test {function.name!r} leaves monitored DUT input signals "
                f"uninitialized before its first await; source={source_index}, "
                f"line={function.lineno}, missing={missing}. Each @cocotb.test runs "
                "with a fresh DUT and contract_coverage samples every interface signal "
                "from the first clock edge. Assign every listed dut.<signal>.value to "
                "a known idle/reset value in this test before awaiting time; another "
                "test's initialization is not shared."
            )
    return errors


def _invalid_cocotb_time_units(tree: ast.AST, source_index: int) -> list[str]:
    """Validate literal cocotb 2.x time units before the simulator starts."""

    accepted = {"step", "fs", "ps", "ns", "us", "ms", "sec"}
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            call_name = node.func.attr
            is_test = (
                call_name == "test"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "cocotb"
            )
        elif isinstance(node.func, ast.Name):
            call_name = node.func.id
            is_test = False
        else:
            continue
        is_timer = call_name == "Timer"
        if not (is_test or is_timer):
            continue
        relevant = {"timeout_unit"} if is_test else {"unit", "units"}
        for keyword in node.keywords:
            if (
                keyword.arg in relevant
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
                and keyword.value.value.lower() not in accepted
            ):
                unit = keyword.value.value
                replacement = "sec" if unit.lower() in {"s", "second", "seconds"} else None
                errors.append(
                    f"Cocotb time unit {unit!r} is invalid; source={source_index}, "
                    f"line={node.lineno}, argument={keyword.arg!r}. "
                    f"Accepted units are {sorted(accepted)}. "
                    + (f"Use {replacement!r} for seconds" if replacement else "Use an accepted unit")
                )
    return errors


def _standalone_awaited_trigger(statement: ast.stmt) -> str | None:
    if not (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Await)
        and isinstance(statement.value.value, ast.Call)
    ):
        return None
    function = statement.value.value.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return None


def _dut_output_value_reads(statement: ast.stmt, output_names: set[str]) -> set[str]:
    roots: list[ast.AST]
    if isinstance(statement, (ast.If, ast.While)):
        roots = [statement.test]
    elif isinstance(statement, (ast.For, ast.AsyncFor)):
        roots = [statement.iter]
    elif isinstance(statement, (ast.With, ast.AsyncWith)):
        roots = [item.context_expr for item in statement.items]
    elif isinstance(statement, (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        roots = []
    else:
        roots = [statement]
    reads: set[str] = set()
    for root in roots:
        for node in ast.walk(root):
            if not (
                isinstance(node, ast.Attribute)
                and isinstance(node.ctx, ast.Load)
                and node.attr == "value"
                and isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "dut"
                and node.value.attr in output_names
            ):
                continue
            reads.add(node.value.attr)
    return reads


def _unsettled_post_rising_output_reads(
    tree: ast.AST,
    source_index: int,
    interface_contract: Mapping[str, Any] | None,
) -> list[str]:
    """Reject output reads before the active-edge NBA/update region has settled."""

    output_names = {
        str(signal.get("name"))
        for signal in (interface_contract or {}).get("signals", [])
        if isinstance(signal, Mapping) and signal.get("direction") == "output"
    }
    handshake_output_names = {
        str(signal.get("name"))
        for signal in (interface_contract or {}).get("signals", [])
        if isinstance(signal, Mapping)
        and signal.get("direction") == "output"
        and signal.get("channel") is not None
        and signal.get("role") in {"valid", "ready", "payload", "last"}
    }
    if not output_names:
        return []
    errors: list[str] = []

    def inspect_statements(
        statements: list[ast.stmt],
        *,
        drives_dut: bool,
        incoming_rising_line: int | None = None,
        incoming_status_settled: bool = False,
    ) -> None:
        rising_line = incoming_rising_line
        status_settled = incoming_status_settled
        for statement in statements:
            trigger = _standalone_awaited_trigger(statement)
            if trigger in {"FallingEdge", "Edge"}:
                rising_line = None
                status_settled = True
            if rising_line is not None:
                reads = _dut_output_value_reads(statement, output_names)
                handshake_reads = reads & handshake_output_names
                status_reads = reads - handshake_output_names
                if handshake_reads:
                    errors.append(
                        "Ready/valid handshake output is read after RisingEdge, too "
                        "late to decide whether that edge transferred; "
                        f"source={source_index}, edge_line={rising_line}, "
                        f"read_line={statement.lineno}, signals={sorted(handshake_reads)}. "
                        "Drive valid/payload on the inactive edge, settle, snapshot the "
                        "channel ready/valid/payload before RisingEdge, then cross the "
                        "RisingEdge and use that saved pre-edge snapshot for acceptance. "
                        "A post-edge Timer or ReadOnly does not repair transfer accounting."
                    )
                    rising_line = None
                elif status_reads and not status_settled:
                    correction = (
                        "This coroutine also drives DUT inputs, so it must await a "
                        "small Timer before reading; do not add ReadOnly to this "
                        "coroutine."
                        if drives_dut
                        else "This coroutine is read-only, so await ReadOnly() before reading."
                    )
                    errors.append(
                        "Cocotb output/status read occurs immediately after "
                        "RisingEdge without a settling observation; "
                        f"source={source_index}, edge_line={rising_line}, "
                        f"read_line={statement.lineno}, signals={sorted(status_reads)}. "
                        "RisingEdge resumes before all HDL/NBA updates are reliably "
                        "observable. " + correction
                    )
                    rising_line = None
                if trigger in {"ReadOnly", "Timer"}:
                    status_settled = True
            if trigger == "RisingEdge":
                rising_line = statement.lineno
                status_settled = False
            elif (
                trigger not in {"Timer", "ReadOnly"}
                and any(isinstance(node, ast.Await) for node in ast.walk(statement))
            ):
                # An awaited helper or other suspension point means this is no longer
                # a straight-line read immediately following the remembered edge.
                rising_line = None
                status_settled = True
            for field in ("body", "orelse", "finalbody"):
                nested = getattr(statement, field, None)
                if isinstance(nested, list):
                    inspect_statements(
                        nested,
                        drives_dut=drives_dut,
                        incoming_rising_line=rising_line,
                        incoming_status_settled=status_settled,
                    )
            handlers = getattr(statement, "handlers", None)
            if isinstance(handlers, list):
                for handler in handlers:
                    inspect_statements(
                        handler.body,
                        drives_dut=drives_dut,
                        incoming_rising_line=rising_line,
                        incoming_status_settled=status_settled,
                    )

    for function in ast.walk(tree):
        if isinstance(function, ast.AsyncFunctionDef):
            drives_dut = any(
                isinstance(target, ast.Attribute)
                and target.attr == "value"
                and isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "dut"
                for assignment in ast.walk(function)
                if isinstance(assignment, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                for target in (
                    assignment.targets
                    if isinstance(assignment, ast.Assign)
                    else [assignment.target]
                )
            )
            inspect_statements(function.body, drives_dut=drives_dut)
    return errors


def _literal_mapping_shape(node: ast.AST) -> dict[str, str | None] | None:
    """Return statically provable top-level dict keys and simple value kinds."""

    if not isinstance(node, ast.Dict):
        return None
    result: dict[str, str | None] = {}
    for key_node, value_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            return None
        kind: str | None = None
        if isinstance(value_node, ast.Constant):
            kind = type(value_node.value).__name__
        elif (
            isinstance(value_node, ast.Call)
            and isinstance(value_node.func, ast.Name)
            and value_node.func.id in {"int", "str", "bool", "float", "list", "tuple", "dict"}
        ):
            kind = value_node.func.id
        elif isinstance(value_node, ast.List):
            kind = "list"
        elif isinstance(value_node, ast.Tuple):
            kind = "tuple"
        elif isinstance(value_node, ast.Dict):
            kind = "dict"
        result[key_node.value] = kind
    return result


def _name_is_unobserved_literal_alias(
    tree: ast.AST, call: ast.Call, name: str
) -> bool:
    """Prove a recorded observation name is only an unmodified literal alias."""

    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    scope: ast.AST = call
    while scope in parents and not isinstance(
        scope, (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        scope = parents[scope]

    def base_name(target: ast.AST) -> str | None:
        value = target
        while isinstance(value, (ast.Attribute, ast.Subscript)):
            value = value.value
        return value.id if isinstance(value, ast.Name) else None

    def literal_alias(candidate: str, before_line: int, seen: set[str]) -> bool:
        if candidate in seen:
            return False
        assignments: list[tuple[int, ast.AST]] = []
        for item in ast.walk(scope):
            if getattr(item, "lineno", before_line) >= before_line:
                continue
            if isinstance(item, ast.Assign):
                if any(isinstance(target, ast.Name) and target.id == candidate for target in item.targets):
                    assignments.append((item.lineno, item.value))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == candidate:
                assignments.append((item.lineno, item.value))
        if not assignments:
            return False
        assignment_line, value = max(assignments, key=lambda item: item[0])

        for item in ast.walk(scope):
            line = getattr(item, "lineno", -1)
            if not assignment_line < line < before_line:
                continue
            if isinstance(item, ast.AugAssign) and base_name(item.target) == candidate:
                return False
            if isinstance(item, (ast.Assign, ast.AnnAssign)):
                targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                if any(
                    base_name(target) == candidate
                    and not isinstance(target, ast.Name)
                    for target in targets
                ):
                    return False
            if (
                isinstance(item, ast.Call)
                and isinstance(item.func, ast.Attribute)
                and base_name(item.func.value) == candidate
            ):
                return False

        if isinstance(value, ast.Name):
            return literal_alias(value.id, assignment_line, seen | {candidate})
        try:
            ast.literal_eval(value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False
        return True

    return literal_alias(name, call.lineno, set())


def _name_aliases_name(
    tree: ast.AST, call: ast.Call, candidate: str, expected: str
) -> bool:
    """Prove that ``candidate`` is only a direct alias chain to ``expected``."""

    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    scope: ast.AST = call
    while scope in parents and not isinstance(
        scope, (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        scope = parents[scope]

    def resolve(name: str, before_line: int, seen: set[str]) -> bool:
        if name == expected:
            return True
        if name in seen:
            return False
        assignments = [
            item
            for item in ast.walk(scope)
            if isinstance(item, ast.Assign)
            and getattr(item, "lineno", before_line) < before_line
            and any(
                isinstance(target, ast.Name) and target.id == name
                for target in item.targets
            )
        ]
        if not assignments:
            return False
        assignment = max(assignments, key=lambda item: item.lineno)
        if not isinstance(assignment.value, ast.Name):
            return False
        for item in ast.walk(scope):
            line = getattr(item, "lineno", -1)
            if not assignment.lineno < line < before_line:
                continue
            if (
                isinstance(item, ast.AugAssign)
                and isinstance(item.target, ast.Name)
                and item.target.id == name
            ):
                return False
            if (
                isinstance(item, ast.Call)
                and isinstance(item.func, ast.Attribute)
                and isinstance(item.func.value, ast.Name)
                and item.func.value.id == name
            ):
                return False
        return resolve(assignment.value.id, assignment.lineno, seen | {name})

    return resolve(candidate, call.lineno, set())
