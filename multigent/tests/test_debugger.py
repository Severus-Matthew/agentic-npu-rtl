from __future__ import annotations

import json

import pytest

import multigent.agents.debugger as debugger_module
from multigent.agents.base import AgentRuntimeError
from multigent.agents.debugger import CAUSE_PRIORITY, DebuggerAgent


def cause_ranking(root: str, *, eliminated_before: bool = False) -> list[dict]:
    root_index = CAUSE_PRIORITY.index(root)
    rows = []
    for index, domain in enumerate(CAUSE_PRIORITY):
        assessment = "SUPPORTED" if domain == root else "UNRESOLVED"
        if eliminated_before and index < root_index:
            assessment = "ELIMINATED"
        rows.append(
            {
                "domain": domain,
                "priority": index + 1,
                "assessment": assessment,
                "evidence": f"fixture evidence for {domain}",
            }
        )
    return rows


def debugger_context() -> dict:
    return {
        "failure_class": "ELABORATION_ERROR",
        "verification_status": "COMPILE_FAILURE",
        "verification_evidence": {
            "status": "COMPILE_FAILURE",
            "failure_class": "ELABORATION_ERROR",
            "verilator": {"stderr": "%Error: port dimension is not constant"},
        },
        "frozen_architecture": {
            "architecture_contract": {"design": {"name": "stream_filter"}},
            "interface_contract": {
                "protocol": "ready_valid_streaming",
                "signals": [
                    {"name": "clk"},
                    {"name": "rst"},
                    {"name": "in_valid"},
                    {"name": "in_ready"},
                    {"name": "out_valid"},
                    {"name": "out_ready"},
                ],
            },
            "module_manifest": {
                "top": "filter_top",
                "modules": [
                    {"name": "filter_top"},
                    {"name": "filter_core"},
                ],
            },
            "acceptance_criteria": {"rtl": ["synthesizable"]},
        },
        "current_rtl": {
            "filter_top.sv": "module filter_top; endmodule",
            "filter_core.sv": "module filter_core; endmodule",
        },
        "frozen_reference": {"ref.py": "def ref(x): return x\n"},
        "frozen_tests": {"test_filter.py": "import cocotb\n"},
        "failed_run_artifacts": {
            "coverage_plan": None,
            "coverage_report": None,
            "stimulus_ledger": None,
        },
        "provenance": {
            "deterministic_evidence_authoritative": True,
            "tests_frozen_during_functional_repair": True,
            "debugger_may_edit_rtl": False,
        },
        "root_cause_policy": {
            "priority_order": list(CAUSE_PRIORITY),
            "lower_priority_requires_eliminating_every_higher_priority": True,
            "contract_generated_protocol_assertions_are_code_owned": True,
        },
    }


def valid_repair_result() -> dict:
    return {
        "status": "REPAIR_PLAN_READY",
        "summary": "Localize the elaboration defect to filter_core.",
        "diagnosis": {
            "failure_class": "ELABORATION_ERROR",
            "root_cause": "filter_core uses a runtime value as a static port dimension.",
            "root_cause_domain": "RTL_DESIGN",
            "cause_ranking": cause_ranking("RTL_DESIGN"),
            "confidence": 0.98,
            "first_divergence": {
                "cycle": None,
                "signal_or_output": "filter_core port declaration",
                "expected": "compile-time constant dimension",
                "observed": "runtime-sized dimension",
            },
            "evidence": [
                {
                    "source": "verilator",
                    "observation": "port dimension is not constant",
                    "relevance": "fatal elaboration diagnostic identifies the declaration",
                }
            ],
            "affected_modules": ["filter_core"],
            "alternative_hypotheses": [],
            "additional_evidence_requested": [],
        },
        "repair_plan": {
            "action": "PATCH",
            "affected_modules": ["filter_core"],
            "protected_modules": ["filter_top"],
            "protected_interfaces": [
                "clk",
                "rst",
                "in_valid",
                "in_ready",
                "out_valid",
                "out_ready",
            ],
            "recommended_change": "Replace the runtime-sized port dimension with the frozen compile-time bound while retaining runtime indexing limits.",
            "do_not_change": ["external interface", "reference tests", "architecture"],
            "expected_side_effects": ["elaboration should proceed to later checks"],
            "regression_required": "FULL",
        },
    }


def test_debugger_accepts_localized_generic_repair_plan() -> None:
    DebuggerAgent._validate_result(
        result=valid_repair_result(), context=debugger_context()
    )


def test_debugger_rejects_unknown_module() -> None:
    result = valid_repair_result()
    result["diagnosis"]["affected_modules"] = ["gemm_core"]
    result["repair_plan"]["affected_modules"] = ["gemm_core"]
    with pytest.raises(AgentRuntimeError, match="undeclared modules"):
        DebuggerAgent._validate_result(result=result, context=debugger_context())


def test_debugger_protects_every_unaffected_module() -> None:
    result = valid_repair_result()
    result["repair_plan"]["protected_modules"] = []
    with pytest.raises(AgentRuntimeError, match="protect every unaffected"):
        DebuggerAgent._validate_result(result=result, context=debugger_context())


