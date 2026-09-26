"""Proves the stateful AXI4-Lite control-bus tracker fires JOB_START exactly
on the cycle the trigger write's B-response closes, and JOB_COMPLETE exactly
on the cycle a poll's R-response returns the expected bit -- not before, not
on a mismatched address, and correctly ignoring failed poll attempts.
"""
from __future__ import annotations

from multigent.verifier_tool.lifecycle.assertion.control_plane_sequence_tracker import (
    advance_control_plane_sequence,
)

CONTROL_SIGNALS = {
    "write_address": {"valid": "awvalid", "ready": "awready", "addr": "awaddr"},
    "write_data": {"valid": "wvalid", "ready": "wready", "data": "wdata"},
    "write_response": {"valid": "bvalid", "ready": "bready"},
    "read_address": {"valid": "arvalid", "ready": "arready", "addr": "araddr"},
    "read_data": {"valid": "rvalid", "ready": "rready", "data": "rdata"},
}

IDLE = {
    "awvalid": 0, "awready": 1, "awaddr": 0,
    "wvalid": 0, "wready": 1, "wdata": 0,
    "bvalid": 0, "bready": 1,
    "arvalid": 0, "arready": 1, "araddr": 0,
    "rvalid": 0, "rready": 1, "rdata": 0,
}


def _cycle(**overrides):
    return {**IDLE, **overrides}


def _run(cycles, control_signals, sequence, state):
    starts, completes = [], []
    for index, snapshot in enumerate(cycles):
        started, completed = advance_control_plane_sequence(snapshot, control_signals, sequence, state)
        if started:
            starts.append(index)
        if completed:
            completes.append(index)
    return starts, completes


REGISTERS = {
    "control": {"address": 0x00, "fields": {"ap_start": {"bit": 0}, "ap_done": {"bit": 1}}},
    "a_low": {"address": 0x10},
    "b_low": {"address": 0x1c},
}


def _sequence():
    return {
        "registers": REGISTERS,
        "job_start": {
            "actions": [
                {"op": "write_reg", "register": "a_low", "value_from": {"data_object": "A_matrix", "address_role": "base", "half": "low"}},
                {"op": "write_reg", "register": "b_low", "value_from": {"data_object": "B_matrix", "address_role": "base", "half": "low"}},
                {"op": "write_field", "register": "control", "field": "ap_start", "value": 1},
            ]
        },
        "job_complete": {
            "actions": [
                {"op": "poll_field", "register": "control", "field": "ap_done", "expected": 1},
            ]
        },
    }


def test_job_start_fires_exactly_on_the_last_actions_b_response_cycle():
    cycles = [
        # a_low: AW and W together, B one cycle later
        _cycle(awvalid=1, awaddr=0x10, wvalid=1, wdata=0x1000),
        _cycle(bvalid=1),
        # b_low: AW first, W later, B after
        _cycle(awvalid=1, awaddr=0x1c),
        _cycle(wvalid=1, wdata=0x2000),
        _cycle(bvalid=1),
        # ap_start write_field: AWVALID/WVALID together, B one cycle later
        _cycle(awvalid=1, awaddr=0x00, wvalid=1, wdata=1),
        _cycle(bvalid=1),  # <- JOB_START must fire exactly here
        _cycle(),
    ]
    starts, completes = _run(cycles, CONTROL_SIGNALS, _sequence(), {})
    assert starts == [6]
    assert completes == []


def test_wrong_address_write_does_not_advance_the_sequence():
    """A write to an unrelated register between the real actions must not be
    mistaken for progress -- the state machine should just keep waiting."""

    cycles = [
        _cycle(awvalid=1, awaddr=0x10, wvalid=1, wdata=0x1000),
        _cycle(bvalid=1),
        # stray write to an address that isn't the next expected action (b_low)
        _cycle(awvalid=1, awaddr=0x99, wvalid=1, wdata=0xDEAD),
        _cycle(bvalid=1),
        # now the real b_low write happens
        _cycle(awvalid=1, awaddr=0x1c, wvalid=1, wdata=0x2000),
        _cycle(bvalid=1),
        _cycle(awvalid=1, awaddr=0x00, wvalid=1, wdata=1),
        _cycle(bvalid=1),
    ]
    starts, _ = _run(cycles, CONTROL_SIGNALS, _sequence(), {})
    assert starts == [7]


def test_job_complete_ignores_a_failed_poll_and_fires_on_the_first_success():
    cycles = [
        # poll attempt 1: ap_done bit (bit 1) is 0 -> not a match
        _cycle(arvalid=1, araddr=0x00),
        _cycle(rvalid=1, rdata=0b00),
        # poll attempt 2 (back-to-back): still 0
        _cycle(arvalid=1, araddr=0x00),
        _cycle(rvalid=1, rdata=0b00),
        # poll attempt 3: ap_done now set
        _cycle(arvalid=1, araddr=0x00),
        _cycle(rvalid=1, rdata=0b10),  # <- JOB_COMPLETE must fire exactly here
        _cycle(),
    ]
    _, completes = _run(cycles, CONTROL_SIGNALS, _sequence(), {})
    assert completes == [5]


def test_start_and_complete_track_independently_across_a_full_job():
    """One combined run: job_start's three actions, then job_complete's poll,
    then a second job's job_start begins immediately (rearm proof)."""

    cycles = [
        _cycle(awvalid=1, awaddr=0x10, wvalid=1, wdata=0x1000), _cycle(bvalid=1),
        _cycle(awvalid=1, awaddr=0x1c, wvalid=1, wdata=0x2000), _cycle(bvalid=1),
        _cycle(awvalid=1, awaddr=0x00, wvalid=1, wdata=1), _cycle(bvalid=1),  # index 5: JOB_START
        _cycle(arvalid=1, araddr=0x00), _cycle(rvalid=1, rdata=0b10),  # index 7: JOB_COMPLETE
        # second job's first action begins right away
        _cycle(awvalid=1, awaddr=0x10, wvalid=1, wdata=0x3000), _cycle(bvalid=1),
        _cycle(awvalid=1, awaddr=0x1c, wvalid=1, wdata=0x4000), _cycle(bvalid=1),
        _cycle(awvalid=1, awaddr=0x00, wvalid=1, wdata=1), _cycle(bvalid=1),  # index 13: JOB_START #2
    ]
    starts, completes = _run(cycles, CONTROL_SIGNALS, _sequence(), {})
    assert starts == [5, 13]
    assert completes == [7]
