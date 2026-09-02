from __future__ import annotations

from pathlib import Path

import yaml

from multigent.agents.architect import ArchitectAgent


class FakeArchitectAgent(ArchitectAgent):
    """Avoid a live Codex call while testing artifact ownership/writing."""

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
                    "kind": "GEMM",
                    "equation": "C=A*B",
                    "description": "dense integer GEMM",
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


def test_architect_writes_only_architecture_artifacts(tmp_path: Path) -> None:
    agent = FakeArchitectAgent()
    result = agent.run(
        {
            "operation": {"type": "GEMM"},
            "numeric": {"activation": {"width": 8}},
        },
        output_dir=tmp_path,
        run_id="unit",
    )

    assert result["status"] == "READY"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "acceptance_criteria.yaml",
        "architect_result.json",
        "architecture_contract.yaml",
        "interface_contract.yaml",
        "module_manifest.json",
    ]

    contract = yaml.safe_load(
        (tmp_path / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    assert contract["compute"]["mac_count"] == 64
    assert not list(tmp_path.glob("*.sv"))
