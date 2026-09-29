"""Hand-authored frozen contract for the ready_valid tiny-GEMM fixture,
variant B: bias_add -> affine_quantize (no relu), matching
`rtl_b/tiny_gemm_rv_b_top.v` exactly. No Architect/Verifier LLM call.

Deliberately does NOT chain a relu stage before the quantizer: doing so
provably makes `quantization.negative_saturation` unreachable (relu's output
is always >= 0, and the quantizer's zero_point must itself be representable
in the output dtype, so the quantized value can never fall below the dtype
minimum) -- verifier_tool's own `generate_canonical_stimulus_for_bin` already
detects exactly that case and raises `unreachable`. This variant exists
specifically so `negative_saturation` (and `positive_saturation`, `exact`,
`rounded`, `nonzero_zero_point`) are all genuinely required and reachable.
"""
from __future__ import annotations

from pathlib import Path

import yaml

HERE = Path(__file__).parent
M, K, N = 1, 4, 1


def build_architecture_contract() -> dict:
    return {
        "design": {
            "name": "ready_valid_tiny_gemm_b",
            "description": (
                "Minimal hand-authored ready/valid GEMM (M=1,K=4,N=1) with "
                "bias-add then per-tensor affine_quantize (round-nearest-even, "
                "clamp saturation), no memory-mapped transport -- qualifies "
                "the ready_valid protocol profile plus the "
                "post_processing.quantization operation bins, independent of "
                "the AXI4 HLS Golden fixture."
            ),
        },
        "operations": [
            {
                "name": "gemm",
                "kind": "arithmetic",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values", "accumulation", "post_processing"],
                "feature_extensions": ["bias", "quantization"],
                "semantics": (
                    "Y = quantize(sum_k A[k]*B[k] + bias), exact s16 product, "
                    "wrapping s16 accumulator, per-tensor affine quantization "
                    "to s8 with scale_multiplier=1, scale_shift=2, zero_point=-1, "
                    "round-nearest-even, clamp saturation."
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
                            "scale_multiplier": 1, "scale_shift": 2, "zero_point": -1,
                            "data_type": "s8", "rounding": "nearest_ties_to_even",
                            "saturation": "clamp", "granularity": "per_tensor",
                        },
                    },
                    "post_output": "quantized",
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
            {"name": "s8", "role": "signed 8-bit GEMM operand/quantized result", "width_bits": 8, "signed": True,
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
    channels = []
    signals = [
        {"name": "clk", "role": "clock", "semantic_class": None, "channel": None,
         "direction": "input", "width": 1, "signed": False, "semantic": "Free-running clock.", "reset_value": "0"},
        {"name": "rst_n", "role": "reset", "semantic_class": None, "channel": None,
         "direction": "input", "width": 1, "signed": False,
         "semantic": "Synchronous active-low reset.", "reset_value": "0"},
    ]

    channels.append({
        "name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
        "data_objects": [], "ordering": "one command", "framing": "one beat",
    })
    signals.extend([
        {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input", "width": 1, "signed": False},
        {"name": "cmd_ready", "role": "ready", "channel": "cmd", "direction": "output", "width": 1, "signed": False},
        {"name": "cmd_op", "role": "payload", "semantic_class": "command", "channel": "cmd",
         "direction": "input", "width": "1", "signed": False, "semantic": "legal only 1'd1"},
    ])

    for name, direction, obj, width, signed in (
        ("a", "input", "A_matrix", 8, True),
        ("b", "input", "B_matrix", 8, True),
        ("bias", "input", "bias_vector", 16, True),
        ("y", "output", "Y_matrix", 8, True),
    ):
        channels.append({
            "name": name, "direction": direction, "protocol_profile": "ready_valid",
            "data_objects": [obj], "ordering": "declared dimension order", "framing": "exact tensor",
        })
        ready_direction = "output" if direction == "input" else "input"
        signals.extend([
            {"name": f"{name}_valid", "role": "valid", "channel": name, "direction": direction,
             "width": 1, "signed": False},
            {"name": f"{name}_ready", "role": "ready", "channel": name, "direction": ready_direction,
             "width": 1, "signed": False},
            {"name": f"{name}_data", "role": "payload", "semantic_class": "data", "channel": name,
             "direction": direction, "width": str(width), "signed": signed},
        ])

    signals.extend([
        {"name": "busy", "role": "busy", "channel": None, "direction": "output", "width": 1, "signed": False},
        {"name": "done", "role": "completion", "channel": None, "direction": "output", "width": 1, "signed": False},
        {"name": "err", "role": "error", "channel": None, "direction": "output", "width": 1, "signed": False},
    ])

    return {
        "clock": "clk", "reset": "rst_n",
        "channels": channels, "signals": signals,
        "global_handshake_rules": (
            "Every VALID/READY pair follows standard ready/valid stability: once "
            "asserted, VALID and its payload hold stable until the paired READY "
            "active edge. All producer VALIDs are held low throughout active reset."
        ),
    }


if __name__ == "__main__":
    architecture = build_architecture_contract()
    interface = build_interface_contract()
    (HERE / "architecture_contract_b.yaml").write_text(
        yaml.safe_dump(architecture, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    (HERE / "interface_contract_b.yaml").write_text(
        yaml.safe_dump(interface, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    print("Wrote architecture_contract_b.yaml and interface_contract_b.yaml")
