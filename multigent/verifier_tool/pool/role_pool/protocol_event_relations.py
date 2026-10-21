"""Compile declarative causal relations between observable protocol events.

This module owns the reusable part of cross-protocol timing.  The Architect
declares that one observed event causes another after a bounded number of
cycles; Contract Review resolves the event bindings; the protocol assertion
runtime checks the relation.  No protocol or signal spelling is interpreted.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .protocol_semantics import (
    compile_protocol_expression,
    compile_protocol_semantics,
    expression_signals,
)
from .standard_protocols import compile_standard_protocol_plan


class ProtocolEventRelationError(ValueError):
    """A protocol event relation is ambiguous or cannot be executed safely."""


def _event_binding_schema() -> dict[str, Any]:
    return {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "profile", "event"],
                "properties": {
                    "kind": {"const": "protocol_event"},
                    "profile": {"type": "string", "minLength": 1},
                    "event": {"type": "string", "minLength": 1},
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "protocol_group", "protocol_channel"],
                "properties": {
                    "kind": {"const": "standard_channel_transfer"},
                    "protocol_group": {"type": "string", "minLength": 1},
                    "protocol_channel": {"type": "string", "minLength": 1},
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "expression"],
                "properties": {
                    "kind": {"const": "expression"},
                    "expression": {"type": "string", "minLength": 1},
                },
            },
        ]
    }


def protocol_event_relations_schema() -> dict[str, Any]:
    """Return the Architect-facing schema for bounded event causality."""

    event_binding = _event_binding_schema()
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "id",
                "description",
                "clock",
                "cause",
                "effect",
                "minimum_latency_cycles",
                "maximum_latency_cycles",
                "ordering",
                "maximum_outstanding",
                "unmatched_effect",
                "require_effect_before_test_end",
                "cancellation",
            ],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "description": {"type": "string", "minLength": 1},
                "clock": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["signal", "edge"],
                    "properties": {
                        "signal": {"type": "string", "minLength": 1},
                        "edge": {"type": "string", "enum": ["rising", "falling"]},
                    },
                },
                "cause": deepcopy(event_binding),
                "effect": deepcopy(event_binding),
                "minimum_latency_cycles": {"type": "integer", "minimum": 0},
                "maximum_latency_cycles": {
                    "anyOf": [
                        {"type": "integer", "minimum": 0},
                        {"type": "null"},
                    ]
                },
                "ordering": {"const": "fifo"},
                "maximum_outstanding": {"type": "integer", "minimum": 1},
                "unmatched_effect": {"type": "string", "enum": ["error", "ignore"]},
                "require_effect_before_test_end": {"type": "boolean"},
                "cancellation": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["event", "pending_behavior"],
                    "properties": {
                        "event": {
                            "anyOf": [deepcopy(event_binding), {"type": "null"}]
                        },
                        "pending_behavior": {
                            "type": "string",
                            "enum": ["flush", "preserve"],
                        },
                    },
                },
            },
        },
    }


def with_protocol_event_relations_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Expose optional event relations in the effective Architect schema."""

    result = deepcopy(dict(schema))
    try:
        properties = result["properties"]["interface_contract"]["properties"]
    except (KeyError, TypeError) as exc:
        raise ProtocolEventRelationError(
            "Architect schema needs interface_contract.properties"
        ) from exc
    properties["protocol_event_relations"] = protocol_event_relations_schema()
    return result


def _standard_transfer_expression(channel: Mapping[str, Any]) -> dict[str, Any]:
    valid = str(channel.get("valid", ""))
    if not valid:
        raise ProtocolEventRelationError("standard channel has no VALID binding")
    ready = channel.get("ready")
    if ready in {None, ""}:
        return {"signal": valid}
    return {
        "op": "and",
        "args": [{"signal": valid}, {"signal": str(ready)}],
    }


