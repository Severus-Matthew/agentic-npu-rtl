from __future__ import annotations

import asyncio
from copy import deepcopy
import sys
from types import ModuleType

import pytest

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent
from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
    ProtocolSemanticsError,
    compile_protocol_semantics,
    evaluate_protocol_expression,
)
from multigent.verifier_tool.pool.role_pool.protocol_event_relations import (
    ProtocolEventRelationError,
    compile_protocol_event_relations,
)
from multigent.verifier_tool.protocol.assertion.runtime import (
    build_protocol_assertion_plan,
    check_protocol_assertions,
    finalize_protocol_assertions,
)
from multigent.verifier_tool.protocol.coverage.plan import (
    build_interface_coverage_plan,
)
from multigent.verifier_tool.protocol.stimulus import build_protocol_stimulus_plan
from multigent.verifier_tool.protocol.stimulus import cocotb as cocotb_helpers
from multigent.verifier_tool.protocol.evidence import (
    ProtocolEvidenceError,
    ProtocolEventTraceRecorder,
    capture_protocol_event_traces,
)


def _interface() -> dict:
    return {
        "clock": "clk",
        "reset": "rst",
        "channels": [
            {
                "name": "req",
                "direction": "input",
                "protocol_profile": "example_pipelined",
                "data_objects": [],
                "ordering": "in_order",
                "framing": "single_beat",
            }
        ],
        "signals": [
            {"name": "clk", "role": "clock", "channel": None, "direction": "input", "width": 1, "signed": False, "semantic": "clock"},
            {"name": "rst", "role": "reset", "channel": None, "direction": "input", "width": 1, "signed": False, "semantic": "active-high reset"},
            {"name": "cyc", "role": "metadata", "semantic_class": "command", "channel": "req", "direction": "input", "width": 1, "signed": False},
            {"name": "stb", "role": "valid", "channel": "req", "direction": "input", "width": 1, "signed": False},
            {"name": "stall", "role": "metadata", "semantic_class": "configuration", "channel": "req", "direction": "output", "width": 1, "signed": False},
            {"name": "ack", "role": "metadata", "semantic_class": "response_code", "channel": "req", "direction": "output", "width": 1, "signed": False},
            {"name": "err", "role": "metadata", "semantic_class": "response_code", "channel": "req", "direction": "output", "width": 1, "signed": False},
            {"name": "addr", "role": "payload", "semantic_class": "address", "channel": "req", "direction": "input", "width": 8, "signed": False},
        ],
        "global_handshake_rules": "defined by protocol_semantics",
        "protocol_semantics": [
            {
                "name": "example_pipelined",
                "description": "Composed request and response events.",
                "protocol_groups": ["example"],
                "clock": {"signal": "clk", "edge": "rising"},
                "events": [
                    {"name": "presented", "expression": "cyc && stb", "description": "request visible"},
                    {"name": "ready", "expression": "!stall", "description": "request accepted by sink"},
                    {"name": "accepted", "expression": "presented && ready", "description": "request transfer"},
                    {"name": "stalled", "expression": "presented && !ready", "description": "request waits"},
                    {"name": "success", "expression": "ack", "description": "successful response"},
                    {"name": "error", "expression": "err", "description": "error response"},
                    {"name": "completed", "expression": "ack || err", "description": "response transfer"},
                    {"name": "cancel", "expression": "!cyc", "description": "cycle cancelled"},
                ],
                "transactions": [
                    {
                        "name": "request",
                        "channel": "req",
                        "presented_event": "presented",
                        "ready_event": "ready",
                        "accepted_event": "accepted",
                        "stalled_event": "stalled",
                        "completed_event": "completed",
                        "success_event": "success",
                        "error_event": "error",
                        "content_signals": ["addr"],
                        "stable_while_stalled": True,
                        "stability_rules": [],
                        "source_drive": {
                            "presented_assignments": [
                                {"signal": "cyc", "value": 1},
                                {"signal": "stb", "value": 1},
                            ],
                            "idle_assignments": [
                                {"signal": "cyc", "value": 0},
                                {"signal": "stb", "value": 0},
                            ],
                            "post_accept_assignments": [
                                {"signal": "cyc", "value": 1},
                                {"signal": "stb", "value": 0},
                            ],
                            "driven_fields": ["addr"],
                            "completion_mode": "wait_for_all_completions",
                        },
                    }
                ],
                "flow_control": {
                    "maximum_outstanding": 2,
                    "ordering": "oldest_outstanding",
                    "in_order": True,
                },
                "cancellation": {
                    "supported": True,
                    "trigger_event": "cancel",
                    "pending_behavior": "flush",
                },
                "custom_rules": [],
            }
        ],
    }


