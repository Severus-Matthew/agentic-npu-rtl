from __future__ import annotations

from copy import deepcopy

import pytest

from multigent.verifier_tool import (
    CanonicalOperationError,
    CanonicalStimulusGenerationError,
    InterfaceCoverageTracker,
    automatic_campaign_support,
    assemble_canonical_job,
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    build_lifecycle_assertion_plan,
    canonical_bins_for_concept,
    classify_operation_job,
    check_lifecycle_assertions,
    evaluate_canonical_operation,
    generate_canonical_stimulus_for_bin,
    generate_canonical_stimulus_suite,
    generate_random_canonical_stimuli,
    finalize_lifecycle_assertions,
    normalize_operation_sampling_bindings,
    operation_plan_for_tests,
    reachable_canonical_bins_for_concept,
    render_contract_generated_block,
)
from multigent.verifier_tool.pool.operation_metadata.protocol import (
    ProtocolAdapterError,
    ReadyValidCaptureAdapter,
)


def contracts():
    architecture = {
        "operations": [{
            "name": "gemm_core",
            "kind": "matrix_multiply",
            "coverage_family": "matrix_multiply",
            "coverage_family_source": "catalog",
            "features": ["dimensions", "operand_values", "accumulation", "post_processing"],
            "feature_extensions": ["bias", "activation"],
            "semantics": "signed integer GEMM; add bias; apply ReLU",
            "arithmetic": {
                "classifier_profile": "integer_matrix_multiply",
                "product_data_type": "s16",
                "accumulator_data_type": "s32",
                "accumulator_initialization": 0,
                "reduction_dimensions": ["K"],
                "reduction_order": "increasing_declared_reduction_coordinate",
                "reduction_conversion": "wrap_twos_complement_after_each_add",
                "post_operations": {
                    "bias": {"kind": "bias_add", "depends_on": ["accumulator"], "data_object": "bias_vector", "broadcast_dimensions": ["N"]},
                    "wrapped": {"kind": "wrap", "depends_on": ["bias"], "data_type": "s32"},
                    "activated": {"kind": "relu", "depends_on": ["wrapped"]},
                },
                "post_output": "activated",
                "bias_conversion": "wrap_twos_complement_after_add",
                "result_data_type": "s32",
                "result_conversion": "wrap_twos_complement",
            },
            "lifecycle_policy": {
                "job_acceptance": "valid_ready_handshake",
                "job_overlap": "single_inflight",
                "busy_behavior": "tracks_active_job",
                "completion_style": "pulse",
                "completion_timing": "next_cycle_after_retirement",
                "illegal_command_behavior": "error_without_start",
                "error_style": "sticky_until_reset",
                "error_timing": "next_cycle_after_error_event",
                "reset_behavior": "abort_inflight",
            },
            "inputs": ["A_matrix", "B_matrix", "bias_vector"],
            "outputs": ["Y_matrix"],
        }],
        "data_types": [
            {"name": "s8", "width_bits": 8, "signed": True, "overflow_semantics": "not_applicable"},
            {"name": "s32", "width_bits": 32, "signed": True, "overflow_semantics": "wrap_two_complement"},
            {"name": "s16", "width_bits": 16, "signed": True, "overflow_semantics": "exact"},
        ],
        "data_objects": [
            {"name": "A_matrix", "role": "left_operand_matrix", "data_type": "s8", "dimensions": ["M", "K"]},
            {"name": "B_matrix", "role": "right_operand_matrix", "data_type": "s8", "dimensions": ["K", "N"]},
            {"name": "bias_vector", "role": "per_output_column_bias", "data_type": "s32", "dimensions": ["N"]},
            {"name": "Y_matrix", "role": "result_matrix", "data_type": "s32", "dimensions": ["M", "N"]},
        ],
        "dimensions": [
            {"name": "M", "minimum": 1, "maximum": 1, "bound_parameter": "M_DIM"},
            {"name": "N", "minimum": 1, "maximum": 1, "bound_parameter": "N_DIM"},
            {"name": "K", "minimum": 1, "maximum": 1, "bound_parameter": "K_DIM"},
        ],
        "parameters": [
            {"name": "M_DIM", "default_value": "1"},
            {"name": "N_DIM", "default_value": "1"},
            {"name": "K_DIM", "default_value": "1"},
        ],
    }
    for obj in architecture["data_objects"]:
        obj["serialization"] = {
            "kind": "dense_tensor", "index_order": list(obj["dimensions"]),
            "description": "One element per transfer, innermost declared axis varies fastest.",
        }
    channels = []
    signals = []
    for name, direction, obj, width, signed in (
        ("a", "input", "A_matrix", 8, True),
        ("b", "input", "B_matrix", 8, True),
        ("bias", "input", "bias_vector", 32, True),
        ("y", "output", "Y_matrix", 32, True),
    ):
        channels.append({
            "name": name, "direction": direction, "protocol_profile": "ready_valid",
            "data_objects": [obj], "ordering": "declared dimension order", "framing": "exact tensor",
        })
        signals.extend([
            {"name": f"{name}_valid", "channel": name, "role": "valid"},
            {"name": f"{name}_ready", "channel": name, "role": "ready"},
            {"name": f"{name}_payload", "channel": name, "role": "payload", "width": str(width), "signed": signed},
        ])
    return architecture, {"channels": channels, "signals": signals}


