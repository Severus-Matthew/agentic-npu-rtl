"""Hand-authored frozen contract for a minimal ready/valid GEMM fixture with
the full bias_add -> relu -> affine_quantize post-processing DAG. No
Architect/Verifier LLM call.

Modeled directly on ../ready_valid_tiny_gemm/build_contract_a.py (same
M=1,K=4,N=1 shape, same 5-channel ready/valid protocol, same
job_acceptance=valid_ready_handshake / completion_style=pulse lifecycle
policy, already independently qualified there), extended with one new
affine_quantize stage so this is the first fixture in the pool to declare
all three optional matrix_multiply post_processing concepts (bias,
activation, quantization) at once -- closing the operation_bin
`accumulation.{positive,negative}_{boundary,overflow}` and
`post_processing.{bias,activation,quantization}.*` cluster, the largest
still-open block of the qualification pool.

quantize stage: scale_multiplier=1, scale_shift=4 (i.e. divide the
non-negative post-relu value by 16, round half to even), zero_point=-200,
result_data_type=s8. zero_point is deliberately large and negative so
negative_saturation is reachable despite the post-relu input always being
>= 0 (see notes.md for the full bin-covering stimulus derivation).
"""
from __future__ import annotations

from pathlib import Path

import yaml

HERE = Path(__file__).parent
M, K, N = 1, 4, 1


def build_architecture_contract() -> dict:
    return {
        "design": {
            "name": "post_processing_tiny_gemm",
            "description": (
                "Minimal hand-authored ready/valid GEMM (M=1,K=4,N=1) with "
                "bias-add, ReLU, and affine requantization to int8, no "
                "memory-mapped transport -- a verifier_tool benchmark "
                "fixture built specifically to qualify the operation_bin "
                "accumulation boundary/overflow bins and the full "
                "post_processing.{bias,activation,quantization} bin set, "
                "none of which any other fixture in this pool declares."
            ),
        },
        "operations": [
            {
                "name": "gemm",
                "kind": "arithmetic",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values", "accumulation", "post_processing"],
                "feature_extensions": ["bias", "activation", "quantization"],
                "semantics": (
                    "Y = relu(quantize(sum_k A[k]*B[k] + bias)), exact s16 "
                    "product, wrapping s16 accumulator, scale_multiplier=1, "
                    "scale_shift=4, zero_point=5, s8 result. Quantize before "
                    "relu (not after) so a negative biased accumulator can "
                    "still reach affine_quantize's negative_saturation bin; "
                    "relu then guarantees a non-negative final s8 result."
                ),
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
                        "biased": {
                            "kind": "bias_add", "depends_on": ["accumulator"],
                            "data_object": "bias_vector", "broadcast_dimensions": ["N"],
                        },
                        "quantized": {
                            "kind": "affine_quantize", "depends_on": ["biased"],
                            "scale_multiplier": 1, "scale_shift": 4,
                            "zero_point": 5, "data_type": "s8",
                            "rounding": "nearest_ties_to_even",
                            "saturation": "clamp",
                            "granularity": "per_tensor",
                        },
                        "activated": {"kind": "relu", "depends_on": ["quantized"]},
                    },
                    "post_output": "activated",
                    "bias_conversion": "wrap_twos_complement_after_add",
                    "result_data_type": "s8",
                    "result_conversion": "exact",
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
            }
        ],
        "data_types": [
            {"name": "s8", "role": "signed 8-bit GEMM operand and quantized result", "width_bits": 8, "signed": True,
             "representation": "twos_complement", "conversion_semantics": "n/a",
             "overflow_semantics": "n/a", "rounding_semantics": "n/a"},
            {"name": "s16", "role": "signed 16-bit product/accumulator/bias", "width_bits": 16, "signed": True,
             "representation": "twos_complement", "conversion_semantics": "n/a",
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
            {"name": "Y_matrix", "role": "result_matrix", "data_type": "s8",
             "dimensions": ["M", "N"], "producer": "gemm", "consumers": ["external"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["M", "N"],
                                "description": "One element per transfer."}},
        ],
        "dimensions": [
            {"name": "M", "semantic": "GEMM row count", "minimum": M, "maximum": M,
             "runtime_configurable": False, "bound_parameter": ""},
            {"name": "K", "semantic": "GEMM reduction depth", "minimum": K, "maximum": K,
             "runtime_configurable": False, "bound_parameter": ""},
            {"name": "N", "semantic": "GEMM column count", "minimum": N, "maximum": N,
             "runtime_configurable": False, "bound_parameter": ""},
        ],
        "parameters": [],
        "compute": {"organization": "sequential streaming load/compute/store FSM"},
        "storage": [],
        "pipeline": {"stages": "load_a -> load_b -> load_bias -> output"},
        "control": {"style": "single ready/valid command channel, valid_ready_handshake"},
        "reset": {"synchronous": True, "active_low": True, "behavior": "aborts any in-flight job"},
        "latency_model": {"exact": False, "note": "No exact cycle count promised."},
        "architectural_invariants": ["Exactly one GEMM job may be in flight at a time."],
        "open_assumptions": [],
    }


