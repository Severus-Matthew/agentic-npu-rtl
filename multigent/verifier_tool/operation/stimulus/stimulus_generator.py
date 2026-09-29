"""Code-owned canonical stimulus generation for known operation families.

The generator works in canonical data-object space.  It deliberately does not
drive DUT signals: protocol serialization remains a separate adapter concern.
Every directed vector is evaluated by the code-owned golden model and then fed
back through the existing classifier before it is returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import prod
from random import Random
from typing import Any, Mapping, Sequence

import z3

from ...pool.operation_metadata.canonical import (
    CanonicalOperationError,
    _binding_by_role,
    _dtype,
    _integer_bounds,
    assemble_canonical_job,
    canonical_bins_for_concept,
    classify_operation_job,
    integer_matrix_multiply_events,
    supported_code_owned_concepts,
)
from ...pool.operation_metadata.formula import (
    FormulaError,
    compile_formula,
    compile_formula_expression,
)


_ERROR_CODES = {
    "unreachable",
    "metadata_missing",
    "unsupported_known_feature",
    "generation_inconclusive",
    "llm_extension_required",
}
_MAX_CANONICAL_ELEMENTS_PER_CASE = 1_000_000


class CanonicalStimulusGenerationError(ValueError):
    """A target bin cannot be generated safely from canonical metadata."""

    def __init__(
        self,
        code: str,
        reason: str,
        *,
        operation_name: str = "",
        concept: str = "",
        bin_name: str = "",
    ) -> None:
        if code not in _ERROR_CODES:
            raise ValueError(f"Unknown canonical stimulus error code {code!r}")
        self.code = code
        self.reason = reason
        self.operation_name = operation_name
        self.concept = concept
        self.bin_name = bin_name
        super().__init__(
            f"{code}: operation={operation_name!r} concept={concept!r} "
            f"bin={bin_name!r}: {reason}"
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "operation_name": self.operation_name,
            "concept": self.concept,
            "bin_name": self.bin_name,
            "code": self.code,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class _GemmModel:
    operation: Mapping[str, Any]
    operation_name: str
    dimensions: Mapping[str, int]
    left: Mapping[str, Any]
    right: Mapping[str, Any]
    result: Mapping[str, Any]
    bias: Mapping[str, Any] | None
    accumulator_dtype: Mapping[str, Any]
    post_operations: Mapping[str, Mapping[str, Any]]
    resolved_stage_order: tuple[str, ...]
    m: int
    n: int
    k: int


def _generation_error(
    model_or_operation: _GemmModel | Mapping[str, Any],
    code: str,
    reason: str,
    *,
    concept: str = "",
    bin_name: str = "",
) -> CanonicalStimulusGenerationError:
    operation = (
        model_or_operation.operation
        if isinstance(model_or_operation, _GemmModel)
        else model_or_operation
    )
    return CanonicalStimulusGenerationError(
        code,
        reason,
        operation_name=str(operation.get("operation_name", "")),
        concept=concept,
        bin_name=bin_name,
    )


def _select_operation(
    metadata: Mapping[str, Any], operation_name: str | None
) -> Mapping[str, Any]:
    if "operations" not in metadata:
        if operation_name not in {None, str(metadata.get("operation_name", ""))}:
            raise _generation_error(
                metadata,
                "metadata_missing",
                f"operation {operation_name!r} is not present",
            )
        return metadata
    operations = [
        item for item in metadata.get("operations", []) if isinstance(item, Mapping)
    ]
    if operation_name is None:
        if len(operations) != 1:
            raise CanonicalStimulusGenerationError(
                "metadata_missing",
                "operation_name is required when metadata contains zero or multiple operations",
            )
        return operations[0]
    matches = [
        item for item in operations if str(item.get("operation_name", "")) == operation_name
    ]
    if len(matches) != 1:
        raise CanonicalStimulusGenerationError(
            "metadata_missing",
            f"expected one operation named {operation_name!r}, found {len(matches)}",
            operation_name=operation_name,
        )
    return matches[0]


def _shape(binding: Mapping[str, Any], dimensions: Mapping[str, int]) -> tuple[int, ...]:
    names = list(map(str, binding.get("dimensions", [])))
    missing = [name for name in names if not isinstance(dimensions.get(name), int)]
    if missing:
        raise ValueError(f"unresolved dimensions {missing}")
    shape = tuple(int(dimensions[name]) for name in names)
    if any(size <= 0 for size in shape):
        raise ValueError(f"dimensions must be positive, got {shape}")
    return shape


def _gemm_model(operation: Mapping[str, Any]) -> _GemmModel:
    profile = operation.get("arithmetic", {}).get("classifier_profile")
    if profile != "integer_matrix_multiply":
        raise _generation_error(
            operation,
            "llm_extension_required",
            f"classifier profile {profile!r} has no code-owned stimulus generator",
        )
    try:
        left = _binding_by_role(operation, "left_operand_matrix")
        right = _binding_by_role(operation, "right_operand_matrix")
        result = _binding_by_role(operation, "result_matrix")
        dimensions = {
            str(name): int(value)
            for name, value in operation.get("dimensions", {}).items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        left_shape = _shape(left, dimensions)
        right_shape = _shape(right, dimensions)
        result_shape = _shape(result, dimensions)
        accumulator_dtype = _dtype(
            operation,
            str(operation.get("arithmetic", {}).get("accumulator_data_type", "")),
        )
    except (CanonicalOperationError, KeyError, TypeError, ValueError) as exc:
        raise _generation_error(
            operation, "metadata_missing", f"incomplete GEMM metadata: {exc}"
        ) from exc
    if len(left_shape) != 2 or len(right_shape) != 2 or len(result_shape) != 2:
        raise _generation_error(
            operation,
            "unsupported_known_feature",
            "the code-owned generator currently supports rank-2 GEMM only",
        )
    m, k = left_shape
    if right_shape[0] != k:
        raise _generation_error(
            operation, "metadata_missing", "GEMM reduction dimensions do not match"
        )
    n = right_shape[1]
    if result_shape != (m, n):
        raise _generation_error(
            operation, "metadata_missing", "GEMM result shape does not match A x B"
        )
    if sum(map(prod, (left_shape, right_shape, result_shape))) > _MAX_CANONICAL_ELEMENTS_PER_CASE:
        raise _generation_error(
            operation,
            "unsupported_known_feature",
            "canonical tensor size exceeds the bounded in-memory generator limit",
        )

    post_operations = dict(operation.get("arithmetic", {}).get("post_operations", {}))
    resolved_stage_order = tuple(operation.get("arithmetic", {}).get("resolved_stage_order", ()))
    if set(resolved_stage_order) != set(post_operations):
        raise _generation_error(
            operation,
            "metadata_missing",
            "resolved_stage_order does not match the declared post_operations stages",
        )
    post_kinds = [str(post_operations[name].get("kind", "")) for name in resolved_stage_order]
    unsupported = sorted(
        {
            kind for kind in post_kinds
            if kind
            not in {
                "bias_add",
                "wrap",
                "relu",
                "affine_quantize",
                "llm_defined",
            }
        }
    )
    if unsupported:
        raise _generation_error(
            operation,
            "unsupported_known_feature",
            f"unsupported post operations {unsupported}",
        )
    # llm_defined is exempt from the at-most-once rule: unlike bias_add/wrap/
    # relu/affine_quantize (each singular by construction), a contract may declare several
    # distinct llm_defined stages, disambiguated by stage name and formula.
    fixed_kinds = [kind for kind in post_kinds if kind != "llm_defined"]
    if len(fixed_kinds) != len(set(fixed_kinds)):
        raise _generation_error(
            operation,
            "unsupported_known_feature",
            "post operations must declare each of "
            "bias_add/wrap/relu/affine_quantize at most once",
        )
    for name in resolved_stage_order:
        stage = post_operations[name]
        if stage.get("kind") != "llm_defined":
            continue
        try:
            compile_formula(str(stage.get("formula", "")))
        except FormulaError as exc:
            raise _generation_error(
                operation, "unsupported_known_feature", f"post-operation {name!r}: {exc}"
            ) from exc
    bias_operations = [post_operations[name] for name in resolved_stage_order if post_operations[name].get("kind") == "bias_add"]
    bias: Mapping[str, Any] | None = None
    if bias_operations:
        if len(bias_operations) != 1:
            raise _generation_error(
                operation, "metadata_missing", "GEMM needs at most one bias_add mapping"
            )
        object_name = str(bias_operations[0].get("data_object", ""))
        matches = [
            item for item in operation.get("inputs", [])
            if str(item.get("data_object", "")) == object_name
        ]
        if len(matches) != 1:
            raise _generation_error(
                operation,
                "metadata_missing",
                f"bias_add data object {object_name!r} is not uniquely bound",
            )
        bias = matches[0]
        if _shape(bias, dimensions) != (n,):
            raise _generation_error(
                operation,
                "unsupported_known_feature",
                "the code-owned GEMM generator supports per-output-column bias only",
            )
    try:
        for binding in (left, right, result, *([] if bias is None else [bias])):
            width = int(binding["data_type"]["width_bits"])
            if width <= 0 or not isinstance(binding["data_type"].get("signed"), bool):
                raise ValueError(f"invalid data type on {binding.get('data_object')!r}")
        _integer_bounds(accumulator_dtype)
    except (KeyError, TypeError, ValueError) as exc:
        raise _generation_error(
            operation, "metadata_missing", f"invalid integer data type metadata: {exc}"
        ) from exc
    known_input_names = {
        str(left["data_object"]),
        str(right["data_object"]),
        *([] if bias is None else [str(bias["data_object"])]),
    }
    unknown_inputs = sorted(
        str(item.get("data_object", ""))
        for item in operation.get("inputs", [])
        if str(item.get("data_object", "")) not in known_input_names
    )
    unknown_outputs = sorted(
        str(item.get("data_object", ""))
        for item in operation.get("outputs", [])
        if str(item.get("data_object", "")) != str(result["data_object"])
    )
    if unknown_inputs or unknown_outputs:
        raise _generation_error(
            operation,
            "unsupported_known_feature",
            f"unmodeled operation objects inputs={unknown_inputs}, outputs={unknown_outputs}",
        )
    return _GemmModel(
        operation=operation,
        operation_name=str(operation["operation_name"]),
        dimensions=dimensions,
        left=left,
        right=right,
        result=result,
        bias=bias,
        accumulator_dtype=accumulator_dtype,
        post_operations=post_operations,
        resolved_stage_order=resolved_stage_order,
        m=m,
        n=n,
        k=k,
    )


def _base_stimulus(model: _GemmModel) -> dict[str, list[int]]:
    return {
        str(binding["data_object"]): [0] * prod(_shape(binding, model.dimensions))
        for binding in model.operation.get("inputs", [])
    }


def evaluate_canonical_operation(
    operation_metadata: Mapping[str, Any],
    stimulus: Mapping[str, Any],
    *,
    operation_name: str | None = None,
) -> dict[str, list[int]]:
    """Evaluate the code-owned integer GEMM reference in canonical object order."""

    operation = _select_operation(operation_metadata, operation_name)
    model = _gemm_model(operation)
    try:
        job = assemble_canonical_job(operation, stimulus, {}, {})
    except CanonicalOperationError as exc:
        raise _generation_error(
            model, "metadata_missing", f"stimulus does not form a canonical job: {exc}"
        ) from exc
    if job is None:
        raise _generation_error(model, "metadata_missing", "stimulus contains no operation input")
    a = job.inputs[str(model.left["data_object"])]
    b = job.inputs[str(model.right["data_object"])]
    bias = job.inputs[str(model.bias["data_object"])] if model.bias is not None else ()
    try:
        events = integer_matrix_multiply_events(
            a,
            b,
            bias,
            m=model.m,
            k=model.k,
            n=model.n,
            accumulator_dtype=model.accumulator_dtype,
            reduction_conversion=str(
                operation.get("arithmetic", {}).get("reduction_conversion", "exact")
            ),
            post_operations=model.post_operations,
            resolved_stage_order=model.resolved_stage_order,
            bias_conversion=str(
                operation.get("arithmetic", {}).get("bias_conversion", "exact")
            ),
            result_dtype=model.result["data_type"],
            result_conversion=operation.get("arithmetic", {})
            .get("result_data_type", {})
            .get("conversion", "exact"),
        )
    except CanonicalOperationError as exc:
        raise _generation_error(model, "unsupported_known_feature", str(exc)) from exc
    return {str(model.result["data_object"]): [event["result_value"] for event in events]}


def _predicate_matches(value: Any, predicate: Mapping[str, Any]) -> bool:
    op = predicate.get("op")
    args = list(predicate.get("args", []))
    if op == "eq":
        return value == args[0]
    if op == "neq":
        return value != args[0]
    if op == "lt":
        return value < args[0]
    if op == "lte":
        return value <= args[0]
    if op == "gt":
        return value > args[0]
    if op == "gte":
        return value >= args[0]
    if op == "between":
        return args[0] <= value <= args[1]
    if op == "one_of":
        return value in args
    if op == "mod_eq":
        return value % args[0] == args[1]
    if op == "mod_ne":
        return value % args[0] != args[1]
    if op == "truthy":
        return bool(value)
    if op == "falsy":
        return not bool(value)
    raise ValueError(f"canonical stimulus generator cannot evaluate predicate {op!r}")


def _case(
    model: _GemmModel,
    concept: str,
    bin_name: str,
    stimulus: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    bins = canonical_bins_for_concept(model.operation, concept) or []
    matches = [item for item in bins if item.get("name") == bin_name]
    if len(matches) != 1:
        raise _generation_error(
            model,
            "unsupported_known_feature",
            "target is not a code-owned canonical bin",
            concept=concept,
            bin_name=bin_name,
        )
    concrete = {str(name): list(map(int, values)) for name, values in stimulus.items()}
    expected = evaluate_canonical_operation(model.operation, concrete)
    job = assemble_canonical_job(model.operation, concrete, expected, expected)
    assert job is not None
    evidence = classify_operation_job(job)
    values = evidence.get(concept, [])
    predicate = matches[0].get("predicate", {})
    if not any(_predicate_matches(value, predicate) for value in values):
        raise _generation_error(
            model,
            "generation_inconclusive",
            f"generated vector did not hit target; classifier evidence={values!r}",
            concept=concept,
            bin_name=bin_name,
        )
    return {
        "operation_name": model.operation_name,
        "kind": "directed",
        "label": f"canonical_{concept}_{bin_name}",
        "target": {"concept": concept, "bin": bin_name},
        "stimulus": concrete,
        "expected": expected,
        "evidence": evidence,
    }


def _dot_bounds(model: _GemmModel) -> tuple[int, int]:
    left_bounds = _integer_bounds(model.left["data_type"])
    right_bounds = _integer_bounds(model.right["data_type"])
    products = [
        left * right
        for left in left_bounds
        for right in right_bounds
    ]
    return model.k * min(products), model.k * max(products)


def _reduction_query(
    model: _GemmModel, target: int, *, bias: bool
) -> tuple[list[int], list[int], int | None] | None:
    """General SMT witness search: row 0 of A, column 0 of B[, bias] such
    that their *exact* (unwrapped) product-sum equals `target`.

    Replaces what used to be a GEMM-specific constructive search
    (distribute-a-sum-across-slots, then factor-pair-by-trial-division, then
    a hybrid fallback) with one general bounded-integer query. This stays
    exact-arithmetic-only, matching `_dot_bounds`'s own loose bound and the
    caller's existing contract: `target` is a *pre*-wrap/pre-relu witness
    value, used only to steer the search -- `reduction_conversion` and
    `bias_conversion` are never consulted here, because the boundary/
    overflow bins this feeds (e.g. `positive_overflow == accumulator_high +
    1`) are specifically about the raw value *before* any wrap is applied;
    the actual wrap/relu forward simulation and bin classification both
    happen afterward, in `evaluate_canonical_operation` /
    `classify_operation_job`, which is what really decides whether the
    generated stimulus counts as a witness for the requested bin (see
    `_case`). A future post-op `kind` needs a new rule in `_target_stimulus`
    for *which* pre-image to aim for, never new search code here.
    """

    k = model.k
    a_low, a_high = _integer_bounds(model.left["data_type"])
    b_low, b_high = _integer_bounds(model.right["data_type"])
    if bias and model.bias is None:
        return None

    solver = z3.Solver()
    a_vars = [z3.Int(f"a_{i}") for i in range(k)]
    b_vars = [z3.Int(f"b_{i}") for i in range(k)]
    for var in a_vars:
        solver.add(var >= a_low)
        solver.add(var <= a_high)
    for var in b_vars:
        solver.add(var >= b_low)
        solver.add(var <= b_high)
    reduction_sum = z3.Sum([a_var * b_var for a_var, b_var in zip(a_vars, b_vars)])

    bias_var = None
    if bias:
        bias_low, bias_high = _integer_bounds(model.bias["data_type"])
        bias_var = z3.Int("bias")
        solver.add(bias_var >= bias_low)
        solver.add(bias_var <= bias_high)
        solver.add(reduction_sum + bias_var == target)
    else:
        solver.add(reduction_sum == target)

    if solver.check() != z3.sat:
        return None
    witness = solver.model()

    left = [0] * (model.m * model.k)
    right = [0] * (model.k * model.n)
    for depth in range(k):
        left[depth] = witness.evaluate(a_vars[depth], model_completion=True).as_long()
        right[depth * model.n] = witness.evaluate(b_vars[depth], model_completion=True).as_long()
    bias_value = witness.evaluate(bias_var, model_completion=True).as_long() if bias else None
    return left, right, bias_value


def _z3_wrap(value: z3.ArithRef, dtype: Mapping[str, Any]) -> z3.ArithRef:
    width = int(dtype["width_bits"])
    modulus = 1 << width
    unsigned = value % modulus
    if bool(dtype["signed"]):
        sign = 1 << (width - 1)
        return z3.If(unsigned >= sign, unsigned - modulus, unsigned)
    return unsigned


def _z3_affine_quantize(
    value: z3.ArithRef,
    stage: Mapping[str, Any],
    dtype: Mapping[str, Any],
) -> z3.ArithRef:
    numerator = value * int(stage["scale_multiplier"])
    denominator = 1 << int(stage["scale_shift"])
    magnitude = z3.If(numerator < 0, -numerator, numerator)
    quotient = magnitude / denominator
    remainder = magnitude % denominator
    rounded_magnitude = z3.If(
        2 * remainder < denominator,
        quotient,
        z3.If(
            2 * remainder > denominator,
            quotient + 1,
            z3.If(quotient % 2 == 0, quotient, quotient + 1),
        ),
    )
    rounded = z3.If(numerator < 0, -rounded_magnitude, rounded_magnitude)
    shifted = rounded + int(stage["zero_point"])
    low, high = _integer_bounds(dtype)
    return z3.If(shifted < low, low, z3.If(shifted > high, high, shifted))


def _z3_predicate(value: z3.ArithRef, predicate: Mapping[str, Any]) -> z3.BoolRef:
    op = str(predicate.get("op", ""))
    args = list(predicate.get("args", []))
    if op == "eq" and len(args) == 1:
        return value == args[0]
    if op == "neq" and len(args) == 1:
        return value != args[0]
    if op == "lt" and len(args) == 1:
        return value < args[0]
    if op == "lte" and len(args) == 1:
        return value <= args[0]
    if op == "gt" and len(args) == 1:
        return value > args[0]
    if op == "gte" and len(args) == 1:
        return value >= args[0]
    if op == "between" and len(args) == 2:
        return z3.And(value >= args[0], value <= args[1])
    if op == "one_of" and args:
        return z3.Or(*[value == item for item in args])
    if op == "mod_eq" and len(args) == 2 and int(args[0]) > 0:
        return value % int(args[0]) == int(args[1])
    if op == "mod_ne" and len(args) == 2 and int(args[0]) > 0:
        return value % int(args[0]) != int(args[1])
    if op == "truthy" and not args:
        return value != 0
    if op == "falsy" and not args:
        return value == 0
    raise ValueError(f"unsupported formula-stage coverage predicate {dict(predicate)!r}")


def generate_solver_compiled_stimulus_for_bin(
    operation_metadata: Mapping[str, Any],
    concept: str,
    bin_spec: Mapping[str, Any],
    *,
    operation_name: str | None = None,
) -> dict[str, Any]:
    """Solve one Verifier-defined bin over a formula-stage golden trace.

    The Verifier owns ``bin_spec``.  The tool owns the symbolic GEMM pipeline,
    the compiled formula, canonical tensor construction, forward golden check,
    and final predicate confirmation.
    """

    operation = _select_operation(operation_metadata, operation_name)
    model = _gemm_model(operation)
    stage = model.post_operations.get(str(concept))
    if not isinstance(stage, Mapping) or stage.get("kind") != "llm_defined":
        raise _generation_error(
            model,
            "unsupported_known_feature",
            "target concept must name a solver-compiled formula DAG stage",
            concept=str(concept),
            bin_name=str(bin_spec.get("name", "")),
        )
    predicate = bin_spec.get("predicate")
    if not isinstance(predicate, Mapping):
        raise _generation_error(
            model,
            "metadata_missing",
            "Verifier formula-stage bin needs a declarative predicate",
            concept=str(concept),
            bin_name=str(bin_spec.get("name", "")),
        )

    solver = z3.Solver()
    solver.set(timeout=10_000)
    a_low, a_high = _integer_bounds(model.left["data_type"])
    b_low, b_high = _integer_bounds(model.right["data_type"])
    a_vars = [z3.Int(f"formula_a_{index}") for index in range(model.k)]
    b_vars = [z3.Int(f"formula_b_{index}") for index in range(model.k)]
    for item in a_vars:
        solver.add(item >= a_low, item <= a_high)
    for item in b_vars:
        solver.add(item >= b_low, item <= b_high)

    arithmetic = operation.get("arithmetic", {})
    value: z3.ArithRef = z3.IntVal(
        int(arithmetic.get("accumulator_initialization", 0))
    )
    reduction_conversion = str(arithmetic.get("reduction_conversion", "exact"))
    for left, right in zip(a_vars, b_vars):
        value = value + left * right
        if reduction_conversion == "wrap_twos_complement_after_each_add":
            value = _z3_wrap(value, model.accumulator_dtype)
        elif reduction_conversion != "exact":
            raise _generation_error(
                model,
                "unsupported_known_feature",
                f"cannot symbolically compile reduction conversion {reduction_conversion!r}",
                concept=str(concept),
                bin_name=str(bin_spec.get("name", "")),
            )

    bias_var: z3.ArithRef | None = None
    target_value: z3.ArithRef | None = None
    for stage_name in model.resolved_stage_order:
        current = model.post_operations[stage_name]
        kind = str(current.get("kind", ""))
        if kind == "bias_add":
            if model.bias is None:
                raise _generation_error(
                    model, "metadata_missing", "bias_add has no canonical bias binding"
                )
            bias_low, bias_high = _integer_bounds(model.bias["data_type"])
            bias_var = z3.Int("formula_bias")
            solver.add(bias_var >= bias_low, bias_var <= bias_high)
            value = value + bias_var
            conversion = str(arithmetic.get("bias_conversion", "exact"))
            if conversion == "wrap_twos_complement_after_add":
                value = _z3_wrap(value, model.accumulator_dtype)
            elif conversion != "exact":
                raise _generation_error(
                    model,
                    "unsupported_known_feature",
                    f"cannot symbolically compile bias conversion {conversion!r}",
                    concept=str(concept),
                    bin_name=str(bin_spec.get("name", "")),
                )
        elif kind == "wrap":
            value = _z3_wrap(value, _dtype(operation, str(current["data_type"])))
        elif kind == "relu":
            value = z3.If(value < 0, 0, value)
        elif kind == "affine_quantize":
            value = _z3_affine_quantize(
                value, current, _dtype(operation, str(current["data_type"]))
            )
        elif kind == "llm_defined":
            try:
                value, constraints = compile_formula_expression(
                    str(current["formula"]), value
                )
            except FormulaError as exc:
                raise _generation_error(
                    model,
                    "unsupported_known_feature",
                    f"formula stage {stage_name!r} no longer compiles: {exc}",
                    concept=str(concept),
                    bin_name=str(bin_spec.get("name", "")),
                ) from exc
            solver.add(*constraints)
        if stage_name == concept:
            target_value = value
            break

    assert target_value is not None
    try:
        solver.add(_z3_predicate(target_value, predicate))
    except (TypeError, ValueError) as exc:
        raise _generation_error(
            model,
            "metadata_missing",
            str(exc),
            concept=str(concept),
            bin_name=str(bin_spec.get("name", "")),
        ) from exc
    status = solver.check()
    if status == z3.unsat:
        raise _generation_error(
            model,
            "unreachable",
            "Verifier predicate has no legal witness under the compiled operation",
            concept=str(concept),
            bin_name=str(bin_spec.get("name", "")),
        )
    if status != z3.sat:
        raise _generation_error(
            model,
            "generation_inconclusive",
            "solver did not finish the formula-stage witness search",
            concept=str(concept),
            bin_name=str(bin_spec.get("name", "")),
        )

    witness = solver.model()
    stimulus = _base_stimulus(model)
    left_values = stimulus[str(model.left["data_object"])]
    right_values = stimulus[str(model.right["data_object"])]
    for depth in range(model.k):
        left_values[depth] = witness.eval(a_vars[depth], model_completion=True).as_long()
        right_values[depth * model.n] = witness.eval(
            b_vars[depth], model_completion=True
        ).as_long()
    if model.bias is not None and bias_var is not None:
        stimulus[str(model.bias["data_object"])][0] = witness.eval(
            bias_var, model_completion=True
        ).as_long()

    expected = evaluate_canonical_operation(operation, stimulus)
    job = assemble_canonical_job(operation, stimulus, expected, expected)
    assert job is not None
    evidence = classify_operation_job(job)
    values = evidence.get(str(concept), [])
    if not any(_predicate_matches(item, predicate) for item in values):
        raise _generation_error(
            model,
            "generation_inconclusive",
            f"solver witness failed forward classification; evidence={values!r}",
            concept=str(concept),
            bin_name=str(bin_spec.get("name", "")),
        )
    return {
        "operation_name": model.operation_name,
        "kind": "directed",
        "label": f"solver_{concept}_{bin_spec.get('name', 'bin')}",
        "target": {"concept": str(concept), "bin": str(bin_spec.get("name", ""))},
        "stimulus": stimulus,
        "expected": expected,
        "evidence": evidence,
        "solver_origin": "verifier_predicate_over_compiled_formula_stage",
    }


def _solve_dot(model: _GemmModel, target: int) -> tuple[list[int], list[int]] | None:
    result = _reduction_query(model, target, bias=False)
    if result is None:
        return None
    left, right, _ = result
    return left, right


def _solve_dot_with_bias(
    model: _GemmModel, target: int
) -> tuple[list[int], list[int], int] | None:
    result = _reduction_query(model, target, bias=True)
    if result is None:
        return None
    left, right, bias_value = result
    assert bias_value is not None
    return left, right, bias_value


def _raw_bounds(model: _GemmModel) -> tuple[int, int]:
    low, high = _dot_bounds(model)
    if model.bias is not None:
        bias_low, bias_high = _integer_bounds(model.bias["data_type"])
        low += bias_low
        high += bias_high
    return low, high


def _stimulus_for_dot(model: _GemmModel, target: int) -> dict[str, list[int]]:
    low, high = _dot_bounds(model)
    if target < low or target > high:
        raise _generation_error(
            model,
            "unreachable",
            f"reduction value {target} is outside legal dot-product range [{low}, {high}]",
        )
    dot = _solve_dot(model, target)
    if dot is None:
        raise _generation_error(
            model,
            "generation_inconclusive",
            f"reduction value {target} is within loose bounds but no constructive witness was found",
        )
    stimulus = _base_stimulus(model)
    stimulus[str(model.left["data_object"])] = dot[0]
    stimulus[str(model.right["data_object"])] = dot[1]
    return stimulus


def _stimulus_for_raw(model: _GemmModel, target: int) -> dict[str, list[int]]:
    raw_low, raw_high = _raw_bounds(model)
    if target < raw_low or target > raw_high:
        raise _generation_error(
            model,
            "unreachable",
            f"raw value {target} is outside legal contract range [{raw_low}, {raw_high}]",
        )
    if model.bias is None:
        dot = _solve_dot(model, target)
        if dot is not None:
            stimulus = _base_stimulus(model)
            stimulus[str(model.left["data_object"])] = dot[0]
            stimulus[str(model.right["data_object"])] = dot[1]
            return stimulus
    else:
        # Solve for A, B, and bias jointly in one query instead of looping
        # over a handful of guessed bias candidates -- Z3 finds any legal
        # combination, not just the ones a heuristic thought to try.
        solved = _solve_dot_with_bias(model, target)
        if solved is not None:
            left, right, bias_value = solved
            stimulus = _base_stimulus(model)
            stimulus[str(model.left["data_object"])] = left
            stimulus[str(model.right["data_object"])] = right
            stimulus[str(model.bias["data_object"])][0] = bias_value
            return stimulus
    raise _generation_error(
        model,
        "generation_inconclusive",
        f"raw value {target} is within loose numeric bounds but the deterministic constructor could not synthesize it",
    )


def _first_raw_stimulus(
    model: _GemmModel,
    targets: Sequence[int],
    *,
    concept: str,
    bin_name: str,
) -> dict[str, list[int]]:
    failures: list[CanonicalStimulusGenerationError] = []
    for target in targets:
        try:
            return _stimulus_for_raw(model, target)
        except CanonicalStimulusGenerationError as exc:
            failures.append(exc)
    code = (
        "unreachable"
        if failures and all(item.code == "unreachable" for item in failures)
        else "generation_inconclusive"
    )
    raise _generation_error(
        model,
        code,
        "; ".join(item.reason for item in failures) or "no candidate raw value",
        concept=concept,
        bin_name=bin_name,
    )


def _target_stimulus(
    model: _GemmModel, concept: str, bin_name: str
) -> dict[str, list[int]]:
    stimulus = _base_stimulus(model)
    if concept == "dimensions" and bin_name == "fixed_shape":
        return stimulus
    if concept == "operand_values":
        candidates = [model.left, model.right]
        desired: int | None = None
        if bin_name == "zero":
            return stimulus
        if bin_name == "positive":
            desired = 1
            candidates = [item for item in candidates if _integer_bounds(item["data_type"])[1] >= 1]
        elif bin_name == "negative":
            desired = -1
            candidates = [item for item in candidates if _integer_bounds(item["data_type"])[0] <= -1]
        elif bin_name == "minimum":
            desired = min(_integer_bounds(item["data_type"])[0] for item in candidates)
            candidates = [item for item in candidates if _integer_bounds(item["data_type"])[0] == desired]
        elif bin_name == "maximum":
            desired = max(_integer_bounds(item["data_type"])[1] for item in candidates)
            candidates = [item for item in candidates if _integer_bounds(item["data_type"])[1] == desired]
        if desired is not None and candidates:
            selected = candidates[0]
            stimulus[str(selected["data_object"])][0] = desired
            # Do not let an operand-class witness disappear behind an all-zero
            # counterpart.  Make the selected value participate in one real dot
            # product and choose the counterpart sign so signed minima/negative
            # values remain observable after an optional ReLU.
            counterpart = model.right if selected is model.left else model.left
            counterpart_low, counterpart_high = _integer_bounds(
                counterpart["data_type"]
            )
            preferred = -1 if desired < 0 else 1
            if not counterpart_low <= preferred <= counterpart_high:
                preferred = 1 if counterpart_low <= 1 <= counterpart_high else -1
            if not counterpart_low <= preferred <= counterpart_high:
                raise _generation_error(
                    model,
                    "generation_inconclusive",
                    "operand witness has no legal non-zero counterpart",
                    concept=concept,
                    bin_name=bin_name,
                )
            stimulus[str(counterpart["data_object"])][0] = preferred
            return stimulus
    if concept == "bias" and model.bias is not None:
        low, high = _integer_bounds(model.bias["data_type"])
        values = {
            "zero_bias": 0,
            "positive_bias": 1,
            "negative_bias": -1,
            "minimum_bias": low,
            "maximum_bias": high,
        }
        if bin_name in values and low <= values[bin_name] <= high:
            stimulus[str(model.bias["data_object"])][0] = values[bin_name]
            return stimulus
    accumulator_low, accumulator_high = _integer_bounds(model.accumulator_dtype)
    if concept == "accumulation":
        if bin_name == "ordinary":
            interior = [
                value for value in (1, -1, 0, accumulator_low + 1, accumulator_high - 1)
                if accumulator_low < value < accumulator_high
            ]
            failures = []
            for target in interior:
                try:
                    return _stimulus_for_dot(model, target)
                except CanonicalStimulusGenerationError as exc:
                    failures.append(exc)
            raise _generation_error(
                model,
                "unreachable"
                if failures and all(item.code == "unreachable" for item in failures)
                else "generation_inconclusive",
                "; ".join(item.reason for item in failures),
                concept=concept,
                bin_name=bin_name,
            )
        boundary_targets = {
            "positive_boundary": accumulator_high,
            "negative_boundary": accumulator_low,
            "positive_overflow": accumulator_high + 1,
            "negative_overflow": accumulator_low - 1,
        }
        if bin_name in boundary_targets:
            try:
                return _stimulus_for_dot(model, boundary_targets[bin_name])
            except CanonicalStimulusGenerationError as exc:
                raise _generation_error(
                    model,
                    exc.code,
                    exc.reason,
                    concept=concept,
                    bin_name=bin_name,
                ) from exc
    if concept == "activation":
        targets = {
            "negative_region": (-1,),
            "zero_region": (0,),
            "positive_region": (1,),
        }
        if bin_name in targets:
            activation_index = next(
                index
                for index, name in enumerate(model.resolved_stage_order)
                if model.post_operations[name].get("kind") == "relu"
            )
            preceding_quantizers = [
                model.post_operations[name]
                for name in model.resolved_stage_order[:activation_index]
                if model.post_operations[name].get("kind") == "affine_quantize"
            ]
            if preceding_quantizers:
                # The classifier observes the value *entering* ReLU.  If
                # quantization precedes it, raw reduction values -1/0/+1 no
                # longer identify the desired activation regions (a nonzero
                # zero-point is an immediate counterexample).  Invert the
                # quantizer approximately, then let the canonical classifier
                # certify the exact bin after rounding and saturation.
                stage = preceding_quantizers[-1]
                desired = targets[bin_name][0]
                numerator = (desired - int(stage["zero_point"])) * (
                    1 << int(stage["scale_shift"])
                )
                pivot = numerator // int(stage["scale_multiplier"])
                candidates = tuple(
                    dict.fromkeys(
                        pivot + offset
                        for offset in (0, -1, 1, -2, 2, -3, 3)
                    )
                )
                failures: list[CanonicalStimulusGenerationError] = []
                for target in candidates:
                    try:
                        candidate = _stimulus_for_raw(model, target)
                        _case(model, concept, bin_name, candidate)
                        return candidate
                    except CanonicalStimulusGenerationError as exc:
                        failures.append(exc)
                raise _generation_error(
                    model,
                    "generation_inconclusive",
                    "quantizer-inverted candidates did not hit the activation bin: "
                    + "; ".join(item.reason for item in failures),
                    concept=concept,
                    bin_name=bin_name,
                )
            if (
                bin_name == "negative_region"
                and any(item.get("kind") == "wrap" for item in model.post_operations.values())
                and _integer_bounds(model.accumulator_dtype)[0] >= 0
            ):
                raise _generation_error(
                    model,
                    "unreachable",
                    "negative activation is impossible after unsigned wrapping",
                    concept=concept,
                    bin_name=bin_name,
                )
            preceding_bias = any(
                model.post_operations[name].get("kind") == "bias_add"
                for name in model.resolved_stage_order[:activation_index]
            )
            if not preceding_bias:
                # A bias *after* ReLU must not be included in the inverse
                # target for the value entering ReLU. The old raw solver saw
                # any bias object and solved dot+bias=target regardless of
                # the DAG order, often yielding dot=0 for negative_region.
                return _stimulus_for_dot(model, targets[bin_name][0])
            return _first_raw_stimulus(
                model, targets[bin_name], concept=concept, bin_name=bin_name
            )
    if concept == "quantization":
        quantized_stages = [
            (index, model.post_operations[name])
            for index, name in enumerate(model.resolved_stage_order)
            if model.post_operations[name].get("kind") == "affine_quantize"
        ]
        if len(quantized_stages) != 1:
            raise _generation_error(
                model,
                "unsupported_known_feature",
                "quantization requires exactly one affine_quantize stage",
                concept=concept,
                bin_name=bin_name,
            )
        quantized_index, stage = quantized_stages[0]
        denominator = 1 << int(stage["scale_shift"])
        multiplier = int(stage["scale_multiplier"])
        zero_point = int(stage["zero_point"])
        low, high = _integer_bounds(model.result["data_type"])
        if bin_name in {"exact", "nonzero_zero_point"}:
            return _first_raw_stimulus(
                model, (0,), concept=concept, bin_name=bin_name
            )
        if bin_name == "rounded":
            if multiplier % denominator == 0:
                raise _generation_error(
                    model,
                    "unreachable",
                    "the fixed-point scale is integral, so rounding cannot occur",
                    concept=concept,
                    bin_name=bin_name,
                )
            return _first_raw_stimulus(
                model, (1, -1), concept=concept, bin_name=bin_name
            )
        if bin_name == "negative_saturation":
            if any(
                model.post_operations[name].get("kind") == "relu"
                for name in model.resolved_stage_order[:quantized_index]
            ):
                raise _generation_error(
                    model,
                    "unreachable",
                    "ReLU precedes quantization, so negative saturation is impossible",
                    concept=concept,
                    bin_name=bin_name,
                )
            magnitude = ((zero_point - low + 2) * denominator + multiplier - 1) // multiplier
            return _first_raw_stimulus(
                model, (-magnitude,), concept=concept, bin_name=bin_name
            )
        if bin_name == "positive_saturation":
            target = ((high - zero_point + 2) * denominator + multiplier - 1) // multiplier
            return _first_raw_stimulus(
                model, (target,), concept=concept, bin_name=bin_name
            )
    raise _generation_error(
        model,
        (
            "unreachable"
            if concept in {"bias", "activation", "quantization"}
            else "generation_inconclusive"
        ),
        "the requested class has no legal code-owned construction under this contract",
        concept=concept,
        bin_name=bin_name,
    )


def generate_canonical_stimulus_for_bin(
    operation_metadata: Mapping[str, Any],
    concept: str,
    bin_name: str,
    *,
    operation_name: str | None = None,
) -> dict[str, Any]:
    """Generate and self-check one directed canonical vector for a target bin."""

    operation = _select_operation(operation_metadata, operation_name)
    model = _gemm_model(operation)
    if canonical_bins_for_concept(operation, str(concept)) is None:
        raise _generation_error(
            model,
            "unsupported_known_feature",
            "target must be an implemented leaf concept, not a feature group",
            concept=str(concept),
            bin_name=str(bin_name),
        )
    try:
        stimulus = _target_stimulus(model, str(concept), str(bin_name))
        return _case(model, str(concept), str(bin_name), stimulus)
    except CanonicalStimulusGenerationError as exc:
        if exc.concept and exc.bin_name:
            raise
        raise CanonicalStimulusGenerationError(
            exc.code,
            exc.reason,
            operation_name=model.operation_name,
            concept=str(concept),
            bin_name=str(bin_name),
        ) from exc


def generate_random_canonical_stimuli(
    operation_metadata: Mapping[str, Any],
    count: int,
    *,
    operation_name: str | None = None,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Generate reproducible randomized canonical jobs and golden results."""

    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be a non-negative integer")
    operation = _select_operation(operation_metadata, operation_name)
    model = _gemm_model(operation)
    rng = Random(seed)
    result: list[dict[str, Any]] = []
    for index in range(count):
        stimulus = _base_stimulus(model)
        for binding in operation.get("inputs", []):
            low, high = _integer_bounds(binding["data_type"])
            edge_values = tuple(dict.fromkeys((low, high, 0, -1, 1)))
            legal_edges = tuple(value for value in edge_values if low <= value <= high)
            values = stimulus[str(binding["data_object"])]
            for element in range(len(values)):
                values[element] = (
                    rng.choice(legal_edges)
                    if rng.random() < 0.35
                    else rng.randint(low, high)
                )
        expected = evaluate_canonical_operation(operation, stimulus)
        job = assemble_canonical_job(operation, stimulus, expected, expected)
        assert job is not None
        result.append(
            {
                "operation_name": model.operation_name,
                "kind": "randomized",
                "label": f"canonical_random_{index:04d}",
                "target": None,
                "stimulus": stimulus,
                "expected": expected,
                "evidence": classify_operation_job(job),
            }
        )
    return result


