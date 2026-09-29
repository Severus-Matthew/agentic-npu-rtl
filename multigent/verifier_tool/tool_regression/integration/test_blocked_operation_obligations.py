"""An operation that cannot be compiled must not shrink the contract's required set.

Before, such an operation vanished from every downstream plan: its lifecycle
features and obligations disappeared, the coverage gate never asked for them, and a
run could PASS with part of the contract unverified. Now the operation's contract-
required lifecycle obligations are planned from whatever fragments did compile and
stay `required_reachable`; the tool owns no checker/sampler/stimulus for them, so
the ordinary hit-based gate decides -- unhit means FAIL, hit by anyone means covered.
"""
from __future__ import annotations

import ast
import json
from copy import deepcopy

import pytest

from multigent.agents.verifier import VerifierAgent
from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import axi_lite_contracts
from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context
from multigent.verifier_tool.tool_regression.benchmarks.u55c_inspired_int8_gemm_4x4x4 import build_contract_and_tb
from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT
from multigent.verifier_tool import (
    InterfaceCoverageTracker,
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    build_lifecycle_assertion_plan,
    build_lifecycle_feature_plan,
    build_lifecycle_stimulus_plan,
    compile_assertion_feature_plan,
    compile_coverage_feature_plan,
    compile_stimulus_feature_plan,
    install_contract_generated_block,
    render_contract_generated_block,
    validate_contract_generated_block,
)
from multigent.verifier_tool.operation.coverage.plan import (
    build_operation_coverage_plan,
    merge_coverage_plans,
    operation_plan_for_tests,
    synthesize_code_owned_operation_coverage,
)
from multigent.verifier_tool.orchestration.campaign import (
    code_owned_obligations_for_supported_operations,
)
from multigent.verifier_tool.pool import diagnostics as diag


def _axi():
    return deepcopy(axi_lite_contracts())


def _channel(interface, name):
    return next(item for item in interface["channels"] if item["name"] == name)


# Each way to block gemm_core while leaving the fragments the planner needs intact.
def _block_arithmetic(architecture, interface):
    architecture["operations"][0]["arithmetic"]["post_output"] = "nonexistent"
    return "invalid_arithmetic_declaration", diag.CONTRACT_ERROR


def _block_ambiguous_binding(architecture, interface):
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]
    return "ambiguous_transport_binding", diag.CONTRACT_ERROR


def _block_two_busy(architecture, interface):
    interface["signals"].append({"name": "busy_b", "role": "busy", "direction": "output", "channel": None})
    return "ambiguous_status_binding", diag.CONTRACT_ERROR


def _block_internal_object(architecture, interface):
    """A valid contract the tool cannot automate: the operation also produces an internal stage."""

    operation = architecture["operations"][0]
    operation["arithmetic"] = {"classifier_profile": "llm_extension", "reason": "staged datapath"}
    operation["semantics"] = "Compute Y through an internal intermediate stage."
    architecture["data_objects"].append({
        "name": "T_matrix", "role": "intermediate", "data_type": "s32", "dimensions": ["M", "N"],
        "external": False, "producer": operation["name"], "consumers": [operation["name"]],
        "serialization": {"kind": "dense_tensor", "index_order": ["M", "N"], "description": "row-major"},
    })
    operation["outputs"].append("T_matrix")
    return "internal_data_object_not_channel_bound", diag.TOOL_CAPABILITY


BLOCKERS = [_block_arithmetic, _block_ambiguous_binding, _block_two_busy, _block_internal_object]


def _obligation_shape(plan):
    return {
        item["id"]: [
            (b["name"], b["intent"], b["required"], b["minimum_hits"], b["applicability"]["status"])
            for b in item["bins"]
        ]
        for item in plan["coverage_obligations"]
    }


def _merged(architecture, interface, metadata):
    """The production path: canonical sampling attached, then merged with the interface plan."""

    interface_plan = build_interface_coverage_plan(interface)
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    return interface_plan, merge_coverage_plans(interface_plan, operation_plan)


