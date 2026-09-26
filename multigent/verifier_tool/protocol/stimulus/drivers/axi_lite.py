"""Executable AXI4-Lite memory-subordinate model for code-owned operations."""

from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Any, Mapping, Sequence

from ..adapter import OperationMemoryAdapter, pack_words, word_count
from ._bus_binding import bind_channel_bus

# `lifecycle.stimulus` imports `protocol.stimulus.cocotb`, and this package's
# own __init__ pulls in this module via `.drivers` -- a module-level import
# here would be circular. Deferred to call time instead, consistent with
# this file's other cocotb-only imports below.


class AxiLiteMemoryDriveError(AssertionError):
    """A frozen AXI4-Lite memory operation cannot be driven unambiguously."""


class _FaultInjectingTarget:
    """Byte-addressable target for `cocotbext.axi.axil_slave`, wrapping the
    shared `OperationMemoryAdapter` with error injection at a specific request.

    `AxiLiteSlaveWrite`/`AxiLiteSlaveRead` already set BRESP/RRESP to SLVERR
    whenever a `target.write`/`target.read` call raises -- so injecting an
    error at exactly the Nth request is just counting calls and raising on
    the matching one, entirely on top of the library's own error handling,
    not a reimplementation of it. Also records every accepted write, in
    order, since that IS this file's `output_beats` return value.
    """

    def __init__(
        self,
        memory: OperationMemoryAdapter,
        *,
        byte_lanes: int,
        read_error_at: int | None,
        write_error_at: int | None,
    ) -> None:
        self._memory = memory
        self._byte_lanes = byte_lanes
        self._read_error_at = read_error_at
        self._write_error_at = write_error_at
        self.read_count = 0
        self.write_count = 0
        self.accepted_writes: list[int] = []

    async def read(self, address: int, length: int) -> bytes:
        self.read_count += 1
        if self._read_error_at == self.read_count:
            raise AxiLiteMemoryDriveError(f"injected read error at read #{self.read_count}")
        return bytes(self._memory.mem.read(address, length))

    async def write(self, address: int, data: bytes) -> None:
        if len(data) != self._byte_lanes:
            raise AxiLiteMemoryDriveError(
                f"DUT emitted a non-full-width write ({len(data)} of {self._byte_lanes} bytes)"
            )
        self.write_count += 1
        if self._write_error_at == self.write_count:
            raise AxiLiteMemoryDriveError(f"injected write error at write #{self.write_count}")
        self.accepted_writes.append(int.from_bytes(data, "little"))
        self._memory.mem.write(address, data)


def _handle(dut: Any, name: str) -> Any:
    if not name or not hasattr(dut, name):
        raise AxiLiteMemoryDriveError(f"DUT is missing AXI4-Lite signal {name!r}")
    return getattr(dut, name)


def _elements(binding: Mapping[str, Any], dimensions: Mapping[str, Any]) -> int:
    extents = [dimensions.get(str(axis)) for axis in binding.get("dimensions", [])]
    if extents and all(isinstance(value, int) and value > 0 for value in extents):
        return prod(map(int, extents))
    if not extents:
        return 1
    raise AxiLiteMemoryDriveError(
        f"binding {binding.get('data_object')!r} has unresolved dimensions {extents!r}"
    )


