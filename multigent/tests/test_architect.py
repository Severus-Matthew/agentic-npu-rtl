from __future__ import annotations

from pathlib import Path

import yaml

from multigent.agents.architect import ArchitectAgent
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
                        "inputs": ["sample", "coefficient"],
                        "outputs": ["result"],
                    }
                ],
                "data_types": [
                    {
                        "name": "sample",
                        "role": "stream input",
                        "width_bits": 16,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "none",
                        "overflow_semantics": "not applicable at input",
                        "rounding_semantics": "none",
                    },
                    {
                        "name": "coefficient",
                        "role": "filter coefficient",
                        "width_bits": 16,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "none",
                        "overflow_semantics": "not applicable at input",
                        "rounding_semantics": "none",
                    },
                    {
                        "name": "result",
                        "role": "stream output",
                        "width_bits": 32,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "truncate accumulator to output width",
                        "overflow_semantics": "wrap",
                        "rounding_semantics": "none",
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
                    "organization": "pipelined multiply-accumulate datapath",
                    "dataflow": "streaming sample history through tap operations",
                    "parallelism": "one tap operation per stage",
                    "scheduling": "one accepted input advances the pipeline",
                },
                "storage": [
                    {
                        "name": "sample_history",
                        "stores": "previous input samples",
                        "capacity_expression": "TAPS",
                        "maximum_elements": 16,
                        "element_width_bits": 16,
                        "access_pattern": "shift/register history",
                        "port_requirements": "one new sample write and tap reads per accepted sample",
                        "implementation_hint": "register array",
                        "reuse_semantics": "history samples reused across adjacent outputs",
                        "lifetime": "persistent across accepted samples until reset/overwrite",
                    }
                ],
                "pipeline": [],
                "control": {
                    "strategy": "stream-driven",
                    "state_progression": "advance only on accepted input",
                    "counters": [],
                    "error_behavior": "no protocol side effects on stalls",
                },
                "reset": {
                    "style": "synchronous",
                    "polarity": "active_high",
                    "required_state": "valid state cleared and history marked invalid",
                },
                "latency_model": "fixed pipeline latency after an accepted sample",
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
                        "framing": "one sample per transfer",
                        "ordering": "in order",
                        "backpressure": "supported",
                    },
                    {
                        "name": "result_out",
                        "direction": "output",
                        "purpose": "filtered output stream",
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
                        "dependencies": [],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    }
                ],
            },
            "acceptance_criteria": {
                "functional": ["matches independent FIR reference"],
                "verification": ["random regression"],
                "rtl": ["synthesizable SystemVerilog"],
                "synopsys_handoff": ["verified RTL package"],
            },
        }


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
