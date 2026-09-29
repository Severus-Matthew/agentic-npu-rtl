"""Proves `check_lifecycle_operations` correctly consumes externally-tracked
JOB_START/JOB_COMPLETE (from control_plane_sequence_tracker) to drive the same
`active`/`busy_tracks_active_job`/`completion_due` state machine a
ready_valid-accepted operation already uses -- the checker itself never learns
how the event was produced.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from multigent.verifier_tool.lifecycle.assertion.assertion_checkers import (
    check_lifecycle_operations,
    finalize_lifecycle_checker_state,
)

OPERATION = {
    "operation_name": "gemm",
    "policy": {"error_style": "pulse", "completion_style": "control_plane_sequence"},
    "status": {"busy": ["busy"], "completion": [], "error": []},
    "commands": [],
    "outputs": [],
    "retirements": [],
    "error_responses": [],
}

BASE_SNAPSHOT = {"busy": 0}


def test_job_start_event_sets_active():
    state = {}
    check_lifecycle_operations(
        {**BASE_SNAPSHOT, "busy": 0}, [OPERATION], state,
        job_start_by_operation={"gemm": True},
    )
    assert state["operations"]["gemm"]["active"] is True


def test_busy_must_track_the_job_start_event_next_cycle():
    state = {}
    check_lifecycle_operations(
        {**BASE_SNAPSHOT, "busy": 0}, [OPERATION], state,
        job_start_by_operation={"gemm": True},
    )
    with pytest.raises(AssertionError, match="busy is low"):
        check_lifecycle_operations({**BASE_SNAPSHOT, "busy": 0}, [OPERATION], state)


def test_busy_correctly_tracking_active_raises_nothing():
    state = {}
    check_lifecycle_operations(
        {**BASE_SNAPSHOT, "busy": 0}, [OPERATION], state,
        job_start_by_operation={"gemm": True},
    )
    check_lifecycle_operations({**BASE_SNAPSHOT, "busy": 1}, [OPERATION], state)
    assert state["operations"]["gemm"]["active"] is True


def test_job_complete_event_clears_active():
    state = {}
    check_lifecycle_operations({**BASE_SNAPSHOT, "busy": 0}, [OPERATION], state, job_start_by_operation={"gemm": True})
    check_lifecycle_operations({**BASE_SNAPSHOT, "busy": 1}, [OPERATION], state)
    assert state["operations"]["gemm"]["active"] is True

    check_lifecycle_operations(
        {**BASE_SNAPSHOT, "busy": 1}, [OPERATION], state,
        job_complete_by_operation={"gemm": True},
    )
    assert state["operations"]["gemm"]["active"] is False
    # No dedicated completion signal is bound, so completion_due stays False --
    # nothing further for completion_matches_final_output to check.
    assert state["operations"]["gemm"]["completion_due"] is False


def test_no_event_leaves_state_untouched():
    state = {}
    check_lifecycle_operations({**BASE_SNAPSHOT}, [OPERATION], state)
    assert state["operations"]["gemm"]["active"] is False


def test_missing_job_events_default_to_false_without_erroring():
    """Every existing caller that never passes these two new parameters must
    behave exactly as before -- pure backward compatibility."""

    state = {}
    check_lifecycle_operations({**BASE_SNAPSHOT}, [OPERATION], state, {"gemm": set()})
    assert state["operations"]["gemm"]["active"] is False


RETIREMENT_OPERATION = {
    **deepcopy(OPERATION),
    "control_plane_sequence": {"job_start": {}, "job_complete": {}},
    "retirements": [{
        "signals": {"valid": "bvalid", "ready": "bready"},
        "expected_count": 2,
        "count_mode": "accepted_data_beats_after_all_write_responses",
        "request_signals": {"valid": "awvalid", "ready": "awready"},
        "data_signals": {"valid": "wvalid", "ready": "wready"},
    }],
}
RETIREMENT_SNAPSHOT = {
    "busy": 0, "awvalid": 0, "awready": 1,
    "wvalid": 0, "wready": 1, "bvalid": 0, "bready": 1,
}


def _retirement_cycle(state, *, start=False, complete=False, **overrides):
    check_lifecycle_operations(
        {**RETIREMENT_SNAPSHOT, **overrides}, [RETIREMENT_OPERATION], state,
        job_start_by_operation={"gemm": start},
        job_complete_by_operation={"gemm": complete},
    )


def test_control_plane_done_before_final_write_response_is_rejected():
    state = {}
    _retirement_cycle(state, start=True)
    _retirement_cycle(state, awvalid=1, wvalid=1, busy=1)
    with pytest.raises(AssertionError, match="completion_matches_final_output.*before final output retirement"):
        _retirement_cycle(state, complete=True, busy=1)


def test_control_plane_done_after_final_write_response_is_accepted():
    state = {}
    _retirement_cycle(state, start=True)
    _retirement_cycle(state, awvalid=1, wvalid=1, busy=1)
    _retirement_cycle(state, wvalid=1, busy=1)
    _retirement_cycle(state, bvalid=1, busy=1)
    assert state["operations"]["gemm"]["final_output_retired"] is True
    assert state["operations"]["gemm"]["active"] is True
    _retirement_cycle(state, complete=True, busy=1)
    assert state["operations"]["gemm"]["active"] is False


COMMAND_OPERATION = {
    "operation_name": "commanded",
    "policy": {"error_style": "pulse", "completion_style": "pulse"},
    "status": {"busy": [], "completion": [], "error": []},
    "commands": [{
        "signals": {"valid": "cmd_valid", "ready": "cmd_ready", "payload": "cmd"},
        "legal_values": [1],
    }],
    "inputs": [{"signals": {"valid": "in_valid", "ready": "in_ready"}}],
    "outputs": [{"signals": {"valid": "out_valid", "ready": "out_ready"}}],
    "retirements": [{
        "signals": {"valid": "out_valid", "ready": "out_ready"},
        "expected_count": 1,
    }],
    "error_responses": [],
}
COMMAND_SNAPSHOT = {
    "cmd_valid": 0, "cmd_ready": 1, "cmd": 1,
    "in_valid": 0, "in_ready": 1,
    "out_valid": 0, "out_ready": 1,
}


def test_accepted_command_without_observable_progress_has_named_failure():
    state = {}
    enabled = {"commanded": {"accepted_command_starts_job"}}
    check_lifecycle_operations(
        {**COMMAND_SNAPSHOT, "cmd_valid": 1},
        [COMMAND_OPERATION],
        state,
        enabled,
    )
    with pytest.raises(
        AssertionError,
        match="accepted_command_starts_job.*no observable job progress",
    ):
        finalize_lifecycle_checker_state({}, state)


def test_accepted_command_progress_and_retirement_satisfy_start_checker():
    state = {}
    enabled = {"commanded": {"accepted_command_starts_job"}}
    check_lifecycle_operations(
        {**COMMAND_SNAPSHOT, "cmd_valid": 1},
        [COMMAND_OPERATION],
        state,
        enabled,
    )
    check_lifecycle_operations(
        {**COMMAND_SNAPSHOT, "in_valid": 1},
        [COMMAND_OPERATION],
        state,
        enabled,
    )
    check_lifecycle_operations(
        {**COMMAND_SNAPSHOT, "out_valid": 1},
        [COMMAND_OPERATION],
        state,
        enabled,
    )
    finalize_lifecycle_checker_state({}, state)


def test_second_accepted_command_has_precise_single_inflight_failure():
    state = {}
    enabled = {"commanded": {"single_inflight_job_enforced"}}
    accepted = {**COMMAND_SNAPSHOT, "cmd_valid": 1}
    check_lifecycle_operations(accepted, [COMMAND_OPERATION], state, enabled)
    with pytest.raises(AssertionError, match="single_inflight_job_enforced"):
        check_lifecycle_operations(accepted, [COMMAND_OPERATION], state, enabled)
