"""Paired generated-checker RTL tests for AXI4-Lite read/response features."""

from __future__ import annotations

import json
import shutil

import pytest

from multigent.tests.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_read_feature_source (
    input logic clk, rst, arready, rvalid,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [2:0] arprot
);
    localparam bit NO_ERROR_ADDRESS = %d;
    localparam bit ZERO_PROT = %d;
    localparam bit SINGLE_OUTSTANDING = %d;
    logic [2:0] issued;
    logic [2:0] completed;
    assign arvalid = !rst && issued < 4 &&
        (!SINGLE_OUTSTANDING || issued == completed);
    assign rready = !rst;
    always_comb begin
        case (issued)
          0: araddr = 32'h0000;
          1: araddr = NO_ERROR_ADDRESS ? 32'h0800 : 32'h1000;
          2: araddr = 32'h2000;
          3: araddr = 32'h3000;
          default: araddr = 0;
        endcase
    end
    assign arprot = ZERO_PROT ? 3'd0 : {2'd0, issued[0]};
    always_ff @(posedge clk) begin
        if (rst) begin issued <= 0; completed <= 0; end
        else begin
            if (arvalid && arready) issued <= issued + 1;
            if (rvalid && rready) completed <= completed + 1;
        end
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

TARGETS = %s

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_lite_read_features(dut):
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
        dut.rvalid.value = int(reply is not None)
        dut.rresp.value = 2 if reply is not None and reply["addr"] == 0x1000 else 0
        dut.rdata.value = 7
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["rvalid"]) and int(snapshot["rready"]):
            pending.pop(0)
            completed += 1
        if int(snapshot["arvalid"]) and int(snapshot["arready"]):
            pending.append({"addr": int(snapshot["araddr"]), "cycle": cycle})
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed == 4:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed == 4, f"only {completed} responses completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for target in TARGETS:
        assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_FEATURE_BINS = {
    "response": "channel.r.axi_lite_response_code.slverr",
    "protection": "protocol_field.bus_read_address_prot.axi_lite_protection_partition.nonzero",
    "outstanding": "protocol_group.bus.axi_lite_outstanding_depth.multiple",
}


def _interface_read_only() -> dict:
    interface = _interface("axi4_lite")
    interface["channels"] = [c for c in interface["channels"] if c["name"] in {"ar", "r"}]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") in {None, "ar", "r"}]
    interface["channels"][0]["protocol_capabilities"] = {
        "max_outstanding": 2,
        "protection_bins": ["zero", "nonzero"],
    }
    return interface


def _run(tmp_path, variant: str, targets: list[str]) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flags = {
        "no_error_address": (1, 0, 0),
        "zero_prot": (0, 1, 0),
        "single_outstanding": (0, 0, 1),
        "correct": (0, 0, 0),
    }[variant]
    (rtl / "axi_lite_read_feature_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_read_only()))
    (tests / "test_lite_read_features.py").write_text(source + _TB % json.dumps(targets))
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_read_feature_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_lite_read_features"], seed=13,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_lite_read_response_protection_and_outstanding_fault_fix_pairs(tmp_path):
    for variant, feature in (
        ("no_error_address", "response"),
        ("zero_prot", "protection"),
        ("single_outstanding", "outstanding"),
    ):
        target = _FEATURE_BINS[feature]
        bad = _run(tmp_path, variant, [target])
        assert bad["status"] == "SIMULATION_FAILURE", (variant, bad)
        assert target in bad["stdout"], (variant, bad["stdout"][-3000:])
    good = _run(tmp_path, "correct", [
        *_FEATURE_BINS.values(),
        "channel.r.axi_lite_response_code.okay",
        "protocol_field.bus_read_address_prot.axi_lite_protection_partition.zero",
        "protocol_group.bus.axi_lite_outstanding_depth.one",
    ])
    assert good["status"] == "PASS", good
