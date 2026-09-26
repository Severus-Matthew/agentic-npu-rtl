"""Rebuild finite taxonomy release artifacts from one frozen Architect contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    build_qualification_evidence,
    build_trial_manifest,
    load_qualification_catalog,
    merge_coverage_plans,
    operation_plan_for_tests,
    synthesize_code_owned_operation_coverage,
    validate_release_gate,
)


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a mapping in {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def build_release(
    frozen_architecture: Path,
    output_directory: Path,
    *,
    intended_trials: int,
    randomized_transactions_minimum: int,
    qualification_command: str,
    source_revision: str,
) -> dict[str, Any]:
    architecture = _yaml(frozen_architecture / "architecture_contract.yaml")
    interface = _yaml(frozen_architecture / "interface_contract.yaml")
    metadata = build_architect_operation_metadata(architecture, interface)
    unrepresentable = metadata.get("unrepresentable_operations", [])
    if unrepresentable:
        summary = "; ".join(
            f"{item['name']} [{item.get('reason_code', 'unclassified')}; "
            f"{item.get('category', 'unclassified')}; owner={item.get('owner', 'unknown')}]: "
            f"{item['reason']}"
            for item in unrepresentable
        )
        raise ValueError(
            "Refusing to build a taxonomy release that would silently drop "
            f"operations with no deterministic metadata: {summary}"
        )
    operation_specs = synthesize_code_owned_operation_coverage(
        [], architecture, metadata
    )
    operation_plan = operation_plan_for_tests(
        operation_specs,
        ["COVERAGE_OBLIGATIONS = set()\n"],
        architecture,
        interface,
    )
    combined = merge_coverage_plans(
        build_interface_coverage_plan(interface), operation_plan
    )
    verification_manifest = combined["verification_manifest"]
    trial_manifest = build_trial_manifest(
        architecture,
        interface,
        verification_manifest,
        intended_trials=intended_trials,
        randomized_transactions_minimum=randomized_transactions_minimum,
    )
    catalog = load_qualification_catalog()
    evidence = build_qualification_evidence(
        (str(item["id"]) for item in catalog["cases"]),
        command=qualification_command,
        source_revision=source_revision,
    )
    release_gate = validate_release_gate(
        trial_manifest, verification_manifest, evidence
    )
    _write(output_directory / "verification_manifest.json", verification_manifest)
    _write(output_directory / "trial_manifest.json", trial_manifest)
    _write(output_directory / "qualification_evidence.json", evidence)
    _write(output_directory / "release_gate.json", release_gate)
    return release_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-architecture", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--intended-trials", type=int, default=30)
    parser.add_argument("--randomized-transactions-minimum", type=int, default=100)
    parser.add_argument("--qualification-command", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = build_release(
        args.frozen_architecture,
        args.output_directory,
        intended_trials=args.intended_trials,
        randomized_transactions_minimum=args.randomized_transactions_minimum,
        qualification_command=args.qualification_command,
        source_revision=args.source_revision,
    )
    print(json.dumps({"status": result["status"], "failures": result["failures"]}))
    return 0 if result["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
