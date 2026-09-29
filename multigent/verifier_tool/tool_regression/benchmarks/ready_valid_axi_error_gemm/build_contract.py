"""Hand-authored frozen contract (no Architect/Verifier API calls) for
ready_valid_axi_error_gemm: the sibling of ready_valid_tiny_gemm variant A
(same M=1/K=4/N=1 bias+ReLU arithmetic, same ready_valid cmd/b/bias/y
channels) with exactly one difference -- A_matrix is read over a minimal
AXI4-Lite manager port (a_ar/a_r) instead of a plain ready_valid channel.

This is the only combination in this pool where an input binding's
memory_mapping resolves a `response_channel` (confirmed empirically against
the existing u55c_inspired_int8_gemm_4x4x4 fixture, whose A_matrix/B_matrix
bindings already auto-populate memory_mapping.response_channel="m_axi_r"
purely from being axi4_lite-profile reads -- no explicit "response_channel="
semantic tag exists or is needed), which is the sole precondition
lfeat:operation_features.response_error_follows_nonokay needs to become
applicable at all (pool/feature_plans/lifecycle.py line 127). Reusing the
proven bias+ReLU arithmetic core keeps this fixture's only real novelty
narrowly scoped to the AXI4-Lite read path and the error-propagation RTL.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent


def sig(name, role, direction, width, channel=None, semantic_class=None, semantic="", reset_value=None):
    entry = {
        "name": name, "role": role, "semantic_class": semantic_class,
        "channel": channel, "direction": direction, "width": width,
        "signed": False,
    }
    if semantic:
        entry["semantic"] = semantic
    # Only declare (and thus have outputs_match_declared_reset_values check)
    # a reset value where the design actually promises one -- matching
    # ready_valid_tiny_gemm variant A's own interface_contract_a.yaml, which
    # leaves this unset for most signals rather than defaulting to "0".
    if reset_value is not None:
        entry["reset_value"] = reset_value
    return entry


def build() -> tuple[dict, dict]:
    channels = [
        {"name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
         "data_objects": [], "ordering": "one command", "framing": "one beat"},
        {"name": "a_ar", "direction": "output", "protocol_profile": "axi4_lite",
         "purpose": "a_axi read_address", "data_objects": [],
         "metadata": ["protocol_group=a_axi", "protocol_channel=read_address"],
         "framing": "single_beat_per_transfer", "ordering": "in_order", "backpressure": True},
        {"name": "a_r", "direction": "input", "protocol_profile": "axi4_lite",
         "purpose": "a_axi read_data", "data_objects": ["A_matrix"],
         "metadata": ["protocol_group=a_axi", "protocol_channel=read_data"],
         "framing": "single_beat_per_transfer", "ordering": "in_order", "backpressure": True},
        {"name": "b", "direction": "input", "protocol_profile": "ready_valid",
         "data_objects": ["B_matrix"], "ordering": "declared dimension order", "framing": "exact tensor"},
        {"name": "bias", "direction": "input", "protocol_profile": "ready_valid",
         "data_objects": ["bias_vector"], "ordering": "declared dimension order", "framing": "exact tensor"},
        {"name": "y", "direction": "output", "protocol_profile": "ready_valid",
         "data_objects": ["Y_matrix"], "ordering": "declared dimension order", "framing": "exact tensor"},
    ]
    signals = [
        sig("clk", "clock", "input", 1, None, None, "Free-running clock."),
        sig("rst_n", "reset", "input", 1, None, None, "Synchronous active-low reset."),
        sig("cmd_valid", "valid", "input", 1, "cmd"),
        # No declared reset_value, matching ready_valid_tiny_gemm variant
        # A's own interface_contract_a.yaml: cmd_ready is primed high during
        # reset (rtl_a/tiny_gemm_rv_a_top.v) so a command can be accepted on
        # the very first post-reset accepting edge, but that choice is not
        # asserted as a required, checked reset value here either.
        sig("cmd_ready", "ready", "output", 1, "cmd"),
        sig("cmd_op", "payload", "input", 1, "cmd", "command", "legal only 1'd1"),
        sig("a_araddr", "payload", "output", 32, "a_ar", "address", "protocol_field=addr"),
        sig("a_arvalid", "valid", "output", 1, "a_ar"),
        sig("a_arready", "ready", "input", 1, "a_ar"),
        sig("a_rdata", "payload", "input", 32, "a_r", "data", "protocol_field=data"),
        sig("a_rresp", "metadata", "input", 2, "a_r", "response_code", "protocol_field=resp"),
        sig("a_rvalid", "valid", "input", 1, "a_r"),
        sig("a_rready", "ready", "output", 1, "a_r"),
        sig("a_base", "metadata", "input", 32, "cmd", "address",
            "data_object=A_matrix address_role=base byte_order=little "
            "address_sequence=contiguous word_stride_bytes=4"),
        sig("b_valid", "valid", "input", 1, "b"),
        sig("b_ready", "ready", "output", 1, "b"),
        sig("b_data", "payload", "input", 8, "b", "data"),
        sig("bias_valid", "valid", "input", 1, "bias"),
        sig("bias_ready", "ready", "output", 1, "bias"),
        sig("bias_data", "payload", "input", 16, "bias", "data"),
        sig("y_valid", "valid", "output", 1, "y"),
        sig("y_ready", "ready", "input", 1, "y"),
        sig("y_data", "payload", "output", 16, "y", "data"),
        sig("busy", "busy", "output", 1, None),
        sig("done", "completion", "output", 1, None),
        sig("err", "error", "output", 1, None),
    ]
    interface_contract = {
        "clock": "clk",
        "reset": "rst_n",
        "channels": channels,
        "signals": signals,
        "global_handshake_rules": (
            "Every VALID/READY pair follows standard ready/valid stability: once "
            "asserted, VALID and its payload hold stable until the paired READY "
            "active edge. All producer VALIDs are held low throughout active reset."
        ),
    }

    architecture_contract = {
        "design": {
            "name": "ready_valid_axi_error_gemm",
            "description": (
                "Sibling of ready_valid_tiny_gemm variant A (identical M=1/K=4/N=1 "
                "bias-add-then-ReLU arithmetic) with A_matrix read over a minimal "
                "AXI4-Lite manager port instead of a plain ready_valid channel -- "
                "the only combination in this pool whose memory_mapping resolves a "
                "response_channel, built specifically to qualify "
                "response_error_follows_nonokay."
            ),
        },
        "operations": [{
            "name": "gemm", "kind": "arithmetic",
            "coverage_family": "matrix_multiply", "coverage_family_source": "catalog",
            "features": ["dimensions", "operand_values", "accumulation", "post_processing"],
            "feature_extensions": ["bias", "activation"],
            "semantics": "Y = relu(sum_k A[k]*B[k] + bias), exact s16 product, wrapping s16 accumulator.",
            "inputs": ["A_matrix", "B_matrix", "bias_vector"],
            "outputs": ["Y_matrix"],
            "arithmetic": {
                "classifier_profile": "integer_matrix_multiply",
                "product_data_type": "s16",
                "accumulator_data_type": "s16",
                "accumulator_initialization": 0,
                "reduction_dimensions": ["K"],
                "reduction_order": "increasing_declared_reduction_coordinate",
                "reduction_conversion": "wrap_twos_complement_after_each_add",
                "post_operations": {
                    "biased": {"kind": "bias_add", "depends_on": ["accumulator"],
                               "data_object": "bias_vector", "broadcast_dimensions": ["N"]},
                    "activated": {"kind": "relu", "depends_on": ["biased"]},
                },
                "post_output": "activated",
                "bias_conversion": "wrap_twos_complement_after_add",
                "result_data_type": "s16",
                "result_conversion": "wrap_twos_complement",
            },
            "lifecycle_policy": {
                "job_acceptance": "valid_ready_handshake",
                "job_overlap": "single_inflight",
                "busy_behavior": "tracks_active_job",
                "completion_style": "pulse",
                "completion_timing": "next_cycle_after_retirement",
                "illegal_command_behavior": "error_without_start",
                "error_style": "pulse",
                "error_timing": "next_cycle_after_error_event",
                "reset_behavior": "abort_inflight",
            },
        }],
        "data_types": [
            {"name": "s8", "role": "signed 8-bit GEMM operand", "width_bits": 8, "signed": True,
             "representation": "twos_complement", "conversion_semantics": "n/a",
             "overflow_semantics": "n/a", "rounding_semantics": "n/a"},
            {"name": "s16", "role": "signed 16-bit product/accumulator/bias/result", "width_bits": 16,
             "signed": True, "representation": "twos_complement", "conversion_semantics": "n/a",
             "overflow_semantics": "wrap_twos_complement", "rounding_semantics": "n/a"},
        ],
        "data_objects": [
            {"name": "A_matrix", "role": "left_operand_matrix", "data_type": "s8",
             "dimensions": ["M", "K"], "producer": "external", "consumers": ["gemm"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["M", "K"],
                                "description": "One element per transfer, K varies fastest."}},
            {"name": "B_matrix", "role": "right_operand_matrix", "data_type": "s8",
             "dimensions": ["K", "N"], "producer": "external", "consumers": ["gemm"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["K", "N"],
                                "description": "One element per transfer, N varies fastest."}},
            {"name": "bias_vector", "role": "per_output_column_bias", "data_type": "s16",
             "dimensions": ["N"], "producer": "external", "consumers": ["gemm"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["N"],
                                "description": "One element per transfer."}},
            {"name": "Y_matrix", "role": "result_matrix", "data_type": "s16",
             "dimensions": ["M", "N"], "producer": "gemm", "consumers": ["external"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["M", "N"],
                                "description": "One element per transfer."}},
        ],
        "dimensions": [
            {"name": "M", "semantic": "GEMM row count", "minimum": 1, "maximum": 1,
             "runtime_configurable": False, "bound_parameter": ""},
            {"name": "K", "semantic": "GEMM reduction depth", "minimum": 4, "maximum": 4,
             "runtime_configurable": False, "bound_parameter": ""},
            {"name": "N", "semantic": "GEMM column count", "minimum": 1, "maximum": 1,
             "runtime_configurable": False, "bound_parameter": ""},
        ],
        "parameters": [],
        "compute": {"organization": "sequential streaming load/compute/store FSM"},
        "storage": [],
        "pipeline": {"stages": "load_a_over_axi_lite -> load_b -> load_bias -> output"},
        "control": {"style": "single ready/valid command channel, valid_ready_handshake"},
        "reset": {"synchronous": True, "active_low": True, "behavior": "aborts any in-flight job"},
        "latency_model": {"exact": False, "note": "No exact cycle count promised."},
        "architectural_invariants": ["Exactly one GEMM job may be in flight at a time."],
        "open_assumptions": [],
    }
    return architecture_contract, interface_contract


def main() -> None:
    architecture_contract, interface_contract = build()
    (OUT / "architecture_contract.yaml").write_text(yaml.safe_dump(architecture_contract, sort_keys=False))
    (OUT / "interface_contract.yaml").write_text(yaml.safe_dump(interface_contract, sort_keys=False))


if __name__ == "__main__":
    main()
