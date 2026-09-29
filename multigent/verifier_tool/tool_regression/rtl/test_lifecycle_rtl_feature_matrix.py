"""Real-RTL, contract-generated lifecycle-feature fault/fix pairs.

Mirrors the existing `test_{axis,axi4_read,axi4_write,axi_lite_*,
custom_address}_rtl_feature*.py` pattern (small hand-authored RTL with
fault-selecting `localparam`s, the real generated assertion/coverage block,
a minimal hand-driven TB loop) but for the lifecycle domain instead of the
protocol domain: `render_contract_generated_block` is called with an
`architecture_contract` so it also emits `_check_contract_lifecycle_assertions`/
`_finalize_contract_lifecycle_assertions`, and the TB drives the DUT directly
rather than through `run_code_owned_verification_campaign`. This deliberately
never calls `record_stimulus` (there is no operation golden model here --
`classifier_profile: llm_extension` -- so no operation-domain numeric bins are
claimed), which keeps this fixture outside the completion-count bookkeeping
path used by the full operation campaign.

Deliberately out of scope here: `lifecycle.probe.single_inflight_job_enforced`.
Probing it on a `valid_ready_handshake` channel requires holding `cmd_valid`
asserted across the whole job so a premature second accept can be observed
without violating the protocol layer's own valid/ready stability check (valid
may not be withdrawn before an accept) -- `orchestration/README.md` describes
the real held-overlapping-command mechanism `campaign.py` uses for this on
AXI4-Lite jobs. That rule is qualified against the HLS Golden benchmark's own
`control_plane_sequence` mutants instead; see the checked-in HLS benchmark
qualification matrix.
"""

from __future__ import annotations

