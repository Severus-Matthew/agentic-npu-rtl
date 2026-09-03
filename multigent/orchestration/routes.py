"""Deterministic routing functions for LangGraph workflow edges."""

from __future__ import annotations

from typing import Literal

from .state import HardwareDesignState


StartRoute = Literal["architect", "rtl_generator", "verifier", "verification_tools"]
ArchitectRoute = Literal["rtl_generator", "failed"]
RTLRoute = Literal["architect", "verifier", "verification_tools", "failed"]
VerifierRoute = Literal["architect", "verification_tools", "failed"]
VerificationRoute = Literal[
    "synthesis", "debugger", "repair_exhausted", "tool_unavailable"
]
DebuggerRoute = Literal["rtl_generator", "architect", "failed"]


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
    status = state.get("architecture_status")
    if status == "READY":
        return "rtl_generator"
    if status == "SPEC_CONFLICT":
        return "failed"
    raise ValueError(f"Cannot route unknown architecture_status={status!r}")


def route_after_rtl(state: HardwareDesignState) -> RTLRoute:
    """Keep the verifier frozen across RTL-only repair iterations."""

    status = state.get("rtl_status")
    if status == "RTL_GENERATED":
        repair_mode = state.get("rtl_task_type") in {
            "FUNCTIONAL_REPAIR",
            "SYNTHESIS_REPAIR",
            "PPA_OPTIMIZATION",
        }
        verifier_frozen = (
            state.get("verifier_status") == "VERIFICATION_READY"
            and bool(state.get("verification_plan"))
        )
        if repair_mode and verifier_frozen:
            return "verification_tools"
        return "verifier"
    if status == "ARCHITECTURE_CONFLICT":
        return "architect" if _architecture_revision_available(state) else "failed"
    if status == "REPAIR_BLOCKED":
        return "failed"
    raise ValueError(f"Cannot route unknown rtl_status={status!r}")


def route_after_verifier(state: HardwareDesignState) -> VerifierRoute:
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
        return "debugger" if _repair_available(state) else "repair_exhausted"
    raise ValueError(f"Cannot route unknown verification_status={status!r}")


def route_after_debugger(state: HardwareDesignState) -> DebuggerRoute:
    status = state.get("debugger_status")
    if status == "REPAIR_PLAN_READY":
        return "rtl_generator"
    if status == "ARCHITECTURE_ESCALATION":
        return "architect" if _architecture_revision_available(state) else "failed"
    if status == "EVIDENCE_INSUFFICIENT":
        return "failed"
    raise ValueError(f"Cannot route unknown debugger_status={status!r}")


def _architecture_revision_available(state: HardwareDesignState) -> bool:
    current = int(state.get("architecture_revision", 0))
    maximum = int(state.get("max_architecture_revisions", 2))
    return current < maximum


def _repair_available(state: HardwareDesignState) -> bool:
    current = int(state.get("repair_iteration", 0))
    maximum = int(state.get("max_repair_iterations", 5))
    return current < maximum
