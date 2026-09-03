"""LangGraph node adapter for the evidence-driven Debugger Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from multigent.agents.debugger import DebuggerAgent

from .state import HardwareDesignState


def make_debugger_node(
    agent: DebuggerAgent | None = None,
) -> Callable[[HardwareDesignState], dict[str, Any]]:
    """Return a Debugger node; routing remains owned by the graph."""

    runtime = agent or DebuggerAgent()

    def debugger_node(state: HardwareDesignState) -> dict[str, Any]:
        current_repair = int(state.get("repair_iteration", 0))
        update = runtime.run_from_state(state)
        return {
            **update,
            "history": [
                {
                    "stage": "debugger",
                    "status": update["debugger_status"],
                    "failure_class": state.get("failure_class"),
                    "repair_iteration_before": current_repair,
                    "repair_iteration_after": update.get(
                        "repair_iteration", current_repair
                    ),
                    "affected_modules": list(
                        (update.get("diagnosis") or {}).get("affected_modules", [])
                    ),
                }
            ],
        }

    return debugger_node
