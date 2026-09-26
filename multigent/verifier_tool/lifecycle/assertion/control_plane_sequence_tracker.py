"""Stateful AXI4-Lite control-bus tracker: turns a raw per-cycle signal
snapshot into JOB_START / JOB_COMPLETE events for an operation whose
`job_acceptance`/`completion_style` selects `control_plane_sequence`.

Unlike ready_valid's `_transfer()` (a pure function of one snapshot),
detecting "this write_reg/write_field action's transaction completed" spans
several cycles (AW+W both accepted, then B accepted) and detecting a
poll_field's success spans an AR+R pair -- genuinely stateful, tracked here
per operation in the same persistent `state` dict every other lifecycle
checker already threads through `check_lifecycle_assertions`.

Only ever reads the declared AXI4-Lite control channel's own valid/ready/
addr/data/resp signals plus the `control_plane_sequence` register/field map --
never anything operation-specific beyond that.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def _read(snapshot: Mapping[str, Any], name: str) -> int:
    if name not in snapshot:
        raise AssertionError(f"control_plane_sequence snapshot is missing bound signal {name!r}")
    return int(snapshot[name])


def _hs(snapshot: Mapping[str, Any], signals: Mapping[str, str], valid: str, ready: str) -> bool:
    return bool(_read(snapshot, signals[valid])) and bool(_read(snapshot, signals[ready]))


def _advance_write_transaction(
    snapshot: Mapping[str, Any], control_signals: Mapping[str, Mapping[str, str]], sub_state: MutableMapping[str, Any]
) -> tuple[int, int] | None:
    """Track one AW+W (either order) then B AXI4-Lite write. Returns
    (address, data) the cycle B closes, else None."""

    aw = control_signals["write_address"]
    w = control_signals["write_data"]
    b = control_signals["write_response"]
    if sub_state.get("aw_addr") is None and _hs(snapshot, aw, "valid", "ready"):
        sub_state["aw_addr"] = _read(snapshot, aw["addr"])
    if sub_state.get("w_data") is None and _hs(snapshot, w, "valid", "ready"):
        sub_state["w_data"] = _read(snapshot, w["data"])
    if (
        sub_state.get("aw_addr") is not None
        and sub_state.get("w_data") is not None
        and _hs(snapshot, b, "valid", "ready")
    ):
        result = (sub_state["aw_addr"], sub_state["w_data"])
        sub_state["aw_addr"] = None
        sub_state["w_data"] = None
        return result
    return None


def _advance_read_transaction(
    snapshot: Mapping[str, Any], control_signals: Mapping[str, Mapping[str, str]], sub_state: MutableMapping[str, Any]
) -> tuple[int, int] | None:
    """Track one AR then R AXI4-Lite read. Returns (address, data) the cycle
    R closes, else None."""

    ar = control_signals["read_address"]
    r = control_signals["read_data"]
    if sub_state.get("ar_addr") is None and _hs(snapshot, ar, "valid", "ready"):
        sub_state["ar_addr"] = _read(snapshot, ar["addr"])
    if sub_state.get("ar_addr") is not None and _hs(snapshot, r, "valid", "ready"):
        result = (sub_state["ar_addr"], _read(snapshot, r["data"]))
        sub_state["ar_addr"] = None
        return result
    return None


def _register_address(registers: Mapping[str, Any], name: str) -> int:
    return int(registers[name]["address"])


def _action_matches(action: Mapping[str, Any], registers: Mapping[str, Any], address: int, data: int) -> bool:
    if address != _register_address(registers, str(action["register"])):
        return False
    op = str(action["op"])
    if op in ("write_reg", "read_reg"):
        return True
    bit = int(registers[str(action["register"])]["fields"][str(action["field"])]["bit"])
    observed = (data >> bit) & 1
    expected = int(action["value"]) if op == "write_field" else int(action["expected"])
    return observed == (expected & 1)


def advance_control_plane_sequence(
    snapshot: Mapping[str, Any],
    control_signals: Mapping[str, Mapping[str, str]],
    sequence: Mapping[str, Any],
    state: MutableMapping[str, Any],
) -> tuple[bool, bool]:
    """Advance both job_start and job_complete tracking by one sampled cycle.

    Returns (job_start_fired_this_cycle, job_complete_fired_this_cycle).
    Rearms automatically after firing, ready to track the next job.
    """

    registers = sequence["registers"]
    write_sub_state = state.setdefault("cps_write", {})
    read_sub_state = state.setdefault("cps_read", {})
    completed_write = _advance_write_transaction(snapshot, control_signals, write_sub_state)
    completed_read = _advance_read_transaction(snapshot, control_signals, read_sub_state)

    start_index = state.setdefault("cps_job_start_index", 0)
    start_actions = list(sequence["job_start"]["actions"])
    job_start_fired = False
    if start_index < len(start_actions):
        expected = start_actions[start_index]
        observed = completed_write if str(expected["op"]) in ("write_reg", "write_field") else completed_read
        if observed is not None and _action_matches(expected, registers, *observed):
            start_index += 1
            if start_index == len(start_actions):
                job_start_fired = True
                start_index = 0
            state["cps_job_start_index"] = start_index

    complete_index = state.setdefault("cps_job_complete_index", 0)
    complete_actions = list(sequence["job_complete"]["actions"])
    job_complete_fired = False
    if complete_index < len(complete_actions):
        expected = complete_actions[complete_index]
        observed = completed_write if str(expected["op"]) in ("write_reg", "write_field") else completed_read
        if observed is not None and _action_matches(expected, registers, *observed):
            complete_index += 1
            if complete_index == len(complete_actions):
                job_complete_fired = True
                complete_index = 0
            state["cps_job_complete_index"] = complete_index

    return job_start_fired, job_complete_fired


__all__ = ["advance_control_plane_sequence"]
