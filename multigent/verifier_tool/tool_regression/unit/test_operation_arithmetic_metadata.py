"""Architect declares semantics; the tool may resolve, but must never guess."""

from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent, ContractValidationError
from multigent.verifier_tool.tool_regression.integration.test_architect import FakeArchitectAgent
from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import contracts
from multigent.verifier_tool import (
    automatic_campaign_support, build_architect_operation_metadata,
    evaluate_canonical_operation, generate_canonical_stimulus_for_bin,
    operation_arithmetic_schema,
    validate_architecture_operation_arithmetic, with_operation_arithmetic_schema,
)
from multigent.verifier_tool.pool.operation_metadata.architect_metadata import ArchitectMetadataError
from multigent.verifier_tool.pool.operation_metadata.protocol import ProtocolAdapterError, ReadyValidCaptureAdapter


def _plain_gemm():
    architecture, interface = contracts()
    operation = architecture["operations"][0]
    operation["inputs"].remove("bias_vector")
    operation["feature_extensions"] = []
    operation["arithmetic"]["post_operations"] = {}
    operation["arithmetic"]["post_output"] = "accumulator"
    operation["arithmetic"]["bias_conversion"] = "exact"
    operation["semantics"] = "Signed integer A x B, without bias or activation."
    return architecture, interface


def _plain_quantized_gemm():
    architecture, interface = _plain_gemm()
    operation = architecture["operations"][0]
    operation["feature_extensions"] = ["quantization"]
    output = next(
        item for item in architecture["data_objects"] if item["name"] == "Y_matrix"
    )
    output["data_type"] = "s8"
    operation["arithmetic"].update(
        {
            "result_data_type": "s8",
            "result_conversion": "exact",
            "post_operations": {
                "quantized": {
                    "kind": "affine_quantize",
                    "depends_on": ["accumulator"],
                    "scale_multiplier": 1,
                    "scale_shift": 1,
                    "zero_point": 0,
                    "data_type": "s8",
                    "rounding": "nearest_ties_to_even",
                    "saturation": "clamp",
                    "granularity": "per_tensor",
                }
            },
            "post_output": "quantized",
        }
    )
    return architecture, interface


def _compile(architecture, interface):
    """Compile the contract's one operation, or raise exactly as before.

    `build_architect_operation_metadata` itself no longer raises for a
    per-operation failure -- it isolates the failure into
    `unrepresentable_operations` instead, so a contract with an unrelated
    second operation does not lose the first one's metadata too (see
    `test_mixed_operation_campaign_support.py` and
    `test_lifecycle_policy_pool.py`'s isolation regression tests). This
    module's fixtures are all single-operation, and every test below wants
    the original "tell me exactly why, via this one exception" behavior, so
    this helper re-raises the recorded reason verbatim.
    """

    metadata = build_architect_operation_metadata(architecture, interface)
    if metadata["unrepresentable_operations"]:
        raise ArchitectMetadataError(metadata["unrepresentable_operations"][0]["reason"])
    return metadata["operations"][0]


def test_effective_schema_requires_declarations_without_mutating_base_schema():
    base = json.loads(ARCHITECT_OUTPUT_SCHEMA.read_text())
    original = deepcopy(base)
    effective = ArchitectAgent().load_output_schema(ARCHITECT_OUTPUT_SCHEMA)
    Draft202012Validator.check_schema(effective)
    Draft202012Validator(effective).validate(FakeArchitectAgent().run_structured())
    arch = effective["properties"]["architecture_contract"]["properties"]
    assert "arithmetic" in arch["operations"]["items"]["required"]
    assert "serialization" in arch["data_objects"]["items"]["required"]
    assert arch["operations"]["items"]["properties"]["arithmetic"] == operation_arithmetic_schema()
    assert with_operation_arithmetic_schema(effective) == effective
    assert base == original


def test_missing_arithmetic_is_a_contract_error_even_with_detailed_prose():
    architecture, interface = contracts()
    operation = architecture["operations"][0]
    operation.pop("arithmetic")
    operation["semantics"] = "Signed int8 GEMM, s32 wrap accumulator from zero, then column bias, then ReLU."
    before = deepcopy(architecture)
    with pytest.raises(ArchitectMetadataError, match="arithmetic is required"):
        _compile(architecture, interface)
    assert validate_architecture_operation_arithmetic(architecture)
    assert architecture == before


@pytest.mark.parametrize("field", operation_arithmetic_schema()["anyOf"][0]["required"])
def test_partial_arithmetic_never_inherits_a_default(field):
    architecture, interface = contracts()
    architecture["operations"][0]["arithmetic"].pop(field)
    with pytest.raises(ArchitectMetadataError):
        _compile(architecture, interface)


