"""Run HLS AXI4 response-driver faults in bounded local parallel batches."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Any

from .qualify_driver_fault import DRIVER_FAULTS, driver_fault_plan, qualify_driver_fault
from .qualification_common import (
    cleanup_simulation_builds,
    compact_completed_qualification,
    load_completed_qualification,
    reset_qualification_workspace,
)


def validate_registry(names: list[str]) -> list[dict[str, Any]]:
    result = []
    for name in names:
        try:
            plan, diagnostic = driver_fault_plan(name)
        except (ValueError, TypeError) as exc:
            result.append({"name": name, "status": "INVALID", "error": str(exc)})
        else:
            result.append({
                "name": name,
                "status": "READY",
                "fault_plan": plan,
                "expected_diagnostic": diagnostic,
            })
    return result


def _run_one(name: str, case_dir_raw: str, baseline_dir: str, baseline_generated: str) -> dict[str, Any]:
    case_dir = Path(case_dir_raw)
    try:
        result = qualify_driver_fault(
            name,
            case_dir,
            baseline_dir=Path(baseline_dir),
            baseline_generated=Path(baseline_generated),
        )
        compact_completed_qualification(case_dir)
        return result
    except Exception as exc:
        return {
            "name": name,
            "status": "RUNNER_ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        cleanup_simulation_builds(case_dir)


def run_batch(
    names: list[str],
    output_root: Path,
    *,
    baseline_dir: Path,
    baseline_generated: Path,
    jobs: int = 2,
) -> dict[str, Any]:
    if not 1 <= jobs <= 4:
        raise ValueError("jobs must be between 1 and 4 for this HLS benchmark")
    invalid = [item for item in validate_registry(names) if item["status"] != "READY"]
    if invalid:
        raise ValueError(f"driver-fault registry validation failed: {invalid!r}")
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    pending: list[tuple[str, Path]] = []
    for name in names:
        case_dir = output_root / name
        completed = load_completed_qualification(
            case_dir / "qualification.json",
            baseline_generated=baseline_generated,
        )
        if completed is not None:
            results.append(completed)
            compact_completed_qualification(case_dir)
            print(f"{name}: QUALIFIED (resumed)", flush=True)
        else:
            reset_qualification_workspace(case_dir)
            pending.append((name, case_dir))
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(
                _run_one, name, str(case_dir), str(baseline_dir), str(baseline_generated)
            ): name
            for name, case_dir in pending
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result.get('name')}: {result.get('status')}", flush=True)
    results.sort(key=lambda item: str(item.get("name", "")))
    summary = {
        "schema_version": 1,
        "baseline_dir": str(baseline_dir),
        "baseline_generated": str(baseline_generated),
        "jobs": jobs,
        "requested": len(names),
        "resumed": len(names) - len(pending),
        "qualified": sum(item.get("status") == "QUALIFIED" for item in results),
        "unqualified": sum(item.get("status") == "UNQUALIFIED" for item in results),
        "runner_errors": sum(item.get("status") == "RUNNER_ERROR" for item in results),
        "results": results,
    }
    (output_root / "batch_qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


def _names(raw: list[str] | None) -> list[str]:
    if not raw or raw == ["all"]:
        return sorted(DRIVER_FAULTS)
    result: list[str] = []
    for value in raw:
        result.extend(item for item in value.split(",") if item)
    return list(dict.fromkeys(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path, nargs="?")
    parser.add_argument("--names", nargs="+")
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--baseline-generated", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    selected = _names(args.names)
    if args.list:
        print(json.dumps(validate_registry(selected), indent=2))
    else:
        if args.output_root is None or args.baseline_dir is None or args.baseline_generated is None:
            parser.error("output_root, --baseline-dir, and --baseline-generated are required")
        print(json.dumps(run_batch(
            selected,
            args.output_root,
            baseline_dir=args.baseline_dir,
            baseline_generated=args.baseline_generated,
            jobs=args.jobs,
        ), indent=2))
