"""Protocol-neutral completion ordering utilities for wire drivers."""

from __future__ import annotations

import random
from typing import Any


class RandomCompletionScheduler:
    """Preserve per-key FIFO order while randomizing order across keys.

    The scheduler knows nothing about AXI, addresses, or memory.  A caller
    awaits ``schedule(key, action)``; the action runs after every older action
    for the same key and after a seeded-random number of clock edges.  ``None``
    is a valid key and naturally degenerates to one global FIFO.
    """

    def __init__(
        self,
        clock: Any,
        *,
        seed: int | None = None,
        max_extra_cycles: int = 4,
    ) -> None:
        self._clock = clock
        self._random = random.Random(seed)
        self._max_extra_cycles = max(0, int(max_extra_cycles))
        self._tail: dict[Any, Any] = {}

    async def schedule(self, request_id: Any, action) -> None:
        from cocotb.triggers import Event, RisingEdge

        previous = self._tail.get(request_id)
        own_turn = Event()
        self._tail[request_id] = own_turn
        if previous is not None:
            await previous.wait()
        for _ in range(self._random.randint(0, self._max_extra_cycles)):
            await RisingEdge(self._clock)
        try:
            await action()
        finally:
            own_turn.set()
            if self._tail.get(request_id) is own_turn:
                del self._tail[request_id]


__all__ = ["RandomCompletionScheduler"]
