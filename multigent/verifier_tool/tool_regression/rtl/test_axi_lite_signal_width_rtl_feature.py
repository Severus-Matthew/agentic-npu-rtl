"""Paired generated-checker RTL test for the AXI4-Lite standard rule
`standard_signal_widths` (check_standard_signal_widths), which every other
AXI4-Lite fixture in this pool always satisfies (they all declare
correctly-sized ports), so it has never been exercised by a fault. The
check compares each field's *actually simulated* RTL port width (via
cocotb/Verilator's own width introspection, not the interface contract's
declared width) against AXI4-Lite's fixed table (`prot` must be 3 bits).

Same read-only manager pattern as test_axi_lite_standard_rules_rtl_feature.py,
with ARPROT genuinely declared 2 bits wide in the fault RTL instead of 3.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL_NARROW = """module axi_lite_signal_width_source (
    input logic clk, rst, arready, rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [1:0] arprot
);
    logic issued;
    assign arvalid = !rst && !issued;
    assign rready = !rst;
    assign araddr = 32'h1000;
    assign arprot = 2'd0;
    always_ff @(posedge clk) begin
        if (rst) issued <= 1'b0;
        else if (arvalid && arready) issued <= 1'b1;
    end
endmodule
"""

_RTL_CORRECT = """module axi_lite_signal_width_source (
    input logic clk, rst, arready, rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [2:0] arprot
);
    logic issued;
    assign arvalid = !rst && !issued;
    assign rready = !rst;
    assign araddr = 32'h1000;
    assign arprot = 3'd0;
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

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi_lite_signal_widths(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    completed = False
    for cycle in range(30):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        dut.rvalid.value = int(cycle >= 6)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["rvalid"]) and int(snapshot["rready"]):
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
"""


_RULE = "protocol.bus.standard_signal_widths"


def _interface_read_only() -> dict:
    interface = _interface("axi4_lite")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    return interface


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    rtl_source = _RTL_NARROW if variant == "narrow_prot" else _RTL_CORRECT
    (rtl / "axi_lite_signal_width_source.sv").write_text(rtl_source)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_only()))
    (tests / "test_lite_signal_widths.py").write_text(source + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_signal_width_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_lite_signal_widths"], seed=53,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_signal_width_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "narrow_prot")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
