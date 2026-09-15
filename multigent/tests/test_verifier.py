from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VERIFIER_OUTPUT_SCHEMA, VerifierAgent


def generic_fir_context() -> dict:
    context = {
        "user_request": "design a signed 16-bit streaming FIR filter",
        "verification_policy": {
            "exact_integer_match_when_applicable": True,
            "randomized_transactions_minimum": 100,
            "require_reset_tests": True,
            "require_backpressure_tests_when_applicable": True,
            "regression_wall_timeout_seconds_minimum": 120,
            "require_completion_behavior_tests_when_defined": True,
            "require_error_behavior_tests_when_defined": True,
        },
        "frozen_architecture": {
            "architecture_contract": {
                "design": {"name": "stream_fir"},
                "operations": [
                    {
                        "name": "filter",
                        "kind": "FIR",
                        "coverage_family": "fir",
                        "coverage_family_source": "catalog",
                        "features": [
                            "tap_count",
                            "stream_length",
                            "coefficient_values",
                            "sample_values",
                            "numeric_behavior",
                        ],
                        "feature_extensions": [],
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
                "channels": [],
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
                        "name": "rst",
                        "role": "reset",
                        "semantic_class": None,
                        "semantic": "synchronous active-high reset",
                        "channel": None,
                        "direction": "input",
                        "width": "1",
                    },
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
                "fpga_handoff": ["verified RTL only"],
            },
        },
        "provenance": {
            "includes_generated_rtl": False,
            "includes_rtl_generator_output": False,
        },
    }
    interface = context["frozen_architecture"]["interface_contract"]
    interface["channels"] = [{"name": "observation", "direction": "input", "protocol_profile": "custom"}]
    for name, semantic in (("cfg", "configuration"), ("coefficient", "data"), ("sample", "data")):
        interface["signals"].append({"name": name, "role": "payload", "semantic_class": semantic,
                                     "channel": "observation", "direction": "input", "width": "16"})
    return context


def test_verifier_prompt_maps_internal_operations_to_completed_external_job() -> None:
    task = VerifierAgent._build_task(generic_fir_context())
    assert "accepted external job is the real transaction" in task
    assert "Absence of internal stage handshakes is not" in task
    assert "sequential all-A-then-all-B" in task
    assert "stable pre-active-edge phase" in task
    assert "portable pre-evaluation snapshot in Verilator" in task
    assert "Never decide whether a handshake occurred from post-edge values" in task
    assert "record_stimulus" in task
    assert "actual randomized stimulus ledger" in task


def test_verifier_prompt_assigns_generic_decision_ownership() -> None:
    task = VerifierAgent._build_task(generic_fir_context())
    assert 'Verifier owns coverage field names/types' in task
    assert 'not a fully' in task and 'specified cycle-by-cycle' in task
    assert 'values representable by the declared encoding' in task
    assert 'Command acceptance and command legality are distinct' in task
    assert 'two incompatible observable outcomes' in task
    assert 'Genuine' in task and 'contradictions must still be reported' in task
    assert 'no compile-time parameter' in task
    assert 'no later agent fills' in task


def test_verifier_rejects_declaration_only_tb_before_feature_metadata_errors() -> None:
    result = verification_ready_result()
    result['operation_coverage'][0]['coverpoints'] = []
    result['test_files'][0]['content'] = 'import cocotb\nCOVERAGE_OBLIGATIONS = {}\n'
    with pytest.raises(AgentRuntimeError, match='no executable async'):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_prompt_does_not_force_unreachable_catalog_starter_bins() -> None:
    task = VerifierAgent._build_task(generic_fir_context())
    assert "Catalog starter-bin labels are" in task
    assert "examples, not a checklist" in task
    assert "represent that concept with exactly one" in task
    assert "do not invent none/some modes" in task


def verification_ready_result() -> dict:
    reference = """def wrap_signed(value: int, bits: int) -> int:\n    mask = (1 << bits) - 1\n    value &= mask\n    sign = 1 << (bits - 1)\n    return value - (1 << bits) if value & sign else value\n"""
    test = """import cocotb\nfrom multigent.verifier_tool.coverage.runtime import contract_coverage, sample_operation\n\nCOVERAGE_OBLIGATIONS = {\"signal.rst.reset_behavior\", \"operation.filter.tap_count\", \"operation.filter.stream_length\", \"operation.filter.coefficient_values\", \"operation.filter.sample_values\", \"operation.filter.numeric_behavior\"}\n\n# === STIMULUS AND COVERAGE INTENT ===\nSTIMULUS_COVERAGE_INTENTS = [{\"label\": \"mixed\", \"targets\": [\"signal.rst.reset_behavior\", \"operation.filter.tap_count\", \"operation.filter.stream_length\", \"operation.filter.coefficient_values\", \"operation.filter.sample_values\", \"operation.filter.numeric_behavior\"]}]\n\n# === LLM-GENERATED OPERATION ASSERTIONS ===\n@cocotb.test(timeout_time=1, timeout_unit=\"ms\")\n@contract_coverage()\nasync def test_contract_smoke(dut):\n    # LLM-GENERATED OPERATION ASSERTION [filter.interface_clock]\n    assert hasattr(dut, \"clk\"), \"feature=filter.interface_clock expected=clk observed=missing signal=clk\"\n    # LLM-GENERATED OPERATION ASSERTION [filter.interface_reset]\n    assert hasattr(dut, \"rst\"), \"feature=filter.interface_reset expected=rst observed=missing signal=rst\"\n    stimulus_id = _contract_record_checked_stimulus(\"randomized\", {\"samples\": [1, 2, 3, 4], \"coefficients\": [1, 1, 1, 1]}, {\"result\": [1, 3, 6, 10]}, {\"result\": [1, 3, 6, 10]}, operations=(\"filter\",), label=\"mixed\")\n    sample_operation(\"filter\", {}, \"randomized\", stimulus_id)\n"""
    bindings = []
    for identity, fields in (("tap_count", {"cfg": {"signal": "cfg"}}),
                             ("stream_length", {"cfg": {"signal": "cfg"}}),
                             ("coefficient_values", {"coefficient": {"signal": "coefficient"}}),
                             ("sample_values", {"sample": {"signal": "sample"}}),
                             ("numeric_behavior", {"coefficient": {"signal": "coefficient"}, "sample": {"signal": "sample"}})):
        bindings.append({"operation": "filter", "point": identity, "template": "custom",
                         "observer": f"observe_{identity}", "event": "clock", "fields": fields})
    test += f"\nOPERATION_SAMPLING_BINDINGS = {bindings!r}\n" + '''
def observe_tap_count(values, state):
    return values["cfg"] & 31
def observe_stream_length(values, state):
    return (values["cfg"] >> 5) & 31
def observe_coefficient_values(values, state):
    return "mixed" if values["coefficient"] else "zero"
def observe_sample_values(values, state):
    return "mixed" if values["sample"] else "zero"
def observe_numeric_behavior(values, state):
    return "normal" if values["coefficient"] * values["sample"] <= 32767 else "overflow"
'''
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
                "coverage_obligations": [
                    "signal.rst.reset_behavior",
                    "operation.filter.tap_count",
                    "operation.filter.stream_length",
                    "operation.filter.coefficient_values",
                    "operation.filter.sample_values",
                    "operation.filter.numeric_behavior",
                ],
                "content": test,
            }
        ],
        "operation_coverage": [
            {
                "operation_name": "filter",
                "family": "fir",
                "coverpoints": [
                    {"id": "tap_count", "concept": "tap_count", "field": "tap_count", "source": "baseline", "description": "FIR tap count", "bins": [{"name": "four", "intent": "Four taps", "predicate": {"op": "eq", "args": [4]}}]},
                    {"id": "stream_length", "concept": "stream_length", "field": "stream_length", "source": "baseline", "description": "Input stream length", "bins": [{"name": "eight", "intent": "Eight samples", "predicate": {"op": "eq", "args": [8]}}]},
                    {"id": "coefficient_values", "concept": "coefficient_values", "field": "coefficient_class", "source": "baseline", "description": "Coefficient value classes", "bins": [{"name": "mixed", "intent": "Mixed signs", "predicate": {"op": "eq", "args": ["mixed"]}}]},
                    {"id": "sample_values", "concept": "sample_values", "field": "sample_class", "source": "baseline", "description": "Sample value classes", "bins": [{"name": "mixed", "intent": "Mixed signs", "predicate": {"op": "eq", "args": ["mixed"]}}]},
                    {"id": "numeric_behavior", "concept": "numeric_behavior", "field": "numeric_case", "source": "baseline", "description": "Numeric behavior", "bins": [{"name": "normal", "intent": "Normal arithmetic", "predicate": {"op": "eq", "args": ["normal"]}}]},
                ],
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


def test_operation_sampling_allows_runtime_stimulus_kind_variable() -> None:
    content = """from multigent.verifier_tool.coverage.runtime import sample_operation
def record(kind):
    stimulus_id = _contract_record_checked_stimulus(kind, {"x": 1}, {"y": 1}, {"y": 1}, operations=("filter",), label="case")
    sample_operation("filter", {"tap_count": 4}, kind, stimulus_id)
"""
    VerifierAgent._validate_operation_coverage_sampling(
        [content], [{"operation_name": "filter"}]
    )


def test_operation_sampling_allows_runtime_stimulus_kind_expression() -> None:
    content = """from multigent.verifier_tool.coverage.runtime import sample_operation
def record(randomized):
    kind = "randomized" if randomized else "directed"
    stimulus_id = _contract_record_checked_stimulus(kind, {"x": 1}, {"y": 1}, {"y": 1}, operations=("filter",), label="case")
    sample_operation("filter", {"tap_count": 4}, kind, stimulus_id)
"""
    VerifierAgent._validate_operation_coverage_sampling(
        [content], [{"operation_name": "filter"}]
    )


def test_operation_ledger_hook_does_not_require_coverage_fields() -> None:
    content = """from multigent.verifier_tool.coverage.runtime import sample_operation
def record(kind):
    stimulus_id = _contract_record_checked_stimulus(kind, {"x": 1}, {"y": 1}, {"y": 1}, operations=("filter",), label="case")
    sample_operation("filter", {"tap_count": 4}, kind, stimulus_id)
"""
    operation_coverage = [
        {
            "operation_name": "filter",
            "coverpoints": [
                {"field": "tap_count"},
                {"field": "mode"},
            ],
        }
    ]
    VerifierAgent._validate_operation_coverage_sampling([content], operation_coverage)


@pytest.mark.parametrize("expression", ["fields", "operation_fields(job)"])
def test_operation_sampling_accepts_mapping_helper_with_runtime_field_checks(expression):
    content = f'''from multigent.verifier_tool.coverage.runtime import sample_operation
def record(kind, job):
    stimulus_id = _contract_record_checked_stimulus(kind, {{"x": 1}}, {{"y": 1}}, {{"y": 1}}, operations=("filter",), label="case")
    fields = {{"tap_count": 4}}
    sample_operation("filter", {expression}, kind, stimulus_id)
'''
    VerifierAgent._validate_operation_coverage_sampling(
        [content], [{"operation_name": "filter", "coverpoints": [{"field": "tap_count"}]}],
    )


def test_operation_sampling_requires_persisted_linked_stimulus() -> None:
    content = """from multigent.verifier_tool.coverage.runtime import sample_operation
def record(kind):
    sample_operation("filter", {"tap_count": 4}, kind)
"""
    with pytest.raises(AgentRuntimeError, match="record_checked_stimulus"):
        VerifierAgent._validate_operation_coverage_sampling(
            [content], [{"operation_name": "filter", "coverpoints": [{"field": "tap_count"}]}]
        )


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


def test_verifier_context_rejects_unknown_signal_role() -> None:
    context = generic_fir_context()
    context["frozen_architecture"]["interface_contract"]["signals"][0]["role"] = "clockish"
    with pytest.raises(AgentRuntimeError, match="invalid taxonomy contract"):
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
    assert (tmp_path / "verification" / "interface_coverage_plan.yaml").is_file()
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


def test_verifier_requires_regression_wall_timeout_minimum() -> None:
    result = verification_ready_result()
    result["verification_plan"]["timeout_seconds"] = 2
    with pytest.raises(AgentRuntimeError, match="wall-clock policy minimum"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_requires_manifest_top() -> None:
    result = verification_ready_result()
    result["verification_plan"]["top_module"] = "wrong_top"
    with pytest.raises(AgentRuntimeError, match="does not match manifest top"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_missing_deterministic_coverage_obligation() -> None:
    result = verification_ready_result()
    result["test_files"][0]["coverage_obligations"] = []
    lines = result["test_files"][0]["content"].splitlines()
    result["test_files"][0]["content"] = "\n".join(
        "COVERAGE_OBLIGATIONS = []"
        if line.startswith("COVERAGE_OBLIGATIONS =")
        else line
        for line in lines
    )
    with pytest.raises(AgentRuntimeError, match="missing=.*reset_behavior"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_structured_and_code_obligation_mismatch() -> None:
    result = verification_ready_result()
    result["test_files"][0]["coverage_obligations"] = []
    with pytest.raises(AgentRuntimeError, match="must match"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_python_that_reads_rtl_workspace() -> None:
    result = verification_ready_result()
    result["test_files"][0]["content"] += (
        '\nopen("multigent/workspace/rtl/dut.sv").read()\n'
    )
    with pytest.raises(AgentRuntimeError, match="forbidden capability"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_allows_local_checker_run_without_relaxing_capabilities() -> None:
    result = verification_ready_result()
    result['test_files'][0]['content'] += '''
class ContractChecker:
    def __init__(observer, dut):
        observer.task = cocotb.start_soon(observer.run())
    async def run(observer):
        # LLM-GENERATED OPERATION ASSERTION [checker_liveness]
        assert True
'''
    VerifierAgent._validate_result(result=result, context=generic_fir_context())


@pytest.mark.parametrize('extra', [
    '\nunknown_receiver.run()\n',
    '\ndef outside_class(self):\n    self.run()\n',
    '\nclass Checker:\n    def __init__(self):\n        self.run()\n    def run(self):\n        open("rtl/dut.sv")\n',
    '\nclass Checker(UnknownBase):\n    def __init__(self):\n        self.run()\n    def run(self):\n        pass\n',
    '\nclass Checker:\n    def __init__(self):\n        self.run = other\n        self.run()\n    def run(self):\n        pass\n',
    '\nclass Checker:\n    def __getattribute__(self, name):\n        return other\n    def __init__(self):\n        self.run()\n    def run(self):\n        pass\n',
    '\nclass Checker:\n    def __init__(self):\n        def nested(self):\n            self.run()\n    def run(self):\n        pass\n',
])
def test_local_checker_exception_keeps_external_and_ambiguous_run_forbidden(extra) -> None:
    result = verification_ready_result()
    result['test_files'][0]['content'] += extra
    with pytest.raises(AgentRuntimeError, match='forbidden capability'):
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


def test_verifier_rejects_explicitly_omitted_test_source() -> None:
    result = verification_ready_result()
    result["test_files"][0]["content"] = (
        "import cocotb\n"
        "# Full source omitted intentionally\n"
        "raise RuntimeError('placeholder removed')\n"
    )
    with pytest.raises(AgentRuntimeError, match="omitted/placeholder source"):
        VerifierAgent._validate_result(result=result, context=generic_fir_context())


def test_verifier_rejects_response_budget_placeholder_variant() -> None:
    result = verification_ready_result()
    result["test_files"][0]["content"] = (
        "import cocotb\n"
        "# Full executable omitted here due response budget constraints.\n"
        "# In actual artifact generation this contains complete cocotb tests.\n"
    )
    with pytest.raises(AgentRuntimeError, match="omitted/placeholder source"):
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
                "timeout_seconds": 120,
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
