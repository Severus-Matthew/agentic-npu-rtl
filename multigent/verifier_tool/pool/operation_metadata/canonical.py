"""Canonical jobs and code-owned classifiers for known operation families."""

from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Any, Mapping, Sequence

from .formula import evaluate_formula


class CanonicalOperationError(AssertionError):
    """A checked TB transaction does not match its Architect I/O metadata."""


@dataclass(frozen=True)
class CanonicalOperationJob:
    operation_name: str
    family: str
    dimensions: Mapping[str, int]
    inputs: Mapping[str, tuple[int, ...]]
    expected: Mapping[str, Any]
    observed: Mapping[str, Any]
    metadata: Mapping[str, Any]


_MATRIX_CONCEPTS = {
    "dimensions", "operand_values", "accumulation",
    "bias", "activation", "quantization",
}

_SPARSE_ATTENTION_CONCEPTS = {
    "dimensions",
    "operand_values",
    "sparsity_patterns",
    "attention_scores",
    "stage_handoffs",
    "output_values",
}

_QK_SCORE_CONCEPTS = {
    "dimensions",
    "operand_values",
    "accumulation",
    "attention_scores",
}

_ATTENTION_SCALE_CONCEPTS = {
    "dimensions",
    "score_values",
    "rounding",
    "scaled_values",
    "attenuation",
}

_ATTENTION_MASK_CONCEPTS = {
    "dimensions",
    "score_values",
    "mask_values",
    "sparsity_patterns",
    "masked_values",
    "mask_effects",
}