def default_axi_lite_memory_bases(
    operation: Mapping[str, Any], *, variant: str = "interior",
    aligned_tail_beats: int | None = None,
) -> dict[str, int]:
    """Choose non-overlapping aligned bases that close legal address partitions."""

    bindings = [*operation.get("inputs", []), *operation.get("outputs", [])]
    if any(not isinstance(item.get("memory_mapping"), Mapping) for item in bindings):
        raise AxiLiteMemoryDriveError("all AXI4-Lite objects need memory_mapping")
    defaults = [0x0001_0000, 0x0002_0000, 0x0003_0000, 0x0004_0000]
    result = {
        str(binding["data_object"]): defaults[index]
        for index, binding in enumerate(bindings)
    }
    dimensions = operation.get("dimensions", {})

    def page_edge_base(binding: Mapping[str, Any]) -> int:
        mapping = binding["memory_mapping"]
        stride = int(mapping["word_stride_bytes"])
        bus_bytes = int(mapping["bus_width_bits"]) // 8
        count = word_count(binding, dimensions)
        start = 0x1000 - (count - 1) * stride - bus_bytes
        if start < 0 or start % bus_bytes:
            raise AxiLiteMemoryDriveError(
                f"{binding['data_object']!r} cannot end on a 4-KiB page edge "
                f"with {count} words, stride {stride}, and bus width {bus_bytes} bytes"
            )
        return start

    if variant == "read_zero":
        result[str(operation["inputs"][0]["data_object"])] = 0
    elif variant == "write_zero":
        result[str(operation["outputs"][0]["data_object"])] = 0
    elif variant == "read_page_edge":
        binding = operation["inputs"][0]
        result[str(binding["data_object"])] = page_edge_base(binding)
    elif variant == "write_page_edge":
        binding = operation["outputs"][0]
        result[str(binding["data_object"])] = page_edge_base(binding)
    elif variant != "interior":
        raise AxiLiteMemoryDriveError(f"unknown AXI4-Lite base variant {variant!r}")
    if aligned_tail_beats is not None:
        if variant != "interior" or aligned_tail_beats <= 0:
            raise AxiLiteMemoryDriveError(
                "aligned_tail_beats needs a positive count and the interior base variant"
            )
        for binding in bindings:
            mapping = binding["memory_mapping"]
            bus_bytes = int(mapping["bus_width_bits"]) // 8
            if bus_bytes <= 0 or 4096 % bus_bytes:
                raise AxiLiteMemoryDriveError("bus word must divide the 4-KiB AXI boundary")
            page_beats = 4096 // bus_bytes
            count = word_count(binding, dimensions)
            if count <= aligned_tail_beats or aligned_tail_beats >= page_beats:
                raise AxiLiteMemoryDriveError(
                    f"{binding['data_object']!r} cannot form a {aligned_tail_beats}-beat "
                    "tail after a 4-KiB split"
                )
            offset_beats = (page_beats - ((count - aligned_tail_beats) % page_beats)) % page_beats
            result[str(binding["data_object"])] += offset_beats * bus_bytes
    return result


@dataclass
class _ReadyPolicy:
    mode: str = "ready_before_valid"
    stall_cycles: int = 0
    seen_valid_cycles: int = 0
    first_transfer_complete: bool = False

    def value(self, valid: bool) -> int:
        if self.first_transfer_complete or self.mode == "ready_before_valid":
            return 1
        if self.mode == "simultaneous":
            return int(valid)
        if self.mode == "valid_before_ready":
            if valid:
                self.seen_valid_cycles += 1
            return int(valid and self.seen_valid_cycles > self.stall_cycles)
        raise AxiLiteMemoryDriveError(f"unknown READY policy {self.mode!r}")

    def accepted(self) -> None:
        self.first_transfer_complete = True


