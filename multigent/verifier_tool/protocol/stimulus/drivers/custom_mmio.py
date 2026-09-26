"""LLM-declared custom memory-like protocol drive (`protocol_profile:
custom_mmio`) -- the driver layer for the pattern documented in
`../../../pool/operation_metadata/README.md`'s custom_mmio section.

This is the concrete proof that the memory/adapter/driver split pays off:
it reuses `adapter.OperationMemoryAdapter` (address windows, canonical value
packing) and `_completion_scheduler.RandomCompletionScheduler` (per-id FIFO
ordering with seeded-random relative order across ids) completely
unmodified -- neither was written with this driver in mind, and neither
needed to change to serve it. Only the wire-level field binding is new,
since a custom protocol has no `cocotbext-axi` convenience classes to build
on: this uses `cocotbext.axi.stream.define_stream`, the same generic
stream-primitive factory AXI's own channel classes (`axi_channels.py`,
`axil_channels.py`) are themselves built from, parameterized here by
whatever fields this contract's `request`/`data`/`response` channels
actually declared (no fixed AXI field set to conform to).

A custom_mmio group is one direction only (see the catalog docstring in
`role_pool/standard_protocols.yaml`), so reads and writes are separate
public functions, each taking its own group -- an operation with both
declares two groups and calls both functions.

`id` is optional throughout: bound, requests complete out of issue order
exactly like full AXI4 via the shared scheduler; unbound, every request
lands in the same `None`-keyed FIFO and completes strictly in issue order
(the exact degenerate-case behavior `RandomCompletionScheduler` and the
capture-side engine both already document). `len` on `request` is optional
too: bound, it sizes a read burst exactly like AXI4's ARLEN (`len` beats
plus one); unbound, every read is a single beat. Writes never need a
length field at all -- unlike a read (which this driver must size before
it can start *sending* beats), a write's data channel is a *sink* here, so
it simply accepts beats until `last` (or immediately, if `last` is
unbound) with no length declared in advance, exactly like AXI4's own WLAST
termination.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..adapter import OperationMemoryAdapter, word_count
from ._bus_binding import bind_signal_bus
from ._completion_scheduler import RandomCompletionScheduler


class CustomMmioDriveError(AssertionError):
    """A frozen custom_mmio memory operation cannot be driven with this driver."""


def _bind_bare_channel_bus(dut: Any, channel: Mapping[str, Any]):
    """Like `_bus_binding.bind_channel_bus`, but with no AXI-style kind
    prefix: custom_mmio's `request`/`data`/`response` channels are not AXI,
    so their fields are bound by their own bare names (`addr`, `data`,
    `id`, ...), not `araddr`/`rdata`-style prefixed ones.
    """

    fields = channel.get("fields", {})
    if not isinstance(fields, Mapping):
        raise CustomMmioDriveError(f"channel {channel.get('name')!r} fields must be a mapping")
    signals = {str(field): str(name) for field, name in fields.items()}
    signals["valid"] = str(channel["valid"])
    if not channel.get("ready"):
        raise CustomMmioDriveError(f"channel {channel.get('name')!r} needs a bound ready signal")
    signals["ready"] = str(channel["ready"])
    return bind_signal_bus(dut, signals)


def _stream_classes(field_names: set[str]):
    """`define_stream` is `cocotbext-axi`'s own generic stream-primitive
    factory -- not AXI-specific -- parameterized here by exactly the fields
    this compiled channel declared, so the generated `Sink`/`Source`
    classes' handshake (`.recv()`/`.send()`, queueing, backpressure) is the
    library's, while the field set is this contract's own, whatever it is.
    """

    from cocotbext.axi.stream import define_stream

    return define_stream(
        "CustomMmio", signals=["valid", "ready", *sorted(field_names)],
        valid_signal="valid", ready_signal="ready",
    )


def _require_request_data(group: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if group.get("profile") != "custom_mmio":
        raise CustomMmioDriveError(f"expected a custom_mmio group, got {group.get('profile')!r}")
    channels = group.get("channels", {})
    if "request" not in channels or "data" not in channels:
        raise CustomMmioDriveError(
            f"custom_mmio group {group.get('name')!r} needs request and data channels"
        )
    return dict(channels)


async def execute_custom_mmio_read_job(
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
    timeout_cycles: int = 262_144,
) -> None:
    """Serve every input object's read requests over one custom_mmio group,
    completing out of order exactly like `axi4_outstanding.execute_axi4_memory_job`
    does, via the identical `RandomCompletionScheduler`. `group` must be the
    compiled group covering `operation`'s *inputs* specifically.

    A `resp` field on `data` is optional: if present, `read_error_at`
    injects a non-zero value on the matching request's final beat; if
    absent, `read_error_at` is rejected (there is nothing to signal an
    error with).
    """

    from cocotb.triggers import RisingEdge
    import cocotb

    channels = _require_request_data(group)
    request_channel = channels["request"]
    data_channel = channels["data"]
    request_fields = set(request_channel.get("fields", {}))
    data_fields = set(data_channel.get("fields", {}))
    has_id = "id" in request_fields and "id" in data_fields
    has_len = "len" in request_fields
    has_last = "last" in data_fields
    has_resp = "resp" in data_fields
    if read_error_at is not None and not has_resp:
        raise CustomMmioDriveError("read_error_at requires a resp field bound on the data channel")

    clock = getattr(dut, clock_name)
    _, _, _, RequestSink, _ = _stream_classes(request_fields)
    _, DataTransaction, DataSource, _, _ = _stream_classes(data_fields)
    request_sink = RequestSink(_bind_bare_channel_bus(dut, request_channel), clock)
    data_source = DataSource(_bind_bare_channel_bus(dut, data_channel), clock)
    data_bus = data_source.bus

    memory = OperationMemoryAdapter.load(operation, case, bases)
    dimensions = operation.get("dimensions", {})
    inputs = list(operation.get("inputs", []))
    if any(not isinstance(item.get("memory_mapping"), Mapping) for item in inputs):
        raise CustomMmioDriveError("all custom_mmio input objects need memory_mapping")
    expected_read_words = sum(word_count(b, dimensions) for b in inputs)

    scheduler = RandomCompletionScheduler(clock, seed=seed, max_extra_cycles=max_extra_cycles)
    progress = {"reads": 0}

    async def _serve(request: Any, sequence: int) -> None:
        request_id = int(getattr(request, "id", 0)) if has_id else None
        address = int(request.addr)
        length = int(getattr(request, "len", 0)) + 1 if has_len else 1
        mapping = memory.mapping_for_input_address(address)
        stride = int(mapping["word_stride_bytes"])
        words = memory.read_words(address, length, mapping)
        resp = 2 if read_error_at == sequence else 0

        async def _send() -> None:
            for index, word in enumerate(words):
                beat = DataTransaction()
                if has_id:
                    beat.id = request_id
                beat.data = word
                if has_resp:
                    beat.resp = resp
                if has_last:
                    beat.last = int(index == length - 1)
                await data_source.send(beat)

        await scheduler.schedule(request_id, _send)

    async def _accept() -> None:
        sequence = 0
        while True:
            request = await request_sink.recv()
            sequence += 1
            cocotb.start_soon(_serve(request, sequence))

    async def _count_completions() -> None:
        # Same discipline as axi4_outstanding.py/axi_lite.py: progress must
        # come from observing the real wire, never from Source.send()
        # returning -- send() only enqueues, it does not wait for the item
        # to actually reach the wire.
        while True:
            await RisingEdge(clock)
            if int(data_bus.valid.value) and int(data_bus.ready.value):
                progress["reads"] += 1

    accept_task = cocotb.start_soon(_accept())
    count_task = cocotb.start_soon(_count_completions())
    try:
        for _ in range(timeout_cycles):
            await RisingEdge(clock)
            if progress["reads"] >= expected_read_words:
                return
        raise CustomMmioDriveError(
            f"custom_mmio read job timed out; reads={progress['reads']}/{expected_read_words}"
        )
    finally:
        accept_task.cancel()
        count_task.cancel()


async def execute_custom_mmio_write_job(
    dut: Any,
    clock_name: str,
    group: Mapping[str, Any],
    operation: Mapping[str, Any],
    memory: OperationMemoryAdapter,
    *,
    seed: int | None = None,
    max_extra_cycles: int = 4,
    write_error_at: int | None = None,
    timeout_cycles: int = 262_144,
) -> list[dict[str, int]]:
    """Serve every output object's write requests over one custom_mmio
    group. `group` must be the compiled group covering `operation`'s
    *outputs* specifically; `memory` is shared with the read job's own
    `OperationMemoryAdapter` (pass the same instance) so a job needing both
    directions writes into and reads from one consistent image.

    The `response` channel is genuinely optional (unlike full AXI4, which
    always has BRESP): if the group declares one, this waits for it and
    treats the write as complete only once it fires; if not, acceptance
    onto the `data` channel itself is the completion signal, exactly as
    `pool/operation_metadata/protocol.py`'s capture engine already
    interprets it. `write_error_at` therefore requires a `response`
    channel to exist -- without one, this driver has no subordinate-to-
    manager path to report an error on at all (a `resp` field bound on the
    write `data` channel is DUT-driven, not something this driver sets).

    Returns accepted write beats as `output_beats` (same shape as the AXI
    drivers'), in **wire acceptance order** -- for the single-writer-group
    case this equals logical order, but a caller driving multiple
    concurrently-writing groups should read back through
    `OperationMemoryAdapter.read_output_values` instead for a
    logical-order guarantee.
    """

    from cocotb.triggers import RisingEdge
    import cocotb

    channels = _require_request_data(group)
    request_channel = channels["request"]
    data_channel = channels["data"]
    response_channel = channels.get("response")
    request_fields = set(request_channel.get("fields", {}))
    data_fields = set(data_channel.get("fields", {}))
    response_fields = set(response_channel.get("fields", {})) if response_channel else set()
    # Unlike the read side (where `data` carries the id, like AXI4's RDATA),
    # a write's id is correlated through `request` and `response` (like
    # AXI4's AWID/BID) -- `data` (here a sink we only consume from) plays no
    # part in id correlation at all.
    has_id = "id" in request_fields and (response_channel is None or "id" in response_fields)
    has_last = "last" in data_fields
    if write_error_at is not None and response_channel is None:
        # A `resp` field bound on the *write* `data` channel is DUT-driven
        # (its direction must match the channel's, which is "output" here),
        # so it is something we observe, never something we can set to
        # signal an error -- only a dedicated `response` channel gives this
        # driver a subordinate-to-manager path to report on at all.
        raise CustomMmioDriveError("write_error_at requires a response channel")

    clock = getattr(dut, clock_name)
    _, _, _, RequestSink, _ = _stream_classes(request_fields)
    _, _, _, DataSink, _ = _stream_classes(data_fields)
    request_sink = RequestSink(_bind_bare_channel_bus(dut, request_channel), clock)
    data_sink = DataSink(_bind_bare_channel_bus(dut, data_channel), clock)
    data_bus = data_sink.bus
    response_source = None
    ResponseTransaction = None
    if response_channel is not None:
        _, ResponseTransaction, ResponseSource, _, _ = _stream_classes(response_fields)
        response_source = ResponseSource(_bind_bare_channel_bus(dut, response_channel), clock)

    outputs = list(operation.get("outputs", []))
    if any(not isinstance(item.get("memory_mapping"), Mapping) for item in outputs):
        raise CustomMmioDriveError("all custom_mmio output objects need memory_mapping")
    dimensions = operation.get("dimensions", {})
    expected_write_words = sum(word_count(b, dimensions) for b in outputs)

    scheduler = RandomCompletionScheduler(clock, seed=seed, max_extra_cycles=max_extra_cycles)
    progress = {"writes": 0}
    output_beats: list[dict[str, int]] = []

    async def _serve(request: Any, sequence: int) -> None:
        request_id = int(getattr(request, "id", 0)) if has_id else None
        address = int(request.addr)
        mapping = memory.mapping_for_output_address(address)
        stride = int(mapping["word_stride_bytes"])
        offset = address
        while True:
            # request/data pairing is strict FIFO by acceptance order (like
            # AXI4's AW/W), never by id -- id only correlates a response to
            # its request, exactly as on the read side.
            beat = await data_sink.recv()
            memory.write_word(offset, int(beat.data), mapping)
            output_beats.append({"payload": int(beat.data)})
            offset += stride
            progress["writes"] += 1
            if not has_last or bool(getattr(beat, "last", 1)):
                break
        resp = 2 if write_error_at == sequence else 0

        async def _send() -> None:
            if response_source is not None:
                ack = ResponseTransaction()
                if has_id:
                    ack.id = request_id
                ack.resp = resp
                await response_source.send(ack)
            # else: nothing to send -- acceptance onto `data` above already
            # was the completion signal; `resp` (if bound on `data`) was
            # already set per beat by the caller-visible RTL, not by us.

        await scheduler.schedule(request_id, _send)

    async def _accept() -> None:
        sequence = 0
        while True:
            request = await request_sink.recv()
            sequence += 1
            cocotb.start_soon(_serve(request, sequence))

    accept_task = cocotb.start_soon(_accept())
    try:
        for _ in range(timeout_cycles):
            await RisingEdge(clock)
            if progress["writes"] >= expected_write_words:
                return output_beats
        raise CustomMmioDriveError(
            f"custom_mmio write job timed out; writes={progress['writes']}/{expected_write_words}"
        )
    finally:
        accept_task.cancel()


__all__ = [
    "CustomMmioDriveError",
    "execute_custom_mmio_read_job",
    "execute_custom_mmio_write_job",
]
