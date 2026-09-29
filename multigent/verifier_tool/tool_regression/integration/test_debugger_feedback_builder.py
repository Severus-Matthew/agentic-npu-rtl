from __future__ import annotations

import copy

import pytest

from multigent.verifier_tool import (
    DebuggerFeedbackError,
    bound_debugger_evidence,
    build_failed_run_artifacts,
    build_verifier_debugger_feedback,
    validate_verifier_debugger_feedback,
)


def _feedback() -> dict:
    evidence = {
        "status": "SIMULATION_FAILURE",
        "failure_class": "FUNCTIONAL_MISMATCH",
        "cocotb": {
            "functional_coverage": {"report_path": "/run/coverage.json"},
            "stimulus_ledger": {"path": "/run/ledger.json"},
        },
    }
    failed = build_failed_run_artifacts(
        evidence,
        coverage_plan={"obligations": [{"id": "operation.gemm.accumulation"}]},
        coverage_report={
            "status": "FAIL",
            "coverage_percent": 80.0,
            "assertion_failures": ["Y mismatch"],
            "failure_records": [{"current_snapshot": {"y_valid": 1}}],
            "last_observed_snapshot": {"y_valid": 1, "y_payload": 9},
            "operation_sampling": [{"id": "operation.gemm.accumulation", "samples": 1}],
            "internal_debug_dump": "must not be forwarded",
        },
        stimulus_ledger={
            "status": "SIMULATION_FAILURE",
            "records": [{"id": f"job:{index}"} for index in range(12)],
            "all_raw_payloads": "must not be forwarded",
        },
    )
    return build_verifier_debugger_feedback(
        verification_status="SIMULATION_FAILURE",
        failure_class="FUNCTIONAL_MISMATCH",
        verification_evidence=evidence,
        failed_run_artifacts=failed,
        frozen_reference={"gemm_ref.py": "def gemm(): pass\n"},
        frozen_tests={"test_gemm.py": "import cocotb\n"},
        verification_plan={"top_module": "gemm_top"},
        operation_coverage=[{"operation_name": "gemm_core"}],
    )


def test_debugger_feedback_selects_exact_deterministic_failure_evidence() -> None:
    feedback = _feedback()
    report = feedback["failed_run_artifacts"]["coverage_report"]
    ledger = feedback["failed_run_artifacts"]["stimulus_ledger"]

    assert report["assertion_failures"] == ["Y mismatch"]
    assert "internal_debug_dump" not in report
    assert [item["id"] for item in ledger["most_recent_checked_stimuli"]] == [
        f"job:{index}" for index in range(4, 12)
    ]
    assert "all_raw_payloads" not in ledger


def test_debugger_feedback_contains_only_frozen_verifier_owned_inputs() -> None:
    feedback = _feedback()

    assert set(feedback["frozen_verifier"]) == {
        "reference",
        "tests",
        "verification_plan",
        "operation_coverage",
    }
    assert feedback["provenance"] == {
        "deterministic_evidence_authoritative": True,
        "verifier_artifacts_frozen": True,
        "coverage_hits_are_measured": True,
    }
    assert not {
        "current_rtl",
        "frozen_architecture",
        "root_cause_policy",
        "prior_diagnosis",
        "repair_iteration",
    } & set(feedback)
    validate_verifier_debugger_feedback(feedback)


@pytest.mark.parametrize("defect", ["foreign_rtl", "editable_tests", "bad_status"])
def test_debugger_feedback_rejects_non_verifier_or_non_authoritative_fields(
    defect: str,
) -> None:
    feedback = _feedback()
    if defect == "foreign_rtl":
        feedback["current_rtl"] = {"gemm.sv": "module gemm; endmodule"}
    elif defect == "editable_tests":
        feedback["provenance"]["verifier_artifacts_frozen"] = False
    else:
        feedback["verification_status"] = "PASS"

    with pytest.raises(DebuggerFeedbackError):
        validate_verifier_debugger_feedback(feedback)


def test_debugger_evidence_bounding_is_non_mutating_and_keeps_endpoints() -> None:
    original = {"stdout": "begin" + "x" * 100_000 + "final-state"}
    before = copy.deepcopy(original)

    bounded = bound_debugger_evidence(original)

    assert bounded["stdout"].startswith("begin")
    assert bounded["stdout"].endswith("final-state")
    assert "TRUNCATED" in bounded["stdout"]
    assert original == before
