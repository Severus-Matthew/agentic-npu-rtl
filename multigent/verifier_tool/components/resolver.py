"""Resolve reusable components and isolate the contract-local residual work."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .registry import ComponentSpec, component_call_contract, load_component_catalog


_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _tokens(value: object) -> set[str]:
    text = _stringify(value)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text).replace("_", " ")
    return {item.lower() for item in _TOKEN.findall(normalized) if len(item) > 1}


def _stringify(value: object) -> str:
    if isinstance(value, Mapping):
        # Schema keys such as "description" and "id" are not semantic
        # similarity evidence. Including them made unrelated components appear
        # close merely because both objects used the same field names.
        return " ".join(_stringify(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _enabled_capabilities(raw: object) -> set[str]:
    if not isinstance(raw, Mapping):
        return set()
    result: set[str] = set()
    for key, value in raw.items():
        if value is None or value is False or value in ("", "none", "unsupported"):
            continue
        result.add(str(key))
        if isinstance(value, str) and value not in {"true", "false"}:
            result.add(str(value))
    return result


def _target_context(
    interface: Mapping[str, Any], target: Mapping[str, Any]
) -> dict[str, list[str]]:
    scope, name = str(target.get("scope", "")), str(target.get("name", ""))
    channels = [item for item in interface.get("channels", []) if isinstance(item, Mapping)]
    signals = [item for item in interface.get("signals", []) if isinstance(item, Mapping)]
    if scope == "channel":
        selected_channels = [item for item in channels if str(item.get("name", "")) == name]
    elif scope == "protocol_group":
        selected_channels = [
            item for item in channels if str(item.get("protocol_group", "")) == name
        ]
    elif scope == "signal":
        channel_names = {
            str(item.get("channel", ""))
            for item in signals
            if str(item.get("name", "")) == name and item.get("channel")
        }
        selected_channels = [
            item for item in channels if str(item.get("name", "")) in channel_names
        ]
    else:
        selected_channels = channels
    channel_names = {str(item.get("name", "")) for item in selected_channels}
    selected_signals = [
        item
        for item in signals
        if (
            (scope == "signal" and str(item.get("name", "")) == name)
            or (
                scope != "signal"
                and str(item.get("channel", "")) in channel_names
            )
        )
    ]
    capabilities: set[str] = set()
    for channel in selected_channels:
        capabilities.update(_enabled_capabilities(channel.get("protocol_capabilities")))
    roles = {str(item.get("role", "")) for item in selected_signals if item.get("role")}
    if "valid" in roles:
        capabilities.add("handshake")
    if {"valid", "ready"} <= roles:
        capabilities.update({"backpressure", "stall_schedule"})
    selected_groups = {
        str(item.get("protocol_group", ""))
        for item in selected_channels
        if item.get("protocol_group")
    }
    semantic_profiles = [
        str(item.get("name", ""))
        for item in interface.get("protocol_semantics", [])
        if isinstance(item, Mapping)
        and (
            not selected_groups
            or selected_groups
            & set(map(str, item.get("protocol_groups", [])))
        )
    ]
    selected_signal_names = {
        str(item.get("name", "")) for item in selected_signals if item.get("name")
    }
    event_relations: list[str] = []
    for relation in interface.get("protocol_event_relations", []):
        if not isinstance(relation, Mapping):
            continue
        bindings = [relation.get("cause"), relation.get("effect")]
        cancellation = relation.get("cancellation", {})
        if isinstance(cancellation, Mapping):
            bindings.append(cancellation.get("event"))
        touches_target = scope == "interface"
        for binding in bindings:
            if not isinstance(binding, Mapping):
                continue
            kind = str(binding.get("kind", ""))
            if kind == "protocol_event" and str(binding.get("profile", "")) in semantic_profiles:
                touches_target = True
            elif kind == "standard_channel_transfer" and str(
                binding.get("protocol_group", "")
            ) in selected_groups:
                touches_target = True
            elif kind == "expression":
                expression_names = set(
                    re.findall(
                        r"[A-Za-z_][A-Za-z0-9_]*",
                        str(binding.get("expression", "")),
                    )
                )
                if expression_names & selected_signal_names:
                    touches_target = True
        if touches_target and relation.get("id"):
            event_relations.append(str(relation["id"]))
    return {
        "profiles": sorted({
            str(item.get("protocol_profile", ""))
            for item in selected_channels
            if item.get("protocol_profile")
        }),
        "roles": sorted(roles),
        "semantic_classes": sorted({
            str(item.get("semantic_class", ""))
            for item in selected_signals
            if item.get("semantic_class")
        }),
        "directions": sorted({
            str(item.get("direction", ""))
            for item in selected_channels
            if item.get("direction")
        }),
        "capabilities": sorted(capabilities),
        "protocol_semantics_profiles": sorted(filter(None, semantic_profiles)),
        "protocol_event_relations": sorted(set(event_relations)),
    }


def _request_requirements(
    request: Mapping[str, Any],
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> dict[str, Any]:
    context = _target_context(interface, request.get("target", {}))
    # A cross-protocol extension has one primary target but may explicitly
    # name a known standard participant in related_builtin_features.  Treat an
    # exact frozen profile name as binding context only when that profile is
    # actually present in the same interface; arbitrary feature names never
    # gain this authority.
    interface_profiles = {
        str(item.get("protocol_profile", ""))
        for item in interface.get("channels", [])
        if isinstance(item, Mapping) and item.get("protocol_profile")
    }
    related_profiles = interface_profiles & set(
        map(str, request.get("related_builtin_features", []))
    )
    context["profiles"] = sorted(set(context["profiles"]) | related_profiles)
    request_text = _tokens({
        "feature": request.get("feature_name", ""),
        "semantics": request.get("semantics", {}),
        "parameters": request.get("parameters", {}),
        "observations": request.get("required_observations", []),
    })
    # Interface capabilities establish whether an implementation can be bound;
    # they are not automatically work requested from the extension.  Treating
    # every capability on a broad interface target as required caused unrelated
    # memory/checker components to be selected for otherwise small extensions.
    capabilities: set[str] = set()
    feature_name = str(request.get("feature_name", ""))
    if feature_name:
        # The new feature itself always remains residual until its own
        # contract-local implementation exists. Similar built-ins may cover
        # constituent mechanics but cannot silently claim the new semantics.
        capabilities.add(feature_name)
    for spec in load_component_catalog():
        for capability in spec.capabilities:
            words = _tokens(capability)
            if words and words <= request_text:
                capabilities.add(capability)
    match = request.get("match", {})
    if isinstance(match, Mapping):
        capabilities.update(
            str(item.get("name", ""))
            for item in match.get("tags", [])
            if isinstance(item, Mapping) and item.get("name")
        )
    observation_kinds = {
        str(item.get("kind", ""))
        for item in request.get("required_observations", [])
        if isinstance(item, Mapping)
    }
    observation_names = {
        str(item.get("name", "")).lower()
        for item in request.get("required_observations", [])
        if isinstance(item, Mapping) and item.get("name")
    }
    if {"valid", "ready"} <= observation_names:
        capabilities.update({"handshake", "backpressure"})
    parameter_names = {
        str(name).lower() for name in request.get("parameters", {})
    }
    if any(
        marker in name
        for name in parameter_names
        for marker in ("cycle", "window", "stall", "delay")
    ):
        capabilities.update({"stall_schedule", "cycle_trace"})
    if "event" in observation_kinds:
        capabilities.add("cycle_trace")
    if "transaction" in observation_kinds:
        capabilities.add("transaction_trace")
    return {
        "domain": str(request.get("domain", "")),
        "target": dict(request.get("target", {})),
        **context,
        "available_capabilities": list(context["capabilities"]),
        "capabilities": sorted(capabilities),
        "request_tokens": sorted(request_text),
        "architecture_sections": sorted(
            str(key)
            for key, value in architecture.items()
            if value not in (None, [], {}, "")
        ),
    }


def _structural_compatibility(
    requirement: Mapping[str, Any], spec: ComponentSpec
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    profiles = set(map(str, requirement.get("profiles", [])))
    supported_profiles = set(spec.supported_profiles)
    if supported_profiles and "*" not in supported_profiles:
        if profiles and not profiles & supported_profiles:
            reasons.append("protocol_profile_mismatch")
    roles = set(map(str, requirement.get("roles", [])))
    missing_roles = set(spec.required_roles) - roles
    if missing_roles:
        reasons.append("missing_roles=" + ",".join(sorted(missing_roles)))
    semantics = set(map(str, requirement.get("semantic_classes", [])))
    missing_semantics = set(spec.required_semantic_classes) - semantics
    if missing_semantics:
        reasons.append("missing_semantics=" + ",".join(sorted(missing_semantics)))
    directions = set(map(str, requirement.get("directions", [])))
    supported_directions = set(spec.supported_directions)
    if supported_directions and directions and not directions & supported_directions:
        reasons.append("direction_mismatch")
    architecture_sections = set(
        map(str, requirement.get("architecture_sections", []))
    )
    missing_sections = set(spec.required_architecture_sections) - architecture_sections
    if missing_sections:
        reasons.append(
            "missing_architecture_sections=" + ",".join(sorted(missing_sections))
        )
    if spec.requires_protocol_semantics and not requirement.get(
        "protocol_semantics_profiles"
    ):
        reasons.append("missing_protocol_semantics")
    if spec.requires_protocol_event_relations and not requirement.get(
        "protocol_event_relations"
    ):
        reasons.append("missing_protocol_event_relations")
    return not reasons, reasons


def _rank(
    requirement: Mapping[str, Any], spec: ComponentSpec
) -> tuple[float, dict[str, Any]]:
    domain = str(requirement["domain"])
    if domain not in spec.domains and "common" not in spec.domains:
        return -1000.0, {"compatibility": "wrong_domain", "reasons": ["wrong_domain"]}
    compatible, reasons = _structural_compatibility(requirement, spec)
    required_caps = set(map(str, requirement.get("capabilities", [])))
    covered = required_caps & set(spec.capabilities)
    request_tokens = set(map(str, requirement.get("request_tokens", [])))
    component_tokens = _tokens({
        "id": spec.id,
        "description": spec.description,
        "tags": spec.tags,
        "terms": spec.match_terms,
        "capabilities": spec.capabilities,
    })
    lexical = request_tokens & component_tokens
    score = (35.0 if compatible else 0.0) + 16.0 * len(covered)
    # Prefer the more specific component when two implementations share one
    # component type.  For example, an operation-aware AXI memory driver is a
    # better fit than the protocol-only responder when operation metadata is
    # actually present; the responder remains available to pure bridges.
    score += 24.0 * len(spec.required_architecture_sections)
    if spec.required_roles and compatible:
        score += 10.0
    supported_profiles = set(spec.supported_profiles)
    if supported_profiles & set(requirement.get("profiles", [])):
        score += 18.0
    elif "*" in supported_profiles:
        score += 10.0
    if request_tokens | component_tokens:
        score += 20.0 * len(lexical) / len(request_tokens | component_tokens)
    if spec.auto_reuse:
        score += 2.0
    return score, {
        "compatibility": "compatible" if compatible else "reference_only",
        "reasons": reasons,
        "covered_capabilities": sorted(covered),
        "term_overlap": sorted(lexical)[:12],
    }


def _runtime_bindings(
    spec: ComponentSpec,
    requirement: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Return exact generated-block accessors for contract-bound components."""

    if spec.id == "protocol.driver.axi4_protocol_responder":
        from multigent.verifier_tool.pool.role_pool.standard_protocols import (
            compile_standard_protocol_plan,
        )

        selected = set(map(str, requirement.get("profiles", [])))
        return [
            {
                "protocol_group": str(group["name"]),
                "protocol_profile": str(group["profile"]),
                "generated_accessor": (
                    "_contract_standard_protocol_group("
                    f"{str(group['name'])!r}, {str(group['profile'])!r})"
                ),
            }
            for group in compile_standard_protocol_plan(
                interface, require_complete=False
            ).get("groups", [])
            if group.get("profile") in selected
            and group.get("profile") == "axi4"
            and group.get("endpoint_role") == "manager"
        ]
    if spec.id not in {
        "protocol.driver.contract_event_source",
        "protocol.monitor.contract_event_trace",
    }:
        return []
    from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
        compile_protocol_semantics,
    )

    selected = set(map(str, requirement.get("protocol_semantics_profiles", [])))
    bindings: list[dict[str, str]] = []
    for profile in compile_protocol_semantics(interface).get("profiles", []):
        profile_name = str(profile["name"])
        if profile_name not in selected:
            continue
        for transaction in profile.get("transactions", []):
            # A source driver can only bind a transaction that the testbench is
            # allowed to drive.  The trace monitor, however, is equally useful
            # for DUT-output transactions and must expose those exact bindings
            # too.  Conflating the two hid destination-side CDC evidence and
            # encouraged extension authors to invent ad-hoc trace fields.
            if (
                spec.id == "protocol.driver.contract_event_source"
                and transaction.get("source_drive") is None
            ):
                continue
            transaction_name = str(transaction["name"])
            bindings.append(
                {
                    "profile_name": profile_name,
                    "transaction_name": transaction_name,
                    "generated_accessor": (
                        "_contract_protocol_event_transaction("
                        f"{profile_name!r}, {transaction_name!r})"
                    ),
                }
            )
    return bindings


