from __future__ import annotations

from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import contracts
from multigent.verifier_tool import (
    build_interface_coverage_plan,
    build_qualification_evidence,
    build_trial_manifest,
    load_qualification_catalog,
    merge_coverage_plans,
    operation_plan_for_tests,
    qualification_pytest_nodeids,
    validate_release_gate,
)


def _released_scope():
    architecture, interface = contracts()
    interface["signals"][:0] = [
        {"name": "clk", "role": "clock", "channel": None},
        {
            "name": "rst_n",
            "role": "reset",
            "channel": None,
            "semantic": "synchronous active-low reset",
        },
    ]
    specs = [
        {
            "operation_name": "gemm_core",
            "family": "matrix_multiply",
            "coverpoints": [
                {
                    "id": concept,
                    "concept": concept,
                    "field": concept,
                    "source": (
                        "baseline"
                        if concept in architecture["operations"][0]["features"]
                        else "architect_extension"
                    ),
                    "description": concept,
                    "bins": [
                        {
                            "name": "draft",
                            "intent": "replaced by code-owned disposition",
                            "predicate": {"op": "truthy", "args": []},
                        }
                    ],
                }
                for concept in (
                    "dimensions",
                    "operand_values",
                    "accumulation",
                    "bias",
                    "activation",
                )
            ],
        }
    ]
    interface_plan = build_interface_coverage_plan(interface)
    operation_plan = operation_plan_for_tests(
        specs, ["OPERATION_SAMPLING_BINDINGS = []\n"], architecture, interface
    )
    verification = merge_coverage_plans(interface_plan, operation_plan)[
        "verification_manifest"
    ]
    trial = build_trial_manifest(
        architecture,
        interface,
        verification,
        intended_trials=30,
        randomized_transactions_minimum=10,
    )
    return trial, verification


def test_release_gate_requires_executed_finite_qualification() -> None:
    trial, verification = _released_scope()
    result = validate_release_gate(trial, verification)
    assert result["status"] == "BLOCKED"
    assert result["checklist"]["finite_positive_negative_qualification"] == "BLOCKED"


def test_release_gate_accepts_exact_complete_qualification_catalog() -> None:
    trial, verification = _released_scope()
    case_ids = [item["id"] for item in load_qualification_catalog()["cases"]]
    evidence = build_qualification_evidence(
        case_ids,
        command="pytest fixed qualification catalog",
        source_revision="unit-test-source",
    )
    result = validate_release_gate(trial, verification, evidence)
    assert result["status"] == "READY", result["failures"]
    assert len(result["checklist"]) == 40
    assert set(result["checklist"].values()) <= {"PASS", "INAPPLICABLE"}
    assert qualification_pytest_nodeids()