async def _serve_via_cocotbext_axi(
    dut: Any,
    clock_name: str,
    channels: Mapping[str, Mapping[str, Any]],
    memory: OperationMemoryAdapter,
    command_metadata: Mapping[str, int],
    command: Mapping[str, Any],
    *,
    expected_reads: int,
    expected_writes: int,
    stop_after: tuple[str, int] | None,
    read_error_at: int | None,
    write_error_at: int | None,
    timeout_cycles: int,
) -> list[dict[str, int]]:
    """Serve one job's read-address-channel default-timing AW/W/B/AR/R
    exchange through `cocotbext-axi`'s own AXI4-Lite slave model instead of
    hand-rolled signal driving -- see `execute_axi_lite_memory_job`'s call
    site for exactly which cases this is (and is not) used for.
    """

    from cocotb.triggers import FallingEdge, RisingEdge
    import cocotb
    from cocotbext.axi.axil_channels import AxiLiteWriteBus, AxiLiteReadBus
    from cocotbext.axi.axil_slave import AxiLiteSlaveWrite, AxiLiteSlaveRead
    from multigent.verifier_tool.lifecycle.stimulus import drive_accepted_command

    aw, w, b = (channels[name] for name in ("write_address", "write_data", "write_response"))
    ar, r = (channels[name] for name in ("read_address", "read_data"))
    clock = _handle(dut, clock_name)

    write_bus = AxiLiteWriteBus(
        aw=bind_channel_bus(dut, aw), w=bind_channel_bus(dut, w), b=bind_channel_bus(dut, b)
    )
    read_bus = AxiLiteReadBus(ar=bind_channel_bus(dut, ar), r=bind_channel_bus(dut, r))

    byte_lanes = int(w["widths"]["data"]) // 8
    target = _FaultInjectingTarget(
        memory, byte_lanes=byte_lanes, read_error_at=read_error_at, write_error_at=write_error_at
    )
    write_model = AxiLiteSlaveWrite(write_bus, clock, target=target)
    read_model = AxiLiteSlaveRead(read_bus, clock, target=target)

    command_task = cocotb.start_soon(
        drive_accepted_command(
            dut,
            clock_name,
            command,
            int(command["legal_values"][0]),
            metadata_values=command_metadata,
            timeout_cycles=timeout_cycles,
        )
    )

    # Progress (and any non-OKAY response, injected or otherwise) must be
    # observed from the real wire, never inferred from target.read/write
    # call counts: a call happens the instant a request is *accepted*, one
    # or more cycles before its response actually reaches RVALID/BVALID.
    progress = {"reads": 0, "writes": 0, "error_fired": False}

    async def _count_responses() -> None:
        r_bus = read_model.r_channel.bus
        b_bus = write_model.b_channel.bus
        while True:
            await RisingEdge(clock)
            if int(r_bus.rvalid.value) and int(r_bus.rready.value):
                progress["reads"] += 1
                if int(r_bus.rresp.value) != 0:
                    progress["error_fired"] = True
            if int(b_bus.bvalid.value) and int(b_bus.bready.value):
                progress["writes"] += 1
                if int(b_bus.bresp.value) != 0:
                    progress["error_fired"] = True

    count_task = cocotb.start_soon(_count_responses())
    timed_out = True
    try:
        for _ in range(timeout_cycles):
            await RisingEdge(clock)
            stop_now = bool(
                stop_after
                and (
                    (stop_after[0] == "read_response" and progress["reads"] >= int(stop_after[1]))
                    or (stop_after[0] == "write_response" and progress["writes"] >= int(stop_after[1]))
                )
            )
            if (
                stop_now
                or progress["error_fired"]
                or (progress["reads"] >= expected_reads and progress["writes"] >= expected_writes)
            ):
                timed_out = False
                # Tear down on the quiet half-cycle, not in the same scheduler
                # phase that observed the response handshake.
                await FallingEdge(clock)
                break
        if timed_out:
            raise AxiLiteMemoryDriveError(
                f"AXI4-Lite memory job timed out; reads={progress['reads']}/{expected_reads} "
                f"writes={progress['writes']}/{expected_writes}"
            )
        if not command_task.done():
            await command_task
    finally:
        count_task.cancel()
        # `_process_write_cr`/`_process_read_cr` are the library's own
        # internal accept/respond coroutines -- not part of its advertised
        # public API, but the only handle available to end one job cleanly
        # before the next job binds fresh models to these same DUT signals.
        if write_model._process_write_cr is not None:
            write_model._process_write_cr.cancel()
        if read_model._process_read_cr is not None:
            read_model._process_read_cr.cancel()
        write_model.b_channel.bus.bvalid.value = 0
        read_model.r_channel.bus.rvalid.value = 0
        for sink in (write_model.aw_channel, write_model.w_channel, read_model.ar_channel):
            getattr(sink.bus, sink._ready_signal).value = 0
        if not command_task.done():
            command_task.cancel()

    return [{"payload": value} for value in target.accepted_writes]