import json
import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module lifecycle_feature_source (
    input logic clk, rst,
    input logic cmd_valid, cmd_op,
    output logic cmd_ready,
    input logic a_valid,
    input logic [7:0] a_data,
    output logic a_ready,
    output logic y_valid,
    output logic [7:0] y_data,
    input logic y_ready,
    output logic busy, done, err
);
    localparam bit NO_ERR_ON_ILLEGAL = %d;
    localparam bit BUSY_STICKY = %d;
    localparam bit DONE_TWO_CYCLES = %d;
    localparam bit ERR_TWO_CYCLES = %d;
    localparam bit DONE_DELAYED_EXTRA_CYCLE = %d;
    localparam bit ERR_DELAYED_EXTRA_CYCLE = %d;
    localparam bit NO_ABORT_ON_RESET = %d;

    typedef enum logic [1:0] {S_IDLE, S_LOAD, S_OUT} state_t;
    state_t state;
    logic [7:0] hold;
    logic done_reg, done_stretch, busy_sticky_reg;
    logic err_reg, err_stretch, err_extra_delay_reg;
    logic retiring, retiring_d1, illegal_now;

    assign retiring = (state == S_OUT) && y_valid && y_ready;
    assign cmd_ready = (state == S_IDLE);
    assign a_ready = (state == S_LOAD);
    assign y_valid = (state == S_OUT);
    assign y_data = hold;
    assign busy = BUSY_STICKY ? busy_sticky_reg : (state != S_IDLE);
    assign done = done_reg || done_stretch;
    assign err = err_reg || err_stretch;
    // Combinational "illegal command accepted this cycle" event, sampled by
    // both the default (next-cycle) and the extra-delayed error_timing fault
    // path below without disturbing the default path's own timing.
    assign illegal_now = (state == S_IDLE) && cmd_valid && cmd_ready && (cmd_op == 1'b0);

    always_ff @(posedge clk) begin
        if (rst) begin
            // "abort_inflight" (reset_behavior) always returns to S_IDLE on
            // reset except under its own dedicated fault flag, which keeps
            // the job state (and therefore BUSY) alive across reset so
            // busy_tracks_active_job can observe the stale in-flight state.
            state <= NO_ABORT_ON_RESET ? state : S_IDLE;
            err_reg <= 1'b0;
            err_stretch <= 1'b0;
            err_extra_delay_reg <= 1'b0;
            done_reg <= 1'b0;
            done_stretch <= 1'b0;
            retiring_d1 <= 1'b0;
            busy_sticky_reg <= 1'b0;
        end else begin
            // Default path (ERR_DELAYED_EXTRA_CYCLE=0) registers directly
            // from the combinational event, exactly like the original,
            // unparameterized version of this line -- the fault path detours
            // through one extra register stage instead of altering it.
            err_extra_delay_reg <= illegal_now;
            err_reg <= ERR_DELAYED_EXTRA_CYCLE ? err_extra_delay_reg : (illegal_now && !NO_ERR_ON_ILLEGAL);
            err_stretch <= ERR_TWO_CYCLES ? err_reg : 1'b0;
            // "done" (completion_timing=next_cycle_after_retirement) registers
            // one cycle after the accepted output handshake, never combinationally
            // in the same cycle. The next-cycle requirement is independently
            // exercised by the ready_valid_tiny_gemm fixture.
            retiring_d1 <= retiring;
            done_reg <= DONE_DELAYED_EXTRA_CYCLE ? retiring_d1 : retiring;
            done_stretch <= DONE_TWO_CYCLES ? done_reg : 1'b0;
            if (state != S_IDLE) busy_sticky_reg <= 1'b1;
            case (state)
                S_IDLE: begin
                    if (cmd_valid && cmd_ready && cmd_op == 1'b1) begin
                        state <= S_LOAD;
                    end
                end
                S_LOAD: begin
                    if (a_valid && a_ready) begin
                        hold <= a_data;
                        state <= S_OUT;
                    end
                end
                S_OUT: begin
                    if (retiring) state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
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
async def verify_lifecycle_features(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    dut.cmd_valid.value = 0
    dut.cmd_op.value = 0
    dut.a_valid.value = 0
    dut.a_data.value = 0
    dut.y_ready.value = 1

    async def sample():
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_assertions)
        return snapshot

    async def tick():
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")

    # Reset.
    for _ in range(2):
        await sample()
        await tick()
    dut.rst.value = 0

    async def run_job(value):
        dut.cmd_valid.value = 1
        dut.cmd_op.value = 1
        accepted = False
        for _ in range(5):
            snap = await sample()
            await tick()
            if int(snap["cmd_valid"]) and int(snap["cmd_ready"]):
                accepted = True
                break
        assert accepted, "legal command was never accepted"
        dut.cmd_valid.value = 0
        dut.a_valid.value = 1
        dut.a_data.value = value
        for _ in range(5):
            snap = await sample()
            await tick()
            if int(snap["a_valid"]) and int(snap["a_ready"]):
                break
        dut.a_valid.value = 0
        for _ in range(6):
            snap = await sample()
            await tick()
            if int(snap["y_valid"]) and int(snap["y_ready"]):
                break

    async def run_illegal():
        dut.cmd_valid.value = 1
        dut.cmd_op.value = 0
        for _ in range(5):
            snap = await sample()
            await tick()
            if int(snap["cmd_valid"]) and int(snap["cmd_ready"]):
                break
        dut.cmd_valid.value = 0
        for _ in range(4):
            await sample()
            await tick()

    async def run_job_then_reset_midflight():
        # reset_behavior=abort_inflight probe: accept a legal command, let the
        # job go active, then reset mid-flight (before it retires). The
        # built-in abort_inflight reset handling clears the checker's own
        # active-job bookkeeping unconditionally on reset, so a compliant DUT
        # must likewise drop BUSY back to its idle value -- a DUT that keeps
        # its state machine (and therefore BUSY) alive across reset produces a
        # busy_tracks_active_job mismatch on the first post-reset sample.
        dut.cmd_valid.value = 1
        dut.cmd_op.value = 1
        accepted = False
        for _ in range(5):
            snap = await sample()
            await tick()
            if int(snap["cmd_valid"]) and int(snap["cmd_ready"]):
                accepted = True
                break
        assert accepted, "legal command was never accepted before mid-flight reset probe"
        dut.cmd_valid.value = 0
        for _ in range(2):
            await sample()
            await tick()
        dut.rst.value = 1
        for _ in range(2):
            await sample()
            await tick()
        dut.rst.value = 0
        for _ in range(3):
            await sample()
            await tick()

    await run_job_then_reset_midflight()
    await run_illegal()
    await run_job(0x11)
    await run_job(0x22)
    for _ in range(4):
        await sample()
        await tick()

    _finalize_contract_assertions()
    report = tracker.report()
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for target in TARGETS:
        assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_ARCHITECTURE = {
    "operations": [{
        "name": "probe",
        "kind": "arithmetic",
        "coverage_family": "matrix_multiply",
        "coverage_family_source": "catalog",
        "features": ["dimensions", "operand_values", "accumulation"],
        "feature_extensions": [],
        "semantics": "Lifecycle-only smoke fixture; arithmetic intentionally not classified.",
        "arithmetic": {
            "classifier_profile": "llm_extension",
            "reason": "Isolates lifecycle assertion/coverage from any operation golden model.",
        },
        "lifecycle_policy": {
            "job_acceptance": "valid_ready_handshake",
            "job_overlap": "single_inflight",
            "busy_behavior": "tracks_active_job",
            "completion_style": "pulse",
            "completion_timing": "next_cycle_after_retirement",
            "illegal_command_behavior": "error_without_start",
            "error_style": "pulse",
            "error_timing": "next_cycle_after_error_event",
            "reset_behavior": "abort_inflight",
        },
        "inputs": ["A"],
        "outputs": ["Y"],
    }],
    "data_types": [
        {"name": "s8", "width_bits": 8, "signed": True},
    ],
    "data_objects": [
        {"name": "A", "role": "left_operand_matrix", "data_type": "s8", "dimensions": ["M", "K"],
         "producer": "external", "consumers": ["probe"], "external": True},
        {"name": "Y", "role": "result_matrix", "data_type": "s8", "dimensions": ["M", "N"],
         "producer": "probe", "consumers": ["external"], "external": True},
    ],
    "dimensions": [
        {"name": "M", "minimum": 1, "maximum": 1},
        {"name": "K", "minimum": 1, "maximum": 1},
        {"name": "N", "minimum": 1, "maximum": 1},
    ],
    "parameters": [],
}
for obj in _ARCHITECTURE["data_objects"]:
    obj["serialization"] = {
        "kind": "dense_tensor", "index_order": list(obj["dimensions"]),
        "description": "One element per transfer.",
    }


def _interface() -> dict:
    channels = [
        {"name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
         "data_objects": [], "ordering": "one command", "framing": "one beat"},
        {"name": "a", "direction": "input", "protocol_profile": "ready_valid",
         "data_objects": ["A"], "ordering": "declared dimension order", "framing": "exact tensor"},
        {"name": "y", "direction": "output", "protocol_profile": "ready_valid",
         "data_objects": ["Y"], "ordering": "declared dimension order", "framing": "exact tensor"},
    ]
    signals = [
        {"name": "clk", "role": "clock", "direction": "input", "channel": None},
        {"name": "rst", "role": "reset", "direction": "input", "channel": None,
         "semantic": "active-high reset"},
        {"name": "cmd_valid", "role": "valid", "direction": "input", "channel": "cmd"},
        {"name": "cmd_ready", "role": "ready", "direction": "output", "channel": "cmd"},
        {"name": "cmd_op", "role": "payload", "semantic_class": "command", "direction": "input",
         "channel": "cmd", "width": "1", "semantic": "legal only 1'd1"},
        {"name": "a_valid", "role": "valid", "direction": "input", "channel": "a"},
        {"name": "a_ready", "role": "ready", "direction": "output", "channel": "a"},
        {"name": "a_data", "role": "payload", "semantic_class": "data", "direction": "input",
         "channel": "a", "width": "8", "signed": True},
        {"name": "y_valid", "role": "valid", "direction": "output", "channel": "y"},
        {"name": "y_ready", "role": "ready", "direction": "input", "channel": "y"},
        {"name": "y_data", "role": "payload", "semantic_class": "data", "direction": "output",
         "channel": "y", "width": "8", "signed": True},
        {"name": "busy", "role": "busy", "direction": "output", "channel": None},
        {"name": "done", "role": "completion", "direction": "output", "channel": None},
        {"name": "err", "role": "error", "direction": "output", "channel": None},
    ]
    return {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}


def _run(tmp_path, variant: str, targets: list[str]) -> dict:
    path = tmp_path / variant
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    flags = {
        "no_err_on_illegal": (1, 0, 0, 0, 0, 0, 0),
        "busy_sticky": (0, 1, 0, 0, 0, 0, 0),
        "done_two_cycles": (0, 0, 1, 0, 0, 0, 0),
        "err_two_cycles": (0, 0, 0, 1, 0, 0, 0),
        "done_delayed": (0, 0, 0, 0, 1, 0, 0),
        "err_delayed": (0, 0, 0, 0, 0, 1, 0),
        "no_abort_on_reset": (0, 0, 0, 0, 0, 0, 1),
        "correct": (0, 0, 0, 0, 0, 0, 0),
    }[variant]
    (rtl / "lifecycle_feature_source.sv").write_text(_RTL % flags)
    (reference / "model.py").write_text("")
    interface = _interface()
    source = render_contract_generated_block(
        build_interface_coverage_plan(interface), _ARCHITECTURE,
    )
    (tests / "test_lifecycle_features.py").write_text(source + _TB % json.dumps(targets))
    return run_cocotb_regression(
        rtl_dir=rtl,
        top_module="lifecycle_feature_source",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_lifecycle_features"],
        seed=11,
        build_dir=path / "build",
        report_path=path / "report.json",
        timeout_seconds=120,
    )


_BINS = {
    "illegal_error": "signal.err.error_behavior.asserted",
    "busy_retired": "signal.busy.busy_behavior.retired",
    "status_pulse": "lifecycle.probe.status_pulses_are_one_cycle",
}


def test_lifecycle_feature_bins_have_real_rtl_fault_fix_pairs(tmp_path):
    bad = _run(tmp_path, "no_err_on_illegal", [_BINS["illegal_error"]])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "lifecycle.probe.illegal_command_errors_without_start" in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "busy_sticky", [_BINS["busy_retired"]])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "lifecycle.probe.busy_tracks_active_job" in bad["stdout"], bad["stdout"][-3000:]

    bad = _run(tmp_path, "done_two_cycles", [])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert _BINS["status_pulse"] in bad["stdout"], bad["stdout"][-3000:]

    # error_style=pulse's own stretch fault, independent of done_two_cycles above
    # (which only ever stretches the completion pulse, not the error pulse) --
    # this is what independently frees `policy:error_style.pulse` from BUG-003's
    # ready_valid-automatic-campaign-only blocker: this fixture never touches the
    # automatic campaign at all.
    bad = _run(tmp_path, "err_two_cycles", [_BINS["illegal_error"]])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "lifecycle.probe.status_pulses_are_one_cycle" in bad["stdout"], bad["stdout"][-3000:]
    assert "error remained high for multiple samples" in bad["stdout"], bad["stdout"][-3000:]

    # completion_timing=next_cycle_after_retirement's own exact-timing fault: a
    # one-extra-cycle-late completion is a distinct defect from the pulse-width
    # fault above (done_two_cycles keeps the *first* completion cycle exactly
    # where it belongs and only widens it; this keeps the pulse exactly one
    # cycle wide but pushes its single edge one cycle later than retirement).
    bad = _run(tmp_path, "done_delayed", [])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "lifecycle.probe.completion_matches_final_output" in bad["stdout"], bad["stdout"][-3000:]
    assert "final output was not followed by completion" in bad["stdout"], bad["stdout"][-3000:]

    # error_timing=next_cycle_after_error_event's own exact-timing fault. Like
    # `job_acceptance`/`reset_aborts_pending_job`, this policy has no uniquely
    # named diagnostic of its own -- a late error is observed by the *sibling*
    # illegal_command_errors_without_start check's own next-sample-due gate
    # (it fires because error is not yet high on the sample where it was due,
    # not because a distinct "error_timing" feature string exists).
    bad = _run(tmp_path, "err_delayed", [])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "lifecycle.probe.illegal_command_errors_without_start" in bad["stdout"], bad["stdout"][-3000:]
    assert "illegal command was not followed by error" in bad["stdout"], bad["stdout"][-3000:]

    # reset_behavior=abort_inflight's own fault: a DUT that keeps its job
    # state (and BUSY) alive across a mid-flight reset instead of aborting to
    # idle. There is likewise no uniquely named "reset_aborts_pending_job"
    # diagnostic anywhere in the checker (confirmed by reading
    # lifecycle/assertion/assertion_checkers.py in full) -- built-in
    # abort_inflight is enforced by unconditionally clearing the checker's own
    # active-job bookkeeping on every reset, so a DUT that does not likewise
    # clear its own active-job signal is caught by the ordinary
    # busy_tracks_active_job mismatch this produces on the first post-reset
    # sample.
    bad = _run(tmp_path, "no_abort_on_reset", [])
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "lifecycle.probe.busy_tracks_active_job" in bad["stdout"], bad["stdout"][-3000:]
    assert "busy is high without an active legal job" in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path, "correct", [
        "signal.busy.busy_behavior.idle",
        "signal.busy.busy_behavior.active",
        "signal.busy.busy_behavior.retired",
        "signal.done.completion_behavior.observed",
        "signal.done.completion_behavior.back_to_back",
        "signal.err.error_behavior.inactive",
        "signal.err.error_behavior.asserted",
        # channel.cmd.command_legality.{legal,illegal} are deliberately not
        # asserted here: crediting them requires the operation-aware merged
        # plan (build_architect_operation_metadata + merge_coverage_plans,
        # as qualify.py builds for ready_valid_tiny_gemm), not the
        # interface-only plan this hand-driven TB constructs.
    ])
    assert good["status"] == "PASS", good
