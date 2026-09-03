"""Deterministic LangGraph node for RTL compile and cocotb regression."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from multigent.agents.base import AgentRuntimeError
from multigent.intake.request_builder import WORKSPACE_ROOT
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.tools.verilator import run_verilator_lint

from .state import HardwareDesignState


def verification_tools_node(state: HardwareDesignState) -> dict[str, Any]:
    """Run deterministic lint/elaboration first, then full cocotb regression."""

    if state.get("verifier_status") != "VERIFICATION_READY":
        raise AgentRuntimeError(
            "Deterministic verification requires verifier_status=VERIFICATION_READY"
        )
    plan = state.get("verification_plan")
    if not isinstance(plan, dict):
        raise AgentRuntimeError("verification_plan missing from graph state")

    architecture_version = int(state.get("architecture_version", 0))
    repair_iteration = int(state.get("repair_iteration", 0))
    tag = f"av{architecture_version}-r{repair_iteration}"

    rtl_dir = WORKSPACE_ROOT / "rtl"
    verification_dir = WORKSPACE_ROOT / "verification"
    reference_dir = WORKSPACE_ROOT / "reference"
    tests_dir = WORKSPACE_ROOT / "tests"
    verification_dir.mkdir(parents=True, exist_ok=True)

    top_module = str(plan["top_module"])
    lint = run_verilator_lint(
        rtl_dir=rtl_dir,
        top_module=top_module,
        report_path=verification_dir / f"verilator-lint-{tag}.json",
    )

    aggregate: dict[str, Any] = {
        "architecture_version": architecture_version,
        "repair_iteration": repair_iteration,
        "top_module": top_module,
        "regression_scope": "FULL",
        "verilator": lint,
        "cocotb": None,
    }

    if lint["status"] == "TOOL_UNAVAILABLE":
        aggregate["status"] = "TOOL_UNAVAILABLE"
        aggregate["failure_class"] = None
        _write_aggregate(verification_dir, tag, aggregate)
        return _state_update(
            verification_status="TOOL_UNAVAILABLE",
            evidence=aggregate,
            failure_class=None,
            status="VERIFICATION_TOOL_UNAVAILABLE",
        )

    if lint["status"] == "TIMEOUT":
        aggregate["status"] = "COMPILE_FAILURE"
        aggregate["failure_class"] = lint["failure_class"]
        _write_aggregate(verification_dir, tag, aggregate)
        return _state_update(
            verification_status="COMPILE_FAILURE",
            evidence=aggregate,
            failure_class=str(lint["failure_class"] or "UNKNOWN"),
            status="REPAIR_REQUIRED",
        )

    if lint["status"] != "PASS":
        aggregate["status"] = "COMPILE_FAILURE"
        aggregate["failure_class"] = lint["failure_class"]
        _write_aggregate(verification_dir, tag, aggregate)
        return _state_update(
            verification_status="COMPILE_FAILURE",
            evidence=aggregate,
            failure_class=str(lint["failure_class"] or "UNKNOWN"),
            status="REPAIR_REQUIRED",
        )

    test_modules = [str(item) for item in plan["regression_groups"]["full"]]
    simulation = run_cocotb_regression(
        rtl_dir=rtl_dir,
        top_module=top_module,
        tests_dir=tests_dir,
        reference_dir=reference_dir,
        test_modules=test_modules,
        seed=int(plan["seed"]),
        build_dir=verification_dir / "build" / tag,
        report_path=verification_dir / f"cocotb-{tag}.json",
        timeout_seconds=int(plan["timeout_seconds"]),
    )
    aggregate["cocotb"] = simulation

    if simulation["status"] == "TOOL_UNAVAILABLE":
        aggregate["status"] = "TOOL_UNAVAILABLE"
        aggregate["failure_class"] = None
        _write_aggregate(verification_dir, tag, aggregate)
        return _state_update(
            verification_status="TOOL_UNAVAILABLE",
            evidence=aggregate,
            failure_class=None,
            status="VERIFICATION_TOOL_UNAVAILABLE",
        )

    if simulation["status"] == "PASS":
        aggregate["status"] = "PASS"
        aggregate["failure_class"] = None
        _write_aggregate(verification_dir, tag, aggregate)
        return _state_update(
            verification_status="PASS",
            evidence=aggregate,
            failure_class=None,
            status="VERIFIED_RTL",
        )

    failure_class = str(simulation.get("failure_class") or "UNKNOWN")
    aggregate["status"] = "SIMULATION_FAILURE"
    aggregate["failure_class"] = failure_class
    _write_aggregate(verification_dir, tag, aggregate)
    return _state_update(
        verification_status=(
            "SIMULATION_TIMEOUT"
            if simulation["status"] == "TIMEOUT"
            else "SIMULATION_FAILURE"
        ),
        evidence=aggregate,
        failure_class=failure_class,
        status="REPAIR_REQUIRED",
    )


def _state_update(
    *,
    verification_status: str,
    evidence: dict[str, Any],
    failure_class: str | None,
    status: str,
) -> dict[str, Any]:
    return {
        "verification_status": verification_status,
        "verification_evidence": evidence,
        "failure_class": failure_class,
        "status": status,
        "needs_regression": verification_status != "PASS",
        "history": [
            {
                "stage": "deterministic_verification",
                "status": verification_status,
                "failure_class": failure_class,
            }
        ],
    }


def _write_aggregate(
    verification_dir: Path,
    tag: str,
    result: dict[str, Any],
) -> None:
    path = verification_dir / f"verification-result-{tag}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
