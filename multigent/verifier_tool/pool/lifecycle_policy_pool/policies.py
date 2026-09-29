"""Lifecycle behavior vocabulary, Architect schema fragment, and resolution.

The pool belongs to verifier_tool. It describes behaviors supported by the current
checkers and drivers; it does not teach an LLM to implement new lifecycle logic.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .control_plane_sequence import ControlPlaneSequenceError, validate_control_plane_sequence


LIFECYCLE_POLICY_POOL_PATH = Path(__file__).with_name("lifecycle_policies.yaml")

# Backend capability guard. YAML may expose a subset, but it must not make a
# behavior supported merely by adding an enum. Extend this alongside its checker,
# sampler, driver, and trace tests when implementing another policy.
_IMPLEMENTED_CHOICES = {
    "job_acceptance": {"valid_ready_handshake", "control_plane_sequence"},
    "job_overlap": {"single_inflight"},
    "busy_behavior": {"tracks_active_job"},
    "completion_style": {"pulse", "control_plane_sequence"},
    "completion_timing": {"next_cycle_after_retirement", "observed_via_poll"},
    "illegal_command_behavior": {"error_without_start"},
    "error_style": {"pulse", "sticky_until_reset"},
    "error_timing": {"next_cycle_after_error_event"},
    "reset_behavior": {"abort_inflight"},
}
_IMPLEMENTED_CHANNEL_RESET_BEHAVIORS = {"valid_deasserted"}


class LifecyclePolicyError(ValueError):
    """A lifecycle policy is missing, unsupported, or contradicts its bindings.

    `reason_code` names the defect class (see `pool/diagnostics.py`); it is set
    where the defect is detected so callers never parse the message.
    """

    def __init__(self, message: str = "", *, reason_code: str = "invalid_lifecycle_policy") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@lru_cache(maxsize=1)
def _pool() -> dict[str, Any]:
    raw = yaml.safe_load(LIFECYCLE_POLICY_POOL_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise LifecyclePolicyError("Lifecycle policy pool needs schema_version=1")
    definitions = raw.get("policies")
    if not isinstance(definitions, dict) or not definitions:
        raise LifecyclePolicyError("Lifecycle policy pool needs nonempty policies")
    if set(definitions) != set(_IMPLEMENTED_CHOICES):
        raise LifecyclePolicyError("Lifecycle policy pool fields disagree with implemented policies")
    for name, spec in definitions.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("choices"), dict) or not spec["choices"]:
            raise LifecyclePolicyError(f"Lifecycle policy {name!r} needs supported choices")
        unsupported = set(spec["choices"]) - _IMPLEMENTED_CHOICES[name]
        if unsupported:
            raise LifecyclePolicyError(
                f"Lifecycle policy {name!r} exposes unimplemented choices {sorted(unsupported)!r}"
            )
    channel_reset = raw.get("channel_reset_behaviors")
    if not isinstance(channel_reset, dict) or not channel_reset:
        raise LifecyclePolicyError("Lifecycle policy pool needs channel_reset_behaviors")
    if set(channel_reset) != _IMPLEMENTED_CHANNEL_RESET_BEHAVIORS:
        raise LifecyclePolicyError(
            "Lifecycle channel reset behaviors disagree with implemented checkers"
        )
    for name, spec in channel_reset.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("description"), str):
            raise LifecyclePolicyError(
                f"Lifecycle channel reset behavior {name!r} needs a description"
            )
    return raw


def load_lifecycle_policy_pool() -> dict[str, Any]:
    """Return an independent copy of the supported lifecycle policy pool."""

    return deepcopy(_pool())


def _extension_reference_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["extension_request"],
        "properties": {
            "extension_request": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$",
            }
        },
    }


def lifecycle_policy_schema() -> dict[str, Any]:
    """Return the merge-facing JSON Schema for an explicit policy selection.

    Embed as operation.lifecycle_policy, or as
    operation.verification_metadata.lifecycle.policy when using full metadata.
    This helper does not mutate the pipeline's Architect response schema.
    """

    definitions = _pool()["policies"]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(definitions),
        "properties": {
            name: {
                "anyOf": [
                    {"type": "string", "enum": list(spec["choices"])},
                    _extension_reference_schema(),
                ],
                "description": spec["description"],
            }
            for name, spec in definitions.items()
        },
    }


def reset_channel_policies_schema() -> dict[str, Any]:
    """Return the interface-level schema for explicit reset channel behavior."""

    return {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["channels", "behavior", "settle_cycles"],
            "properties": {
                "channels": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
                "behavior": {
                    "type": "string",
                    "enum": list(_pool()["channel_reset_behaviors"]),
                },
                "settle_cycles": {
                    "type": "integer",
                    "minimum": 0,
                },
            },
        },
    }


def resolve_reset_channel_policies(
    interface: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate and resolve explicit reset behavior for non-standard channels.

    A plain ``ready_valid`` profile deliberately makes no reset assumption.  The
    policy is therefore opt-in and channel-specific.  Standard AXI-family and
    custom-MMIO channels are rejected here because their standards already emit
    the same rule at protocol-group scope.
    """

    declarations = interface.get("reset_channel_policies", [])
    if declarations in (None, []):
        return []
    if not isinstance(declarations, list):
        raise LifecyclePolicyError(
            "interface.reset_channel_policies must be a list",
            reason_code="invalid_reset_channel_policy",
        )

    from multigent.verifier_tool.pool.role_pool.standard_protocols import (
        STANDARD_PROFILES,
    )

    channels = {
        str(item.get("name", "")): item
        for item in interface.get("channels", [])
        if isinstance(item, Mapping)
    }
    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    resets = [item for item in signals if item.get("role") == "reset"]
    if len(resets) != 1:
        raise LifecyclePolicyError(
            "reset_channel_policies require exactly one reset-role signal",
            reason_code="invalid_reset_channel_policy",
        )
    semantic = str(resets[0].get("semantic", "")).lower().replace("_", "-")
    if not any(token in semantic for token in ("active-low", "active low", "active-high", "active high")):
        raise LifecyclePolicyError(
            "reset_channel_policies require explicit active-high or active-low reset semantics",
            reason_code="invalid_reset_channel_policy",
        )

    resolved: list[dict[str, Any]] = []
    claimed: set[str] = set()
    supported = set(_pool()["channel_reset_behaviors"])
    for index, declaration in enumerate(declarations):
        location = f"interface.reset_channel_policies[{index}]"
        if not isinstance(declaration, Mapping):
            raise LifecyclePolicyError(
                f"{location} must be an object",
                reason_code="invalid_reset_channel_policy",
            )
        unknown = sorted(
            set(declaration) - {"channels", "behavior", "settle_cycles"}
        )
        if unknown:
            raise LifecyclePolicyError(
                f"{location} has unknown fields {unknown}",
                reason_code="invalid_reset_channel_policy",
            )
        names = declaration.get("channels")
        behavior = declaration.get("behavior")
        settle_cycles = declaration.get("settle_cycles")
        if (
            not isinstance(names, list)
            or not names
            or any(not isinstance(name, str) or not name for name in names)
            or len(names) != len(set(names))
        ):
            raise LifecyclePolicyError(
                f"{location}.channels must contain unique nonempty channel names",
                reason_code="invalid_reset_channel_policy",
            )
        if behavior not in supported:
            raise LifecyclePolicyError(
                f"{location}.behavior={behavior!r} is unsupported; supported={sorted(supported)!r}",
                reason_code="invalid_reset_channel_policy",
            )
        if (
            not isinstance(settle_cycles, int)
            or isinstance(settle_cycles, bool)
            or settle_cycles < 0
        ):
            raise LifecyclePolicyError(
                f"{location}.settle_cycles must be a nonnegative integer",
                reason_code="invalid_reset_channel_policy",
            )
        for name in names:
            if name in claimed:
                raise LifecyclePolicyError(
                    f"channel {name!r} has more than one reset channel policy",
                    reason_code="invalid_reset_channel_policy",
                )
            channel = channels.get(name)
            if channel is None:
                raise LifecyclePolicyError(
                    f"{location} references unknown channel {name!r}",
                    reason_code="invalid_reset_channel_policy",
                )
            profile = str(channel.get("protocol_profile", ""))
            if profile in STANDARD_PROFILES:
                raise LifecyclePolicyError(
                    f"channel {name!r} uses standard profile {profile!r}; its reset rule is standard-owned",
                    reason_code="duplicate_reset_channel_policy",
                )
            valid_signals = [
                str(signal.get("name", ""))
                for signal in signals
                if str(signal.get("channel", "")) == name
                and signal.get("role") == "valid"
            ]
            if len(valid_signals) != 1:
                raise LifecyclePolicyError(
                    f"channel {name!r} needs exactly one valid-role signal for {behavior}",
                    reason_code="invalid_reset_channel_policy",
                )
            claimed.add(name)
            resolved.append(
                {
                    "channel": name,
                    "protocol_profile": profile,
                    "behavior": str(behavior),
                    "settle_cycles": settle_cycles,
                    "valid_signals": valid_signals,
                }
            )
    return resolved


