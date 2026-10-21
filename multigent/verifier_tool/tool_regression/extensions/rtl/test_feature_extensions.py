from __future__ import annotations

import ast
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.verifier import (
    VERIFIER_OUTPUT_SCHEMA,
    VERIFIER_SOURCE_REPAIR_SCHEMA,
    VerifierAgent,
)
from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import axi_lite_contracts
from multigent.verifier_tool.tool_regression.integration.test_lifecycle_policy_pool import _contracts
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_feature_extension_manifest,
    build_lifecycle_assertion_plan,
    build_lifecycle_feature_plan,
    build_lifecycle_stimulus_plan,
    check_lifecycle_assertions,
    compile_assertion_feature_plan,
    extension_bundle_schema,
    extension_request_schema,
    interface_vocabulary_extensions,
    render_requested_extension_worklist,
    validate_architect_extension_requests,
    validate_verifier_extension_bundles,
    validate_interface_semantics,
    validate_interface_signal_roles,
)
from multigent.verifier_tool.extensions.authoring import (
    _call_result_is_consumed,
    _coverage_consumer_asserts_named_bin,
    _coverage_handles_declared_bins,
    _extension_symbol_calls,
    _python_function_nodes,
    _unexercised_scenarios,
)


def _call_analysis(source: str, symbol: str):
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "test_case"
    )
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    call = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == symbol
    )
    return call, function, parents


def test_extension_checker_tuple_unpack_is_enforced_by_asserted_decision() -> None:
    call, function, parents = _call_analysis(
        """
def test_case(trace):
    ok, errors, flags = extension_assertion(trace)
    assert ok, errors
""",
        "extension_assertion",
    )
    assert _call_result_is_consumed(
        call, function, parents, require_assertion=True
    )


def test_extension_coverage_literal_scenario_loop_requires_named_bins() -> None:
    call, function, parents = _call_analysis(
        """
def test_case(trace):
    hits = extension_coverage(trace)
    for scenario, required_bin in [
        ("read", "read_lane_mapping"),
        ("write", "write_id_mapping"),
    ]:
        assert required_bin in hits, scenario
""",
        "extension_coverage",
    )
    assert _coverage_consumer_asserts_named_bin(
        [(call, function, parents)],
        ["read_lane_mapping", "write_id_mapping"],
    )


def test_extension_coverage_follows_reachable_reference_classifier() -> None:
    sources = {
        "tests/test_extension.py": """
from reference.model import classify_trace

def extension_coverage(cycle_trace):
    return classify_trace(cycle_trace)

def test_extension(observed_cycle_trace):
    hits = extension_coverage(observed_cycle_trace)
    assert "stall_observed" in hits
""",
        "reference/model.py": """
def classify_trace(cycle_trace):
    hits = set()
    if any(item.get("stalled", False) for item in cycle_trace):
        hits.add("stall_observed")
    return hits
""",
    }
    functions = _python_function_nodes(sources)
    node = functions["tests/test_extension.py"]["extension_coverage"]
    calls = _extension_symbol_calls(sources, "extension_coverage")
    assert _coverage_handles_declared_bins(
        node,
        calls,
        ["stall_observed"],
        functions,
    ) == []


def test_temporal_coverage_accepts_any_observed_trace_trigger() -> None:
    source = """
def extension_coverage(cycle_trace):
    return {"stall_observed"} if any(c.get("stalled", 0) for c in cycle_trace) else set()

def test_case(cycle_trace):
    hits = extension_coverage(cycle_trace)
    assert any(c.get("stalled", 0) for c in cycle_trace)
    assert "stall_observed" in hits
"""
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    call, function, parents = _call_analysis(source, "extension_coverage")
    from multigent.verifier_tool.extensions.authoring import (
        _coverage_consumer_requires_temporal_trigger,
    )

    assert _coverage_consumer_requires_temporal_trigger(
        functions["extension_coverage"],
        [(call, function, parents)],
    )


def _request(operation_name: str = "job") -> dict:
    return {
        "id": "lifecycle.error_three_cycle_pulse",
        "domain": "lifecycle",
        "feature_name": "error_three_cycle_pulse",
        "target": {"scope": "operation", "name": operation_name},
        "semantics": {
            "summary": "Hold error high for exactly three sampled cycles.",
            "trigger": "An illegal command is accepted while no job is active.",
            "required_behavior": [
                "Error is high on each of the next three sampled cycles.",
                "No legal job starts from the illegal command.",
            ],
            "end_condition": "Error is low on the fourth sampled cycle.",
            "forbidden_behavior": ["Error remains high for a fourth cycle."],
        },
        "reason": "The lifecycle pool supports one-cycle and sticky errors only.",
        "parameters": {"cycles": 3},
        "replaces_contract_paths": [
            f"/operations/{operation_name}/lifecycle_policy/error_style"
        ],
        "required_observations": [
            {
                "name": "illegal_command_accept",
                "kind": "event",
                "description": "Accepted illegal command event.",
            },
            {
                "name": "error_signal",
                "kind": "signal",
                "description": "The bound DUT error indication.",
            },
        ],
        "related_builtin_features": ["lifecycle.error_behavior"],
    }


