"""Regression checks for the stable qualification-ledger inventory."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from multigent.verifier_tool.tool_regression.qualification.build_ledger import (
    LEDGER_PATH,
    POLICY_CHOICES,
    PROFILES,
    PROTOCOL_DRIVER_INVARIANTS,
    PROTOCOL_FEATURE_BINS,
    LIFECYCLE_ROWS,
    OPERATION_BINS,
    OPERATION_FAMILY_BINS,
    STANDARD_RULES,
    TAGS,
    build_all_rows,
)
from multigent.verifier_tool.tool_regression.paths import VERIFIER_TOOL_ROOT


def test_generic_ready_valid_reset_is_tracked_as_an_explicit_policy() -> None:
    generated = {row["id"]: row for row in build_all_rows()}
    assert "rule:ready_valid.valid_low_during_reset" not in generated
    assert "policy:channel_reset_behavior.valid_deasserted" in generated
    assert "rule:explicit_generic_channel_reset.valid_deasserted" in generated
    assert len(generated) == 323


def test_committed_ledger_matches_the_generated_inventory() -> None:
    document = json.loads(LEDGER_PATH.read_text())
    generated_ids = {row["id"] for row in build_all_rows()}
    stored_ids = {row["id"] for row in document["rows"]}
    assert stored_ids == generated_ids
    assert document["runtime_target_count"] == 232
    assert document["metadata_entry_count"] == 91
    assert document["total_rows"] == 323


def test_explicit_channel_reset_policy_has_strict_fault_fix_evidence() -> None:
    document = json.loads(LEDGER_PATH.read_text())
    rows = {row["id"]: row for row in document["rows"]}
    policy = rows["policy:channel_reset_behavior.valid_deasserted"]
    assert policy["status"] == "STRICT_PASS"
    assert policy["detection_mechanism"] == "named_assertion_checker"
    assert policy["evidence_paths"] == [
        "multigent/verifier_tool/tool_regression/rtl/"
        "test_ready_valid_reset_channel_policy.py"
    ]


def test_hand_transcribed_inventory_matches_live_pool_sources() -> None:
    """Prevent another pool addition from silently escaping the audit ledger."""

    pool = VERIFIER_TOOL_ROOT / "pool"
    tags = yaml.safe_load((pool / "tag_pool" / "verification_tags.yaml").read_text())
    profiles = yaml.safe_load(
        (pool / "role_pool" / "interface_protocol_profiles.yaml").read_text()
    )
    protocols = yaml.safe_load(
        (pool / "role_pool" / "standard_protocols.yaml").read_text()
    )["profiles"]
    policies = yaml.safe_load(
        (pool / "lifecycle_policy_pool" / "lifecycle_policies.yaml").read_text()
    )
    protocol_features = yaml.safe_load(
        (pool / "feature_plans" / "protocol_features.yaml").read_text()
    )
    lifecycle_features = yaml.safe_load(
        (pool / "feature_plans" / "lifecycle_features.yaml").read_text()
    )
    operation_features = yaml.safe_load(
        (pool / "feature_plans" / "operation_features.yaml").read_text()
    )

    assert {name for name, _domains in TAGS} == set(tags["tags"])
    assert set(PROFILES) == set(profiles["protocol_profiles"])
    assert STANDARD_RULES == {
        name: list(spec.get("rules", []))
        for name, spec in protocols.items()
        if spec.get("rules")
    }
    assert PROTOCOL_DRIVER_INVARIANTS == {
        name: list(spec.get("driver_invariants", []))
        for name, spec in protocols.items()
        if spec.get("driver_invariants")
    }
    source_policy_choices = {
        (field, choice)
        for field, spec in policies["policies"].items()
        for choice in spec["choices"]
    } | {
        ("channel_reset_behavior", choice)
        for choice in policies["channel_reset_behaviors"]
    }
    assert set(POLICY_CHOICES) == source_policy_choices

    source_protocol_bins: list[tuple[str, list[str]]] = []
    for section in ("derived_features", "features"):
        for name, spec in protocol_features[section].items():
            bins = []
            for bin_spec in spec.get("coverage", {}).get("bins", []):
                label = str(bin_spec["name"])
                if bin_spec.get("required", True) is False:
                    label += " (diagnostic)"
                bins.append(label)
            source_protocol_bins.append(
                (f"{section}.{name}", bins or ["assertion-only"])
            )
    assert dict(PROTOCOL_FEATURE_BINS) == dict(source_protocol_bins)

    source_lifecycle_rows: list[tuple[str, str, list[str]]] = []
    for name, spec in lifecycle_features["features"].items():
        source_lifecycle_rows.append((
            "features",
            name,
            [str(item["name"]) for item in spec["coverage"]["bins"]],
        ))
    for name in lifecycle_features["operation_features"]:
        source_lifecycle_rows.append((
            "operation_features", name, ["assertion-only or dynamic obligation"]
        ))
    for name, spec in lifecycle_features["operation_coverage"].items():
        source_lifecycle_rows.append((
            "operation_coverage",
            name,
            [str(item["name"]) for item in spec["bins"]],
        ))
    assert LIFECYCLE_ROWS == source_lifecycle_rows

    source_operation_families: dict[str, list[tuple[str, list[str]]]] = {}
    for family_name, family in operation_features["families"].items():
        source_operation_bins = [
            (concept, list(family["starter_bins"][concept]))
            for concept in family["baseline_concepts"]
        ]
        for group_name, group in family.get("feature_groups", {}).items():
            source_operation_bins.extend(
                (
                    f"{group_name}.{concept}",
                    list(spec["starter_bins"]),
                )
                for concept, spec in group["optional_concepts"].items()
            )
        source_operation_families[family_name] = source_operation_bins
    assert OPERATION_FAMILY_BINS == source_operation_families
    assert OPERATION_BINS == source_operation_families["matrix_multiply"]
