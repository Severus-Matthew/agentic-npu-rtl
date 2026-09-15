from pathlib import Path

import pytest

from multigent.agents.architect import ArchitectAgent, ContractValidationError
from multigent.agents.base import AgentRuntimeError
from multigent.orchestration.architect_node import make_architect_node
from multigent.orchestration.routes import route_after_architect


class InvalidArchitect(ArchitectAgent):
    def run(self, request, *, output_dir, run_id):
        output_dir.mkdir(parents=True, exist_ok=True)
        raise ContractValidationError("missing exact clock reference", {"status": "READY"})


def test_reference_failure_returns_candidate_for_bounded_repair(tmp_path: Path):
    update = make_architect_node(InvalidArchitect())({
        "user_request": "a stream accelerator", "architecture_dir": str(tmp_path),
    })
    assert update["architecture_status"] == "SEMANTIC_VALIDATION_FAILED"
    assert update["architecture_conflict"]["candidate_contract"] == {"status": "READY"}
    assert list(tmp_path.glob("rejected_contract*.json"))
    assert route_after_architect({**update, "max_architecture_revisions": 8}) == "architect"


@pytest.mark.parametrize("used,expected", [(7, "architect"), (8, "failed")])
def test_reference_repair_does_not_extend_architect_budget(used, expected):
    assert route_after_architect({
        "architecture_status": "SEMANTIC_VALIDATION_FAILED",
        "architecture_revision": used, "max_architecture_revisions": 8,
    }) == expected


def test_non_contract_runtime_error_is_not_reclassified(tmp_path):
    class BrokenAPI(InvalidArchitect):
        def run(self, *args, **kwargs):
            raise AgentRuntimeError("API unavailable")
    with pytest.raises(AgentRuntimeError, match="API unavailable"):
        make_architect_node(BrokenAPI())({
            "user_request": "accelerator", "architecture_dir": str(tmp_path),
        })
