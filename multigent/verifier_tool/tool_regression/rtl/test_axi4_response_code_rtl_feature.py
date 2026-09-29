"""Directed coverage tests for the `axi4_response_code.decerr` and
`axi_lite_response_code.decerr` coverage bins. RRESP is a TB-driven input on
both of these existing read-only manager fixtures (same technique as
`test_axi4_standard_rules_rtl_feature.py`'s response-channel rules); DECERR
is a legal AXI4/AXI4-Lite response code for any read (unlike EXOKAY, which
requires a genuinely exclusive read -- see
`test_axi4_read_exclusive_rtl_feature.py` -- DECERR needs no lock field and
carries no extra legality precondition), so these two variants just drive
RRESP=DECERR straight through the existing reference RTL and interfaces
with no RTL change at all.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.rtl.test_axi4_standard_rules_rtl_feature import (
    _RTL as _AXI4_RTL,
    _interface_read_only as _axi4_interface_read_only,
)
from multigent.verifier_tool.tool_regression.rtl.test_axi_lite_ar_standard_rules_rtl_feature import (
    _RTL as _AXI_LITE_RTL,
    _interface_read_only as _axi_lite_interface_read_only,
)
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_AXI4_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_decerr(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    dut.rlast.value = 0
    issued = False
    completed = False
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        dut.rvalid.value = int(issued and not completed)
        dut.rlast.value = int(issued and not completed)
        dut.rresp.value = 3 if issued else 0  # DECERR = 2'b11
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if not issued and int(snapshot["arvalid"]) and int(snapshot["arready"]):
            issued = True
        if issued and not completed and int(snapshot["rvalid"]) and int(snapshot["rready"]):
            completed = True
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed, "the single read never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    target = %r
    assert target in report["covered_bins"], f"missing required feature bin {target}"
"""

# AXI4-Lite has no burst/RLAST concept at all, so this manager's R channel
# (matching test_axi_lite_ar_standard_rules_rtl_feature.py's _RTL) never
# declares an rlast port.
_AXI_LITE_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_decerr(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    issued = False
    completed = False
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        dut.rvalid.value = int(issued and not completed)
        dut.rresp.value = 3 if issued else 0  # DECERR = 2'b11
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if not issued and int(snapshot["arvalid"]) and int(snapshot["arready"]):
            issued = True
        if issued and not completed and int(snapshot["rvalid"]) and int(snapshot["rready"]):
            completed = True
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed, "the single read never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    target = %r
    assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


def test_axi4_decerr_coverage(tmp_path):
    rtl, tests, reference = tmp_path / "rtl", tmp_path / "tests", tmp_path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi4_standard_rule_source.sv").write_text(_AXI4_RTL % (0, 0))
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_axi4_interface_read_only()))
    (tests / "test_axi4_decerr.py").write_text(source + _AXI4_TB % "channel.r.axi4_response_code.decerr")
    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_decerr"], seed=23,
        build_dir=tmp_path / "build", report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result


def test_axi4_lite_decerr_coverage(tmp_path):
    rtl, tests, reference = tmp_path / "rtl", tmp_path / "tests", tmp_path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_ar_standard_rule_source.sv").write_text(_AXI_LITE_RTL % (0, 0))
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_axi_lite_interface_read_only()))
    (tests / "test_axi_lite_decerr.py").write_text(source + _AXI_LITE_TB % "channel.r.axi_lite_response_code.decerr")
    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_ar_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi_lite_decerr"], seed=83,
        build_dir=tmp_path / "build", report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result
