"""Render a minimal TB wrapper around tool-owned lifecycle assertions."""

from __future__ import annotations

from typing import Any, Mapping

from .runtime import build_lifecycle_assertion_plan


def lifecycle_assertion_metadata(
    interface_plan: Mapping[str, Any], operation_metadata: Mapping[str, Any]
) -> tuple[dict[str, Any], tuple[str, ...]]:
    plan = build_lifecycle_assertion_plan(interface_plan, operation_metadata)
    return plan, tuple(map(str, plan["features"]))


def render_lifecycle_assertion_lines(plan: Mapping[str, Any]) -> list[str]:
    lines = [f"CONTRACT_LIFECYCLE_ASSERTION_PLAN = {dict(plan)!r}", ""]
    lines.extend(f"# LIFECYCLE ASSERTION [{feature}]" for feature in plan.get("features", ()))
    lines.extend(
        [
            "def _check_contract_lifecycle_assertions(snapshot):",
            "    return _contract_check_lifecycle_assertions(",
            "        snapshot, CONTRACT_LIFECYCLE_ASSERTION_PLAN, _CONTRACT_LIFECYCLE_STATE",
            "    )",
            "",
            "def _finalize_contract_lifecycle_assertions():",
            "    return _contract_finalize_lifecycle_assertions(",
            "        CONTRACT_LIFECYCLE_ASSERTION_PLAN, _CONTRACT_LIFECYCLE_STATE",
            "    )",
        ]
    )
    return lines
