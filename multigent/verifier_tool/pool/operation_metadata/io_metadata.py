"""Explicit object serialization declarations; never equate shape with wire order."""

from copy import deepcopy
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .packed_encoding import validate_packed_encoding_declaration


def serialization_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["kind", "description"],
        "properties": {
            "kind": {"type": "string", "enum": ["dense_tensor", "scalar", "llm_extension", "packed_encoding"]},
            "index_order": {"type": "array", "items": {"type": "string"}},
            "description": {"type": "string", "minLength": 1,
                            "description": "Exact transfer/packing order; index_order lists outermost to innermost axes. Unsupported layouts use llm_extension, never a guessed dense layout."},
            "extension_request": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$",
                "description": (
                    "Optional exact link to the operation-domain verification_extensions "
                    "request that owns this unsupported serialization. Omitted only for "
                    "legacy coarse llm_extension contracts."
                ),
            },
            "derived_axes": {
                "type": "array",
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["real_axis", "order", "sub_axes"],
                    "properties": {
                        "real_axis": {"type": "string"},
                        "order": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "sub_axes": {
                            "type": "array", "minItems": 1,
                            "items": {
                                "type": "object", "additionalProperties": False,
                                "required": ["name", "extent"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "extent": {"type": "integer", "minimum": 1},
                                },
                            },
                        },
                    },
                },
                "description": (
                    "packed_encoding only. Decomposes one declared dimension into an ordered "
                    "(outermost to innermost) chain of pseudo-axes usable by traversal; "
                    "product(sub_axes[].extent) must equal the real axis's declared extent."
                ),
            },
            "traversal": {
                "type": "object", "additionalProperties": False,
                "required": ["word_axes", "containers_per_word", "field_axis"],
                "properties": {
                    "word_axes": {"type": "array", "items": {"type": "string"}},
                    "containers_per_word": {"type": "integer", "minimum": 1},
                    "container_axis": {"type": ["string", "null"]},
                    "field_axis": {"type": "string"},
                },
                "description": "packed_encoding only. word_axes lists outermost to innermost, same convention as dense_tensor's index_order.",
            },
            "packed_encoding": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "physical_container_width", "used_width", "used_bit_range",
                    "padding_value", "container_bit_layout", "group_size", "fields",
                ],
                "properties": {
                    "physical_container_width": {"type": "integer", "minimum": 1},
                    "used_width": {"type": "integer", "minimum": 1},
                    "used_bit_range": {
                        "type": "array", "items": {"type": "integer", "minimum": 0},
                        "minItems": 2, "maxItems": 2,
                    },
                    "padding_value": {"type": "string", "enum": ["zero", "dont_care"]},
                    "container_bit_layout": {"type": "string", "enum": ["contiguous_ascending"]},
                    "group_size": {"type": "integer", "minimum": 1},
                    "fields": {
                        "type": "array", "minItems": 1,
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["logical_offset", "source_width", "interpretation", "shift"],
                            "properties": {
                                "logical_offset": {"type": "integer", "minimum": 0},
                                "source_width": {"type": "integer", "minimum": 1},
                                "interpretation": {"type": "string", "enum": ["signed", "unsigned"]},
                                "shift": {"type": "integer", "minimum": 0},
                            },
                        },
                    },
                },
                "description": (
                    "packed_encoding only. P = (sum_i extend(fields[i], interpretation) << shift_i) "
                    "mod 2**used_width, where extend is two's-complement sign extension for "
                    "'signed' fields or a plain bitmask for 'unsigned' fields. No other combine "
                    "mode exists. shift is bit 0 = LSB of the container."
                ),
            },
        },
    }


def declared_serialization(
    obj: Mapping[str, Any],
    *,
    dimension_extents: Mapping[str, int] | None = None,
    element_width_bits: int | None = None,
) -> dict[str, Any]:
    declaration = obj.get("serialization")
    errors = list(Draft202012Validator(serialization_schema()).iter_errors(declaration))
    if errors:
        raise ValueError(f"data object {obj.get('name')!r}.serialization must be explicit: {errors[0].message}")
    dimensions = list(map(str, obj.get("dimensions", [])))
    kind = declaration["kind"]
    if kind == "packed_encoding":
        if dimension_extents is None or element_width_bits is None:
            raise ValueError(
                f"data object {obj.get('name')!r}: validating a packed_encoding serialization "
                "requires dimension_extents and element_width_bits"
            )
        validate_packed_encoding_declaration(
            declaration, dimensions,
            dimension_extents=dimension_extents, element_width_bits=element_width_bits,
        )
        return deepcopy(dict(declaration))
    if "index_order" not in declaration:
        raise ValueError(f"{kind} serialization requires index_order")
    order = declaration["index_order"]
    if kind == "scalar" and (dimensions or order):
        raise ValueError("scalar serialization requires no dimensions and index_order=[]")
    if kind == "dense_tensor" and (not dimensions or sorted(order) != sorted(dimensions) or len(set(order)) != len(order)):
        raise ValueError("dense_tensor serialization.index_order must list each declared dimension exactly once")
    return deepcopy(dict(declaration))


def require_supported_serialization(binding: Mapping[str, Any]) -> None:
    """The current wire adapter implements one-element canonical-order streams and the
    generic packed_encoding engine. Other declarations remain explicit, but must not
    execute through this adapter. Canonical arithmetic can still operate on already
    normalized logical tensors.
    """
    serial = binding.get("serialization", {})
    if serial.get("kind") == "packed_encoding":
        return
    dims = binding.get("dimensions", [])
    kind = "dense_tensor" if dims else "scalar"
    if serial.get("kind") != kind or serial.get("index_order") != dims:
        raise ValueError(
            f"{binding.get('data_object')!r}: declared serialization is not supported by "
            "the code-owned adapter; an explicit LLM extension is required (no layout inference)"
        )
