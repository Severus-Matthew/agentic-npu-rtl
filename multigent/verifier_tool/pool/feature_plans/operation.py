"""Operation Feature Plan: resolve known mathematical feature concepts."""

from __future__ import annotations

from typing import Any, Mapping

from .catalog import (
    load_operation_feature_catalog,
    operation_feature_selections,
    operation_optional_concepts,
)
from .common import feature_record, safe_id
from .schema import validate_resolved_feature_plan


def build_operation_feature_plan(
    architecture_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Resolve catalog operation concepts into three explicit sibling branches."""

    from multigent.verifier_tool.operation.coverage.plan import (
        load_operation_coverage_families,
    )

    feature_catalog = load_operation_feature_catalog()
    catalog = load_operation_coverage_families()["families"]
    defaults = feature_catalog["feature_defaults"]
    features: list[dict[str, Any]] = []
    if architecture_contract:
        for operation in architecture_contract.get("operations", []):
            if not isinstance(operation, Mapping):
                continue
            family = str(operation.get("coverage_family", ""))
            if (
                operation.get("coverage_family_source") != "catalog"
                or family not in catalog
            ):
                continue
            known = set(catalog[family]["baseline_concepts"]) | set(
                operation_optional_concepts(catalog[family])
            )
            parents = {
                concept: group_name
                for group_name, group in catalog[family].get("feature_groups", {}).items()
                for concept in group["optional_concepts"]
            }
            name = str(operation.get("name", ""))
            operation_id = safe_id(name)
            baseline, extensions = operation_feature_selections(operation)
            for concept in [*baseline, *extensions]:
                concept = str(concept)
                if concept not in known:
                    continue
                features.append(
                    feature_record(
                        feature_id=f"operation.{operation_id}.{safe_id(concept)}",
                        domain="operation",
                        kind="catalog_operation_concept",
                        scope="operation",
                        scope_name=name,
                        bindings={
                            "operation_name": name,
                            "coverage_family": family,
                            "concept": concept,
                            **({"feature_group": parents[concept]} if concept in parents else {}),
                        },
                        tags=("operation_feature", "mathematical_correctness"),
                        assertion_checker=str(defaults["assertion"]["checker"]),
                        coverage={
                            **defaults["coverage"],
                            "concept": concept,
                            "family": family,
                        },
                        stimulus_strategy=str(defaults["stimulus"]["strategy"]),
                        stimulus=defaults["stimulus"],
                    )
                )
    features.sort(key=lambda item: str(item["id"]))
    return validate_resolved_feature_plan({
        "schema_version": 1,
        "domain": "operation",
        "source": "frozen operation metadata + verifier_tool operation family catalog",
        "features": features,
    })


__all__ = ["build_operation_feature_plan"]
