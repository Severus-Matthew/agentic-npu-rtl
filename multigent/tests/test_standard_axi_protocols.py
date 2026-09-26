from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from multigent.verifier_tool import (
    build_interface_coverage_plan,
    build_protocol_assertion_plan,
    build_protocol_stimulus_plan,
    check_protocol_assertions,
    compile_standard_protocol_plan,
    enrich_standard_protocol_metadata,
    finalize_protocol_assertions,
    generate_random_protocol_scenarios,
    render_contract_generated_block,
    validate_standard_protocol_bindings,
)
from multigent.verifier_tool.protocol.coverage.runtime import ProtocolCoverageMonitor
from multigent.verifier_tool.protocol.stimulus import cocotb as cocotb_helpers


_SEMANTIC = {
    "addr": ("payload", "address"),
    "len": ("metadata", "length"),
    "size": ("metadata", "size"),
    "burst": ("metadata", "burst_type"),
    "data": ("payload", "data"),
    "strb": ("keep", "byte_enable"),
    "keep": ("keep", "byte_enable"),
    "last": ("last", "framing"),
    "id": ("transaction_id", "identifier"),
    "dest": ("metadata", "identifier"),
    "resp": ("payload", "response_code"),
    "prot": ("metadata", "protection"),
    "user": ("metadata", "user_metadata"),
}


def test_logical_field_transfer_wrappers_own_beat_packing_and_unpacking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = {"name": "data", "fields": {"payload": "data_payload"}}

    async def fake_drive(dut, clock_name, bound_channel, beats, **kwargs):
        assert dut == "dut"
        assert clock_name == "clk"
        assert bound_channel is channel
        assert kwargs == {"timeout_cycles": 9, "settle_timer_ps": 2}
        return list(beats)

    async def fake_collect(dut, clock_name, bound_channel, **kwargs):
        assert dut == "dut"
        assert clock_name == "clk"
        assert bound_channel is channel
        assert kwargs["count"] == 2
        return [{"payload": -3}, {"payload": 7}]

    monkeypatch.setattr(cocotb_helpers, "drive_protocol_transfers", fake_drive)
    accepted = asyncio.run(
        cocotb_helpers.drive_protocol_field_values(
            "dut", "clk", channel, "payload", [-3, 7],
            timeout_cycles=9, settle_timer_ps=2,
        )
    )
    assert accepted == [-3, 7]

    monkeypatch.setattr(cocotb_helpers, "collect_protocol_transfers", fake_collect)
    observed = asyncio.run(
        cocotb_helpers.collect_protocol_field_values(
            "dut", "clk", channel, "payload", count=2,
        )
    )
    assert observed == [-3, 7]


def _interface(profile: str) -> dict:
    interface = {
        "clock": "clk",
        "reset": "rst",
        "channels": [],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {
                "name": "rst",
                "role": "reset",
                "direction": "input",
                "channel": None,
                "semantic": "synchronous active-high reset",
            },
        ],
    }

    def add(kind: str, direction: str, fields: dict[str, int]) -> None:
        prefix = {
            "write_address": "aw",
            "write_data": "w",
            "write_response": "b",
            "read_address": "ar",
            "read_data": "r",
            "stream": "t",
        }[kind]
        interface["channels"].append(
            {
                "name": prefix,
                "direction": direction,
                "protocol_profile": profile,
                "protocol_group": "bus",
                "protocol_channel": kind,
            }
        )
        interface["signals"].extend(
            [
                {
                    "name": f"{prefix}valid",
                    "role": "valid",
                    "semantic_class": None,
                    "channel": prefix,
                    "direction": direction,
                    "width": "1",
                },
                {
                    "name": f"{prefix}ready",
                    "role": "ready",
                    "semantic_class": None,
                    "channel": prefix,
                    "direction": "input" if direction == "output" else "output",
                    "width": "1",
                },
            ]
        )
        for field, width in fields.items():
            role, semantic = _SEMANTIC[field]
            interface["signals"].append(
                {
                    "name": f"{prefix}{field}",
                    "role": role,
                    "semantic_class": semantic,
                    "protocol_field": field,
                    "channel": prefix,
                    "direction": direction,
                    "width": str(width),
                }
            )

    if profile == "axi4":
        add("write_address", "output", {"addr": 32, "len": 8, "size": 3, "burst": 2})
        add("write_data", "output", {"data": 32, "strb": 4, "last": 1})
        add("write_response", "input", {"resp": 2})
        add("read_address", "output", {"addr": 32, "len": 8, "size": 3, "burst": 2})
        add("read_data", "input", {"data": 32, "resp": 2, "last": 1})
    elif profile == "axi4_lite":
        add("write_address", "output", {"addr": 32, "prot": 3})
        add("write_data", "output", {"data": 32, "strb": 4})
        add("write_response", "input", {"resp": 2})
        add("read_address", "output", {"addr": 32, "prot": 3})
        add("read_data", "input", {"data": 32, "resp": 2})
    else:
        add(
            "stream",
            "output",
            {"data": 32, "strb": 4, "keep": 4, "last": 1, "id": 2, "dest": 2, "user": 4},
        )
    return interface


