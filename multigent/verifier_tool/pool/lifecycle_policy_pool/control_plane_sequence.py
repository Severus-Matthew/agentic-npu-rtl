"""`control_plane_sequence`: the closed vocabulary for register-mapped job
start/completion on a black-box control interface (e.g. a Vitis HLS
`ap_ctrl_chain` AXI4-Lite control bus, where `ap_start`/`ap_done` are internal
wires never exposed as top-level pins).

Four primitives only, deliberately narrow, no LLM-authored code, no eval/exec:
`write_reg`, `write_field`, `read_reg`, `poll_field`. This sits beside
`policy` in a lifecycle declaration whenever `job_acceptance` or
`completion_style` selects `control_plane_sequence` (see
`lifecycle_policies.yaml`). Opcode-legality and overlap concepts
(`single_inflight_job_enforced`, `illegal_command_errors_without_start`) never
apply here -- there is no opcode/legal_values concept for a register-driven
start. The orchestration path can still prove `accepted_command_starts_job`
from post-start memory progress because that feature does not depend on an
opcode encoding.
"""

from __future__ import annotations

from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match


class ControlPlaneSequenceError(ValueError):
    """A control_plane_sequence declaration is not well-formed.

    `reason_code` names the defect class (see `pool/diagnostics.py`); it is set
    where the defect is detected so callers never parse the message.
    """

    def __init__(
        self,
        message: str = "",
        *,
        reason_code: str = "control_plane_sequence_schema_violation",
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code


_VALUE_FROM_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["data_object", "address_role", "half"],
    "properties": {
        "data_object": {"type": "string", "minLength": 1},
        "address_role": {"type": "string", "enum": ["base"]},
        "half": {"type": "string", "enum": ["low", "high", "whole"]},
    },
}

# `anyOf`, not `oneOf`: the branches are mutually exclusive through their `op`
# value (so acceptance is identical), and provider structured-output schemas
# reject `oneOf` (see tests/test_provider_schema_compat.py). `op` is a one-value
# `enum` rather than a `const` so this fragment adds no JSON-schema keyword the
# rest of the effective Architect schema does not already use.
_ACTION_SCHEMA = {
    "type": "object",
    "anyOf": [
        {
            "additionalProperties": False,
            "required": ["op", "register", "value_from"],
            "properties": {
                "op": {"type": "string", "enum": ["write_reg"]},
                "register": {"type": "string", "minLength": 1},
                "value_from": _VALUE_FROM_SCHEMA,
            },
        },
        {
            "additionalProperties": False,
            "required": ["op", "register", "field", "value"],
            "properties": {
                "op": {"type": "string", "enum": ["write_field"]},
                "register": {"type": "string", "minLength": 1},
                "field": {"type": "string", "minLength": 1},
                "value": {"type": "integer", "minimum": 0},
            },
        },
        {
            "additionalProperties": False,
            "required": ["op", "register"],
            "properties": {
                "op": {"type": "string", "enum": ["read_reg"]},
                "register": {"type": "string", "minLength": 1},
            },
        },
        {
            "additionalProperties": False,
            "required": ["op", "register", "field", "expected"],
            "properties": {
                "op": {"type": "string", "enum": ["poll_field"]},
                "register": {"type": "string", "minLength": 1},
                "field": {"type": "string", "minLength": 1},
                "expected": {"type": "integer", "minimum": 0},
            },
        },
    ],
}


_ACTION_BRANCHES = {
    str(branch["properties"]["op"]["enum"][0]): branch for branch in _ACTION_SCHEMA["anyOf"]
}


def _describe_schema_error(error: Any) -> str:
    """Name what is actually wrong, not just "not valid under any of the given schemas".

    An action failing its `anyOf` is re-validated against the one branch its own
    `op` selects, so the message says which field is missing/unexpected.
    """

    location = ".".join(str(part) for part in error.absolute_path)
    message = error.message
    instance = error.instance
    if error.validator == "anyOf" and isinstance(instance, Mapping):
        op = instance.get("op")
        branch = _ACTION_BRANCHES.get(str(op)) if isinstance(op, str) else None
        if branch is None:
            message = f"unknown action op {op!r}; allowed ops are {sorted(_ACTION_BRANCHES)}"
        else:
            specific = best_match(Draft202012Validator(branch).iter_errors(instance))
            inner = ".".join(str(part) for part in specific.absolute_path)
            message = f"{op} action: " + (f"{inner}: " if inner else "") + specific.message
    return f"{location}: {message}" if location else message


