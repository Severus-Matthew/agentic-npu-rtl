"""Materialize the 30 frozen contracts in this benchmark corpus.

The builder performs no model or network call.  It starts from the real
ready/valid GEMM fixture and applies only the explicitly listed unknown
features.  Checked-in outputs are frozen inputs for later Verifier evaluation;
regeneration must be followed by the benchmark regression.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import yaml

from multigent.verifier_tool.tool_regression.api_evaluation.contexts import (
    api_scenarios,
)
from multigent.verifier_tool.tool_regression.paths import VERIFIER_TOOL_ROOT


HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "benchmark_catalog.yaml"
CASES_ROOT = HERE / "cases"
BASE_ROOT = (
    VERIFIER_TOOL_ROOT
    / "tool_regression"
    / "benchmarks"
    / "ready_valid_tiny_gemm"
)


def load_catalog() -> list[dict[str, Any]]:
    document = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("extension benchmark catalog requires schema_version=1")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("extension benchmark catalog requires cases")
    return [dict(item) for item in cases]


def _base_artifacts() -> dict[str, Any]:
    architecture = yaml.safe_load(
        (BASE_ROOT / "architecture_contract_a.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (BASE_ROOT / "interface_contract_a.yaml").read_text(encoding="utf-8")
    )
    return {
        "architecture_contract": architecture,
        "interface_contract": interface,
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
            "functional": [
                "Every accepted output equals the frozen arithmetic DAG."
            ],
            "verification": [
                "Exercise all built-in obligations and every declared unknown feature."
            ],
            "rtl": ["No generated RTL is visible to the independent Verifier."],
            "fpga_handoff": ["Outside this Verifier-only benchmark."],
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
            "forbidden_behavior": list(
                map(str, spec.get("forbidden_behavior", []))
            ),
        },
        "reason": (
            f"The built-in {domain} pool does not represent this exact behavior."
        ),
        "parameters": deepcopy(dict(spec.get("parameters", {}))),
        "required_observations": [
            {
                "name": name,
                "kind": _observation_kind(name),
                "description": f"Frozen-contract evidence required for {name}.",
            }
            for name in observations
        ],
        "related_builtin_features": list(
            map(str, spec.get("related_builtin_features", []))
        ),
    }
    if domain == "protocol":
        request["match"] = {
            "tags": [{"source": "builtin", "name": "handshake"}],
            "required_roles": [
                name for name in observations if name in {"valid", "ready", "payload"}
            ],
            "required_semantic_classes": [],
            "required_protocol_profiles": ["ready_valid"],
        }
    return request


def _apply_formula(architecture: dict[str, Any], spec: Mapping[str, Any]) -> None:
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
    operation["semantics"] += (
        f" Then apply {stage_name}(value) = {spec['formula']}."
    )


def build_case(case: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts = _base_artifacts()
    architecture = artifacts["architecture_contract"]
    scenario_catalog = api_scenarios()
    requests: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    for identity in map(str, case["features"]):
        spec = scenario_catalog.get(identity)
        if spec is None or spec.get("kind") == "composition":
            raise ValueError(f"case {case['id']!r} has invalid atomic feature {identity!r}")
        if spec["kind"] == "solver_formula":
            _apply_formula(architecture, spec)
            representation = "solver_compiled_formula"
            representation_detail = {"stage_name": str(spec["stage_name"])}
        elif spec["kind"] == "extension_request":
            requests.append(_extension_request(spec))
            representation = "verifier_extension_request"
            representation_detail = {"request_id": identity}
        else:
            raise ValueError(f"unsupported feature kind {spec['kind']!r}")
        inventory.append(
            {
                "id": identity,
                "domain": str(spec["domain"]),
                "representation": representation,
                **representation_detail,
                "intent": str(spec.get("intent", spec.get("summary", ""))),
            }
        )
    if requests:
        architecture["verification_extensions"] = requests
    else:
        architecture.pop("verification_extensions", None)
    architecture["design"]["name"] = str(case["id"])
    architecture["design"]["description"] += (
        f" Frozen extension benchmark {case['id']} with {len(inventory)} unknown features."
    )
    manifest = {
        "schema_version": 1,
        "case_id": str(case["id"]),
        "unknown_feature_count": len(inventory),
        "domains": sorted({item["domain"] for item in inventory}),
        "features": inventory,
        "provenance": {
            "contract_author": "benchmark_builder",
            "includes_generated_rtl": False,
            "includes_verifier_output": False,
            "includes_model_output": False,
        },
    }
    return artifacts, manifest


def _feature_summary(item: Mapping[str, Any]) -> str:
    if item["representation"] == "solver_compiled_formula":
        detail = f"solver DAG stage `{item['stage_name']}`"
    else:
        detail = f"Verifier extension request `{item['request_id']}`"
    return (
        f"- `{item['id']}` ({item['domain']}): {item['intent']}  "
        f"Representation: {detail}."
    )


def _case_readme(manifest: Mapping[str, Any]) -> str:
    feature_lines = "\n".join(
        _feature_summary(item) for item in manifest["features"]
    )
    return f"""# {manifest['case_id']}

