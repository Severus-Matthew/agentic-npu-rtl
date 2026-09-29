"""Runs the frozen `int8_gemm_hls_golden` benchmark contract against the REAL
Vitis HLS-generated RTL in `gemm_golden/` (source: `gemm_golden_hls/gemm_hls/
int8_gemm.cpp`) through real Verilator + cocotb -- the actual golden RTL this
whole session's packed_encoding/control_plane_sequence work was built for.
"""
from __future__ import annotations

import random
import shutil

import pytest
import yaml

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_lifecycle_assertion_plan,
    build_protocol_assertion_plan,
    evaluate_canonical_operation,
)
from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT, REPOSITORY_ROOT

GEMM_GOLDEN_RTL = REPOSITORY_ROOT / "gemm_golden"
BENCHMARK_DIR = BENCHMARKS_ROOT / "int8_gemm_hls_golden"

M, K, N = 32, 64, 128


def _load_metadata():
    architecture = yaml.safe_load((BENCHMARK_DIR / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((BENCHMARK_DIR / "interface_contract.yaml").read_text())
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == [], metadata["unrepresentable_operations"]
    return metadata["operations"][0], interface


def run_hls_gemm_case(tmp_path, mutation=None):
    """Run one real RTL variant through the same contract-bound cocotb case.

    A mutation is (relative Verilog path, exact source anchor, replacement).
    It is applied only to an isolated pytest temporary copy of the RTL.
    """

    operation, interface = _load_metadata()
    rtl_dir = GEMM_GOLDEN_RTL
    if mutation is not None:
        rtl_dir = tmp_path / "mutated_rtl"
        shutil.copytree(GEMM_GOLDEN_RTL, rtl_dir)
        relative_path, anchor, replacement = mutation
        target = rtl_dir / relative_path
        original = target.read_text()
        assert original.count(anchor) == 1
        target.write_text(original.replace(anchor, replacement, 1))

    metadata = {"schema_version": 2, "operations": [operation]}
    lifecycle_plan = build_lifecycle_assertion_plan(interface, metadata)
    protocol_plan = build_protocol_assertion_plan(interface)
    assert "completion_matches_final_output" in lifecycle_plan["enabled_by_operation"]["gemm"]

    rng = random.Random(7)
    a_flat = [rng.randint(-128, 127) for _ in range(M * K)]
    b_flat = [rng.randint(-128, 127) for _ in range(K * N)]
    stimulus = {"A_matrix": a_flat, "B_matrix": b_flat}
    expected = evaluate_canonical_operation(operation, stimulus)
    case = {"stimulus": stimulus, "expected": expected, "kind": "directed", "label": "real_rtl_smoke"}

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    ref_dir = tmp_path / "reference"
    ref_dir.mkdir()
    (ref_dir / "model.py").write_text("")

    fixture_path = tests_dir / "gemm_fixture.py"
    import pickle

    (tmp_path / "operation.pkl").write_bytes(pickle.dumps({
        "operation": operation, "interface": interface, "case": case,
        "lifecycle_plan": lifecycle_plan, "protocol_plan": protocol_plan,
    }))

    fixture_path.write_text(
        "import pickle\n"
        f"with open({str(tmp_path / 'operation.pkl')!r}, 'rb') as _f:\n"
        "    _payload = pickle.load(_f)\n"
        "operation = _payload['operation']\n"
        "interface = _payload['interface']\n"
        "case = _payload['case']\n"
        "lifecycle_plan = _payload['lifecycle_plan']\n"
        "protocol_plan = _payload['protocol_plan']\n"
    )

    test_code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer

from multigent.verifier_tool.orchestration import campaign
from multigent.verifier_tool.lifecycle.assertion.runtime import check_lifecycle_assertions
from multigent.verifier_tool.protocol.assertion.runtime import check_protocol_assertions
from multigent.verifier_tool.orchestration.runtime import capture_contract_snapshot
from gemm_fixture import interface, operation, case, lifecycle_plan, protocol_plan

captured = []

def _stub_record_stimulus(kind, stimulus, expected, label=None, operation_evidence=None,
                           operation_metadata=None, operations=(), observed=None):
    captured.append({"observed": dict(observed or {})})
    return f"stub-{len(captured)}"

def _stub_sample_operation(*args, **kwargs):
    return None

campaign.record_stimulus = _stub_record_stimulus
campaign.sample_operation = _stub_sample_operation

async def _monitor_contract(dut):
    lifecycle_state = {}
    protocol_state = {}
    signal_names = tuple(signal['name'] for signal in interface['signals'])
    while True:
        await FallingEdge(dut.ap_clk)
        await Timer(2, unit='ps')
        await ReadOnly()
        snapshot = capture_contract_snapshot(dut, signal_names)
        check_protocol_assertions(snapshot, protocol_plan, protocol_state)
        check_lifecycle_assertions(snapshot, lifecycle_plan, lifecycle_state)

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.ap_clk, 10, unit="ns").start())
    cocotb.start_soon(_monitor_contract(dut))
    await campaign.initialize_testbench_owned_signals(dut, interface)
    dut.ap_rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.ap_clk)
    dut.ap_rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.ap_clk)

    stimulus_id = await campaign.run_code_owned_axi4_operation_case_via_control_plane_sequence(
        dut, interface, operation, case, timeout_cycles=2_000_000,
    )
    assert stimulus_id is not None
    assert len(captured) == 1, captured

    expected_y = case["expected"]["Y_matrix"]
    observed_y = captured[0]["observed"]["Y_matrix"]
    assert observed_y == expected_y, (
        f"mismatch at first diff index "
        f"{next((i for i, (a, b) in enumerate(zip(observed_y, expected_y)) if a != b), None)}"
    )
'''
    (tests_dir / "test_check.py").write_text(test_code)

    result = run_cocotb_regression(
        rtl_dir=rtl_dir, top_module="int8_gemm", tests_dir=tests_dir, reference_dir=ref_dir,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=580,
    )
    return result


@pytest.mark.skipif(not GEMM_GOLDEN_RTL.is_dir(), reason="real gemm_golden RTL not present")
@pytest.mark.parametrize("premature_done", [False, True], ids=["golden", "early_ap_done_mutant"])
def test_int8_gemm_hls_golden_campaign_matches_real_rtl(tmp_path, premature_done):
    mutation = (
        "int8_gemm_control_s_axi.v",
        "rdata[1] <= int_task_ap_done;",
        "rdata[1] <= 1'b1;",
    ) if premature_done else None
    result = run_hls_gemm_case(tmp_path, mutation)
    if premature_done:
        assert result["status"] == "SIMULATION_FAILURE", result
        assert "feature=lifecycle.gemm.completion_matches_final_output" in result["stdout"], result
        assert "before final output retirement" in result["stdout"], result
    else:
        assert result["status"] == "PASS", result
