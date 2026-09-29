"""Paired generated-checker RTL tests for the AXI4 standard rules
`exclusive_access_restrictions` and `exclusive_response_consistency`. Needs
an explicit AWLOCK/BID-adjacent "lock" field, which no existing AXI4
fixture in this pool declares.

Two independent single-beat-burst write scenarios on the same manager RTL:
`bad_exclusive_size` issues an AWLOCK=1 (exclusive) write with a 3-beat
burst (12 total bytes, not a power of two -- exclusive bursts must total a
power-of-two size of at most 128 bytes); `exokay_for_non_exclusive` issues
an ordinary AWLOCK=0 write and the TB (playing the subordinate) returns an
EXOKAY response, which is only legal for a genuinely exclusive write.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_exclusive_source (
    input logic clk, rst, awready, wready, bvalid,
    input logic [1:0] bresp,
    output logic awvalid, wvalid, bready, wlast,
    output logic [31:0] awaddr, wdata,
    output logic [7:0] awlen,
    output logic [2:0] awsize,
    output logic [1:0] awburst,
    output logic awlock,
    output logic [3:0] wstrb
);
    localparam bit BAD_EXCLUSIVE_SIZE = %d;
    localparam bit NON_EXCLUSIVE = %d;
    logic aw_done;
    logic [1:0] w_beats;
    logic [7:0] beats_total;
    assign beats_total = BAD_EXCLUSIVE_SIZE ? 8'd3 : 8'd1;
    assign awaddr = 32'h1000;
    assign awlen = beats_total - 8'd1;
    assign awsize = 2;
    assign awburst = 1;
    assign awlock = !NON_EXCLUSIVE;
    assign wdata = 32'hCAFEBABE;
    assign wstrb = 4'hF;
    assign awvalid = !rst && !aw_done;
    assign wvalid = !rst && aw_done && (w_beats < beats_total[1:0]);
    assign wlast = (w_beats == beats_total[1:0] - 2'd1);
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

MODE = %r

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_axi4_exclusive(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.awready.value = 0
    dut.wready.value = 0
    dut.bvalid.value = 0
    dut.bresp.value = 0
    completed = False
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.awready.value = int(cycle >= 2)
        dut.wready.value = int(cycle >= 2)
        dut.bvalid.value = int(cycle >= 12)
        # exokay_for_non_exclusive: the TB (subordinate) returns EXOKAY(1)
        # for an ordinary AWLOCK=0 write, which is only legal for a real
        # exclusive write.
        dut.bresp.value = 1 if MODE == "exokay_for_non_exclusive" else 0
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
    assert completed, "the single write never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULES = {
    "bad_exclusive_size": "protocol.bus.exclusive_access_restrictions",
    "exokay_for_non_exclusive": "protocol.bus.exclusive_response_consistency",
}


def _interface_with_lock() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"aw", "w", "b"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "aw", "w", "b"}]
    interface["signals"].append({
        "name": "awlock", "role": "metadata", "semantic_class": "exclusive_lock",
        "protocol_field": "lock", "direction": "output", "channel": "aw", "width": "1",
    })
    return interface


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    # "correct" is deliberately an ordinary (non-exclusive) write, not a
    # legal exclusive one: a genuinely legal exclusive write must be
    # preceded by a completed matching exclusive read (a separate,
    # unrelated pairing rule this fixture doesn't exercise), so proving
    # that case would need an AR channel this write-only manager has no
    # other reason to declare. This still proves both checkers stay silent
    # on the common (non-exclusive) case.
    flags = (int(mode == "bad_exclusive_size"), int(mode != "bad_exclusive_size"))
    (rtl / "axi4_exclusive_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_with_lock()))
    (tests / "test_axi4_exclusive.py").write_text(source + _TB % mode)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_exclusive_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_exclusive"], seed=73,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_exclusive_fault_fix_pairs(tmp_path):
    for mode in ("bad_exclusive_size", "exokay_for_non_exclusive"):
        bad = _run(tmp_path, mode)
        assert bad["status"] == "SIMULATION_FAILURE", (mode, bad)
        assert _RULES[mode] in bad["stdout"], (mode, bad["stdout"][-3000:])

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
