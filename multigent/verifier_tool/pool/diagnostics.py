"""Structured, owner-attributed diagnostics for operation-metadata compilation.

`build_architect_operation_metadata` compiles each operation independently. When
one cannot be compiled, the failure is recorded as a diagnostic instead of an
exception, and this module says *whose problem it is*:

* ``contract_error`` -- the frozen contract is inconsistent or under-specified;
  the Architect can fix it (owner ``architect_contract``).
* ``extension_required`` -- the contract legitimately asks for behavior the
  closed pools do not cover; a Verifier-authored extension must supply it
  (owner ``verifier_extension``).
* ``tool_capability`` -- the contract is valid but ``verifier_tool`` has no
  automatic path for it (owner ``verifier_tool``). Never an Architect error.

The category is decided once, at the first raise site, by attaching a
``reason_code`` to the exception; nothing here parses message text. Only reason
codes flagged ``architect_blocking`` are ever sent back to the Architect, and
only when no earlier validator already reports the same defect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

CONTRACT_ERROR = "contract_error"
EXTENSION_REQUIRED = "extension_required"
TOOL_CAPABILITY = "tool_capability"
CATEGORIES = (CONTRACT_ERROR, EXTENSION_REQUIRED, TOOL_CAPABILITY)

OWNER_BY_CATEGORY = {
    CONTRACT_ERROR: "architect_contract",
    EXTENSION_REQUIRED: "verifier_extension",
    TOOL_CAPABILITY: "verifier_tool",
}

DOMAIN_OPERATION_IO = "operation_io"
DOMAIN_ARITHMETIC = "arithmetic"
DOMAIN_LIFECYCLE = "lifecycle"
DOMAINS = (DOMAIN_OPERATION_IO, DOMAIN_ARITHMETIC, DOMAIN_LIFECYCLE)

CODE_OWNED = "code_owned"
AUTOMATION_STATUSES = (
    CODE_OWNED,
    "verifier_extension_required",
    "tool_capability_required",
    "contract_error",
)
AUTOMATION_STATUS_BY_CATEGORY = {
    CONTRACT_ERROR: "contract_error",
    EXTENSION_REQUIRED: "verifier_extension_required",
    TOOL_CAPABILITY: "tool_capability_required",
}

UNCLASSIFIED = "unclassified_metadata_error"


@dataclass(frozen=True)
class ReasonSpec:
    category: str
    domains: tuple[str, ...]
    hint: str
    # Sent back to the Architect by `validate_operation_compilation`. False for
    # a contract error that an earlier validator already reports (avoids a
    # duplicate message), that only a hand-authored full-metadata contract can
    # reach, or whose absence a caller may tolerate (`require_*=False`).
    architect_blocking: bool = False
    # Alternative hints selected by `details["hint_variant"]` on the raising error,
    # for a defect class whose fix differs by situation (never by message text).
    variants: Mapping[str, str] | None = None


_IO = (DOMAIN_OPERATION_IO,)
_LC = (DOMAIN_LIFECYCLE,)
_AR = (DOMAIN_ARITHMETIC,)

_CONTROL_PLANE_HINT = (
    "Fix operation.lifecycle_control_plane_sequence: every register/field/data object it "
    "names must be declared, register addresses and field bits must not collide, "
    "job_start must end in a write and job_complete in exactly one final poll_field."
)

REASONS: dict[str, ReasonSpec] = {
    # ---- operation I/O -> interface channel binding -------------------------
    "unknown_or_duplicate_data_object": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "List only declared data objects in operation inputs/outputs, each declared exactly once.",
    ),
    "unknown_or_duplicate_data_type": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Declare every data type a data object names exactly once.",
    ),
    "data_object_not_carried_by_channel": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "List every external data object in one interface channel's data_objects.",
    ),
    "data_object_channel_direction_mismatch": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "An operation input must be carried by an input channel and an output by an output "
        "channel; list the object on a channel with the matching direction.",
        architect_blocking=True,
    ),
    "ambiguous_transport_binding": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Carry each data object on exactly one channel per direction: keep it in one "
        "channel's data_objects, or split it into separately declared data objects. The "
        "tool does not take extra routing metadata to choose between channels.",
        architect_blocking=True,
        variants={
            "memory_mapped": (
                "List a memory-mapped (axi4 / axi4_lite / custom_mmio) data object only on its "
                "data channel (read_data or write_data); the address and response channels of "
                "its protocol group carry no data objects. The tool takes no extra routing "
                "metadata to choose between channels."
            ),
        },
    ),
    "internal_data_object_not_channel_bound": ReasonSpec(
        TOOL_CAPABILITY, _IO,
        "The canonical operation model binds an operation's inputs/outputs to interface "
        "channels, so an operation that consumes or produces an internal (non-external) data "
        "object has no automatic path: its required coverage cannot be met by the code-owned "
        "campaign. An operation whose inputs and outputs are all channel-carried objects "
        "(internal stages described in the module manifest instead of as separate operations) "
        "is what the tool can bind; otherwise it needs tool support for multi-stage operations.",
    ),
    "ambiguous_channel_signal_role": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Give each data channel exactly one valid, one ready and one payload signal.",
        architect_blocking=True,
    ),
    "multi_signal_role_on_data_channel": ReasonSpec(
        TOOL_CAPABILITY, _IO,
        "The canonical binding keeps one signal per role on a data channel; a second signal "
        "of the same non-handshake role is legal in the contract but outside the automatic path.",
    ),
    "missing_ready_valid_signal_roles": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Every ready_valid data channel needs signals with the roles valid, ready and payload.",
        architect_blocking=True,
    ),
    "invalid_data_object_serialization": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Fix the data object's serialization declaration.",
    ),
    "ambiguous_base_pointer": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Tag exactly one command metadata signal with data_object=<object> address_role=base "
        "for each memory-mapped data object.",
        architect_blocking=True,
    ),
    "memory_channel_kind_mismatch": ReasonSpec(
        CONTRACT_ERROR, _IO,
        "Carry an input object on a read-data (or custom data) channel and an output object "
        "on a write-data channel of its memory-mapped protocol group.",
        architect_blocking=True,
    ),
    # ---- lifecycle -----------------------------------------------------------
    "missing_lifecycle_policy": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "Select every field of operation.lifecycle_policy from the Lifecycle Policy Pool.",
    ),
    "invalid_lifecycle_policy": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "Select a supported choice for every lifecycle_policy field, or name one "
        "verification_extensions request.",
    ),
    "lifecycle_policy_conflict": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "operation.lifecycle_policy and verification_metadata.lifecycle.policy must agree.",
    ),
    "unsupported_lifecycle_policy_source": ReasonSpec(
        CONTRACT_ERROR, _LC, "Use lifecycle.policy_source=explicit_contract.",
    ),
    "lifecycle_metadata_contradiction": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "Remove the lifecycle field that contradicts the supported fixed lifecycle contract.",
    ),
    "ambiguous_status_binding": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "Bind at most one busy, one completion and one error signal.",
        architect_blocking=True,
    ),
    "conflicting_semantic_tags": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "Command metadata semantics must not repeat a tag key with different values.",
        architect_blocking=True,
    ),
    "control_plane_sequence_required_but_missing": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "When job_acceptance or completion_style selects control_plane_sequence, declare "
        "operation.lifecycle_control_plane_sequence (registers, job_start, job_complete); "
        "otherwise select a different job_acceptance/completion_style.",
        architect_blocking=True,
    ),
    "control_plane_sequence_unused": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "Remove operation.lifecycle_control_plane_sequence, or select control_plane_sequence "
        "for job_acceptance/completion_style.",
        architect_blocking=True,
    ),
    "control_plane_sequence_schema_violation": ReasonSpec(
        CONTRACT_ERROR, _LC, _CONTROL_PLANE_HINT, architect_blocking=True,
    ),
    "control_plane_sequence_address_collision": ReasonSpec(
        CONTRACT_ERROR, _LC, _CONTROL_PLANE_HINT, architect_blocking=True,
    ),
    "control_plane_sequence_unknown_reference": ReasonSpec(
        CONTRACT_ERROR, _LC, _CONTROL_PLANE_HINT, architect_blocking=True,
    ),
    "control_plane_sequence_bad_start_action": ReasonSpec(
        CONTRACT_ERROR, _LC, _CONTROL_PLANE_HINT, architect_blocking=True,
    ),
    "control_plane_sequence_bad_completion_poll": ReasonSpec(
        CONTRACT_ERROR, _LC, _CONTROL_PLANE_HINT, architect_blocking=True,
    ),
    "control_plane_requires_axi4_lite_subordinate": ReasonSpec(
        CONTRACT_ERROR, _LC,
        "control_plane_sequence is driven through an AXI4-Lite subordinate (control) channel "
        "group; declare one in the interface, or select another job_acceptance/completion_style.",
        architect_blocking=True,
    ),
    # ---- arithmetic ----------------------------------------------------------
    "missing_arithmetic_declaration": ReasonSpec(
        CONTRACT_ERROR, _AR,
        "Declare operation.arithmetic explicitly, or select classifier_profile=llm_extension "
        "with exact operations[].semantics.",
    ),
    "invalid_arithmetic_declaration": ReasonSpec(
        CONTRACT_ERROR, _AR,
        "Fix the arithmetic declaration, or select classifier_profile=llm_extension with "
        "exact operations[].semantics.",
    ),
    "arithmetic_declaration_conflict": ReasonSpec(
        CONTRACT_ERROR, _AR,
        "Declare operation.arithmetic or a full verification_metadata, not both.",
    ),
    # ---- whole operation -----------------------------------------------------
    "invalid_verification_metadata": ReasonSpec(
        CONTRACT_ERROR, (DOMAIN_OPERATION_IO, DOMAIN_ARITHMETIC, DOMAIN_LIFECYCLE),
        "The externally supplied verification_metadata is invalid; correct or omit it.",
    ),
    UNCLASSIFIED: ReasonSpec(
        CONTRACT_ERROR, (DOMAIN_OPERATION_IO, DOMAIN_ARITHMETIC, DOMAIN_LIFECYCLE),
        "No specific reason code was attached to this failure.",
    ),
}

ARCHITECT_BLOCKING_REASON_CODES = frozenset(
    code for code, spec in REASONS.items() if spec.architect_blocking
)


def reason_spec(reason_code: str) -> ReasonSpec:
    return REASONS.get(str(reason_code)) or REASONS[UNCLASSIFIED]


def owner_for(category: str) -> str:
    return OWNER_BY_CATEGORY[category]


def blocked_by_id(operation_name: str, reason_code: str) -> str:
    """Stable key linking a feature/obligation back to the diagnostic that blocks it."""

    return f"{operation_name}:{reason_code}"


def diagnostic_from_error(operation_name: str, error: BaseException) -> dict[str, Any]:
    """Build one diagnostic from a reasoned exception (never from its message text)."""

    code = str(getattr(error, "reason_code", "") or UNCLASSIFIED)
    if code not in REASONS:
        code = UNCLASSIFIED
    spec = REASONS[code]
    details = dict(getattr(error, "details", None) or {})
    hint = (spec.variants or {}).get(str(details.get("hint_variant", "")), spec.hint)
    return {
        "operation_name": operation_name,
        "reason_code": code,
        "category": spec.category,
        "owner": owner_for(spec.category),
        "affected_domains": list(spec.domains),
        "message": str(error),
        "resolution_hint": hint,
        "details": details,
        "blocked_by": blocked_by_id(operation_name, code),
    }


def automation_record(diagnostics: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Feature-level automation metadata for something blocked by `diagnostics`.

    The most Architect-actionable category wins the status (a contract error is
    reported before a tool limitation), and every blocker stays listed.
    """

    items = [dict(item) for item in diagnostics]
    if not items:
        return {"status": CODE_OWNED}
    order = {CONTRACT_ERROR: 0, EXTENSION_REQUIRED: 1, TOOL_CAPABILITY: 2}
    primary = min(items, key=lambda item: order.get(str(item.get("category")), 9))
    category = str(primary["category"])
    return {
        "status": AUTOMATION_STATUS_BY_CATEGORY[category],
        "owner": owner_for(category),
        "reason_code": str(primary["reason_code"]),
        "blocked_by": sorted({str(item["blocked_by"]) for item in items}),
    }


