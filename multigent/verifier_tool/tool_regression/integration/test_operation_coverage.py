from __future__ import annotations

from types import SimpleNamespace
import pytest
from multigent.verifier_tool import (
    CoverageRuntimeError,
    InterfaceCoverageTracker,
    build_operation_coverage_plan,
    canonical_operation_obligation_id,
    canonicalize_operation_obligation_claim,
    capture_contract_snapshot,
    load_operation_coverage_families,
    load_operation_assertion_catalog,
    operation_family,
    render_operation_assertion_catalog,
    render_operation_coverage_catalog,
    validate_architecture_operation_features,
    validate_frozen_operation_scope,
    validate_operation_coverage,
)


def _gemm_architecture() -> dict:
    return {
        "operations": [
            {
                "name": "gemm_bias_relu",
                "kind": "GEMM",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values", "accumulation", "post_processing"],
                "feature_extensions": [],
                "semantics": "C=A*B+bias then ReLU",
            }
        ]
    }


def _point(concept: str, field: str, value, *, source: str = "baseline") -> dict:
    return {
        "id": concept,
        "concept": concept,
        "field": field,
        "source": source,
        "description": concept,
        "bins": [
            {
                "name": "covered_case",
                "intent": "Exercise the selected contract case",
                "predicate": {"op": "eq", "args": [value]},
            }
        ],
    }


def _gemm_spec() -> list[dict]:
    return [
        {
            "operation_name": "gemm_bias_relu",
            "family": "matrix_multiply",
            "coverpoints": [
                _point("dimensions", "shape_class", "partial"),
                _point("operand_values", "operand_class", "extremes"),
                _point("accumulation", "accumulation_case", "overflow"),
                _point("sparse_operand", "sparsity", "sparse", source="llm_extension"),
            ],
        }
    ]


def test_operation_catalog_only_advertises_code_owned_families() -> None:
    families = load_operation_coverage_families()["families"]
    assert set(families) == {
        "matrix_multiply", "sparse_attention", "attention_qk", "attention_scale",
        "attention_mask",
    }
    assert operation_family("GEMM") == "matrix_multiply"
    assert operation_family("qk_score") == "attention_qk"
    assert operation_family("qk_scale") == "attention_scale"
    assert operation_family("binary_attention_mask") == "attention_mask"
    assert operation_family("depthwise-convolution") is None
    assert operation_family("invented accelerator") is None


def test_gemm_catalog_exposes_only_executable_optional_features() -> None:
    matrix = load_operation_coverage_families()["families"]["matrix_multiply"]
    assert matrix["optional_concepts"] == {}
    assert set(matrix["feature_groups"]["post_processing"]["optional_concepts"]) == {
        "bias", "activation", "quantization",
    }
    assert not {"bias", "activation", "quantization"} & set(matrix["optional_concepts"])
    rendered = render_operation_coverage_catalog()
    assert "optional bias" in rendered
    assert "optional transpose_modes" not in rendered


def test_advertised_gemm_concepts_have_code_owned_classifier_support() -> None:
    from multigent.verifier_tool.pool.operation_metadata.canonical import (
        supported_code_owned_concepts,
    )

    family = load_operation_coverage_families()["families"]["matrix_multiply"]
    advertised = set(family["baseline_concepts"])
    advertised.update(family["feature_groups"]["post_processing"]["optional_concepts"])
    metadata = {"operations": [{
        "operation_name": "gemm",
        "arithmetic": {
            "classifier_profile": "integer_matrix_multiply",
            "post_operations": {
                "biased": {"kind": "bias_add"},
                "activated": {"kind": "relu"},
                "quantized": {"kind": "affine_quantize"},
            },
        },
    }]}

    assert advertised == supported_code_owned_concepts(metadata)["gemm"]


def test_gemm_assertion_catalog_exposes_required_property_guidance() -> None:
    matrix = load_operation_assertion_catalog()["families"]["matrix_multiply"]
    assert {
        "oracle_equivalence",
        "exact_result_accounting",
        "contract_phase_consumption",
        "no_unsolicited_stream_output",
    } <= set(matrix["required_properties"])
    rendered = render_operation_assertion_catalog()
    assert "property oracle_equivalence" in rendered


