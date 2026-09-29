"""Qualify every required HLS coverage bin with real and ablated evidence.

Coverage is not an RTL correctness assertion.  Its positive witness must come
from observed DUT traffic, while its negative qualification asks whether the
gate rejects a missing individual witness even when aggregate counters still
claim completion.  This runner therefore pairs one real generated-TB HLS
report with one evidence-ablation mutant per required bin.

No RTL, frozen contract, generated test, or source report is modified.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from .qualify_positive_coverage import qualify_positive_coverage


def _required_bin_locations(report: Mapping[str, Any]) -> list[tuple[int, int, str]]:
    locations: list[tuple[int, int, str]] = []
    for obligation_index, obligation in enumerate(report.get("obligations", [])):
        obligation_id = str(obligation.get("id", ""))
        for bin_index, item in enumerate(obligation.get("bins", [])):
            if item.get("required") is not True:
                continue
            bin_name = str(item.get("name", ""))
            locations.append(
                (obligation_index, bin_index, f"{obligation_id}.{bin_name}")
            )
    return locations


def qualify_coverage_evidence(report: Mapping[str, Any]) -> dict[str, Any]:
    """Pair the real HLS witness with an exact zero-hit mutant for every bin."""

    positive = qualify_positive_coverage(report)
    cases: list[dict[str, Any]] = []
    for obligation_index, bin_index, full_name in _required_bin_locations(report):
        mutant = deepcopy(report)
        mutant["obligations"][obligation_index]["bins"][bin_index]["hits"] = 0
        # Deliberately retain PASS and the aggregate hit count.  The qualifier
        # must inspect the individual bin rather than trusting summary fields.
        result = qualify_positive_coverage(mutant)
        exact_rejection = (
            result["status"] == "UNQUALIFIED"
            and result["zero_hit_bins"] == [full_name]
            and not result["missing_obligations"]
            and not result["extra_obligations"]
            and not result["bin_mismatches"]
        )
        cases.append({
            "bin": full_name,
            "status": "QUALIFIED" if exact_rejection else "UNQUALIFIED",
            "exact_zero_hit_rejection": exact_rejection,
        })

    complete = (
        positive["status"] == "QUALIFIED"
        and len(cases) == positive["required_bins_expected"]
        and all(item["status"] == "QUALIFIED" for item in cases)
    )
    return {
        "schema_version": 1,
        "status": "QUALIFIED" if complete else "UNQUALIFIED",
        "evidence_class": "real_hls_positive_plus_per_bin_report_ablation",
        "positive": {
            key: value for key, value in positive.items() if key != "evidence"
        },
        "required_bins": positive["required_bins_expected"],
        "ablation_mutants": len(cases),
        "qualified_ablation_mutants": sum(
            item["status"] == "QUALIFIED" for item in cases
        ),
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.coverage_report.read_text(encoding="utf-8"))
    qualification = qualify_coverage_evidence(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qualification, indent=2), encoding="utf-8")
    print(json.dumps({
        key: value for key, value in qualification.items() if key != "cases"
    }, indent=2))
    raise SystemExit(0 if qualification["status"] == "QUALIFIED" else 1)
