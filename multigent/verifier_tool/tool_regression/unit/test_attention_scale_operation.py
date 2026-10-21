from __future__ import annotations

from copy import deepcopy

from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_operation_feature_plan,
    canonical_bins_for_concept,
    classify_operation_job,
    evaluate_canonical_operation,
    generate_canonical_stimulus_suite,
    reachable_canonical_bins_for_concept,
    validate_architecture_operation_features,
)
from multigent.verifier_tool.operation.assertion.catalog import (
    load_operation_assertion_catalog,
)
from multigent.verifier_tool.pool.operation_metadata import assemble_canonical_job


def attention_scale_contracts():
    dimensions = {"Q": 2, "S": 3, "D": 64}
    architecture = {
        "operations": [
            {
                "name": "attention_scale_core",
                "kind": "attention_scale",
                "coverage_family": "attention_scale",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "score_values",
                    "rounding",
                    "scaled_values",
                    "attenuation",
                ],
                "feature_extensions": [],
                "semantics": (
                    "signed scaled_score=floor(score*32/256), where 32 is "
                    "round(256/sqrt(64)); no mask or softmax is included"
                ),
                "arithmetic": {
                    "classifier_profile": "fixed_point_attention_scale",
                    "head_dimension": "D",
                    "coefficient_derivation": "round_inverse_sqrt",
                    "scale_multiplier": 32,
                    "scale_shift": 8,
                    "rounding": "arithmetic_floor",
                    "product_data_type": "s32",
                    "result_data_type": "s16",
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
                "inputs": ["score_matrix"],
                "outputs": ["scaled_score_matrix"],
            }
        ],
        "data_types": [
            {"name": "s16", "width_bits": 16, "signed": True},
            {"name": "s32", "width_bits": 32, "signed": True},
        ],
        "data_objects": [
            {
                "name": "score_matrix",
                "role": "attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
            },
            {
                "name": "scaled_score_matrix",
                "role": "scaled_attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
            },
        ],
        "dimensions": [
            {
                "name": name,
                "minimum": extent,
                "maximum": extent,
                "runtime_configurable": False,
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
            "description": "One signed score per transfer in row-major order.",
        }
    channels = []
    signals = []
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        direction = "output" if index else "input"
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
                    "width": "16",
                    "signed": True,
                },
            ]
        )
    return architecture, {"channels": channels, "signals": signals}


def compiled_attention_scale():
    architecture, interface = attention_scale_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    return architecture, interface, metadata["operations"][0]


def test_attention_scale_is_independent_and_code_owned():
    architecture, _, operation = compiled_attention_scale()
    assert validate_architecture_operation_features(architecture) == []
    assert operation["arithmetic"]["support_status"] == (
        "supported_fixed_point_attention_scale"
    )
    assert operation["arithmetic"]["head_dimension_value"] == 64
    assert [item["object_role"] for item in operation["inputs"]] == [
        "attention_score_matrix"
    ]
    assert [item["object_role"] for item in operation["outputs"]] == [
        "scaled_attention_score_matrix"
    ]
    assert "mask_mode" not in operation["arithmetic"]
    assert "normalization" not in operation["arithmetic"]
    plan = build_operation_feature_plan(architecture)
    assert {item["bindings"]["concept"] for item in plan["features"]} == {
        "dimensions",
        "score_values",
        "rounding",
        "scaled_values",
        "attenuation",
    }
    assertions = load_operation_assertion_catalog()["families"]["attention_scale"]
    assert "coefficient_derivation" in assertions["required_properties"]
    assert "output_stability_under_backpressure" in assertions["required_properties"]


def test_attention_scale_signed_known_answer_and_floor_rounding():
    _, _, operation = compiled_attention_scale()
    stimulus = {"score_matrix": [-32768, -9, -8, -1, 0, 32767]}
    expected = {
        "scaled_score_matrix": [-4096, -2, -1, -1, 0, 4095]
    }
    assert evaluate_canonical_operation(operation, stimulus) == expected
    job = assemble_canonical_job(operation, stimulus, expected, expected)
    assert job is not None
    evidence = classify_operation_job(job)
    assert set(evidence["rounding"]) == {
        "exact",
        "positive_fraction_discarded",
        "negative_fraction_discarded",
    }
    assert set(evidence["scaled_values"]) == {
        "zero_scaled",
        "positive_scaled",
        "negative_scaled",
    }


def test_attention_scale_generates_all_fourteen_bins_and_qualification_cases():
    _, _, operation = compiled_attention_scale()
    concepts = (
        "dimensions",
        "score_values",
        "rounding",
        "scaled_values",
        "attenuation",
    )
    suite = generate_canonical_stimulus_suite(operation, randomized_count=3, seed=0x5CA1E)
    expected_targets = {
        (concept, str(bin_spec["name"]))
        for concept in concepts
        for bin_spec in reachable_canonical_bins_for_concept(operation, concept) or []
    }
    assert len(expected_targets) == 14
    assert {
        (item["target"]["concept"], item["target"]["bin"])
        for item in suite["directed"]
    } == expected_targets
    assert suite["exceptions"] == []
    assert {item.get("solver_origin") for item in suite["directed"]} == {
        "code_owned_predicate_over_symbolic_attention_scale_trace"
    }
    assert {item["label"] for item in suite["qualification"]} == {
        "canonical_attention_scale_signed_edges",
        "canonical_attention_scale_exact_and_fractional",
        "canonical_attention_scale_zero_after_nonzero",
    }


def test_attention_scale_rejects_wrong_inverse_sqrt_coefficient_and_runtime_d():
    architecture, interface = attention_scale_contracts()
    wrong = deepcopy(architecture)
    wrong["operations"][0]["arithmetic"]["scale_multiplier"] = 31
    metadata = build_architect_operation_metadata(wrong, interface)
    assert metadata["operations"] == []
    assert "expected 32" in metadata["unrepresentable_operations"][0]["reason"]

    runtime = deepcopy(architecture)
    next(item for item in runtime["dimensions"] if item["name"] == "D")[
        "runtime_configurable"
    ] = True
    metadata = build_architect_operation_metadata(runtime, interface)
    assert metadata["operations"] == []
    assert "runtime-configurable attention scaling" in metadata[
        "unrepresentable_operations"
    ][0]["reason"]


def test_attention_scale_catalog_is_stage_specific():
    _, _, operation = compiled_attention_scale()
    assert [
        item["name"]
        for item in canonical_bins_for_concept(operation, "rounding") or []
    ] == [
        "exact",
        "positive_fraction_discarded",
        "negative_fraction_discarded",
    ]
    assert canonical_bins_for_concept(operation, "attention_scores") is None
    assert canonical_bins_for_concept(operation, "sparsity_patterns") is None
