"""Paired generated-checker RTL tests for the AXI4-Lite standard rules
`ready_valid_stability` and `valid_low_during_reset`, applied to the AR
channel of an otherwise-minimal read manager. No existing AXI4-Lite
fixture in this pool targets these two rules (the existing ones exercise
response-channel and signal-width rules instead).

Same fault shapes as test_ready_valid_standard_rules_rtl_feature.py's
producer RTL, applied to ARVALID/ARREADY instead of a bare channel:
WITHDRAW_WHEN_STALLED drops ARVALID before an accept while backpressured;
VALID_DURING_RESET asserts ARVALID while reset is active. The read
completes with a fixed OKAY response so the "correct" run finishes
cleanly; R itself is not the target of either fault here.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_ar_standard_rule_source (
    input logic clk, rst, arready, rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [2:0] arprot
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
        end else if (arready) begin
            pending <= 1'b0;
        end else begin
            stall_count <= stall_count + 1'b1;
            if (WITHDRAW_WHEN_STALLED && stall_count == 2) pending <= 1'b0;
        end
    end
    assign arvalid = rst ? VALID_DURING_RESET : pending;
    assign araddr = 32'h1000;
    assign arprot = 3'd0;
    assign rready = !rst;
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

BACKPRESSURE_CYCLES = %d

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi_lite_ar_standard_rules(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    accepted = False
    completed = False
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= (2 + BACKPRESSURE_CYCLES))
        dut.rvalid.value = int(accepted and not completed)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["arvalid"]) and int(snapshot["arready"]):
            accepted = True
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
    assert completed, "producer never completed a single transfer"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


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
    flags, backpressure = {
        "withdraw_when_stalled": ((1, 0), 4),
        "valid_during_reset": ((0, 1), 0),
        "correct": ((0, 0), 3),
    }[variant]
    (rtl / "axi_lite_ar_standard_rule_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_only()))
    (tests / "test_axi_lite_ar_standard_rules.py").write_text(source + _TB % backpressure)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_ar_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi_lite_ar_standard_rules"], seed=83,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_ar_standard_rule_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "withdraw_when_stalled")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "stall_stability" in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "valid_during_reset")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "valid_low_during_reset" in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
