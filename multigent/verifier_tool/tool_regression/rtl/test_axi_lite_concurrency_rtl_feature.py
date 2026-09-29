"""AXI4-Lite simultaneous read/write coverage against a real RTL pair."""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_concurrent_source (
    input logic clk, rst, awready, wready, arready, bvalid, rvalid,
    input logic [1:0] bresp, rresp,
    input logic [31:0] rdata,
    output logic awvalid, wvalid, arvalid, bready, rready,
    output logic [31:0] awaddr, wdata, araddr,
    output logic [3:0] wstrb,
    output logic [2:0] awprot, arprot
);
    localparam bit SERIAL_FINAL = %d;
    logic [3:0] phase;
    assign awvalid = !rst && (phase == 0 || phase == 4);
    assign wvalid  = awvalid;
    assign arvalid = !rst && (phase == 2 || (SERIAL_FINAL ? phase == 5 : phase == 4));
    assign awaddr = phase == 0 ? 32'h0010 : 32'h0020;
    assign araddr = phase == 2 ? 32'h0030 : 32'h0040;
    assign wdata = 32'hA5A55A5A;
    assign wstrb = 4'hF;
    assign awprot = 0;
    assign arprot = 0;
    assign bready = !rst;
    assign rready = !rst;
    always_ff @(posedge clk) begin
        if (rst) phase <= 0;
        else if (phase < 8) phase <= phase + 1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_lite_concurrency(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    for name in ("awready", "wready", "arready", "bvalid", "rvalid", "bresp", "rresp", "rdata"):
        getattr(dut, name).value = 0
    writes = []
    reads = []
    w_count = 0
    aw_count = 0
    ar_count = 0
    b_count = 0
    r_count = 0
    for cycle in range(20):
        dut.rst.value = int(cycle < 2)
        dut.awready.value = int(cycle >= 2)
        dut.wready.value = int(cycle >= 2)
        dut.arready.value = int(cycle >= 2)
        dut.bvalid.value = int(bool(writes and cycle - writes[0] >= 2))
        dut.rvalid.value = int(bool(reads and cycle - reads[0] >= 2))
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["bvalid"]) and int(snapshot["bready"]):
            writes.pop(0)
            b_count += 1
        if int(snapshot["rvalid"]) and int(snapshot["rready"]):
            reads.pop(0)
            r_count += 1
        if int(snapshot["awvalid"]) and int(snapshot["awready"]):
            aw_count += 1
        if int(snapshot["wvalid"]) and int(snapshot["wready"]):
            w_count += 1
            writes.append(cycle)
        if int(snapshot["arvalid"]) and int(snapshot["arready"]):
            ar_count += 1
            reads.append(cycle)
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
    _finalize_contract_protocol_assertions()
    assert (aw_count, w_count, ar_count, b_count, r_count) == (2, 2, 2, 2, 2)
    report = tracker.report()
    assert report["assertion_failures"] == [], report["assertion_failures"]
    target = "protocol_group.bus.axi_lite_read_write_concurrency.simultaneous"
    assert target in report["covered_bins"], f"missing required feature bin {target}"
    for name in ("write_only_cycle", "read_only_cycle"):
        assert "protocol_group.bus.axi_lite_read_write_concurrency." + name in report["covered_bins"]
"""


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_concurrent_source.sv").write_text(_RTL % int(variant == "serial"))
    (reference / "model.py").write_text("")
    interface = _interface("axi4_lite")
    interface["channels"][0]["protocol_capabilities"] = {
        "read_write_concurrency": True,
        "max_outstanding": 2,
    }
    source = render_contract_generated_block(build_interface_coverage_plan(interface))
    (tests / "test_lite_concurrency.py").write_text(source + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_concurrent_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_lite_concurrency"], seed=17,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_concurrency_fault_fix_pair(tmp_path):
    bad = _run(tmp_path, "serial")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "axi_lite_read_write_concurrency.simultaneous" in bad["stdout"], bad["stdout"][-3000:]
    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
