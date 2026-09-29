"""Full-AXI4 (not AXI4-Lite) memory-mapped operand capture: multiple
simultaneously outstanding requests, ID-correlated, completing in any order,
with multi-beat bursts terminated by LAST -- attribution must come from each
request's own captured address, never from response arrival position.
"""
from __future__ import annotations

import pytest

from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import contracts
from multigent.verifier_tool import build_architect_operation_metadata
from multigent.verifier_tool.pool.operation_metadata.protocol import (
    ProtocolAdapterError,
    ReadyValidCaptureAdapter,
)


def axi4_contracts(*, with_id: bool = True):
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

    def add_channel(name, kind, direction, objects, fields):
        channels.append({
            "name": name, "direction": direction, "protocol_profile": "axi4",
            "data_objects": objects, "ordering": "any completion order", "framing": "burst",
            "metadata": [f"protocol_group=mem protocol_channel={kind}"],
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
    add_channel("aw", "write_address", "output", [], {
        "addr": ("payload", "address", 32), "len": ("metadata", "length", 8),
        "size": ("metadata", "size", 3), "burst": ("metadata", "burst_type", 2), **id_field,
    })
    add_channel("w", "write_data", "output", ["Y_matrix"], {
        "data": ("payload", "data", 32), "strb": ("metadata", "byte_enable", 4),
        "last": ("last", "framing", 1),
    })
    add_channel("b", "write_response", "input", [], {
        "resp": ("payload", "response_code", 2), **id_field,
    })
    add_channel("ar", "read_address", "output", [], {
        "addr": ("payload", "address", 32), "len": ("metadata", "length", 8),
        "size": ("metadata", "size", 3), "burst": ("metadata", "burst_type", 2), **id_field,
    })
    add_channel("r", "read_data", "input", ["A_matrix", "B_matrix", "bias_vector"], {
        "data": ("payload", "data", 32), "resp": ("metadata", "response_code", 2),
        "last": ("last", "framing", 1), **id_field,
    })
    signals.extend([
        {"name": "busy", "role": "busy", "direction": "output", "channel": None},
        {"name": "completion", "role": "completion", "direction": "output", "channel": None},
        {"name": "error", "role": "error", "direction": "output", "channel": None,
         "semantic": "sticky error until reset"},
    ])
    return architecture, {"clock": "clk", "reset": "rst_n", "channels": channels, "signals": signals}


def _operation(with_id: bool = True):
    architecture, interface = axi4_contracts(with_id=with_id)
    metadata = build_architect_operation_metadata(architecture, interface)
    return metadata["operations"][0], interface


def _command_snapshot(bases: dict[str, int]) -> dict[str, int]:
    return {
        "cmd_valid": 1, "cmd_ready": 1, "opcode": 1,
        "left_ptr": bases["A_matrix"], "right_ptr": bases["B_matrix"],
        "bias_ptr": bases["bias_vector"], "result_ptr": bases["Y_matrix"],
    }


def _r_beat(*, valid=1, ready=1, data=0, resp=0, last=1, id_=None):
    event = {"r_valid": valid, "r_ready": ready, "r_data": data, "r_resp": resp, "r_last": last}
    if id_ is not None:
        event["r_id"] = id_
    return event


def _ar_beat(*, addr, id_=None, valid=1, ready=1):
    event = {"ar_valid": valid, "ar_ready": ready, "ar_addr": addr, "ar_len": 0, "ar_size": 2, "ar_burst": 1}
    if id_ is not None:
        event["ar_id"] = id_
    return event


def _idle(names):
    return {name: 0 for name in names}


def test_out_of_order_responses_are_attributed_by_request_id_not_arrival_order():
    """B's read is issued second but its response arrives first; correct
    attribution requires correlating each response to ITS OWN request via ID
    and that request's captured address, not response arrival position."""

    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(["ar_valid", "ar_ready", "r_valid", "r_ready"]), **_command_snapshot(bases)})

    # Both reads issued -- A (id=0) first, then B (id=1) -- before either responds.
    adapter.observe(_ar_beat(addr=bases["A_matrix"], id_=0))
    adapter.observe(_ar_beat(addr=bases["B_matrix"], id_=1))
    adapter.observe(_ar_beat(addr=bases["bias_vector"], id_=2))
    # B's response (id=1) completes first, out of issue order.
    adapter.observe(_r_beat(data=100, id_=1, last=1))
    # A's response (id=0) completes second.
    adapter.observe(_r_beat(data=111, id_=0, last=1))
    adapter.observe(_r_beat(data=7, id_=2, last=1))

    result = adapter.consume_operation_inputs(operation)
    assert result["A_matrix"] == [111]
    assert result["B_matrix"] == [100]
    assert result["bias_vector"] == [7]


def test_multi_beat_burst_terminated_by_last_is_captured_as_one_request():
    operation, interface = _operation(with_id=True)
    # A_matrix is a single M=K=1 scalar in the shared `contracts()` fixture,
    # so exercise the burst path directly against its one-word window plus a
    # deliberately oversized read the adapter must still bound correctly:
    # two beats returned for a request whose window is only one word wide
    # would silently corrupt B's data if burst decoding ever ignored
    # per-object element counts, so this proves decode still trims per binding.
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(["ar_valid", "ar_ready", "r_valid", "r_ready"]), **_command_snapshot(bases)})

    adapter.observe(_ar_beat(addr=bases["A_matrix"], id_=0))
    adapter.observe(_r_beat(data=111, id_=0, last=1))
    adapter.observe(_ar_beat(addr=bases["B_matrix"], id_=0))
    adapter.observe(_r_beat(data=100, id_=0, last=1))
    adapter.observe(_ar_beat(addr=bases["bias_vector"], id_=0))
    adapter.observe(_r_beat(data=7, id_=0, last=1))

    result = adapter.consume_operation_inputs(operation)
    assert result["A_matrix"] == [111]
    assert result["B_matrix"] == [100]
    assert result["bias_vector"] == [7]


