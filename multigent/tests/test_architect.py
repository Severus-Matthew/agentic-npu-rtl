from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent
from multigent.agents.base import AgentRuntimeError
from multigent.intake.request_builder import build_architect_intake


class FakeArchitectAgent(ArchitectAgent):
    """Deterministic non-GEMM fixture; values here are not project defaults."""

    def run_structured(self, **_: object) -> dict:
        return {
            "status": "READY",
            "conflicts": [],
            "architecture_contract": {
                "design": {
                    "name": "test_stream_filter",
                    "version": "0.1",
                    "description": "test-only generic streaming filter architecture",
                },
                "operations": [
                    {
                        "name": "filter",
                        "kind": "FIR",
                        "semantics": "y[t] is the weighted sum of the current and previous samples",
                        "inputs": ["sample_stream", "coefficient_vector"],
                        "outputs": ["result_stream"],
                    }
                ],
                "data_types": [
                    {
                        "name": "sample_t",
                        "role": "stream input element",
                        "width_bits": 16,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "none",
                        "overflow_semantics": "not applicable at input",
                        "rounding_semantics": "none",
                    },
                    {
                        "name": "coefficient_t",
                        "role": "filter coefficient element",
                        "width_bits": 16,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "none",
                        "overflow_semantics": "not applicable at input",
                        "rounding_semantics": "none",
                    },
                    {
                        "name": "result_t",
                        "role": "stream output element",
                        "width_bits": 32,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "accumulated result",
                        "overflow_semantics": "wrap",
                        "rounding_semantics": "none",
                    },
                ],
                "data_objects": [
                    {
                        "name": "sample_stream",
                        "role": "external input sample sequence",
                        "data_type": "sample_t",
                        "dimensions": [],
                        "producer": "external",
                        "consumers": ["filter"],
                        "external": True,
                    },
                    {
                        "name": "coefficient_vector",
                        "role": "FIR coefficient set",
                        "data_type": "coefficient_t",
                        "dimensions": ["tap_count"],
                        "producer": "external",
                        "consumers": ["filter"],
                        "external": True,
                    },
                    {
                        "name": "result_stream",
                        "role": "external filtered sample sequence",
                        "data_type": "result_t",
                        "dimensions": [],
                        "producer": "filter",
                        "consumers": ["external"],
                        "external": True,
                    },
                ],
                "dimensions": [
                    {
                        "name": "tap_count",
                        "semantic": "number of FIR taps",
                        "minimum": 1,
                        "maximum": 16,
                        "runtime_configurable": False,
                        "bound_parameter": "TAPS",
                    }
                ],
                "parameters": [
                    {
                        "name": "TAPS",
                        "default_value": "8",
                        "legality_constraint": "1 <= TAPS <= 16",
                        "description": "number of filter taps",
                    }
                ],
                "compute": {
                    "organization": "serial multiply-accumulate datapath",
                    "dataflow": "sample history with coefficient traversal",
                    "parallelism": "one multiply-accumulate per cycle",
                    "scheduling": "iterate tap index for each accepted sample",
                },
                "storage": [
                    {
                        "name": "sample_history",
                        "stored_objects": ["sample_stream"],
                        "capacity_expression": "TAPS",
                        "capacity_at_default_parameters": 8,
                        "access_pattern": "shift/register history",
                        "port_requirements": "one insert and one indexed read",
                        "implementation_hint": "register array",
                        "reuse_semantics": "history samples reused across adjacent outputs",
                        "lifetime": "persistent across accepted samples until reset/overwrite",
                    },
                    {
                        "name": "coefficient_store",
                        "stored_objects": ["coefficient_vector"],
                        "capacity_expression": "TAPS",
                        "capacity_at_default_parameters": 8,
                        "access_pattern": "one coefficient read per MAC cycle",
                        "port_requirements": "one read port",
                        "implementation_hint": "register array",
                        "reuse_semantics": "coefficients reused across samples",
                        "lifetime": "configuration lifetime",
                    },
                ],
                "pipeline": [],
                "control": {
                    "strategy": "stream-driven FSM",
                    "state_progression": "IDLE->MAC->OUTPUT->IDLE",
                    "counters": ["tap_idx"],
                    "error_behavior": "reject invalid configuration",
                    "error_recovery": "synchronous reset returns design to IDLE",
                },
                "reset": {
                    "style": "synchronous",
                    "polarity": "active_high",
                    "required_state": "valid state cleared and history marked invalid",
                },
                "latency_model": "TAPS MAC cycles plus output handshake",
                "architectural_invariants": ["TAPS is compile-time bounded"],
                "open_assumptions": [],
            },
            "interface_contract": {
                "protocol": "ready_valid_stream",
                "clock": "clk",
                "reset": "rst",
                "channels": [
                    {
                        "name": "sample_in",
                        "direction": "input",
                        "purpose": "input sample stream",
                        "data_objects": ["sample_stream"],
                        "metadata": [],
                        "framing": "one sample per transfer",
                        "ordering": "in order",
                        "backpressure": "supported",
                    },
                    {
                        "name": "coefficients",
                        "direction": "input",
                        "purpose": "coefficient loading",
                        "data_objects": ["coefficient_vector"],
                        "metadata": ["coefficient_index"],
                        "framing": "TAPS transfers per configuration",
                        "ordering": "ascending coefficient index",
                        "backpressure": "supported",
                    },
                    {
                        "name": "result_out",
                        "direction": "output",
                        "purpose": "filtered output stream",
                        "data_objects": ["result_stream"],
                        "metadata": [],
                        "framing": "one result per transfer",
                        "ordering": "in order",
                        "backpressure": "supported",
                    },
                ],
                "signals": [],
                "global_handshake_rules": {
                    "transfer_condition": "valid && ready",
                    "stall_behavior": "payload remains stable while stalled",
                },
            },
            "module_manifest": {
                "top": "filter_top",
                "modules": [
                    {
                        "name": "filter_top",
                        "responsibility": "top-level integration",
                        "dependencies": ["filter_core"],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    },
                    {
                        "name": "filter_core",
                        "responsibility": "FIR datapath and control",
                        "dependencies": [],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    },
                ],
            },
            "acceptance_criteria": {
                "functional": ["matches independent FIR reference"],
                "verification": ["random regression"],
                "rtl": ["synthesizable SystemVerilog"],
                "synopsys_handoff": ["verified RTL package"],
            },
        }


