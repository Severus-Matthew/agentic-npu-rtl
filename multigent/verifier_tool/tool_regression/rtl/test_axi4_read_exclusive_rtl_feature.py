"""Paired generated-checker RTL test for the AXI4 standard rule
`exclusive_response_consistency` on the *read* side, and for the
`axi4_response_code.exokay` coverage bin. Needs an explicit ARLOCK "lock"
field, which no existing AXI4 fixture in this pool declares (the existing
`test_axi4_exclusive_rtl_feature.py` only declares AWLOCK on the write
side).

Two independent single-beat-burst read scenarios on the same manager RTL,
differing only in the TB-driven ARLOCK value (RRESP is a TB-driven input to
this read-only manager, same technique as
`test_axi4_standard_rules_rtl_feature.py`'s response-channel rules):
`exokay_for_exclusive_read` issues ARLOCK=1 and the TB (playing the
subordinate) returns EXOKAY, which is legal only for a genuinely exclusive
read; `exokay_for_non_exclusive_read` issues ARLOCK=0 with the same EXOKAY
response, which `exclusive_response_consistency` must reject.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_read_exclusive_source (
    input logic clk, rst, arready, rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    input logic rlast,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [7:0] arlen,
    output logic [2:0] arsize,
    output logic [1:0] arburst,
    output logic arlock
);
    localparam bit NON_EXCLUSIVE = %d;
    logic issued;
    assign araddr = 32'h1000;
    assign arlen = 8'd0;
    assign arsize = 2;
    assign arburst = 1;
    assign arlock = !NON_EXCLUSIVE;
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
async def check_axi4_read_exclusive(dut):
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
        # Both modes return EXOKAY; only the RTL's ARLOCK (driven by
        # MODE via NON_EXCLUSIVE above) differs between them.
        dut.rresp.value = 1
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
    target = "channel.r.axi4_response_code.exokay"
    assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_RULES = {
    "exokay_for_non_exclusive_read": "protocol.bus.exclusive_response_consistency",
}


def _interface_read_with_lock() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    interface["signals"].append({
        "name": "arlock", "role": "metadata", "semantic_class": "exclusive_lock",
        "protocol_field": "lock", "direction": "output", "channel": "ar", "width": "1",
    })
    return interface


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    non_exclusive = int(mode == "exokay_for_non_exclusive_read")
    (rtl / "axi4_read_exclusive_source.sv").write_text(_RTL % non_exclusive)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_with_lock()))
    (tests / "test_axi4_read_exclusive.py").write_text(source + _TB % mode)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_read_exclusive_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_read_exclusive"], seed=23,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_read_exclusive_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "exokay_for_non_exclusive_read")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["exokay_for_non_exclusive_read"] in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "exokay_for_exclusive_read")
    assert good["status"] == "PASS", good
