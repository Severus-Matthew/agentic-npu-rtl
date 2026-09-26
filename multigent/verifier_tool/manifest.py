"""Frozen verification manifests and finite taxonomy release gates."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


TAXONOMY_VERSION = "accelerator_verification_v2.15"
QUALIFICATION_CATALOG_VERSION = "v2.15"


class TaxonomyReleaseError(ValueError):
    """The selected finite trial scope is not ready for execution."""


_PREDICATES: dict[tuple[str, str], str] = {
    ("reset_behavior", "asserted"): "sample(reset)==active_value",
    ("reset_behavior", "deasserted"): "sample(reset)!=active_value",
    ("reset_behavior", "release"): "previous(reset)==active_value and sample(reset)!=active_value",
    ("completion_behavior", "observed"): "rising_edge(completion) after accepted_legal_job",
    ("completion_behavior", "back_to_back"): "count(rising_edge(completion))>=2",
    ("error_behavior", "inactive"): "sample(error)==0 during legal_work",
    ("error_behavior", "asserted"): "sample(error)==1 after contracted_illegal_input",
    ("error_behavior", "recovered"): "previous(error)==1 and sample(error)==0",
}


def _json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def manifest_hash(value: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 identity for a JSON-compatible manifest."""

    return hashlib.sha256(_json(value)).hexdigest()


def _declarative_bin_predicate(item: Mapping[str, Any]) -> dict[str, Any] | None:
    values = item.get("values")
    if isinstance(values, Mapping):
        return {"kind": "sample_values", "values": dict(values)}
    if isinstance(item.get("event"), str):
        return {"kind": "observed_event", "event": str(item["event"])}
    interval = item.get("range")
    if isinstance(interval, list) and len(interval) == 2:
        return {"kind": "inclusive_range", "low": interval[0], "high": interval[1]}
    return None


