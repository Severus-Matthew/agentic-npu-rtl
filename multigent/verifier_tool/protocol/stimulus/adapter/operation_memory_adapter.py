"""The "adapter" half of the memory/adapter/driver split: the operation-
contract-aware bridge between raw byte storage (`../memory`) and a wire
driver's protocol-specific view of the world.

A driver (`../drivers/axi_lite.py`, `../drivers/axi4_outstanding.py`, and
eventually a custom_mmio driver) knows how to *speak a wire protocol* --
when to assert valid, how to build a response -- but should never need to
know which operation object a given address belongs to, how many canonical
elements pack into one bus word, or where each object's address window
starts and ends. That is exactly what lives here instead, so it is written
once and shared, rather than re-derived per protocol. This is the concrete
proof that separation pays off: `axi4_outstanding.py` used to carry its own
private `_memory_windows`/`_find_window` copy of exactly this logic; a
custom_mmio driver reuses this module unchanged rather than growing a third
copy.

Nothing here touches cocotb, a clock, or a signal handle -- every function
and method is plain, synchronous Python, testable without a simulator.
"""
from __future__ import annotations

from math import prod
from typing import Any, Mapping, Sequence

from ..memory import Memory


class OperationMemoryAdapterError(AssertionError):
    """A code-owned memory image cannot be built, addressed, or read back
    unambiguously."""


def expected_elements(binding: Mapping[str, Any], dimensions: Mapping[str, Any]) -> int:
    extents = [dimensions.get(str(axis)) for axis in binding.get("dimensions", [])]
    if extents and all(isinstance(value, int) and value > 0 for value in extents):
        return prod(map(int, extents))
    if not extents:
        return 1
    raise OperationMemoryAdapterError(
        f"binding {binding.get('data_object')!r} has unresolved dimensions {extents!r}"
    )


def _packed_encoding_dimension_extents(
    binding: Mapping[str, Any], dimensions: Mapping[str, Any]
) -> dict[str, int]:
    names = list(map(str, binding.get("dimensions", [])))
    missing = [name for name in names if not isinstance(dimensions.get(name), int)]
    if missing:
        raise OperationMemoryAdapterError(
            f"binding {binding.get('data_object')!r} needs fixed extents for dimensions {missing}"
        )
    return {name: int(dimensions[name]) for name in names}


def pack_words(
    values: Sequence[int], binding: Mapping[str, Any], dimensions: Mapping[str, Any] = {},
) -> list[int]:
    """Pack canonical element values into bus words, lane 0 least-significant.

    A `packed_encoding` serialization (several logical elements arithmetically
    combined into one physical container -- see
    `pool/operation_metadata/packed_encoding.py`) is dispatched to that
    generic engine instead of this function's own naive
    one-element-per-`width`-bit-lane placement, which only ever matches
    `dense_tensor`/`scalar` layouts.
    """

    serialization = binding.get("serialization", {})
    if serialization.get("kind") == "packed_encoding":
        from ....pool.operation_metadata.packed_encoding import pack_words as pack_words_packed_encoding

        extents = _packed_encoding_dimension_extents(binding, dimensions)
        return pack_words_packed_encoding(
            serialization, list(map(str, binding.get("dimensions", []))), extents, values,
        )
    mapping = binding.get("memory_mapping", {})
    width = int(binding.get("data_type", {}).get("width_bits", 0))
    per_word = int(mapping.get("elements_per_word", 0))
    if (
        width <= 0
        or per_word <= 0
        or mapping.get("byte_order") != "little"
        or mapping.get("address_sequence") != "contiguous"
    ):
        raise OperationMemoryAdapterError(
            f"binding {binding.get('data_object')!r} lacks supported memory packing metadata"
        )
    mask = (1 << width) - 1
    words: list[int] = []
    for start in range(0, len(values), per_word):
        word = 0
        for lane, value in enumerate(values[start : start + per_word]):
            word |= (int(value) & mask) << (lane * width)
        words.append(word)
    return words


