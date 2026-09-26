"""Executable deterministic campaign for code-owned operation/protocol/lifecycle scope."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

from multigent.verifier_tool.orchestration.runtime import (
    get_coverage_tracker,
    record_stimulus,
    sample_operation,
)
from multigent.verifier_tool.pool.feature_plans.catalog import operation_feature_selections
from multigent.verifier_tool.pool.lifecycle_policy_pool import policy_extension_request
from multigent.verifier_tool.lifecycle.stimulus import (
    drive_accepted_command,
    drive_accepted_command_on_reset_release,
)
from multigent.verifier_tool.operation.stimulus import generate_canonical_stimulus_suite
from multigent.verifier_tool.protocol.stimulus import (
    OperationMemoryAdapter,
    collect_protocol_transfers,
    default_axi_lite_memory_bases,
    drive_protocol_reset,
    drive_protocol_transfers,
    execute_axi4_memory_job,
    execute_axi_lite_memory_job,
    execute_custom_mmio_read_job,
    execute_custom_mmio_write_job,
    resolved_control_plane_probe_plan,
    resolved_operation_transport_variants,
)
from multigent.verifier_tool.protocol.stimulus.adapter import unpack_words
from multigent.verifier_tool.pool.role_pool.standard_protocols import (
    compile_standard_protocol_plan,
)


class AutomaticCampaignError(AssertionError):
    """The code-owned campaign cannot execute the frozen supported subset."""


def _lifecycle_extension_fields(operation: Mapping[str, Any]) -> set[str]:
    policy = operation.get("lifecycle", {}).get("policy", {})
    if not isinstance(policy, Mapping):
        return set()
    return {
        str(field)
        for field, value in policy.items()
        if policy_extension_request(value) is not None
    }


def code_owned_arithmetic_profiles() -> frozenset[str]:
    """Every `classifier_profile` this tool has *some* code-owned golden
    model/classifier for -- derived from the arithmetic schema's own `anyOf`
    branches, not a hardcoded name, so this stays correct the day a second
    profile (e.g. an attention/softmax family, alongside today's sole
    `integer_matrix_multiply`) gets its own schema branch, without anyone
    having to remember to update a separate list here. `llm_extension` is
    the explicit "not code-owned" escape hatch, never counted as one.
    """

    from multigent.verifier_tool.pool.operation_metadata.arithmetic_metadata import (
        operation_arithmetic_schema,
    )

    profiles = {
        value
        for branch in operation_arithmetic_schema().get("anyOf", [])
        for value in branch.get("properties", {}).get("classifier_profile", {}).get("enum", [])
    }
    return frozenset(profiles - {"llm_extension"})


def _operation_arithmetic_reasons(
    operation: Mapping[str, Any],
    name: str,
    *,
    declared_features: set[str] | None = None,
    supported_concepts: set[str] | None = None,
) -> list[str]:
    """Reasons this operation's *arithmetic specifically* has no code-owned
    golden model -- independent of whether its protocol/lifecycle/shape are
    drivable at all (see `_operation_protocol_lifecycle_reasons`). Checking
    "is my arithmetic the problem, or something else" is exactly what lets
    `run_code_owned_verification_campaign` still drive (without a golden
    check) an operation whose protocol and lifecycle are otherwise fine, and
    what lets the LLM-facing prompt tell an operation's stimulus/protocol
    apart from its math being the actual gap.
    """

    reasons: list[str] = []
    if declared_features is not None and supported_concepts is not None:
        unsupported = sorted(declared_features - supported_concepts)
        if unsupported:
            reasons.append(f"{name}:llm_extension_features={unsupported}")
    if operation.get("arithmetic", {}).get("classifier_profile") not in code_owned_arithmetic_profiles():
        reasons.append(f"{name}:operation_profile_not_executable")
    return reasons


def _operation_protocol_lifecycle_reasons(operation: Mapping[str, Any], name: str) -> list[str]:
    """Reasons this operation cannot be *driven* at all -- protocol, wire
    serialization, output shape, or command legality -- independent of
    whether its arithmetic has a code-owned golden model
    (`_operation_arithmetic_reasons`). Empty here means the automatic
    campaign can push real traffic through this operation's channels and
    close its own protocol/lifecycle coverage regardless of whether its
    arithmetic is code-owned, llm_extension, or anything else.
    """

    reasons: list[str] = []
    extension_fields = _lifecycle_extension_fields(operation)
    drive_critical_extensions = extension_fields & {
        "job_acceptance", "completion_style", "completion_timing",
    }
    if drive_critical_extensions:
        reasons.append(
            f"{name}:lifecycle_drive_extension={sorted(drive_critical_extensions)}"
        )
    bindings = [*operation.get("inputs", []), *operation.get("outputs", [])]
    from multigent.verifier_tool.pool.operation_metadata.io_metadata import require_supported_serialization
    for binding in bindings:
        try:
            require_supported_serialization(binding)
        except ValueError as exc:
            reasons.append(f"{name}:{exc}")
    profiles = {str(item.get("protocol_profile", "")) for item in bindings}
    if profiles in ({"axi4_lite"}, {"axi4"}):
        missing_memory = sorted(
            str(item.get("data_object", ""))
            for item in bindings
            if not isinstance(item.get("memory_mapping"), Mapping)
        )
        if missing_memory:
            reasons.append(f"{name}:memory_mapping_unresolved={missing_memory}")
        else:
            # Every binding may belong to its own independent group (three
            # single-capability gmem_a/b/c manager ports rather than one
            # shared group), so this must be a union across all of them, not
            # just the first binding's own group.
            required_capabilities = {
                "max_outstanding",
                "read_write_concurrency",
                "address_bins",
                "write_strobe_bins",
                "protection_bins",
                "write_order_bins",
            }
            missing_capabilities_set: set[str] = set()
            for item in bindings:
                capabilities = item["memory_mapping"].get("protocol_capabilities", {})
                missing_capabilities_set |= required_capabilities - set(capabilities)
            missing_capabilities = sorted(missing_capabilities_set)
            if missing_capabilities:
                reasons.append(
                    f"{name}:protocol_capabilities_unresolved={missing_capabilities}"
                )
            if profiles == {"axi4_lite"}:
                # The standard checker can observe partial/zero WSTRB and
                # unaligned addresses, but the code-owned GEMM memory model
                # currently serves full-word writes at aligned object bases.
                # Advertise only combinations its complete operation campaign
                # can actually drive; an extension may supply the others.
                def declared_bins(key: str) -> set[str]:
                    value = capabilities.get(key, ())
                    if isinstance(value, str):
                        return set(value.split("|"))
                    if isinstance(value, (tuple, list, set)):
                        return {str(item) for item in value}
                    return {str(value)}

                unsupported_strobes = declared_bins("write_strobe_bins") - {"full"}
                if unsupported_strobes:
                    reasons.append(
                        f"{name}:axi4_lite_operation_write_strobe_bins_not_executable="
                        f"{sorted(unsupported_strobes)}"
                    )
                if "unaligned" in declared_bins("address_bins"):
                    reasons.append(
                        f"{name}:axi4_lite_operation_unaligned_address_not_executable"
                    )
            if profiles == {"axi4"}:
                from multigent.verifier_tool.protocol.stimulus.drivers.axi4_outstanding import (
                    AXI4_OUTSTANDING_ID_CHANNELS,
                )

                # Each binding's own group may be single-capability (e.g. three
                # independent read-only/write-only gmem_a/b/c manager ports,
                # rather than one shared group with both directions) -- only
                # ever require an ID field for a channel kind that binding's
                # own group actually declares, never for one it has no
                # channel for at all.
                missing_ids: set[str] = set()
                for item in bindings:
                    protocol_fields = item["memory_mapping"].get("protocol_fields", {})
                    if not isinstance(protocol_fields, Mapping):
                        continue
                    for kind in AXI4_OUTSTANDING_ID_CHANNELS:
                        if kind in protocol_fields and "id" not in protocol_fields.get(kind, ()):
                            missing_ids.add(kind)
                if missing_ids:
                    reasons.append(f"{name}:axi4_outstanding_requires_id_fields={sorted(missing_ids)}")
    elif profiles == {"custom_mmio"}:
        # custom_mmio's channel vocabulary has no AxPROT/WSTRB-style
        # signals to bin coverage on, so unlike axi4/axi4_lite above it
        # does not gate on `required_capabilities` -- only on having a
        # resolved memory_mapping to address each object at all.
        missing_memory = sorted(
            str(item.get("data_object", ""))
            for item in bindings
            if not isinstance(item.get("memory_mapping"), Mapping)
        )
        if missing_memory:
            reasons.append(f"{name}:memory_mapping_unresolved={missing_memory}")
    elif profiles != {"ready_valid"}:
        reasons.append(f"{name}:operation_io_profile_not_executable={sorted(profiles)}")
    if len(operation.get("outputs", [])) != 1:
        reasons.append(f"{name}:requires_one_serialized_output")
    job_acceptance = operation.get("lifecycle", {}).get("policy", {}).get("job_acceptance")
    if job_acceptance == "control_plane_sequence":
        if not isinstance(operation.get("lifecycle", {}).get("control_plane_sequence"), Mapping):
            reasons.append(f"{name}:command_legality_unresolved")
    else:
        commands = list(operation.get("lifecycle", {}).get("job_accept_channels", []))
        if len(commands) != 1 or not commands[0].get("legal_values"):
            reasons.append(f"{name}:command_legality_unresolved")
    return reasons


def _operation_campaign_reasons(
    operation: Mapping[str, Any],
    name: str,
    *,
    declared_features: set[str] | None = None,
    supported_concepts: set[str] | None = None,
) -> list[str]:
    """Reasons this *one* operation cannot run the *full, golden-checked*
    automatic campaign -- arithmetic and protocol/lifecycle/shape combined.

    Shared by `automatic_campaign_support` (the aggregate report a caller
    checks before deciding whether to embed the campaign at all) and
    `run_code_owned_verification_campaign` (the per-operation skip decision
    at actual drive time), so a single operation with an unrecognized
    protocol, lifecycle, or shape does not have to poison every other
    operation in the same contract -- the runtime already skips
    `classifier_profile: llm_extension` operations exactly this way; this is
    the same treatment for an operation whose arithmetic has *some*
    code-owned profile (`code_owned_arithmetic_profiles()`, today only
    `integer_matrix_multiply` but not hardcoded to it) but fails some other
    executability check. See `_operation_arithmetic_reasons`/
    `_operation_protocol_lifecycle_reasons` for the two independent halves
    this is built from -- an operation can fail only the arithmetic half and
    still be driven (without a golden check) for its own protocol/lifecycle
    coverage; see `_run_arithmetic_blocked_operation_smoke`.
    """

    return [
        *_operation_arithmetic_reasons(
            operation, name, declared_features=declared_features, supported_concepts=supported_concepts
        ),
        *_operation_protocol_lifecycle_reasons(operation, name),
    ]


def automatic_campaign_support(
    operation_metadata: Mapping[str, Any],
    architecture_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Report whether the complete operation set has an executable code-owned path.

    `"supported"`/`"reasons"` are the aggregate view (unchanged shape, for
    existing callers): `supported` is True only if *every* operation
    qualifies. `"operations"` is the per-operation breakdown callers should
    prefer going forward: a contract with one unsupported operation among
    several supported ones can still run the automatic campaign for the
    ones that qualify (see `run_code_owned_verification_campaign`), instead
    of the whole contract falling back to fully Verifier-authored source.
    `"any_operation_supported"` is the convenience check for "is it worth
    embedding the campaign at all". It is true when at least one operation's
    protocol/lifecycle path is executable, even if that operation's arithmetic
    is LLM-owned: the campaign can still run its arithmetic-blocked smoke path.
    Each per-operation entry also carries
    `"protocol_lifecycle_supported"` (`_operation_protocol_lifecycle_reasons`
    empty -- independent of arithmetic) and `"arithmetic_reasons"`
    specifically, since an operation can fail only the arithmetic half and
    still get `_run_arithmetic_blocked_operation_smoke`'s automatic
    protocol/lifecycle traffic and coverage; see that function and
    `code_owned_obligations_for_supported_operations`.
    """

    reasons: list[str] = []
    operations = list(operation_metadata.get("operations", []))
    declared_features = {
        str(item.get("name", "")): {
            concept for selection in operation_feature_selections(item)
            for concept in selection
        }
        for item in (architecture_contract or {}).get("operations", [])
        if isinstance(item, Mapping)
    }
    if architecture_contract is not None:
        from multigent.verifier_tool.pool.operation_metadata import supported_code_owned_concepts

        supported_concepts = supported_code_owned_concepts(operation_metadata)
    else:
        supported_concepts = {}
    if not operations:
        reasons.append("no_operations")
    per_operation: dict[str, dict[str, Any]] = {}
    for operation in operations:
        name = str(operation.get("operation_name", ""))
        arithmetic_reasons = _operation_arithmetic_reasons(
            operation,
            name,
            declared_features=declared_features.get(name) if architecture_contract is not None else None,
            supported_concepts=supported_concepts.get(name, set()) if architecture_contract is not None else None,
        )
        protocol_lifecycle_reasons = _operation_protocol_lifecycle_reasons(operation, name)
        extension_fields = sorted(_lifecycle_extension_fields(operation))
        extension_reasons = (
            [f"{name}:lifecycle_extension_fields={extension_fields}"]
            if extension_fields
            else []
        )
        op_reasons = [
            *arithmetic_reasons,
            *protocol_lifecycle_reasons,
            *extension_reasons,
        ]
        reasons.extend(op_reasons)
        per_operation[name] = {
            "supported": not op_reasons,
            "reasons": op_reasons,
            "arithmetic_reasons": arithmetic_reasons,
            "protocol_lifecycle_supported": not protocol_lifecycle_reasons,
        }
        if extension_fields:
            per_operation[name]["lifecycle_extension_fields"] = extension_fields
            per_operation[name]["known_scope_campaign_supported"] = not (
                arithmetic_reasons or protocol_lifecycle_reasons
            )
    blocked_operations = _compile_blocked_operations(operation_metadata, set(per_operation))
    for name, info in blocked_operations.items():
        # Not driven, not golden-checked, not silently absent: an operation that
        # failed to compile is unsupported, so the contract is never reported as
        # fully automatic while part of it has no metadata at all.
        reasons.extend(info["reasons"])
        per_operation[name] = {
            "supported": False,
            "reasons": list(info["reasons"]),
            "arithmetic_reasons": [],
            "protocol_lifecycle_supported": False,
            "compile_blocked": True,
            "category": info["category"],
            "owner": info["owner"],
            "reason_code": info["reason_code"],
        }
    report = {
        "supported": not reasons,
        "status": "supported" if not reasons else "llm_extension_required",
        "reasons": reasons,
        "operations": per_operation,
        "any_operation_supported": any(
            item["protocol_lifecycle_supported"]
            for item in per_operation.values()
        ),
    }
    if blocked_operations:
        report["blocked_operations"] = blocked_operations
    return report


