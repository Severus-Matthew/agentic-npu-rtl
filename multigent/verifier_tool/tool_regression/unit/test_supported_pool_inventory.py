"""Every advertised protocol template must bind in a representative contract."""

from __future__ import annotations

from copy import deepcopy

from multigent.verifier_tool.tool_regression.unit.test_custom_mmio_protocol import custom_contracts
from multigent.verifier_tool.tool_regression.integration.test_standard_axi_protocols import _interface
from multigent.verifier_tool.tool_regression.benchmarks.u55c_inspired_int8_gemm_4x4x4 import (
    build_contract_and_tb,
)
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_interface_coverage_plan,
)
from multigent.verifier_tool.pool.feature_plans.catalog import (
    load_protocol_feature_catalog,
)
from multigent.verifier_tool.pool.role_pool.interface_semantics import (
    load_interface_protocol_taxonomy,
)


def _axi4_with_ids() -> dict:
    interface = deepcopy(_interface("axi4"))
    for channel, direction in (
        ("aw", "output"), ("b", "input"),
        ("ar", "output"), ("r", "input"),
    ):
        interface["signals"].append({
            "name": f"{channel}id",
            "role": "transaction_id",
            "semantic_class": "identifier",
            "protocol_field": "id",
            "channel": channel,
            "direction": direction,
            "width": "4",
        })
    return interface


def test_every_advertised_protocol_template_has_a_resolved_binding() -> None:
    interfaces = [
        _interface("axi4"), _interface("axi4_lite"),
        _interface("axi4_stream"), _axi4_with_ids(),
        custom_contracts()[1],
    ]
    matched = {
        feature["kind"]
        for interface in interfaces
        for feature in build_interface_coverage_plan(interface)["feature_plan"]["features"]
    }
    advertised = set(load_protocol_feature_catalog()["features"])

    assert advertised <= matched


def test_custom_address_coverage_is_bound_to_an_accepted_request() -> None:
    _, interface = custom_contracts()
    obligations = [
        item for item in build_interface_coverage_plan(interface)["obligations"]
        if item["template"] == "address_alignment"
    ]
    assert obligations
    for item in obligations:
        signal = item["bindings"]["signal"]
        channel_name = next(
            entry["channel"] for entry in interface["signals"]
            if entry["name"] == signal
        )
        assert item["bindings"]["valid"] == f"{channel_name}_valid"
        assert item["bindings"]["ready"] == f"{channel_name}_ready"


def test_only_implemented_protocol_profiles_are_selectable() -> None:
    profiles = load_interface_protocol_taxonomy()["protocol_profiles"]
    assert set(profiles) == {
        "custom", "ready_valid", "axi4", "axi4_lite", "custom_mmio", "axi4_stream",
    }


def test_dut_owned_ready_does_not_require_a_particular_arrival_order() -> None:
    _, interface, _, _ = build_contract_and_tb.build_architecture_contract()
    obligations = {
        item["id"]: item
        for item in build_interface_coverage_plan(interface)["obligations"]
    }

    def required(obligation_id: str) -> set[str]:
        return {
            item["name"]
            for item in obligations[obligation_id]["bins"]
            if item.get("required", True)
        }

    # The command is a generic ready/valid input. Both a sink that waits for
    # VALID and one that raises READY early are legal, so only transfer is
    # universally required. All other bins remain observable diagnostics.
    assert required("channel.cmd_chan.handshake_states") == {"transfer"}
    assert required("channel.cmd_chan.handshake_arrival_order") == set()
    assert required("channel.cmd_chan.stall_stability") == set()
    # The TB owns READY on the AXI address output and can intentionally force
    # the directed handshake states and stalls.
    assert "backpressured" in required("channel.m_axi_ar.handshake_states")


def test_noncanonical_dense_wire_order_requires_an_explicit_extension() -> None:
    architecture, interface, _, _ = build_contract_and_tb.build_architecture_contract()
    altered = deepcopy(architecture)
    b_matrix = next(item for item in altered["data_objects"] if item["name"] == "B_matrix")
    b_matrix["serialization"]["index_order"] = ["N", "K"]
    metadata = build_architect_operation_metadata(altered, interface)
    support = automatic_campaign_support(metadata, altered)
    assert support["supported"] is False
    assert support["any_operation_supported"] is False
    assert support["operations"]["gemm"]["protocol_lifecycle_supported"] is False
    assert "serialization is not supported" in support["reasons"][0]


def test_axi4_declared_single_beat_capabilities_limit_only_applicable_bins() -> None:
    interface = _axi4_with_ids()
    interface["channels"][0]["protocol_capabilities"] = {
        "burst_type_bins": ["incrementing"],
        "burst_length_bins": ["single"],
        "transfer_size_bins": ["full_width"],
        "alignment_bins": ["aligned"],
        "boundary_bins": ["ends_before_boundary"],
        "id_bins": ["zero"],
    }
    obligations = build_interface_coverage_plan(interface)["obligations"]
    for feature, selected in (
        ("axi4_burst_type", "incrementing"),
        ("axi4_burst_length", "single"),
        ("axi4_transfer_size", "full_width"),
        ("axi4_alignment", "aligned"),
        ("axi4_4k_boundary", "ends_before_boundary"),
        ("axi4_sideband_partition", "zero"),
    ):
        relevant = [item for item in obligations if item["template"] == feature]
        assert relevant
        for item in relevant:
            assert {
                bin_spec["name"] for bin_spec in item["bins"]
                if bin_spec["required"]
            } == {selected}

    broken = deepcopy(interface)
    broken["channels"][0]["protocol_capabilities"]["burst_type_bins"] = ["imaginary"]
    import pytest

    with pytest.raises(ValueError, match="must select known"):
        build_interface_coverage_plan(broken)
