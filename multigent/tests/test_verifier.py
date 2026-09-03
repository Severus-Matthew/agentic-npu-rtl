from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VERIFIER_OUTPUT_SCHEMA, VerifierAgent


def generic_fir_context() -> dict:
    return {
        "user_request": "design a signed 16-bit streaming FIR filter",
        "verification_policy": {
            "exact_integer_match_when_applicable": True,
            "randomized_transactions_minimum": 100,
            "require_reset_tests": True,
            "require_backpressure_tests_when_applicable": True,
        },
        "frozen_architecture": {
            "architecture_contract": {
                "design": {"name": "stream_fir"},
                "operations": [
                    {
                        "name": "filter",
                        "kind": "FIR",
                        "semantics": "weighted sum of current and prior samples",
                    }
                ],
                "data_types": [
                    {"name": "sample_t", "width_bits": 16, "signed": True}
                ],
                "control": {"strategy": "stream-driven"},
                "reset": {"style": "synchronous", "polarity": "active_high"},
            },
            "interface_contract": {
                "protocol": "ready_valid_stream",
                "clock": "clk",
                "reset": "rst",
                "signals": [
                    {"name": "clk", "direction": "input", "width": "1"},
                    {"name": "rst", "direction": "input", "width": "1"},
                ],
            },
            "module_manifest": {
                "top": "filter_top",
                "modules": [
                    {
                        "name": "filter_top",
                        "responsibility": "top integration",
                        "dependencies": ["filter_core"],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    },
                    {
                        "name": "filter_core",
                        "responsibility": "filter datapath",
                        "dependencies": [],
                        "parameters": ["TAPS"],
                        "stateful": True,
                    },
                ],
            },
            "acceptance_criteria": {
                "functional": ["matches independent FIR reference"],
                "verification": ["at least 100 randomized streams"],
                "rtl": ["synthesizable SystemVerilog"],
                "synopsys_handoff": ["verified RTL only"],
            },
        },
        "provenance": {
            "includes_generated_rtl": False,
            "includes_rtl_generator_output": False,
        },
    }


def verification_ready_result() -> dict:
    reference = """def wrap_signed(value: int, bits: int) -> int:\n    mask = (1 << bits) - 1\n    value &= mask\n    sign = 1 << (bits - 1)\n    return value - (1 << bits) if value & sign else value\n"""
    test = """import cocotb\n\n@cocotb.test(timeout_time=1, timeout_unit=\"ms\")\nasync def test_contract_smoke(dut):\n    assert hasattr(dut, \"clk\")\n"""
    return {
        "status": "VERIFICATION_READY",
        "summary": "Independent FIR reference and cocotb contract tests.",
        "reference_files": [
            {
                "path": "fir_reference.py",
                "purpose": "golden arithmetic",
                "content": reference,
            }
        ],
        "test_files": [
            {
                "path": "test_fir_contract.py",
                "purpose": "functional/protocol regression",
                "categories": ["smoke", "randomized", "reset", "backpressure"],
                "regression_groups": ["smoke", "targeted", "full"],
                "content": test,
            }
        ],
        "verification_plan": {
            "top_module": "filter_top",
            "test_modules": ["test_fir_contract"],
            "test_categories": ["smoke", "randomized", "reset", "backpressure"],
            "randomized_test_count": 100,
            "seed": 20260903,
            "timeout_seconds": 120,
            "regression_groups": {
                "smoke": ["test_fir_contract"],
                "targeted": ["test_fir_contract"],
                "full": ["test_fir_contract"],
            },
            "pass_criteria": "all cocotb tests pass",
            "protocol_assumptions": [
                "ready/valid transfers occur on ready && valid"
            ],
        },
        "architecture_conflict": None,
        "known_verification_gaps": [],
    }


class FakeVerifierAgent(VerifierAgent):
    def run_structured(self, **_: object) -> dict:
        return copy.deepcopy(verification_ready_result())


def verifier_schema() -> dict:
    return json.loads(VERIFIER_OUTPUT_SCHEMA.read_text(encoding="utf-8"))


def test_generic_non_gemm_verifier_output_satisfies_schema() -> None:
    Draft202012Validator(verifier_schema()).validate(verification_ready_result())


