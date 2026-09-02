from __future__ import annotations

from pathlib import Path

import yaml

from multigent.agents.architect import ArchitectAgent
from multigent.intake.request_builder import build_architect_intake


class FakeArchitectAgent(ArchitectAgent):
    """Avoid a live API call while testing artifact ownership/writing."""

    def run_structured(self, **_: object) -> dict:
        return {
            "status": "READY",
            "conflicts": [],
            "architecture_contract": {
                "design": {
                    "name": "test_npu",
                    "version": "0.1",
                    "description": "test architecture",
                },
                "operation": {
                    "kind": "GEMM_BIAS_RELU",
                    "equation": "C=ReLU(A*B+bias)",
                    "description": "dense integer GEMM with bias and ReLU",
                },
                "numeric": {
                    "activation_width": 8,
                    "activation_signed": True,
                    "weight_width": 8,
                    "weight_signed": True,
                    "accumulator_width": 32,
                    "accumulator_signed": True,
                    "overflow_semantics": "wrap",
                    "rounding_semantics": "none",
                },
                "compute": {
                    "organization": "systolic_array",
                    "rows": 8,
                    "columns": 8,
                    "mac_count": 64,
                    "parameterization": "rows and columns are parameters",
                },
                "dataflow": "weight-stationary",
                "pipeline": [],
                "buffers": [],
                "control": "single transaction controller",
                "reset": {
                    "style": "synchronous",
                    "polarity": "active_high",
                    "required_state": "idle and valids cleared",
                },
                "latency_model": "implementation contract defines fixed pipeline latency",
                "architectural_invariants": ["signed INT8 inputs"],
                "open_assumptions": [],
            },
            "interface_contract": {
                "protocol": "ready_valid_stream",
                "clock": "clk",
                "reset": "rst",
                "signals": [],
                "handshake": {
                    "transfer_condition": "valid && ready",
                    "stall_behavior": "payload remains stable",
                    "backpressure_supported": True,
                    "ordering": "in order",
                },
            },
            "module_manifest": {
                "top": "npu_top",
                "modules": [
                    {
                        "name": "npu_top",
                        "responsibility": "top-level integration",
                        "dependencies": [],
                        "stateful": True,
                    }
                ],
            },
            "acceptance_criteria": {
                "functional": ["exact integer match"],
                "verification": ["random regression"],
                "rtl": ["synthesizable SystemVerilog"],
                "synopsys_handoff": ["verified RTL package"],
            },
        }


def test_intake_keeps_architecture_choices_out_of_user_input() -> None:
    request = "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type"
    intake = build_architect_intake(request)

    assert intake["user_request"] == request
    assert intake["provenance"]["user_supplied_fields"] == ["user_request"]

    # Fixed policy may be injected by software.
    assert intake["project_constraints"]["rtl_constraints"]["language"] == "SystemVerilog"
    assert (
        intake["project_constraints"]["verification_policy"][
            "randomized_transactions_minimum"
        ]
        == 100
    )

    # Genuine architecture choices are delegated to the Architect, not silently
    # inserted as if the user requested them.
    decisions = intake["architect_must_decide_when_unspecified"]
    assert "array_dimensions" in decisions
    assert "interface_protocol" in decisions
    assert "reset_style" in decisions
    assert "overflow_semantics" in decisions


def test_architect_writes_only_architecture_artifacts(tmp_path: Path) -> None:
    architecture_dir = tmp_path / "architecture"
    agent = FakeArchitectAgent()
    result = agent.run(
        "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type",
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

    contract = yaml.safe_load(
        (architecture_dir / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    assert contract["compute"]["mac_count"] == 64
    assert not list(architecture_dir.glob("*.sv"))
