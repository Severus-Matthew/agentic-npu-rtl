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
from multigent.verifier_tool import (
    findings_from_validation_error,
    review_verifier_artifacts,
)

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


def _repair_context(
    context: dict[str, Any],
    *,
    candidate: dict[str, Any],
    findings: list[dict[str, Any]],
    error: str | None,
) -> dict[str, Any]:
    repaired = dict(context)
    if error and (
        "Invalid Verifier feature extensions:" in error
        or "Cannot install contract-generated TB monitor:" in error
        or "Source completion must replace exactly the planned files" in error
        or "Source completion duplicates file:" in error
    ):
        # The local deterministic patch format can edit Python source and
        # operation-coverage metadata, but it cannot change the
        # ``feature_extensions`` bundle that names those source symbols.  Route
        # a coupled source+bundle defect through the existing complete-source
        # correction path so stale bindings/symbols cannot survive every retry.
        repaired["semantic_validation_review"] = {
            "validator_error": error,
            "previous_verifier_output": candidate,
            "missing_concepts": [],
            "instruction": (
                "Correct the Verifier-owned feature-extension bundle and only "
                "the source regions implicated by validator_error. Preserve all "
                "unaffected source, coverage, checks, and frozen-contract facts."
            ),
        }
        return repaired
    repaired["deterministic_validation_review"] = {
        "findings": findings,
        "previous_verifier_output": candidate,
        "already_addressed_findings": [],
        "patch_validation_error": error,
        "instruction": (
            "Patch every listed deterministic finding locally in the previous "
            "Verifier artifact. Preserve all unaffected bytes and valid checks. "
            "Do not modify verifier_tool, generated blocks, the frozen contract, "
            "Architect, RTL Generator, or Debugger artifacts. Define or repair the "
            "requested extension symbols only in the LLM-owned source before the "
            "CONTRACT-GENERATED block, as callable def/async def functions, and call "
            "them from a reachable cocotb test. A string/dict/tuple assigned under "
            "the symbol name is data, not an implementation. "
            "Every authored @cocotb.test must import and use @contract_coverage() "
            "directly below it and must never start _contract_generated_monitor "
            "manually; the decorator owns the single monitor and per-test reset. "
            "For temporal features, drive real DUT signals, collect a multi-cycle "
            "runtime trace, enforce the declared bound, and classify the exact "
            "declared coverage-bin names. Invoke every declared scenario with its "
            "exact parameter values. Start a DUT-observing monitor concurrently "
            "before stimulus; for every DUT-produced output extension, temporal or "
            "not, also start the code-owned campaign/driver or fully drive command "
            "and operand inputs so the triggering VALID can occur. Start a Clock in an "
            "independent cocotb test and use a direct assertion such as `assert "
            "trigger_seen` or `assert observed_count > 0` before awarding any "
            "temporal bin; merely storing a triggered field is insufficient."
        ),
    }
    return repaired


def _is_api_or_transport_failure(exc: BaseException) -> bool:
    """Return true when no Verifier-owned source edit can repair the failure."""

    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "api request exceeded the total wall-clock deadline",
            "api request failed using mode",
            "openai_api_key is not set",
            "connection error",
            "connect timeout",
            "read timeout",
            "rate limit",
            "authentication",
        )
    )


def run_one(
    identity: str,
    output_root: Path,
    *,
    max_attempts: int = 1,
) -> dict[str, Any]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
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
        "max_api_attempts": max_attempts,
        "attempts": [],
    }
    context = scenario_context(identity)
    for attempt in range(1, max_attempts + 1):
        agent = VerifierAgent()
        # One structured request per outer attempt keeps the user-visible repair
        # budget exact. Deterministic semantic failures are fed back explicitly
        # through the normal Verifier local-patch path below.
        agent.config = replace(agent.config, structured_attempts=1)
        try:
            result = agent.run(
                context,
                workspace_dir=output_root,
                run_id=f"api-evaluation-{_safe_name(identity)}-{attempt:02d}",
            )
        except Exception as exc:  # Preserve and, when possible, repair the draft.
            candidate = agent.last_generated_result
            infrastructure_failure = _is_api_or_transport_failure(exc)
            attempt_record: dict[str, Any] = {
                "attempt": attempt,
                "status": (
                    "TOOL_OR_API_ERROR"
                    if infrastructure_failure or not candidate
                    else "SEMANTIC_VALIDATION_FAILED"
                ),
                "exception_type": type(exc).__name__,
                "diagnostic": str(exc)[:4000],
            }
            record["attempts"].append(attempt_record)
            if infrastructure_failure:
                # Keeping a previous draft does not turn timeout/auth/transport
                # failure into a patchable source defect.
                break
            if isinstance(candidate, dict):
                findings = findings_from_validation_error(exc)
                attempt_record["finding_count"] = len(findings)
                repeated = 1
                for previous in reversed(record["attempts"][:-1]):
                    if previous.get("diagnostic") != attempt_record["diagnostic"]:
                        break
                    repeated += 1
                if repeated >= 3:
                    attempt_record["repair_stalled"] = True
                    attempt_record["stalled_repetitions"] = repeated
                    break
                if findings and attempt < max_attempts:
                    context = _repair_context(
                        scenario_context(identity),
                        candidate=candidate,
                        findings=findings,
                        error=str(exc),
                    )
                    continue
            if candidate is None:
                # No model artifact exists to repair. Retrying a transport/auth/API
                # failure would only burn the bounded semantic-repair budget and can
                # repeat the same infrastructure failure ten times.
                break
            break

        errors = _validate_result(identity, result, output_root)
        review = review_verifier_artifacts(context, result)
        if review.get("status") != "APPROVED":
            errors.append(
                "deterministic artifact review did not approve: "
                f"{review.get('status')!r}"
            )
        record["attempts"].append(
            {
                "attempt": attempt,
                "status": "PASS" if not errors else "VERIFIER_REPAIR_REQUIRED",
                "validation_errors": errors,
                "review_status": review.get("status"),
                "review_finding_count": len(review.get("findings", [])),
            }
        )
        if errors and attempt < max_attempts and review.get("findings"):
            context = _repair_context(
                scenario_context(identity),
                candidate=result,
                findings=list(review["findings"]),
                error="; ".join(errors),
            )
            continue
        record.update(
            {
                "verdict": "PASS" if not errors else "FAIL",
                "verifier_status": result.get("status"),
                "validation_errors": errors,
                "generated_test_files": len(result.get("test_files", [])),
                "generated_reference_files": len(result.get("reference_files", [])),
                "generated_extension_bundles": len(result.get("feature_extensions", [])),
            }
        )
        break

    record["api_calls"] = len(record["attempts"])
    if "verdict" not in record:
        last = record["attempts"][-1]
        record.update(
            {
                "verdict": "REJECTED",
                "exception_type": last.get("exception_type"),
                "diagnostic": last.get("diagnostic", "attempt limit reached"),
            }
        )
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    (output_root / "attempt_summary.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


def run_selected(
    identities: Sequence[str], *, output_root: Path, max_attempts: int = 1
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
        run_one(
            identity,
            output_root / _safe_name(identity),
            max_attempts=max_attempts,
        )
        for identity in identities
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--domain", choices=["operation", "protocol", "lifecycle", "mixed"])
    parser.add_argument("--max-cases", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=1)
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
    if args.max_attempts < 1:
        raise SystemExit("--max-attempts must be positive")
    selected = selected[: args.max_cases]
    records = run_selected(
        selected,
        output_root=args.output_dir,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(records, indent=2))
    if any(item["verdict"] != "PASS" for item in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
