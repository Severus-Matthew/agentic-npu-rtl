"""Qualify every required HLS benchmark coverage bin from one real run.

This is positive runtime evidence, not mutant evidence.  It cross-checks the
human-readable benchmark matrix against the machine report so an aggregate
``137/137`` cannot hide a renamed, omitted, or duplicate obligation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .prepare_qualification_catalog import build_catalog


def qualify_positive_coverage(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return exact per-obligation evidence for the frozen benchmark matrix."""

    expected_cases = {
        case["feature_id"]: set(case["required_bins"])
        for case in build_catalog()["cases"]
        if case["target_type"] == "coverage_obligation"
    }
    observed: dict[str, dict[str, int]] = {}
    duplicate_ids: list[str] = []
    for obligation in report.get("obligations", []):
        obligation_id = str(obligation.get("id", ""))
        required_bins = [
            item for item in obligation.get("bins", [])
            if item.get("required") is True
        ]
        # Runtime plans may keep structural containers whose every bin is
        # inapplicable for this frozen endpoint topology.  They are useful in
        # reports, but they are not qualification targets and must not inflate
        # the denominator.
        if not required_bins:
            continue
        if obligation_id in observed:
            duplicate_ids.append(obligation_id)
        observed[obligation_id] = {
            str(item["name"]): int(item.get("hits", 0))
            for item in required_bins
        }

    expected_ids = set(expected_cases)
    observed_ids = set(observed)
    missing_obligations = sorted(expected_ids - observed_ids)
    extra_obligations = sorted(observed_ids - expected_ids)
    bin_mismatches: dict[str, dict[str, list[str]]] = {}
    zero_hit_bins: list[str] = []
    evidence: dict[str, dict[str, int]] = {}
    for obligation_id in sorted(expected_ids & observed_ids):
        expected_bins = expected_cases[obligation_id]
        actual_bins = set(observed[obligation_id])
        if expected_bins != actual_bins:
            bin_mismatches[obligation_id] = {
                "missing": sorted(expected_bins - actual_bins),
                "extra": sorted(actual_bins - expected_bins),
            }
        hits = {
            name: observed[obligation_id][name]
            for name in sorted(expected_bins & actual_bins)
        }
        evidence[obligation_id] = hits
        zero_hit_bins.extend(
            f"{obligation_id}.{name}" for name, count in hits.items() if count <= 0
        )

    reported_required = int(report.get("required_bins", -1))
    reported_hit = int(report.get("hit_bins", -1))
    enumerated_required = sum(len(names) for names in expected_cases.values())
    complete = not any((
        report.get("status") != "PASS",
        report.get("assertion_failures"),
        report.get("missing_bins"),
        duplicate_ids,
        missing_obligations,
        extra_obligations,
        bin_mismatches,
        zero_hit_bins,
        reported_required != enumerated_required,
        reported_hit != enumerated_required,
    ))
    return {
        "schema_version": 1,
        "status": "QUALIFIED" if complete else "UNQUALIFIED",
        "obligations_expected": len(expected_cases),
        "obligations_observed": len(observed),
        "required_bins_expected": enumerated_required,
        "required_bins_reported": reported_required,
        "hit_bins_reported": reported_hit,
        "duplicate_obligations": sorted(set(duplicate_ids)),
        "missing_obligations": missing_obligations,
        "extra_obligations": extra_obligations,
        "bin_mismatches": bin_mismatches,
        "zero_hit_bins": zero_hit_bins,
        "evidence": evidence,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.coverage_report.read_text(encoding="utf-8"))
    result = qualify_positive_coverage(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "evidence"}, indent=2))
    raise SystemExit(0 if result["status"] == "QUALIFIED" else 1)