## Baseline

This case starts from the checked-in `ready_valid_tiny_gemm_a` frozen
contract: a fixed M=1, K=4, N=1 signed-integer GEMM, followed by bias addition
and ReLU. It uses separate ready/valid channels for command, A, B, bias, and Y;
single-inflight job control; a busy signal; one-cycle completion and error
pulses; and reset-aborts-inflight behavior.

The baseline RTL is intentionally not copied into this contract-input folder.
`module_manifest.json` names `tiny_gemm_rv_a_top`; its benchmark RTL is
[`tiny_gemm_rv_a_top.v`](../../../ready_valid_tiny_gemm/rtl_a/tiny_gemm_rv_a_top.v).
This corpus evaluates frozen contract inputs first; a later RTL campaign
must explicitly choose a compatible baseline or mutant.

## Unknown features ({manifest['unknown_feature_count']})

{feature_lines}

## Direct inputs

The files below are fully materialized and may be passed to one Verifier run
without regenerating this case:

- `architecture_contract.yaml`
- `interface_contract.yaml`
- `module_manifest.json`
- `acceptance_criteria.yaml`
- `benchmark_manifest.yaml`

`benchmark_manifest.yaml` is evaluation metadata, not part of the frozen
Architect contract. No Verifier output, generated TB, or model response is
stored in this directory.
"""


def _case_index(manifests: list[Mapping[str, Any]]) -> str:
    rows = []
    for manifest in manifests:
        feature_ids = "<br>".join(
            f"`{item['id']}`" for item in manifest["features"]
        )
        rows.append(
            f"| [`{manifest['case_id']}`](cases/{manifest['case_id']}/) "
            f"| {manifest['unknown_feature_count']} "
            f"| {', '.join(manifest['domains'])} | {feature_ids} |"
        )
    return """# Frozen extension benchmark case index

## Shared baseline

All 30 cases start from the same frozen `ready_valid_tiny_gemm_a` contract:

- fixed signed GEMM dimensions: M=1, K=4, N=1;
- arithmetic: signed products, wrapping signed accumulation, bias, then ReLU;
- command, A, B, bias, and Y use separate ready/valid channels;
- one job may be active at a time;
- `busy`, one-cycle `done`, one-cycle `err`, and reset-aborts-inflight lifecycle;
- top module: `tiny_gemm_rv_a_top`;
- baseline RTL location: `../ready_valid_tiny_gemm/rtl_a/tiny_gemm_rv_a_top.v`.

Every linked directory contains real, frozen YAML/JSON inputs. The builder is
only for deterministic regeneration; an evaluator may select and run one case
directly from its directory.

## Cases

| Case | Unknown count | Domains | Unknown features |
|---|---:|---|---|
""" + "\n".join(rows) + "\n"


def materialize(*, clean: bool = True) -> None:
    if clean and CASES_ROOT.exists():
        shutil.rmtree(CASES_ROOT)
    CASES_ROOT.mkdir(parents=True, exist_ok=True)
    manifests: list[dict[str, Any]] = []
    for case in load_catalog():
        artifacts, manifest = build_case(case)
        manifests.append(manifest)
        destination = CASES_ROOT / str(case["id"])
        destination.mkdir(parents=True, exist_ok=False)
        for name in ("architecture_contract", "interface_contract"):
            (destination / f"{name}.yaml").write_text(
                yaml.safe_dump(
                    artifacts[name], sort_keys=False, default_flow_style=False
                ),
                encoding="utf-8",
            )
        (destination / "module_manifest.json").write_text(
            json.dumps(artifacts["module_manifest"], indent=2) + "\n",
            encoding="utf-8",
        )
        (destination / "acceptance_criteria.yaml").write_text(
            yaml.safe_dump(
                artifacts["acceptance_criteria"],
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        (destination / "benchmark_manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        (destination / "README.md").write_text(
            _case_readme(manifest), encoding="utf-8"
        )
    (HERE / "CASE_INDEX.md").write_text(
        _case_index(manifests), encoding="utf-8"
    )


if __name__ == "__main__":
    materialize()
    print(f"Wrote {len(load_catalog())} frozen extension benchmark cases to {CASES_ROOT}")
