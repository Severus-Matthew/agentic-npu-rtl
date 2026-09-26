"""Lifecycle Feature Plan: resolve reset, command, job, and status behavior."""

from __future__ import annotations

from math import prod
from typing import Any, Mapping

from multigent.verifier_tool.pool.diagnostics import automation_record
from multigent.verifier_tool.pool.lifecycle_policy_pool import (
    policy_extension_request,
    resolve_lifecycle_policy,
)

from .catalog import load_lifecycle_feature_catalog
from .common import feature_record, interface_parts, resolved_reset, safe_id
from .schema import validate_resolved_feature_plan


def _control_plane_signals(standard_groups: list[Mapping[str, Any]]) -> dict[str, dict[str, str]] | None:
    """Flatten the one AXI4-Lite subordinate (control) group's compiled
    channels into the shape `control_plane_sequence_tracker.py` expects:
    `{kind: {valid, ready, addr|data}}`. Returns None if this interface has no
    such group (i.e. no operation here can use `control_plane_sequence`)."""

    group = next(
        (
            item
            for item in standard_groups
            if item.get("profile") == "axi4_lite" and item.get("endpoint_role") == "subordinate"
        ),
        None,
    )
    if group is None:
        return None
    channels = group.get("channels", {})
    result: dict[str, dict[str, str]] = {}
    for kind in ("write_address", "write_data", "write_response", "read_address", "read_data"):
        channel = channels.get(kind)
        if not isinstance(channel, Mapping):
            continue
        entry = {"valid": str(channel.get("valid", "")), "ready": str(channel.get("ready", ""))}
        fields = channel.get("fields", {})
        if "addr" in fields:
            entry["addr"] = str(fields["addr"])
        if "data" in fields:
            entry["data"] = str(fields["data"])
        result[kind] = entry
    return result


_LIFECYCLE_FEATURE_TAGS = {
    "legal_command_starts_one_job": ("lifecycle", "legal_command"),
    "illegal_command_errors_without_start": ("lifecycle", "illegal_command", "error"),
    "response_error_follows_nonokay": ("lifecycle", "error"),
    "no_output_without_active_job": ("lifecycle",),
    "busy_tracks_active_job": ("lifecycle", "busy"),
    "completion_matches_final_output": ("lifecycle", "completion"),
    "reset_aborts_pending_job": ("lifecycle", "reset"),
    "status_pulses_are_one_cycle": ("lifecycle", "completion", "error"),
}

_AFFECTED_POLICY_FIELDS = {
    "legal_command_starts_one_job": {"job_acceptance", "job_overlap"},
    "illegal_command_errors_without_start": {
        "job_acceptance", "illegal_command_behavior", "error_style", "error_timing",
    },
    "response_error_follows_nonokay": {"error_style", "error_timing"},
    "no_output_without_active_job": {"job_acceptance"},
    "busy_tracks_active_job": {"job_acceptance", "busy_behavior"},
    "completion_matches_final_output": {"completion_style", "completion_timing"},
    "reset_aborts_pending_job": {"reset_behavior"},
    "status_pulses_are_one_cycle": {"completion_style", "error_style"},
}