def test_architect_effective_schema_exposes_protocol_semantics() -> None:
    schema = ArchitectAgent().load_output_schema(ARCHITECT_OUTPUT_SCHEMA)
    assert "protocol_semantics" in schema["properties"]["interface_contract"]["properties"]
    assert "protocol_event_relations" in schema["properties"]["interface_contract"]["properties"]


def _interface_with_event_relation() -> dict:
    interface = deepcopy(_interface())
    interface["protocol_event_relations"] = [
        {
            "id": "accepted_to_success",
            "description": "An accepted request completes successfully one cycle later.",
            "clock": {"signal": "clk", "edge": "rising"},
            "cause": {
                "kind": "protocol_event",
                "profile": "example_pipelined",
                "event": "accepted",
            },
            "effect": {
                "kind": "protocol_event",
                "profile": "example_pipelined",
                "event": "success",
            },
            "minimum_latency_cycles": 1,
            "maximum_latency_cycles": 1,
            "ordering": "fifo",
            "maximum_outstanding": 2,
            "unmatched_effect": "error",
            "require_effect_before_test_end": True,
            "cancellation": {
                "event": {
                    "kind": "protocol_event",
                    "profile": "example_pipelined",
                    "event": "cancel",
                },
                "pending_behavior": "flush",
            },
        }
    ]
    return interface


def test_compiler_inlines_events_and_runtime_evaluates_them() -> None:
    compiled = compile_protocol_semantics(_interface())
    accepted = compiled["profiles"][0]["transactions"][0]["accepted"]
    assert evaluate_protocol_expression(
        accepted, {"cyc": 1, "stb": 1, "stall": 0}
    )
    assert not evaluate_protocol_expression(
        accepted, {"cyc": 1, "stb": 1, "stall": 1}
    )


def test_compiler_rejects_unknown_identifiers_and_event_cycles() -> None:
    unknown = _interface()
    unknown["protocol_semantics"][0]["events"][0]["expression"] = "missing && stb"
    with pytest.raises(ProtocolSemanticsError, match="undeclared"):
        compile_protocol_semantics(unknown)

    cycle = _interface()
    cycle["protocol_semantics"][0]["events"][0]["expression"] = "ready"
    cycle["protocol_semantics"][0]["events"][1]["expression"] = "presented"
    with pytest.raises(ProtocolSemanticsError, match="dependency cycle"):
        compile_protocol_semantics(cycle)


def test_event_relation_compiler_resolves_events_and_rejects_bad_latency() -> None:
    interface = _interface_with_event_relation()
    relation = compile_protocol_event_relations(interface)["relations"][0]
    assert relation["cause"]["signals"] == ("cyc", "stb", "stall")
    assert relation["effect"]["signals"] == ("ack",)

    interface["protocol_event_relations"][0]["maximum_latency_cycles"] = 0
    with pytest.raises(ProtocolEventRelationError, match="below minimum"):
        compile_protocol_event_relations(interface)


