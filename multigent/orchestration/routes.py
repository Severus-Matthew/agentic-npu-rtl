"""Deterministic routing functions for LangGraph workflow edges."""

from __future__ import annotations

from typing import Literal

from .state import HardwareDesignState


StartRoute = Literal["architect", "rtl_generator", "verifier", "verifier_review", "verification_tools", "verification_repair", "diagnostic_probe", "debugger", "failed"]
ArchitectRoute = Literal["architect", "verifier", "failed"]
RTLRoute = Literal["architect", "verifier", "verification_tools", "failed"]
VerifierRoute = Literal["architect", "verifier_review", "verification_repair", "failed"]
VerifierReviewRoute = Literal["rtl_generator", "verification_tools", "verification_repair", "failed"]
VerificationRoute = Literal[
    "synthesis", "final_report", "debugger", "verification_repair", "repair_exhausted", "tool_unavailable", "failed"
]
DebuggerRoute = Literal["rtl_generator", "verification_repair", "diagnostic_probe", "failed"]


def route_start(state: HardwareDesignState) -> StartRoute:
    """Resume from the most advanced explicitly supplied validated checkpoint."""

    history = state.get("history", [])
    if history and history[-1].get("status") == "ERROR" and history[-1].get("stage") in {"architect","rtl_generator","verifier","verifier_review","debugger","verification_tools"}:
        return history[-1]["stage"]
    if state.get("debugger_status") == "EVIDENCE_INSUFFICIENT" and state.get("max_diagnostic_iterations",0)>state.get("diagnostic_iteration",0):
        return "diagnostic_probe"
    if state.get("architecture_status") == "READY":
        if state.get("verifier_status") == "VERIFICATION_READY" and state.get("verification_plan"):
            if state.get("verifier_review_status") in {"APPROVED", "VERIFIER_REPAIR_REQUIRED"}:
                return route_after_verifier_review(state)
            return "verifier_review"
        return "verifier"
    return "architect"


def route_after_architect(state: HardwareDesignState) -> ArchitectRoute:
    status = state.get("architecture_status")
    if status == "READY":
        return "verifier"
    if status == "SPEC_CONFLICT":
        return "failed"
    if status == "SEMANTIC_VALIDATION_FAILED":
        return "architect" if _architecture_revision_available(state) else "failed"
    raise ValueError(f"Cannot route unknown architecture_status={status!r}")


def route_after_rtl(state: HardwareDesignState) -> RTLRoute:
    """Keep the verifier frozen across RTL-only repair iterations."""

    status = state.get("rtl_status")
    if status == "RTL_GENERATED":
        verifier_frozen = (
            state.get("verifier_status") == "VERIFICATION_READY"
            and bool(state.get("verification_plan"))
            and state.get("verifier_review_status") == "APPROVED"
        )
        if verifier_frozen:
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
        return "verifier_review"
    if status == "ARCHITECTURE_CONFLICT":
        return "architect" if _architecture_revision_available(state) else "failed"
    if status == "SEMANTIC_VALIDATION_FAILED":
        return "verification_repair" if _verifier_repair_available(state) else "failed"
    raise ValueError(f"Cannot route unknown verifier_status={status!r}")


def route_after_verifier_review(state: HardwareDesignState) -> VerifierReviewRoute:
    status = state.get("verifier_review_status")
    if status == "APPROVED":
        if state.get("rtl_task_type") == "CONTRACT_FIXED":
            return "rtl_generator"
        return "verification_tools" if state.get("rtl_status") == "RTL_GENERATED" else "rtl_generator"
    if status == "VERIFIER_REPAIR_REQUIRED":
        return "verification_repair" if _verifier_repair_available(state) else "failed"
    raise ValueError(f"Cannot route unknown verifier_review_status={status!r}")


def route_after_verification(state: HardwareDesignState) -> VerificationRoute:
    """Only deterministic tool status determines functional pass/fail routing."""

    status = state.get("verification_status")
    if status == "PASS":
        return "final_report" if state.get("verification_only") else "synthesis"
    if status == "TOOL_UNAVAILABLE":
        return "tool_unavailable"
    if status == "COVERAGE_FAILURE":
        return "verification_repair" if _verifier_repair_available(state) else "failed"
    if status in {
        "COMPILE_FAILURE",
        "SIMULATION_FAILURE",
        "SIMULATION_TIMEOUT",
    }:
        return "debugger" if _repair_available(state) else "repair_exhausted"
    raise ValueError(f"Cannot route unknown verification_status={status!r}")


def route_after_debugger(state: HardwareDesignState) -> DebuggerRoute:
    status = state.get("debugger_status")
    if status == "VERIFICATION_REPAIR_REQUIRED":
        return "verification_repair" if _verifier_repair_available(state) else "failed"
    if status == "REPAIR_PLAN_READY":
        return "rtl_generator"
    if status == "EVIDENCE_INSUFFICIENT":
        return "diagnostic_probe" if state.get("max_diagnostic_iterations", 0) > state.get("diagnostic_iteration", 0) else "failed"
    raise ValueError(f"Cannot route unknown debugger_status={status!r}")


def _architecture_revision_available(state: HardwareDesignState) -> bool:
    current = int(state.get("architecture_revision", 0))
    maximum = int(state.get("max_architecture_revisions", 2))
    return current < maximum


def _repair_available(state: HardwareDesignState) -> bool:
    current = int(state.get("repair_iteration", 0))
    maximum = int(state.get("max_repair_iterations", 5))
    return current < maximum


def _verifier_repair_available(state):
    # A new contract needs an independent verifier and its own bounded repair budget.
    # Keep the global revision ID monotonic for unique artifact names.
    history=state.get('history',[])
    architectures=[
        i for i,event in enumerate(history)
        if event.get('stage')=='architect'
        and event.get('status')=='READY'
        and event.get('architect_decision')!='CONTRACT_CONFIRMED'
    ]
    used=state.get('verifier_revision',0)
    if architectures:
        used=sum(event.get('stage')=='verification_repair' for event in history[architectures[-1]+1:])
    return used < state.get('max_verifier_revisions',2)