def _snapshot(interface: dict, **updates: int) -> dict[str, int]:
    result = {str(item["name"]): 0 for item in interface["signals"]}
    result.update(updates)
    return result


def _checker(interface: dict):
    plan = build_protocol_assertion_plan(build_interface_coverage_plan(interface))
    state: dict = {}
    return state, lambda **values: check_protocol_assertions(
        _snapshot(interface, **values), plan, state
    )


def test_standard_metadata_is_exact_and_name_independent() -> None:
    interface = _interface("axi4")
    compiled = compile_standard_protocol_plan(interface)
    group = compiled["groups"][0]
    assert group["endpoint_role"] == "manager"
    assert group["channels"]["write_address"]["fields"]["addr"] == "awaddr"

    broken = deepcopy(interface)
    del broken["channels"][0]["protocol_group"]
    assert any("requires protocol_group" in item for item in validate_standard_protocol_bindings(broken))
    with pytest.raises(ValueError, match="requires protocol_group"):
        build_interface_coverage_plan(broken)


def test_current_architect_schema_tags_compile_without_name_inference() -> None:
    interface = _interface("axi4_lite")
    for channel in interface["channels"]:
        channel["metadata"] = [
            f"protocol_group={channel.pop('protocol_group')}",
            f"protocol_channel={channel.pop('protocol_channel')}",
        ]
    for signal in interface["signals"]:
        field = signal.pop("protocol_field", None)
        if field is not None:
            signal["semantic"] = f"contract prose, protocol_field={field} fixed"

    enriched = enrich_standard_protocol_metadata(interface)
    assert "protocol_group" not in interface["channels"][0]
    assert enriched["channels"][0]["protocol_group"] == "bus"
    compiled = compile_standard_protocol_plan(interface)
    group = compiled["groups"][0]
    assert group["profile"] == "axi4_lite"
    assert group["channels"]["write_address"]["fields"]["addr"] == "awaddr"

    missing = deepcopy(interface)
    missing["channels"][0]["metadata"] = ["unrelated prose"]
    with pytest.raises(ValueError, match="requires protocol_group"):
        compile_standard_protocol_plan(missing)

    renamed = deepcopy(interface)
    renamed["signals"][-1]["name"] = "definitely_not_an_axi_name"
    renamed["signals"][-1]["semantic"] = "response payload without an explicit tag"
    with pytest.raises(ValueError, match="requires protocol_field"):
        compile_standard_protocol_plan(renamed)


def test_schema_tag_conflicts_are_blocking() -> None:
    interface = _interface("axi4_lite")
    interface["channels"][0]["metadata"] = ["protocol_group=other"]
    with pytest.raises(ValueError, match="conflicting native and tagged protocol_group"):
        compile_standard_protocol_plan(interface)