def control_plane_sequence_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["registers", "job_start", "job_complete"],
        "properties": {
            "registers": {
                "type": "object", "minProperties": 1,
                "additionalProperties": {
                    "type": "object", "additionalProperties": False,
                    "required": ["address"],
                    "properties": {
                        "address": {"type": "integer", "minimum": 0},
                        "fields": {
                            "type": "object", "minProperties": 1,
                            "additionalProperties": {
                                "type": "object", "additionalProperties": False,
                                "required": ["bit"],
                                "properties": {"bit": {"type": "integer", "minimum": 0}},
                            },
                        },
                    },
                },
            },
            "job_start": {
                "type": "object", "additionalProperties": False,
                "required": ["actions"],
                "properties": {"actions": {"type": "array", "minItems": 1, "items": _ACTION_SCHEMA}},
            },
            "job_complete": {
                "type": "object", "additionalProperties": False,
                "required": ["actions"],
                "properties": {"actions": {"type": "array", "minItems": 1, "items": _ACTION_SCHEMA}},
            },
        },
    }


def _register_field_bit(
    registers: Mapping[str, Any], register: str, field: str, *, context: str
) -> int:
    entry = registers.get(register)
    if not isinstance(entry, Mapping):
        raise ControlPlaneSequenceError(
            f"{context}: register {register!r} is not declared",
            reason_code="control_plane_sequence_unknown_reference",
        )
    fields = entry.get("fields", {})
    if field not in fields:
        raise ControlPlaneSequenceError(
            f"{context}: register {register!r} has no field {field!r}",
            reason_code="control_plane_sequence_unknown_reference",
        )
    return int(fields[field]["bit"])


def validate_control_plane_sequence(
    declaration: Mapping[str, Any], *, known_data_objects: set[str] | None
) -> None:
    """Check every structural invariant, independent of any specific accelerator.

    `known_data_objects=None` skips only the `value_from.data_object` cross-
    reference (a caller re-validating already-compiled metadata may not have
    the operation's own binding names in scope); every other structural check
    still runs unconditionally.
    """

    errors = list(Draft202012Validator(control_plane_sequence_schema()).iter_errors(declaration))
    if errors:
        raise ControlPlaneSequenceError(
            "control_plane_sequence must be explicit: "
            + _describe_schema_error(best_match(errors)),
            reason_code="control_plane_sequence_schema_violation",
        )

    registers = declaration["registers"]
    addresses: dict[int, str] = {}
    for name, entry in registers.items():
        address = int(entry["address"])
        if address in addresses:
            raise ControlPlaneSequenceError(
                f"registers {addresses[address]!r} and {name!r} collide at address {address:#x}",
                reason_code="control_plane_sequence_address_collision",
            )
        addresses[address] = name
        bits: dict[int, str] = {}
        for field, spec in entry.get("fields", {}).items():
            bit = int(spec["bit"])
            if bit in bits:
                raise ControlPlaneSequenceError(
                    f"register {name!r} fields {bits[bit]!r} and {field!r} collide at bit {bit}",
                    reason_code="control_plane_sequence_address_collision",
                )
            bits[bit] = field

    def _check_actions(actions: list[Mapping[str, Any]], *, context: str) -> None:
        for action in actions:
            register = str(action["register"])
            if register not in registers:
                raise ControlPlaneSequenceError(
                    f"{context}: action references unknown register {register!r}",
                    reason_code="control_plane_sequence_unknown_reference",
                )
            op = str(action["op"])
            if op == "write_reg":
                value_from = action["value_from"]
                data_object = str(value_from["data_object"])
                if known_data_objects is not None and data_object not in known_data_objects:
                    raise ControlPlaneSequenceError(
                        f"{context}: write_reg.value_from.data_object {data_object!r} is not one of "
                        f"this operation's own data objects",
                        reason_code="control_plane_sequence_unknown_reference",
                    )
            elif op in ("write_field", "poll_field"):
                _register_field_bit(registers, register, str(action["field"]), context=context)

    job_start_actions = list(declaration["job_start"]["actions"])
    _check_actions(job_start_actions, context="job_start")
    last = job_start_actions[-1]
    if str(last["op"]) not in ("write_reg", "write_field"):
        raise ControlPlaneSequenceError(
            "job_start.actions must end in a write_reg or write_field -- the action whose "
            "completing transaction fires the JOB_START event, never a poll",
            reason_code="control_plane_sequence_bad_start_action",
        )

    job_complete_actions = list(declaration["job_complete"]["actions"])
    _check_actions(job_complete_actions, context="job_complete")
    polls = [item for item in job_complete_actions if str(item["op"]) == "poll_field"]
    if len(polls) != 1 or str(job_complete_actions[-1]["op"]) != "poll_field":
        raise ControlPlaneSequenceError(
            "job_complete.actions must contain exactly one poll_field action, as the last action -- "
            "its success is what fires the JOB_COMPLETE event",
            reason_code="control_plane_sequence_bad_completion_poll",
        )


__all__ = [
    "ControlPlaneSequenceError",
    "control_plane_sequence_schema",
    "validate_control_plane_sequence",
]