def test_optional_gemm_feature_is_contract_selected_not_baseline_forced() -> None:
    assert validate_architecture_operation_features(_gemm_architecture()) == []
    architecture = _gemm_architecture()
    architecture["operations"][0]["feature_extensions"] = ["transpose_modes"]
    specs = _gemm_spec()
    specs[0]["coverpoints"].append(
        _point("transpose_modes", "transpose_mode", "nt", source="architect_extension")
    )
    assert validate_architecture_operation_features(architecture) == []
    assert validate_operation_coverage(architecture, specs) == []


def test_operation_obligation_ids_strip_recursive_llm_prefixes() -> None:
    expected = "operation.gemm_bias_relu.accumulation"
    assert canonical_operation_obligation_id(
        "gemm_bias_relu", "accumulation"
    ) == expected
    assert canonical_operation_obligation_id(
        "gemm_bias_relu",
        "operation_gemm_bias_relu_operation_gemm_bias_relu_accumulation",
    ) == expected
    assert canonicalize_operation_obligation_claim(
        "operation.gemm_bias_relu.operation_gemm_bias_relu_accumulation",
        ["gemm_bias_relu"],
    ) == expected


def test_known_family_requires_every_baseline_but_allows_llm_extensions() -> None:
    assert validate_architecture_operation_features(_gemm_architecture()) == []
    assert validate_operation_coverage(_gemm_architecture(), _gemm_spec()) == []
    incomplete = _gemm_spec()
    incomplete[0]["coverpoints"] = incomplete[0]["coverpoints"][1:]
    errors = validate_operation_coverage(_gemm_architecture(), incomplete)
    assert any("missing=['dimensions']" in error for error in errors)


def test_release_scope_rejects_post_freeze_llm_operation_obligations() -> None:
    specs = _gemm_spec()
    errors = validate_frozen_operation_scope(_gemm_architecture(), specs)
    assert errors == [
        "operation gemm_bias_relu adds post-freeze release concepts "
        "['sparse_operand']; required operation coverage is exactly Architect "
        "leaf features+feature_extensions=['accumulation', 'dimensions', "
        "'operand_values']. Keep proposed risks diagnostic, "
        "and use existing interface/protocol obligations for handshake, stall, "
        "reset, completion, or error behavior."
    ]


def test_operation_coverage_rejects_explicitly_noncoverable_bins() -> None:
    specs = _gemm_spec()
    specs[0]["coverpoints"][0]["bins"][0]["intent"] = (
        "Inapplicable placeholder that is not sampled"
    )
    errors = validate_operation_coverage(_gemm_architecture(), specs)
    assert any("declares a non-coverable bin" in error for error in errors)


def test_operation_coverage_rejects_distinct_bins_with_identical_predicates() -> None:
    specs = _gemm_spec()
    point = specs[0]["coverpoints"][2]
    point["bins"].append({
        "name": "fake_boundary",
        "intent": "Claim a distinct case without a distinct observation",
        "predicate": dict(point["bins"][0]["predicate"]),
    })
    errors = validate_operation_coverage(_gemm_architecture(), specs)
    assert any("identical predicate" in error for error in errors)


def test_known_family_allows_architect_feature_extension_and_enforces_provenance() -> None:
    architecture = _gemm_architecture()
    architecture["operations"][0]["feature_extensions"] = ["sparse_operand"]
    specs = _gemm_spec()
    specs[0]["coverpoints"][-1]["source"] = "architect_extension"
    assert validate_architecture_operation_features(architecture) == []
    assert validate_operation_coverage(architecture, specs) == []

    specs[0]["coverpoints"][-1]["source"] = "llm_extension"
    assert any(
        "expected architect_extension" in error
        for error in validate_operation_coverage(architecture, specs)
    )


def test_generic_architect_kind_still_requires_llm_selected_family_baseline() -> None:
    architecture = {
        "operations": [
            {
                "name": "op_gemm_accumulate",
                "kind": "compute",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values", "accumulation", "post_processing"],
                "feature_extensions": [],
                "semantics": "matrix multiply accumulate",
            }
        ]
    }
    selected = _gemm_spec()
    selected[0]["operation_name"] = "op_gemm_accumulate"
    assert validate_operation_coverage(architecture, selected) == []
    assert any(
        "missing operation coverage for contract operations" in error
        for error in validate_operation_coverage(architecture, [])
    )
    selected[0]["family"] = "invented_family"
    errors = validate_operation_coverage(architecture, selected)
    assert any("must use contract family" in error for error in errors)


