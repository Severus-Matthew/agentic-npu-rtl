"""Ten deliberately diverse local extension scenarios.

These are not a list of features chosen because the tool already supports
them.  The matrix mixes compositional GEMM post-operations, wholly LLM-owned
    math, custom APB-like and credit-based behavior, contract-local vocabulary, lifecycle
replacement/addition, and a three-domain contract.  Every extension case
crosses the same Architect request -> Verifier bundle -> inert manifest
boundary without calling an external model.
"""

from __future__ import annotations

from copy import deepcopy
import re

from jsonschema import Draft202012Validator

from multigent.tests.test_canonical_operation import axi_lite_contracts, contracts
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_feature_extension_manifest,
    build_lifecycle_feature_plan,
    evaluate_canonical_operation,
    extension_bundle_schema,
    extension_request_schema,
    interface_vocabulary_extensions,
    render_requested_extension_worklist,
    validate_architect_extension_requests,
    validate_interface_semantics,
    validate_interface_signal_roles,
    validate_verifier_extension_bundles,
)
from multigent.verifier_tool.pool.feature_plans import (
    build_operation_feature_plan,
    build_protocol_feature_plan,
)


def _request(
    identity: str,
    domain: str,
    feature_name: str,
    target: dict,
    *,
    observations: tuple[str, ...],
    related: tuple[str, ...] = (),
    replacements: tuple[str, ...] = (),
    vocabulary: dict | None = None,
) -> dict:
    request = {
        "id": identity,
        "domain": domain,
        "feature_name": feature_name,
        "target": target,
        "semantics": {
            "summary": f"Contract-local semantics for {feature_name}.",
            "trigger": f"The {feature_name} scenario begins.",
            "required_behavior": [
                f"Observed behavior follows the frozen {feature_name} contract."
            ],
            "end_condition": f"The {feature_name} scenario reaches its terminal state.",
            "forbidden_behavior": [
                f"No unrelated built-in feature is replaced by {feature_name}."
            ],
        },
        "reason": f"The closed {domain} pool does not define {feature_name}.",
        "parameters": {"scenario_version": 1},
        "required_observations": [
            {
                "name": name,
                "kind": "golden_trace" if name == "golden_trace" else "signal",
                "description": f"Evidence input {name} for {feature_name}.",
            }
            for name in observations
        ],
        "related_builtin_features": list(related),
    }
    if replacements:
        request["replaces_contract_paths"] = list(replacements)
    if vocabulary is not None:
        request["contract_vocabulary"] = vocabulary
    return request


