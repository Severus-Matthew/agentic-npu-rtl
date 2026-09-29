"""Local catalog gates plus one explicitly opt-in Verifier API case."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.verifier import VERIFIER_OUTPUT_SCHEMA, VerifierAgent
from multigent.verifier_tool import (
    decode_verifier_extension_transport,
    extension_bundle_schema,
    operation_formula_compilation_report,
    review_contract_deterministically,
    validate_architect_extension_requests,
)

from .contexts import (
    api_scenarios,
    expected_extension_request_ids,
    expected_formula_concepts,
    scenario_context,
)
from .runner import run_selected


HERE = Path(__file__).resolve().parent


def _assert_openai_strict_object_shapes(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False, path
            assert set(value.get("required", [])) == set(
                value.get("properties", {})
            ), path
        for key, child in value.items():
            _assert_openai_strict_object_shapes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_openai_strict_object_shapes(child, f"{path}[{index}]")


def test_catalog_is_balanced_and_paper_reviewable() -> None:
    scenarios = api_scenarios()
    counts = {
        domain: sum(item["domain"] == domain for item in scenarios.values())
        for domain in ("operation", "protocol", "lifecycle", "mixed")
    }
    assert counts == {"operation": 10, "protocol": 7, "lifecycle": 7, "mixed": 3}
    assert len(scenarios) == 27


def test_reviewed_evidence_references_catalog_without_inflating_case_count() -> None:
    ledger = json.loads(
        (HERE / "evidence" / "evaluation_ledger.json").read_text(encoding="utf-8")
    )
    scenarios = api_scenarios()
    attempts = ledger["attempts"]
    assert ledger["catalog_case_count"] == len(scenarios)
    assert ledger["domain_case_counts"] == {
        domain: sum(item["domain"] == domain for item in scenarios.values())
        for domain in ("operation", "protocol", "lifecycle", "mixed")
    }
    assert len({item["attempt_id"] for item in attempts}) == len(attempts)
    assert all(item["scenario_id"] in scenarios for item in attempts)
    assert all(item["api_calls"] >= 1 for item in attempts)
    assert sum(item["api_calls"] for item in attempts) == 1


def test_api_runner_requires_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("RUN_VERIFIER_API_EVALUATION", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    with pytest.raises(RuntimeError, match="RUN_VERIFIER_API_EVALUATION=1"):
        run_selected(
            ["operation.affine_triple_plus_one"], output_root=tmp_path
        )
    assert list(tmp_path.iterdir()) == []


def test_api_extension_transport_is_strict_and_decodes_to_canonical_schema() -> None:
    schema = VerifierAgent().load_output_schema(VERIFIER_OUTPUT_SCHEMA)
    _assert_openai_strict_object_shapes(schema)
    transport = {
        "schema_version": 1,
        "request_id": "lifecycle.busy_watchdog_observation",
        "id": "lifecycle.busy_watchdog_observation",
        "domain": "lifecycle",
        "feature_name": "busy_watchdog_observation",
        "target": {"scope": "operation", "name": "gemm"},
        "description": "Observe a long-running busy interval.",
        "bindings": '{"busy": "busy"}',
        "reuse": {
            "based_on_features": ["lifecycle.gemm.busy_tracks_active_job"],
            "helpers": ["capture_contract_snapshot"],
        },
        "assertion": {
            "implementation": {
                "kind": "verifier_python",
                "name": "busy_watchdog_assertion",
                "file": "tests/test_busy_watchdog.py",
                "symbol": "check_busy_watchdog",
            },
            "parameters": '{"threshold_cycles": 12}',
        },
        "coverage": {
            "implementation": {
                "kind": "verifier_python",
                "name": "busy_watchdog_coverage",
                "file": "tests/test_busy_watchdog.py",
                "symbol": "sample_busy_watchdog",
            },
            "parameters": '{"threshold_cycles": 12}',
            "bins": [
                {
                    "name": "threshold_reached",
                    "intent": "Observe twelve busy cycles.",
                    "predicate": '{"gte": 12}',
                }
            ],
        },
        "stimulus": {
            "implementation": {
                "kind": "verifier_python",
                "name": "busy_watchdog_stimulus",
                "file": "tests/test_busy_watchdog.py",
                "symbol": "drive_busy_watchdog",
            },
            "parameters": '{"threshold_cycles": 12}',
            "scenarios": [
                {
                    "name": "long_busy_job",
                    "intent": "Run a long job.",
                    "parameters": "{}",
                }
            ],
        },
    }
    decoded = decode_verifier_extension_transport(
        {"feature_extensions": [transport]}
    )["feature_extensions"][0]
    Draft202012Validator(extension_bundle_schema()).validate(decoded)
    assert decoded["bindings"] == {"busy": "busy"}
    assert decoded["coverage"]["bins"][0]["predicate"] == {"gte": 12}


@pytest.mark.parametrize("identity", sorted(api_scenarios()))
def test_every_api_scenario_has_a_valid_frozen_contract(identity: str) -> None:
    context = scenario_context(identity)
    frozen = context["frozen_architecture"]
    architecture = frozen["architecture_contract"]
    interface = frozen["interface_contract"]
    assert validate_architect_extension_requests(architecture, interface) == []
    review = review_contract_deterministically(architecture, interface)
    assert review["status"] == "PASS", review["findings"]
    report = operation_formula_compilation_report(architecture)
    assert report["status"] == "PASS", report
    VerifierAgent._validate_context(context)
    assert [
        item["id"] for item in architecture.get("verification_extensions", [])
    ] == expected_extension_request_ids(identity)
    compiled = {
        stage["stage"]
        for operation in report["operations"]
        for stage in operation["stages"]
        if stage["status"] == "solver_compiled"
    }
    assert compiled == set(expected_formula_concepts(identity))


@pytest.mark.skipif(
    os.getenv("RUN_VERIFIER_API_EVALUATION") != "1",
    reason="Explicit opt-in required because this test makes one Verifier API request.",
)
def test_selected_verifier_api_scenario(tmp_path: Path) -> None:
    identity = os.getenv(
        "VERIFIER_API_SCENARIO_ID", "mixed.affine_and_busy_watchdog"
    )
    output = Path(os.getenv("VERIFIER_API_OUTPUT_DIR", str(tmp_path))).resolve()
    records = run_selected([identity], output_root=output)
    assert records[0]["verdict"] == "PASS", records[0]
