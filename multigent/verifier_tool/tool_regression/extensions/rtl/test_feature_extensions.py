from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.verifier import (
    VERIFIER_OUTPUT_SCHEMA,
    VERIFIER_SOURCE_REPAIR_SCHEMA,
    VerifierAgent,
)
from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import axi_lite_contracts
from multigent.verifier_tool.tool_regression.integration.test_lifecycle_policy_pool import _contracts
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_feature_extension_manifest,
    build_lifecycle_assertion_plan,
    build_lifecycle_feature_plan,
    build_lifecycle_stimulus_plan,
    check_lifecycle_assertions,
    compile_assertion_feature_plan,
    extension_bundle_schema,
    extension_request_schema,
    interface_vocabulary_extensions,
    render_requested_extension_worklist,
    validate_architect_extension_requests,
    validate_verifier_extension_bundles,
    validate_interface_semantics,
    validate_interface_signal_roles,
)


def _request(operation_name: str = "job") -> dict:
    return {
        "id": "lifecycle.error_three_cycle_pulse",
        "domain": "lifecycle",
        "feature_name": "error_three_cycle_pulse",
        "target": {"scope": "operation", "name": operation_name},
        "semantics": {
            "summary": "Hold error high for exactly three sampled cycles.",
            "trigger": "An illegal command is accepted while no job is active.",
            "required_behavior": [
                "Error is high on each of the next three sampled cycles.",
                "No legal job starts from the illegal command.",
            ],
            "end_condition": "Error is low on the fourth sampled cycle.",
            "forbidden_behavior": ["Error remains high for a fourth cycle."],
        },
        "reason": "The lifecycle pool supports one-cycle and sticky errors only.",
        "parameters": {"cycles": 3},
        "replaces_contract_paths": [
            f"/operations/{operation_name}/lifecycle_policy/error_style"
        ],
        "required_observations": [
            {
                "name": "illegal_command_accept",
                "kind": "event",
                "description": "Accepted illegal command event.",
            },
            {
                "name": "error_signal",
                "kind": "signal",
                "description": "The bound DUT error indication.",
            },
        ],
        "related_builtin_features": ["lifecycle.error_behavior"],
    }


def _lifecycle_policy_request(field: str, operation_name: str = "gemm_core") -> dict:
    identity = f"lifecycle.{field}_extension"
    return {
        "id": identity,
        "domain": "lifecycle",
        "feature_name": f"{field}_extension",
        "target": {"scope": "operation", "name": operation_name},
        "semantics": {
            "summary": f"Contract-local behavior for lifecycle policy field {field}.",
            "trigger": f"The event governed by {field} occurs.",
            "required_behavior": [
                f"The Verifier checks the frozen contract behavior for {field}."
            ],
            "end_condition": f"The {field} behavior reaches its declared terminal state.",
            "forbidden_behavior": [
                f"No built-in {field} behavior is assumed by the deterministic runtime."
            ],
        },
        "reason": f"The closed lifecycle pool does not represent this {field} behavior.",
        "replaces_contract_paths": [
            f"/operations/{operation_name}/lifecycle_policy/{field}"
        ],
        "required_observations": [
            {
                "name": "lifecycle_event",
                "kind": "event",
                "description": f"Observed event governed by {field}.",
            }
        ],
        "related_builtin_features": [f"lifecycle.{field}"],
    }


def _protocol_request() -> dict:
    return {
        "id": "protocol.bounded_ready_recovery",
        "domain": "protocol",
        "feature_name": "bounded_ready_recovery",
        "target": {"scope": "channel", "name": "cmd"},
        "semantics": {
            "summary": "READY must recover within seven cycles after VALID is presented.",
            "trigger": "VALID is asserted while READY is low.",
            "required_behavior": ["READY is observed within seven sampled cycles."],
            "end_condition": "The transfer is accepted or the seventh cycle expires.",
            "forbidden_behavior": ["READY remains low for eight sampled cycles."],
        },
        "reason": "The generic ready/valid pool has stall bins but no bounded-liveness rule.",
        "parameters": {"maximum_cycles": 7},
        "required_observations": [
            {"name": "valid", "kind": "signal", "description": "Bound VALID signal."},
            {"name": "ready", "kind": "signal", "description": "Bound READY signal."},
        ],
        "related_builtin_features": ["stall_stability"],
    }