def _bundle_and_source(request: dict) -> tuple[dict, dict]:
    slug = re.sub(r"[^a-z0-9_]", "_", request["id"])
    path = f"tests/test_extension_{slug}.py"
    symbols = {
        "assertion": f"check_{slug}",
        "coverage": f"sample_{slug}",
        "stimulus": f"drive_{slug}",
    }
    implementation = {
        "kind": "verifier_python",
        "name": request["feature_name"],
        "file": path,
    }
    bundle = {
        "schema_version": 1,
        "request_id": request["id"],
        "id": request["id"],
        "domain": request["domain"],
        "feature_name": request["feature_name"],
        "target": deepcopy(request["target"]),
        "description": f"Contract-local implementation for {request['feature_name']}.",
        "bindings": {
            item["name"]: f"bound_{item['name']}"
            for item in request["required_observations"]
        },
        "reuse": {
            "based_on_features": list(request.get("related_builtin_features", [])),
            "helpers": ["contract_snapshot"],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": symbols["assertion"]},
            "parameters": deepcopy(request.get("parameters", {})),
        },
        "coverage": {
            "implementation": {**implementation, "symbol": symbols["coverage"]},
            "parameters": deepcopy(request.get("parameters", {})),
            "bins": [
                {
                    "name": "contract_case",
                    "intent": "Observe the requested contract-local behavior.",
                    "predicate": {"observed": True},
                }
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": symbols["stimulus"]},
            "parameters": deepcopy(request.get("parameters", {})),
            "scenarios": [
                {
                    "name": "directed_contract_case",
                    "intent": "Drive the requested contract-local behavior.",
                    "parameters": deepcopy(request.get("parameters", {})),
                }
            ],
        },
    }
    source = {
        "path": path,
        "purpose": f"Local scenario implementation for {request['id']}",
        "categories": [request["domain"]],
        "content": f'''import cocotb
from cocotb.triggers import RisingEdge

def {symbols["assertion"]}(snapshot, state):
    assert snapshot["observed"] == snapshot["expected"]

def {symbols["coverage"]}(snapshot, state):
    return {{"matched": snapshot["observed"] == snapshot["expected"]}}

async def {symbols["stimulus"]}(dut):
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_{slug}(dut):
    snapshot = {{"expected": 0, "observed": 0}}
    state = {{}}
    {symbols["assertion"]}(snapshot, state)
    {symbols["coverage"]}(snapshot, state)
    await {symbols["stimulus"]}(dut)
''',
    }
    return bundle, source


def _round_trip(architecture: dict, interface: dict) -> dict:
    requests = list(architecture.get("verification_extensions", []))
    bundles: list[dict] = []
    sources: list[dict] = []
    for request in requests:
        Draft202012Validator(extension_request_schema()).validate(request)
        bundle, source = _bundle_and_source(request)
        Draft202012Validator(extension_bundle_schema()).validate(bundle)
        bundles.append(bundle)
        sources.append(source)

    assert validate_architect_extension_requests(architecture, interface) == []
    assert validate_verifier_extension_bundles(
        architecture, bundles, source_files=sources
    ) == []
    manifest = build_feature_extension_manifest(
        architecture, bundles, source_files=sources
    )
    assert manifest["status"] == "contract_local_only"
    assert manifest["promotion"] == "not_implemented"
    assert {item["request"]["id"] for item in manifest["entries"]} == {
        item["id"] for item in requests
    }
    worklist = render_requested_extension_worklist(architecture)
    assert all(item["id"] in worklist for item in requests)
    return manifest


def _append_formula_stage(
    architecture: dict, name: str, formula: str, *, predecessor: str = "activated"
) -> None:
    arithmetic = architecture["operations"][0]["arithmetic"]
    arithmetic["post_operations"][name] = {
        "kind": "llm_defined",
        "depends_on": [predecessor],
        "formula": formula,
    }
    arithmetic["post_output"] = name


def _lifecycle_request(field: str, feature_name: str) -> dict:
    identity = f"lifecycle.{feature_name}"
    return _request(
        identity,
        "lifecycle",
        feature_name,
        {"scope": "operation", "name": "gemm_core"},
        observations=("lifecycle_event",),
        related=(f"lifecycle.{field}",),
        replacements=(f"/operations/gemm_core/lifecycle_policy/{field}",),
    )


def test_case_01_gemm_saturating_quantization_keeps_tool_owned_golden() -> None:
    architecture, interface = contracts()
    _append_formula_stage(architecture, "quantized", "clip(value, -128, 127)")
    request = _request(
        "operation.saturating_quantization",
        "operation",
        "saturating_quantization",
        {"scope": "operation", "name": "gemm_core"},
        observations=("golden_trace", "observed_output"),
        related=("operation.matrix_multiply.accumulation",),
    )
    architecture["verification_extensions"] = [request]

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    operation = metadata["operations"][0]
    assert metadata["unrepresentable_operations"] == []
    assert evaluate_canonical_operation(
        operation,
        {"A_matrix": [127], "B_matrix": [127], "bias_vector": [0]},
    ) == {"Y_matrix": [127]}


def test_case_02_gemm_two_new_dag_stages_preserve_composition_order() -> None:
    architecture, interface = contracts()
    arithmetic = architecture["operations"][0]["arithmetic"]
    arithmetic["post_operations"]["absolute"] = {
        "kind": "llm_defined",
        "depends_on": ["wrapped"],
        "formula": "abs(value)",
    }
    arithmetic["post_operations"]["scaled"] = {
        "kind": "llm_defined",
        "depends_on": ["absolute"],
        "formula": "value * 3",
    }
    arithmetic["post_operations"]["activated"]["depends_on"] = ["scaled"]
    request = _request(
        "operation.absolute_scaled_activation",
        "operation",
        "absolute_scaled_activation",
        {"scope": "operation", "name": "gemm_core"},
        observations=("golden_trace", "observed_output"),
        related=("operation.matrix_multiply.activation",),
    )
    architecture["verification_extensions"] = [request]

    _round_trip(architecture, interface)
    operation = build_architect_operation_metadata(
        architecture, interface
    )["operations"][0]
    assert operation["arithmetic"]["resolved_stage_order"] == [
        "bias", "wrapped", "absolute", "scaled", "activated"
    ]
    assert evaluate_canonical_operation(
        operation,
        {"A_matrix": [1], "B_matrix": [1], "bias_vector": [-5]},
    ) == {"Y_matrix": [12]}


def test_case_03_wholly_unknown_math_keeps_protocol_and_lifecycle_automation() -> None:
    architecture, interface = axi_lite_contracts()
    operation_contract = architecture["operations"][0]
    operation_contract["arithmetic"] = {
        "classifier_profile": "llm_extension",
        "reason": "Stochastic quantization is not in the closed formula grammar.",
    }
    operation_contract["semantics"] = "GEMM followed by stochastic quantization."
    request = _request(
        "operation.stochastic_quantization",
        "operation",
        "stochastic_quantization",
        {"scope": "operation", "name": "gemm_core"},
        observations=("accepted_inputs", "observed_output"),
        related=("operation.matrix_multiply.accumulation",),
    )
    architecture["verification_extensions"] = [request]

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    lifecycle_plan = build_lifecycle_feature_plan(interface, metadata)
    assert lifecycle_plan["features"]
    assert lifecycle_plan["coverage_obligations"]
    assert build_protocol_feature_plan(interface)["features"]
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["gemm_core"]["protocol_lifecycle_supported"] is True
    assert support["any_operation_supported"] is True


def test_case_04_apb_wait_state_behavior_uses_a_local_protocol_extension() -> None:
    interface = {
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {
                "name": "apb_write",
                "direction": "output",
                "protocol_profile": "custom",
                "data_objects": [],
                "ordering": "single outstanding transfer",
                "framing": "setup then access phase",
            }
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {
                "name": "rst_n", "role": "reset", "direction": "input", "channel": None,
                "semantic": "synchronous active-low reset",
            },
            {"name": "psel", "role": "valid", "direction": "output", "channel": "apb_write"},
            {"name": "pready", "role": "ready", "direction": "input", "channel": "apb_write"},
            {
                "name": "paddr", "role": "metadata", "semantic_class": "address",
                "direction": "output", "channel": "apb_write", "width": "32",
            },
            {
                "name": "penable", "role": "metadata", "semantic_class": "configuration",
                "direction": "output", "channel": "apb_write", "width": "1",
            },
            {
                "name": "pwdata", "role": "payload", "semantic_class": "data",
                "direction": "output", "channel": "apb_write", "width": "32",
            },
        ],
    }
    request = _request(
        "protocol.apb_bounded_wait_state",
        "protocol",
        "apb_bounded_wait_state",
        {"scope": "channel", "name": "apb_write"},
        observations=("psel", "penable", "pready"),
        related=(),
    )
    architecture = {"operations": [], "verification_extensions": [request]}

    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []
    _round_trip(architecture, interface)