# ---------------------------------------------------------------------------
# The required set does not shrink
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("blocker", BLOCKERS, ids=lambda item: item.__name__)
def test_blocking_an_operation_does_not_change_its_required_obligations_or_features(blocker):
    architecture, interface = _axi()
    good = build_lifecycle_feature_plan(interface, build_architect_operation_metadata(architecture, interface))
    reason, category = blocker(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["operations"] == [] and metadata["unrepresentable_operations"]
    blocked = build_lifecycle_feature_plan(interface, metadata)

    reference = _obligation_shape(build_lifecycle_feature_plan(
        interface,
        build_architect_operation_metadata(*_axi()),
    ))
    assert reference, "the good contract must have lifecycle obligations to compare against"
    assert _obligation_shape(blocked) == reference
    assert sorted(item["id"] for item in blocked["features"]) == sorted(item["id"] for item in good["features"])
    for item in blocked["coverage_obligations"]:
        assert item["automation"]["reason_code"] == reason
        assert item["automation"]["status"] == diag.AUTOMATION_STATUS_BY_CATEGORY[category]
        assert item["automation"]["owner"] == diag.OWNER_BY_CATEGORY[category]
        for spec in item["bins"]:
            # Never `inapplicable` for a tool limit: that would drop it from the denominator.
            assert spec["required"] is True
            assert spec["applicability"]["status"] == "required_reachable"
            assert f"gemm_core:{reason}" in spec["applicability"]["basis"]


@pytest.mark.parametrize("blocker", BLOCKERS, ids=lambda item: item.__name__)
def test_blocked_features_own_no_checker_sampler_or_stimulus_and_are_never_compiled(blocker):
    architecture, interface = _axi()
    blocker(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    blocked = [item for item in plan["features"] if item.get("automation")]
    assert blocked and {item["scope_name"] for item in blocked} == {"gemm_core"}
    for feature in blocked:
        assert diag.feature_automation(feature)["status"] != diag.CODE_OWNED
        assert not diag.is_code_owned(feature)
        assert feature["assertion"]["checker"] is None
        assert feature["coverage"]["sampler"] is None
        assert feature["stimulus"]["strategy"] == "not_automated"
    blocked_ids = {item["id"] for item in blocked}
    for compile_branch in (compile_assertion_feature_plan, compile_coverage_feature_plan, compile_stimulus_feature_plan):
        assert not {entry["id"] for entry in compile_branch(plan)["entries"]} & blocked_ids

    # For everything the tool executes, blocking equals absence...
    absent_architecture = deepcopy(architecture)
    absent_architecture["operations"] = []
    absent = build_architect_operation_metadata(absent_architecture, interface)
    absent_plan = build_lifecycle_feature_plan(interface, absent)
    for compile_branch in (compile_assertion_feature_plan, compile_coverage_feature_plan, compile_stimulus_feature_plan):
        assert compile_branch(plan) == compile_branch(absent_plan)
    interface_plan = build_interface_coverage_plan(interface)
    blocked_assertions = build_lifecycle_assertion_plan(interface_plan, metadata)
    absent_assertions = build_lifecycle_assertion_plan(interface_plan, absent)
    assert blocked_assertions["operations"] == absent_assertions["operations"] == []
    assert blocked_assertions["enabled_by_operation"] == absent_assertions["enabled_by_operation"] == {}
    assert blocked_assertions["features"] == absent_assertions["features"]
    blocked_stimulus = build_lifecycle_stimulus_plan(interface, metadata)
    absent_stimulus = build_lifecycle_stimulus_plan(interface, absent)
    assert blocked_stimulus["scenarios"] == absent_stimulus["scenarios"]
    assert {key: value for key, value in blocked_stimulus.items() if key != "feature_plan"} == {
        key: value for key, value in absent_stimulus.items() if key != "feature_plan"
    }
    # ...but the obligations are only in the blocked plan.
    assert not absent_plan["coverage_obligations"] and plan["coverage_obligations"]


def test_blocked_operations_are_planning_only_and_listed_in_bindings():
    architecture, interface = _axi()
    _block_ambiguous_binding(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    assert plan["bindings"]["operations"] == [], "runtime checkers/drivers must never see a shell"
    (record,) = plan["bindings"]["blocked_operations"]
    assert record["operation_name"] == "gemm_core"
    assert record["fragments"] == {"operation_io": "partial", "lifecycle": "compiled", "arithmetic": "compiled"}
    assert record["automation"]["status"] == "contract_error"
    assert record["obligation_ids"] == sorted(item["id"] for item in plan["coverage_obligations"])
    assert set(record["feature_ids"]) <= set(metadata["unrepresentable_operations"][0]["affected_feature_ids"])
    # A fully compiled contract has no such key at all.
    good = build_lifecycle_feature_plan(interface, build_architect_operation_metadata(*_axi()))
    assert "blocked_operations" not in good["bindings"]
    assert not any("automation" in item for item in good["features"])
    assert not any("automation" in item for item in good["coverage_obligations"])


def test_lifecycle_feature_ids_in_the_diagnostic_match_the_planned_features():
    architecture, interface = _axi()
    _block_arithmetic(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    planned = {item["id"] for item in plan["features"] if item.get("automation")}
    (entry,) = metadata["unrepresentable_operations"]
    lifecycle_ids = {item for item in entry["affected_feature_ids"] if item.startswith("lifecycle.")}
    assert lifecycle_ids == planned and planned
    # Operation-domain features the blocked operation owns are listed too.
    assert any(item.startswith("operation.gemm_core.") for item in entry["affected_feature_ids"])


def test_a_lifecycle_failed_operation_plans_features_but_cannot_plan_obligations():
    # Conflicting command tags leave no usable command channel to plan obligations
    # from; the contract error is blocked at the Architect, and the run can never
    # pass silently on it because the operation is unsupported.
    architecture, interface = _axi()
    next(s for s in interface["signals"] if s["name"] == "left_ptr")["semantic"] += " data_object=B_matrix"
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    assert plan["coverage_obligations"] == []
    assert plan["features"] and all(
        item["coverage"]["obligation_ids"] == [] for item in plan["features"] if item.get("automation")
    )
    support = automatic_campaign_support(metadata, architecture)
    assert support["supported"] is False and support["operations"]["gemm_core"]["compile_blocked"] is True


def test_extension_policy_fields_filter_blocked_features_exactly_like_compiled_ones():
    def build(block):
        architecture, interface = _axi()
        architecture["operations"][0]["lifecycle_policy"]["reset_behavior"] = {
            "extension_request": "lifecycle.reset_policy"
        }
        if block:
            _block_arithmetic(architecture, interface)
        metadata = build_architect_operation_metadata(architecture, interface)
        return build_lifecycle_feature_plan(interface, metadata)

    compiled, blocked = build(False), build(True)
    assert sorted(item["id"] for item in blocked["features"]) == sorted(item["id"] for item in compiled["features"])
    assert _obligation_shape(blocked) == _obligation_shape(compiled)
    assert not any(item["kind"] == "reset_aborts_pending_job" for item in blocked["features"])
    assert not any(
        item["id"].endswith(("reset_abort_phase", "post_reset_purity")) for item in blocked["coverage_obligations"]
    )


def test_a_contract_with_no_command_channel_plans_no_obligations_for_a_blocked_operation_either():
    architecture, interface = _axi()
    interface["channels"] = [item for item in interface["channels"] if item["name"] != "cmd"]
    interface["signals"] = [item for item in interface["signals"] if item.get("channel") != "cmd"]
    good = build_lifecycle_feature_plan(interface, build_architect_operation_metadata(architecture, interface))
    assert good["coverage_obligations"] == []
    _block_arithmetic(architecture, interface)
    blocked = build_lifecycle_feature_plan(interface, build_architect_operation_metadata(architecture, interface))
    assert blocked["coverage_obligations"] == []
    assert sorted(item["id"] for item in blocked["features"]) == sorted(item["id"] for item in good["features"])


# ---------------------------------------------------------------------------
# Tolerance: legacy shapes, duplicates, JSON
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "unrepresentable",
    [None, [], [{"name": "old_op", "reason": "legacy entry with no structure"}],
     [{"name": "old_op", "reason": "x", "shell": None}], ["not a mapping"], [{"name": "", "shell": {}}]],
    ids=["none", "empty", "legacy", "null_shell", "non_mapping", "nameless"],
)
def test_legacy_or_degenerate_entries_are_tolerated_everywhere(unrepresentable):
    architecture, interface = _axi()
    metadata = build_architect_operation_metadata(architecture, interface)
    metadata["unrepresentable_operations"] = unrepresentable
    plan = build_lifecycle_feature_plan(interface, metadata)
    assert "blocked_operations" not in plan["bindings"]
    support = automatic_campaign_support(metadata, architecture)
    assert set(support["operations"]) >= {"gemm_core"}
    interface_plan, merged = _merged(architecture, interface, metadata)
    assert code_owned_obligations_for_supported_operations(
        merged["obligations"], metadata, {"gemm_core"}, reset_signal_name="rst_n"
    )


def test_metadata_without_the_key_or_with_hand_built_shape_still_works():
    architecture, interface = _axi()
    metadata = build_architect_operation_metadata(architecture, interface)
    del metadata["unrepresentable_operations"]
    assert automatic_campaign_support(metadata, architecture)["supported"] is True
    assert build_lifecycle_feature_plan(interface, metadata)["coverage_obligations"]
    assert "blocked_operations" not in automatic_campaign_support(metadata, architecture)


def test_legacy_entry_without_a_shell_is_reported_but_plans_nothing():
    architecture, interface = _axi()
    metadata = {"schema_version": 2, "operations": [], "unrepresentable_operations": [
        {"name": "old_op", "reason": "legacy"},
    ]}
    support = automatic_campaign_support(metadata)
    assert support["supported"] is False
    assert support["operations"]["old_op"]["compile_blocked"] is True
    assert support["operations"]["old_op"]["reason_code"] == "unclassified_metadata_error"
    assert support["blocked_operations"]["old_op"]["message"] == "legacy"
    assert build_lifecycle_feature_plan(interface, metadata)["coverage_obligations"] == []


def test_two_entries_for_one_name_plan_once_and_a_compiled_name_is_never_replanned():
    architecture, interface = _axi()
    _block_arithmetic(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    once = build_lifecycle_feature_plan(interface, metadata)
    metadata["unrepresentable_operations"].append(deepcopy(metadata["unrepresentable_operations"][0]))
    twice = build_lifecycle_feature_plan(interface, metadata)
    assert twice == once and len(twice["bindings"]["blocked_operations"]) == 1

    healthy_architecture, healthy_interface = _axi()
    compiled = build_architect_operation_metadata(healthy_architecture, healthy_interface)
    compiled["unrepresentable_operations"] = deepcopy(metadata["unrepresentable_operations"])
    replanned = build_lifecycle_feature_plan(healthy_interface, compiled)
    assert "blocked_operations" not in replanned["bindings"]
    ids = [item["id"] for item in replanned["coverage_obligations"]]
    assert len(ids) == len(set(ids))


def test_id_collisions_between_distinct_blocked_names_fail_loudly_not_silently():
    architecture, interface = _axi()
    second = deepcopy(architecture["operations"][0])
    second["name"] = "gemm core"          # normalizes to the same obligation id as gemm_core
    architecture["operations"].append(second)
    for operation in architecture["operations"]:
        operation["arithmetic"]["post_output"] = "nonexistent"
    metadata = build_architect_operation_metadata(architecture, interface)
    assert len(metadata["unrepresentable_operations"]) == 2
    interface_plan = build_interface_coverage_plan(interface)
    operation_plan = build_operation_coverage_plan([])
    operation_plan["operation_metadata"] = metadata
    with pytest.raises(ValueError, match="duplicate obligation IDs"):
        merge_coverage_plans(interface_plan, operation_plan)


def test_planning_from_a_json_round_tripped_metadata_is_identical():
    architecture, interface = _axi()
    _block_ambiguous_binding(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    restored = json.loads(json.dumps(metadata))
    assert build_lifecycle_feature_plan(interface, restored) == build_lifecycle_feature_plan(interface, metadata)
    assert automatic_campaign_support(restored, architecture) == automatic_campaign_support(metadata, architecture)
    _, merged = _merged(architecture, interface, metadata)
    assert json.loads(json.dumps(merged["obligations"])) == json.loads(json.dumps(merged["obligations"]))
    tracker_a = InterfaceCoverageTracker(merged).report()
    tracker_b = InterfaceCoverageTracker(json.loads(json.dumps(merged))).report()
    assert tracker_a["missing_bins"] == tracker_b["missing_bins"]
    assert tracker_a["unmet_by_blocker"] == tracker_b["unmet_by_blocker"]


# ---------------------------------------------------------------------------
# Capability report and code-owned attribution
# ---------------------------------------------------------------------------

def test_capability_report_marks_a_blocked_operation_unsupported_and_says_why():
    architecture, interface = _axi()
    _block_internal_object(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    report = automatic_campaign_support(metadata, architecture)
    assert report["supported"] is False
    assert report["any_operation_supported"] is False
    info = report["operations"]["gemm_core"]
    assert info == {
        "supported": False,
        "reasons": ["gemm_core:operation_not_compiled=internal_data_object_not_channel_bound"],
        "arithmetic_reasons": [],
        "protocol_lifecycle_supported": False,
        "compile_blocked": True,
        "category": "tool_capability",
        "owner": "verifier_tool",
        "reason_code": "internal_data_object_not_channel_bound",
    }
    blocked = report["blocked_operations"]["gemm_core"]
    assert blocked["blocked_by"] == ["gemm_core:internal_data_object_not_channel_bound"]
    assert blocked["resolution_hint"] and blocked["affected_feature_ids"]
    assert "gemm_core:operation_not_compiled=internal_data_object_not_channel_bound" in report["reasons"]


def _two_operation_contracts(block_second: bool):
    architecture, interface = _axi()
    second = deepcopy(architecture["operations"][0])
    second["name"] = "second_op"
    architecture["operations"].append(second)
    if block_second:
        second["arithmetic"]["post_output"] = "nonexistent"
    return architecture, interface


def test_a_blocked_sibling_never_weakens_or_borrows_the_supported_operations_credit():
    architecture, interface = _two_operation_contracts(block_second=True)
    metadata = build_architect_operation_metadata(architecture, interface)
    assert [item["operation_name"] for item in metadata["operations"]] == ["gemm_core"]
    report = automatic_campaign_support(metadata, architecture)
    assert report["supported"] is False and report["any_operation_supported"] is True
    assert report["operations"]["gemm_core"]["supported"] is True
    assert report["operations"]["second_op"]["compile_blocked"] is True
    _, merged = _merged(architecture, interface, metadata)
    owned = code_owned_obligations_for_supported_operations(
        merged["obligations"], metadata, {"gemm_core"}, reset_signal_name="rst_n",
        protocol_lifecycle_ready_operations={"gemm_core"},
    )
    assert {item for item in owned if item.startswith("operation.gemm_core.")}
    assert not {item for item in owned if item.startswith("operation.second_op.")}
    second_obligations = {
        item["id"] for item in merged["obligations"] if item["id"].startswith("operation.second_op.")
    }
    assert second_obligations and not second_obligations & owned

    # The blocked sibling occupies the shared memory channels too, so those
    # protocol obligations are no longer credited to the supported one alone...
    healthy_architecture, healthy_interface = _two_operation_contracts(block_second=False)
    healthy = build_architect_operation_metadata(healthy_architecture, healthy_interface)
    _, healthy_merged = _merged(healthy_architecture, healthy_interface, healthy)
    healthy_owned = code_owned_obligations_for_supported_operations(
        healthy_merged["obligations"], healthy, {"gemm_core", "second_op"}, reset_signal_name="rst_n",
        protocol_lifecycle_ready_operations={"gemm_core", "second_op"},
    )
    shared_protocol = {
        item for item in healthy_owned if not item.startswith("operation.")
    } - {"signal.rst_n.reset_behavior"}
    assert shared_protocol, "with both operations supported the shared channels are credited"
    assert not shared_protocol & owned - {"signal.rst_n.reset_behavior"}, (
        "a channel shared with a blocked operation must not be credited as code-owned"
    )


def test_blocking_only_adds_required_bins_and_never_removes_any():
    architecture, interface = _axi()
    metadata = build_architect_operation_metadata(architecture, interface)
    _, good = _merged(architecture, interface, metadata)
    architecture_b, interface_b = _axi()
    _block_arithmetic(architecture_b, interface_b)
    blocked_metadata = build_architect_operation_metadata(architecture_b, interface_b)
    _, blocked = _merged(architecture_b, interface_b, blocked_metadata)

    def required(plan):
        return {
            f"{item['id']}.{b['name']}" for item in plan["obligations"] for b in item["bins"] if b.get("required", True)
        }

    # Operation-domain coverpoints are Verifier-owned when the operation is blocked
    # (no code-owned math), so they are absent from the seed; every *lifecycle and
    # protocol* required bin is still there.
    good_lifecycle_protocol = {item for item in required(good) if not item.startswith("operation.gemm_core.accum")}
    missing = {
        item for item in good_lifecycle_protocol
        if item not in required(blocked) and item.startswith(("operation.gemm_core.job", "operation.gemm_core.reset", "operation.gemm_core.post_reset", "channel.", "signal.", "group."))
    }
    assert missing == set()


def test_protocol_obligations_and_features_are_identical_with_or_without_a_blocked_operation():
    # Protocol coverage is planned from the interface alone; an operation that fails to
    # compile must neither add to nor remove from it.
    architecture, interface = _axi()
    good_metadata = build_architect_operation_metadata(architecture, interface)
    _, good = _merged(architecture, interface, good_metadata)
    architecture_b, interface_b = _axi()
    _block_ambiguous_binding(architecture_b, interface_b)
    blocked_metadata = build_architect_operation_metadata(architecture_b, interface_b)
    _, blocked = _merged(architecture_b, interface_b, blocked_metadata)

    def protocol(plan):
        return {item["id"]: item for item in plan["obligations"] if not item["id"].startswith("operation.")}

    assert protocol(blocked) == protocol(good) and protocol(good)
    good_interface_plan = build_interface_coverage_plan(interface)
    blocked_interface_plan = build_interface_coverage_plan(interface_b)
    assert blocked_interface_plan["obligations"] == good_interface_plan["obligations"]
    assert blocked_interface_plan["feature_plan"] == good_interface_plan["feature_plan"]


@pytest.mark.parametrize(
    "name,obligations,required_bins",
    [("u55c", 37, 74), ("hls", 83, 152)],
)
def test_fully_supported_benchmarks_keep_their_obligation_counts(name, obligations, required_bins):
    """The two checked-in fully supported contracts must not gain or lose a single required bin."""

    import yaml

    if name == "u55c":
        architecture, interface, *_ = build_contract_and_tb.build_architecture_contract()
    else:
        root = BENCHMARKS_ROOT / "int8_gemm_hls_golden"
        architecture = yaml.safe_load((root / "architecture_contract.yaml").read_text())
        interface = yaml.safe_load((root / "interface_contract.yaml").read_text())
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    interface_plan = build_interface_coverage_plan(interface)
    operation_plan = build_operation_coverage_plan(synthesize_code_owned_operation_coverage([], architecture, metadata))
    operation_plan["operation_metadata"] = metadata
    merged = merge_coverage_plans(interface_plan, operation_plan)
    assert len(merged["obligations"]) == obligations
    assert sum(1 for item in merged["obligations"] for b in item["bins"] if b.get("required", True)) == required_bins
    assert not any("automation" in item for item in merged["obligations"])
    assert automatic_campaign_support(metadata, architecture)["supported"] is True


# ---------------------------------------------------------------------------
# The gate: verdict by hits, one required set
# ---------------------------------------------------------------------------

BLOCKER_ID = "gemm_core:internal_data_object_not_channel_bound"


def _blocked_only_tracker():
    """A tracker whose only obligations are the blocked operation's (real merged plan, filtered)."""

    architecture, interface = _axi()
    _block_internal_object(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    _, merged = _merged(architecture, interface, metadata)
    obligations = [item for item in merged["obligations"] if item.get("automation")]
    return InterfaceCoverageTracker({**merged, "obligations": obligations}), obligations


def test_unhit_required_bins_fail_and_name_their_blocker_and_hits_by_anyone_clear_them():
    tracker, obligations = _blocked_only_tracker()
    total = sum(len(item["bins"]) for item in obligations)
    assert total == 12
    reset_abort = next(
        item for item in obligations if item["id"].endswith(".reset_abort_phase")
    )
    assert "output" not in {item["name"] for item in reset_abort["bins"]}
    report = tracker.report()
    assert report["status"] == "FAIL"
    assert report["required_bins"] == total and report["hit_bins"] == 0
    assert report["verdicts"]["scenario_coverage"] == "FAIL"
    assert report["unmet_by_blocker"] == {BLOCKER_ID: sorted(report["missing_bins"])}
    # The domain state is a roll-up of the feature-level records: the operation's lifecycle
    # features are blocked, the reset-output feature is still code-owned.
    state = report["automation_state"]["lifecycle"]
    assert state["state"] == "partial" and state["blocked"] > 0 and state["code_owned"] >= 1
    assert list(state["blocked_by"]) == [BLOCKER_ID]
    assert len(report["missing_bins"]) == total

    # Nothing special-cases a blocked bin: whoever records the hit closes it.
    for item in obligations:
        for spec in item["bins"]:
            tracker._hit(item["id"], spec["name"])
    covered = tracker.report()
    assert covered["missing_bins"] == [] and covered["hit_bins"] == total
    assert covered["status"] == "PASS"
    assert "unmet_by_blocker" not in covered


def test_a_partly_hit_plan_reports_only_the_still_unmet_bins_under_the_blocker():
    tracker, obligations = _blocked_only_tracker()
    first = obligations[0]
    tracker._hit(first["id"], first["bins"][0]["name"])
    report = tracker.report()
    remaining = report["unmet_by_blocker"][BLOCKER_ID]
    assert f"{first['id']}.{first['bins'][0]['name']}" not in remaining
    assert len(remaining) == len(report["missing_bins"]) == 11


def test_a_plan_without_blocked_obligations_reports_no_blocker_summary():
    architecture, interface = _axi()
    metadata = build_architect_operation_metadata(architecture, interface)
    _, merged = _merged(architecture, interface, metadata)
    report = InterfaceCoverageTracker(merged).report()
    assert "unmet_by_blocker" not in report and "automation_state" not in report


def test_domain_state_is_only_a_roll_up_of_feature_level_records():
    architecture, interface = _two_operation_contracts(block_second=True)
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    summary = diag.summarize_feature_automation({"lifecycle": plan})["lifecycle"]
    assert summary["state"] == "partial"
    assert summary["blocked"] == len([item for item in plan["features"] if item.get("automation")])
    assert summary["code_owned"] == len(plan["features"]) - summary["blocked"]
    assert list(summary["blocked_by"]) == ["second_op:invalid_arithmetic_declaration"]

    healthy = build_lifecycle_feature_plan(interface, build_architect_operation_metadata(*_two_operation_contracts(False)))
    assert diag.summarize_feature_automation({"lifecycle": healthy})["lifecycle"] == {
        "state": "ready", "code_owned": len(healthy["features"]), "blocked": 0, "blocked_by": {},
    }
    only_blocked = {"features": [item for item in plan["features"] if item.get("automation")]}
    assert diag.summarize_feature_automation({"x": only_blocked})["x"]["state"] == "blocked"
    assert diag.summarize_feature_automation({"empty": {"features": []}})["empty"]["state"] == "ready"


def test_automation_record_prefers_the_architect_actionable_cause():
    architecture, interface = _axi()
    _block_internal_object(architecture, interface)          # tool limit, found first
    interface["signals"].append({"name": "busy_b", "role": "busy", "direction": "output", "channel": None})
    metadata = build_architect_operation_metadata(architecture, interface)
    (entry,) = metadata["unrepresentable_operations"]
    codes = [item["reason_code"] for item in entry["diagnostics"]]
    assert codes == ["internal_data_object_not_channel_bound", "ambiguous_status_binding"]
    record = diag.automation_record(entry["diagnostics"])
    # The tool limit was hit first, but the Architect-fixable defect owns the status.
    assert record["status"] == "contract_error" and record["reason_code"] == "ambiguous_status_binding"
    assert record["blocked_by"] == sorted(item["blocked_by"] for item in entry["diagnostics"])
    assert diag.automation_record([]) == {"status": "code_owned"}
    only_limit = diag.automation_record([entry["diagnostics"][0]])
    assert only_limit == {
        "status": "tool_capability_required", "owner": "verifier_tool",
        "reason_code": "internal_data_object_not_channel_bound",
        "blocked_by": ["gemm_core:internal_data_object_not_channel_bound"],
    }


# ---------------------------------------------------------------------------
# Generated block and Verifier prompt
# ---------------------------------------------------------------------------

def test_generated_block_renders_and_validates_with_a_blocked_operation():
    architecture, interface = _axi()
    _block_ambiguous_binding(architecture, interface)
    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(interface_plan, architecture, include_automatic_campaign=False)
    ast.parse(block)
    installed = install_contract_generated_block(
        "import cocotb\n", interface_plan, architecture, include_automatic_campaign=False
    )
    ast.parse(installed)
    validate_contract_generated_block(installed, interface_plan, architecture, include_automatic_campaign=False)
    with pytest.raises(ValueError, match="modified"):
        validate_contract_generated_block(
            installed.replace("CONTRACT_LIFECYCLE_ASSERTION_PLAN", "TAMPERED_PLAN", 1),
            interface_plan, architecture, include_automatic_campaign=False,
        )
    line = next(item for item in block.splitlines() if item.startswith("CONTRACT_LIFECYCLE_ASSERTION_PLAN = "))
    plan = ast.literal_eval(line.split(" = ", 1)[1])
    assert plan["operations"] == [] and plan["enabled_by_operation"] == {}
    assert plan["feature_plan"]["bindings"]["blocked_operations"][0]["operation_name"] == "gemm_core"


def _blocked_verifier_context(mutate):
    context = generic_fir_context()
    mutate(context["frozen_architecture"]["architecture_contract"])
    return context


def test_verifier_prompt_explains_uncompilable_operations_with_structured_evidence():
    context = _blocked_verifier_context(lambda arch: arch["operations"][0].update(inputs=["ghost"]))
    task = VerifierAgent._build_task(context)
    assert "OPERATIONS THAT COULD NOT BE COMPILED" in task
    assert "filter [unknown_or_duplicate_data_object; contract_error; owner=architect_contract]" in task
    assert "resolution: List only declared data objects" in task
    assert "REMAIN in the deterministic plan" in task
    assert "known_verification_gaps" in task
    # The old wording that told the Verifier a lifecycle policy problem was 'unresolvable'
    # is gone; the two are distinguished by category now.
    assert "an unresolvable\n  one" not in task


def test_verifier_prompt_has_no_such_section_for_a_compiled_contract():
    task = VerifierAgent._build_task(generic_fir_context())
    assert "OPERATIONS THAT COULD NOT BE COMPILED" not in task


def test_a_feature_the_tool_cannot_own_is_never_offered_as_a_reusable_sibling():
    """Extension reuse resolves tool-owned siblings a Verifier bundle must preserve; an
    operation that failed to compile has none to preserve."""

    from multigent.verifier_tool.tool_regression.integration.test_tag_pool_and_contract_preflight import _request
    from multigent.verifier_tool import resolve_extension_reuse

    def with_request(architecture):
        architecture["verification_extensions"] = [
            _request("lifecycle.gemm_core_custom", "lifecycle", "gemm_core_custom",
                     {"scope": "operation", "name": "gemm_core"}, {})
        ]

    architecture, interface = _axi()
    with_request(architecture)
    healthy = resolve_extension_reuse(architecture, interface)

    architecture_b, interface_b = _axi()
    _block_arithmetic(architecture_b, interface_b)
    with_request(architecture_b)
    blocked = resolve_extension_reuse(architecture_b, interface_b)

    def preserved(report):
        return {
            item for entry in report["entries"] for item in entry.get("preserved_feature_ids", [])
            if item.startswith("lifecycle.")
        }

    assert preserved(healthy), "the healthy operation offers its lifecycle siblings for reuse"
    assert not preserved(blocked), "a blocked operation has no tool-owned sibling to preserve"