def test_axi_lite_capability_tags_make_unreachable_bins_inapplicable() -> None:
    interface = _interface("axi4_lite")
    for channel in interface["channels"]:
        channel["metadata"] = [
            (
                "protocol_capability.max_outstanding=1 "
                "protocol_capability.read_write_concurrency=false "
                "protocol_capability.address_bins=zero|aligned|page_edge "
                "protocol_capability.write_strobe_bins=full "
                "protocol_capability.protection_bins=zero "
                "protocol_capability.write_order_bins=address_first|data_first|same_cycle"
            )
        ]
    plan = build_interface_coverage_plan(interface)
    by_template = {}
    for obligation in plan["obligations"]:
        by_template.setdefault(obligation["template"], []).append(obligation)

    def required(template: str) -> set[str]:
        return {
            item["name"]
            for obligation in by_template[template]
            for item in obligation["bins"]
            if item.get("required", True)
        }

    assert required("axi_lite_outstanding_depth") == {"one"}
    assert required("axi_lite_read_write_concurrency") == {
        "write_only_cycle", "read_only_cycle"
    }
    assert required("axi_lite_address_partition") == {"zero", "aligned", "page_edge"}
    assert required("axi_lite_write_strobe") == {"full"}
    assert required("axi_lite_protection_partition") == {"zero"}


def test_axi4_single_outstanding_capability_does_not_require_multiple_requests() -> None:
    interface = _interface("axi4")
    interface["channels"][0]["metadata"] = ["protocol_capability.max_outstanding=1"]
    plan = build_interface_coverage_plan(interface)
    depth = next(
        item for item in plan["obligations"]
        if item["template"] == "axi4_outstanding_depth"
    )
    assert {
        item["name"] for item in depth["bins"] if item.get("required", True)
    } == {"one"}


def test_custom_ready_valid_channels_are_exposed_to_tool_owned_drivers() -> None:
    interface = {
        "channels": [
            {
                "name": "operand",
                "direction": "input",
                "protocol_profile": "ready_valid",
            }
        ],
        "signals": [
            {"name": "v", "channel": "operand", "role": "valid", "width": "1"},
            {"name": "r", "channel": "operand", "role": "ready", "width": "1"},
            {"name": "p", "channel": "operand", "role": "payload", "width": "8"},
        ],
    }
    plan = build_protocol_stimulus_plan(interface)
    group = next(item for item in plan["groups"] if item["name"] == "contract_ready_valid")
    assert group["channels"]["operand"] == {
        "name": "operand",
        "direction": "input",
        "kind": "operand",
        "valid": "v",
        "ready": "r",
        "effective_defaults": {},
        "fields": {"payload": "p"},
        "widths": {"payload": 8},
    }


def test_axi_profiles_build_deep_coverage_and_directed_stimulus() -> None:
    minimum_templates = {
        "axi4": {
            "axi4_burst_type",
            "axi4_burst_length",
            "axi4_transfer_size",
            "axi4_alignment",
            "axi4_4k_boundary",
            "axi4_write_strobe",
            "axi4_write_channel_order",
            "axi4_response_code",
            "axi4_outstanding_depth",
        },
        "axi4_lite": {
            "axi_lite_write_channel_order",
            "axi_lite_write_strobe",
            "axi_lite_response_code",
            "axi_lite_read_write_concurrency",
        },
        "axi4_stream": {
            "axis_packet_length",
            "axis_keep_pattern",
            "axis_stall_position",
            "axis_back_to_back_packets",
            "axis_sideband_partition",
        },
    }
    minimum_scenarios = {"axi4": 50, "axi4_lite": 40, "axi4_stream": 14}
    for profile in minimum_templates:
        interface = _interface(profile)
        plan = build_interface_coverage_plan(interface)
        assert minimum_templates[profile] <= {
            item["template"] for item in plan["obligations"]
        }
        stimulus = build_protocol_stimulus_plan(interface)
        assert len(stimulus["groups"][0]["scenarios"]) >= minimum_scenarios[profile]
        claimed = {
            target
            for scenario in [
                *stimulus["global_scenarios"],
                *stimulus["groups"][0]["scenarios"],
            ]
            for target in scenario.get("coverage_targets", [])
        }
        required_obligations = {
            item["id"]
            for item in plan["obligations"]
            if any(bin_spec.get("required", True) for bin_spec in item["bins"])
        }
        assert required_obligations <= claimed
        assert len(generate_random_protocol_scenarios(interface, 5, seed=9)) == 5


