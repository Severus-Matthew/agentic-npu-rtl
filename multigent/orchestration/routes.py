"""Deterministic routing functions for LangGraph workflow edges."""

from __future__ import annotations

from typing import Literal

from .state import HardwareDesignState


StartRoute = Literal["architect", "rtl_generator"]
ArchitectRoute = Literal["rtl_generator", "failed"]
RTLRoute = Literal["architect", "verification", "failed"]


def route_start(state: HardwareDesignState) -> StartRoute:
    """Reuse an explicitly supplied frozen RTL context instead of rerunning Architect."""

    if state.get("architecture_status") == "READY" and state.get("rtl_context"):
        return "rtl_generator"
    return "architect"


def route_after_architect(state: HardwareDesignState) -> ArchitectRoute:
    """Continue only when Architect produced a validated READY contract."""

    status = state.get("architecture_status")
    if status == "READY":
        return "rtl_generator"
    if status == "SPEC_CONFLICT":
        return "failed"
    raise ValueError(f"Cannot route unknown architecture_status={status!r}")


def route_after_rtl(state: HardwareDesignState) -> RTLRoute:
    """Route RTL Generator status without letting the LLM choose graph control flow."""

    status = state.get("rtl_status")
    if status == "RTL_GENERATED":
        return "verification"
    if status == "ARCHITECTURE_CONFLICT":
        current = int(state.get("architecture_revision", 0))
        maximum = int(state.get("max_architecture_revisions", 2))
        return "architect" if current < maximum else "failed"
    if status == "REPAIR_BLOCKED":
        return "failed"
    raise ValueError(f"Cannot route unknown rtl_status={status!r}")
