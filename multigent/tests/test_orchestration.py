from __future__ import annotations

from multigent.orchestration.graph import build_workflow_graph
from multigent.orchestration.routes import (
    route_after_architect,
    route_after_rtl,
    route_after_verification,
    route_after_verifier,
    route_start,
)


def test_langgraph_compiles_verification_nodes() -> None:
    class StubArchitect:
        pass

    class StubRTL:
        pass

    class StubVerifier:
        pass

    graph = build_workflow_graph(  # type: ignore[arg-type]
        architect_agent=StubArchitect(),
        rtl_agent=StubRTL(),
        verifier_agent=StubVerifier(),
    )
    nodes = set(graph.get_graph().nodes)
    assert {
        "architect",
        "rtl_generator",
        "verifier",
        "verification_tools",
        "synthesis",
        "repair_required",
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


def test_generated_rtl_routes_to_independent_verifier() -> None:
    assert route_after_rtl({"rtl_status": "RTL_GENERATED"}) == "verifier"


def test_verifier_ready_routes_to_deterministic_tools() -> None:
    assert route_after_verifier({"verifier_status": "VERIFICATION_READY"}) == "verification_tools"


def test_verifier_architecture_conflict_uses_revision_budget() -> None:
    state = {
        "verifier_status": "ARCHITECTURE_CONFLICT",
        "architecture_revision": 1,
        "max_architecture_revisions": 2,
    }
    assert route_after_verifier(state) == "architect"


def test_compile_failure_routes_to_repair() -> None:
    assert route_after_verification({"verification_status": "COMPILE_FAILURE"}) == "repair_required"


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