def test_verifier_context_rejects_rtl_contamination() -> None:
    context = generic_fir_context()
    context["provenance"]["includes_generated_rtl"] = True
    with pytest.raises(AgentRuntimeError, match="exclude generated RTL"):
        VerifierAgent._validate_context(context)


def test_verifier_writes_only_owned_artifacts(tmp_path: Path) -> None:
    result = FakeVerifierAgent().run(
        generic_fir_context(),
        workspace_dir=tmp_path,
        run_id="unit",
    )
    assert result["status"] == "VERIFICATION_READY"
    assert (tmp_path / "reference" / "fir_reference.py").is_file()
    assert (tmp_path / "tests" / "test_fir_contract.py").is_file()
    assert (tmp_path / "verification" / "verification_plan.yaml").is_file()
    assert not list(tmp_path.rglob("*.sv"))


def test_verifier_accepts_explicit_owned_path_prefixes(tmp_path: Path) -> None:
    class PrefixedVerifier(FakeVerifierAgent):
        def run_structured(self, **_: object) -> dict:
            result = verification_ready_result()
            result["reference_files"][0]["path"] = "reference/fir_reference.py"
            result["test_files"][0]["path"] = "tests/test_fir_contract.py"
            return result

    PrefixedVerifier().run(
        generic_fir_context(),
        workspace_dir=tmp_path,
        run_id="prefixed",
    )
    assert (tmp_path / "reference" / "fir_reference.py").is_file()
    assert (tmp_path / "tests" / "test_fir_contract.py").is_file()
    assert not (tmp_path / "reference" / "reference").exists()
    assert not (tmp_path / "tests" / "tests").exists()


def test_verifier_rejects_cross_owned_path_prefix() -> None:
    result = verification_ready_result()
    result["reference_files"][0]["path"] = "tests/fir_reference.py"
    with pytest.raises(AgentRuntimeError, match="outside its owned root"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_requires_policy_randomized_minimum() -> None:
    result = verification_ready_result()
    result["verification_plan"]["randomized_test_count"] = 99
    with pytest.raises(AgentRuntimeError, match="below policy minimum"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_requires_manifest_top() -> None:
    result = verification_ready_result()
    result["verification_plan"]["top_module"] = "wrong_top"
    with pytest.raises(AgentRuntimeError, match="does not match manifest top"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_python_that_reads_rtl_workspace() -> None:
    result = verification_ready_result()
    result["test_files"][0]["content"] += (
        '\nopen("multigent/workspace/rtl/dut.sv").read()\n'
    )
    with pytest.raises(AgentRuntimeError, match="forbidden capability"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_old_sim_timeout_import() -> None:
    result = verification_ready_result()
    result["test_files"][0]["content"] = (
        "import cocotb\n"
        "from cocotb.result import SimTimeoutError\n\n"
        "@cocotb.test()\n"
        "async def test_old_api(dut):\n"
        "    pass\n"
    )
    with pytest.raises(AgentRuntimeError, match="obsolete cocotb 2.x API"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_deprecated_cocotb_start() -> None:
    result = verification_ready_result()
    result["test_files"][0]["content"] = (
        "import cocotb\n\n"
        "async def child():\n"
        "    return None\n\n"
        "@cocotb.test()\n"
        "async def test_old_start(dut):\n"
        "    await cocotb.start(child())\n"
    )
    with pytest.raises(AgentRuntimeError, match="cocotb.start"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_architecture_conflict_emits_no_tests() -> None:
    result = verification_ready_result()
    result.update(
        {
            "status": "ARCHITECTURE_CONFLICT",
            "reference_files": [],
            "test_files": [],
            "verification_plan": {
                "top_module": "",
                "test_modules": [],
                "test_categories": [],
                "randomized_test_count": 0,
                "seed": 0,
                "timeout_seconds": 60,
                "regression_groups": {"smoke": [], "targeted": [], "full": []},
                "pass_criteria": "blocked",
                "protocol_assumptions": [],
            },
            "architecture_conflict": {
                "category": "INTERFACE_AMBIGUITY",
                "affected_modules": ["filter_top"],
                "issue": "output framing is contradictory",
                "evidence": "two frozen clauses disagree",
                "requested_architect_decision": (
                    "choose one externally visible framing rule"
                ),
            },
        }
    )
    VerifierAgent._validate_result(result=result, context=generic_fir_context())
