"""Bounded Verifier-only API generation for audited external contracts.

This runner never invokes Architect, RTL Generator, Debugger, or FPGA stages.
The global call budget is shared across cases, so ``--max-api-calls 5`` means at
most five structured model requests in total.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.agents.verifier import VerifierAgent
from multigent.verifier_tool import findings_from_validation_error, review_verifier_artifacts
from multigent.verifier_tool.orchestration.instrumentation import (
    strip_contract_generated_block,
    verifier_owned_source_for_repair,
)
from multigent.verifier_tool.tool_regression.api_evaluation.runner import (
    _is_api_or_transport_failure,
    _repair_context,
)


HERE = Path(__file__).resolve().parent
CASES_ROOT = HERE / "cases"
LOCAL_RESULTS = HERE / "local_results"


def _case_dir(case_id: str) -> Path:
    matches = sorted(CASES_ROOT.glob(f"{case_id.lower()}_*"))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one case for {case_id}, found {matches}")
    return matches[0]


def _load_context(case_id: str) -> dict[str, Any]:
    case = _case_dir(case_id)
    status = yaml.safe_load((case / "contract_status.yaml").read_text(encoding="utf-8"))
    if status.get("status") != "reviewer_pass_candidate":
        raise ValueError(f"{case_id} is not reviewer_pass_candidate: {status.get('status')}")
    architecture = yaml.safe_load((case / "architecture_contract.yaml").read_text(encoding="utf-8"))
    interface = yaml.safe_load((case / "interface_contract.yaml").read_text(encoding="utf-8"))
    manifest = json.loads((case / "module_manifest.json").read_text(encoding="utf-8"))
    criteria = yaml.safe_load((case / "acceptance_criteria.yaml").read_text(encoding="utf-8"))
    return {
        "user_request": (
            f"Generate an independent cocotb verification environment for external "
            f"benchmark {case_id}. Implement only the explicit contract-local extensions "
            "and reuse every applicable deterministic verifier_tool primitive."
        ),
        "verification_policy": {
            "exact_integer_match_when_applicable": True,
            "randomized_transactions_minimum": 8,
            "require_reset_tests": True,
            "require_backpressure_tests_when_applicable": True,
            "regression_wall_timeout_seconds_minimum": 120,
            "require_completion_behavior_tests_when_defined": True,
            "require_error_behavior_tests_when_defined": True,
        },
        "frozen_architecture": {
            "architecture_contract": architecture,
            "interface_contract": interface,
            "module_manifest": manifest,
            "acceptance_criteria": criteria,
        },
        "provenance": {
            "includes_generated_rtl": False,
            "includes_rtl_generator_output": False,
        },
        "evaluation_scenario": {"id": case_id, "domain": "protocol"},
    }


def _expected_ids(context: Mapping[str, Any]) -> list[str]:
    return [
        str(item["id"])
        for item in context["frozen_architecture"]["architecture_contract"].get(
            "verification_extensions", []
        )
    ]


def _save_attempt_candidate(
    root: Path,
    *,
    run_started_at: str,
    attempt: int,
    candidate: Mapping[str, Any],
) -> str:
    """Preserve a rejected API draft for direct post-run source auditing.

    ``VerifierAgent`` only persists fully processed results in its normal output
    tree.  A deterministic validation exception can therefore leave the most
    useful failing source available only in ``last_generated_result``.  API
    qualification must retain that source rather than diagnose a stale result
    from an earlier invocation.
    """

    timestamp = run_started_at.replace(":", "-").replace("+", "_")
    relative = Path("rejected_candidates") / f"{timestamp}-attempt-{attempt:02d}.json"
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(dict(candidate), indent=2) + "\n",
        encoding="utf-8",
    )
    return relative.as_posix()


def _fresh_generation_retry(case_id: str, diagnostic: str) -> dict[str, Any]:
    """Retry an incomplete draft without echoing the large rejected response.

    A schema-valid ``VERIFICATION_READY`` response can still omit both source
    collections.  Such a draft has no useful local edit target, so embedding it
    in ``deterministic_validation_review`` only consumes context.  Rebuild the
    original frozen-contract request and carry forward the concise deterministic
    failure instead.
    """

    context = _load_context(case_id)
    context["user_request"] = (
        f'{context["user_request"]} The previous verifier draft was rejected by '
        f'the deterministic gate: {diagnostic}. Return at least one complete '
        'Python reference-model file and one complete cocotb test file. Do not '
        'return placeholders, empty file collections, or prose in place of code. '
        'Do not return ARCHITECTURE_CONFLICT for defects in prior Verifier output, '
        'repair instructions, generated markers, or output truncation. Regenerate '
        'clean Verifier-owned source and never emit or define pipeline-owned '
        'contract-generated markers, constants, or helper functions.'
    )
    return context


def _verifier_owned_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Remove pipeline-owned source before returning a draft to the Verifier."""

    result = copy.deepcopy(dict(candidate))
    for collection in ("reference_files", "test_files"):
        for item in result.get(collection, []):
            if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                continue
            content = strip_contract_generated_block(item["content"])
            content = verifier_owned_source_for_repair(content)
            item["content"] = content
    return result


