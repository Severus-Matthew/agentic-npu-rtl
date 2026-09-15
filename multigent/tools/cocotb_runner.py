"""Deterministic cocotb regression runner using Verilator.

The public ``run_cocotb_regression`` entry point executes a worker subprocess with a
wall-clock timeout. The worker uses cocotb 2.x's Python Runner API and writes a
machine-readable result consumed by LangGraph.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import xml.etree.ElementTree as ET
import shutil
import subprocess
from multigent.tools.process import run_process
import sys
from pathlib import Path
from typing import Any, Mapping


def run_cocotb_regression(
    *,
    rtl_dir: Path,
    top_module: str,
    tests_dir: Path,
    reference_dir: Path,
    test_modules: list[str],
    seed: int,
    build_dir: Path,
    report_path: Path,
    timeout_seconds: int,
    public_signals: bool = False,
    coverage_plan: Mapping[str, Any] | None = None,
    coverage_report_path: Path | None = None,
    stimulus_ledger_report_path: Path | None = None,
) -> dict[str, Any]:
    """Build and run cocotb tests in a bounded worker subprocess."""

    rtl_dir = rtl_dir.resolve()
    tests_dir = tests_dir.resolve()
    reference_dir = reference_dir.resolve()
    build_dir = build_dir.resolve()
    report_path = report_path.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    sources = sorted(rtl_dir.rglob("*.sv"))
    if not sources:
        raise FileNotFoundError(f"No SystemVerilog sources found under {rtl_dir}")
    if not test_modules:
        raise ValueError("At least one cocotb test module is required")

    if shutil.which("verilator") is None:
        result = {
            "stage": "cocotb_regression",
            "status": "TOOL_UNAVAILABLE",
            "failure_class": None,
            "tests": 0,
            "failures": 0,
            "seed": seed,
            "top_module": top_module,
            "test_modules": test_modules,
            "results_xml": None,
            "stdout": "",
            "stderr": "verilator executable not found on PATH",
        }
        _write_json(report_path, result)
        return result

    config_path = build_dir / "cocotb_worker_config.json"
    worker_result_path = build_dir / "cocotb_worker_result.json"
    results_xml = build_dir / "results.xml"
    coverage_config_path = build_dir / "functional_coverage_config.json"
    if coverage_plan is not None:
        if coverage_report_path is None:
            raise ValueError("coverage_report_path is required with coverage_plan")
        coverage_report_path = coverage_report_path.resolve()
        _write_json(coverage_config_path, coverage_plan)
        if coverage_report_path.exists():
            coverage_report_path.unlink()
    if stimulus_ledger_report_path is not None:
        stimulus_ledger_report_path = stimulus_ledger_report_path.resolve()
        if stimulus_ledger_report_path.exists():
            stimulus_ledger_report_path.unlink()
    config = {
        "public_signals": public_signals,
        "sources": [str(path) for path in sources],
        "top_module": top_module,
        "tests_dir": str(tests_dir),
        "reference_dir": str(reference_dir),
        "test_modules": test_modules,
        "seed": seed,
        "build_dir": str(build_dir),
        "results_xml": str(results_xml),
        "worker_result_path": str(worker_result_path),
        "coverage_config_path": (
            str(coverage_config_path) if coverage_plan is not None else None
        ),
        "coverage_plan": dict(coverage_plan) if coverage_plan is not None else None,
        "coverage_report_path": (
            str(coverage_report_path) if coverage_report_path is not None else None
        ),
        "stimulus_ledger_report_path": (
            str(stimulus_ledger_report_path)
            if stimulus_ledger_report_path is not None
            else None
        ),
    }
    _write_json(config_path, config)
    if worker_result_path.exists():
        worker_result_path.unlink()
    if results_xml.exists():
        results_xml.unlink()

    command = [
        sys.executable,
        "-m",
        "multigent.tools.cocotb_runner",
        "--worker-config",
        str(config_path),
    ]
    try:
        completed = run_process(
            command,
            # The caller may import this variant by sys.path from a comparison
            # directory. That in-process path is not inherited by a new Python
            # worker; resolve the loaded package's root, not the caller's cwd.
            cwd=str(Path(__file__).resolve().parents[2]),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result = {
            "stage": "cocotb_regression",
            "status": "TIMEOUT",
            "failure_class": "SIMULATION_TIMEOUT",
            "tests": 0,
            "failures": 0,
            "seed": seed,
            "top_module": top_module,
            "test_modules": test_modules,
            "results_xml": str(results_xml),
            "stdout": exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            "stderr": exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
        }
        _write_json(report_path, result)
        return result

    if worker_result_path.is_file():
        worker = json.loads(worker_result_path.read_text(encoding="utf-8"))
        if not isinstance(worker, dict):
            raise RuntimeError("cocotb worker result is not a JSON object")
        result = dict(worker)
    else:
        combined = f"{completed.stdout}\n{completed.stderr}".lower()
        if (
            "modulenotfounderror" in combined
            or "importerror" in combined
            or "syntaxerror" in combined
        ):
            failure_class = "TESTBENCH_ERROR"
        else:
            failure_class = "UNKNOWN"
        result = {
            "stage": "cocotb_regression",
            "status": "SIMULATION_FAILURE",
            "failure_class": failure_class,
            "tests": 0,
            "failures": 0,
            "seed": seed,
            "top_module": top_module,
            "test_modules": test_modules,
            "results_xml": str(results_xml),
        }

    if completed.returncode != 0 and result.get("status") == "PASS":
        result.update(status="SIMULATION_FAILURE", failure_class="UNKNOWN")
    build_log = completed.stdout + "\n" + completed.stderr
    if result.get("status") == "SIMULATION_BUILD_FAILURE" and any(token in build_log for token in ("command not found", "No such file or directory", "SRE module mismatch")):
        result.update(status="TOOL_UNAVAILABLE", failure_class=None)
    result["worker_return_code"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr
    if stimulus_ledger_report_path is not None:
        result["stimulus_ledger"] = _finalize_stimulus_ledger(
            stimulus_ledger_report_path,
            status=str(result.get("status", "UNKNOWN")),
            seed=seed,
            top_module=top_module,
            test_modules=test_modules,
        )
    _write_json(report_path, result)
    return result


def _worker(config: Mapping[str, Any]) -> dict[str, Any]:
    """Execute cocotb runner in the isolated worker process."""

    result_path = Path(str(config["worker_result_path"]))
    results_xml = Path(str(config["results_xml"]))
    build_dir = Path(str(config["build_dir"]))
    tests_dir = Path(str(config["tests_dir"]))
    reference_dir = Path(str(config["reference_dir"]))
    test_modules = [str(item) for item in config["test_modules"]]
    top_module = str(config["top_module"])
    seed = int(config["seed"])

    try:
        from cocotb_tools.check_results import get_results
        from cocotb_tools.runner import get_runner
    except ImportError as exc:
        result = {
            "stage": "cocotb_regression",
            "status": "TOOL_UNAVAILABLE",
            "failure_class": None,
            "tests": 0,
            "failures": 0,
            "seed": seed,
            "top_module": top_module,
            "test_modules": test_modules,
            "results_xml": str(results_xml),
            "worker_error": f"cocotb import failed: {exc}",
        }
        _write_json(result_path, result)
        return result

    workspace_root = reference_dir.parent
    pythonpath_parts = [
        str(tests_dir),
        str(reference_dir),
        str(workspace_root),
    ]
    existing = os.environ.get("PYTHONPATH", "").strip()
    if existing:
        pythonpath_parts.append(existing)
    # cocotb 2.x overwrites extra_env[PYTHONPATH] with sys.path.
    # Set the worker's actual import path so both flat and reference.* imports work.
    sys.path[:0] = [str(tests_dir), str(reference_dir), str(workspace_root)]
    extra_env = {"PYTHONPATH": os.pathsep.join(pythonpath_parts)}
    coverage_config = config.get("coverage_config_path")
    coverage_report = config.get("coverage_report_path")
    stimulus_ledger_report = config.get("stimulus_ledger_report_path")
    if coverage_config and coverage_report:
        extra_env["NPU_FUNCTIONAL_COVERAGE_CONFIG"] = str(coverage_config)
        extra_env["NPU_FUNCTIONAL_COVERAGE_REPORT"] = str(coverage_report)
        if stimulus_ledger_report:
            extra_env["NPU_STIMULUS_LEDGER_REPORT"] = str(
                stimulus_ledger_report
            )

    for key in ("COCOTB_TEST_FILTER", "COCOTB_TESTCASE", "TESTCASE", "COCOTB_TEST_MODULES"):
        os.environ.pop(key, None)
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    runner = get_runner("verilator")
    try:
        runner.build(
            sources=[Path(str(item)) for item in config["sources"]],
            hdl_toplevel=top_module,
            build_dir=build_dir,
            always=True,
            clean=True,
            build_args=["-Wno-fatal"] + (["--public-flat-rw"] if config.get("public_signals") else []),
        )
    except BaseException as exc:
        result = {
            "stage": "cocotb_regression",
            "status": "SIMULATION_BUILD_FAILURE",
            "failure_class": "ELABORATION_ERROR",
            "tests": 0,
            "failures": 0,
            "seed": seed,
            "top_module": top_module,
            "test_modules": test_modules,
            "results_xml": str(results_xml),
            "worker_error": f"{type(exc).__name__}: {exc}",
        }
        _write_json(result_path, result)
        return result

    if coverage_config and config.get("coverage_plan") is not None:
        _write_json(Path(str(coverage_config)), config["coverage_plan"])

    simulation_exception: BaseException | None = None
    try:
        runner.test(
            test_module=test_modules,
            hdl_toplevel=top_module,
            build_dir=build_dir,
            test_dir=tests_dir,
            results_xml=str(results_xml),
            seed=seed,
            extra_env=extra_env,
        )
    except BaseException as exc:
        simulation_exception = exc

    try:
        tests, failures = get_results(results_xml)
        expected_count = 0
        for module in test_modules:
            tree = ast.parse((tests_dir/(module + ".py")).read_text())
            expected_count += sum(1 for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
                                  and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                                          and d.func.attr == "test" for d in node.decorator_list))
    except Exception as exc:
        text = (
            f"{type(simulation_exception).__name__}: {simulation_exception}"
            if simulation_exception
            else ""
        )
        lowered = text.lower()
        failure_class = (
            "TESTBENCH_ERROR"
            if any(
                token in lowered
                for token in ("modulenotfounderror", "importerror", "syntaxerror")
            )
            else "UNKNOWN"
        )
        result = {
            "stage": "cocotb_regression",
            "status": "SIMULATION_FAILURE",
            "failure_class": failure_class,
            "tests": 0,
            "failures": 0,
            "seed": seed,
            "top_module": top_module,
            "test_modules": test_modules,
            "results_xml": str(results_xml),
            "worker_error": f"results unavailable: {exc}; simulation={text}",
        }
        _write_json(result_path, result)
        return result

    coverage = evaluate_functional_coverage_report(
        Path(str(coverage_report)) if coverage_report else None,
        Path(str(coverage_config)) if coverage_config else None,
    )
    simulation_pass = (
        "PASS"
        if tests >= max(1, expected_count) and failures == 0 and simulation_exception is None and xunit_complete(results_xml)
        else "SIMULATION_FAILURE"
    )
    status = (
        "COVERAGE_FAILURE"
        if (
            simulation_pass == "PASS"
            and coverage_config
            and coverage_report
            and coverage.get("status") != "PASS"
        )
        else simulation_pass
    )
    result = {
        "stage": "cocotb_regression",
        "status": status,
        "failure_class": (
            None
            if status == "PASS"
            else "COVERAGE_MISS"
            if status == "COVERAGE_FAILURE"
            else "UNKNOWN"
        ),
        "tests": tests,
        "failures": failures,
        "seed": seed,
        "top_module": top_module,
        "test_modules": test_modules,
        "results_xml": str(results_xml),
        "worker_error": (
            None
            if simulation_exception is None
            else f"{type(simulation_exception).__name__}: {simulation_exception}"
        ),
        "functional_coverage": coverage,
    }
    _write_json(result_path, result)
    return result


def xunit_complete(path: Path) -> bool:
    """Reject vacuous passes, skipped cases, errors and malformed result files."""
    try:
        cases = ET.parse(path).getroot().findall('.//testcase')
        return bool(cases) and all(not any(c.find(tag) is not None for tag in ('skipped','failure','error')) for c in cases)
    except (ET.ParseError, OSError):
        return False


def evaluate_functional_coverage_report(
    report_path: Path | None, config_path: Path | None
) -> dict[str, Any]:
    """Recompute closure from runner-owned plan and monitor-produced hit counts."""

    if report_path is None or config_path is None:
        return {
            "status": "NOT_CONFIGURED",
            "missing_bins": [],
            "covered_bins": [],
            "bin_hits": {},
        }
    if not report_path.is_file():
        return {
            "status": "FAIL",
            "coverage_percent": 0.0,
            "missing_bins": ["runtime_report_missing"],
            "covered_bins": [],
            "bin_hits": {},
            "report_path": str(report_path),
        }
    try:
        plan = json.loads(config_path.read_text(encoding="utf-8"))
        raw = json.loads(report_path.read_text(encoding="utf-8"))
        observed = {
            str(obligation["id"]): {
                str(item["name"]): int(item["hits"])
                for item in obligation.get("bins", [])
            }
            for obligation in raw.get("obligations", [])
        }
        missing: list[str] = []
        covered: list[str] = []
        bin_hits: dict[str, int] = {}
        hit_bins = 0
        total_bins = 0
        for obligation in plan.get("obligations", []):
            obligation_id = str(obligation["id"])
            for item in obligation.get("bins", []):
                required = bool(item.get("required", True))
                bin_name = str(item["name"])
                count = observed.get(obligation_id, {}).get(bin_name, 0)
                bin_id = f"{obligation_id}.{bin_name}"
                bin_hits[bin_id] = count
                if count > 0:
                    covered.append(bin_id)
                if required:
                    total_bins += 1
                    hit_bins += int(count > 0)
                if required and count == 0:
                    missing.append(bin_id)
        assertion_failures = list(map(str, raw.get("assertion_failures", [])))
        minimum_randomized = int(
            plan.get("requirements", {}).get("randomized_transactions_minimum", 0)
        )
        randomized_samples = int(raw.get("randomized_operation_samples", 0))
        ledger_enabled = bool(raw.get("stimulus_ledger_enabled", False))
        randomized_transactions = int(
            raw.get("randomized_stimuli", 0)
            if ledger_enabled
            else randomized_samples
        )
        if randomized_transactions < minimum_randomized:
            missing.append(
                f"runtime.randomized_transactions.minimum_{minimum_randomized}"
            )
        return {
            "status": "PASS" if not missing and not assertion_failures else "FAIL",
            "samples": int(raw.get("samples", 0)),
            "operation_samples": int(raw.get("operation_samples", 0)),
            "directed_operation_samples": int(
                raw.get("directed_operation_samples", 0)
            ),
            "randomized_operation_samples": randomized_samples,
            "stimulus_count": int(raw.get("stimulus_count", 0)),
            "directed_stimuli": int(raw.get("directed_stimuli", 0)),
            "randomized_stimuli": int(raw.get("randomized_stimuli", 0)),
            "randomized_transactions_observed": randomized_transactions,
            "stimulus_ledger_enabled": ledger_enabled,
            "randomized_transactions_minimum": minimum_randomized,
            "coverage_engine": str(raw.get("coverage_engine", "")),
            "required_bins": total_bins,
            "hit_bins": hit_bins,
            "coverage_percent": (
                100.0 if not total_bins else 100.0 * hit_bins / total_bins
            ),
            "missing_bins": missing,
            "covered_bins": sorted(covered),
            "bin_hits": dict(sorted(bin_hits.items())),
            "assertion_failures": assertion_failures,
            "failure_records": list(raw.get("failure_records", [])),
            "last_observed_snapshot": dict(
                raw.get("last_observed_snapshot", {})
                if isinstance(raw.get("last_observed_snapshot", {}), Mapping)
                else {}
            ),
            "operation_sampling": list(raw.get("operation_sampling", [])),
            "report_path": str(report_path),
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {
            "status": "FAIL",
            "coverage_percent": 0.0,
            "missing_bins": ["invalid_runtime_report"],
            "covered_bins": [],
            "bin_hits": {},
            "error": f"{type(exc).__name__}: {exc}",
            "report_path": str(report_path),
        }


def _finalize_stimulus_ledger(
    path: Path,
    *,
    status: str,
    seed: int,
    top_module: str,
    test_modules: list[str],
) -> dict[str, Any]:
    """Attach reproducibility metadata and return a compact result summary."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        raw = {}
    records = raw.get("records", [])
    if not isinstance(records, list):
        records = []
    ledger = {
        "schema_version": 1,
        "status": status,
        "seed": seed,
        "top_module": top_module,
        "test_modules": list(test_modules),
        "stimulus_count": len(records),
        "directed_stimuli": sum(
            1 for item in records if isinstance(item, Mapping) and item.get("kind") == "directed"
        ),
        "randomized_stimuli": sum(
            1 for item in records if isinstance(item, Mapping) and item.get("kind") == "randomized"
        ),
        "records": records,
    }
    _write_json(path, ledger)
    return {
        "path": str(path),
        "status": status,
        "stimulus_count": ledger["stimulus_count"],
        "directed_stimuli": ledger["directed_stimuli"],
        "randomized_stimuli": ledger["randomized_stimuli"],
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="cocotb deterministic worker")
    parser.add_argument("--worker-config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.worker_config.read_text(encoding="utf-8"))
    result = _worker(config)
    if result["status"] not in {"PASS", "TOOL_UNAVAILABLE"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