@pytest.mark.parametrize("field,value,match", [
    ("accumulator_data_type", "missing", "data type"),
    ("accumulator_initialization", 7, "accumulator_initialization"),
    ("product_data_type", "s8", "exact A\\*B product"),
    ("reduction_dimensions", ["M"], "shared A/B"),
    ("reduction_order", "arbitrary", "reduction_order"),
    ("reduction_conversion", "saturate", "reduction_conversion"),
    ("result_data_type", "s8", "output data object"),
    ("post_operations", [{"kind": "gelu"}], "post_operations"),
])
def test_inconsistent_or_unimplemented_numeric_rules_are_not_reinterpreted(field, value, match):
    architecture, interface = contracts()
    architecture["operations"][0]["arithmetic"][field] = value
    with pytest.raises(ArchitectMetadataError, match=match):
        _compile(architecture, interface)


def test_activation_label_does_not_invent_relu_and_dag_order_is_respected():
    architecture, interface = contracts()
    arithmetic = architecture["operations"][0]["arithmetic"]
    stages = arithmetic["post_operations"]
    del stages["activated"]
    arithmetic["post_output"] = "wrapped"
    with pytest.raises(ArchitectMetadataError, match="activation.*agree"):
        _compile(architecture, interface)

    # post_operations is a DAG: order comes from depends_on, not declaration
    # position, so relu can legally sit *before* wrap in the dependency
    # chain (bias -> relu -> wrap) instead of only ever being last.
    stages["activated"] = {"kind": "relu", "depends_on": ["bias"]}
    stages["wrapped"]["depends_on"] = ["activated"]
    arithmetic["post_output"] = "wrapped"
    operation = _compile(architecture, interface)
    assert operation["arithmetic"]["resolved_stage_order"] == ["bias", "activated", "wrapped"]


def test_declared_accumulator_can_differ_from_output_type():
    architecture, interface = _plain_gemm()
    architecture["operations"][0]["arithmetic"]["accumulator_data_type"] = "s8"
    operation = _compile(architecture, interface)
    assert operation["arithmetic"]["accumulator_type"]["width_bits"] == 8
    assert operation["outputs"][0]["data_type"]["width_bits"] == 32
    assert evaluate_canonical_operation(operation, {"A_matrix": [100], "B_matrix": [2]}) == {"Y_matrix": [-56]}


def test_result_narrowing_obeys_declared_conversion():
    architecture, interface = _plain_gemm()
    arithmetic = architecture["operations"][0]["arithmetic"]
    arithmetic["result_data_type"] = "s8"
    architecture["data_objects"][3]["data_type"] = "s8"
    operation = _compile(architecture, interface)
    assert operation["arithmetic"]["accumulator_type"]["width_bits"] == 32
    assert evaluate_canonical_operation(operation, {"A_matrix": [100], "B_matrix": [2]}) == {"Y_matrix": [-56]}


@pytest.mark.parametrize(
    "mutate,match",
    [
        (
            lambda architecture, operation, stage: stage.update(zero_point=128),
            "zero_point must be representable",
        ),
        (
            lambda architecture, operation, stage: stage.update(data_type="s32"),
            "data_type must match result_data_type",
        ),
        (
            lambda architecture, operation, stage: operation["arithmetic"].update(
                result_conversion="wrap_twos_complement"
            ),
            "result_conversion must be exact",
        ),
        (
            lambda architecture, operation, stage: operation.update(
                feature_extensions=[]
            ),
            "selected feature 'quantization' must agree",
        ),
    ],
)
def test_affine_quantization_rejects_ambiguous_or_inconsistent_metadata(
    mutate, match
):
    architecture, interface = _plain_quantized_gemm()
    operation = architecture["operations"][0]
    stage = operation["arithmetic"]["post_operations"]["quantized"]
    mutate(architecture, operation, stage)
    with pytest.raises(ArchitectMetadataError, match=match):
        _compile(architecture, interface)


def test_quantization_selection_requires_the_declared_stage():
    architecture, interface = _plain_gemm()
    architecture["operations"][0]["feature_extensions"] = ["quantization"]
    with pytest.raises(
        ArchitectMetadataError,
        match="selected feature 'quantization' must agree",
    ):
        _compile(architecture, interface)


def test_declared_dag_order_of_wrap_then_relu_is_honored_even_without_bias():
    architecture, interface = _plain_gemm()
    declaration = architecture["operations"][0]
    declaration["feature_extensions"] = ["activation"]
    declaration["arithmetic"].update({
        "accumulator_data_type": "s8", "reduction_conversion": "exact",
        "post_operations": {
            "wrapped": {"kind": "wrap", "depends_on": ["accumulator"], "data_type": "s8"},
            "activated": {"kind": "relu", "depends_on": ["wrapped"]},
        },
        "post_output": "activated",
    })
    operation = _compile(architecture, interface)
    # 100*2=200 overflows s8: wrap(200)=-56 first, then relu(-56)=0. A
    # different declared order (relu before wrap) would instead give -56,
    # since relu(200)=200 unchanged, then wrap(200)=-56 -- proving the
    # compiled result actually follows the declared depends_on chain rather
    # than a hardcoded assumption.
    assert evaluate_canonical_operation(operation, {"A_matrix": [100], "B_matrix": [2]}) == {"Y_matrix": [0]}

    declaration["arithmetic"]["post_operations"] = {
        "activated": {"kind": "relu", "depends_on": ["accumulator"]},
        "wrapped": {"kind": "wrap", "depends_on": ["activated"], "data_type": "s8"},
    }
    declaration["arithmetic"]["post_output"] = "wrapped"
    operation = _compile(architecture, interface)
    assert operation["arithmetic"]["resolved_stage_order"] == ["activated", "wrapped"]
    assert evaluate_canonical_operation(operation, {"A_matrix": [100], "B_matrix": [2]}) == {"Y_matrix": [-56]}