def test_event_relation_runtime_accepts_declared_cycle_and_rejects_same_cycle() -> None:
    coverage_plan = build_interface_coverage_plan(_interface_with_event_relation())
    assertion_plan = build_protocol_assertion_plan(coverage_plan)
    assert len(assertion_plan["event_correlations"]) == 1

    state: dict = {}
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 0, "ack": 0, "err": 0, "addr": 7},
        assertion_plan,
        state,
    )
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 0, "stall": 0, "ack": 1, "err": 0, "addr": 7},
        assertion_plan,
        state,
    )
    finalize_protocol_assertions(assertion_plan, state)

    same_cycle: dict = {}
    with pytest.raises(AssertionError, match="effect latency 0 cycles"):
        check_protocol_assertions(
            {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 0, "ack": 1, "err": 0, "addr": 7},
            assertion_plan,
            same_cycle,
        )


def test_event_relation_cancellation_flushes_pending_cause() -> None:
    coverage_plan = build_interface_coverage_plan(_interface_with_event_relation())
    assertion_plan = build_protocol_assertion_plan(coverage_plan)
    state: dict = {}
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 0, "ack": 0, "err": 0, "addr": 9},
        assertion_plan,
        state,
    )
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 0, "stb": 0, "stall": 0, "ack": 0, "err": 0, "addr": 0},
        assertion_plan,
        state,
    )
    finalize_protocol_assertions(assertion_plan, state)


def test_custom_events_reuse_handshake_stall_and_accounting_features() -> None:
    coverage_plan = build_interface_coverage_plan(_interface())
    identities = {
        str(item["id"]): item for item in coverage_plan["feature_plan"]["features"]
    }
    root = "protocol_transaction.example_pipelined.request"
    assert identities[f"{root}.handshake_states"]["coverage"]["sampler"] == "valid_ready_cross"
    assert identities[f"{root}.stall.stall_stability"]["assertion"]["checker"] == "stall_stability"
    assert identities[f"{root}.accounting"]["assertion"]["checker"] == "transaction_accounting"


def test_custom_input_transaction_is_exposed_to_generic_stimulus_driver() -> None:
    stimulus = build_protocol_stimulus_plan(_interface())
    event_profile = stimulus["event_protocols"][0]
    assert event_profile["name"] == "example_pipelined"
    assert event_profile["driver_component_id"] == (
        "protocol.driver.contract_event_source"
    )
    transaction = event_profile["transactions"][0]
    assert transaction["name"] == "request"
    assert transaction["source_drive"]["driven_fields"] == ("addr",)


def test_runtime_catches_stall_mutation_and_completion_without_request() -> None:
    coverage_plan = build_interface_coverage_plan(_interface())
    assertion_plan = build_protocol_assertion_plan(coverage_plan)
    state: dict = {}
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 1, "ack": 0, "err": 0, "addr": 3},
        assertion_plan,
        state,
    )
    with pytest.raises(AssertionError, match="content changed during stall"):
        check_protocol_assertions(
            {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 1, "ack": 0, "err": 0, "addr": 4},
            assertion_plan,
            state,
        )

    empty_state: dict = {}
    with pytest.raises(AssertionError, match="without an accepted outstanding request"):
        check_protocol_assertions(
            {"clk": 1, "rst": 0, "cyc": 1, "stb": 0, "stall": 0, "ack": 1, "err": 0, "addr": 0},
            assertion_plan,
            empty_state,
        )


def test_runtime_accept_complete_and_cancel_paths_finalize_cleanly() -> None:
    coverage_plan = build_interface_coverage_plan(_interface())
    assertion_plan = build_protocol_assertion_plan(coverage_plan)
    state: dict = {}
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 0, "ack": 0, "err": 0, "addr": 7},
        assertion_plan,
        state,
    )
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 0, "stall": 0, "ack": 1, "err": 0, "addr": 7},
        assertion_plan,
        state,
    )
    finalize_protocol_assertions(assertion_plan, state)

    cancelled: dict = {}
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 1, "stb": 1, "stall": 0, "ack": 0, "err": 0, "addr": 9},
        assertion_plan,
        cancelled,
    )
    check_protocol_assertions(
        {"clk": 1, "rst": 0, "cyc": 0, "stb": 0, "stall": 0, "ack": 0, "err": 0, "addr": 0},
        assertion_plan,
        cancelled,
    )
    finalize_protocol_assertions(assertion_plan, cancelled)


