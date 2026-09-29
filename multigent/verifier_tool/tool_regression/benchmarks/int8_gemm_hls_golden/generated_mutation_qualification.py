"""Qualify a real-HLS RTL mutation with the normal generated Verifier TB.

No Architect/Verifier API call is made. The frozen contract is hand-authored,
but the cocotb test, operation campaign, assertions, and coverage plan are
rendered by the same deterministic functions used by the Verifier pipeline.
The mutant is run first; only a precise failure followed by full coverage and
ledger closure on the original RTL can qualify the pair.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

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
RTL_DIR = REPOSITORY_ROOT / "gemm_golden"


def generate_tb_from_contracts(
    output_dir: Path,
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> dict[str, Any]:
    """Render the full generated campaign from an explicit matched contract pair."""

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
    if not support["supported"]:
        raise AssertionError(f"complete code-owned campaign unsupported: {support!r}")

    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(
        interface_plan, architecture,
        include_automatic_campaign=True,
        randomized_transactions_minimum=8,
    )
    compile(block, "test_gemm_automatic.py", "exec")
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test_gemm_automatic.py").write_text(block)
    (output_dir / "functional_coverage_plan.json").write_text(json.dumps(coverage_plan, indent=2))
    return {
        "support": support,
        "obligation_count": len(coverage_plan["obligations"]),
        "generated_test": str(output_dir / "test_gemm_automatic.py"),
    }


def generate_normal_tb(output_dir: Path) -> dict[str, Any]:
    """Render the full generated campaign, without hand-written Cocotb code."""

    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    return generate_tb_from_contracts(output_dir, architecture, interface)


def _simulate(
    rtl_dir: Path,
    generated: Path,
    output_dir: Path,
    *,
    simulation_env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = output_dir / "functional_coverage_report.json"
    ledger_path = output_dir / "stimulus_ledger.json"
    result = run_cocotb_regression(
        rtl_dir=rtl_dir,
        top_module="int8_gemm",
        tests_dir=generated,
        reference_dir=REPOSITORY_ROOT,
        test_modules=["test_gemm_automatic"],
        seed=1,
        build_dir=output_dir / "build",
        report_path=output_dir / "simulation_report.json",
        timeout_seconds=900,
        coverage_plan=json.loads((generated / "functional_coverage_plan.json").read_text()),
        coverage_report_path=coverage_path,
        stimulus_ledger_report_path=ledger_path,
        simulation_env=simulation_env,
    )
    print(
        f"{output_dir.name}: status={result.get('status')} "
        f"failure_class={result.get('failure_class')}",
        flush=True,
    )
    if result.get("status") != "PASS":
        print(str(result.get("stdout", ""))[-4000:], flush=True)
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
    }


def qualify_first_mutant(output_dir: Path) -> dict[str, Any]:
    generated = output_dir / "generated"
    generation = generate_normal_tb(generated)
    mutant_rtl = output_dir / "mutated_rtl"
    shutil.copytree(RTL_DIR, mutant_rtl)
    target = mutant_rtl / "int8_gemm_gmem_a_m_axi.v"
    source = target.read_text()
    # Both generate branches of the AXI burst converter feed the externally
    # visible ARVALID. The earlier core-side tmp_valid mutation only issued a
    # bogus address after reset and was caught by the memory adapter first.
    anchor = "assign out_BURST_VALID = burst_valid;"
    if source.count(anchor) != 2:
        raise AssertionError("reset-valid mutation anchor is absent or ambiguous")
    target.write_text(source.replace(anchor, "assign out_BURST_VALID = 1'b1;"))

    mutant = _simulate(mutant_rtl, generated, output_dir / "mutant_reset_valid")
    original = _simulate(RTL_DIR, generated, output_dir / "original")
    precise_failure = (
        mutant["status"] == "SIMULATION_FAILURE"
        and "feature=protocol.gmem_a.valid_low_during_reset" in mutant["stdout"]
        and "VALID must be low while reset is active" in mutant["stdout"]
    )
    coverage = original["coverage"]
    original_complete = (
        original["status"] == "PASS"
        and coverage["status"] == "PASS"
        and isinstance(coverage["required_bins"], int)
        and coverage["required_bins"] == coverage["hit_bins"]
        and not coverage["missing_bins"]
        and not coverage["assertion_failures"]
        and original["ledger"]["status"] == "PASS"
    )
    summary = {
        "status": "QUALIFIED" if precise_failure and original_complete else "UNQUALIFIED",
        "generation": generation,
        "mutant": {key: value for key, value in mutant.items() if key != "stdout"},
        "mutant_precise_failure": precise_failure,
        "original": {key: value for key, value in original.items() if key != "stdout"},
        "original_complete": original_complete,
    }
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    print(json.dumps(qualify_first_mutant(parser.parse_args().output_dir), indent=2))