def _lifecycle_policy_request(field: str, operation_name: str = "gemm_core") -> dict:
    identity = f"lifecycle.{field}_extension"
    return {
        "id": identity,
        "domain": "lifecycle",
        "feature_name": f"{field}_extension",
        "target": {"scope": "operation", "name": operation_name},
        "semantics": {
            "summary": f"Contract-local behavior for lifecycle policy field {field}.",
            "trigger": f"The event governed by {field} occurs.",
            "required_behavior": [
                f"The Verifier checks the frozen contract behavior for {field}."
            ],
            "end_condition": f"The {field} behavior reaches its declared terminal state.",
            "forbidden_behavior": [
                f"No built-in {field} behavior is assumed by the deterministic runtime."
            ],
        },
        "reason": f"The closed lifecycle pool does not represent this {field} behavior.",
        "replaces_contract_paths": [
            f"/operations/{operation_name}/lifecycle_policy/{field}"
        ],
        "required_observations": [
            {
                "name": "lifecycle_event",
                "kind": "event",
                "description": f"Observed event governed by {field}.",
            }
        ],
        "related_builtin_features": [f"lifecycle.{field}"],
    }


def _protocol_request() -> dict:
    return {
        "id": "protocol.bounded_ready_recovery",
        "domain": "protocol",
        "feature_name": "bounded_ready_recovery",
        "target": {"scope": "channel", "name": "cmd"},
        "semantics": {
            "summary": "READY must recover within seven cycles after VALID is presented.",
            "trigger": "VALID is asserted while READY is low.",
            "required_behavior": ["READY is observed within seven sampled cycles."],
            "end_condition": "The transfer is accepted or the seventh cycle expires.",
            "forbidden_behavior": ["READY remains low for eight sampled cycles."],
        },
        "reason": "The generic ready/valid pool has stall bins but no bounded-liveness rule.",
        "parameters": {"maximum_cycles": 7},
        "required_observations": [
            {"name": "valid", "kind": "signal", "description": "Bound VALID signal."},
            {"name": "ready", "kind": "signal", "description": "Bound READY signal."},
        ],
        "related_builtin_features": ["stall_stability"],
    }


def _protocol_bundle() -> dict:
    implementation = {
        "kind": "verifier_python",
        "name": "bounded_ready_recovery",
        "file": "tests/test_protocol_extension.py",
    }
    return {
        "schema_version": 1,
        "request_id": "protocol.bounded_ready_recovery",
        "id": "protocol.bounded_ready_recovery",
        "domain": "protocol",
        "feature_name": "bounded_ready_recovery",
        "target": {"scope": "channel", "name": "cmd"},
        "description": "Contract-local bounded READY recovery verification.",
        "bindings": {"valid": "cmd_valid", "ready": "cmd_ready"},
        "reuse": {
            "based_on_features": ["stall_stability"],
            "helpers": ["channel_schedule"],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": "check_ready_recovery"},
            "parameters": {"maximum_cycles": 7},
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "sample_ready_recovery"},
            "parameters": {"maximum_cycles": 7},
            "bins": [
                {
                    "name": "seven_cycle_recovery",
                    "intent": "Observe READY recovery on the seventh cycle.",
                    "predicate": {"recovery_cycle": 7},
                }
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "drive_ready_recovery"},
            "parameters": {"stall_cycles": 7},
            "scenarios": [
                {
                    "name": "maximum_legal_stall",
                    "intent": "Hold the receiver unavailable for seven cycles.",
                    "parameters": {"stall_cycles": 7},
                }
            ],
        },
    }


def _protocol_source() -> dict:
    return {
        "path": "test_protocol_extension.py",
        "purpose": "cocotb test for a contract-local protocol behavior",
        "categories": ["protocol"],
        "content": """
import cocotb
from cocotb.triggers import RisingEdge

def check_ready_recovery(snapshot, state):
    assert snapshot["recovery_cycle"] <= state["maximum_cycles"]

def sample_ready_recovery(snapshot, state):
    return snapshot["recovery_cycle"]

async def drive_ready_recovery(dut):
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    snapshot = {"recovery_cycle": 7}
    state = {"maximum_cycles": 7}
    check_ready_recovery(snapshot, state)
    sample_ready_recovery(snapshot, state)
    await drive_ready_recovery(dut)
""",
    }