def axi_lite_contracts():
    architecture, _ = contracts()
    channels = [
        {
            "name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
            "data_objects": [], "ordering": "one command", "framing": "one beat",
        }
    ]
    signals = [
        {"name": "clk", "role": "clock", "direction": "input", "channel": None},
        {"name": "rst_n", "role": "reset", "direction": "input", "channel": None,
         "semantic": "synchronous active-low reset"},
        {"name": "cmd_valid", "role": "valid", "direction": "input", "channel": "cmd"},
        {"name": "cmd_ready", "role": "ready", "direction": "output", "channel": "cmd"},
        {"name": "opcode", "role": "payload", "semantic_class": "command",
         "direction": "input", "channel": "cmd", "width": "8", "semantic": "legal only 8'h01"},
    ]
    for signal, data_object in (
        ("left_ptr", "A_matrix"), ("right_ptr", "B_matrix"),
        ("bias_ptr", "bias_vector"), ("result_ptr", "Y_matrix"),
    ):
        signals.append({
            "name": signal, "role": "metadata", "semantic_class": "address",
            "direction": "input", "channel": "cmd", "width": "32",
            "semantic": (
                f"data_object={data_object} address_role=base byte_order=little "
                "address_sequence=contiguous word_stride_bytes=4"
            ),
        })

    def add_channel(name, kind, direction, objects, fields):
        channels.append({
            "name": name, "direction": direction, "protocol_profile": "axi4_lite",
            "data_objects": objects, "ordering": "in request order", "framing": "one beat",
            "metadata": [
                f"protocol_group=mem protocol_channel={kind} "
                "protocol_capability.max_outstanding=1 "
                "protocol_capability.read_write_concurrency=false "
                "protocol_capability.address_bins=zero|aligned|page_edge "
                "protocol_capability.write_strobe_bins=full "
                "protocol_capability.protection_bins=zero "
                "protocol_capability.write_order_bins=address_first|data_first|same_cycle"
            ],
        })
        prefix = name
        signals.extend([
            {"name": f"{prefix}_valid", "role": "valid", "direction": direction,
             "channel": name, "width": "1"},
            {"name": f"{prefix}_ready", "role": "ready",
             "direction": "input" if direction == "output" else "output",
             "channel": name, "width": "1"},
        ])
        for field, (role, semantic_class, width) in fields.items():
            signals.append({
                "name": f"{prefix}_{field}", "role": role,
                "semantic_class": semantic_class, "direction": direction,
                "channel": name, "width": str(width),
                "semantic": f"protocol_field={field}",
            })

    add_channel("aw", "write_address", "output", [], {
        "addr": ("payload", "address", 32), "prot": ("metadata", "protection", 3),
    })
    add_channel("w", "write_data", "output", ["Y_matrix"], {
        "data": ("payload", "data", 32), "strb": ("metadata", "byte_enable", 4),
    })
    add_channel("bresp", "write_response", "input", [], {
        "resp": ("payload", "response_code", 2),
    })
    add_channel("ar", "read_address", "output", [], {
        "addr": ("payload", "address", 32), "prot": ("metadata", "protection", 3),
    })
    add_channel("r", "read_data", "input", ["A_matrix", "B_matrix", "bias_vector"], {
        "data": ("payload", "data", 32), "resp": ("metadata", "response_code", 2),
    })
    signals.extend([
        {"name": "busy", "role": "busy", "direction": "output", "channel": None},
        {"name": "completion", "role": "completion", "direction": "output", "channel": None},
        {"name": "error", "role": "error", "direction": "output", "channel": None,
         "semantic": "sticky error until reset"},
    ])
    return architecture, {"clock": "clk", "reset": "rst_n", "channels": channels, "signals": signals}


