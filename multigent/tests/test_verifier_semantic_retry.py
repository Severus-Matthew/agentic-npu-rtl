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


def test_semantic_validation_failure_gets_one_feedback_retry() -> None:
    class StubVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run_from_state(self, state: dict) -> dict:
            self.calls += 1
            if self.calls == 1:
                raise AgentRuntimeError(
                    "Generated ready/valid source driver deasserts valid inside a handshake wait loop"
                )

            assert state["run_id"] == "unit-semantic-retry1"
            feedback = state["verification_context"]["semantic_retry_feedback"]
            assert "ready/valid" in feedback["validator_error"]
            assert feedback["attempt"] == 1
            assert "Do not weaken" in feedback["required_action"]
            return _success_update()

    runtime = StubVerifier()
    node = make_verifier_node(runtime)  # type: ignore[arg-type]
    update = node(  # type: ignore[arg-type]
        {
            "run_id": "unit",
            "user_request": "design a streaming block",
            "architecture_version": 1,
            "repair_iteration": 0,
            "verification_context": {
                "user_request": "design a streaming block",
                "verification_policy": {},
                "frozen_architecture": {},
                "provenance": {
                    "includes_generated_rtl": False,
                    "includes_rtl_generator_output": False,
                },
            },
        }
    )

    assert runtime.calls == 2
    assert update["verifier_status"] == "VERIFICATION_READY"
    assert update["history"][0]["semantic_retry"] is True
    assert "ready/valid" in update["history"][0]["semantic_retry_error"]


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


def test_second_semantic_failure_surfaces_without_third_call() -> None:
    class StubVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def run_from_state(self, state: dict) -> dict:
            self.calls += 1
            raise AgentRuntimeError(
                "Verifier claims readiness without referencing required contract-visible completion/error signals: status_done"
            )

    runtime = StubVerifier()
    node = make_verifier_node(runtime)  # type: ignore[arg-type]

    with pytest.raises(AgentRuntimeError, match="status_done"):
        node(  # type: ignore[arg-type]
            {
                "run_id": "unit",
                "user_request": "design a streaming block",
                "verification_context": {
                    "user_request": "design a streaming block",
                    "verification_policy": {},
                    "frozen_architecture": {},
                    "provenance": {
                        "includes_generated_rtl": False,
                        "includes_rtl_generator_output": False,
                    },
                },
            }
        )
    assert runtime.calls == 2
