from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
import yaml

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent
from multigent.agents.verifier_review import VerifierReviewAgent
from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan
from multigent.verifier_tool.coverage.operation.plan import build_operation_coverage_plan, merge_coverage_plans, operation_plan_for_tests
from multigent.verifier_tool.coverage.operation.sampling import (
    OperationSamplingError, effective_operation_coverage, extract_operation_sampling_bindings,
    normalize_operation_sampling_bindings, operation_observer_views,
)
from multigent.verifier_tool.coverage.runtime import (
    CoverageRuntimeError,
    InterfaceCoverageTracker,
    capture_contract_snapshot,
)
from multigent.verifier_tool.predefined_assertion.instrumentation import (
    install_contract_generated_block,
    render_contract_generated_block,
)
from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.tests.test_verifier import generic_fir_context, verification_ready_result
from multigent.orchestration import artifacts
import multigent.orchestration.verification_tools_node as verification_tools


class Signal:
    def __init__(self, width, value=0):
        self.width, self.value = width, value

    def __len__(self):
        return self.width


class Dut:
    def __init__(self):
        for name, width in {"clk": 1, "rst": 1, "cv": 1, "cr": 1, "cfg": 10,
                            "av": 1, "ar": 1, "left": 4, "right": 4,
                            "yv": 1, "yr": 1, "result": 4}.items():
            setattr(self, name, Signal(width))


def contracts():
    architecture = {
        "dimensions": [{"name": name, "minimum": 1, "maximum": 4} for name in ("M", "N", "K")],
        "parameters": [{"name": "TILE", "default_value": "2"}],
        "data_types": [{"name": "u4", "width_bits": 4, "signed": False},
                       {"name": "s4", "width_bits": 4, "signed": True},
                       {"name": "u5", "width_bits": 5, "signed": False}],
    }
    interface = {
        "clock": "clk", "reset": "rst",
        "channels": [{"name": name, "protocol_profile": "ready_valid"} for name in ("cmd", "a", "y")],
        "signals": [{"name": "clk", "role": "clock", "width": "1"},
                    {"name": "rst", "role": "reset", "width": "1", "semantic": "active-high reset"}],
    }
    for channel, names, width in (("cmd", ("cv", "cr", "cfg"), 10),
                                  ("a", ("av", "ar", "left"), 4),
                                  ("y", ("yv", "yr", "result"), 4)):
        for role, name in zip(("valid", "ready", "payload"), names):
            interface["signals"].append({"name": name, "role": role, "channel": channel,
                                         "width": str(width if role == "payload" else 1)})
    interface["signals"].append({"name": "right", "role": "payload", "width": "4", "channel": None})
    return architecture, interface


def point(identity, concept="dimensions", source="baseline"):
    return {"id": identity, "concept": concept, "field": identity, "source": source,
            "description": concept, "bins": [{"name": "draft", "intent": "draft bin",
                                                "predicate": {"op": "eq", "args": [999]}}]}


def spec(*points):
    return [{"operation_name": "compute", "family": "matrix_multiply", "coverpoints": list(points)}]


def binding(identity, template="dimension", **kwargs):
    result = {"operation": "compute", "point": identity, "template": template,
              "event": "transfer", "channel": "cmd"}
    if template == "dimension":
        result.update(fields={"value": {"signal": "cfg", "lsb": 0, "width": 3}}, dimension="M")
    result.update(kwargs)
    return result


def test_static_binding_alias_is_safely_expanded_to_literal() -> None:
    source = '''FIELDS = {"value": {"signal": "cfg", "lsb": 0, "width": 3}}
OPERATION_SAMPLING_BINDINGS = [
    {"operation": "compute", "point": "m", "template": "dimension",
     "event": "transfer", "channel": "cmd", "fields": FIELDS, "dimension": "M"}
]
'''
    bindings = extract_operation_sampling_bindings([source])
    assert bindings[0]["fields"]["value"]["signal"] == "cfg"
    normalized = normalize_operation_sampling_bindings(source)
    assert "'fields': {'value': {'signal': 'cfg'" in normalized
    assert extract_operation_sampling_bindings([normalized]) == bindings


def tracker_for(specs, bindings, *, architecture=None, interface=None, with_protocol=False):
    default_architecture, default_interface = contracts()
    architecture, interface = architecture or default_architecture, interface or default_interface
    plan = build_operation_coverage_plan(specs, sampling_bindings=bindings, architecture=architecture, interface=interface)
    if with_protocol:
        plan = merge_coverage_plans(build_interface_coverage_plan(interface), plan)
    return InterfaceCoverageTracker(plan), plan