def test_event_trace_recorder_derives_cycle_and_transaction_evidence() -> None:
    profile = compile_protocol_semantics(_interface())["profiles"][0]
    transaction = profile["transactions"][0]
    recorder = ProtocolEventTraceRecorder(profile, transaction, ["rst"])

    recorder.sample(
        {"rst": 0, "cyc": 1, "stb": 1, "stall": 0, "ack": 0, "err": 0, "addr": 7}
    )
    recorder.sample(
        {"rst": 0, "cyc": 1, "stb": 0, "stall": 0, "ack": 1, "err": 0, "addr": 7}
    )

    evidence = recorder.evidence(stimulus_result=[{"addr": 7}])
    assert [item["event"] for item in evidence["transaction_trace"]] == [
        "accepted", "success"
    ]
    assert evidence["transaction_trace"][0]["signals"]["addr"] == 7
    assert evidence["cycle_trace"][0]["events"]["accepted"] is True
    assert evidence["cycle_trace"][1]["events"]["completed"] is True
    assert evidence["stimulus_result"] == [{"addr": 7}]


def test_multi_binding_event_capture_rejects_empty_binding_map() -> None:
    class Stimulus:
        def __await__(self):
            if False:
                yield None
            return None

    with pytest.raises(ProtocolEvidenceError, match="bindings must be nonempty"):
        asyncio.run(capture_protocol_event_traces(object(), {}, Stimulus()))


def test_generic_event_driver_holds_post_accept_state_until_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Signal:
        def __init__(self, value: int = 0) -> None:
            self.value = value

    class Dut:
        pass

    dut = Dut()
    for name in ("clk", "rst", "cyc", "stb", "stall", "ack", "err", "addr"):
        setattr(dut, name, Signal())
    dut.stall.value = 1

    class Scheduler:
        accepted_address: int | None = None
        pending = False
        saw_post_accept = False

        def rising(self) -> None:
            if int(dut.cyc.value) and int(dut.stb.value) and not int(dut.stall.value):
                self.accepted_address = int(dut.addr.value)
                self.pending = True
            elif int(dut.cyc.value) and not int(dut.stb.value):
                self.saw_post_accept = True
            dut.ack.value = int(self.pending and int(dut.cyc.value))
            if int(dut.ack.value):
                self.pending = False
            dut.stall.value = 0

    scheduler = Scheduler()

    class Edge:
        def __init__(self, _signal: Signal, *, rising: bool) -> None:
            self.rising = rising

        def __await__(self):
            if self.rising:
                scheduler.rising()
            if False:
                yield None
            return None

    triggers = ModuleType("cocotb.triggers")
    triggers.FallingEdge = lambda signal: Edge(signal, rising=False)
    triggers.RisingEdge = lambda signal: Edge(signal, rising=True)
    cocotb = ModuleType("cocotb")
    cocotb.triggers = triggers
    monkeypatch.setitem(sys.modules, "cocotb", cocotb)
    monkeypatch.setitem(sys.modules, "cocotb.triggers", triggers)

    async def no_settle(_timer_ps: int) -> None:
        return None

    monkeypatch.setattr(cocotb_helpers, "_settle", no_settle)
    profile = compile_protocol_semantics(_interface())["profiles"][0]
    transaction = profile["transactions"][0]
    accepted = asyncio.run(
        cocotb_helpers.drive_protocol_event_transactions(
            dut, profile, transaction, [{"addr": 0x35}], timeout_cycles=8
        )
    )
    assert accepted == [{"addr": 0x35}]
    assert scheduler.accepted_address == 0x35
    assert scheduler.saw_post_accept
    assert int(dut.cyc.value) == 0
    assert int(dut.stb.value) == 0
