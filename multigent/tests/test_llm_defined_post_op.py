"""Proves the `llm_defined` post-operation kind: an Architect-declared
post-op stage this tool has no built-in `kind` for (unlike `bias_add`/
`wrap`/`relu`), expressed in `formula.py`'s closed grammar instead of
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

from multigent.tests.test_canonical_operation import contracts
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    evaluate_canonical_operation,
    generate_canonical_stimulus_for_bin,
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


def test_llm_defined_stage_rejects_formula_outside_the_grammar():
    architecture, interface = _contracts_with_clip_stage(formula="__import__('os').system('echo hi')")
    _unrepresentable_reason(architecture, interface)


def test_llm_defined_stage_rejects_division():
    architecture, interface = _contracts_with_clip_stage(formula="value / 2")
    _unrepresentable_reason(architecture, interface)