def _standard_channels(
    standard_groups: list[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(channel.get("name", "")): channel
        for group in standard_groups
        for channel in group.get("channels", {}).values()
        if isinstance(channel, Mapping)
    }


def _error_responses(
    bindings: list[Mapping[str, Any]],
    standard_channels: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    error_responses: list[dict[str, str]] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        mapping = binding.get("memory_mapping", {})
        if not isinstance(mapping, Mapping) or not mapping.get("response_channel"):
            continue
        response = standard_channels.get(str(mapping["response_channel"]), {})
        fields = response.get("fields", {}) if isinstance(response, Mapping) else {}
        if response and "resp" in fields:
            candidate = {
                "valid": str(response.get("valid", "")),
                "ready": str(response.get("ready", "")),
                "resp": str(fields["resp"]),
            }
            if candidate not in error_responses:
                error_responses.append(candidate)
    return error_responses


def _extension_fields(operation: Mapping[str, Any]) -> set[str]:
    return {
        field
        for field, value in operation.get("policy", {}).items()
        if policy_extension_request(value) is not None
    }


def _operation_feature_kinds(
    operation: Mapping[str, Any], catalog: Mapping[str, Any]
) -> list[str]:
    """Operation-scoped lifecycle feature kinds this operation's contract requires."""

    extension_fields = _extension_fields(operation)
    kinds: list[str] = []
    for kind in catalog["operation_features"]:
        if kind == "response_error_follows_nonokay" and not operation.get("error_responses"):
            continue
        affected = _AFFECTED_POLICY_FIELDS.get(kind, set())
        if kind == "status_pulses_are_one_cycle":
            if affected <= extension_fields:
                continue
        elif extension_fields & affected:
            continue
        kinds.append(kind)
    return kinds


def _shell_runtime_operation(
    shell: Mapping[str, Any],
    standard_channels: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Planning-only view of an operation that failed to compile whole.

    Built from the fragments that did compile (`unrepresentable_operations[].shell`).
    It feeds obligation/feature planning only; it is never placed in
    `bindings["operations"]`, which the runtime checkers and drivers consume.
    """

    lifecycle = dict(shell.get("lifecycle") or {})
    inputs = [dict(item) for item in shell.get("inputs", []) if isinstance(item, Mapping)]
    outputs = [dict(item) for item in shell.get("outputs", []) if isinstance(item, Mapping)]
    return {
        "operation_name": str(shell.get("operation_name", "")),
        "classifier_profile": str((shell.get("arithmetic") or {}).get("classifier_profile", "")),
        "commands": [
            dict(item)
            for item in lifecycle.get("job_accept_channels", [])
            if isinstance(item, Mapping)
        ],
        "inputs": inputs,
        "outputs": outputs,
        "retirements": [],
        "error_responses": _error_responses([*inputs, *outputs], standard_channels),
        "policy": dict(lifecycle.get("policy") or {}),
        "policy_source": str(lifecycle.get("policy_source", "unresolved")),
        "status": dict(lifecycle.get("status_bindings", {})),
        "lifecycle": lifecycle,
    }


def blocked_lifecycle_feature_ids(
    shell: Mapping[str, Any], standard_groups: list[Mapping[str, Any]]
) -> list[str]:
    """Lifecycle feature IDs the plan would emit for a shell (never raises on a shell)."""

    operation = _shell_runtime_operation(shell, _standard_channels(standard_groups))
    catalog = load_lifecycle_feature_catalog()
    return [
        f"lifecycle.{operation['operation_name']}.{kind}"
        for kind in _operation_feature_kinds(operation, catalog)
    ]


def _blocked_operations(
    operation_metadata: Mapping[str, Any],
    standard_groups: list[Mapping[str, Any]],
    compiled_names: set[str],
) -> list[tuple[Mapping[str, Any], dict[str, Any], dict[str, Any]]]:
    """(diagnostic entry, planning operation, automation record) per blocked operation."""

    channels = _standard_channels(standard_groups)
    blocked: list[tuple[Mapping[str, Any], dict[str, Any], dict[str, Any]]] = []
    seen = set(compiled_names)
    for entry in operation_metadata.get("unrepresentable_operations", []) or []:
        # Entries from older/hand-built metadata carry no shell: nothing to plan from.
        if not isinstance(entry, Mapping) or not isinstance(entry.get("shell"), Mapping):
            continue
        operation = _shell_runtime_operation(entry["shell"], channels)
        name = operation["operation_name"]
        # One plan per operation name: a name already compiled or already planned
        # would otherwise emit duplicate feature/obligation IDs.
        if not name or name in seen:
            continue
        seen.add(name)
        blocked.append(
            (entry, operation, automation_record(entry.get("diagnostics", [])))
        )
    return blocked


def _runtime_operations(
    operation_metadata: Mapping[str, Any],
    standard_groups: list[Mapping[str, Any]],
    signals: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    standard_channels = _standard_channels(standard_groups)
    control_plane_signals = _control_plane_signals(standard_groups)
    operations: list[dict[str, Any]] = []
    for operation in operation_metadata.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        lifecycle = operation.get("lifecycle", {})
        resolved_policy = resolve_lifecycle_policy(lifecycle, signals)
        lifecycle = {**lifecycle, **resolved_policy}
        outputs = [
            dict(item)
            for item in operation.get("outputs", [])
            if isinstance(item, Mapping)
        ]
        retirements: list[dict[str, Any]] = []
        dimensions = operation.get("dimensions", {})
        for output in outputs:
            extents = [dimensions.get(str(axis)) for axis in output.get("dimensions", [])]
            expected_count = (
                prod(map(int, extents))
                if extents
                and all(isinstance(value, int) and value > 0 for value in extents)
                else 1
                if not extents
                else None
            )
            mapping = output.get("memory_mapping", {})
            if isinstance(mapping, Mapping) and mapping.get("response_channel"):
                # A memory write response retires one bus word, not one logical
                # tensor element. Narrow results can pack several elements into
                # each accepted write and therefore need fewer responses.
                elements_per_word = mapping.get("elements_per_word")
                if expected_count is not None and isinstance(elements_per_word, int) and elements_per_word > 0:
                    expected_count = (expected_count + elements_per_word - 1) // elements_per_word
                response = standard_channels.get(str(mapping["response_channel"]), {})
                retirement = {
                    "signals": {
                        "valid": str(response.get("valid", "")),
                        "ready": str(response.get("ready", "")),
                    },
                    "expected_count": expected_count,
                    "kind": "memory_write_response",
                }
                if mapping.get("protocol_profile") == "axi4":
                    address = standard_channels.get(str(mapping.get("address_channel", "")), {})
                    data = standard_channels.get(str(mapping.get("data_channel", "")), {})
                    transfer_sizes = str(
                        mapping.get("protocol_capabilities", {}).get(
                            "transfer_size_bins", "full_width"
                        )
                    )
                    byte_count_mode = transfer_sizes != "full_width"
                    if byte_count_mode and isinstance(expected_count, int):
                        expected_count *= int(mapping["bus_width_bits"]) // 8
                    retirement.update({
                        "expected_count": expected_count,
                        "count_mode": (
                            "accepted_data_bytes_after_all_write_responses"
                            if byte_count_mode else
                            "accepted_data_beats_after_all_write_responses"
                        ),
                        "request_signals": {
                            "valid": str(address.get("valid", "")),
                            "ready": str(address.get("ready", "")),
                        },
                        "data_signals": {
                            "valid": str(data.get("valid", "")),
                            "ready": str(data.get("ready", "")),
                            "strobe": str(data.get("fields", {}).get("strb", "")),
                        },
                        "response_signal": str(response.get("fields", {}).get("resp", "")),
                    })
                retirements.append(retirement)
            else:
                retirements.append(
                    {
                        "signals": dict(output.get("signals", {})),
                        "expected_count": expected_count,
                        "kind": "output_transfer",
                    }
                )

        error_responses = _error_responses(
            [*operation.get("inputs", []), *operation.get("outputs", [])],
            standard_channels,
        )
        uses_control_plane_sequence = "control_plane_sequence" in lifecycle
        runtime_operation: dict[str, Any] = {
            "operation_name": str(operation.get("operation_name", "")),
            "classifier_profile": str(
                operation.get("arithmetic", {}).get("classifier_profile", "")
            ),
            "commands": [
                dict(item)
                for item in lifecycle.get("job_accept_channels", [])
                if isinstance(item, Mapping)
            ],
            "inputs": [
                dict(item)
                for item in operation.get("inputs", [])
                if isinstance(item, Mapping)
            ],
            "outputs": outputs,
            "retirements": retirements,
            "error_responses": error_responses,
            **resolved_policy,
            "status": dict(lifecycle.get("status_bindings", {})),
            "lifecycle": dict(lifecycle),
        }
        if uses_control_plane_sequence:
            if control_plane_signals is None:
                raise ValueError(
                    f"operation {runtime_operation['operation_name']!r} declares "
                    "control_plane_sequence but this interface has no AXI4-Lite "
                    "subordinate (control) group to drive/observe it through"
                )
            runtime_operation["control_plane_sequence"] = dict(lifecycle["control_plane_sequence"])
            runtime_operation["control_plane_signals"] = control_plane_signals
        operations.append(runtime_operation)
    return operations


def _bin(name: str, intent: str) -> dict[str, Any]:
    return {
        "name": name,
        "intent": intent,
        "required": True,
        "minimum_hits": 1,
        "applicability": {
            "status": "required_reachable",
            "basis": "resolved operation lifecycle metadata",
        },
    }


def _coverage_obligations(
    operations: list[Mapping[str, Any]],
    coverage_catalog: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    for operation in operations:
        name = str(operation.get("operation_name", ""))
        commands = list(operation.get("commands", []))
        # Lifecycle coverage depends on observable command/job/status behavior,
        # not on whether the operation's mathematics has a tool-owned golden
        # model.  An ``llm_extension`` operation with a resolved command path
        # still has accepted/active/retired/reset behavior to cover.
        if len(commands) != 1 or not commands[0].get("legal_values"):
            continue
        input_phases = [
            f"input_{safe_id(item.get('data_object', ''))}"
            for item in operation.get("inputs", [])
            if isinstance(item, Mapping)
        ]
        bindings = {
            "operation_name": name,
            "lifecycle": dict(operation.get("lifecycle", {})),
            "inputs": [dict(item) for item in operation.get("inputs", [])],
            "outputs": [dict(item) for item in operation.get("outputs", [])],
        }
        extension_fields = {
            field
            for field, value in operation.get("policy", {}).items()
            if policy_extension_request(value) is not None
        }
        for coverage_name, spec in coverage_catalog.items():
            if coverage_name in {"reset_abort_phase", "post_reset_purity"} and "reset_behavior" in extension_fields:
                continue
            bin_specs = [dict(item) for item in spec["bins"]]
            if coverage_name == "job_lifecycle":
                affected_fields = {
                    "accepted": {"job_acceptance"},
                    "active": {"job_acceptance", "busy_behavior"},
                    "retired": {
                        "job_acceptance", "completion_style", "completion_timing",
                    },
                    "aborted": {"reset_behavior"},
                }
                bin_specs = [
                    item
                    for item in bin_specs
                    if not extension_fields & affected_fields.get(str(item.get("name", "")), set())
                ]
                if not bin_specs:
                    continue
            if spec.get("dynamic_bins") == "input_phases":
                bin_specs = [
                    bin_specs[0],
                    *[
                        {
                            "name": phase,
                            "intent": f"Reset while loading {phase.removeprefix('input_')}.",
                        }
                        for phase in input_phases
                    ],
                    *bin_specs[1:],
                ]
            obligations.append(
                {
                    "id": f"operation.{safe_id(name)}.{coverage_name}",
                    "category": "lifecycle",
                    "template": str(coverage_name),
                    "scope": "operation",
                    "scope_name": name,
                    "description": str(spec["description"]),
                    "bindings": bindings,
                    "sample_unit": str(spec["sample_unit"]),
                    "controllability": str(spec["controllability"]),
                    "bins": [
                        _bin(str(item["name"]), str(item["intent"]))
                        for item in bin_specs
                    ],
                }
            )
    return obligations


def build_lifecycle_feature_plan(
    interface_or_plan: Mapping[str, Any], operation_metadata: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve reset, command, job, status, abort, and recovery features once."""

    interface, standard_groups = interface_parts(interface_or_plan)
    catalog = load_lifecycle_feature_catalog()
    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    reset = resolved_reset(interface)
    reset_outputs = {
        str(item.get("name", "")): int(str(item.get("reset_value", "0")), 0)
        for item in signals
        if item.get("direction") == "output"
        and str(item.get("reset_value", "")).strip()
        and str(item.get("reset_value", "0")).strip().lower() not in {"x", "z"}
    }
    operations = _runtime_operations(operation_metadata, standard_groups, signals)
    coverage_obligations = _coverage_obligations(
        operations, catalog["operation_coverage"]
    )
    # An operation that failed to compile whole is not driven or checked by the
    # tool, but its contract-required lifecycle obligations must not vanish with
    # it: they are planned from the fragments that did compile and stay required
    # (`required_reachable`), so the ordinary hit-based gate fails the run unless
    # someone else -- a Verifier-authored extension -- actually covers them.
    blocked = _blocked_operations(
        operation_metadata, standard_groups, {str(item["operation_name"]) for item in operations}
    )
    blocked_obligation_ids: dict[str, list[str]] = {}
    for entry, blocked_operation, automation in blocked:
        obligations = _coverage_obligations([blocked_operation], catalog["operation_coverage"])
        basis = (
            "contract-required lifecycle behavior; automatic verification blocked by "
            + ", ".join(automation.get("blocked_by", []))
        )
        for obligation in obligations:
            obligation["automation"] = dict(automation)
            for item in obligation["bins"]:
                item["applicability"] = {**item["applicability"], "basis": basis}
        blocked_obligation_ids[str(blocked_operation["operation_name"])] = [
            str(item["id"]) for item in obligations
        ]
        coverage_obligations.extend(obligations)
    coverage_ids = {str(item["id"]) for item in coverage_obligations}
    features: list[dict[str, Any]] = []

    def operation_features(
        operation: Mapping[str, Any], automation: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        name = str(operation["operation_name"])
        extension_fields = _extension_fields(operation)
        owned = automation is None
        records: list[dict[str, Any]] = []
        for kind in _operation_feature_kinds(operation, catalog):
            spec = catalog["operation_features"][kind]
            operation_coverage = [
                f"operation.{safe_id(name)}.{obligation}"
                for obligation in spec["coverage"].get("obligations", [])
                if f"operation.{safe_id(name)}.{obligation}" in coverage_ids
            ]
            records.append(
                feature_record(
                    feature_id=f"lifecycle.{name}.{kind}",
                    domain="lifecycle",
                    kind=kind,
                    scope="operation",
                    scope_name=name,
                    bindings={
                        "operation_name": name,
                        "policy": dict(operation["policy"]),
                        "policy_source": operation["policy_source"],
                        "extension_policy_fields": tuple(sorted(extension_fields)),
                    },
                    tags=_LIFECYCLE_FEATURE_TAGS.get(kind, ("lifecycle",)),
                    assertion_checker=spec["assertion"].get("checker") if owned else None,
                    coverage={
                        **spec["coverage"],
                        **({} if owned else {"sampler": None}),
                        "obligation_ids": tuple(operation_coverage),
                    },
                    stimulus_strategy=(
                        str(spec["stimulus"]["strategy"]) if owned else "not_automated"
                    ),
                    stimulus=spec["stimulus"] if owned else None,
                    automation=automation,
                )
            )
        return records

    for operation in operations:
        features.extend(operation_features(operation))
    blocked_bindings: list[dict[str, Any]] = []
    for entry, blocked_operation, automation in blocked:
        records = operation_features(blocked_operation, automation)
        features.extend(records)
        blocked_bindings.append(
            {
                "operation_name": str(blocked_operation["operation_name"]),
                "automation": dict(automation),
                "fragments": dict(entry["shell"].get("fragments", {})),
                "feature_ids": sorted(str(item["id"]) for item in records),
                "obligation_ids": sorted(
                    blocked_obligation_ids[str(blocked_operation["operation_name"])]
                ),
            }
        )
    if reset:
        reset_spec = catalog["features"]["reset_behavior"]
        reset_id = f"signal.{safe_id(reset['signal'])}.reset_behavior"
        features.append(
            feature_record(
                feature_id="lifecycle.reset.outputs_match_declared_reset_values",
                domain="lifecycle",
                kind="reset_outputs",
                scope="reset_domain",
                scope_name=str(reset["signal"]),
                bindings={"reset": dict(reset), "outputs": dict(reset_outputs)},
                tags=("lifecycle", "reset"),
                assertion_checker=reset_spec["assertion"].get("checker"),
                coverage={
                    **reset_spec["coverage"],
                    "obligation_ids": (reset_id,),
                },
                stimulus_strategy=str(reset_spec["stimulus"]["strategy"]),
                stimulus=reset_spec["stimulus"],
            )
        )
    features.sort(key=lambda item: str(item["id"]))
    return validate_resolved_feature_plan({
        "schema_version": 1,
        "domain": "lifecycle",
        "source": "frozen lifecycle bindings + verifier_tool lifecycle feature catalog",
        "bindings": {
            "reset": reset,
            "reset_outputs": reset_outputs,
            "operations": operations,
            **({"blocked_operations": blocked_bindings} if blocked_bindings else {}),
        },
        "features": features,
        "coverage_obligations": coverage_obligations,
    })


__all__ = ["blocked_lifecycle_feature_ids", "build_lifecycle_feature_plan"]
