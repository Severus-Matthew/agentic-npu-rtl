"""Paired generated-checker tests for two AXI4-Lite *standard protocol rules*
from check_axi4_lite() (protocol/assertion/assertion_checkers.py) that
test_axi_lite_read_rtl_feature_matrix.py does not target:
`legal_lite_response_encoding` and `read_response_after_address`.

Unlike the RTL-localparam-fault pattern used elsewhere, the fault here lives
in the TB's own response-channel stimulus, not in the RTL: `rvalid`/`rresp`
are TB-driven inputs to this small requester RTL (the RTL only issues AR
requests; it does not implement an AXI4-Lite subordinate), so the "subordinate
bus behavior" being checked is inherently played by the TB script. This still
exercises the real generated checker (render_contract_generated_block's
_check_contract_protocol_assertions) against a real Verilator/cocotb
waveform -- it is the checker's detection of a misbehaving bus under strict
qualification, not a stubbed check. The RTL itself is identical (fault-free)
across all three variants.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_standard_rule_source (
    input logic clk, rst, arready, rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [2:0] arprot
);
    logic [2:0] issued;
    assign arvalid = !rst && issued < 4;
    assign rready = !rst;
    always_comb begin
        case (issued)
          0: araddr = 32'h0000;
          1: araddr = 32'h1000;
          2: araddr = 32'h2000;
          3: araddr = 32'h3000;
          default: araddr = 0;
        endcase
    end
    assign arprot = {2'd0, issued[0]};
    always_ff @(posedge clk) begin
        if (rst) issued <= 0;
        else if (arvalid && arready) issued <= issued + 1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

MODE = %r

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_lite_standard_rules(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    pending = []
    completed = 0
    for cycle in range(90):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        reply = pending[0] if pending and cycle - pending[0]["cycle"] >= 3 else None
        spurious = MODE == "spurious_response" and cycle == 2 and not pending
        dut.rvalid.value = int(reply is not None or spurious)
        dut.rresp.value = 1 if (MODE == "illegal_resp" and reply is not None) else 0
        dut.rdata.value = 7
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["rvalid"]) and int(snapshot["rready"]):
            if pending:
                pending.pop(0)
            completed += 1
        if int(snapshot["arvalid"]) and int(snapshot["arready"]):
            pending.append({"addr": int(snapshot["araddr"]), "cycle": cycle})
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed >= 4:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


_RULES = {
    "illegal_resp": "protocol.bus.legal_lite_response_encoding",
    "spurious_response": "protocol.bus.read_response_after_address",
}


def _interface_read_only() -> dict:
    interface = _interface("axi4_lite")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    return interface


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_standard_rule_source.sv").write_text(_RTL)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_only()))
    (tests / "test_lite_standard_rules.py").write_text(source + _TB % mode)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_lite_standard_rules"], seed=17,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_lite_standard_rule_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "illegal_resp")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["illegal_resp"] in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "spurious_response")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["spurious_response"] in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
