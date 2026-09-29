from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent, ContractValidationError
from multigent.agents.base import AgentRuntimeError
from multigent.intake.request_builder import build_architect_intake


def _datapath_signals() -> tuple[list[dict], list[dict]]:
    """Valid/ready/payload bindings for every fixture channel and the matching top ports.

    A ready_valid channel that carries an operation's data object but has no
    valid/ready/payload signals cannot be captured or driven, so the Architect
    validator rejects it (`missing_ready_valid_signal_roles`); the fixture is a
    complete, implementable interface, not a channel list with no wires.
    """

    signals: list[dict] = []
    ports: list[dict] = []
    for channel, direction, width in (
        ("sample_in", "input", "16"),
        ("coefficients", "input", "16"),
        ("result_out", "output", "32"),
    ):
        for role in ("valid", "ready", "payload"):
            signal_direction = direction
            if role == "ready":
                signal_direction = "output" if direction == "input" else "input"
            signal = {
                "name": f"{channel}_{role}",
                "role": role,
                "semantic_class": "data" if role == "payload" else None,
                "channel": channel,
                "direction": signal_direction,
                "width": width if role == "payload" else "1",
                "signed": role == "payload",
                "semantic": role,
                "reset_value": "0",
            }
            signals.append(signal)
            ports.append({
                **{key: signal[key] for key in ("name", "direction", "width", "signed")},
                "semantics": role,
            })
    return signals, ports