def _compile_blocked_operations(
    operation_metadata: Mapping[str, Any], known: set[str]
) -> dict[str, dict[str, Any]]:
    """Diagnostics of operations `build_architect_operation_metadata` could not compile."""

    blocked: dict[str, dict[str, Any]] = {}
    for entry in operation_metadata.get("unrepresentable_operations", []) or []:
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("operation_name") or entry.get("name", ""))
        if not name or name in known or name in blocked:
            continue
        code = str(entry.get("reason_code", "unclassified_metadata_error"))
        blocked[name] = {
            "reasons": [f"{name}:operation_not_compiled={code}"],
            "reason_code": code,
            "category": str(entry.get("category", "")),
            "owner": str(entry.get("owner", "")),
            "blocked_by": list(entry.get("blocked_by", [])),
            "affected_domains": list(entry.get("affected_domains", [])),
            "affected_feature_ids": list(entry.get("affected_feature_ids", [])),
            "message": str(entry.get("message", entry.get("reason", ""))),
            "resolution_hint": str(entry.get("resolution_hint", "")),
        }
    return blocked


def code_owned_obligations_for_supported_operations(
    obligations: Sequence[Mapping[str, Any]],
    operation_metadata: Mapping[str, Any],
    supported_operations: set[str],
    *,
    reset_signal_name: str | None = None,
    protocol_lifecycle_ready_operations: set[str] | None = None,
) -> set[str]:
    """Which obligation IDs a caller may treat as automatically covered,
    given that only `supported_operations` (from
    `automatic_campaign_support(...)["operations"]`) can actually be driven
    *and golden-checked* by the automatic campaign.

    `protocol_lifecycle_ready_operations` (from that same report's
    per-operation `"protocol_lifecycle_supported"`), if given, widens
    exactly the channel/command/status/reset checks below (never the
    `scope == "operation"` ones) to also credit an operation whose
    arithmetic alone is unsupported: `_run_arithmetic_blocked_operation_smoke`
    drives real traffic through such an operation's own channels too, so
    its protocol/lifecycle coverage closes the same way a fully-supported
    operation's does, even though nothing here checks its output. Omit it
    to keep the older, more conservative behavior (protocol/lifecycle
    obligations credited only for fully-supported operations).

    Operation- and lifecycle-*policy*-level obligations (`scope ==
    "operation"`, tagged by `pool/feature_plans/lifecycle.py` and
    `operation/coverage/plan.py` identically) map directly onto one
    operation via `scope_name`. Protocol-level obligations are channel/group/
    field/signal-addressed, not operation-addressed (`scope` in
    `{"protocol_group", "protocol_field", "channel", "signal"}`), because one
    physical channel can in principle serve more than one operation -- such a
    channel's coverage bins get closed by whichever operation's traffic
    actually crosses them, so it is code-owned only if *every* operation that
    binds to it is itself individually supported; an unsupported sibling
    operation on the same channel contributes no automatic traffic at all.
    "Binds to it" covers three distinct places a channel/signal name can
    come from: an operation's own I/O bindings (`channel`,
    `memory_mapping.protocol_group`), its command channel
    (`lifecycle.job_accept_channels[].channel`), and its status signals
    (`lifecycle.status_bindings["busy"/"completion"/"error"]`) -- missing any
    of these would wrongly leave, say, a fully-supported operation's own
    command-channel obligations off this set. `reset_signal_name`, if given,
    is treated separately: reset is interface-global (one signal shared by
    every operation, driven unconditionally by
    `run_code_owned_verification_campaign` the moment it runs at all), so its
    obligation is code-owned whenever `supported_operations` is non-empty,
    not only when *every* operation qualifies.

    Standard-field obligations use a compound `scope_name` for stable IDs,
    but the coverage-plan binding also contains the real `channel_name` and
    `protocol_group`. Attribute through those explicit bindings, never by
    parsing the compound name. An obligation with no operation reference is
    conservatively left off this set rather than guessed.

    Getting this attribution wrong is not a silent coverage hole either way:
    `InterfaceCoverageTracker.report()` independently checks actual bin hits
    against the same deterministic obligation set at simulation end,
    regardless of what a caller believed was code-owned here. Wrongly
    crediting an obligation here just means a caller skips writing source for
    it and the run then fails loudly on `missing_bins`, not silently.
    """

    protocol_lifecycle_eligible = supported_operations | (protocol_lifecycle_ready_operations or set())
    channel_to_operations: dict[str, set[str]] = {}

    def _bind(key: Any, name: str) -> None:
        if key:
            channel_to_operations.setdefault(str(key), set()).add(name)

    def _bind_operation(name: str, bindings: Sequence[Any], lifecycle: Mapping[str, Any]) -> None:
        for binding in bindings:
            if not isinstance(binding, Mapping):
                continue
            _bind(binding.get("channel"), name)
            mapping = binding.get("memory_mapping") or {}
            _bind(mapping.get("protocol_group"), name)
            # A memory-mapped binding's own logical `channel` is only its
            # *data* channel (e.g. AXI4-Lite's "r"/"w") -- address and
            # response can be separate physical channels ("ar"/"aw"/"bresp")
            # that never appear as a top-level `channel` on any binding at
            # all, only inside memory_mapping.
            _bind(mapping.get("address_channel"), name)
            _bind(mapping.get("data_channel"), name)
            _bind(mapping.get("response_channel"), name)
        for command in lifecycle.get("job_accept_channels", []):
            _bind(command.get("channel"), name)
        for signal_names in lifecycle.get("status_bindings", {}).values():
            for signal_name in signal_names:
                _bind(signal_name, name)

    for operation in operation_metadata.get("operations", []):
        _bind_operation(
            str(operation.get("operation_name", "")),
            [*operation.get("inputs", []), *operation.get("outputs", [])],
            operation.get("lifecycle", {}),
        )
    # An operation that failed to compile still occupies its channels: it
    # contributes no automatic traffic, so it must keep those channels from being
    # credited as code-owned on a sibling's account.
    for entry in operation_metadata.get("unrepresentable_operations", []) or []:
        shell = entry.get("shell") if isinstance(entry, Mapping) else None
        if isinstance(shell, Mapping):
            _bind_operation(
                str(entry.get("operation_name") or entry.get("name", "")),
                [*shell.get("inputs", []), *shell.get("outputs", [])],
                shell.get("lifecycle") or {},
            )

    owned: set[str] = set()
    for item in obligations:
        scope = str(item.get("scope", ""))
        scope_name = str(item.get("scope_name", ""))
        if scope == "operation":
            if scope_name in supported_operations:
                owned.add(str(item["id"]))
            continue
        if reset_signal_name and scope_name == reset_signal_name:
            if protocol_lifecycle_eligible:
                owned.add(str(item["id"]))
            continue
        bindings = item.get("bindings", {})
        bound_channel = (
            str(bindings.get("channel_name", ""))
            if scope == "protocol_field" and isinstance(bindings, Mapping)
            else ""
        )
        referencing = channel_to_operations.get(bound_channel or scope_name)
        if referencing and referencing <= protocol_lifecycle_eligible:
            owned.add(str(item["id"]))
    return owned


def _axi_lite_group(
    interface: Mapping[str, Any], operation: Mapping[str, Any]
) -> Mapping[str, Any]:
    groups = compile_standard_protocol_plan(interface).get("groups", [])
    names = {
        str(item.get("memory_mapping", {}).get("protocol_group", ""))
        for item in [*operation.get("inputs", []), *operation.get("outputs", [])]
    }
    matches = [
        group
        for group in groups
        if str(group.get("name", "")) in names
        and group.get("profile") == "axi4_lite"
        and group.get("endpoint_role") == "manager"
    ]
    if len(names) != 1 or len(matches) != 1:
        raise AutomaticCampaignError(
            f"operation {operation.get('operation_name')!r} needs one mapped AXI4-Lite manager group"
        )
    return matches[0]