def test_architect_metadata_compiles_role_bound_ready_valid_channels() -> None:
    architecture, interface = contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    operation = metadata["operations"][0]
    assert operation["dimensions"] == {"M": 1, "N": 1, "K": 1}
    assert operation["inputs"][0]["data_object"] == "A_matrix"
    assert operation["inputs"][0]["signals"] == {
        "valid": "a_valid", "ready": "a_ready", "payload": "a_payload"
    }
    assert operation["arithmetic"]["classifier_profile"] == "integer_matrix_multiply"
    assert {item["kind"] for item in operation["arithmetic"]["post_operations"].values()} == {
        "bias_add", "wrap", "relu"
    }
    assert operation["arithmetic"]["resolved_stage_order"] == ["bias", "wrapped", "activated"]


def test_axi_lite_adapter_reconstructs_objects_from_accepted_addresses() -> None:
    architecture, interface = axi_lite_contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    assert all("memory_mapping" in item for item in [*operation["inputs"], *operation["outputs"]])
    adapter = ReadyValidCaptureAdapter(interface)
    names = {str(item["name"]) for item in interface["signals"]}
    base = {name: 0 for name in names}

    sequence = 0
    def observe(**values):
        nonlocal sequence
        sequence += 1
        adapter.observe({**base, **values}, event_sequence=sequence, reset_epoch=1)

    observe(
        cmd_valid=1, cmd_ready=1, opcode=1,
        left_ptr=0x1000, right_ptr=0x2000, bias_ptr=0x3000, result_ptr=0x4000,
    )
    for address, data in ((0x1000, 2), (0x2000, 3), (0x3000, 4)):
        observe(ar_valid=1, ar_ready=1, ar_addr=address)
        observe(r_valid=1, r_ready=1, r_data=data, r_resp=0)
    observe(aw_valid=1, aw_ready=1, aw_addr=0x4000)
    observe(w_valid=1, w_ready=1, w_data=10, w_strb=0xF)
    observe(bresp_valid=1, bresp_ready=1, bresp_resp=0)

    assert adapter.consume_operation_inputs(operation) == {
        "A_matrix": [2], "B_matrix": [3], "bias_vector": [4]
    }
    assert adapter.consume_operation_outputs(operation) == {"Y_matrix": [10]}

    broken = ReadyValidCaptureAdapter(interface)
    broken.observe(
        {**base, "cmd_valid": 1, "cmd_ready": 1, "opcode": 1,
         "left_ptr": 0x1000, "right_ptr": 0x2000,
         "bias_ptr": 0x3000, "result_ptr": 0x4000}
    )
    broken.observe({**base, "ar_valid": 1, "ar_ready": 1, "ar_addr": 0x1004})
    broken.observe({**base, "r_valid": 1, "r_ready": 1, "r_data": 2, "r_resp": 0})
    with pytest.raises(ProtocolAdapterError, match="AXI read addresses differ"):
        broken.consume_operation_inputs(operation)


def test_axi_lite_memory_metadata_enables_the_code_owned_campaign() -> None:
    architecture, interface = axi_lite_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert automatic_campaign_support(metadata, architecture) == {
        "supported": True,
        "status": "supported",
        "reasons": [],
        "operations": {
            "gemm_core": {
                "supported": True,
                "reasons": [],
                "arithmetic_reasons": [],
                "protocol_lifecycle_supported": True,
            }
        },
        "any_operation_supported": True,
    }
    source = render_contract_generated_block(
        build_interface_coverage_plan(interface),
        architecture,
        include_automatic_campaign=True,
        randomized_transactions_minimum=100,
    )
    compile(source, "axi_lite_generated_contract_block.py", "exec")
    assert "'memory_mapping':" in source
    assert source.count("async def _contract_automatic_verification_campaign") == 1


