from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
import yaml

from multigent.verifier_tool.benchmark.u55c_inspired_int8_gemm_4x4x4 import build_contract_and_tb
from multigent.verifier_tool import (
    LifecyclePolicyError,
    build_architect_operation_metadata,
    build_lifecycle_assertion_plan,
    build_lifecycle_feature_plan,
    build_lifecycle_stimulus_plan,
    check_lifecycle_assertions,
    compile_assertion_feature_plan,
    compile_coverage_feature_plan,
    compile_stimulus_feature_plan,
    finalize_lifecycle_assertions,
    lifecycle_policy_schema,
    load_lifecycle_policy_pool,
    render_architect_metadata_format,
    resolve_lifecycle_policy,
    validate_lifecycle_policy,
    validate_architecture_lifecycle_policies,
)


def _policy(error_style: str = "pulse") -> dict:
    return {
        "job_acceptance": "valid_ready_handshake",
        "job_overlap": "single_inflight",
        "busy_behavior": "tracks_active_job",
        "completion_style": "pulse",
        "completion_timing": "next_cycle_after_retirement",
        "illegal_command_behavior": "error_without_start",
        "error_style": error_style,
        "error_timing": "next_cycle_after_error_event",
        "reset_behavior": "abort_inflight",
    }


def _contracts(error_semantic: str = "error pulse") -> tuple[dict, dict]:
    architecture = {
        "operations": [{
            "name": "job", "coverage_family": "custom_identity",
            "inputs": [], "outputs": ["result"],
            "semantics": "Emit the job result as a single unsigned byte.",
            "arithmetic": {"classifier_profile": "llm_extension", "reason": "custom identity"},
            "lifecycle_policy": _policy(),
        }],
        "data_types": [{"name": "u8", "width_bits": 8, "signed": False}],
        "data_objects": [{
            "name": "result", "role": "result", "data_type": "u8", "dimensions": [],
            "serialization": {"kind": "scalar", "index_order": [], "description": "One result per transfer."},
        }],
        "dimensions": [], "parameters": [],
    }
    interface = {
        "clock": "clk",
        "channels": [
            {"name": "cmd", "direction": "input", "protocol_profile": "ready_valid", "data_objects": []},
            {"name": "out", "direction": "output", "protocol_profile": "ready_valid", "data_objects": ["result"]},
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "width": "1"},
            {"name": "rst_n", "role": "reset", "direction": "input", "width": "1", "semantic": "active-low reset"},
            {"name": "busy", "role": "busy", "direction": "output", "width": "1"},
            {"name": "done", "role": "completion", "direction": "output", "width": "1"},
            {"name": "err", "role": "error", "direction": "output", "width": "1", "semantic": error_semantic},
            {"name": "cv", "role": "valid", "channel": "cmd", "direction": "input", "width": "1"},
            {"name": "cr", "role": "ready", "channel": "cmd", "direction": "output", "width": "1"},
            {"name": "opcode", "role": "payload", "channel": "cmd", "direction": "input", "width": "8", "semantic_class": "command", "semantic": "legal only 8'h01"},
            {"name": "ov", "role": "valid", "channel": "out", "direction": "output", "width": "1"},
            {"name": "orr", "role": "ready", "channel": "out", "direction": "input", "width": "1"},
            {"name": "data", "role": "payload", "channel": "out", "direction": "output", "width": "8", "semantic_class": "data"},
        ],
    }
    return architecture, interface


def _plan(error_style: str = "pulse") -> tuple[dict, dict]:
    architecture, interface = _contracts()
    architecture["operations"][0]["lifecycle_policy"] = _policy(error_style)
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_assertion_plan(interface, metadata)
    base = {str(item["name"]): 0 for item in interface["signals"]}
    base["rst_n"] = 1
    return plan, base


@pytest.mark.parametrize("style", ["pulse", "sticky_until_reset"])
def test_explicit_policy_matches_schema_and_reaches_all_three_branches(style):
    policy = _policy(style)
    Draft202012Validator.check_schema(lifecycle_policy_schema())
    Draft202012Validator(lifecycle_policy_schema()).validate(policy)
    architecture, interface = _contracts("unrelated prose; not used for explicit policy")
    architecture["operations"][0]["lifecycle_policy"] = policy
    before = deepcopy(architecture)
    metadata = build_architect_operation_metadata(architecture, interface)
    lifecycle = metadata["operations"][0]["lifecycle"]
    assert lifecycle["policy"] == policy
    assert lifecycle["policy_source"] == "explicit_contract"
    assert architecture == before
    feature_plan = build_lifecycle_feature_plan(interface, metadata)
    for compile_branch in (compile_assertion_feature_plan, compile_coverage_feature_plan, compile_stimulus_feature_plan):
        entries = [item for item in compile_branch(feature_plan)["entries"] if item["scope"] == "operation"]
        assert entries
        assert all(item["bindings"]["policy"] == policy for item in entries)
    stimulus = build_lifecycle_stimulus_plan(interface, metadata)
    recovery = next(item for item in stimulus["scenarios"] if item["kind"] == "illegal_then_legal_recovery")
    assert recovery["clear_error_before_legal_job"] == (
        "reset" if style == "sticky_until_reset" else "pulse_deassertion"
    )


