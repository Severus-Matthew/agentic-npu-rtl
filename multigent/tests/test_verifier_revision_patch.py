from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.base import AgentRuntimeError, SCHEMA_ROOT
from multigent.agents.verifier import VERIFIER_REVISION_PATCH_SCHEMA, VerifierAgent
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