def sample_tracker(tracker, dut):
    namespace = getattr(tracker, "_test_protocol_namespace", None)
    if namespace is None:
        namespace = {}
        exec(render_contract_generated_block(tracker.plan), namespace)
        tracker._test_protocol_namespace = namespace
    tracker.sample_snapshot(
        capture_contract_snapshot(dut, tracker.signal_names),
        namespace["_check_contract_protocol_assertions"],
    )


def hits(tracker, identity):
    return {row["name"]: row["hits"] for item in tracker.report()["obligations"]
            if item["id"] == f"operation.compute.{identity}" for row in item["bins"]}


def test_dimension_observation_not_claimed_tb_value_hits_real_coverpoint():
    tracker, plan = tracker_for(spec(point("m")), [binding("m")])
    dut = Dut()
    dut.cfg.value, dut.cr.value = 2, 1
    sample_tracker(tracker, dut)  # valid=0: no accepted command.
    tracker.sample_operation("compute", {"m": 4}, "directed")
    assert hits(tracker, "m") == {"minimum": 0, "interior": 0, "maximum": 0}
    dut.cv.value = 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "m") == {"minimum": 0, "interior": 1, "maximum": 0}
    assert tracker.report()["operation_sampling"][0]["last_value"] == 2
    assert tracker.coverage_model.coverage_items["operation.compute.m"].__class__.__name__ == "CoverPoint"
    assert plan["obligations"][0]["bins"][0]["predicate"]["args"] == [1]


@pytest.mark.parametrize("low,high,labels", [(1, 4, ["minimum", "interior", "maximum"]),
                                            (1, 64, ["minimum", "interior", "maximum"]),
                                            (4, 4, ["fixed"]), (1, 2, ["minimum", "maximum"])])
def test_dimension_bins_are_contract_owned_and_reachable(low, high, labels):
    architecture, interface = contracts()
    architecture["dimensions"][0].update(minimum=low, maximum=high)
    _, plan = tracker_for(spec(point("m")), [binding("m", fields={"value": {"signal": "cfg", "width": max(3, high.bit_length())}})], architecture=architecture, interface=interface)
    assert [item["name"] for item in plan["obligations"][0]["bins"]] == labels
    assert plan["obligations"][0]["bins"][-1]["predicate"]["args"] == [high]


def test_integer_operand_uses_actual_transfer_signed_decode_and_type_bounds():
    config = binding("operand", "integer_operand", channel="a", fields={"value": {"channel": "a", "role": "payload"}}, data_type="s4")
    tracker, _ = tracker_for(spec(point("operand", "operand_values")), [config])
    dut = Dut()
    dut.left.value, dut.av.value, dut.ar.value = 15, 1, 0
    sample_tracker(tracker, dut)
    assert not any(hits(tracker, "operand").values())
    dut.ar.value = 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "operand")["negative"] == 1
    assert hits(tracker, "operand")["positive"] == 0
    assert tracker.report()["operation_sampling"][0]["last_value"] == -1


def test_unique_whole_operand_payload_is_code_bound_by_role_and_type():
    architecture, interface = contracts()
    next(signal for signal in interface["signals"] if signal["name"] == "left")["signed"] = True
    config = binding("operand", "integer_operand", channel="a", fields={}, data_type="s4")
    tracker, plan = tracker_for(
        spec(point("operand", "operand_values")), [config],
        architecture=architecture, interface=interface,
    )
    sampling = plan["obligations"][0]["bindings"]["sampling"]
    assert sampling["fields"]["value"]["signal"] == "left"
    dut = Dut()
    dut.left.value, dut.av.value, dut.ar.value = 15, 1, 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "operand")["negative"] == 1


def test_one_bit_boolean_payload_can_be_code_bound_by_role():
    architecture, interface = contracts()
    payload = next(signal for signal in interface["signals"] if signal["name"] == "left")
    payload.update(width="1", signed=False)
    config = binding("mode", "boolean_mode", channel="a", fields={}, legal_values=[0, 1])
    _, plan = tracker_for(
        spec(point("mode", "post_processing")), [config],
        architecture=architecture, interface=interface,
    )
    assert plan["obligations"][0]["bindings"]["sampling"]["fields"]["value"]["signal"] == "left"


