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
    accumulator = metadata.get("arithmetic", {}).get("accumulator_type", {})
    if accumulator.get("name") == name:
        return accumulator
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
                    # kind for, expressed in formula.py's closed grammar --
                    # see its module docstring for why this, rather than a
                    # blanket llm_extension fallback, is what keeps every
                    # concept that never looks past this stage (accumulation,
                    # dimensions, operand_values, and bias/activation if they
                    # sit earlier in the chain) fully code-owned.
                    value = evaluate_formula(str(stage["formula"]), value)
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
    return result


def classify_operation_job(job: CanonicalOperationJob) -> dict[str, list[Any]]:
    profile = job.metadata.get("arithmetic", {}).get("classifier_profile")
    if profile == "integer_matrix_multiply":
        return _classify_integer_matrix_multiply(job)
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
    """Return code-owned reachable semantic bins for supported GEMM concepts."""

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

    if operation_metadata.get("arithmetic", {}).get("classifier_profile") != "integer_matrix_multiply":
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
