from __future__ import annotations

import pytest

from multigent.verifier_tool import (
    CanonicalStimulusGenerationError,
    build_architect_operation_metadata,
    build_operation_feature_plan,
    canonical_bin_dispositions,
    canonical_bins_for_concept,
    classify_operation_job,
    evaluate_canonical_operation,
    generate_canonical_stimulus_suite,
    operation_plan_for_tests,
    reachable_canonical_bins_for_concept,
    validate_architecture_operation_features,
)
from multigent.verifier_tool.operation.assertion.catalog import (
    load_operation_assertion_catalog,
)
from multigent.verifier_tool.pool.operation_metadata import assemble_canonical_job


def sparse_attention_contracts():
    dimensions = {"Q": 2, "S": 3, "D": 2, "DV": 2}
    architecture = {
        "operations": [
            {
                "name": "sparse_attention_core",
                "kind": "sparse_attention",
                "coverage_family": "sparse_attention",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "operand_values",
                    "sparsity_patterns",
                    "attention_scores",
                    "stage_handoffs",
                    "output_values",
                ],
                "feature_extensions": [],
                "semantics": (
                    "Exact integer unnormalized sparse attention: score=Q*K^T; "
                    "binary mask removes inactive keys; Y=sum(score*V)."
                ),
                "arithmetic": {
                    "classifier_profile": "integer_sparse_attention",
                    "score_product_data_type": "s16",
                    "score_accumulator_data_type": "s32",
                    "score_accumulator_initialization": 0,
                    "score_reduction_dimensions": ["D"],
                    "score_reduction_order": "increasing_declared_reduction_coordinate",
                    "score_reduction_conversion": "exact",
                    "scaling": "none",
                    "mask_mode": "binary_keep",
                    "normalization": "none",
                    "output_product_data_type": "s32",
                    "output_accumulator_data_type": "s32",
                    "output_accumulator_initialization": 0,
                    "output_reduction_dimensions": ["S"],
                    "output_reduction_order": "increasing_declared_reduction_coordinate",
                    "output_reduction_conversion": "exact",
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
                    "error_style": "sticky_until_reset",
                    "error_timing": "next_cycle_after_error_event",
                    "reset_behavior": "abort_inflight",
                },
                "inputs": ["Q_matrix", "K_matrix", "V_matrix", "sparse_mask"],
                "outputs": ["Y_matrix"],
            }
        ],
        "data_types": [
            {"name": "s8", "width_bits": 8, "signed": True},
            {"name": "u1", "width_bits": 1, "signed": False},
            {"name": "s16", "width_bits": 16, "signed": True},
            {"name": "s32", "width_bits": 32, "signed": True},
        ],
        "data_objects": [
            {"name": "Q_matrix", "role": "query_matrix", "data_type": "s8", "dimensions": ["Q", "D"]},
            {"name": "K_matrix", "role": "key_matrix", "data_type": "s8", "dimensions": ["S", "D"]},
            {"name": "V_matrix", "role": "value_matrix", "data_type": "s8", "dimensions": ["S", "DV"]},
            {"name": "sparse_mask", "role": "attention_mask", "data_type": "u1", "dimensions": ["Q", "S"]},
            {"name": "Y_matrix", "role": "attention_result", "data_type": "s32", "dimensions": ["Q", "DV"]},
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
    widths = {"Q_matrix": 8, "K_matrix": 8, "V_matrix": 8, "sparse_mask": 1, "Y_matrix": 32}
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        direction = "output" if obj["name"] == "Y_matrix" else "input"
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
                    "signed": obj["data_type"] != "u1",
                },
            ]
        )
    return architecture, {"channels": channels, "signals": signals}


def compiled_sparse_attention():
    architecture, interface = sparse_attention_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    return architecture, interface, metadata["operations"][0]


def test_sparse_attention_catalog_contract_and_assertions_are_code_owned():
    architecture, _, operation = compiled_sparse_attention()
    assert validate_architecture_operation_features(architecture) == []
    assert operation["arithmetic"]["support_status"] == (
        "supported_composed_restricted_integer_sparse_attention"
    )
    feature_plan = build_operation_feature_plan(architecture)
    assert {item["bindings"]["concept"] for item in feature_plan["features"]} == {
        "dimensions",
        "operand_values",
        "sparsity_patterns",
        "attention_scores",
        "stage_handoffs",
        "output_values",
    }
    assertions = load_operation_assertion_catalog()["families"]["sparse_attention"]
    assert "masked_key_isolation" in assertions["required_properties"]
    assert "binary_mask_legality" in assertions["required_properties"]
    assert "composed_stage_equivalence" in assertions["required_properties"]
    assert operation["arithmetic"]["composition"] == [
        {"stage": "qk_score", "profile": "integer_qk_score", "mode": "raw_qk_transpose"},
        {"stage": "scale", "profile": "attention_scale", "mode": "none"},
        {"stage": "mask", "profile": "attention_mask", "mode": "binary_keep"},
        {"stage": "normalization", "profile": "attention_normalization", "mode": "none"},
        {"stage": "value_reduction", "profile": "attention_value", "mode": "integer_weighted_sum"},
    ]


