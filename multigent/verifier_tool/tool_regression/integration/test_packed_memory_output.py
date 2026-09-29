"""A packed memory result retires by bus word but compares by logical element."""

from __future__ import annotations

from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_lifecycle_feature_plan,
)
from multigent.verifier_tool.tool_regression.benchmarks.u55c_inspired_int8_gemm_4x4x4 import (
    build_contract_and_tb,
)
from multigent.verifier_tool.orchestration import campaign


def _packed_operation():
    architecture, interface, _, _ = build_contract_and_tb.build_architecture_contract()
    metadata = build_architect_operation_metadata(architecture, interface)
    operation = metadata["operations"][0]
    operation["dimensions"]["M"] = 3
    output = operation["outputs"][0]
    output["data_type"] = {"name": "s8", "width_bits": 8, "signed": True}
    output["memory_mapping"]["elements_per_word"] = 4
    return interface, metadata, operation


def test_packed_result_retirement_counts_accepted_words_not_elements():
    interface, metadata, _ = _packed_operation()

    plan = build_lifecycle_feature_plan(interface, metadata)
    retirement = plan["bindings"]["operations"][0]["retirements"][0]

    assert retirement["kind"] == "memory_write_response"
    assert retirement["expected_count"] == 3  # ceil(3 * 4 / 4)


def test_packed_result_observation_unpacks_bus_words(monkeypatch):
    _, _, operation = _packed_operation()
    captured = {}

    def record_stimulus(*args, **kwargs):
        captured.update(kwargs)
        return "sample-1"

    monkeypatch.setattr(campaign, "record_stimulus", record_stimulus)
    monkeypatch.setattr(campaign, "sample_operation", lambda *args: None)
    observed_beats = [
        {"payload": 0x7F80FF01},
        {"payload": 0x04030201},
        {"payload": 0x08070605},
    ]

    assert campaign._record_case(operation, {"stimulus": {}, "expected": {}}, observed_beats) == "sample-1"
    assert captured["observed"]["Y_matrix"] == [
        1, -1, -128, 127, 1, 2, 3, 4, 5, 6, 7, 8,
    ]
