"""Deterministic routing functions for LangGraph workflow edges."""

from __future__ import annotations

from typing import Literal

from .state import HardwareDesignState


RTLRoute = Literal["architect", "verification", "failed"]


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
