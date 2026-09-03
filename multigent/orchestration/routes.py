"""Deterministic routing functions for LangGraph workflow edges."""

from __future__ import annotations

from typing import Literal

from .state import HardwareDesignState


StartRoute = Literal["architect", "rtl_generator", "verifier", "verification_tools"]
ArchitectRoute = Literal["rtl_generator", "failed"]
RTLRoute = Literal["architect", "verifier", "failed"]
VerifierRoute = Literal["architect", "verification_tools", "failed"]
VerificationRoute = Literal["synthesis", "repair_required", "tool_unavailable"]


def route_start(state: HardwareDesignState) -> StartRoute:
    """Resume from the most advanced explicitly supplied validated checkpoint."""

    if state.get("architecture_status") == "READY":
        if (
            state.get("rtl_status") == "RTL_GENERATED"
            and state.get("verifier_status") == "VERIFICATION_READY"
            and state.get("verification_plan")
        ):
            return "verification_tools"
        if state.get("rtl_status") == "RTL_GENERATED":
            return "verifier"
        if state.get("rtl_context"):
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
    """Route RTL status without letting the implementation LLM control workflow."""

    status = state.get("rtl_status")
    if status == "RTL_GENERATED":
        return "verifier"
    if status == "ARCHITECTURE_CONFLICT":
        return "architect" if _architecture_revision_available(state) else "failed"
    if status == "REPAIR_BLOCKED":
        return "failed"
    raise ValueError(f"Cannot route unknown rtl_status={status!r}")


def route_after_verifier(state: HardwareDesignState) -> VerifierRoute:
    """Verifier artifacts go to tools; contract ambiguity returns to Architect."""

    status = state.get("verifier_status")
    if status == "VERIFICATION_READY":
        return "verification_tools"
    if status == "ARCHITECTURE_CONFLICT":
        return "architect" if _architecture_revision_available(state) else "failed"
    raise ValueError(f"Cannot route unknown verifier_status={status!r}")


def route_after_verification(state: HardwareDesignState) -> VerificationRoute:
    """Only deterministic tool status determines functional pass/fail routing."""

    status = state.get("verification_status")
    if status == "PASS":
        return "synthesis"
    if status == "TOOL_UNAVAILABLE":
        return "tool_unavailable"
    if status in {
        "COMPILE_FAILURE",
        "SIMULATION_FAILURE",
        "SIMULATION_TIMEOUT",
    }:
        return "repair_required"
    raise ValueError(f"Cannot route unknown verification_status={status!r}")


def _architecture_revision_available(state: HardwareDesignState) -> bool:
    current = int(state.get("architecture_revision", 0))
    maximum = int(state.get("max_architecture_revisions", 2))
    return current < maximum
