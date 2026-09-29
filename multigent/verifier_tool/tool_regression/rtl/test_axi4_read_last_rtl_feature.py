"""Paired generated-checker RTL test for the AXI4 standard rule
`read_last_matches_length`, the read-side sibling of
rule:axi4.write_last_matches_length (test_axi4_write_last_rtl_feature.py).
test_axi4_read_rtl_feature_matrix.py's TB tracks remaining beats correctly
for every one of its bursts (including a 17-beat one), so its RTL already
gets this right in every variant -- none of its fault flags ever drive RLAST
incorrectly, so this rule has no fault/fix pair anywhere in this pool yet.

A 2-beat (ARLEN=1) read burst: the fault variant never asserts RLAST; the
corrected variant asserts it on the second (final) beat.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_read_last_source (
    input logic clk, rst, arready,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [7:0] arlen,
    output logic [2:0] arsize,
    output logic [1:0] arburst,
    input logic rvalid, rlast,
    input logic [31:0] rdata,
    input logic [1:0] rresp
);
    assign araddr = 32'h1000;
    assign arlen = 8'd1;
    assign arsize = 2;
    assign arburst = 1;
    logic issued;
    assign arvalid = !rst && !issued;
    assign rready = !rst;
    always_ff @(posedge clk) begin
        if (rst) issued <= 1'b0;
        else if (arvalid && arready) issued <= 1'b1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

MODE = %r

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi4_read_last(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    dut.rlast.value = 0
    remaining = None
    completed = False
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        dut.rvalid.value = int(remaining is not None)
        # never_assert_rlast: RLAST stays low even on what should be the
        # final beat (remaining == 1) -- the read-side mirror of
        # write_last_matches_length's NEVER_ASSERT_WLAST fault.
        dut.rlast.value = int(MODE != "never_assert_rlast" and remaining == 1)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if remaining is None and int(snapshot["arvalid"]) and int(snapshot["arready"]):
            remaining = int(snapshot["arlen"]) + 1
        if remaining is not None and int(snapshot["rvalid"]) and int(snapshot["rready"]):
            remaining -= 1
            if remaining == 0:
                completed = True
                remaining = None
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed, "the single read burst never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULE = "protocol.bus.read_last_matches_length"


def _interface_read_only() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    return interface


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi4_read_last_source.sv").write_text(_RTL)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_only()))
    (tests / "test_axi4_read_last.py").write_text(source + _TB % mode)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_read_last_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_read_last"], seed=47,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_read_last_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "never_assert_rlast")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
