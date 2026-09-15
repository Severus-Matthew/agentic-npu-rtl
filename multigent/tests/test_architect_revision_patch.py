import copy
import json

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.orchestration.architect_node import _run_architect_revision
from multigent.orchestration import architect_node as architect_node_module
from multigent.orchestration.architect_revision_patch import (
    RevisionPatchError, apply_architect_revision_patch,
)
from multigent.orchestration.routes import route_after_verifier_review


@pytest.fixture
def previous():
    return {
        "status": "READY", "conflicts": [],
        "architecture_contract": {
            "design": {"name": "example"},
            "operations": [{"name": "gemm", "kind": "matrix", "features": ["dimensions"]}],
            "parameters": [{"name": "MAX_M", "default_value": "64"}],
            "control": {"error_behavior": "dimension above bound aborts"},
            "latency_model": "bounded",
        },
        "interface_contract": {
            "channels": [{"name": "cmd", "direction": "input", "framing": "one beat"}],
            "signals": [{"name": "cmd_ready", "role": "ready", "direction": "output",
                         "reset_value": 1}],
        },
        "module_manifest": {"top": "example", "modules": [{"name": "example"}]},
        "acceptance_criteria": {"verification": ["test legal command"]},
    }


def _patch(*edits):
    return {"status": "PATCH_READY", "issue": "", "edits": [
        {"op": op, "path": path, "value_json": json.dumps(value),
         "reason": "directly requested by Verifier"}
        for op, path, value in edits
    ]}


def test_leaf_patch_preserves_every_other_contract_field(previous):
    before = copy.deepcopy(previous)
    result = apply_architect_revision_patch(previous, {"issue": "reset cmd_ready timing"},
        _patch(("replace", "/interface_contract/signals/name=cmd_ready/reset_value", 0)))
    assert result["interface_contract"]["signals"][0]["reset_value"] == 0
    assert result["architecture_contract"] == before["architecture_contract"]
    assert result["module_manifest"] == before["module_manifest"]
    assert previous == before


@pytest.mark.parametrize("path,value", [
    ("/architecture_contract/design/name", "new_design"),
    ("/architecture_contract/operations/name=gemm/name", "fft"),
    ("/module_manifest/top", "new_top"),
    ("/architecture_contract/control", {"error_behavior": "new design"}),
    ("/architecture_contract/parameters/name=MAX_M/default_value", "16"),
])
def test_unrelated_or_wholesale_rewrites_are_rejected(previous, path, value):
    with pytest.raises(RevisionPatchError):
        apply_architect_revision_patch(previous, {"issue": "reset command timing"},
                                       _patch(("replace", path, value)))


def test_feedback_related_parameter_bound_can_change_locally(previous):
    result = apply_architect_revision_patch(previous,
        {"issue": "MAX_M dimension encoding cannot represent values above bound"},
        _patch(("replace", "/architecture_contract/parameters/name=MAX_M/default_value", "63")))
    assert result["architecture_contract"]["parameters"][0]["default_value"] == "63"
    assert result["module_manifest"] == previous["module_manifest"]


def test_named_contract_collections_reject_fragile_numeric_indices(previous):
    with pytest.raises(RevisionPatchError, match="stable name="):
        apply_architect_revision_patch(
            previous, {"issue": "reset cmd_ready timing"},
            _patch(("replace", "/interface_contract/signals/0/reset_value", 0)),
        )


def test_pipeline_stage_selector_locally_repairs_existing_stage(previous):
    previous["architecture_contract"]["pipeline"] = [
        {"stage": "FINALIZE", "responsibility": "write serializer"},
        {"stage": "OUTPUT", "responsibility": "transfer result"},
    ]
    result = apply_architect_revision_patch(
        previous, {"issue": "FINALIZE serializer handoff timing"},
        _patch(("replace", "/architecture_contract/pipeline/stage=FINALIZE/responsibility",
                "write a registered output")),
    )
    assert result["architecture_contract"]["pipeline"][0]["responsibility"] == "write a registered output"
    assert result["architecture_contract"]["pipeline"][1] == previous["architecture_contract"]["pipeline"][1]
    with pytest.raises(RevisionPatchError, match="stable stage="):
        apply_architect_revision_patch(
            previous, {"issue": "FINALIZE timing"},
            _patch(("replace", "/architecture_contract/pipeline/0/responsibility", "other")),
        )


