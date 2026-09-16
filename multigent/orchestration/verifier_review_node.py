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
    runtime = agent  # Optional legacy injection; the default flow makes no reviewer model call.

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
        if runtime is not None:
            result = runtime.review(context, candidate, run_id=tag)
            VerifierReviewAgent.validate_result(result, context)
        else:
            try:
                VerifierAgent._validate_prepared_result(result=candidate, context=context)
                result = {"status": "APPROVED", "summary": "Deterministic source and contract checks passed", "findings": []}
            except AgentRuntimeError as exc:
                result = {"status": "VERIFIER_REPAIR_REQUIRED", "summary": str(exc), "findings": [{
                    "category": "INVALID_ASSERTION", "requirement": "Executable contract-compliant testbench",
                    "evidence": str(exc), "recommended_change": "Correct this validator failure while preserving existing file and function names."}]}
        import ast
        inventory = []
        for field, owner in (("test_files", "tests"), ("reference_files", "reference")):
            for item in candidate[field]:
                try:
                    tree = ast.parse(item['content'])
                except SyntaxError:
                    inventory.append({'path': owner + '/' + Path(item['path']).name, 'test_functions': [],
                                      'assertions': 0, 'source_check': 'SYNTAX_ERROR', 'functional_result': 'NOT_RUN'})
                    continue
                tests = [n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)
                         and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                                 and d.func.attr == 'test' for d in n.decorator_list)]
                inventory.append({"path": owner + '/' + Path(item['path']).name, "test_functions": tests,
                                  "assertions": sum(isinstance(n, ast.Assert) for n in ast.walk(tree)),
                                  "source_check": result['status'], "functional_result": "NOT_RUN"})
        write_json(WORKSPACE_ROOT / "verification" / "testbench-checks.json",
                   {"status": result['status'], "files": inventory, "definition_hashes": definition_hashes,
                    "scope": "STATIC_SOURCE_AND_CONTRACT_CHECKS", "simulation_pass": False})
        report = {"review": result, "definition_hashes": definition_hashes,
                  "scope": "STATIC_SOURCE_AND_CONTRACT_CHECKS",
                  "simulation_pass": False, "stimulus_reviewed": runtime is not None}
        write_json(
            WORKSPACE_ROOT / "verification" /
            f"verifier-review-av{version}-ar{architecture_revision}-r{state.get('repair_iteration', 0)}-v{revision}.json",
            report,
        )
        return {"verifier_review_status": result["status"], "verifier_review_result": result,
                "verifier_review_hashes": definition_hashes,
                "verification_status": "PENDING",
                "history": [{"stage": "testbench_checks", "status": result["status"],
                             "findings": result["findings"], "stimulus_reviewed": runtime is not None}]}

    return review_node