def _bundle() -> dict:
    implementation = {
        "kind": "verifier_python",
        "name": "error_three_cycle_pulse",
        "file": "tests/test_error_extension.py",
    }
    return {
        "schema_version": 1,
        "request_id": "lifecycle.error_three_cycle_pulse",
        "id": "lifecycle.error_three_cycle_pulse",
        "domain": "lifecycle",
        "feature_name": "error_three_cycle_pulse",
        "target": {"scope": "operation", "name": "job"},
        "description": "Contract-local three-cycle error verification.",
        "bindings": {
            "illegal_command_accept": {"valid": "cv", "ready": "cr", "payload": "opcode"},
            "error_signal": "err",
        },
        "reuse": {
            "based_on_features": ["lifecycle.error_behavior"],
            "helpers": ["drive_accepted_command"],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": "check_error_three_cycle"},
            "parameters": {"cycles": 3},
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "sample_error_three_cycle"},
            "parameters": {"cycles": 3},
            "bins": [
                {
                    "name": "exact_three_cycles",
                    "intent": "Observe exactly three asserted cycles.",
                    "predicate": {"observed_cycles": 3},
                }
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "drive_error_three_cycle"},
            "parameters": {"illegal_opcode": 0},
            "scenarios": [
                {
                    "name": "illegal_then_recover",
                    "intent": "Trigger the error and then run a legal job.",
                    "parameters": {"illegal_opcode": 0, "legal_opcode": 1},
                }
            ],
        },
    }


def _source() -> dict:
    return {
        "path": "test_error_extension.py",
        "purpose": "cocotb test for contract-local lifecycle extension",
        "categories": ["lifecycle"],
        "content": """
import cocotb
from cocotb.triggers import RisingEdge

def check_error_three_cycle(snapshot, state):
    assert snapshot["error_high_cycles"] == state["required_cycles"]

def sample_error_three_cycle(snapshot, state):
    return snapshot["error_high_cycles"]

async def drive_error_three_cycle(dut):
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_contract_local_error_extension(dut):
    snapshot = {"error_high_cycles": 3}
    state = {"required_cycles": 3}
    check_error_three_cycle(snapshot, state)
    sample_error_three_cycle(snapshot, state)
    await drive_error_three_cycle(dut)
""",
    }


def test_extension_request_and_bundle_have_a_stable_machine_readable_boundary() -> None:
    request = _request()
    bundle = _bundle()
    Draft202012Validator(extension_request_schema()).validate(request)
    Draft202012Validator(extension_bundle_schema()).validate(bundle)
    architecture = {"verification_extensions": [request]}
    assert validate_verifier_extension_bundles(
        architecture, [bundle], source_files=[_source()]
    ) == []
    manifest = build_feature_extension_manifest(
        architecture, [bundle], source_files=[_source()]
    )
    assert manifest["status"] == "contract_local_only"
    assert manifest["promotion"] == "not_implemented"
    assert manifest["entries"][0]["request"] == request
    assert manifest["entries"][0]["implementation"] == bundle


def test_extension_bundle_rejects_noop_assertion_constant_coverage_and_idle_stimulus() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    source["content"] = """
import cocotb

def check_ready_recovery(snapshot, state):
    return None

def sample_ready_recovery(snapshot, state):
    return 7

async def drive_ready_recovery(dut):
    return None

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    check_ready_recovery({}, {})
    sample_ready_recovery({}, {})
    await drive_ready_recovery(dut)
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
    )
    assert any("no observable decision" in error for error in errors)
    assert any("constant coverage" in error for error in errors)
    assert any("await executable stimulus work" in error for error in errors)


def test_generated_extension_rejects_vacuous_or_fabricated_runtime_evidence() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

def check_ready_recovery(*args, **kwargs):
    observed = bool(kwargs.get("completion_seen", False))
    return observed

def sample_ready_recovery(*args, **kwargs):
    return {"observed": bool(kwargs.get("completion_seen", False))}

async def drive_ready_recovery(dut):
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    await drive_ready_recovery(dut)
    sample_ready_recovery(
        dut=dut,
        completion_seen=False,
        busy_samples=(int(dut.cmd_ready.value),),
    )
    check_ready_recovery(
        dut=dut,
        completion_seen=False,
        busy_samples=(int(dut.cmd_ready.value),),
    )
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    )
    assert any("fabricated literal observation" in error for error in errors)
    assert any("decision that no generated test asserts" in error for error in errors)
    assert any("sample that no generated test consumes" in error for error in errors)
    assert any("only waits" in error for error in errors)


def test_generated_extension_accepts_scheduled_driver_delegation() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

def check_ready_recovery(snapshot, state):
    assert snapshot["recovery_cycle"] <= state["maximum_cycles"]
    return True

def sample_ready_recovery(snapshot, state):
    return {"seven_cycle_recovery"} if snapshot["recovery_cycle"] == 7 else set()

async def reusable_driver(dut):
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)

async def drive_ready_recovery(dut):
    driver_task = cocotb.start_soon(reusable_driver(dut))
    await driver_task

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    snapshot = {"recovery_cycle": int(dut.recovery_cycle.value)}
    state = {"maximum_cycles": 7}
    assert check_ready_recovery(snapshot, state) is True
    hits = sample_ready_recovery(snapshot, state)
    assert "seven_cycle_recovery" in hits
    await drive_ready_recovery(dut)
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    )
    assert not any("only waits" in error for error in errors)


def test_generated_extension_rejects_single_snapshot_markers_and_inert_protocol_driver() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    source = _protocol_source()
    source["content"] = """
import cocotb

def check_ready_recovery(dut):
    valid = int(dut.cmd_valid.value)
    ready = int(dut.cmd_ready.value)
    return {"checked": True, "triggered": bool(valid and not ready)}

