"""Executable cocotb primitives for exact role-bound protocol channels.

The primitives deliberately know only the machine-readable binding.  Protocol
groups decide which side the testbench owns; operation-specific sequencing stays
outside this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


class ProtocolDriveError(AssertionError):
    """A generated protocol drive cannot complete safely."""


def _handle(dut: Any, name: str) -> Any:
    try:
        return getattr(dut, name)
    except AttributeError as exc:
        raise ProtocolDriveError(f"DUT is missing bound protocol signal {name!r}") from exc


def _channel_fields(channel: Mapping[str, Any]) -> dict[str, str]:
    fields = channel.get("fields", {})
    if not isinstance(fields, Mapping):
        raise ProtocolDriveError("protocol channel fields binding must be a mapping")
    return {str(field): str(name) for field, name in fields.items()}


def _drive_fields(dut: Any, fields: Mapping[str, str], beat: Mapping[str, Any]) -> None:
    unknown = sorted(set(beat) - set(fields))
    if unknown:
        raise ProtocolDriveError(f"protocol beat contains unmapped fields {unknown}")
    for field, signal_name in fields.items():
        _handle(dut, signal_name).value = int(beat.get(field, 0))


async def _settle(timer_ps: int) -> None:
    from cocotb.triggers import Timer

    await Timer(max(1, int(timer_ps)), unit="ps")


async def drive_protocol_transfers(
    dut: Any,
    clock_name: str,
    channel: Mapping[str, Any],
    beats: Iterable[Mapping[str, Any]],
    *,
    timeout_cycles: int = 4096,
    settle_timer_ps: int = 1,
    accepted_event: Any | None = None,
) -> list[dict[str, int]]:
    """Act as the channel source and hold each beat through its accepting edge.

    This is legal only when the channel direction is input relative to the DUT.
    The function drives VALID and all mapped fields, samples READY in the stable
    pre-active-edge half-cycle, and never replays an accepted beat.
    """

    from cocotb.triggers import FallingEdge, RisingEdge, Timer

    if str(channel.get("direction", "")) != "input":
        raise ProtocolDriveError(
            "drive_protocol_transfers requires a DUT-input/source channel binding"
        )
    clock = _handle(dut, str(clock_name))
    valid = _handle(dut, str(channel["valid"]))
    ready_name = channel.get("ready")
    ready = None if ready_name in {None, ""} else _handle(dut, str(ready_name))
    fields = _channel_fields(channel)
    accepted: list[dict[str, int]] = []
    valid.value = 0
    for raw_beat in beats:
        beat = {str(field): int(value) for field, value in raw_beat.items()}
        waiting = 0
        first_drive = True
        while True:
            await FallingEdge(clock)
            if first_drive:
                _drive_fields(dut, fields, beat)
                valid.value = 1
                first_drive = False
            await _settle(settle_timer_ps)
            pre_edge_ready = 1 if ready is None else int(ready.value)
            await RisingEdge(clock)
            waiting += 1
            if pre_edge_ready:
                accepted.append(dict(beat))
                break
            if waiting >= timeout_cycles:
                raise ProtocolDriveError(
                    f"source transfer timed out after {timeout_cycles} cycles; "
                    f"valid={channel['valid']!r} ready={ready_name!r} beat={beat!r}"
                )
    # Wake a pre-scheduled next-phase producer immediately after the accepting
    # active edge. It can then present its first beat at the very next falling
    # edge, which is required to create an observed simultaneous VALID/READY
    # arrival without a spurious ready-only gap.
    if accepted_event is not None:
        accepted_event.set()
    await FallingEdge(clock)
    valid.value = 0
    for signal_name in fields.values():
        _handle(dut, signal_name).value = 0
    return accepted


async def drive_protocol_event_transactions(
    dut: Any,
    profile: Mapping[str, Any],
    transaction: Mapping[str, Any],
    beats: Iterable[Mapping[str, Any]],
    *,
    timeout_cycles: int = 4096,
    settle_timer_ps: int = 1,
) -> list[dict[str, int]]:
    """Drive a Contract-Reviewer-compiled custom input transaction.

    The frozen contract supplies exact drive assignments and a compiled accepted
    event.  This helper is protocol-name agnostic: it works for composed events
    such as ``cyc && stb && !stall`` without generated handshake code.
    """

    from cocotb.triggers import FallingEdge, RisingEdge
    from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
        evaluate_protocol_expression,
        expression_signals,
    )

    drive = transaction.get("source_drive")
    if not isinstance(drive, Mapping):
        raise ProtocolDriveError("event transaction has no source_drive binding")
    accepted_expression = transaction.get("accepted")
    if not isinstance(accepted_expression, Mapping):
        raise ProtocolDriveError("event transaction has no compiled accepted expression")
    clock_binding = profile.get("clock", {})
    clock_name = str(clock_binding.get("signal", ""))
    if str(clock_binding.get("edge", "rising")) != "rising":
        raise ProtocolDriveError("event transaction source currently requires a rising-edge clock")
    clock = _handle(dut, clock_name)
    presented = {
        str(name): int(value)
        for name, value in drive.get("presented_assignments", {}).items()
    }
    idle = {
        str(name): int(value)
        for name, value in drive.get("idle_assignments", {}).items()
    }
    post_accept = {
        str(name): int(value)
        for name, value in drive.get("post_accept_assignments", {}).items()
    }
    completion_mode = str(
        drive.get("completion_mode", "return_after_acceptance")
    )
    fields = tuple(map(str, drive.get("driven_fields", ())))
    completed_expression = transaction.get("completed")
    dependencies = tuple(
        dict.fromkeys(
            (*expression_signals(accepted_expression), *(
                expression_signals(completed_expression)
                if isinstance(completed_expression, Mapping)
                else ()
            ))
        )
    )

    def assign(values: Mapping[str, Any]) -> None:
        for signal, value in values.items():
            _handle(dut, str(signal)).value = int(value)

    def snapshot() -> dict[str, int]:
        return {name: int(_handle(dut, name).value) for name in dependencies}

    unknown_fixed = sorted(
        (set(presented) | set(idle) | set(post_accept)) & set(fields)
    )
    if unknown_fixed:
        raise ProtocolDriveError(
            f"source_drive control assignments overlap driven fields {unknown_fixed}"
        )
    assign(idle)
    for field in fields:
        _handle(dut, field).value = 0
    accepted_beats: list[dict[str, int]] = []
    completed_count = 0
    for raw_beat in beats:
        beat = {str(name): int(value) for name, value in raw_beat.items()}
        unknown = sorted(set(beat) - set(fields))
        missing = sorted(set(fields) - set(beat))
        if unknown or missing:
            raise ProtocolDriveError(
                f"event transaction beat must map every driven field; missing={missing}, unknown={unknown}"
            )
        first_drive = True
        for cycle in range(1, timeout_cycles + 1):
            await FallingEdge(clock)
            if first_drive:
                assign(beat)
                assign(presented)
                first_drive = False
            await _settle(settle_timer_ps)
            accepted = evaluate_protocol_expression(accepted_expression, snapshot())
            completed = (
                evaluate_protocol_expression(completed_expression, snapshot())
                if isinstance(completed_expression, Mapping)
                else False
            )
            await RisingEdge(clock)
            completed_count += int(completed)
            if accepted:
                accepted_beats.append(dict(beat))
                break
        else:
            raise ProtocolDriveError(
                f"event transaction timed out after {timeout_cycles} cycles; "
                f"profile={profile.get('name')!r} transaction={transaction.get('name')!r}"
            )
    await FallingEdge(clock)
    assign(post_accept)
    if completion_mode == "wait_for_all_completions":
        if not isinstance(completed_expression, Mapping):
            raise ProtocolDriveError(
                "wait_for_all_completions requires a compiled completed expression"
            )
        for _cycle in range(1, timeout_cycles + 1):
            if completed_count >= len(accepted_beats):
                break
            await _settle(settle_timer_ps)
            completed = evaluate_protocol_expression(completed_expression, snapshot())
            await RisingEdge(clock)
            completed_count += int(completed)
            await FallingEdge(clock)
        else:
            raise ProtocolDriveError(
                f"event transaction completion timed out after {timeout_cycles} cycles; "
                f"accepted={len(accepted_beats)} completed={completed_count}"
            )
    assign(idle)
    for field in fields:
        _handle(dut, field).value = 0
    return accepted_beats


async def drive_protocol_field_values(
    dut: Any,
    clock_name: str,
    channel: Mapping[str, Any],
    field: str,
    values: Iterable[Any],
    *,
    timeout_cycles: int = 4096,
    settle_timer_ps: int = 1,
) -> list[int]:
    """Pack one logical scalar field per transfer using an exact role binding."""

    field = str(field)
    if field not in _channel_fields(channel):
        raise ProtocolDriveError(
            f"logical field {field!r} is not mapped by channel {channel.get('name')!r}"
        )
    accepted = await drive_protocol_transfers(
        dut,
        clock_name,
        channel,
        ({field: int(value)} for value in values),
        timeout_cycles=timeout_cycles,
        settle_timer_ps=settle_timer_ps,
    )
    return [int(beat[field]) for beat in accepted]


async def collect_protocol_transfers(
    dut: Any,
    clock_name: str,
    channel: Mapping[str, Any],
    *,
    count: int | None = None,
    until_last: bool = False,
    ready_pattern: Sequence[int] = (1,),
    initial_valid_stall_cycles: int | None = None,
    timeout_cycles: int = 4096,
    settle_timer_ps: int = 1,
) -> list[dict[str, int]]:
    """Act as the channel sink and return only transfers accepted on active edges.

    This is legal only when the channel direction is output relative to the DUT.
    A finite count or an implemented LAST field must define completion.
    """

    from cocotb.triggers import FallingEdge, RisingEdge

    if str(channel.get("direction", "")) != "output":
        raise ProtocolDriveError(
            "collect_protocol_transfers requires a DUT-output/source channel binding"
        )
    if count is not None and count < 0:
        raise ProtocolDriveError("count must be nonnegative")
    fields = _channel_fields(channel)
    if until_last and "last" not in fields:
        raise ProtocolDriveError("until_last requires a mapped last field")
    if count is None and not until_last:
        raise ProtocolDriveError("collector requires count or until_last")
    pattern = tuple(int(bool(value)) for value in ready_pattern)
    if not pattern:
        raise ProtocolDriveError("ready_pattern must not be empty")
    clock = _handle(dut, str(clock_name))
    valid = _handle(dut, str(channel["valid"]))
    ready_name = channel.get("ready")
    ready = None if ready_name in {None, ""} else _handle(dut, str(ready_name))
    observed: list[dict[str, int]] = []
    if initial_valid_stall_cycles is not None and initial_valid_stall_cycles < 0:
        raise ProtocolDriveError("initial_valid_stall_cycles must be nonnegative")
    first_valid_seen = False
    first_valid_stalls = 0
    for cycle in range(timeout_cycles):
        if count is not None and len(observed) >= count:
            break
        await FallingEdge(clock)
        if ready is None:
            ready_value = 1
        elif initial_valid_stall_cycles is None:
            ready_value = pattern[cycle % len(pattern)]
        elif not first_valid_seen:
            # Keep READY low until VALID is actually present. A zero count then
            # raises READY in that same stable half-cycle (simultaneous arrival);
            # positive counts produce an exact first-beat stall length.
            ready_value = 0
        elif first_valid_stalls < initial_valid_stall_cycles:
            ready_value = 0
        else:
            ready_value = 1
        if ready is not None:
            ready.value = ready_value
        await _settle(settle_timer_ps)
        pre_edge_valid = int(valid.value)
        if initial_valid_stall_cycles is not None and pre_edge_valid:
            if not first_valid_seen:
                first_valid_seen = True
                ready_value = int(initial_valid_stall_cycles == 0)
                if ready is not None:
                    ready.value = ready_value
                await _settle(settle_timer_ps)
            if not ready_value:
                first_valid_stalls += 1
        snapshot = {
            field: int(_handle(dut, signal_name).value)
            for field, signal_name in fields.items()
        }
        await RisingEdge(clock)
        if pre_edge_valid and ready_value:
            observed.append(snapshot)
            if until_last and snapshot.get("last", 0):
                break
            if count is not None and len(observed) >= count:
                break
    else:
        raise ProtocolDriveError(
            f"sink collection timed out after {timeout_cycles} cycles; "
            f"valid={channel['valid']!r} ready={ready_name!r}"
        )
    await FallingEdge(clock)
    if ready is not None:
        ready.value = 0
    return observed


async def collect_protocol_field_values(
    dut: Any,
    clock_name: str,
    channel: Mapping[str, Any],
    field: str,
    *,
    count: int | None = None,
    until_last: bool = False,
    ready_pattern: Sequence[int] = (1,),
    initial_valid_stall_cycles: int | None = None,
    timeout_cycles: int = 4096,
    settle_timer_ps: int = 1,
) -> list[int]:
    """Collect accepted transfers and unpack one exact logical scalar field."""

    field = str(field)
    if field not in _channel_fields(channel):
        raise ProtocolDriveError(
            f"logical field {field!r} is not mapped by channel {channel.get('name')!r}"
        )
    observed = await collect_protocol_transfers(
        dut,
        clock_name,
        channel,
        count=count,
        until_last=until_last,
        ready_pattern=ready_pattern,
        initial_valid_stall_cycles=initial_valid_stall_cycles,
        timeout_cycles=timeout_cycles,
        settle_timer_ps=settle_timer_ps,
    )
    return [int(beat[field]) for beat in observed]


async def drive_protocol_reset(
    dut: Any,
    clock_name: str,
    reset_name: str,
    active_value: int,
    *,
    asserted_cycles: int = 2,
) -> None:
    """Drive a synchronous reset for a deterministic number of active edges."""

    from cocotb.triggers import FallingEdge, RisingEdge, Timer

    if active_value not in {0, 1}:
        raise ProtocolDriveError("reset active_value must be 0 or 1")
    if asserted_cycles < 1:
        raise ProtocolDriveError("asserted_cycles must be positive")
    clock = _handle(dut, str(clock_name))
    reset = _handle(dut, str(reset_name))
    await FallingEdge(clock)
    # The generated monitor samples the complete interface in ReadOnly on
    # falling edges.  Move the synchronous-reset assertion just beyond that
    # observation window: otherwise the monitor can see reset active together
    # with the DUT's pre-reset VALID state, before the first rising edge at
    # which a synchronous DUT is allowed to clear it.
    await Timer(1, unit="ps")
    reset.value = active_value
    for _ in range(asserted_cycles):
        await RisingEdge(clock)
        await FallingEdge(clock)
    reset.value = 1 - active_value


__all__ = [
    "ProtocolDriveError",
    "collect_protocol_field_values",
    "collect_protocol_transfers",
    "drive_protocol_reset",
    "drive_protocol_field_values",
    "drive_protocol_event_transactions",
    "drive_protocol_transfers",
]
