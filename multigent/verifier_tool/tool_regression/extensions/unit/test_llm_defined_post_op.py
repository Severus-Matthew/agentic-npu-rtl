"""Proves the `llm_defined` post-operation kind: an Architect-declared
post-op stage this tool has no built-in `kind` for (unlike `bias_add`/
`wrap`/`relu`), compiled by `formula.py` into the deterministic solver IR instead of
falling back to `classifier_profile: llm_extension` for the whole operation.

The core claim under test: adding one new, tool-unknown stage to the end of
an existing GEMM's post-op chain does *not* poison stimulus generation for
concepts that only need what came before it (`accumulation`, `bias`,
`activation`) -- because `evaluate_canonical_operation` can now walk all the
way through the new stage to produce a correct end-to-end golden value,
which is what every concept's generated case needs regardless of which
concept it targets (see `_case`).
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import contracts
from multigent.verifier_tool import (
    OperationSamplingError,
    build_architect_operation_metadata,
    classify_checked_operations,
    evaluate_canonical_operation,
    generate_canonical_stimulus_for_bin,
    generate_solver_compiled_stimulus_for_bin,
    operation_formula_compilation_report,
    operation_plan_for_tests,
    review_contract_deterministically,
    synthesize_code_owned_operation_coverage,
    validate_operation_coverage,
)


def _unrepresentable_reason(architecture, interface) -> str:
    """`build_architect_operation_metadata` isolates a per-operation failure
    into `unrepresentable_operations` rather than raising (see
    `test_lifecycle_policy_pool.py`'s isolation regression test); these two
    tests just want the one operation's rejection reason."""

    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["operations"] == []
    return metadata["unrepresentable_operations"][0]["reason"]


def _contracts_with_clip_stage(formula: str = "clip(value, 0, 100)"):
    architecture, interface = contracts()
    arithmetic = architecture["operations"][0]["arithmetic"]
    arithmetic["post_operations"]["clipped"] = {
        "kind": "llm_defined", "depends_on": ["activated"], "formula": formula,
    }
    arithmetic["post_output"] = "clipped"
    return architecture, interface


def test_llm_defined_stage_extends_the_golden_walk():
    architecture, interface = _contracts_with_clip_stage()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    assert operation["arithmetic"]["resolved_stage_order"] == ["bias", "wrapped", "activated", "clipped"]

    stimulus = {"A_matrix": [5], "B_matrix": [6], "bias_vector": [100]}
    # product=30, +bias=130, relu(130)=130, wrap32(130)=130, clip(130,0,100)=100
    assert evaluate_canonical_operation(operation, stimulus) == {"Y_matrix": [100]}


def test_llm_defined_stage_does_not_block_existing_concepts():
    """The actual claim: accumulation/bias/activation bins -- none of which
    have anything to do with the new stage -- remain fully automatic."""

    architecture, interface = _contracts_with_clip_stage()
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]

    for concept, bin_name in (
        ("accumulation", "ordinary"),
        ("bias", "positive_bias"),
        ("activation", "negative_region"),
        ("operand_values", "positive"),
    ):
        # generate_canonical_stimulus_for_bin already self-checks the
        # generated vector against the classifier before returning it
        # (raising CanonicalStimulusGenerationError on any mismatch), so
        # simply reaching a returned case is the proof: this concept's
        # stimulus construction and end-to-end golden value both still work
        # automatically despite the operation now ending in a stage this
        # file's Python has never heard of.
        case = generate_canonical_stimulus_for_bin(operation, concept, bin_name)
        assert concept in case["evidence"]


def test_two_llm_defined_stages_coexist():
    architecture, interface = contracts()
    arithmetic = architecture["operations"][0]["arithmetic"]
    arithmetic["post_operations"]["scaled"] = {
        "kind": "llm_defined", "depends_on": ["activated"], "formula": "value * 2",
    }
    arithmetic["post_operations"]["clipped"] = {
        "kind": "llm_defined", "depends_on": ["scaled"], "formula": "clip(value, 0, 100)",
    }
    arithmetic["post_output"] = "clipped"
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    stimulus = {"A_matrix": [5], "B_matrix": [6], "bias_vector": [1]}
    # product=30, +bias=1 -> 31, relu=31, wrap=31, *2=62, clip(62,0,100)=62
    assert evaluate_canonical_operation(operation, stimulus) == {"Y_matrix": [62]}


def test_formula_acceptance_is_decided_by_solver_compilation():
    architecture, interface = _contracts_with_clip_stage(
        formula="abs(value) if value % 3 else value ** 2"
    )
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    assert evaluate_canonical_operation(
        operation, {"A_matrix": [-2], "B_matrix": [3], "bias_vector": [0]}
    ) == {"Y_matrix": [0]}

    report = operation_formula_compilation_report(architecture)
    assert report["status"] == "PASS"
    assert report["coverage_owner"] == "verifier"
    stage = report["operations"][0]["stages"][0]
    assert stage["status"] == "solver_compiled"
    assert stage["stage"] == "clipped"
    assert "solver_ir" in stage


