"""Deterministic LangGraph node for RTL compile and cocotb regression."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan
from multigent.verifier_tool.coverage.operation.plan import merge_coverage_plans, operation_plan_for_tests
from multigent.verifier_tool.coverage.stimulus import HISTORY_FILE, rebuild_stimulus_history
from multigent.agents.base import AgentRuntimeError
from multigent.intake.request_builder import WORKSPACE_ROOT
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.tools.verilator import run_verilator_lint

from .state import HardwareDesignState
from .events import emit


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
    tag = f"av{architecture_version}-r{repair_iteration}-p{state.get('ppa_iteration', 0)}-v{state.get('verifier_revision', 0)}"

    rtl_dir = WORKSPACE_ROOT / "rtl"
    verification_dir = WORKSPACE_ROOT / "verification"
    reference_dir = WORKSPACE_ROOT / "reference"
    tests_dir = WORKSPACE_ROOT / "tests"
    verification_dir.mkdir(parents=True, exist_ok=True)

    top_module = str(plan["top_module"])
    for stage in ('cocotb_regression', 'protocol_checks', 'coverage_checks'):
        emit(WORKSPACE_ROOT, stage, 'pending', status='NOT_RUN')
    emit(WORKSPACE_ROOT, 'verilator_lint', 'started')
    lint = run_verilator_lint(
        rtl_dir=rtl_dir,
        top_module=top_module,
        report_path=verification_dir / f"verilator-lint-{tag}.json",
    )

    emit(WORKSPACE_ROOT, 'verilator_lint', 'finished', status=lint['status'])
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
    frozen = state["verification_context"]["frozen_architecture"]
    verifier_result = state.get("verifier_result") or {}
    coverage_plan = merge_coverage_plans(
        build_interface_coverage_plan(
            frozen["interface_contract"]
        ),
        operation_plan_for_tests(
            list(verifier_result.get("operation_coverage", [])),
            [item["content"] for item in verifier_result.get("test_files", [])],
            frozen["architecture_contract"], frozen["interface_contract"],
        ),
    )
    coverage_plan["requirements"] = {
        "randomized_transactions_minimum": int(
            state["verification_context"]["verification_policy"].get(
                "randomized_transactions_minimum", 0
            )
        )
    }
    emit(WORKSPACE_ROOT, 'cocotb_regression', 'started')
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
        coverage_plan=coverage_plan,
        coverage_report_path=verification_dir / f"functional-coverage-{tag}.json",
        stimulus_ledger_report_path=verification_dir
        / f"stimulus-ledger-{tag}.json",
    )
    checks = simulation_check_summary(simulation)
    for stage, result in checks.items():
        if stage != 'cocotb_regression':
            emit(WORKSPACE_ROOT, stage, 'started')
        emit(WORKSPACE_ROOT, stage, 'finished', **result)
    aggregate['checks'] = checks
    stimulus_history = rebuild_stimulus_history(verification_dir)
    history_summary = {
        "path": str(verification_dir / HISTORY_FILE),
        "run_count": stimulus_history["run_count"],
        "stimulus_count": stimulus_history["stimulus_count"],
        "unique_stimulus_count": stimulus_history["unique_stimulus_count"],
        "duplicate_execution_count": stimulus_history[
            "duplicate_execution_count"
        ],
    }
    simulation["stimulus_history"] = history_summary
    # run_cocotb_regression wrote its report before the cumulative history existed;
    # rewrite the versioned result so standalone readers see the same evidence.
    (verification_dir / f"cocotb-{tag}.json").write_text(
        json.dumps(simulation, indent=2) + "\n", encoding="utf-8"
    )
    aggregate["cocotb"] = simulation
    aggregate["stimulus_history"] = history_summary

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
    coverage_failure = simulation["status"] == "COVERAGE_FAILURE"
    aggregate["status"] = "COVERAGE_FAILURE" if coverage_failure else "SIMULATION_FAILURE"
    aggregate["failure_class"] = failure_class
    _write_aggregate(verification_dir, tag, aggregate)
    return _state_update(
        verification_status=(
            "COVERAGE_FAILURE"
            if coverage_failure
            else "SIMULATION_TIMEOUT"
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


def simulation_check_summary(simulation):
    """Separate views of one simulator run; never infer a pass from absent evidence."""
    coverage = simulation.get('functional_coverage') or {}
    completed = simulation.get('status') in {'PASS', 'COVERAGE_FAILURE'}
    failures = [record for record in coverage.get('failure_records', [])
                if 'protocol' in str(record.get('category', '')).lower()]
    protocol = ('FAIL' if failures else 'PASS' if completed and coverage.get('samples', 0) > 0
                and not coverage.get('assertion_failures') else 'INCOMPLETE')
    return {
        'cocotb_regression': {'status': 'PASS' if completed else simulation.get('status', 'NOT_RUN'),
                             'tests': simulation.get('tests', 0), 'failures': simulation.get('failures', 0)},
        'protocol_checks': {'status': protocol, 'failures': failures,
                            'scope': 'Contract monitor observations from this simulation'},
        'coverage_checks': {'status': coverage.get('status', 'NOT_RUN'),
                            'hit_bins': coverage.get('hit_bins', 0),
                            'required_bins': coverage.get('required_bins', 0),
                            'missing_bins': coverage.get('missing_bins', [])},
    }
