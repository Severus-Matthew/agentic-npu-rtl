from __future__ import annotations

from copy import deepcopy

from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_operation_feature_plan,
    canonical_bins_for_concept,
    classify_operation_job,
    evaluate_canonical_operation,
    generate_canonical_stimulus_suite,
    known_operation_features,
    operation_plan_for_tests,
    reachable_canonical_bins_for_concept,
    render_operation_assertion_lines,
    validate_architecture_operation_features,
)
from multigent.verifier_tool.operation.assertion.catalog import (
    load_operation_assertion_catalog,
)
from multigent.verifier_tool.pool.operation_metadata import assemble_canonical_job


def qk_score_contracts():
    dimensions = {"Q": 2, "S": 3, "D": 2}
    architecture = {
        "operations": [
            {
                "name": "qk_score_core",
                "kind": "qk_score",
                "coverage_family": "attention_qk",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "operand_values",
                    "accumulation",
                    "attention_scores",
                ],
                "feature_extensions": [],
                "semantics": "Raw exact integer score=Q*K^T with no scaling, mask, softmax, or V.",
                "arithmetic": {
                    "classifier_profile": "integer_qk_score",
                    "score_product_data_type": "s16",
                    "score_accumulator_data_type": "s8",
                    "score_accumulator_initialization": 0,
                    "score_reduction_dimensions": ["D"],
                    "score_reduction_order": "increasing_declared_reduction_coordinate",
                    "score_reduction_conversion": "exact",
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
                    "error_style": "sticky_until_reset",
                    "error_timing": "next_cycle_after_error_event",
                    "reset_behavior": "abort_inflight",
                },
                "inputs": ["Q_matrix", "K_matrix"],
                "outputs": ["score_matrix"],
            }
        ],
        "data_types": [
            {"name": "s8", "width_bits": 8, "signed": True},
            {"name": "s16", "width_bits": 16, "signed": True},
        ],
        "data_objects": [
            {
                "name": "Q_matrix",
                "role": "query_matrix",
                "data_type": "s8",
                "dimensions": ["Q", "D"],
            },
            {
                "name": "K_matrix",
                "role": "key_matrix",
                "data_type": "s8",
                "dimensions": ["S", "D"],
            },
            {
                "name": "score_matrix",
                "role": "attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
            },
        ],
        "dimensions": [
            {
                "name": name,
                "minimum": extent,
                "maximum": extent,
                "bound_parameter": f"{name}_DIM",
            }
            for name, extent in dimensions.items()
        ],
        "parameters": [
            {"name": f"{name}_DIM", "default_value": str(extent)}
            for name, extent in dimensions.items()
        ],
    }
    for obj in architecture["data_objects"]:
        obj["serialization"] = {
            "kind": "dense_tensor",
            "index_order": list(obj["dimensions"]),
            "description": "One element per transfer; innermost axis varies fastest.",
        }
    channels = []
    signals = []
    widths = {"Q_matrix": 8, "K_matrix": 8, "score_matrix": 16}
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        direction = "output" if obj["name"] == "score_matrix" else "input"
        channels.append(
            {
                "name": channel,
                "direction": direction,
                "protocol_profile": "ready_valid",
                "data_objects": [obj["name"]],
                "ordering": "declared dimension order",
                "framing": "exact tensor",
            }
        )
        signals.extend(
            [
                {"name": f"{channel}_valid", "channel": channel, "role": "valid"},
                {"name": f"{channel}_ready", "channel": channel, "role": "ready"},
                {
                    "name": f"{channel}_payload",
                    "channel": channel,
                    "role": "payload",
                    "width": str(widths[obj["name"]]),
                    "signed": True,
                },
            ]
        )
    return architecture, {"channels": channels, "signals": signals}


def compiled_qk_score():
    architecture, interface = qk_score_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    return architecture, interface, metadata["operations"][0]


