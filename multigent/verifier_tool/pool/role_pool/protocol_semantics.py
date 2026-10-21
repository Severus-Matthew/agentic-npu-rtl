"""Contract-local protocol semantics compiled into a safe, reusable event IR.

The Architect describes externally observable events.  Contract Review parses
the small boolean language below, resolves every identifier to an interface
signal or another declared event, rejects cycles, and inlines event references.
Runtime code therefore evaluates data, never Architect-authored Python.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from typing import Any, Mapping


class ProtocolSemanticsError(ValueError):
    """A contract-local protocol description is ambiguous or unsafe."""


def protocol_semantics_schema() -> dict[str, Any]:
    """Return the Architect-facing schema for contract-local protocol profiles."""

    event_ref = {"type": "string"}
    drive_assignment = {
        "type": "object", "additionalProperties": False,
        "required": ["signal", "value"],
        "properties": {
            "signal": {"type": "string", "minLength": 1},
            "value": {"type": "integer"},
        },
    }
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "name", "description", "protocol_groups", "clock",
                "events", "transactions", "flow_control", "cancellation",
                "custom_rules",
            ],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "description": {"type": "string", "minLength": 1},
                "protocol_groups": {
                    "type": "array", "minItems": 1, "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1},
                },
                "clock": {
                    "type": "object", "additionalProperties": False,
                    "required": ["signal", "edge"],
                    "properties": {
                        "signal": {"type": "string", "minLength": 1},
                        "edge": {"type": "string", "enum": ["rising", "falling"]},
                    },
                },
                "events": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": ["name", "expression", "description"],
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "expression": {"type": "string", "minLength": 1},
                            "description": {"type": "string", "minLength": 1},
                        },
                    },
                },
                "transactions": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": [
                            "name", "channel", "presented_event", "ready_event",
                            "accepted_event", "stalled_event", "completed_event",
                            "success_event", "error_event", "content_signals",
                            "stable_while_stalled", "stability_rules",
                            "source_drive",
                        ],
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "channel": {"type": "string", "minLength": 1},
                            "presented_event": event_ref,
                            "ready_event": event_ref,
                            "accepted_event": event_ref,
                            "stalled_event": event_ref,
                            "completed_event": event_ref,
                            "success_event": event_ref,
                            "error_event": event_ref,
                            "content_signals": {
                                "type": "array", "uniqueItems": True,
                                "items": {"type": "string", "minLength": 1},
                            },
                            "stable_while_stalled": {"type": "boolean"},
                            "stability_rules": {
                                "type": "array",
                                "items": {
                                    "type": "object", "additionalProperties": False,
                                    "required": ["id", "while_event", "signals"],
                                    "properties": {
                                        "id": {"type": "string", "minLength": 1},
                                        "while_event": {"type": "string", "minLength": 1},
                                        "signals": {
                                            "type": "array", "minItems": 1,
                                            "uniqueItems": True,
                                            "items": {"type": "string", "minLength": 1},
                                        },
                                    },
                                },
                            },
                            "source_drive": {
                                "type": ["object", "null"],
                                "additionalProperties": False,
                                "required": [
                                    "presented_assignments", "idle_assignments",
                                    "post_accept_assignments", "driven_fields",
                                    "completion_mode",
                                ],
                                "properties": {
                                    "presented_assignments": {
                                        "type": "array", "minItems": 1,
                                        "items": deepcopy(drive_assignment),
                                    },
                                    "idle_assignments": {
                                        "type": "array", "minItems": 1,
                                        "items": deepcopy(drive_assignment),
                                    },
                                    "post_accept_assignments": {
                                        "type": "array",
                                        "items": deepcopy(drive_assignment),
                                    },
                                    "driven_fields": {
                                        "type": "array", "uniqueItems": True,
                                        "items": {"type": "string", "minLength": 1},
                                    },
                                    "completion_mode": {
                                        "type": "string",
                                        "enum": [
                                            "return_after_acceptance",
                                            "wait_for_all_completions",
                                        ],
                                    },
                                },
                            },
                        },
                    },
                },
                "flow_control": {
                    "type": "object", "additionalProperties": False,
                    "required": ["maximum_outstanding", "ordering", "in_order"],
                    "properties": {
                        "maximum_outstanding": {"type": "integer", "minimum": 1},
                        "ordering": {
                            "type": "string",
                            "enum": ["oldest_outstanding", "unordered", "keyed"],
                        },
                        "in_order": {"type": "boolean"},
                    },
                },
                "cancellation": {
                    "type": "object", "additionalProperties": False,
                    "required": ["supported", "trigger_event", "pending_behavior"],
                    "properties": {
                        "supported": {"type": "boolean"},
                        "trigger_event": event_ref,
                        "pending_behavior": {
                            "type": "string",
                            "enum": ["not_applicable", "flush", "complete", "preserve"],
                        },
                    },
                },
                "custom_rules": {
                    "type": "array",
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": [
                            "id", "description", "required_observations",
                            "extension_request_id",
                        ],
                        "properties": {
                            "id": {"type": "string", "minLength": 1},
                            "description": {"type": "string", "minLength": 1},
                            "required_observations": {
                                "type": "array", "uniqueItems": True,
                                "items": {"type": "string", "minLength": 1},
                            },
                            "extension_request_id": {
                                "type": "string", "minLength": 1,
                            },
                        },
                    },
                },
            },
        },
    }


def with_protocol_semantics_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Expose optional protocol semantics in the effective Architect schema."""

    result = deepcopy(dict(schema))
    try:
        interface = result["properties"]["interface_contract"]
        properties = interface["properties"]
    except (KeyError, TypeError) as exc:
        raise ProtocolSemanticsError(
            "Architect schema needs interface_contract.properties"
        ) from exc
    properties["protocol_semantics"] = protocol_semantics_schema()
    return result


