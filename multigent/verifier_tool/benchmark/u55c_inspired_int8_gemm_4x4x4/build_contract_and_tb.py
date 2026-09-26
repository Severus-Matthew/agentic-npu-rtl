"""Hand-authored frozen contract (no Architect/Verifier API calls) + deterministic
TB rendering via verifier_tool's fully automatic code-owned campaign path.

See README.md in this folder for the full design rationale and how this
compares to the real u55c_mb_packed_gemm32x128/gemm_hls/int8_gemm.cpp kernel.
Re-running this script regenerates architecture_contract.yaml,
interface_contract.yaml, module_manifest.json, acceptance_criteria.yaml, and
test_gemm_automatic.py in place, deterministically, with zero API calls.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent


def sig(name, role, direction, width, channel=None, semantic_class=None, semantic="", reset_value="0"):
    return {
        "name": name, "role": role, "semantic_class": semantic_class, "channel": channel,
        "direction": direction, "width": width, "signed": False, "semantic": semantic,
        "reset_value": reset_value,
    }


_CAPABILITY_TAGS = [
    "protocol_capability.max_outstanding=1",
    "protocol_capability.read_write_concurrency=false",
    "protocol_capability.address_bins=aligned",
    "protocol_capability.write_strobe_bins=full",
    "protocol_capability.protection_bins=none",
    "protocol_capability.write_order_bins=address_first",
]


def axi_lite_group(prefix, *, read_data_objects, write_data_objects):
    """One shared axi4_lite manager group (all 5 channels) serving every
    sequential read (A then B, in that order) and the single write (Y).

    The automatic memory-mapped campaign (stimulus/campaign.py::
    automatic_campaign_support) requires every input/output binding of one
    operation to resolve to the SAME protocol_group -- see
    _axi_lite_group() there, which raises unless exactly one group name is
    referenced across all of an operation's inputs and outputs. Three
    independent manager ports (closer to the real u55c kernel's three
    `gmem_*` bundles) are not automatable today; one shared group is.
    """
    channels, signals = [], []

    def chan(kind, name, direction, data_objects, extra_metadata=()):
        channels.append({
            "name": name, "direction": direction, "protocol_profile": "axi4_lite",
            "purpose": f"{prefix} {kind}", "data_objects": data_objects,
            "metadata": [f"protocol_group={prefix}", f"protocol_channel={kind}", *extra_metadata],
            "framing": "single_beat_per_transfer", "ordering": "in_order",
            "backpressure": True,
        })

    ar, r = f"{prefix}_ar", f"{prefix}_r"
    aw, w, b = f"{prefix}_aw", f"{prefix}_w", f"{prefix}_b"
    chan("read_address", ar, "output", [], extra_metadata=_CAPABILITY_TAGS)
    chan("read_data", r, "input", list(read_data_objects))
    chan("write_address", aw, "output", [])
    chan("write_data", w, "output", list(write_data_objects))
    chan("write_response", b, "input", [])
    signals += [
        sig(f"{prefix}_araddr", "payload", "output", 32, ar, "address", "protocol_field=addr"),
        sig(f"{prefix}_arvalid", "valid", "output", 1, ar, None, "AR channel valid."),
        sig(f"{prefix}_arready", "ready", "input", 1, ar, None, "AR channel ready."),
        sig(f"{prefix}_rdata", "payload", "input", 32, r, "data", "protocol_field=data"),
        sig(f"{prefix}_rresp", "metadata", "input", 2, r, "response_code", "protocol_field=resp"),
        sig(f"{prefix}_rvalid", "valid", "input", 1, r, None, "R channel valid."),
        sig(f"{prefix}_rready", "ready", "output", 1, r, None, "R channel ready."),
        sig(f"{prefix}_awaddr", "payload", "output", 32, aw, "address", "protocol_field=addr"),
        sig(f"{prefix}_awvalid", "valid", "output", 1, aw, None, "AW channel valid."),
        sig(f"{prefix}_awready", "ready", "input", 1, aw, None, "AW channel ready."),
        sig(f"{prefix}_wdata", "payload", "output", 32, w, "data", "protocol_field=data"),
        sig(f"{prefix}_wstrb", "metadata", "output", 4, w, "byte_enable", "protocol_field=strb"),
        sig(f"{prefix}_wvalid", "valid", "output", 1, w, None, "W channel valid."),
        sig(f"{prefix}_wready", "ready", "input", 1, w, None, "W channel ready."),
        sig(f"{prefix}_bresp", "metadata", "input", 2, b, "response_code", "protocol_field=resp"),
        sig(f"{prefix}_bvalid", "valid", "input", 1, b, None, "B channel valid."),
        sig(f"{prefix}_bready", "ready", "output", 1, b, None, "B channel ready."),
    ]
    return channels, signals


def base_pointer_metadata_field(name, data_object):
    return sig(
        name, "metadata", "input", 32, "cmd_chan", "address",
        f"data_object={data_object} address_role=base byte_order=little "
        f"address_sequence=contiguous word_stride_bytes=4",
    )


def build_architecture_contract():
    axi_channels, axi_signals = axi_lite_group(
        "m_axi", read_data_objects=["A_matrix", "B_matrix"], write_data_objects=["Y_matrix"],
    )

    interface_contract = {
        "protocol": "custom_command_plus_axi4_lite_memory",
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {
                "name": "cmd_chan", "direction": "input", "protocol_profile": "ready_valid",
                "purpose": "Accept one GEMM job: opcode plus A/B/Y base pointers.",
                "data_objects": [], "metadata": [], "framing": "single_beat",
                "ordering": "in_order", "backpressure": True,
            },
            *axi_channels,
        ],
        "signals": [
            sig("clk", "clock", "input", 1, None, None, "Free-running clock."),
            sig("rst_n", "reset", "input", 1, None, None, "Synchronous active-low reset."),
            sig("cmd_valid", "valid", "input", 1, "cmd_chan", None, "Command channel valid."),
            sig("cmd_ready", "ready", "output", 1, "cmd_chan", None, "Command channel ready."),
            sig("cmd_opcode", "payload", "input", 8, "cmd_chan", "command",
                "Legal only 8'h01. Selects the single supported GEMM job."),
            base_pointer_metadata_field("a_base", "A_matrix"),
            base_pointer_metadata_field("b_base", "B_matrix"),
            base_pointer_metadata_field("c_base", "Y_matrix"),
            sig("busy", "busy", "output", 1, None, None, "High while a GEMM job is in progress."),
            sig("completion", "completion", "output", 1, None, None, "One-cycle pulse on job completion."),
            sig("error", "error", "output", 1, None, None,
                "One-cycle pulse on any non-OKAY AXI4-Lite response on the shared manager port."),
            *axi_signals,
        ],
        "global_handshake_rules": (
            "Every VALID/READY pair follows standard AMBA stability: once asserted, "
            "VALID and its payload/address/data hold stable until the paired READY "
            "active edge. All producer VALIDs are held low throughout active reset."
        ),
    }

    architecture_contract = {
        "design": {
            "name": "u55c_inspired_int8_gemm_4x4x4",
            "description": (
                "Tiny 4x4x4 signed-int8 GEMM accelerator, hand-authored (no Architect "
                "LLM call) as a verifier_tool benchmark fixture. Loosely inspired by "
                "u55c_mb_packed_gemm32x128/gemm_hls/int8_gemm.cpp: same core math "
                "(signed int8 A/B, exact product, signed int32 accumulate, no bias, "
                "no activation) at a scale small enough for this tool's fully "
                "automatic ready/valid + AXI4-Lite capture/drive campaign to cover "
                "end to end without any Verifier-authored code. Memory access is "
                "one shared AXI4-Lite manager port (sequential A-then-B reads, "
                "then Y writes) rather than the real kernel's three independent "
                "burst-AXI4 gmem ports; this fixture intentionally uses the simpler "
                "shared single-beat interface to keep the benchmark compact."
            ),
        },
        "operations": [
            {
                "name": "gemm", "kind": "arithmetic",
                "coverage_family": "matrix_multiply", "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values", "accumulation"],
                "feature_extensions": [],
                "semantics": "Y[m,n] = sum_k A[m,k] * B[k,n], exact signed 32-bit accumulation, no bias, no activation.",
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
            {"name": "A_matrix", "role": "left_operand_matrix", "data_type": "s8",
             "dimensions": ["M", "K"], "producer": "external", "consumers": ["gemm"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["M", "K"],
                                "description": "Row-major: one element per logical position, K varies fastest, then M."}},
            {"name": "B_matrix", "role": "right_operand_matrix", "data_type": "s8",
             "dimensions": ["K", "N"], "producer": "external", "consumers": ["gemm"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["K", "N"],
                                "description": "Row-major: one element per logical position, N varies fastest, then K."}},
            {"name": "Y_matrix", "role": "result_matrix", "data_type": "s32",
             "dimensions": ["M", "N"], "producer": "gemm", "consumers": ["external"], "external": True,
             "serialization": {"kind": "dense_tensor", "index_order": ["M", "N"],
                                "description": "Row-major: one element per logical position, N varies fastest, then M."}},
        ],
        "dimensions": [
            {"name": "M", "semantic": "GEMM row count", "minimum": 4, "maximum": 4,
             "runtime_configurable": False, "bound_parameter": ""},
            {"name": "K", "semantic": "GEMM reduction depth", "minimum": 4, "maximum": 4,
             "runtime_configurable": False, "bound_parameter": ""},
            {"name": "N", "semantic": "GEMM column count", "minimum": 4, "maximum": 4,
             "runtime_configurable": False, "bound_parameter": ""},
        ],
        "parameters": [],
        "compute": {"organization": "direct elementwise MAC, no tiling", "parallelism": "fully sequential", "dataflow": "load A/B then compute then store Y"},
        "storage": [],
        "pipeline": {"stages": "none: single always-legal command executes to completion before the next is accepted"},
        "control": {"style": "single-job FSM: IDLE -> LOAD_A -> LOAD_B -> COMPUTE -> STORE_Y -> IDLE"},
        "reset": {"synchronous": True, "active_low": True, "behavior": "aborts any in-flight job with no ghost completion/error"},
        "latency_model": {"exact": False, "note": "Bounded by handshake liveness only; no exact cycle count promised."},
        "architectural_invariants": [
            "Exactly one GEMM job may be in flight at a time.",
            "A and B are fully consumed through the shared AXI4-Lite manager group before Y is written through that same group.",
        ],
        "open_assumptions": [
            "Real burst AXI4 (as in the u55c reference kernel) is out of scope; this benchmark uses one shared AXI4-Lite manager group for sequential single-beat A/B reads and Y writes instead.",
        ],
    }

    module_manifest = {
        "top": "u55c_inspired_int8_gemm_4x4x4_top",
        "modules": [
            {
                "name": "u55c_inspired_int8_gemm_4x4x4_top",
                "responsibility": "Command decode, AXI4-Lite manager sequencing for A/B/Y, and the GEMM datapath.",
                "dependencies": [], "parameters": [], "stateful": True,
                "ports": [
                    {"name": s["name"], "direction": s["direction"], "width": s["width"]}
                    for s in interface_contract["signals"]
                ],
            }
        ],
    }

    acceptance_criteria = {
        "functional": ["Y exactly equals the int32 golden GEMM of the accepted A/B for every legal job."],
        "verification": ["100% functional coverage on dimensions/operand_values/accumulation bins.", "Reset-abort and illegal-opcode recovery both exercised."],
        "rtl": ["Synthesizable SystemVerilog, no forbidden constructs."],
        "fpga_handoff": ["Not required for this benchmark fixture."],
    }

    return architecture_contract, interface_contract, module_manifest, acceptance_criteria


def main():
    architecture_contract, interface_contract, module_manifest, acceptance_criteria = build_architecture_contract()

    (OUT / "architecture_contract.yaml").write_text(yaml.safe_dump(architecture_contract, sort_keys=False), encoding="utf-8")
    (OUT / "interface_contract.yaml").write_text(yaml.safe_dump(interface_contract, sort_keys=False), encoding="utf-8")
    (OUT / "module_manifest.json").write_text(json.dumps(module_manifest, indent=2), encoding="utf-8")
    (OUT / "acceptance_criteria.yaml").write_text(yaml.safe_dump(acceptance_criteria, sort_keys=False), encoding="utf-8")

    from multigent.verifier_tool import (
        validate_interface_signal_roles,
        validate_interface_semantics,
        validate_architecture_operation_features,
        validate_architecture_lifecycle_policies,
        validate_architecture_operation_arithmetic,
        build_architect_operation_metadata,
        build_interface_coverage_plan,
        automatic_campaign_support,
        render_contract_generated_block,
        synthesize_code_owned_operation_coverage,
        operation_plan_for_tests,
        merge_coverage_plans,
    )
    from multigent.verifier_tool.orchestration.runtime import InterfaceCoverageTracker

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
        return

    print("All five reference-validation checks passed with zero errors.")

    operation_metadata = build_architect_operation_metadata(architecture_contract, interface_contract)
    print("operation_metadata built OK. operations:", [o["operation_name"] for o in operation_metadata["operations"]])

    interface_plan = build_interface_coverage_plan(interface_contract)
    print("interface_plan built OK. obligation count:", len(interface_plan["obligations"]))

    support = automatic_campaign_support(operation_metadata, architecture_contract)
    print("automatic_campaign_support:", json.dumps(support, indent=2))

    block = render_contract_generated_block(
        interface_plan, architecture_contract,
        include_automatic_campaign=bool(support.get("supported")),
        randomized_transactions_minimum=8,
    )
    (OUT / "test_gemm_automatic.py").write_text(block, encoding="utf-8")
    print(f"Rendered generated block: {len(block)} bytes, {block.count(chr(10))} lines -> test_gemm_automatic.py")

    # Prove it's at least syntactically valid, complete Python.
    compile(block, "test_gemm_automatic.py", "exec")
    print("compile() succeeded: generated block is syntactically valid Python.")

    # Companion functional-coverage plan. contract_coverage() calls
    # get_coverage_tracker() the moment the generated test actually runs, and
    # that hard-requires NPU_FUNCTIONAL_COVERAGE_CONFIG to point at exactly
    # this merged (interface + operation + lifecycle) plan shape -- without
    # it the test would fail before any stimulus runs. specs=[] because this
    # design has zero Verifier-authored declarations; every concept here is
    # code-owned, so synthesize_code_owned_operation_coverage derives the
    # complete operation coverage from the frozen contract alone.
    # operation_plan_for_tests (not build_operation_coverage_plan directly)
    # is required: it is the one function that attaches
    # bindings.sampling={"template": "canonical_job"} for every code-owned
    # concept, which OperationSamplingMonitor hard-requires. contents=[]
    # because there is no Verifier-authored source to scan for custom
    # OPERATION_SAMPLING_BINDINGS -- this design declares none.
    synthesized_specs = synthesize_code_owned_operation_coverage(
        [], architecture_contract, operation_metadata
    )
    operation_plan = operation_plan_for_tests(
        synthesized_specs, [], architecture_contract, interface_contract
    )
    merged_plan = merge_coverage_plans(interface_plan, operation_plan)
    (OUT / "functional_coverage_plan.json").write_text(
        json.dumps(merged_plan, indent=2), encoding="utf-8"
    )
    print(
        "Merged functional coverage plan built OK. total obligations:",
        len(merged_plan["obligations"]),
        "-> functional_coverage_plan.json",
    )

    # A real InterfaceCoverageTracker against this plan -- the same
    # construction get_coverage_tracker() performs at test time, without
    # needing a live simulator -- then close() it immediately so it writes
    # its real report shape. This is a genuine zero-hit BASELINE, not a
    # placeholder: no RTL exists for this benchmark, so no stimulus has ever
    # actually run against a DUT. Every bin legitimately reads hits=0 and
    # status=FAIL here; a real simulator run would overwrite this file at
    # whatever path NPU_FUNCTIONAL_COVERAGE_REPORT names (see README.md),
    # with the identical shape but real hit counts.
    report_path = OUT / "functional_coverage_report.json"
    tracker = InterfaceCoverageTracker(merged_plan, report_path)
    tracker.close()
    print(
        "Baseline (zero-hit) coverage report written -> functional_coverage_report.json "
        "(+ functional_coverage_report.cocotb-coverage.yml)"
    )


if __name__ == "__main__":
    main()
