from __future__ import annotations

import pytest

from multigent.verifier_tool import (
    CoverageRuntimeError,
    InterfaceCoverageTracker,
    build_extension_coverage_plan,
    check_transaction_completion_payloads,
    merge_coverage_plans,
)
from multigent.verifier_tool.protocol.assertion.completion_payload import (
    CompletionPayloadError,
)


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "entries": [
            {
                "request": {
                    "id": "protocol.example_completion_data",
                    "domain": "protocol",
                    "target": {"scope": "protocol_group", "name": "example"},
                    "semantics": {"summary": "Check completion data."},
                },
                "implementation": {
                    "domain": "protocol",
                    "coverage": {
                        "implementation": {
                            "kind": "verifier_python",
                            "file": "tests/test_example.py",
                            "symbol": "extension_coverage",
                        },
                        "bins": [
                            {
                                "name": "read_observed",
                                "intent": "Observe a checked read completion.",
                                "predicate": {"kind": "observed_event"},
                            },
                            {
                                "name": "reset_observed",
                                "intent": "Observe reset disposal.",
                                "predicate": {"kind": "observed_event"},
                            },
                        ],
                    },
                },
            }
        ],
    }


def test_extension_bins_join_shared_required_denominator() -> None:
    extension_plan = build_extension_coverage_plan(_manifest())
    merged = merge_coverage_plans(
        {"interface_contract": {}, "obligations": [], "monitor": {}},
        {"operation_metadata": {"operations": []}, "obligations": []},
        extension_plan,
    )
    obligation = next(
        item
        for item in merged["obligations"]
        if item["id"] == "extension.protocol.example_completion_data"
    )
    assert [item["name"] for item in obligation["bins"]] == [
        "read_observed",
        "reset_observed",
    ]
    assert all(item["required"] is True for item in obligation["bins"])
    manifest_ids = {
        item["id"] for item in merged["verification_manifest"]["obligations"]
    }
    assert obligation["id"] in manifest_ids


def test_extension_hits_are_sampled_by_exact_request_and_bin_name() -> None:
    extension_plan = build_extension_coverage_plan(_manifest())
    tracker = InterfaceCoverageTracker(
        {
            "schema_version": 3,
            "monitor": {"signals": []},
            "operation_metadata": {"operations": []},
            "obligations": extension_plan["obligations"],
        }
    )
    assert tracker.report()["required_bins"] == 2
    tracker.sample_extension_coverage(
        "protocol.example_completion_data", {"read_observed"}
    )
    report = tracker.report()
    assert report["hit_bins"] == 1
    assert report["missing_bins"] == [
        "extension.protocol.example_completion_data.reset_observed"
    ]
    with pytest.raises(CoverageRuntimeError, match="undeclared coverage bin"):
        tracker.sample_extension_coverage(
            "protocol.example_completion_data", ["invented"]
        )


def test_completion_payload_checker_pairs_same_cycle_payloads() -> None:
    trace = [
        {"event": "accepted", "signals": {"request": 1}},
        {"event": "accepted", "signals": {"request": 2}},
        {"event": "success", "signals": {"ack": 1, "data": 11}},
        {"event": "success", "signals": {"ack": 1, "data": 22}},
    ]
    result = check_transaction_completion_payloads(trace, [11, 22], "data")
    assert result["passed"] is True
    assert result["observed_payloads"] == [11, 22]


def test_completion_payload_checker_supports_out_of_order_keys() -> None:
    trace = [
        {"event": "accepted", "signals": {"request_id": 1}},
        {"event": "accepted", "signals": {"request_id": 2}},
        {"event": "success", "signals": {"response_id": 2, "data": 22}},
        {"event": "success", "signals": {"response_id": 1, "data": 11}},
    ]
    result = check_transaction_completion_payloads(
        trace,
        [11, 22],
        "data",
        request_key_signal="request_id",
        completion_key_signal="response_id",
    )
    assert result["passed"] is True
    assert result["observed_payloads"] == [22, 11]


def test_completion_payload_checker_supports_mixed_read_write_requests() -> None:
    trace = [
        {"event": "accepted", "signals": {"kind": "read"}},
        {"event": "accepted", "signals": {"kind": "write"}},
        {"event": "success", "signals": {"data": 11}},
        {"event": "success", "signals": {"ack": 1}},
    ]
    result = check_transaction_completion_payloads(
        trace,
        [11, None],
        "data",
        payload_required=[True, False],
    )
    assert result["passed"] is True
    assert result["checked_payload_count"] == 1
    assert result["observed_payloads"] == [11]


def test_completion_payload_checker_rejects_misaligned_payload_mask() -> None:
    with pytest.raises(CompletionPayloadError, match="payload_required count"):
        check_transaction_completion_payloads(
            [],
            [11],
            "data",
            payload_required=[True, False],
        )


@pytest.mark.parametrize(
    ("trace", "expected", "message"),
    [
        ([], [], "no accepted request"),
        (
            [{"event": "accepted", "signals": {"request": 1}}],
            [11],
            "remain without completion",
        ),
        (
            [{"event": "success", "signals": {"data": 11}}],
            [],
            "has no accepted request",
        ),
        (
            [
                {"event": "accepted", "signals": {"request": 1}},
                {"event": "success", "signals": {"data": 12}},
            ],
            [11],
            "payload mismatch",
        ),
    ],
)
def test_completion_payload_checker_rejects_vacuous_or_incorrect_evidence(
    trace: list[dict], expected: list[int], message: str
) -> None:
    result = check_transaction_completion_payloads(trace, expected, "data")
    assert result["passed"] is False
    assert any(message in item for item in result["errors"])
