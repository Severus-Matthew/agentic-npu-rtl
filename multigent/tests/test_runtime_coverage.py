from __future__ import annotations

import json
import shutil

import pytest

from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan
from multigent.verifier_tool.coverage.runtime import (
    CoverageRuntimeError,
    InterfaceCoverageTracker,
    capture_contract_snapshot,
)
from multigent.verifier_tool.predefined_assertion.instrumentation import (
    install_contract_generated_block,
    render_contract_generated_block,
)
from multigent.verifier_tool.coverage.stimulus import (
    rebuild_stimulus_history,
    verifier_stimulus_history_view,
)
from multigent.tools.cocotb_runner import evaluate_functional_coverage_report
from multigent.tools.cocotb_runner import run_cocotb_regression


class _Signal:
    def __init__(self, value: int = 0, width: int | None = None) -> None:
        self.value = value
        self.width = width

    def __len__(self) -> int:
        if self.width is None:
            raise TypeError("test signal has no elaborated width")
        return self.width


class _Dut:
    def __init__(self) -> None:
        for name in ("clk", "rst", "v", "r", "p", "done", "err"):
            setattr(self, name, _Signal())


def _plan() -> dict:
    interface = {
        "clock": "clk",
        "reset": "rst",
        "channels": [
            {"name": "req", "direction": "input", "protocol_profile": "ready_valid"}
        ],
        "signals": [
            {"name": "clk", "role": "clock", "channel": None, "semantic": "clock"},
            {"name": "rst", "role": "reset", "channel": None, "semantic": "active-high reset"},
            {"name": "v", "role": "valid", "channel": "req"},
            {"name": "r", "role": "ready", "channel": "req"},
            {"name": "p", "role": "payload", "semantic_class": "data", "channel": "req"},
            {"name": "done", "role": "completion", "channel": None},
            {"name": "err", "role": "error", "channel": None},
        ],
    }
    return build_interface_coverage_plan(interface)


def _sample(tracker: InterfaceCoverageTracker, dut: _Dut, **values: int) -> None:
    for name, value in values.items():
        getattr(dut, name).value = value
    namespace = getattr(tracker, "_test_protocol_namespace", None)
    if namespace is None:
        namespace = {}
        exec(render_contract_generated_block(tracker.plan), namespace)
        tracker._test_protocol_namespace = namespace
    tracker.sample_snapshot(
        capture_contract_snapshot(dut, tracker.signal_names),
        namespace["_check_contract_protocol_assertions"],
    )


def _observe_reset(tracker: InterfaceCoverageTracker, dut: _Dut) -> None:
    namespace = tracker._test_protocol_namespace
    tracker.observe_reset_snapshot(
        capture_contract_snapshot(dut, ("rst",)),
        namespace["_check_contract_protocol_assertions"],
    )


def test_runtime_tracker_closes_required_interface_bins(tmp_path) -> None:
    plan = _plan()
    report_path = tmp_path / "coverage.json"
    tracker = InterfaceCoverageTracker(plan, report_path)
    dut = _Dut()

    _sample(tracker, dut, rst=1, v=0, r=0, p=3, done=0, err=0)
    _sample(tracker, dut, rst=0, v=0, r=1)
    _sample(tracker, dut, v=1, r=1)

    for stall_length in (1, 2, 5):
        for _ in range(stall_length):
            _sample(tracker, dut, v=1, r=0, p=11)
        _sample(tracker, dut, v=1, r=1, p=11)

    _sample(tracker, dut, v=0, r=0, done=1, err=1)
    _sample(tracker, dut, done=0, err=0)
    _sample(tracker, dut, done=1)
    tracker.close()

    report = tracker.report()
    assert report["status"] == "PASS"
    assert report["coverage_engine"] == "cocotb-coverage"
    handshake_model = next(
        item
        for item in report["coverage_model"]
        if item["obligation_id"] == "channel.req.handshake_states"
    )
    assert handshake_model["covercross"].endswith(".valid_x_ready")
    assert len(handshake_model["coverpoints"]) == 2
    standard_yaml = report_path.with_suffix(".cocotb-coverage.yml")
    assert standard_yaml.is_file()
    standard_coverage = standard_yaml.read_text(encoding="utf-8")
    assert "signal.rst.reset_behavior" in standard_coverage
    assert "valid_x_ready" in standard_coverage
    assert "CoverCross" in standard_coverage
    config_path = tmp_path / "plan.json"
    config_path.write_text(json.dumps(plan), encoding="utf-8")
    evaluated = evaluate_functional_coverage_report(report_path, config_path)
    assert evaluated["status"] == "PASS"
    assert evaluated["coverage_percent"] == 100.0
    assert set(evaluated["covered_bins"]) == set(evaluated["bin_hits"])
    assert evaluated["missing_bins"] == []


