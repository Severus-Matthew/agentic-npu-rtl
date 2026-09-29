"""Isolated single-fault proof for the lifecycle assertion
`no_output_without_active_job` (lfeat:operation_features.
no_output_without_active_job), reusing this pool's existing
ready_valid_tiny_gemm variant "a" contract/RTL.

Does NOT use the automatic verification campaign (same reasoning as
post_processing_tiny_gemm/qualify.py: the campaign's reset-abort sweep is
BUG-003's blast radius). Instead: hold Y_READY high through several idle
cycles right after reset release, before any command is ever issued, then
run one ordinary job via `run_code_owned_operation_case`.

Compliant RTL (tiny_gemm_rv_a_top.v): Y_VALID is registered low in S_IDLE
every cycle no command is accepted, so it can never present a transfer while
idle regardless of Y_READY -- 0 assertion failures.

Mutant (mutants/tiny_gemm_rv_a_top__ghost_output_while_idle.v): a single
line changed, S_IDLE's `y_valid <= 1'b0;` -> `y_valid <= 1'b1;` -- Y_VALID
is asserted from the second post-reset cycle on, with no command ever
accepted, so it presents a genuine "ghost" transfer while idle. This must
trip `no_output_without_active_job` immediately.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    merge_coverage_plans,
    operation_plan_for_tests,
    render_contract_generated_block,
    synthesize_code_owned_operation_coverage,
    validate_architecture_lifecycle_policies,
    validate_architecture_operation_arithmetic,
    validate_architecture_operation_features,
    validate_interface_semantics,
    validate_interface_signal_roles,
)
from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

HERE = BENCHMARKS_ROOT / "ready_valid_tiny_gemm"
TOP_MODULE = "tiny_gemm_rv_a_top"
COMPLIANT_RTL = HERE / "rtl_a" / "tiny_gemm_rv_a_top.v"
MUTANT_RTL = HERE / "mutants" / "tiny_gemm_rv_a_top__ghost_output_while_idle.v"

_TB_BODY = """
from multigent.verifier_tool.operation.stimulus.stimulus_generator import evaluate_canonical_operation
from multigent.verifier_tool.orchestration.campaign import (
    initialize_testbench_owned_signals as _nooaj_initialize_testbench_owned_signals,
    run_code_owned_operation_case as _nooaj_run_code_owned_operation_case,
)

@_contract_cocotb.test(timeout_time=60, timeout_unit="sec")
@_contract_coverage()
async def check_no_ghost_output(dut):
    import cocotb
    from cocotb.clock import Clock
    from cocotb.triggers import RisingEdge

    interface = CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"]
    await _nooaj_initialize_testbench_owned_signals(dut, interface)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _contract_drive_protocol_reset(dut, "clk", "rst_n", 0)

    # Hold Y_READY high through several idle cycles -- no command has ever
    # been issued yet -- before running any real job. A compliant design
    # must never present a Y transfer here; the ghost_output mutant does,
    # immediately.
    dut.y_ready.value = 1
    for _ in range(10):
        await RisingEdge(dut.clk)

    operation = CONTRACT_OPERATION_METADATA["operations"][0]
    stimulus = {"A_matrix": [1, -1, 1, -1], "B_matrix": [1, 1, 1, 1], "bias_vector": [0]}
    expected = evaluate_canonical_operation(CONTRACT_OPERATION_METADATA, stimulus)
    case = {
        "operation_name": "gemm", "kind": "directed", "label": "after_idle_hold",
        "target": None, "qualification_purpose": "no_output_without_active_job_isolation",
        "stimulus": stimulus, "expected": expected,
    }
    await _nooaj_run_code_owned_operation_case(dut, "clk", operation, case)
"""


def _load_contracts() -> tuple[dict, dict]:
    architecture = yaml.safe_load((HERE / "architecture_contract_a.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract_a.yaml").read_text())
    return architecture, interface


def _generate_tb(output_dir: Path) -> dict[str, Any]:
    architecture, interface = _load_contracts()
    findings = [
        *validate_interface_signal_roles(interface),
        *validate_interface_semantics(interface),
        *validate_architecture_operation_features(architecture),
        *validate_architecture_lifecycle_policies(architecture),
        *validate_architecture_operation_arithmetic(architecture),
    ]
    assert not findings, findings
    metadata = build_architect_operation_metadata(architecture, interface)
    assert not metadata["unrepresentable_operations"], metadata["unrepresentable_operations"]

    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(interface_plan, architecture, include_automatic_campaign=False)
    source = block + _TB_BODY
    compile(source, "test_no_ghost_output.py", "exec")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test_no_ghost_output.py").write_text(source)
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    (output_dir / "functional_coverage_plan.json").write_text(json.dumps(coverage_plan, indent=2))
    return coverage_plan


def _run(tmp_path: Path, rtl_file: Path, label: str) -> dict[str, Any]:
    path = tmp_path / label
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "tiny_gemm_rv_a_top.v").write_text(rtl_file.read_text())
    (reference / "model.py").write_text("")
    coverage_plan = _generate_tb(tests)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module=TOP_MODULE, tests_dir=tests, reference_dir=reference,
        test_modules=["test_no_ghost_output"], seed=1,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=180,
        coverage_plan=coverage_plan,
        coverage_report_path=path / "functional_coverage_report.json",
        stimulus_ledger_report_path=path / "stimulus_ledger.json",
    )


def test_no_output_without_active_job_fault_fix_pair(tmp_path):
    mutant = _run(tmp_path, MUTANT_RTL, "ghost_output_while_idle")
    assert mutant["status"] == "SIMULATION_FAILURE", mutant
    assert "no_output_without_active_job" in mutant["stdout"], mutant["stdout"][-3000:]

    # This directed single-job TB does not attempt full coverage closure
    # (that is ready_valid_tiny_gemm/qualify.py's automatic campaign's job);
    # it only needs to show the compliant RTL raises no assertion, so check
    # assertion_failures directly rather than requiring overall PASS status
    # (which also demands every coverage obligation be hit).
    good = _run(tmp_path, COMPLIANT_RTL, "compliant")
    assert good["status"] in ("PASS", "COVERAGE_FAILURE"), good
    report = json.loads((tmp_path / "compliant" / "functional_coverage_report.json").read_text())
    assert report["assertion_failures"] == [], report["assertion_failures"]
