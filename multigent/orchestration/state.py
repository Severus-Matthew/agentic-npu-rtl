"""Typed state shared by LangGraph hardware-design nodes.

The state is intentionally workload-agnostic. Large artifacts remain in files or
structured handoff objects; nodes return partial updates and LangGraph owns routing.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class HardwareDesignState(TypedDict, total=False):
    """Shared state for the Architect/RTL/verification/synthesis workflow."""

    run_id: str
    user_request: str

    architecture_dir: str
    architecture_version: int
    architecture_status: str
    architecture_artifacts: dict[str, Any]
    architecture_conflict: dict[str, Any] | None
    architecture_revision: int
    max_architecture_revisions: int

    rtl_context: dict[str, Any]
    rtl_task_type: str
    rtl_feedback: dict[str, Any] | None
    rtl_status: str
    rtl_result: dict[str, Any]
    rtl_files: list[str]

    verification_context: dict[str, Any]
    verifier_status: str
    verifier_result: dict[str, Any]
    verification_plan: dict[str, Any]
    verification_status: str
    verification_evidence: dict[str, Any] | None

    diagnosis: dict[str, Any] | None
    repair_plan: dict[str, Any] | None

    synthesis_result: dict[str, Any] | None
    optimization_plan: dict[str, Any] | None

    repair_iteration: int
    max_repair_iterations: int
    ppa_iteration: int
    max_ppa_iterations: int
    needs_regression: bool

    failure_class: str | None
    status: str
    history: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
