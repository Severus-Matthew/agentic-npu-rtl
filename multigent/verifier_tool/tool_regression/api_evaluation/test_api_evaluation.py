"""Local catalog gates plus one explicitly opt-in Verifier API case."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.verifier import VERIFIER_OUTPUT_SCHEMA, VerifierAgent
from multigent.verifier_tool.extensions.authoring import (
    _temporal_output_has_activation_path,
)
from multigent.verifier_tool import (
    decode_verifier_extension_transport,
    extension_bundle_schema,
    operation_formula_compilation_report,
    render_extension_authoring_guide,
    resolve_extension_reuse,
    review_contract_deterministically,
    validate_architect_extension_requests,
    validate_verifier_extension_bundles,
)

from .contexts import (
    api_scenarios,
    expected_extension_request_ids,
    expected_formula_concepts,
    scenario_context,
)
from . import runner
from .runner import run_selected


HERE = Path(__file__).resolve().parent


def _assert_openai_strict_object_shapes(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False, path
            assert set(value.get("required", [])) == set(
                value.get("properties", {})
            ), path
        for key, child in value.items():
            _assert_openai_strict_object_shapes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_openai_strict_object_shapes(child, f"{path}[{index}]")


def test_catalog_is_balanced_and_paper_reviewable() -> None:
    scenarios = api_scenarios()
    counts = {
        domain: sum(item["domain"] == domain for item in scenarios.values())
        for domain in ("operation", "protocol", "lifecycle", "mixed")
    }
    assert counts == {"operation": 10, "protocol": 7, "lifecycle": 7, "mixed": 3}
    assert len(scenarios) == 27


def test_reviewed_evidence_references_catalog_without_inflating_case_count() -> None:
    ledger = json.loads(
        (HERE / "evidence" / "evaluation_ledger.json").read_text(encoding="utf-8")
    )
    scenarios = api_scenarios()
    attempts = ledger["attempts"]
    assert ledger["catalog_case_count"] == len(scenarios)
    assert ledger["domain_case_counts"] == {
        domain: sum(item["domain"] == domain for item in scenarios.values())
        for domain in ("operation", "protocol", "lifecycle", "mixed")
    }
    assert len({item["attempt_id"] for item in attempts}) == len(attempts)
    assert all(item["scenario_id"] in scenarios for item in attempts)
    assert all(item["api_calls"] >= 1 for item in attempts)
    assert ledger["reviewed_attempt_count"] == len(attempts)
    assert ledger["reviewed_api_calls"] == sum(
        item["api_calls"] for item in attempts
    )
    assert ledger["reviewed_verdict_counts"] == {
        verdict: sum(item["reviewed_verdict"] == verdict for item in attempts)
        for verdict in ("PASS", "REJECTED_BY_DETERMINISTIC_GATES")
    }
    assert ledger["reviewed_domain_attempt_counts"] == {
        domain: sum(item["domain"] == domain for item in attempts)
        for domain in ("operation", "protocol", "lifecycle", "mixed")
    }


def test_api_runner_requires_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("RUN_VERIFIER_API_EVALUATION", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    with pytest.raises(RuntimeError, match="RUN_VERIFIER_API_EVALUATION=1"):
        run_selected(
            ["operation.affine_triple_plus_one"], output_root=tmp_path
        )
    assert list(tmp_path.iterdir()) == []


def test_api_runner_retries_semantic_failure_with_previous_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[dict] = []
    verifier_config = VerifierAgent().config

    class FakeVerifier:
        def __init__(self) -> None:
            self.config = verifier_config
            self.last_generated_result = None

        def run(self, context: dict, **_: object) -> dict:
            calls.append(context)
            if len(calls) == 1:
                self.last_generated_result = {
                    "status": "VERIFICATION_READY",
                    "reference_files": [{"path": "reference.py", "content": "x = 1\n"}],
                    "test_files": [{"path": "test_dut.py", "content": "x = 1\n"}],
                }
                raise RuntimeError("missing checker body")
            return {
                "status": "VERIFICATION_READY",
                "reference_files": [],
                "test_files": [],
                "reference_model_files": [],
                "feature_extensions": [],
            }

    monkeypatch.setattr(runner, "VerifierAgent", FakeVerifier)
    monkeypatch.setattr(
        runner,
        "findings_from_validation_error",
        lambda exc: [{"category": "INVALID_ASSERTION", "evidence": str(exc)}],
    )
    monkeypatch.setattr(runner, "_validate_result", lambda *args: [])
    monkeypatch.setattr(
        runner,
        "review_verifier_artifacts",
        lambda *args: {"status": "APPROVED", "findings": []},
    )

    result = runner.run_one(
        "operation.absolute_value", tmp_path, max_attempts=3
    )

    assert result["verdict"] == "PASS"
    assert result["api_calls"] == 2
    assert calls[1]["deterministic_validation_review"]["previous_verifier_output"]
    assert result["attempts"][0]["status"] == "SEMANTIC_VALIDATION_FAILED"
    assert result["attempts"][1]["status"] == "PASS"


def test_extension_bundle_error_uses_source_and_bundle_repair_context() -> None:
    context = scenario_context("operation.absolute_value")
    candidate = {
        "status": "VERIFICATION_READY",
        "reference_files": [{"path": "reference.py", "content": "x = 1\n"}],
        "test_files": [{"path": "test_dut.py", "content": "x = 1\n"}],
        "feature_extensions": [{"request_id": "operation.absolute_value"}],
    }
    repaired = runner._repair_context(
        context,
        candidate=candidate,
        findings=[{"category": "COVERAGE_DEFINITION"}],
        error=(
            "Invalid Verifier feature extensions: feature_extensions[0].bindings "
            "omits required observation(s) ['trace']"
        ),
    )
    assert "deterministic_validation_review" not in repaired
    review = repaired["semantic_validation_review"]
    assert review["previous_verifier_output"] == candidate
    assert "feature_extensions[0].bindings" in review["validator_error"]


def test_incomplete_source_completion_stays_on_complete_source_path() -> None:
    context = scenario_context("operation.absolute_value")
    candidate = {
        "status": "VERIFICATION_READY",
        "reference_files": [{"path": "reference.py", "content": "x = 1\n"}],
        "test_files": [{"path": "test_dut.py", "content": "x = 1\n"}],
        "feature_extensions": [],
    }
    repaired = runner._repair_context(
        context,
        candidate=candidate,
        findings=[{"category": "INVALID_ASSERTION"}],
        error=(
            "Source completion must replace exactly the planned files; "
            "missing=['tests/test_dut.py'], unknown=[]"
        ),
    )
    assert "deterministic_validation_review" not in repaired
    assert "missing=['tests/test_dut.py']" in (
        repaired["semantic_validation_review"]["validator_error"]
    )


def test_monitor_install_error_stays_on_complete_source_path() -> None:
    context = scenario_context("operation.absolute_value")
    candidate = {
        "status": "VERIFICATION_READY",
        "reference_files": [{"path": "reference.py", "content": "x = 1\n"}],
        "test_files": [{"path": "test_dut.py", "content": "x = 1\n"}],
        "feature_extensions": [],
    }
    repaired = runner._repair_context(
        context,
        candidate=candidate,
        findings=[{"category": "INVALID_ASSERTION"}],
        error=(
            "Cannot install contract-generated TB monitor: generated block markers "
            "are malformed"
        ),
    )
    assert "deterministic_validation_review" not in repaired
    review = repaired["semantic_validation_review"]
    assert review["previous_verifier_output"] == candidate
    assert "generated block markers" in review["validator_error"]


def test_api_runner_does_not_retry_transport_failure_without_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0
    verifier_config = VerifierAgent().config

    class OfflineVerifier:
        def __init__(self) -> None:
            self.config = verifier_config
            self.last_generated_result = None

        def run(self, context: dict, **_: object) -> dict:
            nonlocal calls
            calls += 1
            raise RuntimeError("Connection error")

    monkeypatch.setattr(runner, "VerifierAgent", OfflineVerifier)
    result = runner.run_one(
        "operation.absolute_value", tmp_path, max_attempts=10
    )

    assert calls == 1
    assert result["api_calls"] == 1
    assert result["verdict"] == "REJECTED"
    assert result["attempts"][0]["status"] == "TOOL_OR_API_ERROR"


def test_api_runner_does_not_patch_retained_candidate_after_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0
    verifier_config = VerifierAgent().config

    class TimedOutVerifier:
        def __init__(self) -> None:
            self.config = verifier_config
            self.last_generated_result = None

        def run(self, context: dict, **_: object) -> dict:
            nonlocal calls
            calls += 1
            self.last_generated_result = {
                "status": "VERIFICATION_READY",
                "reference_files": [{"path": "reference.py", "content": "x = 1\n"}],
                "test_files": [{"path": "test_dut.py", "content": "x = 1\n"}],
            }
            raise RuntimeError(
                "verifier API request exceeded the total wall-clock deadline of 600 seconds"
            )

    monkeypatch.setattr(runner, "VerifierAgent", TimedOutVerifier)
    result = runner.run_one("operation.absolute_value", tmp_path, max_attempts=10)

    assert calls == 1
    assert result["api_calls"] == 1
    assert result["verdict"] == "REJECTED"
    assert result["attempts"][0]["status"] == "TOOL_OR_API_ERROR"


def test_api_runner_stops_after_three_identical_semantic_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0
    verifier_config = VerifierAgent().config

    class StalledVerifier:
        def __init__(self) -> None:
            self.config = verifier_config
            self.last_generated_result = None

        def run(self, context: dict, **_: object) -> dict:
            nonlocal calls
            calls += 1
            self.last_generated_result = {
                "status": "VERIFICATION_READY",
                "reference_files": [],
                "test_files": [],
            }
            raise RuntimeError("same deterministic finding")

    monkeypatch.setattr(runner, "VerifierAgent", StalledVerifier)
    monkeypatch.setattr(
        runner,
        "findings_from_validation_error",
        lambda exc: [{"category": "INVALID_STIMULUS", "evidence": str(exc)}],
    )
    result = runner.run_one(
        "operation.absolute_value", tmp_path, max_attempts=10
    )

    assert calls == 3
    assert result["api_calls"] == 3
    assert result["attempts"][-1]["repair_stalled"] is True


def test_api_extension_transport_is_strict_and_decodes_to_canonical_schema() -> None:
    schema = VerifierAgent().load_output_schema(VERIFIER_OUTPUT_SCHEMA)
    _assert_openai_strict_object_shapes(schema)
    implementation_file = (
        schema["properties"]["feature_extensions"]["items"]["properties"]
        ["assertion"]["properties"]["implementation"]["properties"]["file"]
    )
    assert implementation_file["pattern"] == r"^(reference|tests)/[^/]+\.py$"
    transport = {
        "schema_version": 1,
        "request_id": "lifecycle.busy_watchdog_observation",
        "id": "lifecycle.busy_watchdog_observation",
        "domain": "lifecycle",
        "feature_name": "busy_watchdog_observation",
        "target": {"scope": "operation", "name": "gemm"},
        "description": "Observe a long-running busy interval.",
        "bindings": '{"busy": "busy"}',
        "reuse": {
            "based_on_features": ["lifecycle.gemm.busy_tracks_active_job"],
            "helpers": ["capture_contract_snapshot"],
        },
        "assertion": {
            "implementation": {
                "kind": "verifier_python",
                "name": "busy_watchdog_assertion",
                "file": "tests/test_busy_watchdog.py",
                "symbol": "check_busy_watchdog",
            },
            "parameters": '{"threshold_cycles": 12}',
        },
        "coverage": {
            "implementation": {
                "kind": "verifier_python",
                "name": "busy_watchdog_coverage",
                "file": "tests/test_busy_watchdog.py",
                "symbol": "sample_busy_watchdog",
            },
            "parameters": '{"threshold_cycles": 12}',
            "bins": [
                {
                    "name": "threshold_reached",
                    "intent": "Observe twelve busy cycles.",
                    "predicate": '{"gte": 12}',
                }
            ],
        },
        "stimulus": {
            "implementation": {
                "kind": "verifier_python",
                "name": "busy_watchdog_stimulus",
                "file": "tests/test_busy_watchdog.py",
                "symbol": "drive_busy_watchdog",
            },
            "parameters": '{"threshold_cycles": 12}',
            "scenarios": [
                {
                    "name": "long_busy_job",
                    "intent": "Run a long job.",
                    "parameters": "{}",
                }
            ],
        },
    }
    decoded = decode_verifier_extension_transport(
        {"feature_extensions": [transport]}
    )["feature_extensions"][0]
    Draft202012Validator(extension_bundle_schema()).validate(decoded)
    assert decoded["bindings"] == {"busy": "busy"}
    assert decoded["coverage"]["bins"][0]["predicate"] == {"gte": 12}


def test_extension_guide_requires_emitted_reachable_source_and_exact_reuse() -> None:
    guide = render_extension_authoring_guide()
    assert "test_files or reference_model_files" in guide
    assert "verification/*.py" in guide
    assert "never name" in guide
    assert "make it reachable from a generated ``tests/*.py`` cocotb entry point" in guide
    assert "copy every exact ID shown" in guide
    assert "simulator-derived observations" in guide
    assert "must actually assert that" in guide
    assert "awaiting only Timer/RisingEdge" in guide
    assert "every declared scenario" in guide
    assert "monitor concurrently" in guide
    assert "code-owned campaign/driver" in guide
    assert "every ``required_observations[].name`` as an exact key" in guide
    assert "three distinct module-level functions" in guide
    assert "only parameters its own function actually consumes" in guide
    assert "For a protocol/lifecycle-only contract" in guide
    assert "capture_protocol_event_trace" in guide
    assert "runtime bin hits, not the list, remain authoritative" in guide
    assert "Returning ``{\"passed\": ok}`` is not itself an assertion" in guide


@pytest.mark.parametrize("identity", sorted(api_scenarios()))
def test_every_api_scenario_has_a_valid_frozen_contract(identity: str) -> None:
    context = scenario_context(identity)
    frozen = context["frozen_architecture"]
    architecture = frozen["architecture_contract"]
    interface = frozen["interface_contract"]
    assert validate_architect_extension_requests(architecture, interface) == []
    review = review_contract_deterministically(architecture, interface)
    assert review["status"] == "PASS", review["findings"]
    report = operation_formula_compilation_report(architecture)
    assert report["status"] == "PASS", report
    VerifierAgent._validate_context(context)
    assert [
        item["id"] for item in architecture.get("verification_extensions", [])
    ] == expected_extension_request_ids(identity)
    compiled = {
        stage["stage"]
        for operation in report["operations"]
        for stage in operation["stages"]
        if stage["status"] == "solver_compiled"
    }
    assert compiled == set(expected_formula_concepts(identity))


def test_bounded_ready_recovery_targets_dut_owned_ready() -> None:
    frozen = scenario_context("protocol.bounded_ready_recovery")["frozen_architecture"]
    request = frozen["architecture_contract"]["verification_extensions"][0]
    target = request["target"]["name"]
    ready = next(
        signal
        for signal in frozen["interface_contract"]["signals"]
        if signal.get("channel") == target and signal.get("role") == "ready"
    )
    assert ready["direction"] == "output"


def test_output_observation_extension_requires_a_real_activation_path() -> None:
    frozen = scenario_context("protocol.payload_parity_observation")["frozen_architecture"]
    request = frozen["architecture_contract"]["verification_extensions"][0]
    interface = frozen["interface_contract"]
    passive_source = '''
import cocotb
from cocotb.triggers import RisingEdge

async def observe_parity(dut):
    dut.y_ready.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_parity(dut):
    await observe_parity(dut)
'''
    assert not _temporal_output_has_activation_path(
        request, interface, {"tests/test_parity.py": passive_source}, "observe_parity"
    )
    driven_source = passive_source.replace(
        "dut.y_ready.value = 1",
        "dut.cmd_valid.value = 1\n    dut.y_ready.value = 1",
    )
    assert _temporal_output_has_activation_path(
        request, interface, {"tests/test_parity.py": driven_source}, "observe_parity"
    )


def test_temporal_extension_requires_clock_in_standalone_cocotb_test() -> None:
    frozen = scenario_context("protocol.bounded_ready_recovery")["frozen_architecture"]
    architecture = frozen["architecture_contract"]
    interface = frozen["interface_contract"]
    request = architecture["verification_extensions"][0]
    reuse = resolve_extension_reuse(architecture, interface)["entries"][0]
    implementation = {
        "kind": "verifier_python",
        "name": "bounded_ready_recovery",
        "file": "tests/test_extension.py",
    }
    bundle = {
        "schema_version": 1,
        "request_id": request["id"],
        "id": request["id"],
        "domain": request["domain"],
        "feature_name": request["feature_name"],
        "target": request["target"],
        "description": "Exercise bounded command READY recovery.",
        "bindings": {"valid": "cmd_valid", "ready": "cmd_ready"},
        "reuse": {
            "based_on_features": reuse["preserved_feature_ids"],
            "helpers": [],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": "check_recovery"},
            "parameters": {"maximum_cycles": 7},
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "cover_recovery"},
            "parameters": {"maximum_cycles": 7},
            "bins": [{
                "name": "within_bound",
                "intent": "Observe command READY recovery within the bound.",
                "predicate": {"op": "lte", "args": [7]},
            }],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "drive_recovery"},
            "parameters": {"maximum_cycles": 7},
            "scenarios": [{
                "name": "bounded_window",
                "intent": "Hold VALID until DUT READY recovers.",
                "parameters": {"maximum_cycles": 7},
            }],
        },
    }
    source = {
        "path": "tests/test_extension.py",
        "categories": ["protocol"],
        "content": '''
import cocotb
from cocotb.triggers import RisingEdge

async def drive_recovery(dut, maximum_cycles):
    dut.cmd_valid.value = 1
    observed_cycles = 0
    for _ in range(maximum_cycles):
        await RisingEdge(dut.clk)
        observed_cycles += 1
        if int(dut.cmd_ready.value):
            break
    return observed_cycles

def cover_recovery(recovery_cycle, maximum_cycles):
    return {"triggered": recovery_cycle > 0, "bin": "within_bound" if recovery_cycle <= maximum_cycles else "over_bound"}

def check_recovery(recovery_cycle, maximum_cycles):
    assert recovery_cycle <= maximum_cycles
    return True

@cocotb.test()
async def test_recovery(dut):
    recovery_cycle = await drive_recovery(dut, maximum_cycles=7)
    sample = cover_recovery(recovery_cycle, maximum_cycles=7)
    assert sample["triggered"]
    assert sample["bin"] == "within_bound"
    assert check_recovery(recovery_cycle, maximum_cycles=7)
''',
    }
    errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[source],
        interface=interface,
        require_runtime_evidence=True,
    )
    assert any("does not start a Clock" in error for error in errors)

    helper_clock_source = dict(source)
    helper_clock_source["content"] = source["content"].replace(
        "from cocotb.triggers import RisingEdge\n",
        "from cocotb.clock import Clock\nfrom cocotb.triggers import RisingEdge\n",
    ).replace(
        "async def drive_recovery(dut, maximum_cycles):\n",
        "async def start_clock(dut):\n"
        "    cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())\n\n"
        "async def drive_recovery(dut, maximum_cycles):\n",
    ).replace(
        "async def test_recovery(dut):\n"
        "    recovery_cycle = await drive_recovery(dut, maximum_cycles=7)\n",
        "async def test_recovery(dut):\n"
        "    await start_clock(dut)\n"
        "    recovery_cycle = await drive_recovery(dut, maximum_cycles=7)\n",
    )
    helper_clock_errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[helper_clock_source],
        interface=interface,
        require_runtime_evidence=True,
    )
    assert not any("does not start a Clock" in error for error in helper_clock_errors)

    data_only_source = dict(source)
    data_only_source["content"] = source["content"].replace(
        "def check_recovery(recovery_cycle, maximum_cycles):\n"
        "    assert recovery_cycle <= maximum_cycles\n"
        "    return True\n",
        "check_recovery = {'maximum_cycles': 7}\n",
    )
    data_errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[data_only_source],
        interface=interface,
        require_runtime_evidence=True,
    )
    assert any(
        "is module-scope data, not an executable function" in error
        for error in data_errors
    )


@pytest.mark.skipif(
    os.getenv("RUN_VERIFIER_API_EVALUATION") != "1",
    reason="Explicit opt-in required because this test makes one Verifier API request.",
)
def test_selected_verifier_api_scenario(tmp_path: Path) -> None:
    identity = os.getenv(
        "VERIFIER_API_SCENARIO_ID", "mixed.affine_and_busy_watchdog"
    )
    output = Path(os.getenv("VERIFIER_API_OUTPUT_DIR", str(tmp_path))).resolve()
    records = run_selected([identity], output_root=output)
    assert records[0]["verdict"] == "PASS", records[0]
