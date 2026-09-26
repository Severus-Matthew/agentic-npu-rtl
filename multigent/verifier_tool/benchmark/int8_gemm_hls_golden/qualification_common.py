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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


__all__ = [
    "GENERATED_ARTIFACTS",
    "materialize_baseline_generated_pair",
    "sha256",
    "validate_positive_baseline",
]