@pytest.mark.parametrize("change,reason", [
    ("extra_payload", "exactly one payload"),
    ("packed_payload", "width/signedness"),
    ("symbolic_width", "literal width"),
    ("unknown_signedness", "literal width and signedness"),
])
def test_uncertain_payload_binding_requires_explicit_field(change, reason):
    architecture, interface = contracts()
    payload = next(signal for signal in interface["signals"] if signal["name"] == "left")
    payload["signed"] = True
    if change == "extra_payload":
        interface["signals"].append({"name": "second", "role": "payload", "channel": "a",
                                     "width": "4", "signed": True})
    elif change == "packed_payload":
        payload["width"] = "8"
    elif change == "symbolic_width":
        payload["width"] = "OPERAND_WIDTH"
    else:
        del payload["signed"]
    config = binding("operand", "integer_operand", channel="a", fields={}, data_type="s4")
    with pytest.raises(OperationSamplingError, match=reason):
        tracker_for(
            spec(point("operand", "operand_values")), [config],
            architecture=architecture, interface=interface,
        )


def test_fixed_enabled_mode_does_not_invent_disabled_bin_or_accept_claimed_label():
    config = binding("relu", "boolean_mode", fields={"value": {"signal": "cfg", "lsb": 9, "width": 1}}, legal_values=[1])
    tracker, _ = tracker_for(spec(point("relu", "post_processing")), [config])
    dut = Dut()
    dut.cv.value = dut.cr.value = 1
    sample_tracker(tracker, dut)
    tracker.sample_operation("compute", {"relu": True}, "directed")
    assert hits(tracker, "relu") == {"enabled": 0}
    dut.cfg.value = 1 << 9
    sample_tracker(tracker, dut)
    assert hits(tracker, "relu") == {"enabled": 1}


def test_channel_stall_measures_actual_overlap_not_planned_delay():
    config = binding("bp", "channel_stall", channel="y")
    tracker, _ = tracker_for(
        spec(point("bp", "output_backpressure", "architect_extension")),
        [config],
        with_protocol=True,
    )
    dut = Dut()
    dut.yr.value = 0  # ready low without valid does not exercise backpressure.
    sample_tracker(tracker, dut)
    tracker.sample_operation("compute", {"bp": 6}, "directed")
    assert not any(hits(tracker, "bp").values())
    dut.yv.value = dut.yr.value = 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "bp")["none"] == 1
    for length, label in ((1, "one_cycle"), (3, "short"), (6, "long")):
        dut.yr.value = 0
        for _ in range(length):
            sample_tracker(tracker, dut)
        assert hits(tracker, "bp")[label] == 0
        dut.yr.value = 1
        sample_tracker(tracker, dut)
        assert hits(tracker, "bp")[label] == 1


def test_reset_and_test_boundaries_cancel_pending_operation_stall():
    tracker, _ = tracker_for(spec(point("bp")), [binding("bp", "channel_stall", channel="y")], with_protocol=True)
    dut = Dut()
    dut.yv.value = 1
    for _ in range(3):
        sample_tracker(tracker, dut)
    dut.rst.value = 1
    tracker.observe_reset_snapshot(
        capture_contract_snapshot(dut, ("rst",)),
        tracker._test_protocol_namespace["_check_contract_protocol_assertions"],
    )
    dut.rst.value, dut.yr.value = 0, 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "bp")["short"] == 0
    assert hits(tracker, "bp")["none"] == 1
    dut.yr.value = 0
    sample_tracker(tracker, dut)
    tracker.end_test()
    tracker._test_protocol_namespace["_CONTRACT_PROTOCOL_STATE"].clear()
    tracker.begin_test("next")
    dut.yr.value = 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "bp")["one_cycle"] == 0


def test_operation_guard_filters_shared_channel_encodings():
    config = binding("m", guards=[{"field": {"signal": "cfg", "lsb": 9, "width": 1}, "equals": 0}])
    tracker, _ = tracker_for(spec(point("m")), [config])
    dut = Dut()
    dut.cv.value = dut.cr.value = 1
    dut.cfg.value = (1 << 9) | 4
    sample_tracker(tracker, dut)
    assert not any(hits(tracker, "m").values())
    dut.cfg.value = 4
    sample_tracker(tracker, dut)
    assert hits(tracker, "m")["maximum"] == 1