def test_axi4_assertions_enforce_dependencies_bursts_last_and_strobes() -> None:
    interface = _interface("axi4")
    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="BVALID was presented before"):
        check(bvalid=1, bready=1)

    _, check = _checker(interface)
    check(
        awvalid=1,
        awready=1,
        awaddr=0,
        awlen=0,
        awsize=2,
        awburst=1,
        wvalid=1,
        wready=1,
        wdata=1,
        wstrb=0xF,
        wlast=1,
    )
    check(bvalid=1, bready=1, bresp=0)

    _, check = _checker(interface)
    check(
        awvalid=1,
        awready=1,
        awaddr=0,
        awlen=0,
        awsize=2,
        awburst=1,
        wvalid=1,
        wready=1,
        wstrb=0xF,
        wlast=1,
    )
    with pytest.raises(AssertionError, match="EXOKAY write response"):
        check(bvalid=1, bready=1, bresp=1)

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="no_4k_boundary_crossing"):
        check(awvalid=1, awready=1, awaddr=0xFFC, awlen=1, awsize=2, awburst=1)

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="AWLEN expects 2 W beats"):
        check(
            awvalid=1,
            awready=1,
            awaddr=0,
            awlen=1,
            awsize=2,
            awburst=1,
            wvalid=1,
            wready=1,
            wstrb=0xF,
            wlast=1,
        )

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="outside allowed mask"):
        check(
            awvalid=1,
            awready=1,
            awaddr=0,
            awlen=0,
            awsize=0,
            awburst=1,
            wvalid=1,
            wready=1,
            wstrb=0x8,
            wlast=1,
        )


def test_axi4_read_response_requires_address_and_exact_rlast() -> None:
    interface = _interface("axi4")
    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="without an earlier matching AR"):
        check(rvalid=1, rready=1, rlast=1)

    _, check = _checker(interface)
    check(arvalid=1, arready=1, araddr=0, arlen=1, arsize=2, arburst=1)
    check(rvalid=1, rready=1, rresp=0, rlast=0)
    check(rvalid=1, rready=1, rresp=0, rlast=1)

    _, check = _checker(interface)
    check(arvalid=1, arready=1, araddr=0, arlen=1, arsize=2, arburst=1)
    with pytest.raises(AssertionError, match="read_last_matches_length"):
        check(rvalid=1, rready=1, rresp=0, rlast=1)


def test_axi4_exclusive_access_restrictions_and_read_before_write() -> None:
    interface = _interface("axi4")
    for prefix in ("aw", "ar"):
        direction = next(item["direction"] for item in interface["channels"] if item["name"] == prefix)
        interface["signals"].append(
            {
                "name": f"{prefix}lock",
                "role": "metadata",
                "semantic_class": "configuration",
                "protocol_field": "lock",
                "channel": prefix,
                "direction": direction,
                "width": "1",
            }
        )
    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="exclusive access requires"):
        check(arvalid=1, arready=1, araddr=0, arlen=2, arsize=2, arburst=1, arlock=1)

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="exclusive write did not follow"):
        check(awvalid=1, awready=1, awaddr=0, awlen=3, awsize=2, awburst=1, awlock=1)

    _, check = _checker(interface)
    check(arvalid=1, arready=1, araddr=0, arlen=3, arsize=2, arburst=1, arlock=1)
    for beat in range(4):
        check(rvalid=1, rready=1, rresp=0, rlast=int(beat == 3))
    check(awvalid=1, awready=1, awaddr=0, awlen=3, awsize=2, awburst=1, awlock=1)


def test_axi4_lite_asserts_pairing_and_forbids_exokay() -> None:
    interface = _interface("axi4_lite")
    _, check = _checker(interface)
    check(awvalid=1, awready=1, awaddr=0x10, awprot=0)
    check(wvalid=1, wready=1, wdata=3, wstrb=0xF)
    check(bvalid=1, bready=1, bresp=0)

    _, check = _checker(interface)
    check(awvalid=1, awready=1, awaddr=0x10, awprot=0)
    check(wvalid=1, wready=1, wdata=3, wstrb=0xF)
    with pytest.raises(AssertionError, match="not legal AXI4-Lite"):
        check(bvalid=1, bready=1, bresp=1)


