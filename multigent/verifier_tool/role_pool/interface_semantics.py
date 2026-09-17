"""Load semantic-class and protocol-profile taxonomies for interfaces."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml


INTERFACE_SEMANTIC_TAXONOMY_PATH = Path(__file__).with_name(
    "interface_semantic_classes.yaml"
)
INTERFACE_PROTOCOL_TAXONOMY_PATH = Path(__file__).with_name(
    "interface_protocol_profiles.yaml"
)


def _load_mapping(path: Path, key: str) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get(key), dict) or not raw[key]:
        raise ValueError(f"{path.name} must contain a non-empty {key} mapping")
    for name, spec in raw[key].items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise ValueError(f"{path.name} contains an invalid {key} entry")
        if not isinstance(spec.get("description"), str):
            raise ValueError(f"{path.name} entry {name!r} needs a description")
        tags = spec.get("coverage_tags")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"{path.name} entry {name!r} has invalid coverage_tags")
    return raw


@lru_cache(maxsize=1)
def load_interface_semantic_taxonomy() -> dict[str, Any]:
    raw = _load_mapping(INTERFACE_SEMANTIC_TAXONOMY_PATH, "semantic_classes")
    from .signal_roles import load_signal_role_taxonomy

    known_roles = set(load_signal_role_taxonomy()["roles"])
    binding = raw.get("role_binding")
    if not isinstance(binding, dict):
        raise ValueError("Semantic taxonomy must contain role_binding")
    binding_sets: list[set[str]] = []
    for kind in ("required", "optional", "forbidden"):
        values = binding.get(kind)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"Semantic taxonomy role_binding.{kind} must be a list")
        binding_sets.append(set(values))
    if set.union(*binding_sets) != known_roles or sum(map(len, binding_sets)) != len(known_roles):
        raise ValueError(
            "Semantic taxonomy must classify every signal role exactly once"
        )
    for name, spec in raw["semantic_classes"].items():
        allowed_roles = spec.get("allowed_roles")
        if not isinstance(allowed_roles, list) or not set(allowed_roles) <= known_roles:
            raise ValueError(f"Semantic class {name!r} has invalid allowed_roles")
    return raw


@lru_cache(maxsize=1)
def load_interface_protocol_taxonomy() -> dict[str, Any]:
    return _load_mapping(INTERFACE_PROTOCOL_TAXONOMY_PATH, "protocol_profiles")


def render_interface_semantic_catalog() -> str:
    taxonomy = load_interface_semantic_taxonomy()
    classes = taxonomy["semantic_classes"]
    lines = ["Semantic classes:"]
    for name, spec in classes.items():
        roles = "/".join(spec["allowed_roles"])
        tags = ",".join(spec["coverage_tags"])
        lines.append(
            f"- {name}: {spec['description']} [roles={roles}; coverage={tags}]"
        )

    lines.append("Protocol profiles:")
    for name, spec in load_interface_protocol_taxonomy()["protocol_profiles"].items():
        tags = ",".join(spec["coverage_tags"])
        lines.append(f"- {name}: {spec['description']} [coverage={tags}]")
    return "\n".join(lines)


def validate_interface_semantics(interface: Mapping[str, Any]) -> list[str]:
    """Validate semantic-class bindings and per-channel protocol profiles."""

    semantic_taxonomy = load_interface_semantic_taxonomy()
    classes = semantic_taxonomy["semantic_classes"]
    binding = semantic_taxonomy["role_binding"]
    profiles = load_interface_protocol_taxonomy()["protocol_profiles"]
    errors: list[str] = []

    for channel in interface.get("channels", []):
        if not isinstance(channel, Mapping):
            continue
        name = str(channel.get("name", ""))
        profile = str(channel.get("protocol_profile", ""))
        if profile not in profiles:
            errors.append(
                f"channel {name} uses unknown protocol_profile {profile!r}"
            )

    for signal in interface.get("signals", []):
        if not isinstance(signal, Mapping):
            continue
        name = str(signal.get("name", ""))
        role = str(signal.get("role", ""))
        semantic_value = signal.get("semantic_class")
        semantic_class = (
            str(semantic_value).strip() if semantic_value is not None else ""
        )

        if role in binding["required"] and not semantic_class:
            errors.append(f"signal {name} role {role} requires a semantic_class")
            continue
        if role in binding["forbidden"] and semantic_class:
            errors.append(f"signal {name} role {role} forbids a semantic_class")
            continue
        if not semantic_class:
            continue

        spec = classes.get(semantic_class)
        if spec is None:
            errors.append(
                f"signal {name} uses unknown semantic_class {semantic_class!r}"
            )
        elif role not in spec["allowed_roles"]:
            errors.append(
                f"signal {name} semantic_class {semantic_class} does not allow role {role}"
            )
    return errors


def derive_interface_coverage_seed(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Derive name-independent coverage tags from the three taxonomy axes."""

    from .signal_roles import load_signal_role_taxonomy

    role_specs = load_signal_role_taxonomy()["roles"]
    class_specs = load_interface_semantic_taxonomy()["semantic_classes"]
    profile_specs = load_interface_protocol_taxonomy()["protocol_profiles"]

    channel_tags: dict[str, list[str]] = {}
    for channel in interface.get("channels", []):
        if not isinstance(channel, Mapping):
            continue
        profile = profile_specs.get(channel.get("protocol_profile"), {})
        channel_tags[str(channel.get("name", ""))] = sorted(
            set(profile.get("coverage_tags", []))
        )

    signal_tags: dict[str, list[str]] = {}
    for signal in interface.get("signals", []):
        if not isinstance(signal, Mapping):
            continue
        tags = set(role_specs.get(signal.get("role"), {}).get("coverage_tags", []))
        semantic_class = signal.get("semantic_class")
        if semantic_class:
            tags.update(class_specs.get(semantic_class, {}).get("coverage_tags", []))
        signal_tags[str(signal.get("name", ""))] = sorted(tags)

    return {"channels": channel_tags, "signals": signal_tags}