def resolve_extension_components(
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
    *,
    references_per_type: int = 2,
) -> dict[str, Any]:
    """Resolve exact reusable components and RAG references for each request."""

    from multigent.verifier_tool.extensions.authoring import extension_requests

    entries: list[dict[str, Any]] = []
    catalog = load_component_catalog()

    def payload(spec: ComponentSpec) -> dict[str, Any]:
        return {**spec.as_dict(), "call_contract": component_call_contract(spec)}

    for request in extension_requests(architecture):
        requirement = _request_requirements(request, architecture, interface)
        ranked: list[tuple[float, ComponentSpec, dict[str, Any]]] = []
        for spec in catalog:
            score, detail = _rank(requirement, spec)
            if score > -1000:
                ranked.append((score, spec, detail))
        ranked.sort(key=lambda item: (-item[0], item[1].id))

        automatic: list[dict[str, Any]] = []
        selected_types: set[str] = set()
        required_caps = set(requirement["capabilities"])
        for score, spec, detail in ranked:
            if spec.component_type in selected_types:
                continue
            if not spec.auto_reuse or detail["compatibility"] != "compatible":
                continue
            if (
                spec.component_type
                in {"protocol_source_driver", "protocol_sink_driver"}
                and request.get("target", {}).get("scope") == "interface"
                and len(requirement.get("profiles", [])) > 1
            ):
                # A mixed-protocol bridge has several unrelated source/sink
                # channels. Without an exact channel target, a generic helper is
                # an implementation reference rather than deterministic reuse.
                continue
            covered = set(detail["covered_capabilities"])
            if not covered:
                continue
            automatic.append({
                **payload(spec),
                "selection": "automatic_reuse",
                "similarity_score": round(score, 3),
                "runtime_bindings": _runtime_bindings(
                    spec, requirement, interface
                ),
                **detail,
            })
            selected_types.add(spec.component_type)

        covered_by_reuse = {
            capability
            for item in automatic
            for capability in item["covered_capabilities"]
        }
        selected_ids = {item["id"] for item in automatic}
        references: list[dict[str, Any]] = []
        reference_counts: dict[str, int] = {}
        for score, spec, detail in ranked:
            if spec.id in selected_ids:
                continue
            count = reference_counts.get(spec.component_type, 0)
            if count >= references_per_type:
                continue
            if score <= 0:
                continue
            if not detail["covered_capabilities"] and not detail["term_overlap"]:
                continue
            references.append({
                **payload(spec),
                "selection": "rag_reference_only",
                "similarity_score": round(score, 3),
                **detail,
                "usage": "reference_shape_only_do_not_change_frozen_semantics",
            })
            reference_counts[spec.component_type] = count + 1
        required_explicit = sorted(
            item["id"]
            for item in automatic
            if item.get("execution_owner") == "verifier_extension"
        )
        pipeline_managed = sorted(
            item["id"]
            for item in automatic
            if item.get("execution_owner") == "pipeline"
        )
        entries.append({
            "request_id": str(request["id"]),
            "requirement": {
                key: value for key, value in requirement.items() if key != "request_tokens"
            },
            "automatic_reuse": automatic,
            "required_reuse_component_ids": required_explicit,
            "pipeline_managed_reuse_component_ids": pipeline_managed,
            "covered_capabilities": sorted(covered_by_reuse),
            "residual_capabilities": sorted(required_caps - covered_by_reuse),
            "rag_component_references": references,
            "llm_rule": (
                "Call every required_reuse_component_id through its normative "
                "call_contract. Do not manually call pipeline-managed components. "
                "Implement only residual_capabilities in contract-local source. "
                "RAG references are analogies, never authority to alter the contract."
            ),
        })
    return {"schema_version": 1, "entries": entries}