def test_axi_lite_lifecycle_retires_on_bresp_and_accepts_sticky_defined_errors() -> None:
    architecture, interface = axi_lite_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_assertion_plan(
        build_interface_coverage_plan(interface), metadata
    )
    base = {str(item["name"]): 0 for item in interface["signals"]}
    base["rst_n"] = 1
    command = {
        "cmd_valid": 1, "cmd_ready": 1, "opcode": 1,
        "left_ptr": 0x1000, "right_ptr": 0x2000,
        "bias_ptr": 0x3000, "result_ptr": 0x4000,
    }

    state = {}
    check_lifecycle_assertions({**base, **command}, plan, state)
    check_lifecycle_assertions({**base, "busy": 1, "w_valid": 1, "w_ready": 1}, plan, state)
    check_lifecycle_assertions(
        {**base, "busy": 1, "bresp_valid": 1, "bresp_ready": 1, "bresp_resp": 0},
        plan,
        state,
    )
    check_lifecycle_assertions({**base, "completion": 1}, plan, state)
    check_lifecycle_assertions(base, plan, state)
    finalize_lifecycle_assertions(plan, state)

    state = {}
    check_lifecycle_assertions(
        {**base, **command, "left_ptr": 0x1001}, plan, state
    )
    check_lifecycle_assertions({**base, "error": 1}, plan, state)
    check_lifecycle_assertions({**base, "error": 1}, plan, state)
    check_lifecycle_assertions({**base, "rst_n": 0}, plan, state)
    finalize_lifecycle_assertions(plan, state)

    state = {}
    check_lifecycle_assertions({**base, **command}, plan, state)
    check_lifecycle_assertions(
        {**base, "busy": 1, "r_valid": 1, "r_ready": 1, "r_resp": 2},
        plan,
        state,
    )
    check_lifecycle_assertions({**base, "error": 1}, plan, state)
    check_lifecycle_assertions({**base, "rst_n": 0}, plan, state)
    finalize_lifecycle_assertions(plan, state)


def test_canonical_gemm_classifier_uses_complete_accepted_job() -> None:
    architecture, interface = contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    job = assemble_canonical_job(
        operation,
        {"A_matrix": [1], "B_matrix": [1], "bias_vector": [(1 << 31) - 1]},
        {"Y_matrix": [0]},
        {"Y_matrix": [0]},
    )
    assert job is not None
    evidence = classify_operation_job(job)
    assert evidence["accumulation"] == ["ordinary"]
    assert evidence["numeric_stage_events"][0]["bias_excursion"] is True
    assert "post_processing" not in evidence
    assert evidence["activation"] == ["negative"]


def test_integer_gemm_known_answers_cover_sign_wrap_bias_and_relu_order() -> None:
    architecture, interface = contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    cases = (
        ({"A_matrix": [-128], "B_matrix": [127], "bias_vector": [0]}, [0]),
        ({"A_matrix": [127], "B_matrix": [127], "bias_vector": [1]}, [16130]),
        (
            {
                "A_matrix": [1],
                "B_matrix": [1],
                "bias_vector": [(1 << 31) - 1],
            },
            [0],
        ),
    )
    for stimulus, expected in cases:
        assert evaluate_canonical_operation(operation, stimulus) == {
            "Y_matrix": expected
        }


def test_canonical_job_rejects_partial_tensor_instead_of_crediting_coverage() -> None:
    architecture, interface = contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    with pytest.raises(CanonicalOperationError, match="missing accepted input"):
        assemble_canonical_job(
            operation,
            {"A_matrix": [1]},
            {"Y_matrix": [1]},
            {"Y_matrix": [1]},
        )


def test_known_gemm_points_get_tool_sampling_without_tb_bindings() -> None:
    architecture, interface = contracts()
    specs = [{
        "operation_name": "gemm_core",
        "family": "matrix_multiply",
        "coverpoints": [
            {
                "id": concept,
                "concept": concept,
                "field": concept,
                "source": "baseline" if concept in architecture["operations"][0]["features"] else "architect_extension",
                "description": concept,
                "bins": [{"name": "draft", "intent": "draft", "predicate": {"op": "eq", "args": [0]}}],
            }
            for concept in ["dimensions", "operand_values", "accumulation", "bias", "activation"]
        ],
    }]
    plan = operation_plan_for_tests(specs, ["OPERATION_SAMPLING_BINDINGS = []\n"], architecture, interface)
    assert {item["bindings"]["sampling"]["template"] for item in plan["obligations"]} == {"canonical_job"}
    accumulation = next(item for item in plan["obligations"] if item["bindings"]["concept"] == "accumulation")
    assert [item["name"] for item in accumulation["bins"]] == [
        "ordinary", "positive_boundary", "negative_boundary",
        "positive_overflow", "negative_overflow",
    ]