def _axi4_group(
    interface: Mapping[str, Any], operation: Mapping[str, Any]
) -> Mapping[str, Any]:
    groups = compile_standard_protocol_plan(interface).get("groups", [])
    names = {
        str(item.get("memory_mapping", {}).get("protocol_group", ""))
        for item in [*operation.get("inputs", []), *operation.get("outputs", [])]
    }
    matches = [
        group
        for group in groups
        if str(group.get("name", "")) in names
        and group.get("profile") == "axi4"
        and group.get("endpoint_role") == "manager"
    ]
    if len(names) != 1 or len(matches) != 1:
        raise AutomaticCampaignError(
            f"operation {operation.get('operation_name')!r} needs one mapped AXI4 manager group"
        )
    return matches[0]


def _axi_command_metadata(
    operation: Mapping[str, Any], base_variant: str,
    *, object_bases: Mapping[str, int] | None = None,
) -> dict[str, int]:
    bases = object_bases or default_axi_lite_memory_bases(operation, variant=base_variant)
    return {
        str(binding["memory_mapping"]["base_signal"]): int(bases[str(binding["data_object"])])
        for binding in [*operation.get("inputs", []), *operation.get("outputs", [])]
    }


async def run_code_owned_axi4_operation_case(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    base_variant: str = "interior",
    aligned_tail_beats: int | None = None,
    seed: int | None = None,
    max_extra_cycles: int = 4,
    read_error_at: int | None = None,
    write_error_at: int | None = None,
    stop_after: tuple[str, int] | None = None,
    timeout_cycles: int = 262_144,
    record: bool = True,
) -> str | None:
    """Execute one full-AXI4 memory job, completing out of order per `seed`.

    Narrower than `run_code_owned_axi_lite_operation_case`: it does not yet
    replay AXI4-Lite's full ready-mode/misalignment/reset-abort coverage
    matrix for this profile -- see `stimulus/README.md` for the exact gap.
    It does prove the one thing AXI4-Lite structurally cannot: that a
    concurrently-issued, out-of-order-completing exchange is captured
    correctly, using the same `RandomCompletionScheduler` verified against
    real RTL in `multigent/tests/test_axi4_outstanding_drive.py`.

    `record=False` drives `case["stimulus"]` and waits for completion
    exactly as usual, but skips the final golden-model check/coverage
    sample (`_record_case`, which needs `case["expected"]`) and returns
    `None` -- driving traffic and checking its correctness are genuinely
    separate steps here: nothing about pushing `case["stimulus"]` through
    the wire or observing completion needs a golden value at all, only the
    final comparison does. This is what lets
    `_run_arithmetic_blocked_operation_smoke` exercise (and let the
    always-on protocol/lifecycle monitor sample) an operation's own
    channel and command/status coverage even when its arithmetic is
    `llm_extension` and has no golden model to check against.
    """

    import cocotb

    clock_name = str(interface["clock"])
    group = _axi4_group(interface, operation)
    bases = default_axi_lite_memory_bases(
        operation, variant=base_variant, aligned_tail_beats=aligned_tail_beats,
    )
    metadata = _axi_command_metadata(operation, base_variant, object_bases=bases)
    commands = list(operation.get("lifecycle", {}).get("job_accept_channels", []))
    if len(commands) != 1 or not commands[0].get("legal_values"):
        raise AutomaticCampaignError("AXI4 job needs one resolved legal command")

    command_task = cocotb.start_soon(
        drive_accepted_command(
            dut,
            clock_name,
            commands[0],
            int(commands[0]["legal_values"][0]),
            metadata_values=metadata,
            timeout_cycles=timeout_cycles,
        )
    )
    # The final AXI4 B handshake and the DUT completion pulse may occur on
    # the same active edge. Arm observation before the memory driver finishes;
    # waiting only afterwards can miss a valid one-cycle completion entirely.
    status_role = (
        None if stop_after is not None else
        "error" if read_error_at is not None or write_error_at is not None
        else "completion"
    )
    status_bindings = operation.get("lifecycle", {}).get("status_bindings", {})
    status_task = (
        cocotb.start_soon(
            _wait_status_pulse(
                dut,
                clock_name,
                status_bindings,
                status_role,
                timeout_cycles=timeout_cycles,
            )
        )
        if status_role is not None
        else None
    )
    error_signals = status_bindings.get("error", [])
    if status_role == "error" and len(error_signals) != 1:
        raise AutomaticCampaignError("AXI4 injected-error job needs one bound error signal")
    reset_name = str(interface["reset"])
    reset_signal = next(
        item for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("name") == reset_name
    )
    reset_semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    reset_active_value = (
        0 if "active-low" in reset_semantic or "active low" in reset_semantic else 1
    )
    try:
        observed_beats = await execute_axi4_memory_job(
            dut,
            clock_name,
            group,
            operation,
            case,
            bases,
            seed=seed,
            max_extra_cycles=max_extra_cycles,
            read_error_at=read_error_at,
            write_error_at=write_error_at,
            abort_signal_name=str(error_signals[0]) if status_role == "error" else None,
            reset_signal_name=reset_name,
            reset_active_value=reset_active_value,
            stop_after=stop_after,
            first_transfer_simultaneous=(
                seed == 0 and stop_after is None and status_role == "completion"
            ),
            initial_sink_stall_cycles=(0, 2, 4, 7)[(seed or 0) % 4],
            timeout_cycles=timeout_cycles,
        )
    except BaseException:
        if status_task is not None and not status_task.done():
            status_task.cancel()
        if not command_task.done():
            command_task.cancel()
        raise
    await command_task
    if status_task is not None:
        await status_task
    if stop_after is not None or read_error_at is not None or write_error_at is not None:
        return None
    if not record:
        return None
    return _record_case(operation, case, observed_beats, beats_are_canonical_elements=True)


def _control_plane_group(interface: Mapping[str, Any]) -> Mapping[str, Any]:
    groups = compile_standard_protocol_plan(interface).get("groups", [])
    matches = [
        group for group in groups
        if group.get("profile") == "axi4_lite" and group.get("endpoint_role") == "subordinate"
    ]
    if len(matches) != 1:
        raise AutomaticCampaignError(
            f"control_plane_sequence needs exactly one AXI4-Lite subordinate control group, found {len(matches)}"
        )
    return matches[0]


def _resolve_control_plane_value_from(value_from: Mapping[str, Any], bases: Mapping[str, int]) -> int:
    base = int(bases[str(value_from["data_object"])])
    half = str(value_from["half"])
    if half == "whole":
        return base
    return (base & 0xFFFFFFFF) if half == "low" else ((base >> 32) & 0xFFFFFFFF)


def _axi4_group_by_name(interface: Mapping[str, Any], protocol_group_name: str) -> Mapping[str, Any]:
    groups = compile_standard_protocol_plan(interface).get("groups", [])
    matches = [
        group for group in groups
        if str(group.get("name", "")) == protocol_group_name
        and group.get("profile") == "axi4" and group.get("endpoint_role") == "manager"
    ]
    if len(matches) != 1:
        raise AutomaticCampaignError(
            f"expected exactly one AXI4 manager group named {protocol_group_name!r}, found {len(matches)}"
        )
    return matches[0]


async def run_code_owned_axi4_operation_case_via_control_plane_sequence(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    base_variant: str = "interior",
    aligned_tail_beats: int | None = None,
    seed: int | None = None,
    max_extra_cycles: int = 4,
    initial_sink_stall_cycles: int = 0,
    write_data_stall_cycles: int = 0,
    write_address_one_cycle_probe: bool = False,
    first_transfer_simultaneous: bool = False,
    control_response_stall_cycles: int = 0,
    control_probe_plan: Mapping[str, bool] | None = None,
    timeout_cycles: int = 262_144,
    record: bool = True,
) -> str | None:
    """Execute one full-AXI4 memory job whose command is a register-mapped
    `control_plane_sequence` (e.g. a Vitis HLS `ap_ctrl_chain` AXI4-Lite
    control bus) instead of a `valid_ready_handshake` command channel.

    Unlike `run_code_owned_axi4_operation_case`, this does not assume every
    input/output binding shares one AXI4 manager group -- a real Vitis HLS
    kernel typically has three independent single-capability ports
    (`gmem_a`/`gmem_b` read-only, `gmem_c` write-only) rather than one shared
    group carrying both directions, so each binding's own group is served by
    its own concurrent `execute_axi4_memory_job` call, narrowed to just that
    one object.

    Deliberately the basic happy-path case only -- matching
    `run_code_owned_axi4_operation_case`'s own scope note, this does not yet
    replay the deeper reset-abort/error-injection sweep for this command
    source; see `control_plane_sequence_design.md`.
    """

    from multigent.verifier_tool.lifecycle.stimulus import drive_control_plane_sequence

    import cocotb

    clock_name = str(interface["clock"])
    control_group = _control_plane_group(interface)
    bases = default_axi_lite_memory_bases(
        operation, variant=base_variant, aligned_tail_beats=aligned_tail_beats,
    )
    sequence = operation.get("lifecycle", {}).get("control_plane_sequence")
    if not isinstance(sequence, Mapping):
        raise AutomaticCampaignError("operation has no resolved control_plane_sequence")

    def _resolve(value_from: Mapping[str, Any]) -> int:
        return _resolve_control_plane_value_from(value_from, bases)

    start_task = cocotb.start_soon(
        drive_control_plane_sequence(
            dut, clock_name, control_group, sequence, sequence["job_start"]["actions"],
            resolve_value_from=_resolve,
            response_stall_cycles=control_response_stall_cycles,
            timeout_cycles=timeout_cycles,
        )
    )

    memory_bindings = [
        (binding, "inputs") for binding in operation.get("inputs", [])
    ] + [
        (binding, "outputs") for binding in operation.get("outputs", [])
    ]
    memory_tasks = {}
    for binding, direction in memory_bindings:
        protocol_group_name = str(binding["memory_mapping"]["protocol_group"])
        group = _axi4_group_by_name(interface, protocol_group_name)
        narrowed_operation = {
            **operation,
            "inputs": [binding] if direction == "inputs" else [],
            "outputs": [binding] if direction == "outputs" else [],
        }
        memory_tasks[str(binding["data_object"])] = cocotb.start_soon(
            execute_axi4_memory_job(
                dut, clock_name, group, narrowed_operation, case, bases,
                seed=seed, max_extra_cycles=max_extra_cycles,
                initial_sink_stall_cycles=initial_sink_stall_cycles,
                initial_sink_stall_cycles_by_kind={"write_data": write_data_stall_cycles}
                if write_data_stall_cycles else None,
                write_address_one_cycle_probe=write_address_one_cycle_probe,
                first_transfer_simultaneous=first_transfer_simultaneous,
                timeout_cycles=timeout_cycles,
            )
        )
    # Start polling as soon as the start transaction completes. Polling only
    # after the memory coroutines finish hides a falsely early ap_done: by
    # then the final write response has already retired. The generated
    # lifecycle monitor compares each successful poll with that retirement.
    await start_task
    completion_task = cocotb.start_soon(
        drive_control_plane_sequence(
            dut, clock_name, control_group, sequence, sequence["job_complete"]["actions"],
            resolve_value_from=_resolve,
            response_stall_cycles=control_response_stall_cycles,
            timeout_cycles=timeout_cycles,
        )
    )
    observed_beats: list[dict[str, int]] = []
    for binding in operation.get("outputs", []):
        observed_beats = await memory_tasks[str(binding["data_object"])]
    for binding in operation.get("inputs", []):
        await memory_tasks[str(binding["data_object"])]

    await completion_task
    result = (
        _record_case(operation, case, observed_beats, beats_are_canonical_elements=True)
        if record else None
    )
    if control_probe_plan and any(control_probe_plan.values()):
        # Functional capture/ledger closes before protocol-only probes. Their
        # AW/W/B events must never masquerade as job-start pointer writes.
        await drive_control_plane_sequence(
            dut, clock_name, control_group, sequence, [],
            resolve_value_from=_resolve,
            protocol_probe_plan=control_probe_plan,
            timeout_cycles=timeout_cycles,
        )
        record_stimulus(
            "directed",
            {"protocol_probe": dict(control_probe_plan)},
            {},
            label="code_owned_control_plane_protocol_probe",
            observed={},
        )
    return result


