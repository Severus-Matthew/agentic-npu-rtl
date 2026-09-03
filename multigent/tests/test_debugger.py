from __future__ import annotations

import copy

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.debugger import DebuggerAgent


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
        "provenance": {
            "deterministic_evidence_authoritative": True,
            "tests_frozen_during_functional_repair": True,
            "debugger_may_edit_rtl": False,
        },
    }


def valid_repair_result() -> dict:
    return {
        "status": "REPAIR_PLAN_READY",
        "summary": "Localize the elaboration defect to filter_core.",
        "diagnosis": {
            "failure_class": "ELABORATION_ERROR",
            "root_cause": "filter_core uses a runtime value as a static port dimension.",
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
            "architecture_change_required": False,
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
        "architecture_conflict": None,
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


def test_architecture_escalation_does_not_authorize_patch() -> None:
    result = copy.deepcopy(valid_repair_result())
    result["status"] = "ARCHITECTURE_ESCALATION"
    result["repair_plan"] = None
    result["diagnosis"]["architecture_change_required"] = True
    result["architecture_conflict"] = {
        "category": "INTERFACE_CONTRADICTION",
        "affected_modules": ["filter_top"],
        "issue": "two frozen clauses define incompatible packet widths",
        "evidence": "architecture and interface contracts disagree",
        "requested_architect_decision": "choose one packet width and issue a revised contract",
    }
    DebuggerAgent._validate_result(result=result, context=debugger_context())
