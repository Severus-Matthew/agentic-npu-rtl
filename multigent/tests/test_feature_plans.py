from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from multigent.verifier_tool import (
    RESOLVED_FEATURE_PLAN_SCHEMA_PATH,
    build_interface_coverage_plan,
    build_lifecycle_assertion_plan,
    build_lifecycle_feature_plan,
    build_operation_feature_plan,
    build_protocol_assertion_plan,
    build_protocol_feature_plan,
    build_protocol_stimulus_plan,
    compile_assertion_feature_plan,
    compile_coverage_feature_plan,
    compile_stimulus_feature_plan,
    load_lifecycle_feature_catalog,
    load_operation_feature_catalog,
    load_protocol_feature_catalog,
    load_resolved_feature_plan_schema,
    validate_resolved_feature_plan,
)


def _interface() -> dict:
    return {
        "channels": [
            {
                "name": "request",
                "direction": "output",
                "protocol_profile": "ready_valid",
            }
        ],
        "signals": [
            {
                "name": "rst_n",
                "role": "reset",
                "direction": "input",
                "semantic": "active-low reset",
            },
            {
                "name": "send",
                "role": "valid",
                "channel": "request",
                "direction": "output",
            },
            {
                "name": "accept",
                "role": "ready",
                "channel": "request",
                "direction": "input",
            },
            {
                "name": "word",
                "role": "payload",
                "semantic_class": "data",
                "channel": "request",
                "direction": "output",
            },
        ],
    }


def test_protocol_assertions_do_not_depend_on_coverage_template_names() -> None:
    coverage_plan = build_interface_coverage_plan(_interface())
    coverage_plan.pop("feature_plan")
    coverage_plan["obligations"] = []

    assertion_plan = build_protocol_assertion_plan(coverage_plan)

    assert assertion_plan["stalls"] == [
        {
            "id": "channel.request.stall_stability",
            "valid": "send",
            "ready": "accept",
            "content": ("word",),
        }
    ]
    assert assertion_plan["feature_plan"]["domain"] == "protocol"


def test_lifecycle_assertions_and_stimulus_share_resolved_feature_bindings() -> None:
    interface = _interface()
    operation_metadata = {"schema_version": 2, "operations": []}
    feature_plan = build_lifecycle_feature_plan(interface, operation_metadata)
    interface_plan = build_interface_coverage_plan(interface)
    interface_plan.pop("feature_plan")
    interface_plan["obligations"] = []

    assertion_plan = build_lifecycle_assertion_plan(interface_plan, operation_metadata)

    assert feature_plan["bindings"]["reset"] == {
        "signal": "rst_n",
        "active_value": 0,
        "settle_cycles": 0,
    }
    assert assertion_plan["reset"] == feature_plan["bindings"]["reset"]
    assert "lifecycle.reset.outputs_match_declared_reset_values" in assertion_plan[
        "features"
    ]


def test_operation_feature_plan_exposes_three_sibling_products() -> None:
    architecture = {
        "operations": [
            {
                "name": "GEMM",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "operand_values",
                    "accumulation",
                    "post_processing",
                ],
                "feature_extensions": [],
            }
        ]
    }

    plan = build_operation_feature_plan(architecture)

    assert {item["bindings"]["concept"] for item in plan["features"]} == {
        "dimensions",
        "operand_values",
        "accumulation",
    }
    for item in plan["features"]:
        assert item["assertion"]["checker"] == "central_golden_equivalence"
        assert item["coverage"]["concept"] == item["bindings"]["concept"]
        assert item["stimulus"]["strategy"] == "canonical_discriminating_stimuli"


def test_protocol_coverage_plan_publishes_resolved_feature_plan() -> None:
    plan = build_interface_coverage_plan(_interface())
    assert plan["feature_plan"] == build_protocol_feature_plan(plan)


def test_domain_catalogs_are_the_single_declarative_feature_sources() -> None:
    protocol = load_protocol_feature_catalog()
    lifecycle = load_lifecycle_feature_catalog()
    operation = load_operation_feature_catalog()

    stall = protocol["features"]["stall_stability"]
    assert stall["match"]["required_roles"] == ["valid", "ready"]
    assert stall["assertion"]["checker"] == "stall_stability"
    assert [item["name"] for item in stall["coverage"]["bins"]] == [
        "one_cycle_stall",
        "short_stall",
        "long_stall",
    ]
    assert [item["name"] for item in stall["stimulus"]["scenarios"]] == [
        "one_cycle_stall",
        "short_stall",
        "long_stall",
    ]
    assert {
        "assertion",
        "coverage",
        "stimulus",
    } <= lifecycle["features"]["reset_behavior"].keys()
    assert operation["feature_defaults"] == {
        "assertion": {"checker": "central_golden_equivalence"},
        "coverage": {"sampler": "canonical_classifier"},
        "stimulus": {"strategy": "canonical_discriminating_stimuli"},
    }


def test_machine_readable_handshake_values_drive_all_three_compiled_branches() -> None:
    interface_plan = build_interface_coverage_plan(_interface())
    feature_plan = interface_plan["feature_plan"]
    handshake = next(
        item
        for item in interface_plan["obligations"]
        if item["template"] == "handshake_states"
    )
    arrival = next(
        item
        for item in interface_plan["obligations"]
        if item["template"] == "handshake_arrival_order"
    )
    stall = next(
        item
        for item in interface_plan["obligations"]
        if item["template"] == "stall_stability"
    )

    assert {item["name"]: item["values"] for item in handshake["bins"]} == {
        "idle": {"valid": 0, "ready": 0},
        "receiver_ready": {"valid": 0, "ready": 1},
        "backpressured": {"valid": 1, "ready": 0},
        "transfer": {"valid": 1, "ready": 1},
    }
    assert [item["event"] for item in arrival["bins"]] == [
        "simultaneous",
        "valid_before_ready",
        "ready_before_valid",
    ]
    assert [item["range"] for item in stall["bins"]] == [
        [1, 1],
        [2, 4],
        [5, None],
    ]
    assert compile_assertion_feature_plan(feature_plan)["entries"]
    assert compile_coverage_feature_plan(feature_plan)["entries"]
    assert compile_stimulus_feature_plan(feature_plan)["entries"]

    stimulus = build_protocol_stimulus_plan(_interface())
    schedules = {
        item["id"].rsplit(".", 1)[-1]: item["schedule"]
        for item in stimulus["groups"][0]["scenarios"]
    }
    assert schedules["one_cycle_stall"]["stall_cycles"] == 1
    assert schedules["short_stall"]["stall_cycles"] == 3
    assert schedules["long_stall"]["stall_cycles"] == 6


def test_resolved_feature_plan_schema_is_executable_and_json_stable() -> None:
    schema = load_resolved_feature_plan_schema()
    Draft202012Validator.check_schema(schema)
    assert RESOLVED_FEATURE_PLAN_SCHEMA_PATH.name == "resolved_feature_plan.schema.json"

    plan = build_interface_coverage_plan(_interface())["feature_plan"]
    assert json.loads(json.dumps(plan)) == plan
    assert validate_resolved_feature_plan(plan) == plan

    malformed = copy.deepcopy(plan)
    del malformed["features"][0]["assertion"]
    with pytest.raises(ValidationError):
        validate_resolved_feature_plan(malformed)

    duplicate = copy.deepcopy(plan)
    duplicate["features"].append(copy.deepcopy(duplicate["features"][0]))
    with pytest.raises(ValueError, match="duplicate id"):
        validate_resolved_feature_plan(duplicate)
