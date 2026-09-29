"""Build frozen Verifier contexts from the paper-facing scenario catalog."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.verifier_tool.tool_regression.paths import VERIFIER_TOOL_ROOT


HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "scenario_catalog.yaml"
_BENCHMARK = (
    VERIFIER_TOOL_ROOT / "tool_regression" / "benchmarks" / "ready_valid_tiny_gemm"
)


@lru_cache(maxsize=1)
def api_scenarios() -> dict[str, dict[str, Any]]:
    document = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("API evaluation catalog requires schema_version=1")
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("API evaluation catalog requires scenarios")
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(scenarios):
        if not isinstance(raw, Mapping):
            raise ValueError(f"scenario[{index}] must be a mapping")
        item = dict(raw)
        identity = str(item.get("id", ""))
        if not identity or identity in result:
            raise ValueError(f"scenario[{index}] has invalid or duplicate id {identity!r}")
        result[identity] = item
    return result


def _base_context() -> dict[str, Any]:
    architecture = yaml.safe_load(
        (_BENCHMARK / "architecture_contract_a.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (_BENCHMARK / "interface_contract_a.yaml").read_text(encoding="utf-8")
    )
    return {
        "user_request": (
            "Verify the frozen 1x4x1 signed integer GEMM contract with bias and ReLU, "
            "including every explicitly declared contract-local behavior."
        ),
        "verification_policy": {
            "exact_integer_match_when_applicable": True,
            "randomized_transactions_minimum": 8,
            "require_reset_tests": True,
            "require_backpressure_tests_when_applicable": True,
            "regression_wall_timeout_seconds_minimum": 120,
            "require_completion_behavior_tests_when_defined": True,
            "require_error_behavior_tests_when_defined": True,
        },
        "frozen_architecture": {
            "architecture_contract": deepcopy(architecture),
            "interface_contract": deepcopy(interface),
            "module_manifest": {
                "top": "tiny_gemm_rv_a_top",
                "modules": [
                    {
                        "name": "tiny_gemm_rv_a_top",
                        "responsibility": "Frozen ready/valid GEMM top level.",
                        "dependencies": [],
                        "parameters": [],
                        "stateful": True,
                    }
                ],
            },
            "acceptance_criteria": {
                "functional": ["Every accepted output equals the frozen arithmetic DAG."],
                "verification": [
                    "Exercise all built-in obligations and every declared residual feature."
                ],
                "rtl": ["No generated RTL is visible to the independent Verifier."],
                "fpga_handoff": ["Outside this Verifier-only evaluation."],
            },
        },
        "provenance": {
            "includes_generated_rtl": False,
            "includes_rtl_generator_output": False,
        },
    }


def _observation_kind(name: str) -> str:
    if name in {"valid", "ready", "payload", "busy", "completion", "error"}:
        return "signal"
    if name in {"golden_trace", "expected_value"}:
        return "golden_trace"
    if name in {"configuration", "parameters"}:
        return "configuration"
    return "event"


def _extension_request(spec: Mapping[str, Any]) -> dict[str, Any]:
    domain = str(spec["domain"])
    observations = [str(item) for item in spec.get("observations", [])]
    request: dict[str, Any] = {
        "id": str(spec["id"]),
        "domain": domain,
        "feature_name": str(spec["feature_name"]),
        "target": deepcopy(dict(spec["target"])),
        "semantics": {
            "summary": str(spec["summary"]),
            "trigger": str(spec["trigger"]),
            "required_behavior": list(map(str, spec["required_behavior"])),
            "end_condition": str(spec["end_condition"]),
            "forbidden_behavior": list(map(str, spec.get("forbidden_behavior", []))),
        },
        "reason": (
            f"The built-in {domain} pool does not represent this exact residual behavior."
        ),
        "parameters": deepcopy(dict(spec.get("parameters", {}))),
        "required_observations": [
            {
                "name": name,
                "kind": _observation_kind(name),
                "description": f"Frozen-contract observation required for {name}.",
            }
            for name in observations
        ],
        "related_builtin_features": list(
            map(str, spec.get("related_builtin_features", []))
        ),
    }
    if domain == "protocol":
        required_roles = [
            name for name in observations if name in {"valid", "ready", "payload"}
        ]
        request["match"] = {
            "tags": [{"source": "builtin", "name": "handshake"}],
            "required_roles": required_roles,
            "required_semantic_classes": [],
            "required_protocol_profiles": ["ready_valid"],
        }
    return request


def _apply_formula(context: dict[str, Any], spec: Mapping[str, Any]) -> None:
    architecture = context["frozen_architecture"]["architecture_contract"]
    operation = architecture["operations"][0]
    arithmetic = operation["arithmetic"]
    predecessor = str(arithmetic["post_output"])
    stage_name = str(spec["stage_name"])
    arithmetic["post_operations"][stage_name] = {
        "kind": "llm_defined",
        "depends_on": [predecessor],
        "formula": str(spec["formula"]),
    }
    arithmetic["post_output"] = stage_name
    operation["semantics"] = (
        f"Apply {stage_name}(value) = {spec['formula']} after the existing signed "
        "integer GEMM, bias, and ReLU DAG, then use the declared result conversion."
    )
    architecture["design"]["description"] += (
        f" Solver-compiled post-operation {stage_name}(value) = {spec['formula']}."
    )


def _atomic_components(identity: str) -> list[dict[str, Any]]:
    catalog = api_scenarios()
    if identity not in catalog:
        raise KeyError(f"unknown API evaluation scenario {identity!r}")
    selected = catalog[identity]
    if selected["kind"] != "composition":
        return [selected]
    result: list[dict[str, Any]] = []
    for child in selected.get("components", []):
        nested = catalog.get(str(child))
        if nested is None or nested.get("kind") == "composition":
            raise ValueError(f"composition {identity!r} has invalid component {child!r}")
        result.append(nested)
    return result


def scenario_context(identity: str) -> dict[str, Any]:
    context = _base_context()
    architecture = context["frozen_architecture"]["architecture_contract"]
    requests: list[dict[str, Any]] = []
    for component in _atomic_components(identity):
        kind = str(component["kind"])
        if kind == "solver_formula":
            _apply_formula(context, component)
        elif kind == "extension_request":
            requests.append(_extension_request(component))
        else:
            raise ValueError(f"unsupported API evaluation scenario kind {kind!r}")
    if requests:
        architecture["verification_extensions"] = requests
    else:
        architecture.pop("verification_extensions", None)
    context["evaluation_scenario"] = {
        "id": identity,
        "domain": str(api_scenarios()[identity]["domain"]),
    }
    return context


def expected_extension_request_ids(identity: str) -> list[str]:
    return [
        str(item["id"])
        for item in _atomic_components(identity)
        if item["kind"] == "extension_request"
    ]


def expected_formula_concepts(identity: str) -> list[str]:
    return [
        str(item["stage_name"])
        for item in _atomic_components(identity)
        if item["kind"] == "solver_formula"
    ]


__all__ = [
    "CATALOG_PATH",
    "api_scenarios",
    "expected_extension_request_ids",
    "expected_formula_concepts",
    "scenario_context",
]
