"""Real-RTL, contract-generated AXI4 read-feature fault/fix pairs.

This intentionally isolates bus semantics from any GEMM arithmetic. A small
manager issues complete, legal read bursts; the TB returns exactly the
accepted number of beats with matching RID/RLAST. The frozen interface drives
the same generated assertion/coverage logic for each faulty/corrected pair.
"""

from __future__ import annotations

import json
import shutil

import pytest

from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi4_read_feature_source (
    input logic clk, rst, arready,
    output logic arvalid, rready,
    output logic [31:0] araddr,
    output logic [7:0] arlen,
    output logic [2:0] arsize,
    output logic [1:0] arburst,
    output logic [3:0] arid,
    input logic rvalid, rlast,
    input logic [31:0] rdata,
    input logic [1:0] rresp,
    input logic [3:0] rid
);
    localparam bit ONLY_INCR = %d;
    localparam bit ONLY_SINGLE = %d;
    localparam bit ONLY_FULL = %d;
    localparam bit ONLY_ALIGNED = %d;
    localparam bit NO_BOUNDARY = %d;
    localparam bit NO_ERROR_REQUEST = %d;
    localparam bit ZERO_ID = %d;
    logic [3:0] index;
    logic waiting;
    assign arvalid = !rst && index < 8 && !waiting;
    assign rready = !rst && waiting;
    assign arid = ZERO_ID ? 4'd0 : {3'd0, index[0]};
    always_comb begin
        araddr = 32'h1000;
        arlen = 0;
        arsize = 2;
        arburst = 1;
        case (index)
          0: begin araddr=32'h1000; arlen=0;  arsize=2; arburst=1; end
          1: begin araddr=32'h0020; arlen=3;  arsize=2; arburst=0; end
          2: begin araddr=32'h0040; arlen=3;  arsize=2; arburst=2; end
          3: begin araddr=32'h0800; arlen=16; arsize=0; arburst=1; end
          4: begin araddr=32'h0880; arlen=3;  arsize=1; arburst=1; end
          5: begin araddr=ONLY_ALIGNED ? 32'h0900 : 32'h0901;
                   arlen=3; arsize=2; arburst=1; end
          6: begin araddr=NO_BOUNDARY ? 32'h0ff8 : 32'h0ffc;
                   arlen=0; arsize=2; arburst=1; end
          7: begin araddr=NO_ERROR_REQUEST ? 32'h0d04 : 32'h0d00;
                   arlen=0; arsize=2; arburst=1; end
          default: ;
        endcase
        if (ONLY_INCR) arburst = 1;
        if (ONLY_SINGLE) begin arlen = 0; arburst = 1; end
        if (ONLY_FULL) arsize = 2;
    end
    always_ff @(posedge clk) begin
        if (rst) begin index <= 0; waiting <= 0; end
        else if (arvalid && arready) waiting <= 1;
        else if (rvalid && rready && rlast) begin
            waiting <= 0;
            index <= index + 1;
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
async def verify_axi4_read_features(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.arready.value = 0
    dut.rvalid.value = 0
    dut.rdata.value = 0
    dut.rresp.value = 0
    dut.rlast.value = 0
    dut.rid.value = 0
    pending = None
    completed = 0
    for cycle in range(200):
        dut.rst.value = int(cycle < 2)
        dut.arready.value = int(cycle >= 2)
        if pending is not None and cycle >= 2:
            dut.rvalid.value = 1
            dut.rlast.value = int(pending["remaining"] == 1)
            dut.rdata.value = pending["remaining"]
            dut.rresp.value = 2 if pending["addr"] == 0xD00 else 0
            dut.rid.value = pending["id"]
        else:
            dut.rvalid.value = 0
            dut.rlast.value = 0
            dut.rresp.value = 0
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["rvalid"]) and int(snapshot["rready"]):
            pending["remaining"] -= 1
            if pending["remaining"] == 0:
                completed += 1
                pending = None
        if int(snapshot["arvalid"]) and int(snapshot["arready"]):
            assert pending is None
            pending = {
                "addr": int(snapshot["araddr"]),
                "remaining": int(snapshot["arlen"]) + 1,
                "id": int(snapshot["arid"]),
            }
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed == 8:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed == 8, f"only {completed} bursts completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for target in TARGETS:
        assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_FEATURE_BINS = {
    "boundary": "channel.ar.axi4_4k_boundary.ends_at_boundary",
    "burst": "channel.ar.axi4_burst_type.wrapping",
    "length": "channel.ar.axi4_burst_length.seventeen_to_256",
    "size": "channel.ar.axi4_transfer_size.one_byte",
    "alignment": "channel.ar.axi4_alignment.unaligned",
    "response": "channel.r.axi4_response_code.slverr",
    "sideband": "protocol_field.bus_read_address_id.axi4_sideband_partition.nonzero",
}


def _interface_with_ids() -> dict:
    interface = _interface("axi4")
    interface["channels"] = [
        channel for channel in interface["channels"]
        if channel["name"] in {"ar", "r"}
    ]
    interface["signals"] = [
        signal for signal in interface["signals"]
        if signal.get("channel") in {None, "ar", "r"}
    ]
    for prefix, direction in (("ar", "output"), ("r", "input")):
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
        "only_incr": (1, 0, 0, 0, 0, 0, 0),
        "only_single": (0, 1, 0, 0, 0, 0, 0),
        "only_full": (0, 0, 1, 0, 0, 0, 0),
        "only_aligned": (0, 0, 0, 1, 0, 0, 0),
        "no_boundary": (0, 0, 0, 0, 1, 0, 0),
        "no_error_request": (0, 0, 0, 0, 0, 1, 0),
        "zero_id": (0, 0, 0, 0, 0, 0, 1),
        "correct": (0, 0, 0, 0, 0, 0, 0),
    }[variant]
    (rtl / "axi4_read_feature_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(
        build_interface_coverage_plan(_interface_with_ids())
    )
    (tests / "test_axi4_read_features.py").write_text(source + _TB % json.dumps(targets))
    return run_cocotb_regression(
        rtl_dir=rtl,
        top_module="axi4_read_feature_source",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_axi4_read_features"],
        seed=7,
        build_dir=path / "build",
        report_path=path / "report.json",
        timeout_seconds=120,
    )


def test_axi4_read_feature_bins_have_real_rtl_fault_fix_pairs(tmp_path):
    pairs = (
        ("no_boundary", "boundary"),
        ("only_incr", "burst"),
        ("only_single", "length"),
        ("only_full", "size"),
        ("only_aligned", "alignment"),
        ("no_error_request", "response"),
        ("zero_id", "sideband"),
    )
    for variant, feature in pairs:
        target = _FEATURE_BINS[feature]
        bad = _run(tmp_path, variant, [target])
        assert bad["status"] == "SIMULATION_FAILURE", (variant, bad)
        assert target in bad["stdout"], (variant, bad["stdout"][-3000:])
    good = _run(tmp_path, "correct", [
        *_FEATURE_BINS.values(),
        "channel.ar.axi4_burst_type.fixed",
        "channel.ar.axi4_burst_type.incrementing",
        "channel.ar.axi4_burst_length.single",
        "channel.ar.axi4_burst_length.two_to_sixteen",
        "channel.ar.axi4_transfer_size.narrow",
        "channel.ar.axi4_transfer_size.full_width",
        "channel.ar.axi4_alignment.aligned",
        "channel.ar.axi4_4k_boundary.ends_before_boundary",
        "channel.r.axi4_response_code.okay",
        "protocol_field.bus_read_address_id.axi4_sideband_partition.zero",
    ])
    assert good["status"] == "PASS", good
