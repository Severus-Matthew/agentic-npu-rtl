"""Exact AXI4 transfer geometry shared by checkers and coverage classifiers."""

from __future__ import annotations

from typing import Mapping


class AXIGeometryError(ValueError):
    """An AXI descriptor cannot describe a legal transfer window sequence."""


def axi_transfer_windows(
    descriptor: Mapping[str, int],
) -> tuple[tuple[int, int], ...]:
    """Return inclusive byte windows for every beat of an AXI4 burst.

    ``len`` and ``size`` use their encoded AXI values.  The first unaligned
    FIXED/INCR transfer begins at AxADDR and ends at the end of its aligned
    transfer-size container; subsequent INCR transfers are aligned.  WRAP starts
    must already be transfer-size aligned and wrap inside the descriptor span.
    """

    address = int(descriptor["addr"])
    length = int(descriptor["len"])
    size = int(descriptor["size"])
    burst = int(descriptor["burst"])
    if address < 0 or not 0 <= length <= 255 or not 0 <= size <= 7:
        raise AXIGeometryError("AXI descriptor has out-of-domain address/LEN/SIZE")
    if burst not in {0, 1, 2}:
        raise AXIGeometryError(f"reserved AxBURST encoding {burst}")
    beats = length + 1
    transfer_bytes = 1 << size
    aligned = address - address % transfer_bytes
    if burst == 2:
        if beats not in {2, 4, 8, 16}:
            raise AXIGeometryError("WRAP requires 2, 4, 8, or 16 beats")
        if address != aligned:
            raise AXIGeometryError("WRAP start must be transfer-size aligned")
        span = beats * transfer_bytes
        base = address - address % span
        return tuple(
            (
                base + ((address - base + beat * transfer_bytes) % span),
                base + ((address - base + beat * transfer_bytes) % span) + transfer_bytes - 1,
            )
            for beat in range(beats)
        )

    first = (address, aligned + transfer_bytes - 1)
    if burst == 0:
        return (first,) * beats
    return (first,) + tuple(
        (
            aligned + beat * transfer_bytes,
            aligned + (beat + 1) * transfer_bytes - 1,
        )
        for beat in range(1, beats)
    )


def axi_burst_crosses_4k(descriptor: Mapping[str, int]) -> bool:
    """Return whether any descriptor-derived transfer crosses a 4-KiB container."""

    windows = axi_transfer_windows(descriptor)
    page = windows[0][0] >> 12
    return any(lower >> 12 != page or upper >> 12 != page for lower, upper in windows)


def axi_lane_mask(window: tuple[int, int], bus_bytes: int) -> int:
    """Return legal byte lanes for one descriptor-derived transfer window."""

    if bus_bytes <= 0 or bus_bytes & (bus_bytes - 1):
        raise AXIGeometryError("AXI bus width must contain a power-of-two byte count")
    lower, upper = map(int, window)
    if lower < 0 or upper < lower or upper - lower + 1 > bus_bytes:
        raise AXIGeometryError(f"invalid AXI transfer window {window!r}")
    first_lane = lower % bus_bytes
    last_lane = upper % bus_bytes
    if last_lane < first_lane:
        raise AXIGeometryError("one AXI transfer window cannot wrap across the data bus")
    return ((1 << (last_lane - first_lane + 1)) - 1) << first_lane


__all__ = [
    "AXIGeometryError",
    "axi_burst_crosses_4k",
    "axi_lane_mask",
    "axi_transfer_windows",
]
