"""End-to-end regression for the scalar-result reset-abort campaign.

The compliant fixture previously failed after an unchecked one-beat output
completed during the campaign's attempted ``output`` reset phase. The test
uses an ordinary generated contract block; it does not call private checker
functions or hand-credit coverage.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    build_lifecycle_stimulus_plan,
    merge_coverage_plans,
    operation_plan_for_tests,
    render_contract_generated_block,
    synthesize_code_owned_operation_coverage,
)
from multigent.verifier_tool.tool_regression.paths import FIXTURES_ROOT, REPOSITORY_ROOT

FIXTURE = FIXTURES_ROOT / "ready_valid_scalar_gemm"


@pytest.mark.skipif(shutil.which("verilator") is None, reason="verilator not installed")
def test_generated_campaign_passes_for_a_single_transfer_result(tmp_path: Path) -> None:
    architecture = yaml.safe_load((FIXTURE / "architecture_contract_a.yaml").read_text())
    interface = yaml.safe_load((FIXTURE / "interface_contract_a.yaml").read_text())
    metadata = build_architect_operation_metadata(architecture, interface)
    assert not metadata["unrepresentable_operations"]

    lifecycle = build_lifecycle_stimulus_plan(interface, metadata)
    reset_phases = {
        str(item["phase"])
        for item in lifecycle["scenarios"]
        if item.get("kind") == "reset_abort"
    }
    assert "input_bias_vector" in reset_phases
    assert "output" not in reset_phases

    interface_plan = build_interface_coverage_plan(interface)
    source = render_contract_generated_block(
        interface_plan,
        architecture,
        include_automatic_campaign=True,
        randomized_transactions_minimum=8,
    )
    generated = tmp_path / "generated"
    generated.mkdir()
    module_name = "test_ready_valid_scalar_gemm_generated"
    (generated / f"{module_name}.py").write_text(source)

    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    coverage_path = tmp_path / "functional_coverage_report.json"
    ledger_path = tmp_path / "stimulus_ledger.json"
    result = run_cocotb_regression(
        rtl_dir=FIXTURE,
        top_module="tiny_gemm_rv_a_top",
        tests_dir=generated,
        reference_dir=REPOSITORY_ROOT,
        test_modules=[module_name],
        seed=1,
        build_dir=tmp_path / "build",
        report_path=tmp_path / "simulation_report.json",
        timeout_seconds=300,
        coverage_plan=coverage_plan,
        coverage_report_path=coverage_path,
        stimulus_ledger_report_path=ledger_path,
    )
    coverage = json.loads(coverage_path.read_text())
    ledger = json.loads(ledger_path.read_text())

    assert result["status"] == "PASS"
    assert coverage["status"] == "PASS"
    assert coverage["required_bins"] == coverage["hit_bins"] == 58
    assert coverage["missing_bins"] == []
    assert coverage["assertion_failures"] == []
    assert ledger["status"] == "PASS"
    assert ledger["stimulus_count"] == 43
