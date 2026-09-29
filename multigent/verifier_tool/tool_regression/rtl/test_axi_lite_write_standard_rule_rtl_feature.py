"""Paired generated-checker RTL test for the AXI4-Lite standard rule
`write_response_after_address_and_data`, which the existing AXI4-Lite
fixtures (read-only) never exercise since none of them declare a write
channel. Per check_axi4_lite: BVALID presented while `pending_b` is still
empty (no AW+W pair has yet both transferred) fails this rule.

Same TB-side-stimulus technique as rule:axi4_lite.read_response_after_address
and rule:axi4.response_after_request: BVALID is a TB-driven input to this
small AXI4-Lite write manager (it issues AW/W only, not a subordinate), so
the fault is a deliberate response-channel stimulus choice, not an RTL
change.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_write_standard_rule_source (
    input logic clk, rst, awready, wready, bvalid,
    input logic [1:0] bresp,
    output logic awvalid, wvalid, bready,
    output logic [31:0] awaddr, wdata,
    output logic [2:0] awprot,
    output logic [3:0] wstrb
);
    logic aw_done, w_done;
    assign awaddr = 32'h1000;
    assign awprot = 3'd0;
    assign wdata = 32'hCAFEBABE;
    assign wstrb = 4'hF;
    assign awvalid = !rst && !aw_done;
    assign wvalid = !rst && !w_done;
    assign bready = !rst;
    always_ff @(posedge clk) begin
        if (rst) begin
            aw_done <= 1'b0;
            w_done <= 1'b0;
        end else begin
            if (awvalid && awready) aw_done <= 1'b1;
            if (wvalid && wready) w_done <= 1'b1;
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
async def check_axi_lite_write_standard_rules(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.awready.value = 0
    dut.wready.value = 0
    dut.bvalid.value = 0
    dut.bresp.value = 0
    completed = False
    for cycle in range(30):
        dut.rst.value = int(cycle < 2)
        # early_response: present BVALID starting the first post-reset cycle,
        # well before AWREADY/WREADY are ever raised, so pending_b is still
        # empty when the checker samples the first presented BVALID.
        if MODE == "early_response":
            dut.awready.value = int(cycle >= 6)
            dut.wready.value = int(cycle >= 6)
            dut.bvalid.value = int(cycle >= 2)
        else:
            dut.awready.value = int(cycle >= 2)
            dut.wready.value = int(cycle >= 2)
            dut.bvalid.value = int(cycle >= 6)
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


_RULE = "protocol.bus.write_response_after_address_and_data"


def _interface_write_only() -> dict:
    interface = _interface("axi4_lite")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"aw", "w", "b"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "aw", "w", "b"}]
    return interface


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_write_standard_rule_source.sv").write_text(_RTL)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_write_only()))
    (tests / "test_lite_write_standard_rules.py").write_text(source + _TB % mode)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_write_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_lite_write_standard_rules"], seed=41,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_write_standard_rule_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "early_response")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