def unpack_words(
    words: Sequence[int], binding: Mapping[str, Any], expected_count: int
) -> list[int]:
    """Inverse of `pack_words`, truncated to the binding's expected element count.

    Only ever called for `dense_tensor`/`scalar` output objects today -- an
    output declared `packed_encoding` has no decode direction implemented
    (see `packed_encoding.py`'s module docstring: only encoding is needed,
    since a stimulus generator never reads a packed object back out).
    """

    serialization = binding.get("serialization", {})
    if serialization.get("kind") == "packed_encoding":
        raise OperationMemoryAdapterError(
            f"binding {binding.get('data_object')!r}: packed_encoding has no decode "
            "direction (only ever used for inputs a stimulus generator writes, never "
            "reads back)"
        )
    mapping = binding.get("memory_mapping", {})
    width = int(binding.get("data_type", {}).get("width_bits", 0))
    signed = bool(binding.get("data_type", {}).get("signed"))
    per_word = int(mapping.get("elements_per_word", 0))
    if width <= 0 or per_word <= 0 or mapping.get("byte_order") != "little":
        raise OperationMemoryAdapterError(
            f"binding {binding.get('data_object')!r} lacks supported memory packing metadata"
        )
    mask = (1 << width) - 1
    result: list[int] = []
    for word in words:
        for lane in range(per_word):
            value = (int(word) >> (lane * width)) & mask
            if signed and value & (1 << (width - 1)):
                value -= 1 << width
            result.append(value)
    return result[:expected_count]


def word_count(binding: Mapping[str, Any], dimensions: Mapping[str, Any]) -> int:
    """How many bus words this binding's elements pack into."""

    per_word = int(binding.get("memory_mapping", {}).get("elements_per_word", 0))
    return (expected_elements(binding, dimensions) + per_word - 1) // per_word


def build_address_windows(
    bindings: list[Mapping[str, Any]], dimensions: Mapping[str, Any], bases: Mapping[str, int]
) -> list[tuple[int, int, Mapping[str, Any]]]:
    """One `[base, base+word_count*stride)` window per bound object.

    Shared by every driver that needs to work out, from a raw address a DUT
    presented on the wire, which object's `memory_mapping` applies -- full
    AXI4 needs this because it does not otherwise know which object an
    accepted AR/AW address belongs to; a future custom_mmio driver needs the
    exact same thing for the exact same reason.
    """

    windows: list[tuple[int, int, Mapping[str, Any]]] = []
    for binding in bindings:
        mapping = binding.get("memory_mapping", {})
        stride = int(mapping["word_stride_bytes"])
        count = word_count(binding, dimensions)
        base = int(bases[str(binding["data_object"])])
        windows.append((base, base + stride * count, mapping))
    return windows


def find_window_mapping(
    address: int, windows: list[tuple[int, int, Mapping[str, Any]]]
) -> Mapping[str, Any]:
    """The bound object's `memory_mapping` whose window contains `address`."""

    match = next(((lo, hi, mapping) for lo, hi, mapping in windows if lo <= address < hi), None)
    if match is None:
        raise OperationMemoryAdapterError(
            f"address {address:#x} is not inside any bound data object's expected range"
        )
    return match[2]


