"""Does `check_axi4_lite` enforce any AW/W arrival-order constraint? Reuses
the existing `test_axi_lite_write_standard_rule_rtl_feature.py` fixture (its
manager already issues AWVALID and WVALID fully independently -- neither
depends on the other), just driving AWREADY/WREADY at different times to
force address-first and data-first orderings.

Same reasoning and same POSITIVE_ONLY-only ceiling as the already-qualified
AXI4 sibling `rule:axi4.write_address_and_data_are_independent`: this rule
asserts the *absence* of an ordering constraint, so there is no adversarial
DUT behavior for a mutant to embody (no way to construct "the checker
wrongly imposed the constraint" as a failing case) -- both orderings simply
need to complete with zero assertion failures.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.rtl.test_axi_lite_write_standard_rule_rtl_feature import (
    _RTL,
    _interface_write_only,
)
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

MODE = %r

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check_order(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.awready.value = 0
    dut.wready.value = 0
    dut.bvalid.value = 0
    dut.bresp.value = 0
    completed = False
    for cycle in range(30):
        dut.rst.value = int(cycle < 2)
        if MODE == "address_first":
            dut.awready.value = int(cycle >= 2)
            dut.wready.value = int(cycle >= 5)
        else:
            dut.awready.value = int(cycle >= 5)
            dut.wready.value = int(cycle >= 2)
        dut.bvalid.value = int(cycle >= 8)
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_protocol_assertions)
        if int(snapshot["bvalid"]) and int(snapshot["bready"]):
            completed = True
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")
        if completed:
            break
    _finalize_contract_protocol_assertions()
    report = tracker.report()
    assert completed, "the single write never completed"
    assert report["assertion_failures"] == [], report["assertion_failures"]
    target = "protocol_group.bus.axi_lite_write_channel_order." + %r
    assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


def _run(tmp_path, mode: str) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_write_standard_rule_source.sv").write_text(_RTL)
    (reference / "model.py").write_text("")
    source = render_contract_generated_block(build_interface_coverage_plan(_interface_write_only()))
    bin_name = "address_first" if mode == "address_first" else "data_first"
    (tests / "test_order.py").write_text(source + _TB % (mode, bin_name))
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_write_standard_rule_source", tests_dir=tests,
        reference_dir=reference, test_modules=["test_order"], seed=5,
        build_dir=path / "build", report_path=path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_write_address_and_data_orders_are_both_legal(tmp_path):
    address_first = _run(tmp_path, "address_first")
    assert address_first["status"] == "PASS", address_first

    data_first = _run(tmp_path, "data_first")
    assert data_first["status"] == "PASS", data_first