def generate_canonical_discriminating_stimuli(
    operation_metadata: Mapping[str, Any],
    *,
    operation_name: str | None = None,
) -> list[dict[str, Any]]:
    """Generate bounded G07 witnesses for indexing, sign, cancellation, and stale state."""

    operation = _select_operation(operation_metadata, operation_name)
    model = _gemm_model(operation)

    def checked(label: str, stimulus: dict[str, list[int]], purpose: str) -> dict[str, Any]:
        expected = evaluate_canonical_operation(operation, stimulus)
        job = assemble_canonical_job(operation, stimulus, expected, expected)
        assert job is not None
        return {
            "operation_name": model.operation_name,
            "kind": "directed",
            "label": label,
            "target": None,
            "qualification_purpose": purpose,
            "stimulus": stimulus,
            "expected": expected,
            "evidence": classify_operation_job(job),
        }

    cases: list[dict[str, Any]] = []
    one_hot = _base_stimulus(model)
    row, depth, column = min(1, model.m - 1), min(1, model.k - 1), min(1, model.n - 1)
    a_low, a_high = _integer_bounds(model.left["data_type"])
    b_low, b_high = _integer_bounds(model.right["data_type"])
    a_value = 2 if a_low <= 2 <= a_high else 1
    b_value = 3 if b_low <= 3 <= b_high else 1
    one_hot[str(model.left["data_object"])][row * model.k + depth] = a_value
    one_hot[str(model.right["data_object"])][depth * model.n + column] = b_value
    cases.append(
        checked(
            "canonical_one_hot_coordinate",
            one_hot,
            "distinguish row/column/K indexing and dropped terms",
        )
    )

    asymmetric = _base_stimulus(model)
    a_palette = [value for value in (-3, -1, 1, 2, 5) if a_low <= value <= a_high]
    b_palette = [value for value in (4, -2, 3, 1, -1) if b_low <= value <= b_high]
    if not a_palette:
        a_palette = [a_low]
    if not b_palette:
        b_palette = [b_low]
    asymmetric[str(model.left["data_object"])] = [
        a_palette[index % len(a_palette)]
        for index in range(model.m * model.k)
    ]
    asymmetric[str(model.right["data_object"])] = [
        b_palette[(index * 3 + 1) % len(b_palette)]
        for index in range(model.k * model.n)
    ]
    cases.append(
        checked(
            "canonical_asymmetric_matrix",
            asymmetric,
            "distinguish transpose, neighbor swap, and job association errors",
        )
    )

    if model.k >= 2 and a_low <= 1 <= a_high and b_low <= -1 <= b_high:
        cancellation = _base_stimulus(model)
        cancellation[str(model.left["data_object"])][0:2] = [1, 1]
        cancellation[str(model.right["data_object"])][0] = 1
        cancellation[str(model.right["data_object"])][model.n] = -1
        cases.append(
            checked(
                "canonical_exact_cancellation",
                cancellation,
                "distinguish signed reduction and exact cancellation",
            )
        )

    zero_after_nonzero = _base_stimulus(model)
    cases.append(
        checked(
            "canonical_zero_after_nonzero",
            zero_after_nonzero,
            "run after the asymmetric case to expose stale operation state",
        )
    )
    return cases


