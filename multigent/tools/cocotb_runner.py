"""Deterministic cocotb regression runner using Verilator.

The public ``run_cocotb_regression`` entry point executes a worker subprocess with a
wall-clock timeout. The worker uses cocotb 2.x's Python Runner API and writes a
machine-readable result consumed by LangGraph.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
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
    config = {
        "sources": [str(path) for path in sources],
        "top_module": top_module,
        "tests_dir": str(tests_dir),
        "reference_dir": str(reference_dir),
        "test_modules": test_modules,
        "seed": seed,
        "build_dir": str(build_dir),
        "results_xml": str(results_xml),
        "worker_result_path": str(worker_result_path),
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
        completed = subprocess.run(
            command,
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
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
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
        if "modulenotfounderror" in combined or "importerror" in combined or "syntaxerror" in combined:
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

    result["worker_return_code"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr
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

    pythonpath_parts = [str(tests_dir), str(reference_dir)]
    existing = os.environ.get("PYTHONPATH", "").strip()
    if existing:
        pythonpath_parts.append(existing)
    extra_env = {"PYTHONPATH": os.pathsep.join(pythonpath_parts)}

    runner = get_runner("verilator")
    try:
        runner.build(
            sources=[Path(str(item)) for item in config["sources"]],
            hdl_toplevel=top_module,
            build_dir=build_dir,
            always=True,
            clean=True,
            build_args=["-Wno-fatal"],
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
    except Exception as exc:
        text = f"{type(simulation_exception).__name__}: {simulation_exception}" if simulation_exception else ""
        lowered = text.lower()
        failure_class = (
            "TESTBENCH_ERROR"
            if any(token in lowered for token in ("modulenotfounderror", "importerror", "syntaxerror"))
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

    status = "PASS" if failures == 0 and simulation_exception is None else "SIMULATION_FAILURE"
    result = {
        "stage": "cocotb_regression",
        "status": status,
        "failure_class": None if status == "PASS" else "UNKNOWN",
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
    }
    _write_json(result_path, result)
    return result


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
