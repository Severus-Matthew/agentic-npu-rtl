"""Closed verification-tag registry and contract-local vocabulary validation."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator


TAG_POOL_PATH = Path(__file__).with_name("verification_tags.yaml")
DOMAINS = {"protocol", "lifecycle", "operation"}
SCOPES = {"interface", "protocol_group", "channel", "signal", "operation", "data_object"}
SOURCES = {"signal_role", "semantic_class", "protocol_profile", "feature_catalog", "contract_local"}


def verification_vocabulary_schema() -> dict[str, Any]:
    tag_definition = {
        "type": "object",
        "additionalProperties": False,
        "required": ["description", "domains", "allowed_scopes"],
        "properties": {
            "description": {"type": "string", "minLength": 1},
            "domains": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"enum": sorted(DOMAINS)},
            },
            "allowed_scopes": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"enum": sorted(SCOPES)},
            },
            "required_observations": {
                "type": "array", "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }
    role_definition = {
        "type": "object", "additionalProperties": False,
        "required": [
            "description", "category", "channel_binding", "direction_relation",
            "allowed_directions", "semantic_class_binding", "coverage_tags",
        ],
        "properties": {
            "description": {"type": "string", "minLength": 1},
            "category": {"type": "string", "minLength": 1},
            "channel_binding": {"enum": ["required", "optional", "forbidden"]},
            "direction_relation": {"enum": ["fixed", "same_as_channel", "opposite_to_channel"]},
            "allowed_directions": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"enum": ["input", "output"]},
            },
            "semantic_class_binding": {"enum": ["required", "optional", "forbidden"]},
            "coverage_tags": {
                "type": "array", "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }
    semantic_definition = {
        "type": "object", "additionalProperties": False,
        "required": ["description", "allowed_roles", "coverage_tags"],
        "properties": {
            "description": {"type": "string", "minLength": 1},
            "allowed_roles": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            },
            "coverage_tags": {
                "type": "array", "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }

    def entries(definition: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "type": "array", "uniqueItems": True,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["name", "definition"],
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                    "definition": dict(definition),
                },
            },
        }

    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "signal_roles": entries(role_definition),
            "semantic_classes": entries(semantic_definition),
            "tags": entries(tag_definition),
        },
        "minProperties": 1,
    }


@lru_cache(maxsize=1)
def load_verification_tag_pool() -> dict[str, Any]:
    raw = yaml.safe_load(TAG_POOL_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or not isinstance(raw.get("tags"), Mapping):
        raise ValueError("verification_tags.yaml needs a tags mapping")
    defaults = dict(raw.get("tag_defaults", {}))
    tags: dict[str, dict[str, Any]] = {}
    for name, value in raw["tags"].items():
        if not isinstance(name, str) or not isinstance(value, Mapping):
            raise ValueError("verification tag entries must be named mappings")
        spec = {**defaults, **dict(value)}
        if not str(spec.get("description", "")).strip():
            raise ValueError(f"verification tag {name!r} needs a description")
        domains = set(map(str, spec.get("domains", [])))
        scopes = set(map(str, spec.get("allowed_scopes", [])))
        sources = set(map(str, spec.get("allowed_sources", [])))
        if not domains or not domains <= DOMAINS:
            raise ValueError(f"verification tag {name!r} has invalid domains")
        if not scopes or not scopes <= SCOPES:
            raise ValueError(f"verification tag {name!r} has invalid allowed_scopes")
        if not sources or not sources <= SOURCES:
            raise ValueError(f"verification tag {name!r} has invalid allowed_sources")
        tags[name] = {
            **spec,
            "domains": sorted(domains),
            "allowed_scopes": sorted(scopes),
            "allowed_sources": sorted(sources),
        }
    return {**dict(raw), "tags": tags}


def _entries(raw: object, field: str) -> dict[str, dict[str, Any]]:
    if raw is None:
        return {}
    if not isinstance(raw, list):
        raise ValueError(f"verification_vocabulary.{field} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"verification_vocabulary.{field}[{index}] must be a mapping")
        name = str(item.get("name", ""))
        if name in result:
            raise ValueError(f"verification_vocabulary.{field} duplicates {name!r}")
        result[name] = deepcopy(dict(item.get("definition", {})))
    return result


def contract_vocabulary_extensions(
    architecture: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return all contract-local roles, semantic classes, and tags.

    Top-level plural vocabulary is authoritative. The older one-definition-per-
    request form remains readable so existing frozen contracts do not break.
    """

    raw = architecture.get("verification_vocabulary", {})
    if raw is None:
        raw = {}
    errors = list(Draft202012Validator(verification_vocabulary_schema()).iter_errors(raw)) if raw else []
    if errors:
        raise ValueError("; ".join(error.message for error in errors))
    roles = _entries(raw.get("signal_roles"), "signal_roles") if isinstance(raw, Mapping) else {}
    classes = _entries(raw.get("semantic_classes"), "semantic_classes") if isinstance(raw, Mapping) else {}
    tags = _entries(raw.get("tags"), "tags") if isinstance(raw, Mapping) else {}
    for request in architecture.get("verification_extensions", []):
        if not isinstance(request, Mapping):
            continue
        legacy = request.get("contract_vocabulary")
        if not isinstance(legacy, Mapping):
            continue
        target = roles if legacy.get("pool") == "signal_role" else classes
        name = str(legacy.get("name", ""))
        if name in target:
            raise ValueError(f"contract vocabulary duplicates {name!r}")
        target[name] = deepcopy(dict(legacy.get("definition", {})))
    return roles, classes, tags