class FakeArchitectAgent(ArchitectAgent):
    """Deterministic non-GEMM fixture; values here are not project defaults."""

    def run_structured(self, **_: object) -> dict:
        return {
            "status": "READY",
            "conflicts": [],
            "architecture_contract": {
                "design": {
                    "name": "test_stream_filter",
                    "version": "0.1",
                    "description": "test-only generic streaming filter architecture",
                },
                "operations": [
                    {
                        "name": "filter",
                        "kind": "FIR",
                        "coverage_family": "fir",
                        "coverage_family_source": "novel",
                        "features": [
                            "tap_count",
                            "stream_length",
                            "coefficient_values",
                            "sample_values",
                            "numeric_behavior",
                        ],
                        "feature_extensions": [],
                        "semantics": "y[t] is the weighted sum of the current and previous samples",
                        "inputs": ["sample_stream", "coefficient_vector"],
                        "outputs": ["result_stream"],
                        "arithmetic": {
                            "classifier_profile": "llm_extension",
                            "reason": "FIR history and coefficient convolution are not implemented by the code-owned GEMM profile",
                        },
                        "lifecycle_policy": {
                            "job_acceptance": "valid_ready_handshake",
                            "job_overlap": "single_inflight",
                            "busy_behavior": "tracks_active_job",
                            "completion_style": "pulse",
                            "completion_timing": "next_cycle_after_retirement",
                            "illegal_command_behavior": "error_without_start",
                            "error_style": "pulse",
                            "error_timing": "next_cycle_after_error_event",
                            "reset_behavior": "abort_inflight",
                        },
                    }
                ],
                "data_types": [
                    {
                        "name": "sample_t",
                        "role": "stream input element",
                        "width_bits": 16,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "none",
                        "overflow_semantics": "not applicable at input",
                        "rounding_semantics": "none",
                    },
                    {
                        "name": "coefficient_t",
                        "role": "filter coefficient element",
                        "width_bits": 16,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "none",
                        "overflow_semantics": "not applicable at input",
                        "rounding_semantics": "none",
                    },
                    {
                        "name": "result_t",
                        "role": "stream output element",
                        "width_bits": 32,
                        "signed": True,
                        "representation": "two's-complement integer",
                        "conversion_semantics": "accumulated result",
                        "overflow_semantics": "wrap",
                        "rounding_semantics": "none",
                    },
                ],
                "data_objects": [
                    {
                        "name": "sample_stream",
                        "role": "external input sample sequence",
                        "data_type": "sample_t",
                        "dimensions": [],
                        "serialization": {"kind": "scalar", "index_order": [], "description": "One sample per transfer."},
                        "producer": "external",
                        "consumers": ["filter"],
                        "external": True,
                    },
                    {
                        "name": "coefficient_vector",
                        "role": "FIR coefficient set",
                        "data_type": "coefficient_t",
                        "dimensions": ["tap_count"],
                        "serialization": {"kind": "dense_tensor", "index_order": ["tap_count"], "description": "Coefficients in increasing tap index order."},
                        "producer": "external",
                        "consumers": ["filter"],
                        "external": True,
                    },
                    {
                        "name": "result_stream",
                        "role": "external filtered sample sequence",
                        "data_type": "result_t",
                        "dimensions": [],
                        "serialization": {"kind": "scalar", "index_order": [], "description": "One result per transfer."},
                        "producer": "filter",
                        "consumers": ["external"],
                        "external": True,
                    },
                ],
                "dimensions": [
                    {
                        "name": "tap_count",
                        "semantic": "number of FIR taps",
                        "minimum": 1,
                        "maximum": 16,
                        "runtime_configurable": False,
                        "bound_parameter": "TAPS",
                    }
                ],
                "parameters": [
                    {
                        "name": "TAPS",
                        "default_value": "8",
                        "legality_constraint": "1 <= TAPS <= 16",
                        "description": "number of filter taps",
                    }
                ],
                "compute": {
                    "organization": "serial multiply-accumulate datapath",
                    "dataflow": "sample history with coefficient traversal",
                    "parallelism": "one multiply-accumulate per cycle",
                    "scheduling": "iterate tap index for each accepted sample",
                },
                "storage": [
                    {
                        "name": "sample_history",
                        "stored_objects": ["sample_stream"],
                        "capacity_expression": "TAPS",
                        "capacity_at_default_parameters": 8,
                        "access_pattern": "shift/register history",
                        "port_requirements": "one insert and one indexed read",
                        "implementation_hint": "register array",
                        "reuse_semantics": "history samples reused across adjacent outputs",
                        "lifetime": "persistent across accepted samples until reset/overwrite",
                    },
                    {
                        "name": "coefficient_store",
                        "stored_objects": ["coefficient_vector"],
                        "capacity_expression": "TAPS",
                        "capacity_at_default_parameters": 8,
                        "access_pattern": "one coefficient read per MAC cycle",
                        "port_requirements": "one read port",
                        "implementation_hint": "register array",
                        "reuse_semantics": "coefficients reused across samples",
                        "lifetime": "configuration lifetime",
                    },
                ],
                "pipeline": [],
                "control": {
                    "strategy": "stream-driven FSM",
                    "state_progression": "IDLE->MAC->OUTPUT->IDLE",
                    "counters": ["tap_idx"],
                    "error_behavior": "reject invalid configuration",
                    "error_recovery": "synchronous reset returns design to IDLE",
                },
                "reset": {
                    "style": "synchronous",
                    "polarity": "active_high",
                    "required_state": "valid state cleared and history marked invalid",
                },
                "latency_model": "TAPS MAC cycles plus output handshake",
                "architectural_invariants": ["TAPS is compile-time bounded"],
                "open_assumptions": [],
            },
            "interface_contract": {
                "protocol": "ready_valid_stream",
                "clock": "clk",
                "reset": "rst",
                "channels": [
                    {
                        "name": "sample_in",
                        "direction": "input",
                        "protocol_profile": "ready_valid",
                        "purpose": "input sample stream",
                        "data_objects": ["sample_stream"],
                        "metadata": [],
                        "framing": "one sample per transfer",
                        "ordering": "in order",
                        "backpressure": "supported",
                    },
                    {
                        "name": "coefficients",
                        "direction": "input",
                        "protocol_profile": "ready_valid",
                        "purpose": "coefficient loading",
                        "data_objects": ["coefficient_vector"],
                        "metadata": ["coefficient_index"],
                        "framing": "TAPS transfers per configuration",
                        "ordering": "ascending coefficient index",
                        "backpressure": "supported",
                    },
                    {
                        "name": "result_out",
                        "direction": "output",
                        "protocol_profile": "ready_valid",
                        "purpose": "filtered output stream",
                        "data_objects": ["result_stream"],
                        "metadata": [],
                        "framing": "one result per transfer",
                        "ordering": "in order",
                        "backpressure": "supported",
                    },
                ],
                "signals": [
                    {
                        "name": "clk",
                        "role": "clock",
                        "semantic_class": None,
                        "channel": None,
                        "direction": "input",
                        "width": "1",
                        "signed": False,
                        "semantic": "rising-edge clock",
                        "reset_value": "not applicable",
                    },
                    {
                        "name": "rst",
                        "role": "reset",
                        "semantic_class": None,
                        "channel": None,
                        "direction": "input",
                        "width": "1",
                        "signed": False,
                        "semantic": "synchronous active-high reset",
                        "reset_value": "not applicable",
                    },
                    *_datapath_signals()[0],
                ],
                "global_handshake_rules": {
                    "transfer_condition": "valid && ready",
                    "stall_behavior": "payload remains stable while stalled",
                },
            },
            "module_manifest": {
                "top": "filter_top",
                "modules": [
                    {
                        "name": "filter_top",
                        "responsibility": "top-level integration",
                        "dependencies": ["filter_core"],
                        "parameters": ["TAPS"],
                        "stateful": True,
                        "ports": [
                            {"name":"clk", "direction":"input", "width":"1", "signed":False, "semantics":"rising-edge clock"},
                            {"name":"rst", "direction":"input", "width":"1", "signed":False, "semantics":"active-high reset"},
                            *_datapath_signals()[1],
                        ],
                    },
                    {
                        "name": "filter_core",
                        "responsibility": "FIR datapath and control",
                        "dependencies": [],
                        "parameters": ["TAPS"],
                        "stateful": True,
                        "ports": [{"name":"clk", "direction":"input", "width":"1", "signed":False, "semantics":"rising-edge clock"}],
                    },
                ],
            },
            "acceptance_criteria": {
                "functional": ["matches independent FIR reference"],
                "verification": ["random regression"],
                "rtl": ["synthesizable SystemVerilog"],
                "fpga_handoff": ["verified RTL package"],
            },
        }


