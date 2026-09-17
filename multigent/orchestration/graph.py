"""LangGraph-owned contract review, parallel generation, evidence-driven repair and PPA."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from multigent.models import MODELS, DEFAULT_MODEL, validate_model

from langgraph.graph import END, START, StateGraph

from multigent.agents.architect import ArchitectAgent
from multigent.agents.debugger import DebuggerAgent
from multigent.agents.rtl_generator import RTLGeneratorAgent
from multigent.agents.verifier import VerifierAgent
from multigent.agents.verifier_review import VerifierReviewAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, build_rtl_context

from multigent.agents.contract_reviewer import ContractReviewerAgent
from .contract_review_node import make_contract_review_node, route_after_contract_review
from .parallel_generation import generation_start, generation_join, branch, route_after_generation
from .architecture_escalation import (escalation_start, make_contract_critique,
    make_architecture_diagnosis, route_after_architecture_diagnosis)
from .architect_node import make_architect_node
from .debugger_node import make_debugger_node
from .routes import (
    route_after_architect,
    route_after_debugger,
    route_after_rtl,
    route_after_verification,
    route_after_verifier,
    route_after_verifier_review,
    route_start,
)
from .rtl_node import make_rtl_generator_node
from .state import HardwareDesignState
from .ppa_node import synthesis_node, make_ppa_node, route_after_synthesis, route_after_ppa
from .artifacts import guarded, verification_repair_node, final_report_node, diagnostic_node
from .verification_tools_node import verification_tools_node
from .verifier_node import make_verifier_node
from .verifier_review_node import make_verifier_review_node


def _repair_exhausted_node(state: HardwareDesignState) -> dict[str, Any]:
    exhausted = ("CONTRACT_REVIEW_BUDGET_EXHAUSTED"
                 if state.get("contract_review_status") == "REVISION_REQUIRED"
                 else "REPAIR_BUDGET_EXHAUSTED")
    return {
        "status": exhausted,
        "history": [
            {
                "stage": "repair",
                "status": "BUDGET_EXHAUSTED",
                "repair_iteration": state.get("repair_iteration"),
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
        state.get("debugger_status")
        or state.get("verifier_status")
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
    verifier_review_agent: VerifierReviewAgent | None = None,
    debugger_agent: DebuggerAgent | None = None,
    ppa_agent=None,
    contract_review_agent=None,
):
    """Compile the deterministic evidence-driven multi-agent workflow."""

    architect_agent = architect_agent or ArchitectAgent()
    rtl_agent = rtl_agent or RTLGeneratorAgent()
    verifier_agent = verifier_agent or VerifierAgent()
    debugger_agent = debugger_agent or DebuggerAgent()
    builder = StateGraph(HardwareDesignState)
    def add_node(name, action):
        return builder.add_node(name, action if name == "final_report" else guarded(name, action))
    def safe_route(route):
        return lambda state: "final_report" if state.get("orchestration_error") else route(state)
    add_node("architect", make_architect_node(architect_agent))
    add_node("contract_reviewer", make_contract_review_node(contract_review_agent))
    add_node("generation_start", generation_start)
    builder.add_node("rtl_parallel", branch("rtl_generator", make_rtl_generator_node(rtl_agent)))
    builder.add_node("tb_parallel", branch("verifier", make_verifier_node(verifier_agent)))
    add_node("generation_join", generation_join)
    add_node("architecture_escalation", escalation_start)
    # Read-only critique calls have disjoint result keys; join before diagnosis.
    add_node("rtl_contract_critique", make_contract_critique(rtl_agent, "rtl"))
    add_node("tb_contract_critique", make_contract_critique(verifier_agent, "tb"))
    add_node("debugger_architecture", make_architecture_diagnosis(debugger_agent))
    add_node("rtl_generator", make_rtl_generator_node(rtl_agent))
    add_node("verifier", make_verifier_node(verifier_agent))
    # Retain the checkpoint node identifier, but use code-only preflight checks.
    add_node("verifier_review", make_verifier_review_node(verifier_review_agent))
    def run_verification(state):
        update = verification_tools_node(state)
        if update.get("verification_status") == "PASS" and state.get("verification_only"):
            update["status"] = "SUCCESS"
        return update
    add_node("verification_tools", run_verification)
    add_node("debugger", make_debugger_node(debugger_agent))
    add_node("synthesis", synthesis_node)
    add_node("ppa_optimizer", make_ppa_node(ppa_agent))
    def counted_verification_repair(state):
        update = verification_repair_node(state)
        if state.get("verification_evidence") and state.get("verification_status") not in {"PASS", "PENDING"}:
            update["repair_cycle_iteration"] = state.get("repair_cycle_iteration",state.get("repair_iteration",0)) + 1
            update["repair_iteration"] = state.get("repair_iteration",0) + 1
        return update
    add_node("verification_repair", counted_verification_repair)
    add_node("final_report", final_report_node)
    add_node("diagnostic_probe", diagnostic_node)
    add_node("repair_exhausted", _repair_exhausted_node)
    add_node("tool_unavailable", _tool_unavailable_node)
    add_node("failed", _failed_node)

    builder.add_conditional_edges(START, route_start)
    builder.add_conditional_edges("architect", safe_route(route_after_architect))
    builder.add_conditional_edges("contract_reviewer", safe_route(route_after_contract_review))
    builder.add_conditional_edges("generation_start", lambda state: "final_report" if state.get("orchestration_error") else ["rtl_parallel", "tb_parallel"])
    builder.add_edge(["rtl_parallel", "tb_parallel"], "generation_join")
    builder.add_conditional_edges("generation_join", safe_route(route_after_generation))
    builder.add_conditional_edges("architecture_escalation", safe_route(lambda state: "rtl_contract_critique"))
    builder.add_conditional_edges("rtl_contract_critique", safe_route(lambda state: "tb_contract_critique"))
    builder.add_conditional_edges("tb_contract_critique", safe_route(lambda state: "debugger_architecture"))
    builder.add_conditional_edges("debugger_architecture", safe_route(route_after_architecture_diagnosis))
    builder.add_conditional_edges("rtl_generator", safe_route(route_after_rtl))
    builder.add_conditional_edges("verifier", safe_route(route_after_verifier))
    builder.add_conditional_edges("verifier_review", safe_route(route_after_verifier_review))
    builder.add_conditional_edges("verification_tools", safe_route(route_after_verification))
    builder.add_conditional_edges("debugger", safe_route(route_after_debugger))
    builder.add_conditional_edges("synthesis", safe_route(route_after_synthesis))
    builder.add_conditional_edges("ppa_optimizer", safe_route(route_after_ppa))
    builder.add_conditional_edges("verification_repair", safe_route(lambda state: "verifier"))
    builder.add_conditional_edges("diagnostic_probe", safe_route(lambda state: "debugger"))
    builder.add_edge("final_report", END)
    builder.add_edge("repair_exhausted", "final_report")
    builder.add_edge("tool_unavailable", "final_report")
    builder.add_edge("failed", "final_report")
    return builder.compile()


def build_architect_rtl_graph(
    *,
    architect_agent: ArchitectAgent | None = None,
    rtl_agent: RTLGeneratorAgent | None = None,
):
    """Backward-compatible alias for the complete workflow constructor."""

    return build_workflow_graph(
        architect_agent=architect_agent,
        rtl_agent=rtl_agent,
    )


def _existing_rtl_files() -> list[str]:
    rtl_dir = WORKSPACE_ROOT / "rtl"
    return [
        path.relative_to(rtl_dir).as_posix()
        for path in sorted(rtl_dir.rglob("*.sv"))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run LangGraph Architect <-> Contract Reviewer -> parallel RTL/TB -> simulation -> "
            "Debugger/repair loop"
        )
    )
    parser.add_argument("--request")
    parser.add_argument('--model', choices=list(MODELS), help='Model for every agent in this run')
    parser.add_argument("--run-id")
    parser.add_argument("--max-architecture-revisions", type=int, default=12)
    parser.add_argument("--max-repair-iterations", type=int, default=7)
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
        help="Resume using existing workspace/rtl/*.sv files.",
    )
    parser.add_argument("--external-vivado-bundle", type=Path)
    parser.add_argument("--resume-state", type=Path, help="Resume saved state; rerun verification before Vivado")
    parser.add_argument("--vivado-config", type=Path, help="JSON with explicit part, clock_port, period_ns and optional xdc")
    parser.add_argument("--vivado-executable", default="vivado")
    parser.add_argument("--vivado-timeout", type=int, default=3600)
    parser.add_argument("--max-ppa-iterations", type=int, default=3)
    parser.add_argument("--max-verifier-revisions", type=int, default=7)
    parser.add_argument("--max-contract-review-revisions", type=int, default=3)
    parser.add_argument("--max-architecture-escalations", type=int, default=3)
    parser.add_argument(
        "--verification-only",
        action="store_true",
        help=(
            "Stop successfully after deterministic Verilator/cocotb verification; "
            "do not invoke Vivado synthesis or PPA optimization."
        ),
    )
    parser.add_argument("--ppa-objective", choices=["lut", "estimated_power_w", "critical_path_delay_ns"], default="lut")
    args = parser.parse_args()
    if args.resume_state:
        resume_metadata = json.loads(args.resume_state.read_text())
        saved_workspace = Path(resume_metadata.get('workspace_root', args.resume_state.resolve().parent.parent))
        if saved_workspace.resolve() != WORKSPACE_ROOT.resolve():
            parser.error(f"Set NPU_WORKSPACE_ROOT={saved_workspace} before resuming; refusing to mix workspaces")
        args.request = args.request or resume_metadata['user_request']
        args.run_id = args.run_id or resume_metadata['run_id']
    if not args.request or not args.run_id:
        parser.error("A new run requires --request and --run-id")
    saved_model = resume_metadata.get('model') if args.resume_state else None
    if saved_model and args.model and saved_model != args.model:
        parser.error('A resumed run keeps its original model. Start a new run to switch models.')
    selected_model = args.model or saved_model or os.getenv('NPU_AGENT_MODEL', DEFAULT_MODEL)
    try:
        validate_model(selected_model)
    except ValueError as exc:
        parser.error(str(exc))
    os.environ['NPU_AGENT_MODEL'] = selected_model
    import re
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.run_id):
        parser.error("run-id must be a safe filename component")
    if min(args.max_ppa_iterations, args.max_verifier_revisions) < 0 or args.vivado_timeout <= 0:
        parser.error("Invalid iteration or timeout budget")

    if min(args.max_contract_review_revisions, args.max_architecture_escalations) < 0:
        parser.error("Review and escalation budgets must be nonnegative")
    if args.max_architecture_revisions < 0:
        raise ValueError("--max-architecture-revisions must be >= 0")
    if args.max_repair_iterations < 0:
        raise ValueError("--max-repair-iterations must be >= 0")
    if args.use_existing_rtl and not args.use_frozen_architecture:
        raise ValueError("--use-existing-rtl requires --use-frozen-architecture")

    graph = build_workflow_graph()
    initial: HardwareDesignState = {
        "run_id": args.run_id,
        "model": selected_model,
        "workspace_root": str(WORKSPACE_ROOT),
        "user_request": args.request.strip(),
        "architecture_dir": str(args.architecture_dir),
        "architecture_version": 0,
        "architecture_revision": 0,
        "max_architecture_revisions": args.max_architecture_revisions,
        "rtl_task_type": "INITIAL_GENERATION",
        "repair_iteration": 0,
        "repair_cycle_iteration": 0,
        "architecture_escalation": 0,
        "contract_review_revision": 0,
        "max_contract_review_revisions": args.max_contract_review_revisions,
        "max_architecture_escalations": args.max_architecture_escalations,
        "max_repair_iterations": args.max_repair_iterations,
        "ppa_iteration": 0,
        "max_ppa_iterations": args.max_ppa_iterations,
        "max_verifier_revisions": args.max_verifier_revisions,
        "verification_only": args.verification_only,
        "max_diagnostic_iterations": 2,
        "diagnostic_iteration": 0,
        "verifier_revision": 0,
        "vivado_config": json.loads(args.vivado_config.read_text()) if args.vivado_config else {},
        "vivado_executable": args.vivado_executable,
        "vivado_timeout": args.vivado_timeout,
        "ppa_objective": args.ppa_objective,
        "history": [],
        "errors": [],
        "status": "RUNNING",
    }

    if args.resume_state:
        saved = json.loads(args.resume_state.read_text())
        if saved.get("user_request") != args.request.strip() or saved.get("run_id") != args.run_id:
            parser.error("Resume must use the exact original request and run-id")
        initial.update(saved)
        initial.update(status="RUNNING", orchestration_error=None)
        # Resuming must not expand the recorded retry budget; CLI can lower it.
        initial["max_architecture_revisions"] = min(
            int(saved.get("max_architecture_revisions", 0)),
            args.max_architecture_revisions,
        )
        initial["max_repair_iterations"] = min(
            int(saved.get("max_repair_iterations", 0)), args.max_repair_iterations
        )
        initial["max_verifier_revisions"] = min(
            int(saved.get("max_verifier_revisions", 0)), args.max_verifier_revisions
        )
        if args.verification_only:
            initial["verification_only"] = True
        for budget in ('max_contract_review_revisions', 'max_architecture_escalations'):
            initial[budget] = min(saved.get(budget, 0), getattr(args,budget))
        initial['model'] = selected_model

    if args.vivado_config:
        initial['vivado_config'] = json.loads(args.vivado_config.read_text())
    if args.external_vivado_bundle:
        initial['external_vivado_bundle'] = str(args.external_vivado_bundle.resolve())

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

    recursion_limit = (100 + (args.max_architecture_escalations + 1) *
                       (20 * args.max_repair_iterations + 10 * args.max_verifier_revisions +
                        8 * args.max_contract_review_revisions) + 10 * args.max_ppa_iterations)
    final_state = graph.invoke(initial, {"recursion_limit": recursion_limit})
    print(
        json.dumps(
            {
                "status": final_state.get("status"),
                "vivado_status": (final_state.get("synthesis_result") or {}).get("status"),
                "final_report": final_state.get("final_report"),
                "errors": final_state.get("errors", []),
                "architecture_status": final_state.get("architecture_status"),
                "architecture_version": final_state.get("architecture_version"),
                "architecture_revision": final_state.get("architecture_revision"),
                "rtl_status": final_state.get("rtl_status"),
                "rtl_files": final_state.get("rtl_files", []),
                "verifier_status": final_state.get("verifier_status"),
                "verification_status": final_state.get("verification_status"),
                "debugger_status": final_state.get("debugger_status"),
                "repair_iteration": final_state.get("repair_iteration"),
                "failure_class": final_state.get("failure_class"),
                "architecture_conflict": final_state.get("architecture_conflict"),
            },
            indent=2,
        )
    )

    if final_state.get("status") != "SUCCESS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