def generate_canonical_stimulus_suite(
    operation_metadata: Mapping[str, Any],
    *,
    operation_name: str | None = None,
    concepts: Sequence[str] | None = None,
    randomized_count: int = 0,
    seed: int = 0,
) -> dict[str, Any]:
    """Return directed/randomized cases plus explicit per-bin exceptions."""

    operation = _select_operation(operation_metadata, operation_name)
    model = _gemm_model(operation)
    supported = supported_code_owned_concepts({"operations": [operation]}).get(
        model.operation_name, set()
    )
    selected = sorted(supported if concepts is None else set(map(str, concepts)))
    directed: list[dict[str, Any]] = []
    exceptions: list[dict[str, str]] = []
    for concept in selected:
        bins = canonical_bins_for_concept(operation, concept)
        if bins is None:
            exceptions.append(
                _generation_error(
                    model,
                    "unsupported_known_feature",
                    "concept has no code-owned canonical bins",
                    concept=concept,
                ).as_dict()
            )
            continue
        for bin_spec in bins:
            bin_name = str(bin_spec["name"])
            try:
                directed.append(
                    generate_canonical_stimulus_for_bin(
                        operation, concept, bin_name
                    )
                )
            except CanonicalStimulusGenerationError as exc:
                exceptions.append(exc.as_dict())
    return {
        "schema_version": 1,
        "operation_name": model.operation_name,
        "directed": directed,
        "randomized": generate_random_canonical_stimuli(
            operation, randomized_count, seed=seed
        ),
        "qualification": generate_canonical_discriminating_stimuli(operation),
        "exceptions": exceptions,
    }


