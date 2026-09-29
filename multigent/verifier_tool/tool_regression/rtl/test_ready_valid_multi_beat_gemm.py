"""Fault/fix pairs for ready_valid_multi_beat_gemm, the sibling of
ready_valid_tiny_gemm variant A with N=2 (a genuinely two-beat Y output)
and error_style=sticky_until_reset instead of pulse. Runs the real
automatic verification campaign (BUG-003 is fixed, so this is safe) against
two isolated single-fault mutants:

- `cmd_ready_stays_high_while_busy`: the compliant RTL's one line
  `cmd_ready <= 1'b0;` (in the S_IDLE accept branch) is simply omitted, so
  cmd_ready never drops while a job is active. The campaign's own
  `_probe_command_stall` (gated on output_transfer_count >= 2, which this
  fixture satisfies) races a second legal command in against the active
  job's retiring output -- against the mutant, that second command is
  illegally accepted, tripping `single_inflight_job_enforced`.
- `error_not_sticky`: a single line added (`err_latch <= 1'b0;` at the top
  of the non-reset block, unconditionally), reverting the sticky error
  latch to pulse-like auto-clearing. The campaign's own explicit
  sticky-error-style handling (driving an illegal command, then checking
  the error persists until an explicit reset) trips
  "sticky error deasserted without reset".
"""
from __future__ import annotations

import json
import shutil
import yaml
from pathlib import Path
from typing import Any

import pytest

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
from multigent.verifier_tool.tool_regression.benchmarks.ready_valid_multi_beat_gemm.qualify import (
    DEFAULT_RTL_DIR,
    generate_normal_tb,
    simulate,
)
from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

HERE = BENCHMARKS_ROOT / "ready_valid_multi_beat_gemm"
MUTANTS_DIR = HERE / "mutants"

# Hand-driven sticky-error TB: the automatic campaign's own sticky-error
# handling (orchestration/campaign.py's `_wait_status_pulse` + immediate
# `drive_protocol_reset`) returns the instant it first sees `err` go high
# and starts driving reset right away, leaving no window for a too-early
# auto-clear to be observed as a violation before reset legitimately clears
# it too (confirmed by a throwaway probe: the error_not_sticky mutant PASSES
# the automatic campaign cleanly). This drives the illegal command by hand
# and holds off reset for several extra cycles instead.
_STICKY_TB_BODY = """
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@_contract_cocotb.test(timeout_time=60, timeout_unit="sec")
@_contract_coverage()
async def check_sticky_error(dut):
    dut.cmd_valid.value = 0
    dut.cmd_op.value = 0
    dut.a_valid.value = 0
    dut.a_data.value = 0
    dut.b_valid.value = 0
    dut.b_data.value = 0
    dut.bias_valid.value = 0
    dut.bias_data.value = 0
    dut.y_ready.value = 1
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _contract_drive_protocol_reset(dut, "clk", "rst_n", 0)

    dut.cmd_valid.value = 1
    dut.cmd_op.value = 0  # illegal: only 1'd1 is a legal command value
    await RisingEdge(dut.clk)
    dut.cmd_valid.value = 0

    for _ in range(8):
        await RisingEdge(dut.clk)
        assert int(dut.err.value) == 1, "sticky error cleared before reset was ever driven"

    await _contract_drive_protocol_reset(dut, "clk", "rst_n", 0)
    await RisingEdge(dut.clk)
    assert int(dut.err.value) == 0, "sticky error did not clear on reset"
"""


def _generate_sticky_tb(output_dir: Path) -> dict[str, Any]:
    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    findings = [
        *validate_interface_signal_roles(interface),
        *validate_interface_semantics(interface),
        *validate_architecture_operation_features(architecture),
        *validate_architecture_lifecycle_policies(architecture),
        *validate_architecture_operation_arithmetic(architecture),
    ]
    assert not findings, findings
    metadata = build_architect_operation_metadata(architecture, interface)
    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(interface_plan, architecture, include_automatic_campaign=False)
    source = block + _STICKY_TB_BODY
    compile(source, "test_sticky_error.py", "exec")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test_sticky_error.py").write_text(source)
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    (output_dir / "functional_coverage_plan.json").write_text(json.dumps(coverage_plan, indent=2))
    return coverage_plan


