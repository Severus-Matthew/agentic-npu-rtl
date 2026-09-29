from __future__ import annotations

import json
from pathlib import Path

import yaml

from multigent.agents.verifier import VerifierAgent
from multigent.orchestration import artifacts, verifier_review_node
from multigent.orchestration.routes import route_after_verifier_review, route_start
from multigent.verifier_tool.tool_regression.integration.test_verifier import generic_fir_context, verification_ready_result


def repair():
    return {
        "status": "VERIFIER_REPAIR_REQUIRED",
        "summary": "Missing output count check",
        "findings": [{
            "category": "MISSING_ASSERTION",
            "requirement": "No extra output",
            "evidence": "Sink returns after expected count without a continuing checker",
            "recommended_change": "Keep independent output accounting active",
        }],
    }


def test_review_routes_use_existing_budgets():
    approved = {
        "verifier_review_status": "APPROVED",
        "verifier_revision": 0,
        "max_verifier_revisions": 2,
        "rtl_status": "RTL_GENERATED",
    }
    assert route_after_verifier_review(approved) == "verification_tools"
    rejected = {**approved, "verifier_review_status": "VERIFIER_REPAIR_REQUIRED"}
    assert route_after_verifier_review(rejected) == "verification_repair"
    rejected["verifier_revision"] = 2
    assert route_after_verifier_review(rejected) == "failed"


def test_saved_unreviewed_tb_resumes_at_deterministic_review():
    state = {
        "architecture_status": "READY",
        "rtl_status": "RTL_GENERATED",
        "verifier_status": "VERIFICATION_READY",
        "verification_plan": {"top_module": "top"},
    }
    assert route_start(state) == "verifier_review"
    state["verifier_review_status"] = "APPROVED"
    assert route_start(state) == "verification_tools"


def test_definition_repair_uses_generic_deterministic_local_patch(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "build_verification_context", lambda **kw: generic_fir_context())
    update = artifacts.verification_repair_node({
        "user_request": "fir",
        "architecture_dir": str(tmp_path),
        "verifier_review_status": "VERIFIER_REPAIR_REQUIRED",
        "verifier_review_result": repair(),
        "verifier_result": verification_ready_result(),
        "verifier_revision": 1,
        "verification_evidence": {"stdout": "RTL_EXECUTION_SECRET"},
    })
    feedback = update["verification_context"]["deterministic_validation_review"]
    assert feedback["findings"] == repair()["findings"]
    assert feedback["previous_verifier_output"]["test_files"]
    assert "exact local source patches" in feedback["instruction"]
    assert "RTL_EXECUTION_SECRET" not in json.dumps(update)
    assert update["verifier_revision"] == 2
    assert update["verifier_review_status"] == "PENDING"


def test_deterministic_stimulus_finding_reaches_verifier_patch_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "build_verification_context", lambda **kw: generic_fir_context())
    finding = {
        "category": "MISSING_STIMULUS",
        "requirement": "Each checked stimulus needs a distinct DUT observation",
        "evidence": (
            "Stimulus 'second' has no await since stimulus 'first'; "
            "targets=['channel.a.stall_stability']"
        ),
        "recommended_change": "Present valid and payload before ready; measure actual stalls",
    }
    draft = verification_ready_result()
    update = artifacts.verification_repair_node({
        "user_request": "fir",
        "architecture_dir": str(tmp_path),
        "verifier_review_status": "VERIFIER_REPAIR_REQUIRED",
        "verifier_review_result": {
            "status": "VERIFIER_REPAIR_REQUIRED", "findings": [finding],
        },
        "verifier_result": draft,
    })
    prompt = VerifierAgent._build_review_patch_task(update["verification_context"], draft)
    envelope = yaml.safe_load(
        prompt.split("FROZEN INPUT, FINDINGS, AND EXISTING SOURCES\n", 1)[1]
    )
    assert envelope["review_findings"] == [{"index": 0, **finding}]
    assert envelope["files"][0]["path"].startswith("reference/")


def test_review_node_is_read_only_and_never_calls_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(verifier_review_node, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(
        verifier_review_node,
        "build_verification_context",
        lambda **kw: generic_fir_context(),
    )
    candidate = VerifierAgent._with_contract_generated_blocks(
        verification_ready_result(), generic_fir_context()
    )
    for field, owner in (("test_files", "tests"), ("reference_files", "reference")):
        (tmp_path / owner).mkdir()
        for item in candidate[field]:
            content = item["content"] if item["content"].endswith("\n") else item["content"] + "\n"
            (tmp_path / owner / Path(item["path"]).name).write_text(content)

    class Reviewer:
        def review(self, *args, **kwargs):
            raise AssertionError("LLM reviewer must not be called")

    state = {
        "user_request": "fir",
        "verifier_status": "VERIFICATION_READY",
        "verifier_result": candidate,
        "history": [],
        "architecture_dir": str(tmp_path / "architecture"),
    }
    update = artifacts.guarded(
        "verifier_review", verifier_review_node.make_verifier_review_node(Reviewer())
    )(state)
    assert "orchestration_error" not in update
    assert update["verification_status"] == "PENDING"
    report = json.loads(next((tmp_path / "verification").glob("verifier-review-*.json")).read_text())
    assert report["review_mode"] == "DETERMINISTIC"
    assert report["simulation_pass"] is False