@pytest.mark.parametrize("field,value", [
    ("completion_style", "sticky_until_clear"),
    ("completion_timing", "same_cycle"),
    ("job_overlap", "multiple_inflight"),
    ("reset_behavior", "preserve_inflight"),
    ("error_style", "typo"),
    ("error_style", None),
])
def test_unsupported_policy_is_rejected_by_schema_and_compiler(field, value):
    """An operation whose lifecycle_policy is outside the closed Lifecycle
    Policy Pool cannot be compiled -- but `build_architect_operation_metadata`
    reports that as one entry in `unrepresentable_operations` rather than
    raising, so a contract with more than one operation does not lose every
    operation's metadata over one operation's unsupported policy (see
    `test_one_bad_lifecycle_policy_does_not_poison_a_sibling_operation`)."""

    policy = {**_policy(), field: value}
    with pytest.raises(ValidationError):
        Draft202012Validator(lifecycle_policy_schema()).validate(policy)
    architecture, interface = _contracts()
    architecture["operations"][0]["lifecycle_policy"] = policy
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["operations"] == []
    assert len(metadata["unrepresentable_operations"]) == 1
    failure = metadata["unrepresentable_operations"][0]
    assert failure["name"] == "job"
    assert field in failure["reason"]


def test_partial_unknown_and_missing_explicit_policies_do_not_get_defaults():
    for policy in ({"error_style": "pulse"}, {**_policy(), "extra_policy": "x"}, {}):
        with pytest.raises(LifecyclePolicyError, match="fields"):
            validate_lifecycle_policy(policy)
    with pytest.raises(LifecyclePolicyError, match="Missing lifecycle.policy"):
        resolve_lifecycle_policy({})
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    explicit = deepcopy(metadata["operations"][0])
    explicit["lifecycle"].pop("policy")
    architecture["operations"][0].pop("arithmetic")
    architecture["operations"][0].pop("lifecycle_policy")
    architecture["operations"][0]["verification_metadata"] = explicit
    broken = build_architect_operation_metadata(architecture, interface)
    assert broken["operations"] == []
    assert "Missing lifecycle.policy" in broken["unrepresentable_operations"][0]["reason"]


def test_missing_policy_is_rejected_and_explicit_policy_overrides_prose():
    architecture, interface = _contracts("sticky until reset")
    architecture["operations"][0].pop("lifecycle_policy")
    broken = build_architect_operation_metadata(architecture, interface)
    assert broken["operations"] == []
    assert "Missing lifecycle.policy" in broken["unrepresentable_operations"][0]["reason"]
    architecture["operations"][0]["lifecycle_policy"] = _policy("pulse")
    explicit = build_architect_operation_metadata(architecture, interface)["operations"][0]["lifecycle"]
    assert explicit["policy_source"] == "explicit_contract"
    assert explicit["policy"]["error_style"] == "pulse"


def test_full_metadata_and_compact_policy_cannot_disagree():
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    architecture["operations"][0]["verification_metadata"] = metadata["operations"][0]
    architecture["operations"][0].pop("arithmetic")
    architecture["operations"][0]["lifecycle_policy"] = _policy("sticky_until_reset")
    broken = build_architect_operation_metadata(architecture, interface)
    assert broken["operations"] == []
    assert "disagree" in broken["unrepresentable_operations"][0]["reason"]


@pytest.mark.parametrize("field,value", [
    ("reset_disposition", "preserve_work"),
    ("result_retirement", "on_done_only"),
    ("configuration_snapshot", "live_configuration"),
])
def test_policy_rejects_conflicting_canonical_metadata(field, value):
    with pytest.raises(LifecyclePolicyError, match=field):
        resolve_lifecycle_policy({"policy": _policy(), field: value})
    with pytest.raises(LifecyclePolicyError, match="acceptance"):
        resolve_lifecycle_policy({
            "policy": _policy(),
            "job_accept_channels": [{"acceptance": "start_rising_edge"}],
        })


