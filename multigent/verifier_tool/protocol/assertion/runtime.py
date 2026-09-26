"""Runtime orchestration for code-owned protocol assertion checkers."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from multigent.verifier_tool.feature_plan import build_protocol_feature_plan
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_assertion_feature_plan,
)

from .assertion_checkers import (
    check_axi4,
    check_axi4_lite,
    check_axi4_stream,
    check_stall_stability,
    check_standard_signal_widths,
    check_valid_low_during_reset,
    finalize_protocol_checker_state,
)


def build_protocol_assertion_plan(interface_plan: Mapping[str, Any]) -> dict[str, Any]:
    """Build the inert protocol assertion plan embedded in a generated TB."""

    feature_plan = build_protocol_feature_plan(interface_plan)
    compiled_assertions = compile_assertion_feature_plan(feature_plan)
    stalls = [
        {
            "id": str(item["id"]),
            "valid": str(item.get("bindings", {}).get("valid", "")),
            "ready": str(item.get("bindings", {}).get("ready", "")),
            "content": tuple(
                map(str, item.get("bindings", {}).get("content", ()))
            ),
        }
        for item in compiled_assertions["entries"]
        if item.get("implementation") == "stall_stability"
    ]
    reset_binding = feature_plan.get("bindings", {}).get("reset", {})
    reset = str(reset_binding.get("signal", ""))
    candidate = reset_binding.get("active_value")
    active_value: int | None = int(candidate) if candidate in {0, 1} else None
    standard_groups = list(
        feature_plan.get("bindings", {}).get("standard_groups", [])
    )
    valid_reset_features: dict[str, str] = {}
    for item in compiled_assertions["entries"]:
        if item.get("implementation") != "valid_low_during_reset":
            continue
        for signal in item.get("bindings", {}).get("valid_signals", ()):
            valid_reset_features[str(signal)] = str(item["id"])
    valid_signals = tuple(sorted(valid_reset_features))
    features = [str(item["id"]) for item in compiled_assertions["entries"]]
    return {
        "schema_version": 2,
        "feature_plan": feature_plan,
        "compiled_assertions": compiled_assertions,
        "reset": reset,
        "reset_active_value": active_value,
        "reset_settle_cycles": int(reset_binding.get("settle_cycles", 0)),
        "valid_signals": valid_signals,
        "valid_reset_features": valid_reset_features,
        "stalls": stalls,
        "standard_groups": standard_groups,
        "features": tuple(dict.fromkeys(features)),
    }


def check_protocol_assertions(
    snapshot: Mapping[str, Any],
    plan: Mapping[str, Any],
    state: MutableMapping[str, Any],
) -> dict[str, int]:
    """Run the selected protocol assertion checkers for one sampled cycle."""

    reset = str(plan.get("reset", ""))
    active = plan.get("reset_active_value")
    reset_active = bool(
        reset
        and active in {0, 1}
        and reset in snapshot
        and int(bool(snapshot[reset])) == int(active)
    )
    if reset_active:
        # The generated monitor also sends a reset-only snapshot on the
        # rising edge. Count only full falling-edge observations; otherwise
        # a pipelined reset appears to settle twice as fast as the DUT clock.
        has_valid_sample = any(
            signal in snapshot for signal in plan.get("valid_signals", ())
        )
        active_samples = int(state.get("_reset_active_samples", 0)) + int(has_valid_sample)
        state.clear()
        state["_reset_active_samples"] = active_samples
        if has_valid_sample and active_samples > int(plan.get("reset_settle_cycles", 0)):
            check_valid_low_during_reset(
                snapshot,
                reset,
                tuple(map(str, plan.get("valid_signals", ()))),
                plan.get("valid_reset_features", {}),
            )
        return {}

    state.pop("_reset_active_samples", None)

    completed = check_stall_stability(snapshot, plan, state)
    group_states = state.setdefault("groups", {})
    for group in plan.get("standard_groups", []):
        group_state = group_states.setdefault(str(group["name"]), {})
        check_standard_signal_widths(snapshot, group, group_state)
        profile = str(group["profile"])
        if profile == "axi4":
            check_axi4(snapshot, group, group_state)
        elif profile == "axi4_lite":
            check_axi4_lite(snapshot, group, group_state)
        elif profile == "axi4_stream":
            check_axi4_stream(snapshot, group, group_state)
    if not state.get("stalls"):
        state.pop("stalls", None)
    if not state.get("groups"):
        state.pop("groups", None)
    return completed


def finalize_protocol_assertions(
    plan: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    """Finalize temporal protocol checker state at the end of a finite test."""

    finalize_protocol_checker_state(plan, state)


__all__ = [
    "build_protocol_assertion_plan",
    "check_protocol_assertions",
    "finalize_protocol_assertions",
]