def architect_schema() -> dict:
    return json.loads(ARCHITECT_OUTPUT_SCHEMA.read_text(encoding="utf-8"))


def test_generic_non_gemm_output_satisfies_architect_schema() -> None:
    Draft202012Validator(architect_schema()).validate(
        FakeArchitectAgent().run_structured()
    )


def test_dimension_maximum_must_be_concrete_integer() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["dimensions"][0]["maximum"] = ","
    with pytest.raises(ValidationError):
        Draft202012Validator(architect_schema()).validate(result)


def test_intake_keeps_architecture_choices_out_of_user_input() -> None:
    request = "design a 16-bit streaming FIR accelerator with 8 taps"
    intake = build_architect_intake(request)

    assert intake["user_request"] == request
    assert intake["provenance"]["user_supplied_fields"] == ["user_request"]
    assert intake["project_constraints"]["rtl_constraints"]["language"] == "SystemVerilog"
    assert intake["project_constraints"]["verification_policy"]["randomized_transactions_minimum"] == 100
    assert intake["project_constraints"]["synthesis_policy"]["provider"] == "synopsys"
    assert "owner" not in intake["project_constraints"]["synthesis_policy"]

    decisions = intake["architect_must_decide_when_unspecified"]
    assert "operation_semantics" in decisions
    assert "data_type_semantics" in decisions
    assert "legal_runtime_bounds" in decisions
    assert "compile_time_parameters" in decisions
    assert "compute_organization" in decisions
    assert "storage_and_reuse" in decisions
    assert "interface_protocol" in decisions
    assert "reset_style" in decisions


def test_architect_loads_role_technical_context_only() -> None:
    instructions = FakeArchitectAgent().load_instructions()
    assert "# ARCHITECT TECHNICAL SKILL" in instructions
    assert "external_team_member" not in instructions
    assert "Artifact Ownership" not in instructions
    assert "Do not assume GEMM" in instructions


def test_architect_writes_only_architecture_artifacts(tmp_path: Path) -> None:
    architecture_dir = tmp_path / "architecture"
    agent = FakeArchitectAgent()
    result = agent.run(
        "design a 16-bit streaming FIR accelerator with 8 taps",
        output_dir=architecture_dir,
        run_id="unit",
    )

    assert result["status"] == "READY"
    assert sorted(path.name for path in architecture_dir.iterdir()) == [
        "acceptance_criteria.yaml",
        "architect_result.json",
        "architecture_contract.yaml",
        "interface_contract.yaml",
        "module_manifest.json",
    ]

    intake_path = tmp_path / "specs" / "request-unit.yaml"
    assert intake_path.is_file()
    intake = yaml.safe_load(intake_path.read_text(encoding="utf-8"))
    assert intake["provenance"]["user_supplied_fields"] == ["user_request"]
    assert "owner" not in intake["project_constraints"]["synthesis_policy"]

    contract = yaml.safe_load(
        (architecture_dir / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    assert contract["design"]["name"] == "test_stream_filter"
    assert contract["parameters"][0]["name"] == "TAPS"
    assert not list(architecture_dir.glob("*.sv"))


def test_semantic_validator_rejects_unknown_data_object() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["inputs"].append("missing_object")
    with pytest.raises(AgentRuntimeError, match="unknown data object"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_unknown_module_parameter() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["module_manifest"]["modules"][0]["parameters"].append("MISSING_PARAM")
    with pytest.raises(AgentRuntimeError, match="unknown parameter"):
        ArchitectAgent._validate_contract_references(result)
