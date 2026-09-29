"""Paired generated-checker RTL test for the AXI4-Stream standard rule
`standard_signal_widths` (which, per IMPLEMENTATION_MAP.md, folds
`keep_and_strobe_width_match_data_bytes` into the same runtime feature id).
test_axi4_stream_standard_rules_rtl_feature.py's RTL always declares
correctly-sized TKEEP/TSTRB (4 bits for a 32-bit/4-byte TDATA), so this had
never been exercised by a fault: TKEEP genuinely declared 3 bits instead of
the required 4 (4-byte TDATA / 8 = 4).
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL_NARROW = """module axi4_stream_signal_width_source (
    input logic clk, rst, tready,
    output logic tvalid, tlast,
    output logic [31:0] tdata,
    output logic [2:0] tkeep,
    output logic [3:0] tstrb,
    output logic [1:0] tid, tdest,
    output logic [3:0] tuser
);
    logic sent;
    assign tvalid = !rst && !sent;
    assign tlast = 1'b1;
    assign tdata = 32'hA5A5A5A5;
    assign tkeep = 3'b111;
    assign tstrb = 4'hF;
    assign tid = 2'd0;
    assign tdest = 2'd0;
    assign tuser = 4'd0;
    always_ff @(posedge clk) begin
        if (rst) sent <= 1'b0;
        else if (tvalid && tready) sent <= 1'b1;
    end
endmodule
"""

_RTL_CORRECT = """module axi4_stream_signal_width_source (
    input logic clk, rst, tready,
    output logic tvalid, tlast,
    output logic [31:0] tdata,
    output logic [3:0] tkeep,
    output logic [3:0] tstrb,
    output logic [1:0] tid, tdest,
    output logic [3:0] tuser
);
    logic sent;
    assign tvalid = !rst && !sent;
    assign tlast = 1'b1;
    assign tdata = 32'hA5A5A5A5;
    assign tkeep = 4'hF;
    assign tstrb = 4'hF;
    assign tid = 2'd0;
    assign tdest = 2'd0;
    assign tuser = 4'd0;
    always_ff @(posedge clk) begin
        if (rst) sent <= 1'b0;
        else if (tvalid && tready) sent <= 1'b1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi4_stream_signal_widths(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.tready.value = 0
    for cycle in range(20):
        dut.rst.value = int(cycle < 2)
        dut.tready.value = int(cycle >= 2)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULE = "protocol.bus.standard_signal_widths"


def _interface_stream_only() -> dict:
    interface = _interface("axi4_stream")
    interface["channels"] = [c for c in interface["channels"] if c["name"] == "t"]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "t"}]
    return interface


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    rtl_source = _RTL_NARROW if variant == "narrow_keep" else _RTL_CORRECT
    (rtl / "axi4_stream_signal_width_source.sv").write_text(rtl_source)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_stream_only()))
    (tests / "test_axi4_stream_signal_widths.py").write_text(source + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_stream_signal_width_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_stream_signal_widths"], seed=61,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_stream_signal_width_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "narrow_keep")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
