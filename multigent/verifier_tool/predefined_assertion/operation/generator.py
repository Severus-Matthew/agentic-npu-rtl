"""Generate code-owned result assertions for catalog operation features."""

from __future__ import annotations

import re
from typing import Any, Mapping

from multigent.verifier_tool.coverage.operation.plan import (
    load_operation_coverage_families,
)


def known_operation_features(
    architecture_contract: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    """Select catalog features; novel contract extensions stay LLM-owned."""

    if not architecture_contract:
        return {}
    catalog = load_operation_coverage_families()["families"]
    result: dict[str, tuple[str, ...]] = {}
    for operation in architecture_contract.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        family = str(operation.get("coverage_family", ""))
        if operation.get("coverage_family_source") != "catalog" or family not in catalog:
            continue
        known = set(catalog[family]["baseline_concepts"]) | set(
            catalog[family].get("optional_concepts", {})
        )
        name = str(operation.get("name", ""))
        operation_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        selected = [
            str(feature)
            for feature in [
                *operation.get("features", []),
                *operation.get("feature_extensions", []),
            ]
            if str(feature) in known
        ]
        result[name] = tuple(
            f"operation.{operation_id}."
            + re.sub(r"[^a-z0-9]+", "_", feature.lower()).strip("_")
            for feature in selected
        )
    return result


def render_operation_assertion_lines(
    operation_features: Mapping[str, tuple[str, ...]],
) -> list[str]:
    """Render the catalog-owned expected-versus-observed assertion wrapper."""

    lines = [
        "def _contract_record_checked_stimulus(stimulus_kind, stimulus, expected, observed, *, operations, label):",
        "    \"\"\"Apply taxonomy-owned assertions for catalog operation features.\"\"\"",
        "    expected_value = _contract_normalize_verification_value(expected, 'expected')",
        "    observed_value = _contract_normalize_verification_value(observed, 'observed')",
    ]
    for operation, features in operation_features.items():
        lines.append(f"    if {operation!r} in operations:")
        lines.append(f"        # CATALOG OPERATION [{operation}]")
        for feature in features:
            lines += [
                f"        # OPERATION ASSERTION [{feature}]",
                "        assert observed_value == expected_value, (",
                f"            'taxonomy-owned operation assertion failed; feature={feature}; '",
                "            + 'label=' + repr(label) + '; expected=' + repr(expected_value)",
                "            + '; observed=' + repr(observed_value)",
                "        )",
            ]
    lines += [
        "    return _contract_runtime_record_stimulus(",
        "        stimulus_kind, stimulus, expected_value, label=label",
        "    )",
    ]
    return lines