def feature_automation(feature: Mapping[str, Any]) -> dict[str, Any]:
    """A feature's automation record; a feature without one is plainly code-owned."""

    record = feature.get("automation")
    if isinstance(record, Mapping) and record.get("status"):
        return dict(record)
    return {"status": CODE_OWNED}


def is_code_owned(feature: Mapping[str, Any]) -> bool:
    return feature_automation(feature)["status"] == CODE_OWNED


def blockers_of(record: Mapping[str, Any]) -> list[str]:
    """Blocker IDs of an automation record (its reason code when none are listed)."""

    listed = [str(item) for item in record.get("blocked_by") or []]
    return listed or [str(record.get("reason_code") or "unspecified")]


def summarize_feature_automation(
    plans: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Per-domain automation state derived from feature-level automation records.

    ``ready``: every feature is code-owned. ``partial``: some are blocked.
    ``blocked``: every feature is blocked. There is no plan-level status of its
    own -- a domain's state is only ever the roll-up of its features.
    """

    summary: dict[str, dict[str, Any]] = {}
    for domain, plan in plans.items():
        features = [item for item in plan.get("features", []) if isinstance(item, Mapping)]
        blocked = [item for item in features if not is_code_owned(item)]
        by_blocker: dict[str, list[str]] = {}
        for feature in blocked:
            for blocker in blockers_of(feature_automation(feature)):
                by_blocker.setdefault(blocker, []).append(str(feature.get("id", "")))
        owned = len(features) - len(blocked)
        summary[str(domain)] = {
            "state": "ready" if not blocked else ("blocked" if not owned else "partial"),
            "code_owned": owned,
            "blocked": len(blocked),
            "blocked_by": {key: sorted(value) for key, value in sorted(by_blocker.items())},
        }
    return summary


__all__ = [
    "ARCHITECT_BLOCKING_REASON_CODES",
    "AUTOMATION_STATUSES",
    "AUTOMATION_STATUS_BY_CATEGORY",
    "CATEGORIES",
    "CODE_OWNED",
    "CONTRACT_ERROR",
    "DOMAINS",
    "DOMAIN_ARITHMETIC",
    "DOMAIN_LIFECYCLE",
    "DOMAIN_OPERATION_IO",
    "EXTENSION_REQUIRED",
    "OWNER_BY_CATEGORY",
    "REASONS",
    "ReasonSpec",
    "TOOL_CAPABILITY",
    "UNCLASSIFIED",
    "automation_record",
    "blocked_by_id",
    "blockers_of",
    "diagnostic_from_error",
    "feature_automation",
    "is_code_owned",
    "owner_for",
    "reason_spec",
    "summarize_feature_automation",
]