def test_qk_score_is_an_independent_code_owned_stage():
    architecture, _, operation = compiled_qk_score()
    assert validate_architecture_operation_features(architecture) == []
    assert operation["arithmetic"]["support_status"] == "supported_integer_qk_score"
    assert {item["object_role"] for item in operation["inputs"]} == {
        "query_matrix",
        "key_matrix",
    }
    assert [item["object_role"] for item in operation["outputs"]] == [
        "attention_score_matrix"
    ]
    assert "normalization" not in operation["arithmetic"]
    assert "mask_mode" not in operation["arithmetic"]
    feature_plan = build_operation_feature_plan(architecture)
    assert {item["bindings"]["concept"] for item in feature_plan["features"]} == {
        "dimensions",
        "operand_values",
        "accumulation",
        "attention_scores",
    }
    assertions = load_operation_assertion_catalog()["families"]["attention_qk"]
    assert "score_coordinate_order" in assertions["required_properties"]
    assert set(assertions["feature_checks"]) == {
        "dimensions",
        "operand_values",
        "accumulation",
        "attention_scores",
    }


def test_qk_score_assertion_generation_uses_one_oracle_and_feature_evidence():
    architecture, _ = qk_score_contracts()
    features = known_operation_features(architecture)
    assert set(features["qk_score_core"]) == {
        "operation.qk_score_core.dimensions",
        "operation.qk_score_core.operand_values",
        "operation.qk_score_core.accumulation",
        "operation.qk_score_core.attention_scores",
    }
    rendered = "\n".join(render_operation_assertion_lines(features))
    assert rendered.count("assert observed_value == expected_value") == 1
    assert "OPERATION ASSERTION [central_golden_equivalence]" in rendered
    for feature in features["qk_score_core"]:
        assert f"OPERATION ASSERTION [{feature}]" in rendered


def test_qk_score_known_answer_is_row_major_q_times_k_transpose():
    _, _, operation = compiled_qk_score()
    stimulus = {
        "Q_matrix": [1, 2, -1, 3],
        "K_matrix": [3, 7, 5, -2, -4, 1],
    }
    expected = {"score_matrix": [17, 1, -2, 18, -11, 7]}
    assert evaluate_canonical_operation(operation, stimulus) == expected
    job = assemble_canonical_job(operation, stimulus, expected, expected)
    assert job is not None
    evidence = classify_operation_job(job)
    assert set(evidence["attention_scores"]) == {
        "negative_score",
        "positive_score",
    }
    assert len(evidence["numeric_stage_events"]) == 6


def test_qk_score_generates_every_reachable_bin_and_discriminating_case():
    _, _, operation = compiled_qk_score()
    suite = generate_canonical_stimulus_suite(operation, randomized_count=3, seed=13)
    expected_targets = {
        (concept, str(bin_spec["name"]))
        for concept in (
            "dimensions",
            "operand_values",
            "accumulation",
            "attention_scores",
        )
        for bin_spec in reachable_canonical_bins_for_concept(operation, concept) or []
    }
    assert {
        (item["target"]["concept"], item["target"]["bin"])
        for item in suite["directed"]
    } == expected_targets
    assert suite["exceptions"] == []
    assert len(suite["randomized"]) == 3
    assert {
        item.get("solver_origin") for item in suite["directed"]
    } == {"code_owned_predicate_over_symbolic_qk_score_trace"}
    assert {
        item["label"] for item in suite["qualification"]
    } >= {
        "canonical_qk_one_hot_coordinate",
        "canonical_qk_asymmetric",
        "canonical_qk_exact_cancellation",
        "canonical_qk_zero_after_nonzero",
    }
    for case in [*suite["directed"], *suite["qualification"], *suite["randomized"]]:
        assert case["expected"] == evaluate_canonical_operation(
            operation, case["stimulus"]
        )


def test_qk_score_wrapping_accumulator_generates_both_signed_extremes():
    architecture, interface = qk_score_contracts()
    for dimension in architecture["dimensions"]:
        dimension["minimum"] = dimension["maximum"] = 4
    for parameter in architecture["parameters"]:
        parameter["default_value"] = "4"
    arithmetic = architecture["operations"][0]["arithmetic"]
    arithmetic["score_accumulator_data_type"] = "s16"
    arithmetic["score_reduction_conversion"] = (
        "wrap_twos_complement_after_each_add"
    )
    arithmetic["result_data_type"] = "s16"
    arithmetic["result_conversion"] = "exact"

    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    suite = generate_canonical_stimulus_suite(
        metadata["operations"][0], randomized_count=0, seed=0x514B
    )

    assert suite["exceptions"] == []
    assert {
        (case["target"]["concept"], case["target"]["bin"])
        for case in suite["directed"]
    } >= {
        ("accumulation", "negative_boundary"),
        ("accumulation", "negative_overflow"),
        ("accumulation", "positive_boundary"),
        ("accumulation", "positive_overflow"),
    }


