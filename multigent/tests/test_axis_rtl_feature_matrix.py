"""Frozen AXI4-Stream feature plan against six real, isolated RTL variants.

The TB embeds the contract-generated checker block, observes actual DUT
signals, and credits only real accepted transfers. Faulty variants must miss
their own named bin (or trip the named checker); the same contract and stimulus
must pass against the corrected RTL. This is protocol qualification, not an
operation/golden-model campaign.
"""

from __future__ import annotations

import json
import shutil

import pytest

from multigent.tests.test_standard_axi_protocols import _interface
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axis_feature_source (
    input logic clk, rst, tready,
    output logic tvalid, tlast,
    output logic [31:0] tdata,
    output logic [3:0] tstrb, tkeep, tuser,
    output logic [1:0] tid, tdest
);
    localparam bit NO_MULTI = %d;
    localparam bit NO_PARTIAL = %d;
    localparam bit NO_GAP = %d;
    localparam bit NO_NONZERO = %d;
    localparam bit UNSTABLE_STALL = %d;
    localparam bit BAD_STRB = %d;
    localparam bit READY_GATED_VALID = %d;
    logic [2:0] beat;
    logic gap;
    logic [3:0] stall_bump;
    assign tvalid = !rst && beat < 6 && !gap && (!READY_GATED_VALID || tready);
    assign tlast = NO_MULTI || beat == 0 || beat == 3 || beat == 4 || beat == 5;
    assign tkeep = (!NO_PARTIAL && beat == 3) ? 4'b0011 : 4'b1111;
    assign tstrb = BAD_STRB ? 4'b1111 : tkeep;
    assign tdata = 32'(beat + 1) + (UNSTABLE_STALL ? 32'(stall_bump) : 32'd0);
    assign tid = (!NO_NONZERO && beat >= 1) ? 2'd1 : 2'd0;
    assign tdest = tid;
    assign tuser = {2'b0, tid};
    always_ff @(posedge clk) begin
        if (rst) begin
            beat <= 0;
            gap <= 0;
            stall_bump <= 0;
        end else if (gap) begin
            gap <= 0;
        end else if (tvalid && tready) begin
            if (beat == 4 && !NO_GAP) gap <= 1;
            beat <= beat + 1;
            stall_bump <= 0;
        end else if (tvalid && !tready && UNSTABLE_STALL) begin
            stall_bump <= stall_bump + 1;
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
async def verify_stream_features(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.tready.value = 0
    accepted = 0
    stalled = 0
    quotas = {1: 3, 2: 6, 3: 1}
    for cycle in range(80):
        dut.rst.value = int(cycle < 2)
        if cycle < 2:
            ready = 0
        else:
            ready = int(stalled >= quotas.get(accepted, 0))
        dut.tready.value = ready
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if cycle >= 2 and not ready:
            stalled += 1
        if cycle >= 2 and int(snapshot["tvalid"]) and ready:
            accepted += 1
            stalled = 0
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if accepted == 6 and cycle > 8:
            dut.tready.value = 0
            await Timer(1, unit="ns")
            snapshot = capture_contract_snapshot(dut, tracker.signal_names)
            tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
            break
    report = tracker.report()
    assert accepted == 6, f"stream ended after {accepted} accepted beats"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for target in TARGETS:
        assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_FEATURE_BINS = {
    "packet_length": "channel.t.axis_packet_length.multi_beat",
    "keep_pattern": "channel.t.axis_keep_pattern.partial",
    "stall_position": "channel.t.axis_stall_position.last_beat",
    "packet_spacing": "channel.t.axis_back_to_back_packets.with_gap",
    "sideband": "protocol_field.bus_stream_id.axis_sideband_partition.nonzero",
}


def _run(tmp_path, variant: str, targets: list[str]) -> dict:
    path = tmp_path / variant
    rtl = path / "rtl"
    tests = path / "tests"
    reference = path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flags = {
        "no_multi": (1, 0, 0, 0, 0, 0, 0),
        "no_partial": (0, 1, 0, 0, 0, 0, 0),
        "no_gap": (0, 0, 1, 0, 0, 0, 0),
        "no_nonzero": (0, 0, 0, 1, 0, 0, 0),
        "unstable_stall": (0, 0, 0, 0, 1, 0, 0),
        "bad_strb": (0, 0, 0, 0, 0, 1, 0),
        "ready_gated_valid": (0, 0, 0, 0, 0, 0, 1),
        "correct": (0, 0, 0, 0, 0, 0, 0),
    }[variant]
    (rtl / "axis_feature_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    interface = _interface("axi4_stream")
    source = render_contract_generated_block(build_interface_coverage_plan(interface))
    (tests / "test_axis_features.py").write_text(
        source + _TB % json.dumps(targets)
    )
    return run_cocotb_regression(
        rtl_dir=rtl,
        top_module="axis_feature_source",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_axis_features"],
        seed=5,
        build_dir=path / "build",
        report_path=path / "report.json",
        timeout_seconds=120,
    )


def test_axis_five_feature_bins_reject_faulty_rtl_and_accept_corrected_rtl(tmp_path):
    for variant, feature in (
        ("no_multi", "packet_length"),
        ("no_partial", "keep_pattern"),
        ("no_gap", "packet_spacing"),
        ("no_nonzero", "sideband"),
    ):
        target = _FEATURE_BINS[feature]
        bad = _run(tmp_path, variant, [target])
        assert bad["status"] == "SIMULATION_FAILURE", (variant, bad)
        assert target in bad["stdout"], (variant, bad["stdout"][-3000:])
    good = _run(tmp_path, "correct", [
        *_FEATURE_BINS.values(),
        "channel.t.axis_packet_length.single_beat",
        "channel.t.axis_keep_pattern.full",
        "channel.t.axis_stall_position.first_beat",
        "channel.t.axis_stall_position.middle_beat",
        "channel.t.axis_back_to_back_packets.no_gap",
        "protocol_field.bus_stream_id.axis_sideband_partition.zero",
        "channel.t.handshake_states.idle",
        "channel.t.handshake_states.receiver_ready",
        "channel.t.handshake_states.backpressured",
        "channel.t.handshake_states.transfer",
        "channel.t.handshake_arrival_order.simultaneous",
        "channel.t.handshake_arrival_order.valid_before_ready",
        "channel.t.handshake_arrival_order.ready_before_valid",
    ])
    assert good["status"] == "PASS", good


def test_axis_stalled_content_fault_is_rejected_by_generated_checker(tmp_path):
    bad = _run(tmp_path, "unstable_stall", [_FEATURE_BINS["stall_position"]])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "channel.t.stall_stability" in bad["stdout"], bad["stdout"][-3000:]


def test_axis_standard_protocol_rule_rejects_strobe_outside_keep(tmp_path):
    bad = _run(tmp_path, "bad_strb", [_FEATURE_BINS["keep_pattern"]])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "protocol.bus.strobe_is_subset_of_keep" in bad["stdout"], bad["stdout"][-3000:]
    good = _run(tmp_path, "correct", [_FEATURE_BINS["keep_pattern"]])
    assert good["status"] == "PASS", good


def test_ready_gated_valid_misses_handshake_state_and_arrival_order(tmp_path):
    targets = [
        "channel.t.handshake_states.backpressured",
        "channel.t.handshake_arrival_order.valid_before_ready",
    ]
    bad = _run(tmp_path, "ready_gated_valid", targets)
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert any(target in bad["stdout"] for target in targets), bad["stdout"][-3000:]
    good = _run(tmp_path, "correct", targets)
    assert good["status"] == "PASS", good
