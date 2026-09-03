from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent


def test_equivalent_test_module_references_canonicalize() -> None:
    assert VerifierAgent._canonical_test_module("test_core") == "test_core"
    assert VerifierAgent._canonical_test_module("test_core.py") == "test_core"
    assert VerifierAgent._canonical_test_module("tests/test_core.py") == "test_core"
    assert VerifierAgent._canonical_test_module("tests.test_core") == "test_core"


def test_plan_module_references_are_normalized_in_place() -> None:
    plan = {
        "test_modules": ["tests/test_core.py", "test_protocol.py"],
        "regression_groups": {
            "smoke": ["tests.test_core"],
            "targeted": ["test_core.py", "tests/test_protocol.py"],
            "full": ["tests/test_core.py", "test_protocol"],
        },
    }

    VerifierAgent._normalize_plan_test_modules(plan)

    assert plan["test_modules"] == ["test_core", "test_protocol"]
    assert plan["regression_groups"]["smoke"] == ["test_core"]
    assert plan["regression_groups"]["targeted"] == ["test_core", "test_protocol"]
    assert plan["regression_groups"]["full"] == ["test_core", "test_protocol"]


def test_nested_or_cross_owned_module_reference_is_rejected() -> None:
    with pytest.raises(AgentRuntimeError):
        VerifierAgent._canonical_test_module("other/test_core.py")


def test_duplicate_equivalent_module_references_are_rejected() -> None:
    plan = {
        "test_modules": ["test_core", "tests/test_core.py"],
        "regression_groups": {
            "smoke": ["test_core"],
            "targeted": ["test_core"],
            "full": ["test_core"],
        },
    }
    with pytest.raises(AgentRuntimeError, match="duplicate module references"):
        VerifierAgent._normalize_plan_test_modules(plan)
