"""Initial executable LangGraph for Architect -> RTL generation.

The graph can start from a user request or reuse a previously frozen architecture.
If RTL reports ``ARCHITECTURE_CONFLICT``, deterministic routing sends the structured
feedback to Architect within the configured revision budget. The graph intentionally
stops at a verification placeholder until the independent Verifier is implemented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from multigent.agents.architect import ArchitectAgent
from multigent.agents.rtl_generator import RTLGeneratorAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, build_rtl_context

from .architect_node import make_architect_node
from .routes import route_after_architect, route_after_rtl, route_start
from .rtl_node import make_rtl_generator_node
from .state import HardwareDesignState


def _verification_placeholder(state: HardwareDesignState) -> dict[str, Any]:
    """Terminal placeholder until the independent Verifier node is implemented."""

    return {
        "verification_status": "PENDING_IMPLEMENTATION",
        "status": "RTL_READY_FOR_VERIFICATION",
        "history": [
            {
                "stage": "verification",
                "status": "PENDING_IMPLEMENTATION",
                "rtl_files": list(state.get("rtl_files", [])),
            }
        ],
    }


def _failed_node(state: HardwareDesignState) -> dict[str, Any]:
    reason = (
        state.get("rtl_status")
        or state.get("architecture_status")
        or state.get("failure_class")
        or "UNKNOWN"
    )
    return {
        "status": "FAILED",
        "history": [{"stage": "orchestrator", "status": "FAILED", "reason": reason}],
    }


def build_architect_rtl_graph(
    *,
    architect_agent: ArchitectAgent | None = None,
    rtl_agent: RTLGeneratorAgent | None = None,
):
    """Compile the first LangGraph slice with an architecture-revision loop."""

    builder = StateGraph(HardwareDesignState)
    builder.add_node("architect", make_architect_node(architect_agent))
    builder.add_node("rtl_generator", make_rtl_generator_node(rtl_agent))
    builder.add_node("verification", _verification_placeholder)
    builder.add_node("failed", _failed_node)

    builder.add_conditional_edges(START, route_start)
    builder.add_conditional_edges("architect", route_after_architect)
    builder.add_conditional_edges("rtl_generator", route_after_rtl)
    builder.add_edge("verification", END)
    builder.add_edge("failed", END)
    return builder.compile()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the LangGraph Architect -> RTL generation slice"
    )
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-architecture-revisions", type=int, default=2)
    parser.add_argument(
        "--architecture-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
    )
    parser.add_argument(
        "--use-frozen-architecture",
        action="store_true",
        help="Start at RTL using the validated architecture artifacts already in --architecture-dir.",
    )
    args = parser.parse_args()

    if args.max_architecture_revisions < 0:
        raise ValueError("--max-architecture-revisions must be >= 0")

    graph = build_architect_rtl_graph()
    initial: HardwareDesignState = {
        "run_id": args.run_id,
        "user_request": args.request.strip(),
        "architecture_dir": str(args.architecture_dir),
        "architecture_version": 0,
        "architecture_revision": 0,
        "max_architecture_revisions": args.max_architecture_revisions,
        "rtl_task_type": "INITIAL_GENERATION",
        "history": [],
        "errors": [],
        "status": "RUNNING",
    }

    if args.use_frozen_architecture:
        initial.update(
            {
                "architecture_status": "READY",
                "architecture_version": 1,
                "rtl_context": build_rtl_context(
                    user_request=args.request.strip(),
                    architecture_dir=args.architecture_dir,
                ),
            }
        )

    recursion_limit = 8 + 2 * args.max_architecture_revisions
    final_state = graph.invoke(initial, {"recursion_limit": recursion_limit})
    print(
        json.dumps(
            {
                "status": final_state.get("status"),
                "architecture_status": final_state.get("architecture_status"),
                "architecture_version": final_state.get("architecture_version"),
                "architecture_revision": final_state.get("architecture_revision"),
                "rtl_status": final_state.get("rtl_status"),
                "rtl_files": final_state.get("rtl_files", []),
                "verification_status": final_state.get("verification_status"),
                "architecture_conflict": final_state.get("architecture_conflict"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