def _group_channels(group: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if group.get("profile") != "axi4_lite" or group.get("endpoint_role") != "manager":
        raise AxiLiteMemoryDriveError(
            "memory operation requires one DUT-manager AXI4-Lite group"
        )
    channels = group.get("channels", {})
    required = {
        "write_address", "write_data", "write_response", "read_address", "read_data"
    }
    if not required <= set(channels):
        raise AxiLiteMemoryDriveError(
            f"AXI4-Lite group is missing channels {sorted(required - set(channels))}"
        )
    return channels


async def execute_axi_lite_memory_job(
    dut: Any,
    clock_name: str,
    group: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    base_variant: str = "interior",
    ready_modes: Mapping[str, tuple[str, int]] | None = None,
    stop_after: tuple[str, int] | None = None,
    read_error_at: int | None = None,
    write_error_at: int | None = None,
    timeout_cycles: int = 262_144,
) -> list[dict[str, int]]:
    """Serve one exact memory job and return accepted output data beats.

    Requests are observed from the DUT. Read data comes only from the addressed
    code-owned memory image; writes are paired from independently accepted AW/W
    transfers and retired only by accepted BRESP. Responses are never presented
    in the same sampling window as their prerequisite request.
    """

    from cocotb.triggers import FallingEdge, RisingEdge, Timer
    from multigent.verifier_tool.lifecycle.stimulus import drive_accepted_command

    channels = _group_channels(group)
    if stop_after is not None and (
        stop_after[0] not in {"read_response", "write_response"}
        or int(stop_after[1]) < 1
    ):
        raise AxiLiteMemoryDriveError(f"invalid stop_after={stop_after!r}")
    aw, w, b = (channels[name] for name in ("write_address", "write_data", "write_response"))
    ar, r = (channels[name] for name in ("read_address", "read_data"))
    clock = _handle(dut, clock_name)
    ready_modes = dict(ready_modes or {})
    policies = {
        kind: _ReadyPolicy(*ready_modes.get(kind, ("ready_before_valid", 0)))
        for kind in ("write_address", "write_data", "read_address")
    }

    dimensions = operation.get("dimensions", {})
    bindings = [*operation.get("inputs", []), *operation.get("outputs", [])]
    bases = default_axi_lite_memory_bases(operation, variant=base_variant)
    # Storage lives in the same protocol-agnostic memory model full-AXI4
    # driving uses (`axi4_outstanding.py`) -- only the raw byte width needed
    # for a bare, no-object-context word access is derived here, since a
    # single-outstanding AXI4-Lite exchange never needs to know which bound
    # object an address belongs to in order to store or fetch a word.
    memory = OperationMemoryAdapter(size=2**32)
    _raw_word_bytes = int(w["widths"]["data"]) // 8
    raw_mapping = {"bus_width_bits": int(w["widths"]["data"]), "word_stride_bytes": _raw_word_bytes}
    command_metadata: dict[str, int] = {}
    expected_reads = 0
    expected_writes = 0
    for binding in bindings:
        mapping = binding.get("memory_mapping", {})
        object_name = str(binding["data_object"])
        base = int(bases[object_name])
        command_metadata[str(mapping["base_signal"])] = base
        if binding.get("direction") != "input":
            expected_writes += (
                _elements(binding, dimensions) + int(mapping["elements_per_word"]) - 1
            ) // int(mapping["elements_per_word"])
            continue
        values = case.get("stimulus", {}).get(object_name)
        if not isinstance(values, list):
            raise AxiLiteMemoryDriveError(f"case is missing canonical input {object_name!r}")
        words = pack_words(values, binding, dimensions)
        stride = int(mapping["word_stride_bytes"])
        for index, word in enumerate(words):
            memory.write_word(base + stride * index, word, mapping)
        expected_reads += len(words)

    commands = list(operation.get("lifecycle", {}).get("job_accept_channels", []))
    if len(commands) != 1 or not commands[0].get("legal_values"):
        raise AxiLiteMemoryDriveError("AXI4-Lite job needs one resolved legal command")

    # `ready_modes` needs cycle-accurate control of when AWREADY/WREADY/ARREADY
    # assert, which is what the hand-rolled loop below (`_ReadyPolicy`) exists
    # for. cocotbext-axi's own accept-side primitives always assert ready as
    # soon as they are able; retargeting `_ReadyPolicy`'s exact per-cycle
    # decision onto their `.pause` property is possible in principle but its
    # exact registration timing relative to this tool's FallingEdge-sampled
    # discipline was not verified here, and campaign.py's ready-mode coverage
    # sweep depends on this being exactly right -- so only the *default*
    # ready policy (every real automatic-campaign case except that one sweep)
    # is served through the library; a genuinely custom `ready_modes` falls
    # back to the original, fully verified hand-rolled loop unchanged.
    uses_default_ready_policy = all(
        ready_modes.get(kind, ("ready_before_valid", 0)) == ("ready_before_valid", 0)
        for kind in ("write_address", "write_data", "read_address")
    )
    if uses_default_ready_policy:
        return await _serve_via_cocotbext_axi(
            dut,
            clock_name,
            channels,
            memory,
            command_metadata,
            commands[0],
            expected_reads=expected_reads,
            expected_writes=expected_writes,
            stop_after=stop_after,
            read_error_at=read_error_at,
            write_error_at=write_error_at,
            timeout_cycles=timeout_cycles,
        )

    tb_driven = {
        str(aw["ready"]): 0,
        str(w["ready"]): 0,
        str(ar["ready"]): 0,
        str(b["valid"]): 0,
        str(b["fields"]["resp"]): 0,
        str(r["valid"]): 0,
        str(r["fields"]["data"]): 0,
        str(r["fields"]["resp"]): 0,
    }
    for name, value in tb_driven.items():
        _handle(dut, name).value = value

    pending_aw: list[int] = []
    pending_w: list[dict[str, int]] = []
    pending_b: list[tuple[int, int]] = []
    pending_r: list[tuple[int, int, int]] = []
    b_active: tuple[int, int] | None = None
    r_active: tuple[int, int, int] | None = None
    read_requests = 0
    write_requests = 0
    read_responses = 0
    write_responses = 0
    output_beats: list[dict[str, int]] = []

    import cocotb

    command_task = cocotb.start_soon(
        drive_accepted_command(
            dut,
            clock_name,
            commands[0],
            int(commands[0]["legal_values"][0]),
            metadata_values=command_metadata,
            timeout_cycles=timeout_cycles,
        )
    )
    try:
        for _ in range(timeout_cycles):
            await FallingEdge(clock)
            aw_valid = bool(int(_handle(dut, str(aw["valid"])).value))
            w_valid = bool(int(_handle(dut, str(w["valid"])).value))
            ar_valid = bool(int(_handle(dut, str(ar["valid"])).value))
            aw_ready = policies["write_address"].value(aw_valid)
            w_ready = policies["write_data"].value(w_valid)
            ar_ready = policies["read_address"].value(ar_valid)
            _handle(dut, str(aw["ready"])).value = aw_ready
            _handle(dut, str(w["ready"])).value = w_ready
            _handle(dut, str(ar["ready"])).value = ar_ready

            # Wait for DUT-owned READY before presenting TB-owned responses. This
            # makes the controllable response-channel order ready-before-valid.
            if not r_active and pending_r and int(_handle(dut, str(r["ready"])).value):
                r_active = pending_r.pop(0)
            if r_active is not None:
                _handle(dut, str(r["fields"]["data"])).value = r_active[1]
                _handle(dut, str(r["fields"]["resp"])).value = r_active[2]
                _handle(dut, str(r["valid"])).value = 1
            else:
                _handle(dut, str(r["valid"])).value = 0
            if b_active is None and pending_b and int(_handle(dut, str(b["ready"])).value):
                b_active = pending_b.pop(0)
            _handle(dut, str(b["valid"])).value = int(b_active is not None)
            _handle(dut, str(b["fields"]["resp"])).value = (
                0 if b_active is None else b_active[1]
            )

            await Timer(1, unit="ps")
            aw_fire = aw_valid and bool(aw_ready)
            w_fire = w_valid and bool(w_ready)
            ar_fire = ar_valid and bool(ar_ready)
            r_fire = r_active is not None and bool(int(_handle(dut, str(r["ready"])).value))
            b_fire = b_active is not None and bool(int(_handle(dut, str(b["ready"])).value))
            r_response = 0 if r_active is None else int(r_active[2])
            b_response = 0 if b_active is None else int(b_active[1])
            aw_value = int(_handle(dut, str(aw["fields"]["addr"])).value)
            w_value = {
                "data": int(_handle(dut, str(w["fields"]["data"])).value),
                "strb": int(_handle(dut, str(w["fields"]["strb"])).value),
            }
            ar_value = int(_handle(dut, str(ar["fields"]["addr"])).value)
            await RisingEdge(clock)

            if aw_fire:
                pending_aw.append(aw_value)
                policies["write_address"].accepted()
            if w_fire:
                pending_w.append(w_value)
                policies["write_data"].accepted()
            if ar_fire:
                read_requests += 1
                pending_r.append(
                    (
                        ar_value,
                        int(memory.read_words(ar_value, 1, raw_mapping)[0]),
                        2 if read_error_at == read_requests else 0,
                    )
                )
                policies["read_address"].accepted()
            while pending_aw and pending_w:
                address = pending_aw.pop(0)
                beat = pending_w.pop(0)
                full_strobe = (1 << int(w["widths"]["strb"])) - 1
                if beat["strb"] != full_strobe:
                    raise AxiLiteMemoryDriveError(
                        f"DUT emitted WSTRB={beat['strb']:#x}, expected {full_strobe:#x}"
                    )
                memory.write_word(address, int(beat["data"]), raw_mapping)
                output_beats.append({"payload": int(beat["data"])})
                write_requests += 1
                pending_b.append(
                    (address, 2 if write_error_at == write_requests else 0)
                )
            if r_fire:
                read_responses += 1
                r_active = None
            if b_fire:
                write_responses += 1
                b_active = None

            stop_now = bool(
                stop_after
                and (
                    (stop_after[0] == "read_response" and read_responses >= int(stop_after[1]))
                    or (stop_after[0] == "write_response" and write_responses >= int(stop_after[1]))
                )
            )
            stop_now |= bool((r_fire and r_response != 0) or (b_fire and b_response != 0))

            if stop_now or (
                read_responses == expected_reads
                and write_responses == expected_writes
                and not any((pending_aw, pending_w, pending_b, pending_r))
                and r_active is None
                and b_active is None
            ):
                await FallingEdge(clock)
                _handle(dut, str(r["valid"])).value = 0
                _handle(dut, str(b["valid"])).value = 0
                _handle(dut, str(aw["ready"])).value = 0
                _handle(dut, str(w["ready"])).value = 0
                _handle(dut, str(ar["ready"])).value = 0
                await command_task
                return output_beats
        raise AxiLiteMemoryDriveError(
            f"AXI4-Lite memory job timed out; reads={read_responses}/{expected_reads} "
            f"writes={write_responses}/{expected_writes}"
        )
    finally:
        if not command_task.done():
            command_task.cancel()


__all__ = [
    "AxiLiteMemoryDriveError",
    "default_axi_lite_memory_bases",
    "execute_axi_lite_memory_job",
]
