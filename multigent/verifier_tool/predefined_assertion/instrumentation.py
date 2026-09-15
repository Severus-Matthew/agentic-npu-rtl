"""Generate the code-owned contract instrumentation embedded in cocotb TBs.

The generated block is deliberately visible in every saved testbench. It owns
reusable protocol assertions, catalog-operation result assertions, and the one
clock observer that captures the contract interface. Accelerator-specific stimulus,
golden-model construction, and novel-feature assertions remain Verifier-authored.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Mapping

from multigent.verifier_tool.predefined_assertion.operation import (
    known_operation_features,
    render_operation_assertion_lines,
)
from multigent.verifier_tool.predefined_assertion.protocol import (
    protocol_assertion_metadata,
    render_protocol_assertion_lines,
    render_protocol_monitor_lines,
)


BEGIN_MARKER = "# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ==="
END_MARKER = "# === END CONTRACT-GENERATED PROTOCOL MONITOR ==="
AUDIT_BEGIN_MARKER = "# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ==="
AUDIT_END_MARKER = "# === END PIPELINE-GENERATED VERIFIER ANNOTATIONS ==="
STIMULUS_SECTION = "# === STIMULUS AND COVERAGE INTENT ==="
OPERATION_ASSERTION_SECTION = "# === LLM-GENERATED OPERATION ASSERTIONS ==="
_RESERVED_NAMES = {
    "CONTRACT_SIGNAL_NAMES",
    "CONTRACT_PROTOCOL_ASSERTION_FEATURES",
    "CONTRACT_OPERATION_ASSERTION_FEATURES",
    "_CONTRACT_PROTOCOL_STATE",
    "_contract_record_checked_stimulus",
    "_contract_runtime_record_checked_stimulus",
    "_check_contract_protocol_assertions",
    "_contract_generated_monitor",
}


def _literal(value: object) -> str:
    return repr(value)


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
        "# This literal and the following comments are emitted by my_v.",
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
    conflict = sorted(declared & _RESERVED_NAMES)
    if conflict:
        raise ValueError(
            "Verifier source may not define code-owned protocol monitor names: "
            + ", ".join(conflict)
        )


def render_contract_generated_block(
    interface_plan: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
) -> str:
    """Render one deterministic, contract-bound observer/assertion block."""

    monitor = interface_plan.get("monitor", {})
    signal_names = tuple(map(str, monitor.get("signals", [])))
    clock = str(monitor.get("clock", ""))
    reset = str(monitor.get("reset", ""))
    obligations, feature_ids = protocol_assertion_metadata(interface_plan)
    operation_features = known_operation_features(architecture_contract)

    lines = [
        BEGIN_MARKER,
        "# This block is emitted by my_v from the frozen interface contract.",
        "# It is not authored or repaired by the LLM.",
        "from multigent.verifier_tool.coverage.runtime import (",
        "    capture_contract_snapshot,",
        "    observe_contract_reset_snapshot,",
        "    sample_contract_snapshot,",
        "    normalize_verification_value as _contract_normalize_verification_value,",
        "    record_stimulus as _contract_runtime_record_stimulus,",
        ")",
        "from cocotb.triggers import Edge, ReadOnly",
        "",
        f"CONTRACT_SIGNAL_NAMES = {_literal(signal_names)}",
        f"CONTRACT_PROTOCOL_ASSERTION_FEATURES = {_literal(feature_ids)}",
        f"CONTRACT_OPERATION_ASSERTION_FEATURES = {_literal(operation_features)}",
        "_CONTRACT_PROTOCOL_STATE = {}",
        "",
    ]
    lines += render_operation_assertion_lines(operation_features)
    lines += [""]
    lines += render_protocol_assertion_lines(
        interface_plan, reset=reset, obligations=obligations
    )
    lines += [""]
    lines += render_protocol_monitor_lines(clock=clock, reset=reset)
    lines += ["", END_MARKER, ""]
    return "\n".join(lines)


def install_contract_generated_block(
    source: str,
    interface_plan: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
) -> str:
    """Replace the final generated block with the current deterministic version."""

    verifier_source = strip_contract_generated_block(source)
    _assert_reserved_names_are_free(verifier_source)
    return verifier_source.rstrip() + "\n\n" + render_contract_generated_block(
        interface_plan, architecture_contract
    )


def validate_contract_generated_block(
    source: str,
    interface_plan: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
) -> None:
    """Reject edits or omissions of the code-owned block."""

    verifier_source = strip_contract_generated_block(source)
    expected = verifier_source.rstrip() + "\n\n" + render_contract_generated_block(
        interface_plan, architecture_contract
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


def validate_verifier_authored_structure(
    sources: list[str],
    required_obligations: set[str],
    architecture_contract: Mapping[str, Any] | None = None,
) -> None:
    """Require auditable sections and complete declared stimulus intent coverage."""

    pipeline_owned_operation_features = {
        feature
        for features in known_operation_features(architecture_contract).values()
        for feature in features
    }
    declared_targets: set[str] = set()
    known_labels: set[str] = set()
    used_labels: set[str] = set()
    for source in sources:
        verifier_source = strip_contract_generated_block(source)
        if STIMULUS_SECTION not in verifier_source:
            raise ValueError(f"Test source is missing {STIMULUS_SECTION}")
        if OPERATION_ASSERTION_SECTION not in verifier_source:
            raise ValueError(f"Test source is missing {OPERATION_ASSERTION_SECTION}")
        intents = extract_stimulus_coverage_intents(source)
        for item in intents:
            label = item["label"]
            if label in known_labels:
                raise ValueError(f"Stimulus intent label {label!r} is duplicated across files")
            known_labels.add(label)
            declared_targets.update(item["targets"])
            if f"# STIMULUS [{label}]" not in verifier_source:
                raise ValueError(f"Stimulus {label!r} needs a # STIMULUS [{label}] comment")

        tree = ast.parse(verifier_source)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_contract_record_checked_stimulus"
            ):
                continue
            label_nodes = [item.value for item in node.keywords if item.arg == "label"]
            if len(label_nodes) != 1 or not isinstance(label_nodes[0], ast.Constant) or not isinstance(label_nodes[0].value, str):
                raise ValueError(
                    "Every _contract_record_checked_stimulus call needs one literal label"
                )
            used_labels.add(label_nodes[0].value)

        source_lines = verifier_source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            preceding = source_lines[node.lineno - 2].strip() if node.lineno >= 2 else ""
            match = re.fullmatch(
                r"# (?:LLM-GENERATED )?(?:OPERATION|PROTOCOL) ASSERTION \[([^\]]+)\]",
                preceding,
            )
            if not match:
                raise ValueError(
                    f"Every Verifier-authored assert needs a feature comment immediately above it; line {node.lineno}"
                )
            if match.group(1) in pipeline_owned_operation_features:
                raise ValueError(
                    f"Verifier must not duplicate pipeline-owned catalog assertion "
                    f"{match.group(1)!r}; only taxonomy-missing feature assertions "
                    "belong in the LLM section"
                )

    unknown_targets = sorted(declared_targets - required_obligations)
    missing_targets = sorted(required_obligations - declared_targets)
    if unknown_targets or missing_targets:
        raise ValueError(
            "Stimulus coverage intent must target every exact coverage obligation; "
            f"missing={missing_targets}, unknown={unknown_targets}"
        )
    if used_labels != known_labels:
        raise ValueError(
            "STIMULUS_COVERAGE_INTENTS labels must match "
            "_contract_record_checked_stimulus labels; "
            f"unused={sorted(known_labels - used_labels)}, undeclared={sorted(used_labels - known_labels)}"
        )
