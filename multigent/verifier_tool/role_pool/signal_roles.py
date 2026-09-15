"""Load and enforce the external signal-role taxonomy.

Role names and their rules intentionally live in YAML, not in Python.  Architect
and Verifier import this module so both stages consume the same vocabulary.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


SIGNAL_ROLE_TAXONOMY_PATH = Path(__file__).with_name("interface_signal_roles.yaml")
_CHANNEL_BINDINGS = {"required", "optional", "forbidden"}
_DIRECTION_RELATIONS = {"fixed", "same_as_channel", "opposite_to_channel"}
_DIRECTIONS = {"input", "output"}


@lru_cache(maxsize=1)
def load_signal_role_taxonomy() -> dict[str, Any]:
    """Return the validated taxonomy from its single YAML source of truth."""

    raw = yaml.safe_load(SIGNAL_ROLE_TAXONOMY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("roles"), dict):
        raise ValueError("Signal-role taxonomy must contain a roles mapping")

    roles = raw["roles"]
    if not roles:
        raise ValueError("Signal-role taxonomy must define at least one role")
    for role, spec in roles.items():
        if not isinstance(role, str) or not role.strip() or not isinstance(spec, dict):
            raise ValueError("Every signal role must be a named mapping")
        binding = spec.get("channel_binding")
        relation = spec.get("direction_relation")
        directions = spec.get("allowed_directions")
        if binding not in _CHANNEL_BINDINGS:
            raise ValueError(f"Signal role {role!r} has invalid channel_binding")
        if relation not in _DIRECTION_RELATIONS:
            raise ValueError(f"Signal role {role!r} has invalid direction_relation")
        if not isinstance(directions, list) or not set(directions) <= _DIRECTIONS:
            raise ValueError(f"Signal role {role!r} has invalid allowed_directions")
        if not isinstance(spec.get("description"), str) or not spec["description"].strip():
            raise ValueError(f"Signal role {role!r} needs a description")
        coverage_tags = spec.get("coverage_tags")
        if not isinstance(coverage_tags, list) or not all(
            isinstance(tag, str) and tag.strip() for tag in coverage_tags
        ):
            raise ValueError(f"Signal role {role!r} has invalid coverage_tags")
        if relation != "fixed" and binding == "forbidden":
            raise ValueError(
                f"Signal role {role!r} cannot derive direction without a channel"
            )
    return raw


def render_signal_role_catalog() -> str:
    """Render compact, model-facing instructions from the YAML taxonomy."""

    roles = load_signal_role_taxonomy()["roles"]
    lines: list[str] = []
    for role, spec in roles.items():
        directions = "/".join(spec["allowed_directions"])
        coverage_tags = ",".join(spec.get("coverage_tags", []))
        lines.append(
            f"- {role}: {spec['description']} "
            f"[channel={spec['channel_binding']}; direction={directions}; "
            f"relation={spec['direction_relation']}; coverage={coverage_tags}]"
        )
    return "\n".join(lines)


def signals_with_roles(
    signals: Sequence[Any], roles: set[str]
) -> set[str]:
    """Return signal names selected only by explicit contract roles."""

    return {
        str(signal["name"])
        for signal in signals
        if isinstance(signal, Mapping) and signal.get("role") in roles
    }


def signals_with_coverage_tags(
    signals: Sequence[Any], coverage_tags: set[str]
) -> set[str]:
    """Return signal names whose declared roles carry any requested tag."""

    role_specs = load_signal_role_taxonomy()["roles"]
    return {
        str(signal["name"])
        for signal in signals
        if isinstance(signal, Mapping)
        and signal.get("role") in role_specs
        and coverage_tags.intersection(role_specs[signal["role"]].get("coverage_tags", []))
    }


def validate_interface_signal_roles(interface: Mapping[str, Any]) -> list[str]:
    """Return deterministic errors for invalid signal-role assignments."""

    role_specs = load_signal_role_taxonomy()["roles"]
    channels = {
        str(channel.get("name")): str(channel.get("direction"))
        for channel in interface.get("channels", [])
        if isinstance(channel, Mapping)
    }
    signals = list(interface.get("signals", []))
    errors: list[str] = []

    signal_names = [
        str(signal.get("name"))
        for signal in signals
        if isinstance(signal, Mapping)
    ]
    if len(signal_names) != len(set(signal_names)):
        errors.append("duplicate interface signal names")

    by_name: dict[str, Mapping[str, Any]] = {}
    for signal in signals:
        if not isinstance(signal, Mapping):
            errors.append("interface signal is not a mapping")
            continue
        name = str(signal.get("name", ""))
        role = str(signal.get("role", ""))
        direction = str(signal.get("direction", ""))
        channel_value = signal.get("channel")
        channel = str(channel_value).strip() if channel_value is not None else ""
        by_name[name] = signal

        spec = role_specs.get(role)
        if spec is None:
            errors.append(f"signal {name} uses unknown role {role!r}")
            continue
        if direction not in spec["allowed_directions"]:
            errors.append(
                f"signal {name} role {role} does not allow direction {direction!r}"
            )

        binding = spec["channel_binding"]
        if binding == "required" and not channel:
            errors.append(f"signal {name} role {role} requires a channel")
            continue
        if binding == "forbidden" and channel:
            errors.append(f"signal {name} role {role} forbids a channel")
            continue
        if channel and channel not in channels:
            errors.append(f"signal {name} references unknown channel {channel}")
            continue

        relation = spec["direction_relation"]
        if channel and relation in {"same_as_channel", "opposite_to_channel"}:
            expected = channels[channel]
            if relation == "opposite_to_channel":
                expected = "output" if expected == "input" else "input"
            if direction != expected:
                errors.append(
                    f"signal {name} role {role} must be {expected} for "
                    f"{channels[channel]} channel {channel}"
                )

        if role == "reset":
            semantic = str(signal.get("semantic", "")).lower().replace("_", "-")
            declares_active_low = "active-low" in semantic or "active low" in semantic
            declares_active_high = "active-high" in semantic or "active high" in semantic
            if declares_active_low == declares_active_high:
                errors.append(
                    f"signal {name} role reset semantic must declare exactly one of "
                    "active-high or active-low"
                )

    for role, spec in role_specs.items():
        reference = spec.get("interface_reference")
        if not reference:
            continue
        referenced_name = str(interface.get(reference, ""))
        signal = by_name.get(referenced_name)
        if signal is None:
            errors.append(
                f"interface {reference} references missing signal {referenced_name!r}"
            )
        elif signal.get("role") != role:
            errors.append(
                f"interface {reference} signal {referenced_name} must have role {role}"
            )

    return errors