def supported_code_owned_concepts(metadata: Mapping[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for operation in metadata.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        profile = operation.get("arithmetic", {}).get("classifier_profile")
        if profile == "integer_matrix_multiply":
            concepts = {
                "dimensions", "operand_values", "accumulation"
            }
            post_operations = operation.get("arithmetic", {}).get(
                "post_operations", {}
            ).values()
            if any(item.get("kind") == "bias_add" for item in post_operations):
                concepts.add("bias")
            if any(item.get("kind") == "relu" for item in post_operations):
                concepts.add("activation")
            if any(
                item.get("kind") == "affine_quantize"
                for item in post_operations
            ):
                concepts.add("quantization")
            result[str(operation.get("operation_name", ""))] = concepts
        elif profile == "integer_sparse_attention":
            result[str(operation.get("operation_name", ""))] = set(
                _SPARSE_ATTENTION_CONCEPTS
            )
        elif profile == "integer_qk_score":
            result[str(operation.get("operation_name", ""))] = set(
                _QK_SCORE_CONCEPTS
            )
        elif profile == "fixed_point_attention_scale":
            result[str(operation.get("operation_name", ""))] = set(
                _ATTENTION_SCALE_CONCEPTS
            )
        elif profile == "binary_attention_mask":
            result[str(operation.get("operation_name", ""))] = set(
                _ATTENTION_MASK_CONCEPTS
            )
    return result


def solver_compiled_formula_concepts(
    metadata: Mapping[str, Any],
) -> dict[str, set[str]]:
    """Formula-stage concepts sampled from the canonical golden trace.

    Their arithmetic observation is tool-owned, but their coverage bins and
    predicates are Verifier-owned.  Keeping this separate from
    :func:`supported_code_owned_concepts` prevents deterministic synthesis from
    inventing coverage intent for a new mathematical feature.
    """

    result: dict[str, set[str]] = {}
    for operation in metadata.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        stages = operation.get("arithmetic", {}).get("post_operations", {})
        if not isinstance(stages, Mapping):
            continue
        concepts = {
            str(name)
            for name, stage in stages.items()
            if isinstance(stage, Mapping) and stage.get("kind") == "llm_defined"
        }
        if concepts:
            result[str(operation.get("operation_name", ""))] = concepts
    return result


def _flatten(value: Any, path: str) -> tuple[int, ...]:
    result: list[int] = []

    def visit(item: Any) -> None:
        if isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
            return
        if isinstance(item, bool) or not isinstance(item, int):
            raise CanonicalOperationError(f"{path} must contain only integer elements")
        result.append(int(item))

    visit(value)
    return tuple(result)


def _lookup_payload(mapping: Mapping[str, Any], binding: Mapping[str, Any]) -> Any:
    exact = str(binding["data_object"])
    if exact in mapping:
        return mapping[exact]
    # Compatibility aliases are derived from declared object roles, not signal names.
    role = str(binding.get("object_role", ""))
    aliases = {
        "left_operand_matrix": ("a", "A"),
        "right_operand_matrix": ("b", "B"),
        "per_output_column_bias": ("bias",),
        "result_matrix": ("y", "Y"),
        "query_matrix": ("q", "Q"),
        "key_matrix": ("k", "K"),
        "value_matrix": ("v", "V"),
        "attention_mask": ("mask", "MASK"),
        "attention_score_matrix": ("score", "S", "scores"),
        "scaled_attention_score_matrix": (
            "scaled_score", "scaled_scores", "scaled_S"
        ),
        "masked_attention_score_matrix": (
            "masked_score", "masked_scores", "masked_S"
        ),
        "attention_result": ("y", "Y"),
    }.get(role, ())
    present = [name for name in aliases if name in mapping]
    if len(present) == 1:
        return mapping[present[0]]
    raise KeyError(exact)


def assemble_canonical_job(
    operation_metadata: Mapping[str, Any],
    stimulus: Mapping[str, Any],
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> CanonicalOperationJob | None:
    """Assemble one complete functional job, or skip a protocol-only transaction."""

    inputs: dict[str, tuple[int, ...]] = {}
    found_any = False
    for binding in operation_metadata.get("inputs", []):
        try:
            raw = _lookup_payload(stimulus, binding)
        except KeyError:
            continue
        found_any = True
        values = _flatten(raw, str(binding["data_object"]))
        shape = [operation_metadata.get("dimensions", {}).get(name) for name in binding.get("dimensions", [])]
        if all(isinstance(size, int) and size >= 0 for size in shape):
            required = prod(shape) if shape else 1
            if len(values) != required:
                raise CanonicalOperationError(
                    f"{binding['data_object']} accepted-value count {len(values)} != canonical shape {shape} ({required})"
                )
        inputs[str(binding["data_object"])] = values
    if not found_any:
        return None
    missing = [
        str(binding["data_object"])
        for binding in operation_metadata.get("inputs", [])
        if str(binding["data_object"]) not in inputs
    ]
    if missing:
        raise CanonicalOperationError(
            f"Functional job is missing accepted input data objects {missing}"
        )
    return CanonicalOperationJob(
        operation_name=str(operation_metadata["operation_name"]),
        family=str(operation_metadata["family"]),
        dimensions={
            str(key): int(value)
            for key, value in operation_metadata.get("dimensions", {}).items()
            if isinstance(value, int)
        },
        inputs=inputs,
        expected=expected,
        observed=observed,
        metadata=operation_metadata,
    )


def _binding_by_role(metadata: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    bindings = [
        item for item in [*metadata.get("inputs", []), *metadata.get("outputs", [])]
        if item.get("object_role") == role
    ]
    if len(bindings) != 1:
        raise CanonicalOperationError(f"Expected one canonical object role {role!r}")
    return bindings[0]


def _dtype(metadata: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    arithmetic = metadata.get("arithmetic", {})
    for field in (
        "accumulator_type",
        "score_product_data_type",
        "score_accumulator_type",
        "output_product_data_type",
        "output_accumulator_type",
        "result_data_type",
    ):
        dtype = arithmetic.get(field, {})
        if isinstance(dtype, Mapping) and dtype.get("name") == name:
            return dtype
    for item in [*metadata.get("inputs", []), *metadata.get("outputs", [])]:
        dtype = item.get("data_type", {})
        if dtype.get("name") == name:
            return dtype
    raise CanonicalOperationError(f"Unknown canonical data type {name!r}")


def _integer_bounds(dtype: Mapping[str, Any]) -> tuple[int, int]:
    width = int(dtype["width_bits"])
    signed = bool(dtype["signed"])
    return (-(1 << (width - 1)), (1 << (width - 1)) - 1) if signed else (0, (1 << width) - 1)


def _wrap(value: int, dtype: Mapping[str, Any]) -> int:
    width = int(dtype["width_bits"])
    mask = (1 << width) - 1
    result = value & mask
    if bool(dtype["signed"]) and result & (1 << (width - 1)):
        result -= 1 << width
    return result


def _round_divide_nearest_even(numerator: int, denominator: int) -> int:
    """Round an exact signed rational to nearest, resolving ties to even."""

    if denominator <= 0:
        raise CanonicalOperationError("quantization denominator must be positive")
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    doubled = remainder * 2
    if doubled > denominator or (doubled == denominator and quotient % 2 == 1):
        quotient += 1
    return sign * quotient


def _affine_quantize(
    value: int,
    stage: Mapping[str, Any],
    dtype: Mapping[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Apply the supported per-tensor fixed-point affine quantizer exactly."""

    multiplier = int(stage["scale_multiplier"])
    shift = int(stage["scale_shift"])
    denominator = 1 << shift
    numerator = int(value) * multiplier
    scaled = _round_divide_nearest_even(numerator, denominator)
    raw_quantized = scaled + int(stage["zero_point"])
    low, high = _integer_bounds(dtype)
    quantized = min(max(raw_quantized, low), high)
    classes = ["exact" if numerator % denominator == 0 else "rounded"]
    if int(stage["zero_point"]) != 0:
        classes.append("nonzero_zero_point")
    if raw_quantized < low:
        classes.append("negative_saturation")
    elif raw_quantized > high:
        classes.append("positive_saturation")
    return quantized, {
        "input": int(value),
        "scale_multiplier": multiplier,
        "scale_shift": shift,
        "zero_point": int(stage["zero_point"]),
        "scaled": scaled,
        "raw_quantized": raw_quantized,
        "quantized": quantized,
        "classes": classes,
    }


def _reduction_trace(
    terms: Sequence[int],
    accumulator_dtype: Mapping[str, Any],
    conversion: str,
) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    """Return final accumulator plus mathematical and converted prefix traces."""

    mathematical: list[int] = []
    converted: list[int] = []
    value = 0
    reference = 0
    for term in terms:
        reference += int(term)
        mathematical.append(reference)
        value += int(term)
        if conversion == "wrap_twos_complement_after_each_add":
            value = _wrap(value, accumulator_dtype)
        elif conversion != "exact":
            raise CanonicalOperationError(
                f"Unsupported reduction conversion {conversion!r}"
            )
        converted.append(value)
    return value, tuple(mathematical), tuple(converted)


def integer_matrix_multiply_events(
    a: Sequence[int],
    b: Sequence[int],
    bias: Sequence[int],
    *,
    m: int,
    k: int,
    n: int,
    accumulator_dtype: Mapping[str, Any],
    reduction_conversion: str,
    post_operations: Mapping[str, Any],
    resolved_stage_order: Sequence[str],
    bias_conversion: str,
    result_dtype: Mapping[str, Any] | None = None,
    result_conversion: str = "exact",
) -> list[dict[str, Any]]:
    """The one product -> reduction -> post-op DAG -> result-conversion walk
    every integer_matrix_multiply consumer needs, computed once instead of
    independently by `evaluate_canonical_operation` (golden values) and
    `_classify_integer_matrix_multiply` (classification evidence) -- the two
    used to each replay this same arithmetic with their own copy of the
    loop, one stopping before `result_conversion`, the other never applying
    it at all. Each returned event carries every number either caller
    wants: `mathematical_reduction_prefixes` for classifying excursions,
    `converted_reduction_prefixes` for the actual converted running value,
    `bias_excursion`/`pre_activation` for activation-bin classification,
    and `result_value` -- the actual golden output, honoring
    `result_conversion` -- so a caller that only wants golden values never
    needs to know the trace exists, and one that needs the trace never has
    to recompute it to also get the final value.
    """

    accumulator_low, accumulator_high = _integer_bounds(accumulator_dtype)
    events: list[dict[str, Any]] = []
    for row in range(m):
        for column in range(n):
            terms = [a[row * k + depth] * b[depth * n + column] for depth in range(k)]
            value, mathematical_prefixes, converted_prefixes = _reduction_trace(
                terms, accumulator_dtype, reduction_conversion
            )
            reduction_final = value
            bias_excursion = False
            # Walk the resolved DAG order rather than a fixed bias->wrap->relu
            # sequence, so this stays correct for any depends_on chain. relu
            # must actually clamp `value` here (not just label it) so a stage
            # placed after relu in a future contract would see the real
            # post-clamp value; `activation_value` separately remembers what
            # relu itself received, wherever it sits.
            activation_value = value
            quantization_trace: dict[str, Any] | None = None
            formula_stage_values: dict[str, dict[str, int]] = {}
            for name in resolved_stage_order:
                stage = post_operations[name]
                kind = stage.get("kind")
                if kind == "bias_add":
                    raw_bias_sum = value + (bias[column] if bias else 0)
                    bias_excursion = raw_bias_sum < accumulator_low or raw_bias_sum > accumulator_high
                    value = raw_bias_sum
                    if bias_conversion == "wrap_twos_complement_after_add":
                        value = _wrap(value, accumulator_dtype)
                    elif bias_conversion != "exact":
                        raise CanonicalOperationError(
                            f"Unsupported bias conversion {bias_conversion!r}"
                        )
                elif kind == "wrap":
                    value = _wrap(value, accumulator_dtype)
                elif kind == "relu":
                    activation_value = value
                    value = max(0, value)
                elif kind == "affine_quantize":
                    if result_dtype is None:
                        raise CanonicalOperationError(
                            "affine_quantize requires a resolved result data type"
                        )
                    if str(stage.get("data_type", "")) != str(
                        result_dtype.get("name", "")
                    ):
                        raise CanonicalOperationError(
                            "affine_quantize data_type disagrees with result data type"
                        )
                    value, quantization_trace = _affine_quantize(
                        value, stage, result_dtype
                    )
                elif kind == "llm_defined":
                    # An Architect-declared post-op this file has no built-in
                    # kind for, accepted by formula.py's solver compiler --
                    # see its module docstring for why this, rather than a
                    # blanket llm_extension fallback, is what keeps every
                    # concept that never looks past this stage (accumulation,
                    # dimensions, operand_values, and bias/activation if they
                    # sit earlier in the chain) fully code-owned.
                    stage_input = value
                    value = evaluate_formula(str(stage["formula"]), value)
                    formula_stage_values[str(name)] = {
                        "input": stage_input,
                        "output": value,
                    }
            result_value = value
            if result_conversion == "wrap_twos_complement":
                result_value = _wrap(result_value, result_dtype or accumulator_dtype)
            elif result_conversion != "exact":
                raise CanonicalOperationError(
                    f"Unsupported result conversion {result_conversion!r}"
                )
            events.append(
                {
                    "coordinate": [row, column],
                    "product_terms": list(terms),
                    "mathematical_reduction_prefixes": list(mathematical_prefixes),
                    "converted_reduction_prefixes": list(converted_prefixes),
                    "reduction_final": reduction_final,
                    "bias_excursion": bias_excursion,
                    "pre_activation": activation_value,
                    "quantization": quantization_trace,
                    "formula_stages": formula_stage_values,
                    "result_value": result_value,
                }
            )
    return events


def _classify_integer_matrix_multiply(job: CanonicalOperationJob) -> dict[str, list[Any]]:
    metadata = job.metadata
    left = _binding_by_role(metadata, "left_operand_matrix")
    right = _binding_by_role(metadata, "right_operand_matrix")
    output = _binding_by_role(metadata, "result_matrix")
    a = job.inputs[str(left["data_object"])]
    b = job.inputs[str(right["data_object"])]
    left_dims, right_dims, out_dims = left["dimensions"], right["dimensions"], output["dimensions"]
    if len(left_dims) != 2 or len(right_dims) != 2 or len(out_dims) != 2:
        raise CanonicalOperationError("integer_matrix_multiply requires rank-2 A, B, and Y")
    m = job.dimensions[left_dims[0]]
    k = job.dimensions[left_dims[1]]
    if right_dims[0] != left_dims[1]:
        raise CanonicalOperationError("GEMM reduction dimension mismatch in metadata")
    n = job.dimensions[right_dims[1]]
    if out_dims != [left_dims[0], right_dims[1]]:
        raise CanonicalOperationError("GEMM result dimensions do not match A/B metadata")

    arithmetic = metadata.get("arithmetic", {})
    accumulator_name = arithmetic.get("accumulator_data_type")
    accumulator_dtype = _dtype(metadata, str(accumulator_name))
    low, high = _integer_bounds(accumulator_dtype)
    post_operations: Mapping[str, Any] = arithmetic.get("post_operations", {})
    resolved_order: Sequence[str] = arithmetic.get("resolved_stage_order", [])
    bias_binding = next(
        (
            item for item in metadata.get("inputs", [])
            if any(
                stage.get("kind") == "bias_add" and stage.get("data_object") == item.get("data_object")
                for stage in post_operations.values()
            )
        ),
        None,
    )
    bias = job.inputs[str(bias_binding["data_object"])] if bias_binding else ()

    has_relu = any(stage.get("kind") == "relu" for stage in post_operations.values())
    has_quantization = any(
        stage.get("kind") == "affine_quantize"
        for stage in post_operations.values()
    )
    events = integer_matrix_multiply_events(
        a,
        b,
        bias,
        m=m,
        k=k,
        n=n,
        accumulator_dtype=accumulator_dtype,
        reduction_conversion=str(arithmetic.get("reduction_conversion", "exact")),
        post_operations=post_operations,
        resolved_stage_order=resolved_order,
        bias_conversion=str(arithmetic.get("bias_conversion", "exact")),
        result_dtype=output["data_type"] if has_quantization else None,
        # Classification is about the accumulator pipeline (excursions,
        # boundaries, activation sign) -- it never looks at the converted
        # output dtype, so result_conversion is left at its "exact" default.
    )

    accum_classes: list[str] = []
    numeric_stage_events: list[dict[str, Any]] = []
    pre_activation: list[int] = []
    quantization_classes: list[str] = []
    for event in events:
        mathematical_prefixes = event["mathematical_reduction_prefixes"]
        reduction_excursion = any(
            item < low or item > high for item in mathematical_prefixes
        )
        reduction_boundary = any(
            item in {low, high} for item in mathematical_prefixes
        )
        reduction_classes: list[str] = []
        if any(item == high for item in mathematical_prefixes):
            reduction_classes.append("positive_boundary")
        if any(item == low for item in mathematical_prefixes):
            reduction_classes.append("negative_boundary")
        if any(item > high for item in mathematical_prefixes):
            reduction_classes.append("positive_overflow")
        if any(item < low for item in mathematical_prefixes):
            reduction_classes.append("negative_overflow")
        accum_classes.extend(reduction_classes or ["ordinary"])
        pre_activation.append(event["pre_activation"])
        quantization = event.get("quantization")
        if isinstance(quantization, Mapping):
            quantization_classes.extend(map(str, quantization.get("classes", [])))
        numeric_stage_events.append(
            {
                "coordinate": event["coordinate"],
                "product_terms": event["product_terms"],
                "mathematical_reduction_prefixes": event["mathematical_reduction_prefixes"],
                "converted_reduction_prefixes": event["converted_reduction_prefixes"],
                "reduction_excursion": reduction_excursion,
                "reduction_boundary": reduction_boundary,
                "reduction_final": event["reduction_final"],
                "bias_excursion": event["bias_excursion"],
                "pre_activation": event["pre_activation"],
                "quantization": event.get("quantization"),
                "internal_dut_state_observed": False,
            }
        )

    result: dict[str, list[Any]] = {
        "dimensions": ["fixed"],
        "operand_values": [*a, *b],
        "accumulation": accum_classes,
        "numeric_stage_events": numeric_stage_events,
    }
    if bias:
        result["bias"] = list(bias)
    if has_relu:
        result["activation"] = [
            "negative" if value < 0 else "zero" if value == 0 else "positive"
            for value in pre_activation
        ]
    if has_quantization:
        result["quantization"] = quantization_classes
    formula_stage_names = [
        str(name)
        for name in resolved_order
        if post_operations.get(name, {}).get("kind") == "llm_defined"
    ]
    for stage_name in formula_stage_names:
        result[stage_name] = [
            event["formula_stages"][stage_name]["output"] for event in events
        ]
    return result


def integer_qk_score_events(
    query: Sequence[int],
    key: Sequence[int],
    *,
    query_count: int,
    key_count: int,
    feature_count: int,
    score_accumulator_dtype: Mapping[str, Any],
    score_reduction_conversion: str,
    result_dtype: Mapping[str, Any],
    result_conversion: str,
) -> list[dict[str, Any]]:
    """Evaluate raw row-major ``Q*K^T`` scores and retain each reduction trace."""

    events: list[dict[str, Any]] = []
    for query_index in range(query_count):
        for key_index in range(key_count):
            terms = [
                query[query_index * feature_count + depth]
                * key[key_index * feature_count + depth]
                for depth in range(feature_count)
            ]
            score, mathematical, converted = _reduction_trace(
                terms,
                score_accumulator_dtype,
                score_reduction_conversion,
            )
            result_value = score
            if result_conversion == "wrap_twos_complement":
                result_value = _wrap(result_value, result_dtype)
            elif result_conversion != "exact":
                raise CanonicalOperationError(
                    f"Unsupported QK score result conversion {result_conversion!r}"
                )
            events.append(
                {
                    "coordinate": [query_index, key_index],
                    "product_terms": list(terms),
                    "mathematical_reduction_prefixes": list(mathematical),
                    "converted_reduction_prefixes": list(converted),
                    "reduction_final": score,
                    "result_value": result_value,
                }
            )
    return events


def fixed_point_attention_scale_events(
    scores: Sequence[int],
    *,
    query_count: int,
    key_count: int,
    scale_multiplier: int,
    scale_shift: int,
    rounding: str,
    result_dtype: Mapping[str, Any],
    result_conversion: str,
) -> list[dict[str, Any]]:
    """Scale signed QK scores by multiplier/2**shift in coordinate order."""

    if len(scores) != query_count * key_count:
        raise CanonicalOperationError(
            "attention scale input count does not match Q by S shape"
        )
    if rounding != "arithmetic_floor":
        raise CanonicalOperationError(
            f"Unsupported attention-scale rounding {rounding!r}"
        )
    denominator = 1 << scale_shift
    events: list[dict[str, Any]] = []
    for index, raw_score in enumerate(scores):
        score = int(raw_score)
        product = score * scale_multiplier
        shifted = product // denominator
        result_value = shifted
        if result_conversion == "wrap_twos_complement":
            result_value = _wrap(result_value, result_dtype)
        elif result_conversion != "exact":
            raise CanonicalOperationError(
                f"Unsupported attention-scale result conversion {result_conversion!r}"
            )
        fractional = product % denominator != 0
        events.append(
            {
                "coordinate": [index // key_count, index % key_count],
                "score": score,
                "scale_multiplier": scale_multiplier,
                "scale_shift": scale_shift,
                "exact_product": product,
                "fraction_discarded": fractional,
                "rounding_class": (
                    "exact"
                    if not fractional
                    else "positive_fraction_discarded"
                    if score > 0
                    else "negative_fraction_discarded"
                ),
                "shifted_value": shifted,
                "result_value": result_value,
            }
        )
    return events


def binary_attention_mask_events(
    scores: Sequence[int],
    mask: Sequence[int],
    *,
    query_count: int,
    key_count: int,
    mask_mode: str,
    result_dtype: Mapping[str, Any],
    result_conversion: str,
) -> list[dict[str, Any]]:
    """Apply an independent binary-keep mask to signed scaled scores."""

    element_count = query_count * key_count
    if len(scores) != element_count or len(mask) != element_count:
        raise CanonicalOperationError(
            "attention mask input counts do not match Q by S shape"
        )
    if mask_mode != "binary_keep":
        raise CanonicalOperationError(
            f"Unsupported attention-mask mode {mask_mode!r}"
        )
    if any(item not in {0, 1} for item in mask):
        raise CanonicalOperationError(
            "binary_keep attention mask accepts only 0 and 1"
        )
    events: list[dict[str, Any]] = []
    for index, (raw_score, raw_mask) in enumerate(zip(scores, mask)):
        score = int(raw_score)
        mask_value = int(raw_mask)
        masked_score = score if mask_value == 1 else 0
        result_value = masked_score
        if result_conversion == "wrap_twos_complement":
            result_value = _wrap(result_value, result_dtype)
        elif result_conversion != "exact":
            raise CanonicalOperationError(
                f"Unsupported attention-mask result conversion {result_conversion!r}"
            )
        events.append(
            {
                "coordinate": [index // key_count, index % key_count],
                "scaled_score": score,
                "mask_value": mask_value,
                "active": mask_value == 1,
                "mask_mode": "binary_keep",
                "masked_score": masked_score,
                "result_value": result_value,
            }
        )
    return events


def integer_sparse_attention_events(
    query: Sequence[int],
    key: Sequence[int],
    value: Sequence[int],
    mask: Sequence[int],
    *,
    query_count: int,
    key_count: int,
    feature_count: int,
    value_count: int,
    score_accumulator_dtype: Mapping[str, Any],
    score_reduction_conversion: str,
    scaling: str,
    mask_mode: str,
    normalization: str,
    output_accumulator_dtype: Mapping[str, Any],
    output_reduction_conversion: str,
    result_dtype: Mapping[str, Any],
    result_conversion: str,
) -> list[dict[str, Any]]:
    """Compose QK, scale, mask, normalization, and value stages.

    This restricted profile deliberately selects identity scaling and no
    normalization, but still models those boundaries explicitly.  That keeps the
    end-to-end oracle assembled from stage contracts instead of maintaining a
    second private implementation of Q*K^T.
    """

    qk_events = integer_qk_score_events(
        query,
        key,
        query_count=query_count,
        key_count=key_count,
        feature_count=feature_count,
        score_accumulator_dtype=score_accumulator_dtype,
        score_reduction_conversion=score_reduction_conversion,
        result_dtype=score_accumulator_dtype,
        result_conversion="exact",
    )
    scaled_events = integer_attention_scale_events(qk_events, scaling=scaling)
    masked_events = integer_attention_mask_events(
        scaled_events,
        mask,
        query_count=query_count,
        key_count=key_count,
        mask_mode=mask_mode,
    )
    normalized_events = integer_attention_normalization_events(
        masked_events,
        normalization=normalization,
    )
    return integer_attention_value_events(
        normalized_events,
        value,
        query_count=query_count,
        key_count=key_count,
        value_count=value_count,
        output_accumulator_dtype=output_accumulator_dtype,
        output_reduction_conversion=output_reduction_conversion,
        result_dtype=result_dtype,
        result_conversion=result_conversion,
    )


def integer_attention_scale_events(
    qk_events: Sequence[Mapping[str, Any]], *, scaling: str
) -> list[dict[str, Any]]:
    """Apply the declared score scaling stage to canonical QK events."""

    if scaling != "none":
        raise CanonicalOperationError(
            f"Unsupported sparse-attention scaling {scaling!r}"
        )
    return [
        {
            **dict(event),
            "qk_score": int(event["result_value"]),
            "scale_mode": "none",
            "scaled_score": int(event["result_value"]),
        }
        for event in qk_events
    ]


def integer_attention_mask_events(
    scaled_events: Sequence[Mapping[str, Any]],
    mask: Sequence[int],
    *,
    query_count: int,
    key_count: int,
    mask_mode: str,
) -> list[dict[str, Any]]:
    """Apply one explicit attention-mask stage to scaled score events."""

    if mask_mode != "binary_keep":
        raise CanonicalOperationError(
            f"Unsupported sparse-attention mask mode {mask_mode!r}"
        )
    if len(mask) != query_count * key_count or any(item not in {0, 1} for item in mask):
        raise CanonicalOperationError(
            "binary_keep attention mask accepts only 0 and 1"
        )
    result: list[dict[str, Any]] = []
    for event in scaled_events:
        query_index, key_index = map(int, event["coordinate"])
        active = bool(mask[query_index * key_count + key_index])
        result.append(
            {
                **dict(event),
                "active": active,
                "mask_mode": "binary_keep",
                "masked_score": int(event["scaled_score"]) if active else 0,
            }
        )
    return result


def integer_attention_normalization_events(
    masked_events: Sequence[Mapping[str, Any]], *, normalization: str
) -> list[dict[str, Any]]:
    """Apply the declared normalization boundary to masked scores."""

    if normalization != "none":
        raise CanonicalOperationError(
            f"Unsupported sparse-attention normalization {normalization!r}"
        )
    return [
        {
            **dict(event),
            "normalization_mode": "none",
            "normalized_weight": int(event["masked_score"]),
        }
        for event in masked_events
    ]


def integer_attention_value_events(
    normalized_events: Sequence[Mapping[str, Any]],
    value: Sequence[int],
    *,
    query_count: int,
    key_count: int,
    value_count: int,
    output_accumulator_dtype: Mapping[str, Any],
    output_reduction_conversion: str,
    result_dtype: Mapping[str, Any],
    result_conversion: str,
) -> list[dict[str, Any]]:
    """Reduce normalized attention weights against V in row-major order."""

    rows: list[list[dict[str, Any]]] = [[] for _ in range(query_count)]
    for event in normalized_events:
        query_index, key_index = map(int, event["coordinate"])
        rows[query_index].append({**dict(event), "key_index": key_index})
    if any(len(row) != key_count for row in rows):
        raise CanonicalOperationError("attention stage composition lost a QK coordinate")
    for row in rows:
        row.sort(key=lambda item: int(item["key_index"]))

    events: list[dict[str, Any]] = []
    for query_index, row in enumerate(rows):
        active_count = sum(int(item["active"]) for item in row)
        for value_index in range(value_count):
            weighted_terms = [
                int(item["normalized_weight"])
                * value[int(item["key_index"]) * value_count + value_index]
                for item in row
            ]
            output_value, mathematical, converted = _reduction_trace(
                weighted_terms,
                output_accumulator_dtype,
                output_reduction_conversion,
            )
            result_value = output_value
            if result_conversion == "wrap_twos_complement":
                result_value = _wrap(result_value, result_dtype)
            elif result_conversion != "exact":
                raise CanonicalOperationError(
                    f"Unsupported sparse-attention result conversion {result_conversion!r}"
                )
            scores = [
                {
                    **dict(item),
                    "score": int(item["qk_score"]),
                }
                for item in row
            ]
            events.append(
                {
                    "coordinate": [query_index, value_index],
                    "active_key_count": active_count,
                    "scores": scores,
                    "weighted_terms": weighted_terms,
                    "mathematical_output_prefixes": list(mathematical),
                    "converted_output_prefixes": list(converted),
                    "result_value": result_value,
                    "stage_trace": {
                        "qk_score": [
                            {
                                "coordinate": list(item["coordinate"]),
                                "product_terms": list(item["product_terms"]),
                                "result_value": int(item["qk_score"]),
                            }
                            for item in row
                        ],
                        "scale": [int(item["scaled_score"]) for item in row],
                        "mask": [int(item["masked_score"]) for item in row],
                        "normalization": [
                            int(item["normalized_weight"]) for item in row
                        ],
                        "value_reduction": {
                            "weighted_terms": list(weighted_terms),
                            "result_value": result_value,
                        },
                    },
                }
            )
    return events


def _classify_integer_qk_score(
    job: CanonicalOperationJob,
) -> dict[str, list[Any]]:
    metadata = job.metadata
    query_binding = _binding_by_role(metadata, "query_matrix")
    key_binding = _binding_by_role(metadata, "key_matrix")
    score_binding = _binding_by_role(metadata, "attention_score_matrix")
    qd, kd, sd = [
        list(item["dimensions"])
        for item in (query_binding, key_binding, score_binding)
    ]
    if (
        len(qd) != 2
        or len(kd) != 2
        or qd[1] != kd[1]
        or sd != [qd[0], kd[0]]
    ):
        raise CanonicalOperationError("integer_qk_score metadata shape is inconsistent")
    arithmetic = metadata.get("arithmetic", {})
    accumulator_dtype = _dtype(
        metadata, str(arithmetic["score_accumulator_data_type"])
    )
    events = integer_qk_score_events(
        job.inputs[str(query_binding["data_object"])],
        job.inputs[str(key_binding["data_object"])],
        query_count=job.dimensions[qd[0]],
        key_count=job.dimensions[kd[0]],
        feature_count=job.dimensions[qd[1]],
        score_accumulator_dtype=accumulator_dtype,
        score_reduction_conversion=str(arithmetic["score_reduction_conversion"]),
        result_dtype=score_binding["data_type"],
        result_conversion=str(
            arithmetic.get("result_data_type", {}).get("conversion", "exact")
        ),
    )
    low, high = _integer_bounds(accumulator_dtype)
    accumulation: list[str] = []
    for event in events:
        mathematical = event["mathematical_reduction_prefixes"]
        classes: list[str] = []
        if any(item == high for item in mathematical):
            classes.append("positive_boundary")
        if any(item == low for item in mathematical):
            classes.append("negative_boundary")
        if any(item > high for item in mathematical):
            classes.append("positive_overflow")
        if any(item < low for item in mathematical):
            classes.append("negative_overflow")
        accumulation.extend(classes or ["ordinary"])
    return {
        "dimensions": ["fixed"],
        "operand_values": [
            *job.inputs[str(query_binding["data_object"])],
            *job.inputs[str(key_binding["data_object"])],
        ],
        "accumulation": accumulation,
        "attention_scores": [
            "negative_score"
            if int(event["result_value"]) < 0
            else "zero_score"
            if int(event["result_value"]) == 0
            else "positive_score"
            for event in events
        ],
        "numeric_stage_events": events,
    }


def _classify_fixed_point_attention_scale(
    job: CanonicalOperationJob,
) -> dict[str, list[Any]]:
    metadata = job.metadata
    score_binding = _binding_by_role(metadata, "attention_score_matrix")
    result_binding = _binding_by_role(metadata, "scaled_attention_score_matrix")
    score_dimensions = list(score_binding["dimensions"])
    if (
        len(score_dimensions) != 2
        or list(result_binding["dimensions"]) != score_dimensions
    ):
        raise CanonicalOperationError(
            "fixed_point_attention_scale metadata shape is inconsistent"
        )
    arithmetic = metadata.get("arithmetic", {})
    events = fixed_point_attention_scale_events(
        job.inputs[str(score_binding["data_object"])],
        query_count=job.dimensions[score_dimensions[0]],
        key_count=job.dimensions[score_dimensions[1]],
        scale_multiplier=int(arithmetic["scale_multiplier"]),
        scale_shift=int(arithmetic["scale_shift"]),
        rounding=str(arithmetic["rounding"]),
        result_dtype=result_binding["data_type"],
        result_conversion=str(
            arithmetic.get("result_data_type", {}).get("conversion", "exact")
        ),
    )
    attenuation: list[str] = []
    for event in events:
        score = int(event["score"])
        result = int(event["result_value"])
        if score == 0 and result == 0:
            attenuation.append("zero_preserved")
        if score != 0 and abs(result) < abs(score):
            attenuation.append("magnitude_reduced")
    return {
        "dimensions": ["fixed"],
        "score_values": [int(event["score"]) for event in events],
        "rounding": [str(event["rounding_class"]) for event in events],
        "scaled_values": [
            "negative_scaled"
            if int(event["result_value"]) < 0
            else "zero_scaled"
            if int(event["result_value"]) == 0
            else "positive_scaled"
            for event in events
        ],
        "attenuation": attenuation,
        "numeric_stage_events": events,
    }


def _classify_binary_attention_mask(
    job: CanonicalOperationJob,
) -> dict[str, list[Any]]:
    metadata = job.metadata
    score_binding = _binding_by_role(metadata, "scaled_attention_score_matrix")
    mask_binding = _binding_by_role(metadata, "attention_mask")
    result_binding = _binding_by_role(metadata, "masked_attention_score_matrix")
    dimensions = list(score_binding["dimensions"])
    if (
        len(dimensions) != 2
        or list(mask_binding["dimensions"]) != dimensions
        or list(result_binding["dimensions"]) != dimensions
    ):
        raise CanonicalOperationError(
            "binary_attention_mask metadata shape is inconsistent"
        )
    query_count = job.dimensions[dimensions[0]]
    key_count = job.dimensions[dimensions[1]]
    arithmetic = metadata.get("arithmetic", {})
    events = binary_attention_mask_events(
        job.inputs[str(score_binding["data_object"])],
        job.inputs[str(mask_binding["data_object"])],
        query_count=query_count,
        key_count=key_count,
        mask_mode=str(arithmetic["mask_mode"]),
        result_dtype=result_binding["data_type"],
        result_conversion=str(
            arithmetic.get("result_data_type", {}).get("conversion", "exact")
        ),
    )
    mask_values = job.inputs[str(mask_binding["data_object"])]
    patterns: list[str] = []
    for row in range(query_count):
        active = sum(mask_values[row * key_count : (row + 1) * key_count])
        patterns.append(
            "empty_row"
            if active == 0
            else "singleton_row"
            if active == 1
            else "dense_row"
            if active == key_count
            else "partial_row"
        )
    effects: list[str] = []
    if any(
        event["active"]
        and int(event["result_value"]) == int(event["scaled_score"])
        for event in events
    ):
        effects.append("active_score_preserved")
    if any(
        not event["active"]
        and int(event["scaled_score"]) != 0
        and int(event["result_value"]) == 0
        for event in events
    ):
        effects.append("inactive_nonzero_zeroed")
    return {
        "dimensions": ["fixed"],
        "score_values": [int(event["scaled_score"]) for event in events],
        "mask_values": [
            "keep" if int(event["mask_value"]) == 1 else "drop"
            for event in events
        ],
        "sparsity_patterns": patterns,
        "masked_values": [
            "negative_masked"
            if int(event["result_value"]) < 0
            else "zero_masked"
            if int(event["result_value"]) == 0
            else "positive_masked"
            for event in events
        ],
        "mask_effects": effects,
        "numeric_stage_events": events,
    }


def _classify_integer_sparse_attention(
    job: CanonicalOperationJob,
) -> dict[str, list[Any]]:
    metadata = job.metadata
    query_binding = _binding_by_role(metadata, "query_matrix")
    key_binding = _binding_by_role(metadata, "key_matrix")
    value_binding = _binding_by_role(metadata, "value_matrix")
    mask_binding = _binding_by_role(metadata, "attention_mask")
    output_binding = _binding_by_role(metadata, "attention_result")
    qd, kd, vd, md, od = [
        list(item["dimensions"])
        for item in (
            query_binding,
            key_binding,
            value_binding,
            mask_binding,
            output_binding,
        )
    ]
    if (
        len(qd) != 2
        or len(kd) != 2
        or len(vd) != 2
        or md != [qd[0], kd[0]]
        or od != [qd[0], vd[1]]
        or qd[1] != kd[1]
        or kd[0] != vd[0]
    ):
        raise CanonicalOperationError(
            "integer_sparse_attention metadata shape is inconsistent"
        )
    query_count = job.dimensions[qd[0]]
    key_count = job.dimensions[kd[0]]
    feature_count = job.dimensions[qd[1]]
    value_count = job.dimensions[vd[1]]
    arithmetic = metadata.get("arithmetic", {})
    events = integer_sparse_attention_events(
        job.inputs[str(query_binding["data_object"])],
        job.inputs[str(key_binding["data_object"])],
        job.inputs[str(value_binding["data_object"])],
        job.inputs[str(mask_binding["data_object"])],
        query_count=query_count,
        key_count=key_count,
        feature_count=feature_count,
        value_count=value_count,
        score_accumulator_dtype=_dtype(
            metadata, str(arithmetic["score_accumulator_data_type"])
        ),
        score_reduction_conversion=str(arithmetic["score_reduction_conversion"]),
        scaling=str(arithmetic["scaling"]),
        mask_mode=str(arithmetic["mask_mode"]),
        normalization=str(arithmetic["normalization"]),
        output_accumulator_dtype=_dtype(
            metadata, str(arithmetic["output_accumulator_data_type"])
        ),
        output_reduction_conversion=str(arithmetic["output_reduction_conversion"]),
        result_dtype=output_binding["data_type"],
        result_conversion=str(
            arithmetic.get("result_data_type", {}).get("conversion", "exact")
        ),
    )
    mask_values = job.inputs[str(mask_binding["data_object"])]
    patterns: list[str] = []
    for row in range(query_count):
        active = sum(mask_values[row * key_count : (row + 1) * key_count])
        patterns.append(
            "empty_row"
            if active == 0
            else "singleton_row"
            if active == 1
            else "dense_row"
            if active == key_count
            else "partial_row"
        )
    active_scores: list[int] = []
    seen_query_rows: set[int] = set()
    for event in events:
        row = int(event["coordinate"][0])
        if row in seen_query_rows:
            continue
        seen_query_rows.add(row)
        active_scores.extend(
            int(item["score"]) for item in event["scores"] if item["active"]
        )
    score_classes = [
        "negative_score" if item < 0 else "zero_score" if item == 0 else "positive_score"
        for item in active_scores
    ]
    output_classes = [
        "negative_output"
        if int(event["result_value"]) < 0
        else "zero_output"
        if int(event["result_value"]) == 0
        else "positive_output"
        for event in events
    ]
    score_events = [
        item
        for event in events
        for item in event["scores"]
    ]
    stage_handoffs: list[str] = []
    if score_events and all(
        int(item["scaled_score"]) == int(item["qk_score"])
        for item in score_events
    ):
        stage_handoffs.append("qk_to_scale_forwarded")
    if any(
        item["active"]
        and int(item["masked_score"]) == int(item["scaled_score"])
        for item in score_events
    ):
        stage_handoffs.append("active_mask_preserved")
    if any(
        not item["active"]
        and int(item["scaled_score"]) != 0
        and int(item["masked_score"]) == 0
        for item in score_events
    ):
        stage_handoffs.append("inactive_mask_zeroed")
    if score_events and all(
        int(item["normalized_weight"]) == int(item["masked_score"])
        for item in score_events
    ):
        stage_handoffs.append("normalization_bypass_forwarded")
    if any(
        int(term) != 0
        for event in events
        for term in event["weighted_terms"]
    ):
        stage_handoffs.append("value_reduction_consumed")
    return {
        "dimensions": ["fixed"],
        "operand_values": [
            *job.inputs[str(query_binding["data_object"])],
            *job.inputs[str(key_binding["data_object"])],
            *job.inputs[str(value_binding["data_object"])],
        ],
        "sparsity_patterns": patterns,
        "attention_scores": score_classes,
        "stage_handoffs": stage_handoffs,
        "output_values": output_classes,
        "numeric_stage_events": events,
    }


def classify_operation_job(job: CanonicalOperationJob) -> dict[str, list[Any]]:
    profile = job.metadata.get("arithmetic", {}).get("classifier_profile")
    if profile == "integer_matrix_multiply":
        return _classify_integer_matrix_multiply(job)
    if profile == "integer_qk_score":
        return _classify_integer_qk_score(job)
    if profile == "fixed_point_attention_scale":
        return _classify_fixed_point_attention_scale(job)
    if profile == "binary_attention_mask":
        return _classify_binary_attention_mask(job)
    if profile == "integer_sparse_attention":
        return _classify_integer_sparse_attention(job)
    return {}


def classify_checked_operations(
    metadata: Mapping[str, Any],
    operations: Sequence[str],
    stimulus: Mapping[str, Any],
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, dict[str, list[Any]]]:
    """Assemble and classify every complete known operation in one checked job."""

    by_name = {
        str(item.get("operation_name")): item
        for item in metadata.get("operations", [])
        if isinstance(item, Mapping)
    }
    result: dict[str, dict[str, list[Any]]] = {}
    for name in map(str, operations):
        operation_metadata = by_name.get(name)
        if operation_metadata is None:
            continue
        job = assemble_canonical_job(operation_metadata, stimulus, expected, observed)
        if job is not None:
            result[name] = classify_operation_job(job)
    return result


def canonical_bins_for_concept(
    operation_metadata: Mapping[str, Any], concept: str
) -> list[dict[str, Any]] | None:
    """Return code-owned semantic bins for supported operation concepts."""

    def bin_(name: str, value: Any) -> dict[str, Any]:
        return {
            "name": name,
            "intent": f"Observe canonical {concept} class {name} from a checked job.",
            "predicate": {"op": "eq", "args": [value]},
        }

    def unique(bins: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Avoid duplicate semantic bins for degenerate integer domains."""

        result: list[dict[str, Any]] = []
        predicates: set[str] = set()
        for item in bins:
            key = repr(item.get("predicate"))
            if key not in predicates:
                result.append(item)
                predicates.add(key)
        return result

    profile = operation_metadata.get("arithmetic", {}).get("classifier_profile")
    if profile == "binary_attention_mask":
        if concept == "dimensions":
            return [bin_("fixed_shape", "fixed")]
        if concept == "score_values":
            score_types = [
                item["data_type"]
                for item in operation_metadata.get("inputs", [])
                if item.get("object_role") == "scaled_attention_score_matrix"
            ]
            if len(score_types) != 1:
                return None
            low, high = _integer_bounds(score_types[0])
            bins = [bin_("zero", 0)]
            if high >= 1:
                bins.append(
                    {
                        "name": "positive",
                        "intent": "Observe a positive scaled attention score.",
                        "predicate": {"op": "between", "args": [1, high]},
                    }
                )
            if low < 0:
                bins.append(
                    {
                        "name": "negative",
                        "intent": "Observe a negative scaled attention score.",
                        "predicate": {"op": "between", "args": [low, -1]},
                    }
                )
            bins.extend([bin_("minimum", low), bin_("maximum", high)])
            return unique(bins)
        if concept == "mask_values":
            return [bin_("drop", "drop"), bin_("keep", "keep")]
        if concept == "sparsity_patterns":
            return [
                bin_(name, name)
                for name in (
                    "empty_row",
                    "singleton_row",
                    "partial_row",
                    "dense_row",
                )
            ]
        if concept == "masked_values":
            return [
                bin_(name, name)
                for name in ("zero_masked", "positive_masked", "negative_masked")
            ]
        if concept == "mask_effects":
            return [
                bin_(name, name)
                for name in ("active_score_preserved", "inactive_nonzero_zeroed")
            ]
        return None
    if profile == "fixed_point_attention_scale":
        if concept == "dimensions":
            return [bin_("fixed_shape", "fixed")]
        if concept == "score_values":
            score_types = [
                item["data_type"]
                for item in operation_metadata.get("inputs", [])
                if item.get("object_role") == "attention_score_matrix"
            ]
            if len(score_types) != 1:
                return None
            low, high = _integer_bounds(score_types[0])
            bins = [bin_("zero", 0)]
            if high >= 1:
                bins.append(
                    {
                        "name": "positive",
                        "intent": "Observe a positive unscaled attention score.",
                        "predicate": {"op": "between", "args": [1, high]},
                    }
                )
            if low < 0:
                bins.append(
                    {
                        "name": "negative",
                        "intent": "Observe a negative unscaled attention score.",
                        "predicate": {"op": "between", "args": [low, -1]},
                    }
                )
            bins.extend([bin_("minimum", low), bin_("maximum", high)])
            return unique(bins)
        if concept == "rounding":
            return [
                bin_(name, name)
                for name in (
                    "exact",
                    "positive_fraction_discarded",
                    "negative_fraction_discarded",
                )
            ]
        if concept == "scaled_values":
            return [
                bin_(name, name)
                for name in ("zero_scaled", "positive_scaled", "negative_scaled")
            ]
        if concept == "attenuation":
            return [
                bin_(name, name)
                for name in ("zero_preserved", "magnitude_reduced")
            ]
        return None
    if profile == "integer_qk_score":
        if concept == "dimensions":
            return [bin_("fixed_shape", "fixed")]
        if concept == "operand_values":
            operand_types = [
                item["data_type"]
                for item in operation_metadata.get("inputs", [])
                if item.get("object_role") in {"query_matrix", "key_matrix"}
            ]
            if not operand_types:
                return None
            low = min(_integer_bounds(item)[0] for item in operand_types)
            high = max(_integer_bounds(item)[1] for item in operand_types)
            bins = [bin_("zero", 0)]
            if high >= 1:
                bins.append(
                    {
                        "name": "positive",
                        "intent": "Observe a positive Q or K operand.",
                        "predicate": {"op": "between", "args": [1, high]},
                    }
                )
            if low < 0:
                bins.append(
                    {
                        "name": "negative",
                        "intent": "Observe a negative Q or K operand.",
                        "predicate": {"op": "between", "args": [low, -1]},
                    }
                )
            bins.extend([bin_("minimum", low), bin_("maximum", high)])
            return unique(bins)
        if concept == "accumulation":
            return [
                bin_(name, name)
                for name in (
                    "ordinary",
                    "positive_boundary",
                    "negative_boundary",
                    "positive_overflow",
                    "negative_overflow",
                )
            ]
        if concept == "attention_scores":
            return [
                bin_(name, name)
                for name in ("zero_score", "positive_score", "negative_score")
            ]
        return None
    if profile == "integer_sparse_attention":
        if concept == "dimensions":
            return [bin_("fixed_shape", "fixed")]
        if concept == "operand_values":
            operand_types = [
                item["data_type"]
                for item in operation_metadata.get("inputs", [])
                if item.get("object_role")
                in {"query_matrix", "key_matrix", "value_matrix"}
            ]
            if not operand_types:
                return None
            low = min(_integer_bounds(item)[0] for item in operand_types)
            high = max(_integer_bounds(item)[1] for item in operand_types)
            bins = [bin_("zero", 0)]
            if high >= 1:
                bins.append(
                    {
                        "name": "positive",
                        "intent": "Observe a positive Q, K, or V operand.",
                        "predicate": {"op": "between", "args": [1, high]},
                    }
                )
            if low < 0:
                bins.append(
                    {
                        "name": "negative",
                        "intent": "Observe a negative Q, K, or V operand.",
                        "predicate": {"op": "between", "args": [low, -1]},
                    }
                )
            bins.extend([bin_("minimum", low), bin_("maximum", high)])
            return unique(bins)
        if concept == "sparsity_patterns":
            return [
                bin_(name, name)
                for name in (
                    "empty_row",
                    "singleton_row",
                    "partial_row",
                    "dense_row",
                )
            ]
        if concept == "attention_scores":
            return [
                bin_(name, name)
                for name in ("zero_score", "positive_score", "negative_score")
            ]
        if concept == "stage_handoffs":
            return [
                bin_(name, name)
                for name in (
                    "qk_to_scale_forwarded",
                    "active_mask_preserved",
                    "inactive_mask_zeroed",
                    "normalization_bypass_forwarded",
                    "value_reduction_consumed",
                )
            ]
        if concept == "output_values":
            return [
                bin_(name, name)
                for name in ("zero_output", "positive_output", "negative_output")
            ]
        return None
    if profile != "integer_matrix_multiply":
        return None
    if concept == "dimensions":
        return [bin_("fixed_shape", "fixed")]
    if concept == "operand_values":
        operand_types = [
            item["data_type"] for item in operation_metadata.get("inputs", [])
            if item.get("object_role") in {"left_operand_matrix", "right_operand_matrix"}
        ]
        if not operand_types:
            return None
        low = min(_integer_bounds(item)[0] for item in operand_types)
        high = max(_integer_bounds(item)[1] for item in operand_types)
        bins = [bin_("zero", 0)]
        if high >= 1:
            bins.append({"name": "positive", "intent": "Observe a positive operand.", "predicate": {"op": "between", "args": [1, high]}})
        if low < 0:
            bins.append({"name": "negative", "intent": "Observe a negative operand.", "predicate": {"op": "between", "args": [low, -1]}})
        bins.extend([bin_("minimum", low), bin_("maximum", high)])
        return unique(bins)
    if concept == "accumulation":
        return [
            bin_(name, name)
            for name in (
                "ordinary",
                "positive_boundary",
                "negative_boundary",
                "positive_overflow",
                "negative_overflow",
            )
        ]
    if concept == "bias":
        post_operations = operation_metadata.get("arithmetic", {}).get(
            "post_operations", {}
        ).values()
        bias_names = {
            str(item.get("data_object"))
            for item in post_operations
            if item.get("kind") == "bias_add"
        }
        bindings = [
            item for item in operation_metadata.get("inputs", [])
            if str(item.get("data_object")) in bias_names
        ]
        if len(bindings) != 1:
            return None
        dtype = bindings[0]["data_type"]
        low, high = _integer_bounds(dtype)
        return unique([
            bin_("zero_bias", 0),
            *([{"name": "positive_bias", "intent": "Observe positive bias.", "predicate": {"op": "between", "args": [1, high]}}] if high >= 1 else []),
            *([{"name": "negative_bias", "intent": "Observe negative bias.", "predicate": {"op": "between", "args": [low, -1]}}] if low < 0 else []),
            bin_("minimum_bias", low),
            bin_("maximum_bias", high),
        ])
    if concept == "activation":
        return [bin_(name + "_region", name) for name in ("negative", "zero", "positive")]
    if concept == "quantization":
        stages = [
            stage
            for stage in operation_metadata.get("arithmetic", {})
            .get("post_operations", {})
            .values()
            if stage.get("kind") == "affine_quantize"
        ]
        if len(stages) != 1:
            return None
        stage = stages[0]
        denominator = 1 << int(stage["scale_shift"])
        bins = [bin_("exact", "exact")]
        if int(stage["scale_multiplier"]) % denominator != 0:
            bins.append(bin_("rounded", "rounded"))
        if int(stage["zero_point"]) != 0:
            bins.append(bin_("nonzero_zero_point", "nonzero_zero_point"))
        bins.extend(
            [
                bin_("negative_saturation", "negative_saturation"),
                bin_("positive_saturation", "positive_saturation"),
            ]
        )
        return bins
    return None