async def _run_axi4_operation_campaign(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    *,
    timeout_cycles: int,
) -> int:
    """Close operation and lifecycle scope over full AXI4, out of order.

    Deliberately narrower than `_run_axi_lite_operation_campaign` -- see
    `run_code_owned_axi4_operation_case`'s docstring for the exact gap.
    """

    clock_name = str(interface["clock"])
    reset_signal = next(
        item
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    )
    semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    active_value = 0 if "active-low" in semantic or "active low" in semantic else 1
    reset_name = str(reset_signal["name"])

    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    first_case = cases[0]
    cumulative_reads = 0
    for binding in operation.get("inputs", []):
        await run_code_owned_axi4_operation_case(
            dut, interface, operation, first_case,
            stop_after=("read_response", cumulative_reads + 1),
            timeout_cycles=timeout_cycles,
        )
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
        cumulative_reads += _memory_transfer_count(binding, operation.get("dimensions", {}))
    await run_code_owned_axi4_operation_case(
        dut, interface, operation, first_case,
        stop_after=("read_response", cumulative_reads), timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    await run_code_owned_axi4_operation_case(
        dut, interface, operation, first_case,
        stop_after=("write_data", 1), timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    completed = 0
    for index, case in enumerate(cases):
        await run_code_owned_axi4_operation_case(
            dut, interface, operation, case, seed=index, timeout_cycles=timeout_cycles
        )
        completed += 1
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)

    # Explicitly close a genuinely out-of-order completion, rather than
    # trusting whatever relative order the cases above happened to produce --
    # seed=6 is the exact value `test_axi4_outstanding_drive.py` verified
    # against real RTL to swap two concurrent requests' completion order.
    if len(operation.get("inputs", [])) >= 2:
        await run_code_owned_axi4_operation_case(
            dut, interface, operation, cases[0], seed=6, max_extra_cycles=4,
            timeout_cycles=timeout_cycles,
        )
        completed += 1
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    for variant in ("read_page_edge", "write_page_edge"):
        await run_code_owned_axi4_operation_case(
            dut, interface, operation, cases[0], base_variant=variant,
            timeout_cycles=timeout_cycles,
        )
        completed += 1
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    command = operation.get("lifecycle", {}).get("job_accept_channels", [])[0]
    metadata = _axi_command_metadata(operation, "interior")
    await drive_accepted_command(
        dut, clock_name, command, int(command["illegal_value"]),
        metadata_values=metadata, timeout_cycles=timeout_cycles,
    )
    await _wait_status_pulse(
        dut, clock_name,
        operation.get("lifecycle", {}).get("status_bindings", {}),
        "error", timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    for error_kind in ("read", "write"):
        await run_code_owned_axi4_operation_case(
            dut, interface, operation, cases[0],
            read_error_at=1 if error_kind == "read" else None,
            write_error_at=1 if error_kind == "write" else None,
            timeout_cycles=timeout_cycles,
        )
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    return completed


async def _run_axi4_control_plane_operation_campaign(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    *,
    timeout_cycles: int,
) -> int:
    """Run supported multi-port AXI4 jobs via their AXI4-Lite start/done sequence.

    The generic AXI4 campaign assumes one shared manager and a ready/valid
    command. A control-plane-sequence job has neither assumption; its per-case
    driver already serves each bound memory group concurrently. Keep this
    dispatch separate so the generic reset/illegal-command probes do not
    accidentally use an absent command channel.
    """

    clock_name = str(interface["clock"])
    reset_signal = next(
        item for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    )
    semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    active_value = 0 if "active-low" in semantic or "active low" in semantic else 1
    reset_name = str(reset_signal["name"])

    from cocotb.triggers import RisingEdge

    # HLS register-mapped control and cocotbext AXI-Lite endpoints both need
    # several sampled edges after reset release before the first register write.
    # This matches the proven frozen-HLS RTL harness rather than launching a
    # second reset one cycle after the outer campaign reset.
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=5)
    for _ in range(5):
        await RisingEdge(getattr(dut, clock_name))
    variants = resolved_operation_transport_variants(interface)
    control_group = _control_plane_group(interface)
    control_probe_plan = resolved_control_plane_probe_plan(interface, str(control_group["name"]))
    completed = 0
    for index in range(max(len(cases), len(variants))):
        case = cases[index % len(cases)]
        variant = variants[index] if index < len(variants) else variants[0]
        stall_cycles = int(variant["stall_cycles"])
        await run_code_owned_axi4_operation_case_via_control_plane_sequence(
            dut, interface, operation, case, seed=index,
            aligned_tail_beats=variant["tail_beats"],
            initial_sink_stall_cycles=stall_cycles,
            write_data_stall_cycles=int(variant.get("write_data_stall_cycles", 0)),
            write_address_one_cycle_probe=bool(variant.get("write_address_one_cycle_probe")),
            first_transfer_simultaneous=bool(variant["simultaneous"]),
            control_response_stall_cycles=stall_cycles,
            control_probe_plan=control_probe_plan if index == 0 else None,
            timeout_cycles=timeout_cycles,
        )
        completed += 1
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=5)
        for _ in range(5):
            await RisingEdge(getattr(dut, clock_name))
    return completed


def _custom_mmio_group(
    interface: Mapping[str, Any], bindings: Sequence[Mapping[str, Any]], *, purpose: str
) -> Mapping[str, Any]:
    """Find the one compiled custom_mmio manager group covering `bindings`.

    Unlike AXI4/AXI4-Lite (one group carries both directions), a custom_mmio
    group is one direction only, so inputs and outputs generally name two
    different groups -- callers look each up separately (`purpose` is only
    used to make a lookup failure's error message say which side failed).
    """

    groups = compile_standard_protocol_plan(interface).get("groups", [])
    names = {
        str(item.get("memory_mapping", {}).get("protocol_group", ""))
        for item in bindings
    }
    matches = [
        group
        for group in groups
        if str(group.get("name", "")) in names
        and group.get("profile") == "custom_mmio"
        and group.get("endpoint_role") == "manager"
    ]
    if len(names) != 1 or len(matches) != 1:
        raise AutomaticCampaignError(
            f"custom_mmio {purpose} side needs one mapped manager group, found {len(matches)}"
        )
    return matches[0]


async def run_code_owned_custom_mmio_operation_case(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    seed: int | None = None,
    max_extra_cycles: int = 4,
    read_error_at: int | None = None,
    write_error_at: int | None = None,
    timeout_cycles: int = 262_144,
    record: bool = True,
) -> str | None:
    """Execute one custom_mmio memory job, completing out of order per `seed`.

    A custom_mmio group is one direction only (see `drivers/custom_mmio.py`),
    so -- unlike `run_code_owned_axi4_operation_case`'s single combined
    group -- this always resolves two groups: one covering `operation`'s
    inputs (served by `execute_custom_mmio_read_job`) and one covering its
    outputs (served by `execute_custom_mmio_write_job`), run concurrently.
    Both share `RandomCompletionScheduler` under the hood, so the same seed
    that proves out-of-order completion for AXI4 proves it here too.

    The write job gets its own `OperationMemoryAdapter` rather than sharing
    the read job's internal one -- input and output address windows never
    overlap, so two independently loaded images touch disjoint memory and
    the final output values are read back from the write job's image in
    logical (address) order via `read_output_values`, never trusted from
    wire acceptance order.

    `record=False`: see `run_code_owned_axi4_operation_case`'s docstring --
    same meaning, same reason.
    """

    import cocotb

    clock_name = str(interface["clock"])
    inputs = list(operation.get("inputs", []))
    outputs = list(operation.get("outputs", []))
    read_group = _custom_mmio_group(interface, inputs, purpose="read")
    write_group = _custom_mmio_group(interface, outputs, purpose="write")
    bases = default_axi_lite_memory_bases(operation, variant="interior")
    metadata = _axi_command_metadata(operation, "interior")
    commands = list(operation.get("lifecycle", {}).get("job_accept_channels", []))
    if len(commands) != 1 or not commands[0].get("legal_values"):
        raise AutomaticCampaignError("custom_mmio job needs one resolved legal command")

    write_memory = OperationMemoryAdapter.load(operation, case, bases)

    command_task = cocotb.start_soon(
        drive_accepted_command(
            dut,
            clock_name,
            commands[0],
            int(commands[0]["legal_values"][0]),
            metadata_values=metadata,
            timeout_cycles=timeout_cycles,
        )
    )
    read_task = cocotb.start_soon(
        execute_custom_mmio_read_job(
            dut,
            clock_name,
            read_group,
            operation,
            case,
            bases,
            seed=seed,
            max_extra_cycles=max_extra_cycles,
            read_error_at=read_error_at,
            timeout_cycles=timeout_cycles,
        )
    )
    await execute_custom_mmio_write_job(
        dut,
        clock_name,
        write_group,
        operation,
        write_memory,
        seed=seed,
        max_extra_cycles=max_extra_cycles,
        write_error_at=write_error_at,
        timeout_cycles=timeout_cycles,
    )
    await read_task
    await command_task
    if read_error_at is not None or write_error_at is not None:
        return None
    await _wait_status_pulse(
        dut,
        clock_name,
        operation.get("lifecycle", {}).get("status_bindings", {}),
        "completion",
        timeout_cycles=timeout_cycles,
    )
    if not record:
        return None
    dimensions = operation.get("dimensions", {})
    observed_beats = [
        {"payload": value}
        for value in write_memory.read_output_values(outputs[0], dimensions, bases)
    ]
    return _record_case(operation, case, observed_beats, beats_are_canonical_elements=True)


async def _run_custom_mmio_operation_campaign(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    *,
    timeout_cycles: int,
) -> int:
    """Close operation and lifecycle scope over custom_mmio, out of order.

    Structurally identical to `_run_axi4_operation_campaign` -- same reset-
    between-cases loop, same explicit seed=6 out-of-order-completion close --
    because both protocols share the same underlying completion scheduler;
    only the per-case driver differs.
    """

    clock_name = str(interface["clock"])
    reset_signal = next(
        item
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    )
    semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    active_value = 0 if "active-low" in semantic or "active low" in semantic else 1
    reset_name = str(reset_signal["name"])

    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    completed = 0
    for index, case in enumerate(cases):
        await run_code_owned_custom_mmio_operation_case(
            dut, interface, operation, case, seed=index, timeout_cycles=timeout_cycles
        )
        completed += 1
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)

    if len(operation.get("inputs", [])) >= 2:
        await run_code_owned_custom_mmio_operation_case(
            dut, interface, operation, cases[0], seed=6, max_extra_cycles=4,
            timeout_cycles=timeout_cycles,
        )
        completed += 1
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    return completed


