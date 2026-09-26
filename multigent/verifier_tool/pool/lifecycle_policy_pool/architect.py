"""Small Architect integration boundary for the tool-owned lifecycle policy pool."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .control_plane_sequence import control_plane_sequence_schema
from .policies import LifecyclePolicyError, lifecycle_policy_schema, validate_lifecycle_policy


def with_lifecycle_policy_schema(
    schema: Mapping[str, Any], *, required: bool = True
) -> dict[str, Any]:
    """Compose the effective Architect schema without duplicating pool enums.

    Initial generation requires an explicit selection for every operation.
    Semantic validation also requires a declaration for older frozen operations.
    """

    result = deepcopy(dict(schema))
    try:
        operation = result["properties"]["architecture_contract"]["properties"][
            "operations"
        ]["items"]
        properties = operation["properties"]
    except (KeyError, TypeError) as exc:
        raise LifecyclePolicyError("Architect schema needs architecture_contract.operations.items") from exc
    properties["lifecycle_policy"] = lifecycle_policy_schema()
    # Optional here (JSON Schema cannot express "required iff a policy field equals
    # control_plane_sequence" in a provider-safe way); `validate_operation_compilation`
    # enforces the declaration exactly when the policy selects control_plane_sequence.
    properties["lifecycle_control_plane_sequence"] = {
        **control_plane_sequence_schema(),
        "description": (
            "Register-level start/completion sequence. Declare it if and only if "
            "lifecycle_policy.job_acceptance or completion_style is control_plane_sequence; "
            "omit it otherwise."
        ),
    }
    fields = list(operation.get("required", []))
    if required and "lifecycle_policy" not in fields:
        fields.append("lifecycle_policy")
    operation["required"] = fields if required else [name for name in fields if name != "lifecycle_policy"]
    return result


def validate_architecture_lifecycle_policies(
    architecture: Mapping[str, Any],
    *,
    require_policy: bool = True,
    previous_architecture: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate explicit policies; old frozen contracts do not receive defaults."""

    previous_declared = {
        str(item.get("name", ""))
        for item in (previous_architecture or {}).get("operations", [])
        if isinstance(item, Mapping) and "lifecycle_policy" in item
    }
    errors: list[str] = []
    for operation in architecture.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        name = str(operation.get("name", ""))
        location = f"operation {name!r}.lifecycle_policy"
        if "lifecycle_policy" not in operation:
            if require_policy or name in previous_declared:
                errors.append(
                    f"{location} is required; select every field from Lifecycle Policy Pool. "
                    "An explicit selection cannot be removed to fall back to legacy defaults."
                )
            continue
        try:
            validate_lifecycle_policy(operation["lifecycle_policy"])
        except LifecyclePolicyError as exc:
            errors.append(f"{location}: {exc}")
    return errors


__all__ = [
    "validate_architecture_lifecycle_policies",
    "with_lifecycle_policy_schema",
]
