from __future__ import annotations

from multigent.agents.verifier import VerifierAgent
from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
from multigent.verifier_tool.tb_validation.validator import (
    coverage_obligation_mapping_diff,
    findings_from_coverage,
    findings_from_validation_error,
    review_verifier_artifacts,
    synchronize_test_coverage_metadata,
)


def test_coverage_obligation_mapping_diff_reports_both_exact_sides() -> None:
    assert coverage_obligation_mapping_diff(
        ["common", "stale_json"], ["common", "stale_source"]
    ) == {
        "missing_in_source_constant": ["stale_json"],
        "unexpected_in_source_constant": ["stale_source"],
    }


def test_test_coverage_metadata_is_rebuilt_without_editing_source() -> None:
    source = 'COVERAGE_OBLIGATIONS = {"b", "a"}\n'
    candidate = {
        "status": "VERIFICATION_READY",
        "test_files": [{
            "path": "tests/test_generated.py",
            "content": source,
            "coverage_obligations": ["stale"],
        }],
    }

    normalized = synchronize_test_coverage_metadata(candidate)

    assert normalized["test_files"][0]["coverage_obligations"] == ["a", "b"]
    assert normalized["test_files"][0]["content"] == source
    assert candidate["test_files"][0]["coverage_obligations"] == ["stale"]


def _prepared_candidate():
    context = generic_fir_context()
    return context, VerifierAgent._with_contract_generated_blocks(
        verification_ready_result(), context
    )


def test_valid_candidate_is_approved_without_model_review() -> None:
    context, candidate = _prepared_candidate()
    result = review_verifier_artifacts(context, candidate)
    assert result["status"] == "APPROVED"
    assert result["findings"] == []
    assert "llm_extension semantics were trusted" in result["summary"]


def test_empty_test_is_rejected_deterministically() -> None:
    candidate = verification_ready_result()
    candidate["test_files"][0]["content"] = ""
    result = review_verifier_artifacts(generic_fir_context(), candidate)
    assert result["status"] == "VERIFIER_REPAIR_REQUIRED"
    assert "empty" in result["findings"][0]["evidence"]


def test_sampling_binding_to_unknown_signal_is_rejected_deterministically() -> None:
    context, candidate = _prepared_candidate()
    candidate["test_files"][0]["content"] = candidate["test_files"][0]["content"].replace(
        "'signal': 'cfg'", "'signal': 'not_a_contract_signal'", 1
    )
    result = review_verifier_artifacts(context, candidate)
    assert result["status"] == "VERIFIER_REPAIR_REQUIRED"
    assert result["findings"][0]["category"] == "COVERAGE_DEFINITION"
    assert "not_a_contract_signal" in result["findings"][0]["evidence"]


def test_injected_validator_keeps_facade_portable() -> None:
    calls = []

    def validator(candidate, context):
        calls.append((candidate["status"], context["user_request"]))

    result = review_verifier_artifacts(
        generic_fir_context(), verification_ready_result(), validator=validator
    )
    assert result["status"] == "APPROVED"
    assert calls == [("VERIFICATION_READY", "design a signed 16-bit streaming FIR filter")]


def test_aggregated_validator_errors_become_multiple_findings() -> None:
    def validator(candidate, context):
        raise ValueError(
            "Test source is missing stimulus section; "
            "Every Verifier-authored assert needs a feature comment immediately above it"
        )

    result = review_verifier_artifacts(
        generic_fir_context(), verification_ready_result(), validator=validator
    )
    assert result["status"] == "VERIFIER_REPAIR_REQUIRED"
    assert len(result["findings"]) == 2
    assert "stimulus section" in result["findings"][0]["evidence"]
    assert "feature comment" in result["findings"][1]["evidence"]


def test_coverage_findings_group_sibling_bins_without_losing_evidence() -> None:
    findings = findings_from_coverage({
        "status": "FAIL",
        "missing_bins": [
            "channel.cmd.handshake_states.idle",
            "channel.cmd.handshake_states.transfer",
            "signal.done.completion_behavior.observed",
        ],
    })
    assert len(findings) == 2
    assert "idle" in findings[0]["evidence"]
    assert "transfer" in findings[0]["evidence"]


def test_missing_hit_report_is_not_mislabeled_as_missing_stimulus() -> None:
    findings = findings_from_coverage({
        "status": "FAIL",
        "missing_bins": ["runtime_report_missing"],
        "bin_hits": {},
    })
    assert len(findings) == 1
    assert findings[0]["category"] == "COVERAGE_DEFINITION"
    assert "do not infer missing stimulus" in findings[0]["recommended_change"]


def test_duplicate_stimulus_record_finding_gives_local_repair_options() -> None:
    findings = findings_from_validation_error(
        "Stimulus 'second' records a new checked stimulus at source=0, line=30 "
        "with no await since stimulus 'first' at line=20"
    )
    assert len(findings) == 1
    assert findings[0]["category"] == "MISSING_STIMULUS"
    assert "second" in findings[0]["evidence"]
    assert "under its existing label" in findings[0]["recommended_change"]


def test_copied_observation_finding_requires_dut_measurement() -> None:
    findings = findings_from_validation_error(
        "_contract_record_checked_stimulus expected/observed are identical "
        "literal values; source=0, line=10, label='case'"
    )
    assert findings[0]["category"] == "INVALID_ASSERTION"
    assert "sampled from the DUT" in findings[0]["recommended_change"]


def test_unused_stimulus_control_finding_requires_real_dut_effect() -> None:
    findings = findings_from_validation_error(
        "Stimulus helper 'run_job' never reads passed keyword "
        "'directed_input_stalls'; source=0, call line=25"
    )
    assert findings[0]["category"] == "INVALID_STIMULUS_MAPPING"
    assert "count actual ready/valid cycles" in findings[0]["recommended_change"]


def test_unchecked_stall_replay_finding_requires_unique_handshake() -> None:
    findings = findings_from_validation_error(
        "Stimulus stall helper 'send_one_with_stall' may transfer a beat "
        "before replay; source=0, loop line=10, replay line=15"
    )
    assert findings[0]["category"] == "INVALID_STIMULUS_MAPPING"
    assert "count an accepted beat exactly once" in findings[0]["recommended_change"]


def test_invalid_cocotb_time_unit_finding_is_local_to_tb() -> None:
    findings = findings_from_validation_error(
        "Cocotb time unit 's' is invalid; source=0, line=38, "
        "argument='timeout_unit'. Use 'sec' for seconds"
    )
    assert findings[0]["category"] == "INVALID_ASSERTION"
    assert "for seconds use 'sec'" in findings[0]["recommended_change"]
