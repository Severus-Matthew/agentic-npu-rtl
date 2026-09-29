"""Paired generated-checker RTL tests for the AXI4-Stream standard rules
`ready_valid_stability` and `valid_low_during_reset`. No existing
AXI4-Stream fixture in this pool targets either rule (the existing ones
exercise packet-shape, signal-width, and continuous-packet rules instead).

Same fault shapes as the ready_valid/custom_mmio/axi4_lite AR siblings,
applied to TVALID/TREADY on a single-channel stream source.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_stream_ready_valid_source (
    input logic clk, rst, tready,
    output logic tvalid, tlast,
    output logic [31:0] tdata,
    output logic [3:0] tkeep, tstrb,
    output logic [1:0] tid, tdest,
    output logic [3:0] tuser
);
    localparam bit WITHDRAW_WHEN_STALLED = %d;
    localparam bit VALID_DURING_RESET = %d;
    logic pending;
    logic [3:0] stall_count;

    always_ff @(posedge clk) begin
        if (rst) begin
            pending <= 1'b0;
            stall_count <= 0;
        end else if (!pending) begin
            pending <= 1'b1;
            stall_count <= 0;
        end else if (tready) begin
            pending <= 1'b0;
        end else begin
            stall_count <= stall_count + 1'b1;
            if (WITHDRAW_WHEN_STALLED && stall_count == 2) pending <= 1'b0;
        end
    end
    assign tvalid = rst ? VALID_DURING_RESET : pending;
    assign tlast = 1'b1;
    assign tdata = 32'hA5A5A5A5;
    assign tkeep = 4'hF;
    assign tstrb = 4'hF;
    assign tid = 2'd0;
    assign tdest = 2'd0;
    assign tuser = 4'd0;
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

BACKPRESSURE_CYCLES = %d

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi4_stream_ready_valid(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.tready.value = 0
    transfers = 0
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.tready.value = int(cycle >= (2 + BACKPRESSURE_CYCLES))
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["tvalid"]) and int(snapshot["tready"]):
            transfers += 1
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if transfers >= 1:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert transfers >= 1, "producer never completed a single transfer"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


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
    flags, backpressure = {
        "withdraw_when_stalled": ((1, 0), 4),
        "valid_during_reset": ((0, 1), 0),
        "correct": ((0, 0), 3),
    }[variant]
    (rtl / "axi4_stream_ready_valid_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_stream_only()))
    (tests / "test_axi4_stream_ready_valid.py").write_text(source + _TB % backpressure)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_stream_ready_valid_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_stream_ready_valid"], seed=89,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_stream_ready_valid_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "withdraw_when_stalled")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "stall_stability" in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "valid_during_reset")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "valid_low_during_reset" in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
