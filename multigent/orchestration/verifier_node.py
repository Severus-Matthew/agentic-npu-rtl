"""LangGraph node adapter for the independent Verifier Agent."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context

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
    else raised after a schema-valid verifier output is eligible for one self-correction
    attempt at this orchestration boundary.
    """

    message = str(exc)
    return not any(marker in message for marker in _NON_SEMANTIC_RUNTIME_MARKERS)


def _build_semantic_retry_state(
    state: HardwareDesignState,
    *,
    error: AgentRuntimeError,
) -> dict[str, Any]:
    context = state.get("verification_context")
    if isinstance(context, Mapping):
        retry_context: dict[str, Any] = dict(context)
    else:
        user_request = state.get("user_request")
        if not isinstance(user_request, str) or not user_request.strip():
            raise AgentRuntimeError(
                "Verifier semantic retry requires user_request or verification_context"
            ) from error
        architecture_dir = Path(
            state.get("architecture_dir", WORKSPACE_ROOT / "architecture")
        )
        retry_context = build_verification_context(
            user_request=user_request,
            architecture_dir=architecture_dir,
        )

    retry_context["semantic_retry_feedback"] = {
        "validator_error": str(error),
        "required_action": (
            "Regenerate the complete verifier output and correct this semantic defect. "
            "Do not weaken the frozen contract, verification policy, oracle, coverage, "
            "or independence rules. Preserve all unaffected requirements."
        ),
        "attempt": 1,
    }

    retry_state: dict[str, Any] = dict(state)
    retry_state["verification_context"] = retry_context
    retry_state["run_id"] = f"{state.get('run_id', 'langgraph')}-semantic-retry1"
    return retry_state


def make_verifier_node(
    agent: VerifierAgent | None = None,
) -> Callable[[HardwareDesignState], dict[str, Any]]:
    """Return a Verifier node with one bounded semantic self-correction attempt.

    The underlying API runtime already retries malformed/schema-invalid structured
    output. This node adds exactly one retry for a *schema-valid but semantically
    invalid* verifier artifact, using the deterministic validator error as feedback.
    This keeps verifier rules strict without requiring a human to rerun the graph for
    ordinary generation mistakes.
    """

    runtime = agent or VerifierAgent()

    def verifier_node(state: HardwareDesignState) -> dict[str, Any]:
        semantic_retry = False
        semantic_error: str | None = None
        try:
            update = runtime.run_from_state(state)
        except AgentRuntimeError as exc:
            if not _is_semantic_validation_error(exc):
                raise
            semantic_retry = True
            semantic_error = str(exc)
            retry_state = _build_semantic_retry_state(state, error=exc)
            update = runtime.run_from_state(retry_state)

        history_entry: dict[str, Any] = {
            "stage": "verifier_generation",
            "status": update["verifier_status"],
            "architecture_version": int(state.get("architecture_version", 0)),
            "repair_iteration": int(state.get("repair_iteration", 0)),
            "semantic_retry": semantic_retry,
        }
        if semantic_error is not None:
            history_entry["semantic_retry_error"] = semantic_error

        return {
            **update,
            "history": [history_entry],
        }

    return verifier_node