def sample_ready_recovery(dut):
    valid = int(dut.cmd_valid.value)
    ready = int(dut.cmd_ready.value)
    return {"sampled": True, "state": (valid << 1) | ready}

def drive_ready_recovery(dut):
    return {"invoked": True}

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    stimulus = drive_ready_recovery(dut)
    coverage = sample_ready_recovery(dut)
    decision = check_ready_recovery(dut)
    assert stimulus["invoked"]
    assert coverage["sampled"]
    assert decision["checked"]
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    )
    assert any("must be async" in error for error in errors)
    assert any("ignores declared parameter" in error for error in errors)
    assert any("instantaneous snapshot" in error for error in errors)
    assert any("does not classify declared bin" in error for error in errors)
    assert any("multi-cycle schedule" in error for error in errors)
    assert any("no reachable test assertion requiring a declared bin" in error for error in errors)


def test_generated_temporal_extension_accepts_driven_trace_and_named_bin() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

def check_ready_recovery(recovery_cycle, maximum_cycles):
    assert recovery_cycle <= maximum_cycles
    return True

def sample_ready_recovery(recovery_cycle, maximum_cycles):
    return "seven_cycle_recovery" if recovery_cycle <= maximum_cycles else "over_bound"

async def drive_ready_recovery(dut, stall_cycles):
    dut.cmd_ready.value = 0
    observed_cycles = 0
    for _ in range(stall_cycles):
        await RisingEdge(dut.clk)
        observed_cycles += 1
    dut.cmd_ready.value = 1
    await RisingEdge(dut.clk)
    return observed_cycles

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    stall_cycles = 7
    recovery_cycle = await drive_ready_recovery(dut, stall_cycles=stall_cycles)
    decision = check_ready_recovery(
        recovery_cycle=recovery_cycle, maximum_cycles=7
    )
    covered_bin = sample_ready_recovery(
        recovery_cycle=recovery_cycle, maximum_cycles=7
    )
    _contract_record_extension_coverage(
        "protocol.bounded_ready_recovery", [covered_bin]
    )
    assert recovery_cycle > 0
    assert decision
    assert covered_bin == "seven_cycle_recovery"
"""
    assert validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    ) == []


def test_generated_temporal_extension_rejects_expected_trace_as_observation() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

def _build_trace_from_job(job):
    return [
        {"cycle": cycle, "valid": 1, "ready": int(cycle == job["stall_cycles"])}
        for cycle in range(job["stall_cycles"] + 1)
    ]

def check_ready_recovery(trace, maximum_cycles):
    recovery_cycle = next(item["cycle"] for item in trace if item["ready"])
    assert recovery_cycle <= maximum_cycles
    return True

def sample_ready_recovery(trace, maximum_cycles):
    recovery_cycle = next(item["cycle"] for item in trace if item["ready"])
    return "seven_cycle_recovery" if recovery_cycle <= maximum_cycles else "over_bound"

async def drive_ready_recovery(dut, stall_cycles):
    dut.cmd_ready.value = 0
    for _ in range(stall_cycles):
        await RisingEdge(dut.clk)
    dut.cmd_ready.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    job = {"stall_cycles": 7}
    await drive_ready_recovery(dut, stall_cycles=job["stall_cycles"])
    trace = _build_trace_from_job(job)
    decision = check_ready_recovery(trace=trace, maximum_cycles=7)
    covered_bin = sample_ready_recovery(trace=trace, maximum_cycles=7)
    assert decision
    assert covered_bin == "seven_cycle_recovery"
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    )
    assert any("not called with simulator-derived evidence" in error for error in errors)
    assert not any("instantaneous snapshot" in error for error in errors)


def test_generated_temporal_extension_rejects_late_monitor_unlisted_schedule_and_bad_decorator_order() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    source = _protocol_source()
    source["content"] = """
from cocotb.triggers import RisingEdge

async def drive_ready_recovery(dut, stall_cycles):
    dut.cmd_ready.value = 0
    for _ in range(stall_cycles):
        await RisingEdge(dut.clk)
    dut.cmd_ready.value = 1

async def sample_ready_recovery(dut, maximum_cycles):
    recovery_cycle = 0
    for _ in range(maximum_cycles):
        await RisingEdge(dut.clk)
        recovery_cycle += 1
        if int(dut.cmd_ready.value):
            return {"bin": "seven_cycle_recovery", "recovery_cycle": recovery_cycle}
    return {"bin": "over_bound", "recovery_cycle": recovery_cycle}

def check_ready_recovery(recovery_cycle, maximum_cycles):
    assert maximum_cycles == 7
    return recovery_cycle <= maximum_cycles

@_contract_cocotb.test()
async def test_bounded_ready_recovery(dut):
    await drive_ready_recovery(dut, stall_cycles=2)
    covered_bin = await sample_ready_recovery(dut, maximum_cycles=7)
    assert covered_bin == "seven_cycle_recovery"
    assert check_ready_recovery(covered_bin, maximum_cycles=7)

