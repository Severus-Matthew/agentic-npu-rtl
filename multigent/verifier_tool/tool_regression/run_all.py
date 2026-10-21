"""Run the complete verifier-tool regression from one stable entry point.

The default is intentionally the full queue: Python unit/integration tests,
non-HLS RTL fault/fix tests, one freshly generated HLS positive baseline, all
registered HLS RTL mutants, and all registered protocol-driver fault
injections. ``--quick`` runs only the simulator-free unit/integration portion
for normal edit/test cycles.

Results are written outside the repository by default.  Pass ``--output-dir``
only when a durable local report is wanted; generated RTL remains an output,
never a checked-in source fixture.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Sequence

from .paths import (
    API_EVALUATION_ROOT,
    EXTENSION_RTL_ROOT,
    EXTENSION_UNIT_ROOT,
    INTEGRATION_ROOT,
    REPOSITORY_ROOT,
    RTL_ROOT,
    UNIT_ROOT,
)


HLS_MODULE = (
    "multigent.verifier_tool.tool_regression.benchmarks."
    "int8_gemm_hls_golden"
)


def _run(command: Sequence[str]) -> None:
    print("+", " ".join(map(str, command)), flush=True)
    completed = subprocess.run(list(command), cwd=REPOSITORY_ROOT)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def _require_qualified(path: Path, *, label: str) -> dict:
    report = json.loads(path.read_text())
    if report.get("status") == "QUALIFIED":
        return report
    if report.get("requested") is not None:
        if (
            report.get("qualified") == report.get("requested")
            and report.get("unqualified") == 0
            and report.get("runner_errors") == 0
        ):
            return report
    raise SystemExit(f"{label} did not qualify: {path}")


def run(*, quick: bool, jobs: int, output_dir: Path | None) -> Path:
    if not 1 <= jobs <= 4:
        raise SystemExit("--jobs must be between 1 and 4 for the HLS benchmark")
    python = sys.executable
    pytest_command = [
        python,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        str(UNIT_ROOT),
        str(INTEGRATION_ROOT),
        str(EXTENSION_UNIT_ROOT),
        str(API_EVALUATION_ROOT),
        # API outputs deliberately contain generated test_*.py files. They are
        # evidence to inspect, never regression modules to collect again.
        "--ignore",
        str(API_EVALUATION_ROOT / "local_results"),
    ]
    if not quick:
        pytest_command.extend([
            str(RTL_ROOT),
            str(EXTENSION_RTL_ROOT),
            # The complete HLS baseline and every registered HLS mutation run
            # below. Avoid recompiling the older selected-subset wrappers here.
            "--ignore",
            str(RTL_ROOT / "test_int8_gemm_hls_golden.py"),
            "--ignore",
            str(RTL_ROOT / "test_int8_gemm_hls_mutations.py"),
        ])
    _run(pytest_command)

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="verifier_tool_regression_"))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "schema_version": 1,
        "mode": "quick" if quick else "full",
        "pytest": "PASS",
        "output_dir": str(output_dir.resolve()),
    }
    if quick:
        summary["status"] = "PASS"
        (output_dir / "run_all_summary.json").write_text(json.dumps(summary, indent=2))
        return output_dir

    baseline = output_dir / "hls_baseline"
    _run([python, "-m", f"{HLS_MODULE}.generated_mutation_qualification", str(baseline)])
    baseline_report = _require_qualified(
        baseline / "qualification.json", label="HLS baseline"
    )

    mutants = output_dir / "hls_named_mutants"
    _run([
        python,
        "-m",
        f"{HLS_MODULE}.batch_qualify_mutants",
        str(mutants),
        "--names",
        "all",
        "--baseline-dir",
        str(baseline / "original"),
        "--baseline-generated",
        str(baseline / "generated"),
        "--jobs",
        str(jobs),
    ])
    mutant_report = _require_qualified(
        mutants / "batch_qualification.json", label="HLS named mutants"
    )

    driver_faults = output_dir / "hls_driver_faults"
    _run([
        python,
        "-m",
        f"{HLS_MODULE}.batch_qualify_driver_faults",
        str(driver_faults),
        "--names",
        "all",
        "--baseline-dir",
        str(baseline / "original"),
        "--baseline-generated",
        str(baseline / "generated"),
        "--jobs",
        str(jobs),
    ])
    driver_report = _require_qualified(
        driver_faults / "batch_qualification.json", label="HLS driver faults"
    )

    summary.update({
        "status": "PASS",
        "hls_baseline": baseline_report.get("status"),
        "hls_named_mutants": {
            key: mutant_report.get(key)
            for key in ("requested", "qualified", "unqualified", "runner_errors")
        },
        "hls_driver_faults": {
            key: driver_report.get(key)
            for key in ("requested", "qualified", "unqualified", "runner_errors")
        },
    })
    (output_dir / "run_all_summary.json").write_text(json.dumps(summary, indent=2))
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run the simulator-free unit/integration regression only",
    )
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = run(quick=args.quick, jobs=args.jobs, output_dir=args.output_dir)
    print(f"verifier-tool regression PASS; report directory: {output}")


if __name__ == "__main__":
    main()
