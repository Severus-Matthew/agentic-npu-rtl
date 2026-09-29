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
from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result


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
    assert VERIFIER_REVISION_PATCH_SCHEMA == SCHEMA_ROOT / "deterministic_verifier_patch.schema.json"
    Draft202012Validator.check_schema(schema)
    assert "occurrence_line" in schema["properties"]["patches"]["items"]["required"]


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


def test_patch_targeting_only_already_addressed_findings_is_ignored() -> None:
    # Applied findings are frozen within the round. Stale/no-op replays must not
    # reject genuinely new patches or mutate the preserved partial result.
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
    assert "review-refined-0" not in content
    assert "review-fixed-0" in content


def test_review_patch_prompt_contains_only_still_open_findings() -> None:
    context, draft = _context(findings=[
        {"category": "MISSING_ASSERTION", "requirement": "closed", "evidence": "ev0",
         "recommended_change": "rc0"},
        {"category": "MISSING_ASSERTION", "requirement": "open", "evidence": "ev1",
         "recommended_change": "rc1"},
    ])
    context["assertion_definition_review"]["already_addressed_findings"] = [0]
    task = VerifierAgent._build_review_patch_task(context, draft)
    findings_section = task.split("review_findings:", 1)[1].split(
        "already_applied_finding_indices:", 1
    )[0]
    assert "index: 1" in findings_section
    assert "requirement: open" in findings_section
    assert "index: 0" not in findings_section
    assert "requirement: closed" not in findings_section


