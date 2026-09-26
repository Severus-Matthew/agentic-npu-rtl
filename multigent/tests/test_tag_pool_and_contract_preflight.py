from __future__ import annotations

from copy import deepcopy

import pytest

from multigent.tests.test_canonical_operation import axi_lite_contracts
from multigent.tests.test_extension_scenario_matrix import _bundle_and_source
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    build_lifecycle_feature_plan,
    build_operation_feature_plan,
    load_verification_tag_pool,
    render_requested_extension_worklist,
    resolve_extension_reuse,
    review_contract_deterministically,
    validate_architect_extension_requests,
    validate_builtin_tag_references,
    validate_contract_vocabulary,
    validate_verifier_extension_bundles,
)


def _request(
    identity: str,
    domain: str,
    feature_name: str,
    target: dict,
    match: dict,
) -> dict:
    return {
        "id": identity,
        "domain": domain,
        "feature_name": feature_name,
        "target": target,
        "match": match,
        "semantics": {
            "summary": f"Contract-local {feature_name} behavior.",
            "trigger": "The exact target accepts its triggering event.",
            "required_behavior": ["Record and verify the declared observable behavior."],
            "end_condition": "The declared observable behavior completes.",
            "forbidden_behavior": [],
        },
        "reason": "The behavior is not implemented by a closed feature entry.",
        "required_observations": [
            {
                "name": "observed_event",
                "kind": "event",
                "description": "The exact externally observable target event.",
            }
        ],
    }


def test_tag_pool_covers_every_code_owned_taxonomy_reference() -> None:
    assert load_verification_tag_pool()["tags"]
    assert validate_builtin_tag_references() == []


def test_custom_protocol_reuses_ready_valid_features_from_signal_roles() -> None:
    interface = {
        "channels": [
            {"name": "request", "direction": "input", "protocol_profile": "custom"}
        ],
        "signals": [
            {
                "name": "request_valid",
                "role": "valid",
                "direction": "input",
                "channel": "request",
            },
            {
                "name": "request_ready",
                "role": "ready",
                "direction": "output",
                "channel": "request",
            },
            {
                "name": "request_data",
                "role": "payload",
                "semantic_class": "data",
                "direction": "input",
                "channel": "request",
            },
        ],
    }

    plan = build_interface_coverage_plan(interface)
    obligation_ids = {item["id"] for item in plan["obligations"]}
    feature_ids = {item["id"] for item in plan["feature_plan"]["features"]}

    assert {
        "channel.request.handshake_states",
        "channel.request.handshake_arrival_order",
        "channel.request.stall_stability",
    } <= obligation_ids
    assert {
        "channel.request.handshake_states",
        "channel.request.handshake_arrival_order",
        "channel.request.stall_stability",
    } <= feature_ids


@pytest.mark.parametrize(
    "profile",
    ["credit_based", "apb", "tilelink", "wishbone", "avalon_mm", "avalon_st"],
)
def test_unimplemented_protocol_is_not_a_selectable_profile(profile: str) -> None:
    architecture, interface = axi_lite_contracts()
    interface = deepcopy(interface)
    interface["channels"][0]["protocol_profile"] = profile

    report = review_contract_deterministically(
        architecture, interface,
        require_lifecycle_policy=False,
        require_operation_arithmetic=False,
    )

    assert report["status"] == "BLOCKED"
    assert any(
        item["check_id"] == "interface_semantics"
        and profile in item["message"]
        and "cmd" in item["message"]
        for item in report["findings"]
    )


def test_unsupported_named_profile_is_rejected_even_with_an_extension() -> None:
    architecture, interface = axi_lite_contracts()
    architecture, interface = deepcopy(architecture), deepcopy(interface)
    interface["channels"][0]["protocol_profile"] = "apb"
    architecture["verification_extensions"] = [
        _request(
            "protocol.apb_access", "protocol", "apb_access",
            {"scope": "channel", "name": "aw"},
            {"required_protocol_profiles": ["apb"]},
        )
    ]
    architecture["verification_extensions"][0]["target"]["name"] = "cmd"
    report = review_contract_deterministically(
        architecture, interface,
        require_lifecycle_policy=False,
        require_operation_arithmetic=False,
    )
    assert report["status"] == "BLOCKED"
    assert any(
        item["check_id"] == "interface_semantics" and "apb" in item["message"]
        for item in report["findings"]
    )


