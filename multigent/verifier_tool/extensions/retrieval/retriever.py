"""Retrieve reusable verification shapes without weakening the frozen contract.

This is deliberately a deterministic first-stage RAG retriever.  It indexes the
checked-in protocol, lifecycle, operation, and lifecycle-policy pools, filters by
domain, and ranks candidates by structural compatibility before lexical overlap.
The returned entries are analogies only: they never add requirements, change the
request, or claim that an unsupported feature has become code-owned.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Mapping

import yaml


HERE = Path(__file__).resolve().parent
POOL_ROOT = HERE.parents[1] / "pool"
FEATURE_ROOT = POOL_ROOT / "feature_plans"
POLICY_PATH = POOL_ROOT / "lifecycle_policy_pool" / "lifecycle_policies.yaml"

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "one", "or", "the", "to", "when",
    "with", "without", "behavior", "feature", "observe", "observed",
}
_TEMPORAL_FAMILIES = {
    "handshake": {"accept", "accepted", "grant", "handshake", "ready", "valid"},
    "stall": {"backpressure", "hold", "remain", "stability", "stable", "stall", "wait"},
    "phase": {"access", "phase", "setup", "sequence", "transition"},
    "pulse": {"cycle", "onecycle", "pulse", "width"},
    "delay": {"after", "before", "deadline", "delay", "latency", "later", "window"},
    "ordering": {"correlate", "correlation", "id", "order", "ordering", "response", "split"},
    "reset": {"abort", "clear", "release", "reset"},
    "error": {"error", "illegal", "recover", "recovery", "responsecode"},
    "lifecycle": {"active", "busy", "command", "complete", "completion", "job", "retire"},
    "math": {"accumulation", "activation", "golden", "matrix", "operand", "quantization"},
}


def _load(path: Path) -> Mapping[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, Mapping) else {}


def _tokens(value: object) -> set[str]:
    if isinstance(value, Mapping):
        text = " ".join(f"{key} {_stringify(item)}" for key, item in value.items())
    else:
        text = _stringify(value)
    words: set[str] = set()
    for raw in _TOKEN_RE.findall(text.replace("_", " ").replace("-", " ")):
        split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw).lower().split()
        words.update(word for word in split if len(word) > 1 and word not in _STOP)
    return words


def _stringify(value: object) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{key} {_stringify(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _temporal_families(tokens: set[str]) -> set[str]:
    return {
        family for family, vocabulary in _TEMPORAL_FAMILIES.items()
        if tokens & vocabulary
    }


def _document(
    *, identity: str, domain: str, scope: str, source: str,
    description: str, match: Mapping[str, Any] | None = None,
    assertion: Mapping[str, Any] | None = None,
    coverage: Mapping[str, Any] | None = None,
    stimulus: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    template = {
        "match": dict(match or {}),
        "assertion": dict(assertion or {}),
        "coverage": dict(coverage or {}),
        "stimulus": dict(stimulus or {}),
    }
    token_set = _tokens(
        {"id": identity, "scope": scope, "description": description, **template}
    )
    return {
        "id": identity,
        "domain": domain,
        "scope": scope,
        "source": source,
        "description": description,
        "template": template,
        "_tokens": token_set,
        "_temporal": _temporal_families(token_set),
        "_roles": set(map(str, (match or {}).get("required_roles", []))),
        "_profiles": {
            str(value)
            for value in (
                [(match or {}).get("protocol_profile")]
                if (match or {}).get("protocol_profile")
                else (match or {}).get("protocol_profiles", [])
            )
        },
    }


@lru_cache(maxsize=1)
def _corpus() -> tuple[dict[str, Any], ...]:
    documents: list[dict[str, Any]] = []
    for domain, filename in (
        ("protocol", "protocol_features.yaml"),
        ("lifecycle", "lifecycle_features.yaml"),
    ):
        raw = _load(FEATURE_ROOT / filename)
        for name, feature in raw.get("features", {}).items():
            if not isinstance(feature, Mapping):
                continue
            documents.append(_document(
                identity=f"{domain}.{name}", domain=domain,
                scope=str(feature.get("scope", "")),
                source=f"pool/feature_plans/{filename}",
                description=str(feature.get("description", "")),
                match=feature.get("match", {}), assertion=feature.get("assertion", {}),
                coverage=feature.get("coverage", {}), stimulus=feature.get("stimulus", {}),
            ))
        if domain == "lifecycle":
            for name, feature in raw.get("operation_features", {}).items():
                if not isinstance(feature, Mapping):
                    continue
                documents.append(_document(
                    identity=f"lifecycle.{name}", domain="lifecycle",
                    scope=str(feature.get("scope", "operation")),
                    source=f"pool/feature_plans/{filename}", description=name,
                    assertion=feature.get("assertion", {}),
                    coverage=feature.get("coverage", {}), stimulus=feature.get("stimulus", {}),
                ))

    operation = _load(FEATURE_ROOT / "operation_features.yaml")
    defaults = operation.get("feature_defaults", {})
    for family_name, family in operation.get("families", {}).items():
        if not isinstance(family, Mapping):
            continue
        concepts: dict[str, Any] = {
            str(name): bins for name, bins in family.get("starter_bins", {}).items()
        }
        for group in family.get("feature_groups", {}).values():
            if not isinstance(group, Mapping):
                continue
            for name, concept in group.get("optional_concepts", {}).items():
                concepts[str(name)] = (
                    concept.get("starter_bins", [])
                    if isinstance(concept, Mapping) else []
                )
        for concept, bins in concepts.items():
            documents.append(_document(
                identity=f"operation.{family_name}.{concept}", domain="operation",
                scope="operation", source="pool/feature_plans/operation_features.yaml",
                description=f"{family_name} {concept}",
                assertion=defaults.get("assertion", {}),
                coverage={**dict(defaults.get("coverage", {})), "bins": bins},
                stimulus=defaults.get("stimulus", {}),
            ))

    policies = _load(POLICY_PATH)
    for policy_name, policy in policies.get("policies", {}).items():
        if not isinstance(policy, Mapping):
            continue
        for choice, meaning in policy.get("choices", {}).items():
            documents.append(_document(
                identity=f"lifecycle.policy.{policy_name}.{choice}",
                domain="lifecycle", scope="operation",
                source="pool/lifecycle_policy_pool/lifecycle_policies.yaml",
                description=f"{policy.get('description', '')} {meaning}",
                match={"policy_field": policy_name, "choice": choice},
            ))
    return tuple(documents)


def _scope_score(request_scope: str, candidate_scope: str) -> float:
    if request_scope == candidate_scope:
        return 18.0
    if request_scope == "interface" and candidate_scope in {
        "channel", "signal", "standard_channel", "standard_group", "protocol_group",
    }:
        return 7.0
    if request_scope == "operation" and candidate_scope in {"signal", "channel"}:
        return 3.0
    return 0.0


def _request_tokens(request: Mapping[str, Any]) -> set[str]:
    """Tokenize behavioral content without scoring schema boilerplate."""

    semantics = request.get("semantics", {})
    observations = request.get("required_observations", [])
    return _tokens({
        "id": request.get("feature_name", request.get("id", "")),
        "semantics": list(semantics.values()) if isinstance(semantics, Mapping) else semantics,
        "parameters": request.get("parameters", {}),
        "observations": [
            [item.get("name", ""), item.get("kind", ""), item.get("description", "")]
            for item in observations
            if isinstance(item, Mapping)
        ],
        "related": request.get("related_builtin_features", []),
    })


def _interface_context(
    interface: Mapping[str, Any] | None,
) -> tuple[set[str], set[str], set[str]]:
    if not isinstance(interface, Mapping):
        return set(), set(), set()
    roles: set[str] = set()
    semantics: set[str] = set()
    profiles = {
        str(item.get("protocol_profile", ""))
        for item in interface.get("channels", [])
        if isinstance(item, Mapping) and item.get("protocol_profile")
    }
    for signal in interface.get("signals", []):
        if not isinstance(signal, Mapping):
            continue
        if signal.get("role"):
            roles.add(str(signal["role"]))
        if signal.get("semantic_class"):
            semantics.add(str(signal["semantic_class"]))
    return roles, semantics, profiles


def _score(
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    interface_roles: set[str],
    interface_semantics: set[str],
    interface_profiles: set[str],
) -> tuple[float, list[str]]:
    request_tokens = _request_tokens(request)
    candidate_tokens = set(candidate["_tokens"])
    request_temporal = _temporal_families(request_tokens)
    temporal_overlap = request_temporal & set(candidate["_temporal"])
    lexical_overlap = request_tokens & candidate_tokens
    lexical_union = request_tokens | candidate_tokens
    score = _scope_score(
        str(request.get("target", {}).get("scope", "")), str(candidate["scope"])
    )
    reasons: list[str] = []
    if score:
        reasons.append("compatible_scope")
    if temporal_overlap:
        score += 13.0 * len(temporal_overlap)
        reasons.append("temporal=" + ",".join(sorted(temporal_overlap)))
    if lexical_union:
        score += 30.0 * len(lexical_overlap) / len(lexical_union)
    if lexical_overlap:
        reasons.append("terms=" + ",".join(sorted(lexical_overlap)[:8]))
    candidate_roles = set(candidate["_roles"])
    if candidate_roles:
        role_overlap = candidate_roles & interface_roles
        if role_overlap:
            score += 8.0 * len(role_overlap) / len(candidate_roles)
            reasons.append("roles=" + ",".join(sorted(role_overlap)))
        elif interface_roles:
            score -= 8.0
    candidate_profiles = set(candidate["_profiles"])
    if candidate_profiles:
        profile_overlap = candidate_profiles & interface_profiles
        if profile_overlap:
            score += 14.0
            reasons.append("profile=" + ",".join(sorted(profile_overlap)))
        elif interface_profiles:
            score -= 24.0
            reasons.append("protocol_profile_mismatch")
    template = candidate["template"]
    implementation_parts = {
        "checker": bool(template.get("assertion", {}).get("checker")),
        "sampler": bool(template.get("coverage", {}).get("sampler")),
        "strategy": bool(template.get("stimulus", {}).get("strategy")),
    }
    implemented = [name for name, present in implementation_parts.items() if present]
    score += 5.0 * len(implemented)
    if implemented:
        reasons.append("reusable=" + ",".join(implemented))
    semantic_overlap = interface_semantics & candidate_tokens
    if semantic_overlap:
        score += min(6.0, 2.0 * len(semantic_overlap))
        reasons.append("semantics=" + ",".join(sorted(semantic_overlap)[:4]))
    related = set(map(str, request.get("related_builtin_features", [])))
    candidate_id = str(candidate["id"])
    if candidate_id in related or candidate_id.rsplit(".", 1)[-1] in related:
        score += 35.0
        reasons.append("architect_related_feature")
    observation_kinds = {
        str(item.get("kind", ""))
        for item in request.get("required_observations", [])
        if isinstance(item, Mapping)
    }
    if observation_kinds & {"event", "transaction"} and candidate["_temporal"]:
        score += 5.0
        reasons.append("temporal_evidence_shape")
    return score, reasons


def retrieve_extension_analogues(
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any] | None = None,
    *,
    top_k: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    """Return top structural analogues for every unsupported feature request."""

    from multigent.verifier_tool.extensions.authoring import extension_requests

    result: dict[str, list[dict[str, Any]]] = {}
    interface_roles, interface_semantics, interface_profiles = _interface_context(interface)
    for request in extension_requests(architecture):
        domain = str(request["domain"])
        ranked: list[tuple[float, str, Mapping[str, Any], list[str]]] = []
        for candidate in _corpus():
            if candidate["domain"] != domain:
                continue
            score, reasons = _score(
                request,
                candidate,
                interface_roles=interface_roles,
                interface_semantics=interface_semantics,
                interface_profiles=interface_profiles,
            )
            ranked.append((score, str(candidate["id"]), candidate, reasons))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        result[str(request["id"])] = [
            {
                "id": candidate["id"],
                "domain": candidate["domain"],
                "scope": candidate["scope"],
                "source": candidate["source"],
                "similarity_score": round(score, 3),
                "match_reasons": reasons,
                "description": candidate["description"],
                "reusable_shape": candidate["template"],
                "usage": "analogy_only_preserve_frozen_request_semantics",
            }
            for score, _, candidate, reasons in ranked[:top_k]
            if score > 0
        ]
    return result


__all__ = ["retrieve_extension_analogues"]
