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
    return result


__all__ = [
    "LIFECYCLE_POLICY_POOL_PATH",
    "LifecyclePolicyError",
    "lifecycle_policy_schema",
    "load_lifecycle_policy_pool",
    "policy_extension_request",
    "render_lifecycle_policy_pool",
    "resolve_lifecycle_policy",
    "validate_lifecycle_policy",
]