def _rewrite_expression(text: str) -> str:
    # ``!`` is allowed only as boolean NOT; ``!=`` remains a comparison token.
    result = text.replace("&&", " and ").replace("||", " or ")
    result = result.replace("!=", " __NE__ ").replace("!", " not ")
    return result.replace("__NE__", "!=").strip()


def _parse_expression(text: str) -> ast.AST:
    try:
        return ast.parse(_rewrite_expression(text), mode="eval").body
    except SyntaxError as exc:
        raise ProtocolSemanticsError(f"invalid event expression {text!r}: {exc.msg}") from exc


def _compile_node(
    node: ast.AST,
    *,
    signals: set[str],
    event_nodes: Mapping[str, ast.AST],
    stack: tuple[str, ...],
) -> dict[str, Any]:
    if isinstance(node, ast.Name):
        if node.id in signals:
            return {"signal": node.id}
        if node.id in event_nodes:
            if node.id in stack:
                cycle = " -> ".join((*stack, node.id))
                raise ProtocolSemanticsError(f"protocol event dependency cycle: {cycle}")
            return _compile_node(
                event_nodes[node.id], signals=signals, event_nodes=event_nodes,
                stack=(*stack, node.id),
            )
        if node.id.lower() in {"true", "false"}:
            return {"constant": node.id.lower() == "true"}
        raise ProtocolSemanticsError(
            f"event expression references undeclared signal/event {node.id!r}"
        )
    if isinstance(node, ast.Constant) and node.value in {0, 1, False, True}:
        return {"constant": bool(node.value)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return {
            "op": "not",
            "arg": _compile_node(
                node.operand, signals=signals, event_nodes=event_nodes, stack=stack
            ),
        }
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        return {
            "op": "and" if isinstance(node.op, ast.And) else "or",
            "args": [
                _compile_node(item, signals=signals, event_nodes=event_nodes, stack=stack)
                for item in node.values
            ],
        }
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        operator = node.ops[0]
        if not isinstance(operator, (ast.Eq, ast.NotEq)):
            raise ProtocolSemanticsError("only == and != comparisons are allowed")
        return {
            "op": "eq" if isinstance(operator, ast.Eq) else "ne",
            "left": _compile_node(
                node.left, signals=signals, event_nodes=event_nodes, stack=stack
            ),
            "right": _compile_node(
                node.comparators[0], signals=signals, event_nodes=event_nodes, stack=stack
            ),
        }
    raise ProtocolSemanticsError(
        "protocol expressions allow only signal/event names, !, &&, ||, ==, !=, 0, and 1"
    )


def compile_protocol_expression(
    text: str, *, signals: set[str] | tuple[str, ...] | list[str]
) -> dict[str, Any]:
    """Compile one signal-only protocol expression into the safe event IR.

    Contract-local protocol profiles may reference named events while they are
    being compiled.  Other declarative metadata, such as a cross-protocol event
    relation, intentionally receives only the physical signal namespace so it
    cannot depend on an implicit profile-local name.
    """

    return _compile_node(
        _parse_expression(text),
        signals=set(map(str, signals)),
        event_nodes={},
        stack=(),
    )


def expression_signals(expression: Mapping[str, Any]) -> tuple[str, ...]:
    """Return exact signal dependencies of one compiled expression."""

    result: list[str] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        if "signal" in value:
            result.append(str(value["signal"]))
        for child in value.values():
            if isinstance(child, Mapping):
                visit(child)
            elif isinstance(child, list):
                for item in child:
                    visit(item)

    visit(expression)
    return tuple(dict.fromkeys(result))


def evaluate_protocol_expression(
    expression: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> bool:
    """Evaluate a Contract-Reviewer-compiled event against one RTL snapshot."""

    if "signal" in expression:
        name = str(expression["signal"])
        if name not in snapshot:
            raise AssertionError(f"protocol expression is missing signal {name!r}")
        return bool(int(snapshot[name]))
    if "constant" in expression:
        return bool(expression["constant"])
    op = str(expression.get("op", ""))
    if op == "not":
        return not evaluate_protocol_expression(expression["arg"], snapshot)
    if op in {"and", "or"}:
        values = [evaluate_protocol_expression(item, snapshot) for item in expression["args"]]
        return all(values) if op == "and" else any(values)
    if op in {"eq", "ne"}:
        left = evaluate_protocol_expression(expression["left"], snapshot)
        right = evaluate_protocol_expression(expression["right"], snapshot)
        return left == right if op == "eq" else left != right
    raise AssertionError(f"unknown compiled protocol expression operator {op!r}")


def compile_protocol_semantics(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize every contract-local protocol profile."""

    declared_signals = {
        str(item.get("name", ""))
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("name")
    }
    declared_channels = {
        str(item.get("name", ""))
        for item in interface.get("channels", [])
        if isinstance(item, Mapping) and item.get("name")
    }
    profiles: list[dict[str, Any]] = []
    seen_profiles: set[str] = set()
    for raw in interface.get("protocol_semantics", []):
        if not isinstance(raw, Mapping):
            raise ProtocolSemanticsError("protocol_semantics entries must be mappings")
        name = str(raw.get("name", "")).strip()
        if not name or name in seen_profiles:
            raise ProtocolSemanticsError(f"duplicate or empty protocol semantics name {name!r}")
        seen_profiles.add(name)
        clock = raw.get("clock", {})
        clock_signal = str(clock.get("signal", "")) if isinstance(clock, Mapping) else ""
        if clock_signal not in declared_signals:
            raise ProtocolSemanticsError(
                f"protocol profile {name!r} references unknown clock {clock_signal!r}"
            )
        raw_events = raw.get("events", [])
        event_nodes: dict[str, ast.AST] = {}
        event_descriptions: dict[str, str] = {}
        for event in raw_events:
            if not isinstance(event, Mapping):
                raise ProtocolSemanticsError(f"protocol profile {name!r} has invalid event")
            event_name = str(event.get("name", "")).strip()
            if not event_name or event_name in event_nodes or event_name in declared_signals:
                raise ProtocolSemanticsError(
                    f"profile {name!r} event {event_name!r} is duplicate or collides with a signal"
                )
            event_nodes[event_name] = _parse_expression(str(event.get("expression", "")))
            event_descriptions[event_name] = str(event.get("description", ""))
        compiled_events = {
            event_name: {
                "expression": _compile_node(
                    node, signals=declared_signals, event_nodes=event_nodes,
                    stack=(event_name,),
                ),
                "description": event_descriptions[event_name],
            }
            for event_name, node in event_nodes.items()
        }

        def event_expression(event_name: object, *, required: bool = False) -> dict[str, Any] | None:
            identity = str(event_name or "")
            if not identity:
                if required:
                    raise ProtocolSemanticsError(
                        f"protocol profile {name!r} is missing a required event reference"
                    )
                return None
            if identity not in compiled_events:
                raise ProtocolSemanticsError(
                    f"protocol profile {name!r} references unknown event {identity!r}"
                )
            return deepcopy(compiled_events[identity]["expression"])

        transactions: list[dict[str, Any]] = []
        seen_transactions: set[str] = set()
        for transaction in raw.get("transactions", []):
            if not isinstance(transaction, Mapping):
                raise ProtocolSemanticsError(f"profile {name!r} has invalid transaction")
            tx_name = str(transaction.get("name", ""))
            channel = str(transaction.get("channel", ""))
            if not tx_name or tx_name in seen_transactions:
                raise ProtocolSemanticsError(f"profile {name!r} has duplicate transaction {tx_name!r}")
            if channel not in declared_channels:
                raise ProtocolSemanticsError(
                    f"transaction {tx_name!r} references unknown channel {channel!r}"
                )
            seen_transactions.add(tx_name)
            content = tuple(map(str, transaction.get("content_signals", [])))
            unknown = sorted(set(content) - declared_signals)
            if unknown:
                raise ProtocolSemanticsError(
                    f"transaction {tx_name!r} content references unknown signals {unknown}"
                )
            stability_rules: list[dict[str, Any]] = []
            for rule in transaction.get("stability_rules", []):
                if not isinstance(rule, Mapping):
                    raise ProtocolSemanticsError(
                        f"transaction {tx_name!r} has an invalid stability rule"
                    )
                signals = tuple(map(str, rule.get("signals", [])))
                unknown = sorted(set(signals) - declared_signals)
                if unknown:
                    raise ProtocolSemanticsError(
                        f"transaction {tx_name!r} stability rule references unknown signals {unknown}"
                    )
                stability_rules.append({
                    "id": str(rule.get("id", "")),
                    "while": event_expression(rule.get("while_event"), required=True),
                    "signals": signals,
                })
            channel_direction = next(
                str(item.get("direction", ""))
                for item in interface.get("channels", [])
                if isinstance(item, Mapping) and str(item.get("name", "")) == channel
            )
            source_drive = transaction.get("source_drive")
            if channel_direction == "input" and not isinstance(source_drive, Mapping):
                raise ProtocolSemanticsError(
                    f"input transaction {tx_name!r} requires source_drive bindings"
                )
            compiled_drive: dict[str, Any] | None = None
            if isinstance(source_drive, Mapping):
                presented_assignments = {
                    str(item.get("signal", "")): int(item.get("value", 0))
                    for item in source_drive.get("presented_assignments", [])
                    if isinstance(item, Mapping)
                }
                idle_assignments = {
                    str(item.get("signal", "")): int(item.get("value", 0))
                    for item in source_drive.get("idle_assignments", [])
                    if isinstance(item, Mapping)
                }
                post_accept_assignments = {
                    str(item.get("signal", "")): int(item.get("value", 0))
                    for item in source_drive.get("post_accept_assignments", [])
                    if isinstance(item, Mapping)
                }
                driven_fields = tuple(map(str, source_drive.get("driven_fields", [])))
                drive_signals = (
                    set(presented_assignments)
                    | set(idle_assignments)
                    | set(post_accept_assignments)
                    | set(driven_fields)
                )
                unknown = sorted(drive_signals - declared_signals)
                if unknown:
                    raise ProtocolSemanticsError(
                        f"transaction {tx_name!r} source_drive references unknown signals {unknown}"
                    )
                signal_directions = {
                    str(item.get("name", "")): str(item.get("direction", ""))
                    for item in interface.get("signals", []) if isinstance(item, Mapping)
                }
                not_inputs = sorted(
                    signal for signal in drive_signals
                    if signal_directions.get(signal) != "input"
                )
                if not_inputs:
                    raise ProtocolSemanticsError(
                        f"transaction {tx_name!r} source_drive attempts DUT output signals {not_inputs}"
                    )
                compiled_drive = {
                    "presented_assignments": presented_assignments,
                    "idle_assignments": idle_assignments,
                    "post_accept_assignments": post_accept_assignments,
                    "driven_fields": driven_fields,
                    "completion_mode": str(
                        source_drive.get("completion_mode", "return_after_acceptance")
                    ),
                }
                if (
                    compiled_drive["completion_mode"] == "wait_for_all_completions"
                    and not transaction.get("completed_event")
                ):
                    raise ProtocolSemanticsError(
                        f"transaction {tx_name!r} waits for completions but has no completed_event"
                    )
            transactions.append(
                {
                    "name": tx_name,
                    "channel": channel,
                    "presented": event_expression(transaction.get("presented_event"), required=True),
                    "ready": event_expression(transaction.get("ready_event"), required=True),
                    "accepted": event_expression(transaction.get("accepted_event"), required=True),
                    "stalled": event_expression(transaction.get("stalled_event")),
                    "completed": event_expression(transaction.get("completed_event")),
                    "success": event_expression(transaction.get("success_event")),
                    "error": event_expression(transaction.get("error_event")),
                    "content": content,
                    "stable_while_stalled": bool(transaction.get("stable_while_stalled", False)),
                    "stability_rules": stability_rules,
                    "source_drive": compiled_drive,
                }
            )
        cancellation = raw.get("cancellation", {})
        cancel_expression = (
            event_expression(cancellation.get("trigger_event"))
            if isinstance(cancellation, Mapping) else None
        )
        profiles.append(
            {
                "name": name,
                "description": str(raw.get("description", "")),
                "protocol_groups": tuple(map(str, raw.get("protocol_groups", []))),
                "clock": {"signal": clock_signal, "edge": str(clock.get("edge", "rising"))},
                "events": compiled_events,
                "transactions": transactions,
                "flow_control": deepcopy(dict(raw.get("flow_control", {}))),
                "cancellation": {
                    **(
                        deepcopy(dict(cancellation))
                        if isinstance(cancellation, Mapping)
                        else {}
                    ),
                    "trigger": cancel_expression,
                },
                "custom_rules": deepcopy(list(raw.get("custom_rules", []))),
            }
        )
    return {"schema_version": 1, "profiles": profiles}


def validate_protocol_semantics_extensions(
    architecture: Mapping[str, Any], interface: Mapping[str, Any]
) -> list[str]:
    """Require every residual custom rule to name a real protocol request."""

    requests = {
        str(item.get("id", "")): item
        for item in architecture.get("verification_extensions", [])
        if isinstance(item, Mapping) and item.get("domain") == "protocol"
    }
    errors: list[str] = []
    for profile in compile_protocol_semantics(interface).get("profiles", []):
        for rule in profile.get("custom_rules", []):
            request_id = str(rule.get("extension_request_id", ""))
            if request_id not in requests:
                errors.append(
                    f"protocol profile {profile['name']!r} custom rule "
                    f"{rule.get('id')!r} references missing protocol extension "
                    f"{request_id!r}"
                )
    return errors


__all__ = [
    "ProtocolSemanticsError",
    "compile_protocol_expression",
    "compile_protocol_semantics",
    "evaluate_protocol_expression",
    "expression_signals",
    "protocol_semantics_schema",
    "validate_protocol_semantics_extensions",
    "with_protocol_semantics_schema",
]
