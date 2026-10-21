"""Structural and deterministic preflight for every frozen benchmark case."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import yaml

from multigent.verifier_tool import (
    extension_requests,
    operation_formula_compilation_report,
    review_contract_deterministically,
)

from .build_contracts import (
    CASES_ROOT,
    HERE,
    _case_index,
    _case_readme,
    build_case,
    load_catalog,
)


def _load_case(case_id: str) -> tuple[dict, dict, dict, dict, dict]:
    root = CASES_ROOT / case_id
    return (
        yaml.safe_load((root / "architecture_contract.yaml").read_text()),
        yaml.safe_load((root / "interface_contract.yaml").read_text()),
        json.loads((root / "module_manifest.json").read_text()),
        yaml.safe_load((root / "acceptance_criteria.yaml").read_text()),
        yaml.safe_load((root / "benchmark_manifest.yaml").read_text()),
    )


def test_catalog_has_thirty_unique_balanced_cases() -> None:
    cases = load_catalog()
    assert len(cases) == 30
    assert len({case["id"] for case in cases}) == 30
    assert len({tuple(case["features"]) for case in cases}) == 30
    assert Counter(map(lambda case: len(case["features"]), cases)) == {
        1: 5,
        2: 5,
        3: 5,
        4: 5,
        5: 5,
        6: 5,
    }


def test_materialized_contracts_match_builder_and_pass_preflight() -> None:
    manifests = []
    for case in load_catalog():
        case_id = str(case["id"])
        architecture, interface, modules, acceptance, manifest = _load_case(case_id)
        expected_artifacts, expected_manifest = build_case(case)
        assert architecture == expected_artifacts["architecture_contract"]
        assert interface == expected_artifacts["interface_contract"]
        assert modules == expected_artifacts["module_manifest"]
        assert acceptance == expected_artifacts["acceptance_criteria"]
        assert manifest == expected_manifest
        manifests.append(manifest)
        assert (CASES_ROOT / case_id / "README.md").read_text() == _case_readme(
            manifest
        )
        assert manifest["unknown_feature_count"] == len(case["features"])
        assert {item["id"] for item in manifest["features"]} == set(case["features"])

        review = review_contract_deterministically(
            architecture, interface, modules, acceptance
        )
        assert review["status"] == "PASS", (case_id, review["findings"])

        requests = extension_requests(architecture)
        request_ids = {request["id"] for request in requests}
        expected_requests = {
            item["id"]
            for item in manifest["features"]
            if item["representation"] == "verifier_extension_request"
        }
        assert request_ids == expected_requests

        compilation = operation_formula_compilation_report(architecture)
        assert compilation["status"] == "PASS", (case_id, compilation)
        compiled_names = {
            stage["stage"]
            for operation in compilation.get("operations", [])
            for stage in operation.get("stages", [])
            if stage.get("status") == "solver_compiled"
        }
        expected_formula_names = {
            item["stage_name"]
            for item in manifest["features"]
            if item["representation"] == "solver_compiled_formula"
        }
        assert compiled_names == expected_formula_names, (
            case_id,
            compiled_names,
            expected_formula_names,
        )
    assert (HERE / "CASE_INDEX.md").read_text() == _case_index(manifests)


def test_every_case_covers_its_declared_domains() -> None:
    for case in load_catalog():
        _, _, _, _, manifest = _load_case(str(case["id"]))
        assert manifest["domains"] == sorted(
            {item["domain"] for item in manifest["features"]}
        )
        assert set(manifest["domains"]) <= {"operation", "protocol", "lifecycle"}
