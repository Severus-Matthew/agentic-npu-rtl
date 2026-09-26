"""Shared cocotb ``Bus`` construction for standard and custom drivers.

Every driver eventually needs to wrap an exact ``attribute -> DUT signal``
mapping as a ``cocotbext-axi``-compatible ``Bus`` object.  The low-level
wrapper, including the generic-Bus ``_optional_signals`` compatibility shim,
lives here once.  AXI-family and custom-MMIO helpers only decide how their
contract fields map to those attribute names.
"""
from __future__ import annotations

from typing import Any, Mapping

from cocotb_bus.bus import Bus

KIND_PREFIX = {
    "write_address": "aw",
    "write_data": "w",
    "write_response": "b",
    "read_address": "ar",
    "read_data": "r",
}


class BusBindingError(AssertionError):
    """A compiled channel cannot be bound as a cocotbext-axi Bus."""


def bind_signal_bus(dut: Any, signals: Mapping[str, Any]) -> Bus:
    """Wrap an exact attribute-to-DUT-signal mapping as a generic Bus.

    This primitive deliberately knows nothing about AXI prefixes or custom
    channel kinds.  Keeping the ``_optional_signals`` compatibility shim here
    prevents each protocol driver from carrying its own copy.
    """

    bus = Bus(
        dut,
        None,
        signals={str(attribute): str(signal) for attribute, signal in signals.items()},
        bus_separator="",
    )
    # ``Bus.__init__`` populates ``self._signals`` but a generic ``Bus`` has
    # no class-level ``_optional_signals``.  cocotbext-axi model constructors
    # read the latter for diagnostic logging even when no optional field is
    # requested.
    bus._optional_signals = []
    return bus


def bind_channel_bus(dut: Any, channel: Mapping[str, Any]) -> Bus:
    """Wrap one compiled channel's exact field->signal names as a cocotbext-axi Bus.

    `name=None`/`bus_separator=""` make `cocotb_bus.bus.Bus` bind each dict
    key literally to the DUT signal named by its value -- no AXI-standard
    naming convention is assumed, exactly like this tool's own capture
    adapter (`pool/operation_metadata/protocol.py`) never assumes signal
    names. Only fields our compiled contract actually maps are ever named,
    so `.drive()`/`.sample()` (which iterate this Bus instance's own bound
    signal dict, not the fixed AXI field list) never touch an unbound
    optional AXI field.
    """

    kind = str(channel.get("kind", ""))
    prefix = KIND_PREFIX.get(kind)
    if prefix is None:
        raise BusBindingError(f"unsupported AXI channel kind {kind!r}")
    fields = channel.get("fields", {})
    if not isinstance(fields, Mapping):
        raise BusBindingError(f"channel {channel.get('name')!r} fields must be a mapping")
    signals = {f"{prefix}{field}": str(name) for field, name in fields.items()}
    signals[f"{prefix}valid"] = str(channel["valid"])
    if not channel.get("ready"):
        raise BusBindingError(f"channel {channel.get('name')!r} needs a bound ready signal")
    signals[f"{prefix}ready"] = str(channel["ready"])
    return bind_signal_bus(dut, signals)


__all__ = ["BusBindingError", "KIND_PREFIX", "bind_channel_bus", "bind_signal_bus"]
