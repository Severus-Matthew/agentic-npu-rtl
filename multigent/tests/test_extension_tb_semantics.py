"""Run and structurally audit the executable extension TB scenarios 11-25."""

from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    build_feature_extension_manifest,
    validate_verifier_extension_bundles,
)


FIXTURE = Path(__file__).parent / "fixtures" / "feature_extensions"
TB_PATH = FIXTURE / "test_extension_reference_tb.py"


def _functions() -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(TB_PATH.read_text(encoding="utf-8"), filename=str(TB_PATH))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _called_names(node: ast.AST) -> set[str]:
    result: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name):
            result.add(child.func.id)
        elif isinstance(child.func, ast.Attribute):
            result.add(child.func.attr)
    return result


def test_each_extension_tb_has_real_stimulus_assertion_coverage_and_negative_control() -> None:
    """Reject the exact no-op/constant-coverage mistake in the old matrix."""

    functions = _functions()
    for case in range(11, 26):
        assertion = functions[f"assert_case_{case}"]
        coverage = functions[f"cover_case_{case}"]
        stimulus = functions[f"stimulate_case_{case}"]
        root = next(
            node
            for name, node in functions.items()
            if name.startswith(f"test_case_{case}_")
        )

        assert any(isinstance(node, ast.Assert) for node in ast.walk(assertion)), case
        assert any(
            isinstance(node, (ast.Compare, ast.BoolOp)) for node in ast.walk(coverage)
        ), case
        assert isinstance(stimulus, ast.AsyncFunctionDef), case
        assert any(isinstance(node, ast.Await) for node in ast.walk(stimulus)), case
        assert "dut" in {argument.arg for argument in stimulus.args.args}, case

        called = _called_names(root)
        assert {
            f"assert_case_{case}",
            f"cover_case_{case}",
            f"stimulate_case_{case}",
            "_must_reject",
        } <= called, case


def test_executable_tb_symbols_are_the_implementations_saved_in_extension_bundles() -> None:
    """The semantic TB must cross the same request/bundle manifest boundary."""

    domains = {
        **{case: "operation" for case in range(11, 15)},
        **{case: "protocol" for case in range(15, 20)},
        **{case: "lifecycle" for case in range(20, 24)},
        24: "operation",
        25: "operation",
    }
    requests, bundles = [], []
    source_path = "tests/test_extension_reference_tb.py"
    for case in range(11, 26):
        domain = domains[case]
        identity = f"{domain}.case_{case}"
        request = {
            "id": identity,
            "domain": domain,
            "feature_name": f"case_{case}",
            "target": {"scope": "interface", "name": "interface"},
            "semantics": {
                "summary": f"Executable frozen semantics for extension case {case}.",
                "trigger": "The directed case begins.",
                "required_behavior": ["The observed evidence satisfies the case-specific checker."],
                "end_condition": "The case-specific terminal observation is recorded.",
                "forbidden_behavior": ["Corrupted negative-control evidence is accepted."],
            },
            "reason": "This behavior is absent from the closed pool used by the fixture.",
            "required_observations": [
                {
                    "name": "evidence",
                    "kind": "transaction",
                    "description": "Actual evidence returned by the cocotb stimulus.",
                }
            ],
            "related_builtin_features": [],
        }
        implementation = {
            "kind": "verifier_python",
            "name": f"case_{case}",
            "file": source_path,
        }
        bundle = {
            "schema_version": 1,
            "request_id": identity,
            "id": identity,
            "domain": domain,
            "feature_name": f"case_{case}",
            "target": {"scope": "interface", "name": "interface"},
            "description": f"Executable cocotb implementation for case {case}.",
            "bindings": {"evidence": "actual simulator observations"},
            "reuse": {"based_on_features": [], "helpers": ["reference_dut"]},
            "assertion": {
                "implementation": {**implementation, "symbol": f"assert_case_{case}"},
                "parameters": {},
            },
            "coverage": {
                "implementation": {**implementation, "symbol": f"cover_case_{case}"},
                "parameters": {},
                "bins": [
                    {
                        "name": "observed_case",
                        "intent": "Observe the case-specific directed condition.",
                        "predicate": {"case": case},
                    }
                ],
            },
            "stimulus": {
                "implementation": {**implementation, "symbol": f"stimulate_case_{case}"},
                "parameters": {},
                "scenarios": [
                    {
                        "name": "directed_case",
                        "intent": "Drive the case-specific reference behavior.",
                        "parameters": {"case": case},
                    }
                ],
            },
        }
        requests.append(request)
        bundles.append(bundle)

    architecture = {"verification_extensions": requests}
    sources = [
        {
            "path": source_path,
            "purpose": "Executable cocotb extension semantic regression",
            "categories": ["operation", "protocol", "lifecycle"],
            "content": TB_PATH.read_text(encoding="utf-8"),
        }
    ]
    assert validate_verifier_extension_bundles(
        architecture, bundles, source_files=sources
    ) == []
    manifest = build_feature_extension_manifest(
        architecture, bundles, source_files=sources
    )
    assert len(manifest["entries"]) == 15


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")
def test_extension_tbs_run_against_real_reference_rtl(tmp_path: Path) -> None:
    result = run_cocotb_regression(
        rtl_dir=FIXTURE,
        top_module="extension_reference_dut",
        tests_dir=FIXTURE,
        reference_dir=FIXTURE,
        test_modules=["test_extension_reference_tb"],
        seed=20260921,
        build_dir=tmp_path / "build",
        report_path=tmp_path / "result.json",
        timeout_seconds=180,
    )
    assert result["status"] == "PASS", result
