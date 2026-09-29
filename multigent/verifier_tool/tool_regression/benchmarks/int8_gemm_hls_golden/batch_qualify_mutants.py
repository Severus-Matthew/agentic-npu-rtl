"""Run prepared HLS benchmark mutants in bounded local parallel batches.

The runner never changes ``gemm_golden`` and never calls an agent or external
API.  Each worker delegates to :mod:`qualify_named_mutant`, which verifies the
saved positive baseline, regenerates the normal deterministic TB, copies the
RTL, applies one exact mutation, and requires the intended diagnostic.

Verilator builds for this design are memory intensive.  The CLI deliberately
caps parallelism at four and defaults to two workers.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Any, Iterable

from .qualify_named_mutant import MUTANTS, RTL_DIR, mutant_definition, qualify_named_mutant
from .qualification_common import (
    cleanup_simulation_builds,
    compact_completed_qualification,
    load_completed_qualification,
    reset_qualification_workspace,
)


def validate_registry(names: Iterable[str]) -> list[dict[str, Any]]:
    """Validate every selected exact substitution without editing any RTL."""

    findings: list[dict[str, Any]] = []
    for name in names:
        if name not in MUTANTS:
            findings.append({"name": name, "status": "UNKNOWN_MUTANT"})
            continue
        edits, diagnostic = mutant_definition(MUTANTS[name])
        checked_edits: list[dict[str, Any]] = []
        ready = bool(diagnostic)
        for file_name, anchor, replacement, expected_count in edits:
            path = RTL_DIR / file_name
            count = path.read_text().count(anchor) if path.is_file() else 0
            edit_ready = count == expected_count and anchor != replacement
            ready = ready and edit_ready
            checked_edits.append({
                "rtl_file": file_name,
                "anchor_count": count,
                "expected_anchor_count": expected_count,
                "status": "READY" if edit_ready else "INVALID",
            })
        status = "READY" if ready else "INVALID"
        findings.append({
            "name": name,
            "status": status,
            "edits": checked_edits,
            "expected_diagnostic": diagnostic,
        })
    return findings


def _run_one(
    name: str,
    case_dir_raw: str,
    baseline_dir: str,
    baseline_generated: str,
) -> dict[str, Any]:
    case_dir = Path(case_dir_raw)
    try:
        result = qualify_named_mutant(
            name,
            case_dir,
            baseline_dir=Path(baseline_dir),
            baseline_generated=Path(baseline_generated),
        )
        compact_completed_qualification(case_dir)
        return result
    except Exception as exc:  # Persist a batch result even if one worker breaks.
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
    """Run selected mutants and write one resumable batch summary."""

    if not 1 <= jobs <= 4:
        raise ValueError("jobs must be between 1 and 4 for this HLS benchmark")
    registry = validate_registry(names)
    invalid = [item for item in registry if item["status"] != "READY"]
    if invalid:
        raise ValueError(f"mutant registry validation failed: {invalid!r}")

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
                _run_one,
                name,
                str(case_dir),
                str(baseline_dir),
                str(baseline_generated),
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


def _parse_names(raw_names: list[str] | None) -> list[str]:
    if not raw_names or raw_names == ["all"]:
        return sorted(MUTANTS)
    names: list[str] = []
    for raw in raw_names:
        names.extend(item for item in raw.split(",") if item)
    return list(dict.fromkeys(names))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path, nargs="?")
    parser.add_argument("--names", nargs="+", help="mutant names, comma lists, or 'all'")
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--baseline-generated", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--list", action="store_true", help="validate and list without simulation")
    args = parser.parse_args()
    selected = _parse_names(args.names)
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
