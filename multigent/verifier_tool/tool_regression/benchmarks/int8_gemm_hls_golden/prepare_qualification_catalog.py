"""Prepare every HLS benchmark qualification target without simulating it.

The benchmark matrix contains three different kinds of evidence target:

* assertion/checker fault injection, often an RTL mutant;
* environment-owned protocol responses, which require driver fault injection;
* coverage bins, which require observed stimulus evidence rather than a broken RTL.

This tool keeps those categories explicit, validates all executable named RTL
mutants, and writes a complete machine-readable catalog.  It intentionally does
not compile RTL or call an agent/API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from .batch_qualify_mutants import validate_registry
from .qualify_named_mutant import MUTANTS, mutant_definition
from multigent.verifier_tool.tool_regression.paths import (
    QUALIFICATION_ROOT,
    REPOSITORY_ROOT,
)


HERE = Path(__file__).resolve().parent
MATRIX = QUALIFICATION_ROOT / "hls_benchmark_qualification_matrix.md"


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _feature(text: str) -> str:
    match = re.search(r"`([^`]+)`", text)
    return match.group(1) if match else text.strip()


def _code_items(text: str) -> list[str]:
    """Return individual Markdown code spans from one matrix cell."""

    if text.strip() == "none":
        return []
    items = re.findall(r"`([^`]+)`", text)
    return items if items else [item.strip() for item in text.split(",") if item.strip()]


def _named_targets() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name, spec in MUTANTS.items():
        _edits, diagnostic = mutant_definition(spec)
        marker = "feature="
        if marker in diagnostic:
            feature_id = diagnostic.split(marker, 1)[1].split(";", 1)[0].strip()
            result.setdefault(feature_id, []).append(name)
    return result


def _assertion_recipe(domain: str, feature_id: str) -> tuple[str, str, str]:
    """Return (kind, readiness, rationale) for an unqualified assertion."""

    if domain == "lifecycle":
        if feature_id == "lifecycle.reset.outputs_match_declared_reset_values":
            return (
                "rtl_mutant",
                "recipe_prepared",
                "Drive one declared DUT output away from reset_value only while reset is active.",
            )
        if feature_id.endswith("completion_matches_final_output"):
            return ("rtl_mutant", "named_registry", "Force completion before final output retirement.")
        return (
            "lifecycle_sequence_variant",
            "requires_harness_support",
            "The HLS contract observes lifecycle through AXI4-Lite control-plane polling; prepare a named sequence/checker case rather than claiming a generic timeout.",
        )

    if feature_id.startswith("channel.") and feature_id.endswith(".stall_stability"):
        channel = feature_id[len("channel.") : -len(".stall_stability")]
        environment_owned = channel in {
            "m_axi_gmem_a_r", "m_axi_gmem_b_r", "m_axi_gmem_c_b",
            "s_axi_control_ar", "s_axi_control_aw", "s_axi_control_w",
        }
        if environment_owned:
            return (
                "driver_fault_injection",
                "recipe_prepared",
                "This channel's producer is the verification environment; perturb content on stalled release through the reusable driver.",
            )
        return (
            "rtl_mutant",
            "requires_named_mutant",
            "Change one DUT-owned content field only when READY releases a generated stall.",
        )

    group = feature_id.split(".")[1] if feature_id.startswith("protocol.") else ""
    rule = feature_id.rsplit(".", 1)[-1]
    read_only_group = group in {"gmem_a", "gmem_b"}
    write_only_group = group == "gmem_c"
    if read_only_group and rule.startswith("write_"):
        return ("not_applicable", "topology_excluded", "The frozen group has no write channel.")
    if write_only_group and rule.startswith("read_"):
        return ("not_applicable", "topology_excluded", "The frozen group has no read channel.")
    if rule == "exclusive_response_consistency":
        return (
            "driver_fault_injection",
            "recipe_prepared",
            "Return EXOKAY for a non-exclusive request through the reusable AXI memory model.",
        )
    if rule == "exclusive_access_restrictions":
        return (
            "contract_capability_variant",
            "recipe_prepared",
            "Use the frozen physical LOCK binding and inject a logical exclusive request against exclusive_access=false.",
        )
    if rule in {
        "response_after_request", "response_id_matches_request", "read_last_matches_length",
    }:
        return (
            "driver_fault_injection",
            "recipe_prepared",
            "The relevant response is environment-owned for this manager port; inject it through the reusable AXI memory model.",
        )
    if rule in {
        "standard_signal_widths", "data_width_is_32_or_64", "strobe_width_matches_data_bytes",
    }:
        return (
            "contract_rtl_shape_variant",
            "recipe_prepared",
            "Signal widths are compile-time interface facts and require a matched contract/RTL shape variant.",
        )
    if rule == "optional_id_return_and_in_order_completion" and group == "control":
        return (
            "not_applicable",
            "topology_excluded",
            "The frozen AXI4-Lite interface has no response ID fields.",
        )
    if rule == "ready_valid_stability":
        return (
            "derived_channel_checker_evidence",
            "checker_alias_review",
            "The executable stability checker reports per-channel feature IDs; qualification must aggregate all applicable channel.stall_stability evidence or add a direct group diagnostic.",
        )
    if rule == "write_address_and_data_are_independent":
        return (
            "checker_implementation_gap",
            "requires_harness_support",
            "The standard rule is declared, but the current AXI checker has no direct diagnostic for coupling AW acceptance to W or vice versa.",
        )
    if rule == "valid_low_during_reset":
        return (
            "rtl_mutant",
            "requires_named_mutant",
            "Force one producer-owned VALID high during the declared reset window while preserving reset values elsewhere.",
        )
    return (
        "rtl_mutant",
        "requires_named_mutant",
        "Prepare one exact-anchor mutation that reaches this named deterministic checker.",
    )


def _recipe_details(kind: str, feature_id: str) -> dict[str, Any]:
    """Provide machine-readable parameters for every non-named recipe."""

    channel = ""
    if feature_id.startswith("channel."):
        channel = feature_id[len("channel.") :].rsplit(".", 1)[0]
    group = feature_id.split(".")[1] if feature_id.startswith("protocol.") else ""
    rule = feature_id.rsplit(".", 1)[-1]
    if kind == "driver_fault_injection":
        if rule == "stall_stability":
            field_by_channel = {
                "m_axi_gmem_a_r": "data", "m_axi_gmem_b_r": "data",
                "m_axi_gmem_c_b": "resp", "s_axi_control_ar": "addr",
                "s_axi_control_aw": "addr", "s_axi_control_w": "data",
            }
            return {
                "strategy": "channel_schedule_fault",
                "channel": channel,
                "stall_cycles": [1, 3, 6],
                "fault": "change_content_on_ready_release",
                "field": field_by_channel.get(channel, "payload"),
            }
        if rule == "read_last_matches_length":
            return {"strategy": "axi_response_fault", "group": group, "fault": "invert_rlast_on_nonfinal_or_final_beat"}
        if rule == "response_after_request":
            return {"strategy": "axi_response_fault", "group": group, "fault": "present_response_before_request"}
        if rule == "response_id_matches_request":
            return {"strategy": "axi_response_fault", "group": group, "fault": "return_nonmatching_id"}
        if rule == "exclusive_response_consistency":
            return {"strategy": "axi_response_fault", "group": group, "fault": "return_exokay_for_nonexclusive_request"}
    if kind == "contract_rtl_shape_variant":
        return {"strategy": "matched_contract_rtl_variant", "target_rule": rule, "group": group}
    if kind == "contract_capability_variant":
        return {"strategy": "physical_lock_fault", "target_rule": rule, "group": group}
    if kind == "lifecycle_sequence_variant":
        return {"strategy": "control_plane_lifecycle_fault", "feature_id": feature_id}
    if kind in {"protocol_schedule_observation", "protocol_descriptor_observation"}:
        return {"strategy": kind, "feature_id": feature_id, "credit": "observed_runtime_evidence_only"}
    if kind == "directed_operation_evidence":
        return {"strategy": "directed_operation_case", "feature_id": feature_id, "credit": "accepted_inputs_plus_golden_trace_plus_correct_output"}
    if kind == "lifecycle_stimulus_observation":
        return {"strategy": "lifecycle_event_schedule", "feature_id": feature_id, "credit": "observed_runtime_evidence_only"}
    return {"strategy": kind, "feature_id": feature_id}


def _coverage_recipe(domain: str, feature_id: str) -> tuple[str, str]:
    if domain == "operation":
        return (
            "directed_operation_evidence",
            "Generate a directed logical tensor, confirm accepted canonical inputs, golden trace classification, and DUT correctness.",
        )
    if domain == "lifecycle":
        return (
            "lifecycle_stimulus_observation",
            "Drive the declared lifecycle event and credit only the runtime-observed transition.",
        )
    if "stall_stability" in feature_id or "handshake_" in feature_id:
        return (
            "protocol_schedule_observation",
            "Use the reusable channel_schedule strategy and credit only observed handshakes/stall lengths.",
        )
    return (
        "protocol_descriptor_observation",
        "Use a contract-selected driver descriptor and credit only the monitor-observed field/bin.",
    )


def build_catalog(matrix_path: Path = MATRIX) -> dict[str, Any]:
    named_targets = _named_targets()
    cases: list[dict[str, Any]] = []
    section = ""
    for line in matrix_path.read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or "`" not in line:
            continue
        cells = _cells(line)
        if section == "Resolved coverage obligations" and len(cells) >= 5:
            domain, feature_id, required_bins, _prior, strict = cells[:5]
            feature_id = _feature(feature_id)
            kind, rationale = _coverage_recipe(domain, feature_id)
            evidence_qualified = strict.strip().startswith("E")
            cases.append({
                "target_type": "coverage_obligation",
                "domain": domain,
                "feature_id": feature_id,
                "required_bins": _code_items(required_bins),
                # Coverage is qualified by real observed HLS evidence plus an
                # exact per-bin evidence ablation, not by pretending that a
                # coverage target is an RTL correctness assertion.
                "strict_status": (
                    "evidence_qualified" if evidence_qualified else "pending"
                ),
                "qualification_kind": kind,
                "preparation": (
                    "evidence_qualified" if evidence_qualified else "recipe_prepared"
                ),
                "rationale": rationale,
                "recipe": _recipe_details(kind, feature_id),
            })
        elif section in {
            "Resolved protocol assertion/checker features",
            "Resolved lifecycle assertion/checker features",
        } and len(cells) >= 3:
            domain = "protocol" if "protocol" in section.lower() else "lifecycle"
            feature_id = _feature(cells[0])
            strict = cells[-1]
            names = sorted(named_targets.get(feature_id, []))
            if "✓" in strict:
                kind, readiness, rationale = "existing_evidence", "qualified", strict
            elif names:
                kind, readiness, rationale = "rtl_mutant", "named_registry", "Exact-anchor named mutant is ready for batch execution."
            else:
                kind, readiness, rationale = _assertion_recipe(domain, feature_id)
            cases.append({
                "target_type": "assertion_checker",
                "domain": domain,
                "feature_id": feature_id,
                "strict_status": "qualified" if "✓" in strict else "pending",
                "qualification_kind": kind,
                "preparation": readiness,
                "named_mutants": names,
                "rationale": rationale,
                "recipe": _recipe_details(kind, feature_id),
            })

    registry = validate_registry(sorted(MUTANTS))
    counts: dict[str, int] = {}
    for case in cases:
        key = f"{case['target_type']}:{case['strict_status']}:{case['preparation']}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "schema_version": 1,
        "benchmark": "int8_gemm_hls_golden",
        "source_matrix": str(matrix_path.resolve().relative_to(REPOSITORY_ROOT)),
        "policy": {
            "rtl_mutant": "mutated RTL must fail for the exact named diagnostic",
            "coverage_obligation": "coverage needs observed positive evidence; a broken RTL is not automatically meaningful",
            "positive_pair": "the identical generated TB must pass every required bin, assertion, and ledger check on original RTL",
        },
        "summary": {
            "targets": len(cases),
            "named_rtl_mutants": len(MUTANTS),
            "registry_ready": sum(item["status"] == "READY" for item in registry),
            "case_counts": counts,
        },
        "named_mutant_registry": registry,
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=HERE / "prepared_qualification_catalog.json",
    )
    args = parser.parse_args()
    catalog = build_catalog()
    args.output.write_text(json.dumps(catalog, indent=2))
    print(json.dumps(catalog["summary"], indent=2))
