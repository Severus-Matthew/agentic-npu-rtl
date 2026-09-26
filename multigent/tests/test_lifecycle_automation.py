from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import yaml

from multigent.agents.verifier import VerifierAgent
from multigent.tests.test_canonical_operation import contracts as explicit_gemm_contracts
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    build_lifecycle_assertion_plan,
    build_lifecycle_coverage_plan,
    build_lifecycle_stimulus_plan,
    check_lifecycle_assertions,
    compile_verification_manifest,
    finalize_lifecycle_assertions,
    render_contract_generated_block,
    synthesize_code_owned_operation_coverage,
)
from multigent.verifier_tool.orchestration import campaign as campaign_module


_FROZEN = (
    Path(__file__).parents[1]
    / "runs"
    / "taxonomy-v2-30trial-20260917"
    / "frozen-architecture"
)


def _contracts() -> tuple[dict, dict]:
    architecture = yaml.safe_load(
        (_FROZEN / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (_FROZEN / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    # Explicit fixture migration only; production must reject the old contract.
    declared, _ = explicit_gemm_contracts()
    for field in ("arithmetic", "lifecycle_policy"):
        architecture["operations"][0][field] = copy.deepcopy(declared["operations"][0][field])
    architecture["operations"][0]["lifecycle_policy"]["error_style"] = "pulse"
    architecture["data_types"].append(copy.deepcopy(declared["data_types"][2]))
    for obj, template in zip(architecture["data_objects"], declared["data_objects"], strict=True):
        assert obj["name"] == template["name"]
        obj["serialization"] = copy.deepcopy(template["serialization"])
    return architecture, interface


def _context() -> dict:
    frozen = json.loads(
        (_FROZEN / "architect_result.json").read_text(encoding="utf-8")
    )
    frozen["architecture_contract"], frozen["interface_contract"] = _contracts()
    return {
        "user_request": "frozen GEMM verification",
        "frozen_architecture": frozen,
        "verification_policy": {
            "randomized_transactions_minimum": 100,
            "regression_wall_timeout_seconds_minimum": 120,
            "require_completion_behavior_tests_when_defined": True,
            "require_error_behavior_tests_when_defined": True,
        },
    }


def test_command_legality_is_machine_resolved_without_signal_name_guessing() -> None:
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    command = metadata["operations"][0]["lifecycle"]["job_accept_channels"][0]
    assert command["signals"] == {
        "valid": "cmd_valid",
        "ready": "cmd_ready",
        "payload": "cmd_payload",
    }
    assert command["legal_values"] == [1]
    assert command["illegal_value"] == 0
    assert command["legality_resolution"] == "machine_parsed_contract_semantic"


def test_command_legal_only_and_multiple_metadata_fields_are_preserved() -> None:
    architecture, interface = _contracts()
    interface = copy.deepcopy(interface)
    payload = next(item for item in interface["signals"] if item["name"] == "cmd_payload")
    payload["semantic"] = "legal only 8'h01"
    for signal, data_object in (
        ("ptr_left", "A_matrix"),
        ("ptr_right", "B_matrix"),
        ("ptr_bias", "bias_vector"),
        ("ptr_result", "Y_matrix"),
    ):
        interface["signals"].append(
            {
                "name": signal,
                "channel": "cmd_chan",
                "role": "metadata",
                "semantic_class": "address",
                "direction": "input",
                "width": "32",
                "signed": False,
                "semantic": (
                    f"base pointer; data_object={data_object}; address_role=base"
                ),
            }
        )
    command = build_architect_operation_metadata(
        architecture, interface
    )["operations"][0]["lifecycle"]["job_accept_channels"][0]
    assert command["legal_values"] == [1]
    assert command["signals"] == {
        "valid": "cmd_valid",
        "ready": "cmd_ready",
        "payload": "cmd_payload",
    }
    assert {
        item["data_object"]: item["signal"]
        for item in command["metadata_fields"]
    } == {
        "A_matrix": "ptr_left",
        "B_matrix": "ptr_right",
        "bias_vector": "ptr_bias",
        "Y_matrix": "ptr_result",
    }


def test_lifecycle_owns_reset_command_status_abort_and_purity_coverage() -> None:
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    interface_plan = build_interface_coverage_plan(interface)
    lifecycle_plan = build_lifecycle_coverage_plan(interface, metadata)
    templates = {
        item["template"] for item in interface_plan["obligations"]
    }
    assert {
        "reset_behavior",
        "busy_behavior",
        "completion_behavior",
        "error_behavior",
        "command_legality",
    } <= templates
    assert {item["template"] for item in lifecycle_plan["obligations"]} == {
        "job_lifecycle",
        "reset_abort_phase",
        "post_reset_purity",
    }
    manifest = compile_verification_manifest(
        interface_plan,
        {"obligations": [], "operation_metadata": metadata},
        lifecycle_plan,
    )
    lifecycle_ids = {
        item["id"] for item in manifest["obligations"] if item["category"] == "lifecycle"
    }
    assert "channel.cmd_chan.command_legality" in lifecycle_ids
    assert "operation.gemm_core.reset_abort_phase" in lifecycle_ids
    assert "operation.gemm_core.post_reset_purity" in lifecycle_ids


def test_lifecycle_stimulus_plan_covers_every_external_phase() -> None:
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_stimulus_plan(interface, metadata)
    phases = {
        item.get("phase")
        for item in plan["scenarios"]
        if item.get("kind") == "reset_abort"
    }
    assert phases == {
        "idle",
        "input_a_matrix",
        "input_b_matrix",
        "input_bias_vector",
        "compute",
        "output",
    }
    kinds = {item["kind"] for item in plan["scenarios"]}
    assert {"illegal_command", "illegal_then_legal_recovery", "abort_then_clean_job"} <= kinds


def test_command_stall_probe_golden_checks_the_perturbed_job_before_next_acceptance() -> None:
    source = inspect.getsource(campaign_module._probe_command_stall)
    completion_wait = source.index('"completion"')
    golden_record = source.index("stimulus_id = _record_case(")
    next_acceptance = source.index("await next_command")
    assert "[*prefix_beats, *final_beats]" in source
    assert completion_wait < golden_record < next_acceptance
    assert "return stimulus_id" in source


def test_automatic_campaign_executes_a_golden_checked_simultaneous_command_job() -> None:
    source = inspect.getsource(campaign_module.run_code_owned_verification_campaign)
    assert "command_reset_release=(reset_name, int(active_value))" in source
    operation_case = inspect.getsource(campaign_module.run_code_owned_operation_case)
    assert "drive_accepted_command_on_reset_release" in operation_case


def test_generated_block_contains_one_executable_code_owned_campaign_when_enabled() -> None:
    architecture, interface = _contracts()
    source = render_contract_generated_block(
        build_interface_coverage_plan(interface),
        architecture,
        include_automatic_campaign=True,
        randomized_transactions_minimum=100,
    )
    compile(source, "generated_contract_block.py", "exec")
    assert source.count("async def _contract_automatic_verification_campaign") == 1
    assert "randomized_transactions_minimum': 100" in source
    assert "run_code_owned_verification_campaign" in source
    assert "CONTRACT_LIFECYCLE_STIMULUS_PLAN" in source


def test_known_operation_coverage_is_synthesized_without_llm_decisions() -> None:
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    assert [item["concept"] for item in specs[0]["coverpoints"]] == [
        "dimensions",
        "operand_values",
        "accumulation",
        "bias",
        "activation",
    ]
    assert all(
        point["field"].startswith("canonical_job.")
        for point in specs[0]["coverpoints"]
    )
    assert all(point["bins"] for point in specs[0]["coverpoints"])


def test_unknown_architect_feature_disables_whole_automatic_campaign() -> None:
    architecture, interface = _contracts()
    architecture = copy.deepcopy(architecture)
    architecture["operations"][0]["feature_extensions"].append("novel_quantizer")
    metadata = build_architect_operation_metadata(architecture, interface)
    support = automatic_campaign_support(metadata, architecture)
    assert support["supported"] is False
    assert any("novel_quantizer" in reason for reason in support["reasons"])


def test_minimal_llm_host_becomes_a_complete_deterministic_tb() -> None:
    context = _context()
    frozen = context["frozen_architecture"]
    result = {
        "status": "VERIFICATION_READY",
        "summary": "verifier_tool owns the supported campaign",
        "reference_files": [
            {
                "path": "automatic_reference.py",
                "purpose": "code-owned reference marker",
                "content": "REFERENCE_MODEL_OWNED_BY_VERIFIER_TOOL = True\n",
            }
        ],
        "test_files": [
            {
                "path": "test_automatic_campaign.py",
                "purpose": "host the generated deterministic campaign",
                "categories": ["operation", "protocol", "lifecycle"],
                "regression_groups": ["smoke", "targeted", "full"],
                "coverage_obligations": [],
                "content": "COVERAGE_OBLIGATIONS = set()\n",
            }
        ],
        "operation_coverage": [],
        "verification_plan": {
            "top_module": frozen["module_manifest"]["top"],
            "test_modules": ["test_automatic_campaign"],
            "test_categories": ["operation", "protocol", "lifecycle"],
            "randomized_test_count": 100,
            "seed": 1,
            "timeout_seconds": 3600,
            "regression_groups": {
                "smoke": ["test_automatic_campaign"],
                "targeted": ["test_automatic_campaign"],
                "full": ["test_automatic_campaign"],
            },
            "pass_criteria": "all generated assertions and coverage close",
            "protocol_assumptions": [],
        },
        "architecture_conflict": None,
        "known_verification_gaps": [],
    }
    prepared = VerifierAgent._with_contract_generated_blocks(result, context)
    content = prepared["test_files"][0]["content"]
    assert content.count("async def _contract_automatic_verification_campaign") == 1
    assert len(prepared["operation_coverage"][0]["coverpoints"]) == 5
    VerifierAgent._validate_result(result=result, context=context)


def test_supported_prompt_assigns_known_tb_work_to_verifier_tool() -> None:
    task = VerifierAgent._build_task(_context())
    assert "CODE-OWNED AUTOMATIC CAMPAIGN" in task
    assert "Do not write another golden model" in task
    assert "COVERAGE_OBLIGATIONS = set()" in task


def test_lifecycle_assertions_track_legal_job_retirement_and_illegal_recovery() -> None:
    architecture, interface = _contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_assertion_plan(
        build_interface_coverage_plan(interface), metadata
    )
    state: dict = {}
    base = {str(item["name"]): 0 for item in interface["signals"]}
    base["rst_n"] = 1

    check_lifecycle_assertions(
        {**base, "cmd_valid": 1, "cmd_ready": 1, "cmd_payload": 1}, plan, state
    )
    check_lifecycle_assertions({**base, "busy": 1}, plan, state)
    for index in range(64):
        check_lifecycle_assertions(
            {
                **base,
                "busy": 1,
                "y_valid": 1,
                "y_ready": 1,
                "y_last": int(index == 63),
            },
            plan,
            state,
        )
    check_lifecycle_assertions({**base, "completion": 1}, plan, state)
    check_lifecycle_assertions(base, plan, state)
    check_lifecycle_assertions(
        {**base, "cmd_valid": 1, "cmd_ready": 1, "cmd_payload": 0}, plan, state
    )
    check_lifecycle_assertions({**base, "error": 1}, plan, state)
    check_lifecycle_assertions(base, plan, state)
    finalize_lifecycle_assertions(plan, state)
