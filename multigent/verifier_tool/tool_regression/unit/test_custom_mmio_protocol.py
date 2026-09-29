"""LLM-declared custom memory-like protocol capture (``protocol_profile:
custom_mmio``): proves the exact same multi-outstanding, ID-correlated,
burst-aware engine built for full AXI4 applies to a protocol that is not
AXI at all, reusing only the generic protocol_group/protocol_channel/
protocol_field tag vocabulary -- channel and signal names below are
deliberately non-AXI (``req_out``/``dat_in``/``ack_in``) to prove nothing
is matched by spelling.
"""
from __future__ import annotations

import pytest

from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import contracts
from multigent.verifier_tool import build_architect_operation_metadata
from multigent.verifier_tool.protocol.stimulus.stimulus_generator import (
    build_protocol_stimulus_plan,
    generate_random_protocol_scenarios,
)
from multigent.verifier_tool.pool.operation_metadata.protocol import (
    ProtocolAdapterError,
    ReadyValidCaptureAdapter,
)


def custom_contracts(*, with_id: bool = True, with_write_ack: bool = True):
    architecture, _ = contracts()
    channels = [
        {
            "name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
            "data_objects": [], "ordering": "one command", "framing": "one beat",
        }
    ]
    signals = [
        {"name": "clk", "role": "clock", "direction": "input", "channel": None},
        {"name": "rst_n", "role": "reset", "direction": "input", "channel": None,
         "semantic": "synchronous active-low reset"},
        {"name": "cmd_valid", "role": "valid", "direction": "input", "channel": "cmd"},
        {"name": "cmd_ready", "role": "ready", "direction": "output", "channel": "cmd"},
        {"name": "opcode", "role": "payload", "semantic_class": "command",
         "direction": "input", "channel": "cmd", "width": "8", "semantic": "legal only 8'h01"},
    ]
    for signal, data_object in (
        ("left_ptr", "A_matrix"), ("right_ptr", "B_matrix"),
        ("bias_ptr", "bias_vector"), ("result_ptr", "Y_matrix"),
    ):
        signals.append({
            "name": signal, "role": "metadata", "semantic_class": "address",
            "direction": "input", "channel": "cmd", "width": "32",
            "semantic": (
                f"data_object={data_object} address_role=base byte_order=little "
                "address_sequence=contiguous word_stride_bytes=4"
            ),
        })

    def add_channel(name, kind, direction, objects, fields, *, group):
        # A custom_mmio group has only 3 generic kinds (request/data/
        # response), unlike AXI4's 5 direction-specific kinds -- so read and
        # write each need their own protocol_group, exactly as if they were
        # two separate physical ports (which is what most custom protocols
        # actually look like; a single combined read+write port that still
        # wants this tool's automatic capture should just declare axi4).
        channels.append({
            "name": name, "direction": direction, "protocol_profile": "custom_mmio",
            "data_objects": objects, "ordering": "any completion order", "framing": "burst",
            "metadata": [f"protocol_group={group} protocol_channel={kind}"],
        })
        prefix = name
        signals.extend([
            {"name": f"{prefix}_valid", "role": "valid", "direction": direction,
             "channel": name, "width": "1"},
            {"name": f"{prefix}_ready", "role": "ready",
             "direction": "input" if direction == "output" else "output",
             "channel": name, "width": "1"},
        ])
        for field, (role, semantic_class, width) in fields.items():
            signals.append({
                "name": f"{prefix}_{field}", "role": role,
                "semantic_class": semantic_class, "direction": direction,
                "channel": name, "width": str(width),
                "semantic": f"protocol_field={field}",
            })

    id_field = {"id": ("transaction_id", "identifier", 4)} if with_id else {}

    # Read side: a request channel (address only) and a data channel that is
    # itself the completion (matching AXI4's RDATA-is-the-read-response shape).
    add_channel("req_out", "request", "output", [], {
        "addr": ("payload", "address", 32), **id_field,
    }, group="my_mem_r")
    add_channel("dat_in", "data", "input", ["A_matrix", "B_matrix", "bias_vector"], {
        "data": ("payload", "data", 32), "last": ("last", "framing", 1), **id_field,
    }, group="my_mem_r")

    # Write side: a request channel, a data channel, and -- only if
    # with_write_ack -- a separate completion-ack channel (proving the ack
    # channel is genuinely optional, unlike AXI4's always-present BRESP).
    add_channel("wreq_out", "request", "output", [], {
        "addr": ("payload", "address", 32), **id_field,
    }, group="my_mem_w")
    write_data_fields = {"data": ("payload", "data", 32), "last": ("last", "framing", 1), **id_field}
    if not with_write_ack:
        write_data_fields = {**write_data_fields, "resp": ("metadata", "response_code", 2)}
    add_channel("wdat_out", "data", "output", ["Y_matrix"], write_data_fields, group="my_mem_w")
    if with_write_ack:
        add_channel("ack_in", "response", "input", [], {
            "resp": ("payload", "response_code", 2), **id_field,
        }, group="my_mem_w")

    signals.extend([
        {"name": "busy", "role": "busy", "direction": "output", "channel": None},
        {"name": "completion", "role": "completion", "direction": "output", "channel": None},
        {"name": "error", "role": "error", "direction": "output", "channel": None,
         "semantic": "sticky error until reset"},
    ])
    return architecture, {"clock": "clk", "reset": "rst_n", "channels": channels, "signals": signals}