async def run_code_owned_axi_lite_operation_case(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    base_variant: str = "interior",
    ready_modes: Mapping[str, tuple[str, int]] | None = None,
    stop_after: tuple[str, int] | None = None,
    read_error_at: int | None = None,
    write_error_at: int | None = None,
    timeout_cycles: int = 262_144,
    record: bool = True,
) -> str | None:
    """Execute one AXI4-Lite memory job from accepted bus traffic.

    `record=False`: see `run_code_owned_axi4_operation_case`'s docstring --
    same meaning, same reason.
    """

    clock_name = str(interface["clock"])
    expects_completion = (
        stop_after is None and read_error_at is None and write_error_at is None
    )
    expects_error = read_error_at is not None or write_error_at is not None
    status_role = "completion" if expects_completion else ("error" if expects_error else None)
    status_task = None
    if status_role is not None:
        import cocotb

        # A legal one-cycle completion or injected-error pulse may coincide
        # with the final response and disappear before the memory-serving
        # coroutine returns. Observe it concurrently instead of afterward.
        status_task = cocotb.start_soon(
            _wait_status_pulse(
                dut,
                clock_name,
                operation.get("lifecycle", {}).get("status_bindings", {}),
                status_role,
                timeout_cycles=timeout_cycles,
                require_runtime_completion=record and status_role == "completion",
            )
        )
    try:
        observed_beats = await execute_axi_lite_memory_job(
            dut,
            clock_name,
            _axi_lite_group(interface, operation),
            operation,
            case,
            base_variant=base_variant,
            ready_modes=ready_modes,
            stop_after=stop_after,
            read_error_at=read_error_at,
            write_error_at=write_error_at,
            timeout_cycles=timeout_cycles,
        )
    except BaseException:
        if status_task is not None and not status_task.done():
            status_task.cancel()
        raise
    if status_task is not None:
        await status_task
    if not expects_completion:
        return None
    if not record:
        return None
    return _record_case(operation, case, observed_beats)


def _memory_transfer_count(
    binding: Mapping[str, Any], dimensions: Mapping[str, Any]
) -> int:
    elements = _expected_elements(binding, dimensions)
    per_word = int(binding.get("memory_mapping", {}).get("elements_per_word", 0))
    if per_word <= 0:
        raise AutomaticCampaignError(
            f"binding {binding.get('data_object')!r} lacks elements_per_word"
        )
    return (elements + per_word - 1) // per_word


async def _drive_overlapping_axi_lite_command(
    dut: Any,
    clock_name: str,
    command: Mapping[str, Any],
    metadata_values: Mapping[str, int],
    write_response_channel: Mapping[str, Any],
    write_address_channel: Mapping[str, Any],
    write_data_channel: Mapping[str, Any],
    *,
    trigger: str,
    defer_cycles: int = 0,
    expected_writes: int,
    timeout_cycles: int,
) -> None:
    """Hold a second command while the first AXI-Lite job retires.

    The trigger selects a deterministic distance from retirement.  An optional
    whole-cycle deferral lets the campaign probe adjacent command-stall lengths
    without guessing from unobservable DUT state.  The command remains stable
    until the single-inflight DUT accepts it after retirement.
    """

    from cocotb.triggers import FallingEdge, RisingEdge, Timer

    if trigger not in {"final_response", "final_request", "first_response"}:
        raise AutomaticCampaignError(f"unknown AXI-Lite command trigger {trigger!r}")
    if expected_writes < 2:
        raise AutomaticCampaignError(
            "AXI-Lite command-stall coverage requires at least two output writes"
        )
    if defer_cycles < 0:
        raise AutomaticCampaignError("AXI-Lite command deferral cannot be negative")

    signals = command.get("signals", {})
    clock = getattr(dut, clock_name)
    valid = getattr(dut, str(signals["valid"]))
    ready = getattr(dut, str(signals["ready"]))
    payload = getattr(dut, str(signals["payload"]))
    metadata_handles = {
        str(item["signal"]): getattr(dut, str(item["signal"]))
        for item in command.get("metadata_fields", [])
    }
    unknown = sorted(set(metadata_values) - set(metadata_handles))
    if unknown:
        raise AutomaticCampaignError(
            f"AXI-Lite command probe has unmapped metadata {unknown}"
        )

    def handle(channel: Mapping[str, Any], key: str) -> Any:
        return getattr(dut, str(channel[key]))

    b_valid = handle(write_response_channel, "valid")
    b_ready = handle(write_response_channel, "ready")
    aw_valid = handle(write_address_channel, "valid")
    aw_ready = handle(write_address_channel, "ready")
    w_valid = handle(write_data_channel, "valid")
    w_ready = handle(write_data_channel, "ready")
    responses = 0
    addresses = 0
    data_beats = 0

    for _ in range(timeout_cycles):
        await FallingEdge(clock)
        if int(b_valid.value) and int(b_ready.value):
            responses += 1
        if int(aw_valid.value) and int(aw_ready.value):
            addresses += 1
        if int(w_valid.value) and int(w_ready.value):
            data_beats += 1
        triggered = (
            (trigger == "first_response" and responses >= 1)
            or (trigger == "final_response" and responses >= expected_writes)
            or (
                trigger == "final_request"
                and addresses >= expected_writes
                and data_beats >= expected_writes
            )
        )
        if triggered:
            for _ in range(defer_cycles):
                await RisingEdge(clock)
                await FallingEdge(clock)
            # Publish VALID before the contract monitor's FallingEdge +
            # ReadOnly snapshot, so a one-cycle early acceptance is visible.
            payload.value = int(command["legal_values"][0])
            for name, signal in metadata_handles.items():
                signal.value = int(metadata_values.get(name, 0))
            valid.value = 1
            break
    else:
        raise AutomaticCampaignError(
            f"AXI-Lite command probe never observed trigger {trigger!r}"
        )

    for _ in range(timeout_cycles):
        await Timer(1, unit="ps")
        pre_edge_ready = int(ready.value)
        await RisingEdge(clock)
        if pre_edge_ready:
            await FallingEdge(clock)
            valid.value = 0
            payload.value = 0
            for signal in metadata_handles.values():
                signal.value = 0
            return
        await FallingEdge(clock)
    raise AutomaticCampaignError(
        f"overlapping AXI-Lite command was not accepted after {trigger!r}"
    )


async def _run_axi_lite_command_stall_probe(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    trigger: str,
    *,
    defer_cycles: int = 0,
    timeout_cycles: int,
) -> None:
    """Run one real job while timing a held next command from AXI evidence."""

    import cocotb

    clock_name = str(interface["clock"])
    command = operation.get("lifecycle", {}).get("job_accept_channels", [])[0]
    group = _axi_lite_group(interface, operation)
    channels = group["channels"]
    dimensions = operation.get("dimensions", {})
    expected_writes = sum(
        _memory_transfer_count(binding, dimensions)
        for binding in operation.get("outputs", [])
    )
    held_command = cocotb.start_soon(
        _drive_overlapping_axi_lite_command(
            dut,
            clock_name,
            command,
            _axi_command_metadata(operation, "interior"),
            channels["write_response"],
            channels["write_address"],
            channels["write_data"],
            trigger=trigger,
            defer_cycles=defer_cycles,
            expected_writes=expected_writes,
            timeout_cycles=timeout_cycles,
        )
    )
    try:
        await run_code_owned_axi_lite_operation_case(
            dut,
            interface,
            operation,
            case,
            timeout_cycles=timeout_cycles,
            record=False,
        )
        await held_command
    except BaseException:
        if not held_command.done():
            held_command.cancel()
        raise


async def _run_axi_lite_operation_campaign(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    *,
    timeout_cycles: int,
) -> int:
    """Close operation, AXI4-Lite, and lifecycle scope with checked jobs."""

    clock_name = str(interface["clock"])
    reset_signal = next(
        item
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    )
    semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    active_value = 0 if "active-low" in semantic or "active low" in semantic else 1
    reset_name = str(reset_signal["name"])
    first_case = cases[0]

    # Every externally distinguishable phase is reached only through accepted
    # AXI responses, then reset aborts it before any unchecked disposition.
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    cumulative_reads = 0
    for binding in operation.get("inputs", []):
        await run_code_owned_axi_lite_operation_case(
            dut,
            interface,
            operation,
            first_case,
            stop_after=("read_response", cumulative_reads + 1),
            timeout_cycles=timeout_cycles,
        )
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
        cumulative_reads += _memory_transfer_count(binding, operation.get("dimensions", {}))
    # All reads complete and no write is accepted: compute phase.
    await run_code_owned_axi_lite_operation_case(
        dut,
        interface,
        operation,
        first_case,
        stop_after=("read_response", cumulative_reads),
        timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    # One fully retired output write distinguishes the output phase.
    await run_code_owned_axi_lite_operation_case(
        dut,
        interface,
        operation,
        first_case,
        stop_after=("write_response", 1),
        timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)

    completed = 0
    # First successful post-abort job proves recovery and post-reset purity.
    await run_code_owned_axi_lite_operation_case(
        dut, interface, operation, first_case, timeout_cycles=timeout_cycles
    )
    completed += 1

    protocol_modes = [
        {
            kind: ("simultaneous", 0)
            for kind in ("read_address", "write_address", "write_data")
        },
        {
            kind: ("valid_before_ready", 1)
            for kind in ("read_address", "write_address", "write_data")
        },
        {
            kind: ("valid_before_ready", 3)
            for kind in ("read_address", "write_address", "write_data")
        },
        {
            kind: ("valid_before_ready", 6)
            for kind in ("read_address", "write_address", "write_data")
        },
        {
            "read_address": ("ready_before_valid", 0),
            "write_address": ("ready_before_valid", 0),
            "write_data": ("valid_before_ready", 3),
        },
        {
            "read_address": ("ready_before_valid", 0),
            "write_address": ("valid_before_ready", 3),
            "write_data": ("ready_before_valid", 0),
        },
    ]
    for modes in protocol_modes:
        await run_code_owned_axi_lite_operation_case(
            dut,
            interface,
            operation,
            first_case,
            ready_modes=modes,
            timeout_cycles=timeout_cycles,
        )
        completed += 1
    for variant in ("read_zero", "write_zero", "read_page_edge", "write_page_edge"):
        await run_code_owned_axi_lite_operation_case(
            dut,
            interface,
            operation,
            first_case,
            base_variant=variant,
            timeout_cycles=timeout_cycles,
        )
        completed += 1
    for case in cases:
        await run_code_owned_axi_lite_operation_case(
            dut, interface, operation, case, timeout_cycles=timeout_cycles
        )
        completed += 1

    # Command-channel coverage is independent of where the operation data
    # travels.  AXI-Lite used to return before the generic ready/valid command
    # probes below, leaving all controllable valid-before-ready/stall bins
    # permanently uncovered.  Close them from real retirement evidence, then
    # abort the newly accepted overlapping command before the next probe.
    command = operation.get("lifecycle", {}).get("job_accept_channels", [])[0]
    metadata = _axi_command_metadata(operation, "interior")
    await drive_accepted_command_on_reset_release(
        dut,
        clock_name,
        reset_name,
        active_value,
        command,
        int(command["legal_values"][0]),
        metadata_values=metadata,
    )
    await drive_protocol_reset(
        dut, clock_name, reset_name, active_value, asserted_cycles=2
    )
    # Publishing VALID before the monitor's falling-edge sample shifts the
    # observed short stalls by one cycle. Two/one-cycle offsets from the final
    # write request now close the one-cycle/short bins; the first response
    # supplies a long overlap. Credit only observed command handshakes.
    for trigger, defer_cycles in (
        ("final_request", 2),
        ("final_request", 1),
        ("first_response", 0),
    ):
        await _run_axi_lite_command_stall_probe(
            dut,
            interface,
            operation,
            first_case,
            trigger,
            defer_cycles=defer_cycles,
            timeout_cycles=timeout_cycles,
        )
        await drive_protocol_reset(
            dut, clock_name, reset_name, active_value, asserted_cycles=2
        )

    await drive_accepted_command(
        dut,
        clock_name,
        command,
        int(command["illegal_value"]),
        metadata_values=metadata,
        timeout_cycles=timeout_cycles,
    )
    await _wait_status_pulse(
        dut,
        clock_name,
        operation.get("lifecycle", {}).get("status_bindings", {}),
        "error",
        timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)

    misaligned = dict(metadata)
    first_pointer = next(iter(misaligned))
    misaligned[first_pointer] += 1
    await drive_accepted_command(
        dut,
        clock_name,
        command,
        int(command["legal_values"][0]),
        metadata_values=misaligned,
        timeout_cycles=timeout_cycles,
    )
    await _wait_status_pulse(
        dut,
        clock_name,
        operation.get("lifecycle", {}).get("status_bindings", {}),
        "error",
        timeout_cycles=timeout_cycles,
    )
    await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)

    for error_kind in ("read", "write"):
        await run_code_owned_axi_lite_operation_case(
            dut,
            interface,
            operation,
            first_case,
            read_error_at=1 if error_kind == "read" else None,
            write_error_at=1 if error_kind == "write" else None,
            timeout_cycles=timeout_cycles,
        )
        await drive_protocol_reset(dut, clock_name, reset_name, active_value, asserted_cycles=2)
    return completed


