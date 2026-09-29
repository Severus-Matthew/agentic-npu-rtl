"""Isolated proof for lfeat:operation_features.response_error_follows_
nonokay, using the new ready_valid_axi_error_gemm fixture (the only
operation in this pool whose memory_mapping resolves a response_channel --
confirmed empirically against the pre-existing u55c_inspired_int8_gemm_4x4x4
fixture, which auto-populates memory_mapping.response_channel purely from
being an axi4_lite-profile read, no explicit "response_channel=" semantic
tag needed or supported).

Cannot use either the automatic campaign (rejects this operation outright:
`operation_io_profile_not_executable=['axi4_lite', 'ready_valid']` -- the
automatic campaign requires one uniform transport across an operation) or
`run_code_owned_operation_case` (misdrives the mixed-transport A_matrix
read, tripping `read_response_after_address` before the job even starts).
Instead drives the AR/R handshake and the B/bias/Y ready_valid channels by
hand, exactly mirroring what those helpers do internally for a
single-outstanding, single-beat exchange.

Two scenarios, same RTL:
- OKAY: A read returns a clean response; the job completes normally with
  the correct golden Y value.
- SLVERR: A read returns SLVERR. This does not just need the DUT to
  raise `err`, it needs the DUT to abort the job entirely and drop `busy`
  right there -- confirmed via assertion_checkers.py's error_responses
  handling, which sets `current["active"] = False` the instant it observes
  a non-OKAY response on a tracked channel, so a design that continued on
  to load B/bias/output while busy stays high would trip
  `busy_tracks_active_job` ("busy is high without an active legal job").

The strict feature proof uses a second, narrower mutant that performs the
required abort but suppresses only the error pulse.  That mutant must fail
with the exact `response_error_follows_nonokay` diagnostic; the
continues-past-error mutant remains useful independent evidence for the abort
semantics shared with `busy_tracks_active_job`.
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
)
from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

HERE = BENCHMARKS_ROOT / "ready_valid_axi_error_gemm"
TOP_MODULE = "ready_valid_axi_error_gemm_top"
MUTANTS_DIR = HERE / "mutants"

_TB_BODY = """
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.operation.stimulus.stimulus_generator import evaluate_canonical_operation

RESP = %d

@_contract_cocotb.test(timeout_time=60, timeout_unit="sec")
@_contract_coverage()
async def check_one_job(dut):
    dut.cmd_valid.value = 0
    dut.cmd_op.value = 0
    dut.a_base.value = 0
    dut.a_arready.value = 0
    dut.a_rvalid.value = 0
    dut.a_rdata.value = 0
    dut.a_rresp.value = 0
    dut.b_valid.value = 0
    dut.b_data.value = 0
    dut.bias_valid.value = 0
    dut.bias_data.value = 0
    dut.y_ready.value = 1
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _contract_drive_protocol_reset(dut, "clk", "rst_n", 0)

    operation = CONTRACT_OPERATION_METADATA["operations"][0]
    stimulus = {"A_matrix": [1, 1, 1, 1], "B_matrix": [1, 1, 1, 1], "bias_vector": [0]}
    expected = evaluate_canonical_operation(CONTRACT_OPERATION_METADATA, stimulus)

    dut.cmd_valid.value = 1
    dut.cmd_op.value = 1
    dut.a_base.value = 0x1000
    await RisingEdge(dut.clk)
    dut.cmd_valid.value = 0

    dut.a_arready.value = 1
    for _ in range(20):
        await RisingEdge(dut.clk)
        if int(dut.a_arvalid.value):
            break
    await RisingEdge(dut.clk)
    dut.a_arready.value = 0

    packed = 1 | (1 << 8) | (1 << 16) | (1 << 24)
    dut.a_rvalid.value = 1
    dut.a_rdata.value = packed
    dut.a_rresp.value = RESP
    for _ in range(20):
        await RisingEdge(dut.clk)
        if int(dut.a_rready.value):
            break
    dut.a_rvalid.value = 0

    if RESP == 0:
        for _ in range(4):
            dut.b_valid.value = 1
            dut.b_data.value = 1
            for _ in range(20):
                await RisingEdge(dut.clk)
                if int(dut.b_ready.value):
                    break
            dut.b_valid.value = 0
            await RisingEdge(dut.clk)

        dut.bias_valid.value = 1
        dut.bias_data.value = 0
        for _ in range(20):
            await RisingEdge(dut.clk)
            if int(dut.bias_ready.value):
                break
        dut.bias_valid.value = 0

        y_value = None
        for _ in range(20):
            await RisingEdge(dut.clk)
            if int(dut.y_valid.value) and int(dut.y_ready.value):
                y_value = int(dut.y_data.value)
                break
        assert y_value is not None, "Y never presented"
        assert y_value == expected["Y_matrix"][0], (y_value, expected)
        for _ in range(10):
            await RisingEdge(dut.clk)
    else:
        for _ in range(3):
            await RisingEdge(dut.clk)
            assert int(dut.busy.value) == 0, "busy stayed high after an aborted (errored) job"

    # Clear the accepted-but-unrecorded AR/R transfer (hand-driven, so never
    # went through record_stimulus) via an actual protocol reset, matching
    # this design's own reset_behavior=abort_inflight, rather than leaving
    # the test to end mid-job.
    await _contract_drive_protocol_reset(dut, "clk", "rst_n", 0)
    await RisingEdge(dut.clk)