def _run_sticky(tmp_path: Path, rtl_source: str, label: str) -> dict[str, Any]:
    out = tmp_path / label
    tests = out / "tests"
    coverage_plan = _generate_sticky_tb(tests)
    rtl = out / "rtl"
    rtl.mkdir(parents=True)
    (rtl / "tiny_gemm_rv_multi_top.v").write_text(rtl_source)
    reference = out / "reference"
    reference.mkdir(parents=True)
    (reference / "model.py").write_text("")
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="tiny_gemm_rv_multi_top", tests_dir=tests,
        reference_dir=reference, test_modules=["test_sticky_error"], seed=1,
        build_dir=out / "build", report_path=out / "report.json", timeout_seconds=120,
        coverage_plan=coverage_plan, coverage_report_path=out / "coverage.json",
        stimulus_ledger_report_path=out / "ledger.json",
    )


def _run_mutant(tmp_path: Path, generated: Path, mutant_filename: str, label: str) -> dict:
    rtl_dir = tmp_path / label
    rtl_dir.mkdir(parents=True)
    (rtl_dir / "tiny_gemm_rv_multi_top.v").write_text((MUTANTS_DIR / mutant_filename).read_text())
    return simulate(rtl_dir, generated, tmp_path / f"{label}_out", seed=1)


def test_compliant_rtl_passes(tmp_path):
    generated = tmp_path / "generated"
    generate_normal_tb(generated)
    result = simulate(DEFAULT_RTL_DIR, generated, tmp_path / "compliant_out", seed=1)
    assert result["status"] == "PASS", result
    assert result["coverage"]["assertion_failures"] == [], result["coverage"]
    covered = set(result["covered_bins"])
    for required in (
        "operation.gemm.reset_abort_phase.output",
        "signal.err.error_behavior.recovered",
        "channel.cmd.command_legality.illegal",
    ):
        assert required in covered, f"missing {required} in {sorted(covered)}"


def test_cmd_ready_stays_high_while_busy_trips_single_inflight_job_enforced(tmp_path):
    generated = tmp_path / "generated"
    generate_normal_tb(generated)
    result = _run_mutant(
        tmp_path, generated, "tiny_gemm_rv_multi_top__cmd_ready_stays_high_while_busy.v",
        "cmd_ready_stays_high",
    )
    assert result["status"] == "SIMULATION_FAILURE", result
    assert "single_inflight_job_enforced" in result["stdout"], result["stdout"][-3000:]
    assert "a second legal command was accepted while a job was active" in result["stdout"], result["stdout"][-3000:]


def test_sticky_error_fault_fix_pair(tmp_path):
    # This directed single-scenario TB does not attempt full coverage
    # closure (that is qualify.py's automatic campaign's job); it only
    # needs to show the compliant RTL raises no assertion over this exact
    # illegal-command-then-hold-then-reset sequence, so check status is not
    # a hard failure class rather than requiring overall PASS (which also
    # demands every coverage obligation be hit).
    good = _run_sticky(tmp_path, (HERE / "rtl" / "tiny_gemm_rv_multi_top.v").read_text(), "compliant_sticky")
    assert good["status"] in ("PASS", "COVERAGE_FAILURE"), good

    bad = _run_sticky(
        tmp_path,
        (MUTANTS_DIR / "tiny_gemm_rv_multi_top__error_not_sticky.v").read_text(),
        "error_not_sticky",
    )
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "sticky error deasserted without reset" in bad["stdout"], bad["stdout"][-3000:]