def _protocol_bundle() -> dict:
    implementation = {
        "kind": "verifier_python",
        "name": "bounded_ready_recovery",
        "file": "tests/test_protocol_extension.py",
    }
    return {
        "schema_version": 1,
        "request_id": "protocol.bounded_ready_recovery",
        "id": "protocol.bounded_ready_recovery",
        "domain": "protocol",
        "feature_name": "bounded_ready_recovery",
        "target": {"scope": "channel", "name": "cmd"},
        "description": "Contract-local bounded READY recovery verification.",
        "bindings": {"valid": "cmd_valid", "ready": "cmd_ready"},
        "reuse": {
            "based_on_features": ["stall_stability"],
            "helpers": ["channel_schedule"],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": "check_ready_recovery"},
            "parameters": {"maximum_cycles": 7},
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "sample_ready_recovery"},
            "parameters": {"maximum_cycles": 7},
            "bins": [
                {
                    "name": "seven_cycle_recovery",
                    "intent": "Observe READY recovery on the seventh cycle.",
                    "predicate": {"recovery_cycle": 7},
                }
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "drive_ready_recovery"},
            "parameters": {"stall_cycles": 7},
            "scenarios": [
                {
                    "name": "maximum_legal_stall",
                    "intent": "Hold the receiver unavailable for seven cycles.",
                    "parameters": {"stall_cycles": 7},
                }
            ],
        },
    }


def _protocol_source() -> dict:
    return {
        "path": "test_protocol_extension.py",
        "purpose": "cocotb test for a contract-local protocol behavior",
        "categories": ["protocol"],
        "content": """
import cocotb
from cocotb.triggers import RisingEdge

def check_ready_recovery(snapshot, state):
    assert snapshot["recovery_cycle"] <= state["maximum_cycles"]

def sample_ready_recovery(snapshot, state):
    return snapshot["recovery_cycle"]

async def drive_ready_recovery(dut):
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    snapshot = {"recovery_cycle": 7}
    state = {"maximum_cycles": 7}
    check_ready_recovery(snapshot, state)
    sample_ready_recovery(snapshot, state)
    await drive_ready_recovery(dut)
""",
    }


def _bundle() -> dict:
    implementation = {
        "kind": "verifier_python",
        "name": "error_three_cycle_pulse",
        "file": "tests/test_error_extension.py",
    }
    return {
        "schema_version": 1,
        "request_id": "lifecycle.error_three_cycle_pulse",
        "id": "lifecycle.error_three_cycle_pulse",
        "domain": "lifecycle",
        "feature_name": "error_three_cycle_pulse",
        "target": {"scope": "operation", "name": "job"},
        "description": "Contract-local three-cycle error verification.",
        "bindings": {
            "illegal_command_accept": {"valid": "cv", "ready": "cr", "payload": "opcode"},
            "error_signal": "err",
        },
        "reuse": {
            "based_on_features": ["lifecycle.error_behavior"],
            "helpers": ["drive_accepted_command"],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": "check_error_three_cycle"},
            "parameters": {"cycles": 3},
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "sample_error_three_cycle"},
            "parameters": {"cycles": 3},
            "bins": [
                {
                    "name": "exact_three_cycles",
                    "intent": "Observe exactly three asserted cycles.",
                    "predicate": {"observed_cycles": 3},
                }
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "drive_error_three_cycle"},
            "parameters": {"illegal_opcode": 0},
            "scenarios": [
                {
                    "name": "illegal_then_recover",
                    "intent": "Trigger the error and then run a legal job.",
                    "parameters": {"illegal_opcode": 0, "legal_opcode": 1},
                }
            ],
        },
    }


def _source() -> dict:
    return {
        "path": "test_error_extension.py",
        "purpose": "cocotb test for contract-local lifecycle extension",
        "categories": ["lifecycle"],
        "content": """
import cocotb
from cocotb.triggers import RisingEdge

def check_error_three_cycle(snapshot, state):
    assert snapshot["error_high_cycles"] == state["required_cycles"]

def sample_error_three_cycle(snapshot, state):
    return snapshot["error_high_cycles"]

async def drive_error_three_cycle(dut):
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_contract_local_error_extension(dut):
    snapshot = {"error_high_cycles": 3}
    state = {"required_cycles": 3}
    check_error_three_cycle(snapshot, state)
    sample_error_three_cycle(snapshot, state)
    await drive_error_three_cycle(dut)
""",
    }


