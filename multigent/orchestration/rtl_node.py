"""LangGraph node adapter for the RTL Generator Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from multigent.agents.rtl_generator import RTLGeneratorAgent

from .state import HardwareDesignState


def make_rtl_generator_node(
    agent: RTLGeneratorAgent | None = None,
) -> Callable[[HardwareDesignState], dict[str, Any]]:
    """Return a node callable suitable for ``StateGraph.add_node``.

    Routing is deliberately not encoded here. The graph may route
    ``ARCHITECTURE_CONFLICT`` back to Architect, ``RTL_GENERATED`` to verification,
    and ``REPAIR_BLOCKED`` to its retry/failure policy.
    """

    runtime = agent or RTLGeneratorAgent()

    def rtl_generator_node(state: HardwareDesignState) -> dict[str, Any]:
        base_run_id = str(state.get("run_id", "langgraph"))
        architecture_version = int(state.get("architecture_version", 0))
        repair_iteration = int(state.get("repair_iteration", 0))
        ppa_iteration = int(state.get("ppa_iteration", 0))
        node_state = dict(state)
        node_state["run_id"] = (
            f"{base_run_id}-rtl-av{architecture_version}"
            f"-r{repair_iteration}-p{ppa_iteration}"
        )

        update = runtime.run_from_state(node_state)
        return {
            **update,
            "history": [
                {
                    "stage": "rtl_generator",
                    "status": update["rtl_status"],
                    "architecture_version": architecture_version,
                    "repair_iteration": repair_iteration,
                    "ppa_iteration": ppa_iteration,
                    "files": list(update["rtl_files"]),
                }
            ],
        }

    return rtl_generator_node
