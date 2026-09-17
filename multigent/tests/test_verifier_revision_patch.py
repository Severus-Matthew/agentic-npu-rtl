from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.base import AgentRuntimeError, SCHEMA_ROOT
from multigent.agents.verifier import (
    VERIFIER_REVISION_PATCH_SCHEMA, ReviewPatchPartialFailure, VerifierAgent,
)
from multigent.orchestration import artifacts
from multigent.tests.test_verifier import generic_fir_context, verification_ready_result


def _context(findings: list[dict] | None = None) -> tuple[dict, dict]:
    draft = verification_ready_result()
    context = generic_fir_context()
    context["assertion_definition_review"] = {
        "findings": findings or [{
            "category": "MISSING_ASSERTION",
            "requirement": "Make the smoke assertion auditable",
            "evidence": "The existing assertion has no local audit marker",
            "recommended_change": "Add a local marker without changing behavior",
        }],
        "previous_verifier_output": draft,
    }
    return context, draft


def _patch(old_text: str, new_text: str, *, finding_indices: list[int] | None = None) -> dict:
    return {
        "status": "PATCH_READY",
        "summary": "Local verifier correction",
        "patches": [{
            "path": "tests/test_fir_contract.py",
            "old_text": old_text,
            "new_text": new_text,
            "finding_indices": finding_indices or [0],
            "reason": "Address the concrete review finding only",
        }],
        "metadata_edits": [],
        "architecture_conflict": None,
        "known_verification_gaps": [],
    }


def test_verifier_revision_patch_schema_is_valid() -> None:
    schema = json.loads(VERIFIER_REVISION_PATCH_SCHEMA.read_text())
    assert VERIFIER_REVISION_PATCH_SCHEMA == SCHEMA_ROOT / "verifier_revision_patch.schema.json"
    Draft202012Validator.check_schema(schema)


