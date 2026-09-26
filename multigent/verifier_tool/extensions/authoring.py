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
    """Add contract-local bundles to the Verifier response schema.

    The property stays optional for contracts with no requests.  Semantic
    validation requires an exact one-to-one response whenever requests exist.
    """

    result = deepcopy(dict(schema))
    try:
        properties = result["properties"]
    except (KeyError, TypeError) as exc:
        raise FeatureExtensionError("Verifier schema needs root properties") from exc
    properties["feature_extensions"] = {
        "type": "array",
        "items": extension_bundle_schema(),
        "description": (
            "Verifier-authored, contract-local implementations for Architect extension "
            "requests. These are not promoted pool entries."
        ),
    }
    return result


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
    if interface is not None:
        from multigent.verifier_tool.contract_review import resolve_extension_reuse

        try:
            resolved_reuse = resolve_extension_reuse(architecture, interface)
        except (ValueError, AssertionError, KeyError, TypeError) as exc:
            return [f"deterministic extension reuse resolution failed: {exc}"]
        resolved_reuse_by_request = {
            str(item.get("request_id", "")): item
            for item in resolved_reuse.get("entries", [])
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
    source_symbols = _python_symbols(sources)
    source_functions = _python_function_nodes(sources)
    reachable_test_symbols = _reachable_test_symbols(sources)
    for index, item in enumerate(bundles):
        if not isinstance(item, Mapping):
            continue
        verifier_symbols: list[tuple[str, str]] = []
        for branch_name in ("assertion", "coverage", "stimulus"):
            branch = item.get(branch_name, {})
            implementation = branch.get("implementation", {}) if isinstance(branch, Mapping) else {}
            if implementation.get("kind") not in {"verifier_python", "protocol_driver"}:
                continue
            path, symbol = str(implementation.get("file", "")), str(implementation.get("symbol", ""))
            if implementation.get("kind") == "verifier_python" and path and symbol:
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
                errors.append(
                    f"feature_extensions[{index}].{branch_name} symbol {symbol!r} is not defined at module scope in {path!r}"
                )
            elif symbol not in reachable_test_symbols:
                errors.append(
                    f"feature_extensions[{index}].{branch_name} symbol {symbol!r} "
                    "is not reachable from a generated tests/*.py test entry point"
                )
            elif implementation.get("kind") == "verifier_python":
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
    if interface is not None:
        from multigent.verifier_tool.contract_review import resolve_extension_reuse

        resolved_reuse = resolve_extension_reuse(architecture, interface)
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
    resolved_by_request: dict[str, Mapping[str, Any]] = {}
    if interface is not None:
        from multigent.verifier_tool.contract_review import resolve_extension_reuse

        resolved = resolve_extension_reuse(architecture, interface)
        resolved_by_request = {
            str(item.get("request_id", "")): item
            for item in resolved.get("entries", [])
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
                **(
                    {
                        "resolved_tool_owned_reuse": resolved_by_request[
                            str(request["id"])
                        ]
                    }
                    if str(request["id"]) in resolved_by_request
                    else {}
                ),
                "required_bundle_branches": ["assertion", "coverage", "stimulus"],
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

Reusable built-in examples:
{examples}
"""


__all__ = [
    "BUNDLE_SCHEMA_PATH",
    "EXAMPLES_PATH",
    "FeatureExtensionError",
    "REQUEST_SCHEMA_PATH",
    "build_feature_extension_manifest",
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