def test_case_05_credit_starvation_and_recovery_crosses_two_channels() -> None:
    interface = {
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {
                "name": "data_tx", "direction": "output",
                "protocol_profile": "custom", "data_objects": [],
                "ordering": "in order", "framing": "one flit",
            },
            {
                "name": "credit_rx", "direction": "input",
                "protocol_profile": "custom", "data_objects": [],
                "ordering": "in order", "framing": "one credit update",
            },
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {
                "name": "rst_n", "role": "reset", "direction": "input", "channel": None,
                "semantic": "synchronous active-low reset",
            },
            {"name": "tx_valid", "role": "valid", "direction": "output", "channel": "data_tx"},
            {"name": "tx_ready", "role": "ready", "direction": "input", "channel": "data_tx"},
            {
                "name": "tx_data", "role": "payload", "semantic_class": "data",
                "direction": "output", "channel": "data_tx", "width": "64",
            },
            {"name": "credit_valid", "role": "valid", "direction": "input", "channel": "credit_rx"},
            {"name": "credit_ready", "role": "ready", "direction": "output", "channel": "credit_rx"},
            {
                "name": "credit_count", "role": "payload", "semantic_class": "credit",
                "direction": "input", "channel": "credit_rx", "width": "4",
            },
        ],
    }
    request = _request(
        "protocol.credit_starvation_recovery",
        "protocol",
        "credit_starvation_recovery",
        {"scope": "interface", "name": "interface"},
        observations=("tx_valid", "credit_count"),
        related=("protocol.flow_control",),
    )
    architecture = {"operations": [], "verification_extensions": [request]}

    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []
    _round_trip(architecture, interface)