def test_qk_score_catalog_bins_are_stage_specific():
    _, _, operation = compiled_qk_score()
    assert [
        item["name"]
        for item in canonical_bins_for_concept(operation, "attention_scores") or []
    ] == ["zero_score", "positive_score", "negative_score"]
    assert canonical_bins_for_concept(operation, "sparsity_patterns") is None
    assert canonical_bins_for_concept(operation, "output_values") is None


def test_qk_score_coverage_plan_is_code_owned_and_all_bins_are_reachable():
    architecture, interface = qk_score_contracts()
    concepts = [
        "dimensions",
        "operand_values",
        "accumulation",
        "attention_scores",
    ]
    specs = [
        {
            "operation_name": "qk_score_core",
            "family": "attention_qk",
            "coverpoints": [
                {
                    "id": concept,
                    "concept": concept,
                    "field": concept,
                    "source": "baseline",
                    "description": concept,
                    "bins": [
                        {
                            "name": "draft",
                            "intent": "Verifier draft replaced by code-owned bins.",
                            "predicate": {"op": "eq", "args": [0]},
                        }
                    ],
                }
                for concept in concepts
            ],
        }
    ]
    plan = operation_plan_for_tests(
        specs,
        ["OPERATION_SAMPLING_BINDINGS = []\n"],
        architecture,
        interface,
    )
    assert {
        item["bindings"]["concept"] for item in plan["obligations"]
    } == set(concepts)
    assert {
        item["bindings"]["sampling"]["template"]
        for item in plan["obligations"]
    } == {"canonical_job"}
    bins = {
        item["bindings"]["concept"]: [entry["name"] for entry in item["bins"]]
        for item in plan["obligations"]
    }
    assert bins == {
        "dimensions": ["fixed_shape"],
        "operand_values": ["zero", "positive", "negative", "minimum", "maximum"],
        "accumulation": [
            "ordinary",
            "positive_boundary",
            "negative_boundary",
            "positive_overflow",
            "negative_overflow",
        ],
        "attention_scores": ["zero_score", "positive_score", "negative_score"],
    }
    assert sum(len(item["bins"]) for item in plan["obligations"]) == 14
    assert all(
        entry["required"]
        and entry["minimum_hits"] == 1
        and entry["applicability"]["status"] == "required_reachable"
        and entry["applicability"]["witness"] is not None
        for item in plan["obligations"]
        for entry in item["bins"]
    )


def test_qk_score_rejects_runtime_shape_and_extra_mask_input():
    architecture, interface = qk_score_contracts()
    runtime = deepcopy(architecture)
    runtime["dimensions"][0]["runtime_configurable"] = True
    metadata = build_architect_operation_metadata(runtime, interface)
    assert metadata["operations"] == []
    assert "runtime-configurable QK shapes" in metadata["unrepresentable_operations"][0]["reason"]

    extra = deepcopy(architecture)
    extra["data_types"].append({"name": "u1", "width_bits": 1, "signed": False})
    extra["data_objects"].append(
        {
            "name": "mask",
            "role": "attention_mask",
            "data_type": "u1",
            "dimensions": ["Q", "S"],
            "serialization": {
                "kind": "dense_tensor",
                "index_order": ["Q", "S"],
                "description": "One element per transfer.",
            },
        }
    )
    extra["operations"][0]["inputs"].append("mask")
    extra_interface = deepcopy(interface)
    extra_interface["channels"].append(
        {
            "name": "tensor_3",
            "direction": "input",
            "protocol_profile": "ready_valid",
            "data_objects": ["mask"],
            "ordering": "declared dimension order",
            "framing": "exact tensor",
        }
    )
    extra_interface["signals"].extend(
        [
            {"name": "tensor_3_valid", "channel": "tensor_3", "role": "valid"},
            {"name": "tensor_3_ready", "channel": "tensor_3", "role": "ready"},
            {
                "name": "tensor_3_payload",
                "channel": "tensor_3",
                "role": "payload",
                "width": "1",
                "signed": False,
            },
        ]
    )
    assert "unmodeled input/output" in build_architect_operation_metadata(
        extra, extra_interface
    )["unrepresentable_operations"][0]["reason"]
