"""Normalized Architect-request/Verifier-implementation extension boundary.

This package deliberately stops before qualification or promotion.  A bundle is
Verifier-owned evidence describing one contract-local implementation; it is not a
new pool entry and never mutates verifier_tool source at runtime.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent
REQUEST_SCHEMA_PATH = ROOT / "extension_request.schema.json"
BUNDLE_SCHEMA_PATH = ROOT / "extension_bundle.schema.json"
EXAMPLES_PATH = ROOT / "examples.yaml"


class FeatureExtensionError(ValueError):
    """An extension request or Verifier-authored bundle is not auditable."""


@lru_cache(maxsize=2)
def _load_schema(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def extension_request_schema() -> dict[str, Any]:
    return deepcopy(_load_schema(REQUEST_SCHEMA_PATH))


def extension_bundle_schema() -> dict[str, Any]:
    return deepcopy(_load_schema(BUNDLE_SCHEMA_PATH))


def with_architect_extension_request_schema(
    schema: Mapping[str, Any], *, required: bool = False,
) -> dict[str, Any]:
    """Add contract-level extension requests without copying them into base schema."""

    result = deepcopy(dict(schema))
    try:
        architecture = result["properties"]["architecture_contract"]
        properties = architecture["properties"]
    except (KeyError, TypeError) as exc:
        raise FeatureExtensionError(
            "Architect schema needs architecture_contract.properties"
        ) from exc
    properties["verification_extensions"] = {
        "type": "array",
        "items": extension_request_schema(),
        "description": (
            "Only contract-required behavior absent from the closed verifier_tool pools. "
            "Architect declares meaning and target; Verifier owns implementation."
        ),
    }
    from multigent.verifier_tool.pool.tag_pool import verification_vocabulary_schema

    properties["verification_vocabulary"] = {
        **verification_vocabulary_schema(),
        "description": (
            "Contract-local roles, semantic classes, and verification tags that are "
            "absent from the closed pools. Definitions remain local and are never promoted."
        ),
    }
    fields = list(architecture.get("required", []))
    if required and "verification_extensions" not in fields:
        fields.append("verification_extensions")
    architecture["required"] = fields
    return result


def with_verifier_extension_bundle_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Add an OpenAI-strict transport for contract-local Verifier bundles.

    Canonical bundles intentionally contain free-form JSON mappings for bindings,
    parameters, and predicates. OpenAI strict structured outputs reject dynamic
    object keys, so only the API boundary serializes those mappings as JSON
    strings. :func:`decode_verifier_extension_transport` restores the canonical
    bundle before any persistence or semantic validation. The internal bundle
    schema and every saved artifact therefore remain unchanged.
    """

    result = deepcopy(dict(schema))
    try:
        properties = result["properties"]
    except (KeyError, TypeError) as exc:
        raise FeatureExtensionError("Verifier schema needs root properties") from exc
    implementation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "name", "file", "symbol"],
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["verifier_python", "protocol_driver"],
            },
            "name": {"type": "string", "minLength": 1},
            "file": {
                "type": ["string", "null"],
                "pattern": "^(reference|tests)/[^/]+\\.py$",
                "description": (
                    "Exact path of a Python file also emitted in test_files or "
                    "reference_model_files. Only one-level reference/*.py or "
                    "tests/*.py paths are valid; never use verification/*.py."
                ),
            },
            "symbol": {
                "type": ["string", "null"],
                "description": "Generated module-level symbol, or null when not applicable.",
            },
        },
    }
    branch_properties = {
        "implementation": implementation,
        "parameters": {
            "type": "string",
            "description": "A JSON-encoded object of branch parameters; use '{}' when empty.",
        },
    }
    branch_required = ["implementation", "parameters"]
    assertion_properties = deepcopy(branch_properties)
    assertion_properties["implementation"]["properties"]["kind"]["enum"] = [
        "verifier_python"
    ]
    coverage_properties = deepcopy(assertion_properties)
    stimulus_properties = deepcopy(branch_properties)
    stimulus_properties["implementation"]["properties"]["kind"]["enum"] = [
        "verifier_python", "protocol_driver"
    ]
    properties["feature_extensions"] = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "schema_version", "request_id", "id", "domain", "feature_name",
                "target", "description", "bindings", "reuse", "assertion",
                "coverage", "stimulus",
            ],
            "properties": {
                "schema_version": {"type": "integer", "const": 1},
                "request_id": {"type": "string", "minLength": 1},
                "id": {"type": "string", "minLength": 1},
                "domain": {
                    "type": "string",
                    "enum": ["protocol", "lifecycle", "operation"],
                },
                "feature_name": {"type": "string", "minLength": 1},
                "target": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["scope", "name"],
                    "properties": {
                        "scope": {"type": "string", "minLength": 1},
                        "name": {"type": "string", "minLength": 1},
                    },
                },
                "description": {"type": "string", "minLength": 1},
                "bindings": {
                    "type": "string",
                    "description": (
                        "A JSON-encoded non-empty object mapping every Architect-required "
                        "observation name to its concrete binding."
                    ),
                },
                "reuse": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["based_on_features", "helpers"],
                    "properties": {
                        "based_on_features": {
                            "type": "array", "items": {"type": "string"},
                        },
                        "helpers": {
                            "type": "array", "items": {"type": "string"},
                        },
                    },
                },
                "assertion": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": branch_required,
                    "properties": assertion_properties,
                },
                "coverage": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [*branch_required, "bins"],
                    "properties": {
                        **coverage_properties,
                        "bins": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "intent", "predicate"],
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "intent": {"type": "string", "minLength": 1},
                                    "predicate": {
                                        "type": "string",
                                        "description": "A JSON-encoded non-empty predicate object.",
                                    },
                                },
                            },
                        },
                    },
                },
                "stimulus": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [*branch_required, "scenarios"],
                    "properties": {
                        **stimulus_properties,
                        "scenarios": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "intent", "parameters"],
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "intent": {"type": "string", "minLength": 1},
                                    "parameters": {
                                        "type": "string",
                                        "description": "A JSON-encoded scenario parameter object.",
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        "description": (
            "Verifier-authored, contract-local implementations for Architect extension "
            "requests. Dynamic mappings use JSON strings only in this API transport; "
            "the runtime decodes them before validation and persistence."
        ),
    }
    required = list(result.get("required", []))
    if "feature_extensions" not in required:
        required.append("feature_extensions")
    result["required"] = required
    return result


def _decode_json_object(value: object, *, location: str, nonempty: bool = False) -> dict[str, Any]:
    if isinstance(value, Mapping):
        decoded = dict(value)
    elif isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise FeatureExtensionError(
                f"{location} must be a JSON-encoded object: {exc.msg}"
            ) from exc
        if not isinstance(decoded, dict):
            raise FeatureExtensionError(f"{location} must decode to an object")
    else:
        raise FeatureExtensionError(f"{location} must be an object or JSON-object string")
    if nonempty and not decoded:
        raise FeatureExtensionError(f"{location} must not be empty")
    return decoded


def decode_verifier_extension_transport(result: Mapping[str, Any]) -> dict[str, Any]:
    """Decode strict-API bundle strings into the canonical internal shape.

    The operation is idempotent so locally authored canonical results and review
    drafts can pass through the same Verifier code path safely.
    """

    decoded_result = deepcopy(dict(result))
    bundles = decoded_result.get("feature_extensions", [])
    if not isinstance(bundles, list):
        raise FeatureExtensionError("feature_extensions must be a list")
    for bundle_index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            raise FeatureExtensionError(
                f"feature_extensions[{bundle_index}] must be an object"
            )
        prefix = f"feature_extensions[{bundle_index}]"
        bundle["bindings"] = _decode_json_object(
            bundle.get("bindings"), location=f"{prefix}.bindings", nonempty=True
        )
        for branch_name in ("assertion", "coverage", "stimulus"):
            branch = bundle.get(branch_name)
            if not isinstance(branch, dict):
                raise FeatureExtensionError(f"{prefix}.{branch_name} must be an object")
            branch["parameters"] = _decode_json_object(
                branch.get("parameters"),
                location=f"{prefix}.{branch_name}.parameters",
            )
            implementation_spec = branch.get("implementation")
            if isinstance(implementation_spec, dict):
                for optional in ("file", "symbol"):
                    if implementation_spec.get(optional) is None:
                        implementation_spec.pop(optional, None)
        coverage = bundle.get("coverage", {})
        for bin_index, item in enumerate(coverage.get("bins", [])):
            if isinstance(item, dict):
                item["predicate"] = _decode_json_object(
                    item.get("predicate"),
                    location=f"{prefix}.coverage.bins[{bin_index}].predicate",
                    nonempty=True,
                )
        stimulus = bundle.get("stimulus", {})
        for scenario_index, item in enumerate(stimulus.get("scenarios", [])):
            if isinstance(item, dict):
                item["parameters"] = _decode_json_object(
                    item.get("parameters"),
                    location=f"{prefix}.stimulus.scenarios[{scenario_index}].parameters",
                )
    return decoded_result


def _errors(value: object, schema: Mapping[str, Any], location: str) -> list[str]:
    return [
        f"{location}{'.' if error.absolute_path else ''}"
        f"{'.'.join(map(str, error.absolute_path))}: {error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda item: tuple(map(str, item.absolute_path)),
        )
    ]


