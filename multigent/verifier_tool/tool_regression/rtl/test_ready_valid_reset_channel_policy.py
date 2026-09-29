"""Generated-checker fault/fix proof for an explicit ready/valid reset policy."""

from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    build_interface_coverage_plan,
    build_protocol_stimulus_plan,
    render_contract_generated_block,
)


pytestmark = pytest.mark.skipif(
    shutil.which("verilator") is None, reason="Verilator not on PATH"
)


_RTL = """module ready_valid_reset_source (
    input logic clk, rst, ready,
    output logic valid,
    output logic [7:0] data
);
    localparam bit VALID_DURING_RESET = %d;
    logic pending;
    always_ff @(posedge clk) begin
        if (rst) pending <= 1'b0;
        else if (!pending) pending <= 1'b1;
        else if (ready) pending <= 1'b0;
    end
    assign valid = rst ? VALID_DURING_RESET : pending;
    assign data = 8'h2a;
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_ready_valid_reset_policy(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.ready.value = 0
    for cycle in range(8):
        dut.rst.value = int(cycle < 2)
        dut.ready.value = int(cycle >= 2)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_assertions)
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
    _finalize_contract_assertions()
"""


def _interface(*, policy: bool) -> dict:
    interface = {
        "clock": "clk",
        "reset": "rst",
        "channels": [
            {"name": "data", "direction": "output", "protocol_profile": "ready_valid"}
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {
                "name": "rst", "role": "reset", "direction": "input", "channel": None,
                "semantic": "synchronous active-high reset",
            },
            {"name": "valid", "role": "valid", "direction": "output", "channel": "data"},
            {"name": "ready", "role": "ready", "direction": "input", "channel": "data"},
            {
                "name": "data", "role": "payload", "semantic_class": "data",
                "direction": "output", "channel": "data", "width": "8",
            },
        ],
    }
    if policy:
        interface["reset_channel_policies"] = [
            {
                "channels": ["data"],
                "behavior": "valid_deasserted",
                "settle_cycles": 1,
            }
        ]
    return interface


def _run(tmp_path, name: str, *, faulty: bool, policy: bool) -> dict:
    root = tmp_path / name
    rtl, tests, reference = root / "rtl", root / "tests", root / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "ready_valid_reset_source.sv").write_text(_RTL % int(faulty))
    (reference / "model.py").write_text("")
    generated = render_contract_generated_block(
        build_interface_coverage_plan(_interface(policy=policy))
    )
    (tests / "test_ready_valid_reset.py").write_text(generated + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl,
        top_module="ready_valid_reset_source",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_ready_valid_reset"],
        seed=31,
        build_dir=root / "build",
        report_path=root / "report.json",
        timeout_seconds=120,
    )


def test_explicit_policy_catches_fault_and_fixed_rtl_passes(tmp_path):
    bad = _run(tmp_path, "bad", faulty=True, policy=True)
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "feature=channel.data.valid_low_during_reset" in bad["stdout"]

    good = _run(tmp_path, "good", faulty=False, policy=True)
    assert good["status"] == "PASS", good


def test_plain_ready_valid_makes_no_unstated_reset_assumption(tmp_path):
    result = _run(tmp_path, "unspecified", faulty=True, policy=False)
    assert result["status"] == "PASS", result
    plan = build_interface_coverage_plan(_interface(policy=False))["feature_plan"]
    assert not any(
        item["kind"] == "valid_low_during_reset" for item in plan["features"]
    )


def test_policy_reuses_reset_stimulus_strategy_and_existing_reset_sequence():
    plan = build_protocol_stimulus_plan(_interface(policy=True))
    entries = [
        item
        for item in plan["compiled_stimulus"]["entries"]
        if item["id"] == "channel.data.valid_low_during_reset"
    ]
    assert len(entries) == 1
    assert entries[0]["implementation"] == "reset_assert_release"
    assert any(item["kind"] == "reset_sequence" for item in plan["global_scenarios"])
