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


def test_passive_extension_stimulus_feedback_names_the_function_boundary() -> None:
    findings = findings_from_validation_error(
        "feature_extensions[0].stimulus symbol 'extension_stimulus' only waits; "
        "it must drive a DUT signal or await a reusable driver"
    )
    assert findings[0]["category"] == "INVALID_STIMULUS_MAPPING"
    assert "Inside the named stimulus function itself" in findings[0]["recommended_change"]
    assert "extension_worklist call_contract" in findings[0]["recommended_change"]


def test_missing_channel_drive_feedback_preserves_required_responder_reuse() -> None:
    findings = findings_from_validation_error(
        "Stimulus 'read' claims channel 'axi_b' coverage but the test source "
        "never drives its DUT-input valid signal asserted (['i_axi_bvalid'])"
    )
    assert findings[0]["category"] == "MISSING_STIMULUS"
    assert "keep that responder call" in findings[0]["recommended_change"]
    assert "request_counts" in findings[0]["recommended_change"]


def test_preawaited_evidence_stimulus_feedback_names_concurrent_api_contract() -> None:
    findings = findings_from_validation_error(
        "capture_protocol_event_trace must receive the unawaited stimulus coroutine "
        "so its observer starts before DUT traffic; source=0, line=10"
    )
    assert findings[0]["category"] == "INVALID_STIMULUS_MAPPING"
    assert "without awaiting it there" in findings[0]["recommended_change"]


def test_protocol_trace_schema_feedback_rejects_invented_record_fields() -> None:
    findings = findings_from_validation_error(
        "transaction_trace record has no top-level field 'kind'; source=0, line=20. "
        "Use record['signals']['kind'] for sampled DUT signals"
    )
    assert findings[0]["category"] == "INVALID_ASSERTION"
    assert "record['signals']" in findings[0]["recommended_change"]


def test_aggregated_protocol_feedback_is_split_into_independent_repairs() -> None:
    findings = findings_from_validation_error(
        "Verifier TB review structure is invalid: Test source is missing "
        "# === LLM-GENERATED OPERATION ASSERTIONS ===; "
        "A new capture_protocol_event_trace stimulus is started immediately after "
        "a previous capture returned in Cocotb's ReadOnly phase; source=0, line=151. "
        "Await a writable scheduling boundary; "
        "cycle_trace record has no top-level field 'i_reset'; source=0, line=110. "
        "Use record['signals'][<exact frozen-contract signal name>]; "
        "Ready/valid handshake output is read after RisingEdge, too late to decide "
        "whether that edge transferred; source=0, edge_line=27, read_line=28; "
        "Stimulus coverage intent must target every exact coverage obligation; "
        "missing=['feature.stall'], unknown=[]"
    )
    assert [finding["category"] for finding in findings] == [
        "MISSING_ASSERTION",
        "INVALID_STIMULUS_MAPPING",
        "INVALID_ASSERTION",
        "INVALID_STIMULUS_MAPPING",
        "COVERAGE_DEFINITION",
    ]
    assert "exact line" in findings[0]["recommended_change"]
    assert "same transaction" in findings[1]["recommended_change"]
    assert "record['signals']" in findings[2]["recommended_change"]
    assert "pre-edge snapshot" in findings[3]["recommended_change"]
    assert "each exact ID" in findings[4]["recommended_change"]


def test_multi_clock_trace_feedback_requires_one_shared_stimulus() -> None:
    findings = findings_from_validation_error(
        "component 'protocol.monitor.contract_event_trace' resolves multiple "
        "runtime bindings [('source', 'request'), ('destination', 'request')]; "
        "call capture_protocol_event_traces once with every exact binding and "
        "one shared unawaited stimulus coroutine"
    )
    assert len(findings) == 1
    assert findings[0]["category"] == "INVALID_STIMULUS_MAPPING"
    assert "one shared unawaited stimulus" in findings[0]["recommended_change"]


def test_unenforced_extension_assertion_feedback_names_direct_assertion() -> None:
    findings = findings_from_validation_error(
        "feature_extensions[0].assertion symbol 'extension_assertion' returns "
        "a decision that no generated test asserts"
    )
    assert findings[0]["category"] == "INVALID_ASSERTION"
    assert "assert the named checker result directly" in findings[0]["recommended_change"]


def test_vacuous_temporal_coverage_feedback_requires_observed_trigger() -> None:
    findings = findings_from_validation_error(
        "feature_extensions[0].coverage symbol 'extension_coverage' can earn a "
        "temporal bin without a reachable assertion that the trigger/event was "
        "actually observed; empty or idle traces must not pass vacuously"
    )
    assert findings[0]["category"] == "COVERAGE_DEFINITION"
    assert "trigger/event count is nonzero" in findings[0]["recommended_change"]


def test_invalid_stimulus_intent_shape_feedback_gives_canonical_literal() -> None:
    findings = findings_from_validation_error(
        "Cannot install contract-generated TB monitor: "
        "STIMULUS_COVERAGE_INTENTS must be a non-empty list"
    )
    assert findings[0]["category"] == "COVERAGE_DEFINITION"
    assert 'STIMULUS_COVERAGE_INTENTS = [{"label": "case_id"' in (
        findings[0]["recommended_change"]
    )
    assert "Do not use a dict keyed by label" in findings[0]["recommended_change"]


def test_invalid_cocotb_time_unit_finding_is_local_to_tb() -> None:
    findings = findings_from_validation_error(
        "Cocotb time unit 's' is invalid; source=0, line=38, "
        "argument='timeout_unit'. Use 'sec' for seconds"
    )
    assert findings[0]["category"] == "INVALID_ASSERTION"
    assert "for seconds use 'sec'" in findings[0]["recommended_change"]


def test_extension_trace_finding_names_runtime_evidence_collector() -> None:
    findings = findings_from_validation_error(
        "feature_extensions[0].coverage symbol 'classify' is not called with "
        "simulator-derived evidence; fabricated literal observation or "
        "non-simulator-derived argument(s)=['cycle_trace', 'transaction_trace']"
    )
    assert findings[0]["category"] == "INVALID_ASSERTION"
    assert "capture_protocol_event_trace" in findings[0]["recommended_change"]
    assert "evidence['cycle_trace']" in findings[0]["recommended_change"]


def test_extension_unused_parameter_finding_explains_branch_local_parameters() -> None:
    findings = findings_from_validation_error(
        "feature_extensions[0].assertion symbol 'check' ignores declared "
        "parameter(s) ['width']"
    )
    assert findings[0]["category"] == "INVALID_STIMULUS_MAPPING"
    assert "not copied into every branch" in findings[0]["recommended_change"]


def test_extension_bundle_errors_split_into_independent_repair_findings() -> None:
    findings = findings_from_validation_error(
        "Invalid Verifier feature extensions: feature_extensions[0].assertion "
        "symbol 'check' ignores declared parameter(s) ['width']; "
        "feature_extensions[0].stimulus symbol 'drive' never executes declared "
        "scenario(s) ['abort'] with their exact parameter values"
    )
    assert len(findings) == 2
    assert "not copied into every branch" in findings[0]["recommended_change"]
    assert "remove it from the bundle" in findings[1]["recommended_change"]
