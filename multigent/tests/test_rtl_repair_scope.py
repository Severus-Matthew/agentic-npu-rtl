from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.rtl_generator import RTLGeneratorAgent


def _feedback() -> dict:
    return {
        "frozen_verifier": True,
        "repair_plan": {
            "affected_modules": ["core"],
            "protected_modules": ["top", "streamer"],
        },
    }


def test_functional_repair_accepts_authorized_module_only() -> None:
    RTLGeneratorAgent._validate_authorized_change_scope(
        changed_modules={"core"},
        task_type="FUNCTIONAL_REPAIR",
        feedback=_feedback(),
    )


def test_functional_repair_rejects_unauthorized_module() -> None:
    with pytest.raises(AgentRuntimeError, match="outside Debugger authorization"):
        RTLGeneratorAgent._validate_authorized_change_scope(
            changed_modules={"core", "top"},
            task_type="FUNCTIONAL_REPAIR",
            feedback=_feedback(),
        )


def test_functional_repair_rejects_protected_module() -> None:
    feedback = _feedback()
    feedback["repair_plan"]["affected_modules"] = ["top"]
    with pytest.raises(AgentRuntimeError, match="protected modules"):
        RTLGeneratorAgent._validate_authorized_change_scope(
            changed_modules={"top"},
            task_type="FUNCTIONAL_REPAIR",
            feedback=feedback,
        )


def test_functional_repair_requires_frozen_verifier() -> None:
    feedback = _feedback()
    feedback["frozen_verifier"] = False
    with pytest.raises(AgentRuntimeError, match="preserve the frozen verifier"):
        RTLGeneratorAgent._validate_authorized_change_scope(
            changed_modules={"core"},
            task_type="FUNCTIONAL_REPAIR",
            feedback=feedback,
        )
