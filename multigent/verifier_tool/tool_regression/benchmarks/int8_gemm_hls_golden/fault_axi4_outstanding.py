"""HLS-golden qualification copy of the AXI4 driver with fault injection.

This is the driver -- the thin, wire-protocol-specific layer of the
memory/adapter/driver split documented in
`../../../pool/operation_metadata/README.md`'s custom_mmio section.
`../adapter/` (operation-contract-aware: address windows, canonical value
packing) and `../memory/` (raw byte storage) are the two reusable layers
underneath; nothing address- or object-related is re-derived here.

Built on `cocotbext-axi`'s low-level channel sink/source primitives
(`cocotbext.axi.axi_channels`) directly -- not its `AxiSlave`/`AxiRam`
convenience wrappers -- because those wrappers' own `_process_read`/
`_process_write` loops service one accepted request fully (through its
response) before starting the next: strictly in issue order despite
carrying an ID, which is legal AXI4 behavior but defeats the purpose of
this module, which exists specifically to drive genuinely out-of-order
completions so `operation_metadata/protocol.py`'s capture engine (and,
transitively, any real DUT) is exercised against the corner case the AXI4
spec permits but does not require. This also lets every data object share
one `OperationMemoryAdapter` at independently chosen base addresses, which
`AxiRam`'s own private, single-purpose memory does not support.

Scope: same-ID requests complete in issue order (per AMBA AXI4); different
IDs complete in a seeded-random relative order via `RandomCompletionScheduler`,
reproducible from a fixed seed. `FIXED`, `INCR`, and legal-length `WRAP` bursts
are mapped through the same exact transfer windows used by the AXI checkers.
Aligned byte/halfword transfers and legal unaligned INCR starts use actual
address-selected bus lanes and WSTRB bytes. An `id` field must be bound on the address channels (the scheduler's
key) *and* on the response/read-data channels (so the capture engine this
proves out against can actually see it on the wire) -- a full-AXI4 design
without physical IDs needs a different single-outstanding AXI4 driver; it is
not AXI4-Lite.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, MutableMapping

from multigent.verifier_tool.protocol.assertion.axi import axi_lane_mask, axi_transfer_windows
from multigent.verifier_tool.protocol.stimulus.adapter import OperationMemoryAdapter, word_count
from multigent.verifier_tool.protocol.stimulus.drivers._bus_binding import bind_channel_bus
from multigent.verifier_tool.protocol.stimulus.drivers._completion_scheduler import RandomCompletionScheduler
from multigent.verifier_tool.protocol.stimulus.drivers.axi4_outstanding import (
    Axi4OutstandingDriveError,
)
from .protocol_fault_plan import change_content_on_ready_release, resolved_axi4_fault

AXI4_OUTSTANDING_ID_CHANNELS = ("write_address", "write_response", "read_address", "read_data")


_bind_channel_bus = bind_channel_bus


def _require_channels(
    group: Mapping[str, Any], *, needs_read: bool = True, needs_write: bool = True,
) -> dict[str, Mapping[str, Any]]:
    """`needs_read`/`needs_write` narrow this to a single-capability group --
    e.g. one of three independent read-only/write-only manager ports (real
    Vitis HLS `gmem_a`/`gmem_b`/`gmem_c`-style kernels) rather than one shared
    group carrying both directions. Both default True for the original,
    single-shared-group callers."""

    if group.get("profile") != "axi4" or group.get("endpoint_role") != "manager":
        raise Axi4OutstandingDriveError("memory operation requires one DUT-manager AXI4 group")
    channels = group.get("channels", {})
    required = set()
    if needs_write:
        required |= {"write_address", "write_data", "write_response"}
    if needs_read:
        required |= {"read_address", "read_data"}
    if not required <= set(channels):
        raise Axi4OutstandingDriveError(
            f"AXI4 group is missing channels {sorted(required - set(channels))}"
        )
    for kind in AXI4_OUTSTANDING_ID_CHANNELS:
        if kind not in required:
            continue
        if "id" not in channels[kind].get("fields", {}):
            raise Axi4OutstandingDriveError(
                f"this adapter requires an id field bound on {kind!r} -- both to key the "
                "completion scheduler and so the capture engine can see it on the wire "
                "(a no-ID full-AXI4 design needs a different driver, not AXI4-Lite)"
            )
    return dict(channels)


def _burst_addresses(addr: int, length: int, num_bytes: int, burst: int) -> list[int]:
    try:
        if num_bytes <= 0 or num_bytes & (num_bytes - 1):
            raise ValueError("AXI4 transfer width must be a positive power of two")
        return [
            lower for lower, _upper in axi_transfer_windows(
                {"addr": addr, "len": length - 1, "size": num_bytes.bit_length() - 1,
                 "burst": burst}
            )
        ]
    except ValueError as exc:
        raise Axi4OutstandingDriveError(str(exc)) from exc




async def execute_axi4_memory_job(
    dut: Any,
    clock_name: str,
    group: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    bases: Mapping[str, int],
    *,
    seed: int | None = None,
    max_extra_cycles: int = 4,
    read_error_at: int | None = None,
    write_error_at: int | None = None,
    abort_signal_name: str | None = None,
    reset_signal_name: str | None = None,
    reset_active_value: int = 0,
    stop_after: tuple[str, int] | None = None,
    first_transfer_simultaneous: bool = False,
    initial_sink_stall_cycles: int = 0,
    initial_sink_stall_cycles_by_kind: Mapping[str, int] | None = None,
    write_address_one_cycle_probe: bool = False,
    progress_state: MutableMapping[str, int] | None = None,
    timeout_cycles: int = 262_144,
) -> list[dict[str, int]]:
    """Serve one exact memory job over full AXI4, completing out of order.

    Unlike `axi_lite.py::execute_axi_lite_memory_job`, base addresses are a
    required parameter here rather than computed internally, so a campaign
    can hold them fixed across a whole multi-outstanding scenario while
    varying which requests it issues concurrently. Returns each output
    object's accepted values in correct logical (address) order, read back
    from the shared memory image after every expected write word has been
    accepted -- never from wire arrival order, which a genuinely concurrent
    DUT need not preserve.
    """

    from cocotb.triggers import Edge, Event, FallingEdge, RisingEdge, Timer
    import cocotb
    from cocotbext.axi.axi_channels import AxiAWSink, AxiWSink, AxiBSource, AxiARSink, AxiRSource

    # A binding's own operation may only ever have inputs (a read-only manager
    # port, e.g. a real Vitis HLS `gmem_a`) or only outputs (write-only,
    # `gmem_c`) rather than both directions on one shared group -- narrow
    # which channels this call actually requires/drives accordingly.
    needs_read = bool(operation.get("inputs"))
    needs_write = bool(operation.get("outputs"))
    channels = _require_channels(group, needs_read=needs_read, needs_write=needs_write)
    qualification_fault = resolved_axi4_fault(group)
    clock = getattr(dut, clock_name)

    def _driver_bus(kind: str) -> Any:
        channel = channels[kind]
        lock_metadata = channel.get("field_metadata", {}).get("lock", {})
        legacy_lock = (
            isinstance(lock_metadata, Mapping)
            and lock_metadata.get("physical_encoding") == "legacy_hls_2bit"
        )
        omit = ("lock",) if legacy_lock and "lock" in channel.get("fields", {}) else ()
        return _bind_channel_bus(dut, channel, omit_fields=omit)

    # cocotbext-axi hard-codes AXI4 AxLOCK as one bit.  A Vitis HLS legacy
    # two-bit physical port is still observed by the generated monitor and
    # normalized by our checker, but is intentionally omitted from the memory
    # model's optional bus view; serving memory never depends on AxLOCK.
    aw_channel = AxiAWSink(_driver_bus("write_address"), clock) if needs_write else None
    w_channel = AxiWSink(_bind_channel_bus(dut, channels["write_data"]), clock) if needs_write else None
    b_bus = _bind_channel_bus(dut, channels["write_response"]) if needs_write else None
    b_channel = AxiBSource(b_bus, clock) if needs_write else None
    ar_channel = AxiARSink(_driver_bus("read_address"), clock) if needs_read else None
    r_bus = _bind_channel_bus(dut, channels["read_data"]) if needs_read else None
    r_channel = AxiRSource(r_bus, clock) if needs_read else None

    stall_by_kind = dict(initial_sink_stall_cycles_by_kind or {})
    if initial_sink_stall_cycles < 0 or any(value < 0 for value in stall_by_kind.values()):
        raise Axi4OutstandingDriveError("initial sink stall length must be nonnegative")
    if set(stall_by_kind) - {"write_address", "write_data", "read_address"}:
        raise Axi4OutstandingDriveError("unknown AXI4 sink kind in stall schedule")

    async def _stall_first_transfer(sink: Any, valid_name: str, cycles: int) -> None:
        """Hold READY low for accepted-source evidence, then release it.

        The delay begins only when the DUT presents VALID. This makes the
        one/short/long stall bins deterministic without assuming when the
        operation microarchitecture will issue its first request.
        """

        remaining = cycles
        while remaining:
            await FallingEdge(clock)
            if int(getattr(dut, valid_name).value):
                remaining -= 1
        # Publish READY before the next accepting edge, not after the sink's
        # next _run iteration; otherwise a requested one-cycle hold lasts two.
        sink.ready.value = 1
        sink.pause = False

    if first_transfer_simultaneous and (
        initial_sink_stall_cycles or any(stall_by_kind.values())
        or write_address_one_cycle_probe
    ):
        raise Axi4OutstandingDriveError(
            "simultaneous first transfer and first-transfer stall are exclusive"
        )

    async def _release_on_first_valid(sink: Any, valid_name: str) -> None:
        from cocotb.triggers import Timer

        while True:
            await RisingEdge(clock)
            await Timer(1, unit="ps")
            if int(getattr(dut, valid_name).value):
                sink.ready.value = 1
                sink.pause = False
                return

    async def _release_after_one_sampled_stall(sink: Any, valid_name: str) -> None:
        from cocotb.triggers import Timer

        while True:
            await RisingEdge(clock)
            await Timer(1, unit="ps")
            if int(getattr(dut, valid_name).value):
                await RisingEdge(clock)
                await FallingEdge(clock)
                sink.ready.value = 1
                sink.pause = False
                return

    stall_tasks = []
    if (initial_sink_stall_cycles or any(stall_by_kind.values())
            or first_transfer_simultaneous or write_address_one_cycle_probe):
        for sink, kind in (
            (aw_channel, "write_address"),
            (w_channel, "write_data"),
            (ar_channel, "read_address"),
        ):
            if sink is None:
                continue
            cycles = stall_by_kind.get(kind, initial_sink_stall_cycles)
            one_cycle_probe = write_address_one_cycle_probe and kind == "write_address"
            if not cycles and not first_transfer_simultaneous and not one_cycle_probe:
                continue
            # Set PAUSE before the channel's own _run task can drive READY.
            # Deferring this assignment into a start_soon task lets the first
            # request escape and stalls a later one instead.
            sink.pause = True
            stall_tasks.append(
                cocotb.start_soon(
                    _release_on_first_valid(sink, str(channels[kind]["valid"]))
                    if first_transfer_simultaneous else
                    _release_after_one_sampled_stall(sink, str(channels[kind]["valid"]))
                    if one_cycle_probe else
                    _stall_first_transfer(sink, str(channels[kind]["valid"]), cycles)
                )
            )

    dimensions = operation.get("dimensions", {})
    inputs = list(operation.get("inputs", []))
    outputs = list(operation.get("outputs", []))
    if any(not isinstance(item.get("memory_mapping"), Mapping) for item in (*inputs, *outputs)):
        raise Axi4OutstandingDriveError("all AXI4 objects need memory_mapping")

    memory = OperationMemoryAdapter.load(operation, case, bases)
    expected_read_words = sum(word_count(b, dimensions) for b in inputs)
    expected_write_words = sum(word_count(b, dimensions) for b in outputs)
    expected_write_bytes = sum(
        word_count(binding, dimensions)
        * (int(binding["memory_mapping"]["bus_width_bits"]) // 8)
        for binding in outputs
    )
    if abort_signal_name is not None and (read_error_at is None and write_error_at is None):
        raise Axi4OutstandingDriveError(
            "abort observation requires an injected read or write response error"
        )
    if stop_after is not None and (
        stop_after[0] not in {"read_response", "write_data", "write_response"}
        or stop_after[1] <= 0
        or abort_signal_name is not None
    ):
        raise Axi4OutstandingDriveError(f"invalid AXI4 early-stop target {stop_after!r}")

    read_scheduler = RandomCompletionScheduler(clock, seed=seed, max_extra_cycles=max_extra_cycles)
    write_scheduler = RandomCompletionScheduler(clock, seed=seed, max_extra_cycles=max_extra_cycles)
    # A register-started campaign may need to distinguish "the accepted start
    # produced no memory activity" from "the job ran but never reported
    # completion".  Expose only the already-observed counters through an
    # optional caller-owned mapping; the driver remains the sole writer and
    # no protocol/operation policy leaks into this wire-level module.
    progress = progress_state if progress_state is not None else {}
    progress.update({
        "read_words": 0,
        "write_words": 0,
        "write_bytes": 0,
        "write_requests": 0,
        "write_responses": 0,
    })
    child_tasks: list[Any] = []
    protocol_guard_failures: list[str] = []
    reorder_first_ids: dict[str, int] = {}
    reorder_second_accepted = Event()

    def _response_order_failure(request_id: int, sequence: int) -> str:
        group_name = re.sub(r"[^a-zA-Z0-9_]+", "_", str(group["name"])).strip("_")
        return (
            f"feature=protocol.{group_name}.response_order_preserved_per_id; "
            f"qualification fault attempted to complete request sequence={sequence} "
            f"before an older request with ID={request_id}"
        )

    if qualification_fault is not None:
        fault_name = str(qualification_fault["fault"])
        if fault_name == "invert_rlast_on_nonfinal_or_final_beat" and not needs_read:
            raise Axi4OutstandingDriveError("RLAST fault needs a read-capable AXI4 group")

        async def _present_response_before_request() -> None:
            """Present one response before any matching request is accepted.

            Protocol assertions deliberately check VALID presentation, rather
            than waiting for READY, so this remains a precise negative even if
            the DUT initially backpressures the unsolicited response.
            """

            if needs_read:
                beat = r_channel._transaction_obj()
                beat.rid = 0
                beat.rdata = 0
                beat.rresp = 0
                beat.rlast = 1
                await r_channel.send(beat)
            elif needs_write:
                beat = b_channel._transaction_obj()
                beat.bid = 0
                beat.bresp = 0
                await b_channel.send(beat)
            else:  # Defensive: operation binding validation normally prevents this.
                raise Axi4OutstandingDriveError(
                    "response-before-request fault needs a read or write binding"
                )

        if fault_name == "present_response_before_request":
            child_tasks.append(cocotb.start_soon(_present_response_before_request()))
        elif fault_name == "change_content_on_ready_release":
            bus = r_bus if needs_read else b_bus
            child_tasks.append(cocotb.start_soon(change_content_on_ready_release(
                clock,
                bus.rvalid if needs_read else bus.bvalid,
                bus.rready if needs_read else bus.bready,
                bus.rdata if needs_read else bus.bresp,
            )))

    async def _serve_read(ar: Any, sequence: int) -> None:
        arid = int(getattr(ar, "arid", 0))
        addr = int(ar.araddr)
        length = int(getattr(ar, "arlen", 0)) + 1
        size = int(getattr(ar, "arsize", 2))
        burst = int(getattr(ar, "arburst", 1))
        num_bytes = 2 ** size
        mapping = memory.mapping_for_input_address(addr)
        windows = axi_transfer_windows(
            {"addr": addr, "len": length - 1, "size": size, "burst": burst}
        )
        words = [memory.read_bus_word(lower, mapping) for lower, _upper in windows]
        fault_here = bool(
            qualification_fault
            and int(qualification_fault["occurrence"]) == sequence
        )
        resp = 2 if read_error_at == sequence else 0
        if fault_here and qualification_fault["fault"] == "return_exokay_for_nonexclusive_request":
            resp = 1

        async def _send() -> None:
            if (
                qualification_fault
                and qualification_fault["fault"] == "attempt_same_id_response_reorder"
                and sequence == 1
            ):
                await reorder_second_accepted.wait()
            for index, word in enumerate(words):
                beat = r_channel._transaction_obj()
                beat.rid = (
                    arid ^ 1
                    if fault_here and qualification_fault["fault"] == "return_nonmatching_id"
                    else arid
                )
                beat.rdata = word
                beat.rresp = resp
                normal_last = int(index == length - 1)
                beat.rlast = (
                    1 - normal_last
                    if fault_here
                    and qualification_fault["fault"] == "invert_rlast_on_nonfinal_or_final_beat"
                    and index == 0
                    else normal_last
                )
                await r_channel.send(beat)

        await read_scheduler.schedule(arid, _send)

    async def _serve_write(aw: Any, sequence: int) -> None:
        awid = int(getattr(aw, "awid", 0))
        addr = int(aw.awaddr)
        length = int(getattr(aw, "awlen", 0)) + 1
        size = int(getattr(aw, "awsize", 2))
        burst = int(getattr(aw, "awburst", 1))
        num_bytes = 2 ** size
        mapping = memory.mapping_for_output_address(addr)
        bus_bytes = int(mapping["bus_width_bits"]) // 8
        if num_bytes > bus_bytes:
            raise Axi4OutstandingDriveError(
                f"AXI4 transfer size {num_bytes} exceeds bus width {bus_bytes}"
            )
        windows = axi_transfer_windows(
            {"addr": addr, "len": length - 1, "size": size, "burst": burst}
        )
        permit_invalid_strobe = bool(
            qualification_fault
            and qualification_fault["fault"]
            == "accept_invalid_write_strobe_for_checker"
            and int(qualification_fault["occurrence"]) == sequence
        )
        for lower, upper in windows:
            w = await w_channel.recv()
            active_strobe = axi_lane_mask((lower, upper), bus_bytes)
            strb = int(getattr(w, "wstrb", active_strobe))
            if strb != active_strobe and not permit_invalid_strobe:
                raise Axi4OutstandingDriveError(
                    f"DUT emitted WSTRB={strb:#x}, expected active lanes {active_strobe:#x}"
                )
            memory.write_strobed_bus_word(lower, int(w.wdata), strb, mapping)
            # w_channel is a Sink: recv() only returns after the real wire
            # handshake was sampled, so counting here (unlike the read side
            # below) is safe -- no "queued but not yet on the wire" race.
            progress["write_words"] += 1
            progress["write_bytes"] += strb.bit_count()
        fault_here = bool(
            qualification_fault
            and int(qualification_fault["occurrence"]) == sequence
        )
        resp = 2 if write_error_at == sequence else 0
        if fault_here and qualification_fault["fault"] == "return_exokay_for_nonexclusive_request":
            resp = 1

        async def _send() -> None:
            if (
                qualification_fault
                and qualification_fault["fault"] == "attempt_same_id_response_reorder"
                and sequence == 1
            ):
                await reorder_second_accepted.wait()
            beat = b_channel._transaction_obj()
            beat.bid = (
                awid ^ 1
                if fault_here and qualification_fault["fault"] == "return_nonmatching_id"
                else awid
            )
            beat.bresp = resp
            await b_channel.send(beat)

        await write_scheduler.schedule(awid, _send)

    async def _accept_reads() -> None:
        sequence = 0
        while True:
            ar = await ar_channel.recv()
            sequence += 1
            if (
                qualification_fault
                and qualification_fault["fault"] == "attempt_same_id_response_reorder"
            ):
                request_id = int(getattr(ar, "arid", 0))
                if sequence == 1:
                    reorder_first_ids["read"] = request_id
                if int(qualification_fault["occurrence"]) == sequence:
                    if reorder_first_ids.get("read") == request_id:
                        protocol_guard_failures.append(
                            _response_order_failure(request_id, sequence)
                        )
                    reorder_second_accepted.set()
            child_tasks.append(cocotb.start_soon(_serve_read(ar, sequence)))

    async def _accept_writes() -> None:
        sequence = 0
        while True:
            aw = await aw_channel.recv()
            sequence += 1
            progress["write_requests"] += 1
            if (
                qualification_fault
                and qualification_fault["fault"] == "attempt_same_id_response_reorder"
            ):
                request_id = int(getattr(aw, "awid", 0))
                if sequence == 1:
                    reorder_first_ids["write"] = request_id
                if int(qualification_fault["occurrence"]) == sequence:
                    if reorder_first_ids.get("write") == request_id:
                        protocol_guard_failures.append(
                            _response_order_failure(request_id, sequence)
                        )
                    reorder_second_accepted.set()
            child_tasks.append(cocotb.start_soon(_serve_write(aw, sequence)))

    async def _count_read_completions() -> None:
        # r_channel is a Source: send() only enqueues, it does not wait for
        # the item to actually reach the wire, so progress must be counted
        # from a direct, independent observation of the real RVALID/RREADY
        # handshake -- exactly the same "never trust queue state as if it
        # were wire state" discipline axi_lite.py's hand-rolled loop uses.
        while True:
            await RisingEdge(clock)
            if int(r_bus.rvalid.value) and int(r_bus.rready.value):
                progress["read_words"] += 1

    async def _count_write_responses() -> None:
        while True:
            await RisingEdge(clock)
            if int(b_bus.bvalid.value) and int(b_bus.bready.value):
                progress["write_responses"] += 1

    read_task = cocotb.start_soon(_accept_reads()) if needs_read else None
    write_task = cocotb.start_soon(_accept_writes()) if needs_write else None
    count_task = cocotb.start_soon(_count_read_completions()) if needs_read else None
    response_task = cocotb.start_soon(_count_write_responses()) if needs_write else None
    try:
        for _ in range(timeout_cycles):
            await RisingEdge(clock)
            if protocol_guard_failures:
                raise Axi4OutstandingDriveError(protocol_guard_failures[0])
            if abort_signal_name is not None and int(getattr(dut, abort_signal_name).value):
                break
            if stop_after is not None:
                counter = (
                    "read_words" if stop_after[0] == "read_response"
                    else "write_words" if stop_after[0] == "write_data"
                    else "write_responses"
                )
                if progress[counter] >= stop_after[1]:
                    break
            if (
                progress["read_words"] >= expected_read_words
                and progress["write_bytes"] >= expected_write_bytes
                and (
                    expected_write_bytes == 0
                    or (
                        progress["write_requests"] > 0
                        and progress["write_responses"] >= progress["write_requests"]
                    )
                )
            ):
                break
        else:
            raise Axi4OutstandingDriveError(
                f"AXI4 memory job timed out; reads={progress['read_words']}/{expected_read_words} "
                f"writes={progress['write_words']}/{expected_write_words} minimum beats, "
                f"bytes={progress['write_bytes']}/{expected_write_bytes} "
                f"write_responses={progress['write_responses']}/{progress['write_requests']}"
            )
    finally:
        for task in (read_task, write_task, count_task, response_task):
            if task is not None:
                task.cancel()
        for task in stall_tasks:
            task.cancel()
        for task in child_tasks:
            task.cancel()
        # cocotbext-axi channel constructors start their own _run() tasks.
        # Leaving them alive makes old sinks/sources drive the next job's
        # READY/VALID wires concurrently and silently corrupts coverage.
        for channel in (aw_channel, w_channel, b_channel, ar_channel, r_channel):
            if channel is None:
                continue
            channel.clear_pause_generator()
            if channel._run_cr is not None:
                channel._run_cr.cancel()
                channel._run_cr = None
        # A cancelled multi-beat source may still own a stalled VALID. AXI
        # requires that VALID to remain asserted until transfer or reset; do
        # not withdraw it at cleanup merely because an error/abort ended the
        # job. Release it on the *reset transition* before the next clock edge.
        async def _clear_stalled_valid_on_reset(valid: Any) -> None:
            reset = getattr(dut, reset_signal_name)
            while int(reset.value) != reset_active_value:
                await Edge(reset)
            await Timer(1, unit="ps")
            valid.value = 0

        for bus in (r_bus, b_bus):
            if bus is None:
                continue
            valid, ready = bus.rvalid if bus is r_bus else bus.bvalid, bus.rready if bus is r_bus else bus.bready
            if int(valid.value) and not int(ready.value) and reset_signal_name:
                cocotb.start_soon(_clear_stalled_valid_on_reset(valid))
            else:
                valid.value = 0

    outputs_in_order: list[dict[str, int]] = []
    for binding in outputs:
        for value in memory.read_output_values(binding, dimensions, bases):
            outputs_in_order.append({"payload": value})
    return outputs_in_order


__all__ = [
    "Axi4OutstandingDriveError",
    "RandomCompletionScheduler",
    "execute_axi4_memory_job",
]