def test_novel_family_and_features_flow_from_contract_to_verifier() -> None:
    architecture = {
        "operations": [
            {
                "name": "graph_walk",
                "kind": "graph_traversal",
                "coverage_family": "graph_accelerator",
                "coverage_family_source": "novel",
                "features": ["graph_size", "degree_distribution", "cycle_structure"],
                "feature_extensions": [],
                "semantics": "Traverse a graph",
            }
        ]
    }
    assert validate_architecture_operation_features(architecture) == []
    specs = [
        {
            "operation_name": "graph_walk",
            "family": "graph_accelerator",
            "coverpoints": [
                _point("graph_size", "graph_size", "small"),
                _point("degree_distribution", "degree_distribution", "skewed"),
                _point("cycle_structure", "cycle_structure", "cyclic"),
                _point("frontier_pressure", "frontier_pressure", "high", source="llm_extension"),
            ],
        }
    ]
    assert validate_operation_coverage(architecture, specs) == []


def observed_dimension_plan():
    point = _point("dimensions", "shape", 4)
    return build_operation_coverage_plan(
        [{"operation_name": "gemm_bias_relu", "family": "matrix_multiply", "coverpoints": [point]}],
        sampling_bindings=[{"operation": "gemm_bias_relu", "point": "dimensions", "template": "dimension",
                           "dimension": "M", "event": "clock", "fields": {"value": {"signal": "cfg"}}}],
        architecture={"dimensions": [{"name": "M", "minimum": 1, "maximum": 4}]},
        interface={"signals": [{"name": "cfg", "width": "3"}]})


def fill_dimensions(tracker):
    for value in (1, 2, 4):
        snapshot = capture_contract_snapshot(
            SimpleNamespace(cfg=SimpleNamespace(value=value)), tracker.signal_names
        )
        tracker.sample_snapshot(snapshot, None)


def test_operation_observations_fill_cocotb_coverpoints() -> None:
    plan = observed_dimension_plan()
    tracker = InterfaceCoverageTracker(plan)
    tracker.sample_operation("gemm_bias_relu", {"shape": 4}, "randomized")
    assert tracker.report()["status"] == "FAIL"  # Claimed fields did not hit bins.
    fill_dimensions(tracker)
    report = tracker.report()
    assert report["status"] == "PASS"
    assert report["operation_samples"] == 1
    assert report["randomized_operation_samples"] == 1
    assert report["coverage_engine"] == "cocotb-coverage"


def test_unhit_operation_bins_fail_closure() -> None:
    tracker = InterfaceCoverageTracker(observed_dimension_plan())
    report = tracker.report()
    assert report["status"] == "FAIL"
    assert report["operation_samples"] == 0
    assert any(item.startswith("operation.gemm_bias_relu") for item in report["missing_bins"])


def test_runtime_enforces_actual_randomized_transaction_minimum(tmp_path) -> None:
    plan = observed_dimension_plan()
    plan["requirements"] = {"randomized_transactions_minimum": 2}
    tracker = InterfaceCoverageTracker(plan, stimulus_ledger_path=tmp_path / "ledger.json")
    fill_dimensions(tracker)
    identity = tracker.record_stimulus("randomized", {"M": 1}, {"result": 5})
    tracker.sample_operation("gemm_bias_relu", {}, "randomized", identity)
    report = tracker.report()
    assert report["status"] == "FAIL"
    assert report["randomized_operation_samples"] == 1
    assert "runtime.randomized_transactions.minimum_2" in report["missing_bins"]

    identity = tracker.record_stimulus("randomized", {"M": 4}, {"result": 20})
    tracker.sample_operation("gemm_bias_relu", {}, "randomized", identity)
    assert tracker.report()["status"] == "PASS"


def test_raw_unbound_operation_definitions_cannot_run_as_legacy_coverage():
    with pytest.raises(CoverageRuntimeError, match="Missing operation sampling bindings"):
        InterfaceCoverageTracker(build_operation_coverage_plan(_gemm_spec()))
