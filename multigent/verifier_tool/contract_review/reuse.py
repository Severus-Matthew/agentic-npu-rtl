"""Deterministically resolve code-owned siblings before any LLM extension work."""

from __future__ import annotations

from typing import Any, Mapping

from multigent.verifier_tool.pool.diagnostics import is_code_owned


def _feature_matches_target(
    feature: Mapping[str, Any],
    target: Mapping[str, Any],
) -> bool:
    scope, name = str(target.get("scope", "")), str(target.get("name", ""))
    if scope == "interface":
        return True
    if str(feature.get("scope", "")) == scope and str(feature.get("scope_name", "")) == name:
        return True
    bindings = feature.get("bindings", {})
    if not isinstance(bindings, Mapping):
        return False
    if scope == "operation" and str(bindings.get("operation_name", "")) == name:
        return True
    if scope == "protocol_group" and str(bindings.get("protocol_group", "")) == name:
        return True
    if scope == "signal":
        return name in {
            str(value)
            for value in bindings.values()
            if isinstance(value, str)
        }
    return False


def _helper_summary(features: list[Mapping[str, Any]]) -> dict[str, list[str]]:
    return {
        "assertion_checkers": sorted(
            {
                str(feature.get("assertion", {}).get("checker"))
                for feature in features
                if feature.get("assertion", {}).get("checker")
            }
        ),
        "coverage_samplers": sorted(
            {
                str(feature.get("coverage", {}).get("sampler"))
                for feature in features
                if feature.get("coverage", {}).get("sampler")
            }
        ),
        "stimulus_strategies": sorted(
            {
                str(feature.get("stimulus", {}).get("strategy"))
                for feature in features
                if feature.get("stimulus", {}).get("strategy")
            }
        ),
    }


def _target_interface_capabilities(
    interface: Mapping[str, Any],
    target: Mapping[str, Any],
    protocol_plan: Mapping[str, Any],
    tag_seed: Mapping[str, Any],
) -> dict[str, list[str]]:
    """Return exact contract facts available at one extension target."""

    scope, name = str(target.get("scope", "")), str(target.get("name", ""))
    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    channels = [
        item for item in interface.get("channels", []) if isinstance(item, Mapping)
    ]
    selected_channels: set[str] = set()
    selected_signals: list[Mapping[str, Any]] = []
    if scope == "interface":
        selected_channels = {str(item.get("name", "")) for item in channels}
        selected_signals = signals
    elif scope == "channel":
        selected_channels = {name}
        selected_signals = [
            item for item in signals if str(item.get("channel", "")) == name
        ]
    elif scope == "signal":
        selected_signals = [
            item for item in signals if str(item.get("name", "")) == name
        ]
        selected_channels = {
            str(item.get("channel", ""))
            for item in selected_signals
            if item.get("channel")
        }
    elif scope == "protocol_group":
        from multigent.verifier_tool.pool.role_pool.standard_protocols import (
            declared_protocol_group,
        )

        for group in protocol_plan.get("bindings", {}).get("standard_groups", []):
            if not isinstance(group, Mapping) or str(group.get("name", "")) != name:
                continue
            selected_channels.update(
                str(item.get("name", ""))
                for item in group.get("channels", {}).values()
                if isinstance(item, Mapping)
            )
        selected_channels.update(
            str(item.get("name", ""))
            for item in channels
            if declared_protocol_group(item) == name
        )
        selected_signals = [
            item
            for item in signals
            if str(item.get("channel", "")) in selected_channels
        ]
    profiles = {
        str(item.get("protocol_profile", ""))
        for item in channels
        if str(item.get("name", "")) in selected_channels
        and item.get("protocol_profile")
    }
    tags = {
        str(tag)
        for channel in selected_channels
        for tag in tag_seed.get("channels", {}).get(channel, [])
    }
    tags.update(
        str(tag)
        for signal in selected_signals
        for tag in tag_seed.get("signals", {}).get(str(signal.get("name", "")), [])
    )
    return {
        "roles": sorted(
            {str(item.get("role", "")) for item in selected_signals if item.get("role")}
        ),
        "semantic_classes": sorted(
            {
                str(item.get("semantic_class", ""))
                for item in selected_signals
                if item.get("semantic_class")
            }
        ),
        "protocol_profiles": sorted(profiles),
        "tags": sorted(tags),
    }


