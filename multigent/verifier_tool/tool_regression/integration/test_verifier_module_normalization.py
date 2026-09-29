from __future__ import annotations

import pytest

from multigent.agents.base import AgentRuntimeError
from multigent.agents.verifier import VerifierAgent


def test_equivalent_test_module_references_canonicalize() -> None:
    assert VerifierAgent._canonical_test_module("test_core") == "test_core"
    assert VerifierAgent._canonical_test_module("test_core.py") == "test_core"
    assert VerifierAgent._canonical_test_module("tests/test_core.py") == "test_core"
    assert VerifierAgent._canonical_test_module("tests.test_core") == "test_core"
    assert (
        VerifierAgent._canonical_test_module(
            "tests/test_core.py::test_backpressure"
        )
        == "test_core"
    )


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


def test_pytest_style_group_selectors_collapse_to_owning_cocotb_module() -> None:
    plan = {
        "test_modules": ["tests/test_gemm_bias_relu.py"],
        "regression_groups": {
            "smoke": [
                "tests/test_gemm_bias_relu.py::test_directed_basic_and_partial_tile"
            ],
            "targeted": [
                "tests/test_gemm_bias_relu.py::test_directed_basic_and_partial_tile",
                "tests/test_gemm_bias_relu.py::test_backpressure_all_channels",
            ],
            "full": [
                "tests/test_gemm_bias_relu.py::test_directed_basic_and_partial_tile",
                "tests/test_gemm_bias_relu.py::test_backpressure_all_channels",
                "tests/test_gemm_bias_relu.py::test_randomized_100_jobs",
            ],
        },
    }

    VerifierAgent._normalize_plan_test_modules(plan)

    assert plan["test_modules"] == ["test_gemm_bias_relu"]
    assert plan["regression_groups"]["smoke"] == ["test_gemm_bias_relu"]
    assert plan["regression_groups"]["targeted"] == ["test_gemm_bias_relu"]
    assert plan["regression_groups"]["full"] == ["test_gemm_bias_relu"]


def test_nested_or_cross_owned_module_reference_is_rejected() -> None:
    with pytest.raises(AgentRuntimeError):
        VerifierAgent._canonical_test_module("other/test_core.py")


def test_malformed_pytest_selector_is_rejected() -> None:
    with pytest.raises(AgentRuntimeError, match="Malformed verification test selector"):
        VerifierAgent._canonical_test_module("tests/test_core.py::")


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


def test_regression_group_cannot_reference_undeclared_module() -> None:
    plan = {
        "test_modules": ["test_core"],
        "regression_groups": {
            "smoke": ["test_other::test_x"],
            "targeted": ["test_core"],
            "full": ["test_core"],
        },
    }
    with pytest.raises(AgentRuntimeError, match="undeclared test modules"):
        VerifierAgent._normalize_plan_test_modules(plan)
