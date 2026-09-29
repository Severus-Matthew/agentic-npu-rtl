"""Run bounded, opt-in Verifier API evaluation cases and emit compact evidence.

Raw generated files remain under ``local_results/`` (ignored). The runner never
invokes Architect, RTL Generator, simulation, Debugger, commit, or push.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Sequence

import yaml

from multigent.agents.verifier import VerifierAgent

from .contexts import (
    HERE,
    api_scenarios,
    expected_extension_request_ids,
    expected_formula_concepts,
    scenario_context,
)


LOCAL_RESULTS = HERE / "local_results"


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")


def _formula_points(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(point.get("concept", "")): point
        for spec in result.get("operation_coverage", [])
        for point in spec.get("coverpoints", [])
        if isinstance(point, dict)
    }


def _validate_result(
    identity: str, result: dict[str, Any], output_root: Path
) -> list[str]:
    errors: list[str] = []
    if result.get("status") != "VERIFICATION_READY":
        errors.append(f"unexpected status {result.get('status')!r}")
    expected_requests = expected_extension_request_ids(identity)
    actual_requests = [
        str(item.get("request_id", ""))
        for item in result.get("feature_extensions", [])
        if isinstance(item, dict)
    ]
    if actual_requests != expected_requests:
        errors.append(
            f"extension bundle ids mismatch: expected={expected_requests}, actual={actual_requests}"
        )
    points = _formula_points(result)
    for concept in expected_formula_concepts(identity):
        point = points.get(concept)
        if point is None:
            errors.append(f"missing formula coverage concept {concept!r}")
        elif point.get("source") != "architect_extension":
            errors.append(
                f"formula concept {concept!r} has source={point.get('source')!r}"
            )
        elif not point.get("bins"):
            errors.append(f"formula concept {concept!r} has no bins")
    plan_path = output_root / "verification" / "operation_coverage_plan.yaml"
    if expected_formula_concepts(identity) and plan_path.is_file():
        plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
        obligations = {
            str(item.get("bindings", {}).get("concept", "")): item
            for item in plan.get("obligations", [])
        }
        for concept in expected_formula_concepts(identity):
            obligation = obligations.get(concept, {})
            sampling = obligation.get("bindings", {}).get("sampling")
            if sampling != {
                "template": "canonical_job",
                "origin": "verifier_tool_solver_compiled_formula",
            }:
                errors.append(
                    f"formula concept {concept!r} lacks tool-owned sampling: {sampling!r}"
                )
            for bin_spec in obligation.get("bins", []):
                witness = bin_spec.get("applicability", {}).get("witness")
                if bin_spec.get("required") and not witness:
                    errors.append(
                        f"formula concept {concept!r} bin {bin_spec.get('name')!r} lacks solver witness"
                    )
    elif expected_formula_concepts(identity):
        errors.append("operation coverage plan was not persisted")
    return errors


def run_one(identity: str, output_root: Path) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    output_root.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "schema_version": 1,
        "scenario_id": identity,
        "domain": api_scenarios()[identity]["domain"],
        "started_at": started.isoformat(),
        "expected_extension_requests": expected_extension_request_ids(identity),
        "expected_formula_concepts": expected_formula_concepts(identity),
        "raw_artifact_directory": str(output_root.resolve()),
    }
    try:
        agent = VerifierAgent()
        agent.config = replace(agent.config, structured_attempts=1)
        result = agent.run(
            scenario_context(identity),
            workspace_dir=output_root,
            run_id=f"api-evaluation-{_safe_name(identity)}",
        )
        errors = _validate_result(identity, result, output_root)
        record.update(
            {
                "verdict": "PASS" if not errors else "FAIL",
                "verifier_status": result.get("status"),
                "validation_errors": errors,
                "generated_test_files": len(result.get("test_files", [])),
                "generated_reference_files": len(result.get("reference_model_files", [])),
                "generated_extension_bundles": len(result.get("feature_extensions", [])),
            }
        )
    except Exception as exc:  # Evidence runner must preserve failed attempts.
        record.update(
            {
                "verdict": "REJECTED",
                "exception_type": type(exc).__name__,
                "diagnostic": str(exc)[:4000],
            }
        )
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    (output_root / "attempt_summary.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


def run_selected(
    identities: Sequence[str], *, output_root: Path
) -> list[dict[str, Any]]:
    if os.getenv("RUN_VERIFIER_API_EVALUATION") != "1":
        raise RuntimeError(
            "Set RUN_VERIFIER_API_EVALUATION=1 explicitly; this command spends API usage."
        )
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for API evaluation")
    catalog = api_scenarios()
    unknown = sorted(set(identities) - set(catalog))
    if unknown:
        raise KeyError(f"unknown API evaluation scenario(s): {unknown}")
    return [
        run_one(identity, output_root / _safe_name(identity))
        for identity in identities
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--domain", choices=["operation", "protocol", "lifecycle", "mixed"])
    parser.add_argument("--max-cases", type=int, default=1)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=LOCAL_RESULTS)
    args = parser.parse_args()
    catalog = api_scenarios()
    if args.list:
        for identity, spec in catalog.items():
            print(f"{identity}\t{spec['domain']}\t{spec.get('intent', spec.get('summary', ''))}")
        return
    selected = list(args.scenario)
    if not selected:
        selected = [
            identity
            for identity, spec in catalog.items()
            if args.domain is None or spec["domain"] == args.domain
        ]
    if args.max_cases < 1:
        raise SystemExit("--max-cases must be positive")
    selected = selected[: args.max_cases]
    records = run_selected(selected, output_root=args.output_dir)
    print(json.dumps(records, indent=2))
    if any(item["verdict"] != "PASS" for item in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
