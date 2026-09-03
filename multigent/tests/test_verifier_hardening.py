from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent


def _context() -> dict:
    return {
        "verification_policy": {
            "require_completion_behavior_tests_when_defined": True,
            "require_error_behavior_tests_when_defined": True,
        },
        "frozen_architecture": {
            "interface_contract": {
                "protocol": "ready_valid_streaming",
                "signals": [
                    {"name": "in_valid", "semantic": "Input valid"},
                    {"name": "in_ready", "semantic": "Input ready"},
                    {"name": "status_done", "semantic": "Pulses on completion"},
                    {"name": "status_error", "semantic": "Sticky error flag"},
                ],
            }
        },
    }


def test_ready_valid_source_may_not_withdraw_presented_valid() -> None:
    code = """import cocotb
async def drive(valid_sig, ready_sig, data_sig, value):
    valid_sig.value = 1
    data_sig.value = value
    while True:
        await cocotb.triggers.RisingEdge(ready_sig)
        valid_sig.value = 0
        if int(ready_sig.value):
            break
"""
    with pytest.raises(AgentRuntimeError, match="deasserts valid inside"):
        VerifierAgent._validate_ready_valid_driver_safety([code], _context())


def test_ready_valid_source_can_stall_before_presenting_beat() -> None:
    code = """import cocotb
async def drive(valid_sig, ready_sig, data_sig, value):
    valid_sig.value = 0
    await cocotb.triggers.Timer(1, unit='ns')
    valid_sig.value = 1
    data_sig.value = value
    while not int(ready_sig.value):
        await cocotb.triggers.Timer(1, unit='ns')
    valid_sig.value = 0
"""
    VerifierAgent._validate_ready_valid_driver_safety([code], _context())


def test_required_completion_and_error_signals_must_be_referenced() -> None:
    code = """import cocotb
@cocotb.test()
async def test_error_only(dut):
    assert int(dut.status_error.value) == 0
"""
    with pytest.raises(AgentRuntimeError, match="status_done"):
        VerifierAgent._validate_required_signal_coverage([code], _context())


def test_required_completion_and_error_signals_can_be_covered() -> None:
    code = """import cocotb
@cocotb.test()
async def test_status(dut):
    assert int(dut.status_error.value) == 0
    assert int(dut.status_done.value) in (0, 1)
"""
    VerifierAgent._validate_required_signal_coverage([code], _context())
