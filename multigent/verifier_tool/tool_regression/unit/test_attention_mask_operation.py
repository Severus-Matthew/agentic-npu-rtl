from __future__ import annotations

from copy import deepcopy

from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_operation_feature_plan,
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


CONCEPTS = (
    "dimensions",
    "score_values",
    "mask_values",
    "sparsity_patterns",
    "masked_values",
    "mask_effects",
)


def _serialization(dimensions: list[str]) -> dict[str, object]:
    return {
        "kind": "dense_tensor",
        "index_order": dimensions,
        "description": "One row-major element per transfer.",
    }


def attention_mask_contracts() -> tuple[dict, dict]:
    architecture = {
        "operations": [
            {
                "name": "attention_mask_core",
                "kind": "attention_mask",
                "coverage_family": "attention_mask",
                "coverage_family_source": "catalog",
                "features": list(CONCEPTS),
                "feature_extensions": [],
                "semantics": (
                    "masked_score[q,s] = scaled_score[q,s] when mask[q,s] is "
                    "one, otherwise zero; no softmax or V stage is included"
                ),
                "arithmetic": {
                    "classifier_profile": "binary_attention_mask",
                    "mask_mode": "binary_keep",
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
                "inputs": ["scaled_score_matrix", "mask_matrix"],
                "outputs": ["masked_score_matrix"],
            }
        ],
        "data_types": [
            {"name": "u1", "width_bits": 1, "signed": False},
            {"name": "s8", "width_bits": 8, "signed": True},
            {"name": "s16", "width_bits": 16, "signed": True},
        ],
        "data_objects": [
            {
                "name": "scaled_score_matrix",
                "role": "scaled_attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
            {
                "name": "mask_matrix",
                "role": "attention_mask",
                "data_type": "u1",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
            {
                "name": "masked_score_matrix",
                "role": "masked_attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
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
            for name, extent in {"Q": 2, "S": 3}.items()
        ],
        "parameters": [
            {"name": "Q_DIM", "default_value": "2"},
            {"name": "S_DIM", "default_value": "3"},
        ],
    }
    channels = []
    signals = []
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        channels.append(
            {
                "name": channel,
                "direction": "output" if index == 2 else "input",
                "protocol_profile": "ready_valid",
                "data_objects": [obj["name"]],
                "ordering": "declared dimension order",
                "framing": "exact tensor",
            }
        )
        width = "1" if obj["data_type"] == "u1" else "16"
        signals.extend(
            [
                {"name": f"{channel}_valid", "channel": channel, "role": "valid"},
                {"name": f"{channel}_ready", "channel": channel, "role": "ready"},
                {
                    "name": f"{channel}_payload",
                    "channel": channel,
                    "role": "payload",
                    "width": width,
                    "signed": obj["data_type"] != "u1",
                },
            ]
        )
    return architecture, {"channels": channels, "signals": signals}


def compiled_attention_mask() -> tuple[dict, dict, dict]:
    architecture, interface = attention_mask_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    return architecture, interface, metadata["operations"][0]


def test_attention_mask_is_independent_and_code_owned():
    architecture, _, operation = compiled_attention_mask()
    assert validate_architecture_operation_features(architecture) == []
    assert operation["arithmetic"]["support_status"] == (
        "supported_binary_attention_mask"
    )
    assert [item["object_role"] for item in operation["inputs"]] == [
        "scaled_attention_score_matrix",
        "attention_mask",
    ]
    assert [item["object_role"] for item in operation["outputs"]] == [
        "masked_attention_score_matrix"
    ]
    plan = build_operation_feature_plan(architecture)
    assert {item["bindings"]["concept"] for item in plan["features"]} == set(
        CONCEPTS
    )
    assertions = load_operation_assertion_catalog()["families"]["attention_mask"]
    assert "mask_polarity" in assertions["required_properties"]
    assert "coordinate_alignment" in assertions["required_properties"]


def test_attention_mask_known_answer_polarity_and_patterns():
    _, _, operation = compiled_attention_mask()
    stimulus = {
        "scaled_score_matrix": [-32768, -3, 0, 5, 32767, 7],
        "mask_matrix": [1, 0, 1, 1, 0, 0],
    }
    expected = {"masked_score_matrix": [-32768, 0, 0, 5, 0, 0]}
    assert evaluate_canonical_operation(operation, stimulus) == expected
    job = assemble_canonical_job(operation, stimulus, expected, expected)
    assert job is not None
    evidence = classify_operation_job(job)
    assert set(evidence["mask_values"]) == {"drop", "keep"}
    assert set(evidence["sparsity_patterns"]) == {"singleton_row", "partial_row"}
    assert set(evidence["masked_values"]) == {
        "zero_masked",
        "positive_masked",
        "negative_masked",
    }
    assert set(evidence["mask_effects"]) == {
        "active_score_preserved",
        "inactive_nonzero_zeroed",
        "active_zero_preserved", "inactive_positive_zeroed", "inactive_negative_zeroed",
    }


def test_attention_mask_generates_all_twenty_bins_and_qualification_cases():
    _, _, operation = compiled_attention_mask()
    suite = generate_canonical_stimulus_suite(
        operation, randomized_count=3, seed=0xA55A
    )
    expected_targets = {
        (concept, str(bin_spec["name"]))
        for concept in CONCEPTS
        for bin_spec in reachable_canonical_bins_for_concept(operation, concept) or []
    }
    assert len(expected_targets) == 20
    assert {
        (item["target"]["concept"], item["target"]["bin"])
        for item in suite["directed"]
    } == expected_targets
    assert suite["exceptions"] == []
    assert {item.get("solver_origin") for item in suite["directed"]} == {
        "code_owned_predicate_over_symbolic_attention_mask_trace"
    }
    assert {item["label"] for item in suite["qualification"]} == {
        "canonical_attention_mask_polarity_and_edges",
        "canonical_attention_mask_row_patterns",
        "canonical_attention_mask_zero_after_nonzero",
    }


def test_attention_mask_rejects_non_binary_transport_and_supports_result_wrap():
    architecture, interface = attention_mask_contracts()
    invalid = deepcopy(architecture)
    next(
        item for item in invalid["data_objects"] if item["role"] == "attention_mask"
    )["data_type"] = "s8"
    metadata = build_architect_operation_metadata(invalid, interface)
    assert metadata["operations"] == []
    assert "unsigned one-bit" in metadata["unrepresentable_operations"][0]["reason"]

    wrapped = deepcopy(architecture)
    output = next(
        item
        for item in wrapped["data_objects"]
        if item["role"] == "masked_attention_score_matrix"
    )
    output["data_type"] = "s8"
    arithmetic = wrapped["operations"][0]["arithmetic"]
    arithmetic["result_data_type"] = "s8"
    arithmetic["result_conversion"] = "wrap_twos_complement"
    wrapped_interface = deepcopy(interface)
    output_payload = next(
        item
        for item in wrapped_interface["signals"]
        if item["channel"] == "tensor_2" and item["role"] == "payload"
    )
    output_payload["width"] = "8"
    metadata = build_architect_operation_metadata(wrapped, wrapped_interface)
    assert metadata["unrepresentable_operations"] == []
    operation = metadata["operations"][0]
    assert evaluate_canonical_operation(
        operation,
        {
            "scaled_score_matrix": [-129, -128, -1, 0, 127, 128],
            "mask_matrix": [1, 1, 1, 1, 1, 1],
        },
    ) == {"masked_score_matrix": [127, -128, -1, 0, 127, -128]}