def test_case_06_new_sideband_semantic_class_joins_known_stall_content() -> None:
    architecture, interface = contracts()
    interface["clock"] = "clk"
    interface["reset"] = "rst_n"
    interface["signals"][:0] = [
        {"name": "clk", "role": "clock", "direction": "input", "channel": None},
        {
            "name": "rst_n", "role": "reset", "direction": "input", "channel": None,
            "semantic": "synchronous active-low reset",
        },
    ]
    channel_directions = {
        item["name"]: item["direction"] for item in interface["channels"]
    }
    for signal in interface["signals"]:
        channel = signal.get("channel")
        if not channel:
            continue
        direction = channel_directions[channel]
        if signal["role"] == "ready":
            direction = "output" if direction == "input" else "input"
        signal["direction"] = direction
        if signal["role"] == "payload":
            signal["semantic_class"] = "data"
    interface["signals"].append(
        {
            "name": "a_lane_epoch",
            "role": "metadata",
            "semantic_class": "lane_epoch",
            "direction": "input",
            "channel": "a",
            "width": "4",
        }
    )
    request = _request(
        "protocol.lane_epoch_sideband",
        "protocol",
        "lane_epoch_sideband",
        {"scope": "signal", "name": "a_lane_epoch"},
        observations=("lane_epoch",),
        related=("stall_stability",),
        vocabulary={
            "pool": "semantic_class",
            "name": "lane_epoch",
            "definition": {
                "description": "Epoch tag selecting the logical accelerator lane generation.",
                "coverage_tags": ["epoch_partition", "stall_stability"],
                "allowed_roles": ["metadata"],
            },
        },
    )
    architecture["verification_extensions"] = [request]
    role_extensions, semantic_extensions = interface_vocabulary_extensions(architecture)

    assert validate_interface_signal_roles(
        interface, role_extensions=role_extensions
    ) == []
    assert validate_interface_semantics(
        interface,
        role_extensions=role_extensions,
        semantic_class_extensions=semantic_extensions,
    ) == []
    _round_trip(architecture, interface)
    stall = next(
        item
        for item in build_protocol_feature_plan(interface)["features"]
        if item["id"] == "channel.a.stall_stability"
    )
    assert "a_lane_epoch" in stall["bindings"]["content"]


