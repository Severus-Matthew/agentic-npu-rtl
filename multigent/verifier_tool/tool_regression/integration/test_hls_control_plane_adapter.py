"""The generated HLS campaign must trust accepted pointer writes, not guesses."""

import pytest
import yaml

from multigent.verifier_tool import build_architect_operation_metadata
from multigent.verifier_tool.pool.operation_metadata.protocol import (
    ProtocolAdapterError,
    ReadyValidCaptureAdapter,
)
from multigent.verifier_tool.protocol.stimulus import (
    default_axi_lite_memory_bases,
    resolved_control_plane_probe_plan,
    resolved_operation_transport_variants,
)
from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT


HERE = BENCHMARKS_ROOT / "int8_gemm_hls_golden"


def _fixture():
    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    operation = build_architect_operation_metadata(architecture, interface)["operations"][0]
    adapter = ReadyValidCaptureAdapter(interface)
    sequence = operation["lifecycle"]["control_plane_sequence"]
    bases = {"A_matrix": 0x10000, "B_matrix": 0x20000, "Y_matrix": 0x30000}
    aw, w, b = [], [], []
    for action in sequence["job_start"]["actions"]:
        register = sequence["registers"][action["register"]]
        aw.append({"addr": register["address"]})
        if action["op"] == "write_reg":
            source = action["value_from"]
            value = bases[source["data_object"]]
            value = value & 0xFFFFFFFF if source["half"] == "low" else value >> 32
        else:
            value = int(action["value"]) << int(register["fields"][action["field"]]["bit"])
        w.append({"data": value})
        b.append({"resp": 0})
    adapter.events.update({"s_axi_control_aw": aw, "s_axi_control_w": w, "s_axi_control_b": b})
    return adapter, operation, bases


def test_control_plane_adapter_reconstructs_accepted_object_bases():
    adapter, operation, bases = _fixture()
    assert adapter._control_plane_object_bases(operation) == bases


def test_control_plane_adapter_rejects_wrong_accepted_register_address():
    adapter, operation, _ = _fixture()
    adapter.events["s_axi_control_aw"][0]["addr"] += 4
    with pytest.raises(ProtocolAdapterError, match="declared register"):
        adapter._control_plane_object_bases(operation)


def test_independent_axi4_memory_ports_are_not_reassembled_as_one_bus(monkeypatch):
    adapter, operation, _ = _fixture()
    # Isolate bus grouping from the packed-word decoder; the real RTL
    # regression exercises the complete accepted-byte path.
    operation = {
        **operation,
        "inputs": [
            {**item, "serialization": {"kind": "dense_tensor"}}
            for item in operation["inputs"]
        ],
    }
    calls = []

    def consume(bindings, command_values, dimensions, direction, *, object_bases):
        calls.append(tuple(item["data_object"] for item in bindings))
        return {item["data_object"]: [1] for item in bindings}

    monkeypatch.setattr(adapter, "_consume_burst_memory_objects", consume)
    result = adapter._consume_memory_objects(operation, "input")
    assert calls == [("A_matrix",), ("B_matrix",)]
    assert result == {"A_matrix": [1], "B_matrix": [1]}


def test_page_offset_variants_keep_every_hls_object_bus_aligned():
    _adapter, operation, _bases = _fixture()
    interior = default_axi_lite_memory_bases(operation)
    one = default_axi_lite_memory_bases(operation, aligned_tail_beats=1)
    eight = default_axi_lite_memory_bases(operation, aligned_tail_beats=8)
    for name, base in interior.items():
        assert one[name] == base + 64
        assert eight[name] == base + 8 * 64


def test_transport_variants_are_resolved_from_protocol_feature_plan():
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    variants = resolved_operation_transport_variants(interface)
    assert {variant["stall_cycles"] for variant in variants} == {0, 1, 3, 6}
    assert {variant["tail_beats"] for variant in variants} == {None, 1, 8}
    assert sum(bool(variant["simultaneous"]) for variant in variants) == 1
    assert [variant.get("write_data_stall_cycles") for variant in variants
            if variant.get("write_data_stall_cycles")] == [8]
    assert sum(bool(variant.get("write_address_one_cycle_probe")) for variant in variants) == 1


def test_control_probes_select_required_bins_without_hls_signal_names():
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    assert resolved_control_plane_probe_plan(interface, "control") == {
        "unaligned_write": True,
        "unaligned_read": True,
        "sparse_strobe": True,
        "zero_strobe": True,
        "concurrent_read_write": True,
        "multiple_outstanding": True,
        "response_stall_lengths": {
            "write_response": (1, 8),
            "read_data": (1, 8),
        },
    }