def _compile_binding(
    raw: object,
    *,
    signals: set[str],
    profiles: Mapping[str, Mapping[str, Any]],
    standard_groups: Mapping[str, Mapping[str, Any]],
    relation_clock: Mapping[str, Any],
    location: str,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ProtocolEventRelationError(f"{location} must be an event binding")
    kind = str(raw.get("kind", ""))
    if kind == "protocol_event":
        profile_name = str(raw.get("profile", ""))
        event_name = str(raw.get("event", ""))
        profile = profiles.get(profile_name)
        if profile is None:
            raise ProtocolEventRelationError(
                f"{location} references unknown protocol profile {profile_name!r}"
            )
        if dict(profile.get("clock", {})) != dict(relation_clock):
            raise ProtocolEventRelationError(
                f"{location} uses {profile_name!r} clock {profile.get('clock')!r}, "
                f"which does not match relation clock {dict(relation_clock)!r}"
            )
        event = profile.get("events", {}).get(event_name)
        if not isinstance(event, Mapping):
            raise ProtocolEventRelationError(
                f"{location} references unknown event {profile_name}.{event_name}"
            )
        expression = deepcopy(event["expression"])
        source = {"kind": kind, "profile": profile_name, "event": event_name}
    elif kind == "standard_channel_transfer":
        group_name = str(raw.get("protocol_group", ""))
        channel_name = str(raw.get("protocol_channel", ""))
        group = standard_groups.get(group_name)
        if group is None:
            raise ProtocolEventRelationError(
                f"{location} references unknown standard protocol group {group_name!r}"
            )
        channel = group.get("channels", {}).get(channel_name)
        if not isinstance(channel, Mapping):
            raise ProtocolEventRelationError(
                f"{location} references unknown channel {group_name}.{channel_name}"
            )
        expression = _standard_transfer_expression(channel)
        source = {
            "kind": kind,
            "protocol_group": group_name,
            "protocol_channel": channel_name,
        }
    elif kind == "expression":
        text = str(raw.get("expression", ""))
        expression = compile_protocol_expression(text, signals=signals)
        source = {"kind": kind, "expression": text}
    else:
        raise ProtocolEventRelationError(
            f"{location} has unsupported event binding kind {kind!r}"
        )
    return {
        "source": source,
        "expression": expression,
        "signals": expression_signals(expression),
    }


def compile_protocol_event_relations(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve event relations to executable, signal-name-independent plans."""

    raw_relations = interface.get("protocol_event_relations", [])
    if raw_relations is None or raw_relations == ():
        raw_relations = []
    if not isinstance(raw_relations, list):
        raise ProtocolEventRelationError(
            "interface_contract.protocol_event_relations must be a list"
        )
    if not raw_relations:
        return {"schema_version": 1, "relations": []}
    signals = {
        str(item.get("name", ""))
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("name")
    }
    profiles = {
        str(item["name"]): item
        for item in compile_protocol_semantics(interface).get("profiles", [])
    }
    standard_groups = {
        str(item["name"]): item
        for item in compile_standard_protocol_plan(interface).get("groups", [])
    }
    interface_clock = str(interface.get("clock", ""))
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_relations:
        if not isinstance(raw, Mapping):
            raise ProtocolEventRelationError(
                "protocol_event_relations entries must be mappings"
            )
        relation_id = str(raw.get("id", "")).strip()
        if not relation_id or relation_id in seen:
            raise ProtocolEventRelationError(
                f"duplicate or empty protocol event relation id {relation_id!r}"
            )
        seen.add(relation_id)
        clock = raw.get("clock", {})
        clock_signal = str(clock.get("signal", "")) if isinstance(clock, Mapping) else ""
        clock_edge = str(clock.get("edge", "")) if isinstance(clock, Mapping) else ""
        if clock_signal not in signals:
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} references unknown clock {clock_signal!r}"
            )
        if clock_edge not in {"rising", "falling"}:
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} has invalid clock edge {clock_edge!r}"
            )
        if interface_clock and clock_signal != interface_clock:
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} uses clock {clock_signal!r}; "
                f"the current runtime samples only interface clock {interface_clock!r}"
            )
        minimum_raw = raw.get("minimum_latency_cycles", 0)
        if isinstance(minimum_raw, bool) or not isinstance(minimum_raw, int):
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} minimum latency must be an integer"
            )
        minimum = int(minimum_raw)
        maximum_raw = raw.get("maximum_latency_cycles")
        if maximum_raw is not None and (
            isinstance(maximum_raw, bool) or not isinstance(maximum_raw, int)
        ):
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} maximum latency must be an integer or null"
            )
        maximum = None if maximum_raw is None else int(maximum_raw)
        if minimum < 0 or (maximum is not None and maximum < 0):
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} latency cannot be negative"
            )
        if maximum is not None and maximum < minimum:
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} maximum latency {maximum} "
                f"is below minimum {minimum}"
            )
        ordering = str(raw.get("ordering", ""))
        if ordering != "fifo":
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} supports only fifo ordering"
            )
        outstanding_raw = raw.get("maximum_outstanding", 0)
        if (
            isinstance(outstanding_raw, bool)
            or not isinstance(outstanding_raw, int)
            or outstanding_raw < 1
        ):
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} maximum_outstanding must be at least one"
            )
        unmatched_effect = str(raw.get("unmatched_effect", ""))
        if unmatched_effect not in {"error", "ignore"}:
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} has invalid unmatched_effect "
                f"{unmatched_effect!r}"
            )
        cancellation = raw.get("cancellation", {})
        if not isinstance(cancellation, Mapping):
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} cancellation must be a mapping"
            )
        cancellation_behavior = str(cancellation.get("pending_behavior", ""))
        if cancellation_behavior not in {"flush", "preserve"}:
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} has invalid cancellation behavior "
                f"{cancellation_behavior!r}"
            )
        cancellation_event = (
            cancellation.get("event")
        )
        if cancellation_event is None and cancellation_behavior == "flush":
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} cannot flush without a cancellation event"
            )
        require_final = raw.get("require_effect_before_test_end", True)
        if not isinstance(require_final, bool):
            raise ProtocolEventRelationError(
                f"protocol event relation {relation_id!r} "
                "require_effect_before_test_end must be boolean"
            )
        compiled_cancellation = (
            _compile_binding(
                cancellation_event,
                signals=signals,
                profiles=profiles,
                standard_groups=standard_groups,
                relation_clock={
                    "signal": clock_signal,
                    "edge": str(clock.get("edge", "rising")),
                },
                location=f"protocol event relation {relation_id!r} cancellation",
            )
            if cancellation_event is not None
            else None
        )
        result.append({
            "id": relation_id,
            "description": str(raw.get("description", "")),
            "clock": {
                "signal": clock_signal,
                "edge": clock_edge,
            },
            "cause": _compile_binding(
                raw.get("cause"),
                signals=signals,
                profiles=profiles,
                standard_groups=standard_groups,
                relation_clock={
                    "signal": clock_signal,
                    "edge": clock_edge,
                },
                location=f"protocol event relation {relation_id!r} cause",
            ),
            "effect": _compile_binding(
                raw.get("effect"),
                signals=signals,
                profiles=profiles,
                standard_groups=standard_groups,
                relation_clock={
                    "signal": clock_signal,
                    "edge": clock_edge,
                },
                location=f"protocol event relation {relation_id!r} effect",
            ),
            "minimum_latency_cycles": minimum,
            "maximum_latency_cycles": maximum,
            "ordering": ordering,
            "maximum_outstanding": int(outstanding_raw),
            "unmatched_effect": unmatched_effect,
            "require_effect_before_test_end": require_final,
            "cancellation": {
                "event": compiled_cancellation,
                "pending_behavior": str(
                    cancellation_behavior
                ),
            },
        })
    return {"schema_version": 1, "relations": result}


def validate_protocol_event_relations(interface: Mapping[str, Any]) -> list[str]:
    """Return relation errors in the validator convention used by Architect."""

    try:
        compile_protocol_event_relations(interface)
    except (ProtocolEventRelationError, ValueError, KeyError, TypeError) as exc:
        return [str(exc)]
    return []


__all__ = [
    "ProtocolEventRelationError",
    "compile_protocol_event_relations",
    "protocol_event_relations_schema",
    "validate_protocol_event_relations",
    "with_protocol_event_relations_schema",
]