def test_tile_shape_reads_accepted_dimensions_and_explicit_tile_parameters():
    config = binding("tile", "tile_shape", fields={"M": {"signal": "cfg", "width": 3},
                                                    "N": {"signal": "cfg", "lsb": 3, "width": 3}},
                     tile_parameters={"M": "TILE", "N": "TILE"})
    tracker, _ = tracker_for(spec(point("tile", "tiling")), [config])
    dut = Dut()
    dut.cv.value = dut.cr.value = 1
    for m, n in ((2, 2), (3, 2)):
        dut.cfg.value = m | n << 3
        sample_tracker(tracker, dut)
    assert hits(tracker, "tile") == {"full_tile": 1, "partial_tile": 1}


@pytest.mark.parametrize("dtype,a,b,expected", [("u4", 15, 15, True), ("u4", 8, 8, True),
                                               ("u4", 1, 2, False), ("s4", 15, 15, False),
                                               ("s4", 7, 1, True), ("s4", 8, 15, True)])
def test_add_overflow_covers_input_case_not_assumed_dut_flag(dtype, a, b, expected):
    config = binding("overflow", "integer_add_overflow", event="clock",
                     fields={"a": {"signal": "left"}, "b": {"signal": "right"}},
                     operand_types={"a": dtype, "b": dtype}, result_type=dtype)
    config.pop("channel")
    tracker, _ = tracker_for(spec(point("overflow", "accumulation")), [config])
    dut = Dut()
    dut.left.value, dut.right.value = a, b
    sample_tracker(tracker, dut)
    assert hits(tracker, "overflow")["overflow" if expected else "no_overflow"] == 1


def test_widened_add_does_not_create_unreachable_overflow_bin():
    config = binding("overflow", "integer_add_overflow", event="clock",
                     fields={"a": {"signal": "left"}, "b": {"signal": "right"}},
                     operand_types={"a": "u4", "b": "u4"}, result_type="u5")
    config.pop("channel")
    tracker, _ = tracker_for(spec(point("overflow")), [config])
    assert hits(tracker, "overflow") == {"no_overflow": 0}


def test_effective_definitions_replace_draft_bins_without_mutating_candidate():
    specs = spec(point("m"))
    original = copy.deepcopy(specs)
    _, plan = tracker_for(specs, [binding("m")])
    actual = effective_operation_coverage(specs, plan)
    assert actual[0]["coverpoints"][0]["bins"][0]["name"] == "minimum"
    assert specs == original


def test_literal_metadata_can_repeat_in_modules_but_conflicting_bindings_reject():
    text = f"OPERATION_SAMPLING_BINDINGS = {[binding('m')]!r}\n"
    architecture, interface = contracts()
    plan = operation_plan_for_tests(spec(point("m")), [text, text], architecture, interface)
    assert plan["obligations"][0]["bindings"]["sampling"]["template"] == "dimension"
    conflict = binding("m", dimension="N")
    with pytest.raises(OperationSamplingError, match="Conflicting"):
        operation_plan_for_tests(spec(point("m")), [text, f"OPERATION_SAMPLING_BINDINGS = {[conflict]!r}"], architecture, interface)


@pytest.mark.parametrize("changes,message", [({"dimension": "missing"}, "dimension"),
                                            ({"channel": "missing"}, "channel"),
                                            ({"point": "missing"}, "undeclared"),
                                            ({"template": "new_algorithm"}, "Unknown runtime"),
                                            ({"fields": {"value": {"signal": "missing"}}}, "sampling field"),
                                            ({"fields": {"value": {"signal": "cfg", "lsb": 9, "width": 3}}}, "width")])
def test_invalid_connections_have_precise_preflight_errors(changes, message):
    with pytest.raises(OperationSamplingError, match=message):
        tracker_for(spec(point("m")), [binding("m", **changes)])


def test_dynamic_metadata_is_not_executed():
    with pytest.raises(OperationSamplingError, match="literal list"):
        extract_operation_sampling_bindings(["OPERATION_SAMPLING_BINDINGS = make_bindings()"])