import cocotb as _contract_cocotb
"""
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    )
    assert any("before that name is imported or defined" in error for error in errors)
    assert any("never executes declared scenario" in error for error in errors)
    assert any("only after directed stimulus completes" in error for error in errors)


def test_generated_temporal_extension_accepts_monitor_started_before_stimulus() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

async def drive_ready_recovery(dut, stall_cycles):
    dut.cmd_ready.value = 0
    for _ in range(stall_cycles):
        await RisingEdge(dut.clk)
    dut.cmd_ready.value = 1
    await RisingEdge(dut.clk)

async def sample_ready_recovery(dut, maximum_cycles):
    recovery_cycle = 0
    while recovery_cycle <= maximum_cycles:
        await RisingEdge(dut.clk)
        recovery_cycle += 1
        if int(dut.cmd_ready.value):
            assert recovery_cycle > 0
            return {"bin": "seven_cycle_recovery", "recovery_cycle": recovery_cycle}
    return {"bin": "over_bound", "recovery_cycle": recovery_cycle}

def check_ready_recovery(recovery_cycle, maximum_cycles):
    assert maximum_cycles == 7
    return recovery_cycle <= maximum_cycles

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    monitor = cocotb.start_soon(
        sample_ready_recovery(dut, maximum_cycles=7)
    )
    await drive_ready_recovery(dut, stall_cycles=7)
    sample = await monitor
    _contract_record_extension_coverage(
        "protocol.bounded_ready_recovery", [sample["bin"]]
    )
    assert sample["bin"] == "seven_cycle_recovery"
    assert check_ready_recovery(sample["recovery_cycle"], maximum_cycles=7)
"""
    assert validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    ) == []


def test_generated_temporal_extension_accepts_literal_scenario_table_loop() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    bundle["stimulus"]["scenarios"] = [
        {
            "name": "short_stall",
            "intent": "Exercise a short recovery.",
            "parameters": {"stall_cycles": 3},
        },
        {
            "name": "maximum_legal_stall",
            "intent": "Exercise the declared bound.",
            "parameters": {"stall_cycles": 7},
        },
    ]
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

async def drive_ready_recovery(dut, stall_cycles):
    dut.cmd_ready.value = 0
    observed_cycles = 0
    for _ in range(stall_cycles):
        await RisingEdge(dut.clk)
        observed_cycles += 1
    dut.cmd_ready.value = 1
    return observed_cycles

def sample_ready_recovery(recovery_cycle, maximum_cycles):
    return "seven_cycle_recovery" if recovery_cycle <= maximum_cycles else "over_bound"

def check_ready_recovery(recovery_cycle, maximum_cycles):
    assert recovery_cycle <= maximum_cycles
    return True

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    scenarios = [("short_stall", 3), ("maximum_legal_stall", 7)]
    for name, stall_cycles in scenarios:
        recovery_cycle = await drive_ready_recovery(
            dut, stall_cycles=stall_cycles
        )
        covered_bin = sample_ready_recovery(
            recovery_cycle=recovery_cycle, maximum_cycles=7
        )
        _contract_record_extension_coverage(
            "protocol.bounded_ready_recovery", [covered_bin]
        )
        assert recovery_cycle > 0
        assert name in {"short_stall", "maximum_legal_stall"}
        assert covered_bin == "seven_cycle_recovery"
        assert check_ready_recovery(recovery_cycle, maximum_cycles=7)
"""
    assert validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    ) == []


def test_generated_extension_resolves_literal_scenario_values_inside_try() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    bundle["stimulus"]["parameters"] = {"timeout_cycles": 2048}
    bundle["stimulus"]["scenarios"] = [
        {
            "name": "three_beats",
            "intent": "Drive the exact declared beats.",
            "parameters": {
                "beats": [{"data": 1}, {"data": 2}, {"data": 3}],
                "timeout_cycles": 2048,
            },
        }
    ]
    source = _protocol_source()
    source["path"] = "tests/test_protocol_extension.py"
    source["content"] = """
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

async def drive_ready_recovery(dut, beats, timeout_cycles):
    for beat in beats:
        dut.cmd_data.value = beat["data"]
        await RisingEdge(dut.clk)
    assert timeout_cycles > 0

def sample_ready_recovery(recovery_cycle, maximum_cycles):
    return "seven_cycle_recovery" if recovery_cycle <= maximum_cycles else "over_bound"

def check_ready_recovery(recovery_cycle, maximum_cycles):
    return recovery_cycle <= maximum_cycles

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    clock = cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    try:
        beats = [{"data": 1}, {"data": 2}, {"data": 3}]
        await drive_ready_recovery(dut, beats=beats, timeout_cycles=2048)
        observed = 1
        covered_bin = sample_ready_recovery(observed, maximum_cycles=7)
        _contract_record_extension_coverage(
            "protocol.bounded_ready_recovery", [covered_bin]
        )
        assert covered_bin == "seven_cycle_recovery"
        assert check_ready_recovery(observed, maximum_cycles=7)
    finally:
        clock.kill()