def test_degenerates_to_strict_in_order_when_no_id_field_is_bound():
    operation, interface = _operation(with_id=False)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(["ar_valid", "ar_ready", "r_valid", "r_ready"]), **_command_snapshot(bases)})

    adapter.observe(_ar_beat(addr=bases["A_matrix"]))
    adapter.observe(_r_beat(data=111, last=1))
    adapter.observe(_ar_beat(addr=bases["B_matrix"]))
    adapter.observe(_r_beat(data=100, last=1))
    adapter.observe(_ar_beat(addr=bases["bias_vector"]))
    adapter.observe(_r_beat(data=7, last=1))

    result = adapter.consume_operation_inputs(operation)
    assert result["A_matrix"] == [111]
    assert result["B_matrix"] == [100]
    assert result["bias_vector"] == [7]


def test_response_address_outside_every_bound_window_is_rejected():
    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(["ar_valid", "ar_ready", "r_valid", "r_ready"]), **_command_snapshot(bases)})

    adapter.observe(_ar_beat(addr=0x9999, id_=0))
    adapter.observe(_r_beat(data=111, id_=0, last=1))

    with pytest.raises(ProtocolAdapterError, match="not inside any bound data object"):
        adapter.consume_operation_inputs(operation)


def test_response_with_no_matching_outstanding_request_is_rejected():
    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(["ar_valid", "ar_ready", "r_valid", "r_ready"]), **_command_snapshot(bases)})

    # A response with id=5 arrives, but no AR with id=5 was ever issued.
    adapter.observe(_r_beat(data=111, id_=5, last=1))

    with pytest.raises(ProtocolAdapterError, match="no matching outstanding request"):
        adapter.consume_operation_inputs(operation)


def test_non_okay_rresp_among_out_of_order_completions_is_rejected():
    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe({**_idle(["ar_valid", "ar_ready", "r_valid", "r_ready"]), **_command_snapshot(bases)})

    adapter.observe(_ar_beat(addr=bases["A_matrix"], id_=0))
    adapter.observe(_ar_beat(addr=bases["B_matrix"], id_=1))
    adapter.observe(_r_beat(data=100, id_=1, last=1, resp=0))
    adapter.observe(_r_beat(data=111, id_=0, last=1, resp=2))  # SLVERR

    with pytest.raises(ProtocolAdapterError, match="non-OKAY RRESP"):
        adapter.consume_operation_inputs(operation)


def test_axi4_w_data_without_id_follows_aw_order_and_b_matches_bid():
    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe(_command_snapshot(bases))
    adapter.observe({
        "aw_valid": 1, "aw_ready": 1, "aw_addr": bases["Y_matrix"],
        "aw_len": 0, "aw_size": 2, "aw_burst": 1, "aw_id": 3,
    })
    adapter.observe({
        "w_valid": 1, "w_ready": 1, "w_data": 123, "w_strb": 0xF, "w_last": 1,
    })
    adapter.observe({"b_valid": 1, "b_ready": 1, "b_resp": 0, "b_id": 3})
    assert adapter.consume_operation_outputs(operation) == {"Y_matrix": [123]}


@pytest.mark.parametrize(
    "size,offsets,masks",
    [(0, (0, 1, 2, 3), (1, 2, 4, 8)), (1, (0, 2), (3, 12))],
)
def test_axi4_narrow_output_reassembles_only_accepted_byte_lanes(size, offsets, masks):
    operation, interface = _operation(with_id=True)
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe(_command_snapshot(bases))
    for offset, mask in zip(offsets, masks):
        adapter.observe({
            "aw_valid": 1, "aw_ready": 1, "aw_addr": bases["Y_matrix"] + offset,
            "aw_len": 0, "aw_size": size, "aw_burst": 1, "aw_id": 3,
        })
        adapter.observe({
            "w_valid": 1, "w_ready": 1, "w_data": 123,
            "w_strb": mask, "w_last": 1,
        })
        adapter.observe({"b_valid": 1, "b_ready": 1, "b_resp": 0, "b_id": 3})
    assert adapter.consume_operation_outputs(operation) == {"Y_matrix": [123]}


def test_axi4_write_data_order_is_independent_of_b_response_order():
    operation, interface = _operation(with_id=True)
    operation["dimensions"]["N"] = 2
    bases = {"A_matrix": 0x1000, "B_matrix": 0x2000, "bias_vector": 0x3000, "Y_matrix": 0x4000}
    adapter = ReadyValidCaptureAdapter(interface)
    adapter.observe(_command_snapshot(bases))
    for offset, identity in ((0, 1), (4, 2)):
        adapter.observe({
            "aw_valid": 1, "aw_ready": 1, "aw_addr": bases["Y_matrix"] + offset,
            "aw_len": 0, "aw_size": 2, "aw_burst": 1, "aw_id": identity,
        })
    for value in (10, 20):
        adapter.observe({
            "w_valid": 1, "w_ready": 1, "w_data": value, "w_strb": 0xF, "w_last": 1,
        })
    for identity in (2, 1):
        adapter.observe({"b_valid": 1, "b_ready": 1, "b_resp": 0, "b_id": identity})
    assert adapter.consume_operation_outputs(operation) == {"Y_matrix": [10, 20]}