@pytest.mark.parametrize(
    "changed_content",
    [{"wdata": 4, "wstrb": 0xF}, {"wdata": 3, "wstrb": 0x7}],
)
def test_axi4_lite_w_channel_content_is_stable_through_a_stall(changed_content) -> None:
    _, check = _checker(_interface("axi4_lite"))
    check(wvalid=1, wready=0, wdata=3, wstrb=0xF)
    with pytest.raises(AssertionError, match=r"channel\.w\.stall_stability"):
        check(wvalid=1, wready=1, **changed_content)


def test_axi4_lite_optional_ids_are_returned_in_order() -> None:
    interface = _interface("axi4_lite")
    directions = {item["name"]: item["direction"] for item in interface["channels"]}
    for prefix in ("aw", "b", "ar", "r"):
        interface["signals"].append(
            {
                "name": f"{prefix}id",
                "role": "transaction_id",
                "semantic_class": "identifier",
                "protocol_field": "id",
                "channel": prefix,
                "direction": directions[prefix],
                "width": "2",
            }
        )
    _, check = _checker(interface)
    check(awvalid=1, awready=1, awaddr=0x10, awprot=0, awid=2)
    check(wvalid=1, wready=1, wdata=3, wstrb=0xF)
    with pytest.raises(AssertionError, match="BID=1 does not match oldest AWID=2"):
        check(bvalid=1, bready=1, bresp=0, bid=1)


def test_axi4_lite_rejects_nonstandard_data_width() -> None:
    interface = _interface("axi4_lite")
    for signal in interface["signals"]:
        if signal["name"] in {"wdata", "rdata"}:
            signal["width"] = "16"
        if signal["name"] == "wstrb":
            signal["width"] = "2"
    with pytest.raises(ValueError, match="data width must be 32 or 64"):
        build_interface_coverage_plan(interface)


def test_axi_stream_asserts_stability_mask_subset_and_packet_sidebands() -> None:
    interface = _interface("axi4_stream")
    _, check = _checker(interface)
    check(tvalid=1, tready=0, tdata=1, tkeep=0xF, tstrb=0xF, tid=1, tdest=2)
    with pytest.raises(AssertionError, match="content changed"):
        check(tvalid=1, tready=0, tdata=2, tkeep=0xF, tstrb=0xF, tid=1, tdest=2)

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="strobe_is_subset_of_keep"):
        check(tvalid=1, tready=1, tkeep=0x1, tstrb=0x2, tlast=1)

    _, check = _checker(interface)
    check(tvalid=1, tready=1, tkeep=0xF, tstrb=0xF, tid=1, tdest=2, tlast=0)
    # AXI4-Stream packet state is per effective (TID,TDEST), so another stream
    # may legally complete while stream 1 remains open.
    check(tvalid=1, tready=1, tkeep=0xF, tstrb=0xF, tid=2, tdest=2, tlast=1)
    check(tvalid=1, tready=1, tkeep=0xF, tstrb=0xF, tid=1, tdest=2, tlast=1)


def test_axi4_accepts_w_burst_before_write_address() -> None:
    interface = _interface("axi4")
    _, check = _checker(interface)
    check(wvalid=1, wready=1, wdata=0x1234, wstrb=0xF, wlast=1)
    check(awvalid=1, awready=1, awaddr=0x40, awlen=0, awsize=2, awburst=1)
    check(bvalid=1, bready=1, bresp=0)


def test_axi4_lite_accepts_multiple_independent_pending_writes() -> None:
    interface = _interface("axi4_lite")
    _, check = _checker(interface)
    for address, data in ((0x10, 1), (0x14, 2)):
        check(awvalid=1, awready=1, awaddr=address, awprot=0)
        check(wvalid=1, wready=1, wdata=data, wstrb=0xF)
    check(bvalid=1, bready=1, bresp=0)
    check(bvalid=1, bready=1, bresp=0)


def test_protocol_finalizer_rejects_truncated_pending_work() -> None:
    interface = _interface("axi4")
    plan = build_protocol_assertion_plan(build_interface_coverage_plan(interface))
    state: dict = {}
    check_protocol_assertions(
        _snapshot(
            interface,
            awvalid=1,
            awready=1,
            awaddr=0,
            awlen=0,
            awsize=2,
            awburst=1,
        ),
        plan,
        state,
    )
    with pytest.raises(AssertionError, match="runtime.protocol_finalization"):
        finalize_protocol_assertions(plan, state)