def extension_requests(architecture: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = architecture.get("verification_extensions", [])
    if not isinstance(raw, list):
        raise FeatureExtensionError("architecture_contract.verification_extensions must be a list")
    errors: list[str] = []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        errors.extend(_errors(item, _load_schema(REQUEST_SCHEMA_PATH), f"verification_extensions[{index}]"))
        if isinstance(item, Mapping):
            identity = str(item.get("id", ""))
            if identity in seen:
                errors.append(f"verification_extensions[{index}].id duplicates {identity!r}")
            seen.add(identity)
            result.append(deepcopy(dict(item)))
    if errors:
        raise FeatureExtensionError("; ".join(errors))
    return result


def interface_vocabulary_extensions(
    architecture: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return contract-local role/class definitions without mutating either pool."""

    from multigent.verifier_tool.pool.tag_pool import contract_vocabulary_extensions

    roles, semantic_classes, _ = contract_vocabulary_extensions(architecture)
    return roles, semantic_classes


def validate_architect_extension_requests(
    architecture: Mapping[str, Any], interface: Mapping[str, Any],
) -> list[str]:
    """Validate request targets against exact frozen names, never prose/name guesses."""

    try:
        requests = extension_requests(architecture)
    except FeatureExtensionError as exc:
        return [str(exc)]
    # Standard-protocol groups are often carried in the canonical metadata
    # strings accepted by the Architect schema and materialized only by the
    # protocol compiler.  Extension targets must see that same resolved view;
    # looking only for a literal channel["protocol_group"] rejects valid AXI
    # contracts whose group is declared as ``protocol_group=...`` metadata.
    from multigent.verifier_tool.pool.role_pool.standard_protocols import (
        compile_standard_protocol_plan,
        declared_protocol_group,
    )

    compiled_protocol_groups = {
        str(item.get("name", ""))
        for item in compile_standard_protocol_plan(
            interface, require_complete=False
        ).get("groups", [])
        if isinstance(item, Mapping)
    }
    declared_protocol_groups: set[str] = set()
    group_errors: list[str] = []
    for channel in interface.get("channels", []):
        if not isinstance(channel, Mapping):
            continue
        try:
            group = declared_protocol_group(channel)
        except ValueError as exc:
            group_errors.append(str(exc))
            continue
        if group:
            declared_protocol_groups.add(group)
    names = {
        "operation": {str(item.get("name", "")) for item in architecture.get("operations", []) if isinstance(item, Mapping)},
        "data_object": {str(item.get("name", "")) for item in architecture.get("data_objects", []) if isinstance(item, Mapping)},
        "channel": {str(item.get("name", "")) for item in interface.get("channels", []) if isinstance(item, Mapping)},
        "signal": {str(item.get("name", "")) for item in interface.get("signals", []) if isinstance(item, Mapping)},
        "protocol_group": compiled_protocol_groups | declared_protocol_groups,
    }
    from multigent.verifier_tool.pool.tag_pool import validate_contract_vocabulary

    errors: list[str] = validate_contract_vocabulary(architecture, interface)
    errors.extend(group_errors)
    from multigent.verifier_tool.pool.role_pool.interface_semantics import (
        load_interface_semantic_taxonomy,
    )
    from multigent.verifier_tool.pool.role_pool.signal_roles import (
        load_signal_role_taxonomy,
    )

    known_roles = set(load_signal_role_taxonomy()["roles"])
    known_classes = set(load_interface_semantic_taxonomy()["semantic_classes"])
    vocabulary_names: set[tuple[str, str]] = set()
    requests_by_id = {str(item["id"]): item for item in requests}
    for request in requests:
        target = request["target"]
        scope, name = str(target["scope"]), str(target["name"])
        if scope != "interface" and name not in names.get(scope, set()):
            errors.append(
                f"verification extension {request['id']!r} targets unknown {scope} {name!r}"
            )
        if scope == "interface" and name not in {"interface", str(architecture.get("design", {}).get("name", ""))}:
            errors.append(
                f"verification extension {request['id']!r} interface target must be 'interface' or the design name"
            )
        vocabulary = request.get("contract_vocabulary")
        if not isinstance(vocabulary, Mapping):
            continue
        pool = str(vocabulary.get("pool", ""))
        vocabulary_name = str(vocabulary.get("name", ""))
        definition = vocabulary.get("definition", {})
        identity = (pool, vocabulary_name)
        if identity in vocabulary_names:
            errors.append(
                f"verification extension vocabulary duplicates {pool} {vocabulary_name!r}"
            )
        vocabulary_names.add(identity)
        if request.get("domain") != "protocol":
            errors.append(
                f"contract vocabulary extension {request['id']!r} must belong to protocol domain"
            )
        if scope not in {"interface", "signal"}:
            errors.append(
                f"contract vocabulary extension {request['id']!r} must target interface or signal"
            )
        if pool == "signal_role":
            required = {
                "category", "channel_binding", "direction_relation",
                "allowed_directions", "semantic_class_binding",
            }
            missing = sorted(required - set(definition))
            if missing:
                errors.append(
                    f"signal role extension {vocabulary_name!r} definition missing {missing}"
                )
            for field in (
                "category", "channel_binding", "direction_relation",
                "semantic_class_binding",
            ):
                if not definition.get(field):
                    errors.append(
                        f"signal role extension {vocabulary_name!r} needs non-null {field}"
                    )
            if not definition.get("allowed_directions"):
                errors.append(
                    f"signal role extension {vocabulary_name!r} needs allowed_directions"
                )
            if (
                definition.get("channel_binding") == "forbidden"
                and definition.get("direction_relation") != "fixed"
            ):
                errors.append(
                    f"signal role extension {vocabulary_name!r} without a channel "
                    "must use fixed direction_relation"
                )
            if vocabulary_name in known_roles:
                errors.append(
                    f"signal role {vocabulary_name!r} is already built in; use the pool entry"
                )
        elif pool == "semantic_class":
            if not definition.get("allowed_roles"):
                errors.append(
                    f"semantic class extension {vocabulary_name!r} needs allowed_roles"
                )
            if vocabulary_name in known_classes:
                errors.append(
                    f"semantic class {vocabulary_name!r} is already built in; use the pool entry"
                )
        if scope == "signal":
            signal = next(
                (
                    item for item in interface.get("signals", [])
                    if isinstance(item, Mapping) and str(item.get("name", "")) == name
                ),
                None,
            )
            field = "role" if pool == "signal_role" else "semantic_class"
            if signal is not None and signal.get(field) != vocabulary_name:
                errors.append(
                    f"contract vocabulary extension {request['id']!r} names {field} "
                    f"{vocabulary_name!r}, but signal {name!r} declares {signal.get(field)!r}"
                )
    for operation in architecture.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        operation_name = str(operation.get("name", ""))
        arithmetic = operation.get("arithmetic", {})
        if isinstance(arithmetic, Mapping) and arithmetic.get("extension_request"):
            identity = str(arithmetic["extension_request"])
            request = requests_by_id.get(identity)
            if arithmetic.get("classifier_profile") != "llm_extension":
                errors.append(
                    f"operation {operation_name!r}.arithmetic.extension_request is only "
                    "valid with classifier_profile 'llm_extension'"
                )
            elif request is None:
                errors.append(
                    f"operation {operation_name!r}.arithmetic references missing "
                    f"verification extension {identity!r}"
                )
            elif request.get("domain") != "operation" or request.get("target") != {
                "scope": "operation", "name": operation_name,
            }:
                errors.append(
                    f"arithmetic extension {identity!r} must be an operation-domain "
                    f"request targeting operation {operation_name!r}"
                )
        lifecycle_policy = operation.get("lifecycle_policy", {})
        if not isinstance(lifecycle_policy, Mapping):
            continue
        for field, value in lifecycle_policy.items():
            if not isinstance(value, Mapping) or set(value) != {"extension_request"}:
                continue
            identity = str(value.get("extension_request", ""))
            request = requests_by_id.get(identity)
            if request is None:
                errors.append(
                    f"operation {operation.get('name')!r}.lifecycle_policy.{field} "
                    f"references missing verification extension {identity!r}"
                )
                continue
            if request.get("domain") != "lifecycle":
                errors.append(
                    f"lifecycle policy extension {identity!r} must belong to lifecycle domain"
                )
            target = request.get("target", {})
            if target != {"scope": "operation", "name": str(operation.get("name", ""))}:
                errors.append(
                    f"lifecycle policy extension {identity!r} must target operation {operation.get('name')!r}"
                )
            expected_path = f"/operations/{operation.get('name')}/lifecycle_policy/{field}"
            if expected_path not in request.get("replaces_contract_paths", []):
                errors.append(
                    f"lifecycle policy extension {identity!r} must list {expected_path!r} "
                    "in replaces_contract_paths"
                )
    for data_object in architecture.get("data_objects", []):
        if not isinstance(data_object, Mapping):
            continue
        serialization = data_object.get("serialization", {})
        if not isinstance(serialization, Mapping) or not serialization.get(
            "extension_request"
        ):
            continue
        identity = str(serialization["extension_request"])
        name = str(data_object.get("name", ""))
        request = requests_by_id.get(identity)
        if serialization.get("kind") != "llm_extension":
            errors.append(
                f"data object {name!r}.serialization.extension_request is only "
                "valid with kind 'llm_extension'"
            )
        elif request is None:
            errors.append(
                f"data object {name!r}.serialization references missing verification "
                f"extension {identity!r}"
            )
        elif request.get("domain") != "operation" or request.get("target") != {
            "scope": "data_object", "name": name,
        }:
            errors.append(
                f"serialization extension {identity!r} must be an operation-domain "
                f"request targeting data object {name!r}"
            )
    # Validate the reverse edge as well.  Without this check an Architect can
    # request a replacement for (for example) completion_style while leaving
    # the built-in value in the policy.  The Verifier would then implement the
    # extension while the deterministic plan continued to enforce the old
    # behavior, violating field-level ownership in both directions.
    operations_by_name = {
        str(item.get("name", "")): item
        for item in architecture.get("operations", [])
        if isinstance(item, Mapping)
    }
    for request in requests:
        if request.get("domain") != "lifecycle":
            continue
        replacements = list(request.get("replaces_contract_paths", []))
        if not replacements:
            continue  # Additive lifecycle behavior needs no policy sentinel.
        target = request.get("target", {})
        operation_name = str(target.get("name", ""))
        prefix = f"/operations/{operation_name}/lifecycle_policy/"
        operation = operations_by_name.get(operation_name, {})
        policy = operation.get("lifecycle_policy", {})
        for path in replacements:
            if not str(path).startswith(prefix):
                errors.append(
                    f"lifecycle extension {request['id']!r} replacement {path!r} "
                    f"must name a lifecycle_policy field on operation {operation_name!r}"
                )
                continue
            field = str(path)[len(prefix):]
            value = policy.get(field) if isinstance(policy, Mapping) else None
            if value != {"extension_request": request["id"]}:
                errors.append(
                    f"lifecycle extension {request['id']!r} replaces {path!r}, but "
                    f"that field does not reference the request"
                )
    try:
        role_extensions, semantic_extensions = interface_vocabulary_extensions(
            architecture
        )
    except ValueError:
        role_extensions, semantic_extensions = {}, {}
    declared_roles = {
        str(item.get("role", ""))
        for item in interface.get("signals", [])
        if isinstance(item, Mapping)
    }
    declared_classes = {
        str(item.get("semantic_class", ""))
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("semantic_class")
    }
    for name in role_extensions:
        if name not in declared_roles:
            errors.append(
                f"contract-local signal role {name!r} is not used by any interface signal"
            )
    allowed_roles = known_roles | set(role_extensions)
    for name, definition in semantic_extensions.items():
        if name not in declared_classes:
            errors.append(
                f"contract-local semantic class {name!r} is not used by any interface signal"
            )
        unknown_allowed = sorted(
            set(map(str, definition.get("allowed_roles", []))) - allowed_roles
        )
        if unknown_allowed:
            errors.append(
                f"semantic class extension {name!r} has unknown allowed_roles {unknown_allowed}"
            )
    return errors


def _python_symbols(sources: Mapping[str, str]) -> dict[str, set[str]]:
    symbols: dict[str, set[str]] = {}
    for path, content in sources.items():
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError:
            continue
        symbols[path] = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    return symbols


def _python_module_values(sources: Mapping[str, str]) -> dict[str, set[str]]:
    """Return module-scope names bound to data rather than functions."""

    values: dict[str, set[str]] = {}
    for path, content in sources.items():
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError:
            continue
        names: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        values[path] = names
    return values


def _python_function_nodes(
    sources: Mapping[str, str],
) -> dict[str, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Return module-level functions for lightweight anti-placeholder checks.

    This is deliberately not a semantic proof.  It only prevents an extension
    bundle from satisfying the authoring boundary with the exact no-op pattern
    that previously passed: an assertion returning ``None``, a constant
    coverage result, and an async stimulus function that never awaits anything.
    Runtime simulation and negative controls remain the authority for behavior.
    """

    result: dict[str, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for path, content in sources.items():
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError:
            continue
        result[path] = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    return result


def _assertion_has_observable_decision(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    return any(
        isinstance(child, (ast.Assert, ast.Raise, ast.Compare, ast.BoolOp))
        for child in ast.walk(node)
    )


def _coverage_is_data_dependent(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Return) or child.value is None:
            continue
        if any(
            isinstance(descendant, (ast.Name, ast.Subscript, ast.Compare, ast.BoolOp, ast.Call))
            for descendant in ast.walk(child.value)
            if descendant is not child.value
        ):
            return True
        if isinstance(child.value, (ast.Name, ast.Subscript, ast.Compare, ast.BoolOp, ast.Call)):
            return True
    return False


def _stimulus_is_executable(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    return isinstance(node, ast.AsyncFunctionDef) and any(
        isinstance(child, ast.Await) for child in ast.walk(node)
    )


_PASSIVE_TRIGGER_NAMES = {
    "ClockCycles", "Edge", "FallingEdge", "ReadOnly", "ReadWrite",
    "RisingEdge", "Timer", "Trigger", "ValueChange",
}

_ASYNC_TASK_SCHEDULER_NAMES = {"create_task", "ensure_future", "start_soon"}


def _called_leaf_name(call: ast.Call) -> str:
    called = call.func
    if isinstance(called, ast.Name):
        return called.id
    if isinstance(called, ast.Attribute) and not isinstance(called.value, ast.Call):
        return called.attr
    return ""


def _stimulus_drives_or_delegates(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Reject an extension stimulus that only waits and returns a marker.

    A real directed stimulus either writes a DUT signal itself or awaits a
    non-trigger helper/driver.  Merely awaiting Timer/RisingEdge cannot create
    the extension scenario and previously let inert API-generated bundles pass.
    """

    for child in ast.walk(node):
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if any(
                isinstance(descendant, ast.Attribute)
                and descendant.attr == "value"
                for target in targets
                for descendant in ast.walk(target)
            ):
                return True
        if not isinstance(child, ast.Await) or not isinstance(child.value, ast.Call):
            continue
        name = _called_leaf_name(child.value)
        if name and name not in _PASSIVE_TRIGGER_NAMES:
            return True
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if _called_leaf_name(child) not in _ASYNC_TASK_SCHEDULER_NAMES or not child.args:
            continue
        scheduled = child.args[0]
        if not isinstance(scheduled, ast.Call):
            continue
        scheduled_name = _called_leaf_name(scheduled)
        if scheduled_name and scheduled_name not in _PASSIVE_TRIGGER_NAMES:
            return True
    return False


def _implementation_uses_parameter(
    node: ast.FunctionDef | ast.AsyncFunctionDef, parameter: str,
) -> bool:
    """Return whether executable code consumes one declared configuration key."""

    parents = {
        child: parent
        for parent in ast.walk(node)
        for child in ast.iter_child_nodes(parent)
    }
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            if child.id == parameter:
                parent = parents.get(child)
                if isinstance(parent, (ast.Assign, ast.AnnAssign)):
                    targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
                    if all(isinstance(target, ast.Name) and target.id == "_" for target in targets):
                        continue
                return True
        elif isinstance(child, ast.Attribute) and child.attr == parameter:
            return True
        elif isinstance(child, ast.Constant) and child.value == parameter:
            return True
        elif isinstance(child, ast.keyword) and child.arg == parameter:
            return True
    return False


def _temporal_stimulus_uses_schedule_parameter(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    parameters: set[str],
) -> bool:
    """Require a temporal stimulus bound to shape a loop/clock wait/driver call."""

    for child in ast.walk(node):
        if isinstance(child, (ast.For, ast.AsyncFor)):
            loaded = {
                descendant.id
                for descendant in ast.walk(child.iter)
                if isinstance(descendant, ast.Name) and isinstance(descendant.ctx, ast.Load)
            }
            if loaded & parameters:
                return True
        if not isinstance(child, ast.Call):
            continue
        called = (
            child.func.id if isinstance(child.func, ast.Name)
            else child.func.attr if isinstance(child.func, ast.Attribute)
            else ""
        )
        if called in {"ClockCycles", "range"} or called not in _PASSIVE_TRIGGER_NAMES:
            loaded = {
                descendant.id
                for value in [*child.args, *(keyword.value for keyword in child.keywords)]
                for descendant in ast.walk(value)
                if isinstance(descendant, ast.Name) and isinstance(descendant.ctx, ast.Load)
            }
            if loaded & parameters:
                return True
    return False


def _request_requires_temporal_evidence(request: Mapping[str, Any]) -> bool:
    """Recognize requests whose truth depends on more than one sampled instant."""

    parameter_names = " ".join(map(str, request.get("parameters", {}))).lower()
    semantics = request.get("semantics", {})
    semantic_text = " ".join(
        str(value)
        for value in semantics.values()
    ).lower() if isinstance(semantics, Mapping) else ""
    markers = (
        "cycle", "latency", "duration", "deadline", "window", "gap",
        "consecutive", "following sample", "until", "remains",
    )
    return any(marker in parameter_names or marker in semantic_text for marker in markers)


def _function_has_temporal_state(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Recognize a local monitor/trace implementation rather than one snapshot."""

    temporal_call_markers = (
        "cycle", "sample", "trace", "history", "monitor", "tracker",
        "stall", "count", "collect", "schedule",
    )
    for child in ast.walk(node):
        if isinstance(
            child, (ast.Await, ast.For, ast.AsyncFor, ast.While, ast.comprehension)
        ):
            return True
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if any(
                isinstance(descendant, (ast.Subscript, ast.Attribute))
                for target in targets
                for descendant in ast.walk(target)
            ):
                return True
        if isinstance(child, ast.Call):
            called = (
                child.func.id if isinstance(child.func, ast.Name)
                else child.func.attr if isinstance(child.func, ast.Attribute)
                else ""
            ).lower()
            if any(marker in called for marker in temporal_call_markers):
                return True
    return False


def _call_supplies_temporal_trace(call: ast.Call) -> bool:
    """Recognize an observed trace/count passed into a pure checker/classifier."""

    markers = ("cycle", "sample", "trace", "history", "count", "duration", "latency")
    candidates: list[tuple[str, ast.AST]] = [
        (keyword.arg or "", keyword.value)
        for keyword in call.keywords
        if keyword.arg != "dut"
    ]
    candidates.extend(("", argument) for argument in call.args)
    for name, value in candidates:
        if _is_literal_expression(value):
            continue
        rendered = f"{name} {ast.unparse(value)}".lower()
        if any(marker in rendered for marker in markers):
            return True
    return False


def _coverage_handles_declared_bins(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    calls: Sequence[tuple[ast.Call, ast.AST, dict[ast.AST, ast.AST]]],
    bin_names: Sequence[str],
    source_functions: Mapping[
        str, Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef]
    ],
) -> list[str]:
    """Return declared bin names absent from the executable classifier path."""

    visible_nodes: list[ast.AST] = [node]
    visible_nodes.extend(function for _, function, _ in calls)
    # A generated test may keep protocol/reference mathematics in a separate
    # reference module and expose only a thin coverage wrapper in tests/*.py.
    # Follow the same name-based cross-file call graph used by extension
    # reachability so exact bin literals in a reachable helper count as
    # executable classifier logic.
    definitions: dict[
        str, list[ast.FunctionDef | ast.AsyncFunctionDef]
    ] = {}
    for by_name in source_functions.values():
        for name, function in by_name.items():
            definitions.setdefault(name, []).append(function)
    pending = [
        called
        for visible in visible_nodes
        for called in _called_symbol_names(visible)
    ]
    visited_names: set[str] = set()
    while pending:
        called = pending.pop()
        if called in visited_names:
            continue
        visited_names.add(called)
        for helper in definitions.get(called, []):
            visible_nodes.append(helper)
            pending.extend(_called_symbol_names(helper))
    visible_strings = {
        str(child.value)
        for visible in visible_nodes
        for child in ast.walk(visible)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    }
    return sorted(set(map(str, bin_names)) - visible_strings)


def _coverage_consumer_asserts_named_bin(
    calls: Sequence[tuple[ast.Call, ast.AST, dict[ast.AST, ast.AST]]],
    bin_names: Sequence[str],
) -> bool:
    """Require a reachable test to demand evidence for a declared positive bin."""

    expected = set(map(str, bin_names))
    for _, function, parents in calls:
        for assertion in (
            child for child in ast.walk(function) if isinstance(child, ast.Assert)
        ):
            mentioned = {
                str(child.value)
                for child in ast.walk(assertion.test)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
            for environment in _static_loop_environments(
                assertion, function, parents
            ):
                mentioned.update(
                    str(environment[child.id])
                    for child in ast.walk(assertion.test)
                    if isinstance(child, ast.Name) and child.id in environment
                )
            if mentioned & expected:
                return True
    return False


def _coverage_consumer_requires_temporal_trigger(
    implementation: ast.FunctionDef | ast.AsyncFunctionDef,
    calls: Sequence[tuple[ast.Call, ast.AST, dict[ast.AST, ast.AST]]],
) -> bool:
    """Require proof that the temporal event occurred before awarding a bin.

    The guard may live directly inside the classifier or in its reachable test
    consumer. Both forms prevent an idle trace from receiving coverage credit.
    """

    markers = ("trigger", "observed", "seen", "saw", "stall", "cycle", "count")
    visible_functions = [implementation, *(function for _, function, _ in calls)]
    for function in visible_functions:
        for assertion in (
            child for child in ast.walk(function) if isinstance(child, ast.Assert)
        ):
            rendered = ast.unparse(assertion.test).lower()
            if not any(marker in rendered for marker in markers):
                continue
            if isinstance(assertion.test, (ast.Name, ast.Attribute, ast.Subscript)):
                # ``assert trigger_seen`` is the direct, idiomatic proof that
                # the temporal event happened. Requiring a redundant
                # ``trigger_seen != False`` comparison creates false rejects.
                return True
            if (
                isinstance(assertion.test, ast.Call)
                and _called_leaf_name(assertion.test) == "any"
            ):
                # ``assert any(predicate(sample) for sample in observed_trace)``
                # is likewise a direct non-vacuity proof: an empty trace or a
                # trace without the named trigger evaluates false.
                return True
            if any(
                isinstance(child, (ast.Gt, ast.GtE, ast.NotEq))
                for child in ast.walk(assertion.test)
            ):
                return True
            if any(
                isinstance(child, ast.Constant)
                and isinstance(child.value, str)
                and any(marker in child.value.lower() for marker in markers[:4])
                for child in ast.walk(assertion.test)
            ):
                return True
    return False


def _literal_call_bindings(
    call: ast.Call,
    implementation: ast.FunctionDef | ast.AsyncFunctionDef,
    variables: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return statically known argument values for one implementation call."""

    variables = variables or {}

    def resolve(value: ast.AST) -> Any:
        if isinstance(value, ast.Name) and value.id in variables:
            return variables[value.id]
        return ast.literal_eval(value)

    positional = [
        argument.arg
        for argument in (
            implementation.args.posonlyargs + implementation.args.args
        )
    ]
    bindings: dict[str, Any] = {}
    defaults = implementation.args.defaults
    if defaults:
        for name, default in zip(positional[-len(defaults):], defaults):
            try:
                bindings[name] = resolve(default)
            except (ValueError, TypeError, SyntaxError):
                pass
    for name, value in zip(positional, call.args):
        try:
            bindings[name] = resolve(value)
        except (ValueError, TypeError, SyntaxError):
            bindings.pop(name, None)
    for keyword in call.keywords:
        if keyword.arg is None:
            continue
        try:
            bindings[keyword.arg] = resolve(keyword.value)
        except (ValueError, TypeError, SyntaxError):
            bindings.pop(keyword.arg, None)
    return bindings


def _bind_static_target(target: ast.AST, value: Any) -> dict[str, Any] | None:
    if isinstance(target, ast.Name):
        return {target.id: value}
    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (tuple, list)):
        if len(target.elts) != len(value):
            return None
        result: dict[str, Any] = {}
        for child, item in zip(target.elts, value):
            bound = _bind_static_target(child, item)
            if bound is None:
                return None
            result.update(bound)
        return result
    return None


def _static_loop_environments(
    node: ast.AST,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: Mapping[ast.AST, ast.AST],
) -> list[dict[str, Any]]:
    """Expand a simple literal scenario table surrounding one expression."""

    constants: dict[str, Any] = {}
    for statement in function.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        try:
            constants[targets[0].id] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError):
            continue

    current: ast.AST = node
    loops: list[ast.For | ast.AsyncFor] = []
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.For, ast.AsyncFor)):
            loops.append(current)
        if current is function:
            break
    environments: list[dict[str, Any]] = [{}]
    for loop in reversed(loops):
        try:
            values = (
                constants[loop.iter.id]
                if isinstance(loop.iter, ast.Name) and loop.iter.id in constants
                else ast.literal_eval(loop.iter)
            )
        except (ValueError, TypeError, SyntaxError, KeyError):
            return environments
        if not isinstance(values, (tuple, list)):
            return environments
        expanded: list[dict[str, Any]] = []
        for environment in environments:
            for value in values:
                bound = _bind_static_target(loop.target, value)
                if bound is not None:
                    expanded.append({**environment, **bound})
        if expanded:
            environments = expanded
    return environments


def _literal_assignments_before_call(
    call: ast.Call,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any]:
    """Resolve simple local constants assigned before a direct helper call.

    Verifier-authored tests commonly name a contract value once and pass that
    variable to assertion, coverage, and stimulus helpers. Treating only inline
    literals as exact scenario evidence creates a false rejection even though
    ``stall_cycles = 2; await helper(..., stall_cycles)`` is statically identical
    to the inline spelling.
    """

    call_line = getattr(call, "lineno", 0)
    candidates: dict[str, list[Any]] = {}
    invalid: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is function:
                for statement in node.body:
                    self.visit(statement)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node is function:
                for statement in node.body:
                    self.visit(statement)

        def _record(self, node: ast.Assign | ast.AnnAssign) -> None:
            if getattr(node, "lineno", call_line + 1) >= call_line:
                return
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                return
            name = targets[0].id
            try:
                candidates.setdefault(name, []).append(ast.literal_eval(node.value))
            except (ValueError, TypeError, SyntaxError):
                invalid.add(name)

        def visit_Assign(self, node: ast.Assign) -> None:
            self._record(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            self._record(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

    Visitor().visit(function)
    constants: dict[str, Any] = {}
    for name, values in candidates.items():
        if name in invalid or not values:
            continue
        if all(value == values[0] for value in values[1:]):
            constants[name] = values[0]
    return constants


def _internal_scenario_bindings(
    implementation: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, Any]]:
    """Resolve literal scenario-table rows that feed an awaited local helper.

    This accepts a reusable stimulus that owns its scenario loop internally,
    while rejecting a table that is merely declared or asserted without ever
    shaping executable async work.
    """

    constants: dict[str, Any] = {}
    for statement in implementation.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            continue
        try:
            value = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError):
            continue
        if isinstance(value, (tuple, list)):
            constants[targets[0].id] = value

    bindings: list[dict[str, Any]] = []
    for loop in ast.walk(implementation):
        if not isinstance(loop, (ast.For, ast.AsyncFor)):
            continue
        try:
            rows = (
                constants[loop.iter.id]
                if isinstance(loop.iter, ast.Name) and loop.iter.id in constants
                else ast.literal_eval(loop.iter)
            )
        except (ValueError, TypeError, SyntaxError, KeyError):
            continue
        if not isinstance(rows, (tuple, list)):
            continue
        awaited_calls = [
            child.value
            for statement in loop.body
            for child in ast.walk(statement)
            if isinstance(child, ast.Await) and isinstance(child.value, ast.Call)
        ]
        if not awaited_calls:
            continue
        for row in rows:
            environment = _bind_static_target(loop.target, row)
            if environment is None:
                continue
            consumed = {
                child.id
                for call in awaited_calls
                for value in [*call.args, *(keyword.value for keyword in call.keywords)]
                for child in ast.walk(value)
                if isinstance(child, ast.Name) and child.id in environment
            }
            if consumed:
                bindings.append({name: environment[name] for name in consumed})
    return bindings


def _unexercised_scenarios(
    implementation: ast.FunctionDef | ast.AsyncFunctionDef,
    calls: Sequence[tuple[ast.Call, ast.AST, dict[ast.AST, ast.AST]]],
    scenarios: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Return scenario names whose declared parameter set is never invoked."""

    call_bindings: list[dict[str, Any]] = []
    for call, function, parents in calls:
        local_constants = _literal_assignments_before_call(call, function)
        for environment in _static_loop_environments(call, function, parents):
            call_bindings.append(
                _literal_call_bindings(
                    call,
                    implementation,
                    {**local_constants, **environment},
                )
            )
    call_bindings.extend(_internal_scenario_bindings(implementation))
    missing: list[str] = []
    for scenario in scenarios:
        parameters = scenario.get("parameters", {})
        if not isinstance(parameters, Mapping) or not parameters:
            continue
        if not any(
            all(bindings.get(str(name)) == value for name, value in parameters.items())
            for bindings in call_bindings
        ):
            missing.append(str(scenario.get("name", "<unnamed>")))
    return missing


def _call_is_started_concurrently(
    call: ast.Call, parents: Mapping[ast.AST, ast.AST],
) -> bool:
    current: ast.AST = call
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.Call):
            called = (
                parent.func.id if isinstance(parent.func, ast.Name)
                else parent.func.attr if isinstance(parent.func, ast.Attribute)
                else ""
            )
            if called in {"start_soon", "create_task", "ensure_future"}:
                return True
        if isinstance(parent, (ast.stmt, ast.FunctionDef, ast.AsyncFunctionDef)):
            break
        current = parent
    return False


def _extension_coverage_call_is_recorded(
    call: ast.Call,
    function: ast.AST,
    parents: Mapping[ast.AST, ast.AST],
    request_id: str,
) -> bool:
    """Recognize the exact classifier-result to trusted-runtime handoff."""

    result_names: set[str] = set()
    parent = parents.get(call)
    if isinstance(parent, ast.Await):
        parent = parents.get(parent)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1 and isinstance(
        parent.targets[0], ast.Name
    ):
        result_names.add(parent.targets[0].id)
    elif isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
        result_names.add(parent.target.id)

    # A temporal sampler is commonly launched before stimulus and joined later:
    #
    #   monitor = cocotb.start_soon(sample(...))
    #   sample = await monitor
    #
    # Follow that local task-handle handoff so this safe concurrent form receives
    # the same coverage credit as ``sample = await sample(...)``.
    current: ast.AST = call
    task_handle = ""
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.Assign):
            if len(current.targets) == 1 and isinstance(current.targets[0], ast.Name):
                task_handle = current.targets[0].id
            break
        if isinstance(current, (ast.stmt, ast.FunctionDef, ast.AsyncFunctionDef)):
            break
    if task_handle:
        for candidate in ast.walk(function):
            if not isinstance(candidate, (ast.Assign, ast.AnnAssign)):
                continue
            target = (
                candidate.targets[0]
                if isinstance(candidate, ast.Assign) and len(candidate.targets) == 1
                else candidate.target
                if isinstance(candidate, ast.AnnAssign)
                else None
            )
            value = candidate.value
            if (
                isinstance(target, ast.Name)
                and isinstance(value, ast.Await)
                and isinstance(value.value, ast.Name)
                and value.value.id == task_handle
            ):
                result_names.add(target.id)

    for candidate in ast.walk(function):
        if not (
            isinstance(candidate, ast.Call)
            and isinstance(candidate.func, ast.Name)
            and candidate.func.id == "_contract_record_extension_coverage"
            and len(candidate.args) >= 2
            and isinstance(candidate.args[0], ast.Constant)
            and candidate.args[0].value == request_id
        ):
            continue
        hits = candidate.args[1]
        if result_names and any(
            isinstance(child, ast.Name) and child.id in result_names
            for child in ast.walk(hits)
        ):
            return True
        if any(child is call for child in ast.walk(hits)):
            return True
    return False


def _component_call_argument(
    call: ast.Call, name: str, required_parameters: Sequence[str]
) -> ast.AST | None:
    """Return one statically supplied component argument by ABI name."""

    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    try:
        position = list(required_parameters).index(name)
    except ValueError:
        return None
    return call.args[position] if position < len(call.args) else None


def _is_statically_empty(node: ast.AST | None) -> bool:
    return bool(
        isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict))
        and not (node.elts if hasattr(node, "elts") else node.keys)
    ) or bool(isinstance(node, ast.Constant) and node.value in {None, ""})


def _result_field_is_asserted(
    call: ast.Call,
    function: ast.AST,
    parents: Mapping[ast.AST, ast.AST],
    field: str,
) -> bool:
    """Recognize direct or assigned checker-result enforcement."""

    current: ast.AST = call
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.Assert):
            return True
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            break

    parent = parents.get(call)
    result_name = ""
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1 and isinstance(
        parent.targets[0], ast.Name
    ):
        result_name = parent.targets[0].id
    elif isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
        result_name = parent.target.id
    if not result_name or result_name == "_":
        return False

    for assertion in (
        node for node in ast.walk(function) if isinstance(node, ast.Assert)
    ):
        for node in ast.walk(assertion.test):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == result_name
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == field
            ):
                return True
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == result_name
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == field
            ):
                return True
    return False


