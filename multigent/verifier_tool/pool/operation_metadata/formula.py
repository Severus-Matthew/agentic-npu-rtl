"""A small, closed, sandboxed integer-arithmetic expression language for an
Architect-declared `post_operations` stage this tool has no built-in `kind`
for (`bias_add`/`wrap`/`relu`/`affine_quantize`) -- see `arithmetic_metadata.py`'s
`llm_defined` kind and `canonical.py::integer_matrix_multiply_events`'s
dispatch of it. Declaring a new post-op this way, instead of falling back to
`classifier_profile: llm_extension`, is what lets every concept that does not
need to look past the new stage (e.g. `accumulation`, which only needs the
reduction) keep getting fully automatic code-owned stimulus and golden
values: the moment a `post_operations` stage kind is genuinely unknown to
this whole file, `_gemm_model` rejects the *entire* operation, not just the
part that touches that stage.

Grammar: the single free variable `value` (the running scalar entering this
stage), integer literals, `+ - *` and unary `-`, comparisons (`< <= > >= ==
!=`, yielding 0/1), and calls to `min`/`max` (2 args), `abs` (1 arg), and
`clip(x, lo, hi)` (sugar for `min(max(x, lo), hi)`) -- enough to express
relu-family and saturation/clamp post-ops. The common per-tensor fixed-point
affine quantizer has its own built-in `affine_quantize` kind; this formula path
is for different custom quantizers. No division, modulo, bitwise ops, or
exponentiation in this version; no attribute access, subscripting, other
names, or other calls, ever.

Never uses `eval`/`exec`: `parse_formula` recursively validates the parsed
AST against an explicit shape whitelist and raises `FormulaError` for
anything outside it. This text ultimately comes from LLM-authored contract
input, so accepting it as trusted Python would be a code-execution hole.
"""
from __future__ import annotations

import ast

_ALLOWED_COMPARISONS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult)
_CALL_ARITY = {"min": 2, "max": 2, "abs": 1, "clip": 3}


class FormulaError(ValueError):
    """An llm_defined post-operation formula is not in the supported grammar."""


def _validate(node: ast.AST, formula: str) -> None:
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, int) or isinstance(node.value, bool):
            raise FormulaError(f"formula {formula!r} has a non-integer literal {node.value!r}")
        return
    if isinstance(node, ast.Name):
        if node.id != "value":
            raise FormulaError(
                f"formula {formula!r} references unknown name {node.id!r}; only 'value' is bound"
            )
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.USub):
            raise FormulaError(
                f"formula {formula!r} uses unsupported unary operator {type(node.op).__name__}"
            )
        _validate(node.operand, formula)
        return
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise FormulaError(
                f"formula {formula!r} uses unsupported operator {type(node.op).__name__}"
            )
        _validate(node.left, formula)
        _validate(node.right, formula)
        return
    if isinstance(node, ast.Compare):
        if (
            len(node.ops) != 1
            or len(node.comparators) != 1
            or not isinstance(node.ops[0], _ALLOWED_COMPARISONS)
        ):
            raise FormulaError(f"formula {formula!r} uses an unsupported comparison")
        _validate(node.left, formula)
        _validate(node.comparators[0], formula)
        return
    if isinstance(node, ast.Call):
        if (
            not isinstance(node.func, ast.Name)
            or node.func.id not in _CALL_ARITY
            or node.keywords
            or len(node.args) != _CALL_ARITY[node.func.id]
        ):
            raise FormulaError(
                f"formula {formula!r} calls an unsupported function "
                f"(only {sorted(_CALL_ARITY)} with fixed arity are allowed)"
            )
        for arg in node.args:
            _validate(arg, formula)
        return
    raise FormulaError(f"formula {formula!r} uses unsupported syntax {type(node).__name__}")


def parse_formula(formula: str) -> ast.expr:
    """Parse and validate `formula` against the closed grammar without executing it."""

    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"formula {formula!r} is not valid syntax: {exc}") from exc
    _validate(tree.body, formula)
    return tree.body


def _evaluate(node: ast.expr, value: int) -> int:
    if isinstance(node, ast.Name):
        return value
    if isinstance(node, ast.Constant):
        return int(node.value)
    if isinstance(node, ast.UnaryOp):
        return -_evaluate(node.operand, value)
    if isinstance(node, ast.BinOp):
        left, right = _evaluate(node.left, value), _evaluate(node.right, value)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        return left * right
    if isinstance(node, ast.Compare):
        left, right = _evaluate(node.left, value), _evaluate(node.comparators[0], value)
        op = node.ops[0]
        if isinstance(op, ast.Lt):
            return int(left < right)
        if isinstance(op, ast.LtE):
            return int(left <= right)
        if isinstance(op, ast.Gt):
            return int(left > right)
        if isinstance(op, ast.GtE):
            return int(left >= right)
        if isinstance(op, ast.Eq):
            return int(left == right)
        return int(left != right)
    if isinstance(node, ast.Call):
        args = [_evaluate(arg, value) for arg in node.args]
        name = node.func.id  # type: ignore[union-attr]
        if name == "min":
            return min(args)
        if name == "max":
            return max(args)
        if name == "abs":
            return abs(args[0])
        lo, hi = sorted(args[1:3])
        return min(max(args[0], lo), hi)
    raise FormulaError(f"cannot evaluate node {type(node).__name__}")


def evaluate_formula(formula: str, value: int) -> int:
    """Evaluate `formula` for the concrete integer `value`."""

    return _evaluate(parse_formula(formula), value)


__all__ = ["FormulaError", "evaluate_formula", "parse_formula"]
