"""Real custom-MMIO RTL pair for accepted-address coverage.

The local fixture deliberately declares an 8-bit byte-addressable request
space, so the width maximum is a legal address in this one contract. This
does not prove arbitrary custom address-range semantics without explicit
range metadata.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module custom_address_source (
    input logic clk, rst, req_ready,
    output logic req_valid,
    output logic [7:0] req_addr
);
    localparam bit NO_MAX = %d;
    logic [2:0] index;
    assign req_valid = !rst && index < 4;
    always_comb begin
        case (index)
          0: req_addr = 8'd0;
          1: req_addr = 8'd4;
          2: req_addr = NO_MAX ? 8'd254 : 8'd255;
          3: req_addr = 8'd1;
          default: req_addr = 0;
        endcase
    end
    always_ff @(posedge clk) begin
        if (rst) index <= 0;
        else if (req_valid && req_ready) index <= index + 1;
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

@cocotb.test(timeout_time=20, timeout_unit="us")
async def check_accepted_addresses(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.req_ready.value = 0
    accepted = 0
    for cycle in range(12):
        dut.rst.value = int(cycle < 2)
        dut.req_ready.value = int(cycle >= 2)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        accepted += int(bool(snapshot["req_valid"]) and bool(snapshot["req_ready"]))
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert accepted == 4
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for name in ("minimum", "aligned_interior", "maximum", "boundary_neighbor"):
        target = "signal.req_addr.address_alignment." + name
        assert target in report["covered_bins"], f"missing required feature bin {target}"
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
             "semantic": "active-high reset"},
            {"name": "req_valid", "role": "valid", "direction": "output",
             "channel": "req", "width": "1"},
            {"name": "req_ready", "role": "ready", "direction": "input",
             "channel": "req", "width": "1"},
            {"name": "req_addr", "role": "payload", "semantic_class": "address",
             "protocol_field": "addr", "direction": "output", "channel": "req",
             "width": "8", "semantic": "8-bit byte-addressable range 0..255"},
        ],
    }


def _run(tmp_path, variant: str) -> dict:
    path = tmp_path / variant
    rtl = path / "rtl"
    tests = path / "tests"
    reference = path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "custom_address_source.sv").write_text(_RTL % int(variant == "no_max"))
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface()))
    (tests / "test_custom_address.py").write_text(source + _TB)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="custom_address_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_custom_address"], seed=1,
        build_dir=path / "build", report_path=path / "report.json",
        timeout_seconds=120,
    )


def test_generic_address_bin_uses_real_accepted_values_and_fault_fix_rtl(tmp_path):
    bad = _run(tmp_path, "no_max")
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "signal.req_addr.address_alignment.maximum" in bad["stdout"]
    good = _run(tmp_path, "correct")
    assert good["status"] == "PASS", good
