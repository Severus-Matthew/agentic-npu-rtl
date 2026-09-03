"""LangGraph node adapter for the independent Verifier Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from multigent.agents.verifier import VerifierAgent

from .state import HardwareDesignState


def make_verifier_node(
    agent: VerifierAgent | None = None,
) -> Callable[[HardwareDesignState], dict[str, Any]]:
    """Return a Verifier node; routing remains orchestrator-owned."""

    runtime = agent or VerifierAgent()

    def verifier_node(state: HardwareDesignState) -> dict[str, Any]:
        update = runtime.run_from_state(state)
        return {
            **update,
            "history": [
                {
                    "stage": "verifier_generation",
                    "status": update["verifier_status"],
                    "architecture_version": int(state.get("architecture_version", 0)),
                    "repair_iteration": int(state.get("repair_iteration", 0)),
                }
            ],
        }

    return verifier_node