def _self_owned_verifier_conflict(conflict: object) -> bool:
    """Recognize conflicts whose requested fix belongs to Verifier generation."""

    if not isinstance(conflict, Mapping):
        return False
    text = " ".join(
        str(conflict.get(field, "")).lower()
        for field in ("category", "issue", "evidence", "requested_architect_decision")
    )
    return any(
        marker in text
        for marker in (
            "previous_content",
            "validator_error",
            "contract-generated monitor",
            "generated marker",
            "verifier output",
            "output truncat",
            "source skeleton",
            "helper insertion",
        )
    )


def _repair_or_regenerate_context(
    case_id: str,
    *,
    candidate: Mapping[str, Any],
    findings: list[Mapping[str, Any]],
    error: str,
) -> dict[str, Any]:
    if not candidate.get("reference_files") or not candidate.get("test_files"):
        return _fresh_generation_retry(case_id, error)
    try:
        verifier_candidate = _verifier_owned_candidate(candidate)
    except ValueError:
        return _fresh_generation_retry(
            case_id,
            "The prior Verifier draft corrupted a pipeline-owned generated marker; "
            "discard that draft and emit fresh Verifier-owned files.",
        )
    return _repair_context(
        _load_context(case_id),
        candidate=verifier_candidate,
        findings=findings,
        error=error,
    )


