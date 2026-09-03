from __future__ import annotations

from multigent.orchestration.graph import build_architect_rtl_graph
from multigent.orchestration.routes import route_after_architect, route_after_rtl


def test_langgraph_compiles_expected_architect_rtl_nodes() -> None:
    class StubArchitect:
        pass

    class StubRTL:
        pass

    graph = build_architect_rtl_graph(  # type: ignore[arg-type]
        architect_agent=StubArchitect(),
        rtl_agent=StubRTL(),
    )
    nodes = set(graph.get_graph().nodes)
    assert {"architect", "rtl_generator", "verification", "failed"} <= nodes


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


def test_generated_rtl_routes_to_verification() -> None:
    assert route_after_rtl({"rtl_status": "RTL_GENERATED"}) == "verification"
