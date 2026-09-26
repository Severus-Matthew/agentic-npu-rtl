"""Generate code-owned result assertions for catalog operation features."""

from __future__ import annotations

from typing import Any, Mapping

from multigent.verifier_tool.feature_plan import build_operation_feature_plan
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_assertion_feature_plan,
)


def known_operation_features(
    architecture_contract: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    """Select catalog features; novel contract extensions stay LLM-owned."""

    grouped: dict[str, list[str]] = {}
    feature_plan = build_operation_feature_plan(architecture_contract)
    for feature in compile_assertion_feature_plan(feature_plan)["entries"]:
        operation_name = str(feature.get("bindings", {}).get("operation_name", ""))
        grouped.setdefault(operation_name, []).append(str(feature["id"]))
    return {name: tuple(features) for name, features in grouped.items()}


def render_operation_assertion_lines(
    operation_features: Mapping[str, tuple[str, ...]],
) -> list[str]:
    """Render one central oracle comparison plus code-owned feature evidence.

    Catalog features are classifications of the already checked transaction. They
    are not separate correctness equations, so repeating ``observed == expected``
    once per feature only creates misleading duplicate assertions.
    """

    lines = [
        "def _contract_record_checked_stimulus(stimulus_kind, stimulus, expected, observed, *, operations, label):",
        "    \"\"\"Apply taxonomy-owned assertions for catalog operation features.\"\"\"",
        "    expected_value = _contract_normalize_verification_value(expected, 'expected')",
        "    observed_value = _contract_normalize_verification_value(observed, 'observed')",
        "    # OPERATION ASSERTION [central_golden_equivalence]",
        "    assert observed_value == expected_value, (",
        "        'central golden operation assertion failed; operations=' + repr(operations)",
        "        + '; features=' + repr({name: CONTRACT_OPERATION_ASSERTION_FEATURES.get(name, ()) for name in operations})",
        "        + '; label=' + repr(label) + '; expected=' + repr(expected_value)",
        "        + '; observed=' + repr(observed_value)",
        "    )",
    ]
    for operation, features in operation_features.items():
        lines.append(f"    if {operation!r} in operations:")
        lines.append(f"        # CATALOG OPERATION [{operation}]")
        for feature in features:
            # Keep the stable audit label while correctness itself is asserted
            # once above. These labels now identify classifier evidence only.
            lines.append(f"        # OPERATION ASSERTION [{feature}] (central comparison; classified evidence)")
        lines.append("        pass")
    lines += [
        "    stimulus_id = _contract_runtime_record_stimulus(",
        "        stimulus_kind, stimulus, expected_value, label=label,",
        "        operation_metadata=CONTRACT_OPERATION_METADATA,",
        "        operations=operations, observed=observed_value,",
        "    )",
        "    for operation_name in operations:",
        "        _contract_runtime_sample_operation(",
        "            operation_name, {}, stimulus_kind, stimulus_id",
        "        )",
        "    return stimulus_id",
    ]
    return lines