def compile_verification_manifest(
    interface_plan: Mapping[str, Any],
    operation_plan: Mapping[str, Any],
    lifecycle_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile immutable obligations and support dispositions before simulation."""

    obligations: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for obligation in [
        *interface_plan.get("obligations", []),
        *operation_plan.get("obligations", []),
        *(lifecycle_plan or {}).get("obligations", []),
    ]:
        obligation_id = str(obligation["id"])
        bins: list[dict[str, Any]] = []
        for raw_bin in obligation.get("bins", []):
            item = dict(raw_bin)
            required = bool(item.get("required", True))
            applicability = dict(
                item.get(
                    "applicability",
                    {
                        "status": (
                            "required_reachable" if required else "diagnostic_only"
                        ),
                        "basis": "resolved coverage plan",
                    },
                )
            )
            status = str(applicability.get("status", "metadata_missing"))
            if status in {
                "metadata_missing",
                "generation_inconclusive",
                "unsupported_known_feature",
                "llm_extension_required",
            }:
                unresolved.append(f"{obligation_id}.{item.get('name')}:{status}")
            predicate = item.get("predicate") or _declarative_bin_predicate(item) or {
                "kind": "registered_runtime_predicate",
                "expression": _PREDICATES.get(
                    (str(obligation.get("template", "")), str(item.get("name", ""))),
                    f"{obligation.get('template')}.{item.get('name')}",
                ),
            }
            bins.append(
                {
                    "id": f"{obligation_id}.{item['name']}",
                    "required": required and status == "required_reachable",
                    "minimum_hits": int(item.get("minimum_hits", 1)),
                    "predicate": predicate,
                    "applicability": applicability,
                }
            )
        category = str(obligation.get("category", ""))
        if not category:
            category = (
                "operation"
                if obligation.get("template") == "operation_coverpoint"
                else "lifecycle"
                if obligation.get("template")
                in {
                    "reset_behavior",
                    "busy_behavior",
                    "completion_behavior",
                    "error_behavior",
                    "command_legality",
                    "job_lifecycle",
                    "reset_abort_phase",
                    "post_reset_purity",
                }
                else "protocol"
            )
        obligations.append(
            {
                "id": obligation_id,
                "category": category,
                "sample_unit": str(
                    obligation.get(
                        "sample_unit",
                        "checked_job" if obligation.get("template") == "operation_coverpoint" else obligation.get("scope", "event"),
                    )
                ),
                "controllability": str(
                    obligation.get("controllability", "resolved_from_endpoint_roles")
                ),
                "bins": bins,
            }
        )
    operation_support = []
    for operation in operation_plan.get("operation_metadata", {}).get("operations", []):
        arithmetic = operation.get("arithmetic", {})
        dimensions = dict(operation.get("dimensions", {}))

        def object_summary(binding: Mapping[str, Any]) -> dict[str, Any]:
            axes = list(map(str, binding.get("dimensions", [])))
            extents = [dimensions.get(axis) for axis in axes]
            expected_elements = (
                math.prod(map(int, extents))
                if extents and all(isinstance(value, int) and value >= 0 for value in extents)
                else None
            )
            return {
                "data_object": str(binding.get("data_object", "")),
                "object_role": str(binding.get("object_role", "")),
                "channel": str(binding.get("channel", "")),
                "dimensions": axes,
                "expected_logical_elements": expected_elements,
                "data_type": dict(binding.get("data_type", {})),
                "signals": dict(binding.get("signals", {})),
                "serialization": dict(binding.get("serialization", {})),
            }

        operation_support.append(
            {
                "operation_name": str(operation.get("operation_name", "")),
                "family": str(operation.get("family", "")),
                "classifier_profile": str(arithmetic.get("classifier_profile", "")),
                "support_status": str(
                    arithmetic.get(
                        "support_status",
                        "llm_extension_required"
                        if arithmetic.get("classifier_profile") == "llm_extension"
                        else "metadata_missing",
                    )
                ),
                "dimensions": dimensions,
                "stage_order": list(arithmetic.get("stage_order", [])),
                "arithmetic": dict(arithmetic),
                "inputs": [
                    object_summary(item)
                    for item in operation.get("inputs", [])
                    if isinstance(item, Mapping)
                ],
                "outputs": [
                    object_summary(item)
                    for item in operation.get("outputs", [])
                    if isinstance(item, Mapping)
                ],
                "lifecycle": dict(operation.get("lifecycle", {})),
            }
        )
    result = {
        "schema_version": 2,
        "taxonomy_version": TAXONOMY_VERSION,
        "qualification_catalog_version": QUALIFICATION_CATALOG_VERSION,
        "identity_inputs": [
            "contract_hash",
            "resolved_parameter_hash",
            "dut_revision_hash",
            "tool_version_hash",
            "classifier_version_hash",
        ],
        "protocol_groups": list(
            interface_plan.get("standard_protocol_plan", {}).get("groups", [])
        ),
        "operation_support": operation_support,
        "obligations": obligations,
        "unresolved_obligations": sorted(unresolved),
        "closure": {
            "freeze_before_execution": True,
            "require_all_applicable_checkers_active": True,
            "require_complete_transaction_ledgers": True,
            "require_no_unresolved_obligations": True,
            "diagnostic_bins_in_denominator": False,
            "extension_semantics_reported_separately": True,
        },
    }
    result["manifest_hash"] = manifest_hash(result)
    return result


def build_trial_manifest(
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
    verification_manifest: Mapping[str, Any],
    *,
    intended_trials: int,
    randomized_transactions_minimum: int = 0,
) -> dict[str, Any]:
    """Freeze the exact campaign scope and five independent verification claims."""

    if not isinstance(intended_trials, int) or intended_trials <= 0:
        raise TaxonomyReleaseError("intended_trials must be a positive integer")
    channels = [
        item for item in interface.get("channels", []) if isinstance(item, Mapping)
    ]
    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    protocol_profiles = sorted(
        {str(item.get("protocol_profile", "")) for item in channels}
    )
    edition_catalog = {
        "axi4": "ARM IHI 0022H",
        "axi4_lite": "ARM IHI 0022H B1",
        "axi4_stream": "ARM IHI 0051B",
        "custom_mmio": "verifier_tool generic memory pattern (not an industry standard)",
        "ready_valid": "frozen contract-defined profile",
    }
    endpoint_bindings: dict[str, Any] = {}
    for channel in channels:
        name = str(channel.get("name", ""))
        attached = [signal for signal in signals if signal.get("channel") == name]
        role_bindings: dict[str, list[str]] = {}
        for signal in attached:
            role_bindings.setdefault(str(signal.get("role", "")), []).append(
                str(signal.get("name", ""))
            )
        endpoint_bindings[name] = {
            "protocol_profile": str(channel.get("protocol_profile", "")),
            "protocol_group": channel.get("protocol_group"),
            "protocol_channel": channel.get("protocol_channel"),
            "direction": str(channel.get("direction", "")),
            "endpoint_role": (
                "dut_producer"
                if channel.get("direction") == "output"
                else "dut_consumer"
                if channel.get("direction") == "input"
                else "unresolved"
            ),
            "role_bindings": role_bindings,
        }
    parameters = {
        str(item.get("name", "")): {
            "default_value": str(item.get("default_value", "")),
            "legality_constraint": str(item.get("legality_constraint", "")),
        }
        for item in architecture.get("parameters", [])
        if isinstance(item, Mapping)
    }
    dimensions = {
        str(item.get("name", "")): {
            "minimum": item.get("minimum"),
            "maximum": item.get("maximum"),
            "runtime_configurable": bool(item.get("runtime_configurable", False)),
            "bound_parameter": str(item.get("bound_parameter", "")),
        }
        for item in architecture.get("dimensions", [])
        if isinstance(item, Mapping)
    }
    clocks = [str(item.get("name", "")) for item in signals if item.get("role") == "clock"]
    resets = [
        {
            "name": str(item.get("name", "")),
            "semantic": str(item.get("semantic", "")),
        }
        for item in signals
        if item.get("role") == "reset"
    ]
    from multigent.verifier_tool.qualification import qualification_source_hash

    result = {
        "schema_version": 2,
        "taxonomy_version": TAXONOMY_VERSION,
        "taxonomy_source_hash": qualification_source_hash(),
        "intended_trials": intended_trials,
        "trial_semantics": {
            "completed_trial_requires": [
                "verifier_api_repair_attempts_reach_all_deterministic_gates",
                "generated_tb_manual_semantic_audit_completed",
            ],
            "api_attempts_are_not_trials": True,
            "count_only_manually_audited_deterministic_candidates": True,
        },
        "scope": {
            "protocol_profiles": protocol_profiles,
            "protocol_editions": {
                profile: edition_catalog.get(profile, "contract-defined")
                for profile in protocol_profiles
            },
            "endpoint_bindings": endpoint_bindings,
            "parameter_domains": parameters,
            "dimension_domains": dimensions,
            "observation_domains": {
                "clocks": clocks,
                "resets": resets,
                "sampling_rule": "stable_pre_active_values_qualified_at_receiving_active_edge",
            },
            "operation_support": list(
                verification_manifest.get("operation_support", [])
            ),
            "randomized_policy": {
                "completed_checked_jobs_minimum": int(randomized_transactions_minimum),
                "replay_requires": [
                    "generator_version",
                    "seed",
                    "accepted_inputs",
                    "accepted_schedule",
                ],
            },
            "claims": [
                "mathematical_correctness",
                "protocol_correctness",
                "transaction_completeness",
                "scenario_coverage",
                "structural_tb_validity",
            ],
        },
        "contract_hash": manifest_hash(
            {"architecture": architecture, "interface": interface}
        ),
        "verification_manifest_hash": str(
            verification_manifest.get("manifest_hash", "")
        ),
    }
    result["trial_manifest_hash"] = manifest_hash(result)
    return result


def validate_release_gate(
    trial_manifest: Mapping[str, Any],
    verification_manifest: Mapping[str, Any],
    qualification_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the review checklist for the manifest's declared finite scope."""

    from multigent.verifier_tool.qualification import validate_qualification_evidence

    failures: list[str] = []
    checklist: dict[str, str] = {}
    evidence: dict[str, Any] = {}

    def check(name: str, condition: bool, detail: str, proof: Any = None) -> None:
        checklist[name] = "PASS" if condition else "BLOCKED"
        evidence[name] = proof
        if not condition:
            failures.append(f"{name}: {detail}")

    def inapplicable(name: str, reason: str) -> None:
        checklist[name] = "INAPPLICABLE"
        evidence[name] = reason

    scope = trial_manifest.get("scope", {})
    selected = set(scope.get("protocol_profiles", []))
    endpoints = scope.get("endpoint_bindings", {})
    operations = verification_manifest.get("operation_support", [])
    obligations = verification_manifest.get("obligations", [])
    unresolved = list(verification_manifest.get("unresolved_obligations", []))
    qualification_failures = validate_qualification_evidence(qualification_evidence)
    qualified = not qualification_failures

    manifest_identity_ok = bool(trial_manifest.get("trial_manifest_hash")) and (
        trial_manifest.get("verification_manifest_hash")
        == verification_manifest.get("manifest_hash")
    ) and (
        not isinstance(qualification_evidence, Mapping)
        or trial_manifest.get("taxonomy_source_hash")
        == qualification_evidence.get("source_hash")
    )
    scope_complete = bool(selected) and bool(endpoints) and bool(
        scope.get("protocol_editions")
    ) and bool(scope.get("dimension_domains")) and bool(scope.get("claims"))
    check(
        "manifest_scope",
        manifest_identity_ok and scope_complete,
        "trial identity or exact protocol/endpoint/parameter/claim scope is incomplete",
        {
            "profiles": sorted(selected),
            "endpoints": sorted(endpoints),
            "claims": scope.get("claims", []),
        },
    )

    exact_bindings = bool(endpoints) and all(
        item.get("endpoint_role") in {"dut_producer", "dut_consumer"}
        and len(item.get("role_bindings", {}).get("valid", [])) == 1
        and (
            len(item.get("role_bindings", {}).get("ready", [])) == 1
            or item.get("protocol_profile") == "axi4_stream"
        )
        for item in endpoints.values()
    )
    check(
        "exact_field_bindings",
        exact_bindings,
        "channel roles are ambiguous or unresolved",
        endpoints,
    )
    check(
        "optional_fields_and_defaults",
        qualified,
        "; ".join(qualification_failures),
        "Q-BIND-001/Q-AXIS-002",
    )
    observation = scope.get("observation_domains", {})
    check(
        "clock_reset_sampling",
        len(observation.get("clocks", [])) == 1
        and len(observation.get("resets", [])) == 1
        and bool(observation.get("sampling_rule"))
        and qualified,
        "one exact clock/reset domain and qualified sampling evidence are required",
        observation,
    )
    check("stall_content_and_acceptance", qualified, "; ".join(qualification_failures), "Q-RV-001")
    check("no_cross_profile_axi_inheritance", qualified, "; ".join(qualification_failures), "full regression")

    known = [item for item in operations if item.get("classifier_profile") != "llm_extension"]
    exact_numeric = bool(known) and all(
        item.get("support_status") == "supported_restricted_integer_gemm"
        and item.get("stage_order")
        and item.get("arithmetic", {}).get("product_data_type")
        and item.get("arithmetic", {}).get("accumulator_data_type")
        and item.get("arithmetic", {}).get("result_data_type")
        for item in known
    )
    mappings_complete = bool(known) and all(
        item.get("inputs")
        and item.get("outputs")
        and all(
            binding.get("expected_logical_elements") is not None
            and binding.get("serialization", {}).get("index_order")
            and binding.get("signals", {}).get("payload")
            for binding in [*item.get("inputs", []), *item.get("outputs", [])]
        )
        for item in known
    )
    lifecycle_complete = bool(known) and all(
        item.get("lifecycle", {}).get("job_key")
        and item.get("lifecycle", {}).get("result_retirement")
        and item.get("lifecycle", {}).get("reset_disposition")
        for item in known
    )
    command_lifecycle_selected = any(
        item.get("lifecycle", {}).get("job_accept_channels") for item in known
    )
    command_lifecycle_complete = command_lifecycle_selected and all(
        len(item.get("lifecycle", {}).get("job_accept_channels", [])) == 1
        and item.get("lifecycle", {}).get("job_accept_channels", [{}])[0].get("legal_values")
        and item.get("lifecycle", {}).get("status_bindings")
        for item in known
    )
    check("trusted_golden_from_accepted_inputs", exact_numeric and mappings_complete and qualified, "trusted numeric/accepted-event qualification is incomplete", "Q-GOLD-001/Q-PROV-001")
    check("exact_numeric_stages", exact_numeric, "known operation lacks exact product/accumulator/result stages", [item.get("stage_order") for item in known])
    check("prefix_excursion_is_reference_evidence", exact_numeric and qualified, "stage excursion classifier is not qualified", "Q-GOLD-001")
    check("discriminating_directed_cases", qualified, "; ".join(qualification_failures), "qualification catalog plus canonical qualification vectors")
    check("physical_to_logical_mapping", mappings_complete, "logical counts/index orders/signal bindings are incomplete", [item.get("inputs") for item in known])
    check("complete_job_disposition", mappings_complete and lifecycle_complete and qualified, "job/result accounting is incomplete", "Q-JOB-001/Q-FINAL-001")
    check("capability_gated_operation_modes", exact_numeric and not unresolved, "operation modes contain unresolved support", [item.get("support_status") for item in operations])
    check("completion_vs_retirement", lifecycle_complete, "completion/result retirement lifecycle is incomplete", [item.get("lifecycle") for item in known])
    check("reset_epoch_disposition", lifecycle_complete and qualified, "reset epoch disposition is incomplete", "Q-JOB-001")
    if command_lifecycle_selected:
        check("machine_readable_command_legality", command_lifecycle_complete and qualified, "command legal/illegal encoding is unresolved", "Q-LIFE-001")
        check("lifecycle_phase_stimulus", command_lifecycle_complete and qualified, "reset-abort phase stimulus is not qualified", "Q-LIFE-003")
        check("lifecycle_temporal_assertions", command_lifecycle_complete and qualified, "busy/completion/error lifecycle assertions are not qualified", "Q-LIFE-005")
        check("automatic_campaign_execution_path", command_lifecycle_complete and qualified, "the immutable code-owned campaign is not qualified", "Q-LIFE-004")
    else:
        for name in (
            "machine_readable_command_legality",
            "lifecycle_phase_stimulus",
            "lifecycle_temporal_assertions",
            "automatic_campaign_execution_path",
        ):
            inapplicable(name, "selected operation has no command/job lifecycle channel")

    selected = set(trial_manifest.get("scope", {}).get("protocol_profiles", []))
    axi_selected = bool(selected & {"axi4", "axi4_lite"})
    stream_selected = "axi4_stream" in selected
    for name, applicable, proof in (
        ("axi_aw_w_independence", axi_selected, "Q-AXI-001/Q-LITE-001"),
        ("axi_geometry_and_last", "axi4" in selected, "Q-AXI-002/Q-AXI-004"),
        ("axi_response_presentation", axi_selected, "Q-AXI-003/Q-AXI-004"),
        ("axi_id_ordering", "axi4" in selected, "Q-AXI-003/Q-AXI-004"),
        ("axi_error_burst_continuation", "axi4" in selected, "Q-AXI-004"),
        ("axi_lite_restrictions", "axi4_lite" in selected, "Q-LITE-001/Q-LITE-002"),
        ("axis_optional_and_interleaved", stream_selected, "Q-AXIS-001/Q-AXIS-002/Q-AXIS-003"),
        ("axis_byte_packet_job_separation", stream_selected, "Q-AXIS-001/Q-AXIS-003"),
    ):
        if applicable:
            check(name, qualified, "; ".join(qualification_failures), proof)
        else:
            inapplicable(name, f"profiles {sorted(selected)!r} do not select this rule")

    exact_bins = bool(obligations) and all(
        item.get("sample_unit")
        and item.get("controllability")
        and all(
            bin_spec.get("predicate")
            and bin_spec.get("applicability", {}).get("status")
            and int(bin_spec.get("minimum_hits", 0)) >= 1
            for bin_spec in item.get("bins", [])
        )
        for item in obligations
    )
    diagnostics_separate = all(
        not bin_spec.get("required")
        for item in obligations
        for bin_spec in item.get("bins", [])
        if bin_spec.get("applicability", {}).get("status")
        in {"diagnostic_only", "inapplicable", "proven_unreachable"}
    )
    random_policy = scope.get("randomized_policy", {})
    check("exact_bin_manifest", exact_bins, "one or more bins lack predicate/sample unit/controllability/reachability", len(obligations))
    check("unresolved_obligations_block", not unresolved, f"unresolved obligations: {unresolved!r}", unresolved)
    check("diagnostic_bins_separate", diagnostics_separate, "diagnostic/inapplicable bins enter the required denominator", None)
    check("completed_random_jobs_and_replay", int(random_policy.get("completed_checked_jobs_minimum", 0)) > 0 and len(random_policy.get("replay_requires", [])) == 4, "randomized completed-job minimum or replay identity is missing", random_policy)
    check("trusted_runtime_non_vacuity", qualified, "; ".join(qualification_failures), "Q-MON-001/Q-PROV-001/Q-FINAL-001")
    check("generated_block_authority", qualified, "; ".join(qualification_failures), "Q-TAMPER-001/Q-FAKE-001")
    check("bounded_static_claims", qualified, "; ".join(qualification_failures), "Q-FAKE-001")
    check("finite_liveness_disposition", qualified, "; ".join(qualification_failures), "Q-FINAL-001")
    check("finite_positive_negative_qualification", qualified, "; ".join(qualification_failures), qualification_evidence)
    extension_visible = all(
        item.get("classifier_profile") != "llm_extension"
        or item.get("support_status") == "llm_extension_required"
        for item in operations
    )
    check("extension_trust_visible", extension_visible and not unresolved, "extension trust/support status is unresolved", [item.get("support_status") for item in operations])
    check("five_separate_final_verdicts", scope.get("claims") == ["mathematical_correctness", "protocol_correctness", "transaction_completeness", "scenario_coverage", "structural_tb_validity"], "the five final claims are not frozen separately", scope.get("claims"))
    check("tool_defect_ownership", qualified, "; ".join(qualification_failures), "Q-OWNER-001")
    check("stable_local_findings", qualified, "; ".join(qualification_failures), "Q-OWNER-001")

    status = "READY" if not failures else "BLOCKED"
    return {
        "schema_version": 2,
        "status": status,
        "checklist": checklist,
        "evidence": evidence,
        "failures": failures,
        "trial_manifest_hash": trial_manifest.get("trial_manifest_hash"),
        "verification_manifest_hash": verification_manifest.get("manifest_hash"),
    }


def require_release_ready(
    trial_manifest: Mapping[str, Any],
    verification_manifest: Mapping[str, Any],
    qualification_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = validate_release_gate(
        trial_manifest, verification_manifest, qualification_evidence
    )
    if result["status"] != "READY":
        raise TaxonomyReleaseError("; ".join(result["failures"]))
    return result


__all__ = [
    "QUALIFICATION_CATALOG_VERSION",
    "TAXONOMY_VERSION",
    "TaxonomyReleaseError",
    "build_trial_manifest",
    "compile_verification_manifest",
    "manifest_hash",
    "require_release_ready",
    "validate_release_gate",
]