def _operation(**kwargs):
    architecture, interface = custom_contracts(**kwargs)
    metadata = build_architect_operation_metadata(architecture, interface)
    return metadata["operations"][0], interface


def test_custom_mmio_stimulus_plan_does_not_dispatch_to_axis():
    _, interface = custom_contracts()
    plan = build_protocol_stimulus_plan(interface)
    custom = [group for group in plan["groups"] if group["profile"] == "custom_mmio"]
    assert {group["name"] for group in custom} == {"my_mem_r", "my_mem_w"}
    assert all(
        scenario["kind"] == "channel_schedule"
        for group in custom
        for scenario in group["scenarios"]
    )
    random = generate_random_protocol_scenarios(interface, 1, seed=7)
    assert all(
        "beats" not in item["parameters"]
        for item in random
        if item["kind"] == "custom_mmio_random"
    )


def _command_snapshot(bases: dict[str, int]) -> dict[str, int]:
    return {
        "cmd_valid": 1, "cmd_ready": 1, "opcode": 1,
        "left_ptr": bases["A_matrix"], "right_ptr": bases["B_matrix"],
        "bias_ptr": bases["bias_vector"], "result_ptr": bases["Y_matrix"],
    }


def _req_beat(prefix, *, addr, id_=None, valid=1, ready=1):
    event = {f"{prefix}_valid": valid, f"{prefix}_ready": ready, f"{prefix}_addr": addr}
    if id_ is not None:
        event[f"{prefix}_id"] = id_
    return event


def _dat_beat(prefix, *, valid=1, ready=1, data=0, last=1, id_=None, resp=None):
    event = {f"{prefix}_valid": valid, f"{prefix}_ready": ready, f"{prefix}_data": data, f"{prefix}_last": last}
    if id_ is not None:
        event[f"{prefix}_id"] = id_
    if resp is not None:
        event[f"{prefix}_resp"] = resp
    return event


def _ack_beat(*, resp=0, id_=None, valid=1, ready=1):
    event = {"ack_in_valid": valid, "ack_in_ready": ready, "ack_in_resp": resp}
    if id_ is not None:
        event["ack_in_id"] = id_
    return event


def _idle(names):
    return {name: 0 for name in names}


_READ_IDLE = ["req_out_valid", "req_out_ready", "dat_in_valid", "dat_in_ready"]
_WRITE_IDLE_WITH_ACK = ["wreq_out_valid", "wreq_out_ready", "wdat_out_valid", "wdat_out_ready", "ack_in_valid", "ack_in_ready"]
_WRITE_IDLE_NO_ACK = ["wreq_out_valid", "wreq_out_ready", "wdat_out_valid", "wdat_out_ready"]


