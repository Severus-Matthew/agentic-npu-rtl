"""Executable LangGraph for Architect -> RTL -> independent verification.

The graph supports checkpoint resume from frozen architecture or existing RTL.
Verifier generation is independent from RTL source; deterministic Verilator/cocotb
nodes establish functional tool status. Debugger/repair and Synopsys nodes are the
next extensions and are represented by terminal placeholders here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from multigent.agents.architect import ArchitectAgent
from multigent.agents.rtl_generator import RTLGeneratorAgent
from multigent.agents.verifier import VerifierAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, build_rtl_context

from .architect_node import make_architect_node
from .routes import (
    route_after_architect,
    route_after_rtl,
    route_after_verification,
    route_after_verifier,
    route_start,
)
from .rtl_node import make_rtl_generator_node
from .state import HardwareDesignState
from .verification_tools_node import verification_tools_node
from .verifier_node import make_verifier_node


def _synthesis_placeholder(state: HardwareDesignState) -> dict[str, Any]:
    """Terminal placeholder until deterministic Synopsys workflow is connected."""

    return {
        "status": "READY_FOR_SYNTHESIS",
        "history": [
            {
                "stage": "synthesis",
                "status": "PENDING_IMPLEMENTATION",
                "verification_status": state.get("verification_status"),
            }
        ],
    }


def _repair_required_node(state: HardwareDesignState) -> dict[str, Any]:
    """Terminal placeholder that will be replaced by Debugger -> RTL repair loop."""

    return {
        "status": "REPAIR_REQUIRED",
        "history": [
            {
                "stage": "repair",
                "status": "PENDING_DEBUGGER_IMPLEMENTATION",
                "failure_class": state.get("failure_class"),
            }
        ],
    }


def _tool_unavailable_node(state: HardwareDesignState) -> dict[str, Any]:
    return {
        "status": "VERIFICATION_TOOL_UNAVAILABLE",
        "history": [
            {
                "stage": "verification",
                "status": "TOOL_UNAVAILABLE",
                "failure_class": state.get("failure_class"),
            }
        ],
    }


def _failed_node(state: HardwareDesignState) -> dict[str, Any]:
    reason = (
        state.get("verifier_status")
        or state.get("rtl_status")
        or state.get("architecture_status")
        or state.get("failure_class")
        or "UNKNOWN"
    )
    return {
        "status": "FAILED",
        "history": [{"stage": "orchestrator", "status": "FAILED", "reason": reason}],
    }


def build_workflow_graph(
    *,
    architect_agent: ArchitectAgent | None = None,
    rtl_agent: RTLGeneratorAgent | None = None,
    verifier_agent: VerifierAgent | None = None,
):
    """Compile Architect/RTL/Verifier/tool graph with architecture-revision routing."""

    builder = StateGraph(HardwareDesignState)
    builder.add_node("architect", make_architect_node(architect_agent))
    builder.add_node("rtl_generator", make_rtl_generator_node(rtl_agent))
    builder.add_node("verifier", make_verifier_node(verifier_agent))
    builder.add_node("verification_tools", verification_tools_node)
    builder.add_node("synthesis", _synthesis_placeholder)
    builder.add_node("repair_required", _repair_required_node)
    builder.add_node("tool_unavailable", _tool_unavailable_node)
    builder.add_node("failed", _failed_node)

    builder.add_conditional_edges(START, route_start)
    builder.add_conditional_edges("architect", route_after_architect)
    builder.add_conditional_edges("rtl_generator", route_after_rtl)
    builder.add_conditional_edges("verifier", route_after_verifier)
    builder.add_conditional_edges("verification_tools", route_after_verification)
    builder.add_edge("synthesis", END)
    builder.add_edge("repair_required", END)
    builder.add_edge("tool_unavailable", END)
    builder.add_edge("failed", END)
    return builder.compile()


def build_architect_rtl_graph(
    *,
    architect_agent: ArchitectAgent | None = None,
    rtl_agent: RTLGeneratorAgent | None = None,
):
    """Backward-compatible alias for callers using the earlier graph constructor."""

    return build_workflow_graph(
        architect_agent=architect_agent,
        rtl_agent=rtl_agent,
    )


def _existing_rtl_files() -> list[str]:
    rtl_dir = WORKSPACE_ROOT / "rtl"
    return [path.relative_to(rtl_dir).as_posix() for path in sorted(rtl_dir.rglob("*.sv"))]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LangGraph Architect -> RTL -> independent verification"
    )
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-architecture-revisions", type=int, default=2)
    parser.add_argument("--max-repair-iterations", type=int, default=5)
    parser.add_argument(
        "--architecture-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
    )
    parser.add_argument(
        "--use-frozen-architecture",
        action="store_true",
        help="Reuse validated architecture artifacts already in --architecture-dir.",
    )
    parser.add_argument(
        "--use-existing-rtl",
        action="store_true",
        help="Resume at independent Verifier using existing workspace/rtl/*.sv files.",
    )
    args = parser.parse_args()

    if args.max_architecture_revisions < 0:
        raise ValueError("--max-architecture-revisions must be >= 0")
    if args.max_repair_iterations < 0:
        raise ValueError("--max-repair-iterations must be >= 0")
    if args.use_existing_rtl and not args.use_frozen_architecture:
        raise ValueError("--use-existing-rtl requires --use-frozen-architecture")

    graph = build_workflow_graph()
    initial: HardwareDesignState = {
        "run_id": args.run_id,
        "user_request": args.request.strip(),
        "architecture_dir": str(args.architecture_dir),
        "architecture_version": 0,
        "architecture_revision": 0,
        "max_architecture_revisions": args.max_architecture_revisions,
        "rtl_task_type": "INITIAL_GENERATION",
        "repair_iteration": 0,
        "max_repair_iterations": args.max_repair_iterations,
        "ppa_iteration": 0,
        "max_ppa_iterations": 3,
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

    if args.use_existing_rtl:
        rtl_files = _existing_rtl_files()
        if not rtl_files:
            raise FileNotFoundError(
                f"--use-existing-rtl requested but no .sv files exist under {WORKSPACE_ROOT / 'rtl'}"
            )
        initial.update(
            {
                "rtl_status": "RTL_GENERATED",
                "rtl_files": rtl_files,
                "needs_regression": True,
            }
        )

    recursion_limit = 14 + 3 * args.max_architecture_revisions
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
                "verifier_status": final_state.get("verifier_status"),
                "verification_status": final_state.get("verification_status"),
                "failure_class": final_state.get("failure_class"),
                "architecture_conflict": final_state.get("architecture_conflict"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
