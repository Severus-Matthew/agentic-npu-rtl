"""HLS-golden qualification copy of lifecycle driving with fault injection."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from multigent.verifier_tool.protocol.stimulus.cocotb import (
    drive_protocol_transfers,
)
from multigent.verifier_tool.lifecycle.stimulus.cocotb import LifecycleDriveError


async def drive_control_plane_sequence(
    dut: Any,
    clock_name: str,
    control_group: Mapping[str, Any],
    sequence: Mapping[str, Any],
    actions: list[Mapping[str, Any]],
    *,
    resolve_value_from: Callable[[Mapping[str, Any]], int],
    response_stall_cycles: int = 0,
    protocol_probe_plan: Mapping[str, bool] | None = None,
    timeout_cycles: int = 262_144,
) -> None:
    """Drive one `job_start`/`job_complete` action list to completion over a
    real AXI4-Lite control bus, via `cocotbext-axi`'s own `AxiLiteMaster`
    (this accelerator is the *subordinate*/slave on this bus, the opposite
    role from every other AXI4-Lite driving this tool does elsewhere -- so
    the memory-job drivers in `protocol/stimulus/drivers/axi_lite.py`, which
    all act as the slave/memory side, do not apply here).

    `resolve_value_from` turns one `write_reg` action's structured
    `value_from` (`{data_object, address_role, half}`) into the actual
    integer to write -- e.g. a data object's base address, split high/low.
    Never resolves what a `poll_field`/`write_field` writes; those are fixed,
    declared literals.

    A `poll_field` action re-issues its read back-to-back (no artificial
    delay between attempts) until the bit matches, bounded only by
    `timeout_cycles` and the bus's own minimum AR->R latency -- see
    `control_plane_sequence_design.md`'s note on why this, not an arbitrary
    polling interval, is the tightest bound a register-polled completion can
    ever get on a black-box control interface.
    """

    from cocotbext.axi import AxiLiteBus
    from cocotbext.axi.axil_channels import AxiLiteReadBus, AxiLiteWriteBus
    from cocotbext.axi.axil_master import AxiLiteMaster

    from multigent.verifier_tool.protocol.stimulus.drivers._bus_binding import bind_channel_bus
    from .protocol_fault_plan import (
        change_content_on_ready_release,
        resolved_protocol_fault,
    )

    channels = control_group.get("channels", {})
    aw, w, b = (channels[name] for name in ("write_address", "write_data", "write_response"))
    ar, r = (channels[name] for name in ("read_address", "read_data"))
    write_bus = AxiLiteWriteBus(
        aw=bind_channel_bus(dut, aw), w=bind_channel_bus(dut, w), b=bind_channel_bus(dut, b)
    )
    read_bus = AxiLiteReadBus(ar=bind_channel_bus(dut, ar), r=bind_channel_bus(dut, r))
    bus = AxiLiteBus(write=write_bus, read=read_bus)
    clock = getattr(dut, clock_name)
    master = AxiLiteMaster(bus, clock)

    qualification_fault = resolved_protocol_fault(control_group)
    qualification_tasks = []
    if qualification_fault is not None:
        if qualification_fault["fault"] not in {
            "change_content_on_ready_release",
            "attempt_unpaired_write_channel",
        }:
            raise LifecycleDriveError(
                f"unsupported AXI4-Lite qualification fault {qualification_fault['fault']!r}"
            )
        if qualification_fault["fault"] == "change_content_on_ready_release":
            channel_name = str(qualification_fault["channel"])
            action_ops = {
                "read_address": {"read_reg", "poll_field"},
                "write_address": {"write_reg", "write_field"},
                "write_data": {"write_reg", "write_field"},
            }[channel_name]
            # A frozen lifecycle sequence may call this driver separately for
            # job_start and job_complete.  Do not create a waiter in a phase that
            # cannot produce the selected channel; the same process-level fault
            # plan is resolved again when the relevant phase is driven.
            has_target_action = any(str(action.get("op", "")) in action_ops for action in actions)
            channel = channels[channel_name]
            content_field = {
                "read_address": "addr",
                "write_address": "addr",
                "write_data": "data",
            }[channel_name]
            if has_target_action:
                import cocotb

                qualification_tasks.append(cocotb.start_soon(change_content_on_ready_release(
                    clock,
                    getattr(dut, str(channel["valid"])),
                    getattr(dut, str(channel["ready"])),
                    getattr(dut, str(channel["fields"][content_field])),
                )))

    if response_stall_cycles < 0:
        raise LifecycleDriveError("response_stall_cycles must be nonnegative")

    async def _stall_first_response(sink: Any, valid_name: str) -> None:
        # Begin counting only after the subordinate raises VALID. A fixed
        # delay from the action start would usually expire before B/R exists.
        from cocotb.triggers import FallingEdge

        remaining = response_stall_cycles
        while remaining:
            await FallingEdge(clock)
            if int(getattr(dut, valid_name).value):
                remaining -= 1
        sink.ready.value = 1
        sink.pause = False

    stall_tasks = []
    if response_stall_cycles:
        import cocotb

        for sink, channel, actions_for_channel in (
            (master.write_if.b_channel, b, {"write_reg", "write_field"}),
            (master.read_if.r_channel, r, {"read_reg", "poll_field"}),
        ):
            if not any(str(action["op"]) in actions_for_channel for action in actions):
                continue
            sink.pause = True
            stall_tasks.append(cocotb.start_soon(_stall_first_response(sink, str(channel["valid"]))))

    data_width_bytes = int(w["widths"]["data"]) // 8
    registers = sequence["registers"]

    for action in actions:
        op = str(action["op"])
        register = registers[str(action["register"])]
        address = int(register["address"])
        if op == "write_reg":
            value = int(resolve_value_from(action["value_from"]))
            await master.write(address, value.to_bytes(data_width_bytes, "little"))
        elif op == "write_field":
            bit = int(register["fields"][str(action["field"])]["bit"])
            value = (int(action["value"]) & 1) << bit
            await master.write(address, value.to_bytes(data_width_bytes, "little"))
        elif op == "read_reg":
            await master.read(address, data_width_bytes)
        elif op == "poll_field":
            bit = int(register["fields"][str(action["field"])]["bit"])
            expected = int(action["expected"]) & 1
            from cocotb.triggers import RisingEdge

            for _ in range(timeout_cycles):
                data = await master.read(address, data_width_bytes)
                observed = (int.from_bytes(bytes(data), "little") >> bit) & 1
                if observed == expected:
                    break
                await RisingEdge(clock)
            else:
                raise LifecycleDriveError(
                    f"poll_field {action['register']}.{action['field']} did not reach "
                    f"{expected} within {timeout_cycles} cycles"
                )
        else:
            raise LifecycleDriveError(f"unsupported control_plane_sequence action {op!r}")
    for task in stall_tasks:
        await task
    for task in qualification_tasks:
        await task
    if protocol_probe_plan and any(protocol_probe_plan.values()):
        from .fault_axi_lite_control import (
            drive_axi_lite_control_probes,
        )

        pointer_actions = [
            action for action in sequence["job_start"]["actions"]
            if action.get("op") == "write_reg"
            and isinstance(action.get("value_from"), Mapping)
            and action["value_from"].get("half") == "low"
            and "data_object" in action["value_from"]
        ]
        if not pointer_actions:
            raise LifecycleDriveError(
                "AXI4-Lite control probes need a declared data-object pointer register"
            )
        pointer = pointer_actions[0]
        register = registers[str(pointer["register"])]
        await drive_axi_lite_control_probes(
            master,
            pointer_address=int(register["address"]),
            pointer_value=int(resolve_value_from(pointer["value_from"])),
            data_width_bytes=data_width_bytes,
            plan=protocol_probe_plan,
            qualification_fault=qualification_fault,
        )


def _command_channel(command: Mapping[str, Any]) -> dict[str, Any]:
    signals = command.get("signals", {})
    metadata_fields = {
        str(item.get("signal", "")): str(item.get("signal", ""))
        for item in command.get("metadata_fields", [])
        if isinstance(item, Mapping) and str(item.get("signal", ""))
    }
    return {
        "name": str(command.get("channel", "")),
        "direction": "input",
        "valid": str(signals.get("valid", "")),
        "ready": str(signals.get("ready", "")),
        "fields": {"payload": str(signals.get("payload", "")), **metadata_fields},
    }


async def drive_accepted_command(
    dut: Any,
    clock_name: str,
    command: Mapping[str, Any],
    value: int,
    *,
    metadata_values: Mapping[str, int] | None = None,
    timeout_cycles: int = 4096,
    accepted_event: Any | None = None,
) -> int:
    metadata_values = {
        str(name): int(field_value)
        for name, field_value in (metadata_values or {}).items()
    }
    known_metadata = {
        str(item.get("signal", ""))
        for item in command.get("metadata_fields", [])
        if isinstance(item, Mapping)
    }
    unknown = sorted(set(metadata_values) - known_metadata)
    if unknown:
        raise LifecycleDriveError(f"command metadata has unmapped signals {unknown}")
    accepted = await drive_protocol_transfers(
        dut,
        clock_name,
        _command_channel(command),
        ({"payload": int(value), **metadata_values},),
        timeout_cycles=timeout_cycles,
        accepted_event=accepted_event,
    )
    if len(accepted) != 1:
        raise LifecycleDriveError("command driver did not observe exactly one acceptance")
    return int(accepted[0]["payload"])


async def drive_accepted_command_on_reset_release(
    dut: Any,
    clock_name: str,
    reset_name: str,
    reset_active_value: int,
    command: Mapping[str, Any],
    value: int,
    *,
    metadata_values: Mapping[str, int] | None = None,
    asserted_cycles: int = 2,
    settle_timer_ps: int = 1,
    accepted_event: Any | None = None,
) -> int:
    """Present a command with READY in the reset-release sampling window."""

    from cocotb.triggers import FallingEdge, RisingEdge, Timer

    if reset_active_value not in {0, 1}:
        raise LifecycleDriveError("reset_active_value must be 0 or 1")
    if asserted_cycles < 1:
        raise LifecycleDriveError("asserted_cycles must be positive")
    signals = command.get("signals", {})
    clock = getattr(dut, str(clock_name))
    reset = getattr(dut, str(reset_name))
    valid = getattr(dut, str(signals.get("valid", "")))
    ready = getattr(dut, str(signals.get("ready", "")))
    payload = getattr(dut, str(signals.get("payload", "")))
    metadata_fields = {
        str(item.get("signal", "")): getattr(dut, str(item.get("signal", "")))
        for item in command.get("metadata_fields", [])
        if isinstance(item, Mapping) and str(item.get("signal", ""))
    }
    metadata_values = {
        str(name): int(field_value)
        for name, field_value in (metadata_values or {}).items()
    }
    unknown = sorted(set(metadata_values) - set(metadata_fields))
    if unknown:
        raise LifecycleDriveError(f"command metadata has unmapped signals {unknown}")

    await FallingEdge(clock)
    # Match protocol.stimulus.drive_protocol_reset: the contract monitor
    # observes the pre-reset interface at this falling edge, then a synchronous
    # DUT receives reset on the following active edge.  Asserting immediately
    # here would make stale pre-reset outputs look like reset-value violations.
    await Timer(max(1, int(settle_timer_ps)), unit="ps")
    reset.value = reset_active_value
    valid.value = 0
    payload.value = 0
    for signal in metadata_fields.values():
        signal.value = 0
    for _ in range(asserted_cycles):
        await RisingEdge(clock)
        await FallingEdge(clock)

    payload.value = int(value)
    for name, signal in metadata_fields.items():
        signal.value = metadata_values.get(name, 0)
    valid.value = 1
    reset.value = 1 - reset_active_value
    await Timer(max(1, int(settle_timer_ps)), unit="ps")
    if not int(ready.value):
        raise LifecycleDriveError(
            "command READY was not asserted for the first post-reset accepting edge"
        )
    await RisingEdge(clock)
    if accepted_event is not None:
        accepted_event.set()
    await FallingEdge(clock)
    valid.value = 0
    payload.value = 0
    for signal in metadata_fields.values():
        signal.value = 0
    return int(value)


async def wait_clock_cycles(dut: Any, clock_name: str, cycles: int) -> None:
    from cocotb.triggers import RisingEdge

    if cycles < 0:
        raise LifecycleDriveError("cycles must be nonnegative")
    clock = getattr(dut, str(clock_name))
    for _ in range(cycles):
        await RisingEdge(clock)


def assert_lifecycle_status(
    dut: Any, bindings: Mapping[str, Any], **expected: int
) -> None:
    for role, value in expected.items():
        names = list(bindings.get(role, []))
        if len(names) != 1:
            raise LifecycleDriveError(f"status role {role!r} is not uniquely bound")
        observed = int(getattr(dut, str(names[0])).value)
        if observed != int(value):
            raise LifecycleDriveError(
                f"lifecycle status mismatch role={role} expected={value} observed={observed} signal={names[0]}"
            )