def test_revision_prompt_contains_previous_contract_and_uses_patch_schema(tmp_path, previous):
    output_dir = tmp_path / "architecture"
    output_dir.mkdir()
    (output_dir / "architect_result.json").write_text(json.dumps(previous), encoding="utf-8")

    class FakePatchArchitect:
        def __init__(self):
            self.task = None
            self.schema_path = None

        def _build_architecture_task(self, intake):
            assert intake["previous_contract"] == previous
            return json.dumps(intake)

        def run_structured(self, *, task, schema_path, log_name):
            self.task = task
            self.schema_path = schema_path
            return {"status": "SPEC_CONFLICT", "edits": [], "issue": "cannot locally repair"}

        def _write_json(self, path, value):
            path.write_text(json.dumps(value), encoding="utf-8")

    agent = FakePatchArchitect()
    result = _run_architect_revision(agent, user_request="GEMM NPU",
        feedback={"issue": "reset cmd_ready timing"}, output_dir=output_dir, run_id="test-r1")
    assert result["status"] == "SPEC_CONFLICT"
    assert agent.schema_path.name == "architect_revision_patch.schema.json"
    assert "previous_contract" in agent.task
    assert "Return ONLY a local patch" in agent.task


@pytest.mark.parametrize("patch_result", [
    {"status": "PATCH_READY", "edits": [], "issue": ""},
    {"status": "CONTRACT_CONFIRMED", "edits": [{"op": "replace", "path": "/x", "value_json": "1",
                                                 "reason": "r"}], "issue": "unused"},
    {"status": "CONTRACT_CONFIRMED", "edits": [], "issue": ""},
    {"status": "SPEC_CONFLICT", "edits": [{"op": "replace", "path": "/x", "value_json": "1",
                                            "reason": "r"}], "issue": "unused"},
    {"status": "SPEC_CONFLICT", "edits": [], "issue": "   "},
])
def test_status_conditional_rules_are_enforced_without_schema_allof(
    tmp_path, previous, patch_result,
):
    # These rules used to live in the response schema's allOf/if/then, which
    # OpenAI's structured output API rejects; the Architect node enforces them
    # in Python instead (see architect_node.py).
    output_dir = tmp_path / "architecture"
    output_dir.mkdir()
    (output_dir / "architect_result.json").write_text(json.dumps(previous), encoding="utf-8")

    class FakePatchArchitect:
        def _build_architecture_task(self, intake):
            return "task"

        def run_structured(self, *, task, schema_path, log_name):
            return patch_result

        def _write_json(self, path, value):
            path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(AgentRuntimeError):
        _run_architect_revision(FakePatchArchitect(), user_request="GEMM NPU",
            feedback={"issue": "reset cmd_ready timing"}, output_dir=output_dir, run_id="test-r1")


def test_architect_revision_preserves_existing_rtl_and_routes_review_to_contract_fix(
    monkeypatch, tmp_path, previous,
):
    revision_patch = _patch(("replace", "/architecture_contract/latency_model", "fixed"))
    def fake_revision(*args, **kwargs):
        output_dir = kwargs["output_dir"]
        run_id = kwargs["run_id"]
        (output_dir / f"revision_patch-{run_id}.json").write_text(
            json.dumps(revision_patch), encoding="utf-8"
        )
        return previous
    monkeypatch.setattr(
        architect_node_module, "_run_architect_revision",
        fake_revision,
    )
    monkeypatch.setattr(
        architect_node_module, "build_rtl_context",
        lambda **kwargs: {"frozen_architecture": "v2"},
    )
    update = architect_node_module.make_architect_node(object())({
        "run_id": "reuse", "user_request": "GEMM", "architecture_dir": str(tmp_path),
        "architecture_version": 1, "architecture_revision": 0,
        "architecture_conflict": {"issue": "completion timing"},
        "rtl_status": "RTL_GENERATED", "rtl_files": ["example.sv"],
        "rtl_result": {"status": "RTL_GENERATED"}, "rtl_contract_version": 1,
    })
    assert update["architecture_version"] == 2
    assert update["rtl_status"] == "RTL_GENERATED"
    assert update["rtl_files"] == ["example.sv"]
    assert update["rtl_contract_version"] == 1
    assert update["rtl_task_type"] == "CONTRACT_FIXED"
    assert update["rtl_feedback"]["source"] == "architect_contract_patch"
    assert update["rtl_feedback"]["previous_contract_version"] == 1
    assert update["rtl_feedback"]["current_contract_version"] == 2
    assert update["history"][0]["rtl_preserved"] is True
    reviewed = update | {
        "verifier_status": "VERIFICATION_READY",
        "verification_plan": {"top_module": "top"},
        "verifier_review_status": "APPROVED",
    }
    assert route_after_verifier_review(reviewed) == "rtl_generator"