def test_review_patch_partial_failure_preserves_valid_edits_for_retry() -> None:
    context, draft = _context(findings=[
        {"category": "MISSING_ASSERTION", "requirement": "req0", "evidence": "ev0",
         "recommended_change": "rc0"},
        {"category": "MISSING_ASSERTION", "requirement": "req1", "evidence": "ev1",
         "recommended_change": "rc1"},
    ])
    good_old = "    # LLM-GENERATED OPERATION ASSERTION [filter.interface_clock]\n"
    good_new = good_old + "    # review-fixed-0\n"
    noop_old = "    # LLM-GENERATED OPERATION ASSERTION [filter.interface_reset]\n"
    revision = {
        "status": "PATCH_READY", "summary": "s",
        "patches": [
            {"path": "tests/test_fir_contract.py", "old_text": good_old, "new_text": good_new,
             "finding_indices": [0], "reason": "r0"},
            {"path": "tests/test_fir_contract.py", "old_text": noop_old, "new_text": noop_old,
             "finding_indices": [1], "reason": "r1 (accidentally a no-op)"},
        ],
        "metadata_edits": [], "architecture_conflict": None, "known_verification_gaps": [],
    }
    with pytest.raises(ReviewPatchPartialFailure) as excinfo:
        VerifierAgent._apply_review_patch(context, draft, revision)
    exc = excinfo.value
    assert exc.addressed_findings == {0}
    assert "review-fixed-0" in exc.partial_result["test_files"][0]["content"]

    # A retry seeded with the partial result and already_addressed_findings
    # only needs to resolve what is still outstanding; finding 0's edit
    # from the failed attempt must still be present in the final result.
    context["assertion_definition_review"]["already_addressed_findings"] = sorted(exc.addressed_findings)
    context["assertion_definition_review"]["previous_verifier_output"] = exc.partial_result
    followup_new = noop_old + "    # review-fixed-1\n"
    followup = {
        "status": "PATCH_READY", "summary": "s",
        "patches": [
            {"path": "tests/test_fir_contract.py", "old_text": noop_old, "new_text": followup_new,
             "finding_indices": [1], "reason": "r1-fixed"},
        ],
        "metadata_edits": [], "architecture_conflict": None, "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, exc.partial_result, followup)
    content = result["test_files"][0]["content"]
    assert "review-fixed-0" in content
    assert "review-fixed-1" in content


def test_patch_targeting_only_already_addressed_findings_still_applies() -> None:
    # A model may legitimately want to refine its own earlier fix for a finding
    # before the whole batch is submitted; this must not be treated as an error
    # merely because that finding is already marked done in this same round.
    context, draft = _context(findings=[
        {"category": "MISSING_ASSERTION", "requirement": "req0", "evidence": "ev0",
         "recommended_change": "rc0"},
    ])
    already_fixed_marker = "    # review-fixed-0\n"
    context["assertion_definition_review"]["already_addressed_findings"] = [0]
    draft_with_prior_fix = copy.deepcopy(draft)
    draft_with_prior_fix["test_files"][0]["content"] += already_fixed_marker
    context["assertion_definition_review"]["previous_verifier_output"] = draft_with_prior_fix

    refine_old = already_fixed_marker
    refine_new = "    # review-refined-0\n"
    revision = {
        "status": "PATCH_READY", "summary": "s",
        "patches": [
            {"path": "tests/test_fir_contract.py", "old_text": refine_old, "new_text": refine_new,
             "finding_indices": [0], "reason": "refine the earlier fix for finding 0"},
        ],
        "metadata_edits": [], "architecture_conflict": None, "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, draft_with_prior_fix, revision)
    content = result["test_files"][0]["content"]
    assert "review-refined-0" in content
    assert "review-fixed-0" not in content


def test_stimulus_intent_edit_appends_a_new_declared_label() -> None:
    context, draft = _context()
    original = copy.deepcopy(draft)
    revision = {
        "status": "PATCH_READY", "summary": "s",
        "patches": [],
        "metadata_edits": [],
        "stimulus_intent_edits": [{
            "op": "add", "label": "reset_midjob",
            "targets": ["signal.rst.reset_behavior"],
            "finding_indices": [0], "reason": "add missing reset stimulus intent",
        }],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, draft, revision)
    content = result["test_files"][0]["content"]
    from multigent.verifier_tool.predefined_assertion.instrumentation import (
        extract_stimulus_coverage_intents,
    )
    intents = extract_stimulus_coverage_intents(content)
    labels = {item["label"] for item in intents}
    assert "mixed" in labels  # existing intent preserved
    assert "reset_midjob" in labels  # new intent appended
    new_entry = next(item for item in intents if item["label"] == "reset_midjob")
    assert new_entry["targets"] == ["signal.rst.reset_behavior"]
    # Nothing else in the file changed.
    assert result["reference_files"] == original["reference_files"]


def test_stimulus_intent_edit_rejects_duplicate_label() -> None:
    context, draft = _context()
    revision = {
        "status": "PATCH_READY", "summary": "s",
        "patches": [], "metadata_edits": [],
        "stimulus_intent_edits": [{
            "op": "add", "label": "mixed", "targets": ["operation.filter.tap_count"],
            "finding_indices": [0], "reason": "duplicate label",
        }],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    with pytest.raises(AgentRuntimeError, match="already declared"):
        VerifierAgent._apply_review_patch(context, draft, revision)


def test_review_patch_changes_only_exact_source_and_preserves_metadata() -> None:
    context, draft = _context()
    original = copy.deepcopy(draft)
    old = "    # LLM-GENERATED OPERATION ASSERTION [filter.interface_clock]\n"
    new = old + "    # review-fixed: explicit clock presence follows\n"
    result = VerifierAgent._apply_review_patch(context, draft, _patch(old, new))
    assert "review-fixed" in result["test_files"][0]["content"]
    assert result["reference_files"] == original["reference_files"]
    assert result["operation_coverage"] == original["operation_coverage"]
    assert result["verification_plan"] == original["verification_plan"]
    assert draft == original


def test_review_patch_rejects_whole_file_or_ambiguous_anchor() -> None:
    context, draft = _context()
    whole = draft["test_files"][0]["content"]
    with pytest.raises(AgentRuntimeError, match="entire file"):
        VerifierAgent._apply_review_patch(context, draft, _patch(whole, whole + "\n# changed\n"))
    with pytest.raises(AgentRuntimeError, match="exactly once"):
        VerifierAgent._apply_review_patch(context, draft, _patch("not present", "replacement"))


def test_review_patch_must_cover_every_finding() -> None:
    context, draft = _context([
        {"category": "MISSING_ASSERTION"},
        {"category": "MISSING_STIMULUS"},
    ])
    old = "    # LLM-GENERATED OPERATION ASSERTION [filter.interface_clock]\n"
    with pytest.raises(AgentRuntimeError, match="address every review finding"):
        VerifierAgent._apply_review_patch(context, draft, _patch(old, old + "    # fixed\n"))


def test_review_patch_can_locally_change_operation_coverage_metadata() -> None:
    context, draft = _context()
    original = copy.deepcopy(draft)
    revision = {
        "status": "PATCH_READY",
        "summary": "Fix observed dimension field",
        "patches": [],
        "metadata_edits": [{
            "op": "replace",
            "path": "/operation_coverage/operation_name=filter/coverpoints/id=tap_count/field",
            "value_json": '"observed_tap_count"',
            "finding_indices": [0],
            "reason": "Use the accepted configuration dimension",
        }],
        "architecture_conflict": None,
        "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, draft, revision)
    point = result["operation_coverage"][0]["coverpoints"][0]
    assert point["field"] == "observed_tap_count"
    assert result["test_files"] == original["test_files"]
    assert draft == original


def test_review_metadata_patch_rejects_composite_or_identity_replacement() -> None:
    context, draft = _context()
    base = {
        "status": "PATCH_READY", "summary": "bad", "patches": [],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    for path, value in (
        ("/operation_coverage/operation_name=filter/coverpoints/id=tap_count/id", '"renamed"'),
        ("/operation_coverage/operation_name=filter/coverpoints/id=tap_count/bins", '[]'),
        ("/operation_coverage/0/coverpoints/id=tap_count/field", '"other"'),
    ):
        revision = {**base, "metadata_edits": [{
            "op": "replace", "path": path, "value_json": value,
            "finding_indices": [0], "reason": "bad",
        }]}
        with pytest.raises(AgentRuntimeError, match="Invalid Verifier metadata edit"):
            VerifierAgent._apply_review_patch(context, draft, revision)


def test_multiple_distinct_bins_may_append_to_one_existing_point() -> None:
    context, draft = _context()
    path = "/operation_coverage/operation_name=filter/coverpoints/id=tap_count/bins/-"
    revision = {
        "status": "PATCH_READY", "summary": "add two boundaries", "patches": [],
        "metadata_edits": [
            {
                "op": "add", "path": path,
                "value_json": json.dumps({
                    "name": name, "intent": f"{name} boundary",
                    "predicate": {"op": "eq", "args": [value]},
                }),
                "finding_indices": [0], "reason": "two useful boundaries",
            }
            for name, value in (("minimum", 1), ("maximum", 16))
        ],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, draft, revision)
    bins = result["operation_coverage"][0]["coverpoints"][0]["bins"]
    assert [item["name"] for item in bins][-2:] == ["minimum", "maximum"]


def test_review_patch_cannot_edit_pipeline_generated_blocks() -> None:
    context, draft = _context()
    prepared = VerifierAgent._with_contract_generated_blocks(draft, context)
    old = "# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ==="
    with pytest.raises(AgentRuntimeError, match="may not edit pipeline-generated"):
        VerifierAgent._apply_review_patch(
            context, prepared, _patch(old, old + "\n# injected"),
        )


def test_patch_validation_failure_retries_patch_not_full_replacement(tmp_path, monkeypatch) -> None:
    context, draft = _context()
    monkeypatch.setattr(artifacts, "build_verification_context", lambda **kwargs: generic_fir_context())
    state = {
        "user_request": "fir",
        "architecture_dir": str(tmp_path),
        "verifier_status": "SEMANTIC_VALIDATION_FAILED",
        "verification_context": context,
        "verifier_draft": draft,
        "verifier_revision": 1,
        "errors": ["Verifier source patch 0 old_text must occur exactly once"],
    }
    update = artifacts.verification_repair_node(state)
    review = update["verification_context"]["assertion_definition_review"]
    assert review["previous_verifier_output"] == draft
    assert "occur exactly once" in review["patch_validation_error"]
    assert "semantic_validation_review" not in update["verification_context"]
    assert update["history"][0]["status"] == "SOURCE_PATCH_CORRECTION"


def test_response_capacity_is_not_an_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT",
        "reference_files": [],
        "test_files": [],
        "architecture_conflict": {
            "category": "capacity",
            "affected_modules": ["filter_top"],
            "issue": "The complete replacement exceeds output capacity.",
            "evidence": "It cannot be completed within this response.",
            "requested_architect_decision": "Increase the token limit.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="response-capacity"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())