def architect_schema() -> dict:
    return ArchitectAgent().load_output_schema(ARCHITECT_OUTPUT_SCHEMA)


def test_generic_non_gemm_output_satisfies_architect_schema() -> None:
    Draft202012Validator(architect_schema()).validate(
        FakeArchitectAgent().run_structured()
    )


def test_architect_novel_operation_features_are_explicit_and_nonempty() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["features"] = []
    with pytest.raises(AgentRuntimeError, match="at least one feature"):
        ArchitectAgent._validate_contract_references(result)

    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["features"].append(
        "invented_feature"
    )
    ArchitectAgent._validate_contract_references(result)

    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["feature_extensions"] = [
        "coefficient_reload_during_stream"
    ]
    ArchitectAgent._validate_contract_references(result)


def test_dimension_maximum_must_be_concrete_integer() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["dimensions"][0]["maximum"] = ","
    with pytest.raises(ValidationError):
        Draft202012Validator(architect_schema()).validate(result)


def test_intake_keeps_architecture_choices_out_of_user_input() -> None:
    request = "design a 16-bit streaming FIR accelerator with 8 taps"
    intake = build_architect_intake(request)

    assert intake["user_request"] == request
    assert intake["provenance"]["user_supplied_fields"] == ["user_request"]
    assert intake["project_constraints"]["rtl_constraints"]["language"] == "SystemVerilog"
    assert intake["project_constraints"]["verification_policy"]["randomized_transactions_minimum"] == 100
    assert intake["project_constraints"]["synthesis_policy"]["provider"] == "vivado"
    assert "owner" not in intake["project_constraints"]["synthesis_policy"]

    decisions = intake["architect_must_decide_when_unspecified"]
    assert "operation_semantics" in decisions
    assert "data_type_semantics" in decisions
    assert "legal_runtime_bounds" in decisions
    assert "compile_time_parameters" in decisions
    assert "compute_organization" in decisions
    assert "storage_and_reuse" in decisions
    assert "interface_protocol" in decisions
    assert "reset_style" in decisions


