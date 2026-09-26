"""Schema helpers shared by independent domain feature planners."""

from __future__ import annotations

import re
from typing import Any, Mapping

from multigent.verifier_tool.pool.role_pool.standard_protocols import (
    compile_standard_protocol_plan,
)


def safe_id(value: object) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(value)).strip("_").lower() or "unnamed"


def reset_active_value(signal: Mapping[str, Any]) -> int | None:
    semantic = str(signal.get("semantic", "")).lower().replace("_", "-")
    if "active-low" in semantic or "active low" in semantic:
        return 0
    if "active-high" in semantic or "active high" in semantic:
        return 1
    return None


def interface_parts(
    interface_or_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if isinstance(interface_or_plan.get("interface_contract"), Mapping):
        interface = dict(interface_or_plan["interface_contract"])
        standard_groups = [
            dict(item)
            for item in interface_or_plan.get("standard_protocol_plan", {}).get(
                "groups", []
            )
            if isinstance(item, Mapping)
        ]
    else:
        interface = dict(interface_or_plan)
        standard_groups = [
            dict(item)
            for item in compile_standard_protocol_plan(interface).get("groups", [])
            if isinstance(item, Mapping)
        ]
    return interface, standard_groups


def resolved_reset(interface: Mapping[str, Any]) -> dict[str, Any]:
    resets = sorted(
        (
            item
            for item in interface.get("signals", [])
            if isinstance(item, Mapping) and item.get("role") == "reset"
        ),
        key=lambda item: str(item.get("name", "")),
    )
    if not resets:
        return {}
    signal = resets[0]
    return {
        "signal": str(signal.get("name", "")),
        "active_value": reset_active_value(signal),
        "settle_cycles": int(signal.get("reset_settle_cycles", 0)),
    }


def coverage_branch(
    obligations_by_id: Mapping[str, Mapping[str, Any]], obligation_ids: list[str]
) -> dict[str, Any]:
    resolved = [item for item in obligation_ids if item in obligations_by_id]
    return {
        "obligation_ids": tuple(resolved),
        "observed_bin_names": {
            obligation_id: tuple(
                str(item.get("name", ""))
                for item in obligations_by_id[obligation_id].get("bins", [])
                if isinstance(item, Mapping)
            )
            for obligation_id in resolved
        },
    }


def feature_record(
    *,
    feature_id: str,
    domain: str,
    kind: str,
    scope: str,
    scope_name: str,
    bindings: Mapping[str, Any],
    assertion_checker: str | None,
    coverage: Mapping[str, Any],
    stimulus_strategy: str,
    tags: tuple[str, ...] | list[str] = (),
    stimulus: Mapping[str, Any] | None = None,
    automation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One resolved feature. `automation` is set only for a feature the tool
    cannot own end to end; a feature without it is plainly code-owned."""

    stimulus_branch = dict(stimulus or {})
    stimulus_branch["strategy"] = stimulus_strategy
    record: dict[str, Any] = {
        "id": feature_id,
        "domain": domain,
        "kind": kind,
        "scope": scope,
        "scope_name": scope_name,
        "bindings": dict(bindings),
        "tags": sorted(set(map(str, tags))),
        "assertion": {"checker": assertion_checker},
        "coverage": dict(coverage),
        "stimulus": stimulus_branch,
    }
    if automation is not None:
        record["automation"] = dict(automation)
    return record


__all__ = [
    "coverage_branch",
    "feature_record",
    "interface_parts",
    "resolved_reset",
    "safe_id",
]