@pytest.mark.parametrize("style", ["pulse", "sticky_until_reset"])
def test_policy_controls_actual_error_trace(style):
    plan, base = _plan(style)
    state = {}
    check_lifecycle_assertions({**base, "cv": 1, "cr": 1, "opcode": 0}, plan, state)
    check_lifecycle_assertions({**base, "err": 1}, plan, state)
    if style == "pulse":
        with pytest.raises(AssertionError, match="error remained high"):
            check_lifecycle_assertions({**base, "err": 1}, plan, deepcopy(state))
        check_lifecycle_assertions(base, plan, state)
    else:
        check_lifecycle_assertions({**base, "err": 1}, plan, state)
        with pytest.raises(AssertionError, match="sticky error deasserted"):
            check_lifecycle_assertions(base, plan, deepcopy(state))
        check_lifecycle_assertions({**base, "rst_n": 0}, plan, state)
        check_lifecycle_assertions(base, plan, state)
    finalize_lifecycle_assertions(plan, state)


@pytest.mark.parametrize("channel", ["r", "b"])
def test_nonokay_memory_response_uses_response_specific_checker(channel):
    architecture, interface, _, _ = build_contract_and_tb.build_architecture_contract()
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_assertion_plan(interface, metadata)
    assert "response_error_follows_nonokay" in plan["enabled_by_operation"]["gemm"]
    base = {str(signal["name"]): 0 for signal in interface["signals"]}
    base["rst_n"] = 1
    state = {}
    check_lifecycle_assertions(
        {**base, "cmd_valid": 1, "cmd_ready": 1, "cmd_opcode": 1}, plan, state
    )
    check_lifecycle_assertions(
        {
            **base,
            "busy": 1,
            f"m_axi_{channel}valid": 1,
            f"m_axi_{channel}ready": 1,
            f"m_axi_{channel}resp": 2,
        },
        plan,
        state,
    )
    with pytest.raises(AssertionError, match="response_error_follows_nonokay.*non-OKAY"):
        check_lifecycle_assertions(base, plan, deepcopy(state))
    check_lifecycle_assertions({**base, "error": 1}, plan, state)
    finalize_lifecycle_assertions(plan, state)


def test_response_error_checker_is_absent_without_a_bound_response_channel():
    plan, _ = _plan()
    assert "response_error_follows_nonokay" not in plan["enabled_by_operation"]["job"]


def test_supported_completion_busy_and_reset_policy_traces():
    plan, base = _plan()
    state = {}
    command = {**base, "cv": 1, "cr": 1, "opcode": 1}
    check_lifecycle_assertions(command, plan, state)
    with pytest.raises(AssertionError, match="busy is low"):
        check_lifecycle_assertions(base, plan, deepcopy(state))
    with pytest.raises(AssertionError, match="second legal command"):
        check_lifecycle_assertions({**command, "busy": 1}, plan, deepcopy(state))
    with pytest.raises(AssertionError, match="without a preceding final output"):
        check_lifecycle_assertions({**base, "busy": 1, "done": 1}, plan, deepcopy(state))
    check_lifecycle_assertions({**base, "busy": 1, "ov": 1, "orr": 1}, plan, state)
    with pytest.raises(AssertionError, match="not followed by completion"):
        check_lifecycle_assertions(base, plan, deepcopy(state))
    check_lifecycle_assertions({**base, "done": 1}, plan, state)
    with pytest.raises(AssertionError, match="completion remained high"):
        check_lifecycle_assertions({**base, "done": 1}, plan, deepcopy(state))
    check_lifecycle_assertions(base, plan, state)
    finalize_lifecycle_assertions(plan, state)
    check_lifecycle_assertions(command, plan, state)
    check_lifecycle_assertions({**base, "rst_n": 0}, plan, state)
    with pytest.raises(AssertionError, match="no active legal job"):
        check_lifecycle_assertions({**base, "ov": 1, "orr": 1}, plan, state)


def test_pool_is_isolated_from_callers_and_appears_in_existing_prompt_format():
    pool = load_lifecycle_policy_pool()
    pool["policies"]["completion_style"]["choices"]["invented"] = "not implemented"
    choices = lifecycle_policy_schema()["properties"]["completion_style"]["anyOf"][0]["enum"]
    assert "invented" not in choices
    rendered = render_architect_metadata_format()
    assert "lifecycle_policy_pool:" in rendered
    assert "sticky_until_reset" in rendered
    assert "integrated_in_effective_architect_output_schema" in rendered


