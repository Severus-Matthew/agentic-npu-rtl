from __future__ import annotations

from multigent.orchestration.graph import build_workflow_graph
from multigent.orchestration.routes import (
    route_after_architect,
    route_after_debugger,
    route_after_rtl,
    route_after_verification,
    route_after_verifier,
    route_start,
)


def test_langgraph_compiles_repair_nodes() -> None:
    class StubArchitect:
        pass

    class StubRTL:
        pass

    class StubVerifier:
        pass

    class StubDebugger:
        pass

    graph = build_workflow_graph(  # type: ignore[arg-type]
        architect_agent=StubArchitect(),
        rtl_agent=StubRTL(),
        verifier_agent=StubVerifier(),
        debugger_agent=StubDebugger(),
    )
    nodes = set(graph.get_graph().nodes)
    assert {
        "architect",
        "rtl_generator",
        "verifier",
        "verification_tools",
        "debugger",
        "synthesis",
        "repair_exhausted",
        "tool_unavailable",
        "failed",
    } <= nodes


def test_architect_ready_routes_to_rtl() -> None:
    assert route_after_architect({"architecture_status": "READY"}) == "rtl_generator"


def test_rtl_conflict_routes_back_to_architect_with_budget() -> None:
    state = {
        "rtl_status": "ARCHITECTURE_CONFLICT",
        "architecture_revision": 0,
        "max_architecture_revisions": 2,
    }
    assert route_after_rtl(state) == "architect"


def test_rtl_conflict_stops_when_architecture_budget_exhausted() -> None:
    state = {
        "rtl_status": "ARCHITECTURE_CONFLICT",
        "architecture_revision": 2,
        "max_architecture_revisions": 2,
    }
    assert route_after_rtl(state) == "failed"


def test_initial_generated_rtl_routes_to_independent_verifier() -> None:
    assert route_after_rtl(
        {"rtl_status": "RTL_GENERATED", "rtl_task_type": "INITIAL_GENERATION"}
    ) == "verifier"


def test_functional_repair_reuses_frozen_verifier() -> None:
    state = {
        "rtl_status": "RTL_GENERATED",
        "rtl_task_type": "FUNCTIONAL_REPAIR",
        "verifier_status": "VERIFICATION_READY",
        "verification_plan": {"top_module": "top"},
    }
    assert route_after_rtl(state) == "verification_tools"


def test_verifier_ready_routes_to_deterministic_tools() -> None:
    assert route_after_verifier({"verifier_status": "VERIFICATION_READY"}) == "verification_tools"


def test_verifier_architecture_conflict_uses_revision_budget() -> None:
    state = {
        "verifier_status": "ARCHITECTURE_CONFLICT",
        "architecture_revision": 1,
        "max_architecture_revisions": 2,
    }
    assert route_after_verifier(state) == "architect"


def test_compile_failure_routes_to_debugger_with_budget() -> None:
    state = {
        "verification_status": "COMPILE_FAILURE",
        "repair_iteration": 0,
        "max_repair_iterations": 5,
    }
    assert route_after_verification(state) == "debugger"


def test_compile_failure_stops_when_repair_budget_exhausted() -> None:
    state = {
        "verification_status": "COMPILE_FAILURE",
        "repair_iteration": 5,
        "max_repair_iterations": 5,
    }
    assert route_after_verification(state) == "repair_exhausted"


def test_debugger_plan_routes_to_functional_repair() -> None:
    assert route_after_debugger({"debugger_status": "REPAIR_PLAN_READY"}) == "rtl_generator"


def test_debugger_architecture_escalation_uses_architecture_budget() -> None:
    state = {
        "debugger_status": "ARCHITECTURE_ESCALATION",
        "architecture_revision": 0,
        "max_architecture_revisions": 2,
    }
    assert route_after_debugger(state) == "architect"


def test_debugger_insufficient_evidence_stops() -> None:
    assert route_after_debugger({"debugger_status": "EVIDENCE_INSUFFICIENT"}) == "failed"


def test_pass_routes_to_synthesis() -> None:
    assert route_after_verification({"verification_status": "PASS"}) == "synthesis"


def test_tool_unavailable_is_not_mislabeled_as_rtl_failure() -> None:
    assert route_after_verification({"verification_status": "TOOL_UNAVAILABLE"}) == "tool_unavailable"


def test_resume_existing_rtl_starts_at_verifier() -> None:
    state = {
        "architecture_status": "READY",
        "rtl_status": "RTL_GENERATED",
        "rtl_files": ["design.sv"],
    }
    assert route_start(state) == "verifier"


def test_resume_frozen_architecture_without_rtl_starts_at_rtl() -> None:
    state = {
        "architecture_status": "READY",
        "rtl_context": {"frozen_architecture": {}},
    }
    assert route_start(state) == "rtl_generator"
