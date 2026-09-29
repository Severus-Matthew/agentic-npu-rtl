"""HLS-golden-only protocol fault plans for checker qualification.

Production campaigns do not set ``NPU_PROTOCOL_FAULT_PLAN`` and therefore take
the zero-overhead no-fault path.  Qualification runners may point that variable
at one JSON document.  The document is deliberately closed and exact: a fault
targets one protocol profile/group and names one supported wire-level defect.

This module is deliberately benchmark-local.  The production protocol drivers
must not know about this environment variable or any mutation recipe.
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
    "change_content_on_ready_release",
    "accept_invalid_write_strobe_for_checker",
    "attempt_same_id_response_reorder",
})
AXI4_LITE_SOURCE_FAULTS = frozenset({
    "change_content_on_ready_release",
    "attempt_unpaired_write_channel",
})
AXI4_LITE_SOURCE_CHANNELS = frozenset({
    "read_address", "write_address", "write_data",
})


class ProtocolFaultPlanError(ValueError):
    """A qualification-only protocol fault plan is malformed."""


def validate_protocol_fault_plan(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one closed simulation fault declaration."""

    if not isinstance(raw, Mapping):
        raise ProtocolFaultPlanError("protocol fault plan must be an object")
    allowed = {
        "schema_version", "profile", "group", "channel", "fault", "occurrence",
    }
    unknown = sorted(set(raw) - allowed)
    missing = sorted({"schema_version", "profile", "group", "fault"} - set(raw))
    if missing or unknown:
        raise ProtocolFaultPlanError(
            f"protocol fault plan fields: missing={missing}; unknown={unknown}"
        )
    if raw["schema_version"] != 1:
        raise ProtocolFaultPlanError("protocol fault plan needs schema_version=1")
    profile = raw["profile"]
    if profile not in {"axi4", "axi4_lite"}:
        raise ProtocolFaultPlanError(
            "only profile='axi4' and profile='axi4_lite' qualification faults are implemented"
        )
    group = raw["group"]
    if not isinstance(group, str) or not group:
        raise ProtocolFaultPlanError("protocol fault plan group must be a nonempty string")
    fault = raw["fault"]
    supported = AXI4_RESPONSE_FAULTS if profile == "axi4" else AXI4_LITE_SOURCE_FAULTS
    if fault not in supported:
        raise ProtocolFaultPlanError(
            f"unsupported {profile} qualification fault {fault!r}; "
            f"supported={sorted(supported)!r}"
        )
    channel = raw.get("channel")
    if profile == "axi4_lite":
        if channel not in AXI4_LITE_SOURCE_CHANNELS:
            raise ProtocolFaultPlanError(
                "AXI4-Lite source fault needs channel in "
                f"{sorted(AXI4_LITE_SOURCE_CHANNELS)!r}"
            )
    elif channel is not None:
        raise ProtocolFaultPlanError("AXI4 response faults do not accept a channel field")
    occurrence = raw.get("occurrence", 1)
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise ProtocolFaultPlanError("protocol fault plan occurrence must be a positive integer")
    result = {
        "schema_version": 1,
        "profile": str(profile),
        "group": group,
        "fault": str(fault),
        "occurrence": occurrence,
    }
    if channel is not None:
        result["channel"] = str(channel)
    return result


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


def resolved_protocol_fault(group: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the active plan only when it exactly targets ``group``."""

    plan = load_protocol_fault_plan()
    if plan is None:
        return None
    if group.get("profile") != plan["profile"] or str(group.get("name", "")) != plan["group"]:
        return None
    return dict(plan)


def resolved_axi4_fault(group: Mapping[str, Any]) -> dict[str, Any] | None:
    """Compatibility wrapper restricted to an AXI4 target group."""

    plan = resolved_protocol_fault(group)
    return plan if plan is not None and plan["profile"] == "axi4" else None


async def change_content_on_ready_release(
    clock: Any,
    valid: Any,
    ready: Any,
    content: Any,
    *,
    timeout_cycles: int = 262_144,
) -> None:
    """Change one producer-owned bit after a real stall and before acceptance.

    This qualification-only primitive is protocol-family agnostic.  The
    profile-specific driver selects the channel and content field; this helper
    only implements the temporal defect shared by AXI4 response producers and
    AXI4-Lite request producers.
    """

    from cocotb.triggers import FallingEdge, RisingEdge, Timer

    stalled_value: int | None = None
    for _ in range(timeout_cycles):
        await RisingEdge(clock)
        await Timer(1, unit="ps")
        if int(valid.value) and not int(ready.value) and stalled_value is None:
            stalled_value = int(content.value)
        await FallingEdge(clock)
        if stalled_value is not None and int(valid.value) and int(ready.value):
            content.value = stalled_value ^ 1
            return
    raise ProtocolFaultPlanError(
        "qualification channel never reached a stalled READY release"
    )


__all__ = [
    "AXI4_RESPONSE_FAULTS",
    "AXI4_LITE_SOURCE_CHANNELS",
    "AXI4_LITE_SOURCE_FAULTS",
    "FAULT_PLAN_ENV",
    "ProtocolFaultPlanError",
    "change_content_on_ready_release",
    "load_protocol_fault_plan",
    "resolved_axi4_fault",
    "resolved_protocol_fault",
    "validate_protocol_fault_plan",
]
