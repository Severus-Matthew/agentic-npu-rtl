from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent
from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result


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
    from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
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
    from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
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
    from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
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
    from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
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


def test_truncated_previous_content_is_not_an_architecture_conflict() -> None:
    from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "missing_previous_content_for_required_correction",
            "affected_modules": ["filter_top"],
            "issue": "Counted correction requires byte-for-byte reproduction of full "
                     "prior file bodies with only validator_error-targeted edits, but "
                     "provided previous_content for tests/test_filter.py is truncated "
                     "and not a complete executable source.",
            "evidence": "The supplied previous_content ends mid-function.",
            "requested_architect_decision": "Provide the full prior file content.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="own prior generated output"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


@pytest.mark.parametrize(
    ("category", "issue", "evidence"),
    [
        (
            "tooling_contract_gap",
            "The verifier_tool automatic_reuse payload does not provide a callable API contract.",
            "The Verifier could not determine the verifier_tool API signature.",
        ),
        (
            "missing_previous_artifact_for_targeted_correction",
            "The previous artifact required for targeted correction is missing.",
            "No previous Verifier test file was supplied to this repair attempt.",
        ),
    ],
)
def test_verifier_owned_reuse_or_repair_gap_is_not_architecture_conflict(
    category: str, issue: str, evidence: str
) -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": category,
            "affected_modules": ["filter_top"],
            "issue": issue,
            "evidence": evidence,
            "requested_architect_decision": "Specify the missing Verifier process artifact.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="invalidates itself"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_required_observation_record_shape_is_verifier_owned() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "missing_observation_binding",
            "affected_modules": ["filter_top"],
            "issue": "required_observations transaction_trace and cycle_trace lack a Python schema.",
            "evidence": "Raw contract signals and clock edges are declared.",
            "requested_architect_decision": "Define the observation binding record fields.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="Verifier owns the local record shape"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_missing_verifier_source_skeleton_is_not_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "missing_executable_contract_artifacts",
            "affected_modules": ["filter_top"],
            "issue": "No verifier source skeleton or helper insertion contract is available.",
            "evidence": "The pipeline-generated code shape is not a frozen RTL artifact.",
            "requested_architect_decision": "Provide a metadata-only extension manifest mode.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="author complete independent Python files"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_coverage_bin_applicability_is_not_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "coverage_contract_conflict",
            "affected_modules": ["filter_top"],
            "issue": "One obligation mixes required_reachable and inapplicable bins.",
            "evidence": "Some bins are diagnostic-only while others are required.",
            "requested_architect_decision": "Choose whether all listed bins need hits.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="only bins with required=true"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_constrained_axi_bins_are_not_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "coverage_contract_inconsistency",
            "affected_modules": ["filter_top"],
            "issue": "single_beat framing cannot reach 4K-boundary or write-channel ordering bins.",
            "evidence": "Required sideband nonzero bins coexist with fixed-value constraints.",
            "requested_architect_decision": "Relax the AXI capabilities.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="single-beat transfer can end"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_coverage_id_and_helper_bindings_are_not_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "missing_contract_bindings",
            "affected_modules": ["filter_top"],
            "issue": "The reduced required-ID manifest and helper binding objects are missing.",
            "evidence": "No concrete channel binding maps were provided.",
            "requested_architect_decision": "Authorize Verifier-owned derivation.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="coverage_obligation_ids_to_declare"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_operation_scope_flags_do_not_disable_protocol_extension_tests() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "contract_integration_conflict",
            "affected_modules": ["filter_top"],
            "issue": "No extension test attachment contract exists for standalone cocotb tests.",
            "evidence": "operation_stimulus_ledger_required=false and pipeline callback API is absent.",
            "requested_architect_decision": "Enable a protocol extension pipeline callback API.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="operation-domain scope flag"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_empty_operation_scope_is_not_a_contract_rule_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "contract_rule_conflict",
            "affected_modules": ["filter_top"],
            "issue": "operations is empty but checked-stimulus operation linkage is required.",
            "evidence": "operation_coverage_required=false and operation_stimulus_ledger_required=false.",
            "requested_architect_decision": "Add an operation or waive checked-stimulus linkage.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="vacuous/no-operation requirement"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_bridge_trace_and_required_bin_controllability_are_verifier_owned() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "missing_observable_contract_detail",
            "affected_modules": ["filter_top"],
            "issue": "Cannot distinguish an already-registered response from flush-only abort-edge behavior.",
            "evidence": "Required bins may not be forceable under DUT-controlled stall.",
            "requested_architect_decision": "Guarantee required bridge bins are forceable.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="observable temporal history"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_axi_write_order_ready_scheduling_is_not_an_architecture_conflict() -> None:
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "coverage-contract contradiction",
            "affected_modules": ["filter_top"],
            "issue": (
                "Required axi4_write_channel_order bins address_first and data_first "
                "appear unreachable when AW and W valids are emitted together."
            ),
            "evidence": (
                "The Verifier cannot directly drive DUT output AWVALID/WVALID timing."
            ),
            "requested_architect_decision": (
                "Clarify whether address_first and data_first are guaranteed reachable."
            ),
        },
    })
    with pytest.raises(AgentRuntimeError, match="Independent AWREADY/WREADY schedules"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_explicit_source_roots_route_files_to_their_owned_collection() -> None:
    result = verification_ready_result()
    reference = result["reference_files"][0]
    test = result["test_files"][0]
    reference["path"] = "reference/model.py"
    test["path"] = "tests/test_filter.py"
    result["reference_files"] = [test]
    result["test_files"] = [reference]

    normalized = VerifierAgent._normalize_owned_source_collections(result)

    assert [item["path"] for item in normalized["reference_files"]] == ["reference/model.py"]
    assert [item["path"] for item in normalized["test_files"]] == ["tests/test_filter.py"]


def test_missing_operation_sampling_bindings_is_not_an_architecture_conflict() -> None:
    from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result
    result = verification_ready_result()
    result.update({
        "status": "ARCHITECTURE_CONFLICT", "reference_files": [], "test_files": [],
        "architecture_conflict": {
            "category": "missing_or_incomplete_frozen_operation_coverage_contract",
            "affected_modules": ["filter_top"],
            "issue": "Runtime rules require literal OPERATION_SAMPLING_BINDINGS for "
                     "every operation concept, but frozen artifacts contain no "
                     "operation_sampling_bindings section.",
            "evidence": "No amendable field exists in previous_contract for "
                        "operation_sampling_bindings.",
            "requested_architect_decision": "Provide the frozen operation_sampling_bindings "
                                             "contract artifact.",
        },
    })
    with pytest.raises(AgentRuntimeError, match="never a frozen architecture artifact"):
        VerifierAgent._validate_prepared_result(result=result, context=generic_fir_context())


def test_cocotb_tests_require_individual_timeout() -> None:
    code = """import cocotb
from multigent.verifier_tool import contract_coverage
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
from multigent.verifier_tool import contract_coverage
@cocotb.test(timeout_time=1, timeout_unit="ms")
@contract_coverage()
async def test_status(dut):
    dut.clk.value = 1
"""
    with pytest.raises(AgentRuntimeError, match="direct test writes"):
        VerifierAgent._validate_runtime_coverage_instrumentation([code], context)
