"""Real-RTL AXI4 write strobe/order bins from one frozen generated plan."""

from __future__ import annotations

import json
import shutil

import pytest

from multigent.tests.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_write_feature_source (
    input logic clk, rst, awready, wready, bvalid,
    input logic [1:0] bresp,
    input logic [3:0] bid,
    output logic awvalid, wvalid, bready, wlast,
    output logic [31:0] awaddr, wdata,
    output logic [7:0] awlen,
    output logic [2:0] awsize,
    output logic [1:0] awburst,
    output logic [3:0] awid, wstrb
);
    localparam bit NO_SPARSE = %d;
    localparam bit NO_DATA_FIRST = %d;
    localparam bit NO_SAME_CYCLE = %d;
    logic [1:0] index;
    logic aw_done, w_done, waiting_b;
    assign awaddr = 32'h1000 + (32'(index) * 4);
    assign awlen = 0;
    assign awsize = 2;
    assign awburst = 1;
    assign awid = {2'd0, index};
    assign wdata = 32'h12340000 + 32'(index);
    assign wstrb = index == 0 ? 4'b0000 :
                   index == 1 && !NO_SPARSE ? 4'b0101 : 4'b1111;
    assign wlast = 1;
    assign bready = waiting_b && !rst;
    always_comb begin
        awvalid = 0;
        wvalid = 0;
        if (!rst && index < 3 && !waiting_b) begin
            case (index)
              0: begin
                  awvalid = !aw_done;
                  wvalid = aw_done && !w_done;
              end
              1: if (NO_DATA_FIRST) begin
                  awvalid = !aw_done;
                  wvalid = aw_done && !w_done;
              end else begin
                  wvalid = !w_done;
                  awvalid = w_done && !aw_done;
              end
              2: if (NO_SAME_CYCLE) begin
                  awvalid = !aw_done;
                  wvalid = aw_done && !w_done;
              end else begin
                  awvalid = !aw_done;
                  wvalid = !w_done;
              end
              default: ;
            endcase
        end
    end
    always_ff @(posedge clk) begin
        if (rst) begin
            index <= 0;
            aw_done <= 0;
            w_done <= 0;
            waiting_b <= 0;
        end else begin
            if (awvalid && awready) aw_done <= 1;
            if (wvalid && wready) w_done <= 1;
            if (aw_done && w_done) waiting_b <= 1;
            if (bvalid && bready) begin
                index <= index + 1;
                aw_done <= 0;
                w_done <= 0;
                waiting_b <= 0;
            end
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
async def verify_axi4_write_features(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.awready.value = 0
    dut.wready.value = 0
    dut.bvalid.value = 0
    dut.bresp.value = 0
    dut.bid.value = 0
    got_aw = False
    got_w = False
    pending_bid = None
    completed = 0
    for cycle in range(80):
        dut.rst.value = int(cycle < 2)
        dut.awready.value = int(cycle >= 2)
        dut.wready.value = int(cycle >= 2)
        dut.bvalid.value = int(pending_bid is not None and cycle >= 2)
        dut.bid.value = int(pending_bid or 0)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["bvalid"]) and int(snapshot["bready"]):
            pending_bid = None
            completed += 1
            got_aw = False
            got_w = False
        if int(snapshot["awvalid"]) and int(snapshot["awready"]):
            got_aw = True
            awid = int(snapshot["awid"])
        if int(snapshot["wvalid"]) and int(snapshot["wready"]):
            got_w = True
        if got_aw and got_w and pending_bid is None:
            pending_bid = awid
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed == 3:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed == 3, f"only {completed} writes completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for target in TARGETS:
        assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_BINS = {
    "sparse": "channel.w.axi4_write_strobe.sparse",
    "data_first": "protocol_group.bus.axi4_write_channel_order.data_first",
    "same_cycle": "protocol_group.bus.axi4_write_channel_order.same_cycle",
}


def _interface_with_ids() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [
        channel for channel in interface["channels"]
        if channel["name"] in {"aw", "w", "b"}
    ]
    interface["signals"] = [
        signal for signal in interface["signals"]
        if signal.get("channel") in {None, "aw", "w", "b"}
    ]
    for prefix, direction in (("aw", "output"), ("b", "input")):
        interface["signals"].append({
            "name": f"{prefix}id", "role": "transaction_id",
            "semantic_class": "identifier", "protocol_field": "id",
            "channel": prefix, "direction": direction, "width": "4",
        })
    interface["channels"][0]["protocol_capabilities"] = {"max_outstanding": 1}
    return interface


def _run(tmp_path, variant: str, targets: list[str]) -> dict:
    path = tmp_path / variant
    rtl = path / "rtl"
    tests = path / "tests"
    reference = path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flags = {
        "no_sparse": (1, 0, 0),
        "no_data_first": (0, 1, 0),
        "no_same_cycle": (0, 0, 1),
        "correct": (0, 0, 0),
    }[variant]
    (rtl / "axi4_write_feature_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_with_ids()))
    (tests / "test_axi4_write_features.py").write_text(source + _TB % json.dumps(targets))
    return run_cocotb_regression(
        rtl_dir=rtl,
        top_module="axi4_write_feature_source",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_axi4_write_features"],
        seed=3,
        build_dir=path / "build",
        report_path=path / "report.json",
        timeout_seconds=120,
    )


def test_axi4_write_feature_bins_have_real_rtl_fault_fix_pairs(tmp_path):
    for variant, feature in (
        ("no_sparse", "sparse"),
        ("no_data_first", "data_first"),
        ("no_same_cycle", "same_cycle"),
    ):
        target = _BINS[feature]
        bad = _run(tmp_path, variant, [target])
        assert bad["status"] == "SIMULATION_FAILURE", (variant, bad)
        assert target in bad["stdout"], (variant, bad["stdout"][-3000:])
    good = _run(tmp_path, "correct", [
        *_BINS.values(),
        "channel.w.axi4_write_strobe.all_zero",
        "channel.w.axi4_write_strobe.full",
        "protocol_group.bus.axi4_write_channel_order.address_first",
    ])
    assert good["status"] == "PASS", good