def validate_interface_reset_channel_policies(
    interface: Mapping[str, Any],
) -> list[str]:
    """Return deterministic contract errors for channel reset policies."""

    try:
        resolve_reset_channel_policies(interface)
    except LifecyclePolicyError as exc:
        return [str(exc)]
    return []


def render_lifecycle_policy_pool() -> str:
    """Render the exact vocabulary for Architect/Verifier prompts."""

    return LIFECYCLE_POLICY_POOL_PATH.read_text(encoding="utf-8").rstrip()


def policy_extension_request(value: object) -> str | None:
    """Return the referenced contract-local request, or None for a pool choice."""

    if not isinstance(value, Mapping) or set(value) != {"extension_request"}:
        return None
    identity = value.get("extension_request")
    return str(identity) if isinstance(identity, str) and identity else None


def _validate(value: object, definitions: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LifecyclePolicyError(
            "lifecycle.policy must be an object with explicit policy choices",
            reason_code="invalid_lifecycle_policy",
        )
    missing = sorted(set(definitions) - set(value))
    unknown = sorted(map(str, set(value) - set(definitions)))
    if missing or unknown:
        raise LifecyclePolicyError(
            f"lifecycle.policy fields: missing={missing}; unknown={unknown}; "
            "explicit policies must select every field from Lifecycle Policy Pool",
            reason_code="invalid_lifecycle_policy",
        )
    result: dict[str, Any] = {}
    for name, spec in definitions.items():
        choice = value[name]
        extension = policy_extension_request(choice)
        if extension is not None:
            result[name] = {"extension_request": extension}
            continue
        if not isinstance(choice, str) or choice not in spec["choices"]:
            raise LifecyclePolicyError(
                f"lifecycle.policy.{name}={choice!r} is unsupported; "
                f"supported choices={list(spec['choices'])!r}, or name one "
                "architecture_contract.verification_extensions request",
                reason_code="invalid_lifecycle_policy",
            )
        result[name] = choice
    return result


def validate_lifecycle_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Validate all selections without filling missing fields or guessing modes."""

    return _validate(policy, _pool()["policies"])


def resolve_lifecycle_policy(
    lifecycle: Mapping[str, Any],
    signals: Sequence[Mapping[str, Any]] = (),
    *,
    data_object_names: set[str] | None = None,
) -> dict[str, Any]:
    """Resolve explicit choices only, never policy defaults or signal prose."""

    if not isinstance(lifecycle, Mapping):
        raise LifecyclePolicyError("lifecycle must be an object", reason_code="invalid_lifecycle_policy")
    status = lifecycle.get("status_bindings", {})
    if not isinstance(status, Mapping):
        raise LifecyclePolicyError(
            "lifecycle.status_bindings must be an object", reason_code="ambiguous_status_binding"
        )
    for role in ("busy", "completion", "error"):
        names = status.get(role, [])
        if (
            not isinstance(names, (list, tuple))
            or len(names) > 1
            or any(not isinstance(name, str) or not name for name in names)
        ):
            raise LifecyclePolicyError(
                f"lifecycle.status_bindings.{role} must bind zero or one signal for this policy",
                reason_code="ambiguous_status_binding",
            )
    if "policy" in lifecycle:
        policy = validate_lifecycle_policy(lifecycle["policy"])
        source = str(lifecycle.get("policy_source", "explicit_contract"))
        if source != "explicit_contract":
            raise LifecyclePolicyError(
                f"Unsupported lifecycle.policy_source={source!r}",
                reason_code="unsupported_lifecycle_policy_source",
            )
    else:
        raise LifecyclePolicyError(
            "Missing lifecycle.policy; Architect must select supported lifecycle policies explicitly",
            reason_code="missing_lifecycle_policy",
        )

    commands = lifecycle.get("job_accept_channels", [])
    if not isinstance(commands, (list, tuple)):
        raise LifecyclePolicyError(
            "lifecycle.job_accept_channels must be a list", reason_code="invalid_lifecycle_policy"
        )
    for command in commands:
        if not isinstance(command, Mapping):
            raise LifecyclePolicyError(
                "lifecycle.job_accept_channels entries must be objects",
                reason_code="invalid_lifecycle_policy",
            )
        if (
            policy_extension_request(policy["job_acceptance"]) is None
            and command.get("acceptance") != "valid_and_ready_on_receiving_active_edge"
        ):
            raise LifecyclePolicyError(
                "lifecycle.policy.job_acceptance=valid_ready_handshake requires "
                "job_accept_channels[].acceptance=valid_and_ready_on_receiving_active_edge",
                reason_code="lifecycle_metadata_contradiction",
            )
    # These existing canonical metadata fields describe the same fixed runtime
    # contract. Never accept a contradictory declaration just because enums pass.
    fixed = {
        "configuration_snapshot": "accepted_command_event",
        "result_retirement": "all_declared_output_elements_accepted",
        "reset_disposition": "new_epoch_pending_work_requires_explicit_abort",
    }
    for name, supported in fixed.items():
        if name in lifecycle and lifecycle[name] != supported:
            raise LifecyclePolicyError(
                f"lifecycle.{name}={lifecycle[name]!r} contradicts the supported policy; "
                f"expected {supported!r}",
                reason_code="lifecycle_metadata_contradiction",
            )

    result: dict[str, Any] = {"policy": policy, "policy_source": source}
    needs_control_plane_sequence = (
        policy["job_acceptance"] == "control_plane_sequence"
        or policy["completion_style"] == "control_plane_sequence"
    )
    if needs_control_plane_sequence:
        declaration = lifecycle.get("control_plane_sequence")
        if declaration is None:
            raise LifecyclePolicyError(
                "lifecycle.control_plane_sequence is required when job_acceptance or "
                "completion_style selects control_plane_sequence",
                reason_code="control_plane_sequence_required_but_missing",
            )
        try:
            validate_control_plane_sequence(
                declaration, known_data_objects=data_object_names
            )
        except ControlPlaneSequenceError as exc:
            raise LifecyclePolicyError(str(exc), reason_code=exc.reason_code) from exc
        result["control_plane_sequence"] = deepcopy(dict(declaration))
    elif lifecycle.get("control_plane_sequence") is not None:
        raise LifecyclePolicyError(
            "lifecycle.control_plane_sequence is only meaningful when job_acceptance or "
            "completion_style selects control_plane_sequence",
            reason_code="control_plane_sequence_unused",
        )
    # Validate tuple coherence after declaration presence/absence so a scalar
    # policy edit that selects control_plane_sequence still receives the more
    # actionable missing-declaration diagnostic first.
    lifecycle_transport_fields = (
        "job_acceptance",
        "completion_style",
        "completion_timing",
    )
    if not any(
        policy_extension_request(policy[field]) is not None
        for field in lifecycle_transport_fields
    ):
        transport_tuple = tuple(policy[field] for field in lifecycle_transport_fields)
        supported_transport_tuples = {
            (
                "valid_ready_handshake",
                "pulse",
                "next_cycle_after_retirement",
            ),
            (
                "control_plane_sequence",
                "control_plane_sequence",
                "observed_via_poll",
            ),
        }
        if transport_tuple not in supported_transport_tuples:
            raise LifecyclePolicyError(
                "lifecycle policy contradicts its completion transport: "
                "job_acceptance/completion_style/completion_timing must be "
                "valid_ready_handshake/pulse/next_cycle_after_retirement or "
                "control_plane_sequence/control_plane_sequence/observed_via_poll",
                reason_code="lifecycle_metadata_contradiction",
            )
    return result


__all__ = [
    "LIFECYCLE_POLICY_POOL_PATH",
    "LifecyclePolicyError",
    "lifecycle_policy_schema",
    "load_lifecycle_policy_pool",
    "policy_extension_request",
    "reset_channel_policies_schema",
    "render_lifecycle_policy_pool",
    "resolve_reset_channel_policies",
    "resolve_lifecycle_policy",
    "validate_interface_reset_channel_policies",
    "validate_lifecycle_policy",
]