def run_cases(
    case_ids: list[str], *, max_api_calls: int, api_timeout_seconds: int = 600
) -> dict[str, Any]:
    LOCAL_RESULTS.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "global_max_api_calls": max_api_calls,
        "api_timeout_seconds": api_timeout_seconds,
        "api_calls": 0,
        "cases": [],
    }
    remaining = max_api_calls
    for case_index, case_id in enumerate(case_ids):
        if remaining <= 0:
            summary["cases"].append({"case_id": case_id, "verdict": "NOT_RUN", "reason": "global_api_budget_exhausted"})
            continue
        context = _load_context(case_id)
        root = LOCAL_RESULTS / case_id.lower()
        root.mkdir(parents=True, exist_ok=True)
        case_record: dict[str, Any] = {"case_id": case_id, "attempts": []}
        # Reserve one first attempt for every remaining case. Extra budget is used
        # only for deterministic repair of the current case.
        remaining_cases = len(case_ids) - case_index
        case_budget = max(1, remaining - (remaining_cases - 1))
        for attempt in range(1, case_budget + 1):
            agent = VerifierAgent()
            agent.config = replace(
                agent.config,
                structured_attempts=1,
                timeout_seconds=api_timeout_seconds,
            )
            summary["api_calls"] += 1
            remaining -= 1
            try:
                result = agent.run(
                    context,
                    workspace_dir=root,
                    run_id=f"external-{case_id.lower()}-{attempt:02d}",
                )
                review = review_verifier_artifacts(context, result)
                if result.get("status") == "ARCHITECTURE_CONFLICT":
                    conflict = result.get("architecture_conflict")
                    if _self_owned_verifier_conflict(conflict):
                        diagnostic = (
                            "Verifier returned a self-owned generation/repair conflict: "
                            + json.dumps(conflict, sort_keys=True)
                        )
                        case_record["attempts"].append(
                            {
                                "attempt": attempt,
                                "status": "SELF_OWNED_CONFLICT_REJECTED",
                                "architecture_conflict": conflict,
                            }
                        )
                        if attempt < case_budget:
                            context = _fresh_generation_retry(case_id, diagnostic)
                            continue
                        case_record["verdict"] = "REJECTED"
                        break
                    case_record["attempts"].append(
                        {
                            "attempt": attempt,
                            "status": "ARCHITECTURE_CONFLICT",
                            "architecture_conflict": conflict,
                        }
                    )
                    case_record.update(
                        {
                            "verdict": "ARCHITECTURE_CONFLICT",
                            "architecture_conflict": conflict,
                        }
                    )
                    # A model-declared frozen-contract conflict is Architect-owned;
                    # feeding it through the Verifier artifact repair loop only
                    # repeats the same request and wastes the bounded API budget.
                    break
                actual_ids = [
                    str(item.get("request_id", ""))
                    for item in result.get("feature_extensions", [])
                    if isinstance(item, Mapping)
                ]
                errors: list[str] = []
                if result.get("status") != "VERIFICATION_READY":
                    errors.append(f"unexpected verifier status {result.get('status')!r}")
                if actual_ids != _expected_ids(context):
                    errors.append(f"extension ids expected={_expected_ids(context)}, actual={actual_ids}")
                if review.get("status") != "APPROVED":
                    errors.append(f"artifact review status={review.get('status')!r}")
                case_record["attempts"].append(
                    {
                        "attempt": attempt,
                        "status": "PASS" if not errors else "REPAIR_REQUIRED",
                        "errors": errors,
                        "review_status": review.get("status"),
                        "review_findings": review.get("findings", []),
                    }
                )
                if not errors:
                    case_record.update(
                        {
                            "verdict": "PASS",
                            "generated_test_files": len(result.get("test_files", [])),
                            "generated_reference_files": len(result.get("reference_files", [])),
                        }
                    )
                    break
                if review.get("findings") and attempt < case_budget:
                    context = _repair_or_regenerate_context(
                        case_id,
                        candidate=result,
                        findings=list(review["findings"]),
                        error="; ".join(errors),
                    )
                    continue
                case_record["verdict"] = "FAIL"
                break
            except Exception as exc:
                candidate = agent.last_generated_result
                infrastructure_failure = _is_api_or_transport_failure(exc)
                findings = findings_from_validation_error(exc) if isinstance(candidate, dict) else []
                candidate_snapshot = (
                    _save_attempt_candidate(
                        root,
                        run_started_at=summary["started_at"],
                        attempt=attempt,
                        candidate=candidate,
                    )
                    if isinstance(candidate, Mapping)
                    else None
                )
                case_record["attempts"].append(
                    {
                        "attempt": attempt,
                        "status": (
                            "API_OR_TOOL_ERROR"
                            if infrastructure_failure or not candidate
                            else "GENERATION_REJECTED"
                        ),
                        "exception_type": type(exc).__name__,
                        "diagnostic": str(exc)[:8000],
                        "findings": [] if infrastructure_failure else findings,
                        "candidate_snapshot": candidate_snapshot,
                    }
                )
                if infrastructure_failure:
                    case_record["verdict"] = "API_OR_TOOL_ERROR"
                    break
                if isinstance(candidate, dict) and findings and attempt < case_budget:
                    context = _repair_or_regenerate_context(
                        case_id,
                        candidate=candidate,
                        findings=findings,
                        error=str(exc),
                    )
                    continue
                case_record["verdict"] = "REJECTED"
                break
        summary["cases"].append(case_record)
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    (LOCAL_RESULTS / "api_generation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_ids", nargs="+", help="Audited case IDs, for example P01 P02 P03")
    parser.add_argument("--max-api-calls", type=int, default=5)
    parser.add_argument("--api-timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.max_api_calls < 1:
        raise SystemExit("--max-api-calls must be positive")
    if args.api_timeout_seconds < 1:
        raise SystemExit("--api-timeout-seconds must be positive")
    result = run_cases(
        [item.upper() for item in args.case_ids],
        max_api_calls=args.max_api_calls,
        api_timeout_seconds=args.api_timeout_seconds,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
