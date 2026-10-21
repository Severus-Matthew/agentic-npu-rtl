"""Generate legal, role-bound protocol scenarios without interpreting names."""

from __future__ import annotations

import random
from typing import Any, Mapping

from multigent.verifier_tool.protocol.coverage.plan import build_interface_coverage_plan
from multigent.verifier_tool.feature_plan import build_protocol_feature_plan
from multigent.verifier_tool.pool.feature_plans.catalog import (
    load_protocol_feature_catalog,
)
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_stimulus_feature_plan,
)
from multigent.verifier_tool.pool.role_pool.standard_protocols import compile_standard_protocol_plan
from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
    compile_protocol_semantics,
)


class ProtocolStimulusGenerationError(ValueError):
    """The frozen interface cannot produce a safe standard-protocol stimulus."""


def _targets(plan: Mapping[str, Any], *, group: str, templates: set[str]) -> list[str]:
    result = []
    for item in plan.get("obligations", []):
        bindings = item.get("bindings", {})
        if item.get("template") not in templates:
            continue
        if bindings.get("protocol_group") == group or str(item.get("scope_name")) == group:
            result.append(str(item["id"]))
    return sorted(result)


def _common_channel_scenarios(group: Mapping[str, Any], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    catalog = load_protocol_feature_catalog()["features"]
    declared_scenarios = [
        dict(scenario)
        for feature_name in (
            "handshake_states",
            "handshake_arrival_order",
            "stall_stability",
        )
        for scenario in catalog[feature_name]["stimulus"].get("scenarios", [])
        if isinstance(scenario, Mapping)
    ]
    for kind, channel in group["channels"].items():
        common = {
            "protocol_channel": kind,
            "bindings": {
                "valid": channel["valid"],
                "ready": channel["ready"],
                "fields": dict(channel["fields"]),
            },
            "source_owner": "dut" if channel["direction"] == "output" else "testbench",
            "sink_owner": "testbench" if channel["direction"] == "output" else "dut",
            "coverage_targets": [
                str(item["id"])
                for item in plan.get("obligations", [])
                if item.get("scope_name") == channel["name"]
                and item.get("template")
                in {"handshake_states", "handshake_arrival_order", "stall_stability"}
            ],
        }
        for scenario in declared_scenarios:
            name = str(scenario.get("name", ""))
            schedule = dict(scenario.get("schedule", {}))
            if channel.get("ready") in {None, ""} and (
                schedule.get("arrival_order")
                in {"ready_before_valid", "valid_before_ready"}
                or int(schedule.get("stall_cycles", 0)) > 0
            ):
                continue
            result.append(
                {
                    "id": f"{group['name']}.{kind}.{name}",
                    "kind": "channel_schedule",
                    **common,
                    "schedule": schedule,
                    "requirements": [
                        "hold VALID and every mapped source field stable until transfer",
                        "count a transfer only on the active edge with VALID and READY high",
                    ],
                }
            )
    return result


def _axi_address_cases(group: Mapping[str, Any], channel_kind: str) -> list[dict[str, int]]:
    if channel_kind not in group["channels"]:
        return []
    data_kind = "write_data" if channel_kind == "write_address" else "read_data"
    data_width = group["channels"].get(data_kind, {}).get("widths", {}).get("data")
    bus_bytes = int(data_width) // 8 if isinstance(data_width, int) else 1
    full_size = max(0, bus_bytes.bit_length() - 1)
    narrow_size = max(0, full_size - 1)
    boundary_start = 0x1000 - (16 << full_size)
    return [
        {"addr": 0x0000, "len": 0, "size": 0, "burst": 1},
        {"addr": 0x0020, "len": 3, "size": full_size, "burst": 0},
        {"addr": 0x0040, "len": 3, "size": narrow_size, "burst": 1},
        {"addr": 0x0080, "len": 1, "size": full_size, "burst": 2},
        {"addr": 0x0100, "len": 3, "size": full_size, "burst": 2},
        {"addr": 0x0200, "len": 7, "size": full_size, "burst": 2},
        {"addr": 0x0400, "len": 15, "size": full_size, "burst": 2},
        {"addr": 0x0800, "len": 16, "size": 0, "burst": 1},
        {"addr": 0x0800, "len": 255, "size": 0, "burst": 1},
        {"addr": 0x0001, "len": 3, "size": full_size, "burst": 1},
        {"addr": boundary_start, "len": 15, "size": full_size, "burst": 1},
    ]


def _axi4_scenarios(group: Mapping[str, Any], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = _common_channel_scenarios(group, plan)
    target_set = _targets(
        plan,
        group=group["name"],
        templates={
            "axi4_burst_type",
            "axi4_burst_length",
            "axi4_transfer_size",
            "axi4_alignment",
            "axi4_4k_boundary",
            "axi4_write_strobe",
            "axi4_write_channel_order",
            "axi4_response_code",
            "axi4_outstanding_depth",
            "axi4_sideband_partition",
        },
    )
    for address_kind in ("write_address", "read_address"):
        for index, descriptor in enumerate(_axi_address_cases(group, address_kind)):
            result.append(
                {
                    "id": f"{group['name']}.{address_kind}.legal_burst_{index:02d}",
                    "kind": "axi4_transaction",
                    "protocol_channel": address_kind,
                    "address": descriptor,
                    "data_pattern": "incrementing_bytes",
                    "write_strobes": ["full", "sparse", "all_zero"] if address_kind == "write_address" else [],
                    "response": "okay",
                    "coverage_targets": target_set,
                }
            )
    if {"write_address", "write_data"} <= set(group["channels"]):
        data_width = group["channels"]["write_data"].get("widths", {}).get("data")
        bus_bytes = int(data_width) // 8 if isinstance(data_width, int) else 1
        full_size = max(0, bus_bytes.bit_length() - 1)
        for order in ("address_first", "data_first", "same_cycle"):
            result.append(
                {
                    "id": f"{group['name']}.write.{order}",
                    "kind": "axi4_write_channel_order",
                    "order": order,
                    "address": {"addr": 0x100, "len": 0, "size": full_size, "burst": 1},
                    "beats": [{"data": 0xA5A5A5A5, "strb": "full", "last": 1}],
                    "coverage_targets": target_set,
                }
            )
        result.append(
            {
                "id": f"{group['name']}.write.multiple_outstanding_same_id",
                "kind": "axi4_outstanding",
                "requests": 3,
                "ids": [0, 0, 0],
                "hold_responses": True,
                "coverage_targets": target_set,
            }
        )
        if "id" in group["channels"]["write_address"]["fields"]:
            result.append(
                {
                    "id": f"{group['name']}.write.multiple_outstanding_ids",
                    "kind": "axi4_outstanding",
                    "requests": 3,
                    "ids": [0, 1, 2],
                    "hold_responses": True,
                    "coverage_targets": target_set,
                }
            )
    return result


def _axi_lite_scenarios(group: Mapping[str, Any], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = _common_channel_scenarios(group, plan)
    targets = _targets(
        plan,
        group=group["name"],
        templates={
            "axi_lite_write_channel_order",
            "axi_lite_write_strobe",
            "axi_lite_response_code",
            "axi_lite_read_write_concurrency",
            "axi_lite_address_partition",
            "axi_lite_protection_partition",
            "axi_lite_outstanding_depth",
        },
    )
    for order in ("address_first", "data_first", "same_cycle"):
        for strobe in ("all_zero", "sparse", "full"):
            result.append(
                {
                    "id": f"{group['name']}.write.{order}.{strobe}",
                    "kind": "axi4_lite_write",
                    "order": order,
                    "addr": 0x10,
                    "data": 0xA5A55A5A,
                    "strb": strobe,
                    "response": "okay",
                    "coverage_targets": targets,
                }
            )
    if {"write_address", "read_address"} <= set(group["channels"]):
        result.extend(
            {
                "id": f"{group['name']}.concurrency.{mode}",
                "kind": "axi4_lite_read_write_concurrency",
                "mode": mode,
                "write_addr": 0x10,
                "read_addr": 0x10,
                "coverage_targets": targets,
            }
            for mode in ("write_only_cycle", "read_only_cycle", "simultaneous")
        )
        for channel_kind in ("write_address", "read_address"):
            for label, address in (
                ("zero", 0),
                ("aligned", 0x10),
                ("unaligned", 0x11),
                ("page_edge_low", 0x1000),
                ("page_edge_high", 0x1FFC),
            ):
                result.append(
                    {
                        "id": f"{group['name']}.{channel_kind}.address_{label}",
                        "kind": "axi4_lite_address",
                        "protocol_channel": channel_kind,
                        "addr": address,
                        "prot_values": [0, 1, 7]
                        if "prot" in group["channels"][channel_kind]["fields"]
                        else [],
                        "coverage_targets": targets,
                    }
                )
        result.append(
            {
                "id": f"{group['name']}.multiple_outstanding",
                "kind": "axi4_lite_outstanding",
                "requests": [
                    {"kind": "write", "addr": 0x10},
                    {"kind": "read", "addr": 0x14},
                    {"kind": "write", "addr": 0x18},
                ],
                "hold_responses": True,
                "preserve_response_order": True,
                "coverage_targets": targets,
            }
        )
    return result


def _axis_scenarios(group: Mapping[str, Any], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = _common_channel_scenarios(group, plan)
    channel = group["channels"]["stream"]
    fields = channel["fields"]
    targets = _targets(
        plan,
        group=group["name"],
        templates={
            "axis_packet_length",
            "axis_keep_pattern",
            "axis_stall_position",
            "axis_back_to_back_packets",
            "axis_sideband_partition",
        },
    )
    packets = [
        {"name": "single_full", "beats": 1, "keep": "full", "stalls": {}},
        {"name": "multi_full", "beats": 4, "keep": "full", "stalls": {}},
        {"name": "partial_last", "beats": 3, "keep": "partial_last", "stalls": {}},
    ]
    if channel.get("ready") not in {None, ""}:
        packets.extend(
            [
                {"name": "stall_first", "beats": 3, "keep": "full", "stalls": {0: 3}},
                {"name": "stall_middle", "beats": 3, "keep": "full", "stalls": {1: 3}},
                {"name": "stall_last", "beats": 3, "keep": "full", "stalls": {2: 3}},
                {"name": "long_stall", "beats": 2, "keep": "full", "stalls": {0: 6}},
            ]
        )
    for packet in packets:
        result.append(
            {
                "id": f"{group['name']}.stream.{packet['name']}",
                "kind": "axi4_stream_packet",
                **packet,
                "sidebands": {
                    field: [0, 1] for field in ("id", "dest", "user") if field in fields
                },
                "coverage_targets": targets,
            }
        )
    if "last" in fields:
        result.extend(
            {
                "id": f"{group['name']}.stream.packets_{spacing}",
                "kind": "axi4_stream_packet_pair",
                "packet_beats": [1, 2],
                "spacing": spacing,
                "coverage_targets": targets,
            }
            for spacing in ("no_gap", "with_gap")
        )
    return result


def _generic_ready_valid_group(
    interface: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Compile exact custom ready/valid channels for shared cocotb primitives."""

    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    channels: dict[str, Any] = {}
    for channel in interface.get("channels", []):
        if (
            not isinstance(channel, Mapping)
            or channel.get("protocol_profile") != "ready_valid"
        ):
            continue
        name = str(channel.get("name", ""))
        attached = [item for item in signals if item.get("channel") == name]
        by_role: dict[str, list[Mapping[str, Any]]] = {}
        for signal in attached:
            by_role.setdefault(str(signal.get("role", "")), []).append(signal)
        if any(len(by_role.get(role, [])) != 1 for role in ("valid", "ready")):
            raise ProtocolStimulusGenerationError(
                f"ready_valid channel {name!r} needs exactly one valid and ready binding"
            )
        fields: dict[str, str] = {}
        widths: dict[str, int | None] = {}
        for role in ("payload", "last", "keep", "strb", "transaction_id"):
            values = by_role.get(role, [])
            if len(values) > 1:
                raise ProtocolStimulusGenerationError(
                    f"ready_valid channel {name!r} maps role {role!r} more than once"
                )
            if values:
                fields[role] = str(values[0].get("name", ""))
                width = values[0].get("width")
                widths[role] = int(width) if str(width).isdigit() else None
        channels[name] = {
            "name": name,
            "direction": str(channel.get("direction", "")),
            "kind": name,
            "valid": str(by_role["valid"][0].get("name", "")),
            "ready": str(by_role["ready"][0].get("name", "")),
            "effective_defaults": {},
            "fields": fields,
            "widths": widths,
        }
    if not channels:
        return None
    group = {
        "name": "contract_ready_valid",
        "profile": "ready_valid",
        "endpoint_role": "mixed",
        "channels": channels,
    }
    return {
        **group,
        "scenarios": _common_channel_scenarios(group, plan),
    }


def build_protocol_stimulus_plan(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Return exhaustive directed scenarios for every mapped standard group."""

    coverage_plan = build_interface_coverage_plan(interface)
    feature_plan = build_protocol_feature_plan(coverage_plan)
    compiled_stimulus = compile_stimulus_feature_plan(feature_plan)
    groups = coverage_plan.get("standard_protocol_plan", {}).get("groups", [])
    generated = []
    for group in groups:
        profile = str(group["profile"])
        if profile == "axi4":
            scenarios = _axi4_scenarios(group, coverage_plan)
        elif profile == "axi4_lite":
            scenarios = _axi_lite_scenarios(group, coverage_plan)
        elif profile == "axi4_stream":
            scenarios = _axis_scenarios(group, coverage_plan)
        elif profile == "custom_mmio":
            scenarios = _common_channel_scenarios(group, coverage_plan)
        else:
            raise ProtocolStimulusGenerationError(
                f"no directed scenario builder for protocol profile {profile!r}"
            )
        generated.append(
            {
                "name": group["name"],
                "profile": profile,
                "endpoint_role": group["endpoint_role"],
                "channels": group["channels"],
                "scenarios": scenarios,
            }
        )
    generic = _generic_ready_valid_group(interface, coverage_plan)
    if generic is not None:
        generated.append(generic)
    event_protocols = []
    for profile in compile_protocol_semantics(interface).get("profiles", []):
        input_transactions = [
            dict(transaction)
            for transaction in profile.get("transactions", [])
            if transaction.get("source_drive") is not None
        ]
        if not input_transactions:
            continue
        event_protocols.append(
            {
                "name": str(profile["name"]),
                "protocol_groups": list(profile.get("protocol_groups", [])),
                "clock": dict(profile.get("clock", {})),
                "driver_component_id": "protocol.driver.contract_event_source",
                "driver_entrypoint": (
                    "multigent.verifier_tool.protocol.stimulus.cocotb:"
                    "drive_protocol_event_transactions"
                ),
                "transactions": input_transactions,
                "requirements": [
                    "drive every source field from the compiled source_drive binding",
                    "hold the presented transaction until its compiled accepted event is true",
                    "credit coverage only from runtime-observed compiled events",
                ],
            }
        )
    reset_scenarios = []
    for item in coverage_plan.get("obligations", []):
        if item.get("template") != "reset_behavior":
            continue
        reset_scenarios.append(
            {
                "id": f"reset.{item['scope_name']}.assert_release",
                "kind": "reset_sequence",
                "signal": item["bindings"]["signal"],
                "active_value": item["bindings"].get("active_value"),
                "asserted_cycles": 2,
                "post_release_idle_cycles": 2,
                "coverage_targets": [item["id"]],
                "requirements": [
                    "all mapped VALID signals are low while reset is active",
                    "discard pre-reset pending protocol state",
                    "sample asserted, deasserted, and release states",
                ],
            }
        )
    return {
        "schema_version": 2,
        "source": "verifier_tool role-bound protocol stimulus generator",
        "feature_plan": feature_plan,
        "compiled_stimulus": compiled_stimulus,
        "interface_contract": dict(interface),
        "global_scenarios": reset_scenarios,
        "groups": generated,
        "event_protocols": event_protocols,
        "execution_contract": [
            "testbench drives only DUT input signals and observes DUT output signals",
            "all source fields remain stable from presentation through the accepting edge",
            "scenario completion is measured from actual VALID&&READY transfers",
            "coverage is credited only by runtime observations, never by scenario labels",
        ],
    }


def resolved_operation_transport_variants(interface: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Compile reusable timing/address parameters from required protocol features.

    The operation campaign remains responsible for executing these with its
    protocol-specific driver. This function does not know an accelerator name
    or signal spelling and never assumes a planned scenario earned coverage.
    """

    coverage_plan = build_interface_coverage_plan(interface)
    feature_plan = build_protocol_feature_plan(coverage_plan)
    standard_groups = compile_standard_protocol_plan(interface).get("groups", [])
    write_address_names = {
        str(group["channels"]["write_address"]["name"])
        for group in standard_groups
        if group.get("profile") == "axi4"
        and group.get("endpoint_role") == "manager"
        and "write_address" in group.get("channels", {})
    }
    output_channels = {
        str(channel.get("name", ""))
        for channel in interface.get("channels", [])
        if isinstance(channel, Mapping)
        and channel.get("direction") == "output"
        and channel.get("protocol_profile") in {"axi4", "axi4_lite"}
    }
    stall_lengths: set[int] = set()
    simultaneous = False
    for feature in feature_plan.get("features", []):
        if str(feature.get("scope_name", "")) not in output_channels:
            continue
        kind = str(feature.get("kind", ""))
        for scenario in feature.get("stimulus", {}).get("scenarios", []):
            schedule = scenario.get("schedule", {})
            if kind == "stall_stability":
                length = int(schedule.get("stall_cycles", 0))
                if length > 0:
                    stall_lengths.add(length)
            elif schedule.get("arrival_order") == "simultaneous":
                simultaneous = True

    variants = [
        {"stall_cycles": 0, "simultaneous": False, "tail_beats": None},
        *(
            {"stall_cycles": length, "simultaneous": False, "tail_beats": None}
            for length in sorted(stall_lengths)
        ),
    ]
    if simultaneous:
        variants.append({"stall_cycles": 0, "simultaneous": True, "tail_beats": None})

    required_length_bins = {
        str(bin_spec["name"])
        for obligation in coverage_plan.get("obligations", [])
        if obligation.get("template") == "axi4_burst_length"
        and obligation.get("bindings", {}).get("endpoint_role") == "manager"
        for bin_spec in obligation.get("bins", [])
        if bin_spec.get("required", True)
    }
    for bin_name, tail_beats in (("single", 1), ("two_to_sixteen", 8)):
        if bin_name in required_length_bins:
            variants.append(
                {"stall_cycles": 0, "simultaneous": False, "tail_beats": tail_beats}
            )
    if any(
        obligation.get("template") == "axi4_write_channel_order"
        and obligation.get("bindings", {}).get("endpoint_role") == "manager"
        and any(
            bin_spec["name"] == "address_first" and bin_spec.get("required", True)
            for bin_spec in obligation.get("bins", [])
        )
        for obligation in coverage_plan.get("obligations", [])
    ):
        variants.append({
            "stall_cycles": 0, "simultaneous": False, "tail_beats": None,
            "write_data_stall_cycles": 8,
        })
    if any(
        obligation.get("template") == "stall_stability"
        and obligation.get("scope_name") in write_address_names
        and any(bin_spec["name"] == "one_cycle_stall" and bin_spec.get("required", True)
                for bin_spec in obligation.get("bins", []))
        for obligation in coverage_plan.get("obligations", [])
    ):
        variants.append({
            "stall_cycles": 0, "simultaneous": False, "tail_beats": None,
            "write_address_one_cycle_probe": True,
        })
    return variants


def resolved_control_plane_probe_plan(
    interface: Mapping[str, Any], protocol_group: str,
) -> dict[str, Any]:
    """Select non-destructive AXI4-Lite register probes from required bins.

    The actual register/address is supplied by the lifecycle command contract;
    this protocol planner only selects reusable bus behaviors. In particular,
    it never guesses that an arbitrary unmapped address is harmless.
    """

    required = {
        (str(obligation["template"]), str(bin_spec["name"]),
         str(obligation.get("bindings", {}).get("protocol_channel", "")))
        for obligation in build_interface_coverage_plan(interface).get("obligations", [])
        if obligation.get("bindings", {}).get("protocol_group") == protocol_group
        and obligation.get("bindings", {}).get("endpoint_role") == "subordinate"
        for bin_spec in obligation.get("bins", [])
        if bin_spec.get("required", True)
    }
    groups = compile_standard_protocol_plan(interface).get("groups", [])
    control = next(
        (group for group in groups if group.get("name") == protocol_group
         and group.get("profile") == "axi4_lite"), None,
    )
    if control is None:
        raise ProtocolStimulusGenerationError(
            f"{protocol_group!r} is not a resolved AXI4-Lite group"
        )
    channel_names = {
        kind: str(channel["name"])
        for kind, channel in control.get("channels", {}).items()
    }
    stall_bins = {
        (str(obligation["scope_name"]), str(bin_spec["name"]))
        for obligation in build_interface_coverage_plan(interface).get("obligations", [])
        if obligation.get("template") == "stall_stability"
        for bin_spec in obligation.get("bins", [])
        if bin_spec.get("required", True)
    }
    result = {
        "unaligned_write": ("axi_lite_address_partition", "unaligned", "write_address") in required,
        "unaligned_read": ("axi_lite_address_partition", "unaligned", "read_address") in required,
        "sparse_strobe": ("axi_lite_write_strobe", "sparse", "write_data") in required,
        "zero_strobe": ("axi_lite_write_strobe", "all_zero", "write_data") in required,
        "concurrent_read_write": ("axi_lite_read_write_concurrency", "simultaneous", "") in required,
        "multiple_outstanding": ("axi_lite_outstanding_depth", "multiple", "") in required,
    }
    result["response_stall_lengths"] = {
        kind: tuple(length for name, length in (
            ("one_cycle_stall", 1), ("long_stall", 8),
        ) if (channel_names.get(kind), name) in stall_bins)
        for kind in ("write_response", "read_data")
    }
    return result


def generate_random_protocol_scenarios(
    interface: Mapping[str, Any], count: int, *, seed: int = 0
) -> list[dict[str, Any]]:
    """Generate reproducible legal randomized traffic parameters for stress tests."""

    if count < 0:
        raise ProtocolStimulusGenerationError("count must be nonnegative")
    base = build_protocol_stimulus_plan(interface)
    rng = random.Random(seed)
    result: list[dict[str, Any]] = []
    for group in base["groups"]:
        for index in range(count):
            profile = group["profile"]
            if profile == "axi4":
                burst = rng.choice((0, 1, 2))
                data_channel = group["channels"].get("write_data") or group["channels"].get("read_data")
                data_width = data_channel.get("widths", {}).get("data") if data_channel else None
                bus_bytes = int(data_width) // 8 if isinstance(data_width, int) else 1
                size = rng.randint(0, max(0, bus_bytes.bit_length() - 1))
                beats = (
                    rng.choice((2, 4, 8, 16))
                    if burst == 2
                    else rng.randint(1, min(256, 0x1000 >> size))
                    if burst == 1
                    else rng.randint(1, 16)
                )
                span = beats << size
                address = rng.randrange(0, max(1, 0x1000 - span + 1))
                if burst == 2:
                    address -= address % (1 << size)
                parameters = {
                    "burst": burst,
                    "len": beats - 1,
                    "size": size,
                    "addr": address,
                    "stall_cycles": rng.randint(0, 12),
                }
            elif profile == "axi4_lite":
                data_channel = group["channels"].get("write_data") or group["channels"].get("read_data")
                data_width = data_channel.get("widths", {}).get("data") if data_channel else 32
                parameters = {
                    "addr": rng.randrange(0, 0x1000),
                    "data": rng.getrandbits(int(data_width) if isinstance(data_width, int) else 32),
                    "strb_pattern": rng.choice(("all_zero", "sparse", "full")),
                    "order": rng.choice(("address_first", "data_first", "same_cycle")),
                    "stall_cycles": rng.randint(0, 12),
                }
            elif profile == "axi4_stream":
                beats = rng.randint(1, 32)
                parameters = {
                    "beats": beats,
                    "partial_last": bool(rng.getrandbits(1)),
                    "stall_positions": sorted(
                        {rng.randrange(0, beats) for _ in range(rng.randint(0, 5))}
                    ),
                    "stall_cycles": rng.randint(0, 12),
                }
            elif profile in {"custom_mmio", "ready_valid"}:
                parameters = {
                    "arrival_order": rng.choice(
                        ("simultaneous", "valid_before_ready", "ready_before_valid")
                    ),
                    "stall_cycles": rng.randint(0, 12),
                }
            else:
                raise ProtocolStimulusGenerationError(
                    f"no randomized scenario builder for protocol profile {profile!r}"
                )
            result.append(
                {
                    "id": f"{group['name']}.random.{seed}.{index}",
                    "kind": f"{profile}_random",
                    "protocol_group": group["name"],
                    "parameters": parameters,
                }
            )
    return result