def test_yaml_alone_cannot_advertise_unimplemented_behavior(tmp_path, monkeypatch):
    from multigent.verifier_tool.pool.lifecycle_policy_pool import policies

    raw = load_lifecycle_policy_pool()
    raw["policies"]["completion_style"]["choices"]["sticky"] = "not implemented"
    candidate = tmp_path / "lifecycle_policies.yaml"
    candidate.write_text(yaml.safe_dump(raw), encoding="utf-8")
    monkeypatch.setattr(policies, "LIFECYCLE_POLICY_POOL_PATH", candidate)
    policies._pool.cache_clear()
    try:
        with pytest.raises(LifecyclePolicyError, match="unimplemented"):
            load_lifecycle_policy_pool()
    finally:
        policies._pool.cache_clear()


def test_ambiguous_status_binding_cannot_silently_disable_a_checker():
    with pytest.raises(LifecyclePolicyError, match="completion must bind zero or one"):
        resolve_lifecycle_policy({
            "policy": _policy(),
            "status_bindings": {"completion": ["done_a", "done_b"]},
        })


def _two_operation_contracts() -> tuple[dict, dict]:
    """Two operations on one interface -- they necessarily share one command/
    status lifecycle surface, since `_bind_lifecycle_metadata` reads
    job_accept_channels/status_bindings from the interface as a whole, not
    per operation -- but each picks its own `lifecycle_policy`, one
    supported and one outside the closed Lifecycle Policy Pool."""

    architecture, interface = _contracts()
    architecture["operations"][0]["name"] = "good_job"
    architecture["operations"][0]["outputs"] = ["good_result"]
    architecture["data_objects"][0]["name"] = "good_result"
    interface["channels"][1]["data_objects"] = ["good_result"]

    bad_operation = deepcopy(architecture["operations"][0])
    bad_operation["name"] = "bad_job"
    bad_operation["outputs"] = ["bad_result"]
    bad_operation["lifecycle_policy"] = {**_policy(), "completion_style": "sticky_until_clear"}
    architecture["operations"].append(bad_operation)
    architecture["data_objects"].append({
        "name": "bad_result", "role": "result", "data_type": "u8", "dimensions": [],
        "serialization": {"kind": "scalar", "index_order": [], "description": "One result per transfer."},
    })
    interface["channels"].append({
        "name": "out2", "direction": "output", "protocol_profile": "ready_valid", "data_objects": ["bad_result"],
    })
    interface["signals"].extend([
        {"name": "ov2", "role": "valid", "channel": "out2", "direction": "output", "width": "1"},
        {"name": "orr2", "role": "ready", "channel": "out2", "direction": "input", "width": "1"},
        {"name": "data2", "role": "payload", "channel": "out2", "direction": "output", "width": "8", "semantic_class": "data"},
    ])
    return architecture, interface


def test_one_bad_lifecycle_policy_does_not_poison_a_sibling_operation():
    """Regression test for the crash-the-whole-contract bug:
    `build_architect_operation_metadata` used to raise `ArchitectMetadataError`
    (a `LifecyclePolicyError` under the hood) the instant it hit any operation
    with a lifecycle_policy outside the closed Lifecycle Policy Pool, which
    lost the already-compiled metadata for every other, perfectly fine
    operation in the same contract too -- not merely marked that one
    operation unsupported, the way an unrecognized `arithmetic` profile
    already degraded gracefully via `classifier_profile: llm_extension`.
    Lifecycle policy has no such escape hatch by design (see this module's
    other tests and `pool/lifecycle_policy_pool/README.md` -- it is a closed,
    code-owned vocabulary the Verifier LLM must never extend, since a
    same-author checker/driver for a self-declared policy would not
    independently verify anything), so the fix is not "let the LLM define a
    new policy" but "isolate the one operation that cannot be represented at
    all instead of crashing metadata compilation for the whole contract"."""

    architecture, interface = _two_operation_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert {item["operation_name"] for item in metadata["operations"]} == {"good_job"}
    assert len(metadata["unrepresentable_operations"]) == 1
    failure = metadata["unrepresentable_operations"][0]
    assert failure["name"] == "bad_job"
    assert "completion_style" in failure["reason"]


def test_revision_cannot_erase_policy_or_keep_an_unmigrated_frozen_operation():
    old = {"operations": [{"name": "job"}]}
    declared = {"operations": [{"name": "job", "lifecycle_policy": _policy()}]}
    assert validate_architecture_lifecycle_policies(old, previous_architecture=old)
    assert validate_architecture_lifecycle_policies(old, require_policy=True)
    errors = validate_architecture_lifecycle_policies(old, previous_architecture=declared)
    assert errors and "cannot be removed" in errors[0]