def _channel(binding: Mapping[str, Any]) -> dict[str, Any]:
    signals = binding.get("signals", {})
    fields = {
        role: str(signal)
        for role, signal in signals.items()
        if role in {"payload", "last", "keep", "strb", "transaction_id", "metadata"}
    }
    return {
        "name": str(binding.get("channel", "")),
        "direction": str(binding.get("direction", "")),
        "valid": str(signals.get("valid", "")),
        "ready": str(signals.get("ready", "")),
        "fields": fields,
    }


def _wire_value(value: int, dtype: Mapping[str, Any]) -> int:
    width = int(dtype.get("width_bits", 0))
    return int(value) & ((1 << width) - 1) if width > 0 else int(value)


def _logical_value(value: int, dtype: Mapping[str, Any]) -> int:
    width = int(dtype.get("width_bits", 0))
    value = int(value)
    if width <= 0:
        return value
    value &= (1 << width) - 1
    if bool(dtype.get("signed")) and value & (1 << (width - 1)):
        value -= 1 << width
    return value


def _expected_elements(binding: Mapping[str, Any], dimensions: Mapping[str, Any]) -> int:
    extents = [dimensions.get(str(axis)) for axis in binding.get("dimensions", [])]
    if extents and all(isinstance(value, int) and value >= 0 for value in extents):
        return math.prod(map(int, extents))
    if not extents:
        return 1
    raise AutomaticCampaignError(
        f"binding {binding.get('data_object')!r} has unresolved dimensions {extents!r}"
    )


def _beats(binding: Mapping[str, Any], values: Sequence[int]) -> list[dict[str, int]]:
    dtype = binding.get("data_type", {})
    result = []
    for index, value in enumerate(values):
        beat = {"payload": _wire_value(int(value), dtype)}
        if "last" in binding.get("signals", {}):
            beat["last"] = int(index == len(values) - 1)
        result.append(beat)
    return result


async def initialize_testbench_owned_signals(
    dut: Any, interface: Mapping[str, Any]
) -> None:
    """Drive every non-clock DUT input to a known inactive value before reset."""

    for signal in interface.get("signals", []):
        if not isinstance(signal, Mapping):
            continue
        if signal.get("direction") != "input" or signal.get("role") == "clock":
            continue
        name = str(signal.get("name", ""))
        if not hasattr(dut, name):
            raise AutomaticCampaignError(f"DUT is missing frozen input signal {name!r}")
        getattr(dut, name).value = 0


async def _wait_active_edges(dut: Any, clock_name: str, count: int) -> None:
    from cocotb.triggers import RisingEdge

    for _ in range(max(0, int(count))):
        await RisingEdge(getattr(dut, clock_name))


async def _drive_after_event(
    event: Any,
    dut: Any,
    clock_name: str,
    binding: Mapping[str, Any],
    values: Sequence[int],
    *,
    accepted_event: Any | None,
    ready_lead_cycles: int,
    timeout_cycles: int,
) -> list[dict[str, int]]:
    """Present one phase at the first eligible falling edge after its predecessor."""

    from cocotb.triggers import FallingEdge, RisingEdge

    await event.wait()
    for _ in range(max(0, int(ready_lead_cycles))):
        await FallingEdge(getattr(dut, clock_name))
        await RisingEdge(getattr(dut, clock_name))
    return await drive_protocol_transfers(
        dut,
        clock_name,
        _channel(binding),
        _beats(binding, values),
        timeout_cycles=timeout_cycles,
        accepted_event=accepted_event,
    )


async def _wait_status_pulse(
    dut: Any,
    clock_name: str,
    status_bindings: Mapping[str, Any],
    role: str,
    *,
    timeout_cycles: int,
    require_runtime_completion: bool = False,
) -> None:
    """Wait for a required status pulse and optional monitor acknowledgement."""

    from cocotb.triggers import FallingEdge, RisingEdge, Timer

    names = tuple(map(str, status_bindings.get(role, ())))
    if not names:
        return
    if len(names) != 1:
        raise AutomaticCampaignError(
            f"automatic campaign requires one {role} signal, found {names!r}"
        )
    signal = getattr(dut, names[0])
    clock = getattr(dut, clock_name)
    tracker = get_coverage_tracker() if require_runtime_completion else None
    completion_before = (
        tracker.completion_event_count(names) if tracker is not None else None
    )
    for _ in range(timeout_cycles):
        # The protocol collector returns on a falling edge. Waiting two
        # picoseconds lets the immutable one-picosecond contract monitor sample
        # that same stable half-cycle before record_stimulus checks its ledger.
        await Timer(2, unit="ps")
        if int(signal.value):
            if tracker is None:
                return
            # A checked job must use the monitor's actual lifecycle evidence,
            # never a timing guess.  Yield past the current scheduler phase,
            # then advance falling edges only until that explicit event count
            # changes.  The non-recording callers still return while the pulse
            # itself is asserted.
            for _ in range(timeout_cycles):
                await Timer(2, unit="ps")
                if tracker.completion_event_count(names) > int(completion_before):
                    return
                await FallingEdge(clock)
            raise AutomaticCampaignError(
                f"{role} signal {names[0]!r} pulsed but the generated monitor "
                "did not record its lifecycle event"
            )
        await RisingEdge(clock)
        await FallingEdge(clock)
    raise AutomaticCampaignError(
        f"{role} signal {names[0]!r} did not pulse within {timeout_cycles} cycles"
    )


def _record_case(
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    observed_beats: Sequence[Mapping[str, Any]],
    *,
    beats_are_canonical_elements: bool = False,
) -> str:
    """`observed_beats` is one dict per output beat, under key "payload".

    Two distinct shapes reach here depending on the driver: a raw wire-word
    driver (e.g. AXI4-Lite) hands back one physical bus word per beat, which
    may pack several canonical elements together and must go through
    `unpack_words`. A driver that already resolved each canonical element
    itself (anything built on `OperationMemoryAdapter.read_output_values`,
    e.g. `execute_axi4_memory_job` or custom_mmio) hands back one *already
    decoded* element per beat -- passing those back through `unpack_words`
    double-unpacks them and is only invisible when elements_per_word==1.
    `beats_are_canonical_elements=True` marks the latter shape.
    """
    name = str(operation.get("operation_name", ""))
    output = list(operation.get("outputs", []))[0]
    if output.get("memory_mapping") and not beats_are_canonical_elements:
        observed_values = unpack_words(
            [int(beat["payload"]) for beat in observed_beats],
            output,
            _expected_elements(output, operation.get("dimensions", {})),
        )
    else:
        observed_values = [
            _logical_value(beat["payload"], output.get("data_type", {}))
            for beat in observed_beats
        ]
    observed = {
        str(output["data_object"]): observed_values
    }
    stimulus_id = record_stimulus(
        str(case.get("kind", "directed")),
        case.get("stimulus", {}),
        case.get("expected", {}),
        label=str(case.get("label", "code_owned_case")),
        operation_metadata={"schema_version": 2, "operations": [dict(operation)]},
        operations=(name,),
        observed=observed,
    )
    sample_operation(name, {}, str(case.get("kind", "directed")), stimulus_id)
    return stimulus_id


async def run_code_owned_operation_case(
    dut: Any,
    clock_name: str,
    operation_metadata: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    output_initial_stall_cycles: int | None = None,
    input_ready_lead_cycles: int = 0,
    command_reset_release: tuple[str, int] | None = None,
    timeout_cycles: int = 16384,
    record: bool = True,
) -> str | None:
    """Execute and record one complete legal canonical job from accepted transfers.

    `record=False`: see `run_code_owned_axi4_operation_case`'s docstring --
    same meaning, same reason. Used by `_run_arithmetic_blocked_operation_smoke`
    for a `ready_valid` operation whose arithmetic has no golden model.
    """

    name = str(operation_metadata.get("operation_name", ""))
    lifecycle = operation_metadata.get("lifecycle", {})
    commands = list(lifecycle.get("job_accept_channels", []))
    if len(commands) != 1 or not commands[0].get("legal_values"):
        raise AutomaticCampaignError(
            f"operation {name!r} needs one command channel with machine-readable legal_values"
        )
    outputs = list(operation_metadata.get("outputs", []))
    if len(outputs) != 1:
        raise AutomaticCampaignError(
            f"automatic campaign currently requires one serialized result object for {name!r}"
        )
    output = outputs[0]
    expected_count = _expected_elements(output, operation_metadata.get("dimensions", {}))
    import cocotb

    collector = cocotb.start_soon(
        collect_protocol_transfers(
            dut,
            clock_name,
            _channel(output),
            count=expected_count,
            until_last="last" in output.get("signals", {}),
            initial_valid_stall_cycles=output_initial_stall_cycles,
            timeout_cycles=timeout_cycles,
        )
    )
    from cocotb.triggers import Event

    inputs = list(operation_metadata.get("inputs", []))
    phase_events = [Event() for _ in range(len(inputs) + 1)]
    input_tasks = []
    for index, binding in enumerate(inputs):
        object_name = str(binding.get("data_object", ""))
        values = case.get("stimulus", {}).get(object_name)
        if not isinstance(values, list):
            raise AutomaticCampaignError(f"case is missing canonical input {object_name!r}")
        input_tasks.append(
            cocotb.start_soon(
                _drive_after_event(
                    phase_events[index],
                    dut,
                    clock_name,
                    binding,
                    values,
                    accepted_event=phase_events[index + 1],
                    ready_lead_cycles=input_ready_lead_cycles,
                    timeout_cycles=timeout_cycles,
                )
            )
        )
    if command_reset_release is None:
        await drive_accepted_command(
            dut,
            clock_name,
            commands[0],
            int(commands[0]["legal_values"][0]),
            timeout_cycles=timeout_cycles,
            accepted_event=phase_events[0],
        )
    else:
        reset_name, reset_active_value = command_reset_release
        await drive_accepted_command_on_reset_release(
            dut,
            clock_name,
            reset_name,
            reset_active_value,
            commands[0],
            int(commands[0]["legal_values"][0]),
            accepted_event=phase_events[0],
        )
    for task in input_tasks:
        await task
    observed_beats = await collector
    await _wait_status_pulse(
        dut,
        clock_name,
        lifecycle.get("status_bindings", {}),
        "completion",
        timeout_cycles=timeout_cycles,
        require_runtime_completion=record,
    )
    if not record:
        return None
    return _record_case(operation_metadata, case, observed_beats)