def test_extension_request_and_bundle_have_a_stable_machine_readable_boundary() -> None:
    request = _request()
    bundle = _bundle()
    Draft202012Validator(extension_request_schema()).validate(request)
    Draft202012Validator(extension_bundle_schema()).validate(bundle)
    architecture = {"verification_extensions": [request]}
    assert validate_verifier_extension_bundles(
        architecture, [bundle], source_files=[_source()]
    ) == []
    manifest = build_feature_extension_manifest(
        architecture, [bundle], source_files=[_source()]
    )
    assert manifest["status"] == "contract_local_only"
    assert manifest["promotion"] == "not_implemented"
    assert manifest["entries"][0]["request"] == request
    assert manifest["entries"][0]["implementation"] == bundle


def test_extension_bundle_rejects_noop_assertion_constant_coverage_and_idle_stimulus() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    source["content"] = """
import cocotb

def check_ready_recovery(snapshot, state):
    return None

def sample_ready_recovery(snapshot, state):
    return 7

async def drive_ready_recovery(dut):
    return None

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    check_ready_recovery({}, {})
    sample_ready_recovery({}, {})
    await drive_ready_recovery(dut)
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
    )
    assert any("no observable decision" in error for error in errors)
    assert any("constant coverage" in error for error in errors)
    assert any("await executable stimulus work" in error for error in errors)


def test_verifier_api_schemas_expose_contract_local_extension_bundles() -> None:
    agent = VerifierAgent()
    for schema_path in (VERIFIER_OUTPUT_SCHEMA, VERIFIER_SOURCE_REPAIR_SCHEMA):
        schema = agent.load_output_schema(schema_path)
        assert "feature_extensions" in schema["properties"]
        Draft202012Validator.check_schema(schema)


def test_residual_extension_cannot_be_an_inert_existing_primitive_claim() -> None:
    bundle = _protocol_bundle()
    for branch_name in ("assertion", "coverage", "stimulus"):
        implementation = bundle[branch_name]["implementation"]
        implementation["kind"] = "existing_primitive"
        implementation.pop("file", None)
        implementation.pop("symbol", None)
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [_protocol_request()]},
        [bundle],
        source_files=[_protocol_source()],
    )
    assert sum("is not one of" in error for error in errors) == 3, errors


def test_bundle_must_bind_every_architect_required_observation() -> None:
    bundle = _bundle()
    bundle["bindings"].pop("error_signal")
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [_request()]},
        [bundle],
        source_files=[_source()],
    )
    assert any("error_signal" in error for error in errors)


def test_bundle_python_implementation_must_be_reachable_from_generated_test() -> None:
    source = _source()
    source["content"] = source["content"].replace(
        "    check_error_three_cycle(snapshot, state)\n", ""
    )
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [_request()]},
        [_bundle()],
        source_files=[source],
    )
    assert any(
        "assertion symbol 'check_error_three_cycle' is not reachable" in error
        for error in errors
    )


def test_one_lifecycle_extension_preserves_unaffected_tool_owned_features() -> None:
    architecture, interface = axi_lite_contracts()
    request = _request("gemm_core")
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["error_style"] = {
        "extension_request": request["id"]
    }
    assert validate_architect_extension_requests(architecture, interface) == []

    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    plan = build_lifecycle_feature_plan(interface, metadata)
    checkers = {
        item["implementation"]
        for item in compile_assertion_feature_plan(plan)["entries"]
    }
    assert "illegal_command_errors_without_start" not in checkers
    assert "response_error_follows_nonokay" not in checkers
    assert "status_pulses_are_one_cycle" in checkers
    assert "completion_matches_final_output" in checkers
    assert "busy_tracks_active_job" in checkers

    lifecycle_bins = {
        item["id"]: {entry["name"] for entry in item["bins"]}
        for item in plan["coverage_obligations"]
    }
    assert lifecycle_bins["operation.gemm_core.job_lifecycle"] == {
        "accepted", "active", "retired", "aborted"
    }
    scenario_kinds = {
        item["kind"] for item in build_lifecycle_stimulus_plan(interface, metadata)["scenarios"]
    }
    assert "legal_command" in scenario_kinds
    assert "illegal_command" not in scenario_kinds
    assert "illegal_then_legal_recovery" not in scenario_kinds

    support = automatic_campaign_support(metadata, architecture)
    operation = support["operations"]["gemm_core"]
    assert operation["supported"] is False
    assert operation["known_scope_campaign_supported"] is True
    assert operation["lifecycle_extension_fields"] == ["error_style"]
    assert support["any_operation_supported"] is True


@pytest.mark.parametrize(
    ("field", "removed_checkers"),
    [
        (
            "job_acceptance",
            {
                "accepted_command_starts_job",
                "single_inflight_job_enforced",
                "illegal_command_errors_without_start",
                "no_output_without_active_job",
                "busy_tracks_active_job",
            },
        ),
        ("job_overlap", {"single_inflight_job_enforced"}),
        ("busy_behavior", {"busy_tracks_active_job"}),
        (
            "completion_style",
            {"completion_matches_final_output", "status_pulses_are_one_cycle"},
        ),
        ("completion_timing", {"completion_matches_final_output"}),
        ("illegal_command_behavior", {"illegal_command_errors_without_start"}),
        ("error_style", {"illegal_command_errors_without_start", "response_error_follows_nonokay"}),
        ("error_timing", {"illegal_command_errors_without_start", "response_error_follows_nonokay"}),
        ("reset_behavior", {"reset_aborts_pending_job"}),
    ],
)
def test_every_lifecycle_policy_extension_field_removes_only_dependent_features(
    field: str, removed_checkers: set[str]
) -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_policy_request(field)
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"][field] = {
        "extension_request": request["id"]
    }

    assert validate_architect_extension_requests(architecture, interface) == []
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    plan = build_lifecycle_feature_plan(interface, metadata)
    selected = {
        str(item["kind"])
        for item in plan["features"]
        if item.get("scope") == "operation"
    }
    all_checkers = {
        "accepted_command_starts_job",
        "single_inflight_job_enforced",
        "illegal_command_errors_without_start",
        "response_error_follows_nonokay",
        "no_output_without_active_job",
        "busy_tracks_active_job",
        "completion_matches_final_output",
        "reset_aborts_pending_job",
        "status_pulses_are_one_cycle",
    }
    assert selected == all_checkers - removed_checkers
    # The fixture's completion indication is a pulse while its error is sticky.
    # Extending error_style therefore leaves the completion pulse checker active;
    # extending completion_style leaves no observable pulse for that checker.
    if field == "error_style":
        assert "status_pulses_are_one_cycle" in selected


def test_both_extended_pulse_styles_remove_shared_status_pulse_checker() -> None:
    architecture, interface = axi_lite_contracts()
    requests = [
        _lifecycle_policy_request("completion_style"),
        _lifecycle_policy_request("error_style"),
    ]
    architecture["verification_extensions"] = requests
    for field, request in zip(("completion_style", "error_style"), requests):
        architecture["operations"][0]["lifecycle_policy"][field] = {
            "extension_request": request["id"]
        }
    assert validate_architect_extension_requests(architecture, interface) == []
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    selected = {
        str(item["kind"])
        for item in plan["features"]
        if item.get("scope") == "operation"
    }
    assert "completion_matches_final_output" not in selected
    assert "illegal_command_errors_without_start" not in selected
    assert "response_error_follows_nonokay" not in selected
    assert "status_pulses_are_one_cycle" not in selected


@pytest.mark.parametrize(
    ("field", "expected_bins"),
    [
        ("completion_style", {"accepted", "active", "aborted"}),
        ("busy_behavior", {"accepted", "retired", "aborted"}),
        ("reset_behavior", {"accepted", "active", "retired"}),
    ],
)
def test_lifecycle_extension_filters_dependent_coverage_and_stimulus_only(
    field: str, expected_bins: set[str]
) -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_policy_request(field)
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"][field] = {
        "extension_request": request["id"]
    }
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    lifecycle = next(
        item
        for item in plan["coverage_obligations"]
        if item["id"] == "operation.gemm_core.job_lifecycle"
    )
    assert {str(item["name"]) for item in lifecycle["bins"]} == expected_bins

    scenarios = build_lifecycle_stimulus_plan(interface, metadata)["scenarios"]
    scenario_kinds = {str(item["kind"]) for item in scenarios}
    assert "legal_command" in scenario_kinds
    if field == "reset_behavior":
        assert "reset_abort" not in scenario_kinds
        assert "abort_then_clean_job" not in scenario_kinds
        obligation_ids = {str(item["id"]) for item in plan["coverage_obligations"]}
        assert "operation.gemm_core.reset_abort_phase" not in obligation_ids
        assert "operation.gemm_core.post_reset_purity" not in obligation_ids
    else:
        assert "reset_abort" in scenario_kinds


def test_extended_reset_behavior_does_not_apply_builtin_abort_state_transition() -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_policy_request("reset_behavior")
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["reset_behavior"] = {
        "extension_request": request["id"]
    }
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_assertion_plan(interface, metadata)
    names = {str(item["name"]) for item in interface["signals"]}
    base = {name: 0 for name in names}
    base["rst_n"] = 1
    state: dict = {}

    check_lifecycle_assertions(
        {**base, "cmd_valid": 1, "cmd_ready": 1, "opcode": 1},
        plan,
        state,
    )
    assert state["operations"]["gemm_core"]["active"] is True
    check_lifecycle_assertions({**base, "rst_n": 0}, plan, state)
    assert state["operations"]["gemm_core"]["active"] is True


def test_protocol_behavior_extension_runs_request_to_bundle_boundary() -> None:
    architecture, interface = axi_lite_contracts()
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    architecture["verification_extensions"] = [request]

    Draft202012Validator(extension_request_schema()).validate(request)
    Draft202012Validator(extension_bundle_schema()).validate(bundle)
    assert validate_architect_extension_requests(architecture, interface) == []
    assert validate_verifier_extension_bundles(
        architecture, [bundle], source_files=[source]
    ) == []
    manifest = build_feature_extension_manifest(
        architecture, [bundle], source_files=[source]
    )
    assert manifest["status"] == "contract_local_only"
    assert manifest["promotion"] == "not_implemented"
    entry = manifest["entries"][0]
    assert entry["request"]["domain"] == "protocol"
    assert entry["implementation"]["target"] == {
        "scope": "channel",
        "name": "cmd",
    }


def test_extension_worklist_names_only_the_missing_feature() -> None:
    text = render_requested_extension_worklist(
        {"verification_extensions": [_request()]}
    )
    assert "error_three_cycle_pulse" in text
    assert "preserve_tool_owned_siblings: true" in text
    assert "assertion" in text and "coverage" in text and "stimulus" in text


def test_lifecycle_extension_reference_must_point_to_exact_contract_path() -> None:
    architecture, interface = _contracts()
    request = deepcopy(_request())
    request["replaces_contract_paths"] = []
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["error_style"] = {
        "extension_request": request["id"]
    }
    errors = validate_architect_extension_requests(architecture, interface)
    assert any("replaces_contract_paths" in error for error in errors)


def test_contract_local_signal_role_can_be_declared_without_mutating_role_pool() -> None:
    interface = {
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {
                "name": "credits",
                "direction": "input",
                "protocol_profile": "custom",
            }
        ],
        "signals": [
            {
                "name": "clk",
                "role": "clock",
                "semantic_class": None,
                "channel": None,
                "direction": "input",
                "width": "1",
            },
            {
                "name": "rst_n",
                "role": "reset",
                "semantic_class": None,
                "channel": None,
                "direction": "input",
                "width": "1",
                "semantic": "active-low reset",
            },
            {
                "name": "credit_count",
                "role": "credit_count",
                "semantic_class": None,
                "channel": "credits",
                "direction": "input",
                "width": "4",
            }
        ],
    }
    request = {
        "id": "protocol.credit_count_role",
        "domain": "protocol",
        "feature_name": "credit_count_role",
        "target": {"scope": "signal", "name": "credit_count"},
        "semantics": {
            "summary": "Credit count limits transfers accepted by the receiver.",
            "trigger": "The count changes on a contract-defined credit event.",
            "required_behavior": ["No transfer is accepted with zero credits."],
            "end_condition": "A returned credit permits a later transfer.",
            "forbidden_behavior": [],
        },
        "reason": "The closed Role Pool has no credit-count role.",
        "contract_vocabulary": {
            "pool": "signal_role",
            "name": "credit_count",
            "definition": {
                "description": "Available receiver transaction credits.",
                "coverage_tags": ["flow_control", "credit_boundary"],
                "category": "channel_flow_control",
                "channel_binding": "required",
                "direction_relation": "same_as_channel",
                "allowed_directions": ["input", "output"],
                "semantic_class_binding": "optional",
            },
        },
        "required_observations": [
            {
                "name": "credit_count_signal",
                "kind": "signal",
                "description": "Observed DUT credit count.",
            }
        ],
    }
    architecture = {"verification_extensions": [request]}
    assert validate_architect_extension_requests(architecture, interface) == []
    roles, classes = interface_vocabulary_extensions(architecture)
    assert classes == {}
    assert "credit_count" in roles
    assert validate_interface_signal_roles(
        interface, role_extensions=roles
    ) == []
    assert validate_interface_semantics(
        interface, role_extensions=roles
    ) == []