def build_interface_contract() -> dict:
    def sig(name, role, direction, width, channel=None, semantic_class=None, semantic=None, signed=False, reset_value=None):
        entry = {
            "name": name, "role": role, "semantic_class": semantic_class, "channel": channel,
            "direction": direction, "width": width, "signed": signed,
        }
        if semantic is not None:
            entry["semantic"] = semantic
        if reset_value is not None:
            entry["reset_value"] = reset_value
        return entry

    def channel(name, direction, data_objects, ordering, framing="exact tensor"):
        return {
            "name": name, "direction": direction, "protocol_profile": "ready_valid",
            "data_objects": data_objects, "ordering": ordering, "framing": framing,
        }

    return {
        "clock": "clk", "reset": "rst_n",
        "channels": [
            channel("cmd", "input", [], "one command", framing="one beat"),
            channel("a", "input", ["A_matrix"], "declared dimension order"),
            channel("b", "input", ["B_matrix"], "declared dimension order"),
            channel("bias", "input", ["bias_vector"], "declared dimension order"),
            channel("y", "output", ["Y_matrix"], "declared dimension order"),
        ],
        "signals": [
            sig("clk", "clock", "input", 1, semantic="Free-running clock.", reset_value="0"),
            sig("rst_n", "reset", "input", 1, semantic="Synchronous active-low reset.", reset_value="0"),
            sig("cmd_valid", "valid", "input", 1, channel="cmd"),
            sig("cmd_ready", "ready", "output", 1, channel="cmd"),
            sig("cmd_op", "payload", "input", "1", channel="cmd", semantic_class="command", semantic="legal only 1'd1"),
            sig("a_valid", "valid", "input", 1, channel="a"),
            sig("a_ready", "ready", "output", 1, channel="a"),
            sig("a_data", "payload", "input", "8", channel="a", semantic_class="data", signed=True),
            sig("b_valid", "valid", "input", 1, channel="b"),
            sig("b_ready", "ready", "output", 1, channel="b"),
            sig("b_data", "payload", "input", "8", channel="b", semantic_class="data", signed=True),
            sig("bias_valid", "valid", "input", 1, channel="bias"),
            sig("bias_ready", "ready", "output", 1, channel="bias"),
            sig("bias_data", "payload", "input", "16", channel="bias", semantic_class="data", signed=True),
            sig("y_valid", "valid", "output", 1, channel="y"),
            sig("y_ready", "ready", "input", 1, channel="y"),
            sig("y_data", "payload", "output", "8", channel="y", semantic_class="data", signed=True),
            sig("busy", "busy", "output", 1),
            sig("done", "completion", "output", 1),
            sig("err", "error", "output", 1),
        ],
        "global_handshake_rules": (
            "Every VALID/READY pair follows standard ready/valid stability: "
            "once asserted, VALID and its payload hold stable until the "
            "paired READY active edge. All producer VALIDs are held low "
            "throughout active reset."
        ),
    }


def main() -> None:
    architecture_contract = build_architecture_contract()
    interface_contract = build_interface_contract()
    (HERE / "architecture_contract.yaml").write_text(
        yaml.safe_dump(architecture_contract, sort_keys=False), encoding="utf-8"
    )
    (HERE / "interface_contract.yaml").write_text(
        yaml.safe_dump(interface_contract, sort_keys=False), encoding="utf-8"
    )

    from multigent.verifier_tool import (
        validate_interface_signal_roles,
        validate_interface_semantics,
        validate_architecture_operation_features,
        validate_architecture_lifecycle_policies,
        validate_architecture_operation_arithmetic,
        build_architect_operation_metadata,
    )

    errors = []
    errors += validate_interface_signal_roles(interface_contract)
    errors += validate_interface_semantics(interface_contract)
    errors += validate_architecture_operation_features(architecture_contract)
    errors += validate_architecture_lifecycle_policies(architecture_contract)
    errors += validate_architecture_operation_arithmetic(architecture_contract)
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    print("All five reference-validation checks passed with zero errors.")

    operation_metadata = build_architect_operation_metadata(architecture_contract, interface_contract)
    if operation_metadata.get("unrepresentable_operations"):
        print("UNREPRESENTABLE:", operation_metadata["unrepresentable_operations"])
        raise SystemExit(1)
    print("operation_metadata built OK. operations:", [o["operation_name"] for o in operation_metadata["operations"]])


if __name__ == "__main__":
    main()