def reachable_canonical_bins_for_concept(
    operation_metadata: Mapping[str, Any], concept: str
) -> list[dict[str, Any]] | None:
    """Return only bins with a deterministic legal witness.

    Use :func:`canonical_bin_dispositions` when the reason for exclusion matters.
    Unresolved or unsupported bins are never silently included in a closure target.
    """

    dispositions = canonical_bin_dispositions(operation_metadata, concept)
    if dispositions is None:
        return None
    return [
        dict(item["bin"])
        for item in dispositions
        if item["status"] == "required_reachable"
    ]


def canonical_bin_dispositions(
    operation_metadata: Mapping[str, Any], concept: str
) -> list[dict[str, Any]] | None:
    """Resolve each known bin to a witness-backed or explicit blocking status."""

    bins = canonical_bins_for_concept(operation_metadata, concept)
    if bins is None:
        return None
    result: list[dict[str, Any]] = []
    for bin_spec in bins:
        try:
            witness = generate_canonical_stimulus_for_bin(
                operation_metadata, concept, str(bin_spec["name"])
            )
        except CanonicalStimulusGenerationError as exc:
            status = (
                "proven_unreachable" if exc.code == "unreachable" else exc.code
            )
            result.append(
                {
                    "bin": dict(bin_spec),
                    "status": status,
                    "reason": exc.reason,
                    "witness": None,
                }
            )
        else:
            result.append(
                {
                    "bin": dict(bin_spec),
                    "status": "required_reachable",
                    "reason": "deterministic constructor and classifier produced a legal witness",
                    "witness": {
                        "label": witness["label"],
                        "digest_input": witness["stimulus"],
                    },
                }
            )
    return result
