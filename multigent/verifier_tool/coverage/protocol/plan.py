"""Instantiate deterministic coverage obligations from an interface contract."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.verifier_tool.role_pool.interface_semantics import (
    load_interface_protocol_taxonomy,
)


INTERFACE_COVERAGE_TEMPLATES_PATH = Path(__file__).with_name("templates.yaml")


@lru_cache(maxsize=1)
def load_interface_coverage_templates() -> dict[str, Any]:
    raw = yaml.safe_load(
        INTERFACE_COVERAGE_TEMPLATES_PATH.read_text(encoding="utf-8")
    )
    if not isinstance(raw, dict) or not isinstance(raw.get("templates"), dict):
        raise ValueError("Interface coverage taxonomy must contain templates")
    for name, template in raw["templates"].items():
        if not isinstance(template, dict) or template.get("scope") not in {
            "signal",
            "channel",
        }:
            raise ValueError(f"Coverage template {name!r} has invalid scope")
        if not isinstance(template.get("match"), dict):
            raise ValueError(f"Coverage template {name!r} needs match rules")
        bins = template.get("bins")
        if not isinstance(bins, list) or not bins:
            raise ValueError(f"Coverage template {name!r} needs bins")
    return raw


def _safe_id(value: object) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value)).strip("_").lower()
    return normalized or "unnamed"


def _signal_matches(signal: Mapping[str, Any], match: Mapping[str, Any]) -> bool:
    return all(signal.get(key) == value for key, value in match.items())


def _channel_role_index(
    signals: list[Mapping[str, Any]], channel_name: str
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for signal in signals:
        if signal.get("channel") != channel_name:
            continue
        result.setdefault(str(signal.get("role")), []).append(str(signal.get("name")))
    return result


def _channel_class_index(
    signals: list[Mapping[str, Any]], channel_name: str
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for signal in signals:
        if signal.get("channel") != channel_name or not signal.get("semantic_class"):
            continue
        result.setdefault(str(signal["semantic_class"]), []).append(str(signal.get("name")))
    return result


def _obligation(
    *, template_name: str, template: Mapping[str, Any], scope: str,
    scope_name: str, bindings: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "id": f"{scope}.{_safe_id(scope_name)}.{template_name}",
        "template": template_name,
        "scope": scope,
        "scope_name": scope_name,
        "description": template["description"],
        "bindings": dict(bindings),
        "bins": list(template["bins"]),
    }


def _reset_active_value(signal: Mapping[str, Any]) -> int | None:
    semantic = str(signal.get("semantic", "")).lower().replace("_", "-")
    if "active-low" in semantic or "active low" in semantic:
        return 0
    if "active-high" in semantic or "active high" in semantic:
        return 1
    return None


def build_interface_coverage_plan(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Build stable obligations by applying templates to explicit contract fields."""

    templates = load_interface_coverage_templates()["templates"]
    profiles = load_interface_protocol_taxonomy()["protocol_profiles"]
    signals = [item for item in interface.get("signals", []) if isinstance(item, Mapping)]
    channels = [item for item in interface.get("channels", []) if isinstance(item, Mapping)]
    channels_by_name = {str(item.get("name", "")): item for item in channels}
    obligations: list[dict[str, Any]] = []

    for template_name, template in templates.items():
        match = template["match"]
        if template["scope"] == "signal":
            for signal in signals:
                if _signal_matches(signal, match):
                    # An arbitrary configuration index may legitimately use the
                    # semantic class ``address`` without byte-address alignment
                    # rules.  Instantiate address coverage only when the selected
                    # channel protocol explicitly carries the alignment tag.
                    if template_name == "address_alignment":
                        channel = channels_by_name.get(str(signal.get("channel", "")), {})
                        profile_name = str(channel.get("protocol_profile", ""))
                        profile_tags = set(
                            profiles.get(profile_name, {}).get("coverage_tags", [])
                        )
                        if "alignment" not in profile_tags:
                            continue
                    obligations.append(
                        _obligation(
                            template_name=template_name,
                            template=template,
                            scope="signal",
                            scope_name=str(signal.get("name", "")),
                            bindings={
                                "signal": str(signal.get("name", "")),
                                **(
                                    {"active_value": _reset_active_value(signal)}
                                    if template_name == "reset_behavior"
                                    else {}
                                ),
                                **(
                                    {"width": str(signal.get("width", ""))}
                                    if template_name == "address_alignment"
                                    else {}
                                ),
                            },
                        )
                    )
            continue

        for channel in channels:
            channel_name = str(channel.get("name", ""))
            profile_name = str(channel.get("protocol_profile", ""))
            profile_tags = set(profiles.get(profile_name, {}).get("coverage_tags", []))
            if match.get("coverage_tag") not in {None, *profile_tags}:
                continue
            if match.get("protocol_profile") not in {None, profile_name}:
                continue

            roles = _channel_role_index(signals, channel_name)
            classes = _channel_class_index(signals, channel_name)
            required_roles = list(match.get("required_roles", []))
            required_classes = list(match.get("required_semantic_classes", []))
            if any(not roles.get(role) for role in required_roles):
                continue
            if any(not classes.get(value) for value in required_classes):
                continue

            bindings: dict[str, Any] = {
                role: roles[role][0] for role in required_roles
            }
            for role in match.get("observed_roles", []):
                if roles.get(role):
                    bindings[role] = list(roles[role])
            for semantic_class in required_classes:
                bindings[semantic_class] = list(classes[semantic_class])
            obligations.append(
                _obligation(
                    template_name=template_name,
                    template=template,
                    scope="channel",
                    scope_name=channel_name,
                    bindings=bindings,
                )
            )

    obligations.sort(key=lambda item: item["id"])
    clocks = [str(item.get("name")) for item in signals if item.get("role") == "clock"]
    resets = [str(item.get("name")) for item in signals if item.get("role") == "reset"]
    return {
        "schema_version": 2,
        "source": "frozen interface contract + interface_coverage_templates.yaml",
        "monitor": {
            "clock": str(interface.get("clock") or (clocks[0] if clocks else "")),
            "reset": str(interface.get("reset") or (resets[0] if resets else "")),
            # The TB captures this complete declared interface once per sampling
            # event. Assertions and coverage then share the same immutable values.
            "signals": [str(item.get("name")) for item in signals],
        },
        "obligations": obligations,
    }
