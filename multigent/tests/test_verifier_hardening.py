from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent
from multigent.tests.test_verifier import generic_fir_context, verification_ready_result


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
                    {"name": "in_valid", "role": "valid", "semantic": "Input valid"},
                    {"name": "in_ready", "role": "ready", "semantic": "Input ready"},
                    {"name": "status_done", "role": "completion", "semantic": "Pulses when work retires"},
                    {"name": "status_error", "role": "error", "semantic": "Sticky fault indication"},
                ],
            }
        },
    }


@pytest.mark.parametrize("code", ["""import cocotb
async def drive(valid_sig, ready_sig, data_sig, value):
    valid_sig.value = 0
    await cocotb.triggers.Timer(1, unit='ns')
    valid_sig.value = 1
    data_sig.value = value
    while not int(ready_sig.value):
        await cocotb.triggers.Timer(1, unit='ns')
    valid_sig.value = 0
""", """import cocotb
async def drive(valid_sig, ready_sig, data_sig, value, rng):
    while True:
        if rng.random() < 0.3:
            valid_sig.value = 0
            await cocotb.triggers.Timer(1, unit='ns')
        else:
            break
    valid_sig.value = 1
    data_sig.value = value
    while not int(ready_sig.value):
        await cocotb.triggers.Timer(1, unit='ns')
    valid_sig.value = 0
""", """import cocotb
async def drive(clk, valid_sig, ready_sig, data_sig, values, rng):
    idx = 0
    while idx < len(values):
        while rng.random() < 0.3:
            valid_sig.value = 0
            await cocotb.triggers.Timer(1, unit='ns')
        await cocotb.triggers.FallingEdge(clk)
        data_sig.value = values[idx]
        valid_sig.value = 1
        while True:
            await cocotb.triggers.Timer(0.1, unit='ns')
            ready_before_edge = int(ready_sig.value)
            await cocotb.triggers.RisingEdge(clk)
            if ready_before_edge:
                valid_sig.value = 0
                idx += 1
                break
            await cocotb.triggers.FallingEdge(clk)
"""])
def test_loop_structure_does_not_reject_driver_artifacts(code: str) -> None:
    # Static validation checks executable artifacts, not temporal protocol
    # correctness. Runtime monitor tests cover actual stall violations.
    result = verification_ready_result()
    result['test_files'][0]['content'] += '\n' + code
    context = generic_fir_context()
    context['frozen_architecture']['interface_contract']['protocol'] = 'ready_valid_streaming'
    VerifierAgent._validate_result(result=result, context=context)


def test_cocotb_driver_cannot_resume_from_read_only_into_next_write() -> None:
    code = """from cocotb.triggers import RisingEdge, ReadOnly
async def recv(dut):
    while True:
        dut.y_ready.value = 1
        await RisingEdge(dut.clk)
        await ReadOnly()
        _ = int(dut.y_valid.value)
"""
    with pytest.raises(AgentRuntimeError, match="writes during the ReadOnly phase"):
        VerifierAgent._validate_cocotb_phase_safety([code])


def test_read_only_monitor_without_dut_drive_is_allowed() -> None:
    code = """from cocotb.triggers import RisingEdge, ReadOnly
async def monitor(dut):
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        _ = int(dut.y_valid.value)
"""
    VerifierAgent._validate_cocotb_phase_safety([code])


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


def test_required_signals_accept_literal_getattr_reference() -> None:
    code = """import cocotb
@cocotb.test()
async def test_status(dut):
    assert int(getattr(dut, "status_error").value) == 0
    assert int(getattr(dut, "status_done").value) in (0, 1)
"""
    VerifierAgent._validate_required_signal_coverage([code], _context())


@pytest.mark.parametrize('access', [
    'self.dut.status_done.value',
    'getattr(self.dut, "status_done").value',
    'handle.status_done.value',
])
def test_required_signal_presence_accepts_explicit_dut_aliases(access: str) -> None:
    code = f'''class Driver:
    def __init__(self, dut):
        self.dut = dut
        handle = self.dut
        assert int(self.dut.status_error.value) == 0
        assert int({access}) in (0, 1)
'''
    VerifierAgent._validate_required_signal_coverage([code], _context())


