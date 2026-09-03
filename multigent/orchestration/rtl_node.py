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
        update = runtime.run_from_state(state)
        return {
            **update,
            "history": [
                {
                    "stage": "rtl_generator",
                    "status": update["rtl_status"],
                    "files": list(update["rtl_files"]),
                }
            ],
        }

    return rtl_generator_node