def test_runtime_classifier_uses_role_bound_accepted_payloads() -> None:
    architecture, interface = contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    tracker = InterfaceCoverageTracker({
        "interface_contract": interface,
        "monitor": {},
        "obligations": [],
    })
    snapshot = {
        "a_valid": 1, "a_ready": 1, "a_payload": 0xFF,
        "b_valid": 1, "b_ready": 1, "b_payload": 1,
        "bias_valid": 1, "bias_ready": 1, "bias_payload": (1 << 31) - 1,
        "y_valid": 0, "y_ready": 1, "y_payload": 0,
    }
    tracker.protocol_adapter.observe(snapshot)
    tracker.protocol_adapter.observe(
        {
            **{name: 0 for name in snapshot},
            "y_valid": 1,
            "y_ready": 1,
            "y_payload": (1 << 31) - 2,
        }
    )
    tracker.record_stimulus(
        "directed",
        {"A_matrix": [-1], "B_matrix": [1], "bias_vector": [(1 << 31) - 1]},
        {"Y_matrix": [(1 << 31) - 2]},
        operation_metadata=metadata,
        operations=("gemm_core",),
        observed={"Y_matrix": [(1 << 31) - 2]},
    )
    record = tracker.stimulus_records[0]
    assert record["accepted_channel_payloads"]["a"] == [-1]
    assert record["operation_evidence"]["gemm_core"]["accumulation"] == ["ordinary"]


def test_all_known_sampling_bindings_are_deterministically_erased() -> None:
    source = "OPERATION_SAMPLING_BINDINGS = {'malformed': 'llm output'}\n"
    assert normalize_operation_sampling_bindings(
        source,
        code_owned_ids={"operation.gemm_core.accumulation"},
        all_points_code_owned=True,
    ) == "OPERATION_SAMPLING_BINDINGS = []\n"


def test_tool_generates_and_reclassifies_every_known_gemm_bin() -> None:
    architecture, interface = contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    suite = generate_canonical_stimulus_suite(
        operation, randomized_count=3, seed=17
    )
    expected_targets = {
        (concept, str(bin_spec["name"]))
        for concept in (
            "dimensions", "operand_values", "accumulation",
            "bias", "activation",
        )
        for bin_spec in reachable_canonical_bins_for_concept(operation, concept) or []
    }
    assert {
        (item["target"]["concept"], item["target"]["bin"])
        for item in suite["directed"]
    } == expected_targets
    assert {
        (item["concept"], item["bin_name"], item["code"])
        for item in suite["exceptions"]
    } == {
        ("accumulation", "positive_boundary", "unreachable"),
        ("accumulation", "negative_boundary", "unreachable"),
        ("accumulation", "positive_overflow", "unreachable"),
        ("accumulation", "negative_overflow", "unreachable"),
    }
    assert len(suite["randomized"]) == 3
    for item in [*suite["directed"], *suite["randomized"]]:
        assert item["expected"] == evaluate_canonical_operation(
            operation, item["stimulus"]
        )


def test_numeric_directed_witnesses_are_observable_at_the_result() -> None:
    architecture, interface = contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]

    for bin_name in ("positive", "negative", "minimum", "maximum"):
        case = generate_canonical_stimulus_for_bin(
            operation, "operand_values", bin_name
        )
        assert any(case["expected"]["Y_matrix"]), bin_name

    for concept, bin_name in (
        ("accumulation", "ordinary"),
        ("activation", "positive_region"),
    ):
        case = generate_canonical_stimulus_for_bin(operation, concept, bin_name)
        assert any(case["expected"]["Y_matrix"]), (concept, bin_name)


def test_generator_is_shape_parameterized_not_fixed_to_current_gemm() -> None:
    architecture, interface = contracts()
    dimensions = {"M": 2, "N": 3, "K": 4}
    for dimension in architecture["dimensions"]:
        value = dimensions[dimension["name"]]
        dimension["minimum"] = value
        dimension["maximum"] = value
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    case = generate_canonical_stimulus_for_bin(
        operation, "activation", "negative_region"
    )
    assert len(case["stimulus"]["A_matrix"]) == 8
    assert len(case["stimulus"]["B_matrix"]) == 12
    assert len(case["stimulus"]["bias_vector"]) == 3
    assert len(case["expected"]["Y_matrix"]) == 6
    assert "negative" in case["evidence"]["activation"]


