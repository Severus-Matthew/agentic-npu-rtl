"""Compile lifecycle obligations from frozen role bindings and operation metadata."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

from multigent.verifier_tool.feature_plan import build_lifecycle_feature_plan
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_coverage_feature_plan,
)
from multigent.verifier_tool.pool.feature_plans.catalog import (
    LIFECYCLE_FEATURES_PATH,
    load_lifecycle_feature_catalog,
)


LIFECYCLE_COVERAGE_TEMPLATES_PATH = LIFECYCLE_FEATURES_PATH


@lru_cache(maxsize=1)
def load_lifecycle_coverage_templates() -> dict[str, Any]:
    raw = load_lifecycle_feature_catalog()
    return {**raw, "templates": raw["features"]}


def lifecycle_template_names() -> frozenset[str]:
    return frozenset(map(str, load_lifecycle_coverage_templates()["templates"]))


def build_lifecycle_coverage_plan(
    interface: Mapping[str, Any], operation_metadata: Mapping[str, Any]
) -> dict[str, Any]:
    """Build operation-scoped lifecycle obligations that need both contracts."""

    feature_plan = build_lifecycle_feature_plan(interface, operation_metadata)
    return {
        "schema_version": 2,
        "source": "verifier_tool lifecycle taxonomy",
        "feature_plan": feature_plan,
        "compiled_coverage": compile_coverage_feature_plan(feature_plan),
        "obligations": list(feature_plan["coverage_obligations"]),
    }
