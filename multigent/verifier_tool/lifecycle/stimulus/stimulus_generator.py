"""Generate reset, command-legality, job, abort, and recovery scenarios."""

from __future__ import annotations

import re
from typing import Any, Mapping

from multigent.verifier_tool.feature_plan import build_lifecycle_feature_plan
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_stimulus_feature_plan,
)
from multigent.verifier_tool.pool.lifecycle_policy_pool import policy_extension_request


class LifecycleStimulusGenerationError(ValueError):
    """A lifecycle scenario cannot be resolved safely from the frozen metadata."""


def _safe(value: object) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(value)).strip("_").lower() or "unnamed"


def build_lifecycle_stimulus_plan(
    interface: Mapping[str, Any], operation_metadata: Mapping[str, Any]
) -> dict[str, Any]:
    resets = [
        item
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    ]
    if len(resets) > 1:
        raise LifecycleStimulusGenerationError("lifecycle runner supports one frozen reset domain")
    feature_plan = build_lifecycle_feature_plan(interface, operation_metadata)
    compiled_stimulus = compile_stimulus_feature_plan(feature_plan)
    reset = dict(feature_plan.get("bindings", {}).get("reset", {}))
    active_value = reset.get("active_value")
    scenarios: list[dict[str, Any]] = []
    if reset:
        scenarios.append(
            {
                "id": "lifecycle.reset.idle",
                "kind": "reset_idle",
                "phase": "idle",
                "reset": str(reset.get("signal", "")),
                "active_value": active_value,
                "coverage_targets": [f"signal.{_safe(reset.get('signal', ''))}.reset_behavior"],
            }
        )
    for operation in feature_plan.get("bindings", {}).get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        name = str(operation.get("operation_name", ""))
        extension_fields = {
            field
            for field, value in operation.get("policy", {}).items()
            if policy_extension_request(value) is not None
        }
        command_channels = list(operation.get("commands", []))
        if "job_acceptance" in extension_fields:
            scenarios.append(
                {
                    "id": f"lifecycle.{name}.command.verifier_extension",
                    "kind": "verifier_extension",
                    "request_id": policy_extension_request(
                        operation["policy"]["job_acceptance"]
                    ),
                    "reason": "job acceptance stimulus is Verifier-owned",
                }
            )
            command_channels = []
        elif len(command_channels) != 1:
            scenarios.append(
                {
                    "id": f"lifecycle.{name}.command.unresolved",
                    "kind": "metadata_blocker",
                    "reason": "operation needs exactly one command-accept channel",
                }
            )
            continue
        command = dict(command_channels[0])
        legal_values = list(map(int, command.get("legal_values", [])))
        illegal_value = command.get("illegal_value")
        if not command_channels:
            pass
        elif not legal_values:
            scenarios.append(
                {
                    "id": f"lifecycle.{name}.command.legality_unresolved",
                    "kind": "metadata_blocker",
                    "reason": "command legal values are not machine-readable",
                }
            )
        else:
            scenarios.append(
                {
                    "id": f"lifecycle.{name}.command.legal",
                    "kind": "legal_command",
                    "operation_name": name,
                    "command": command,
                    "value": legal_values[0],
                }
            )
            if not extension_fields & {
                "illegal_command_behavior", "error_style", "error_timing",
            }:
                scenarios.extend([
                    {
                        "id": f"lifecycle.{name}.command.illegal",
                        "kind": "illegal_command",
                        "operation_name": name,
                        "command": command,
                        "value": illegal_value,
                    },
                    {
                        "id": f"lifecycle.{name}.command.illegal_then_legal",
                        "kind": "illegal_then_legal_recovery",
                        "operation_name": name,
                        "command": command,
                        "illegal_value": illegal_value,
                        "legal_value": legal_values[0],
                        "clear_error_before_legal_job": (
                            "reset"
                            if operation["policy"]["error_style"] == "sticky_until_reset"
                            else "pulse_deassertion"
                        ),
                    },
                ])
        phases = [
            {"phase": "idle", "progress": 0},
            *[
                {
                    "phase": f"input_{_safe(item.get('data_object'))}",
                    "data_object": str(item.get("data_object", "")),
                    "progress": "after_at_least_one_accepted_element",
                }
                for item in operation.get("inputs", [])
                if isinstance(item, Mapping)
            ],
            {"phase": "compute", "progress": "all_inputs_accepted_before_first_output"},
            {"phase": "output", "progress": "after_at_least_one_accepted_output"},
        ]
        for phase in phases if "reset_behavior" not in extension_fields else ():
            scenarios.append(
                {
                    "id": f"lifecycle.{name}.reset.{phase['phase']}",
                    "kind": "reset_abort",
                    "operation_name": name,
                    **phase,
                    "requirements": [
                        "no completion is attributable to reset-aborted work",
                        "no accepted pre-reset transfer is associated with a post-reset job",
                    ],
                }
            )
        if "reset_behavior" not in extension_fields:
            scenarios.append(
                {
                    "id": f"lifecycle.{name}.post_reset_purity",
                    "kind": "abort_then_clean_job",
                    "operation_name": name,
                    "requirements": [
                        "new job uses only post-reset accepted inputs",
                        "new job matches the code-owned golden model",
                        "aborted work produces no ghost output or completion",
                    ],
                }
            )
    return {
        "schema_version": 1,
        "source": "verifier_tool role-bound lifecycle stimulus generator",
        "feature_plan": feature_plan,
        "compiled_stimulus": compiled_stimulus,
        "reset": {
            "signal": str(reset.get("signal", "")),
            "active_value": active_value,
        },
        "scenarios": scenarios,
        "execution_contract": [
            "lifecycle scenarios are credited only from observed DUT events",
            "unknown command legality is blocking and is never guessed",
            "reset creates a new accounting epoch and explicitly aborts pending work",
        ],
    }
