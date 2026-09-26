"""Post-processing groups organize features without becoming release targets."""

from copy import deepcopy

import pytest

from multigent.tests.test_canonical_operation import contracts
from multigent.verifier_tool import (
    CanonicalStimulusGenerationError,
    build_architect_operation_metadata,
    build_operation_coverage_plan,
    build_operation_feature_plan,
    canonical_bins_for_concept,
    compile_assertion_feature_plan,
    compile_coverage_feature_plan,
    compile_stimulus_feature_plan,
    evaluate_canonical_operation,
    generate_canonical_stimulus_for_bin,
    generate_canonical_stimulus_suite,
    load_operation_feature_catalog,
    operation_feature_selections,
    operation_optional_concepts,
    render_operation_coverage_catalog,
    synthesize_code_owned_operation_coverage,
    validate_architecture_operation_features,
    validate_frozen_operation_scope,
    validate_operation_coverage,
)


def _point(concept, *, source="baseline"):
    return {
        "id": concept,
        "concept": concept,
        "field": concept,
        "source": source,
        "description": concept,
        "bins": [{"name": "case", "intent": "A concrete case", "predicate": {"op": "eq", "args": [1]}}],
    }


def test_catalog_groups_preserve_leaf_ids_without_parent_coverage():
    matrix = load_operation_feature_catalog()["families"]["matrix_multiply"]
    assert matrix["baseline_concepts"] == ["dimensions", "operand_values", "accumulation"]
    assert "post_processing" not in matrix["starter_bins"]
    assert not {"bias", "activation", "quantization"} & set(matrix["optional_concepts"])
    group = matrix["feature_groups"]["post_processing"]
    assert set(group["optional_concepts"]) == {"bias", "activation", "quantization"}
    assert not {"assertion", "coverage", "stimulus", "bins"} & set(group)
    assert {"bias", "activation", "quantization"} <= set(operation_optional_concepts(matrix))
    rendered = render_operation_coverage_catalog()
    assert "group post_processing (no standalone bins/assertions/stimulus)" in rendered
    assert "    - optional bias:" in rendered
    assert "    - optional activation:" in rendered
    assert "    - optional quantization:" in rendered


def test_per_tensor_affine_quantization_is_fully_tool_owned():
    architecture, interface = contracts()
    operation = architecture["operations"][0]
    operation["feature_extensions"] = ["quantization"]
    operation["inputs"] = ["A_matrix", "B_matrix"]
    output = next(
        item for item in architecture["data_objects"] if item["name"] == "Y_matrix"
    )
    output["data_type"] = "s8"
    arithmetic = operation["arithmetic"]
    arithmetic.update(
        {
            "bias_conversion": "exact",
            "result_data_type": "s8",
            "result_conversion": "exact",
            "post_operations": {
                "quantized": {
                    "kind": "affine_quantize",
                    "depends_on": ["accumulator"],
                    "scale_multiplier": 1,
                    "scale_shift": 1,
                    "zero_point": 3,
                    "data_type": "s8",
                    "rounding": "nearest_ties_to_even",
                    "saturation": "clamp",
                    "granularity": "per_tensor",
                }
            },
            "post_output": "quantized",
        }
    )

    metadata = build_architect_operation_metadata(architecture, interface)
    compiled = metadata["operations"][0]
    assert evaluate_canonical_operation(
        compiled, {"A_matrix": [5], "B_matrix": [1]}
    ) == {"Y_matrix": [5]}  # round(2.5) ties-to-even -> 2, then +3
    assert evaluate_canonical_operation(
        compiled, {"A_matrix": [-5], "B_matrix": [1]}
    ) == {"Y_matrix": [1]}  # round(-2.5) ties-to-even -> -2, then +3
    assert evaluate_canonical_operation(
        compiled, {"A_matrix": [127], "B_matrix": [127]}
    ) == {"Y_matrix": [127]}
    assert evaluate_canonical_operation(
        compiled, {"A_matrix": [-128], "B_matrix": [127]}
    ) == {"Y_matrix": [-128]}

    suite = generate_canonical_stimulus_suite(
        compiled, concepts=["quantization"]
    )
    assert suite["exceptions"] == []
    assert {item["target"]["bin"] for item in suite["directed"]} == {
        "exact",
        "rounded",
        "nonzero_zero_point",
        "negative_saturation",
        "positive_saturation",
    }

    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    quantization = next(
        point
        for point in specs[0]["coverpoints"]
        if point["concept"] == "quantization"
    )
    assert {item["name"] for item in quantization["bins"]} == {
        "exact",
        "rounded",
        "nonzero_zero_point",
        "negative_saturation",
        "positive_saturation",
    }