class OperationMemoryAdapter:
    """One shared byte-addressable image backing every object of one job,
    plus the operation-contract-aware view over it (address windows,
    canonical value packing) that every driver shares instead of each
    re-deriving its own copy.

    Built once per job from its canonical input stimulus, this is what every
    protocol driver servicing that job's request/response traffic reads
    from and writes into -- regardless of how many physical channels,
    outstanding requests, or completion orders that driver's wire protocol
    allows. A multi-outstanding, out-of-order-completing driver and a
    strictly-sequential one both just call `read_words`/`write_word` here;
    neither needs to know the other exists.
    """

    def __init__(self, size: int = 2**32) -> None:
        self.mem = Memory(size=size)
        self.input_windows: list[tuple[int, int, Mapping[str, Any]]] = []
        self.output_windows: list[tuple[int, int, Mapping[str, Any]]] = []

    @classmethod
    def load(
        cls,
        operation: Mapping[str, Any],
        case: Mapping[str, Any],
        bases: Mapping[str, int],
        *,
        size: int = 2**32,
    ) -> "OperationMemoryAdapter":
        """Build a fresh image with every input object's canonical stimulus
        preloaded, and both directions' address windows precomputed."""

        adapter = cls(size=size)
        dimensions = operation.get("dimensions", {})
        for binding in operation.get("inputs", []):
            mapping = binding.get("memory_mapping", {})
            object_name = str(binding["data_object"])
            values = case.get("stimulus", {}).get(object_name)
            if not isinstance(values, list):
                raise OperationMemoryAdapterError(f"case is missing canonical input {object_name!r}")
            words = pack_words(values, binding, dimensions)
            for index, word in enumerate(words):
                adapter.write_word(
                    int(bases[object_name]) + int(mapping["word_stride_bytes"]) * index, word, mapping
                )
        adapter.input_windows = build_address_windows(operation.get("inputs", []), dimensions, bases)
        adapter.output_windows = build_address_windows(operation.get("outputs", []), dimensions, bases)
        return adapter

    def read_words(self, address: int, count: int, mapping: Mapping[str, Any]) -> list[int]:
        stride = int(mapping["word_stride_bytes"])
        byte_width = int(mapping["bus_width_bits"]) // 8
        words = []
        for index in range(count):
            data = self.mem.read(address + stride * index, byte_width)
            words.append(int.from_bytes(bytes(data), "little"))
        return words

    def read_bus_word(self, address: int, mapping: Mapping[str, Any]) -> int:
        """Return a bus-width beat with bytes in their address-selected lanes.

        A narrow AXI transfer at lane 2 still places its bytes in the upper
        lanes of a 32-bit RDATA bus, not in the low half of a shifted word.
        The protocol driver decides which lanes are active; this adapter only
        supplies the byte-addressed memory image in bus-lane order.
        """

        byte_width = int(mapping["bus_width_bits"]) // 8
        aligned = address - address % byte_width
        return int.from_bytes(bytes(self.mem.read(aligned, byte_width)), "little")

    def write_word(self, address: int, word: int, mapping: Mapping[str, Any]) -> None:
        byte_width = int(mapping["bus_width_bits"]) // 8
        self.mem.write(address, int(word).to_bytes(byte_width, "little"))

    def write_strobed_bus_word(
        self, address: int, word: int, strobe: int, mapping: Mapping[str, Any]
    ) -> None:
        """Apply an AXI bus-lane strobe without overwriting inactive bytes."""

        byte_width = int(mapping["bus_width_bits"]) // 8
        aligned = address - address % byte_width
        data = int(word).to_bytes(byte_width, "little")
        for lane in range(byte_width):
            if int(strobe) & (1 << lane):
                self.mem.write(aligned + lane, data[lane : lane + 1])

    def read_output_values(
        self,
        binding: Mapping[str, Any],
        dimensions: Mapping[str, Any],
        bases: Mapping[str, int],
    ) -> list[int]:
        """Read one output object back out, in correct logical (address) order."""

        mapping = binding.get("memory_mapping", {})
        object_name = str(binding["data_object"])
        expected = expected_elements(binding, dimensions)
        per_word = int(mapping["elements_per_word"])
        word_count = (expected + per_word - 1) // per_word
        words = self.read_words(int(bases[object_name]), word_count, mapping)
        return unpack_words(words, binding, expected)

    def mapping_for_input_address(self, address: int) -> Mapping[str, Any]:
        return find_window_mapping(address, self.input_windows)

    def mapping_for_output_address(self, address: int) -> Mapping[str, Any]:
        return find_window_mapping(address, self.output_windows)


__all__ = [
    "OperationMemoryAdapter",
    "OperationMemoryAdapterError",
    "build_address_windows",
    "expected_elements",
    "find_window_mapping",
    "pack_words",
    "unpack_words",
    "word_count",
]