def test_runtime_tracker_asserts_stalled_payload_stability() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()
    _sample(tracker, dut, v=1, r=0, p=1)
    with pytest.raises(CoverageRuntimeError, match="content changed"):
        _sample(tracker, dut, v=1, r=0, p=2)


def test_runtime_tracker_asserts_valid_is_held_until_transfer() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()
    _sample(tracker, dut, v=1, r=0, p=9)
    with pytest.raises(CoverageRuntimeError, match="valid was withdrawn"):
        _sample(tracker, dut, v=0, r=0, p=9)


def test_runtime_tracker_allows_idle_and_post_handshake_valid_clear() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()
    for _ in range(3):
        _sample(tracker, dut, v=0, r=0, p=0)
    _sample(tracker, dut, v=1, r=0, p=9)
    _sample(tracker, dut, v=1, r=1, p=9)
    _sample(tracker, dut, v=0, r=1, p=0)
    assert tracker.assertion_failures == []


def test_runtime_tracker_does_not_leak_temporal_state_between_tests() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()

    tracker.begin_test()
    _sample(tracker, dut, v=1, r=0, p=9)
    tracker.end_test()
    tracker._test_protocol_namespace["_CONTRACT_PROTOCOL_STATE"].clear()

    tracker.begin_test()
    # A new independently reset cocotb test may start with valid low.  This must
    # not be interpreted as dropping the previous test's stalled transfer.
    _sample(tracker, dut, v=0, r=0, p=0)
    assert tracker.assertion_failures == []


def test_runtime_tracker_disables_stall_assertions_during_reset_abort() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()

    _sample(tracker, dut, rst=0, v=1, r=0, p=9)
    _sample(tracker, dut, rst=1, v=0, r=0, p=0)
    _sample(tracker, dut, rst=0, v=0, r=0, p=0)

    assert tracker.assertion_failures == []
    assert tracker.report()["stall_lengths_observed"] == {}


def test_address_coverage_uses_elaborated_width_for_symbolic_contract_width() -> None:
    plan = {
        "obligations": [
            {
                "id": "signal.addr.address_alignment",
                "template": "address_alignment",
                "bindings": {
                    "signal": "addr",
                    "width": "((DEPTH <= 1) ? 1 : $clog2(DEPTH))",
                },
                "bins": [
                    {"name": name}
                    for name in (
                        "minimum",
                        "aligned_interior",
                        "maximum",
                        "boundary_neighbor",
                    )
                ],
            }
        ]
    }
    tracker = InterfaceCoverageTracker(plan)
    dut = _Dut()
    dut.addr = _Signal(3, width=2)

    _sample(tracker, dut)

    report = tracker.report()
    assert "signal.addr.address_alignment.maximum" in report["covered_bins"]


def test_reset_at_active_edge_cancels_stall_even_if_half_cycle_misses_it() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()
    _sample(tracker, dut, rst=0, v=1, r=0, p=9)
    # Reset asserted after falling sample, active at rising, released before next
    # falling sample. This is a legal synchronous one-edge reset.
    dut.rst.value = 1
    _observe_reset(tracker, dut)
    _sample(tracker, dut, rst=0, v=0, r=0, p=0)
    assert tracker.assertion_failures == []
    assert tracker.report()["stall_lengths_observed"] == {}


def test_inactive_reset_edge_does_not_hide_real_valid_withdrawal() -> None:
    tracker = InterfaceCoverageTracker(_plan())
    dut = _Dut()
    _sample(tracker, dut, rst=0, v=1, r=0, p=9)
    _observe_reset(tracker, dut)
    with pytest.raises(CoverageRuntimeError, match="valid was withdrawn"):
        _sample(tracker, dut, v=0, r=0)


def test_missing_runtime_report_is_coverage_failure(tmp_path) -> None:
    config_path = tmp_path / "plan.json"
    config_path.write_text(json.dumps(_plan()), encoding="utf-8")
    result = evaluate_functional_coverage_report(
        tmp_path / "missing.json", config_path
    )
    assert result["status"] == "FAIL"
    assert result["missing_bins"] == ["runtime_report_missing"]
    assert result["covered_bins"] == []


