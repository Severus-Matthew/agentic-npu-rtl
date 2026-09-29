"""Tool-owned Architect arithmetic schema, reference checks, and compilation.

Architect declares semantics; this module resolves named types/objects without
guessing activation, accumulator type, conversion points, or stage order.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
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
    if declaration["classifier_profile"] == "llm_extension":
        if not str(operation.get("semantics", "")).strip():
            raise ArithmeticMetadataError("llm_extension requires explicit operations[].semantics")
        return {
            **deepcopy(dict(declaration)),
            "semantics": operation["semantics"],
            "accumulator_data_type": None, "reduction_dimensions": [], "post_operations": [],
            "metadata_origin": "explicit_contract", "support_status": "llm_extension_required",
        }
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
    if profile == "llm_extension":
        for field in ("reason", "semantics"):
            if not isinstance(arithmetic.get(field), str) or not arithmetic[field].strip():
                raise ArithmeticMetadataError(f"llm_extension requires explicit {field}")
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