def test_successful_patch_round_is_marked_complete_before_final_validation(
    tmp_path, monkeypatch
) -> None:
    context, draft = _context()
    old = "    # LLM-GENERATED OPERATION ASSERTION [filter.interface_clock]\n"
    revision = _patch(old, old + "    # review-fixed\n")
    agent = VerifierAgent()
    monkeypatch.setattr(agent, "run_structured", lambda **_: revision)

    def reject_after_patch(**_: object) -> dict:
        raise AgentRuntimeError("new whole-artifact semantic finding")

    monkeypatch.setattr(agent, "persist_validated_result", reject_after_patch)
    with pytest.raises(AgentRuntimeError, match="new whole-artifact"):
        agent.run(context, workspace_dir=tmp_path, run_id="round-complete")
    assert agent.last_addressed_findings == {0}


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
    from multigent.verifier_tool import (
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


def test_stimulus_intent_add_targets_widens_an_existing_label() -> None:
    context, draft = _context()
    revision = {
        "status": "PATCH_READY", "summary": "s", "patches": [], "metadata_edits": [],
        "stimulus_intent_edits": [{
            "op": "add_targets", "label": "mixed",
            "targets": ["signal.completion.completion_behavior"],
            "finding_indices": [0], "reason": "existing stimulus must also cover this",
        }],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, draft, revision)
    from multigent.verifier_tool import (
        extract_stimulus_coverage_intents,
    )
    intents = extract_stimulus_coverage_intents(result["test_files"][0]["content"])
    entry = next(item for item in intents if item["label"] == "mixed")
    assert "signal.completion.completion_behavior" in entry["targets"]
    assert "operation.filter.tap_count" in entry["targets"]  # original targets kept


def test_stimulus_intent_add_targets_rejects_unknown_label() -> None:
    context, draft = _context()
    revision = {
        "status": "PATCH_READY", "summary": "s", "patches": [], "metadata_edits": [],
        "stimulus_intent_edits": [{
            "op": "add_targets", "label": "never_declared", "targets": ["signal.rst.reset_behavior"],
            "finding_indices": [0], "reason": "typo'd label",
        }],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    with pytest.raises(AgentRuntimeError, match="is not declared"):
        VerifierAgent._apply_review_patch(context, draft, revision)


def test_stimulus_intent_add_targets_rejects_no_new_target() -> None:
    context, draft = _context()
    revision = {
        "status": "PATCH_READY", "summary": "s", "patches": [], "metadata_edits": [],
        "stimulus_intent_edits": [{
            "op": "add_targets", "label": "mixed", "targets": ["operation.filter.tap_count"],
            "finding_indices": [0], "reason": "already covered",
        }],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    with pytest.raises(AgentRuntimeError, match="adds no new target"):
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


def test_patch_mismatch_message_pinpoints_a_near_miss_anchor() -> None:
    content = "line one\nline two\nline three\n"
    old_text = "line two\nline THREE\n"
    message = VerifierAgent._describe_patch_mismatch(old_text, content, "tests/x.py", 0)
    assert "found 0" in message
    assert "line 2" in message
    assert "THREE" in message  # what old_text expected
    assert "three" in message  # what the file actually has


def test_patch_mismatch_message_lists_every_ambiguous_occurrence() -> None:
    content = "def f():\n    x = 1\n\ndef g():\n    x = 1\n"
    old_text = "    x = 1\n"
    message = VerifierAgent._describe_patch_mismatch(old_text, content, "tests/x.py", 2)
    assert "found 2" in message
    assert "line 2" in message
    assert "line 5" in message
    assert "occurrence_line" in message


def test_review_patch_can_select_one_identical_occurrence_by_line() -> None:
    context, draft = _context()
    content = draft["test_files"][0]["content"] + "\nanchor = 1\n\nanchor = 1\n"
    draft["test_files"][0]["content"] = content
    context["assertion_definition_review"]["previous_verifier_output"] = draft
    starts = []
    offset = content.find("anchor = 1\n")
    while offset != -1:
        starts.append(offset)
        offset = content.find("anchor = 1\n", offset + 1)
    second_line = content.count("\n", 0, starts[1]) + 1
    revision = _patch("anchor = 1\n", "anchor = 2\n")
    revision["patches"][0]["occurrence_line"] = second_line
    result = VerifierAgent._apply_review_patch(context, draft, revision)
    updated = result["test_files"][0]["content"]
    assert updated.count("anchor = 1\n") == 1
    assert updated.count("anchor = 2\n") == 1
    assert updated.rfind("anchor = 2\n") > updated.rfind("anchor = 1\n")


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


def test_metadata_add_rejects_a_bin_name_that_already_exists() -> None:
    context, draft = _context()
    path = "/operation_coverage/operation_name=filter/coverpoints/id=tap_count/bins/-"
    revision = {
        "status": "PATCH_READY", "summary": "duplicate name", "patches": [],
        "metadata_edits": [{
            "op": "add", "path": path,
            "value_json": json.dumps({
                "name": "four", "intent": "duplicate of the existing bin",
                "predicate": {"op": "eq", "args": [4]},
            }),
            "finding_indices": [0], "reason": "accidentally reuses an existing name",
        }],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    with pytest.raises(AgentRuntimeError, match="already exists"):
        VerifierAgent._apply_review_patch(context, draft, revision)


def test_metadata_remove_deletes_one_bin_after_a_replacement_is_added() -> None:
    context, draft = _context()
    coverpoint = "/operation_coverage/operation_name=filter/coverpoints/id=tap_count"
    revision = {
        "status": "PATCH_READY", "summary": "swap the stale bin for a valid one",
        "patches": [],
        "metadata_edits": [
            {
                "op": "add", "path": f"{coverpoint}/bins/-",
                "value_json": json.dumps({
                    "name": "eight", "intent": "eight taps",
                    "predicate": {"op": "eq", "args": [8]},
                }),
                "finding_indices": [0], "reason": "add the contract-valid bin first",
            },
            {
                "op": "remove", "path": f"{coverpoint}/bins/name=four",
                "value_json": "", "finding_indices": [0],
                "reason": "four taps can never occur; delete the stale bin",
            },
        ],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    result = VerifierAgent._apply_review_patch(context, draft, revision)
    bins = result["operation_coverage"][0]["coverpoints"][0]["bins"]
    assert [item["name"] for item in bins] == ["eight"]


def test_metadata_remove_rejects_the_last_bin_and_unknown_selectors() -> None:
    context, draft = _context()
    coverpoint = "/operation_coverage/operation_name=filter/coverpoints/id=tap_count"
    base = {
        "status": "PATCH_READY", "summary": "bad", "patches": [],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    for path, why in (
        (f"{coverpoint}/bins/name=four", "last bin"),
        (f"{coverpoint}/bins/name=missing", "unknown selector"),
        (f"{coverpoint}/bins/name=four/intent", "field beneath selector"),
        (f"{coverpoint}/id", "identity field, not a collection item"),
    ):
        revision = {**base, "metadata_edits": [{
            "op": "remove", "path": path, "value_json": "",
            "finding_indices": [0], "reason": why,
        }]}
        with pytest.raises(AgentRuntimeError, match="Invalid Verifier metadata edit"):
            VerifierAgent._apply_review_patch(context, draft, revision)


def test_metadata_edit_batch_failure_does_not_corrupt_operation_coverage() -> None:
    context, draft = _context()
    coverpoint = "/operation_coverage/operation_name=filter/coverpoints/id=tap_count"
    original_bin = copy.deepcopy(draft["operation_coverage"][0]["coverpoints"][0]["bins"][0])
    revision = {
        "status": "PATCH_READY", "summary": "partially valid batch", "patches": [],
        "metadata_edits": [
            {
                "op": "replace", "path": f"{coverpoint}/bins/name=four/predicate/op",
                "value_json": '"gt"', "finding_indices": [0], "reason": "first edit succeeds",
            },
            {
                "op": "replace", "path": f"{coverpoint}/bins/name=four/predicate/args",
                "value_json": "[4]", "finding_indices": [0],
                "reason": "second edit is rejected: args is a composite value",
            },
        ],
        "architecture_conflict": None, "known_verification_gaps": [],
    }
    with pytest.raises(ReviewPatchPartialFailure, match="cannot replace a composite") as exc_info:
        VerifierAgent._apply_review_patch(context, draft, revision)
    live_bin = exc_info.value.partial_result["operation_coverage"][0]["coverpoints"][0]["bins"][0]
    assert live_bin == original_bin, (
        "the first edit's mutation must not survive a later edit's rejection "
        "in the same batch, since this partial_result becomes the next retry's draft"
    )
    assert draft["operation_coverage"][0]["coverpoints"][0]["bins"][0] == original_bin


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
    hits = {
        "missing_bins": ["channel.a.transfer"],
        "covered_bins": ["channel.a.idle"],
        "bin_hits": {"channel.a.idle": 7, "channel.a.transfer": 0},
        "missing_bin_definitions": [{"id": "channel.a", "bins": [{"name": "transfer"}]}],
        "stimulus_summary": {"attempts": 1},
    }
    context["coverage_closure_review"] = hits
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
    review = update["verification_context"]["deterministic_validation_review"]
    assert review["previous_verifier_output"] == draft
    assert "occur exactly once" in review["patch_validation_error"]
    assert "semantic_validation_review" not in update["verification_context"]
    assert update["verification_context"]["coverage_closure_review"] == hits
    task = VerifierAgent._build_review_patch_task(update["verification_context"], draft)
    assert 'channel.a.idle: 7' in task
    assert 'channel.a.transfer: 0' in task
    assert update["history"][0]["status"] == "SOURCE_PATCH_CORRECTION"


def test_missing_coverage_report_never_requests_stimulus_from_fake_hits() -> None:
    context, draft = _context()
    context["coverage_closure_review"] = {
        "missing_bins": ["runtime_report_missing"],
        "covered_bins": [],
        "bin_hits": {},
    }
    task = VerifierAgent._build_review_patch_task(context, draft)
    assert "coverage_report_failure:" in task
    assert "coverage_hit_feedback:" not in task


def test_completed_finding_round_restarts_indices_for_new_validator_error(
    tmp_path, monkeypatch
) -> None:
    context, draft = _context()
    context["assertion_definition_review"]["already_addressed_findings"] = [0]
    context["assertion_definition_review"]["previous_verifier_output"] = draft
    monkeypatch.setattr(
        artifacts, "build_verification_context", lambda **kwargs: generic_fir_context()
    )
    error = (
        "Verifier TB review structure is invalid: "
        "Stimulus 'legal' claims channel 'a' coverage but the test source never drives a_valid"
    )
    update = artifacts.verification_repair_node({
        "user_request": "fir",
        "architecture_dir": str(tmp_path),
        "verifier_status": "SEMANTIC_VALIDATION_FAILED",
        "verification_context": context,
        "verifier_draft": draft,
        "verifier_revision": 4,
        "errors": [error],
    })
    review = update["verification_context"]["deterministic_validation_review"]
    assert review["already_addressed_findings"] == []
    assert len(review["findings"]) == 1
    assert "never drives" in review["findings"][0]["evidence"]
    assert update["history"][0]["status"] == "NEW_DETERMINISTIC_FINDING_ROUND"


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


def test_patch_input_mismatch_is_not_an_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT",
        "reference_files": [],
        "test_files": [],
        "architecture_conflict": {
            "category": "input_evidence_mismatch",
            "affected_modules": ["fir_top"],
            "issue": "Review findings say a label is absent but it exists in the supplied test file.",
            "evidence": "The validator and supplied file snapshot disagree.",
            "requested_architect_decision": "Provide the actual current file snapshot or updated findings.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="patch/input/validator evidence mismatch"):
        VerifierAgent._validate_prepared_result(
            result=result, context=generic_fir_context()
        )


def test_artifact_mismatch_is_not_an_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT",
        "reference_files": [],
        "test_files": [],
        "architecture_conflict": {
            "category": "artifact_mismatch",
            "affected_modules": ["fir_top"],
            "issue": "Findings claim a call is absent but it exists in the supplied source.",
            "evidence": "The supplied test source appears to contain that text.",
            "requested_architect_decision": "Provide the exact current on-disk artifact or precise validator-flagged region.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="patch/input/validator evidence mismatch"):
        VerifierAgent._validate_prepared_result(
            result=result, context=generic_fir_context()
        )


def test_operation_coverage_id_namespace_is_not_an_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT",
        "reference_files": [],
        "test_files": [],
        "architecture_conflict": {
            "category": "coverage_contract_ambiguity",
            "affected_modules": ["fir_top"],
            "issue": "The authoritative operation-obligation ID namespace is not in the interface contract.",
            "evidence": "Multiple operation coverage ID namespace spellings appear possible.",
            "requested_architect_decision": "Provide the operation obligation ID set.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="generated by the deterministic Verifier taxonomy"):
        VerifierAgent._validate_prepared_result(
            result=result, context=generic_fir_context()
        )