def test_initial_architecture_still_requires_initial_rtl_generation(monkeypatch, tmp_path, previous):
    class InitialArchitect:
        def run(self, *args, **kwargs):
            return previous
    monkeypatch.setattr(
        architect_node_module, "build_rtl_context",
        lambda **kwargs: {"frozen_architecture": "v1"},
    )
    update = architect_node_module.make_architect_node(InitialArchitect())({
        "run_id": "initial", "user_request": "GEMM", "architecture_dir": str(tmp_path),
        "architecture_version": 0, "architecture_revision": 0,
        "rtl_status": "PENDING", "rtl_files": [],
    })
    assert update["rtl_status"] == "PENDING"
    assert update["rtl_files"] == []
    assert update["rtl_contract_version"] == 0
    assert update["rtl_task_type"] == "INITIAL_GENERATION"


def test_architect_can_confirm_existing_contract_without_version_or_rtl_change(
    monkeypatch, tmp_path, previous,
):
    confirmation = {
        "status": "CONTRACT_CONFIRMED",
        "edits": [],
        "issue": (
            "/interface_contract/channels/name=cmd/framing already defines one beat; "
            "no contract amendment is required"
        ),
    }

    def fake_revision(*args, **kwargs):
        output_dir = kwargs["output_dir"]
        run_id = kwargs["run_id"]
        (output_dir / f"revision_patch-{run_id}.json").write_text(
            json.dumps(confirmation), encoding="utf-8"
        )
        return previous

    monkeypatch.setattr(architect_node_module, "_run_architect_revision", fake_revision)
    monkeypatch.setattr(
        architect_node_module,
        "build_rtl_context",
        lambda **kwargs: {"frozen_architecture": "unchanged"},
    )
    monkeypatch.setattr(
        architect_node_module,
        "build_verification_context",
        lambda **kwargs: {
            "user_request": "GEMM",
            "verification_policy": {},
            "frozen_architecture": {},
            "provenance": {
                "includes_generated_rtl": False,
                "includes_rtl_generator_output": False,
            },
        },
    )
    question = {"issue": "Is command framing defined?"}
    update = architect_node_module.make_architect_node(object())({
        "run_id": "confirm", "user_request": "GEMM",
        "architecture_dir": str(tmp_path), "architecture_version": 3,
        "architecture_revision": 1, "architecture_conflict": question,
        "rtl_status": "RTL_GENERATED", "rtl_files": ["example.sv"],
        "rtl_result": {"status": "RTL_GENERATED"}, "rtl_contract_version": 3,
    })

    assert update["architecture_version"] == 3
    assert update["architecture_revision"] == 2
    assert update["rtl_task_type"] == "CONTRACT_UNCHANGED"
    assert update["rtl_files"] == ["example.sv"]
    assert update["rtl_feedback"]["current_contract_version"] == 3
    assert update["verification_context"]["architect_resolution"]["decision"] == "CONTRACT_CONFIRMED"
    assert update["verification_context"]["architect_resolution"]["verifier_question"] == question
    assert update["history"][0]["architect_decision"] == "CONTRACT_CONFIRMED"
