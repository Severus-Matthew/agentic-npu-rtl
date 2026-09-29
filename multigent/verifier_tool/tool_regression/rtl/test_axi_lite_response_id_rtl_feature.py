"""Paired generated-checker RTL test for the AXI4-Lite standard rule
`optional_id_return_and_in_order_completion`: AXI4-Lite doesn't require an
ID field, but when one is declared, check_axi4_lite still requires the
returned ID to match the pending request. A single outstanding read
(ARID=0) answered with RID=1.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_response_id_source (
    input logic clk, rst, arready,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [2:0] arprot,
    output logic [3:0] arid,
    input logic rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    input logic [3:0] rid
);
    logic issued;
    assign araddr = 32'h1000;
    assign arprot = 3'd0;
    assign arid = 4'd0;
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
async def check_axi_lite_response_id(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    dut.rid.value = 0
    accepted = False
    completed = False
    for cycle in range(30):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        dut.rvalid.value = int(accepted and not completed)
        dut.rid.value = 1 if MODE == "wrong_id" else 0
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
    assert completed, "the single read never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULE = "protocol.bus.optional_id_return_and_in_order_completion"


def _interface_with_ids() -> dict:
    interface = _interface("axi4_lite")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    for prefix, direction in (("ar", "output"), ("r", "input")):
        interface["signals"].append({
            "name": f"{prefix}id", "role": "transaction_id",
            "semantic_class": "identifier", "protocol_field": "id",
            "channel": prefix, "direction": direction, "width": "4",
        })
    return interface


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_response_id_source.sv").write_text(_RTL)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_with_ids()))
    (tests / "test_lite_response_id.py").write_text(source + _TB % mode)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_response_id_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_lite_response_id"], seed=71,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_response_id_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "wrong_id")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULE in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