def test_out_of_order_responses_on_a_non_axi_custom_protocol_are_attributed_by_id():
    """Same proof as full AXI4's core test, but on channels/fields named
    nothing like AXI (req_out/dat_in, not ar/r) -- confirms the engine
    matches by role/protocol_field tags only, never by name."""

    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(_READ_IDLE), **_command_snapshot(bases)})

    adapter.observe(_req_beat("req_out", addr=bases["A_matrix"], id_=0))
    adapter.observe(_req_beat("req_out", addr=bases["B_matrix"], id_=1))
    # B's response (id=1) completes first, out of issue order.
    adapter.observe(_dat_beat("dat_in", data=100, id_=1, last=1))
    adapter.observe(_dat_beat("dat_in", data=111, id_=0, last=1))

    result = adapter.consume_operation_inputs(operation)
    assert result["A_matrix"] == [111]
    assert result["B_matrix"] == [100]


def test_degenerates_to_strict_in_order_when_no_id_field_is_bound():
    operation, interface = _operation(with_id=False)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(_READ_IDLE), **_command_snapshot(bases)})

    adapter.observe(_req_beat("req_out", addr=bases["A_matrix"]))
    adapter.observe(_dat_beat("dat_in", data=111, last=1))
    adapter.observe(_req_beat("req_out", addr=bases["B_matrix"]))
    adapter.observe(_dat_beat("dat_in", data=100, last=1))

    result = adapter.consume_operation_inputs(operation)
    assert result["A_matrix"] == [111]
    assert result["B_matrix"] == [100]


def test_write_completes_via_dedicated_ack_channel_when_one_is_declared():
    operation, interface = _operation(with_id=True, with_write_ack=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(_READ_IDLE), **_idle(_WRITE_IDLE_WITH_ACK), **_command_snapshot(bases)})

    adapter.observe(_req_beat("wreq_out", addr=bases["Y_matrix"], id_=7))
    adapter.observe(_dat_beat("wdat_out", data=55, id_=7, last=1))
    adapter.observe(_ack_beat(resp=0, id_=7))

    result = adapter.consume_operation_outputs(operation)
    assert result["Y_matrix"] == [55]


def test_write_ack_channel_is_optional_acceptance_onto_data_channel_is_completion():
    """No 'response'/ack channel declared at all for the write side -- proves
    the ack channel is genuinely optional, unlike AXI4 where BRESP always
    exists. Acceptance onto the data channel itself is the completion
    signal, and that beat's own optional resp field (defaulting to OK) is
    the only success check."""

    operation, interface = _operation(with_id=True, with_write_ack=False)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(_READ_IDLE), **_idle(_WRITE_IDLE_NO_ACK), **_command_snapshot(bases)})

    adapter.observe(_req_beat("wreq_out", addr=bases["Y_matrix"], id_=7))
    adapter.observe(_dat_beat("wdat_out", data=55, id_=7, last=1, resp=0))

    result = adapter.consume_operation_outputs(operation)
    assert result["Y_matrix"] == [55]


def test_write_ack_channel_absent_rejects_a_non_okay_resp_on_the_data_beat_itself():
    operation, interface = _operation(with_id=True, with_write_ack=False)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(_READ_IDLE), **_idle(_WRITE_IDLE_NO_ACK), **_command_snapshot(bases)})

    adapter.observe(_req_beat("wreq_out", addr=bases["Y_matrix"], id_=7))
    adapter.observe(_dat_beat("wdat_out", data=55, id_=7, last=1, resp=2))  # non-OKAY

    with pytest.raises(ProtocolAdapterError, match="non-OKAY write response"):
        adapter.consume_operation_outputs(operation)


def test_response_address_outside_every_bound_window_is_rejected():
    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(_READ_IDLE), **_command_snapshot(bases)})

    adapter.observe(_req_beat("req_out", addr=0x9999, id_=0))
    adapter.observe(_dat_beat("dat_in", data=111, id_=0, last=1))

    with pytest.raises(ProtocolAdapterError, match="not inside any bound data object"):
        adapter.consume_operation_inputs(operation)
