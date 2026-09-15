from __future__ import annotations

from multigent.verifier_tool.role_pool.signal_roles import (
    SIGNAL_ROLE_TAXONOMY_PATH,
    load_signal_role_taxonomy,
    signals_with_coverage_tags,
    signals_with_roles,
    validate_interface_signal_roles,
)
from multigent.verifier_tool.role_pool.interface_semantics import (
    derive_interface_coverage_seed,
    load_interface_protocol_taxonomy,
    load_interface_semantic_taxonomy,
    validate_interface_semantics,
)


def test_signal_role_taxonomy_is_external_and_loadable() -> None:
    assert SIGNAL_ROLE_TAXONOMY_PATH.suffix == ".yaml"
    taxonomy = load_signal_role_taxonomy()
    assert taxonomy["taxonomy"]["scope"]
    assert {"clock", "reset", "valid", "ready", "payload", "completion", "error"} <= set(
        taxonomy["roles"]
    )


def test_signal_roles_validate_channel_direction_relations() -> None:
    interface = {
        "clock": "c0",
        "reset": "r0",
        "channels": [
            {
                "name": "ingress",
                "direction": "input",
                "protocol_profile": "ready_valid",
            }
        ],
        "signals": [
            {"name": "c0", "role": "clock", "semantic_class": None, "channel": None, "direction": "input"},
            {"name": "r0", "role": "reset", "semantic_class": None, "semantic": "synchronous active-high reset", "channel": None, "direction": "input"},
            {"name": "q0", "role": "valid", "semantic_class": None, "channel": "ingress", "direction": "input"},
            {"name": "q1", "role": "ready", "semantic_class": None, "channel": "ingress", "direction": "output"},
            {"name": "q2", "role": "payload", "semantic_class": "data", "channel": "ingress", "direction": "input"},
        ],
    }
    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []

    interface["signals"][3]["direction"] = "input"
    assert any(
        "must be output" in error
        for error in validate_interface_signal_roles(interface)
    )


def test_reset_role_requires_unambiguous_active_level() -> None:
    interface = {
        "clock": "c0",
        "reset": "r0",
        "channels": [],
        "signals": [
            {"name": "c0", "role": "clock", "direction": "input", "channel": None},
            {
                "name": "r0",
                "role": "reset",
                "direction": "input",
                "channel": None,
                "semantic": "synchronous reset",
            },
        ],
    }
    assert any(
        "exactly one of active-high or active-low" in error
        for error in validate_interface_signal_roles(interface)
    )

    interface["signals"][1]["semantic"] = "synchronous active-low reset"
    assert validate_interface_signal_roles(interface) == []


def test_role_selection_ignores_names_and_semantics() -> None:
    signals = [
        {"name": "done", "role": "payload", "semantic": "looks like completion"},
        {"name": "opaque_42", "role": "completion", "semantic": "event"},
    ]
    assert signals_with_roles(signals, {"completion"}) == {"opaque_42"}
    assert signals_with_coverage_tags(signals, {"completion"}) == {"opaque_42"}


def test_semantic_and_protocol_taxonomies_cover_cpu_facing_interfaces() -> None:
    classes = load_interface_semantic_taxonomy()["semantic_classes"]
    profiles = load_interface_protocol_taxonomy()["protocol_profiles"]
    assert {"address", "byte_enable", "length", "response_code", "protection"} <= set(classes)
    assert {"axi4", "axi4_lite", "apb", "tilelink"} <= set(profiles)


def test_payload_requires_semantic_class() -> None:
    interface = {
        "channels": [
            {"name": "memory_request", "direction": "input", "protocol_profile": "axi4"}
        ],
        "signals": [
            {
                "name": "not_named_address",
                "role": "payload",
                "semantic_class": None,
                "channel": "memory_request",
                "direction": "input",
            }
        ],
    }
    assert any("requires a semantic_class" in error for error in validate_interface_semantics(interface))

    interface["signals"][0]["semantic_class"] = "address"
    assert validate_interface_semantics(interface) == []

    seed = derive_interface_coverage_seed(interface)
    assert "4k_boundary" in seed["channels"]["memory_request"]
    assert "alignment" in seed["signals"]["not_named_address"]
    assert "address_boundary" in seed["signals"]["not_named_address"]
