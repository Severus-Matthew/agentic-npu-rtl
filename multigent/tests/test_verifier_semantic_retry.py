from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.orchestration.verifier_node import make_verifier_node


def _success_update() -> dict:
    return {
        "verifier_status": "VERIFICATION_READY",
        "verifier_result": {"status": "VERIFICATION_READY"},
        "verification_plan": {"top_module": "dut", "test_modules": ["test_dut"]},
        "architecture_conflict": None,
        "verification_context": {"provenance": {}},
    }


def test_semantic_validation_failure_becomes_explicit_graph_state() -> None:
    class StubVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run_from_state(self, state: dict) -> dict:
            self.calls += 1
            self.last_generated_result = {
                "status": "VERIFICATION_READY",
                "test_files": [{"path": "tests/test_gemm.py", "content": "old"}],
            }
            raise AgentRuntimeError(
                "Invalid operation coverage: missing=['fixed_cmd_word_mapping']"
            )

    runtime = StubVerifier()
    update = make_verifier_node(runtime)(  # type: ignore[arg-type]
        {
            "run_id": "unit",
            "user_request": "design a streaming block",
            "verification_context": {"user_request": "design a streaming block"},
        }
    )

    assert runtime.calls == 1
    assert update["verifier_status"] == "SEMANTIC_VALIDATION_FAILED"
    assert "fixed_cmd_word_mapping" in update["errors"][0]
    assert update["history"][0]["validator_error"] == update["errors"][0]
    assert update["verifier_draft"]["test_files"][0]["content"] == "old"


def test_api_runtime_failure_is_not_semantically_retried() -> None:
    class StubVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run_from_state(self, state: dict) -> dict:
            self.calls += 1
            raise AgentRuntimeError(
                "verifier API request failed using mode 'responses' and model 'example'"
            )

    runtime = StubVerifier()
    node = make_verifier_node(runtime)  # type: ignore[arg-type]

    with pytest.raises(AgentRuntimeError, match="API request failed"):
        node({"run_id": "unit"})  # type: ignore[arg-type]
    assert runtime.calls == 1


def test_successful_graph_retry_is_marked_in_history() -> None:
    class StubVerifier:
        def run_from_state(self, state: dict) -> dict:
            review = state["verification_context"]["semantic_validation_review"]
            assert review["missing_concepts"] == ["required_feature"]
            return _success_update()

    update = make_verifier_node(StubVerifier())(  # type: ignore[arg-type]
        {
            "run_id": "unit",
            "verification_context": {
                "semantic_validation_review": {
                    "validator_error": "missing required_feature",
                    "missing_concepts": ["required_feature"],
                }
            },
        }
    )

    assert update["verifier_status"] == "VERIFICATION_READY"
    assert update["history"][0]["semantic_retry"] is True
    assert "required_feature" in update["history"][0]["semantic_retry_error"]


def test_semantic_correction_can_report_a_genuine_architecture_conflict() -> None:
    class StubVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run_from_state(self, state: dict) -> dict:
            self.calls += 1
            return {
                "verifier_status": "ARCHITECTURE_CONFLICT",
                "architecture_conflict": {"issue": "contradictory output framing"},
            }

    runtime = StubVerifier()
    update = make_verifier_node(runtime)(  # type: ignore[arg-type]
        {
            "run_id": "unit",
            "verification_context": {
                "semantic_validation_review": {
                    "validator_error": "missing=['required_feature']",
                    "previous_verifier_output": {"status": "VERIFICATION_READY"},
                }
            },
        }
    )

    assert update["verifier_status"] == "ARCHITECTURE_CONFLICT"
    assert update["architecture_conflict"]["issue"] == "contradictory output framing"
    assert update["history"][0]["semantic_retry"] is True
    assert runtime.calls == 1
