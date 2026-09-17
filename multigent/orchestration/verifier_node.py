"""LangGraph node adapter for the independent Verifier Agent."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent

from .state import HardwareDesignState


_NON_SEMANTIC_RUNTIME_MARKERS = (
    "API request failed",
    "failed to produce valid structured output",
    "Verifier node requires",
    "Verifier context missing",
    "Independent Verifier context must exclude",
    "Verifier provenance must be",
    "Verifier frozen_architecture must be",
    "Verifier context missing frozen artifacts",
)


def _is_semantic_validation_error(exc: AgentRuntimeError) -> bool:
    """Return True only for post-generation semantic validation failures.

    Transport/schema parsing already has bounded retry inside ``APIAgent``. Context
    construction/configuration failures are deterministic infrastructure problems and
    should surface immediately rather than spending another model call. Everything
    else raised after a schema-valid verifier output is eligible for bounded correction
    through the graph's verifier-revision loop.
    """

    message = str(exc)
    return not any(marker in message for marker in _NON_SEMANTIC_RUNTIME_MARKERS)


def make_verifier_node(
    agent: VerifierAgent | None = None,
) -> Callable[[HardwareDesignState], dict[str, Any]]:
    """Return one Verifier attempt; graph routing owns bounded semantic repair.

    Schema-invalid output is already retried by ``APIAgent``. A schema-valid but
    semantically invalid artifact becomes explicit graph state, so the exact validator
    error can be fed back through the normal, counted verifier-revision budget.
    """

    runtime = agent or VerifierAgent()

    def verifier_node(state: HardwareDesignState) -> dict[str, Any]:
        state = {key: state[key] for key in (
            "run_id", "user_request", "architecture_dir", "architecture_version",
            "architecture_revision", "repair_iteration", "verifier_revision",
            "verification_context",
        ) if key in state}
        context = state.get("verification_context")
        semantic_review = (
            context.get("semantic_validation_review")
            if isinstance(context, Mapping)
            else None
        )
        try:
            update = runtime.run_from_state(state)
        except AgentRuntimeError as exc:
            if not _is_semantic_validation_error(exc):
                raise
            message = str(exc)
            failure: dict[str, Any] = {
                "verifier_status": "SEMANTIC_VALIDATION_FAILED",
                "verifier_review_status": "PENDING",
                "verifier_review_result": None,
                "verifier_review_hashes": {},
                "errors": [message],
                "history": [
                    {
                        "stage": "verifier_generation",
                        "status": "SEMANTIC_VALIDATION_FAILED",
                        "validator_error": message,
                    }
                ],
            }
            draft = getattr(runtime, "last_generated_result", None)
            if isinstance(draft, Mapping):
                failure["verifier_draft"] = dict(draft)
            addressed = getattr(runtime, "last_addressed_findings", None)
            if addressed:
                failure["verifier_addressed_findings"] = sorted(addressed)
            return failure

        # A correction can reveal a genuine frozen-contract contradiction.
        # Do not blanket-relabel every architecture conflict as a TB defect;
        # normal architecture routing/budgets apply to its structured evidence.

        history_entry: dict[str, Any] = {
            "stage": "verifier_generation",
            "status": update["verifier_status"],
            "architecture_version": int(state.get("architecture_version", 0)),
            "repair_iteration": int(state.get("repair_iteration", 0)),
            "semantic_retry": bool(semantic_review),
        }
        if semantic_review:
            history_entry["semantic_retry_error"] = str(
                semantic_review.get("validator_error", "")
            )

        return {
            **update,
            "verifier_review_status": "PENDING",
            "verifier_review_result": None,
            "verifier_review_hashes": {},
            "history": [history_entry],
        }

    return verifier_node
