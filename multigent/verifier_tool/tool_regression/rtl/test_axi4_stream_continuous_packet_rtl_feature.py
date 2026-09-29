"""Paired generated-checker RTL test for the AXI4-Stream standard rule
`continuous_packet_constraints_when_declared`, gated on the
`continuous_packets` protocol capability (no existing AXI4-Stream fixture
in this pool declares it). A 2-beat packet whose TID changes between the
first (non-terminal) and second (terminal) beat.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_stream_continuous_packet_source (
    input logic clk, rst, tready,
    output logic tvalid, tlast,
    output logic [31:0] tdata,
    output logic [3:0] tkeep, tstrb,
    output logic [1:0] tid, tdest,
    output logic [3:0] tuser
);
    localparam bit KEY_CHANGES_MID_PACKET = %d;
    logic [1:0] beat_index;
    assign tvalid = !rst && (beat_index < 2'd2);
    assign tlast = (beat_index == 2'd1);
    assign tdata = 32'hA5A5A5A5;
    assign tkeep = 4'hF;
    assign tstrb = 4'hF;
    assign tid = (KEY_CHANGES_MID_PACKET && beat_index == 2'd1) ? 2'd1 : 2'd0;
    assign tdest = 2'd0;
    assign tuser = 4'd0;
    always_ff @(posedge clk) begin
        if (rst) beat_index <= 2'd0;
        else if (tvalid && tready) beat_index <= beat_index + 2'd1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi4_stream_continuous_packet(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.tready.value = 0
    completed = False
    for cycle in range(30):
        dut.rst.value = int(cycle < 2)
        dut.tready.value = int(cycle >= 2)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["tvalid"]) and int(snapshot["tready"]) and int(snapshot["tlast"]):
            completed = True
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed, "the 2-beat packet never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULE = "protocol.bus.continuous_packet_constraints_when_declared"


def _interface_stream_only() -> dict:
    interface = _interface("axi4_stream")
    interface["channels"] = [c for c in interface["channels"] if c["name"] == "t"]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "t"}]
    interface["channels"][0]["protocol_capabilities"] = {"continuous_packets": True}
    return interface


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flag = int(variant == "key_changes")
    (rtl / "axi4_stream_continuous_packet_source.sv").write_text(_RTL % flag)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_stream_only()))
    (tests / "test_axi4_stream_continuous_packet.py").write_text(source + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_stream_continuous_packet_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_stream_continuous_packet"], seed=79,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_stream_continuous_packet_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "key_changes")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