def _component_invocation_errors(
    sources: Mapping[str, str], component: Mapping[str, Any]
) -> list[str]:
    """Apply the selected component ABI's anti-vacuity call constraints."""

    contract = component.get("call_contract", {})
    constraints = contract.get("semantic_constraints", {})
    symbol = str(component.get("entrypoint", "")).rsplit(":", 1)[-1]
    required = tuple(map(str, contract.get("required_parameters", [])))
    calls = _extension_symbol_calls(sources, symbol)
    errors: list[str] = []
    component_id = str(component.get("id", ""))
    if component_id in {
        "protocol.driver.contract_event_source",
        "protocol.monitor.contract_event_trace",
    }:
        expected = {
            (
                str(binding.get("profile_name", "")),
                str(binding.get("transaction_name", "")),
            )
            for binding in component.get("runtime_bindings", [])
            if isinstance(binding, Mapping)
        }
        used: set[tuple[str, str]] = set()
        for accessor_call, _, _ in _extension_symbol_calls(
            sources, "_contract_protocol_event_transaction"
        ):
            if len(accessor_call.args) < 2:
                continue
            try:
                profile_name = ast.literal_eval(accessor_call.args[0])
                transaction_name = ast.literal_eval(accessor_call.args[1])
            except (ValueError, TypeError, SyntaxError):
                continue
            if isinstance(profile_name, str) and isinstance(transaction_name, str):
                used.add((profile_name, transaction_name))
        missing = sorted(expected - used)
        if missing:
            errors.append(
                f"component {component_id!r} omits exact contract runtime "
                f"binding(s) {missing}; invoke the generated accessor for every "
                "resolved profile/transaction instead of sampling another clock "
                "domain through an unrelated trace"
            )
        if (
            component_id == "protocol.monitor.contract_event_trace"
            and len(expected) > 1
            and not _extension_symbol_calls(sources, "capture_protocol_event_traces")
        ):
            errors.append(
                "component 'protocol.monitor.contract_event_trace' resolves multiple "
                f"runtime bindings {sorted(expected)}; call "
                "capture_protocol_event_traces once with every exact binding and one "
                "shared unawaited stimulus coroutine. Sequential single-binding "
                "capture_protocol_event_trace calls replay different transactions and "
                "cannot prove cross-domain correlation"
            )
        if component_id == "protocol.monitor.contract_event_trace":
            for call, function, parents in _extension_symbol_calls(
                sources, "capture_protocol_event_traces"
            ):
                bindings_node = _component_call_argument(
                    call, "bindings", ("dut", "bindings", "stimulus")
                )
                if not isinstance(bindings_node, ast.Dict) or any(
                    not isinstance(key, ast.Constant)
                    or not isinstance(key.value, str)
                    or not key.value
                    for key in bindings_node.keys
                ):
                    errors.append(
                        "component 'protocol.monitor.contract_event_trace' bindings "
                        "must be a dict with stable nonempty string keys and "
                        "(profile, transaction) tuple values; the returned evidence "
                        "mapping is indexed by those string keys"
                    )
                    continue
                binding_keys = {str(key.value) for key in bindings_node.keys}
                current: ast.AST = call
                while isinstance(parents.get(current), ast.Await):
                    current = parents[current]
                assignment = parents.get(current)
                result_name = ""
                if (
                    isinstance(assignment, ast.Assign)
                    and len(assignment.targets) == 1
                    and isinstance(assignment.targets[0], ast.Name)
                ):
                    result_name = assignment.targets[0].id
                if not result_name:
                    errors.append(
                        "capture_protocol_event_traces result must be assigned so "
                        "every binding's observed evidence can be consumed"
                    )
                    continue
                used_keys: set[str] = set()
                extracted_names: dict[str, str] = {}
                for node in ast.walk(function):
                    if not (
                        isinstance(node, ast.Subscript)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == result_name
                    ):
                        continue
                    if not (
                        isinstance(node.slice, ast.Constant)
                        and isinstance(node.slice.value, str)
                    ):
                        errors.append(
                            f"capture_protocol_event_traces result {result_name!r} "
                            "must be indexed by one of its literal string binding keys"
                        )
                        continue
                    key = str(node.slice.value)
                    used_keys.add(key)
                    parent = parents.get(node)
                    if (
                        isinstance(parent, ast.Assign)
                        and len(parent.targets) == 1
                        and isinstance(parent.targets[0], ast.Name)
                    ):
                        extracted_names[key] = parent.targets[0].id
                unknown_keys = sorted(used_keys - binding_keys)
                missing_keys = sorted(binding_keys - used_keys)
                if unknown_keys or missing_keys:
                    errors.append(
                        "capture_protocol_event_traces evidence binding use is "
                        f"incomplete; missing={missing_keys}, unknown={unknown_keys}"
                    )
                for key, name in extracted_names.items():
                    loads = sum(
                        isinstance(node, ast.Name)
                        and isinstance(node.ctx, ast.Load)
                        and node.id == name
                        for node in ast.walk(function)
                    )
                    if loads == 0:
                        errors.append(
                            f"capture_protocol_event_traces evidence for binding "
                            f"{key!r} is assigned to {name!r} but never consumed by "
                            "an assertion or coverage classifier"
                        )
    if not isinstance(constraints, Mapping) or not constraints:
        return errors
    for call, function, parents in calls:
        for name in map(str, constraints.get("nonempty_arguments", [])):
            if _is_statically_empty(_component_call_argument(call, name, required)):
                errors.append(
                    f"component {component.get('id')!r} argument {name!r} is empty; "
                    "bind independent expected evidence instead of disabling the check"
                )
        for name in map(str, constraints.get("forbid_false_arguments", [])):
            value = _component_call_argument(call, name, required)
            if isinstance(value, ast.Constant) and value.value is False:
                errors.append(
                    f"component {component.get('id')!r} argument {name!r} cannot be "
                    "False in a required verification path"
                )
        result_field = str(constraints.get("assert_result_field", ""))
        if result_field and not _result_field_is_asserted(
            call, function, parents, result_field
        ):
            errors.append(
                f"component {component.get('id')!r} result field {result_field!r} "
                "is not asserted by a reachable test"
            )
    return errors