def test_required_signal_presence_follows_dut_into_called_helper_parameter() -> None:
    code = '''def check_status(device):
    assert int(device.status_done.value) in (0, 1)
    assert int(device.status_error.value) == 0

async def test_status(dut):
    check_status(dut)
'''
    VerifierAgent._validate_required_signal_coverage([code], _context())


def test_unbound_lookalike_does_not_count_as_dut_signal_access() -> None:
    code = '''def status(unrelated):
    assert int(unrelated.status_done.value) in (0, 1)
    assert int(unrelated.status_error.value) == 0
'''
    with pytest.raises(AgentRuntimeError, match='status_done'):
        VerifierAgent._validate_required_signal_coverage([code], _context())


def test_required_signal_coverage_uses_role_not_signal_name() -> None:
    context = _context()
    context["frozen_architecture"]["interface_contract"]["signals"][2] = {
        "name": "opaque_o7",
        "role": "completion",
        "semantic": "One-cycle lifecycle indication",
    }
    code = """import cocotb
@cocotb.test()
async def test_status(dut):
    assert int(dut.status_error.value) == 0
"""
    with pytest.raises(AgentRuntimeError, match="opaque_o7"):
        VerifierAgent._validate_required_signal_coverage([code], context)


def test_architecture_conflict_cannot_conclude_no_architect_decision_is_needed() -> None:
    from multigent.tests.test_verifier import generic_fir_context, verification_ready_result
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "latency", "affected_modules": ["filter_top"],
            "issue": "Two equations might differ.",
            "evidence": "Direct calculation shows these statements agree.",
            "requested_architect_decision": "No architectural decision is required; regenerate verification instead of escalating.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="invalidates itself"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_representable_illegal_encoding_is_verifier_owned_not_architect_conflict() -> None:
    from multigent.tests.test_verifier import generic_fir_context, verification_ready_result
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "command_encoding_legality", "affected_modules": ["filter_top"],
            "issue": "The field has room for an above-bound value, so no conflict exists.",
            "evidence": "Five bits encode 17..31 above the default maximum 16.",
            "requested_architect_decision": "None; Verifier must generate those values.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="invalidates itself"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_verifier_delivery_failure_with_none_period_is_not_architect_conflict() -> None:
    from multigent.tests.test_verifier import generic_fir_context, verification_ready_result
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "verifier_delivery_failure", "affected_modules": ["filter_top"],
            "issue": "Verifier artifacts could not be represented.",
            "evidence": "The frozen hardware contract itself is consistent.",
            "requested_architect_decision": "None.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="invalidates itself"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_representable_dimension_conflict_with_no_conflict_actually_exists_is_rejected() -> None:
    from multigent.tests.test_verifier import generic_fir_context, verification_ready_result
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "illegal_configuration_encoding", "affected_modules": ["filter_top"],
            "issue": "The required decoded value cannot be represented.",
            "evidence": "The maximum field value decodes to it and is physically representable. Therefore no conflict actually exists.",
            "requested_architect_decision": "Clarify whether to test this value.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="invalidates itself"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_cocotb_tests_require_individual_timeout() -> None:
    code = """import cocotb
from multigent.verifier_tool.coverage.runtime import contract_coverage
@cocotb.test()
@contract_coverage()
async def test_status(dut):
    assert int(dut.status_error.value) == 0
"""
    with pytest.raises(AgentRuntimeError, match="timeout_time and timeout_unit"):
        VerifierAgent._validate_runtime_coverage_instrumentation([code], _context())


def test_direct_writes_to_monitored_clock_are_rejected() -> None:
    context = _context()
    context["frozen_architecture"]["interface_contract"]["clock"] = "clk"
    code = """import cocotb
from multigent.verifier_tool.coverage.runtime import contract_coverage
@cocotb.test(timeout_time=1, timeout_unit="ms")
@contract_coverage()
async def test_status(dut):
    dut.clk.value = 1
"""
    with pytest.raises(AgentRuntimeError, match="direct test writes"):
        VerifierAgent._validate_runtime_coverage_instrumentation([code], context)