def test_architect_loads_role_technical_context_only() -> None:
    instructions = FakeArchitectAgent().load_instructions()
    assert "# ARCHITECT TECHNICAL SKILL" in instructions
    assert "external_team_member" not in instructions
    assert "Artifact Ownership" not in instructions
    assert "Do not assume GEMM" in instructions


def test_architect_writes_only_architecture_artifacts(tmp_path: Path) -> None:
    architecture_dir = tmp_path / "architecture"
    agent = FakeArchitectAgent()
    result = agent.run(
        "design a 16-bit streaming FIR accelerator with 8 taps",
        output_dir=architecture_dir,
        run_id="unit",
    )

    assert result["status"] == "READY"
    assert sorted(path.name for path in architecture_dir.iterdir()) == [
        "acceptance_criteria.yaml",
        "architect_result.json",
        "architecture_contract.yaml",
        "interface_contract.yaml",
        "module_manifest.json",
    ]

    intake_path = tmp_path / "specs" / "request-unit.yaml"
    assert intake_path.is_file()
    intake = yaml.safe_load(intake_path.read_text(encoding="utf-8"))
    assert intake["provenance"]["user_supplied_fields"] == ["user_request"]
    assert "owner" not in intake["project_constraints"]["synthesis_policy"]

    contract = yaml.safe_load(
        (architecture_dir / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    assert contract["design"]["name"] == "test_stream_filter"
    assert contract["parameters"][0]["name"] == "TAPS"
    assert not list(architecture_dir.glob("*.sv"))


def test_semantic_validator_rejects_unknown_data_object() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["inputs"].append("missing_object")
    with pytest.raises(AgentRuntimeError, match="unknown data object"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_unknown_module_parameter() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["module_manifest"]["modules"][0]["parameters"].append("MISSING_PARAM")
    with pytest.raises(AgentRuntimeError, match="unknown parameter"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_nonreciprocal_producer() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["outputs"] = []
    with pytest.raises(AgentRuntimeError, match="does not list result_stream as an output"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_nonreciprocal_consumer() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["operations"][0]["inputs"].remove("sample_stream")
    with pytest.raises(AgentRuntimeError, match="does not list sample_stream as an input"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_unexposed_external_object() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["interface_contract"]["channels"] = [
        channel
        for channel in result["interface_contract"]["channels"]
        if channel["name"] != "coefficients"
    ]
    with pytest.raises(AgentRuntimeError, match="not carried by any interface channel"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_bound_default_outside_dimension_range() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["architecture_contract"]["parameters"][0]["default_value"] = "32"
    with pytest.raises(AgentRuntimeError, match="lies outside"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_unknown_signal_role() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["interface_contract"]["signals"][0]["role"] = "clockish"
    with pytest.raises(AgentRuntimeError, match="unknown role"):
        ArchitectAgent._validate_contract_references(result)


def test_semantic_validator_rejects_channel_role_without_channel() -> None:
    result = copy.deepcopy(FakeArchitectAgent().run_structured())
    result["interface_contract"]["signals"].append(
        {
            "name": "sample_valid",
            "role": "valid",
            "semantic_class": None,
            "channel": None,
            "direction": "input",
            "width": "1",
            "signed": False,
            "semantic": "sample transfer is available",
            "reset_value": "0",
        }
    )
    result["module_manifest"]["modules"][0]["ports"].append(
        {
            "name": "sample_valid",
            "direction": "input",
            "width": "1",
            "signed": False,
            "semantics": "sample transfer is available",
        }
    )
    with pytest.raises(AgentRuntimeError, match="requires a channel"):
        ArchitectAgent._validate_contract_references(result)


def test_architect_prompt_contains_external_signal_role_taxonomy() -> None:
    task = ArchitectAgent._build_architecture_task(
        build_architect_intake("design a streaming accelerator")
    )
    assert "SIGNAL ROLE TAXONOMY" in task
    assert "- valid:" in task
    assert "- completion:" in task
    assert "Never infer any of these fields" in task


def test_architect_effective_schema_requires_pool_selection_without_copying_enums():
    from multigent.verifier_tool import (
        lifecycle_policy_schema,
        reset_channel_policies_schema,
        with_lifecycle_policy_schema,
    )

    base = json.loads(ARCHITECT_OUTPUT_SCHEMA.read_text(encoding="utf-8"))
    before = copy.deepcopy(base)
    schema = ArchitectAgent().load_output_schema(ARCHITECT_OUTPUT_SCHEMA)
    operation = schema["properties"]["architecture_contract"]["properties"]["operations"]["items"]
    assert "lifecycle_policy" in operation["required"]
    assert operation["properties"]["lifecycle_policy"] == lifecycle_policy_schema()
    assert (
        schema["properties"]["interface_contract"]["properties"][
            "reset_channel_policies"
        ]
        == {
            **reset_channel_policies_schema(),
            "description": (
                "Optional explicit reset behavior for generic ready_valid or custom "
                "channels. Standard AXI-family channels already receive their "
                "standard-owned reset rules and must not be listed here."
            ),
        }
    )
    assert base == before
    assert with_lifecycle_policy_schema(schema) == schema
    patch_schema = ARCHITECT_OUTPUT_SCHEMA.with_name("architect_revision_patch.schema.json")
    assert ArchitectAgent().load_output_schema(patch_schema) == json.loads(patch_schema.read_text())


@pytest.mark.parametrize("invalid_policy", [None, {}, {"error_style": "pulse"}])
def test_new_architect_output_rejects_incomplete_lifecycle_policy(invalid_policy):
    result = FakeArchitectAgent().run_structured()
    operation = result["architecture_contract"]["operations"][0]
    operation["lifecycle_policy"] = invalid_policy
    with pytest.raises(ValidationError):
        Draft202012Validator(architect_schema()).validate(result)
    with pytest.raises(AgentRuntimeError, match="lifecycle_policy"):
        ArchitectAgent._validate_contract_references(result, require_lifecycle_policy=True)


def test_new_architect_cannot_drop_policy_even_if_transport_validation_is_bypassed(tmp_path):
    class MissingPolicyArchitect(FakeArchitectAgent):
        def run_structured(self, **kwargs):
            result = super().run_structured(**kwargs)
            result["architecture_contract"]["operations"][0].pop("lifecycle_policy")
            return result

    with pytest.raises(AgentRuntimeError, match="lifecycle_policy is required"):
        MissingPolicyArchitect().run("streaming FIR", output_dir=tmp_path / "architecture")
    assert not (tmp_path / "architecture" / "architect_result.json").exists()


@pytest.mark.parametrize("api_mode", ["responses", "chat_completions"])
def test_architect_sends_effective_policy_schema_and_retries_incomplete_policy(
    api_mode, tmp_path, monkeypatch,
):
    from multigent.agents import base as base_module
    from multigent.verifier_tool import build_architect_operation_metadata, lifecycle_policy_schema

    good = FakeArchitectAgent().run_structured()
    bad = copy.deepcopy(good)
    bad["architecture_contract"]["operations"][0]["lifecycle_policy"].pop("error_style")
    outputs = iter([bad, good])
    requests = []

    def create(**request):
        requests.append(request)
        content = json.dumps(next(outputs))
        if api_mode == "responses":
            return SimpleNamespace(output_text=content, status="completed")
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason="stop"
        )])

    client = SimpleNamespace(
        responses=SimpleNamespace(create=create),
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
    )
    monkeypatch.setattr(base_module, "WORKSPACE_ROOT", tmp_path)
    agent = ArchitectAgent(api_mode=api_mode)
    monkeypatch.setattr(agent, "_client", lambda: client)
    result = agent.run("streaming FIR", output_dir=tmp_path / "architecture", run_id="policy")
    assert result == good
    assert len(requests) == 2
    for request in requests:
        schema = (
            request["text"]["format"]["schema"] if api_mode == "responses"
            else request["response_format"]["json_schema"]["schema"]
        )
        operation = schema["properties"]["architecture_contract"]["properties"]["operations"]["items"]
        assert "lifecycle_policy" in operation["required"]
        assert operation["properties"]["lifecycle_policy"] == lifecycle_policy_schema()
        assert "arithmetic" in operation["required"]
        objects = schema["properties"]["architecture_contract"]["properties"]["data_objects"]["items"]
        assert "serialization" in objects["required"]
    trace = json.loads((tmp_path / "logs/agent_traces/architect-policy.json").read_text())
    assert trace["successful_attempt"] == 2
    assert "error_style" in trace["attempts"][0]["parse_error"]
    assert trace["schema_sha256"] == hashlib.sha256(
        json.dumps(agent.load_output_schema(ARCHITECT_OUTPUT_SCHEMA), sort_keys=True).encode()
    ).hexdigest()
    saved = yaml.safe_load((tmp_path / "architecture/architecture_contract.yaml").read_text())
    metadata = build_architect_operation_metadata(saved, result["interface_contract"])
    assert metadata["operations"][0]["lifecycle"]["policy_source"] == "explicit_contract"
    assert metadata["operations"][0]["lifecycle"]["policy"] == saved["operations"][0]["lifecycle_policy"]


@pytest.mark.parametrize("legacy", [False, True])
def test_architect_revision_validates_policy_and_rejects_undeclared_legacy_contracts(
    legacy, tmp_path, monkeypatch,
):
    from multigent.orchestration.architect_node import _run_architect_revision

    previous = FakeArchitectAgent().run_structured()
    if legacy:
        previous["architecture_contract"]["operations"][0].pop("lifecycle_policy")
    output = tmp_path / "architecture"
    output.mkdir()
    (output / "architect_result.json").write_text(json.dumps(previous))
    agent = ArchitectAgent()
    monkeypatch.setattr(agent, "run_structured", lambda **_: {
        "status": "CONTRACT_CONFIRMED", "edits": [], "issue": "existing behavior is unambiguous"
    })
    if legacy:
        with pytest.raises(ContractValidationError, match="lifecycle_policy is required"):
            _run_architect_revision(
                agent, user_request="streaming FIR", feedback={"issue": "status behavior"},
                output_dir=output, run_id="policy-r1",
            )
        assert json.loads((output / "architect_result.json").read_text()) == previous
    else:
        result = _run_architect_revision(
            agent, user_request="streaming FIR", feedback={"issue": "status behavior"},
            output_dir=output, run_id="policy-r1",
        )
        assert result == previous


def test_architect_revision_rejects_unknown_policy_before_persisting(tmp_path, monkeypatch):
    from multigent.orchestration.architect_node import _run_architect_revision

    previous = FakeArchitectAgent().run_structured()
    output = tmp_path / "architecture"
    output.mkdir()
    (output / "architect_result.json").write_text(json.dumps(previous))
    agent = ArchitectAgent()
    monkeypatch.setattr(agent, "run_structured", lambda **_: {
        "status": "PATCH_READY", "issue": "completion style", "edits": [{
            "op": "replace",
            "path": "/architecture_contract/operations/name=filter/lifecycle_policy/completion_style",
            "value_json": json.dumps("unimplemented"), "reason": "completion style feedback",
        }],
    })
    with pytest.raises(AgentRuntimeError, match="schema-invalid"):
        _run_architect_revision(
            agent, user_request="streaming FIR", feedback={"issue": "completion style"},
            output_dir=output, run_id="policy-r1",
        )
    assert json.loads((output / "architect_result.json").read_text()) == previous