def test_stimulus_ledger_links_exact_payload_to_operation_bins(tmp_path) -> None:
    plan = {
        "schema_version": 2,
        "monitor": {"clock": "clk", "reset": "rst", "signals": ["n"]},
        "requirements": {"randomized_transactions_minimum": 1},
        "obligations": [
            {
                "id": "operation.vector_add.length",
                "template": "operation_coverpoint",
                "bindings": {
                    "operation_name": "vector_add",
                    "field": "length",
                    "sampling": {"template": "custom", "observer": "observe_length", "event": "clock",
                                 "channel": {}, "guards": [], "field_types": {},
                                 "fields": {"length": {"signal": "n", "lsb": 0, "width": 3, "declared_width": 3}}},
                },
                "bins": [
                    {
                        "name": "four",
                        "predicate": {"op": "eq", "args": [4]},
                    }
                ],
            }
        ],
    }
    ledger_path = tmp_path / "stimulus-ledger-run1.json"
    tracker = InterfaceCoverageTracker(
        plan, tmp_path / "coverage.json", ledger_path
    )
    tracker.begin_test("test_vector_add")
    from types import SimpleNamespace
    tracker.operation_monitor.bind_observers({
        "OPERATION_SAMPLING_BINDINGS": [{"operation": "vector_add", "point": "length", "template": "custom"}],
        "observe_length": lambda values, state: values["length"],
    })
    snapshot = capture_contract_snapshot(
        SimpleNamespace(n=SimpleNamespace(value=4)), tracker.signal_names
    )
    tracker.sample_snapshot(snapshot, None)
    stimulus_id = tracker.record_stimulus(
        "randomized",
        {"lhs": [1, -2, 3, 4], "rhs": [5, 6, -7, 8], "length": 4},
        {"result": [6, 4, -4, 12]},
        label="mixed_signs",
    )
    tracker.sample_operation(
        "vector_add", {"length": 4}, "randomized", stimulus_id
    )
    tracker.close()

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["stimulus_count"] == 1
    assert ledger["records"][0]["stimulus"]["lhs"] == [1, -2, 3, 4]
    assert ledger["records"][0]["expected"]["result"] == [6, 4, -4, 12]
    assert ledger["records"][0]["operation_samples"][0]["matched_bins"] == []
    assert ledger["records"][0]["covered_bins"] == ["operation.vector_add.length.four"]
    report = tracker.report()
    assert report["status"] == "PASS"
    assert report["randomized_transactions_observed"] == 1
    assert report["covered_bins"] == ["operation.vector_add.length.four"]
    operation_model = report["coverage_model"][0]
    assert operation_model["template"] == "operation_coverpoint"
    assert operation_model["sample_field"] == "length"
    assert operation_model["predicate_bins"] == ["four"]