def test_custom_group_extension_uses_exact_declared_metadata_group() -> None:
    architecture, interface = axi_lite_contracts()
    architecture, interface = deepcopy(architecture), deepcopy(interface)
    interface["channels"][0]["protocol_profile"] = "custom"
    interface["channels"][0]["metadata"] = ["protocol_group=peripheral"]
    architecture["verification_extensions"] = [
        _request(
            "protocol.local_access", "protocol", "local_access",
            {"scope": "protocol_group", "name": "peripheral"},
            {"required_protocol_profiles": ["custom"]},
        )
    ]

    assert validate_architect_extension_requests(architecture, interface) == []
    resolved = resolve_extension_reuse(architecture, interface)
    assert resolved["entries"][0]["match_satisfied"] is True
    assert "custom" in resolved["entries"][0]["target_capabilities"]["protocol_profiles"]


def test_plural_contract_local_vocabulary_drives_exact_match() -> None:
    architecture = {
        "verification_vocabulary": {
            "tags": [
                {
                    "name": "retry_window",
                    "definition": {
                        "description": "A contract-local retry eligibility window.",
                        "domains": ["protocol"],
                        "allowed_scopes": ["signal", "channel"],
                        "required_observations": ["retry_token"],
                    },
                }
            ],
            "signal_roles": [
                {
                    "name": "retry_token",
                    "definition": {
                        "description": "A token authorizing one retry.",
                        "category": "channel_flow_control",
                        "channel_binding": "required",
                        "direction_relation": "same_as_channel",
                        "allowed_directions": ["input", "output"],
                        "semantic_class_binding": "forbidden",
                        "coverage_tags": ["retry_window"],
                    },
                }
            ],
        },
        "verification_extensions": [
            _request(
                "protocol.retry_window",
                "protocol",
                "retry_window",
                {"scope": "signal", "name": "retry_token_i"},
                {
                    "tags": [{"source": "contract_local", "name": "retry_window"}],
                    "required_roles": ["retry_token"],
                    "required_protocol_profiles": ["custom"],
                },
            )
        ],
    }
    interface = {
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {"name": "retry", "direction": "input", "protocol_profile": "custom"}
        ],
        "signals": [
            {
                "name": "clk",
                "role": "clock",
                "semantic_class": None,
                "direction": "input",
                "channel": None,
            },
            {
                "name": "rst_n",
                "role": "reset",
                "semantic_class": None,
                "semantic": "active-low reset",
                "direction": "input",
                "channel": None,
            },
            {
                "name": "retry_token_i",
                "role": "retry_token",
                "semantic_class": None,
                "direction": "input",
                "channel": "retry",
            }
        ],
    }

    assert validate_contract_vocabulary(architecture, interface) == []
    assert validate_architect_extension_requests(architecture, interface) == []
    report = review_contract_deterministically(
        architecture,
        interface,
        require_lifecycle_policy=False,
        require_operation_arithmetic=False,
    )
    assert report["status"] == "PASS"
    entry = report["resolved_extension_reuse"]["entries"][0]
    assert entry["match_satisfied"] is True
    assert "retry_window" in entry["target_tags"]


def test_contract_local_tag_cannot_shadow_builtin_tag() -> None:
    architecture = {
        "verification_vocabulary": {
            "tags": [
                {
                    "name": "handshake",
                    "definition": {
                        "description": "A conflicting local definition.",
                        "domains": ["protocol"],
                        "allowed_scopes": ["channel"],
                    },
                }
            ]
        }
    }
    errors = validate_contract_vocabulary(architecture, {"signals": []})
    assert any("already built in" in error for error in errors)


