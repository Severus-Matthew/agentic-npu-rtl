"""Directed coverage test for the `axis_keep_pattern.empty_last` bin: "TLAST
closes a packet with all TKEEP bits clear" (protocol_features.yaml). This is
a legal AXI4-Stream pattern (a null/padding beat marking end-of-packet with
zero valid bytes) -- confirmed by reading check_axi4_stream
(assertion_checkers.py): every strict TKEEP-prefix-shape rule that could
plausibly restrict this (continuous_packet_constraints_when_declared) is
gated behind `capabilities.get("continuous_packets") is True`, which this
fixture's interface never declares, so no assertion can fire regardless of
TKEEP's value on the terminal beat.

TKEEP/TLAST are TB-driven outputs of this tiny combinational source (a
handful of beats sequenced by a counter); the "fault" is a single stimulus
bit (EMPTY_LAST) selecting whether the terminal beat's TKEEP is full or
all-zero -- no assertion is expected to differ between the two, only the
coverage bin each one hits.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axis_empty_last_source (
    input logic clk, rst, tready,
    output logic tvalid, tlast,
    output logic [31:0] tdata,
    output logic [3:0] tkeep
);
    localparam bit EMPTY_LAST = %d;
    logic [1:0] beat;
    assign tvalid = !rst && beat < 2'd2;
    assign tlast = (beat == 2'd1);
    assign tdata = 32'(beat + 1);
    assign tkeep = (EMPTY_LAST && beat == 2'd1) ? 4'b0000 : 4'b1111;
    always_ff @(posedge clk) begin
        if (rst) beat <= 2'd0;
        else if (tvalid && tready) beat <= beat + 2'd1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_empty_last(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.tready.value = 0
    completed = False
    for cycle in range(40):
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
    target = %r
    assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


def _interface_stream_minimal() -> dict:
    interface = _interface("axi4_stream")
    keep = {"clk", "rst", "tvalid", "tready", "tdata", "tkeep", "tlast"}
    interface["signals"] = [s for s in interface["signals"] if s["name"] in keep]
    return interface


def _run(tmp_path, *, empty_last: bool) -> dict:
    variant = "empty_last" if empty_last else "full_last"
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axis_empty_last_source.sv").write_text(_RTL % int(empty_last))
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_stream_minimal()))
    target = "channel.t.axis_keep_pattern." + ("empty_last" if empty_last else "full")
    (tests / "test_axis_empty_last.py").write_text(source + _TB % target)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axis_empty_last_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axis_empty_last"], seed=11,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axis_empty_last_coverage(tmp_path):
    result = _run(tmp_path, empty_last=True)
    assert result["status"] == "PASS", result

    # Sibling positive control: an ordinary (non-empty) terminal beat hits
    # the "full" bin instead, confirming the two are genuinely distinguished
    # by this fixture and not both vacuously satisfied.
    result = _run(tmp_path, empty_last=False)
    assert result["status"] == "PASS", result
