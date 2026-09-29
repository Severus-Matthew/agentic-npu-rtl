"""Shared protocol-driver utilities remain protocol neutral and single-copy."""

from __future__ import annotations

import asyncio

import cocotb.triggers
import pytest

from multigent.verifier_tool.protocol.stimulus.drivers import _bus_binding
from multigent.verifier_tool.protocol.stimulus.drivers._completion_scheduler import (
    RandomCompletionScheduler,
)
from multigent.verifier_tool.protocol.stimulus.drivers.axi4_outstanding import (
    Axi4OutstandingDriveError,
    RandomCompletionScheduler as Axi4CompletionScheduler,
    _burst_addresses,
)
from multigent.verifier_tool.protocol.stimulus.drivers.axi_lite import (
    default_axi_lite_memory_bases,
)
from multigent.verifier_tool.protocol.stimulus.drivers.custom_mmio import (
    RandomCompletionScheduler as CustomMmioCompletionScheduler,
    _bind_bare_channel_bus,
)
from multigent.verifier_tool.protocol.stimulus.adapter import OperationMemoryAdapter


class _FakeBus:
    def __init__(self, dut, name, *, signals, bus_separator):
        self.dut = dut
        self.name = name
        self.signals = signals
        self.bus_separator = bus_separator


def test_axi4_and_custom_mmio_share_protocol_neutral_completion_scheduler() -> None:
    assert Axi4CompletionScheduler is RandomCompletionScheduler
    assert CustomMmioCompletionScheduler is RandomCompletionScheduler
    assert RandomCompletionScheduler.__module__.endswith("._completion_scheduler")


def test_completion_scheduler_preserves_fifo_within_one_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-ID ordering is a responder-driver invariant, not a passive rule."""

    class AsyncEvent:
        def __init__(self) -> None:
            self._event = asyncio.Event()

        async def wait(self) -> None:
            await self._event.wait()

        def set(self) -> None:
            self._event.set()

    async def edge(_clock) -> None:
        await asyncio.sleep(0)

    monkeypatch.setattr(cocotb.triggers, "Event", AsyncEvent)
    monkeypatch.setattr(cocotb.triggers, "RisingEdge", edge)

    async def exercise() -> None:
        scheduler = RandomCompletionScheduler(object(), seed=7, max_extra_cycles=0)
        first_started = asyncio.Event()
        other_started = asyncio.Event()
        release_first = asyncio.Event()
        order: list[str] = []

        async def first() -> None:
            order.append("same_id_first_start")
            first_started.set()
            await release_first.wait()
            order.append("same_id_first_end")

        async def second() -> None:
            order.append("same_id_second_start")

        async def other_id() -> None:
            order.append("other_id_start")
            other_started.set()

        first_task = asyncio.create_task(scheduler.schedule(5, first))
        await first_started.wait()
        second_task = asyncio.create_task(scheduler.schedule(5, second))
        other_task = asyncio.create_task(scheduler.schedule(6, other_id))
        await other_started.wait()
        await asyncio.sleep(0)
        assert "same_id_second_start" not in order
        release_first.set()
        await asyncio.gather(first_task, second_task, other_task)
        assert order.index("same_id_first_end") < order.index("same_id_second_start")

    asyncio.run(exercise())


def test_axi_and_bare_custom_bindings_share_one_generic_bus_wrapper(monkeypatch) -> None:
    monkeypatch.setattr(_bus_binding, "Bus", _FakeBus)
    dut = object()

    axi = _bus_binding.bind_channel_bus(
        dut,
        {
            "name": "w",
            "kind": "write_data",
            "fields": {"data": "payload_o"},
            "valid": "valid_o",
            "ready": "ready_i",
        },
    )
    custom = _bind_bare_channel_bus(
        dut,
        {
            "name": "data",
            "fields": {"data": "payload_o"},
            "valid": "valid_o",
            "ready": "ready_i",
        },
    )

    assert axi.signals == {
        "wdata": "payload_o",
        "wvalid": "valid_o",
        "wready": "ready_i",
    }
    assert custom.signals == {
        "data": "payload_o",
        "valid": "valid_o",
        "ready": "ready_i",
    }
    assert axi._optional_signals == []
    assert custom._optional_signals == []


def test_page_edge_bases_follow_actual_packed_object_sizes() -> None:
    def binding(name: str, elements_per_word: int) -> dict:
        return {
            "data_object": name,
            "dimensions": ["M", "N"],
            "memory_mapping": {
                "elements_per_word": elements_per_word,
                "word_stride_bytes": 4,
                "bus_width_bits": 32,
            },
        }

    operation = {
        "dimensions": {"M": 4, "N": 4},
        "inputs": [binding("A", 4)],
        "outputs": [binding("C", 1)],
    }
    read = default_axi_lite_memory_bases(operation, variant="read_page_edge")
    write = default_axi_lite_memory_bases(operation, variant="write_page_edge")
    assert read["A"] == 0xFF0  # Four packed words; last address is 0xFFC.
    assert write["C"] == 0xFC0  # Sixteen words; last address is 0xFFC.


def test_axi4_burst_address_sequence_wraps_within_its_window() -> None:
    assert _burst_addresses(0x18, 4, 4, 2) == [0x18, 0x1C, 0x10, 0x14]
    assert _burst_addresses(0x18, 4, 4, 1) == [0x18, 0x1C, 0x20, 0x24]
    assert _burst_addresses(0x19, 4, 4, 1) == [0x19, 0x1C, 0x20, 0x24]
    assert _burst_addresses(0x18, 4, 4, 0) == [0x18] * 4
    with pytest.raises(Axi4OutstandingDriveError, match="transfer-size aligned"):
        _burst_addresses(0x19, 4, 4, 2)


def test_axi4_narrow_bus_lanes_preserve_unselected_bytes() -> None:
    memory = OperationMemoryAdapter()
    mapping = {"bus_width_bits": 32, "word_stride_bytes": 4}
    memory.write_word(0x1000, 0x11223344, mapping)
    assert memory.read_bus_word(0x1002, mapping) == 0x11223344
    memory.write_strobed_bus_word(0x1002, 0xAABBCCDD, 0xC, mapping)
    assert memory.read_words(0x1000, 1, mapping) == [0xAABB3344]