def test_sparse_attention_known_answer_and_trace_classification():
    _, _, operation = compiled_sparse_attention()
    stimulus = {
        "Q_matrix": [1, 0, 0, 1],
        "K_matrix": [1, 0, 0, 1, 1, 1],
        "V_matrix": [2, 3, 4, 5, 6, 7],
        "sparse_mask": [1, 0, 0, 0, 1, 1],
    }
    expected = {"Y_matrix": [2, 3, 10, 12]}
    assert evaluate_canonical_operation(operation, stimulus) == expected
    job = assemble_canonical_job(operation, stimulus, expected, expected)
    assert job is not None
    evidence = classify_operation_job(job)
    assert evidence["sparsity_patterns"] == ["singleton_row", "partial_row"]
    assert "positive_score" in evidence["attention_scores"]
    assert evidence["output_values"] == [
        "positive_output",
        "positive_output",
        "positive_output",
        "positive_output",
    ]
    assert len(evidence["numeric_stage_events"]) == 4
    assert set(evidence["stage_handoffs"]) == {
        "qk_to_scale_forwarded",
        "active_mask_preserved",
        "inactive_mask_zeroed",
        "normalization_bypass_forwarded",
        "value_reduction_consumed",
    }
    trace = evidence["numeric_stage_events"][0]["stage_trace"]
    assert list(trace) == [
        "qk_score",
        "scale",
        "mask",
        "normalization",
        "value_reduction",
    ]
    assert trace["qk_score"][0]["result_value"] == 1
    assert trace["scale"] == [1, 0, 1]
    assert trace["mask"] == [1, 0, 0]
    assert trace["normalization"] == [1, 0, 0]


def test_sparse_attention_generates_and_reclassifies_every_reachable_bin():
    _, _, operation = compiled_sparse_attention()
    suite = generate_canonical_stimulus_suite(operation, randomized_count=2, seed=9)
    expected_targets = {
        (concept, str(bin_spec["name"]))
        for concept in (
            "dimensions",
            "operand_values",
            "sparsity_patterns",
            "attention_scores",
            "stage_handoffs",
            "output_values",
        )
        for bin_spec in reachable_canonical_bins_for_concept(operation, concept) or []
    }
    actual_targets = {
        (item["target"]["concept"], item["target"]["bin"])
        for item in suite["directed"]
    }
    assert actual_targets == expected_targets
    assert suite["exceptions"] == []
    assert len(suite["randomized"]) == 2
    assert {
        item.get("solver_origin") for item in suite["directed"]
    } == {"code_owned_predicate_over_symbolic_sparse_attention_trace"}
    for case in [*suite["directed"], *suite["qualification"], *suite["randomized"]]:
        assert case["expected"] == evaluate_canonical_operation(
            operation, case["stimulus"]
        )


def test_sparse_attention_rejects_softmax_guess_and_nonbinary_mask():
    architecture, interface = sparse_attention_contracts()
    architecture["operations"][0]["arithmetic"]["normalization"] = "softmax"
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["operations"] == []
    assert "normalization" in metadata["unrepresentable_operations"][0]["reason"]

    _, _, operation = compiled_sparse_attention()
    with pytest.raises(
        CanonicalStimulusGenerationError, match="mask accepts only 0 and 1"
    ):
        evaluate_canonical_operation(
            operation,
            {
                "Q_matrix": [0] * 4,
                "K_matrix": [0] * 6,
                "V_matrix": [0] * 6,
                "sparse_mask": [2, 0, 0, 0, 0, 0],
            },
        )


def test_sparse_attention_catalog_bins_are_stable():
    _, _, operation = compiled_sparse_attention()
    assert [
        item["name"]
        for item in canonical_bins_for_concept(operation, "sparsity_patterns") or []
    ] == ["empty_row", "singleton_row", "partial_row", "dense_row"]
    assert [
        item["name"]
        for item in canonical_bins_for_concept(operation, "attention_scores") or []
    ] == ["zero_score", "positive_score", "negative_score"]
    assert [
        item["name"]
        for item in canonical_bins_for_concept(operation, "stage_handoffs") or []
    ] == [
        "qk_to_scale_forwarded",
        "active_mask_preserved",
        "inactive_mask_zeroed",
        "normalization_bypass_forwarded",
        "value_reduction_consumed",
    ]
    assert [
        item["name"]
        for item in canonical_bins_for_concept(operation, "output_values") or []
    ] == ["zero_output", "positive_output", "negative_output"]


def test_sparse_attention_solver_proves_shape_dependent_bin_unreachable():
    architecture, interface = sparse_attention_contracts()
    sequence = next(item for item in architecture["dimensions"] if item["name"] == "S")
    sequence["minimum"] = 2
    sequence["maximum"] = 2
    parameter = next(item for item in architecture["parameters"] if item["name"] == "S_DIM")
    parameter["default_value"] = "2"
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    dispositions = canonical_bin_dispositions(operation, "sparsity_patterns")
    assert dispositions is not None
    partial = next(item for item in dispositions if item["bin"]["name"] == "partial_row")
    assert partial["status"] == "proven_unreachable"
    assert partial["witness"] is None
    assert "Z3 proved" in partial["reason"]


def test_sparse_attention_coverage_plan_replaces_llm_drafts_with_canonical_bins():
    architecture, interface = sparse_attention_contracts()
    concepts = [
        "dimensions",
        "operand_values",
        "sparsity_patterns",
        "attention_scores",
        "stage_handoffs",
        "output_values",
    ]
    specs = [
        {
            "operation_name": "sparse_attention_core",
            "family": "sparse_attention",
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
    sparsity = next(
        item
        for item in plan["obligations"]
        if item["bindings"]["concept"] == "sparsity_patterns"
    )
    assert [item["name"] for item in sparsity["bins"]] == [
        "empty_row",
        "singleton_row",
        "partial_row",
        "dense_row",
    ]
