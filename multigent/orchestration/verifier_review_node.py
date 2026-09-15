"""One explicit, read-only Verifier review attempt before simulation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier_review import VerifierReviewAgent
from multigent.agents.verifier import VerifierAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context
from multigent.tools.vivado import write_json

from .artifacts import review_definition_hashes


def make_verifier_review_node(agent: VerifierReviewAgent | None = None):
    runtime = agent or VerifierReviewAgent()

    def review_node(state: Mapping[str, Any]) -> dict[str, Any]:
        candidate = state.get("verifier_result")
        if state.get("verifier_status") != "VERIFICATION_READY" or not isinstance(candidate, Mapping):
            raise AgentRuntimeError("Verifier review needs a validated VERIFICATION_READY candidate")
        # Rebuild only frozen external inputs; never forward repair/simulation evidence.
        context = build_verification_context(user_request=state["user_request"],
                                             architecture_dir=Path(state.get("architecture_dir", WORKSPACE_ROOT / "architecture")))
        for field, owner in (("test_files", "tests"), ("reference_files", "reference")):
            for item in candidate[field]:
                name = VerifierAgent._safe_python_filename(item['path'], owned_root=owner)
                saved = WORKSPACE_ROOT / owner / name
                expected = item['content'] if item['content'].endswith('\n') else item['content'] + '\n'
                if not saved.is_file() or saved.read_text(encoding='utf-8') != expected:
                    raise AgentRuntimeError(f"Review candidate differs from saved {owner}/{name}")
        definition_hashes = review_definition_hashes(state)
        version, revision = state.get("architecture_version", 0), state.get("verifier_revision", 0)
        architecture_revision = state.get("architecture_revision", 0)
        tag = (
            f"{state.get('run_id', 'manual')}-av{version}-ar{architecture_revision}"
            f"-r{state.get('repair_iteration', 0)}-v{revision}"
        )
        result = runtime.review(context, candidate, run_id=tag)
        VerifierReviewAgent.validate_result(result, context)
        report = {"review": result, "definition_hashes": definition_hashes,
                  "scope": "COVERAGE_ASSERTIONS_AND_STIMULUS_INTENT",
                  "simulation_pass": False, "stimulus_reviewed": True}
        write_json(
            WORKSPACE_ROOT / "verification" /
            f"verifier-review-av{version}-ar{architecture_revision}-r{state.get('repair_iteration', 0)}-v{revision}.json",
            report,
        )
        return {"verifier_review_status": result["status"], "verifier_review_result": result,
                "verifier_review_hashes": definition_hashes,
                "verification_status": "PENDING",
                "history": [{"stage": "verifier_review", "status": result["status"],
                             "findings": result["findings"], "stimulus_reviewed": True}]}

    return review_node