def test_old_frozen_parent_marker_and_new_leaf_selection_have_identical_plans():
    legacy, _ = contracts()
    modern = deepcopy(legacy)
    modern["operations"][0]["features"].remove("post_processing")
    assert validate_architecture_operation_features(legacy) == []
    assert validate_architecture_operation_features(modern) == []
    assert build_operation_feature_plan(legacy) == build_operation_feature_plan(modern)
    plan = build_operation_feature_plan(modern)
    for compiler in (compile_assertion_feature_plan, compile_coverage_feature_plan, compile_stimulus_feature_plan):
        entries = {entry["bindings"]["concept"]: entry for entry in compiler(plan)["entries"]}
        assert set(entries) == {"dimensions", "operand_values", "accumulation", "bias", "activation"}
        for child in ("bias", "activation"):
            assert entries[child]["id"] == f"operation.gemm_core.{child}"
            assert entries[child]["bindings"]["feature_group"] == "post_processing"


@pytest.mark.parametrize("children, expected", [
    ([], -6),
    (["bias"], -2),
    (["activation"], 0),
    (["bias", "activation"], 0),
])
def test_selected_post_processing_leaves_keep_math_and_coverage(children, expected):
    architecture, interface = contracts()
    contract_operation = architecture["operations"][0]
    contract_operation["feature_extensions"] = children
    if "bias" not in children:
        contract_operation["inputs"].remove("bias_vector")
        contract_operation["arithmetic"]["bias_conversion"] = "exact"
    stages = contract_operation["arithmetic"]["post_operations"]
    keep = [
        name for name in ("bias", "wrapped", "activated")
        if name == "wrapped"
        or (name == "bias" and "bias" in children)
        or (name == "activated" and "activation" in children)
    ]
    contract_operation["arithmetic"]["post_operations"] = {
        name: {**stages[name], "depends_on": [keep[index - 1] if index > 0 else "accumulator"]}
        for index, name in enumerate(keep)
    }
    contract_operation["arithmetic"]["post_output"] = keep[-1]
    original = deepcopy(architecture)
    metadata = build_architect_operation_metadata(architecture, interface)
    operation = metadata["operations"][0]
    stimulus = {"A_matrix": [2], "B_matrix": [-3]}
    if "bias" in children:
        stimulus["bias_vector"] = [4]
    assert evaluate_canonical_operation(operation, stimulus) == {"Y_matrix": [expected]}
    post_operations_before = deepcopy(operation["arithmetic"]["post_operations"])
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    points = specs[0]["coverpoints"]
    selected = {"dimensions", "operand_values", "accumulation", *children}
    assert {point["concept"] for point in points} == selected
    assert validate_operation_coverage(architecture, specs) == []
    assert validate_frozen_operation_scope(architecture, specs) == []
    plan = build_operation_coverage_plan(specs)
    for obligation in plan["obligations"]:
        if obligation["bindings"]["concept"] in children:
            assert obligation["bindings"]["feature_group"] == "post_processing"
    suite = generate_canonical_stimulus_suite(operation)
    assert {case["target"]["concept"] for case in suite["directed"]} == selected
    assert "post_processing" not in {error["concept"] for error in suite["exceptions"]}
    for case in suite["directed"]:
        assert "post_processing" not in case["evidence"]
    assert canonical_bins_for_concept(operation, "post_processing") is None
    assert architecture == original
    assert operation["arithmetic"]["post_operations"] == post_operations_before


def test_parent_coverpoints_are_removed_but_child_and_novel_requirements_remain():
    architecture, interface = contracts()
    architecture["operations"][0]["feature_extensions"].append("novel_quantizer")
    metadata = build_architect_operation_metadata(architecture, interface)
    old = [{
        "operation_name": "gemm_core", "family": "matrix_multiply",
        "coverpoints": [_point("post_processing"), _point("novel_quantizer", source="architect_extension")],
    }]
    original = deepcopy(old)
    specs = synthesize_code_owned_operation_coverage(old, architecture, metadata)
    assert specs[0]["coverpoints"][-1] == old[0]["coverpoints"][-1]
    assert validate_operation_coverage(architecture, specs) == []
    assert validate_frozen_operation_scope(architecture, specs) == []
    assert old == original
    for child in ("bias", "activation", "novel_quantizer"):
        incomplete = deepcopy(specs)
        incomplete[0]["coverpoints"] = [point for point in incomplete[0]["coverpoints"] if point["concept"] != child]
        assert any(f"missing=['{child}']" in error for error in validate_operation_coverage(architecture, incomplete))


