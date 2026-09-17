"""Read-only contract approval bound to the exact architecture artifacts."""
from pathlib import Path
from multigent.agents.contract_reviewer import ContractReviewerAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context
from multigent.tools.vivado import write_json
from .artifacts import hashes


def make_contract_review_node(agent=None):
    runtime = agent or ContractReviewerAgent()

    def review(state):
        directory = Path(state.get("architecture_dir", WORKSPACE_ROOT / "architecture"))
        context = build_verification_context(user_request=state["user_request"], architecture_dir=directory)
        context["previous_contract_review"] = state.get("contract_review_result")
        context["architect_revision_patch"] = state.get("architecture_revision_patch")
        result = runtime.review(context, run_id=f"{state['run_id']}-av{state.get('architecture_version',0)}-ar{state.get('architecture_revision',0)}")
        ContractReviewerAgent.validate_result(result)
        artifact_hashes = hashes(directory)
        write_json(WORKSPACE_ROOT / "contract_reviews" / f"review-{len(state.get('history',[])):04d}.json",
                   {"review": result, "architecture_hashes": artifact_hashes})
        update = {"contract_review_status": result["status"], "contract_review_result": result,
                  "contract_review_hashes": artifact_hashes if result["status"] == "APPROVED" else {},
                  "history": [{"stage":"contract_reviewer", "status":result["status"], "findings":result["findings"]}]}
        if result["status"] == "APPROVED":
            update["contract_review_revision"] = 0
        if result["status"] == "REVISION_REQUIRED":
            update["contract_review_revision"] = state.get("contract_review_revision",0) + 1
            update["architecture_conflict"] = {"source":"contract_reviewer", **result}
        return update
    return review


def route_after_contract_review(state):
    if state.get("contract_review_status") == "APPROVED":
        return "generation_start"
    if state.get("contract_review_revision",0) <= state.get("max_contract_review_revisions",3):
        return "architect"
    return "repair_exhausted"
