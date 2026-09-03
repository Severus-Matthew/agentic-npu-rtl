from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.base import AgentRuntimeError
from multigent.agents.rtl_generator import (
    RTL_GENERATOR_OUTPUT_SCHEMA,
    RTLGeneratorAgent,
)
from multigent.orchestration.rtl_node import make_rtl_generator_node


def generic_fir_context() -> dict:
    return {
        "user_request": "design a signed 16-bit streaming FIR filter",
        "fixed_rtl_constraints": {
            "language": "SystemVerilog",
            "synthesizable_only": True,
            "forbidden_constructs": ["real", "shortreal", "delay_statements"],
        },
        "synthesis_policy": {
            "provider": "synopsys",
            "requires_verified_rtl": True,
            "prohibit_metric_estimation": True,
        },
        "frozen_architecture": {
            "architecture_contract": {
                "design": {"name": "stream_fir"},
                "data_types": [{"name": "sample_t", "width_bits": 16, "signed": True}],
                "parameters": [{"name": "TAPS", "default_value": "4"}],
                "control": {"strategy": "stream-driven"},
                "reset": {"style": "synchronous", "polarity": "active_high"},
            },
            "interface_contract": {
                "protocol": "ready_valid_stream",
                "signals": [
                    {"name": "clk", "direction": "input", "width": "1"},
                    {"name": "rst", "direction": "input", "width": "1"},
                ],
            },
            "module_manifest": {
                "top": "filter_top",
                "modules": [
                    {
                        "name": "filter_top",
                        "responsibility": "top integration",
                        "dependencies": ["filter_core"],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    },
                    {
                        "name": "filter_core",
                        "responsibility": "filter datapath",
                        "dependencies": [],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    },
                ],
            },
            "acceptance_criteria": {
                "functional": ["matches FIR reference"],
                "verification": ["randomized stream tests"],
                "rtl": ["synthesizable SystemVerilog"],
                "synopsys_handoff": ["verified RTL only"],
            },
        },
    }


def generated_result() -> dict:
    return {
        "status": "RTL_GENERATED",
        "task_type": "INITIAL_GENERATION",
        "summary": "Implemented the frozen two-module streaming filter manifest.",
        "files": [
            {
                "path": "filter_top.sv",
                "module": "filter_top",
                "purpose": "top integration",
                "content": "module filter_top #(parameter int TAPS=4) ();\nendmodule\n",
            },
            {
                "path": "filter_core.sv",
                "module": "filter_core",
                "purpose": "filter datapath",
                "content": "module filter_core #(parameter int TAPS=4) ();\nendmodule\n",
            },
        ],
        "contract_checks": [
            {
                "requirement": "manifest coverage",
                "satisfied": True,
                "evidence": "filter_top and filter_core are both emitted",
            }
        ],
        "changed_modules": ["filter_top", "filter_core"],
        "architecture_conflict": None,
        "blocked_reason": "",
        "architecture_changed": False,
        "interface_changed": False,
        "latency_changed": False,
        "known_risks": [],
        "regression_required": "FULL",
    }


class FakeRTLGeneratorAgent(RTLGeneratorAgent):
    def run_structured(self, **_: object) -> dict:
        return copy.deepcopy(generated_result())


def rtl_schema() -> dict:
    return json.loads(RTL_GENERATOR_OUTPUT_SCHEMA.read_text(encoding="utf-8"))


def test_generic_non_gemm_output_satisfies_schema() -> None:
    Draft202012Validator(rtl_schema()).validate(generated_result())


def test_initial_generation_writes_exact_manifest(tmp_path: Path) -> None:
    agent = FakeRTLGeneratorAgent()
    result = agent.run(
        generic_fir_context(),
        output_dir=tmp_path / "rtl",
        run_id="unit",
    )

    assert result["status"] == "RTL_GENERATED"
    assert sorted(path.name for path in (tmp_path / "rtl").glob("*.sv")) == [
        "filter_core.sv",
        "filter_top.sv",
    ]
    assert "module filter_top" in (tmp_path / "rtl" / "filter_top.sv").read_text()


def test_initial_generation_rejects_missing_manifest_module() -> None:
    result = generated_result()
    result["files"] = result["files"][:1]
    result["changed_modules"] = ["filter_top"]

    with pytest.raises(AgentRuntimeError, match="exactly the frozen manifest"):
        RTLGeneratorAgent._validate_result(
            result=result,
            context=generic_fir_context(),
            task_type="INITIAL_GENERATION",
            existing_rtl={},
        )


def test_rejects_undeclared_module() -> None:
    result = generated_result()
    result["files"][1]["module"] = "hidden_helper"
    result["files"][1]["content"] = "module hidden_helper; endmodule"
    result["changed_modules"][1] = "hidden_helper"

    with pytest.raises(AgentRuntimeError, match="undeclared modules"):
        RTLGeneratorAgent._validate_result(
            result=result,
            context=generic_fir_context(),
            task_type="INITIAL_GENERATION",
            existing_rtl={},
        )


def test_rejects_unsafe_output_path() -> None:
    with pytest.raises(AgentRuntimeError, match="Unsafe RTL output path"):
        RTLGeneratorAgent._safe_relative_sv_path("../architecture/contract.sv")


def test_architecture_conflict_emits_no_rtl() -> None:
    result = generated_result()
    result.update(
        {
            "status": "ARCHITECTURE_CONFLICT",
            "files": [],
            "changed_modules": [],
            "contract_checks": [],
            "architecture_conflict": {
                "category": "STORAGE_BANDWIDTH",
                "affected_modules": ["filter_core"],
                "issue": "declared storage cannot sustain the frozen schedule",
                "evidence": "required reads exceed contracted ports",
                "requested_architect_decision": "choose more ports or lower parallelism",
            },
            "regression_required": "NONE",
        }
    )

    RTLGeneratorAgent._validate_result(
        result=result,
        context=generic_fir_context(),
        task_type="INITIAL_GENERATION",
        existing_rtl={},
    )


def test_noninitial_task_requires_feedback_and_existing_rtl(tmp_path: Path) -> None:
    agent = FakeRTLGeneratorAgent()
    with pytest.raises(AgentRuntimeError, match="requires existing RTL"):
        agent.run(
            generic_fir_context(),
            task_type="FUNCTIONAL_REPAIR",
            output_dir=tmp_path / "rtl",
            run_id="repair",
        )


def test_skill_context_is_generic_and_role_only() -> None:
    instructions = FakeRTLGeneratorAgent().load_instructions()
    assert "# RTL GENERATOR TECHNICAL SKILL" in instructions
    assert "# GLOBAL PROJECT CONTRACT" not in instructions
    assert "Do not assume a particular operand width" in instructions
    assert "npu_top.sv" not in instructions
    assert "mac_array.sv" not in instructions


def test_langgraph_node_returns_partial_state_update() -> None:
    class StubAgent:
        def run_from_state(self, state: dict) -> dict:
            assert state["run_id"] == "graph-unit-rtl-av0-r0-p0"
            return {
                "rtl_status": "ARCHITECTURE_CONFLICT",
                "rtl_result": {"status": "ARCHITECTURE_CONFLICT"},
                "rtl_files": [],
                "architecture_conflict": {"issue": "needs architect"},
                "needs_regression": False,
            }

    node = make_rtl_generator_node(StubAgent())  # type: ignore[arg-type]
    update = node({"run_id": "graph-unit"})  # type: ignore[arg-type]

    assert update["rtl_status"] == "ARCHITECTURE_CONFLICT"
    assert update["history"][0]["stage"] == "rtl_generator"