def _protocol_completion_drive_errors(
    sources: Mapping[str, str],
    interface: Mapping[str, Any],
    component: Mapping[str, Any],
) -> list[str]:
    """Reject monitored DUT-output transactions whose completion cannot occur.

    A contract-local destination transaction can be observed without being
    testbench-driven, but its ACK/ERR-style completion inputs still need an
    active responder. Merely initializing every such input to zero produces a
    test that deterministically waits forever.
    """

    if str(component.get("id", "")) != "protocol.monitor.contract_event_trace":
        return []
    from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
        compile_protocol_semantics,
        expression_signals,
    )

    profiles = {
        str(profile.get("name", "")): profile
        for profile in compile_protocol_semantics(interface).get("profiles", [])
        if isinstance(profile, Mapping)
    }
    signal_directions = {
        str(signal.get("name", "")): str(signal.get("direction", ""))
        for signal in interface.get("signals", [])
        if isinstance(signal, Mapping)
    }
    channel_directions = {
        str(channel.get("name", "")): str(channel.get("direction", ""))
        for channel in interface.get("channels", [])
        if isinstance(channel, Mapping)
    }

    reachable = _reachable_test_symbols(sources)
    actively_driven: set[str] = set()
    for content in sources.values():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for function in tree.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function.name not in reachable:
                continue
            for assignment in ast.walk(function):
                if not isinstance(assignment, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    continue
                targets = (
                    assignment.targets
                    if isinstance(assignment, ast.Assign)
                    else [assignment.target]
                )
                value = assignment.value
                for target in targets:
                    if not (
                        isinstance(target, ast.Attribute)
                        and target.attr == "value"
                        and isinstance(target.value, ast.Attribute)
                        and isinstance(target.value.value, ast.Name)
                        and target.value.value.id == "dut"
                    ):
                        continue
                    try:
                        literal = ast.literal_eval(value)
                    except (ValueError, TypeError, SyntaxError):
                        actively_driven.add(target.value.attr)
                    else:
                        if bool(literal):
                            actively_driven.add(target.value.attr)

    errors: list[str] = []
    for binding in component.get("runtime_bindings", []):
        if not isinstance(binding, Mapping):
            continue
        profile_name = str(binding.get("profile_name", ""))
        transaction_name = str(binding.get("transaction_name", ""))
        profile = profiles.get(profile_name, {})
        transaction = next(
            (
                item
                for item in profile.get("transactions", [])
                if str(item.get("name", "")) == transaction_name
            ),
            None,
        )
        if not isinstance(transaction, Mapping):
            continue
        if channel_directions.get(str(transaction.get("channel", ""))) != "output":
            continue
        completed = transaction.get("completed")
        if not isinstance(completed, Mapping):
            continue
        completion_inputs = {
            name
            for name in expression_signals(completed)
            if signal_directions.get(name) == "input"
        }
        if completion_inputs and not (completion_inputs & actively_driven):
            errors.append(
                f"component 'protocol.monitor.contract_event_trace' binding "
                f"{profile_name!r}/{transaction_name!r} has no reachable responder "
                f"that can assert completion input(s) {sorted(completion_inputs)}; "
                "zero-only initialization cannot complete the transaction"
            )
    return errors


def _temporal_observer_overlaps_stimulus(
    sources: Mapping[str, str],
    coverage_symbol: str,
    stimulus_symbol: str,
) -> bool:
    """Require a DUT-observing monitor to start before its directed stimulus."""

    coverage_calls = _extension_symbol_calls(sources, coverage_symbol)
    stimulus_calls = _extension_symbol_calls(sources, stimulus_symbol)
    for coverage_call, function, parents in coverage_calls:
        if not _call_is_started_concurrently(coverage_call, parents):
            continue
        coverage_line = getattr(coverage_call, "lineno", 0)
        if any(
            getattr(other_function, "name", None) == getattr(function, "name", None)
            and coverage_line < getattr(stimulus_call, "lineno", 0)
            for stimulus_call, other_function, _ in stimulus_calls
        ):
            return True
    return False


def _undefined_module_decorator_roots(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str]]:
    """Find decorators evaluated before their module root name is defined."""

    builtins = {"classmethod", "property", "staticmethod"}
    failures: set[tuple[str, str, str]] = set()
    for path, content in sources.items():
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError:
            continue
        defined = set(builtins)
        for statement in tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in statement.decorator_list:
                    name = _decorator_name(decorator)
                    root = name.split(".", 1)[0]
                    if root and root not in defined:
                        failures.add((path, statement.name, root))
                defined.add(statement.name)
            elif isinstance(statement, (ast.Import, ast.ImportFrom)):
                for alias in statement.names:
                    defined.add(alias.asname or alias.name.split(".", 1)[0])
            elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)
    return sorted(failures)


