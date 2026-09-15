from __future__ import annotations

from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan


def _ids(plan: dict) -> set[str]:
    return {item["id"] for item in plan["obligations"]}


def test_ready_valid_templates_bind_arbitrary_signal_names() -> None:
    interface = {
        "channels": [
            {"name": "request", "direction": "input", "protocol_profile": "ready_valid"}
        ],
        "signals": [
            {"name": "x1", "role": "valid", "channel": "request"},
            {"name": "x2", "role": "ready", "channel": "request"},
            {"name": "x3", "role": "payload", "semantic_class": "data", "channel": "request"},
        ],
    }
    plan = build_interface_coverage_plan(interface)
    assert {
        "channel.request.handshake_states",
        "channel.request.stall_stability",
    } <= _ids(plan)
    handshake = next(
        item for item in plan["obligations"] if item["template"] == "handshake_states"
    )
    assert handshake["bindings"] == {"valid": "x1", "ready": "x2"}
    assert {item["name"] for item in handshake["bins"]} == {
        "idle",
        "receiver_ready",
        "backpressured",
        "transfer",
    }


def test_axi_boundary_template_requires_address_length_and_size() -> None:
    interface = {
        "channels": [
            {"name": "aw", "direction": "input", "protocol_profile": "axi4"}
        ],
        "signals": [
            {"name": "a", "role": "payload", "semantic_class": "address", "channel": "aw"},
            {"name": "b", "role": "metadata", "semantic_class": "length", "channel": "aw"},
            {"name": "c", "role": "metadata", "semantic_class": "size", "channel": "aw"},
        ],
    }
    plan = build_interface_coverage_plan(interface)
    assert "channel.aw.axi4_4k_boundary" in _ids(plan)

    interface["signals"] = interface["signals"][:-1]
    assert "channel.aw.axi4_4k_boundary" not in _ids(
        build_interface_coverage_plan(interface)
    )


def test_signal_templates_bind_roles_and_semantic_classes() -> None:
    interface = {
        "channels": [
            {"name": "unused", "direction": "input", "protocol_profile": "axi4_lite"}
        ],
        "signals": [
            {"name": "r7", "role": "reset", "semantic_class": None, "semantic": "active-high reset", "channel": None},
            {"name": "z9", "role": "completion", "semantic_class": None, "channel": None},
            {"name": "looks_like_done", "role": "payload", "semantic_class": "address", "channel": "unused"},
        ],
    }
    assert _ids(build_interface_coverage_plan(interface)) == {
        "signal.r7.reset_behavior",
        "signal.z9.completion_behavior",
        "signal.looks_like_done.address_alignment",
    }


def test_configuration_index_does_not_inherit_byte_address_alignment_bins() -> None:
    interface = {
        "channels": [
            {"name": "cfg", "direction": "input", "protocol_profile": "ready_valid"}
        ],
        "signals": [
            {
                "name": "cfg_index",
                "role": "metadata",
                "semantic_class": "address",
                "channel": "cfg",
                "width": "((TAPS <= 1) ? 1 : $clog2(TAPS))",
            }
        ],
    }

    assert "signal.cfg_index.address_alignment" not in _ids(
        build_interface_coverage_plan(interface)
    )
