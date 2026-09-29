"""Paired generated-checker RTL test for the AXI4 standard rule
`write_last_matches_length`, which test_axi4_write_rtl_feature_matrix.py's
existing single-beat-per-burst RTL (WLAST tied high unconditionally, always
legal since every burst there has AWLEN=0) never exercises: the check only
fires once at least AWLEN+1 beats have been collected without WLAST ever
having been asserted (protocol/assertion/assertion_checkers.py's
`_check_write_pair` caller, ~line 406).

A 2-beat (AWLEN=1) write burst: the fault variant never asserts WLAST; the
corrected variant asserts it on the second (final) beat.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_write_last_source (
    input logic clk, rst, awready, wready, bvalid,
    input logic [1:0] bresp,
    output logic awvalid, wvalid, bready, wlast,
    output logic [31:0] awaddr, wdata,
    output logic [7:0] awlen,
    output logic [2:0] awsize,
    output logic [1:0] awburst,
    output logic [3:0] wstrb
);
    localparam bit NEVER_ASSERT_WLAST = %d;
    logic aw_done;
    logic [1:0] w_beats;
    assign awaddr = 32'h1000;
    assign awlen = 8'd1;
    assign awsize = 2;
    assign awburst = 1;
    assign wdata = 32'hCAFEBABE;
    assign wstrb = 4'hF;
    assign awvalid = !rst && !aw_done;
    assign wvalid = !rst && aw_done && w_beats < 2;
    assign wlast = !NEVER_ASSERT_WLAST && (w_beats == 1);
    assign bready = !rst;
    always_ff @(posedge clk) begin
        if (rst) begin
            aw_done <= 1'b0;
            w_beats <= 2'd0;
        end else begin
            if (awvalid && awready) aw_done <= 1'b1;
            if (wvalid && wready) w_beats <= w_beats + 1'b1;
        end
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi4_write_last(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.awready.value = 0
    dut.wready.value = 0
    dut.bvalid.value = 0
    dut.bresp.value = 0
    completed = False
    for cycle in range(40):
        dut.rst.value = int(cycle < 2)
        dut.awready.value = int(cycle >= 2)
        dut.wready.value = int(cycle >= 2)
        dut.bvalid.value = int(cycle >= 10)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["bvalid"]) and int(snapshot["bready"]):
            completed = True
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed, "the single write burst never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULE = "protocol.bus.write_last_matches_length"


def _interface_write_only() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"aw", "w", "b"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "aw", "w", "b"}]
    return interface


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flag = {"never_assert_wlast": 1, "correct": 0}[variant]
    (rtl / "axi4_write_last_source.sv").write_text(_RTL % flag)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_write_only()))
    (tests / "test_axi4_write_last.py").write_text(source + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_write_last_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_write_last"], seed=31,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_write_last_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "never_assert_wlast")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
