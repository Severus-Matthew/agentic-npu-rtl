"""Build only the Verifier-owned portion of a Debugger handoff.

This module deliberately knows nothing about Architect contracts, generated RTL,
Debugger policy, API clients, LangGraph, or workspace layout. A later pipeline
combines this Verifier feedback with its separately owned architecture and RTL
inputs before invoking Debugger.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any


_VERIFICATION_FAILURE_STATUSES = {
    "COMPILE_FAILURE",
    "SIMULATION_FAILURE",
    "SIMULATION_TIMEOUT",
    "COVERAGE_FAILURE",
}


class DebuggerFeedbackError(ValueError):
    """Verifier-to-Debugger evidence is incomplete or contains foreign state."""


def bound_debugger_evidence(value: Any, limit: int = 6000) -> Any:
    """Return a bounded deep copy while retaining each long string's endpoints."""

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 300:
        raise DebuggerFeedbackError("Debugger evidence limit must be an integer >= 300")
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        prefix = limit // 3
        suffix = 2 * limit // 3
        return (
            value[:prefix]
            + "\n[TRUNCATED: full evidence retained in run artifacts]\n"
            + value[-suffix:]
        )
    if isinstance(value, Mapping):
        return {
            str(key): bound_debugger_evidence(item, limit)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [bound_debugger_evidence(item, limit) for item in value[-128:]]
    if isinstance(value, tuple):
        return [bound_debugger_evidence(item, limit) for item in value[-128:]]
    return copy.deepcopy(value)


def build_failed_run_artifacts(
    verification_evidence: Mapping[str, Any],
    *,
    coverage_plan: Mapping[str, Any] | None = None,
    coverage_report: Mapping[str, Any] | None = None,
    stimulus_ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select root-cause-relevant rows from Verifier-side measured artifacts.

    File loading stays in the pipeline adapter. This function owns only the
    stable selection contract, so changing artifact storage cannot change what
    the Verifier tells Debugger.
    """

    cocotb = verification_evidence.get("cocotb")
    cocotb = cocotb if isinstance(cocotb, Mapping) else {}
    functional_summary = cocotb.get("functional_coverage")
    functional_summary = (
        functional_summary if isinstance(functional_summary, Mapping) else {}
    )
    ledger_summary = cocotb.get("stimulus_ledger")
    ledger_summary = ledger_summary if isinstance(ledger_summary, Mapping) else {}

    selected_coverage = None
    if isinstance(coverage_report, Mapping):
        selected_coverage = {
            "path": functional_summary.get("report_path"),
            "status": coverage_report.get("status"),
            "coverage_percent": coverage_report.get("coverage_percent"),
            "assertion_failures": list(
                coverage_report.get("assertion_failures", [])
            ),
            "failure_records": list(coverage_report.get("failure_records", [])),
            "last_observed_snapshot": dict(
                coverage_report.get("last_observed_snapshot", {})
            ),
            "operation_sampling": list(
                coverage_report.get("operation_sampling", [])
            ),
        }

    selected_ledger = None
    if isinstance(stimulus_ledger, Mapping):
        records = stimulus_ledger.get("records", [])
        records = records if isinstance(records, list) else []
        selected_ledger = {
            "path": ledger_summary.get("path"),
            "status": stimulus_ledger.get("status"),
            "most_recent_checked_stimuli": copy.deepcopy(records[-8:]),
        }

    return {
        "coverage_plan": copy.deepcopy(dict(coverage_plan))
        if isinstance(coverage_plan, Mapping)
        else None,
        "coverage_report": selected_coverage,
        "stimulus_ledger": selected_ledger,
    }


def build_verifier_debugger_feedback(
    *,
    verification_status: str,
    failure_class: str,
    verification_evidence: Mapping[str, Any],
    failed_run_artifacts: Mapping[str, Any],
    frozen_reference: Mapping[str, str],
    frozen_tests: Mapping[str, str],
    verification_plan: Mapping[str, Any],
    operation_coverage: list[Mapping[str, Any]],
    evidence_limit: int = 6000,
) -> dict[str, Any]:
    """Assemble the complete and exclusive Verifier-to-Debugger payload."""

    payload = {
        "schema_version": 1,
        "source": "verifier_tool",
        "verification_status": str(verification_status),
        "failure_class": str(failure_class),
        "verification_evidence": bound_debugger_evidence(
            dict(verification_evidence), evidence_limit
        ),
        "failed_run_artifacts": bound_debugger_evidence(
            dict(failed_run_artifacts), evidence_limit
        ),
        "frozen_verifier": {
            "reference": copy.deepcopy(dict(frozen_reference)),
            "tests": copy.deepcopy(dict(frozen_tests)),
            "verification_plan": copy.deepcopy(dict(verification_plan)),
            "operation_coverage": copy.deepcopy(list(operation_coverage)),
        },
        "provenance": {
            "deterministic_evidence_authoritative": True,
            "verifier_artifacts_frozen": True,
            "coverage_hits_are_measured": True,
        },
    }
    validate_verifier_debugger_feedback(payload)
    return payload


def validate_verifier_debugger_feedback(payload: Mapping[str, Any]) -> None:
    """Reject missing evidence and any Architect/RTL/Debugger-owned state."""

    required = {
        "schema_version",
        "source",
        "verification_status",
        "failure_class",
        "verification_evidence",
        "failed_run_artifacts",
        "frozen_verifier",
        "provenance",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise DebuggerFeedbackError(f"Verifier Debugger feedback missing fields: {missing}")
    foreign = {
        "current_rtl",
        "frozen_architecture",
        "root_cause_policy",
        "prior_diagnosis",
        "prior_repair_plan",
        "repair_iteration",
        "rtl_feedback",
    } & set(payload)
    if foreign:
        raise DebuggerFeedbackError(
            f"Verifier Debugger feedback contains non-Verifier fields: {sorted(foreign)}"
        )
    if payload.get("schema_version") != 1 or payload.get("source") != "verifier_tool":
        raise DebuggerFeedbackError("Verifier Debugger feedback identity is invalid")
    if payload.get("verification_status") not in _VERIFICATION_FAILURE_STATUSES:
        raise DebuggerFeedbackError("Verifier Debugger feedback requires a failure status")
    if not str(payload.get("failure_class", "")).strip():
        raise DebuggerFeedbackError("Verifier Debugger feedback failure_class is required")
    if not isinstance(payload.get("verification_evidence"), Mapping):
        raise DebuggerFeedbackError("verification_evidence must be a mapping")
    artifacts = payload.get("failed_run_artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != {
        "coverage_plan",
        "coverage_report",
        "stimulus_ledger",
    }:
        raise DebuggerFeedbackError(
            "failed_run_artifacts must contain exactly coverage_plan, "
            "coverage_report, and stimulus_ledger"
        )
    frozen = payload.get("frozen_verifier")
    if not isinstance(frozen, Mapping) or set(frozen) != {
        "reference",
        "tests",
        "verification_plan",
        "operation_coverage",
    }:
        raise DebuggerFeedbackError("frozen_verifier has an invalid field set")
    for name in ("reference", "tests"):
        sources = frozen.get(name)
        if not isinstance(sources, Mapping) or not sources or not all(
            isinstance(path, str) and path.endswith(".py") and isinstance(source, str)
            for path, source in sources.items()
        ):
            raise DebuggerFeedbackError(
                f"frozen_verifier.{name} requires non-empty .py source mappings"
            )
    if not isinstance(frozen.get("verification_plan"), Mapping):
        raise DebuggerFeedbackError("frozen_verifier.verification_plan must be a mapping")
    if not isinstance(frozen.get("operation_coverage"), list):
        raise DebuggerFeedbackError("frozen_verifier.operation_coverage must be a list")
    if payload.get("provenance") != {
        "deterministic_evidence_authoritative": True,
        "verifier_artifacts_frozen": True,
        "coverage_hits_are_measured": True,
    }:
        raise DebuggerFeedbackError("Verifier Debugger feedback provenance is invalid")