"""
    sources = {source["path"]: source["content"]}
    implementation = _python_function_nodes(sources)[source["path"]][
        "drive_ready_recovery"
    ]
    calls = _extension_symbol_calls(sources, "drive_ready_recovery")
    assert _unexercised_scenarios(
        implementation,
        calls,
        bundle["stimulus"]["scenarios"],
    ) == []


def test_generated_temporal_extension_accepts_internal_awaited_scenario_table() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    bundle["stimulus"]["implementation"]["kind"] = "protocol_driver"
    bundle["stimulus"]["scenarios"] = [
        {
            "name": "short_stall",
            "intent": "Exercise a short recovery.",
            "parameters": {"stall_cycles": 3},
        },
        {
            "name": "maximum_legal_stall",
            "intent": "Exercise the declared bound.",
            "parameters": {"stall_cycles": 7},
        },
    ]
    source = _protocol_source()
    source["content"] = """
import cocotb
from cocotb.triggers import RisingEdge

async def drive_ready_recovery(dut, maximum_cycles):
    observed_cycles = []

    async def run_one(stall_cycles):
        dut.cmd_ready.value = 0
        for _ in range(stall_cycles):
            await RisingEdge(dut.clk)
        dut.cmd_ready.value = 1
        observed_cycles.append(stall_cycles)

    scenarios = [("short_stall", 3), ("maximum_legal_stall", 7)]
    for scenario_name, stall_cycles in scenarios:
        assert scenario_name
        await run_one(stall_cycles)
    assert maximum_cycles == 7
    return observed_cycles

def sample_ready_recovery(recovery_cycles, maximum_cycles):
    return {"bin": "seven_cycle_recovery", "recovery_cycles": recovery_cycles, "maximum_cycles": maximum_cycles}

def check_ready_recovery(recovery_cycles, maximum_cycles):
    assert recovery_cycles and max(recovery_cycles) <= maximum_cycles
    return True

@cocotb.test()
async def test_bounded_ready_recovery(dut):
    recovery_cycles = await drive_ready_recovery(dut, maximum_cycles=7)
    sample = sample_ready_recovery(recovery_cycles, maximum_cycles=7)
    _contract_record_extension_coverage(
        "protocol.bounded_ready_recovery", [sample["bin"]]
    )
    assert len(sample["recovery_cycles"]) > 0
    assert sample["bin"] == "seven_cycle_recovery"
    assert check_ready_recovery(recovery_cycles, maximum_cycles=7)
