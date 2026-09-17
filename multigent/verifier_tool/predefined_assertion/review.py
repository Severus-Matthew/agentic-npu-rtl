"""Read-only assertion definition views; no stimulus schedules or DUT evidence."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


_COLLECTION_MUTATORS = {
    'append', 'appendleft', 'extend', 'extendleft', 'insert', 'pop', 'popleft',
    'popitem', 'remove', 'clear', 'update', 'setdefault', 'add', 'discard',
    'difference_update', 'intersection_update', 'symmetric_difference_update',
    'sort', 'reverse', 'rotate', '__setitem__', '__delitem__',
}


def _call_name(node: ast.Call) -> str:
    return ast.unparse(node.func).rsplit(".", 1)[-1]


def _definition_expression(node: ast.AST) -> str:
    """Hide generator/driver expressions and concrete multi-element payloads."""
    if any(
        isinstance(child, ast.Call)
        and (_call_name(child) in {
            "record_stimulus",
            "_contract_record_checked_stimulus",
            "start_soon",
            "start",
            "drive",
            "send_beat",
        }
             or isinstance(child.func, ast.Attribute)
             and child.func.attr in {"Random", "randint", "randrange", "choice", "getrandbits", "uniform", "shuffle", "random"})
        for child in ast.walk(node)
    ):
        return "<stimulus or task setup excluded from review>"
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        return "<collection generator excluded from review>"
    # Empty checker containers are state initialization, not concrete traffic.
    def empty_container(item: ast.AST) -> bool:
        if isinstance(item, (ast.List, ast.Set, ast.Tuple)):
            return all(empty_container(child) for child in item.elts)
        return isinstance(item, ast.Dict) and not item.keys
    if isinstance(node, (ast.List, ast.Set, ast.Tuple, ast.Dict)) and empty_container(node):
        return ast.unparse(node)
    if (
        isinstance(node, (ast.List, ast.Set)) and len(node.elts) > 1
        or isinstance(node, ast.Tuple)
        and any(isinstance(item, (ast.List, ast.Tuple, ast.Dict)) for item in node.elts)
    ):
        return "<concrete payload/scenario collection excluded from review>"
    return ast.unparse(node)


def assertion_definition_view(source: str, *, filename: str) -> dict[str, Any]:
    """Retain check expressions/guards/origins, not a synthesized executable TB.

    Source coordinates let the model cite real evidence without seeing stimulus
    values. No heuristic assertion-presence gate is imposed by this projection.
    """
    tree = ast.parse(source, filename=filename)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    # Explicit DUT aliases describe driver targets, not checker collection state.
    dut_aliases = {'dut'}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            if isinstance(node.value, (ast.Name, ast.Attribute)) and ast.unparse(node.value) in dut_aliases:
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(target, (ast.Name, ast.Attribute)) and ast.unparse(target) not in dut_aliases:
                        dut_aliases.add(ast.unparse(target))
                        changed = True

    def driver_target(target: ast.AST) -> bool:
        return any(isinstance(child, ast.Attribute) and child.attr == 'value'
                   or isinstance(child, ast.Attribute) and ast.unparse(child.value) in dut_aliases
                   and ast.unparse(child) not in dut_aliases
                   for child in ast.walk(target))

    functions = []
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        checks: list[dict[str, Any]] = []
        assignments: list[tuple[ast.Assign | ast.AnnAssign | ast.AugAssign, list[str]]] = []
        mutations: list[tuple[ast.Call | ast.Delete, list[str]]] = []
        observations: list[dict[str, Any]] = []
        returns: list[dict[str, Any]] = []
        referenced: set[str] = {'self'} if function.name == '__init__' else set()
        owner = parents.get(function)
        if isinstance(owner, ast.ClassDef):
            arguments = function.args.posonlyargs + function.args.args
            if arguments:
                # Keep checker helper updates even if its assertion lives in
                # another method on the same instance.
                referenced.add(arguments[0].arg)

        def remember(node: ast.AST) -> None:
            referenced.update(child.id for child in ast.walk(node) if isinstance(child, ast.Name))

        def visit(statements: list[ast.stmt], guards: list[str]) -> None:
            for node in statements:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue  # Nested checker functions get their own entry.
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    assignments.append((node, guards))
                if isinstance(node, ast.Delete):
                    mutations.append((node, guards))
                if isinstance(node, (ast.Assert, ast.Raise)):
                    checks.append({"line": node.lineno, "guards": guards, "source": ast.unparse(node)})
                    remember(node)
                if isinstance(node, ast.Return) and node.value is not None:
                    returns.append({'line': node.lineno, 'guards': guards,
                                    'expression': _definition_expression(node.value)})
                    remember(node.value)
                for child in ast.walk(node):
                    # Compound statements are visited below, preserving lexical guards.
                    if child is not node and isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)):
                        continue
                    if isinstance(child, ast.Call) and _call_name(child) in {
                        "sample_operation", "_assertion_failure", "fail", "assert_equal", "assert_equals",
                    }:
                        expr = ast.unparse(child)
                        if _call_name(child) == "sample_operation":
                            expr = ast.unparse(ast.Call(func=child.func, args=child.args[:2], keywords=[]))
                        checks.append({"line": child.lineno, "guards": guards, "source": expr})
                        remember(child)
                    if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                            and child.func.attr in _COLLECTION_MUTATORS):
                        mutations.append((child, guards))
                    if isinstance(child, ast.Await) and isinstance(child.value, ast.Call) and _call_name(child.value) in {
                        "RisingEdge", "FallingEdge", "ReadOnly", "Timer", "Edge",
                    }:
                        observations.append({"line": child.lineno, "guards": guards, "source": ast.unparse(child)})
                if isinstance(node, ast.If):
                    condition = _definition_expression(node.test)
                    if not condition.startswith('<'):
                        remember(node.test)
                    visit(node.body, guards + [condition])
                    visit(node.orelse, guards + [f"not ({condition})"])
                elif isinstance(node, ast.While):
                    remember(node.test)
                    visit(node.body, guards + [f"while {ast.unparse(node.test)}"])
                    visit(node.orelse, guards + ["loop exhausted"])
                elif isinstance(node, (ast.For, ast.AsyncFor)):
                    visit(node.body, guards + [f"for {ast.unparse(node.target)} (iteration schedule excluded)"])
                    visit(node.orelse, guards + ["loop exhausted"])
                elif isinstance(node, ast.Try):
                    visit(node.body, guards)
                    for handler in node.handlers:
                        visit(handler.body, guards + [f"except {ast.unparse(handler.type) if handler.type else 'any'}"])
                    visit(node.orelse, guards)
                    visit(node.finalbody, guards + ["finally"])
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    visit(node.body, guards)
                elif isinstance(node, ast.Match):
                    remember(node.subject)
                    for case in node.cases:
                        condition = f'match {ast.unparse(node.subject)} case {ast.unparse(case.pattern)}'
                        if case.guard is not None:
                            condition += f' if {ast.unparse(case.guard)}'
                            remember(case.guard)
                        visit(case.body, guards + [condition])

        visit(function.body, [])
        # Transitive local variable origins expose, e.g., missing snapshot keys.
        origins = []
        updates = []
        pending, pending_mutations = list(assignments), list(mutations)
        while pending or pending_mutations:
            old_pending = len(pending) + len(pending_mutations)
            kept = []
            for node, guards in pending:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = {child.id for target in targets for child in ast.walk(target) if isinstance(child, ast.Name)}
                if names & referenced and not any(driver_target(target) for target in targets):
                    origins.append({"line": node.lineno, "target": ", ".join(ast.unparse(target) for target in targets),
                                    "guards": guards,
                                    "operator": type(node.op).__name__ if isinstance(node, ast.AugAssign) else 'Assign',
                                    "expression": _definition_expression(node.value) if node.value is not None else "annotation only"})
                    if node.value is not None:
                        remember(node.value)
                else:
                    kept.append((node, guards))
            pending = kept
            kept_mutations = []
            for node, guards in pending_mutations:
                targets = node.targets if isinstance(node, ast.Delete) else [node.func.value]
                names = {child.id for target in targets for child in ast.walk(target) if isinstance(child, ast.Name)}
                mutates_dut_object = isinstance(node, ast.Call) and ast.unparse(node.func.value) in dut_aliases
                if not names & referenced or mutates_dut_object or any(driver_target(target) for target in targets):
                    kept_mutations.append((node, guards))
                    continue
                if isinstance(node, ast.Delete):
                    update = {'operation': 'delete', 'targets': [ast.unparse(target) for target in targets]}
                    remember(node)
                else:
                    # Apply the same redaction as variable origins: a mutator
                    # must not bring RNG expressions or concrete vectors back.
                    rendered = _definition_expression(node)
                    if rendered == '<stimulus or task setup excluded from review>':
                        continue
                    update = {'operation': node.func.attr, 'target': ast.unparse(node.func.value),
                              'arguments': [_definition_expression(arg) for arg in node.args],
                              'keyword_arguments': [{'name': arg.arg, 'expression': _definition_expression(arg.value)}
                                                    for arg in node.keywords]}
                    for arg in [*node.args, *(keyword.value for keyword in node.keywords)]:
                        remember(arg)
                    for target in targets:
                        remember(target)
                updates.append({'line': node.lineno, 'guards': guards, **update})
            pending_mutations = kept_mutations
            if len(pending) + len(pending_mutations) == old_pending:
                break
        if not checks and not returns and not updates and function.name != '__init__':
            continue
        functions.append({"function": function.name, "line": function.lineno,
                          "class": owner.name if isinstance(owner, ast.ClassDef) else None,
                          "parameters": ast.unparse(function.args),
                          "decorators": [ast.unparse(item) for item in function.decorator_list],
                          "checks": checks, "variable_origins": sorted(origins, key=lambda item: item["line"]),
                          "state_updates": sorted(updates, key=lambda item: item['line']),
                          "return_definitions": returns,
                          "observation_awaits": observations})
    return {"path": filename, "view": "ASSERTION_DEFINITIONS_ONLY", "functions": functions}


def trusted_monitor_review_view() -> dict[str, Any]:
    """Expose only backend logic not already visible in the saved TB source."""
    sampler_path = Path(__file__).resolve().parents[1] / "coverage" / "operation" / "sampling.py"
    sampler_tree = ast.parse(sampler_path.read_text(encoding="utf-8"))
    return {"operation_sampling_source": "\n\n".join(
        ast.unparse(node) for node in ast.walk(sampler_tree)
        if isinstance(node, ast.FunctionDef) and node.name in {"_read", "sample", "_dtype", "_bound_bins", "bind_observers", "reset"}
    ), "ownership": {
        "stall_stability": "the exact code-owned assertion and signal bindings are embedded in stimulus_and_assertion_source",
        "coverage": "the TB captures one immutable interface snapshot; runtime only evaluates the configured cocotb-coverage backend from that snapshot",
        "completion_reset_error": "event coverpoints observe signals; contract-specific lifecycle assertions remain LLM-authored TB checks",
        "operation": "runtime observes DUT fields for every operation point; reusable or generated custom observers feed the same backend; catalog feature result comparison is code-owned, while taxonomy-missing custom observers/assertions need contract-based review",
    }}