def _temporal_output_has_activation_path(
    request: Mapping[str, Any],
    interface: Mapping[str, Any] | None,
    sources: Mapping[str, str],
    stimulus_symbol: str,
) -> bool:
    """Reject output-channel tests that never start work capable of producing VALID."""

    if interface is None or request.get("target", {}).get("scope") != "channel":
        return True
    target = str(request.get("target", {}).get("name", ""))
    channel = next(
        (
            item for item in interface.get("channels", [])
            if isinstance(item, Mapping) and str(item.get("name", "")) == target
        ),
        None,
    )
    if not isinstance(channel, Mapping) or channel.get("direction") != "output":
        return True

    stimulus_calls = _extension_symbol_calls(sources, stimulus_symbol)
    relevant_functions = {
        function.name
        for _, function, _ in stimulus_calls
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    relevant_functions.add(stimulus_symbol)
    called: set[str] = set()
    driven_inputs: set[str] = set()
    input_signals = {
        str(item.get("name", ""))
        for item in interface.get("signals", [])
        if isinstance(item, Mapping)
        and item.get("direction") == "input"
        and item.get("role") not in {"clock", "reset"}
        and str(item.get("channel", "")) != target
    }
    for content in sources.values():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for function in tree.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function.name not in relevant_functions:
                continue
            called.update(_called_symbol_names(function))
            for child in ast.walk(function):
                if not isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    continue
                targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                for assigned in targets:
                    if not (
                        isinstance(assigned, ast.Attribute)
                        and assigned.attr == "value"
                        and isinstance(assigned.value, ast.Attribute)
                        and isinstance(assigned.value.value, ast.Name)
                        and assigned.value.value.id == "dut"
                    ):
                        continue
                    driven_inputs.add(assigned.value.attr)
    campaign_markers = {
        "run_code_owned_verification_campaign",
        "_contract_run_code_owned_verification_campaign",
        "_contract_automatic_verification_campaign",
        "drive_accepted_command",
        "drive_protocol_transfers",
        "_contract_drive_protocol_transfers",
        "execute_axi4_memory_job",
    }
    return bool((called & campaign_markers) or (driven_inputs & input_signals))


def _temporal_test_starts_clock_or_campaign(
    sources: Mapping[str, str], stimulus_symbol: str,
) -> bool:
    """Require a reachable extension call graph to provide a running clock."""

    campaign_markers = {
        "run_code_owned_verification_campaign",
        "_contract_run_code_owned_verification_campaign",
        "_contract_automatic_verification_campaign",
    }
    definitions: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for content in sources.values():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.setdefault(node.name, []).append(node)

    def reaches_clock_or_campaign(root: ast.AST) -> bool:
        pending = [root]
        seen: set[int] = set()
        while pending:
            function = pending.pop()
            if id(function) in seen:
                continue
            seen.add(id(function))
            called = _called_symbol_names(function)
            if called & campaign_markers:
                return True
            if "Clock" in called and "start_soon" in called:
                return True
            for name in called:
                pending.extend(definitions.get(name, []))
        return False

    for _, function, _ in _extension_symbol_calls(sources, stimulus_symbol):
        if reaches_clock_or_campaign(function):
            return True
    return False


def _is_literal_expression(node: ast.AST) -> bool:
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return False
    return True


def _function_directly_observes_dut(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    argument_names = {
        argument.arg
        for argument in (
            node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        )
    }
    if "dut" not in argument_names:
        return False
    return any(
        isinstance(child, ast.Attribute)
        and isinstance(child.value, ast.Name)
        and child.value.id == "dut"
        for child in ast.walk(node)
    )


def _extension_symbol_calls(
    sources: Mapping[str, str], symbol: str,
) -> list[tuple[ast.Call, ast.AST, dict[ast.AST, ast.AST]]]:
    """Return calls to ``symbol`` below reachable test/helper functions."""

    reachable = _reachable_test_symbols(sources)
    result: list[tuple[ast.Call, ast.AST, dict[ast.AST, ast.AST]]] = []
    for content in sources.values():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        for function in tree.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function.name not in reachable:
                continue
            for child in ast.walk(function):
                if not isinstance(child, ast.Call):
                    continue
                called = (
                    child.func.id if isinstance(child.func, ast.Name)
                    else child.func.attr if isinstance(child.func, ast.Attribute)
                    else ""
                )
                if called == symbol:
                    result.append((child, function, parents))
    return result


def _call_result_is_consumed(
    call: ast.Call,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: Mapping[ast.AST, ast.AST],
    *,
    require_assertion: bool,
) -> bool:
    parent = parents.get(call)
    if isinstance(parent, ast.Await):
        parent = parents.get(parent)
    if isinstance(parent, ast.Assert):
        return True
    if isinstance(parent, (ast.Return, ast.If, ast.While)):
        return True
    if isinstance(parent, (ast.Assign, ast.AnnAssign)):
        target = parent.targets[0] if isinstance(parent, ast.Assign) else parent.target
        target_names = {
            descendant.id
            for descendant in ast.walk(target)
            if isinstance(descendant, ast.Name)
        }
        if not target_names:
            return not require_assertion
        if not require_assertion:
            return True
        return any(
            isinstance(node, ast.Assert)
            and any(
                isinstance(descendant, ast.Name) and descendant.id in target_names
                for descendant in ast.walk(node.test)
            )
            for node in ast.walk(function)
        )
    return not isinstance(parent, ast.Expr) and not require_assertion


def _assigned_expression_before(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    name: str,
    before_line: int,
) -> ast.AST | None:
    """Return the latest visible assignment used to derive a call argument."""

    candidates: list[tuple[int, ast.AST]] = []
    for node in ast.walk(function):
        line = getattr(node, "lineno", -1)
        if line < 0 or line >= before_line:
            continue
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        elif isinstance(node, ast.NamedExpr):
            targets, value = [node.target], node.value
        else:
            continue
        if any(
            isinstance(descendant, ast.Name) and descendant.id == name
            for target in targets
            for descendant in ast.walk(target)
        ):
            candidates.append((line, value))
    return max(candidates, default=(-1, None), key=lambda item: item[0])[1]


def _expression_has_runtime_evidence(
    expression: ast.AST,
    *,
    containing_function: ast.FunctionDef | ast.AsyncFunctionDef,
    source_functions: Mapping[
        str, Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef]
    ],
    before_line: int,
    seen_names: frozenset[str] = frozenset(),
) -> bool:
    """Trace an argument back to DUT/simulator evidence instead of its name.

    Merely assigning a fabricated expected trace to ``trace`` or ``t0`` must not
    make it runtime evidence.  This lightweight provenance walk follows local
    assignments and helper calls far enough to distinguish those values from a
    monitor/driver result derived from ``dut``.
    """

    if _is_literal_expression(expression):
        return False
    if isinstance(expression, ast.Name):
        if expression.id == "dut":
            return True
        if expression.id in seen_names:
            return False
        assigned = _assigned_expression_before(
            containing_function, expression.id, before_line
        )
        if assigned is None:
            return False
        return _expression_has_runtime_evidence(
            assigned,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=getattr(assigned, "lineno", before_line),
            seen_names=seen_names | {expression.id},
        )
    if isinstance(expression, ast.Attribute):
        return _expression_has_runtime_evidence(
            expression.value,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=before_line,
            seen_names=seen_names,
        )
    if isinstance(expression, ast.Subscript):
        return _expression_has_runtime_evidence(
            expression.value,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=before_line,
            seen_names=seen_names,
        )
    if isinstance(expression, ast.Await):
        return _expression_has_runtime_evidence(
            expression.value,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=before_line,
            seen_names=seen_names,
        )
    if isinstance(expression, ast.Call):
        values = [*expression.args, *(item.value for item in expression.keywords)]
        if any(
            _expression_has_runtime_evidence(
                value,
                containing_function=containing_function,
                source_functions=source_functions,
                before_line=before_line,
                seen_names=seen_names,
            )
            for value in values
        ):
            return True
        called = (
            expression.func.id
            if isinstance(expression.func, ast.Name)
            else expression.func.attr
            if isinstance(expression.func, ast.Attribute)
            else ""
        )
        helpers = [
            node
            for by_name in source_functions.values()
            for name, node in by_name.items()
            if name == called
        ]
        return any(_function_directly_observes_dut(helper) for helper in helpers)
    return any(
        _expression_has_runtime_evidence(
            child,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=before_line,
            seen_names=seen_names,
        )
        for child in ast.iter_child_nodes(expression)
    )


def _call_has_runtime_evidence(
    call: ast.Call,
    implementation: ast.FunctionDef | ast.AsyncFunctionDef,
    declared_parameters: set[str],
    containing_function: ast.FunctionDef | ast.AsyncFunctionDef,
    source_functions: Mapping[
        str, Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef]
    ],
) -> tuple[bool, list[str]]:
    """Require observed arguments, not fabricated literals, at a runtime call."""

    non_runtime_observations: list[str] = []
    dynamic = _function_directly_observes_dut(implementation)
    formal_names = [
        argument.arg
        for argument in (
            implementation.args.posonlyargs
            + implementation.args.args
            + implementation.args.kwonlyargs
        )
    ]
    for index, argument in enumerate(call.args):
        formal = formal_names[index] if index < len(formal_names) else ""
        if formal in declared_parameters:
            continue
        if _expression_has_runtime_evidence(
            argument,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=getattr(call, "lineno", 10**9),
        ):
            dynamic = True
        else:
            non_runtime_observations.append(formal or f"positional[{index}]")
    for keyword in call.keywords:
        if keyword.arg is None or keyword.arg in declared_parameters:
            continue
        if keyword.arg == "dut":
            # Passing the handle is evidence only if the implementation actually
            # reads a DUT attribute; accepting and ignoring ``dut`` is not enough.
            dynamic = dynamic or _function_directly_observes_dut(implementation)
            continue
        if _expression_has_runtime_evidence(
            keyword.value,
            containing_function=containing_function,
            source_functions=source_functions,
            before_line=getattr(call, "lineno", 10**9),
        ):
            dynamic = True
        else:
            non_runtime_observations.append(keyword.arg)
    return dynamic, non_runtime_observations