"""
    assert validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    ) == []


def test_generated_temporal_extension_rejects_unexecuted_internal_scenario_table() -> None:
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    source["content"] = source["content"].replace(
        "async def drive_ready_recovery(dut):\n    await RisingEdge(dut.clk)",
        '''async def drive_ready_recovery(dut):
    scenarios = [("maximum_legal_stall", 7)]
    assert scenarios
    await RisingEdge(dut.clk)''',
    )
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [request]},
        [bundle],
        source_files=[source],
        require_runtime_evidence=True,
    )
    assert any("never executes declared scenario" in error for error in errors)


def test_verifier_api_schemas_expose_contract_local_extension_bundles() -> None:
    agent = VerifierAgent()
    for schema_path in (VERIFIER_OUTPUT_SCHEMA, VERIFIER_SOURCE_REPAIR_SCHEMA):
        schema = agent.load_output_schema(schema_path)
        assert "feature_extensions" in schema["properties"]
        Draft202012Validator.check_schema(schema)


def test_residual_extension_cannot_be_an_inert_existing_primitive_claim() -> None:
    bundle = _protocol_bundle()
    for branch_name in ("assertion", "coverage", "stimulus"):
        implementation = bundle[branch_name]["implementation"]
        implementation["kind"] = "existing_primitive"
        implementation.pop("file", None)
        implementation.pop("symbol", None)
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [_protocol_request()]},
        [bundle],
        source_files=[_protocol_source()],
    )
    assert sum("is not one of" in error for error in errors) == 3, errors


def test_bundle_must_bind_every_architect_required_observation() -> None:
    bundle = _bundle()
    bundle["bindings"].pop("error_signal")
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [_request()]},
        [bundle],
        source_files=[_source()],
    )
    assert any("error_signal" in error for error in errors)


def test_bundle_python_implementation_must_be_reachable_from_generated_test() -> None:
    source = _source()
    source["content"] = source["content"].replace(
        "    check_error_three_cycle(snapshot, state)\n", ""
    )
    errors = validate_verifier_extension_bundles(
        {"verification_extensions": [_request()]},
        [_bundle()],
        source_files=[source],
    )
    assert any(
        "assertion symbol 'check_error_three_cycle' is not reachable" in error
        for error in errors
    )


def test_one_lifecycle_extension_preserves_unaffected_tool_owned_features() -> None:
    architecture, interface = axi_lite_contracts()
    request = _request("gemm_core")
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["error_style"] = {
        "extension_request": request["id"]
    }
    assert validate_architect_extension_requests(architecture, interface) == []

    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    plan = build_lifecycle_feature_plan(interface, metadata)
    checkers = {
        item["implementation"]
        for item in compile_assertion_feature_plan(plan)["entries"]
    }
    assert "illegal_command_errors_without_start" not in checkers
    assert "response_error_follows_nonokay" not in checkers
    assert "status_pulses_are_one_cycle" in checkers
    assert "completion_matches_final_output" in checkers
    assert "busy_tracks_active_job" in checkers

    lifecycle_bins = {
        item["id"]: {entry["name"] for entry in item["bins"]}
        for item in plan["coverage_obligations"]
    }
    assert lifecycle_bins["operation.gemm_core.job_lifecycle"] == {
        "accepted", "active", "retired", "aborted"
    }
    scenario_kinds = {
        item["kind"] for item in build_lifecycle_stimulus_plan(interface, metadata)["scenarios"]
    }
    assert "legal_command" in scenario_kinds
    assert "illegal_command" not in scenario_kinds
    assert "illegal_then_legal_recovery" not in scenario_kinds

    support = automatic_campaign_support(metadata, architecture)
    operation = support["operations"]["gemm_core"]
    assert operation["supported"] is False
    assert operation["known_scope_campaign_supported"] is True
    assert operation["lifecycle_extension_fields"] == ["error_style"]
    assert support["any_operation_supported"] is True


@pytest.mark.parametrize(
    ("field", "removed_checkers"),
    [
        (
            "job_acceptance",
            {
                "accepted_command_starts_job",
                "single_inflight_job_enforced",
                "illegal_command_errors_without_start",
                "no_output_without_active_job",
                "busy_tracks_active_job",
            },
        ),
        ("job_overlap", {"single_inflight_job_enforced"}),
        ("busy_behavior", {"busy_tracks_active_job"}),
        (
            "completion_style",
            {"completion_matches_final_output", "status_pulses_are_one_cycle"},
        ),
        ("completion_timing", {"completion_matches_final_output"}),
        ("illegal_command_behavior", {"illegal_command_errors_without_start"}),
        ("error_style", {"illegal_command_errors_without_start", "response_error_follows_nonokay"}),
        ("error_timing", {"illegal_command_errors_without_start", "response_error_follows_nonokay"}),
        ("reset_behavior", {"reset_aborts_pending_job"}),
    ],
)
def test_every_lifecycle_policy_extension_field_removes_only_dependent_features(
    field: str, removed_checkers: set[str]
) -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_policy_request(field)
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"][field] = {
        "extension_request": request["id"]
    }

    assert validate_architect_extension_requests(architecture, interface) == []
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    plan = build_lifecycle_feature_plan(interface, metadata)
    selected = {
        str(item["kind"])
        for item in plan["features"]
        if item.get("scope") == "operation"
    }
    all_checkers = {
        "accepted_command_starts_job",
        "single_inflight_job_enforced",
        "illegal_command_errors_without_start",
        "response_error_follows_nonokay",
        "no_output_without_active_job",
        "busy_tracks_active_job",
        "completion_matches_final_output",
        "reset_aborts_pending_job",
        "status_pulses_are_one_cycle",
    }
    assert selected == all_checkers - removed_checkers
    # The fixture's completion indication is a pulse while its error is sticky.
    # Extending error_style therefore leaves the completion pulse checker active;
    # extending completion_style leaves no observable pulse for that checker.
    if field == "error_style":
        assert "status_pulses_are_one_cycle" in selected


def test_both_extended_pulse_styles_remove_shared_status_pulse_checker() -> None:
    architecture, interface = axi_lite_contracts()
    requests = [
        _lifecycle_policy_request("completion_style"),
        _lifecycle_policy_request("error_style"),
    ]
    architecture["verification_extensions"] = requests
    for field, request in zip(("completion_style", "error_style"), requests):
        architecture["operations"][0]["lifecycle_policy"][field] = {
            "extension_request": request["id"]
        }
    assert validate_architect_extension_requests(architecture, interface) == []
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    selected = {
        str(item["kind"])
        for item in plan["features"]
        if item.get("scope") == "operation"
    }
    assert "completion_matches_final_output" not in selected
    assert "illegal_command_errors_without_start" not in selected
    assert "response_error_follows_nonokay" not in selected
    assert "status_pulses_are_one_cycle" not in selected


@pytest.mark.parametrize(
    ("field", "expected_bins"),
    [
        ("completion_style", {"accepted", "active", "aborted"}),
        ("busy_behavior", {"accepted", "retired", "aborted"}),
        ("reset_behavior", {"accepted", "active", "retired"}),
    ],
)
def test_lifecycle_extension_filters_dependent_coverage_and_stimulus_only(
    field: str, expected_bins: set[str]
) -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_policy_request(field)
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"][field] = {
        "extension_request": request["id"]
    }
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    lifecycle = next(
        item
        for item in plan["coverage_obligations"]
        if item["id"] == "operation.gemm_core.job_lifecycle"
    )
    assert {str(item["name"]) for item in lifecycle["bins"]} == expected_bins

    scenarios = build_lifecycle_stimulus_plan(interface, metadata)["scenarios"]
    scenario_kinds = {str(item["kind"]) for item in scenarios}
    assert "legal_command" in scenario_kinds
    if field == "reset_behavior":
        assert "reset_abort" not in scenario_kinds
        assert "abort_then_clean_job" not in scenario_kinds
        obligation_ids = {str(item["id"]) for item in plan["coverage_obligations"]}
        assert "operation.gemm_core.reset_abort_phase" not in obligation_ids
        assert "operation.gemm_core.post_reset_purity" not in obligation_ids
    else:
        assert "reset_abort" in scenario_kinds


def test_extended_reset_behavior_does_not_apply_builtin_abort_state_transition() -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_policy_request("reset_behavior")
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["reset_behavior"] = {
        "extension_request": request["id"]
    }
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_assertion_plan(interface, metadata)
    names = {str(item["name"]) for item in interface["signals"]}
    base = {name: 0 for name in names}
    base["rst_n"] = 1
    state: dict = {}

    check_lifecycle_assertions(
        {**base, "cmd_valid": 1, "cmd_ready": 1, "opcode": 1},
        plan,
        state,
    )
    assert state["operations"]["gemm_core"]["active"] is True
    check_lifecycle_assertions({**base, "rst_n": 0}, plan, state)
    assert state["operations"]["gemm_core"]["active"] is True


def test_protocol_behavior_extension_runs_request_to_bundle_boundary() -> None:
    architecture, interface = axi_lite_contracts()
    request = _protocol_request()
    bundle = _protocol_bundle()
    source = _protocol_source()
    architecture["verification_extensions"] = [request]

    Draft202012Validator(extension_request_schema()).validate(request)
    Draft202012Validator(extension_bundle_schema()).validate(bundle)
    assert validate_architect_extension_requests(architecture, interface) == []
    assert validate_verifier_extension_bundles(
        architecture, [bundle], source_files=[source]
    ) == []
    manifest = build_feature_extension_manifest(
        architecture, [bundle], source_files=[source]
    )
    assert manifest["status"] == "contract_local_only"
    assert manifest["promotion"] == "not_implemented"
    entry = manifest["entries"][0]
    assert entry["request"]["domain"] == "protocol"
    assert entry["implementation"]["target"] == {
        "scope": "channel",
        "name": "cmd",
    }


def test_extension_worklist_names_only_the_missing_feature() -> None:
    text = render_requested_extension_worklist(
        {"verification_extensions": [_request()]}
    )
    assert "error_three_cycle_pulse" in text
    assert "preserve_tool_owned_siblings: true" in text
    assert "assertion" in text and "coverage" in text and "stimulus" in text


def test_lifecycle_extension_reference_must_point_to_exact_contract_path() -> None:
    architecture, interface = _contracts()
    request = deepcopy(_request())
    request["replaces_contract_paths"] = []
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["error_style"] = {
        "extension_request": request["id"]
    }
    errors = validate_architect_extension_requests(architecture, interface)
    assert any("replaces_contract_paths" in error for error in errors)


def test_contract_local_signal_role_can_be_declared_without_mutating_role_pool() -> None:
    interface = {
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {
                "name": "credits",
                "direction": "input",
                "protocol_profile": "custom",
            }
        ],
        "signals": [
            {
                "name": "clk",
                "role": "clock",
                "semantic_class": None,
                "channel": None,
                "direction": "input",
                "width": "1",
            },
            {
                "name": "rst_n",
                "role": "reset",
                "semantic_class": None,
                "channel": None,
                "direction": "input",
                "width": "1",
                "semantic": "active-low reset",
            },
            {
                "name": "credit_count",
                "role": "credit_count",
                "semantic_class": None,
                "channel": "credits",
                "direction": "input",
                "width": "4",
            }
        ],
    }
    request = {
        "id": "protocol.credit_count_role",
        "domain": "protocol",
        "feature_name": "credit_count_role",
        "target": {"scope": "signal", "name": "credit_count"},
        "semantics": {
            "summary": "Credit count limits transfers accepted by the receiver.",
            "trigger": "The count changes on a contract-defined credit event.",
            "required_behavior": ["No transfer is accepted with zero credits."],
            "end_condition": "A returned credit permits a later transfer.",
            "forbidden_behavior": [],
        },
        "reason": "The closed Role Pool has no credit-count role.",
        "contract_vocabulary": {
            "pool": "signal_role",
            "name": "credit_count",
            "definition": {
                "description": "Available receiver transaction credits.",
                "coverage_tags": ["flow_control", "credit_boundary"],
                "category": "channel_flow_control",
                "channel_binding": "required",
                "direction_relation": "same_as_channel",
                "allowed_directions": ["input", "output"],
                "semantic_class_binding": "optional",
            },
        },
        "required_observations": [
            {
                "name": "credit_count_signal",
                "kind": "signal",
                "description": "Observed DUT credit count.",
            }
        ],
    }
    architecture = {"verification_extensions": [request]}
    assert validate_architect_extension_requests(architecture, interface) == []
    roles, classes = interface_vocabulary_extensions(architecture)
    assert classes == {}
    assert "credit_count" in roles
    assert validate_interface_signal_roles(
        interface, role_extensions=roles
    ) == []
    assert validate_interface_semantics(
        interface, role_extensions=roles
    ) == []