def resolve_extension_reuse(
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve immutable built-in feature/helper reuse for every extension request.

    Failure to build one domain is reported as deterministic diagnostics; it never
    causes the resolver to guess from signal spelling or to ask the Verifier LLM
    to recreate known siblings.
    """

    from multigent.verifier_tool.extensions import extension_requests
    from multigent.verifier_tool.pool.tag_pool import contract_vocabulary_extensions
    from multigent.verifier_tool.pool.role_pool.interface_semantics import (
        derive_interface_coverage_seed,
    )

    roles, classes, _ = contract_vocabulary_extensions(architecture)
    tags = derive_interface_coverage_seed(
        interface,
        role_extensions=roles,
        semantic_class_extensions=classes,
    )
    plans: dict[str, Mapping[str, Any]] = {}
    diagnostics: list[str] = []
    try:
        from multigent.verifier_tool.protocol.coverage.plan import (
            build_interface_coverage_plan,
        )

        interface_plan = build_interface_coverage_plan(
            interface,
            role_extensions=roles,
            semantic_class_extensions=classes,
        )
        plans["protocol"] = interface_plan["feature_plan"]
    except (ValueError, AssertionError, KeyError, TypeError) as exc:
        diagnostics.append(f"protocol feature resolution failed: {exc}")

    try:
        from multigent.verifier_tool.pool.operation_metadata import (
            build_architect_operation_metadata,
        )
        from multigent.verifier_tool.pool.feature_plans import (
            build_lifecycle_feature_plan,
            build_operation_feature_plan,
        )

        metadata = build_architect_operation_metadata(architecture, interface)
        plans["lifecycle"] = build_lifecycle_feature_plan(interface, metadata)
        plans["operation"] = build_operation_feature_plan(architecture)
    except (ValueError, AssertionError, KeyError, TypeError) as exc:
        diagnostics.append(f"operation/lifecycle feature resolution failed: {exc}")
        try:
            from multigent.verifier_tool.pool.feature_plans import (
                build_operation_feature_plan,
            )

            plans["operation"] = build_operation_feature_plan(architecture)
        except (ValueError, AssertionError, KeyError, TypeError) as nested:
            diagnostics.append(f"operation feature resolution failed: {nested}")

    resolved: list[dict[str, Any]] = []
    for request in extension_requests(architecture):
        domain = str(request["domain"])
        target = dict(request["target"])
        candidates = [
            feature
            for feature in plans.get(domain, {}).get("features", [])
            # A feature the tool cannot own (an operation that failed to compile) has
            # no checker/sampler/strategy to reuse or preserve.
            if isinstance(feature, Mapping)
            and is_code_owned(feature)
            and _feature_matches_target(feature, target)
        ]
        if domain == "operation" and target.get("scope") == "data_object":
            object_name = str(target.get("name", ""))
            owning_operations = {
                str(operation.get("name", ""))
                for operation in architecture.get("operations", [])
                if isinstance(operation, Mapping)
                and object_name
                in {
                    str(item)
                    for item in [
                        *operation.get("inputs", []),
                        *operation.get("outputs", []),
                    ]
                }
            }
            candidates = [
                feature
                for feature in plans.get("operation", {}).get("features", [])
                if isinstance(feature, Mapping)
                and str(feature.get("bindings", {}).get("operation_name", ""))
                in owning_operations
            ]
        candidate_ids = [str(feature["id"]) for feature in candidates]
        explicit = list(map(str, request.get("related_builtin_features", [])))
        preserved = sorted(set(candidate_ids) | set(explicit))
        interface_capabilities = _target_interface_capabilities(
            interface, target, plans.get("protocol", {}), tags
        )
        target_tags = sorted(
            set(interface_capabilities["tags"])
            | {
                str(tag)
                for feature in candidates
                for tag in feature.get("tags", [])
            }
            | (
                {"serialization"}
                if domain == "operation" and target.get("scope") == "data_object"
                else set()
            )
        )
        match = request.get("match", {})
        match = dict(match) if isinstance(match, Mapping) else {}
        requested_builtin_tags = {
            str(item.get("name", ""))
            for item in match.get("tags", [])
            if isinstance(item, Mapping) and item.get("source") == "builtin"
        }
        # A contract-local tag identifies the new residual behavior itself. It
        # need not already exist on a built-in target feature; declaration and
        # vocabulary validation are its authority.
        missing = {
            "tags": sorted(requested_builtin_tags - set(target_tags)),
            "roles": sorted(
                set(map(str, match.get("required_roles", [])))
                - set(interface_capabilities["roles"])
            ),
            "semantic_classes": sorted(
                set(map(str, match.get("required_semantic_classes", [])))
                - set(interface_capabilities["semantic_classes"])
            ),
            "protocol_profiles": sorted(
                set(map(str, match.get("required_protocol_profiles", [])))
                - set(interface_capabilities["protocol_profiles"])
            ),
        }
        match_satisfied = not any(missing.values())
        if not match_satisfied:
            diagnostics.append(
                f"extension request {request['id']!r} does not match its target: "
                f"{missing}"
            )
        resolved.append(
            {
                "request_id": str(request["id"]),
                "domain": domain,
                "target": target,
                "target_tags": target_tags,
                "target_capabilities": interface_capabilities,
                "match": match,
                "match_satisfied": match_satisfied,
                "missing_match_requirements": missing,
                "preserved_feature_ids": preserved,
                "resolved_features": [
                    {
                        "id": str(feature["id"]),
                        "kind": str(feature["kind"]),
                        "scope": str(feature["scope"]),
                        "scope_name": str(feature["scope_name"]),
                        "tags": list(map(str, feature.get("tags", []))),
                    }
                    for feature in candidates
                ],
                "helpers": _helper_summary(candidates),
                "llm_owns_only_residual_feature": True,
            }
        )
    return {
        "schema_version": 1,
        "entries": resolved,
        "diagnostics": diagnostics,
    }


__all__ = ["resolve_extension_reuse"]
