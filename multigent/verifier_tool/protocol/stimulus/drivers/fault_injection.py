"""Explicit, simulation-only protocol fault plans for checker qualification.

Production campaigns do not set ``NPU_PROTOCOL_FAULT_PLAN`` and therefore take
the zero-overhead no-fault path.  Qualification runners may point that variable
at one JSON document.  The document is deliberately closed and exact: a fault
targets one protocol profile/group and names one supported wire-level defect.

This module does not decide what should be verified and never changes a frozen
contract or feature plan.  It only gives benchmark/evaluation code a reusable
way to make an environment-owned response violate a selected rule, analogous
to applying one exact RTL mutation to a DUT-owned signal.
"""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Any, Mapping


FAULT_PLAN_ENV = "NPU_PROTOCOL_FAULT_PLAN"

AXI4_RESPONSE_FAULTS = frozenset({
    "present_response_before_request",
    "return_nonmatching_id",
    "invert_rlast_on_nonfinal_or_final_beat",
    "return_exokay_for_nonexclusive_request",
    "accept_invalid_write_strobe_for_checker",
})


class ProtocolFaultPlanError(ValueError):
    """A qualification-only protocol fault plan is malformed."""


def validate_protocol_fault_plan(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one closed simulation fault declaration."""

    if not isinstance(raw, Mapping):
        raise ProtocolFaultPlanError("protocol fault plan must be an object")
    allowed = {"schema_version", "profile", "group", "fault", "occurrence"}
    unknown = sorted(set(raw) - allowed)
    missing = sorted({"schema_version", "profile", "group", "fault"} - set(raw))
    if missing or unknown:
        raise ProtocolFaultPlanError(
            f"protocol fault plan fields: missing={missing}; unknown={unknown}"
        )
    if raw["schema_version"] != 1:
        raise ProtocolFaultPlanError("protocol fault plan needs schema_version=1")
    if raw["profile"] != "axi4":
        raise ProtocolFaultPlanError("only profile='axi4' qualification faults are implemented")
    group = raw["group"]
    if not isinstance(group, str) or not group:
        raise ProtocolFaultPlanError("protocol fault plan group must be a nonempty string")
    fault = raw["fault"]
    if fault not in AXI4_RESPONSE_FAULTS:
        raise ProtocolFaultPlanError(
            f"unsupported AXI4 qualification fault {fault!r}; supported={sorted(AXI4_RESPONSE_FAULTS)!r}"
        )
    occurrence = raw.get("occurrence", 1)
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise ProtocolFaultPlanError("protocol fault plan occurrence must be a positive integer")
    return {
        "schema_version": 1,
        "profile": "axi4",
        "group": group,
        "fault": str(fault),
        "occurrence": occurrence,
    }


@lru_cache(maxsize=1)
def load_protocol_fault_plan() -> dict[str, Any] | None:
    """Load the optional plan named by ``NPU_PROTOCOL_FAULT_PLAN`` once."""

    configured = os.environ.get(FAULT_PLAN_ENV, "").strip()
    if not configured:
        return None
    path = Path(configured)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolFaultPlanError(
            f"cannot load protocol fault plan {path}: {exc}"
        ) from exc
    return validate_protocol_fault_plan(raw)


def resolved_axi4_fault(group: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the active plan only when it exactly targets ``group``."""

    plan = load_protocol_fault_plan()
    if plan is None:
        return None
    if group.get("profile") != plan["profile"] or str(group.get("name", "")) != plan["group"]:
        return None
    return dict(plan)


__all__ = [
    "AXI4_RESPONSE_FAULTS",
    "FAULT_PLAN_ENV",
    "ProtocolFaultPlanError",
    "load_protocol_fault_plan",
    "resolved_axi4_fault",
    "validate_protocol_fault_plan",
]
