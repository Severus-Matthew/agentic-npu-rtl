"""Run bounded Verifier API repairs until deterministic approval, then stop.

This command deliberately does not mark a trial complete. The approved generated
TB must still receive the separate human/agent semantic audit defined by the
campaign trial manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent
from multigent.intake.request_builder import build_verification_context
from multigent.scripts.run_verifier_candidate import (
    _load,
    _repair_context,
    _write_state,
)
from multigent.verifier_tool import (
    findings_from_validation_error,
    review_verifier_artifacts,
)


def _failure_state(
    attempt: int,
    exc: Exception,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "completed_trial": None,
        "status": (
            "SEMANTIC_VALIDATION_FAILED"
            if isinstance(candidate, Mapping)
            else "TOOL_OR_API_ERROR"
        ),
        "candidate": dict(candidate) if isinstance(candidate, Mapping) else None,
        "findings": (
            findings_from_validation_error(exc)
            if isinstance(candidate, Mapping)
            else []
        ),
        "error": str(exc),
        "addressed_findings": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start-attempt", type=int, default=1)
    parser.add_argument("--max-api-attempts", type=int, default=30)
    parser.add_argument("--architecture-dir", required=True, type=Path)
    parser.add_argument("--workspace-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.start_attempt <= 0 or args.max_api_attempts <= 0:
        parser.error("attempt values must be positive")

    workspace = args.workspace_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    previous = _load(workspace / "campaign_candidate_state.json")
    final_attempt = args.start_attempt + args.max_api_attempts
    for attempt in range(args.start_attempt, final_attempt):
        context = build_verification_context(
            user_request=args.request,
            architecture_dir=args.architecture_dir,
        )
        context = _repair_context(context, previous or {})
        agent = VerifierAgent()
        try:
            candidate = agent.run(
                context,
                workspace_dir=workspace,
                run_id=f"{args.run_id}-api-{attempt:02d}",
            )
        except AgentRuntimeError as exc:
            state = _failure_state(attempt, exc, agent.last_generated_result)
            _write_state(workspace, attempt, state)
            print(
                json.dumps(
                    {
                        "attempt": attempt,
                        "status": state["status"],
                        "finding_count": len(state["findings"]),
                        "error": state["error"],
                    }
                ),
                flush=True,
            )
            previous = state
            if state["status"] == "TOOL_OR_API_ERROR":
                continue
            continue

        review = review_verifier_artifacts(context, candidate)
        approved = str(review.get("status", "")) == "APPROVED"
        state = {
            "attempt": attempt,
            "completed_trial": None,
            "status": (
                "DETERMINISTIC_APPROVED_AWAITING_MANUAL_TB_AUDIT"
                if approved
                else "VERIFIER_REPAIR_REQUIRED"
            ),
            "candidate": candidate,
            "findings": list(review.get("findings", [])),
            "error": None,
            "addressed_findings": [],
            "review": review,
        }
        _write_state(workspace, attempt, state)
        print(
            json.dumps(
                {
                    "attempt": attempt,
                    "status": state["status"],
                    "finding_count": len(state["findings"]),
                }
            ),
            flush=True,
        )
        if approved:
            return 0
        previous = state

    state = dict(previous or {})
    state.update(
        {
            "attempt": final_attempt - 1,
            "completed_trial": None,
            "status": "DETERMINISTIC_ATTEMPT_LIMIT_REACHED",
        }
    )
    _write_state(workspace, final_attempt - 1, state)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