def test_axi_stream_continuous_packet_constraints_are_capability_gated() -> None:
    interface = _interface("axi4_stream")
    interface["channels"][0]["protocol_capabilities"] = {
        "continuous_packets": True
    }
    _, check = _checker(interface)
    check(tvalid=1, tready=1, tdata=1, tkeep=0xF, tstrb=0xF, tid=1, tdest=1, tlast=0)
    check(tvalid=1, tready=1, tdata=2, tkeep=0x3, tstrb=0x3, tid=1, tdest=1, tlast=1)

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="contiguous low-byte prefix"):
        check(tvalid=1, tready=1, tdata=2, tkeep=0x5, tstrb=0x5, tid=1, tdest=1, tlast=1)

    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="cannot contain position bytes"):
        check(tvalid=1, tready=1, tdata=2, tkeep=0x3, tstrb=0x1, tid=1, tdest=1, tlast=1)


def test_axi_stream_accepts_24_bit_data_and_absent_tready() -> None:
    interface = _interface("axi4_stream")
    interface["signals"] = [
        signal
        for signal in interface["signals"]
        if signal["name"] != "tready"
    ]
    for signal in interface["signals"]:
        if signal["name"] == "tdata":
            signal["width"] = "24"
        elif signal["name"] in {"tkeep", "tstrb"}:
            signal["width"] = "3"
    plan = compile_standard_protocol_plan(interface)
    stream = plan["groups"][0]["channels"]["stream"]
    assert stream["ready"] is None
    assert stream["widths"]["data"] == 24


def test_axi_unaligned_first_window_uses_only_descriptor_legal_lanes() -> None:
    interface = _interface("axi4")
    _, check = _checker(interface)
    # address=1, AxSIZE=1 describes only byte lane 1 on the unaligned first beat.
    check(
        awvalid=1,
        awready=1,
        awaddr=1,
        awlen=0,
        awsize=1,
        awburst=1,
        wvalid=1,
        wready=1,
        wstrb=0b0010,
        wlast=1,
    )
    _, check = _checker(interface)
    with pytest.raises(AssertionError, match="outside allowed mask"):
        check(
            awvalid=1,
            awready=1,
            awaddr=1,
            awlen=0,
            awsize=1,
            awburst=1,
            wvalid=1,
            wready=1,
            wstrb=0b0100,
            wlast=1,
        )


def test_specialized_coverage_samples_only_real_transfers() -> None:
    interface = _interface("axi4")
    plan = build_interface_coverage_plan(interface)
    monitor = ProtocolCoverageMonitor(plan)
    idle = monitor.sample(_snapshot(interface, awvalid=1, awready=0, awburst=2, awlen=3))
    assert not any("axi4_burst_type" in obligation for obligation, _ in idle)
    accepted = monitor.sample(
        _snapshot(
            interface,
            awvalid=1,
            awready=1,
            awaddr=0x40,
            awburst=2,
            awlen=3,
            awsize=2,
        )
    )
    assert any(bin_name == "wrapping" for _, bin_name in accepted)
    assert any(bin_name == "two_to_sixteen" for _, bin_name in accepted)


def test_generated_tb_block_embeds_axi_plan_and_tool_owned_scenarios() -> None:
    interface = _interface("axi4_stream")
    coverage_plan = build_interface_coverage_plan(interface)
    source = render_contract_generated_block(coverage_plan)
    assert "CONTRACT_PROTOCOL_ASSERTION_PLAN" in source
    assert "CONTRACT_PROTOCOL_STIMULUS_PLAN" in source
    assert "_contract_drive_protocol_transfers" in source
    assert "_contract_collect_protocol_transfers" in source
    assert "protocol.bus.strobe_is_subset_of_keep" in source
    namespace: dict = {}
    exec(source, namespace)
    scenarios = namespace["_contract_protocol_scenarios"]("bus")
    assert any(item["kind"] == "axi4_stream_packet" for item in scenarios)
    channel = namespace["_contract_protocol_channel"]("bus", "stream")
    assert channel["fields"]["data"] == "tdata"
