"""Execute exactly one Verifier API attempt for a frozen TB campaign.

This wrapper does not change Verifier behavior.  It only persists the prior draft
and deterministic findings so a later invocation can request one local revision
without involving Architect, RTL Generator, or Debugger.

An attempt is never counted as a trial. A trial exists only after one or more
attempts reach deterministic approval and the resulting TB passes a separate
manual semantic audit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent
from multigent.intake.request_builder import build_verification_context
from multigent.verifier_tool import (
    findings_from_validation_error,
    review_verifier_artifacts,
)


STATE_NAME = "campaign_candidate_state.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"campaign state {path} must contain an object")
    return value


def _repair_context(
    context: dict[str, Any], previous: Mapping[str, Any]
) -> dict[str, Any]:
    status = str(previous.get("status", ""))
    if status not in {"SEMANTIC_VALIDATION_FAILED", "VERIFIER_REPAIR_REQUIRED"}:
        return context
    draft = previous.get("candidate")
    findings = previous.get("findings")
    if not isinstance(draft, Mapping) or not isinstance(findings, list) or not findings:
        raise ValueError(f"prior status {status} lacks candidate/findings")
    context["deterministic_validation_review"] = {
        "findings": findings,
        "previous_verifier_output": dict(draft),
        "already_addressed_findings": list(
            map(int, previous.get("addressed_findings", []))
        ),
        "patch_validation_error": previous.get("error"),
        "instruction": (
            "Patch every listed deterministic finding locally in the previous "
            "Verifier artifact. Preserve all unaffected bytes and valid checks. "
            "Do not modify verifier_tool, generated blocks, the frozen contract, "
            "Architect, RTL Generator, or Debugger artifacts."
        ),
    }
    return context


def _write_state(workspace: Path, attempt: int, state: Mapping[str, Any]) -> None:
    candidate_dir = workspace / "campaign" / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    (candidate_dir / f"attempt-{attempt:02d}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (workspace / STATE_NAME).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--architecture-dir", required=True, type=Path)
    parser.add_argument("--workspace-dir", required=True, type=Path)
    parser.add_argument("--bootstrap-trace", type=Path)
    args = parser.parse_args()
    if args.attempt <= 0:
        parser.error("--attempt must be positive")

    workspace = args.workspace_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    state_path = workspace / STATE_NAME
    previous = _load(state_path)
    context = build_verification_context(
        user_request=args.request, architecture_dir=args.architecture_dir
    )

    if args.bootstrap_trace:
        if previous is not None:
            raise ValueError("bootstrap trace cannot replace existing campaign state")
        trace = json.loads(args.bootstrap_trace.read_text(encoding="utf-8"))
        attempt = trace["attempts"][trace.get("successful_attempt", 1) - 1]
        candidate = json.loads(attempt["output_text"])
        agent = VerifierAgent()
        try:
            agent.persist_validated_result(
                result=candidate, context=context, root=workspace
            )
        except AgentRuntimeError as exc:
            state = {
                "attempt": args.attempt,
                "completed_trial": None,
                "status": "SEMANTIC_VALIDATION_FAILED",
                "candidate": candidate,
                "findings": findings_from_validation_error(exc),
                "error": str(exc),
                "addressed_findings": [],
            }
            _write_state(workspace, args.attempt, state)
            print(
                json.dumps(
                    {
                        "attempt": args.attempt,
                        "status": state["status"],
                        "finding_count": len(state["findings"]),
                        "bootstrapped": True,
                    },
                    indent=2,
                )
            )
            return
        raise ValueError("bootstrap candidate unexpectedly passed deterministic validation")

    context = _repair_context(context, previous or {})
    agent = VerifierAgent()
    try:
        candidate = agent.run(
            context, workspace_dir=workspace, run_id=args.run_id
        )
    except AgentRuntimeError as exc:
        candidate = agent.last_generated_result
        if not isinstance(candidate, Mapping):
            state = {
                "attempt": args.attempt,
                "completed_trial": None,
                "status": "TOOL_OR_API_ERROR",
                "candidate": None,
                "findings": [],
                "error": str(exc),
                "addressed_findings": [],
            }
            _write_state(workspace, args.attempt, state)
            print(json.dumps({"attempt": args.attempt, "status": state["status"], "error": str(exc)}, indent=2))
            raise SystemExit(3)
        state = {
            "attempt": args.attempt,
            "completed_trial": None,
            "status": "SEMANTIC_VALIDATION_FAILED",
            "candidate": dict(candidate),
            "findings": findings_from_validation_error(exc),
            "error": str(exc),
            # ``findings`` above were freshly derived from the validation error
            # produced *after* the attempted patch.  Addressed indices belong to
            # the prior finding set and must never suppress this new set.
            "addressed_findings": [],
        }
        _write_state(workspace, args.attempt, state)
        print(
            json.dumps(
                {
                    "attempt": args.attempt,
                    "status": state["status"],
                    "finding_count": len(state["findings"]),
                    "addressed_findings": state["addressed_findings"],
                    "first_finding": state["findings"][0] if state["findings"] else None,
                },
                indent=2,
            )
        )
        return

    review = review_verifier_artifacts(context, candidate)
    state = {
        "attempt": args.attempt,
        "completed_trial": None,
        "status": (
            "DETERMINISTIC_APPROVED_AWAITING_MANUAL_TB_AUDIT"
            if str(review["status"]) == "APPROVED"
            else str(review["status"])
        ),
        "candidate": candidate,
        "findings": list(review.get("findings", [])),
        "error": None,
        "addressed_findings": [],
        "review": review,
    }
    _write_state(workspace, args.attempt, state)
    print(
        json.dumps(
            {
                "attempt": args.attempt,
                "status": state["status"],
                "finding_count": len(state["findings"]),
                "test_files": [item["path"] for item in candidate["test_files"]],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
