"""Pre-simulation review of checks and static stimulus intent, independent of RTL."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.verifier_tool.predefined_assertion.review import assertion_definition_view, trusted_monitor_review_view
from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan
from multigent.verifier_tool.coverage.operation.plan import load_operation_coverage_families, operation_plan_for_tests
from multigent.verifier_tool.coverage.operation.sampling import effective_operation_coverage, operation_observer_views

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT
from .verifier import VerifierAgent


class VerifierReviewAgent(APIAgent):
    """Use the generation model in a separate read-only coverage/check review call."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        defaults = AgentConfig(name="verifier_review", role_skill="verifier")
        super().__init__(AgentConfig(name="verifier_review", role_skill="verifier",
                                     model=model or defaults.model, api_mode=api_mode or defaults.api_mode))

    def load_instructions(self) -> str:
        return (Path(__file__).parent / "prompts" / "verifier_review.md").read_text(encoding="utf-8")

    @staticmethod
    def build_context(context: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
        VerifierAgent._validate_context(context)
        families = load_operation_coverage_families()["families"]
        operation_plan = operation_plan_for_tests(
            candidate["operation_coverage"], [item["content"] for item in candidate["test_files"]],
            context["frozen_architecture"]["architecture_contract"],
            context["frozen_architecture"]["interface_contract"],
        )
        selected = {item["family"] for item in candidate.get("operation_coverage", [])}
        concepts = {point['concept'] for item in candidate.get('operation_coverage', []) for point in item['coverpoints']}
        taxonomy = {}
        for name in selected:
            if name in families:
                spec = copy.deepcopy(families[name])
                spec['optional_concepts'] = {key: value for key, value in spec.get('optional_concepts', {}).items() if key in concepts}
                taxonomy[name] = spec
        return {
            "user_request": context["user_request"],
            "frozen_architecture": copy.deepcopy(context["frozen_architecture"]),
            "verification_policy": dict(context["verification_policy"]),
            "interface_coverage_plan": build_interface_coverage_plan(context["frozen_architecture"]["interface_contract"]),
            "selected_operation_taxonomy": taxonomy,
            "operation_coverage": effective_operation_coverage(candidate["operation_coverage"], operation_plan),
            "operation_sampling_plan": operation_plan,
            "operation_observer_definitions": operation_observer_views([item["content"] for item in candidate["test_files"]]),
            "assertion_views": [assertion_definition_view(item["content"], filename=item["path"]) for item in candidate["test_files"]],
            "stimulus_and_assertion_source": [
                {"path": item["path"], "source": item["content"]}
                for item in candidate["test_files"]
            ],
            "reference_checkers": copy.deepcopy(candidate["reference_files"]),
            "trusted_monitor": trusted_monitor_review_view(),
            "provenance": {"includes_generated_rtl": False, "includes_rtl_generator_output": False,
                           "includes_stimulus": True, "includes_simulation_evidence": False},
        }

    def review(self, context: Mapping[str, Any], candidate: Mapping[str, Any], *, run_id: str) -> dict[str, Any]:
        envelope = self.build_context(context, candidate)
        result = self.run_structured(
            task=(
                "Review coverage/assertion definitions and the declared static "
                "stimulus-to-feature intent only.\n\n"
                + yaml.safe_dump(envelope, sort_keys=False)
            ),
            schema_path=SCHEMA_ROOT / "verifier_review.schema.json", log_name=f"verifier-review-{run_id}.json",
        )
        self.validate_result(result, context)
        return result

    @staticmethod
    def validate_result(result: Mapping[str, Any], context: Mapping[str, Any]) -> None:
        status, findings = result["status"], result["findings"]
        if status not in {'APPROVED', 'VERIFIER_REPAIR_REQUIRED'}:
            raise AgentRuntimeError(f'Unknown verifier review status: {status!r}')
        if status == "APPROVED" and findings:
            raise AgentRuntimeError("APPROVED review must have no findings")
        if status == "VERIFIER_REPAIR_REQUIRED" and not findings:
            raise AgentRuntimeError("Review repair requires concrete TB findings")