def build_contract_local_component_manifests(
    architecture: Mapping[str, Any],
    bundles: Sequence[Mapping[str, Any]],
    interface: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Derive auditable local component descriptors from normalized bundles."""

    resolution = {
        str(item["request_id"]): item
        for item in resolve_extension_components(architecture, interface)["entries"]
    }
    manifests: list[dict[str, Any]] = []
    branch_types = {
        "assertion": ("assertion_checker", "contract_local_assertion_v1"),
        "coverage": ("coverage_sampler", "contract_local_coverage_v1"),
    }
    for bundle in bundles:
        request_id = str(bundle.get("request_id", ""))
        resolved = resolution.get(request_id, {})
        residual = list(map(str, resolved.get("residual_capabilities", [])))
        for branch_name in ("assertion", "coverage", "stimulus"):
            branch = bundle.get(branch_name, {})
            implementation = branch.get("implementation", {}) if isinstance(branch, Mapping) else {}
            if branch_name == "stimulus":
                component_type = (
                    "protocol_source_driver"
                    if bundle.get("domain") == "protocol"
                    else "lifecycle_driver"
                    if bundle.get("domain") == "lifecycle"
                    else "stimulus_strategy"
                )
                abi = "contract_local_stimulus_v1"
            else:
                component_type, abi = branch_types[branch_name]
            manifests.append({
                "id": f"contract_local.{request_id}.{branch_name}",
                "request_id": request_id,
                "domain": str(bundle.get("domain", "")),
                "component_type": component_type,
                "abi": abi,
                "file": implementation.get("file"),
                "symbol": implementation.get("symbol"),
                "implements_residual_capabilities": residual,
                "reuses_components": list(map(str, bundle.get("reuse", {}).get("helpers", []))),
                "promotion": "not_implemented",
                "scope": "contract_local_only",
            })
    return manifests


__all__ = [
    "build_contract_local_component_manifests",
    "resolve_extension_components",
]
