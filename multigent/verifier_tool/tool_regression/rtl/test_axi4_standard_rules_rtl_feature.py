"""Paired generated-checker RTL tests for two AXI4 *standard protocol rules*
from `_check_address()` (protocol/assertion/assertion_checkers.py) that
test_axi4_read_rtl_feature_matrix.py's existing fault flags don't violate
(that file's ONLY_INCR/ONLY_SINGLE/ONLY_FULL/ONLY_ALIGNED/NO_BOUNDARY/
NO_ERROR_REQUEST/ZERO_ID flags all narrow which *legal* value gets used --
none of them ever drive an outright illegal encoding, so they qualify
coverage bins, never these rules): `legal_burst_encoding` (ARBURST driven to
the reserved 2'b11 encoding) and `no_4k_boundary_crossing` (a single-beat
transfer whose address genuinely spans the 4K boundary, not just reaches it).

Same small single-outstanding AXI4 read manager pattern as that file, reused
here as a genuinely independent RTL: a single-beat, single-burst issuer
instead of an 8-burst sequence, since one fault-triggering transaction is
all either rule needs.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_standard_rule_source (
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
    localparam bit RESERVED_BURST = %d;
    localparam bit CROSS_4K = %d;
    logic issued;
    assign arvalid = !rst && !issued;
    assign rready = !rst;
    // A single narrow beat can never cross a 4K container (it only ever
    // spans its own aligned transfer-size window -- see axi.py's
    // axi_transfer_windows docstring), so the crossing fault needs an
    // 8-beat INCR burst starting near the boundary: beats land at
    // 0x0ff0, 0x0ff4, ..., 0x1000, 0x1004 -- the last two beats fall in
    // the next 4K page.
    assign araddr = CROSS_4K ? 32'h0FF0 : 32'h1000;
    assign arlen = CROSS_4K ? 8'd7 : 8'd0;
    assign arsize = 2;
    assign arburst = RESERVED_BURST ? 2'b11 : 2'b01;
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
async def check_axi4_standard_rules(dut):
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
        # response_after_request: present RVALID at the exact cycle the only
        # AR transfer is accepted, so from the checker's per-cycle evaluation
        # order (response side is checked before this cycle's AR is folded
        # into `reads`) it sees a response with no prior AR yet recorded.
        spurious = MODE == "response_after_request" and cycle == 2 and remaining is None
        dut.rvalid.value = int(remaining is not None or spurious)
        dut.rlast.value = int((remaining is not None and remaining == 1) or spurious)
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


_RULES = {
    "reserved_burst": "protocol.bus.legal_burst_encoding",
    "cross_4k": "protocol.bus.no_4k_boundary_crossing",
    "response_after_request": "protocol.bus.response_after_request",
}


def _interface_read_only() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    return interface


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flags = {
        "reserved_burst": (1, 0),
        "cross_4k": (0, 1),
        "response_after_request": (0, 0),
        "correct": (0, 0),
    }[variant]
    (rtl / "axi4_standard_rule_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_only()))
    (tests / "test_axi4_standard_rules.py").write_text(source + _TB % variant)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_axi4_standard_rules"], seed=23,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi4_standard_rule_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "reserved_burst")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["reserved_burst"] in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "cross_4k")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["cross_4k"] in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "response_after_request")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["response_after_request"] in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