async def _run_case_with_input_stall(
    dut: Any,
    clock_name: str,
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    target_index: int,
    stall_cycles: int,
    *,
    timeout_cycles: int,
) -> str:
    """Present one input before its phase and complete a fully checked job."""

    import cocotb

    inputs = list(operation.get("inputs", []))
    if not 0 <= target_index < len(inputs) or stall_cycles < 1:
        raise AutomaticCampaignError("invalid input-stall campaign request")
    command = operation.get("lifecycle", {}).get("job_accept_channels", [])[0]
    output = list(operation.get("outputs", []))[0]
    output_count = _expected_elements(output, operation.get("dimensions", {}))
    collector = cocotb.start_soon(
        collect_protocol_transfers(
            dut,
            clock_name,
            _channel(output),
            count=output_count,
            until_last="last" in output.get("signals", {}),
            timeout_cycles=timeout_cycles,
        )
    )
    stimulus = case["stimulus"]
    target = inputs[target_index]
    target_task = None
    if target_index == 0:
        target_task = cocotb.start_soon(
            drive_protocol_transfers(
                dut,
                clock_name,
                _channel(target),
                _beats(target, stimulus[str(target["data_object"])]),
                timeout_cycles=timeout_cycles,
            )
        )
        delayed_command = cocotb.start_soon(
            _drive_command_after_edges(
                dut,
                clock_name,
                command,
                int(command["legal_values"][0]),
                stall_cycles - 1,
                timeout_cycles=timeout_cycles,
            )
        )
        await delayed_command
    else:
        await drive_accepted_command(
            dut,
            clock_name,
            command,
            int(command["legal_values"][0]),
            timeout_cycles=timeout_cycles,
        )
    if target_index == 0:
        assert target_task is not None
        await target_task
        remaining_start = 1
    else:
        for index in range(target_index - 1):
            binding = inputs[index]
            await drive_protocol_transfers(
                dut,
                clock_name,
                _channel(binding),
                _beats(binding, stimulus[str(binding["data_object"])]),
                timeout_cycles=timeout_cycles,
            )
        previous = inputs[target_index - 1]
        previous_beats = _beats(
            previous, stimulus[str(previous["data_object"])]
        )
        if previous_beats[:-1]:
            await drive_protocol_transfers(
                dut,
                clock_name,
                _channel(previous),
                previous_beats[:-1],
                timeout_cycles=timeout_cycles,
            )
        target_task = cocotb.start_soon(
            drive_protocol_transfers(
                dut,
                clock_name,
                _channel(target),
                _beats(target, stimulus[str(target["data_object"])]),
                timeout_cycles=timeout_cycles,
            )
        )
        delayed_previous = cocotb.start_soon(
            _drive_binding_after_edges(
                dut,
                clock_name,
                previous,
                previous_beats[-1:],
                stall_cycles - 1,
                timeout_cycles=timeout_cycles,
            )
        )
        await delayed_previous
        await target_task
        remaining_start = target_index + 1
    for binding in inputs[remaining_start:]:
        await drive_protocol_transfers(
            dut,
            clock_name,
            _channel(binding),
            _beats(binding, stimulus[str(binding["data_object"])]),
            timeout_cycles=timeout_cycles,
        )
    observed = await collector
    await _wait_status_pulse(
        dut,
        clock_name,
        operation.get("lifecycle", {}).get("status_bindings", {}),
        "completion",
        timeout_cycles=timeout_cycles,
        require_runtime_completion=True,
    )
    return _record_case(operation, case, observed)


async def _drive_command_after_edges(
    dut: Any,
    clock_name: str,
    command: Mapping[str, Any],
    value: int,
    edges: int,
    *,
    timeout_cycles: int,
) -> int:
    await _wait_active_edges(dut, clock_name, edges)
    return await drive_accepted_command(
        dut,
        clock_name,
        command,
        value,
        timeout_cycles=timeout_cycles,
    )


async def _drive_binding_after_edges(
    dut: Any,
    clock_name: str,
    binding: Mapping[str, Any],
    beats: Sequence[Mapping[str, Any]],
    edges: int,
    *,
    timeout_cycles: int,
) -> list[dict[str, int]]:
    await _wait_active_edges(dut, clock_name, edges)
    return await drive_protocol_transfers(
        dut,
        clock_name,
        _channel(binding),
        beats,
        timeout_cycles=timeout_cycles,
    )


async def _abort_operation_at_phase(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    phase: str,
    *,
    timeout_cycles: int,
) -> None:
    """Advance only from observed acceptances, then assert reset at one phase."""

    import cocotb

    clock_name = str(interface["clock"])
    reset_signal = next(
        item
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    )
    semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    active_value = (
        0 if "active-low" in semantic or "active low" in semantic else 1
    )
    if phase == "idle":
        await drive_protocol_reset(
            dut,
            clock_name,
            str(reset_signal["name"]),
            active_value,
            asserted_cycles=2,
        )
        return
    command = operation.get("lifecycle", {}).get("job_accept_channels", [])[0]
    await drive_accepted_command(
        dut,
        clock_name,
        command,
        int(command["legal_values"][0]),
        timeout_cycles=timeout_cycles,
    )
    inputs = list(operation.get("inputs", []))
    stimulus = case["stimulus"]
    if phase.startswith("input_"):
        target = phase.removeprefix("input_")
        found = False
        for binding in inputs:
            object_name = str(binding["data_object"])
            values = list(stimulus[object_name])
            if object_name.lower() == target:
                await drive_protocol_transfers(
                    dut,
                    clock_name,
                    _channel(binding),
                    _beats(binding, values[:1]),
                    timeout_cycles=timeout_cycles,
                )
                found = True
                break
            await drive_protocol_transfers(
                dut,
                clock_name,
                _channel(binding),
                _beats(binding, values),
                timeout_cycles=timeout_cycles,
            )
        if not found:
            raise AutomaticCampaignError(f"unknown reset-abort input phase {phase!r}")
    else:
        for binding in inputs:
            values = list(stimulus[str(binding["data_object"])])
            await drive_protocol_transfers(
                dut,
                clock_name,
                _channel(binding),
                _beats(binding, values),
                timeout_cycles=timeout_cycles,
            )
        if phase == "output":
            output = list(operation.get("outputs", []))[0]
            one_output = cocotb.start_soon(
                collect_protocol_transfers(
                    dut,
                    clock_name,
                    _channel(output),
                    count=1,
                    timeout_cycles=timeout_cycles,
                )
            )
            await one_output
        elif phase != "compute":
            raise AutomaticCampaignError(f"unknown reset-abort phase {phase!r}")
    await drive_protocol_reset(
        dut,
        clock_name,
        str(reset_signal["name"]),
        active_value,
        asserted_cycles=2,
    )


async def _probe_command_stall(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    case: Mapping[str, Any],
    stall_cycles: int,
    *,
    timeout_cycles: int,
) -> str:
    """Golden-check a job while the next command is held through retirement."""

    import cocotb

    clock_name = str(interface["clock"])
    command = operation.get("lifecycle", {}).get("job_accept_channels", [])[0]
    output = list(operation.get("outputs", []))[0]
    output_count = _expected_elements(output, operation.get("dimensions", {}))
    if output_count < 2:
        raise AutomaticCampaignError("command-stall probe needs at least two output beats")
    prefix_collector = cocotb.start_soon(
        collect_protocol_transfers(
            dut,
            clock_name,
            _channel(output),
            count=output_count - 1,
            timeout_cycles=timeout_cycles,
        )
    )
    await drive_accepted_command(
        dut,
        clock_name,
        command,
        int(command["legal_values"][0]),
        timeout_cycles=timeout_cycles,
    )
    for binding in operation.get("inputs", []):
        await drive_protocol_transfers(
            dut,
            clock_name,
            _channel(binding),
            _beats(binding, case["stimulus"][str(binding["data_object"])]),
            timeout_cycles=timeout_cycles,
        )
    prefix_beats = await prefix_collector
    next_command = cocotb.start_soon(
        drive_accepted_command(
            dut,
            clock_name,
            command,
            int(command["legal_values"][0]),
            timeout_cycles=timeout_cycles,
        )
    )
    final_collector = cocotb.start_soon(
        _collect_after_edges(
            dut,
            clock_name,
            output,
            stall_cycles - 1,
            timeout_cycles=timeout_cycles,
        )
    )
    final_beats = await final_collector
    # The protocol perturbation is part of the functional test: do not merely
    # consume the retiring job's output.  Wait until the monitor has observed
    # its completion pulse, then compare all accepted output beats against the
    # code-owned golden model before the held next command can be accepted.
    await _wait_status_pulse(
        dut,
        clock_name,
        operation.get("lifecycle", {}).get("status_bindings", {}),
        "completion",
        timeout_cycles=timeout_cycles,
        require_runtime_completion=True,
    )
    stimulus_id = _record_case(
        operation,
        case,
        [*prefix_beats, *final_beats],
    )
    await next_command
    reset_signal = next(
        item
        for item in interface.get("signals", [])
        if isinstance(item, Mapping) and item.get("role") == "reset"
    )
    semantic = str(reset_signal.get("semantic", "")).lower().replace("_", "-")
    active_value = 0 if "active-low" in semantic or "active low" in semantic else 1
    await drive_protocol_reset(
        dut,
        clock_name,
        str(reset_signal["name"]),
        active_value,
        asserted_cycles=2,
    )
    return stimulus_id


async def _collect_after_edges(
    dut: Any,
    clock_name: str,
    binding: Mapping[str, Any],
    edges: int,
    *,
    timeout_cycles: int,
) -> list[dict[str, int]]:
    await _wait_active_edges(dut, clock_name, edges)
    return await collect_protocol_transfers(
        dut,
        clock_name,
        _channel(binding),
        count=1,
        timeout_cycles=timeout_cycles,
    )


def _random_legal_stimulus(operation: Mapping[str, Any], *, seed: int) -> dict[str, list[int]]:
    """Well-typed but not golden-checked stimulus for every declared input.

    Unlike `generate_canonical_stimulus_suite`, this needs only each
    binding's own `data_type`/`dimensions` -- never `classifier_profile` --
    so it works identically whether an operation's arithmetic is
    `integer_matrix_multiply`, `llm_extension`, or anything else. It exists
    only to put real, legal traffic on the wire so protocol/lifecycle
    coverage gets sampled; there is no corresponding golden `expected`, and
    none is needed for that purpose.
    """

    from multigent.verifier_tool.pool.operation_metadata.canonical import _integer_bounds
    from multigent.verifier_tool.protocol.stimulus.adapter import expected_elements

    rng = random.Random(seed)
    dimensions = operation.get("dimensions", {})
    stimulus: dict[str, list[int]] = {}
    for binding in operation.get("inputs", []):
        low, high = _integer_bounds(binding["data_type"])
        count = expected_elements(binding, dimensions)
        stimulus[str(binding["data_object"])] = [rng.randint(low, high) for _ in range(count)]
    return stimulus