def test_impossible_accumulator_bins_are_explicit_and_removed_from_plan() -> None:
    architecture, interface = contracts()
    operation = deepcopy(
        build_architect_operation_metadata(architecture, interface)["operations"][0]
    )
    operation["inputs"] = [
        item for item in operation["inputs"]
        if item["object_role"] != "per_output_column_bias"
    ]
    operation["arithmetic"]["post_operations"] = {
        "wrapped": {"kind": "wrap", "depends_on": ["accumulator"], "data_type": "s32"}
    }
    operation["arithmetic"]["resolved_stage_order"] = ["wrapped"]
    with pytest.raises(CanonicalStimulusGenerationError) as failure:
        generate_canonical_stimulus_for_bin(
            operation, "accumulation", "positive_overflow"
        )
    assert failure.value.code == "unreachable"
    assert [
        item["name"]
        for item in reachable_canonical_bins_for_concept(
            operation, "accumulation"
        ) or []
    ] == ["ordinary"]


def test_accumulation_bins_describe_range_events_not_overflow_policy() -> None:
    architecture, interface = contracts()
    declaration = architecture["operations"][0]
    declaration["inputs"].remove("bias_vector")
    declaration["feature_extensions"] = []
    declaration["arithmetic"].update({
        "accumulator_data_type": "s8",
        "reduction_conversion": "wrap_twos_complement_after_each_add",
        "post_operations": {"wrapped": {"kind": "wrap", "depends_on": ["accumulator"], "data_type": "s8"}},
        "post_output": "wrapped",
        "bias_conversion": "exact",
    })
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    names = [
        item["name"]
        for item in reachable_canonical_bins_for_concept(operation, "accumulation") or []
    ]
    assert names == [
        "ordinary", "positive_boundary", "negative_boundary",
        "positive_overflow", "negative_overflow",
    ]
    assert "wrap" not in names
    for name in names:
        case = generate_canonical_stimulus_for_bin(operation, "accumulation", name)
        assert name in case["evidence"]["accumulation"]


def test_generator_reports_metadata_and_extension_failures_separately() -> None:
    architecture, interface = contracts()
    operation = deepcopy(
        build_architect_operation_metadata(architecture, interface)["operations"][0]
    )
    operation["dimensions"]["K"] = None
    with pytest.raises(CanonicalStimulusGenerationError) as missing:
        generate_random_canonical_stimuli(operation, 1)
    assert missing.value.code == "metadata_missing"

    operation = deepcopy(
        build_architect_operation_metadata(architecture, interface)["operations"][0]
    )
    operation["arithmetic"]["classifier_profile"] = "llm_extension"
    with pytest.raises(CanonicalStimulusGenerationError) as extension:
        generate_random_canonical_stimuli(operation, 1)
    assert extension.value.code == "llm_extension_required"


def test_bias_bins_use_the_bias_dtype_not_accumulator_dtype() -> None:
    architecture, interface = contracts()
    operation = deepcopy(
        build_architect_operation_metadata(architecture, interface)["operations"][0]
    )
    bias = next(
        item for item in operation["inputs"]
        if item["object_role"] == "per_output_column_bias"
    )
    bias["data_type"] = {"name": "s8", "width_bits": 8, "signed": True}
    bins = canonical_bins_for_concept(operation, "bias") or []
    by_name = {item["name"]: item for item in bins}
    assert by_name["minimum_bias"]["predicate"]["args"] == [-128]
    assert by_name["maximum_bias"]["predicate"]["args"] == [127]
    case = generate_canonical_stimulus_for_bin(
        operation, "bias", "minimum_bias"
    )
    assert case["stimulus"]["bias_vector"][0] == -128


def test_generated_tb_block_exposes_code_owned_operation_vector_helpers() -> None:
    architecture, interface = contracts()
    namespace: dict = {}
    exec(
        render_contract_generated_block(
            build_interface_coverage_plan(interface), architecture
        ),
        namespace,
    )
    case = namespace["_contract_generate_operation_stimulus"](
        "gemm_core", "activation", "negative_region"
    )
    random_cases = namespace["_contract_generate_random_operation_stimuli"](
        "gemm_core", 2, seed=9
    )
    assert "negative" in case["evidence"]["activation"]
    assert len(random_cases) == 2
