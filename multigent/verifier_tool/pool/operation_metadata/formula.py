"""Compile Architect-declared scalar formulas into the tool's solver IR.

The contract does not select from a published list of arithmetic tokens or
feature names. It supplies a formula over ``value`` and the Contract Reviewer
accepts it only when this module can compile it into an integer Z3 expression.
The same compiled expression is used for concrete golden-model evaluation, so
the solver and the reference model cannot silently implement different maths.

This is deliberately a compiler, not ``eval``/``exec``. Python syntax is only
used as a convenient parser; names, calls, and expression nodes are translated
one by one into solver expressions. An expression the compiler cannot give
precise integer semantics is rejected. The Architect may revise the formula,
or explicitly declare ``classifier_profile: llm_extension`` when the behavior
is genuinely outside the solver-backed scalar model.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Mapping

import z3


class FormulaError(ValueError):
    """A formula cannot be represented by the deterministic solver backend."""


@dataclass(frozen=True)
class CompiledFormula:
    """One solver-compiled scalar formula and its well-definedness guards."""

    source: str
    value_symbol: z3.ArithRef
    expression: z3.ArithRef
    constraints: tuple[z3.BoolRef, ...]

    def evaluate(self, value: int) -> int:
        """Evaluate with exactly the semantics used by symbolic solving."""

        replacement = z3.IntVal(int(value))
        guards = [
            z3.simplify(z3.substitute(item, (self.value_symbol, replacement)))
            for item in self.constraints
        ]
        if any(z3.is_false(item) for item in guards):
            raise FormulaError(
                f"formula {self.source!r} is undefined for value={value}"
            )
        result = z3.simplify(
            z3.substitute(self.expression, (self.value_symbol, replacement))
        )
        if z3.is_int_value(result):
            return result.as_long()
        solver = z3.Solver()
        solver.add(*guards)
        if solver.check() != z3.sat:
            raise FormulaError(
                f"formula {self.source!r} is undefined for value={value}"
            )
        evaluated = solver.model().eval(result, model_completion=True)
        if not z3.is_int_value(evaluated):
            raise FormulaError(
                f"formula {self.source!r} did not produce a concrete integer"
            )
        return evaluated.as_long()


def _integer(expression: z3.ExprRef, formula: str) -> z3.ArithRef:
    if z3.is_bool(expression):
        return z3.If(expression, z3.IntVal(1), z3.IntVal(0))
    if z3.is_int(expression):
        return expression  # type: ignore[return-value]
    raise FormulaError(
        f"formula {formula!r} does not compile to an integer expression"
    )


def _boolean(expression: z3.ExprRef, formula: str) -> z3.BoolRef:
    if z3.is_bool(expression):
        return expression  # type: ignore[return-value]
    if z3.is_int(expression):
        return expression != 0
    raise FormulaError(
        f"formula {formula!r} does not compile to a boolean condition"
    )


class _SolverCompiler:
    def __init__(self, formula: str, bindings: Mapping[str, z3.ExprRef]) -> None:
        self.formula = formula
        self.bindings = dict(bindings)
        self.constraints: list[z3.BoolRef] = []

    def compile(self, node: ast.AST) -> z3.ExprRef:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return z3.BoolVal(node.value)
            if isinstance(node.value, int):
                return z3.IntVal(node.value)
            raise FormulaError(
                f"formula {self.formula!r} has a non-integer literal {node.value!r}"
            )

        if isinstance(node, ast.Name):
            if node.id not in self.bindings:
                raise FormulaError(
                    f"formula {self.formula!r} references unbound name {node.id!r}"
                )
            return self.bindings[node.id]

        if isinstance(node, ast.UnaryOp):
            operand = self.compile(node.operand)
            if isinstance(node.op, ast.USub):
                return -_integer(operand, self.formula)
            if isinstance(node.op, ast.UAdd):
                return _integer(operand, self.formula)
            if isinstance(node.op, ast.Not):
                return z3.Not(_boolean(operand, self.formula))
            raise FormulaError(
                f"formula {self.formula!r} has no solver meaning for "
                f"unary node {type(node.op).__name__}"
            )

        if isinstance(node, ast.BinOp):
            left = _integer(self.compile(node.left), self.formula)
            right = _integer(self.compile(node.right), self.formula)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.FloorDiv):
                self.constraints.append(right != 0)
                return left / right
            if isinstance(node.op, ast.Mod):
                self.constraints.append(right != 0)
                return left % right
            if isinstance(node.op, ast.Pow):
                if (
                    not isinstance(node.right, ast.Constant)
                    or not isinstance(node.right.value, int)
                    or isinstance(node.right.value, bool)
                    or node.right.value < 0
                    or node.right.value > 64
                ):
                    raise FormulaError(
                        f"formula {self.formula!r} requires an integer literal "
                        "exponent in the bounded range 0..64"
                    )
                result: z3.ArithRef = z3.IntVal(1)
                for _ in range(node.right.value):
                    result = result * left
                return result
            if isinstance(node.op, ast.Div):
                raise FormulaError(
                    f"formula {self.formula!r} uses real division and therefore "
                    "has no declared integer rounding semantics"
                )
            raise FormulaError(
                f"formula {self.formula!r} has no integer solver meaning for "
                f"node {type(node.op).__name__}"
            )

        if isinstance(node, ast.BoolOp):
            values = [
                _boolean(self.compile(item), self.formula) for item in node.values
            ]
            if isinstance(node.op, ast.And):
                return z3.And(*values)
            if isinstance(node.op, ast.Or):
                return z3.Or(*values)
            raise FormulaError(
                f"formula {self.formula!r} has no solver meaning for "
                f"boolean node {type(node.op).__name__}"
            )

        if isinstance(node, ast.Compare):
            operands = [
                self.compile(node.left),
                *[self.compile(item) for item in node.comparators],
            ]
            comparisons: list[z3.BoolRef] = []
            for left_raw, operator, right_raw in zip(
                operands, node.ops, operands[1:]
            ):
                left = _integer(left_raw, self.formula)
                right = _integer(right_raw, self.formula)
                if isinstance(operator, ast.Lt):
                    comparisons.append(left < right)
                elif isinstance(operator, ast.LtE):
                    comparisons.append(left <= right)
                elif isinstance(operator, ast.Gt):
                    comparisons.append(left > right)
                elif isinstance(operator, ast.GtE):
                    comparisons.append(left >= right)
                elif isinstance(operator, ast.Eq):
                    comparisons.append(left == right)
                elif isinstance(operator, ast.NotEq):
                    comparisons.append(left != right)
                else:
                    raise FormulaError(
                        f"formula {self.formula!r} has no solver meaning for "
                        f"comparison node {type(operator).__name__}"
                    )
            return z3.And(*comparisons)

        if isinstance(node, ast.IfExp):
            condition = _boolean(self.compile(node.test), self.formula)
            yes = _integer(self.compile(node.body), self.formula)
            no = _integer(self.compile(node.orelse), self.formula)
            return z3.If(condition, yes, no)

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.keywords:
                raise FormulaError(
                    f"formula {self.formula!r} contains a call the solver cannot bind"
                )
            name = node.func.id
            args = [self.compile(item) for item in node.args]
            if name in {"min", "max"} and args:
                integers = [_integer(item, self.formula) for item in args]
                result = integers[0]
                for item in integers[1:]:
                    if name == "min":
                        result = z3.If(result <= item, result, item)
                    else:
                        result = z3.If(result >= item, result, item)
                return result
            if name == "abs" and len(args) == 1:
                value = _integer(args[0], self.formula)
                return z3.If(value >= 0, value, -value)
            if name == "clip" and len(args) == 3:
                value, low, high = [
                    _integer(item, self.formula) for item in args
                ]
                return z3.If(
                    value < low, low, z3.If(value > high, high, value)
                )
            if name in {"ite", "if_then_else"} and len(args) == 3:
                return z3.If(
                    _boolean(args[0], self.formula),
                    _integer(args[1], self.formula),
                    _integer(args[2], self.formula),
                )
            raise FormulaError(
                f"formula {self.formula!r} calls {name!r}, which has no "
                "registered deterministic solver implementation"
            )

        raise FormulaError(
            f"formula {self.formula!r} contains syntax the solver cannot compile: "
            f"{type(node).__name__}"
        )


def parse_formula(formula: str) -> ast.expr:
    """Parse only; representability is decided by :func:`compile_formula`."""

    if not isinstance(formula, str) or not formula.strip():
        raise FormulaError("formula must be a non-empty string")
    if len(formula) > 4096:
        raise FormulaError("formula exceeds the deterministic compiler size limit")
    try:
        expression = ast.parse(formula, mode="eval").body
    except SyntaxError as exc:
        raise FormulaError(
            f"formula {formula!r} is not valid syntax: {exc}"
        ) from exc
    if sum(1 for _ in ast.walk(expression)) > 512:
        raise FormulaError("formula exceeds the deterministic compiler node limit")
    return expression


def compile_formula(formula: str) -> CompiledFormula:
    """Compile a contract formula into reusable integer solver IR."""

    value = z3.Int("formula_value")
    compiler = _SolverCompiler(formula, {"value": value})
    expression = _integer(compiler.compile(parse_formula(formula)), formula)
    return CompiledFormula(
        source=formula,
        value_symbol=value,
        expression=z3.simplify(expression),
        constraints=tuple(
            z3.simplify(item) for item in compiler.constraints
        ),
    )


def compile_formula_expression(
    formula: str, value: z3.ArithRef
) -> tuple[z3.ArithRef, tuple[z3.BoolRef, ...]]:
    """Compile directly against a caller-owned symbolic stage input."""

    compiler = _SolverCompiler(formula, {"value": value})
    expression = _integer(compiler.compile(parse_formula(formula)), formula)
    return z3.simplify(expression), tuple(
        z3.simplify(item) for item in compiler.constraints
    )


def evaluate_formula(formula: str, value: int) -> int:
    """Evaluate through the same solver expression used for constraint solving."""

    return compile_formula(formula).evaluate(value)


__all__ = [
    "CompiledFormula",
    "FormulaError",
    "compile_formula",
    "compile_formula_expression",
    "evaluate_formula",
    "parse_formula",
]