def _called_symbol_names(node: ast.AST) -> set[str]:
    """Return statically visible function names called below ``node``."""

    result: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            result.add(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            result.add(child.func.attr)
    return result


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _decorator_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _reachable_test_symbols(sources: Mapping[str, str]) -> set[str]:
    """Approximate symbols reachable from generated test entry points.

    Extension implementations must not merely exist in a response file.  This
    lightweight call-graph gate starts at cocotb/pytest-style test functions in
    ``tests/*.py`` and follows direct or module-qualified calls by symbol name.
    Runtime execution remains the final authority, but this catches the common
    dead-code failure before simulation.
    """

    functions: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    roots: set[str] = set()
    for path, content in sources.items():
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            functions.setdefault(node.name, []).append(node)
            if not path.startswith("tests/"):
                continue
            decorators = {_decorator_name(item) for item in node.decorator_list}
            if node.name.startswith("test_") or any(
                name == "test" or name.endswith(".test") for name in decorators
            ):
                roots.add(node.name)

    reachable = set(roots)
    pending = list(roots)
    while pending:
        current = pending.pop()
        for function in functions.get(current, []):
            for called in _called_symbol_names(function):
                if called in reachable:
                    continue
                reachable.add(called)
                if called in functions:
                    pending.append(called)
    return reachable


def validate_verifier_extension_bundles(
    architecture: Mapping[str, Any],
    bundles: object,
    *,
    source_files: Sequence[Mapping[str, Any]] = (),
    interface: Mapping[str, Any] | None = None,
    require_runtime_evidence: bool = False,
) -> list[str]:
    """Require exactly one normalized implementation bundle per request.

    This is an authoring/traceability gate only.  It intentionally performs no
    mutation qualification and never promotes a bundle into a pool.
    """

    try:
        requests = extension_requests(architecture)
    except FeatureExtensionError as exc:
        return [str(exc)]
    if bundles is None:
        bundles = []
    if not isinstance(bundles, list):
        return ["feature_extensions must be a list"]
    request_by_id = {str(item["id"]): item for item in requests}
    resolved_reuse_by_request: dict[str, Mapping[str, Any]] = {}
    resolved_components_by_request: dict[str, Mapping[str, Any]] = {}
    if interface is not None:
        from multigent.verifier_tool.contract_review import resolve_extension_reuse
        from multigent.verifier_tool.components import resolve_extension_components

        try:
            resolved_reuse = resolve_extension_reuse(architecture, interface)
            resolved_components = resolve_extension_components(architecture, interface)
        except (ValueError, AssertionError, KeyError, TypeError) as exc:
            return [f"deterministic extension reuse resolution failed: {exc}"]
        resolved_reuse_by_request = {
            str(item.get("request_id", "")): item
            for item in resolved_reuse.get("entries", [])
            if isinstance(item, Mapping)
        }
        resolved_components_by_request = {
            str(item.get("request_id", "")): item
            for item in resolved_components.get("entries", [])
            if isinstance(item, Mapping)
        }
    errors: list[str] = []
    bundle_by_request: dict[str, Mapping[str, Any]] = {}
    bundle_ids: set[str] = set()
    schema = _load_schema(BUNDLE_SCHEMA_PATH)
    for index, item in enumerate(bundles):
        errors.extend(_errors(item, schema, f"feature_extensions[{index}]"))
        if not isinstance(item, Mapping):
            continue
        request_id = str(item.get("request_id", ""))
        identity = str(item.get("id", ""))
        if request_id in bundle_by_request:
            errors.append(f"feature_extensions[{index}].request_id duplicates {request_id!r}")
        bundle_by_request[request_id] = item
        if identity in bundle_ids:
            errors.append(f"feature_extensions[{index}].id duplicates {identity!r}")
        bundle_ids.add(identity)
        request = request_by_id.get(request_id)
        if request is None:
            errors.append(f"feature_extensions[{index}] answers unknown request {request_id!r}")
            continue
        for field in ("domain", "feature_name", "target"):
            if item.get(field) != request.get(field):
                errors.append(
                    f"feature_extensions[{index}].{field} must exactly preserve request {request_id!r}"
                )
        observation_names = {
            str(observation.get("name", ""))
            for observation in request.get("required_observations", [])
            if isinstance(observation, Mapping)
        }
        missing_bindings = sorted(observation_names - set(item.get("bindings", {})))
        if missing_bindings:
            errors.append(
                f"feature_extensions[{index}].bindings omits required observation(s) "
                f"{missing_bindings}"
            )
        missing_reuse = sorted(
            set(map(str, request.get("related_builtin_features", [])))
            - set(map(str, item.get("reuse", {}).get("based_on_features", [])))
        )
        if missing_reuse:
            errors.append(
                f"feature_extensions[{index}].reuse.based_on_features omits "
                f"Architect reference(s) {missing_reuse}"
            )
        resolved_entry = resolved_reuse_by_request.get(request_id, {})
        resolved_feature_ids = set(
            map(str, resolved_entry.get("preserved_feature_ids", []))
        )
        missing_resolved_reuse = sorted(
            resolved_feature_ids
            - set(map(str, item.get("reuse", {}).get("based_on_features", [])))
        )
        if missing_resolved_reuse:
            errors.append(
                f"feature_extensions[{index}].reuse.based_on_features omits "
                f"deterministically resolved tool-owned feature(s) "
                f"{missing_resolved_reuse}"
            )
        for branch in ("coverage", "stimulus"):
            names = [str(entry.get("name", "")) for entry in item.get(branch, {}).get("bins" if branch == "coverage" else "scenarios", []) if isinstance(entry, Mapping)]
            if len(names) != len(set(names)):
                errors.append(f"feature_extensions[{index}].{branch} names must be unique")
    missing = sorted(set(request_by_id) - set(bundle_by_request))
    if missing:
        errors.append(f"Verifier omitted feature extension request(s) {missing}")

    sources: dict[str, str] = {}
    for item in source_files:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path", ""))
        content = str(item.get("content", ""))
        sources[path] = content
        if "/" not in path:
            owner = "tests" if "categories" in item else "reference"
            sources[f"{owner}/{path}"] = content
    if require_runtime_evidence:
        for path, function, root in _undefined_module_decorator_roots(sources):
            errors.append(
                f"{path}: test/function {function!r} uses decorator root {root!r} "
                "before that name is imported or defined; the module would fail "
                "during test discovery"
            )
    source_symbols = _python_symbols(sources)
    source_values = _python_module_values(sources)
    source_functions = _python_function_nodes(sources)
    reachable_test_symbols = _reachable_test_symbols(sources)
    for index, item in enumerate(bundles):
        if not isinstance(item, Mapping):
            continue
        request = request_by_id.get(str(item.get("request_id", "")), {})
        component_resolution = resolved_components_by_request.get(
            str(item.get("request_id", "")), {}
        )
        if require_runtime_evidence and component_resolution:
            explicitly_required_ids = set(
                map(
                    str,
                    component_resolution.get("required_reuse_component_ids", []),
                )
            )
            required_components = {
                str(component.get("id", "")): component
                for component in component_resolution.get("automatic_reuse", [])
                if (
                    isinstance(component, Mapping)
                    and component.get("id") in explicitly_required_ids
                )
            }
            declared_helpers = set(
                map(str, item.get("reuse", {}).get("helpers", []))
            )
            missing_component_ids = sorted(
                set(required_components) - declared_helpers
            )
            if missing_component_ids:
                errors.append(
                    f"feature_extensions[{index}].reuse.helpers omits "
                    f"deterministically selected component(s) {missing_component_ids}; "
                    "reuse those exact catalog IDs and implement only the residual"
                )
            for component_id in sorted(set(required_components) & declared_helpers):
                component = required_components[component_id]
                entrypoint = str(component.get("entrypoint", ""))
                symbol = entrypoint.rsplit(":", 1)[-1]
                if symbol and symbol not in reachable_test_symbols:
                    errors.append(
                        f"feature_extensions[{index}] claims reusable component "
                        f"{component_id!r}, but entrypoint symbol {symbol!r} is not "
                        "reachable from a generated tests/*.py test entry point"
                    )
                elif symbol:
                    errors.extend(
                        f"feature_extensions[{index}] {message}"
                        for message in _component_invocation_errors(
                            sources, component
                        )
                    )
                    if interface is not None:
                        errors.extend(
                            f"feature_extensions[{index}] {message}"
                            for message in _protocol_completion_drive_errors(
                                sources, interface, component
                            )
                        )
        temporal_request = _request_requires_temporal_evidence(request)
        stimulus_branch = item.get("stimulus", {})
        stimulus_implementation = (
            stimulus_branch.get("implementation", {})
            if isinstance(stimulus_branch, Mapping)
            else {}
        )
        stimulus_symbol = str(stimulus_implementation.get("symbol", ""))
        if (
            require_runtime_evidence
            and stimulus_symbol
            and not _temporal_output_has_activation_path(
                request, interface, sources, stimulus_symbol
            )
        ):
            errors.append(
                f"feature_extensions[{index}] output-channel scenario never "
                "starts a code-owned campaign/driver or drives non-target DUT inputs; "
                "READY-only activity cannot cause the DUT to produce VALID"
            )
        if (
            require_runtime_evidence
            and interface is not None
            and stimulus_symbol
            and not _temporal_test_starts_clock_or_campaign(
                sources, stimulus_symbol
            )
        ):
            errors.append(
                f"feature_extensions[{index}] cocotb scenario does not "
                "start a Clock through its reachable call graph or invoke the "
                "code-owned campaign; an independent test that only awaits clock "
                "edges will hang"
            )
        verifier_symbols: list[tuple[str, str]] = []
        for branch_name in ("assertion", "coverage", "stimulus"):
            branch = item.get(branch_name, {})
            implementation = branch.get("implementation", {}) if isinstance(branch, Mapping) else {}
            if implementation.get("kind") not in {"verifier_python", "protocol_driver"}:
                continue
            path, symbol = str(implementation.get("file", "")), str(implementation.get("symbol", ""))
            if implementation.get("kind") in {"verifier_python", "protocol_driver"} and path and symbol:
                verifier_symbols.append((path, symbol))
            if not path or not symbol:
                errors.append(
                    f"feature_extensions[{index}].{branch_name} verifier code needs file and symbol"
                )
            elif path not in source_symbols:
                errors.append(
                    f"feature_extensions[{index}].{branch_name} references missing source file {path!r}"
                )
            elif symbol not in source_symbols[path]:
                if symbol in source_values.get(path, set()):
                    errors.append(
                        f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                        f"in {path!r} is module-scope data, not an executable function; "
                        "define it with def/async def and call it from a reachable cocotb test"
                    )
                else:
                    errors.append(
                        f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                        f"is not defined as a module-scope function in {path!r}; define "
                        "it with def/async def and call it from a reachable cocotb test"
                    )
            elif symbol not in reachable_test_symbols:
                errors.append(
                    f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                    "is not reachable from a generated tests/*.py test entry point"
                )
            elif implementation.get("kind") in {"verifier_python", "protocol_driver"}:
                node = source_functions.get(path, {}).get(symbol)
                if node is not None and branch_name == "assertion" and not _assertion_has_observable_decision(node):
                    errors.append(
                        f"feature_extensions[{index}].assertion symbol {symbol!r} "
                        "has no observable decision; a no-op/return-None checker is invalid"
                    )
                elif node is not None and branch_name == "coverage" and not _coverage_is_data_dependent(node):
                    errors.append(
                        f"feature_extensions[{index}].coverage symbol {symbol!r} "
                        "returns no data-dependent sample; constant coverage is invalid"
                    )
                elif node is not None and branch_name == "stimulus" and not _stimulus_is_executable(node):
                    errors.append(
                        f"feature_extensions[{index}].stimulus symbol {symbol!r} "
                        "must be async and await executable stimulus work"
                    )
                if require_runtime_evidence and node is not None:
                    calls = _extension_symbol_calls(sources, symbol)
                    declared_parameters = set(
                        map(str, branch.get("parameters", {}))
                    ) if isinstance(branch, Mapping) else set()
                    if branch_name == "stimulus" and isinstance(branch, Mapping):
                        declared_parameters.update(
                            str(name)
                            for scenario in branch.get("scenarios", [])
                            if isinstance(scenario, Mapping)
                            for name in scenario.get("parameters", {})
                        )
                    unused_parameters = sorted(
                        parameter
                        for parameter in declared_parameters
                        if not _implementation_uses_parameter(node, parameter)
                    )
                    if unused_parameters:
                        errors.append(
                            f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                            f"ignores declared parameter(s) {unused_parameters}; the executable "
                            "implementation must consume every behavior-shaping parameter"
                        )
                    if branch_name == "stimulus" and isinstance(branch, Mapping):
                        missing_scenarios = _unexercised_scenarios(
                            node,
                            calls,
                            [
                                scenario
                                for scenario in branch.get("scenarios", [])
                                if isinstance(scenario, Mapping)
                            ],
                        )
                        if missing_scenarios:
                            errors.append(
                                f"feature_extensions[{index}].stimulus symbol {symbol!r} "
                                f"never executes declared scenario(s) {missing_scenarios} "
                                "with their exact parameter values"
                            )
                    call_evidence = [
                        _call_has_runtime_evidence(
                            call,
                            node,
                            declared_parameters,
                            containing_function,
                            source_functions,
                        )
                        for call, containing_function, _ in calls
                    ]
                    if branch_name in {"assertion", "coverage"} and not any(
                        dynamic and not literals
                        for dynamic, literals in call_evidence
                    ):
                        literal_names = sorted({
                            name
                            for _, literals in call_evidence
                            for name in literals
                        })
                        errors.append(
                            f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                            "is not called with simulator-derived evidence"
                            + (
                                f"; fabricated literal observation or non-simulator-derived "
                                f"argument(s)={literal_names}"
                                if literal_names else ""
                            )
                        )
                    if (
                        branch_name in {"assertion", "coverage"}
                        and temporal_request
                        and not _function_has_temporal_state(node)
                        and not any(
                            _call_supplies_temporal_trace(call)
                            for call, _, _ in calls
                        )
                    ):
                        errors.append(
                            f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                            "checks only one instantaneous snapshot for a temporal request; "
                            "consume a simulator-derived cycle trace/counter or implement a "
                            "stateful monitor"
                        )
                    if (
                        branch_name == "stimulus"
                        and temporal_request
                        and not _temporal_stimulus_uses_schedule_parameter(
                            node, declared_parameters
                        )
                    ):
                        errors.append(
                            f"feature_extensions[{index}].stimulus symbol {symbol!r} "
                            "does not use a declared cycle/window parameter to shape "
                            "a multi-cycle schedule or reusable driver call"
                        )
                    if (
                        branch_name == "coverage"
                        and temporal_request
                        and isinstance(node, ast.AsyncFunctionDef)
                        and _function_directly_observes_dut(node)
                        and stimulus_symbol
                        and not _temporal_observer_overlaps_stimulus(
                            sources, symbol, stimulus_symbol
                        )
                    ):
                        errors.append(
                            f"feature_extensions[{index}].coverage symbol {symbol!r} "
                            "observes DUT cycles only after directed stimulus completes; "
                            "start the monitor concurrently before the stimulus so the "
                            "temporal event cannot be missed"
                        )
                    if branch_name == "assertion":
                        enforces_internally = any(
                            isinstance(child, (ast.Assert, ast.Raise))
                            for child in ast.walk(node)
                        )
                        enforced_at_call = any(
                            _call_result_is_consumed(
                                call,
                                function,
                                parents,
                                require_assertion=True,
                            )
                            for call, function, parents in calls
                        )
                        if not enforces_internally and not enforced_at_call:
                            errors.append(
                                f"feature_extensions[{index}].assertion symbol {symbol!r} "
                                "returns a decision that no generated test asserts"
                            )
                    elif branch_name == "coverage" and not any(
                        _call_result_is_consumed(
                            call,
                            function,
                            parents,
                            require_assertion=False,
                        )
                        for call, function, parents in calls
                    ):
                        errors.append(
                            f"feature_extensions[{index}].coverage symbol {symbol!r} "
                            "returns a sample that no generated test consumes"
                        )
                    elif branch_name == "coverage":
                        declared_bin_names = [
                            str(bin_spec.get("name", ""))
                            for bin_spec in branch.get("bins", [])
                            if isinstance(bin_spec, Mapping)
                        ]
                        missing_bin_logic = _coverage_handles_declared_bins(
                            node,
                            calls,
                            declared_bin_names,
                            source_functions,
                        )
                        if missing_bin_logic:
                            errors.append(
                                f"feature_extensions[{index}].coverage symbol {symbol!r} "
                                f"does not classify declared bin(s) {missing_bin_logic}; return "
                                "or record the exact bin names from observed runtime evidence"
                            )
                        if declared_bin_names and not _coverage_consumer_asserts_named_bin(
                            calls, declared_bin_names
                        ):
                            errors.append(
                                f"feature_extensions[{index}].coverage symbol {symbol!r} "
                                "has no reachable test assertion requiring a declared bin "
                                "from observed DUT evidence; type/shape checks alone cannot "
                                "earn coverage credit"
                            )
                        if (
                            temporal_request
                            and not _coverage_consumer_requires_temporal_trigger(node, calls)
                        ):
                            errors.append(
                                f"feature_extensions[{index}].coverage symbol {symbol!r} "
                                f"can earn declared temporal bin(s) {declared_bin_names} "
                                "without a reachable assertion "
                                "that the trigger/event was actually observed; empty or "
                                "idle traces must not pass vacuously"
                            )
                        unrecorded_calls = [
                            call
                            for call, function, parents in calls
                            if not _extension_coverage_call_is_recorded(
                                call,
                                function,
                                parents,
                                str(item.get("request_id", "")),
                            )
                        ]
                        if unrecorded_calls:
                            errors.append(
                                f"feature_extensions[{index}].coverage symbol {symbol!r} "
                                "returns observed bin names that are not passed to "
                                "_contract_record_extension_coverage(request_id, hits); "
                                "local assertions do not add extension bins to the shared "
                                "required coverage denominator"
                            )
                    elif branch_name == "stimulus" and not _stimulus_drives_or_delegates(node):
                        errors.append(
                            f"feature_extensions[{index}].stimulus symbol {symbol!r} "
                            "only waits; it must drive a DUT signal or await a reusable driver"
                        )
        if len(verifier_symbols) != len(set(verifier_symbols)):
            errors.append(
                f"feature_extensions[{index}] must use distinct Verifier Python symbols "
                "for assertion, coverage, and stimulus"
            )
    return errors


def build_feature_extension_manifest(
    architecture: Mapping[str, Any],
    bundles: object,
    *,
    source_files: Sequence[Mapping[str, Any]] = (),
    interface: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pair frozen requests with contract-local Verifier implementations.

    The result is intentionally inert: it is useful input to a future review or
    qualification stage, but it never mutates or promotes a pool entry.
    """

    errors = validate_verifier_extension_bundles(
        architecture,
        bundles,
        source_files=source_files,
        interface=interface,
    )
    if errors:
        raise FeatureExtensionError("; ".join(errors))
    bundle_by_request = {
        str(item["request_id"]): deepcopy(dict(item))
        for item in bundles or []
        if isinstance(item, Mapping)
    }
    resolved_reuse = None
    resolved_components = None
    contract_local_components: list[dict[str, Any]] = []
    if interface is not None:
        from multigent.verifier_tool.contract_review import resolve_extension_reuse
        from multigent.verifier_tool.components import (
            build_contract_local_component_manifests,
            resolve_extension_components,
        )

        resolved_reuse = resolve_extension_reuse(architecture, interface)
        resolved_components = resolve_extension_components(architecture, interface)
        contract_local_components = build_contract_local_component_manifests(
            architecture,
            [item for item in bundles or [] if isinstance(item, Mapping)],
            interface,
        )
    reuse_by_request = {
        str(item.get("request_id", "")): item
        for item in (resolved_reuse or {}).get("entries", [])
        if isinstance(item, Mapping)
    }
    return {
        "schema_version": 1,
        "status": "contract_local_only",
        "promotion": "not_implemented",
        **(
            {"resolved_tool_owned_reuse": resolved_reuse}
            if resolved_reuse is not None
            else {}
        ),
        **(
            {
                "resolved_components": resolved_components,
                "contract_local_components": contract_local_components,
            }
            if resolved_components is not None
            else {}
        ),
        "entries": [
            {
                "request": request,
                "implementation": bundle_by_request[str(request["id"])],
                **(
                    {"resolved_reuse": reuse_by_request[str(request["id"])]}
                    if str(request["id"]) in reuse_by_request
                    else {}
                ),
            }
            for request in extension_requests(architecture)
        ],
    }


def render_requested_extension_worklist(
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any] | None = None,
) -> str:
    """Render exact work items so the Verifier does not redo supported siblings."""

    requests = extension_requests(architecture)
    if not requests:
        return "No contract-local verification extensions were requested. Emit feature_extensions: []."
    from multigent.verifier_tool.extensions.retrieval import (
        retrieve_extension_analogues,
    )

    retrieved_by_request = retrieve_extension_analogues(architecture, interface)
    resolved_by_request: dict[str, Mapping[str, Any]] = {}
    components_by_request: dict[str, Mapping[str, Any]] = {}
    if interface is not None:
        from multigent.verifier_tool.contract_review import resolve_extension_reuse
        from multigent.verifier_tool.components import resolve_extension_components

        resolved = resolve_extension_reuse(architecture, interface)
        resolved_by_request = {
            str(item.get("request_id", "")): item
            for item in resolved.get("entries", [])
            if isinstance(item, Mapping)
        }
        resolved_components = resolve_extension_components(architecture, interface)
        components_by_request = {
            str(item.get("request_id", "")): item
            for item in resolved_components.get("entries", [])
            if isinstance(item, Mapping)
        }
    work = []
    for request in requests:
        work.append(
            {
                "request_id": request["id"],
                "implement_only": {
                    "domain": request["domain"],
                    "feature_name": request["feature_name"],
                    "target": request["target"],
                    "semantics": request["semantics"],
                    "parameters": request.get("parameters", {}),
                    "required_observations": request["required_observations"],
                    **({"match": request["match"]} if request.get("match") else {}),
                    **(
                        {"contract_vocabulary": request["contract_vocabulary"]}
                        if request.get("contract_vocabulary")
                        else {}
                    ),
                },
                "preserve_tool_owned_siblings": True,
                "reuse_first": sorted(
                    set(map(str, request.get("related_builtin_features", [])))
                    | set(
                        map(
                            str,
                            resolved_by_request.get(str(request["id"]), {}).get(
                                "preserved_feature_ids", []
                            ),
                        )
                    )
                ),
                "retrieved_analogues": retrieved_by_request.get(
                    str(request["id"]), []
                ),
                "retrieval_rule": (
                    "Use these as implementation shapes only. Frozen request "
                    "semantics, observations, and parameters remain authoritative; "
                    "never fabricate an expected trace and call it DUT evidence."
                ),
                **(
                    {
                        "resolved_tool_owned_reuse": resolved_by_request[
                            str(request["id"])
                        ]
                    }
                    if str(request["id"]) in resolved_by_request
                    else {}
                ),
                **(
                    {
                        "component_resolution": components_by_request[
                            str(request["id"])
                        ]
                    }
                    if str(request["id"]) in components_by_request
                    else {}
                ),
                "required_bundle_branches": ["assertion", "coverage", "stimulus"],
                "required_coverage_obligation_id": (
                    f"extension.{request['id']}"
                ),
            }
        )
    return yaml.safe_dump(work, sort_keys=False, default_flow_style=False).rstrip()


def render_architect_extension_request_guide() -> str:
    """Tell Architect exactly what it may declare, without implementation work."""

    schema = yaml.safe_dump(extension_request_schema(), sort_keys=False).rstrip()
    return f"""CONTRACT-LOCAL VERIFICATION EXTENSION REQUESTS
==================================================
Use architecture_contract.verification_extensions only when required behavior is
not expressible by a closed verifier_tool pool. Emit [] when every feature is
supported. Architect owns only observable meaning, exact target, parameters, and
required observations. It must not invent checker code, coverage predicates, or
stimulus algorithms; those belong to Verifier.

Each unsupported feature gets one stable request. A lifecycle policy field can
refer to it as {{extension_request: <request id>}} and must list that exact field
in replaces_contract_paths. Do not replace supported sibling fields.

If the external contract genuinely needs a signal role or semantic class absent
from the Role Pool, put its complete candidate definition in contract_vocabulary.
This keeps the contract locally valid and lets Verifier implement only that
meaning. It is not added to the global pool.

When several local roles, semantic classes, or verification tags are needed,
declare them once in architecture_contract.verification_vocabulary. Reuse a
built-in tag by stable name whenever possible. A genuinely new tag must include
its domains, allowed scopes, and observable meaning, and a request.match.tags
entry must reference it as source=contract_local.

Request schema:
{schema}
"""


def render_extension_authoring_guide() -> str:
    """Tell Verifier how to answer exact requests using existing implementations."""

    examples = EXAMPLES_PATH.read_text(encoding="utf-8").rstrip()
    return f"""VERIFICATION FEATURE EXTENSION AUTHORING
=========================================
Use this only for Architect requests in architecture_contract.verification_extensions.
One request describes meaning; one Verifier feature_extensions bundle supplies the
contract-local implementation. Never edit verifier_tool or claim the bundle is a pool
entry. Reuse existing helpers and feature shapes before writing Python.

The exact worklist includes structure-aware ``retrieved_analogues`` from the
same-domain checked-in pools. Use them as RAG references for checker, sampler,
and strategy shape, not as replacement requirements. A retrieved analogue never
overrides the frozen request. Evidence passed to an extension assertion or coverage
classifier must be collected from the running DUT or driver monitor. A Python trace
reconstructed from expected inputs or scenario labels is expected evidence, not
observed evidence, even when it resembles a retrieved trace-based feature.

Emit feature_extensions=[] when there are no requests. When requests exist, implement
only those missing features: supported sibling protocol, lifecycle, and operation
features remain tool-owned. Do not regenerate their drivers, assertions, coverage, or
golden logic. The bundle is the machine-readable manifest for the Verifier-owned code,
not a substitute for executable code.

Every bundle must keep request_id/domain/feature_name/target byte-for-byte equal to
the request and must define all three sibling branches: assertion, measured coverage,
and real stimulus. A verifier_python/protocol_driver branch names the exact generated
file and module-level symbol. Coverage predicates classify observed DUT evidence;
stimulus labels never create hits.

Every extension work item also supplies one
``required_coverage_obligation_id``. Put that exact ID in one test module's
``COVERAGE_OBLIGATIONS``. After calling the extension coverage classifier with
simulator-derived evidence, pass its returned bin-name collection to
``_contract_record_extension_coverage(<exact request_id>, hits)``. The trusted
runtime rejects undeclared bin names and adds every declared extension bin to the
same required coverage denominator as built-in protocol, lifecycle, and operation
bins. A local ``assert '<bin>' in hits`` is useful but does not by itself record
functional coverage.

Before writing source, construct this mechanical checklist from the exact request:
- ``bindings`` contains every ``required_observations[].name`` as an exact key;
- assertion, coverage, and stimulus name three distinct module-level functions;
- each branch declares only parameters its own function actually consumes (do not
  copy all request parameters into every branch);
- each declared scenario is called with its exact parameter values;
- one reachable cocotb test starts a free-running Clock for every independently
  driven clock signal used by that test (directly or through a reachable helper),
  starts any temporal observer before the stimulus, awaits the stimulus, asserts the
  assertion result, consumes the coverage result, and requires at least one exact
  declared bin name. Importing Clock or only awaiting RisingEdge starts no clock.
Treat this checklist as a pre-return gate, not as optional guidance.
The observation names are semantic evidence requirements, not Architect-owned Python
types or trace schemas. Define the local record/list shape yourself from the frozen
signals, clocks, acceptance expressions, and required behavior. For example,
``transaction_trace`` can be a list of records captured only on real acceptance or
retirement edges, while ``cycle_trace`` can be a list of per-clock samples taken by a
concurrent DUT monitor. Bind those simulator-derived runtime objects under the exact
required observation names. Missing Python field names for such local records is a
Verifier implementation task and never an ARCHITECTURE_CONFLICT.
When ``protocol.monitor.contract_event_trace`` appears in
``required_reuse_component_ids``, do not hand-write that recorder. Import and call
its normative ``capture_protocol_event_trace`` entrypoint around the extension
stimulus. The mechanical shape is::

    profile, transaction = _contract_protocol_event_transaction(<exact names>)
    evidence = await capture_protocol_event_trace(
        dut, profile, transaction,
        extension_stimulus(dut, ...),
        signal_names=CONTRACT_SIGNAL_NAMES,
    )
    assert extension_assertion(
        cycle_trace=evidence["cycle_trace"],
        transaction_trace=evidence["transaction_trace"], ...
    ) is True
    hits = extension_coverage(
        cycle_trace=evidence["cycle_trace"],
        transaction_trace=evidence["transaction_trace"], ...
    )
    _contract_record_extension_coverage(<exact request id>, hits)

If that component's ``runtime_bindings`` contains more than one exact binding,
the residual feature spans multiple channels or clock domains. Import
``capture_protocol_event_traces`` from the same module and capture them around
one shared stimulus instead of replaying the traffic once per binding::

    source_profile, source_transaction = _contract_protocol_event_transaction(
        <exact source profile>, <exact source transaction>
    )
    destination_profile, destination_transaction = _contract_protocol_event_transaction(
        <exact destination profile>, <exact destination transaction>
    )
    evidence_by_binding = await capture_protocol_event_traces(
        dut,
        {{
            "source": (source_profile, source_transaction),
            "destination": (destination_profile, destination_transaction),
        }},
        extension_stimulus(dut, ...),
        signal_names=CONTRACT_SIGNAL_NAMES,
    )

Both recorders start before that one stimulus and sample their own declared
clocks. Consume the appropriate ``evidence_by_binding`` entries in the residual
checker and classifier. Creating an unused destination trace, or executing the
same stimulus sequentially for source and destination traces, is invalid.

Replace every placeholder with exact frozen values. The test still starts the
clock and any required sink/memory responder. Declare only the branch parameters
actually accepted and used by that branch. The collector proves provenance; it
does not implement the residual assertion, coverage predicate, or response model.
The underscored accessor and ``CONTRACT_SIGNAL_NAMES`` are pipeline-owned names
that will be appended to the module after your response. Call/read them as shown,
but never define, assign, copy, or emit their generated block or marker text.
For a protocol/lifecycle-only contract, use this minimal execution order rather
than inventing a separate trace format or delaying observation until after traffic::

    @cocotb.test(timeout_time=<finite>, timeout_unit="ns")
    @contract_coverage()
    async def extension_case(dut):
        clock_task = cocotb.start_soon(
            Clock(getattr(dut, <clock_name>), <period>, unit="ns").start()
        )
        try:
            profile, transaction = _contract_protocol_event_transaction(
                <profile_name>, <transaction_name>
            )
            evidence = await capture_protocol_event_trace(
                dut, profile, transaction,
                extension_stimulus(dut, <only stimulus parameters>),
                signal_names=CONTRACT_SIGNAL_NAMES,
            )
            decision = extension_assertion(
                cycle_trace=evidence["cycle_trace"],
                transaction_trace=evidence["transaction_trace"],
                <only assertion parameters>,
            )
            # PROTOCOL ASSERTION [<request id>]
            assert decision is True, <useful failure context>
            hits = extension_coverage(
                cycle_trace=evidence["cycle_trace"],
                transaction_trace=evidence["transaction_trace"],
                <only coverage parameters>,
            )
            _contract_record_extension_coverage(<exact request id>, hits)
            # PROTOCOL ASSERTION [<request id>.coverage]
            assert <exact declared positive bin> in hits
            _contract_record_checked_stimulus(
                "directed",
                {{"scenario": <literal scenario>}},
                {{"extension_ok": True}},
                {{"extension_ok": bool(decision)}},
                operations=(), label=<same literal intent label>,
            )
        finally:
            clock_task.kill()

The placeholders above are explanatory and must all be replaced. The expected and
observed mappings deliberately have identical keys but independent origins. One
test may execute several declared scenarios, but do not declare speculative read,
write, reset, timing, or error scenarios that the residual requirement does not need.
Each ``STIMULUS_COVERAGE_INTENTS`` label must name an actually executed record and
may target several obligations only when that same traffic is intended to exercise
all of them; runtime bin hits, not the list, remain authoritative.
For an assertion wrapper, use an observable decision that the validator and test can
both enforce, for example ``ok, errors = check(trace); assert ok, '; '.join(errors);
return True``, followed by ``assert extension_assertion(observed_trace) is True`` in
the reachable cocotb test. Returning ``{{"passed": ok}}`` is not itself an assertion,
and pointing the bundle at a lower-level function whose return value the test ignores
is also invalid. Apply the same call-graph discipline to coverage: require an exact
declared bin and explicit nonempty/trigger evidence in the reachable test.

The named implementation file is not created from the bundle. It must also appear,
with exactly the same path, in this response's test_files or reference_model_files.
Only one-level ``tests/*.py`` and ``reference/*.py`` paths are accepted; never name a
``verification/*.py`` file. Define every named symbol at module scope in that file and
make it reachable from a generated ``tests/*.py`` cocotb entry point. Before returning,
cross-check the three bundle paths and symbols against the source files you emit.

Reachability alone is insufficient. Assertion and coverage calls must receive
simulator-derived observations, not literal values invented inside the test. If an
assertion function returns a Boolean, the generated test must actually assert that
return value; do not discard it. Consume the coverage sampler's returned evidence.
The stimulus function must drive a DUT signal or await a real reusable driver;
awaiting only Timer/RisingEdge and returning a marker is not stimulus. Literal values
are allowed only for keys declared in the branch parameters.

Every declared behavior-shaping parameter must be consumed by its executable branch;
copying it only into YAML or assigning it to ``_`` is not an implementation. Temporal
stimulus must use its cycle/window parameter to shape a real loop, clock wait, or
reusable driver call, and every declared scenario must actually be invoked with its
exact parameter values. Start a DUT-observing temporal coverage monitor concurrently
before the directed stimulus; observing only after the schedule completes misses the
event. If the target is a DUT-produced output channel, also start a code-owned campaign/driver
(or fully drive the non-target command/operand inputs) so the DUT can
produce VALID. An independent cocotb extension test must start every clock it uses
unless it invokes a code-owned campaign that starts those clocks. Require explicit observed-trigger
evidence (for example ``triggered`` or ``stall_count > 0``) before awarding a temporal
bin; an empty/idle trace must not satisfy a positive bin. Import every decorator root
before its decorated test is defined.
Temporal assertion/coverage requests must use a
simulator-derived multi-cycle trace/counter or a stateful monitor: reading VALID/READY,
BUSY, DONE, or ERROR once cannot prove a deadline, duration, duty cycle, or recovery
window. Coverage code must classify and return/record every exact bin name declared in
the bundle, and a reachable test must assert that observed DUT evidence reaches a
declared bin. Checking only the sampler's type/shape earns no credit. A generic
``sampled=True`` marker or raw instantaneous state is not bin coverage. These rules
apply equally to ``verifier_python`` and ``protocol_driver`` symbols.

For ``reuse.based_on_features``, copy every exact ID shown in the work item's
``reuse_first`` list. This list includes both Architect references and all
deterministically preserved tool-owned sibling features; do not shorten it to only the
closest related feature. The work item's ``component_resolution`` is a separate,
code-owned decision. Its ``call_contract`` is the normative, versioned
verifier_tool API for this run; it is implementation context, not a missing DUT or
Architect contract fact. Never return ARCHITECTURE_CONFLICT because a reusable API
is external to the hardware contract. Copy every ``required_reuse_component_ids``
value into ``reuse.helpers`` and call that entrypoint exactly as its call_contract
specifies from a reachable generated test/helper. Replace every template placeholder
with an exact frozen binding or real runtime value. Entries under
``pipeline_managed_reuse_component_ids`` are already installed and invoked by the
pipeline-generated block: do not list them in ``reuse.helpers``, instantiate them,
or duplicate their behavior. Implement only ``residual_capabilities`` locally.
Entries under ``rag_component_references`` are read-only analogies: use their
structure when useful, but do not claim or call them unless the frozen target
actually satisfies their manifest requirements.

An extension branch may call and compose the helpers listed by deterministic reuse,
but it may not claim that a helper alone is a new ``existing_primitive``. There is no
runtime dispatch registry for such a claim. Put the residual logic in a reachable
verifier_python wrapper (or a reachable protocol_driver stimulus wrapper) and call
the reusable helper from there. This prevents an inert manifest from masquerading as
an implemented extension.

Reusable built-in examples:
{examples}
"""


__all__ = [
    "BUNDLE_SCHEMA_PATH",
    "EXAMPLES_PATH",
    "FeatureExtensionError",
    "REQUEST_SCHEMA_PATH",
    "build_feature_extension_manifest",
    "decode_verifier_extension_transport",
    "extension_bundle_schema",
    "extension_request_schema",
    "extension_requests",
    "interface_vocabulary_extensions",
    "render_architect_extension_request_guide",
    "render_extension_authoring_guide",
    "render_requested_extension_worklist",
    "validate_architect_extension_requests",
    "validate_verifier_extension_bundles",
    "with_architect_extension_request_schema",
    "with_verifier_extension_bundle_schema",
]
