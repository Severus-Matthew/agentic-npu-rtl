"""Shared positive-pair validation for HLS benchmark qualification runners."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


GENERATED_ARTIFACTS = (
    "test_gemm_automatic.py",
    "functional_coverage_plan.json",
)

QUALIFICATION_TRANSIENT_DIRS = (
    "generated",
    "mutated_rtl",
    "mutant",
    "scenario_rtl",
    "fault",
    "scenario_positive",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnostic_excerpt(output: str, diagnostic: str, *, context: int = 240) -> str | None:
    """Return compact case-preserving evidence around a matched diagnostic."""

    index = output.lower().find(diagnostic.lower())
    if index < 0:
        return None
    start = max(0, index - context)
    end = min(len(output), index + len(diagnostic) + context)
    return output[start:end]


def materialize_baseline_generated_pair(
    baseline_generated: Path,
    generated: Path,
) -> None:
    """Copy the already-qualified generated TB/plan into one mutant run.

    A mutation campaign must exercise the exact generated pair that passed on
    the original RTL.  Regenerating per mutant is both unnecessary and unsafe:
    it can accidentally compare a mutant against a different witness plan.
    """

    if generated.exists():
        raise FileExistsError(f"mutant generated directory already exists: {generated}")
    generated.mkdir(parents=True)
    for filename in GENERATED_ARTIFACTS:
        source = baseline_generated / filename
        if not source.is_file():
            raise FileNotFoundError(f"baseline generated artifact is missing: {source}")
        shutil.copy2(source, generated / filename)


def validate_positive_baseline(
    baseline_dir: Path,
    baseline_generated: Path,
    generated: Path,
) -> dict[str, Any]:
    """Require a complete PASS produced by the byte-identical generated TB."""

    report = json.loads((baseline_dir / "simulation_report.json").read_text())
    coverage = json.loads((baseline_dir / "functional_coverage_report.json").read_text())
    ledger = json.loads((baseline_dir / "stimulus_ledger.json").read_text())
    hashes = {
        filename: {
            "generated": sha256(generated / filename),
            "baseline": sha256(baseline_generated / filename),
        }
        for filename in GENERATED_ARTIFACTS
    }
    matching_generated = all(
        item["generated"] == item["baseline"] for item in hashes.values()
    )
    complete = (
        report.get("status") == "PASS"
        and coverage.get("status") == "PASS"
        and coverage.get("required_bins") == coverage.get("hit_bins")
        and not coverage.get("missing_bins")
        and not coverage.get("assertion_failures")
        and ledger.get("status") == "PASS"
        and matching_generated
    )
    if not complete:
        raise AssertionError(
            "saved positive baseline is incomplete or uses a different generated TB"
        )
    return {
        "complete": True,
        "required_bins": coverage.get("required_bins"),
        "stimulus_count": ledger.get("stimulus_count"),
        "hashes": hashes,
    }


def cleanup_simulation_builds(output_dir: Path) -> list[str]:
    """Remove regenerable simulator build trees below one qualification case.

    The evidence used for qualification lives in the JSON/YAML reports, the
    generated test, and the mutated RTL.  A Verilator ``build`` directory is a
    disposable compilation cache and is hundreds of megabytes for this HLS
    design.  Batch campaigns remove those caches after each case so the full
    registry cannot exhaust the host disk while retaining reviewable evidence.
    """

    removed: list[str] = []
    if not output_dir.is_dir():
        return removed
    for path in sorted(output_dir.rglob("build")):
        if path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path))
    return removed


def compact_completed_qualification(output_dir: Path) -> list[str]:
    """Keep the durable result files and discard reproducible working trees."""

    qualification_path = output_dir / "qualification.json"
    if not qualification_path.is_file():
        return []
    try:
        qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    if qualification.get("status") != "QUALIFIED":
        return []
    removed: list[str] = []
    for name in QUALIFICATION_TRANSIENT_DIRS:
        path = output_dir / name
        if path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path))
    return removed


def load_completed_qualification(
    qualification_path: Path,
    *,
    baseline_generated: Path,
) -> dict[str, Any] | None:
    """Return a reusable QUALIFIED result only when its TB hash still matches."""

    if not qualification_path.is_file():
        return None
    try:
        result = json.loads(qualification_path.read_text(encoding="utf-8"))
        current_hash = sha256(baseline_generated / "test_gemm_automatic.py")
    except (OSError, ValueError, TypeError):
        return None
    if (
        result.get("status") != "QUALIFIED"
        or result.get("baseline_complete") is not True
        or result.get("generated_test_sha256") != current_hash
    ):
        return None
    return result


def reset_qualification_workspace(output_dir: Path) -> None:
    """Replace one non-qualified case workspace before a deterministic retry."""

    if output_dir.is_symlink() or output_dir.is_file():
        output_dir.unlink()
    elif output_dir.is_dir():
        shutil.rmtree(output_dir)


__all__ = [
    "GENERATED_ARTIFACTS",
    "QUALIFICATION_TRANSIENT_DIRS",
    "cleanup_simulation_builds",
    "compact_completed_qualification",
    "diagnostic_excerpt",
    "load_completed_qualification",
    "materialize_baseline_generated_pair",
    "reset_qualification_workspace",
    "sha256",
    "validate_positive_baseline",
]