def test_activation_directed_vectors_invert_a_preceding_quantizer():
    architecture, interface = _plain_quantized_gemm()
    declaration = architecture["operations"][0]
    declaration["feature_extensions"] = ["quantization", "activation"]
    stages = declaration["arithmetic"]["post_operations"]
    stages["quantized"]["zero_point"] = 3
    stages["activated"] = {"kind": "relu", "depends_on": ["quantized"]}
    declaration["arithmetic"]["post_output"] = "activated"
    operation = _compile(architecture, interface)
    for bin_name, classification in (
        ("negative_region", "negative"),
        ("zero_region", "zero"),
        ("positive_region", "positive"),
    ):
        case = generate_canonical_stimulus_for_bin(operation, "activation", bin_name)
        assert classification in case["evidence"]["activation"]


def test_overflow_prose_cannot_override_explicit_conversions():
    architecture, interface = _plain_gemm()
    architecture["operations"][0]["arithmetic"].update({"accumulator_data_type": "s8", "reduction_conversion": "exact"})
    architecture["data_types"][0]["overflow_semantics"] = "WRAP WRAP WRAP"
    operation = _compile(architecture, interface)
    assert evaluate_canonical_operation(operation, {"A_matrix": [100], "B_matrix": [2]}) == {"Y_matrix": [200]}


def test_unsupported_math_requires_explicit_llm_delegation_and_specification():
    architecture, interface = contracts()
    declaration = architecture["operations"][0]
    declaration["arithmetic"] = {"classifier_profile": "llm_extension", "reason": "GELU needs an extension formula."}
    declaration["semantics"] = "Y = 0.5*z*(1+erf(z/sqrt(2))), where z = A x B + column_bias."
    operation = _compile(architecture, interface)
    assert operation["arithmetic"]["support_status"] == "llm_extension_required"
    assert operation["arithmetic"]["post_operations"] == []
    assert operation["arithmetic"]["semantics"] == declaration["semantics"]
    assert not automatic_campaign_support({"operations": [operation]})["supported"]
    declaration["semantics"] = ""
    with pytest.raises(ArchitectMetadataError, match="requires explicit"):
        _compile(architecture, interface)


def test_serialization_is_declared_separately_from_shape_and_unsupported_order_stops_adapter():
    architecture, interface = contracts()
    obj = architecture["data_objects"][0]
    obj.pop("serialization")
    with pytest.raises(ArchitectMetadataError, match="serialization must be explicit"):
        _compile(architecture, interface)
    obj["serialization"] = {"kind": "dense_tensor", "index_order": ["K", "M"], "description": "K-major A"}
    operation = _compile(architecture, interface)
    assert operation["inputs"][0]["serialization"]["index_order"] == ["K", "M"]
    support = automatic_campaign_support({"operations": [operation]})
    assert any("serialization" in reason for reason in support["reasons"])
    with pytest.raises(ProtocolAdapterError, match="no layout inference"):
        ReadyValidCaptureAdapter(interface).consume_operation_inputs(operation)


@pytest.mark.parametrize("field,value", [
    ("accumulator_initialization", 2), ("reduction_conversion", "saturate"),
    ("accumulator_type", None), ("result_conversion", "exact"),
])
def test_full_metadata_cannot_bypass_explicit_numeric_validation(field, value):
    architecture, interface = contracts()
    canonical = _compile(architecture, interface)
    architecture["operations"][0].pop("arithmetic")
    architecture["operations"][0]["verification_metadata"] = canonical
    canonical["arithmetic"][field] = value
    with pytest.raises(ArchitectMetadataError):
        _compile(architecture, interface)


def test_revision_cannot_confirm_a_contract_without_arithmetic(tmp_path, monkeypatch):
    from multigent.orchestration.architect_node import _run_architect_revision

    previous = FakeArchitectAgent().run_structured()
    previous["architecture_contract"]["operations"][0].pop("arithmetic")
    output = tmp_path / "architecture"
    output.mkdir()
    (output / "architect_result.json").write_text(json.dumps(previous))
    agent = ArchitectAgent()
    monkeypatch.setattr(agent, "run_structured", lambda **_: {
        "status": "CONTRACT_CONFIRMED", "edits": [], "issue": "no change"
    })
    with pytest.raises(ContractValidationError, match="arithmetic is required"):
        _run_architect_revision(agent, user_request="filter", feedback={"issue": "math"}, output_dir=output, run_id="math-r1")
    assert json.loads((output / "architect_result.json").read_text()) == previous
