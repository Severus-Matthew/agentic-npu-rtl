"""Tool-owned Architect arithmetic schema, reference checks, and compilation.

Architect declares semantics; this module resolves named types/objects without
guessing activation, accumulator type, conversion points, or stage order.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from math import isqrt
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from .formula import FormulaError, compile_formula
from .io_metadata import declared_serialization, serialization_schema


OPERATION_ARITHMETIC_SCHEMA_PATH = Path(__file__).with_name("arithmetic_metadata.schema.json")


class ArithmeticMetadataError(ValueError):
    """An explicit arithmetic declaration is invalid; never use legacy defaults."""


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    schema = json.loads(OPERATION_ARITHMETIC_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def operation_arithmetic_schema() -> dict[str, Any]:
    """Return a provider-compatible inline schema fragment, owned by the tool."""

    return {key: deepcopy(value) for key, value in _schema().items() if key != "$schema"}


def with_operation_arithmetic_schema(
    schema: Mapping[str, Any], *, required: bool = True,
) -> dict[str, Any]:
    """Compose tool-owned arithmetic and object serialization fields."""
    result = deepcopy(dict(schema))
    try:
        operation = result["properties"]["architecture_contract"]["properties"]["operations"]["items"]
        operation["properties"]["arithmetic"] = operation_arithmetic_schema()
        objects = result["properties"]["architecture_contract"]["properties"]["data_objects"]["items"]
        objects["properties"]["serialization"] = serialization_schema()
        object_fields = list(objects.get("required", []))
        if required and "serialization" not in object_fields:
            object_fields.append("serialization")
        objects["required"] = object_fields if required else [name for name in object_fields if name != "serialization"]
    except (KeyError, TypeError) as exc:
        raise ArithmeticMetadataError("Architect schema needs architecture_contract operations and data_objects items") from exc
    fields = list(operation.get("required", []))
    if required and "arithmetic" not in fields:
        fields.append("arithmetic")
    operation["required"] = fields if required else [name for name in fields if name != "arithmetic"]
    return result


def _resolve_post_operation_order(
    post_operations: Mapping[str, Mapping[str, Any]], post_output: str,
) -> list[str]:
    """Return stage names in dependency order by walking depends_on from post_output.

    post_operations is a DAG, not a fixed-order list: each stage names its own
    predecessor via depends_on rather than relying on declaration order. Every
    current stage kind is unary, so a valid graph is always a simple chain
    rooted at the literal "accumulator" sentinel; this rejects cycles,
    dangling references, and stages left unreferenced by that chain.
    """
    if not post_operations:
        if post_output != "accumulator":
            raise ArithmeticMetadataError(
                "post_output must be 'accumulator' when post_operations is empty"
            )
        return []
    if post_output not in post_operations:
        raise ArithmeticMetadataError(
            f"post_output {post_output!r} must name a declared post_operations stage"
        )
    order: list[str] = []
    seen: set[str] = set()
    current = post_output
    while True:
        if current in seen:
            raise ArithmeticMetadataError(f"post_operations depends_on contains a cycle at {current!r}")
        seen.add(current)
        order.append(current)
        predecessor = post_operations[current]["depends_on"][0]
        if predecessor == "accumulator":
            break
        if predecessor not in post_operations:
            raise ArithmeticMetadataError(
                f"post_operations stage {current!r} depends_on unknown stage {predecessor!r}"
            )
        current = predecessor
    order.reverse()
    if set(order) != set(post_operations):
        unreferenced = sorted(set(post_operations) - set(order))
        raise ArithmeticMetadataError(
            f"post_operations declares stage(s) {unreferenced} not on the "
            "depends_on chain from accumulator to post_output"
        )
    return order


def _named(items: Any, name: str, label: str) -> Mapping[str, Any]:
    matches = [item for item in items if isinstance(item, Mapping) and item.get("name") == name]
    if len(matches) != 1:
        raise ArithmeticMetadataError(f"{label} {name!r} must reference exactly one declared item")
    return matches[0]


def _dtype(architecture: Mapping[str, Any], name: str) -> dict[str, Any]:
    item = _named(architecture.get("data_types", []), name, "data type")
    width, signed = item.get("width_bits"), item.get("signed")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0 or not isinstance(signed, bool):
        raise ArithmeticMetadataError(f"data type {name!r} needs a positive integer width and boolean signed")
    return {"name": name, "width_bits": width, "signed": signed}


def _type_bounds(dtype: Mapping[str, Any]) -> tuple[int, int]:
    width = int(dtype["width_bits"])
    return (
        (-(1 << (width - 1)), (1 << (width - 1)) - 1)
        if bool(dtype["signed"])
        else (0, (1 << width) - 1)
    )


def _compile_integer_qk_score(
    operation: Mapping[str, Any],
    architecture: Mapping[str, Any],
    declaration: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile raw integer ``Q*K^T`` score generation as an independent stage."""

    if operation.get("coverage_family") != "attention_qk":
        raise ArithmeticMetadataError(
            "integer_qk_score requires family attention_qk"
        )
    inputs = [
        _named(architecture.get("data_objects", []), str(name), "input data object")
        for name in operation.get("inputs", [])
    ]
    outputs = [
        _named(architecture.get("data_objects", []), str(name), "output data object")
        for name in operation.get("outputs", [])
    ]

    def role(items: list[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
        matches = [item for item in items if item.get("role") == name]
        if len(matches) != 1:
            raise ArithmeticMetadataError(
                f"integer_qk_score needs exactly one object role {name!r}"
            )
        return matches[0]

    query = role(inputs, "query_matrix")
    key = role(inputs, "key_matrix")
    score = role(outputs, "attention_score_matrix")
    qd, kd, sd = [
        list(item.get("dimensions", [])) for item in (query, key, score)
    ]
    if not (
        len(qd) == len(kd) == len(sd) == 2
        and qd[1] == kd[1]
        and sd == [qd[0], kd[0]]
    ):
        raise ArithmeticMetadataError(
            "integer_qk_score requires Q[Q,D], K[S,D], score[Q,S]"
        )
    if declaration["score_reduction_dimensions"] != [qd[1]]:
        raise ArithmeticMetadataError(
            "score_reduction_dimensions must name the shared Q/K feature axis"
        )

    extents: dict[str, int] = {}
    for name in set(qd + kd + sd):
        dimension = _named(architecture.get("dimensions", []), name, "dimension")
        if dimension.get("runtime_configurable"):
            raise ArithmeticMetadataError(
                "runtime-configurable QK shapes require llm_extension; "
                "this base profile uses a fixed elaborated shape"
            )
        low, high = dimension.get("minimum"), dimension.get("maximum")
        resolved = low if low == high else None
        if resolved is None:
            parameter = _named(
                architecture.get("parameters", []),
                str(dimension.get("bound_parameter", "")),
                "shape parameter",
            )
            try:
                resolved = int(str(parameter.get("default_value", "")), 0)
            except ValueError as exc:
                raise ArithmeticMetadataError(
                    f"dimension {name!r} needs an integer elaboration default"
                ) from exc
        if (
            any(
                not isinstance(item, int) or isinstance(item, bool)
                for item in (resolved, low, high)
            )
            or not 0 < int(low) <= int(resolved) <= int(high)
        ):
            raise ArithmeticMetadataError(
                f"dimension {name!r} needs a positive fixed shape within its declared bounds"
            )
        extents[name] = int(resolved)

    query_type = _dtype(architecture, str(query["data_type"]))
    key_type = _dtype(architecture, str(key["data_type"]))
    product = _dtype(architecture, declaration["score_product_data_type"])
    accumulator = _dtype(
        architecture, declaration["score_accumulator_data_type"]
    )
    result = _dtype(architecture, declaration["result_data_type"])
    q_low, q_high = _type_bounds(query_type)
    k_low, k_high = _type_bounds(key_type)
    terms = [a * b for a in (q_low, q_high) for b in (k_low, k_high)]
    product_low, product_high = _type_bounds(product)
    if min(terms) < product_low or max(terms) > product_high:
        raise ArithmeticMetadataError(
            "score_product_data_type must represent every exact Q*K product"
        )
    if declaration["result_data_type"] != score["data_type"]:
        raise ArithmeticMetadataError(
            "result_data_type must match the declared attention score object"
        )
    if {item["name"] for item in inputs} != {query["name"], key["name"]} or len(outputs) != 1:
        raise ArithmeticMetadataError(
            "integer_qk_score has unmodeled input/output objects; use llm_extension"
        )

    return {
        **deepcopy(dict(declaration)),
        "integer_evaluation": "unbounded_between_explicit_conversions",
        "score_product_data_type": {**product, "conversion": "exact"},
        "score_accumulator_type": accumulator,
        "result_data_type": {
            **result,
            "conversion": declaration["result_conversion"],
        },
        "stage_order": [
            "operand_decode",
            "exact_query_key_product",
            "ordered_score_reduction_with_explicit_conversion",
            "result_conversion",
        ],
        "metadata_origin": "explicit_contract",
        "support_status": "supported_integer_qk_score",
    }


def _rounded_inverse_sqrt_coefficient(dimension: int, shift: int) -> int:
    """Return round(2**shift/sqrt(dimension)) without floating-point drift."""

    numerator = 1 << shift
    # floor(numerator/sqrt(D)), followed by an exact comparison against the
    # half-integer threshold.  Positive exact ties select the larger integer,
    # matching ``int'(positive_real + 0.5)`` style RTL derivations.
    floor_value = isqrt((numerator * numerator) // dimension)
    if 4 * numerator * numerator >= dimension * (2 * floor_value + 1) ** 2:
        floor_value += 1
    return floor_value


def _compile_fixed_point_attention_scale(
    operation: Mapping[str, Any],
    architecture: Mapping[str, Any],
    declaration: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile standalone signed score scaling by a fixed-point 1/sqrt(D)."""

    if operation.get("coverage_family") != "attention_scale":
        raise ArithmeticMetadataError(
            "fixed_point_attention_scale requires family attention_scale"
        )
    inputs = [
        _named(architecture.get("data_objects", []), str(name), "input data object")
        for name in operation.get("inputs", [])
    ]
    outputs = [
        _named(architecture.get("data_objects", []), str(name), "output data object")
        for name in operation.get("outputs", [])
    ]

    def role(items: list[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
        matches = [item for item in items if item.get("role") == name]
        if len(matches) != 1:
            raise ArithmeticMetadataError(
                f"fixed_point_attention_scale needs exactly one object role {name!r}"
            )
        return matches[0]

    score = role(inputs, "attention_score_matrix")
    result_object = role(outputs, "scaled_attention_score_matrix")
    score_dimensions = list(score.get("dimensions", []))
    result_dimensions = list(result_object.get("dimensions", []))
    if len(score_dimensions) != 2 or result_dimensions != score_dimensions:
        raise ArithmeticMetadataError(
            "fixed_point_attention_scale requires score[Q,S] and scaled_score[Q,S]"
        )
    if len(inputs) != 1 or len(outputs) != 1:
        raise ArithmeticMetadataError(
            "fixed_point_attention_scale has unmodeled input/output objects; use llm_extension"
        )

    dimension_name = str(declaration["head_dimension"])
    dimension = _named(
        architecture.get("dimensions", []), dimension_name, "head dimension"
    )
    if dimension.get("runtime_configurable"):
        raise ArithmeticMetadataError(
            "runtime-configurable attention scaling requires llm_extension; "
            "this base profile derives a fixed coefficient"
        )
    low, high = dimension.get("minimum"), dimension.get("maximum")
    resolved = low if low == high else None
    if resolved is None:
        parameter = _named(
            architecture.get("parameters", []),
            str(dimension.get("bound_parameter", "")),
            "head-dimension parameter",
        )
        try:
            resolved = int(str(parameter.get("default_value", "")), 0)
        except ValueError as exc:
            raise ArithmeticMetadataError(
                f"head dimension {dimension_name!r} needs an integer elaboration default"
            ) from exc
    if (
        any(
            not isinstance(item, int) or isinstance(item, bool)
            for item in (resolved, low, high)
        )
        or not 0 < int(low) <= int(resolved) <= int(high)
    ):
        raise ArithmeticMetadataError(
            f"head dimension {dimension_name!r} needs a positive fixed value"
        )

    shift = int(declaration["scale_shift"])
    expected_multiplier = _rounded_inverse_sqrt_coefficient(int(resolved), shift)
    if int(declaration["scale_multiplier"]) != expected_multiplier:
        raise ArithmeticMetadataError(
            "scale_multiplier must equal round(2^scale_shift/sqrt(head_dimension)); "
            f"expected {expected_multiplier} for D={resolved}, shift={shift}"
        )

    score_type = _dtype(architecture, str(score["data_type"]))
    product_type = _dtype(architecture, str(declaration["product_data_type"]))
    result_type = _dtype(architecture, str(declaration["result_data_type"]))
    if not score_type["signed"] or not product_type["signed"] or not result_type["signed"]:
        raise ArithmeticMetadataError(
            "fixed_point_attention_scale requires signed score, product, and result types"
        )
    score_low, score_high = _type_bounds(score_type)
    product_low, product_high = _type_bounds(product_type)
    multiplier = int(declaration["scale_multiplier"])
    exact_products = (score_low * multiplier, score_high * multiplier)
    if min(exact_products) < product_low or max(exact_products) > product_high:
        raise ArithmeticMetadataError(
            "product_data_type must represent every exact score*scale_multiplier product"
        )
    if declaration["result_data_type"] != result_object["data_type"]:
        raise ArithmeticMetadataError(
            "result_data_type must match the declared scaled attention score object"
        )
    if declaration["result_conversion"] == "exact":
        result_low, result_high = _type_bounds(result_type)
        denominator = 1 << shift
        scaled_bounds = (
            exact_products[0] // denominator,
            exact_products[1] // denominator,
        )
        if min(scaled_bounds) < result_low or max(scaled_bounds) > result_high:
            raise ArithmeticMetadataError(
                "exact result_data_type cannot represent every scaled score"
            )

    return {
        **deepcopy(dict(declaration)),
        "head_dimension_value": int(resolved),
        "integer_evaluation": "unbounded_between_explicit_conversions",
        "product_data_type": {**product_type, "conversion": "exact"},
        "result_data_type": {
            **result_type,
            "conversion": declaration["result_conversion"],
        },
        "stage_order": [
            "signed_score_decode",
            "exact_fixed_point_multiply",
            "arithmetic_floor_power_of_two_shift",
            "result_conversion",
        ],
        "metadata_origin": "explicit_contract",
        "support_status": "supported_fixed_point_attention_scale",
    }


def _compile_binary_attention_mask(
    operation: Mapping[str, Any],
    architecture: Mapping[str, Any],
    declaration: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a standalone binary-keep mask over scaled attention scores."""

    if operation.get("coverage_family") != "attention_mask":
        raise ArithmeticMetadataError(
            "binary_attention_mask requires family attention_mask"
        )
    inputs = [
        _named(architecture.get("data_objects", []), str(name), "input data object")
        for name in operation.get("inputs", [])
    ]
    outputs = [
        _named(architecture.get("data_objects", []), str(name), "output data object")
        for name in operation.get("outputs", [])
    ]

    def role(items: list[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
        matches = [item for item in items if item.get("role") == name]
        if len(matches) != 1:
            raise ArithmeticMetadataError(
                f"binary_attention_mask needs exactly one object role {name!r}"
            )
        return matches[0]

    score = role(inputs, "scaled_attention_score_matrix")
    mask = role(inputs, "attention_mask")
    result_object = role(outputs, "masked_attention_score_matrix")
    score_dimensions = list(score.get("dimensions", []))
    if (
        len(score_dimensions) != 2
        or list(mask.get("dimensions", [])) != score_dimensions
        or list(result_object.get("dimensions", [])) != score_dimensions
    ):
        raise ArithmeticMetadataError(
            "binary_attention_mask requires scaled_score[Q,S], mask[Q,S], and masked_score[Q,S]"
        )
    if len(inputs) != 2 or len(outputs) != 1:
        raise ArithmeticMetadataError(
            "binary_attention_mask has unmodeled input/output objects; use llm_extension"
        )
    for name in score_dimensions:
        dimension = _named(architecture.get("dimensions", []), name, "dimension")
        if dimension.get("runtime_configurable"):
            raise ArithmeticMetadataError(
                "runtime-configurable attention-mask shapes require llm_extension; "
                "this base profile uses a fixed elaborated shape"
            )

    score_type = _dtype(architecture, str(score["data_type"]))
    mask_type = _dtype(architecture, str(mask["data_type"]))
    result_type = _dtype(architecture, str(declaration["result_data_type"]))
    if not score_type["signed"] or not result_type["signed"]:
        raise ArithmeticMetadataError(
            "binary_attention_mask requires signed score and result types"
        )
    if mask_type["signed"] or int(mask_type["width_bits"]) != 1:
        raise ArithmeticMetadataError(
            "binary_attention_mask requires an unsigned one-bit attention mask"
        )
    if declaration["result_data_type"] != result_object["data_type"]:
        raise ArithmeticMetadataError(
            "result_data_type must match the declared masked attention score object"
        )
    if declaration["result_conversion"] == "exact":
        score_low, score_high = _type_bounds(score_type)
        result_low, result_high = _type_bounds(result_type)
        if score_low < result_low or score_high > result_high:
            raise ArithmeticMetadataError(
                "exact result_data_type must represent every preserved scaled score"
            )

    return {
        **deepcopy(dict(declaration)),
        "integer_evaluation": "unbounded_between_explicit_conversions",
        "result_data_type": {
            **result_type,
            "conversion": declaration["result_conversion"],
        },
        "stage_order": [
            "signed_scaled_score_decode",
            "binary_mask_decode",
            "conditional_preserve_or_zero",
            "result_conversion",
        ],
        "metadata_origin": "explicit_contract",
        "support_status": "supported_binary_attention_mask",
    }


def _compile_integer_sparse_attention(
    operation: Mapping[str, Any],
    architecture: Mapping[str, Any],
    declaration: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile the first exact code-owned sparse-attention profile.

    This intentionally composes the code-owned QK stage with explicit bypass
    scale/normalization stages and binary-mask/value stages:
    score[q,s] = sum_d Q[q,d] * K[s,d], followed by
    Y[q,v] = sum_s(mask[q,s] ? score[q,s] * V[s,v] : 0).
    Non-identity scaling, softmax, and top-k semantics are not guessed.
    """

    if operation.get("coverage_family") != "sparse_attention":
        raise ArithmeticMetadataError(
            "integer_sparse_attention requires family sparse_attention"
        )
    inputs = [
        _named(architecture.get("data_objects", []), str(name), "input data object")
        for name in operation.get("inputs", [])
    ]
    outputs = [
        _named(architecture.get("data_objects", []), str(name), "output data object")
        for name in operation.get("outputs", [])
    ]

    def role(items: list[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
        matches = [item for item in items if item.get("role") == name]
        if len(matches) != 1:
            raise ArithmeticMetadataError(
                f"integer_sparse_attention needs exactly one object role {name!r}"
            )
        return matches[0]

    query = role(inputs, "query_matrix")
    key = role(inputs, "key_matrix")
    value = role(inputs, "value_matrix")
    mask = role(inputs, "attention_mask")
    output = role(outputs, "attention_result")
    qd, kd, vd, md, od = [
        list(item.get("dimensions", []))
        for item in (query, key, value, mask, output)
    ]
    valid_shapes = (
        len(qd) == len(kd) == len(vd) == len(md) == len(od) == 2
        and qd[1] == kd[1]
        and kd[0] == vd[0]
        and md == [qd[0], kd[0]]
        and od == [qd[0], vd[1]]
    )
    if not valid_shapes:
        raise ArithmeticMetadataError(
            "integer_sparse_attention requires Q[Q,D], K[S,D], V[S,DV], "
            "mask[Q,S], result[Q,DV]"
        )
    if declaration["score_reduction_dimensions"] != [qd[1]]:
        raise ArithmeticMetadataError(
            "score_reduction_dimensions must name the shared Q/K feature axis"
        )
    if declaration["output_reduction_dimensions"] != [kd[0]]:
        raise ArithmeticMetadataError(
            "output_reduction_dimensions must name the K/V sequence axis"
        )

    extents: dict[str, int] = {}
    for name in set(qd + kd + vd + md + od):
        dimension = _named(architecture.get("dimensions", []), name, "dimension")
        if dimension.get("runtime_configurable"):
            raise ArithmeticMetadataError(
                "runtime-configurable sparse-attention shapes require llm_extension; "
                "this base profile uses a fixed elaborated shape"
            )
        low, high = dimension.get("minimum"), dimension.get("maximum")
        resolved = low if low == high else None
        if resolved is None:
            parameter = _named(
                architecture.get("parameters", []),
                str(dimension.get("bound_parameter", "")),
                "shape parameter",
            )
            try:
                resolved = int(str(parameter.get("default_value", "")), 0)
            except ValueError as exc:
                raise ArithmeticMetadataError(
                    f"dimension {name!r} needs an integer elaboration default"
                ) from exc
        if (
            any(
                not isinstance(item, int) or isinstance(item, bool)
                for item in (resolved, low, high)
            )
            or not 0 < int(low) <= int(resolved) <= int(high)
        ):
            raise ArithmeticMetadataError(
                f"dimension {name!r} needs a positive fixed shape within its declared bounds"
            )
        extents[name] = int(resolved)

    query_type = _dtype(architecture, str(query["data_type"]))
    key_type = _dtype(architecture, str(key["data_type"]))
    value_type = _dtype(architecture, str(value["data_type"]))
    mask_type = _dtype(architecture, str(mask["data_type"]))
    if mask_type["signed"] or mask_type["width_bits"] != 1:
        raise ArithmeticMetadataError(
            "binary_keep attention_mask requires an unsigned one-bit data type"
        )
    score_product = _dtype(architecture, declaration["score_product_data_type"])
    score_accumulator = _dtype(
        architecture, declaration["score_accumulator_data_type"]
    )
    output_product = _dtype(architecture, declaration["output_product_data_type"])
    output_accumulator = _dtype(
        architecture, declaration["output_accumulator_data_type"]
    )
    result = _dtype(architecture, declaration["result_data_type"])

    q_low, q_high = _type_bounds(query_type)
    k_low, k_high = _type_bounds(key_type)
    score_terms = [a * b for a in (q_low, q_high) for b in (k_low, k_high)]
    score_product_low, score_product_high = _type_bounds(score_product)
    if min(score_terms) < score_product_low or max(score_terms) > score_product_high:
        raise ArithmeticMetadataError(
            "score_product_data_type must represent every exact Q*K product"
        )

    score_low = extents[qd[1]] * min(score_terms)
    score_high = extents[qd[1]] * max(score_terms)
    if declaration["score_reduction_conversion"] == "wrap_twos_complement_after_each_add":
        score_low, score_high = _type_bounds(score_accumulator)
    v_low, v_high = _type_bounds(value_type)
    output_terms = [
        score * operand
        for score in (score_low, score_high)
        for operand in (v_low, v_high)
    ]
    output_product_low, output_product_high = _type_bounds(output_product)
    if min(output_terms) < output_product_low or max(output_terms) > output_product_high:
        raise ArithmeticMetadataError(
            "output_product_data_type must represent every exact score*V product"
        )
    if declaration["result_data_type"] != output["data_type"]:
        raise ArithmeticMetadataError(
            "result_data_type must match the declared attention result object"
        )
    if {item["name"] for item in inputs} != {
        query["name"], key["name"], value["name"], mask["name"]
    } or len(outputs) != 1:
        raise ArithmeticMetadataError(
            "integer_sparse_attention has unmodeled input/output objects; use llm_extension"
        )

    return {
        **deepcopy(dict(declaration)),
        "integer_evaluation": "unbounded_between_explicit_conversions",
        "score_product_data_type": {**score_product, "conversion": "exact"},
        "score_accumulator_type": score_accumulator,
        "output_product_data_type": {**output_product, "conversion": "exact"},
        "output_accumulator_type": output_accumulator,
        "result_data_type": {
            **result,
            "conversion": declaration["result_conversion"],
        },
        "stage_order": [
            "operand_decode",
            "qk_score",
            "scale",
            "mask",
            "normalization",
            "value_reduction",
            "result_conversion",
        ],
        "composition": [
            {
                "stage": "qk_score",
                "profile": "integer_qk_score",
                "mode": "raw_qk_transpose",
            },
            {"stage": "scale", "profile": "attention_scale", "mode": "none"},
            {"stage": "mask", "profile": "attention_mask", "mode": "binary_keep"},
            {
                "stage": "normalization",
                "profile": "attention_normalization",
                "mode": "none",
            },
            {
                "stage": "value_reduction",
                "profile": "attention_value",
                "mode": "integer_weighted_sum",
            },
        ],
        "metadata_origin": "explicit_contract",
        "support_status": "supported_composed_restricted_integer_sparse_attention",
    }


def compile_operation_arithmetic(
    operation: Mapping[str, Any], architecture: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and resolve the compact declaration into canonical arithmetic."""

    if "arithmetic" not in operation:
        raise ArithmeticMetadataError(
            "arithmetic is required: Architect must declare numeric rules explicitly, "
            "or select llm_extension with exact semantics; no inference or default is allowed"
        )
    declaration = operation["arithmetic"]
    errors = list(Draft202012Validator(_schema()).iter_errors(declaration))
    if errors:
        # Select the matching profile's errors to avoid an unhelpful anyOf dump.
        profile = declaration.get("classifier_profile") if isinstance(declaration, Mapping) else None
        branch = next((item for item in _schema()["anyOf"]
                       if profile in item["properties"]["classifier_profile"]["enum"]), None)
        if branch is not None:
            errors = list(Draft202012Validator(branch).iter_errors(declaration))
        details = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or 'arithmetic'}: {error.message}"
            for error in errors[:3]
        )
        raise ArithmeticMetadataError(details)
    assert isinstance(declaration, Mapping)
    from .structured import STRUCTURED_PROFILES, compile_structured_arithmetic
    if declaration["classifier_profile"] in STRUCTURED_PROFILES:
        return compile_structured_arithmetic(operation, architecture, declaration)
    if declaration["classifier_profile"] == "llm_extension":
        if not str(operation.get("semantics", "")).strip():
            raise ArithmeticMetadataError("llm_extension requires explicit operations[].semantics")
        return {
            **deepcopy(dict(declaration)),
            "semantics": operation["semantics"],
            "accumulator_data_type": None, "reduction_dimensions": [], "post_operations": [],
            "metadata_origin": "explicit_contract", "support_status": "llm_extension_required",
        }
    if declaration["classifier_profile"] == "integer_sparse_attention":
        return _compile_integer_sparse_attention(
            operation, architecture, declaration
        )
    if declaration["classifier_profile"] == "integer_qk_score":
        return _compile_integer_qk_score(operation, architecture, declaration)
    if declaration["classifier_profile"] == "fixed_point_attention_scale":
        return _compile_fixed_point_attention_scale(
            operation, architecture, declaration
        )
    if declaration["classifier_profile"] == "binary_attention_mask":
        return _compile_binary_attention_mask(
            operation, architecture, declaration
        )
    if operation.get("coverage_family") != "matrix_multiply":
        raise ArithmeticMetadataError("integer_matrix_multiply requires family matrix_multiply")

    inputs = [_named(architecture.get("data_objects", []), str(name), "input data object")
              for name in operation.get("inputs", [])]
    outputs = [_named(architecture.get("data_objects", []), str(name), "output data object")
               for name in operation.get("outputs", [])]

    def role(items: list[Mapping[str, Any]], name: str) -> Mapping[str, Any]:
        matches = [item for item in items if item.get("role") == name]
        if len(matches) != 1:
            raise ArithmeticMetadataError(f"integer_matrix_multiply needs exactly one object role {name!r}")
        return matches[0]

    left, right = role(inputs, "left_operand_matrix"), role(inputs, "right_operand_matrix")
    output = role(outputs, "result_matrix")
    ld, rd, od = [list(item.get("dimensions", [])) for item in (left, right, output)]
    if any(len(dims) != 2 for dims in (ld, rd, od)) or ld[1] != rd[0] or od != [ld[0], rd[1]]:
        raise ArithmeticMetadataError("integer_matrix_multiply requires A[M,K], B[K,N], result[M,N]")
    if declaration["reduction_dimensions"] != [ld[1]]:
        raise ArithmeticMetadataError("reduction_dimensions must name the shared A/B reduction axis")
    for name in set(ld + rd + od):
        dimension = _named(architecture.get("dimensions", []), name, "dimension")
        if dimension.get("runtime_configurable"):
            raise ArithmeticMetadataError("runtime-configurable shapes require llm_extension; this profile uses a fixed elaborated shape")
        low, high = dimension.get("minimum"), dimension.get("maximum")
        value = low if low == high else None
        if value is None:
            parameter = _named(architecture.get("parameters", []), str(dimension.get("bound_parameter", "")), "shape parameter")
            try:
                value = int(str(parameter.get("default_value", "")), 0)
            except ValueError as exc:
                raise ArithmeticMetadataError(f"dimension {name!r} needs an integer elaboration default") from exc
        if any(not isinstance(item, int) or isinstance(item, bool) for item in (value, low, high)) or not 0 < low <= value <= high:
            raise ArithmeticMetadataError(f"dimension {name!r} needs a positive fixed shape within its declared bounds")

    a_type, b_type = [_dtype(architecture, str(item["data_type"])) for item in (left, right)]
    product = _dtype(architecture, declaration["product_data_type"])
    accumulator = _dtype(architecture, declaration["accumulator_data_type"])
    result = _dtype(architecture, declaration["result_data_type"])
    def bounds(dtype: Mapping[str, Any]) -> tuple[int, int]:
        width = dtype["width_bits"]
        return (-(1 << (width - 1)), (1 << (width - 1)) - 1) if dtype["signed"] else (0, (1 << width) - 1)

    products = [a * b for a in bounds(a_type) for b in bounds(b_type)]
    product_low, product_high = bounds(product)
    if min(products) < product_low or max(products) > product_high:
        raise ArithmeticMetadataError("product_data_type must represent every exact A*B product without truncation")
    if declaration["result_data_type"] != output["data_type"]:
        raise ArithmeticMetadataError("result_data_type must match the declared output data object")

    stages = deepcopy(declaration["post_operations"])
    order = _resolve_post_operation_order(stages, declaration["post_output"])
    kinds = [stages[name]["kind"] for name in order]
    reserved_coverage_concepts = {
        "dimensions",
        "operand_values",
        "accumulation",
        "numeric_stage_events",
        "bias",
        "activation",
        "quantization",
    }
    formula_name_conflicts = sorted(
        name
        for name in order
        if stages[name]["kind"] == "llm_defined"
        and name in reserved_coverage_concepts
    )
    if formula_name_conflicts:
        raise ArithmeticMetadataError(
            "formula-defined post-operation stage names collide with reserved "
            f"coverage concepts: {formula_name_conflicts}"
        )
    # bias_add/wrap/relu/affine_quantize are each singular by construction (there is only one
    # sensible "the" bias add); llm_defined has no such constraint -- a
    # contract may declare several distinct llm_defined stages, disambiguated
    # by their own stage name and formula, not by kind.
    fixed_kinds = [kind for kind in kinds if kind != "llm_defined"]
    if len(fixed_kinds) != len(set(fixed_kinds)):
        raise ArithmeticMetadataError(
            "post_operations may declare each of "
            "bias_add/wrap/relu/affine_quantize at most once"
        )
    selected = set(operation.get("features", [])) | set(operation.get("feature_extensions", []))
    for feature, kind in (
        ("bias", "bias_add"),
        ("activation", "relu"),
        ("quantization", "affine_quantize"),
    ):
        if (feature in selected) != (kind in kinds):
            raise ArithmeticMetadataError(f"selected feature {feature!r} must agree with post_operations stage {kind!r}")
    modeled = {left["name"], right["name"]}
    for name in order:
        stage = stages[name]
        if stage["kind"] == "bias_add":
            bias = _named(inputs, stage["data_object"], "bias data object")
            if bias.get("role") != "per_output_column_bias" or bias.get("dimensions") != [od[1]] or stage["broadcast_dimensions"] != [od[1]]:
                raise ArithmeticMetadataError("bias_add requires a declared per-output-column bias and broadcast_dimensions=[N]")
            _dtype(architecture, str(bias["data_type"]))
            modeled.add(bias["name"])
        elif stage["kind"] == "wrap" and stage["data_type"] != accumulator["name"]:
            raise ArithmeticMetadataError("post-operation wrap must use accumulator_data_type")
        elif stage["kind"] == "affine_quantize":
            quantized_type = _dtype(architecture, str(stage["data_type"]))
            if quantized_type["name"] != result["name"]:
                raise ArithmeticMetadataError(
                    "affine_quantize data_type must match result_data_type"
                )
            quantized_low, quantized_high = bounds(quantized_type)
            if not quantized_low <= int(stage["zero_point"]) <= quantized_high:
                raise ArithmeticMetadataError(
                    "affine_quantize zero_point must be representable by data_type"
                )
        elif stage["kind"] == "llm_defined":
            try:
                compile_formula(stage["formula"])
            except FormulaError as exc:
                raise ArithmeticMetadataError(
                    f"post-operation {name!r} failed deterministic solver "
                    f"compilation: {exc}. Revise the formula, or explicitly "
                    "select classifier_profile='llm_extension' with an "
                    "operation-domain extension_request when the behavior is "
                    "not solver-representable"
                ) from exc
    if {item["name"] for item in inputs} != modeled or len(outputs) != 1:
        raise ArithmeticMetadataError("integer_matrix_multiply has unmodeled input/output objects; use llm_extension")
    if "bias_add" not in kinds and declaration["bias_conversion"] != "exact":
        raise ArithmeticMetadataError("bias_conversion must be exact when no bias_add stage exists")
    if "affine_quantize" in kinds and declaration["result_conversion"] != "exact":
        raise ArithmeticMetadataError(
            "result_conversion must be exact after saturating affine_quantize"
        )

    stage_labels = {
        "bias_add": "bias_add_with_explicit_conversion",
        "wrap": "wrap_accumulator",
        "relu": "relu_threshold_zero",
        "affine_quantize": "per_tensor_affine_quantize_nearest_even_saturate",
    }
    return {
        **deepcopy(dict(declaration)),
        "integer_evaluation": "unbounded_between_explicit_conversions",
        "product_data_type": {**product, "conversion": "exact"},
        "accumulator_type": accumulator,
        "result_data_type": {**result, "conversion": declaration["result_conversion"]},
        "resolved_stage_order": order,
        "stage_order": [
            "operand_decode", "exact_product", "ordered_reduction_with_explicit_conversion",
            *[
                stage_labels[kind] if kind != "llm_defined" else f"llm_defined_stage:{name}"
                for name, kind in zip(order, kinds)
            ],
            "result_conversion",
        ],
        "metadata_origin": "explicit_contract",
        "support_status": "supported_restricted_integer_gemm",
    }


def validate_resolved_arithmetic(metadata: Mapping[str, Any]) -> None:
    """Apply the same checks to externally supplied canonical metadata.

    Full verification_metadata must not bypass the compact declaration contract.
    This checks references and supported numeric rules, without filling any gaps.
    """
    arithmetic = metadata.get("arithmetic", {})
    profile = arithmetic.get("classifier_profile")
    from .structured import STRUCTURED_PROFILES, validate_structured_resolved
    if profile in STRUCTURED_PROFILES:
        validate_structured_resolved(metadata)
        return
    if profile == "llm_extension":
        for field in ("reason", "semantics"):
            if not isinstance(arithmetic.get(field), str) or not arithmetic[field].strip():
                raise ArithmeticMetadataError(f"llm_extension requires explicit {field}")
        return
    if profile == "integer_qk_score":
        branch = next(
            item
            for item in _schema()["anyOf"]
            if profile in item["properties"]["classifier_profile"]["enum"]
        )
        required = branch["required"]
        absent = sorted(set(required) - set(arithmetic))
        if absent:
            raise ArithmeticMetadataError(
                f"integer_qk_score arithmetic metadata is missing {absent}"
            )
        types: dict[str, dict[str, Any]] = {}

        def add_type(spec: Any) -> str:
            if not isinstance(spec, Mapping) or not {
                "name", "width_bits", "signed"
            } <= set(spec):
                raise ArithmeticMetadataError(
                    "resolved QK arithmetic needs complete declared data types"
                )
            item = {key: spec[key] for key in ("name", "width_bits", "signed")}
            if item["name"] in types and item != types[item["name"]]:
                raise ArithmeticMetadataError(
                    f"Conflicting type declarations for {item['name']!r}"
                )
            types[item["name"]] = item
            return str(item["name"])

        compact = {name: deepcopy(arithmetic[name]) for name in required}
        compact["score_product_data_type"] = add_type(
            arithmetic.get("score_product_data_type")
        )
        accumulator_name = add_type(arithmetic.get("score_accumulator_type"))
        compact["result_data_type"] = add_type(arithmetic.get("result_data_type"))
        if accumulator_name != arithmetic["score_accumulator_data_type"]:
            raise ArithmeticMetadataError(
                "score_accumulator_type must resolve score_accumulator_data_type"
            )
        objects = [
            {
                "name": binding["data_object"],
                "role": binding["object_role"],
                "data_type": add_type(binding.get("data_type")),
                "dimensions": list(binding["dimensions"]),
            }
            for binding in [*metadata.get("inputs", []), *metadata.get("outputs", [])]
        ]
        rebuilt = compile_operation_arithmetic(
            {
                "coverage_family": metadata.get("family"),
                "arithmetic": compact,
                "inputs": [item["data_object"] for item in metadata.get("inputs", [])],
                "outputs": [item["data_object"] for item in metadata.get("outputs", [])],
            },
            {
                "data_types": list(types.values()),
                "data_objects": objects,
                "dimensions": [
                    {
                        "name": name,
                        "minimum": value,
                        "maximum": value,
                        "runtime_configurable": False,
                    }
                    for name, value in metadata.get("dimensions", {}).items()
                ],
            },
        )
        for field in (
            "stage_order",
            "integer_evaluation",
            "support_status",
            "metadata_origin",
            "score_product_data_type",
            "score_accumulator_type",
            "result_data_type",
        ):
            if arithmetic.get(field) != rebuilt[field]:
                raise ArithmeticMetadataError(
                    f"resolved QK arithmetic.{field} disagrees with declared rules"
                )
        return
    if profile == "fixed_point_attention_scale":
        branch = next(
            item
            for item in _schema()["anyOf"]
            if profile in item["properties"]["classifier_profile"]["enum"]
        )
        required = branch["required"]
        absent = sorted(set(required) - set(arithmetic))
        if absent:
            raise ArithmeticMetadataError(
                f"fixed_point_attention_scale arithmetic metadata is missing {absent}"
            )
        types: dict[str, dict[str, Any]] = {}

        def add_type(spec: Any) -> str:
            if not isinstance(spec, Mapping) or not {
                "name", "width_bits", "signed"
            } <= set(spec):
                raise ArithmeticMetadataError(
                    "resolved attention-scale arithmetic needs complete declared data types"
                )
            item = {key: spec[key] for key in ("name", "width_bits", "signed")}
            if item["name"] in types and item != types[item["name"]]:
                raise ArithmeticMetadataError(
                    f"Conflicting type declarations for {item['name']!r}"
                )
            types[item["name"]] = item
            return str(item["name"])

        compact = {name: deepcopy(arithmetic[name]) for name in required}
        compact["product_data_type"] = add_type(arithmetic.get("product_data_type"))
        compact["result_data_type"] = add_type(arithmetic.get("result_data_type"))
        objects = [
            {
                "name": binding["data_object"],
                "role": binding["object_role"],
                "data_type": add_type(binding.get("data_type")),
                "dimensions": list(binding["dimensions"]),
            }
            for binding in [*metadata.get("inputs", []), *metadata.get("outputs", [])]
        ]
        head_dimension = str(compact["head_dimension"])
        if head_dimension not in metadata.get("dimensions", {}):
            raise ArithmeticMetadataError(
                f"resolved attention scale is missing head dimension {head_dimension!r}"
            )
        rebuilt = compile_operation_arithmetic(
            {
                "coverage_family": metadata.get("family"),
                "arithmetic": compact,
                "inputs": [item["data_object"] for item in metadata.get("inputs", [])],
                "outputs": [item["data_object"] for item in metadata.get("outputs", [])],
            },
            {
                "data_types": list(types.values()),
                "data_objects": objects,
                "dimensions": [
                    {
                        "name": name,
                        "minimum": value,
                        "maximum": value,
                        "runtime_configurable": False,
                    }
                    for name, value in metadata.get("dimensions", {}).items()
                ],
            },
        )
        for field in (
            "stage_order",
            "integer_evaluation",
            "support_status",
            "metadata_origin",
            "head_dimension_value",
            "product_data_type",
            "result_data_type",
        ):
            if arithmetic.get(field) != rebuilt[field]:
                raise ArithmeticMetadataError(
                    f"resolved attention-scale arithmetic.{field} disagrees with declared rules"
                )
        return
    if profile == "binary_attention_mask":
        branch = next(
            item
            for item in _schema()["anyOf"]
            if profile in item["properties"]["classifier_profile"]["enum"]
        )
        required = branch["required"]
        absent = sorted(set(required) - set(arithmetic))
        if absent:
            raise ArithmeticMetadataError(
                f"binary_attention_mask arithmetic metadata is missing {absent}"
            )
        types: dict[str, dict[str, Any]] = {}

        def add_type(spec: Any) -> str:
            if not isinstance(spec, Mapping) or not {
                "name", "width_bits", "signed"
            } <= set(spec):
                raise ArithmeticMetadataError(
                    "resolved attention-mask arithmetic needs complete declared data types"
                )
            item = {key: spec[key] for key in ("name", "width_bits", "signed")}
            if item["name"] in types and item != types[item["name"]]:
                raise ArithmeticMetadataError(
                    f"Conflicting type declarations for {item['name']!r}"
                )
            types[item["name"]] = item
            return str(item["name"])

        compact = {name: deepcopy(arithmetic[name]) for name in required}
        compact["result_data_type"] = add_type(arithmetic.get("result_data_type"))
        objects = [
            {
                "name": binding["data_object"],
                "role": binding["object_role"],
                "data_type": add_type(binding.get("data_type")),
                "dimensions": list(binding["dimensions"]),
            }
            for binding in [*metadata.get("inputs", []), *metadata.get("outputs", [])]
        ]
        rebuilt = compile_operation_arithmetic(
            {
                "coverage_family": metadata.get("family"),
                "arithmetic": compact,
                "inputs": [item["data_object"] for item in metadata.get("inputs", [])],
                "outputs": [item["data_object"] for item in metadata.get("outputs", [])],
            },
            {
                "data_types": list(types.values()),
                "data_objects": objects,
                "dimensions": [
                    {
                        "name": name,
                        "minimum": value,
                        "maximum": value,
                        "runtime_configurable": False,
                    }
                    for name, value in metadata.get("dimensions", {}).items()
                ],
            },
        )
        for field in (
            "stage_order",
            "integer_evaluation",
            "support_status",
            "metadata_origin",
            "result_data_type",
        ):
            if arithmetic.get(field) != rebuilt[field]:
                raise ArithmeticMetadataError(
                    f"resolved attention-mask arithmetic.{field} disagrees with declared rules"
                )
        return
    if profile == "integer_sparse_attention":
        branch = next(
            item
            for item in _schema()["anyOf"]
            if profile in item["properties"]["classifier_profile"]["enum"]
        )
        required = branch["required"]
        absent = sorted(set(required) - set(arithmetic))
        if absent:
            raise ArithmeticMetadataError(
                f"integer_sparse_attention arithmetic metadata is missing {absent}"
            )
        types: dict[str, dict[str, Any]] = {}

        def add_type(spec: Any) -> str:
            if not isinstance(spec, Mapping) or not {
                "name", "width_bits", "signed"
            } <= set(spec):
                raise ArithmeticMetadataError(
                    "resolved sparse attention arithmetic needs complete declared data types"
                )
            item = {
                key: spec[key] for key in ("name", "width_bits", "signed")
            }
            if item["name"] in types and item != types[item["name"]]:
                raise ArithmeticMetadataError(
                    f"Conflicting type declarations for {item['name']!r}"
                )
            types[item["name"]] = item
            return str(item["name"])

        compact = {name: deepcopy(arithmetic[name]) for name in required}
        compact["score_product_data_type"] = add_type(
            arithmetic.get("score_product_data_type")
        )
        score_accumulator_name = add_type(
            arithmetic.get("score_accumulator_type")
        )
        compact["output_product_data_type"] = add_type(
            arithmetic.get("output_product_data_type")
        )
        output_accumulator_name = add_type(
            arithmetic.get("output_accumulator_type")
        )
        compact["result_data_type"] = add_type(arithmetic.get("result_data_type"))
        if score_accumulator_name != arithmetic["score_accumulator_data_type"]:
            raise ArithmeticMetadataError(
                "score_accumulator_type must resolve score_accumulator_data_type"
            )
        if output_accumulator_name != arithmetic["output_accumulator_data_type"]:
            raise ArithmeticMetadataError(
                "output_accumulator_type must resolve output_accumulator_data_type"
            )
        objects = [
            {
                "name": binding["data_object"],
                "role": binding["object_role"],
                "data_type": add_type(binding.get("data_type")),
                "dimensions": list(binding["dimensions"]),
            }
            for binding in [*metadata.get("inputs", []), *metadata.get("outputs", [])]
        ]
        operation = {
            "coverage_family": metadata.get("family"),
            "arithmetic": compact,
            "inputs": [binding["data_object"] for binding in metadata.get("inputs", [])],
            "outputs": [binding["data_object"] for binding in metadata.get("outputs", [])],
        }
        rebuilt = compile_operation_arithmetic(
            operation,
            {
                "data_types": list(types.values()),
                "data_objects": objects,
                "dimensions": [
                    {
                        "name": name,
                        "minimum": value,
                        "maximum": value,
                        "runtime_configurable": False,
                    }
                    for name, value in metadata.get("dimensions", {}).items()
                ],
            },
        )
        for field in (
            "stage_order",
            "integer_evaluation",
            "support_status",
            "metadata_origin",
            "score_product_data_type",
            "score_accumulator_type",
            "output_product_data_type",
            "output_accumulator_type",
            "result_data_type",
        ):
            if arithmetic.get(field) != rebuilt[field]:
                raise ArithmeticMetadataError(
                    f"resolved sparse attention arithmetic.{field} disagrees with declared rules"
                )
        return
    if profile != "integer_matrix_multiply":
        raise ArithmeticMetadataError(f"Unknown classifier_profile={profile!r}; declare llm_extension explicitly")
    types: dict[str, dict[str, Any]] = {}

    def add_type(spec: Any) -> str:
        if not isinstance(spec, Mapping) or not {"name", "width_bits", "signed"} <= set(spec):
            raise ArithmeticMetadataError("resolved arithmetic needs complete declared data types")
        item = {key: spec[key] for key in ("name", "width_bits", "signed")}
        if item["name"] in types and item != types[item["name"]]:
            raise ArithmeticMetadataError(f"Conflicting type declarations for {item['name']!r}")
        types[item["name"]] = item
        return item["name"]

    required = _schema()["anyOf"][0]["required"]
    absent = sorted(set(required) - set(arithmetic))
    if absent:
        raise ArithmeticMetadataError(f"integer_matrix_multiply arithmetic metadata is missing {absent}")
    compact = {name: deepcopy(arithmetic[name]) for name in required}
    product, accumulator, result = (arithmetic.get(name) for name in ("product_data_type", "accumulator_type", "result_data_type"))
    compact["product_data_type"] = add_type(product)
    accumulator_name = add_type(accumulator)
    compact["result_data_type"] = add_type(result)
    if accumulator_name != arithmetic["accumulator_data_type"]:
        raise ArithmeticMetadataError("accumulator_type must resolve accumulator_data_type")
    if product.get("conversion") != "exact" or result.get("conversion") != arithmetic["result_conversion"]:
        raise ArithmeticMetadataError("resolved product/result conversions disagree with the explicit declaration")
    objects = [
        {"name": binding["data_object"], "role": binding["object_role"],
         "data_type": add_type(binding.get("data_type")), "dimensions": list(binding["dimensions"])}
        for binding in [*metadata.get("inputs", []), *metadata.get("outputs", [])]
    ]
    operation = {
        "coverage_family": metadata.get("family"), "arithmetic": compact,
        "inputs": [b["data_object"] for b in metadata.get("inputs", [])],
        "outputs": [b["data_object"] for b in metadata.get("outputs", [])],
        "features": [feature for feature, kind in (
                         ("bias", "bias_add"),
                         ("activation", "relu"),
                         ("quantization", "affine_quantize"),
                     )
                     if any(stage.get("kind") == kind for stage in arithmetic["post_operations"].values())],
    }
    rebuilt = compile_operation_arithmetic(operation, {
        "data_types": list(types.values()), "data_objects": objects,
        "dimensions": [{"name": name, "minimum": value, "maximum": value, "runtime_configurable": False}
                       for name, value in metadata.get("dimensions", {}).items()],
    })
    for field in ("stage_order", "resolved_stage_order", "integer_evaluation", "support_status", "metadata_origin"):
        if arithmetic.get(field) != rebuilt[field]:
            raise ArithmeticMetadataError(f"resolved arithmetic.{field} disagrees with declared rules")


def validate_architecture_operation_arithmetic(
    architecture: Mapping[str, Any], *, require_arithmetic: bool = True,
    previous_architecture: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate initial declarations and forbid erasing them during revisions."""

    previous = {str(item.get("name", "")) for item in (previous_architecture or {}).get("operations", [])
                if isinstance(item, Mapping) and "arithmetic" in item}
    errors: list[str] = []
    dimension_extents = {
        str(item["name"]): int(item["minimum"])
        for item in architecture.get("dimensions", [])
        if isinstance(item, Mapping) and item.get("minimum") == item.get("maximum")
    }
    data_type_widths = {
        str(item["name"]): int(item["width_bits"])
        for item in architecture.get("data_types", [])
        if isinstance(item, Mapping)
    }
    for obj in architecture.get("data_objects", []):
        try:
            declared_serialization(
                obj,
                dimension_extents=dimension_extents,
                element_width_bits=data_type_widths.get(str(obj.get("data_type", ""))),
            )
        except ValueError as exc:
            errors.append(str(exc))
    for operation in architecture.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        name = str(operation.get("name", ""))
        if "arithmetic" not in operation:
            if require_arithmetic or name in previous:
                errors.append(f"operation {name!r}.arithmetic is required; explicit semantics cannot fall back to legacy inference")
            continue
        try:
            compile_operation_arithmetic(operation, architecture)
        except ArithmeticMetadataError as exc:
            errors.append(f"operation {name!r}.arithmetic: {exc}")
    return errors


def operation_formula_compilation_report(
    architecture: Mapping[str, Any],
) -> dict[str, Any]:
    """Report the Contract Reviewer's solver decision for every operation.

    Coverage goals are intentionally absent: the Architect declares operation
    semantics, while the Verifier owns bins and predicates after the formula
    has crossed this compilation gate.
    """

    entries: list[dict[str, Any]] = []
    for operation in architecture.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        operation_name = str(operation.get("name", ""))
        declaration = operation.get("arithmetic")
        if not isinstance(declaration, Mapping):
            entries.append(
                {
                    "operation": operation_name,
                    "status": "missing_arithmetic",
                    "stages": [],
                }
            )
            continue
        if declaration.get("classifier_profile") == "llm_extension":
            entries.append(
                {
                    "operation": operation_name,
                    "status": "architect_declared_llm_extension",
                    "reason": str(declaration.get("reason", "")),
                    "extension_request": declaration.get("extension_request"),
                    "stages": [],
                }
            )
            continue
        stages: list[dict[str, Any]] = []
        failed = False
        post_operations = declaration.get("post_operations", {})
        if isinstance(post_operations, Mapping):
            for stage_name, stage in post_operations.items():
                if not isinstance(stage, Mapping) or stage.get("kind") != "llm_defined":
                    continue
                formula = str(stage.get("formula", ""))
                try:
                    compiled = compile_formula(formula)
                except FormulaError as exc:
                    failed = True
                    stages.append(
                        {
                            "stage": str(stage_name),
                            "status": "solver_compile_failed",
                            "formula": formula,
                            "diagnostic": str(exc),
                        }
                    )
                else:
                    stages.append(
                        {
                            "stage": str(stage_name),
                            "status": "solver_compiled",
                            "formula": formula,
                            "solver_ir": str(compiled.expression),
                            "domain_constraints": [
                                str(item) for item in compiled.constraints
                            ],
                        }
                    )
        entries.append(
            {
                "operation": operation_name,
                "status": "solver_compile_failed" if failed else "solver_ready",
                "stages": stages,
            }
        )
    return {
        "schema_version": 1,
        "owner": "contract_reviewer",
        "coverage_owner": "verifier",
        "status": (
            "BLOCKED"
            if any(item["status"] in {"missing_arithmetic", "solver_compile_failed"} for item in entries)
            else "PASS"
        ),
        "operations": entries,
    }


__all__ = [
    "OPERATION_ARITHMETIC_SCHEMA_PATH", "ArithmeticMetadataError",
    "compile_operation_arithmetic", "operation_arithmetic_schema",
    "operation_formula_compilation_report",
    "validate_architecture_operation_arithmetic", "with_operation_arithmetic_schema",
]
