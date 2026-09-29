"""Generate the normal verifier-tool TB for the ready_valid_multi_beat_gemm
fixture and run it against a chosen RTL directory. No external API call.
Mirrors ready_valid_tiny_gemm/qualify.py's pattern exactly (this fixture is
its sibling: same protocol profile, same lifecycle shape, just N=2 instead
of N=1 and error_style=sticky_until_reset instead of pulse), so BUG-003 is
already fixed for the automatic campaign this uses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_interface_coverage_plan,
    merge_coverage_plans,
    operation_plan_for_tests,
    render_contract_generated_block,
    synthesize_code_owned_operation_coverage,
    validate_architecture_lifecycle_policies,
    validate_architecture_operation_arithmetic,
    validate_architecture_operation_features,
    validate_interface_semantics,
    validate_interface_signal_roles,
)
from multigent.verifier_tool.tool_regression.paths import REPOSITORY_ROOT

HERE = Path(__file__).resolve().parent
TOP_MODULE = "tiny_gemm_rv_multi_top"
DEFAULT_RTL_DIR = HERE / "rtl"


def generate_normal_tb(output_dir: Path) -> dict[str, Any]:
    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    findings = [
        *validate_interface_signal_roles(interface),
        *validate_interface_semantics(interface),
        *validate_architecture_operation_features(architecture),
        *validate_architecture_lifecycle_policies(architecture),
        *validate_architecture_operation_arithmetic(architecture),
    ]
    if findings:
        raise AssertionError(f"frozen contract validation failed: {findings!r}")
    metadata = build_architect_operation_metadata(architecture, interface)
    if metadata["unrepresentable_operations"]:
        raise AssertionError([
            (item["name"], item.get("reason_code"), item["reason"])
            for item in metadata["unrepresentable_operations"]
        ])
    support = automatic_campaign_support(metadata, architecture)
    if not support["any_operation_supported"]:
        raise AssertionError(f"no code-owned campaign at all: {support!r}")

    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(
        interface_plan, architecture,
        include_automatic_campaign=True,
        randomized_transactions_minimum=8,
    )
    module_name = "test_ready_valid_multi_beat_gemm"
    compile(block, f"{module_name}.py", "exec")
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{module_name}.py").write_text(block)
    (output_dir / "functional_coverage_plan.json").write_text(json.dumps(coverage_plan, indent=2))
    return {
        "support": support,
        "obligation_count": len(coverage_plan["obligations"]),
        "module_name": module_name,
        "generated_test": str(output_dir / f"{module_name}.py"),
    }


def simulate(rtl_dir: Path, generated: Path, output_dir: Path, *, seed: int = 1) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    module_name = "test_ready_valid_multi_beat_gemm"
    coverage_path = output_dir / "functional_coverage_report.json"
    ledger_path = output_dir / "stimulus_ledger.json"
    result = run_cocotb_regression(
        rtl_dir=rtl_dir,
        top_module=TOP_MODULE,
        tests_dir=generated,
        reference_dir=REPOSITORY_ROOT,
        test_modules=[module_name],
        seed=seed,
        build_dir=output_dir / "build",
        report_path=output_dir / "simulation_report.json",
        timeout_seconds=300,
        coverage_plan=json.loads((generated / "functional_coverage_plan.json").read_text()),
        coverage_report_path=coverage_path,
        stimulus_ledger_report_path=ledger_path,
    )
    coverage = json.loads(coverage_path.read_text()) if coverage_path.is_file() else {}
    ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {}
    return {
        "status": result.get("status"),
        "failure_class": result.get("failure_class"),
        "coverage": {key: coverage.get(key) for key in (
            "status", "required_bins", "hit_bins", "missing_bins", "assertion_failures",
        )},
        "ledger": {key: ledger.get(key) for key in (
            "status", "stimulus_count", "directed_stimuli", "randomized_stimuli",
        )},
        "stdout": str(result.get("stdout", "")),
        "report_dir": str(output_dir.resolve()),
        "covered_bins": coverage.get("covered_bins", []),
    }


def run_baseline(output_dir: Path, rtl_dir: Path | None = None) -> dict[str, Any]:
    generated = output_dir / "generated"
    generation = generate_normal_tb(generated)
    original = simulate(rtl_dir or DEFAULT_RTL_DIR, generated, output_dir / "original")
    coverage = original["coverage"]
    complete = (
        original["status"] == "PASS"
        and coverage["status"] == "PASS"
        and isinstance(coverage["required_bins"], int)
        and coverage["required_bins"] == coverage["hit_bins"]
        and not coverage["missing_bins"]
        and not coverage["assertion_failures"]
        and original["ledger"]["status"] == "PASS"
    )
    summary = {
        "status": "BASELINE_PASS" if complete else "BASELINE_FAIL",
        "generation": generation,
        "original": {key: value for key, value in original.items() if key not in ("stdout", "covered_bins")},
        "original_complete": complete,
    }
    if not complete:
        print(original["stdout"][-6000:])
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_baseline(args.output_dir), indent=2))