def test_protocol_lifecycle_and_operation_extensions_reuse_only_residual_work() -> None:
    architecture, interface = axi_lite_contracts()
    architecture = deepcopy(architecture)
    architecture["verification_extensions"] = [
        _request(
            "protocol.retry_window",
            "protocol",
            "retry_window",
            {"scope": "channel", "name": "cmd"},
            {
                "tags": [{"source": "builtin", "name": "handshake"}],
                "required_roles": ["valid", "ready"],
                "required_protocol_profiles": ["ready_valid"],
            },
        ),
        _request(
            "lifecycle.audit_marker",
            "lifecycle",
            "audit_marker",
            {"scope": "operation", "name": "gemm_core"},
            {"tags": [{"source": "builtin", "name": "lifecycle"}]},
        ),
        _request(
            "operation.saturation_metric",
            "operation",
            "saturation_metric",
            {"scope": "operation", "name": "gemm_core"},
            {
                "tags": [
                    {"source": "builtin", "name": "mathematical_correctness"}
                ]
            },
        ),
        _request(
            "operation.a_matrix_checksum",
            "operation",
            "a_matrix_checksum",
            {"scope": "data_object", "name": "A_matrix"},
            {"tags": [{"source": "builtin", "name": "serialization"}]},
        ),
    ]

    assert validate_architect_extension_requests(architecture, interface) == []
    resolved = resolve_extension_reuse(architecture, interface)
    assert resolved["diagnostics"] == []
    by_id = {item["request_id"]: item for item in resolved["entries"]}

    protocol = by_id["protocol.retry_window"]
    assert protocol["match_satisfied"] is True
    assert "channel.cmd.stall_stability" in protocol["preserved_feature_ids"]
    assert "stall_stability" in protocol["helpers"]["assertion_checkers"]
    assert "channel_schedule" in protocol["helpers"]["stimulus_strategies"]

    lifecycle = by_id["lifecycle.audit_marker"]
    assert lifecycle["match_satisfied"] is True
    assert lifecycle["preserved_feature_ids"]
    assert "lifecycle" in lifecycle["target_tags"]

    operation = by_id["operation.saturation_metric"]
    assert operation["match_satisfied"] is True
    assert "operation.gemm_core.accumulation" in operation["preserved_feature_ids"]
    assert operation["helpers"]["assertion_checkers"] == [
        "central_golden_equivalence"
    ]

    data_object = by_id["operation.a_matrix_checksum"]
    assert data_object["match_satisfied"] is True
    assert "serialization" in data_object["target_tags"]
    assert "operation.gemm_core.accumulation" in data_object["preserved_feature_ids"]

    worklist = render_requested_extension_worklist(architecture, interface)
    assert "llm_owns_only_residual_feature: true" in worklist
    assert "central_golden_equivalence" in worklist

    metadata = build_architect_operation_metadata(architecture, interface)
    lifecycle_plan = build_lifecycle_feature_plan(interface, metadata)
    operation_plan = build_operation_feature_plan(architecture)
    assert all(item["tags"] for item in lifecycle_plan["features"])
    assert all(
        item["tags"] == ["mathematical_correctness", "operation_feature"]
        for item in operation_plan["features"]
    )


def test_preflight_blocks_a_declared_match_that_is_not_on_the_target() -> None:
    architecture, interface = axi_lite_contracts()
    architecture = deepcopy(architecture)
    architecture["verification_extensions"] = [
        _request(
            "protocol.wrong_target_match",
            "protocol",
            "wrong_target_match",
            {"scope": "channel", "name": "cmd"},
            {"required_protocol_profiles": ["axi4_stream"]},
        )
    ]

    report = review_contract_deterministically(architecture, interface)
    assert report["status"] == "BLOCKED"
    assert any(
        item["check_id"] == "extension_match" for item in report["findings"]
    )


def test_verifier_bundle_must_preserve_deterministically_resolved_features() -> None:
    architecture, interface = axi_lite_contracts()
    request = _request(
        "protocol.retry_window",
        "protocol",
        "retry_window",
        {"scope": "channel", "name": "cmd"},
        {
            "tags": [{"source": "builtin", "name": "handshake"}],
            "required_roles": ["valid", "ready"],
        },
    )
    architecture["verification_extensions"] = [request]
    bundle, source = _bundle_and_source(request)
    resolved = resolve_extension_reuse(architecture, interface)["entries"][0]
    bundle["reuse"]["based_on_features"] = resolved["preserved_feature_ids"]

    assert validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[source],
        interface=interface,
    ) == []

    bundle["reuse"]["based_on_features"] = []
    errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[source],
        interface=interface,
    )
    assert any("deterministically resolved tool-owned feature" in item for item in errors)
