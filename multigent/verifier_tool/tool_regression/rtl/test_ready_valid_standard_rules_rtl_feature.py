"""Generated-checker RTL tests for the plain `ready_valid` protocol profile.

A generic ready/valid handshake guarantees transfer stability but does not
define reset behavior. Designs that require VALID low during reset opt in via
``interface_contract.reset_channel_policies``; that path is qualified in
``test_ready_valid_reset_channel_policy.py``. Per IMPLEMENTATION_MAP.md,
`ready_valid_stability`
has no dedicated `_fail` literal of its own name -- it is enforced
structurally by `check_stall_stability` under the `channel.<name>.
stall_stability` diagnostic id, so that is the string this test matches on.

A single-channel producer RTL (valid/ready/data, no burst/response
semantics -- the whole point of the plain `ready_valid` profile) with two
independent single-fault flags: `WITHDRAW_WHEN_STALLED` drops VALID before
an accept while backpressured (the exact "valid was withdrawn before a
stalled transfer completed" violation), and `VALID_DURING_RESET` asserts
VALID while reset is active.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module ready_valid_stability_source (
    input logic clk, rst, ready,
    output logic valid,
    output logic [7:0] data
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
        end else if (ready) begin
            pending <= 1'b0;
            counter <= counter + 1'b1;
        end else begin
            stall_count <= stall_count + 1'b1;
            if (WITHDRAW_WHEN_STALLED && stall_count == 2) pending <= 1'b0;
        end
    end
    assign valid = rst ? VALID_DURING_RESET : pending;
    assign data = counter;
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

BACKPRESSURE_CYCLES = %d

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_ready_valid_standard_rules(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.ready.value = 0
    transfers = 0
    for cycle in range(60):
        dut.rst.value = int(cycle < 2)
        dut.ready.value = int(cycle >= (2 + BACKPRESSURE_CYCLES))
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_assertions)
        if int(snapshot["valid"]) and int(snapshot["ready"]):
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


_RULES = {
    "withdraw_when_stalled": "channel.data.stall_stability",
    "valid_during_reset": "protocol.data.valid_low_during_reset",
}


def _interface() -> dict:
    return {
        "clock": "clk",
        "reset": "rst",
        "channels": [
            {"name": "data", "direction": "output", "protocol_profile": "ready_valid"},
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {"name": "rst", "role": "reset", "direction": "input", "channel": None,
             "semantic": "synchronous active-high reset"},
            {"name": "valid", "role": "valid", "direction": "output", "channel": "data"},
            {"name": "ready", "role": "ready", "direction": "input", "channel": "data"},
            {"name": "data", "role": "payload", "semantic_class": "data", "direction": "output",
             "channel": "data", "width": "8"},
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
    (rtl / "ready_valid_stability_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface()))
    (tests / "test_ready_valid_standard_rules.py").write_text(source + _TB % backpressure)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="ready_valid_stability_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_ready_valid_standard_rules"], seed=19,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_ready_valid_standard_rule_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "withdraw_when_stalled")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _RULES["withdraw_when_stalled"] in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good


def test_plain_ready_valid_makes_no_undeclared_reset_assumption(tmp_path):
    """Without an explicit reset-channel policy, VALID reset state is unspecified."""
    result = _run(tmp_path, "valid_during_reset")
    assert result["status"] == "PASS", result
