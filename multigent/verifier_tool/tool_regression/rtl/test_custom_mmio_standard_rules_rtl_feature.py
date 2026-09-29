"""Paired generated-checker RTL tests for the `custom_mmio` protocol
profile's two standard rules: `ready_valid_stability` and
`valid_low_during_reset`. Unlike the plain `ready_valid` profile,
`custom_mmio` is a member of `STANDARD_PROFILES`, so
both rules go through the normal protocol_group compilation path and are
both reachable here.

Same fault shapes as test_ready_valid_standard_rules_rtl_feature.py's
producer RTL (a single custom_mmio request channel): WITHDRAW_WHEN_STALLED
drops VALID before an accept while backpressured; VALID_DURING_RESET
asserts VALID while reset is active.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module custom_mmio_standard_rule_source (
    input logic clk, rst, req_ready,
    output logic req_valid,
    output logic [7:0] req_addr
);
    localparam bit WITHDRAW_WHEN_STALLED = %d;
    localparam bit VALID_DURING_RESET = %d;
    logic pending;
    logic [3:0] stall_count;
    logic [7:0] counter;

    always_ff @(posedge clk) begin
        if (rst) begin
            pending <= 1'b0;
            stall_count <= 0;
            counter <= 0;
        end else if (!pending) begin
            pending <= 1'b1;
            stall_count <= 0;
        end else if (req_ready) begin
            pending <= 1'b0;
            counter <= counter + 1'b1;
        end else begin
            stall_count <= stall_count + 1'b1;
            if (WITHDRAW_WHEN_STALLED && stall_count == 2) pending <= 1'b0;
        end
    end
    assign req_valid = rst ? VALID_DURING_RESET : pending;
    assign req_addr = counter;
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

BACKPRESSURE_CYCLES = %d

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_custom_mmio_standard_rules(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.req_ready.value = 0
    transfers = 0
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.req_ready.value = int(cycle >= (2 + BACKPRESSURE_CYCLES))
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_assertions)
        if int(snapshot["req_valid"]) and int(snapshot["req_ready"]):
            transfers += 1
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if transfers >= 3:
            break
    _finalize_contract_assertions()
    report = tracker.report()
    assert transfers >= 1, "producer never completed a single transfer"
    assert report["assertion_failures"] == [], report["assertion_failures"]
"""


def _interface() -> dict:
    return {
        "clock": "clk", "reset": "rst",
        "channels": [{
            "name": "req", "direction": "output", "protocol_profile": "custom_mmio",
            "protocol_group": "mem", "protocol_channel": "request",
            "data_objects": [], "ordering": "one accepted request at a time",
            "framing": "one beat", "metadata": [],
        }],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {"name": "rst", "role": "reset", "direction": "input", "channel": None,
             "semantic": "synchronous active-high reset"},
            {"name": "req_valid", "role": "valid", "direction": "output", "channel": "req"},
            {"name": "req_ready", "role": "ready", "direction": "input", "channel": "req"},
            {"name": "req_addr", "role": "payload", "semantic_class": "address",
             "protocol_field": "addr", "direction": "output", "channel": "req",
             "width": "8", "semantic": "8-bit byte-addressable range 0..255"},
        ],
    }


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flags, backpressure = {
        "withdraw_when_stalled": ((1, 0), 4),
        "valid_during_reset": ((0, 1), 0),
        "correct": ((0, 0), 3),
    }[variant]
    (rtl / "custom_mmio_standard_rule_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface()))
    (tests / "test_custom_mmio_standard_rules.py").write_text(source + _TB % backpressure)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="custom_mmio_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_custom_mmio_standard_rules"], seed=43,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_custom_mmio_standard_rule_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "withdraw_when_stalled")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "channel.req.stall_stability" in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "valid_during_reset")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "valid_low_during_reset" in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