def test_contract_reviewer_blocks_a_formula_the_solver_cannot_compile():
    architecture, interface = _contracts_with_clip_stage(formula="log(value)")
    report = review_contract_deterministically(architecture, interface)
    assert report["status"] == "BLOCKED"
    assert report["operation_solver_compilation"]["status"] == "BLOCKED"
    assert report["operation_solver_compilation"]["operations"][0]["stages"][0][
        "status"
    ] == "solver_compile_failed"
    assert any(
        item["check_id"] == "operation_arithmetic"
        and "failed deterministic solver compilation" in item["message"]
        and "llm_extension" in item["message"]
        for item in report["findings"]
    )


def test_verifier_owns_formula_stage_bins_but_tool_owns_sampling():
    architecture, interface = _contracts_with_clip_stage()
    metadata = build_architect_operation_metadata(architecture, interface)
    verifier_bins = [
        {
            "operation_name": "gemm_core",
            "family": "matrix_multiply",
            "coverpoints": [
                {
                    "id": "clipped",
                    "concept": "clipped",
                    "field": "canonical_job.clipped",
                    "source": "architect_extension",
                    "description": "Verifier-selected regions at the clipped DAG stage.",
                    "bins": [
                        {
                            "name": "below_limit",
                            "intent": "Observe a clipped-stage result below 100.",
                            "predicate": {"op": "lt", "args": [100]},
                        },
                        {
                            "name": "at_limit",
                            "intent": "Observe clipping at 100.",
                            "predicate": {"op": "eq", "args": [100]},
                        },
                    ],
                }
            ],
        }
    ]
    specs = synthesize_code_owned_operation_coverage(
        verifier_bins, architecture, metadata
    )
    assert validate_operation_coverage(architecture, specs) == []
    plan = operation_plan_for_tests(
        specs, ["OPERATION_SAMPLING_BINDINGS = []\n"], architecture, interface
    )
    point = next(
        item for item in plan["obligations"] if item["id"] == "operation.gemm_core.clipped"
    )
    assert point["bindings"]["sampling"] == {
        "template": "canonical_job",
        "origin": "verifier_tool_solver_compiled_formula",
    }
    assert [item["name"] for item in point["bins"]] == ["below_limit", "at_limit"]
    assert all(item["applicability"]["witness"] for item in point["bins"])

    operation = metadata["operations"][0]
    stimulus = {"A_matrix": [5], "B_matrix": [6], "bias_vector": [100]}
    expected = evaluate_canonical_operation(operation, stimulus)
    evidence = classify_checked_operations(
        metadata, ["gemm_core"], stimulus, expected, expected
    )
    assert evidence["gemm_core"]["clipped"] == [100]

    witness = generate_solver_compiled_stimulus_for_bin(
        operation,
        "clipped",
        {
            "name": "at_limit",
            "intent": "Observe clipping at 100.",
            "predicate": {"op": "eq", "args": [100]},
        },
    )
    assert witness["evidence"]["clipped"] == [100]
    assert witness["expected"] == evaluate_canonical_operation(
        operation, witness["stimulus"]
    )


def test_formula_stage_plan_rejects_an_unreachable_verifier_bin():
    architecture, interface = _contracts_with_clip_stage()
    impossible = [
        {
            "operation_name": "gemm_core",
            "family": "matrix_multiply",
            "coverpoints": [
                {
                    "id": "clipped",
                    "concept": "clipped",
                    "field": "canonical_job.clipped",
                    "source": "architect_extension",
                    "description": "An intentionally impossible clipped-stage region.",
                    "bins": [
                        {
                            "name": "negative",
                            "intent": "Impossible because clip(value, 0, 100) is nonnegative.",
                            "predicate": {"op": "lt", "args": [0]},
                        }
                    ],
                }
            ],
        }
    ]
    with pytest.raises(
        OperationSamplingError,
        match="bin without a legal solver witness",
    ):
        operation_plan_for_tests(
            impossible,
            ["OPERATION_SAMPLING_BINDINGS = []\n"],
            architecture,
            interface,
        )


def test_llm_defined_stage_rejects_formula_the_solver_cannot_bind():
    architecture, interface = _contracts_with_clip_stage(formula="__import__('os').system('echo hi')")
    _unrepresentable_reason(architecture, interface)


def test_llm_defined_stage_rejects_real_division_without_rounding_semantics():
    architecture, interface = _contracts_with_clip_stage(formula="value / 2")
    _unrepresentable_reason(architecture, interface)
