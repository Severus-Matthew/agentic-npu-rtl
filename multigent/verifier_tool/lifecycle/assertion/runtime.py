"""Runtime orchestration for code-owned lifecycle assertion checkers."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from multigent.verifier_tool.feature_plan import build_lifecycle_feature_plan
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_assertion_feature_plan,
)
from multigent.verifier_tool.pool.lifecycle_policy_pool import (
    policy_extension_request,
)

from .assertion_checkers import (
    check_lifecycle_operations,
    check_reset_outputs,
    finalize_lifecycle_checker_state,
    is_lifecycle_reset_active,
)
from .control_plane_sequence_tracker import advance_control_plane_sequence


def build_lifecycle_assertion_plan(
    interface_plan: Mapping[str, Any], operation_metadata: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the inert lifecycle assertion plan embedded in a generated TB."""

    feature_plan = build_lifecycle_feature_plan(interface_plan, operation_metadata)
    compiled_assertions = compile_assertion_feature_plan(feature_plan)
    bindings = feature_plan["bindings"]
    enabled_by_operation: dict[str, list[str]] = {}
    for item in compiled_assertions["entries"]:
        operation_name = str(item.get("scope_name", ""))
        if item.get("scope") != "operation" or not operation_name:
            continue
        enabled_by_operation.setdefault(operation_name, []).append(
            str(item["implementation"])
        )
    return {
        "schema_version": 2,
        "feature_plan": feature_plan,
        "compiled_assertions": compiled_assertions,
        "reset": dict(bindings.get("reset", {})),
        "reset_outputs": dict(bindings.get("reset_outputs", {})),
        "operations": list(bindings.get("operations", [])),
        "enabled_by_operation": {
            name: tuple(sorted(set(checkers)))
            for name, checkers in enabled_by_operation.items()
        },
        "features": tuple(
            str(item["id"]) for item in compiled_assertions["entries"]
        ),
    }


def check_lifecycle_assertions(
    snapshot: Mapping[str, Any],
    plan: Mapping[str, Any],
    state: MutableMapping[str, Any],
) -> None:
    """Run the selected lifecycle assertion checkers for one sampled cycle."""

    if is_lifecycle_reset_active(snapshot, plan.get("reset", {})):
        # Reset-only rising-edge snapshots clear temporal state but do not
        # represent another sampled DUT output cycle.
        has_output_sample = any(
            signal in snapshot for signal in plan.get("reset_outputs", {})
        )
        active_samples = int(state.get("_reset_active_samples", 0)) + int(has_output_sample)
        state["_reset_active_samples"] = active_samples
        if has_output_sample and active_samples > int(plan.get("reset", {}).get("settle_cycles", 0)):
            check_reset_outputs(snapshot, plan.get("reset_outputs", {}))
        # Built-in ``abort_inflight`` owns the normal state-clear transition.
        # A contract-local reset_behavior extension must not silently inherit
        # that assumption: preserve its per-operation job state so the exact
        # extension checker remains the only authority on in-flight work.
        # Status pulse history is a separate, built-in reset boundary and is
        # restarted so samples on opposite sides of reset are not treated as
        # consecutive pulse cycles.
        operation_state = state.get("operations", {})
        preserved: dict[str, dict[str, Any]] = {}
        aborted_operations: set[str] = set()
        if isinstance(operation_state, Mapping):
            for operation in plan.get("operations", []):
                if not isinstance(operation, Mapping):
                    continue
                name = str(operation.get("operation_name", ""))
                current = operation_state.get(name)
                enabled = set(plan.get("enabled_by_operation", {}).get(name, ()))
                if (
                    name
                    and isinstance(current, Mapping)
                    and current.get("active")
                    and "reset_aborts_pending_job" in enabled
                    and operation.get("policy", {}).get("reset_behavior")
                    == "abort_inflight"
                ):
                    aborted_operations.add(name)
                reset_behavior = operation.get("policy", {}).get("reset_behavior")
                if policy_extension_request(reset_behavior) is None:
                    continue
                if not name or not isinstance(current, Mapping):
                    continue
                preserved[name] = dict(current)
                preserved[name]["previous_completion"] = 0
                preserved[name]["previous_error"] = 0
                preserved[name]["error_seen"] = False
        state.clear()
        state["_reset_active_samples"] = active_samples
        state["reset_seen"] = True
        if aborted_operations:
            state["_reset_aborted_operations"] = tuple(sorted(aborted_operations))
        if preserved:
            state["operations"] = preserved
        return

    state.pop("_reset_active_samples", None)
    operations = list(plan.get("operations", []))
    job_start_by_operation: dict[str, bool] = {}
    job_complete_by_operation: dict[str, bool] = {}
    for operation in operations:
        sequence = operation.get("control_plane_sequence")
        if not isinstance(sequence, Mapping):
            continue
        name = str(operation.get("operation_name", ""))
        control_signals = operation["control_plane_signals"]
        sub_state = state.setdefault("operations", {}).setdefault(name, {})
        started, completed = advance_control_plane_sequence(snapshot, control_signals, sequence, sub_state)
        job_start_by_operation[name] = started
        job_complete_by_operation[name] = completed
    check_lifecycle_operations(
        snapshot,
        operations,
        state,
        {
            str(name): set(map(str, checkers))
            for name, checkers in plan.get("enabled_by_operation", {}).items()
        },
        job_start_by_operation,
        job_complete_by_operation,
    )


def finalize_lifecycle_assertions(
    plan: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    """Finalize temporal lifecycle checker state at the end of a finite test."""

    finalize_lifecycle_checker_state(plan, state)


__all__ = [
    "build_lifecycle_assertion_plan",
    "check_lifecycle_assertions",
    "finalize_lifecycle_assertions",
]
