"""Independent contract review; no RTL or testbench is placed in this prompt."""
import json
from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


class ContractReviewerAgent(APIAgent):
    def __init__(self, *, model=None, api_mode=None):
        defaults = AgentConfig(name="contract_reviewer", role_skill="contract-reviewer")
        super().__init__(AgentConfig(name=defaults.name, role_skill=defaults.role_skill,
                         model=model or defaults.model, api_mode=api_mode or defaults.api_mode))

    def review(self, context, *, run_id):
        # Explicit allowlist: callers cannot accidentally attach downstream code.
        envelope = {key: context[key] for key in ("user_request", "frozen_architecture")}
        for key in ("previous_contract_review", "architect_revision_patch"):
            if context.get(key) is not None:
                envelope[key] = context[key]
        result = self.run_structured(task="Review this architecture contract.\n" + json.dumps(envelope),
                   schema_path=SCHEMA_ROOT / "contract_review.schema.json",
                   log_name=f"contract-review-{run_id}.json")
        self.validate_result(result)
        return result

    @staticmethod
    def validate_result(result):
        if result.get("status") not in {"APPROVED", "REVISION_REQUIRED"}:
            raise AgentRuntimeError("Unknown contract review status")
        if bool(result.get("findings")) != (result["status"] == "REVISION_REQUIRED"):
            raise AgentRuntimeError("Contract review approval and findings disagree")