def test_symbolic_signal_width_uses_elaborated_handle():
    architecture, interface = contracts()
    next(item for item in interface["signals"] if item["name"] == "cfg")["width"] = "COMMAND_WIDTH"
    tracker, _ = tracker_for(spec(point("m")), [binding("m")], architecture=architecture, interface=interface)
    dut = Dut()
    dut.cv.value = dut.cr.value = 1
    dut.cfg.value = 4
    sample_tracker(tracker, dut)
    assert hits(tracker, "m")["maximum"] == 1
    bad, _ = tracker_for(spec(point("m")), [binding("m", fields={"value": {"signal": "cfg", "lsb": 9, "width": 3}})],
                         architecture=architecture, interface=interface)
    with pytest.raises(CoverageRuntimeError, match="elaborated width"):
        sample_tracker(bad, dut)
    assert bad.report()["assertion_failures"]


def test_unbound_new_feature_cannot_use_legacy_value_hook():
    with pytest.raises(CoverageRuntimeError, match="Missing operation sampling bindings"):
        tracker_for(spec(point("custom", "new_algorithm_case", "llm_extension")), [])


def bound_fir_candidate():
    context, candidate = generic_fir_context(), verification_ready_result()
    frozen = context["frozen_architecture"]
    frozen["architecture_contract"]["dimensions"] = [{"name": "TAPS", "minimum": 1, "maximum": 16}]
    frozen["interface_contract"]["channels"].append({"name": "tap_configuration", "direction": "input",
                                                   "protocol_profile": "custom"})
    frozen["interface_contract"]["signals"].append({"name": "taps", "role": "payload",
        "width": "5", "direction": "input", "channel": "tap_configuration", "semantic_class": "configuration"})
    config = {"operation": "filter", "point": "tap_count", "template": "dimension", "event": "clock",
              "fields": {"value": {"signal": "taps"}}, "dimension": "TAPS"}
    contents = candidate["test_files"][0]["content"].replace('"tap_count": 4, ', '')
    old = extract_operation_sampling_bindings([contents])
    updated = [config if item["point"] == "tap_count" else item for item in old]
    candidate["test_files"][0]["content"] = "\n".join(
        f"OPERATION_SAMPLING_BINDINGS = {updated!r}" if line.startswith("OPERATION_SAMPLING_BINDINGS =") else line
        for line in contents.splitlines())
    return context, candidate, config


def test_verifier_persists_effective_runtime_plan_without_requiring_claimed_field(tmp_path):
    context, candidate, config = bound_fir_candidate()
    VerifierAgent().persist_validated_result(result=candidate, context=context, root=tmp_path)
    plan = yaml.safe_load((tmp_path / "verification/operation_coverage_plan.yaml").read_text())
    point = next(row for row in plan["obligations"] if row["id"] == "operation.filter.tap_count")
    assert point["bindings"]["sampling"]["fields"]["value"]["signal"] == "taps"
    assert [row["name"] for row in point["bins"]] == ["minimum", "interior", "maximum"]
    assert config in yaml.safe_load((tmp_path / "verification/operation_sampling_bindings.yaml").read_text())
    # Old candidate bins are saved for provenance, never used for runtime sampling.
    saved = json.loads((tmp_path / "verification/verifier_result.json").read_text())
    assert saved["operation_coverage"][0]["coverpoints"][0]["bins"][0]["name"] == "four"


def test_review_sees_actual_operation_sources_and_effective_bins_not_hit_evidence():
    context, candidate, _ = bound_fir_candidate()
    review = VerifierReviewAgent.build_context(context, candidate)
    point = review["operation_coverage"][0]["coverpoints"][0]
    assert [row["name"] for row in point["bins"]] == ["minimum", "interior", "maximum"]
    automatic = next(row for row in review["operation_sampling_plan"]["obligations"] if row["id"] == "operation.filter.tap_count")
    assert automatic["bindings"]["sampling"]["fields"]["value"]["signal"] == "taps"
    assert review["provenance"]["includes_stimulus"] is True
    assert "operation_sampling_source" in review["trusted_monitor"]
    assert "samples" not in automatic and "hits" not in automatic["bins"][0]


def test_source_only_repair_preserves_literal_operation_connections():
    context, candidate, _ = bound_fir_candidate()
    task = VerifierAgent._build_source_repair_task(context, candidate)
    assert "OPERATION_SAMPLING_BINDINGS" in task and "operation_sampling_bindings:" in task
    assert "signal: taps" in task and "sample_operation only links the checked job" in task


