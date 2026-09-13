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
    findings = VerifierAgent._validate_required_signal_coverage([code], _context())
    assert findings and "status_done" in findings[0]


def test_required_completion_and_error_signals_can_be_covered() -> None:
    code = """import cocotb
@cocotb.test()
async def test_status(dut):
    assert int(dut.status_error.value) == 0
    assert int(dut.status_done.value) in (0, 1)
"""
    VerifierAgent._validate_required_signal_coverage([code], _context())

@pytest.mark.parametrize('code', [
    'assert driver.dut.status_done.value == 1\nassert driver.dut.status_error.value == 0',
    'assert getattr(device, "status_done").value == 1\nassert getattr(device, "status_error").value == 0',
    'assert event["post"]["status_done"] == 1\nassert snapshot["status_error"] == 0',
])
def test_signal_presence_accepts_aliases_getattr_and_snapshots(code):
    VerifierAgent._validate_required_signal_coverage([code], _context())


def test_signal_names_only_in_comments_or_strings_do_not_satisfy_check():
    code = '# status_done status_error\nnote = "status_done status_error"'
    findings = VerifierAgent._validate_required_signal_coverage([code], _context())
    assert findings and 'status_done' in findings[0]


def test_helper_files_are_included_in_full_result_validation():
    from multigent.tests.test_verifier import verification_ready_result, generic_fir_context
    result = verification_ready_result()
    context = generic_fir_context()
    context['frozen_architecture']['interface_contract']['signals'] = _context()['frozen_architecture']['interface_contract']['signals']
    helper = dict(result['reference_files'][0])
    helper.update(path='reference/status_helper.py',content='def check(snapshot):\n    assert snapshot["status_done"] == 1\n    assert snapshot["status_error"] == 0\n')
    result['reference_files'].append(helper)
    VerifierAgent._validate_result(result=result,context=context)


def test_dynamic_helper_signal_review_is_advisory_and_persisted(tmp_path, monkeypatch):
    import json
    from multigent.tests.test_verifier import verification_ready_result, generic_fir_context
    result = verification_ready_result()
    context = generic_fir_context()
    context['frozen_architecture']['interface_contract']['signals'] = _context()['frozen_architecture']['interface_contract']['signals']
    result['test_files'][0]['content'] += "\ndef integer(d, name):\n    return int(getattr(d, name).value)\ndef snapshot(d):\n    return (integer(d, 'status_done'), integer(d, 'status_error'))\n"
    agent = VerifierAgent()
    monkeypatch.setattr(agent, 'run_structured', lambda **kwargs: result)
    observed = agent.run(context, workspace_dir=tmp_path)
    assert observed['status'] == 'VERIFICATION_READY'
    review = json.loads((tmp_path/'verification'/'static_review.json').read_text())
    assert review['status'] == 'ADVISORY_ONLY'
    assert review['findings'] and 'status_done' in review['findings'][0]
    assert list((tmp_path/'tests').glob('*.py'))