def validate_builtin_tag_references() -> list[str]:
    """Require every tag used by a code-owned taxonomy to exist in the pool."""

    from multigent.verifier_tool.pool.role_pool.interface_semantics import (
        load_interface_protocol_taxonomy,
        load_interface_semantic_taxonomy,
    )
    from multigent.verifier_tool.pool.role_pool.signal_roles import (
        load_signal_role_taxonomy,
    )

    known = set(load_verification_tag_pool()["tags"])
    errors: list[str] = []
    sources = (
        ("signal_role", load_signal_role_taxonomy()["roles"]),
        ("semantic_class", load_interface_semantic_taxonomy()["semantic_classes"]),
        ("protocol_profile", load_interface_protocol_taxonomy()["protocol_profiles"]),
    )
    for source, entries in sources:
        for name, spec in entries.items():
            for tag in map(str, spec.get("coverage_tags", [])):
                if tag not in known:
                    errors.append(f"{source} {name!r} references unknown verification tag {tag!r}")
                elif source not in load_verification_tag_pool()["tags"][tag]["allowed_sources"]:
                    errors.append(f"verification tag {tag!r} does not allow source {source}")
    return errors


def validate_contract_vocabulary(
    architecture: Mapping[str, Any], interface: Mapping[str, Any],
) -> list[str]:
    """Validate plural local vocabulary, tag ownership, and non-orphan use."""

    from multigent.verifier_tool.pool.role_pool.interface_semantics import (
        load_interface_semantic_taxonomy,
    )
    from multigent.verifier_tool.pool.role_pool.signal_roles import (
        load_signal_role_taxonomy,
    )

    try:
        roles, classes, tags = contract_vocabulary_extensions(architecture)
    except ValueError as exc:
        return [str(exc)]
    errors = validate_builtin_tag_references()
    builtins = load_verification_tag_pool()["tags"]
    known_roles = set(load_signal_role_taxonomy()["roles"])
    known_classes = set(load_interface_semantic_taxonomy()["semantic_classes"])
    for name in roles:
        if name in known_roles:
            errors.append(f"signal role {name!r} is already built in; use the pool entry")
    for name in classes:
        if name in known_classes:
            errors.append(f"semantic class {name!r} is already built in; use the pool entry")
    for name, definition in tags.items():
        if name in builtins:
            errors.append(f"verification tag {name!r} is already built in; use the pool entry")
        domains = set(map(str, definition.get("domains", [])))
        scopes = set(map(str, definition.get("allowed_scopes", [])))
        if not str(definition.get("description", "")).strip():
            errors.append(f"contract-local verification tag {name!r} needs a description")
        if not domains or not domains <= DOMAINS:
            errors.append(f"contract-local verification tag {name!r} has invalid domains")
        if not scopes or not scopes <= SCOPES:
            errors.append(f"contract-local verification tag {name!r} has invalid allowed_scopes")
    known_tags = set(builtins) | set(tags)
    known_profiles = set()
    from multigent.verifier_tool.pool.role_pool.interface_semantics import (
        load_interface_protocol_taxonomy,
    )

    known_profiles.update(load_interface_protocol_taxonomy()["protocol_profiles"])
    used_tags: set[str] = set()
    for definition in [*roles.values(), *classes.values()]:
        for tag in map(str, definition.get("coverage_tags", [])):
            used_tags.add(tag)
            if tag not in known_tags:
                errors.append(f"contract vocabulary references unknown verification tag {tag!r}")
    for request in architecture.get("verification_extensions", []):
        if not isinstance(request, Mapping):
            continue
        domain = str(request.get("domain", ""))
        scope = str(request.get("target", {}).get("scope", ""))
        match = request.get("match", {})
        if not isinstance(match, Mapping):
            continue
        unknown_roles = sorted(
            set(map(str, match.get("required_roles", [])))
            - (known_roles | set(roles))
        )
        if unknown_roles:
            errors.append(
                f"extension request {request.get('id')!r} match names unknown "
                f"signal role(s) {unknown_roles}"
            )
        unknown_classes = sorted(
            set(map(str, match.get("required_semantic_classes", [])))
            - (known_classes | set(classes))
        )
        if unknown_classes:
            errors.append(
                f"extension request {request.get('id')!r} match names unknown "
                f"semantic class(es) {unknown_classes}"
            )
        unknown_profiles = sorted(
            set(map(str, match.get("required_protocol_profiles", [])))
            - known_profiles
        )
        if unknown_profiles:
            errors.append(
                f"extension request {request.get('id')!r} match names unknown "
                f"protocol profile(s) {unknown_profiles}"
            )
        for tag_ref in match.get("tags", []):
            if not isinstance(tag_ref, Mapping):
                continue
            name, source = str(tag_ref.get("name", "")), str(tag_ref.get("source", ""))
            used_tags.add(name)
            if source == "builtin" and name not in builtins:
                errors.append(f"extension request {request.get('id')!r} names unknown built-in tag {name!r}")
            elif source == "contract_local" and name not in tags:
                errors.append(f"extension request {request.get('id')!r} names undeclared local tag {name!r}")
            spec = builtins.get(name, tags.get(name, {}))
            if spec and domain not in set(map(str, spec.get("domains", []))):
                errors.append(f"verification tag {name!r} does not apply to domain {domain!r}")
            if spec and scope not in set(map(str, spec.get("allowed_scopes", []))):
                errors.append(f"verification tag {name!r} does not allow scope {scope!r}")
    for name in sorted(set(tags) - used_tags):
        errors.append(f"contract-local verification tag {name!r} is not used by any role, semantic class, or extension request")
    declared_roles = {str(item.get("role", "")) for item in interface.get("signals", []) if isinstance(item, Mapping)}
    declared_classes = {str(item.get("semantic_class", "")) for item in interface.get("signals", []) if isinstance(item, Mapping)}
    for name in sorted(set(roles) - declared_roles):
        errors.append(f"contract-local signal role {name!r} is not used by any interface signal")
    for name in sorted(set(classes) - declared_classes):
        errors.append(f"contract-local semantic class {name!r} is not used by any interface signal")
    allowed_roles = known_roles | set(roles)
    for name, definition in classes.items():
        unknown = sorted(set(map(str, definition.get("allowed_roles", []))) - allowed_roles)
        if unknown:
            errors.append(f"semantic class extension {name!r} has unknown allowed_roles {unknown}")
    return errors


__all__ = [
    "TAG_POOL_PATH",
    "contract_vocabulary_extensions",
    "load_verification_tag_pool",
    "validate_builtin_tag_references",
    "validate_contract_vocabulary",
    "verification_vocabulary_schema",
]