def test_case_07_three_cycle_error_replaces_only_error_style() -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_request("error_style", "error_three_cycle_pulse")
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["error_style"] = {
        "extension_request": request["id"]
    }

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    kinds = {
        item["kind"] for item in build_lifecycle_feature_plan(interface, metadata)["features"]
    }
    assert "illegal_command_errors_without_start" not in kinds
    assert "busy_tracks_active_job" in kinds
    assert "completion_matches_final_output" in kinds


def test_case_08_delayed_completion_requires_an_explicit_policy_sentinel() -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_request("completion_timing", "completion_after_four_cycles")
    architecture["verification_extensions"] = [request]

    errors = validate_architect_extension_requests(architecture, interface)
    assert any("does not reference the request" in error for error in errors)

    architecture["operations"][0]["lifecycle_policy"]["completion_timing"] = {
        "extension_request": request["id"]
    }
    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    kinds = {
        item["kind"] for item in build_lifecycle_feature_plan(interface, metadata)["features"]
    }
    assert "completion_matches_final_output" not in kinds
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["gemm_core"]["protocol_lifecycle_supported"] is False
    assert support["any_operation_supported"] is False


def test_case_09_additive_watchdog_interrupt_preserves_builtin_lifecycle() -> None:
    architecture, interface = axi_lite_contracts()
    interface["signals"].append(
        {
            "name": "watchdog_irq", "role": "interrupt", "direction": "output",
            "channel": None, "reset_value": "0",
        }
    )
    request = _request(
        "lifecycle.watchdog_interrupt",
        "lifecycle",
        "watchdog_interrupt",
        {"scope": "operation", "name": "gemm_core"},
        observations=("watchdog_irq", "lifecycle_event"),
        related=("lifecycle.busy_behavior",),
    )
    architecture["verification_extensions"] = [request]
    baseline_architecture, baseline_interface = axi_lite_contracts()

    assert validate_interface_signal_roles(interface) == []
    _round_trip(architecture, interface)
    plan = build_lifecycle_feature_plan(
        interface, build_architect_operation_metadata(architecture, interface)
    )
    baseline = build_lifecycle_feature_plan(
        baseline_interface,
        build_architect_operation_metadata(baseline_architecture, baseline_interface),
    )
    assert {
        item["kind"] for item in plan["features"] if item["scope"] == "operation"
    } == {
        item["kind"] for item in baseline["features"] if item["scope"] == "operation"
    }


def test_case_10_three_domain_mix_resolves_compiled_protocol_group() -> None:
    architecture, interface = axi_lite_contracts()
    _append_formula_stage(architecture, "binary_output", "value != 0")
    operation_request = _request(
        "operation.binary_output_partition",
        "operation",
        "binary_output_partition",
        {"scope": "operation", "name": "gemm_core"},
        observations=("golden_trace", "observed_output"),
        related=("operation.matrix_multiply.activation",),
    )
    protocol_request = _request(
        "protocol.axi_retry_budget",
        "protocol",
        "axi_retry_budget",
        {"scope": "protocol_group", "name": "mem"},
        observations=("response_code", "lifecycle_event"),
        related=("axi_lite_response_code",),
    )
    lifecycle_request = _lifecycle_request(
        "reset_behavior", "resume_inflight_after_reset"
    )
    architecture["operations"][0]["lifecycle_policy"]["reset_behavior"] = {
        "extension_request": lifecycle_request["id"]
    }
    architecture["verification_extensions"] = [
        operation_request,
        protocol_request,
        lifecycle_request,
    ]

    manifest = _round_trip(architecture, interface)
    assert {item["request"]["domain"] for item in manifest["entries"]} == {
        "operation", "protocol", "lifecycle"
    }
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    assert build_operation_feature_plan(architecture)["features"]
    assert build_protocol_feature_plan(interface)["features"]
    lifecycle_kinds = {
        item["kind"] for item in build_lifecycle_feature_plan(interface, metadata)["features"]
    }
    assert "reset_aborts_pending_job" not in lifecycle_kinds
    assert "busy_tracks_active_job" in lifecycle_kinds
