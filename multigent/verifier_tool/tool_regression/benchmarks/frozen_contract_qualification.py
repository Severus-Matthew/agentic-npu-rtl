"""Run one API-free frozen-contract fault/fix qualification.

This executes the normal benchmark-generated TB, never a hand-authored test.
The caller supplies immutable contract files and the previous/corrected RTL
directories. A semantic-stage RTL may be supplied when the previous RTL lacks
a newly introduced port or serialization format and therefore cannot reach
the mathematical checker.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
from difflib import unified_diff
import io
import json
from pathlib import Path
from typing import Any

import yaml

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import review_contract_deterministically
from multigent.verifier_tool.tool_regression.benchmarks.u55c_inspired_int8_gemm_4x4x4 import (
    build_contract_and_tb as builder,
)


CONTRACT_FILES = (
    "architecture_contract.yaml",
    "interface_contract.yaml",
    "module_manifest.json",
    "acceptance_criteria.yaml",
)


def _load_contracts(directory: Path) -> tuple[dict, dict, dict, dict]:
    values = []
    for name in CONTRACT_FILES:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"missing frozen contract file: {path}")
        values.append(json.loads(path.read_text()) if path.suffix == ".json" else yaml.safe_load(path.read_text()))
    return tuple(values)  # type: ignore[return-value]


def _contract_diff(previous: Path, changed: Path) -> str:
    chunks = []
    for name in CONTRACT_FILES:
        old, new = previous / name, changed / name
        chunks.extend(unified_diff(
            old.read_text().splitlines(keepends=True),
            new.read_text().splitlines(keepends=True),
            fromfile=str(old), tofile=str(new),
        ))
    return "".join(chunks)


def _rtl_diff(previous: Path, changed: Path) -> str:
    extensions = {".v", ".sv", ".vh", ".svh"}
    old_files = {
        path.relative_to(previous): path for path in previous.rglob("*")
        if path.is_file() and path.suffix in extensions
    }
    new_files = {
        path.relative_to(changed): path for path in changed.rglob("*")
        if path.is_file() and path.suffix in extensions
    }
    chunks = []
    for name in sorted(old_files.keys() | new_files.keys()):
        old, new = old_files.get(name), new_files.get(name)
        chunks.extend(unified_diff(
            old.read_text().splitlines(keepends=True) if old else [],
            new.read_text().splitlines(keepends=True) if new else [],
            fromfile=str(old or "/dev/null"), tofile=str(new or "/dev/null"),
        ))
    return "".join(chunks)


def _run_rtl(
    rtl_dir: Path, generated: Path, result_dir: Path, *, seed: int
) -> dict[str, Any]:
    result_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = result_dir / "functional_coverage_report.json"
    ledger_path = result_dir / "stimulus_ledger.json"
    simulation = run_cocotb_regression(
        rtl_dir=rtl_dir,
        top_module="u55c_inspired_int8_gemm_4x4x4_top",
        tests_dir=generated,
        reference_dir=Path.cwd(),
        test_modules=["test_gemm_automatic"],
        seed=seed,
        build_dir=result_dir / "build",
        report_path=result_dir / "simulation_report.json",
        timeout_seconds=120,
        coverage_plan=json.loads((generated / "functional_coverage_plan.json").read_text()),
        coverage_report_path=coverage_path,
        stimulus_ledger_report_path=ledger_path,
    )
    coverage = json.loads(coverage_path.read_text()) if coverage_path.is_file() else {}
    ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {}
    return {
        "rtl_dir": str(rtl_dir.resolve()),
        "status": simulation.get("status"),
        "failure_class": simulation.get("failure_class"),
        "stdout": str(simulation.get("stdout", "")),
        "coverage": {
            key: coverage.get(key)
            for key in ("status", "hit_bins", "required_bins", "missing_bins", "assertion_failures")
        },
        "stimulus": {
            key: ledger.get(key)
            for key in ("status", "stimulus_count", "directed_stimuli", "randomized_stimuli")
        },
        "report_dir": str(result_dir.resolve()),
    }


def qualify_frozen_contract(
    frozen_contract_dir: Path,
    previous_rtl_dir: Path,
    corrected_rtl_dir: Path,
    output_dir: Path,
    *,
    expected_previous_failure: str | None = None,
    expected_previous_missing_bin: str | None = None,
    expected_previous_missing_bins: tuple[str, ...] | None = None,
    previous_contract_dir: Path | None = None,
    semantic_stage_rtl_dir: Path | None = None,
    expected_semantic_failure: str | None = None,
    expected_semantic_missing_bins: tuple[str, ...] | None = None,
    seed: int = 41,
) -> dict[str, Any]:
    """Require precise old-RTL failure and complete corrected-RTL closure."""

    if bool(semantic_stage_rtl_dir) != bool(
        expected_semantic_failure or expected_semantic_missing_bins
    ) or (expected_semantic_failure and expected_semantic_missing_bins):
        raise ValueError(
            "semantic-stage RTL requires exactly one expected failure or missing-bin set"
        )
    if sum(bool(item) for item in (
        expected_previous_failure,
        expected_previous_missing_bin,
        expected_previous_missing_bins,
    )) != 1:
        raise ValueError("select exactly one assertion/golden failure or missing-bin set")
    contracts = _load_contracts(frozen_contract_dir)
    preflight = review_contract_deterministically(*contracts)
    if preflight.get("status") != "PASS":
        raise AssertionError(f"frozen contract preflight failed: {preflight['findings']!r}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "preflight.json").write_text(json.dumps(preflight, indent=2))
    if previous_contract_dir is not None:
        (output_dir / "contract.diff").write_text(
            _contract_diff(previous_contract_dir, frozen_contract_dir)
        )
    rtl_changes = _rtl_diff(previous_rtl_dir, corrected_rtl_dir)
    if not rtl_changes:
        raise AssertionError("previous and corrected RTL are textually identical")
    (output_dir / "rtl.diff").write_text(rtl_changes)
    generated = output_dir / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    original_build, original_out = builder.build_architecture_contract, builder.OUT
    builder.build_architecture_contract = lambda: deepcopy(contracts)
    builder.OUT = generated
    try:
        with redirect_stdout(io.StringIO()) as log:
            builder.main()
        (output_dir / "generation.log").write_text(log.getvalue())
    finally:
        builder.build_architecture_contract, builder.OUT = original_build, original_out
    if not (generated / "test_gemm_automatic.py").is_file():
        raise AssertionError("normal generated TB was not emitted")

    previous = _run_rtl(previous_rtl_dir, generated, output_dir / "previous", seed=seed)
    expected_missing = (
        list(expected_previous_missing_bins)
        if expected_previous_missing_bins else
        [expected_previous_missing_bin] if expected_previous_missing_bin else None
    )
    if expected_missing:
        missing = previous["coverage"].get("missing_bins")
        if (
            previous["status"] != "COVERAGE_FAILURE"
            or previous["failure_class"] != "COVERAGE_MISS"
            or sorted(missing or []) != sorted(expected_missing)
            or previous["coverage"].get("assertion_failures")
        ):
            raise AssertionError(
                "previous RTL did not miss exactly the specified coverage bins: "
                f"status={previous['status']}; missing={missing!r}; "
                f"expected={expected_missing!r}; report={previous['report_dir']}"
            )
    elif previous["status"] == "PASS" or expected_previous_failure not in previous["stdout"]:
        raise AssertionError(
            "previous RTL did not fail for the specified reason: "
            f"status={previous['status']}; expected={expected_previous_failure!r}; "
            f"report={previous['report_dir']}"
        )
    semantic_stage = None
    if semantic_stage_rtl_dir is not None:
        semantic_stage = _run_rtl(
            semantic_stage_rtl_dir, generated, output_dir / "semantic_stage", seed=seed
        )
        if expected_semantic_missing_bins:
            semantic_coverage = semantic_stage["coverage"]
            valid_semantic_miss = (
                semantic_stage["status"] == "COVERAGE_FAILURE"
                and semantic_stage["failure_class"] == "COVERAGE_MISS"
                and sorted(semantic_coverage.get("missing_bins") or [])
                == sorted(expected_semantic_missing_bins)
                and not semantic_coverage.get("assertion_failures")
            )
        else:
            valid_semantic_miss = (
                semantic_stage["status"] != "PASS"
                and expected_semantic_failure in semantic_stage["stdout"]
            )
        if not valid_semantic_miss:
            raise AssertionError(
                "semantic-stage RTL did not fail for the specified reason: "
                f"status={semantic_stage['status']}; "
                f"expected_failure={expected_semantic_failure!r}; "
                f"expected_missing_bins={expected_semantic_missing_bins!r}; "
                f"report={semantic_stage['report_dir']}"
            )
    corrected = _run_rtl(corrected_rtl_dir, generated, output_dir / "corrected", seed=seed)
    coverage, stimulus = corrected["coverage"], corrected["stimulus"]
    complete = (
        corrected["status"] == "PASS"
        and coverage.get("status") == "PASS"
        and isinstance(coverage.get("required_bins"), int)
        and coverage.get("hit_bins") == coverage.get("required_bins")
        and not coverage.get("missing_bins")
        and not coverage.get("assertion_failures")
        and stimulus.get("status") == "PASS"
        and isinstance(stimulus.get("stimulus_count"), int)
        and stimulus["stimulus_count"] > 0
    )
    summary = {
        "status": "PASS" if complete else "FAIL",
        "frozen_contract_dir": str(frozen_contract_dir.resolve()),
        "previous_contract_dir": str(previous_contract_dir.resolve()) if previous_contract_dir else None,
        "expected_previous_failure": expected_previous_failure,
        "expected_previous_missing_bin": expected_previous_missing_bin,
        "expected_previous_missing_bins": list(expected_previous_missing_bins or ()),
        "expected_semantic_failure": expected_semantic_failure,
        "expected_semantic_missing_bins": list(expected_semantic_missing_bins or ()),
        "previous": {key: value for key, value in previous.items() if key != "stdout"},
        "semantic_stage": (
            {key: value for key, value in semantic_stage.items() if key != "stdout"}
            if semantic_stage else None
        ),
        "corrected": {key: value for key, value in corrected.items() if key != "stdout"},
    }
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    if not complete:
        raise AssertionError(f"corrected RTL did not close all bins/checks: {summary!r}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen_contract_dir", type=Path)
    parser.add_argument("previous_rtl_dir", type=Path)
    parser.add_argument("corrected_rtl_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--previous-contract-dir", type=Path)
    previous_expectation = parser.add_mutually_exclusive_group(required=True)
    previous_expectation.add_argument("--expected-previous-failure")
    previous_expectation.add_argument("--expected-previous-missing-bin")
    previous_expectation.add_argument("--expected-previous-missing-bins", nargs="+")
    parser.add_argument("--semantic-stage-rtl-dir", type=Path)
    semantic_expectation = parser.add_mutually_exclusive_group()
    semantic_expectation.add_argument("--expected-semantic-failure")
    semantic_expectation.add_argument("--expected-semantic-missing-bins", nargs="+")
    args = parser.parse_args()
    result = qualify_frozen_contract(
        args.frozen_contract_dir,
        args.previous_rtl_dir,
        args.corrected_rtl_dir,
        args.output_dir,
        expected_previous_failure=args.expected_previous_failure,
        expected_previous_missing_bin=args.expected_previous_missing_bin,
        expected_previous_missing_bins=(
            tuple(args.expected_previous_missing_bins)
            if args.expected_previous_missing_bins else None
        ),
        previous_contract_dir=args.previous_contract_dir,
        semantic_stage_rtl_dir=args.semantic_stage_rtl_dir,
        expected_semantic_failure=args.expected_semantic_failure,
        expected_semantic_missing_bins=tuple(args.expected_semantic_missing_bins or ()),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
