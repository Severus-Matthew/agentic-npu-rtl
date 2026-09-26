from __future__ import annotations

from multigent.verifier_tool.benchmark.int8_gemm_hls_golden.batch_qualify_mutants import (
    validate_registry,
)
from multigent.verifier_tool.benchmark.int8_gemm_hls_golden.prepare_qualification_catalog import (
    build_catalog,
)
from multigent.verifier_tool.benchmark.int8_gemm_hls_golden.qualify_named_mutant import (
    MUTANTS,
)


def test_every_named_hls_mutant_has_exact_reviewable_anchors() -> None:
    findings = validate_registry(sorted(MUTANTS))
    assert len(findings) >= 40
    assert {item["status"] for item in findings} == {"READY"}
    assert all(item["edits"] for item in findings)
    assert all(
        edit["anchor_count"] == edit["expected_anchor_count"]
        for item in findings
        for edit in item["edits"]
    )


def test_hls_qualification_catalog_covers_every_matrix_target_once() -> None:
    catalog = build_catalog()
    cases = catalog["cases"]
    identities = [(item["target_type"], item["feature_id"]) for item in cases]
    assert len(cases) == 162
    assert len(identities) == len(set(identities))
    assert catalog["summary"]["registry_ready"] == len(MUTANTS)

    allowed_preparation = {
        "qualified",
        "named_registry",
        "recipe_prepared",
        "topology_excluded",
        "checker_alias_review",
        "requires_harness_support",
    }
    assert {
        item["preparation"] for item in cases
    } <= allowed_preparation
    assert all(item.get("recipe") for item in cases)