def test_cumulative_history_preserves_every_run_but_prompt_is_summary_only(tmp_path) -> None:
    verification = tmp_path / "verification"
    verification.mkdir()
    for tag, value in (("a", 1), ("b", 2)):
        (verification / f"stimulus-ledger-{tag}.json").write_text(
            json.dumps(
                {
                    "seed": value,
                    "records": [
                        {
                            "id": "case:000001",
                            "digest": str(value),
                            "kind": "directed",
                            "stimulus": {"x": value},
                            "expected": {"y": value},
                            "covered_bins": [f"op.bin{value}"],
                            "operation_samples": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    history = rebuild_stimulus_history(verification)
    assert history["run_count"] == 2
    assert [item["stimulus"]["x"] for item in history["records"]] == [1, 2]
    summary = verifier_stimulus_history_view(
        history, history_path=verification / "stimulus-history.json"
    )
    assert summary["payload_mode"] == "SUMMARY_ONLY"
    assert summary["exact_payloads_in_prompt"] is False
    assert summary["kind_counts"] == {"directed": 2}
    assert "records" not in summary
    assert "recent_exact_records" not in summary


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_cocotb_decorator_emits_and_enforces_runtime_coverage(tmp_path, monkeypatch) -> None:
    # A caller outside the variant root must still launch the correct package.
    monkeypatch.chdir(tmp_path)
    rtl_dir = tmp_path / "rtl"
    tests_dir = tmp_path / "tests"
    reference_dir = tmp_path / "reference"
    rtl_dir.mkdir()
    tests_dir.mkdir()
    reference_dir.mkdir()
    (rtl_dir / "top.sv").write_text(
        "module top(input logic clk, input logic rst); endmodule\n",
        encoding="utf-8",
    )
    (tests_dir / "test_top.py").write_text(
        """import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.coverage.runtime import contract_coverage, record_stimulus, sample_operation

OPERATION_SAMPLING_BINDINGS = [{"operation": "smoke_op", "point": "mode", "template": "custom"}]
def observe_mode(values, state):
    return "normal" if values["reset"] == 0 else None

@cocotb.test()
@contract_coverage()
async def test_reset_bins(dut):
    cocotb.start_soon(Clock(dut.clk, 2, unit="ns").start())
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    stimulus_id = record_stimulus(
        "directed", {"rst_sequence": [1, 0]}, {"rst": 0}, label="reset_release"
    )
    sample_operation("smoke_op", {"mode": "normal"}, "directed", stimulus_id)
""",
        encoding="utf-8",
    )
    plan = {
        "schema_version": 2,
        "monitor": {"clock": "clk", "reset": "rst", "signals": ["clk", "rst"]},
        "obligations": [
            {
                "id": "signal.rst.reset_behavior",
                "template": "reset_behavior",
                "bindings": {"signal": "rst", "active_value": 1},
                "bins": [
                    {"name": "asserted"},
                    {"name": "deasserted"},
                    {"name": "release"},
                ],
            },
            {
                "id": "operation.smoke_op.mode",
                "template": "operation_coverpoint",
                "bindings": {
                    "operation_name": "smoke_op",
                    "field": "mode",
                    "concept": "mode",
                    "source": "llm_extension",
                    "sampling": {"template": "custom", "observer": "observe_mode", "event": "clock",
                                 "channel": {}, "guards": [], "field_types": {},
                                 "fields": {"reset": {"signal": "rst", "lsb": 0, "width": 1, "declared_width": 1}}},
                },
                "bins": [
                    {
                        "name": "normal",
                        "predicate": {"op": "eq", "args": ["normal"]},
                    }
                ],
            },
        ],
    }
    test_path = tests_dir / "test_top.py"
    test_path.write_text(
        install_contract_generated_block(
            test_path.read_text(encoding="utf-8"), plan
        ),
        encoding="utf-8",
    )
    result = run_cocotb_regression(
        rtl_dir=rtl_dir,
        top_module="top",
        tests_dir=tests_dir,
        reference_dir=reference_dir,
        test_modules=["test_top"],
        seed=7,
        build_dir=tmp_path / "build",
        report_path=tmp_path / "verification" / "cocotb.json",
        timeout_seconds=60,
        coverage_plan=plan,
        coverage_report_path=tmp_path / "verification" / "functional-coverage.json",
        stimulus_ledger_report_path=tmp_path
        / "verification"
        / "stimulus-ledger-run.json",
    )
    assert result["status"] == "PASS", {
        "result": result,
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
        "worker_error": result.get("worker_error"),
    }
    assert result["functional_coverage"]["coverage_percent"] == 100.0
    assert result["functional_coverage"]["operation_samples"] == 1
    assert result["stimulus_ledger"]["stimulus_count"] == 1
    ledger = json.loads(
        (tmp_path / "verification" / "stimulus-ledger-run.json").read_text(
            encoding="utf-8"
        )
    )
    assert ledger["records"][0]["stimulus"] == {"rst_sequence": [1, 0]}
    assert (
        tmp_path
        / "verification"
        / "functional-coverage.cocotb-coverage.yml"
    ).is_file()


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
def test_contract_generated_protocol_assertion_fails_real_simulation(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rtl_dir = tmp_path / "rtl"
    tests_dir = tmp_path / "tests"
    reference_dir = tmp_path / "reference"
    rtl_dir.mkdir()
    tests_dir.mkdir()
    reference_dir.mkdir()
    (rtl_dir / "mutant.sv").write_text(
        """module mutant(
  input logic clk, input logic rst, input logic r,
  output logic v, output logic [7:0] p,
  output logic done, output logic err
);
always_ff @(posedge clk) begin
  if (rst) begin v <= 0; p <= 0; end
  else begin v <= 1; p <= p + 1; end
end
assign done = 0;
assign err = 0;
endmodule
""",
        encoding="utf-8",
    )
    raw_test = """import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.coverage.runtime import contract_coverage

@cocotb.test(timeout_time=1, timeout_unit="us")
@contract_coverage()
async def test_stalled_payload(dut):
    dut.r.value = 0
    dut.rst.value = 1
    cocotb.start_soon(Clock(dut.clk, 2, unit="ns").start())
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
"""
    (tests_dir / "test_mutant.py").write_text(
        install_contract_generated_block(raw_test, _plan()), encoding="utf-8"
    )
    report_path = tmp_path / "verification" / "functional-coverage.json"
    result = run_cocotb_regression(
        rtl_dir=rtl_dir,
        top_module="mutant",
        tests_dir=tests_dir,
        reference_dir=reference_dir,
        test_modules=["test_mutant"],
        seed=4,
        build_dir=tmp_path / "build",
        report_path=tmp_path / "verification" / "cocotb.json",
        timeout_seconds=60,
        coverage_plan=_plan(),
        coverage_report_path=report_path,
    )
    assert result["status"] == "SIMULATION_FAILURE", result
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["failure_records"]
    failure = report["failure_records"][0]
    assert failure["related_signal_names"] == ["v", "r", "p"]
    assert "content changed" in failure["detail"]
