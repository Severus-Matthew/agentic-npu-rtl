"""Build (never via the Architect LLM -- hand-authored, deterministic) the
frozen architecture_contract/interface_contract for the REAL Vitis
HLS-generated int8 GEMM golden RTL in `gemm_golden/` (source:
`gemm_golden_hls/gemm_hls/int8_gemm.cpp`, M=32/K=64/N=128, packed_gemm_contract).

Exercises, in one real contract:
  - `packed_encoding` serialization for A_matrix (padded-lane) and B_matrix
    (DSP48 signed shift-add packing).
  - `control_plane_sequence` lifecycle policy for a genuine Vitis HLS
    `ap_ctrl_chain` AXI4-Lite control interface (no ready/valid command
    channel, no busy/error pins -- see `int8_gemm_control_s_axi.v`).
  - Three independent full-AXI4 manager groups (gmem_a/b/c), matching the
    real RTL's port names exactly.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

HERE = Path(__file__).parent

M, K, N = 32, 64, 128


def _packed_encoding_a() -> dict:
    return {
        "kind": "packed_encoding",
        "description": (
            "Word = K (64 words total). Whole 512-bit word is one container. "
            "field[m] = A[m][k], raw unsigned 8-bit pattern at bit m*8. "
            "Bits 256-511 are zero-padded, never read by the RTL."
        ),
        "traversal": {
            "word_axes": ["K"],
            "containers_per_word": 1,
            "container_axis": None,
            "field_axis": "M",
        },
        "packed_encoding": {
            "physical_container_width": 512,
            "used_width": 256,
            "used_bit_range": [0, 255],
            "padding_value": "zero",
            "container_bit_layout": "contiguous_ascending",
            "group_size": 32,
            "fields": [
                {"logical_offset": m, "source_width": 8, "interpretation": "unsigned", "shift": m * 8}
                for m in range(32)
            ],
        },
    }


def _packed_encoding_b() -> dict:
    return {
        "kind": "packed_encoding",
        "description": (
            "N=128 decomposes into N_tile(4) x N_lane(16) x N_offset(2), outer to "
            "inner: n = N_tile*32 + N_lane*2 + N_offset. Word = K*4 + N_tile (256 "
            "words total). Each word holds 16 containers (lanes); lane N_lane packs "
            "the pair (n0=tile*32+lane*2, n1=n0+1) via signed shift-add: "
            "P = as_signed(B[k][n0],8) + (as_signed(B[k][n1],8)<<18), truncated to "
            "27 bits -- the DSP48 pre-adder packing trick in "
            "gemm_hls/int8_gemm.cpp (packed_gemm_contract::load_b/packed_products). "
            "Bits 27-31 of every lane are zero-padded, never read by the RTL."
        ),
        "derived_axes": [
            {
                "real_axis": "N",
                "order": ["N_tile", "N_lane", "N_offset"],
                "sub_axes": [
                    {"name": "N_tile", "extent": 4},
                    {"name": "N_lane", "extent": 16},
                    {"name": "N_offset", "extent": 2},
                ],
            }
        ],
        "traversal": {
            "word_axes": ["K", "N_tile"],
            "containers_per_word": 16,
            "container_axis": "N_lane",
            "field_axis": "N_offset",
        },
        "packed_encoding": {
            "physical_container_width": 32,
            "used_width": 27,
            "used_bit_range": [0, 26],
            "padding_value": "zero",
            "container_bit_layout": "contiguous_ascending",
            "group_size": 2,
            "fields": [
                {"logical_offset": 0, "source_width": 8, "interpretation": "signed", "shift": 0},
                {"logical_offset": 1, "source_width": 8, "interpretation": "signed", "shift": 18},
            ],
        },
    }


def build_architecture_contract() -> dict:
    return {
        "design": {
            "name": "int8_gemm_hls_golden",
            "description": (
                "Real Vitis HLS v2023.2-generated 32x128x64 signed-int8 GEMM kernel "
                "(gemm_hls/int8_gemm.cpp, packed_gemm_contract), hand-authored contract "
                "(no Architect LLM call) matching gemm_golden/int8_gemm.v exactly: three "
                "independent full-AXI4 gmem_a/b/c manager ports plus a genuine ap_ctrl_chain "
                "AXI4-Lite control interface (ap_start/ap_done are internal wires, never "
                "top-level pins -- job control is entirely register-mapped)."
            ),
        },
        "operations": [
            {
                "name": "gemm",
                "kind": "arithmetic",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values", "accumulation"],
                "feature_extensions": [],
                "semantics": (
                    "Y[m,n] = sum_k A[m,k] * B[k,n], exact signed 32-bit accumulation, "
                    "no bias, no activation."
                ),
                "inputs": ["A_matrix", "B_matrix"],
                "outputs": ["Y_matrix"],
                "arithmetic": {
                    "classifier_profile": "integer_matrix_multiply",
                    "product_data_type": "s16",
                    "accumulator_data_type": "s32",
                    "accumulator_initialization": 0,
                    "reduction_dimensions": ["K"],
                    "reduction_order": "increasing_declared_reduction_coordinate",
                    "reduction_conversion": "exact",
                    "post_operations": {},
                    "post_output": "accumulator",
                    "bias_conversion": "exact",
                    "result_data_type": "s32",
                    "result_conversion": "exact",
                },
                "lifecycle_policy": {
                    "job_acceptance": "control_plane_sequence",
                    "job_overlap": "single_inflight",
                    "busy_behavior": "tracks_active_job",
                    "completion_style": "control_plane_sequence",
                    "completion_timing": "observed_via_poll",
                    "illegal_command_behavior": "error_without_start",
                    "error_style": "pulse",
                    "error_timing": "next_cycle_after_error_event",
                    "reset_behavior": "abort_inflight",
                },
                "lifecycle_control_plane_sequence": {
                    "registers": {
                        "control": {
                            "address": 0x00,
                        "fields": {
                            "ap_start": {"bit": 0},
                            "ap_done": {"bit": 1},
                            "ap_idle": {"bit": 2},
                            "ap_continue": {"bit": 4},
                            },
                        },
                        "a_low": {"address": 0x10},
                        "a_high": {"address": 0x14},
                        "b_low": {"address": 0x1C},
                        "b_high": {"address": 0x20},
                        "c_low": {"address": 0x28},
                        "c_high": {"address": 0x2C},
                    },
                    "job_start": {
                        "actions": [
                            # ap_ctrl_chain retains ap_done until ap_continue. Clear
                            # the previous job before programming the next one.
                            {"op": "write_field", "register": "control", "field": "ap_continue", "value": 1},
                            {"op": "write_reg", "register": "a_low",
                             "value_from": {"data_object": "A_matrix", "address_role": "base", "half": "low"}},
                            {"op": "write_reg", "register": "a_high",
                             "value_from": {"data_object": "A_matrix", "address_role": "base", "half": "high"}},
                            {"op": "write_reg", "register": "b_low",
                             "value_from": {"data_object": "B_matrix", "address_role": "base", "half": "low"}},
                            {"op": "write_reg", "register": "b_high",
                             "value_from": {"data_object": "B_matrix", "address_role": "base", "half": "high"}},
                            {"op": "write_reg", "register": "c_low",
                             "value_from": {"data_object": "Y_matrix", "address_role": "base", "half": "low"}},
                            {"op": "write_reg", "register": "c_high",
                             "value_from": {"data_object": "Y_matrix", "address_role": "base", "half": "high"}},
                            {"op": "write_field", "register": "control", "field": "ap_start", "value": 1},
                        ]
                    },
                    "job_complete": {
                        "actions": [
                            {"op": "poll_field", "register": "control", "field": "ap_done", "expected": 1},
                        ]
                    },
                },
            }
        ],
        "data_types": [
            {"name": "s8", "role": "signed 8-bit GEMM operand", "width_bits": 8, "signed": True,
             "representation": "twos_complement", "conversion_semantics": "n/a",
             "overflow_semantics": "n/a", "rounding_semantics": "n/a"},
            {"name": "s16", "role": "signed 16-bit exact intermediate product", "width_bits": 16, "signed": True,
             "representation": "twos_complement", "conversion_semantics": "n/a",
             "overflow_semantics": "n/a", "rounding_semantics": "n/a"},
            {"name": "s32", "role": "signed 32-bit accumulator and result", "width_bits": 32, "signed": True,
             "representation": "twos_complement", "conversion_semantics": "n/a",
             "overflow_semantics": "n/a", "rounding_semantics": "n/a"},
        ],
        "data_objects": [
            {
                "name": "A_matrix", "role": "left_operand_matrix", "data_type": "s8",
                "dimensions": ["M", "K"], "producer": "external", "consumers": ["gemm"], "external": True,
                "serialization": _packed_encoding_a(),
            },
            {
                "name": "B_matrix", "role": "right_operand_matrix", "data_type": "s8",
                "dimensions": ["K", "N"], "producer": "external", "consumers": ["gemm"], "external": True,
                "serialization": _packed_encoding_b(),
            },
            {
                "name": "Y_matrix", "role": "result_matrix", "data_type": "s32",
                "dimensions": ["M", "N"], "producer": "gemm", "consumers": ["external"], "external": True,
                "serialization": {
                    "kind": "dense_tensor", "index_order": ["M", "N"],
                    "description": "Row-major: N varies fastest, then M (plain, no packing).",
                },
            },
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
        "compute": {
            "organization": "4-way systolic tile array, 32x16 pairs per tile",
            "parallelism": "4 tiles x 32 rows x 16 column-pairs, DSP48 SIMD-packed",
            "dataflow": "load A, load B, run_tiles (dataflow), store C",
        },
        "storage": [],
        "pipeline": {"stages": "load_a || load_b -> run_tiles (4-way dataflow) -> store_c"},
        "control": {"style": "Vitis HLS ap_ctrl_chain: IDLE -> (register-driven start) -> RUNNING -> DONE"},
        "reset": {"synchronous": True, "active_low": True, "behavior": "aborts any in-flight job"},
        "latency_model": {"exact": False, "note": "Bounded by ap_done liveness only; no exact cycle count promised."},
        "architectural_invariants": [
            "Exactly one GEMM job may be in flight at a time.",
            "A_matrix and B_matrix are read via independent AXI4 manager ports (gmem_a, gmem_b) "
            "concurrently with each other; Y_matrix is written via a third (gmem_c).",
        ],
        "open_assumptions": [
            "Job control is entirely AXI4-Lite register-mapped (ap_start/ap_done are internal "
            "wires, never top-level ports) -- see control_plane_sequence.",
        ],
    }


_CAPABILITY_TAGS = [
    "protocol_capability.max_outstanding=16",
    "protocol_capability.read_write_concurrency=false",
    "protocol_capability.address_bins=aligned",
    "protocol_capability.alignment_bins=aligned",
    "protocol_capability.burst_type_bins=incrementing",
    "protocol_capability.transfer_size_bins=full_width",
    "protocol_capability.id_bins=zero",
    "protocol_capability.write_strobe_bins=full",
    "protocol_capability.protection_bins=none",
    "protocol_capability.write_order_bins=address_first|same_cycle",
]


def _axi4_channel(name: str, kind: str, direction: str, protocol_group: str, data_objects: list[str], *, with_id: bool = True) -> dict:
    metadata = [f"protocol_group={protocol_group} protocol_channel={kind}"]
    if kind in ("read_address", "write_address"):
        metadata.extend(_CAPABILITY_TAGS)
    return {
        "name": name, "direction": direction, "protocol_profile": "axi4",
        "data_objects": data_objects, "ordering": "any completion order", "framing": "burst",
        "metadata": metadata,
    }


def _axi4_signals(prefix: str, kind: str, direction: str, *, with_id: bool = True) -> list[dict]:
    signals = [
        {"name": f"{prefix}{_SUFFIX[kind]['V']}", "role": "valid", "direction": direction, "channel": prefix, "width": "1"},
        {"name": f"{prefix}{_SUFFIX[kind]['R']}", "role": "ready",
         "direction": "input" if direction == "output" else "output", "channel": prefix, "width": "1"},
    ]
    for field, (role, semantic_class, width) in _FIELDS[kind](with_id).items():
        signals.append({
            "name": f"{prefix}{field}", "role": role, "semantic_class": semantic_class,
            "direction": direction, "channel": prefix, "width": str(width),
            "semantic": f"protocol_field={field.lower()}",
        })
    return signals


_SUFFIX = {
    "write_address": {"V": "VALID", "R": "READY"}, "write_data": {"V": "VALID", "R": "READY"},
    "write_response": {"V": "VALID", "R": "READY"}, "read_address": {"V": "VALID", "R": "READY"},
    "read_data": {"V": "VALID", "R": "READY"},
}


def _fields_aw(with_id: bool) -> dict:
    fields = {
        "ADDR": ("payload", "address", 64), "LEN": ("metadata", "length", 8),
        "SIZE": ("metadata", "size", 3), "BURST": ("metadata", "burst_type", 2),
    }
    if with_id:
        fields["ID"] = ("transaction_id", "identifier", 1)
    return fields


def _fields_w() -> dict:
    return {"DATA": ("payload", "data", 512), "STRB": ("metadata", "byte_enable", 64), "LAST": ("last", "framing", 1)}


def _fields_b(with_id: bool) -> dict:
    fields = {"RESP": ("payload", "response_code", 2)}
    if with_id:
        fields["ID"] = ("transaction_id", "identifier", 1)
    return fields


def _fields_ar(with_id: bool) -> dict:
    return _fields_aw(with_id)


def _fields_r(with_id: bool) -> dict:
    fields = {"DATA": ("payload", "data", 512), "RESP": ("metadata", "response_code", 2), "LAST": ("last", "framing", 1)}
    if with_id:
        fields["ID"] = ("transaction_id", "identifier", 1)
    return fields


_FIELDS = {
    "write_address": lambda with_id: _fields_aw(with_id),
    "write_data": lambda with_id: _fields_w(),
    "write_response": lambda with_id: _fields_b(with_id),
    "read_address": lambda with_id: _fields_ar(with_id),
    "read_data": lambda with_id: _fields_r(with_id),
}


def _gmem_group(gmem_name: str, prefix: str, *, capability: str, data_object: str) -> tuple[list[dict], list[dict]]:
    """One full-AXI4 manager group named to match the real RTL's own
    `m_axi_<gmem_name>_*` ports exactly -- read-only (gmem_a/b: ar+r only) or
    write-only (gmem_c: aw+w+b only), matching `standard_protocols.py`'s
    channel_set rule that a capability's channels are all present or all
    absent (the real RTL's write/read ports on a read-only/write-only gmem
    port exist electrically but carry no real traffic in this contract)."""

    kind_prefix = {
        "write_address": "AW", "write_data": "W", "write_response": "B",
        "read_address": "AR", "read_data": "R",
    }
    kinds_by_capability = {
        "read": {"read_address": [], "read_data": [data_object]},
        "write": {"write_address": [], "write_data": [data_object], "write_response": []},
    }
    direction_by_kind = {
        "write_address": "output", "write_data": "output", "write_response": "input",
        "read_address": "output", "read_data": "input",
    }
    channels, signals = [], []
    for kind, objs in kinds_by_capability[capability].items():
        direction = direction_by_kind[kind]
        channel_name = f"{prefix}_{kind_prefix[kind].lower()}"
        channels.append(_axi4_channel(channel_name, kind, direction, gmem_name, objs))
        for signal in _axi4_signals(f"{prefix}_{kind_prefix[kind]}", kind, direction):
            signal["channel"] = channel_name
            signals.append(signal)
    return channels, signals


def build_interface_contract() -> dict:
    channels: list[dict] = []
    signals: list[dict] = [
        {"name": "ap_clk", "role": "clock", "semantic_class": None, "channel": None, "direction": "input",
         "width": 1, "signed": False, "semantic": "Free-running kernel clock.", "reset_value": "0"},
        {"name": "ap_rst_n", "role": "reset", "semantic_class": None, "channel": None, "direction": "input",
         "width": 1, "signed": False, "semantic": "Synchronous active-low reset.", "reset_value": "0",
         "reset_settle_cycles": 4},
    ]

    for gmem, prefix, capability, data_object in (
        ("gmem_a", "m_axi_gmem_a", "read", "A_matrix"),
        ("gmem_b", "m_axi_gmem_b", "read", "B_matrix"),
        ("gmem_c", "m_axi_gmem_c", "write", "Y_matrix"),
    ):
        group_channels, group_signals = _gmem_group(gmem, prefix, capability=capability, data_object=data_object)
        channels.extend(group_channels)
        signals.extend(group_signals)

    control_prefix = "s_axi_control"
    control_data_widths = {"write_data": 32, "read_data": 32}
    for kind, chan_short in (
        ("write_address", "aw"), ("write_data", "w"), ("write_response", "b"),
        ("read_address", "ar"), ("read_data", "r"),
    ):
        channel_name = f"{control_prefix}_{chan_short}"
        direction = "input" if kind in ("write_address", "write_data", "read_address") else "output"
        channels.append({
            "name": channel_name, "direction": direction, "protocol_profile": "axi4_lite",
            "data_objects": [], "framing": "single_beat_per_transfer", "ordering": "in_order",
            "backpressure": True,
            "metadata": [
                f"protocol_group=control protocol_channel={kind}",
                *(
                    ["protocol_capability.max_outstanding=2",
                     "protocol_capability.write_order_bins=address_first"]
                    if kind in ("write_address", "read_address") else []
                ),
            ],
        })
        kind_prefix = {"write_address": "AW", "write_data": "W", "write_response": "B", "read_address": "AR", "read_data": "R"}[kind]
        valid_dir = direction
        ready_dir = "output" if direction == "input" else "input"
        signals.append({"name": f"{control_prefix}_{kind_prefix}VALID", "role": "valid", "semantic_class": None,
                         "channel": channel_name, "direction": valid_dir, "width": 1, "signed": False,
                         "semantic": f"{kind} valid.", "reset_value": "0"})
        signals.append({"name": f"{control_prefix}_{kind_prefix}READY", "role": "ready", "semantic_class": None,
                         "channel": channel_name, "direction": ready_dir, "width": 1, "signed": False,
                         "semantic": f"{kind} ready.", "reset_value": "0"})
        if kind in ("write_address", "read_address"):
            signals.append({"name": f"{control_prefix}_{kind_prefix}ADDR", "role": "payload",
                             "semantic_class": "address", "channel": channel_name, "direction": direction,
                             "width": 6, "signed": False, "semantic": "protocol_field=addr", "reset_value": "0"})
        elif kind == "write_data":
            signals.append({"name": f"{control_prefix}_WDATA", "role": "payload", "semantic_class": "data",
                             "channel": channel_name, "direction": direction, "width": 32, "signed": False,
                             "semantic": "protocol_field=data", "reset_value": "0"})
            signals.append({"name": f"{control_prefix}_WSTRB", "role": "metadata", "semantic_class": "byte_enable",
                             "channel": channel_name, "direction": direction, "width": 4, "signed": False,
                             "semantic": "protocol_field=strb", "reset_value": "0"})
        elif kind == "write_response":
            signals.append({"name": f"{control_prefix}_BRESP", "role": "payload", "semantic_class": "response_code",
                             "channel": channel_name, "direction": direction, "width": 2, "signed": False,
                             "semantic": "protocol_field=resp", "reset_value": "0"})
        elif kind == "read_data":
            signals.append({"name": f"{control_prefix}_RDATA", "role": "payload", "semantic_class": "data",
                             "channel": channel_name, "direction": direction, "width": 32, "signed": False,
                             "semantic": "protocol_field=data"})
            signals.append({"name": f"{control_prefix}_RRESP", "role": "metadata", "semantic_class": "response_code",
                             "channel": channel_name, "direction": direction, "width": 2, "signed": False,
                             "semantic": "protocol_field=resp", "reset_value": "0"})

    return {
        "clock": "ap_clk", "reset": "ap_rst_n",
        "channels": channels, "signals": signals,
        "global_handshake_rules": (
            "Every VALID/READY pair follows standard AMBA stability: once asserted, VALID and "
            "its payload/address/data hold stable until the paired READY active edge. All "
            "producer VALIDs are held low throughout active reset."
        ),
    }


if __name__ == "__main__":
    architecture = build_architecture_contract()
    interface = build_interface_contract()
    (HERE / "architecture_contract.yaml").write_text(
        yaml.safe_dump(architecture, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    (HERE / "interface_contract.yaml").write_text(
        yaml.safe_dump(interface, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    print("Wrote architecture_contract.yaml and interface_contract.yaml")