def test_debugger_protects_every_interface_signal() -> None:
    result = valid_repair_result()
    result["repair_plan"]["protected_interfaces"] = ["clk", "rst"]
    with pytest.raises(AgentRuntimeError, match="every frozen top-level"):
        DebuggerAgent._validate_result(result=result, context=debugger_context())


def test_low_confidence_cannot_authorize_patch() -> None:
    result = valid_repair_result()
    result["diagnosis"]["confidence"] = 0.4
    with pytest.raises(AgentRuntimeError, match="Low-confidence"):
        DebuggerAgent._validate_result(result=result, context=debugger_context())


def test_evidence_insufficient_requests_more_evidence() -> None:
    result = valid_repair_result()
    result["status"] = "EVIDENCE_INSUFFICIENT"
    result["repair_plan"] = None
    result["diagnosis"]["confidence"] = 0.3
    result["diagnosis"]["additional_evidence_requested"] = [
        "capture deterministic first-failure waveform window"
    ]
    DebuggerAgent._validate_result(result=result, context=debugger_context())


def test_large_tool_logs_are_bounded_without_mutating_original_evidence():
    from multigent.agents.debugger import bounded_evidence
    evidence={'stdout':'begin'+('x'*100000)+'final-stall-state'}
    compact=bounded_evidence(evidence)
    assert len(compact['stdout']) < 6100
    assert 'begin' in compact['stdout'] and 'final-stall-state' in compact['stdout']
    assert len(evidence['stdout']) > 100000


def test_timeout_can_be_localized_to_testbench_without_overriding_tool_status():
    context=debugger_context()
    context['failure_class']='SIMULATION_TIMEOUT'
    context['verification_status']='SIMULATION_TIMEOUT'
    result=valid_repair_result()
    result.update(status='VERIFICATION_REPAIR_REQUIRED',repair_plan=None)
    result['diagnosis'].update(failure_class='TESTBENCH_ERROR',affected_modules=[],
        root_cause='Test driver waits indefinitely for an illegal transfer instead of observing the contract error response.',
        root_cause_domain='TESTBENCH_INFRASTRUCTURE',
        cause_ranking=cause_ranking('TESTBENCH_INFRASTRUCTURE', eliminated_before=True))
    DebuggerAgent._validate_result(result=result,context=context)
    assert context['verification_status']=='SIMULATION_TIMEOUT'


def test_lower_priority_tb_diagnosis_requires_eliminating_rtl_and_golden() -> None:
    context = debugger_context()
    context["failure_class"] = "SIMULATION_TIMEOUT"
    context["verification_status"] = "SIMULATION_TIMEOUT"
    result = valid_repair_result()
    result.update(status="VERIFICATION_REPAIR_REQUIRED", repair_plan=None)
    result["diagnosis"].update(
        failure_class="TESTBENCH_ERROR",
        affected_modules=[],
        root_cause_domain="TESTBENCH_INFRASTRUCTURE",
        cause_ranking=cause_ranking("TESTBENCH_INFRASTRUCTURE"),
    )
    with pytest.raises(AgentRuntimeError, match="higher-priority domains"):
        DebuggerAgent._validate_result(result=result, context=context)


def test_debugger_loads_exact_failed_assertion_snapshot_and_recent_stimulus(
    tmp_path, monkeypatch
) -> None:
    verification = tmp_path / "verification"
    verification.mkdir()
    coverage_path = verification / "functional-coverage-run.json"
    ledger_path = verification / "stimulus-ledger-run.json"
    coverage_path.write_text(
        json.dumps(
            {
                "assertion_failures": ["payload changed"],
                "failure_records": [
                    {
                        "related_signal_names": ["valid", "ready", "data"],
                        "current_snapshot": {"valid": 1, "ready": 0, "data": 7},
                    }
                ],
                "last_observed_snapshot": {"valid": 1, "ready": 0, "data": 7},
                "operation_sampling": [{"id": "operation.add.mode", "samples": 1}],
            }
        ),
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps(
            {
                "status": "SIMULATION_FAILURE",
                "records": [
                    {"id": f"case:{index}", "stimulus": {"a": index}}
                    for index in range(10)
                ],
            }
        ),
        encoding="utf-8",
    )
    (verification / "combined_coverage_plan.yaml").write_text(
        "schema_version: 2\nobligations: []\n", encoding="utf-8"
    )
    monkeypatch.setattr(debugger_module, "WORKSPACE_ROOT", tmp_path)
    evidence = {
        "cocotb": {
            "functional_coverage": {"report_path": str(coverage_path)},
            "stimulus_ledger": {"path": str(ledger_path)},
        }
    }
    artifacts = DebuggerAgent._verification_artifact_evidence(evidence)
    assert artifacts["coverage_report"]["failure_records"][0][
        "related_signal_names"
    ] == ["valid", "ready", "data"]
    recent = artifacts["stimulus_ledger"]["most_recent_checked_stimuli"]
    assert [item["id"] for item in recent] == [f"case:{index}" for index in range(2, 10)]