"""


def _generate(output_dir: Path, resp: int) -> dict[str, Any]:
    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    metadata = build_architect_operation_metadata(architecture, interface)
    assert not metadata["unrepresentable_operations"], metadata["unrepresentable_operations"]
    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(interface_plan, architecture, include_automatic_campaign=False)
    source = block + (_TB_BODY % resp)
    compile(source, "test_probe.py", "exec")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test_probe.py").write_text(source)
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    (output_dir / "functional_coverage_plan.json").write_text(json.dumps(coverage_plan, indent=2))
    return coverage_plan


def _run(tmp_path: Path, resp: int, label: str, rtl_source: str | None = None) -> dict[str, Any]:
    out = tmp_path / label
    tests = out / "tests"
    coverage_plan = _generate(tests, resp)
    reference = out / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    (reference / "model.py").write_text("")
    rtl_dir = HERE / "rtl"
    if rtl_source is not None:
        rtl_dir = out / "rtl"
        rtl_dir.mkdir(parents=True)
        (rtl_dir / f"{TOP_MODULE}.v").write_text(rtl_source)
    return run_cocotb_regression(
        rtl_dir=rtl_dir, top_module=TOP_MODULE, tests_dir=tests, reference_dir=reference,
        test_modules=["test_probe"], seed=1,
        build_dir=out / "build", report_path=out / "report.json", timeout_seconds=180,
        coverage_plan=coverage_plan, coverage_report_path=out / "coverage.json",
        stimulus_ledger_report_path=out / "ledger.json",
    )


def test_response_error_follows_nonokay(tmp_path):
    # This directed single-job TB does not attempt full coverage closure
    # (no existing campaign machinery can drive this mixed-transport
    # operation at all -- see the module docstring); it only needs to show
    # 0 assertion failures on both the compliant read and the injected
    # SLVERR read, so check status is not a hard failure class rather than
    # requiring overall PASS.
    okay = _run(tmp_path, 0, "okay")
    assert okay["status"] in ("PASS", "COVERAGE_FAILURE"), okay
    okay_report = json.loads((tmp_path / "okay" / "coverage.json").read_text())
    assert okay_report["assertion_failures"] == [], okay_report["assertion_failures"]

    slverr = _run(tmp_path, 2, "slverr")
    assert slverr["status"] in ("PASS", "COVERAGE_FAILURE"), slverr
    slverr_report = json.loads((tmp_path / "slverr" / "coverage.json").read_text())
    assert slverr_report["assertion_failures"] == [], slverr_report["assertion_failures"]


def test_continues_past_error_mutant_trips_busy_tracks_active_job(tmp_path):
    mutant_source = (MUTANTS_DIR / "ready_valid_axi_error_gemm_top__continues_past_error.v").read_text()
    result = _run(tmp_path, 2, "continues_past_error", rtl_source=mutant_source)
    assert result["status"] == "SIMULATION_FAILURE", result
    assert "busy is high without an active legal job" in result["stdout"], result["stdout"][-3000:]


def test_dropped_error_signal_trips_response_error_follows_nonokay(tmp_path):
    mutant_source = (
        MUTANTS_DIR / "ready_valid_axi_error_gemm_top__drops_error_signal.v"
    ).read_text()
    result = _run(tmp_path, 2, "drops_error_signal", rtl_source=mutant_source)
    assert result["status"] == "SIMULATION_FAILURE", result
    assert "response_error_follows_nonokay" in result["stdout"], result["stdout"][-3000:]
    assert "non-OKAY response was not followed by error" in result["stdout"], result["stdout"][-3000:]