async def _run_arithmetic_blocked_operation_smoke(
    dut: Any,
    interface: Mapping[str, Any],
    operation: Mapping[str, Any],
    *,
    seed: int,
    timeout_cycles: int,
) -> None:
    """Drive one operation whose arithmetic has no code-owned golden model
    but whose protocol and lifecycle are otherwise fine
    (`_operation_protocol_lifecycle_reasons` empty), so its own
    protocol/lifecycle coverage still gets closed automatically. Dispatches
    to the same per-protocol drivers the full campaign uses, each called
    with `record=False` (drive and wait for completion, skip the
    golden-model check/coverage sample there is no golden model for).

    Covers all four automatable profiles: the three memory-mapped ones
    (axi4_lite, axi4, custom_mmio) and the generic `ready_valid` streaming
    path (`run_code_owned_operation_case`). This is deliberately the
    *basic* one-legal-job smoke only -- it does not replay
    `run_code_owned_verification_campaign`'s deeper `ready_valid`-only
    lifecycle sweep (abort-at-every-phase, handshake-arrival-order,
    input/output stall durations, illegal-command/recovery, command-stall
    probing), which stays golden-case-driven and unavailable here. Closing
    that gap too is a reasonable follow-on, not yet done.
    """

    case = {"stimulus": _random_legal_stimulus(operation, seed=seed)}
    io_profiles = {
        str(item.get("protocol_profile", ""))
        for item in [*operation.get("inputs", []), *operation.get("outputs", [])]
    }
    if io_profiles == {"axi4_lite"}:
        await run_code_owned_axi_lite_operation_case(
            dut, interface, operation, case, timeout_cycles=timeout_cycles, record=False,
        )
    elif io_profiles == {"axi4"}:
        await run_code_owned_axi4_operation_case(
            dut, interface, operation, case, seed=seed, timeout_cycles=timeout_cycles, record=False,
        )
    elif io_profiles == {"custom_mmio"}:
        await run_code_owned_custom_mmio_operation_case(
            dut, interface, operation, case, seed=seed, timeout_cycles=timeout_cycles, record=False,
        )
    elif io_profiles == {"ready_valid"}:
        await run_code_owned_operation_case(
            dut,
            str(interface["clock"]),
            operation,
            case,
            timeout_cycles=timeout_cycles,
            record=False,
        )


async def run_code_owned_verification_campaign(
    dut: Any,
    interface: Mapping[str, Any],
    operation_metadata: Mapping[str, Any],
    lifecycle_plan: Mapping[str, Any],
    *,
    randomized_count: int,
    seed: int = 0,
    clock_period_ns: int = 10,
    timeout_cycles: int = 16384,
) -> dict[str, Any]:
    """Run every supported base-operation vector plus reset/illegal lifecycle smoke.

    The campaign is intentionally independent of Verifier-authored test logic. Unknown
    operation profiles remain explicit LLM extensions; they are never approximated.
    """

    import cocotb
    from cocotb.clock import Clock

    clock_name = str(interface.get("clock", ""))
    reset = lifecycle_plan.get("reset", {})
    reset_name = str(reset.get("signal", ""))
    active_value = reset.get("active_value")
    if not clock_name or not reset_name or active_value not in {0, 1}:
        raise AutomaticCampaignError("campaign needs one resolved clock and reset polarity")
    await initialize_testbench_owned_signals(dut, interface)
    clock_task = cocotb.start_soon(
        Clock(getattr(dut, clock_name), clock_period_ns, unit="ns").start()
    )
    completed = 0
    try:
        await drive_protocol_reset(
            dut, clock_name, reset_name, int(active_value), asserted_cycles=2
        )
        for operation in operation_metadata.get("operations", []):
            operation_name = str(operation.get("operation_name", ""))
            if _operation_protocol_lifecycle_reasons(operation, operation_name):
                # Cannot drive this operation's own channel/command at all
                # (unrecognized protocol, unresolved capabilities, illegal
                # shape, ...) -- skip it, exactly like today, and leave it
                # entirely to hand-written source. Arithmetic support is
                # irrelevant here: there is no traffic to put on the wire
                # regardless of whether a golden model exists for it.
                continue
            if _operation_arithmetic_reasons(operation, operation_name):
                # Protocol and lifecycle ARE fine (checked above); only the
                # arithmetic (classifier_profile llm_extension, or a
                # declared feature this tool's classifier does not cover)
                # has no code-owned golden model. Still drive real,
                # well-typed traffic through the known protocol so the
                # always-on protocol/lifecycle monitor closes this
                # operation's own channel/command/status coverage --
                # correctness checking is left entirely to whatever
                # hand-written test the LLM must write for this operation's
                # arithmetic anyway, which necessarily drives the same
                # channel again for its own functional job.
                await _run_arithmetic_blocked_operation_smoke(
                    dut, interface, operation, seed=seed, timeout_cycles=timeout_cycles,
                )
                await drive_protocol_reset(
                    dut, clock_name, reset_name, int(active_value), asserted_cycles=2
                )
                continue
            suite = generate_canonical_stimulus_suite(
                operation,
                randomized_count=randomized_count,
                seed=seed,
            )
            blockers = [
                item
                for item in suite.get("exceptions", [])
                if item.get("code") not in {"unreachable"}
            ]
            if blockers:
                raise AutomaticCampaignError(
                    f"canonical suite has unresolved generation blockers: {blockers!r}"
                )
            cases = [
                *suite.get("directed", []),
                *suite.get("qualification", []),
                *suite.get("randomized", []),
            ]
            if not cases:
                raise AutomaticCampaignError(
                    f"canonical campaign generated no executable cases for {operation.get('operation_name')!r}"
                )
            io_profiles = {
                str(item.get("protocol_profile", ""))
                for item in [*operation.get("inputs", []), *operation.get("outputs", [])]
            }
            if io_profiles == {"axi4_lite"}:
                completed += await _run_axi_lite_operation_campaign(
                    dut,
                    interface,
                    operation,
                    cases,
                    timeout_cycles=timeout_cycles,
                )
                continue
            if io_profiles == {"axi4"}:
                axi4_campaign = (
                    _run_axi4_control_plane_operation_campaign
                    if operation.get("lifecycle", {}).get("policy", {}).get("job_acceptance")
                    == "control_plane_sequence"
                    else _run_axi4_operation_campaign
                )
                completed += await axi4_campaign(
                    dut,
                    interface,
                    operation,
                    cases,
                    timeout_cycles=timeout_cycles,
                )
                continue
            if io_profiles == {"custom_mmio"}:
                completed += await _run_custom_mmio_operation_campaign(
                    dut,
                    interface,
                    operation,
                    cases,
                    timeout_cycles=timeout_cycles,
                )
                continue
            extension_fields = _lifecycle_extension_fields(operation)
            if "reset_behavior" not in extension_fields:
                abort_phases = [
                    "idle",
                    *[
                        f"input_{str(binding.get('data_object', '')).lower()}"
                        for binding in operation.get("inputs", [])
                    ],
                    "compute",
                    "output",
                ]
                for phase in abort_phases:
                    await _abort_operation_at_phase(
                        dut,
                        interface,
                        operation,
                        cases[0],
                        phase,
                        timeout_cycles=timeout_cycles,
                    )
            # This first full post-abort job proves recovery/purity and makes
            # command VALID and READY arrive together on reset release.  The
            # runtime recomputes golden from only the new epoch's acceptances.
            await run_code_owned_operation_case(
                dut,
                clock_name,
                operation,
                cases[0],
                output_initial_stall_cycles=None,
                command_reset_release=(reset_name, int(active_value)),
                timeout_cycles=timeout_cycles,
            )
            completed += 1
            # Let each receiver expose READY alone for one full cycle before its
            # first VALID. Together with the phase-edge event chain above and the
            # early-presentation stall cases below, this closes all three legal
            # handshake arrival orders on every input channel.
            await run_code_owned_operation_case(
                dut,
                clock_name,
                operation,
                cases[0],
                input_ready_lead_cycles=1,
                timeout_cycles=timeout_cycles,
            )
            completed += 1
            # Phase-gated DUT-input READY cannot be controlled directly by the
            # testbench. Present the next channel before its phase, hold its first
            # beat stable for each taxonomy duration, then finish and golden-check
            # the complete job.
            for input_index in range(len(operation.get("inputs", []))):
                for stall_cycles in (1, 3, 6):
                    await _run_case_with_input_stall(
                        dut,
                        clock_name,
                        operation,
                        cases[0],
                        input_index,
                        stall_cycles,
                        timeout_cycles=timeout_cycles,
                    )
                    completed += 1
            # The first four jobs deterministically cover simultaneous output arrival
            # plus exact one/short/long stalls; remaining jobs keep READY asserted.
            output_stalls = (0, 1, 3, 6)
            for index, case in enumerate(cases):
                await run_code_owned_operation_case(
                    dut,
                    clock_name,
                    operation,
                    case,
                    output_initial_stall_cycles=(
                        output_stalls[index] if index < len(output_stalls) else None
                    ),
                    timeout_cycles=timeout_cycles,
                )
                completed += 1

            commands = list(operation.get("lifecycle", {}).get("job_accept_channels", []))
            if (
                len(commands) == 1
                and commands[0].get("illegal_value") is not None
                and not extension_fields
                & {"illegal_command_behavior", "error_style", "error_timing"}
            ):
                await drive_accepted_command(
                    dut,
                    clock_name,
                    commands[0],
                    int(commands[0]["illegal_value"]),
                    timeout_cycles=timeout_cycles,
                )
                await _wait_status_pulse(
                    dut,
                    clock_name,
                    operation.get("lifecycle", {}).get("status_bindings", {}),
                    "error",
                    timeout_cycles=timeout_cycles,
                )
                if operation["lifecycle"]["policy"]["error_style"] == "sticky_until_reset":
                    await drive_protocol_reset(
                        dut, clock_name, reset_name, int(active_value), asserted_cycles=2
                    )
                # Pulse errors permit immediate recovery; sticky errors first need
                # their declared reset clearing event. Both paths run a checked job.
                await run_code_owned_operation_case(
                    dut,
                    clock_name,
                    operation,
                    cases[0],
                    timeout_cycles=timeout_cycles,
                )
                completed += 1
            if "job_overlap" not in extension_fields:
                for stall_cycles in (1, 3, 6):
                    await _probe_command_stall(
                        dut,
                        interface,
                        operation,
                        cases[0],
                        stall_cycles,
                        timeout_cycles=timeout_cycles,
                    )
                    completed += 1
        return {"completed_checked_jobs": completed, "randomized_count": randomized_count}
    finally:
        clock_task.cancel()


__all__ = [
    "AutomaticCampaignError",
    "automatic_campaign_support",
    "initialize_testbench_owned_signals",
    "run_code_owned_axi_lite_operation_case",
    "run_code_owned_operation_case",
    "run_code_owned_verification_campaign",
]