def test_a_parent_cannot_be_reintroduced_as_a_coverage_or_stimulus_target():
    architecture, interface = contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    specs[0]["coverpoints"].append(_point("post_processing"))
    assert any("is a feature group" in error for error in validate_operation_coverage(architecture, specs))
    assert validate_frozen_operation_scope(architecture, specs)
    with pytest.raises(ValueError, match="cannot create coverage bins"):
        build_operation_coverage_plan(specs)
    with pytest.raises(CanonicalStimulusGenerationError, match="leaf concept") as error:
        generate_canonical_stimulus_for_bin(metadata["operations"][0], "post_processing", "enabled")
    assert error.value.code == "unsupported_known_feature"


def test_group_marker_does_not_select_children_or_change_novel_feature_names():
    architecture, _ = contracts()
    operation = architecture["operations"][0]
    operation["feature_extensions"] = []
    baseline, extensions = operation_feature_selections(operation)
    assert baseline == ["dimensions", "operand_values", "accumulation"]
    assert extensions == []
    novel = {
        "name": "custom", "kind": "custom", "coverage_family": "custom_family",
        "coverage_family_source": "novel", "features": ["post_processing"],
        "feature_extensions": [],
    }
    assert operation_feature_selections(novel) == (["post_processing"], [])
    specs = [{"operation_name": "custom", "family": "custom_family", "coverpoints": [_point("post_processing")]}]
    assert validate_operation_coverage({"operations": [novel]}, specs) == []
    assert len(build_operation_coverage_plan(specs)["obligations"]) == 1


@pytest.mark.parametrize("defect", ["duplicate_leaf", "parent_bins", "duplicate_group_leaf"])
def test_invalid_group_catalogs_fail_instead_of_creating_duplicate_obligations(defect):
    matrix = deepcopy(load_operation_feature_catalog()["families"]["matrix_multiply"])
    group = matrix["feature_groups"]["post_processing"]
    if defect == "duplicate_leaf":
        matrix["optional_concepts"]["bias"] = deepcopy(group["optional_concepts"]["bias"])
    elif defect == "parent_bins":
        group["coverage"] = {"bins": ["enabled"]}
    else:
        matrix["feature_groups"]["second_group"] = deepcopy(group)
    with pytest.raises(ValueError):
        operation_optional_concepts(matrix)


def test_post_operations_key_order_is_irrelevant_only_depends_on_matters():
    # post_operations is a dict keyed by stage name; execution order comes
    # from following depends_on edges (resolved once at compile time into
    # resolved_stage_order), never from dict key insertion order. Reversing
    # the dict's own key order must not change the computed result.
    architecture, interface = contracts()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    stimulus = {"A_matrix": [2], "B_matrix": [-3], "bias_vector": [4]}
    baseline = evaluate_canonical_operation(operation, stimulus)
    operation["arithmetic"]["post_operations"] = dict(
        reversed(operation["arithmetic"]["post_operations"].items())
    )
    assert evaluate_canonical_operation(operation, stimulus) == baseline


def test_activation_witness_respects_relu_before_bias_dag_order():
    architecture, interface = contracts()
    stages = architecture["operations"][0]["arithmetic"]["post_operations"]
    stages["activated"]["depends_on"] = ["accumulator"]
    stages["bias"]["depends_on"] = ["activated"]
    architecture["operations"][0]["arithmetic"]["post_output"] = "wrapped"
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]

    assert evaluate_canonical_operation(
        operation, {"A_matrix": [-2], "B_matrix": [1], "bias_vector": [1]}
    ) == {"Y_matrix": [1]}
    suite = generate_canonical_stimulus_suite(operation, concepts=["activation"])
    assert suite["exceptions"] == []
    assert {item["target"]["bin"] for item in suite["directed"]} == {
        "negative_region", "zero_region", "positive_region"
    }
