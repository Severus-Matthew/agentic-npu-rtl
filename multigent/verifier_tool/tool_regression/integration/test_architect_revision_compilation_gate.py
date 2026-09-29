"""The Architect's local-revision path applies the same compile-time contract gate.

A revision returns a bounded patch, the patched contract is re-validated, and only then
persisted. These tests pin how the new compile-time defects behave on that path,
including the consequence a caller must know: a local patch can flip a scalar policy
choice but can neither add nor remove a whole declaration or list entry, so a defect
whose only fix is structural surfaces as a precise contract error, never a silent gap.
"""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from multigent.agents.architect import ArchitectAgent, ContractValidationError
from multigent.agents.base import AgentRuntimeError
from multigent.orchestration.architect_node import _run_architect_revision
from multigent.verifier_tool.tool_regression.integration.test_architect import FakeArchitectAgent


def _setup(tmp_path, monkeypatch, patch, previous=None):
    previous = previous or FakeArchitectAgent().run_structured()
    output = tmp_path / "architecture"
    output.mkdir()
    (output / "architect_result.json").write_text(json.dumps(previous))
    agent = ArchitectAgent()
    monkeypatch.setattr(agent, "run_structured", lambda **_: patch)
    return agent, output, previous


def _revise(agent, output):
    return _run_architect_revision(
        agent, user_request="streaming FIR", feedback={"issue": "revision under test"},
        output_dir=output, run_id="gate-r1",
    )


def _replace(path, value, reason="fix"):
    return {
        "status": "PATCH_READY", "issue": "targeted revision",
        "edits": [{"op": "replace", "path": path, "value_json": json.dumps(value), "reason": reason}],
    }


def _unchanged(output, previous):
    assert json.loads((output / "architect_result.json").read_text()) == previous
    assert not (output / "architecture_contract.yaml").exists(), "a rejected revision must persist nothing"


def test_a_benign_scalar_revision_still_passes_the_gate(tmp_path, monkeypatch):
    agent, output, previous = _setup(
        tmp_path, monkeypatch,
        _replace("/architecture_contract/design/description", "reworded description"),
    )
    result = _revise(agent, output)
    assert result["architecture_contract"]["design"]["description"] == "reworded description"
    assert (output / "architecture_contract.yaml").exists()


def test_flipping_a_policy_choice_to_control_plane_sequence_demands_the_declaration(tmp_path, monkeypatch):
    # The scalar flip is a legal patch, but the declaration it now requires is a whole
    # object a local patch cannot add: the gate says exactly that, and persists nothing.
    agent, output, previous = _setup(
        tmp_path, monkeypatch,
        _replace(
            "/architecture_contract/operations/name=filter/lifecycle_policy/job_acceptance",
            "control_plane_sequence",
        ),
    )
    with pytest.raises(ContractValidationError) as raised:
        _revise(agent, output)
    assert "[control_plane_sequence_required_but_missing]" in str(raised.value)
    assert "lifecycle_control_plane_sequence" in str(raised.value)
    _unchanged(output, previous)


def test_a_patch_may_not_add_the_missing_declaration(tmp_path, monkeypatch):
    patch = {
        "status": "PATCH_READY", "issue": "add the declaration",
        "edits": [{
            "op": "add",
            "path": "/architecture_contract/operations/name=filter/lifecycle_control_plane_sequence",
            "value_json": json.dumps({"registers": {"c": {"address": 0}}, "job_start": {"actions": []}, "job_complete": {"actions": []}}),
            "reason": "declare it",
        }],
    }
    agent, output, previous = _setup(tmp_path, monkeypatch, patch)
    with pytest.raises(ContractValidationError, match="local patch rejected"):
        _revise(agent, output)
    _unchanged(output, previous)


def test_a_patch_that_makes_one_object_ride_two_channels_is_rejected_precisely_and_once(tmp_path, monkeypatch):
    agent, output, previous = _setup(
        tmp_path, monkeypatch,
        _replace("/interface_contract/channels/name=coefficients/data_objects/0", "sample_stream"),
    )
    with pytest.raises(ContractValidationError) as raised:
        _revise(agent, output)
    text = str(raised.value)
    assert text.count("[ambiguous_transport_binding]") == 1 and "'sample_stream'" in text
    # The object the patch stopped carrying is reported by the Architect's own validator.
    assert "coefficient_vector is not carried by any interface channel" in text
    _unchanged(output, previous)


def test_confirming_a_contract_that_already_carries_a_binding_defect_is_rejected(tmp_path, monkeypatch):
    # Older frozen contracts may hide a defect the compile used to swallow (the operation
    # silently vanished). Any revision -- even a no-edit confirmation -- now surfaces it.
    previous = FakeArchitectAgent().run_structured()
    next(item for item in previous["interface_contract"]["channels"] if item["name"] == "coefficients")[
        "data_objects"
    ].append("sample_stream")
    agent, output, _ = _setup(
        tmp_path, monkeypatch,
        {"status": "CONTRACT_CONFIRMED", "edits": [], "issue": "existing behavior is unambiguous"},
        previous=previous,
    )
    with pytest.raises(ContractValidationError, match="ambiguous_transport_binding"):
        _revise(agent, output)


def test_a_tool_limit_never_fails_a_revision(tmp_path, monkeypatch):
    previous = FakeArchitectAgent().run_structured()
    architecture = previous["architecture_contract"]
    architecture["data_objects"].append({
        "name": "scratch", "role": "intermediate", "data_type": architecture["data_types"][0]["name"],
        "dimensions": [], "producer": "filter", "consumers": ["filter"], "external": False,
        "serialization": {"kind": "scalar", "index_order": [], "description": "one value"},
    })
    architecture["operations"][0]["inputs"].append("scratch")
    architecture["operations"][0]["outputs"].append("scratch")
    agent, output, _ = _setup(
        tmp_path, monkeypatch,
        {"status": "CONTRACT_CONFIRMED", "edits": [], "issue": "existing behavior is unambiguous"},
        previous=previous,
    )
    result = _revise(agent, output)
    assert result == previous


def test_the_relaxed_revision_flags_do_not_relax_a_blocking_compile_defect():
    result = FakeArchitectAgent().run_structured()
    next(item for item in result["interface_contract"]["channels"] if item["name"] == "coefficients")[
        "data_objects"
    ].append("sample_stream")
    for require in (True, False):
        with pytest.raises(AgentRuntimeError, match="ambiguous_transport_binding"):
            ArchitectAgent._validate_contract_references(
                deepcopy(result), require_lifecycle_policy=require, require_operation_arithmetic=require,
            )
