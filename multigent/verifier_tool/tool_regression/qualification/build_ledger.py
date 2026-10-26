"""Generate/refresh `ledger.json`: the machine-readable qualification ledger.

Enumerates the exact 301 runtime verification targets (31 standard protocol rules + 1
explicit generic-channel reset rule + 1 protocol driver invariant + 77 protocol
feature/bin rows + 32 lifecycle feature/bin rows
+ 139 operation bins + 20 external operation invariants) and 91
metadata/configuration entries (71 verification tags + 6 selectable protocol profiles + 14
lifecycle policy choices) named in the qualification task, transcribed 1:1 from
the pool YAML sources and the existing ledger. Running this script never simulates anything. It preserves
existing evidence except for the explicit, code-reviewed catalog migrations below, adds
missing rows, and refuses if an unrecognized row or expected-count drift would silently
discard qualification evidence.

Usage:
    .venv/bin/python -m multigent.verifier_tool.tool_regression.qualification.build_ledger
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
LEDGER_PATH = HERE / "ledger.json"

STATUSES = {
    "NOT_STARTED",
    "STRICT_PASS",
    "POSITIVE_ONLY",
    "BLOCKED",
    "INAPPLICABLE",
}


def _row(row_id: str, category: str, domain: str, **fields: Any) -> dict[str, Any]:
    base = {
        "id": row_id,
        "category": category,
        "domain": domain,
        "status": "NOT_STARTED",
        "contract": None,
        "generated_tb_hash": None,
        "resolved_feature_plan_hash": None,
        "compliant_rtl": None,
        "mutant_or_negative_contract": None,
        "expected_diagnostic": None,
        "actual_diagnostic": None,
        "detection_mechanism": None,
        "required_coverage": None,
        "actual_coverage": None,
        "deterministic_seed": None,
        "evidence_paths": [],
        "notes": "",
    }
    base.update(fields)
    return base


# ---------------------------------------------------------------------------
# 91 metadata/configuration entries
# ---------------------------------------------------------------------------

TAGS = [
    ("4k_boundary", ["protocol"]), ("ack_phase", ["protocol"]),
    ("address_boundary", ["protocol", "operation"]), ("address_range", ["protocol", "operation"]),
    ("alignment", ["protocol", "operation"]), ("arbitration", ["protocol"]),
    ("back_to_back", ["protocol", "lifecycle"]), ("backpressure", ["protocol"]),
    ("burst_length", ["protocol"]), ("burst_type", ["protocol"]),
    ("busy", ["lifecycle"]), ("byte_enable", ["protocol"]),
    ("cancel", ["lifecycle"]), ("clocking", ["protocol", "lifecycle"]),
    ("coherence_state", ["protocol"]), ("completion", ["lifecycle"]),
    ("configuration", ["operation", "lifecycle"]), ("contract_defined_protocol", ["protocol"]),
    ("control", ["protocol", "lifecycle"]), ("correlation", ["protocol"]),
    ("credit_boundary", ["protocol"]), ("credit_empty", ["protocol"]),
    ("credit_full", ["protocol"]), ("debug_visibility", ["protocol", "lifecycle"]),
    ("denied_access", ["protocol"]), ("destination_partition", ["protocol"]),
    ("empty_frame", ["protocol"]), ("empty_symbols", ["protocol"]),
    ("epoch_partition", ["protocol", "lifecycle"]), ("error", ["protocol", "lifecycle"]),
    ("error_response", ["protocol"]), ("extrema", ["operation", "protocol"]),
    ("flow_control", ["protocol"]), ("flush", ["lifecycle"]),
    ("framing", ["protocol"]), ("handshake", ["protocol"]),
    ("identifier_partition", ["protocol"]), ("illegal_command", ["lifecycle"]),
    ("illegal_opcode", ["protocol", "lifecycle"]), ("illegal_size", ["protocol"]),
    ("illegal_value", ["protocol", "lifecycle", "operation"]), ("interrupt", ["lifecycle"]),
    ("legal_boundary", ["protocol", "operation"]), ("legal_command", ["lifecycle"]),
    ("lifecycle", ["lifecycle"]), ("mask_patterns", ["protocol", "operation"]),
    ("mathematical_correctness", ["operation"]), ("maximum_length", ["protocol", "operation"]),
    ("metadata_values", ["protocol"]), ("minimum_length", ["protocol", "operation"]),
    ("opcode_partition", ["protocol", "lifecycle"]), ("operation_feature", ["operation"]),
    ("ordering", ["protocol", "lifecycle", "operation"]), ("outstanding_ids", ["protocol"]),
    ("partial_transfer", ["protocol"]), ("payload_values", ["protocol"]),
    ("performance_event", ["protocol", "lifecycle"]), ("priority_partition", ["protocol"]),
    ("protection_partition", ["protocol"]), ("recovery", ["lifecycle", "protocol"]),
    ("request_acknowledge", ["protocol"]), ("reset", ["lifecycle", "protocol"]),
    ("response_partition", ["protocol"]), ("serialization", ["operation", "protocol"]),
    ("setup_access_phase", ["protocol"]), ("size_partition", ["protocol"]),
    ("source_id", ["protocol"]), ("stall_stability", ["protocol"]),
    ("user_metadata", ["protocol"]), ("value_partition", ["protocol", "operation"]),
    ("wait_state", ["protocol"]),
]
assert len(TAGS) == 71, len(TAGS)

PROFILES = ["custom", "ready_valid", "axi4", "axi4_lite", "custom_mmio", "axi4_stream"]
assert len(PROFILES) == 6, len(PROFILES)

POLICY_CHOICES = [
    ("job_acceptance", "valid_ready_handshake"), ("job_acceptance", "control_plane_sequence"),
    ("job_overlap", "single_inflight"),
    ("busy_behavior", "tracks_active_job"),
    ("completion_style", "pulse"), ("completion_style", "control_plane_sequence"),
    ("completion_timing", "next_cycle_after_retirement"), ("completion_timing", "observed_via_poll"),
    ("illegal_command_behavior", "error_without_start"),
    ("error_style", "pulse"), ("error_style", "sticky_until_reset"),
    ("error_timing", "next_cycle_after_error_event"),
    ("reset_behavior", "abort_inflight"),
    ("channel_reset_behavior", "valid_deasserted"),
]
assert len(POLICY_CHOICES) == 14, len(POLICY_CHOICES)

# ---------------------------------------------------------------------------
# Runtime verification targets
# ---------------------------------------------------------------------------

STANDARD_RULES = {
    "axi4": [
        "standard_signal_widths", "valid_low_during_reset",
        "legal_burst_encoding", "legal_burst_length", "transfer_size_within_data_bus",
        "wrap_length_and_alignment", "no_4k_boundary_crossing", "write_last_matches_length",
        "read_last_matches_length", "write_strobe_within_active_lanes", "response_after_request",
        "response_id_matches_request", "write_address_and_data_are_independent",
        "exclusive_access_restrictions", "exclusive_response_consistency",
    ],
    "axi4_lite": [
        "standard_signal_widths", "valid_low_during_reset",
        "write_response_after_address_and_data", "read_response_after_address",
        "write_address_and_data_are_independent", "legal_lite_response_encoding",
        "data_width_is_32_or_64", "strobe_width_matches_data_bytes",
        "optional_id_return_and_in_order_completion",
    ],
    "axi4_stream": [
        "standard_signal_widths", "valid_low_during_reset",
        "keep_and_strobe_width_match_data_bytes", "strobe_is_subset_of_keep",
        "packet_state_is_tracked_per_stream_key", "continuous_packet_constraints_when_declared",
    ],
    "custom_mmio": ["valid_low_during_reset"],
}
assert sum(len(v) for v in STANDARD_RULES.values()) == 31

EXPLICIT_PROTOCOL_RULES = [
    (
        "explicit generic-channel reset policy",
        "valid_deasserted",
    ),
]

PROTOCOL_DRIVER_INVARIANTS = {
    "axi4": ["response_order_preserved_per_id"],
}
assert sum(len(v) for v in PROTOCOL_DRIVER_INVARIANTS.values()) == 1

PROTOCOL_FEATURE_BINS = [
    ("features.handshake_states", ["idle", "receiver_ready", "backpressured", "transfer"]),
    ("features.handshake_arrival_order", ["simultaneous", "valid_before_ready", "ready_before_valid"]),
    ("features.stall_stability", ["one_cycle_stall", "short_stall", "long_stall"]),
    ("features.address_alignment", ["minimum", "aligned_interior", "maximum", "boundary_neighbor"]),
    ("features.axi4_4k_boundary", ["ends_before_boundary", "ends_at_boundary", "would_cross_boundary (diagnostic)"]),
    ("features.axi4_burst_type", ["fixed", "incrementing", "wrapping"]),
    ("features.axi4_burst_length", ["single", "two_to_sixteen", "seventeen_to_256"]),
    ("features.axi4_transfer_size", ["one_byte", "narrow", "full_width"]),
    ("features.axi4_alignment", ["aligned", "unaligned"]),
    ("features.axi4_write_strobe", ["all_zero", "sparse", "full"]),
    ("features.axi4_write_channel_order", ["address_first", "data_first", "same_cycle"]),
    ("features.axi4_response_code", ["okay", "exokay (diagnostic)", "slverr (diagnostic)", "decerr (diagnostic)"]),
    ("features.axi4_outstanding_depth", ["one", "multiple_same_id", "multiple_ids (diagnostic)"]),
    ("features.axi4_sideband_partition", ["zero", "nonzero"]),
    ("features.axi_lite_write_channel_order", ["address_first", "data_first", "same_cycle"]),
    ("features.axi_lite_write_strobe", ["all_zero", "sparse", "full"]),
    ("features.axi_lite_response_code", ["okay", "slverr (diagnostic)", "decerr (diagnostic)"]),
    ("features.axi_lite_read_write_concurrency", ["write_only_cycle", "read_only_cycle", "simultaneous"]),
    ("features.axi_lite_address_partition", ["zero", "aligned", "unaligned", "page_edge"]),
    ("features.axi_lite_protection_partition", ["zero", "nonzero"]),
    ("features.axi_lite_outstanding_depth", ["one", "multiple"]),
    ("features.axis_packet_length", ["single_beat", "multi_beat"]),
    ("features.axis_keep_pattern", ["full", "partial", "empty_last (diagnostic)"]),
    ("features.axis_stall_position", ["first_beat", "middle_beat", "last_beat"]),
    ("features.axis_back_to_back_packets", ["no_gap", "with_gap"]),
    ("features.axis_sideband_partition", ["zero", "nonzero"]),
    ("derived_features.valid_low_during_reset", ["assertion-only"]),
    ("derived_features.standard_protocol_rule", ["assertion-only"]),
]
assert sum(len(b) for _, b in PROTOCOL_FEATURE_BINS) == 77

LIFECYCLE_ROWS = [
    ("features", "reset_behavior", ["asserted", "deasserted", "release"]),
    ("features", "busy_behavior", ["idle", "active", "retired"]),
    ("features", "completion_behavior", ["observed", "back_to_back"]),
    ("features", "error_behavior", ["inactive", "asserted", "recovered"]),
    ("features", "command_legality", ["legal", "illegal"]),
    ("operation_features", "accepted_command_starts_job", ["assertion-only or dynamic obligation"]),
    ("operation_features", "single_inflight_job_enforced", ["assertion-only or dynamic obligation"]),
    ("operation_features", "illegal_command_errors_without_start", ["assertion-only or dynamic obligation"]),
    ("operation_features", "response_error_follows_nonokay", ["assertion-only or dynamic obligation"]),
    ("operation_features", "no_output_without_active_job", ["assertion-only or dynamic obligation"]),
    ("operation_features", "busy_tracks_active_job", ["assertion-only or dynamic obligation"]),
    ("operation_features", "completion_matches_final_output", ["assertion-only or dynamic obligation"]),
    ("operation_features", "reset_aborts_pending_job", ["assertion-only or dynamic obligation"]),
    ("operation_features", "status_pulses_are_one_cycle", ["assertion-only or dynamic obligation"]),
    ("operation_coverage", "job_lifecycle", ["accepted", "active", "retired", "aborted"]),
    ("operation_coverage", "reset_abort_phase", ["idle", "compute", "output"]),
    ("operation_coverage", "post_reset_purity", ["no_ghost_completion", "no_ghost_output", "clean_recovery_job"]),
]
assert sum(len(b) for _, _, b in LIFECYCLE_ROWS) == 32

OPERATION_BINS = [
    ("dimensions", ["fixed_shape"]),
    ("operand_values", ["zero", "positive", "negative", "minimum", "maximum"]),
    ("accumulation", ["ordinary", "positive_boundary", "negative_boundary", "positive_overflow", "negative_overflow"]),
    ("post_processing.bias", ["zero_bias", "positive_bias", "negative_bias", "minimum_bias", "maximum_bias"]),
    ("post_processing.activation", ["negative_region", "zero_region", "positive_region"]),
    ("post_processing.quantization", ["exact", "rounded", "nonzero_zero_point", "negative_saturation", "positive_saturation"]),
]
assert sum(len(b) for _, b in OPERATION_BINS) == 24

SPARSE_ATTENTION_BINS = [
    ("dimensions", ["fixed_shape"]),
    ("operand_values", ["zero", "positive", "negative", "minimum", "maximum"]),
    ("sparsity_patterns", ["empty_row", "singleton_row", "partial_row", "dense_row"]),
    ("attention_scores", ["zero_score", "positive_score", "negative_score"]),
    ("stage_handoffs", ["qk_to_scale_forwarded", "active_mask_preserved", "inactive_mask_zeroed", "normalization_bypass_forwarded", "value_reduction_consumed"]),
    ("output_values", ["zero_output", "positive_output", "negative_output"]),
]
assert sum(len(b) for _, b in SPARSE_ATTENTION_BINS) == 21

QK_SCORE_BINS = [
    ("dimensions", ["fixed_shape"]),
    ("operand_values", ["zero", "positive", "negative", "minimum", "maximum"]),
    ("accumulation", ["ordinary", "positive_boundary", "negative_boundary", "positive_overflow", "negative_overflow", "cancellation", "mixed_sign_terms", "last_term_only"]),
    ("attention_scores", ["zero_score", "positive_score", "negative_score"]),
]
assert sum(len(b) for _, b in QK_SCORE_BINS) == 17

ATTENTION_SCALE_BINS = [
    ("dimensions", ["fixed_shape"]),
    ("score_values", ["zero", "positive", "negative", "minimum", "maximum"]),
    ("rounding", ["exact", "positive_fraction_discarded", "negative_fraction_discarded"]),
    ("scaled_values", ["zero_scaled", "positive_scaled", "negative_scaled"]),
    ("attenuation", ["zero_preserved", "magnitude_reduced"]),
]
assert sum(len(b) for _, b in ATTENTION_SCALE_BINS) == 14

ATTENTION_MASK_BINS = [
    ("dimensions", ["fixed_shape"]),
    ("score_values", ["zero", "positive", "negative", "minimum", "maximum"]),
    ("mask_values", ["drop", "keep"]),
    ("sparsity_patterns", ["empty_row", "singleton_row", "partial_row", "dense_row"]),
    ("masked_values", ["zero_masked", "positive_masked", "negative_masked"]),
    ("mask_effects", ["active_score_preserved", "inactive_nonzero_zeroed", "active_zero_preserved", "inactive_positive_zeroed", "inactive_negative_zeroed"]),
]
assert sum(len(b) for _, b in ATTENTION_MASK_BINS) == 20

OPERATION_FAMILY_BINS = {
    "block_matmul": [
        ("dimensions", ["fixed_shape"]),
        ("block_selection", ["empty", "singleton", "multiple", "nonadjacent", "reordered", "duplicate"]),
        ("block_mapping", ["origin", "nonzero_row", "nonzero_column", "distinct_tile_results"]),
        ("block_tails", ["full_tile", "row_tail", "column_tail", "reduction_tail"]),
        ("block_reduction", ["single_chunk", "multiple_chunks", "zero_result", "positive_result", "negative_result", "nonzero_reduction_tail"]),
    ],
    "softmax": [
        ("dimensions", ["fixed_shape"]),
        ("row_patterns", ["uniform", "tied_maximum", "unique_maximum", "all_negative", "mixed_sign", "distinct_rows"]),
        ("mask_patterns", ["unmasked", "singleton", "partial", "fully_masked", "masked_maximum", "masked_zero"]),
        ("exp_domain", ["zero_delta", "interior_delta", "last_lut_entry", "clipped_delta"]),
        ("normalization", ["zero_probability", "positive_probability", "rounded_division", "exact_division", "tiny_positive_weight_zero"]),
    ],
    "matrix_multiply": OPERATION_BINS,
    "sparse_attention": SPARSE_ATTENTION_BINS,
    "attention_qk": QK_SCORE_BINS,
    "attention_scale": ATTENTION_SCALE_BINS,
    "attention_mask": ATTENTION_MASK_BINS,
}

# New semantic crosses do not inherit qualification of their older parent
# concept. Historical reports are not evidence that these targets were sampled.
BLACK_BOX_ADDITION_IDS = {
    f"ofeat:{family}.{concept}.{name}"
    for family, concept, names in (
        ("attention_qk", "accumulation", ("cancellation", "mixed_sign_terms", "last_term_only")),
        ("attention_mask", "mask_effects", ("active_zero_preserved", "inactive_positive_zeroed", "inactive_negative_zeroed")),
        ("block_matmul", "block_mapping", ("distinct_tile_results",)),
        ("block_matmul", "block_reduction", ("nonzero_reduction_tail",)),
        ("softmax", "row_patterns", ("distinct_rows",)),
        ("softmax", "mask_patterns", ("masked_maximum", "masked_zero")),
        ("softmax", "normalization", ("tiny_positive_weight_zero",)),
    ) for name in names
}

EXTERNAL_OPERATION_INVARIANTS = {
    "attention_qk": ["qk.zero_operand", "qk.equal_queries", "qk.equal_keys"],
    "attention_scale": ["scale.zero_preserved", "scale.equal_inputs", "scale.monotonic"],
    "attention_mask": ["mask.excluded_zero", "mask.kept_value"],
    "block_matmul": ["block.padding_zero", "block.duplicate_tile_equal"],
    "softmax": ["softmax.output_range", "softmax.excluded_zero", "softmax.empty_row_zero", "softmax.equal_scores", "softmax.score_order", "softmax.floor_mass_bound", "softmax.equal_rows"],
    "sparse_attention": ["sparse.empty_row_zero", "sparse.zero_value_column", "sparse.equal_value_columns"],
}


def build_all_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, domains in TAGS:
        rows.append(_row(f"tag:{name}", "tag", "/".join(domains), name=name))
    for name in PROFILES:
        rows.append(_row(f"profile:{name}", "protocol_profile", "protocol", name=name))
    for field, choice in POLICY_CHOICES:
        rows.append(_row(f"policy:{field}.{choice}", "lifecycle_policy_choice", "lifecycle",
                          field=field, choice=choice))
    for profile, rules in STANDARD_RULES.items():
        for rule in rules:
            rows.append(_row(f"rule:{profile}.{rule}", "standard_protocol_rule", "protocol",
                              profile=profile, rule=rule))
    for profile, rule in EXPLICIT_PROTOCOL_RULES:
        rows.append(_row(
            "rule:explicit_generic_channel_reset.valid_deasserted",
            "standard_protocol_rule",
            "protocol",
            profile=profile,
            rule=rule,
        ))
    for profile, invariants in PROTOCOL_DRIVER_INVARIANTS.items():
        for invariant in invariants:
            rows.append(_row(
                f"driver_invariant:{profile}.{invariant}",
                "protocol_driver_invariant",
                "protocol",
                profile=profile,
                invariant=invariant,
            ))
    for feature, bins in PROTOCOL_FEATURE_BINS:
        for bin_name in bins:
            rows.append(_row(f"pfeat:{feature}.{bin_name}", "protocol_feature_bin", "protocol",
                              feature=feature, bin=bin_name))
    for section, feature, bins in LIFECYCLE_ROWS:
        for bin_name in bins:
            rows.append(_row(f"lfeat:{section}.{feature}.{bin_name}", "lifecycle_feature_bin", "lifecycle",
                              section=section, feature=feature, bin=bin_name))
    for family, concepts in OPERATION_FAMILY_BINS.items():
        for concept, bins in concepts:
            for bin_name in bins:
                rows.append(_row(
                    f"ofeat:{family}.{concept}.{bin_name}",
                    "operation_bin",
                    "operation",
                    family=family,
                    concept=concept,
                    bin=bin_name,
                ))
    for family, names in EXTERNAL_OPERATION_INVARIANTS.items():
        for name in names:
            rows.append(_row(f"oinvariant:{name}", "operation_invariant", "operation", family=family, invariant=name))
    return rows


def main() -> None:
    rows = build_all_rows()
    runtime_categories = {
        "standard_protocol_rule",
        "protocol_driver_invariant",
        "protocol_feature_bin",
        "lifecycle_feature_bin",
        "operation_bin",
        "operation_invariant",
    }
    metadata_categories = {"tag", "protocol_profile", "lifecycle_policy_choice"}
    runtime_count = sum(1 for r in rows if r["category"] in runtime_categories)
    metadata_count = sum(1 for r in rows if r["category"] in metadata_categories)
    if runtime_count != 301:
        raise AssertionError(f"expected 301 runtime targets, got {runtime_count}")
    if metadata_count != 91:
        raise AssertionError(f"expected 91 metadata entries, got {metadata_count}")
    if len(rows) != len({r["id"] for r in rows}):
        raise AssertionError("duplicate row id generated")

    for row in rows:
        if row.get("family") != "attention_scale" or row["category"] != "operation_bin":
            continue
        row.update(
            {
                "status": "STRICT_PASS",
                "contract": "fixed_point_attention_scale D=64 F=8 multiplier=32 signed s16",
                "generated_tb_hash": "9e30c78ac5961f664aff525d35b588a80b881c00a647473043f4d79cba466b3b",
                "resolved_feature_plan_hash": "60bd76726ca97808b60ec051c29e370a19f717c99e7fc41ca815eac983b7f2eb",
                "compliant_rtl": "attention_scale_fixed.sv sha256=b33c17e2b3f2fbd8e8536ac29252212cb70169d362b3f7026d0ac68a6562ee35",
                "mutant_or_negative_contract": "73 compile-valid coefficient/shift/signedness/data/protocol/reset RTL mutants",
                "expected_diagnostic": "nonzero simulator exit from oracle, accounting, stall-stability, or reset-abort checker",
                "actual_diagnostic": "73/73 compile-valid mutants rejected; zero survivors and zero invalid mutations",
                "detection_mechanism": "canonical_pool_witness+signed16_exhaustive_oracle+ready_valid_temporal_checker",
                "required_coverage": "all 14 attention_scale bins, minimum one checked hit each",
                "actual_coverage": "14/14 bins; 65,536/65,536 signed inputs plus 870 pool/random elements",
                "deterministic_seed": "0x5CA1E",
                "evidence_paths": [
                    "multigent/verifier_tool/tool_regression/benchmarks/attention_scale_fixed/EXHAUSTIVE_RESULT.md",
                    "multigent/verifier_tool/tool_regression/benchmarks/attention_scale_fixed/qualify.py",
                    "multigent/verifier_tool/tool_regression/rtl/test_attention_scale_fixed.py",
                ],
                "notes": "Scale-only stage; excludes mask, softmax, and V. Full JSON evidence is reproducible with the command in EXHAUSTIVE_RESULT.md.",
            }
        )

    for row in rows:
        if row.get("family") != "attention_mask" or row["category"] != "operation_bin" or row["id"] in BLACK_BOX_ADDITION_IDS:
            continue
        row.update(
            {
                "status": "STRICT_PASS",
                "contract": "binary_attention_mask Q=2 S=3 signed s16 score, u1 binary_keep mask",
                "generated_tb_hash": "37e654d8fc8a962544c1b23f8e42b3739d79c75f175e79346146b8e91942f2d3",
                "resolved_feature_plan_hash": "356b52347890b7661d132e97ba66aa6a39fc3e5c90ec228679049d1a7faf0f06",
                "compliant_rtl": "attention_mask_binary.sv sha256=6c6495a09c5e7a6affc885fd3771c6fa385f66d1e8473ce79da8604bbb1f38cc",
                "mutant_or_negative_contract": "59 compile-valid polarity/data/alignment/protocol/reset RTL mutants",
                "expected_diagnostic": "nonzero simulator exit from oracle, independent-input accounting, stall-stability, or reset-abort checker",
                "actual_diagnostic": "59/59 compile-valid mutants rejected; zero survivors and zero invalid mutations",
                "detection_mechanism": "canonical_pool_witness+signed16_x_binary_mask_exhaustive_oracle+independent_ready_valid_temporal_checker",
                "required_coverage": "all 17 attention_mask bins, minimum one checked hit each",
                "actual_coverage": "17/17 bins; 131,072/131,072 signed-score/mask pairs plus 888 pool/random elements",
                "deterministic_seed": "0xA55A",
                "evidence_paths": [
                    "multigent/verifier_tool/tool_regression/benchmarks/attention_mask_binary/EXHAUSTIVE_RESULT.md",
                    "multigent/verifier_tool/tool_regression/benchmarks/attention_mask_binary/qualify.py",
                    "multigent/verifier_tool/tool_regression/rtl/test_attention_mask_binary.py",
                ],
                "notes": "Mask-only stage; mask 1 preserves and 0 emits zero. Excludes softmax and V. Score and mask streams are stalled independently to prove coordinate alignment.",
            }
        )

    existing: dict[str, Any] = {}
    if LEDGER_PATH.is_file():
        existing_doc = json.loads(LEDGER_PATH.read_text())
        existing = {r["id"]: r for r in existing_doc.get("rows", [])}

    # Explicit one-time catalog migrations.  These preserve valid historical
    # evidence while removing rows that no longer describe a current verifier
    # obligation.  Keeping the mapping here makes a ledger refresh reproducible
    # instead of requiring hand-edited JSON.
    legacy_overlap_id = (
        "lfeat:operation_features.legal_command_starts_one_job."
        "assertion-only or dynamic obligation"
    )
    single_inflight_id = (
        "lfeat:operation_features.single_inflight_job_enforced."
        "assertion-only or dynamic obligation"
    )
    if legacy_overlap_id in existing and single_inflight_id not in existing:
        migrated = dict(existing.pop(legacy_overlap_id))
        migrated.update({
            "id": single_inflight_id,
            "feature": "single_inflight_job_enforced",
            "expected_diagnostic": (
                "lifecycle.gemm.single_inflight_job_enforced: a second legal "
                "command was accepted while a job was active"
            ),
            "actual_diagnostic": (
                "test_cmd_ready_stays_high_while_busy_trips_"
                "single_inflight_job_enforced passes with the exact feature ID."
            ),
            "notes": (
                "Migrated from the former over-broad legal_command_starts_one_job "
                "row. The same frozen-contract/generated-TB mutant evidence proves "
                "the narrower and accurate single-inflight claim."
            ),
        })
        existing[single_inflight_id] = migrated

    overlap_policy_id = "policy:job_overlap.single_inflight"
    if overlap_policy_id in existing:
        existing[overlap_policy_id].update({
            "expected_diagnostic": (
                "lifecycle.gemm.single_inflight_job_enforced: a second legal "
                "command was accepted while a job was active"
            ),
            "actual_diagnostic": (
                "test_cmd_ready_stays_high_while_busy_trips_"
                "single_inflight_job_enforced passes with the exact feature ID; "
                "the compliant generated-TB campaign passes the same probe."
            ),
            "actual_coverage": (
                "This metadata choice is enforced by the independently tracked "
                "single_inflight_job_enforced runtime feature."
            ),
            "notes": (
                "The two-beat ready_valid_multi_beat_gemm fixture makes the "
                "automatic campaign's command-stall overlap probe observable."
            ),
        })

    legacy_order_id = "rule:axi4.response_order_preserved_per_id"
    driver_order_id = "driver_invariant:axi4.response_order_preserved_per_id"
    existing.pop(legacy_order_id, None)
    if driver_order_id not in existing:
        existing[driver_order_id] = _row(
            driver_order_id,
            "protocol_driver_invariant",
            "protocol",
            status="STRICT_PASS",
            profile="axi4",
            invariant="response_order_preserved_per_id",
            contract="AXI4 tool-owned subordinate response scheduler",
            compliant_rtl="N/A -- this is a trusted tool-owned driver invariant",
            mutant_or_negative_contract=(
                "A second same-ID completion is released while the first is held; "
                "a different-ID completion remains independently schedulable."
            ),
            expected_diagnostic=(
                "The second same-ID action must not start before the first ends."
            ),
            actual_diagnostic=(
                "test_completion_scheduler_preserves_fifo_within_one_id passes."
            ),
            detection_mechanism="driver_invariant_unit_test",
            evidence_paths=["multigent/verifier_tool/tool_regression/unit/test_protocol_driver_utilities.py"],
            notes=(
                "Same-ID ordering is unobservable from otherwise identical passive "
                "AXI responses. It is therefore enforced and qualified at the "
                "tool-owned responder boundary, while different IDs may reorder."
            ),
        )

    # Removed current-catalog obligations must not remain in the required
    # denominator as historical ghost rows. Generic ready/valid stability is
    # already represented by the reusable stall-stability feature, and reset
    # behavior on a generic ready/valid channel is selected explicitly below.
    existing.pop("rule:axi4.legal_response_encoding", None)
    existing.pop("rule:ready_valid.valid_low_during_reset", None)
    for profile in ("axi4", "axi4_lite", "axi4_stream", "custom_mmio", "ready_valid"):
        existing.pop(f"rule:{profile}.ready_valid_stability", None)

    explicit_reset_id = "rule:explicit_generic_channel_reset.valid_deasserted"
    if explicit_reset_id not in existing:
        existing[explicit_reset_id] = _row(
            explicit_reset_id,
            "standard_protocol_rule",
            "protocol",
            status="STRICT_PASS",
            profile="explicit generic-channel reset policy",
            rule="valid_deasserted",
            contract="ready_valid reset-policy frozen contract",
            compliant_rtl="ready_valid reset-policy corrected RTL fixture",
            mutant_or_negative_contract="VALID remains asserted during reset",
            expected_diagnostic="channel.<name>.valid_low_during_reset",
            actual_diagnostic=(
                "test_ready_valid_reset_channel_policy generated-TB fault/fix pair "
                "passes with the exact named diagnostic"
            ),
            detection_mechanism="named_assertion_checker",
            evidence_paths=["multigent/verifier_tool/tool_regression/rtl/test_ready_valid_reset_channel_policy.py"],
            notes=(
                "This is an explicit generic-channel reset policy, not a hidden "
                "standard ready_valid profile rule. It remains separately visible "
                "in the exhaustive inventory."
            ),
        )
    else:
        existing[explicit_reset_id].update({
            "profile": "explicit generic-channel reset policy",
            "rule": "valid_deasserted",
        })

    reset_policy_id = "policy:channel_reset_behavior.valid_deasserted"
    if reset_policy_id not in existing:
        existing[reset_policy_id] = _row(
            reset_policy_id,
            "lifecycle_policy_choice",
            "lifecycle",
            field="channel_reset_behavior",
            choice="valid_deasserted",
        )
    existing[reset_policy_id].update({
        "status": "STRICT_PASS",
        "contract": "ready_valid reset-policy frozen contract",
        "compliant_rtl": "ready_valid reset-policy corrected RTL fixture",
        "mutant_or_negative_contract": "VALID remains asserted during reset",
        "expected_diagnostic": "channel.<name>.valid_low_during_reset",
        "actual_diagnostic": (
            "test_explicit_policy_catches_fault_and_fixed_rtl_passes produces "
            "the exact named failure for the mutant and PASS for corrected RTL"
        ),
        "detection_mechanism": "named_assertion_checker",
        "deterministic_seed": "seed=31 (run_cocotb_regression)",
        "evidence_paths": [
            "multigent/verifier_tool/tool_regression/rtl/"
            "test_ready_valid_reset_channel_policy.py"
        ],
        "notes": (
            "The metadata choice is qualified by the same explicit channel-policy "
            "fault/fix pair as rule:explicit_generic_channel_reset.valid_deasserted. "
            "A plain ready_valid channel remains unconstrained unless the contract "
            "selects this policy."
        ),
    })

    accepted_id = (
        "lfeat:operation_features.accepted_command_starts_job."
        "assertion-only or dynamic obligation"
    )
    if accepted_id not in existing:
        existing[accepted_id] = _row(
            accepted_id,
            "lifecycle_feature_bin",
            "lifecycle",
            status="STRICT_PASS",
            section="operation_features",
            feature="accepted_command_starts_job",
            bin="assertion-only or dynamic obligation",
            contract=(
                "int8_gemm_hls_golden frozen contract and generated TB; plus the "
                "direct lifecycle checker integration fixture"
            ),
            compliant_rtl="immutable gemm_golden HLS RTL",
            mutant_or_negative_contract="start_ignored HLS RTL mutant",
            expected_diagnostic=(
                "lifecycle.gemm.accepted_command_starts_job: accepted legal command "
                "made no observable progress"
            ),
            actual_diagnostic=(
                "test_start_ignored_fails_with_accepted_command_starts_job passes "
                "with the exact feature diagnostic."
            ),
            detection_mechanism="named_assertion_checker",
            evidence_paths=[
                "multigent/verifier_tool/tool_regression/integration/test_control_plane_sequence_checker_integration.py",
                "multigent/verifier_tool/tool_regression/rtl/test_int8_gemm_hls_mutations.py",
            ],
            notes=(
                "An accepted command arms a bounded progress obligation. Busy, "
                "accepted I/O, retirement activity, final transfer, completion, or "
                "job_complete discharges it; an ignored start now fails by name "
                "instead of ending as a generic timeout."
            ),
        )

    response_error_id = (
        "lfeat:operation_features.response_error_follows_nonokay."
        "assertion-only or dynamic obligation"
    )
    if response_error_id in existing:
        existing[response_error_id].update({
            "status": "STRICT_PASS",
            "contract": (
                "multigent/verifier_tool/tool_regression/benchmarks/ready_valid_axi_error_gemm/"
                "{architecture,interface}_contract.yaml"
            ),
            "compliant_rtl": (
                "multigent/verifier_tool/tool_regression/benchmarks/ready_valid_axi_error_gemm/"
                "rtl/ready_valid_axi_error_gemm_top.v"
            ),
            "mutant_or_negative_contract": (
                "mutants/ready_valid_axi_error_gemm_top__drops_error_signal.v: "
                "aborts the failed AXI4-Lite read but suppresses only the required "
                "error pulse"
            ),
            "expected_diagnostic": (
                "lifecycle.gemm.response_error_follows_nonokay: non-OKAY "
                "response was not followed by error"
            ),
            "actual_diagnostic": (
                "test_dropped_error_signal_trips_response_error_follows_nonokay "
                "passes with the exact feature ID and message"
            ),
            "detection_mechanism": "named_assertion_checker",
            "actual_coverage": (
                "The compliant RTL passes both OKAY and injected SLVERR cases "
                "with zero assertion failures; this row is an assertion claim, not "
                "a coverage-bin claim."
            ),
            "deterministic_seed": "seed=1 (run_cocotb_regression)",
            "evidence_paths": [
                "multigent/verifier_tool/tool_regression/rtl/test_ready_valid_axi_error_gemm.py",
                "multigent/verifier_tool/tool_regression/benchmarks/ready_valid_axi_error_gemm",
            ],
            "notes": (
                "Mixed AXI4-Lite/ready-valid fixture. The exact single-fault "
                "mutant proves the feature's own missing-error diagnostic; a "
                "separate continues-past-error mutant also proves abort semantics "
                "through busy_tracks_active_job."
            ),
        })

    boundary_id = "pfeat:features.axi4_4k_boundary.would_cross_boundary (diagnostic)"
    if boundary_id in existing and existing[boundary_id].get("status") == "BLOCKED":
        existing[boundary_id].update({
            "status": "STRICT_PASS",
            "expected_diagnostic": (
                "The violating snapshot records would_cross_boundary diagnostically "
                "and still fails the no_4k_boundary_crossing assertion."
            ),
            "actual_diagnostic": (
                "test_assertion_failing_axi4_edge_records_only_diagnostic_coverage "
                "passes; the real cross_4k RTL fixture still fails by assertion."
            ),
            "detection_mechanism": "named_assertion_checker+diagnostic_coverage",
            "evidence_paths": [
                "multigent/verifier_tool/tool_regression/integration/test_standard_axi_protocols.py",
                "multigent/verifier_tool/tool_regression/rtl/test_axi4_standard_rules_rtl_feature.py",
            ],
            "notes": (
                "BUG-006 fixed transactionally: on assertion failure the monitor "
                "samples only non-required diagnostic bins, then restores temporal "
                "coverage state before re-raising. Illegal behavior therefore never "
                "earns required verification credit."
            ),
        })

    merged = []
    added = 0
    for row in rows:
        if row["id"] in existing:
            # Scale qualification is fully regenerated from the frozen
            # exhaustive benchmark above; keep its digests/evidence in sync
            # instead of preserving a stale manually-edited copy.
            merged.append(
                row
                if row.get("family") in {"attention_scale", "attention_mask"}
                else existing[row["id"]]
            )
        else:
            merged.append(row)
            added += 1
    removed = [rid for rid in existing if rid not in {r["id"] for r in rows}]
    if removed:
        raise AssertionError(f"rows present in ledger.json but not in the current catalog: {removed}")

    # Positive generated-campaign evidence is intentionally weaker than strict
    # per-bin qualification. Never upgrade it because a few semantic faults were
    # detected, and never overwrite a future STRICT_PASS record with this report.
    structured_root = HERE.parent / "benchmarks" / "block_softmax_external"
    structured_evidence = structured_root / "evidence.json"
    if structured_evidence.is_file():
        evidence = json.loads(structured_evidence.read_text())
        campaigns = evidence["local_generated_campaigns"]
        for row in merged:
            family = row.get("family")
            if row["category"] != "operation_bin" or family not in {"block_matmul", "softmax"} or row["status"] not in {"NOT_STARTED", "POSITIVE_ONLY"}:
                continue
            selected = [value for name, value in campaigns.items()
                        if (name == "masked_softmax") == (family == "softmax")]
            if not selected or any(value["status"] != "PASS" for value in selected):
                raise AssertionError("Structured qualification needs passing real generated campaigns")
            suffix = f".{row['concept']}.{row['bin']}"
            hits = sum(count for value in selected for key, count in value["operation_hits"].items()
                       if key.endswith(suffix))
            if hits <= 0:
                if row["id"] in BLACK_BOX_ADDITION_IDS:
                    continue
                raise AssertionError(f"No observed positive evidence for {row['id']}")
            row.update(
                status="POSITIVE_ONLY",
                contract=f"Explicit fixed {family} contracts in fixtures/structured_operations.py",
                compliant_rtl="Independent local streaming RTL fixtures; pinned external arithmetic cores evaluated separately",
                detection_mechanism="central_golden_equivalence+accepted_transfer_accounting+canonical_classifier",
                required_coverage=f"At least one checked DUT job in {row['concept']}.{row['bin']}",
                actual_coverage=f"{hits} observed checked-job hits across applicable generated campaigns",
                deterministic_seed="generated campaign 19; external canonical suite 0xB10C5",
                evidence_paths=[
                    "multigent/verifier_tool/tool_regression/benchmarks/block_softmax_external/evidence.json",
                    "multigent/verifier_tool/tool_regression/benchmarks/block_softmax_external/RESULT.md",
                    "multigent/verifier_tool/tool_regression/rtl/test_structured_generated_campaign.py",
                    "multigent/verifier_tool/tool_regression/rtl/test_block_softmax_external.py",
                ],
                notes="Positive-only per-bin evidence. Four semantic RTL faults are detected, but exhaustive or individual per-bin strict qualification is not claimed. No internal signals are monitored.",
            )

    audit_path = HERE.parent / "benchmarks" / "attention_source_audit" / "evidence.json"
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text())
        if audit.get("status") != "PASS":
            raise AssertionError("Black-box audit evidence must come from passing RTL campaigns")
        for row in merged:
            if row["id"] in BLACK_BOX_ADDITION_IDS:
                hits = audit["new_bin_hits"].get(row["id"], 0)
            elif row["category"] == "operation_invariant":
                hits = audit["external_invariant_hits"].get(row["invariant"], 0)
            else:
                continue
            if not hits:
                raise AssertionError(f"No black-box RTL evidence for {row['id']}")
            if row["status"] == "STRICT_PASS":
                continue
            row.update(status="POSITIVE_ONLY", contract="Explicit external tensor contracts in the source-audit generated RTL campaigns",
                       actual_coverage=f"{hits} observed checked-job hits in passing external-I/O RTL campaigns",
                       detection_mechanism="external_tensor_invariants+central_golden_equivalence+canonical_classifier",
                       evidence_paths=["multigent/verifier_tool/tool_regression/benchmarks/attention_source_audit/evidence.json",
                                       "multigent/verifier_tool/tool_regression/benchmarks/attention_source_audit/README.md"],
                       notes="No internal monitors. Positive evidence does not establish individual strict fault/fix qualification.")

    doc = {
        "schema_version": 1,
        "runtime_target_count": runtime_count,
        "metadata_entry_count": metadata_count,
        "total_rows": len(merged),
        "rows": merged,
    }
    LEDGER_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {LEDGER_PATH} with {len(merged)} rows ({added} newly added)")


if __name__ == "__main__":
    main()
