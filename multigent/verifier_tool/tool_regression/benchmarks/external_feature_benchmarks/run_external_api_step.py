"""Run one resumable Verifier API repair step for an external benchmark.

This evaluation-only runner preserves the same deterministic repair context used
by ``run_external_api`` under gitignored ``local_results``.  It exists so a human
can inspect one candidate, improve a general validator only when justified, and
then resume the exact repair conversation with one more bounded API call.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from multigent.agents.verifier import VerifierAgent
from multigent.verifier_tool import findings_from_validation_error, review_verifier_artifacts
from multigent.verifier_tool.tool_regression.api_evaluation.runner import (
    _is_api_or_transport_failure,
)

from .run_external_api import (
    LOCAL_RESULTS,
    _expected_ids,
    _load_context,
    _repair_or_regenerate_context,
    _save_attempt_candidate,
    _self_owned_verifier_conflict,
    _fresh_generation_retry,
)


STATE_NAME = "api_step_state.json"
SUMMARY_NAME = "api_step_summary.json"


def _state_path(root: Path) -> Path:
    return root / STATE_NAME


def _write_state(
    root: Path,
    *,
    case_id: str,
    attempt: int,
    status: str,
    context: Mapping[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case_id,
        "attempt": attempt,
        "status": status,
    }
    if context is not None:
        payload["context"] = dict(context)
    _state_path(root).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _load_state(root: Path, case_id: str) -> tuple[dict[str, Any], int]:
    path = _state_path(root)
    if not path.is_file():
        raise ValueError(f"no step state for {case_id}; start with --reset")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("case_id") != case_id:
        raise ValueError(f"invalid step state for {case_id}: {path}")
    if payload.get("status") != "REPAIR_PENDING":
        raise ValueError(
            f"step state for {case_id} is terminal: {payload.get('status')!r}"
        )
    context = payload.get("context")
    if not isinstance(context, dict):
        raise ValueError(f"step state for {case_id} has no repair context")
    return context, int(payload.get("attempt", 0)) + 1


def reopen_reviewed_candidate(case_id: str) -> dict[str, Any]:
    """Resume a terminal structural PASS after a stricter local review rejects it.

    A candidate can pass the current structural gate and then expose a general
    validator gap during simulation.  After that validator is improved, this
    evaluation-only transition feeds the newly deterministic findings back into
    the same repair conversation without editing the generated TB or spending an
    extra API call merely to reproduce the stale candidate.
    """

    case_id = case_id.upper()
    root = LOCAL_RESULTS / case_id.lower()
    state_path = _state_path(root)
    if not state_path.is_file():
        raise ValueError(f"no step state for {case_id}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("case_id") != case_id or state.get("status") != "PASS":
        raise ValueError(
            f"only a terminal PASS may be reopened for {case_id}; "
            f"found {state.get('status')!r}"
        )
    result_path = root / "verification" / "verifier_result.json"
    if not result_path.is_file():
        raise ValueError(f"saved verifier result is missing: {result_path}")
    candidate = json.loads(result_path.read_text(encoding="utf-8"))
    context = _load_context(case_id)
    review = review_verifier_artifacts(context, candidate)
    findings = list(review.get("findings", []))
    if review.get("status") == "APPROVED" or not findings:
        raise ValueError(
            "saved candidate still passes deterministic review; add a general "
            "validator rule before reopening it"
        )
    attempt = int(state.get("attempt", 0))
    next_context = _repair_or_regenerate_context(
        case_id,
        candidate=candidate,
        findings=findings,
        error=(
            "A post-generation simulation exposed a general validation gap. "
            "The improved deterministic review now rejects the saved candidate."
        ),
    )
    _write_state(
        root,
        case_id=case_id,
        attempt=attempt,
        status="REPAIR_PENDING",
        context=next_context,
    )
    return {
        "case_id": case_id,
        "attempt": attempt,
        "status": "REPAIR_PENDING",
        "review_status": review.get("status"),
        "findings": findings,
    }


def reopen_simulation_failure(case_id: str, finding_path: Path) -> dict[str, Any]:
    """Feed one audited simulation failure into the saved repair conversation."""

    case_id = case_id.upper()
    root = LOCAL_RESULTS / case_id.lower()
    state_path = _state_path(root)
    if not state_path.is_file():
        raise ValueError(f"no step state for {case_id}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("case_id") != case_id or state.get("status") != "PASS":
        raise ValueError(
            f"only a terminal structural PASS may receive simulation feedback; "
            f"found {state.get('status')!r}"
        )
    result_path = root / "verification" / "verifier_result.json"
    if not result_path.is_file():
        raise ValueError(f"saved verifier result is missing: {result_path}")
    candidate = json.loads(result_path.read_text(encoding="utf-8"))
    finding_payload = json.loads(finding_path.read_text(encoding="utf-8"))
    findings = (
        finding_payload
        if isinstance(finding_payload, list)
        else finding_payload.get("findings", [])
        if isinstance(finding_payload, Mapping)
        else []
    )
    required_fields = {"category", "requirement", "evidence", "recommended_change"}
    if not findings or any(
        not isinstance(finding, Mapping)
        or not required_fields.issubset(finding)
        or any(not str(finding[field]).strip() for field in required_fields)
        for finding in findings
    ):
        raise ValueError(
            "simulation finding must contain nonempty category, requirement, "
            "evidence, and recommended_change"
        )
    attempt = int(state.get("attempt", 0))
    next_context = _repair_or_regenerate_context(
        case_id,
        candidate=candidate,
        findings=[dict(finding) for finding in findings],
        error="Generated artifact passed structural review but failed audited RTL simulation.",
    )
    _write_state(
        root,
        case_id=case_id,
        attempt=attempt,
        status="REPAIR_PENDING",
        context=next_context,
    )
    return {
        "case_id": case_id,
        "attempt": attempt,
        "status": "REPAIR_PENDING",
        "source": str(finding_path),
        "findings": findings,
    }


def run_step(
    case_id: str, *, reset: bool = False, api_timeout_seconds: int = 600
) -> dict[str, Any]:
    case_id = case_id.upper()
    root = LOCAL_RESULTS / case_id.lower()
    root.mkdir(parents=True, exist_ok=True)
    if reset:
        context = _load_context(case_id)
        attempt = 1
    else:
        context, attempt = _load_state(root, case_id)

    started_at = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case_id,
        "attempt": attempt,
        "started_at": started_at,
    }
    agent = VerifierAgent()
    agent.config = replace(
        agent.config,
        structured_attempts=1,
        timeout_seconds=api_timeout_seconds,
    )
    try:
        result = agent.run(
            context,
            workspace_dir=root,
            run_id=f"external-step-{case_id.lower()}-{attempt:02d}",
        )
        review = review_verifier_artifacts(context, result)
        if result.get("status") == "ARCHITECTURE_CONFLICT":
            conflict = result.get("architecture_conflict")
            record["architecture_conflict"] = conflict
            if _self_owned_verifier_conflict(conflict):
                diagnostic = (
                    "Verifier returned a self-owned generation/repair conflict: "
                    + json.dumps(conflict, sort_keys=True)
                )
                next_context = _fresh_generation_retry(case_id, diagnostic)
                record["status"] = "SELF_OWNED_CONFLICT_REJECTED"
                _write_state(
                    root,
                    case_id=case_id,
                    attempt=attempt,
                    status="REPAIR_PENDING",
                    context=next_context,
                )
            else:
                record["status"] = "ARCHITECTURE_CONFLICT"
                _write_state(
                    root,
                    case_id=case_id,
                    attempt=attempt,
                    status="ARCHITECTURE_CONFLICT",
                )
        else:
            actual_ids = [
                str(item.get("request_id", ""))
                for item in result.get("feature_extensions", [])
                if isinstance(item, Mapping)
            ]
            errors: list[str] = []
            if result.get("status") != "VERIFICATION_READY":
                errors.append(f"unexpected verifier status {result.get('status')!r}")
            if actual_ids != _expected_ids(context):
                errors.append(
                    f"extension ids expected={_expected_ids(context)}, actual={actual_ids}"
                )
            if review.get("status") != "APPROVED":
                errors.append(f"artifact review status={review.get('status')!r}")
            record.update(
                {
                    "status": "PASS" if not errors else "REPAIR_REQUIRED",
                    "errors": errors,
                    "review_status": review.get("status"),
                    "review_findings": review.get("findings", []),
                }
            )
            if not errors:
                record["generated_test_files"] = len(result.get("test_files", []))
                record["generated_reference_files"] = len(result.get("reference_files", []))
                _write_state(
                    root, case_id=case_id, attempt=attempt, status="PASS"
                )
            elif review.get("findings"):
                next_context = _repair_or_regenerate_context(
                    case_id,
                    candidate=result,
                    findings=list(review["findings"]),
                    error="; ".join(errors),
                )
                _write_state(
                    root,
                    case_id=case_id,
                    attempt=attempt,
                    status="REPAIR_PENDING",
                    context=next_context,
                )
            else:
                _write_state(
                    root, case_id=case_id, attempt=attempt, status="FAIL"
                )
    except Exception as exc:
        candidate = agent.last_generated_result
        infrastructure_failure = _is_api_or_transport_failure(exc)
        findings = findings_from_validation_error(exc) if isinstance(candidate, dict) else []
        snapshot = (
            _save_attempt_candidate(
                root,
                run_started_at=started_at,
                attempt=attempt,
                candidate=candidate,
            )
            if isinstance(candidate, Mapping)
            else None
        )
        record.update(
            {
                "status": (
                    "API_OR_TOOL_ERROR"
                    if infrastructure_failure or not candidate
                    else "GENERATION_REJECTED"
                ),
                "exception_type": type(exc).__name__,
                "diagnostic": str(exc)[:8000],
                "findings": [] if infrastructure_failure else findings,
                "candidate_snapshot": snapshot,
            }
        )
        if infrastructure_failure or not isinstance(candidate, dict) or not findings:
            _write_state(
                root,
                case_id=case_id,
                attempt=attempt,
                status=record["status"],
            )
        else:
            next_context = _repair_or_regenerate_context(
                case_id,
                candidate=candidate,
                findings=findings,
                error=str(exc),
            )
            _write_state(
                root,
                case_id=case_id,
                attempt=attempt,
                status="REPAIR_PENDING",
                context=next_context,
            )

    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    (root / SUMMARY_NAME).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--reopen-reviewed-candidate", action="store_true")
    parser.add_argument("--reopen-simulation-failure", type=Path)
    parser.add_argument("--api-timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    transition_count = sum(
        bool(item)
        for item in (
            args.reset,
            args.reopen_reviewed_candidate,
            args.reopen_simulation_failure,
        )
    )
    if transition_count > 1:
        raise SystemExit(
            "--reset, --reopen-reviewed-candidate, and "
            "--reopen-simulation-failure are mutually exclusive"
        )
    if args.api_timeout_seconds < 1:
        raise SystemExit("--api-timeout-seconds must be positive")
    if args.reopen_reviewed_candidate:
        print(json.dumps(reopen_reviewed_candidate(args.case_id), indent=2))
        return 0
    if args.reopen_simulation_failure:
        print(
            json.dumps(
                reopen_simulation_failure(
                    args.case_id, args.reopen_simulation_failure
                ),
                indent=2,
            )
        )
        return 0
    result = run_step(
        args.case_id,
        reset=args.reset,
        api_timeout_seconds=args.api_timeout_seconds,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