def test_actual_simulation_node_passes_runtime_bindings_to_runner(tmp_path, monkeypatch):
    context, candidate, _ = bound_fir_candidate()
    captured = {}
    monkeypatch.setattr(verification_tools, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(verification_tools, "run_verilator_lint", lambda **kwargs: {"status": "PASS"})

    def simulate(**kwargs):
        captured.update(kwargs)
        return {"status": "PASS", "failure_class": None}

    monkeypatch.setattr(verification_tools, "run_cocotb_regression", simulate)
    state = {"verifier_status": "VERIFICATION_READY", "verification_context": context,
             "verification_plan": candidate["verification_plan"], "verifier_result": candidate}
    result = verification_tools.verification_tools_node(state)
    assert result["verification_status"] == "PASS"
    observed = next(row for row in captured["coverage_plan"]["obligations"] if row["id"] == "operation.filter.tap_count")
    assert observed["bindings"]["sampling"]["fields"]["value"]["signal"] == "taps"
    assert [row["name"] for row in observed["bins"]] == ["minimum", "interior", "maximum"]
    assert captured["coverage_plan"]["requirements"]["randomized_transactions_minimum"] == 100


def test_closure_feedback_uses_effective_bins_and_signal_bindings():
    context, candidate, _ = bound_fir_candidate()
    missing = artifacts._missing_bin_definitions(context, {"verifier_result": candidate}, ["operation.filter.tap_count.maximum"])
    assert len(missing) == 1
    assert missing[0]["bins"][0]["predicate"] == {"op": "eq", "args": [16]}
    assert missing[0]["bindings"]["sampling"]["fields"]["value"]["signal"] == "taps"


def test_bad_operation_connection_becomes_verifier_repair_error_not_raw_exception():
    context, candidate, _ = bound_fir_candidate()
    candidate["test_files"][0]["content"] = candidate["test_files"][0]["content"].replace("'taps'", "'missing'")
    with pytest.raises(AgentRuntimeError, match="Invalid operation sampling bindings"):
        VerifierAgent._validate_result(result=candidate, context=context)


@pytest.mark.parametrize("changes", [{"template": []}, {"guards": None},
                                    {"legal_values": [0, 1], "template": "boolean_mode", "guards": 1},
                                    {"dimension": "M", "unrecognized": 1}])
def test_malformed_metadata_uses_explicit_sampling_error(changes):
    with pytest.raises(OperationSamplingError):
        tracker_for(spec(point("m")), [binding("m", **changes)])


def test_dimension_encoding_outside_field_width_requires_binding_correction():
    architecture, interface = contracts()
    architecture["dimensions"][0]["maximum"] = 64
    with pytest.raises(OperationSamplingError, match="encodings exceed"):
        tracker_for(spec(point("m")), [binding("m")], architecture=architecture, interface=interface)


def test_illegal_dimensions_do_not_hit_full_or_partial_tile():
    config = binding("tile", "tile_shape", fields={"M": {"signal": "cfg", "width": 3}},
                     tile_parameters={"M": "TILE"})
    tracker, _ = tracker_for(spec(point("tile", "tiling")), [config])
    dut = Dut()
    dut.cv.value = dut.cr.value = 1
    for value in (0, 5, 6, 7):
        dut.cfg.value = value
        sample_tracker(tracker, dut)
    assert hits(tracker, "tile") == {"full_tile": 0, "partial_tile": 0}


def test_ledger_distinguishes_ignored_tb_labels_from_runtime_observations():
    tracker, _ = tracker_for(spec(point("m")), [binding("m")])
    dut = Dut()
    dut.cv.value = dut.cr.value = 1
    dut.cfg.value = 2
    sample_tracker(tracker, dut)
    identity = tracker.record_stimulus("directed", {"M": 2}, {"result": 5})
    tracker.sample_operation("compute", {"m": 999}, "directed", identity)
    sample = tracker.stimulus_records[0]["operation_samples"][0]
    assert sample["fields"] == {} and sample["ignored_runtime_fields"] == ["m"]
    assert sample["runtime_sampled_points"] == ["operation.compute.m"]
    assert hits(tracker, "m") == {"minimum": 0, "interior": 1, "maximum": 0}


def custom_point():
    result = point("custom", "pool_missing_feature", "llm_extension")
    result["bins"] = [{"name": name, "intent": name, "predicate": {"op": "eq", "args": [value]}}
                      for name, value in (("small", False), ("large", True))]
    return result


def custom_binding(**changes):
    result = binding("custom", "custom", event="clock", observer="observe_custom",
                     fields={"a": {"signal": "left"}, "b": {"signal": "right"}})
    result.pop("channel")
    result.update(changes)
    return result


def custom_tracker(observer, **changes):
    config = custom_binding(**changes)
    tracker, _ = tracker_for(spec(custom_point()), [config])
    tracker.operation_monitor.bind_observers({"OPERATION_SAMPLING_BINDINGS": [config], "observe_custom": observer})
    return tracker


def test_pool_missing_feature_uses_same_dut_monitor_and_real_library():
    tracker = custom_tracker(lambda values, state: values["a"] + values["b"] > 15)
    tracker.sample_operation("compute", {"custom": True}, "directed")
    assert hits(tracker, "custom") == {"small": 0, "large": 0}
    dut = Dut()
    dut.left.value, dut.right.value = 1, 2
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom") == {"small": 1, "large": 0}
    dut.left.value = dut.right.value = 15
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom") == {"small": 1, "large": 1}
    assert tracker.report()["status"] == "PASS"
    assert tracker.coverage_model.coverage_items["operation.compute.custom"].__class__.__name__ == "CoverPoint"


def test_custom_observer_transfer_gating_and_signed_values():
    tracker = custom_tracker(lambda values, state: values["a"] < 0, event="transfer", channel="a", field_types={"a": "s4"})
    dut = Dut()
    dut.left.value, dut.av.value = 15, 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom") == {"small": 0, "large": 0}
    dut.ar.value = 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom") == {"small": 0, "large": 1}


def test_custom_observer_observed_state_and_reset_cancellation():
    def observe(values, state):
        if values["valid"] and values["ready"]:
            state["total"] = state.get("total", 0) + values["a"]
        if values["done"]:
            return state.pop("total", 0) > 15
        return None

    tracker = custom_tracker(observe, fields={"a": {"signal": "left"}, "valid": {"signal": "av"},
                                            "ready": {"signal": "ar"}, "done": {"signal": "cv"}})
    dut = Dut()
    dut.left.value, dut.av.value, dut.ar.value = 10, 1, 1
    sample_tracker(tracker, dut)
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom") == {"small": 0, "large": 0}
    dut.av.value, dut.cv.value = 0, 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom")["large"] == 1
    dut.av.value, dut.cv.value = 1, 0
    sample_tracker(tracker, dut)
    tracker.operation_monitor.reset()
    dut.av.value, dut.cv.value = 0, 1
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom")["small"] == 1
    tracker.begin_test("next")
    sample_tracker(tracker, dut)
    assert hits(tracker, "custom")["small"] == 2


def test_custom_observer_receives_read_only_snapshot_not_dut_or_tracker():
    def observe(values, state):
        values["a"] = 15
        return True

    tracker = custom_tracker(observe)
    with pytest.raises(CoverageRuntimeError, match="Custom observer.*TypeError"):
        sample_tracker(tracker, Dut())
    assert not any(hits(tracker, "custom").values())


@pytest.mark.parametrize("returned", [{"hit": True}, [1, 2], float("nan"), float("inf")])
def test_custom_observer_invalid_returns_are_execution_errors(returned):
    tracker = custom_tracker(lambda values, state: returned)
    with pytest.raises(CoverageRuntimeError, match="finite scalar or None"):
        sample_tracker(tracker, Dut())
    assert tracker.report()["assertion_failures"]


def test_custom_none_return_does_not_sample_and_missing_activation_fails():
    tracker = custom_tracker(lambda values, state: None)
    sample_tracker(tracker, Dut())
    tracker.sample_operation("compute", {"custom": True}, "randomized")
    assert tracker.report()["status"] == "FAIL"
    assert tracker.report()["operation_sampling"][0]["samples"] == 0


def test_custom_callbacks_do_not_leak_across_test_modules():
    tracker = custom_tracker(lambda values, state: values["a"] > 5)
    sample_tracker(tracker, Dut())
    tracker.operation_monitor.bind_observers({})  # Other module doesn't own this point.
    sample_tracker(tracker, Dut())
    assert hits(tracker, "custom")["small"] == 1
    with pytest.raises(OperationSamplingError, match="missing from test module"):
        tracker.operation_monitor.bind_observers({"OPERATION_SAMPLING_BINDINGS": [custom_binding()]})


def test_custom_definition_review_includes_return_condition_and_local_helpers():
    source = f"OPERATION_SAMPLING_BINDINGS = {[custom_binding()]!r}\n" + '''
def larger(a, b):
    return a + b > 15
def observe_custom(values, state):
    if values["a"]:
        state["last"] = values["b"]
    return larger(values["a"], values["b"])
'''
    view = operation_observer_views([source])[0]
    assert "return larger" in view["source"] and "state['last']" in view["source"]
    assert "return a + b > 15" in view["helpers"][0]


@pytest.mark.parametrize("function", ["", "async def observe_custom(values, state):\n    return True",
                                     "def observe_custom(dut):\n    return True",
                                     "@decorate\ndef observe_custom(values, state):\n    return True"])
def test_custom_observer_missing_or_wrong_signature_is_preflight_repair(function):
    source = f"OPERATION_SAMPLING_BINDINGS = {[custom_binding()]!r}\n" + function
    architecture, interface = contracts()
    with pytest.raises(OperationSamplingError, match="local synchronous function"):
        operation_plan_for_tests(spec(custom_point()), [source], architecture, interface)


def test_every_operation_point_must_be_connected_even_in_known_family():
    architecture, interface = contracts()
    with pytest.raises(OperationSamplingError, match="Missing operation sampling bindings"):
        operation_plan_for_tests(spec(custom_point()), [""], architecture, interface)


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not installed")
def test_real_cocotb_automatic_operation_sampling(tmp_path):
    fixture = Path(__file__).parent / "fixtures/operation_sampling"
    architecture, interface = contracts()
    custom = point("sum_boundary", "novel_sum_boundary", "llm_extension")
    custom["bins"] = [{"name": name, "predicate": {"op": "eq", "args": [value]}, "intent": name}
                      for name, value in (("ordinary_sum", False), ("large_sum", True))]
    specs = spec(point("left_values", "operand_values"), point("right_values", "operand_values"), point("overflow", "accumulation"), custom)
    # Only the source ports present in this small combinational-adder fixture.
    interface["signals"] = [{"name": "clk", "role": "clock", "width": "1"},
                            {"name": "left", "role": "payload", "width": "4"},
                            {"name": "right", "role": "payload", "width": "4"}]
    bindings = []
    for identity, signal in (("left_values", "left"), ("right_values", "right")):
        config = binding(identity, "integer_operand", event="clock", fields={"value": {"signal": signal}}, data_type="u4")
        config.pop("channel")
        bindings.append(config)
    config = binding("overflow", "integer_add_overflow", event="clock", fields={"a": {"signal": "left"}, "b": {"signal": "right"}},
                     operand_types={"a": "u4", "b": "u4"}, result_type="u4")
    config.pop("channel")
    bindings.append(config)
    bindings.extend(extract_operation_sampling_bindings([(fixture / "test_observed_adder4.py").read_text()]))
    plan = build_operation_coverage_plan(specs, sampling_bindings=bindings, architecture=architecture, interface=interface)
    plan["monitor"] = {"clock": "clk", "signals": ["clk", "left", "right"]}
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    fixture_test = fixture / "test_observed_adder4.py"
    (tests_dir / fixture_test.name).write_text(
        install_contract_generated_block(
            fixture_test.read_text(encoding="utf-8"), plan
        ),
        encoding="utf-8",
    )
    result = run_cocotb_regression(rtl_dir=fixture, top_module="observed_adder4", tests_dir=tests_dir,
                                   reference_dir=fixture, test_modules=["test_observed_adder4"], seed=1,
                                   build_dir=tmp_path / "build", report_path=tmp_path / "simulation.json", timeout_seconds=120,
                                   coverage_plan=plan, coverage_report_path=tmp_path / "coverage.json",
                                   stimulus_ledger_report_path=tmp_path / "stimulus.json")
    assert result["status"] == "PASS", result
    coverage = json.loads((tmp_path / "coverage.json").read_text())
    assert coverage["status"] == "PASS", coverage
    assert len(coverage["operation_sampling"]) == 4
    assert all(item["origin"] == "runtime_dut_observation" and item["samples"] >= 17 for item in coverage["operation_sampling"])
    observed = next(item for item in coverage["operation_sampling"] if item["id"] == "operation.compute.sum_boundary")
    assert observed["implementation"] == "llm_custom_observer"
    assert coverage["required_bins"] == coverage["hit_bins"] == 12
