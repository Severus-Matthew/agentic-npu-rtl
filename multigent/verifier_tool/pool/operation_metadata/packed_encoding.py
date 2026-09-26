"""The `packed_encoding` serialization kind: several logical elements folded into
one physical container (word or lane) via shift + two's-complement extend + add,
plus the traversal description that says which word/container/field a given
logical tensor position lands in.

This exists for wire layouts `dense_tensor` cannot express: a container narrower
or wider than the natural `bus_width / element_width` count (padding), and/or a
container whose bits are a genuine arithmetic combination of more than one
logical element (not just a reordering) -- e.g. the DSP48 SIMD-multiply packing
trick some Vitis HLS INT8 GEMM kernels use to fold two INT8 multiplies through
one DSP. See `pool/operation_metadata/README.md` for the worked A/B example this
was built against (`gemm_hls/int8_gemm.cpp`).

Only the encode direction (logical values -> wire words) is implemented. That is
all a stimulus generator ever needs: it only ever *constructs* the DRAM image an
accelerator reads, never decodes one back out, since correctness is always
checked through the operation's own output, not by reading packed inputs back.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class PackedEncodingError(ValueError):
    """A packed_encoding serialization declaration or value is not well-formed."""


def _as_signed(value: int, width: int) -> int:
    raw = value & ((1 << width) - 1)
    sign = 1 << (width - 1)
    return raw - (1 << width) if raw & sign else raw


def _mixed_radix_decompose(index: int, extents: Sequence[int]) -> list[int]:
    """Split `index` into per-axis indices for axes ordered outermost to innermost."""

    result = [0] * len(extents)
    remaining = index
    for position in range(len(extents) - 1, -1, -1):
        extent = extents[position]
        result[position] = remaining % extent
        remaining //= extent
    return result


def _mixed_radix_compose(indices: Sequence[int], extents: Sequence[int]) -> int:
    """Inverse of `_mixed_radix_decompose`: axes ordered outermost to innermost."""

    total = 0
    for index, extent in zip(indices, extents):
        total = total * extent + index
    return total


def validate_packed_encoding_declaration(
    declaration: Mapping[str, Any],
    dimensions: Sequence[str],
    *,
    dimension_extents: Mapping[str, int],
    element_width_bits: int,
) -> None:
    """Check every invariant a `kind: packed_encoding` serialization must satisfy.

    `dimensions` is the data object's own declared dimension names (canonical
    logical order, matching how its flat stimulus/golden values are indexed).
    `dimension_extents` must resolve every one of those names to a fixed extent
    (a packed wire layout is only meaningful for a fixed shape); a
    runtime-configurable dimension cannot be used here.
    """

    traversal = declaration.get("traversal")
    packing = declaration.get("packed_encoding")
    if not isinstance(traversal, Mapping):
        raise PackedEncodingError("packed_encoding serialization needs a traversal object")
    if not isinstance(packing, Mapping):
        raise PackedEncodingError("packed_encoding serialization needs a packed_encoding object")

    missing_extents = sorted(set(dimensions) - set(dimension_extents))
    if missing_extents:
        raise PackedEncodingError(f"packed_encoding needs a fixed extent for dimensions {missing_extents}")

    axis_extent: dict[str, int] = dict(dimension_extents)
    sub_axis_owner: dict[str, str] = {}
    decomposition: dict[str, list[str]] = {}
    for entry in declaration.get("derived_axes", []):
        real_axis = str(entry.get("real_axis", ""))
        if real_axis not in dimensions:
            raise PackedEncodingError(f"derived_axes.real_axis {real_axis!r} is not a declared dimension")
        sub_axes = list(entry.get("sub_axes", []))
        order = list(map(str, entry.get("order", [])))
        names = [str(item.get("name", "")) for item in sub_axes]
        if sorted(order) != sorted(names) or len(set(names)) != len(names):
            raise PackedEncodingError(f"derived_axes for {real_axis!r}: order must list each sub_axis exactly once")
        product = 1
        for item in sub_axes:
            name = str(item["name"])
            extent = int(item["extent"])
            if name in axis_extent:
                raise PackedEncodingError(f"derived sub-axis {name!r} collides with an existing axis name")
            axis_extent[name] = extent
            sub_axis_owner[name] = real_axis
            product *= extent
        if product != dimension_extents[real_axis]:
            raise PackedEncodingError(
                f"derived_axes for {real_axis!r}: sub-axis extents multiply to {product}, "
                f"expected the declared extent {dimension_extents[real_axis]}"
            )
        decomposition[real_axis] = order

    word_axes = list(map(str, traversal.get("word_axes", [])))
    container_axis = traversal.get("container_axis")
    field_axis = str(traversal.get("field_axis", ""))
    containers_per_word = traversal.get("containers_per_word")

    placed = [*word_axes, *([str(container_axis)] if container_axis else []), field_axis]
    if len(placed) != len(set(placed)):
        raise PackedEncodingError("traversal axes must not repeat an axis/sub-axis name")
    unknown = [name for name in placed if name not in axis_extent]
    if unknown:
        raise PackedEncodingError(f"traversal references unknown axis/sub-axis names {unknown}")

    placed_set = set(placed)
    for dim in dimensions:
        if dim in decomposition:
            required = set(decomposition[dim])
            covered = required & placed_set
            if covered != required:
                raise PackedEncodingError(
                    f"dimension {dim!r} is decomposed via derived_axes but not fully placed in "
                    f"traversal (missing {sorted(required - covered)})"
                )
        elif dim not in placed_set:
            raise PackedEncodingError(f"dimension {dim!r} is not accounted for by traversal or derived_axes")
    dimension_or_subaxis = set(dimensions) | set(sub_axis_owner)
    extra = placed_set - dimension_or_subaxis
    if extra:
        raise PackedEncodingError(
            f"traversal references axes that are neither declared dimensions nor derived sub-axes: {sorted(extra)}"
        )

    if not isinstance(containers_per_word, int) or containers_per_word < 1:
        raise PackedEncodingError("traversal.containers_per_word must be a positive integer")
    if containers_per_word > 1:
        if not container_axis:
            raise PackedEncodingError("containers_per_word > 1 requires a non-null container_axis")
        if axis_extent[str(container_axis)] != containers_per_word:
            raise PackedEncodingError(
                f"container_axis {container_axis!r} extent {axis_extent[str(container_axis)]} "
                f"must equal containers_per_word {containers_per_word}"
            )
    elif container_axis:
        raise PackedEncodingError("container_axis must be null when containers_per_word == 1")

    group_size = packing.get("group_size")
    fields = list(packing.get("fields", []))
    if field_axis not in axis_extent:
        raise PackedEncodingError(f"traversal.field_axis {field_axis!r} is not a known axis")
    if axis_extent[field_axis] != group_size:
        raise PackedEncodingError(
            f"field_axis {field_axis!r} extent {axis_extent[field_axis]} must equal group_size {group_size}"
        )
    if group_size != len(fields):
        raise PackedEncodingError(f"packed_encoding.group_size {group_size} must equal len(fields) {len(fields)}")

    offsets = sorted(int(item["logical_offset"]) for item in fields)
    if offsets != list(range(group_size)):
        raise PackedEncodingError("packed_encoding.fields logical_offset must be exactly 0..group_size-1, each once")

    used_width = int(packing["used_width"])
    physical_width = int(packing["physical_container_width"])
    used_bit_range = list(packing["used_bit_range"])
    if not (0 < used_width <= physical_width):
        raise PackedEncodingError("packed_encoding.used_width must be > 0 and <= physical_container_width")
    if used_bit_range != [0, used_width - 1]:
        raise PackedEncodingError("packed_encoding.used_bit_range must be [0, used_width - 1] (LSB-anchored only)")

    unsigned_ranges: list[tuple[int, int]] = []
    for item in fields:
        source_width = int(item["source_width"])
        shift = int(item["shift"])
        interpretation = str(item["interpretation"])
        if source_width != element_width_bits:
            raise PackedEncodingError(
                f"packed_encoding field source_width {source_width} must equal the data "
                f"object's own data_type width {element_width_bits}"
            )
        if interpretation == "unsigned":
            unsigned_ranges.append((shift, shift + source_width))
    unsigned_ranges.sort()
    for (_, end_a), (start_b, _) in zip(unsigned_ranges, unsigned_ranges[1:]):
        if start_b < end_a:
            raise PackedEncodingError("packed_encoding: unsigned fields must not overlap")


def packed_encoding_word_count(
    declaration: Mapping[str, Any], dimension_extents: Mapping[str, int]
) -> int:
    """Total number of `physical_container_width * containers_per_word`-bit words."""

    axis_extent = _axis_extents(declaration, dimension_extents)
    traversal = declaration["traversal"]
    total = 1
    for axis in traversal["word_axes"]:
        total *= axis_extent[axis]
    return total


def packed_encoding_word_bits(declaration: Mapping[str, Any]) -> int:
    packing = declaration["packed_encoding"]
    return int(packing["physical_container_width"]) * int(declaration["traversal"]["containers_per_word"])


def _axis_extents(
    declaration: Mapping[str, Any], dimension_extents: Mapping[str, int]
) -> dict[str, int]:
    axis_extent = dict(dimension_extents)
    for entry in declaration.get("derived_axes", []):
        for item in entry["sub_axes"]:
            axis_extent[str(item["name"])] = int(item["extent"])
    return axis_extent


def _real_axis_indices(
    declaration: Mapping[str, Any], sub_axis_values: Mapping[str, int]
) -> dict[str, int]:
    """Recombine any decomposed sub-axis indices back into their real axis index."""

    result = dict(sub_axis_values)
    for entry in declaration.get("derived_axes", []):
        real_axis = str(entry["real_axis"])
        order = list(map(str, entry["order"]))
        indices = [sub_axis_values[name] for name in order]
        extents = [int(item["extent"]) for name in order for item in entry["sub_axes"] if item["name"] == name]
        result[real_axis] = _mixed_radix_compose(indices, extents)
        for name in order:
            result.pop(name, None)
    return result


def pack_words(
    declaration: Mapping[str, Any],
    dimensions: Sequence[str],
    dimension_extents: Mapping[str, int],
    values: Sequence[int],
) -> list[int]:
    """Encode `values` (flat, row-major per `dimensions`, outermost first) into
    the physical word stream this `packed_encoding` declaration describes.

    Each returned int spans `packed_encoding_word_bits(declaration)` bits.
    """

    axis_extent = _axis_extents(declaration, dimension_extents)
    traversal = declaration["traversal"]
    packing = declaration["packed_encoding"]
    word_axes = list(traversal["word_axes"])
    container_axis = traversal.get("container_axis")
    field_axis = str(traversal["field_axis"])
    containers_per_word = int(traversal["containers_per_word"])
    physical_width = int(packing["physical_container_width"])
    used_width = int(packing["used_width"])
    group_size = int(packing["group_size"])
    fields = sorted(packing["fields"], key=lambda item: int(item["logical_offset"]))

    dim_extents = [dimension_extents[name] for name in dimensions]
    word_extents = [axis_extent[name] for name in word_axes]
    total_words = 1
    for extent in word_extents:
        total_words *= extent

    words: list[int] = []
    for word_index in range(total_words):
        word_axis_values = dict(zip(word_axes, _mixed_radix_decompose(word_index, word_extents)))
        word_value = 0
        for container_index in range(containers_per_word):
            sub_axis_values = dict(word_axis_values)
            if container_axis:
                sub_axis_values[str(container_axis)] = container_index
            container_sum = 0
            for field in fields:
                offset = int(field["logical_offset"])
                sub_axis_values[field_axis] = offset
                real_indices = _real_axis_indices(declaration, sub_axis_values)
                per_dim = [real_indices[name] for name in dimensions]
                flat_index = _mixed_radix_compose(per_dim, dim_extents)
                raw = int(values[flat_index])
                source_width = int(field["source_width"])
                value = (
                    _as_signed(raw, source_width)
                    if field["interpretation"] == "signed"
                    else raw & ((1 << source_width) - 1)
                )
                container_sum += value << int(field["shift"])
            container_value = container_sum % (1 << used_width)
            word_value |= container_value << (container_index * physical_width)
        words.append(word_value)
    return words


__all__ = [
    "PackedEncodingError",
    "pack_words",
    "packed_encoding_word_bits",
    "packed_encoding_word_count",
    "validate_packed_encoding_declaration",
]
