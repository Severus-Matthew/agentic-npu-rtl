"""A pipelined synchronous reset may take declared cycles to reach outputs."""

import pytest

from multigent.verifier_tool.lifecycle.assertion.runtime import check_lifecycle_assertions
from multigent.verifier_tool.protocol.assertion.runtime import check_protocol_assertions


def test_protocol_reset_valid_is_checked_after_declared_settle_cycles():
    plan = {
        "reset": "rst_n",
        "reset_active_value": 0,
        "reset_settle_cycles": 2,
        "valid_signals": ("arvalid",),
        "valid_reset_features": {"arvalid": "protocol.mem.valid_low_during_reset"},
        "stalls": [],
        "standard_groups": [],
    }
    state = {}
    snapshot = {"rst_n": 0, "arvalid": 1}
    check_protocol_assertions({"rst_n": 0}, plan, state)
    check_protocol_assertions(snapshot, plan, state)
    check_protocol_assertions({"rst_n": 0}, plan, state)
    check_protocol_assertions(snapshot, plan, state)
    with pytest.raises(AssertionError, match="protocol.mem.valid_low_during_reset"):
        check_protocol_assertions(snapshot, plan, state)
    check_protocol_assertions({"rst_n": 1, "arvalid": 0}, plan, state)
    check_protocol_assertions(snapshot, plan, state)


def test_protocol_reset_valid_supports_per_channel_settle_cycles():
    plan = {
        "reset": "rst_n",
        "reset_active_value": 0,
        "reset_settle_cycles": 0,
        "valid_signals": ("async_valid", "sync_valid"),
        "valid_reset_features": {
            "async_valid": "channel.async.valid_low_during_reset",
            "sync_valid": "channel.sync.valid_low_during_reset",
        },
        "valid_reset_settle_cycles": {"async_valid": 0, "sync_valid": 1},
        "stalls": [],
        "standard_groups": [],
    }
    state = {}
    first = {"rst_n": 0, "async_valid": 0, "sync_valid": 1}
    check_protocol_assertions(first, plan, state)
    with pytest.raises(AssertionError, match="channel.sync.valid_low_during_reset"):
        check_protocol_assertions(first, plan, state)


def test_lifecycle_reset_values_are_checked_after_declared_settle_cycles():
    plan = {
        "reset": {"signal": "rst_n", "active_value": 0, "settle_cycles": 2},
        "reset_outputs": {"awready": 0},
        "operations": [],
    }
    state = {}
    snapshot = {"rst_n": 0, "awready": 1}
    check_lifecycle_assertions({"rst_n": 0}, plan, state)
    check_lifecycle_assertions(snapshot, plan, state)
    check_lifecycle_assertions({"rst_n": 0}, plan, state)
    check_lifecycle_assertions(snapshot, plan, state)
    with pytest.raises(AssertionError, match="outputs_match_declared_reset_values"):
        check_lifecycle_assertions(snapshot, plan, state)
    check_lifecycle_assertions({"rst_n": 1, "awready": 0}, plan, state)
    check_lifecycle_assertions(snapshot, plan, state)
