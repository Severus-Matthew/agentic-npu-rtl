"""Qualify environment-owned AXI4 response faults with the generated HLS TB.

Unlike :mod:`qualify_named_mutant`, this runner does not edit RTL.  It gives
the reusable AXI4 memory driver one closed fault plan while leaving the frozen
contract, generated assertions, coverage plan, operation campaign, and golden
model byte-identical to the saved positive baseline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from multigent.verifier_tool.protocol.stimulus.drivers.fault_injection import (
    FAULT_PLAN_ENV,
    validate_protocol_fault_plan,
)

from .generated_mutation_qualification import RTL_DIR, _simulate
from .qualification_common import (
    materialize_baseline_generated_pair,
    sha256,
    validate_positive_baseline,
)


DRIVER_FAULTS: dict[str, dict[str, Any]] = {
    "a_response_before_request": {
        "group": "gmem_a", "fault": "present_response_before_request",
        "diagnostic": "feature=protocol.gmem_a.response_after_request",
    },
    "a_response_id_mismatch": {
        "group": "gmem_a", "fault": "return_nonmatching_id",
        "diagnostic": "feature=protocol.gmem_a.response_id_matches_request",
    },
    "a_read_last_mismatch": {
        "group": "gmem_a", "fault": "invert_rlast_on_nonfinal_or_final_beat",
        "diagnostic": "feature=protocol.gmem_a.read_last_matches_length",
    },
    "a_nonexclusive_exokay": {
        "group": "gmem_a", "fault": "return_exokay_for_nonexclusive_request",
        "diagnostic": "feature=protocol.gmem_a.exclusive_response_consistency",
    },
    "b_response_before_request": {
        "group": "gmem_b", "fault": "present_response_before_request",
        "diagnostic": "feature=protocol.gmem_b.response_after_request",
    },
    "b_response_id_mismatch": {
        "group": "gmem_b", "fault": "return_nonmatching_id",
        "diagnostic": "feature=protocol.gmem_b.response_id_matches_request",
    },
    "b_read_last_mismatch": {
        "group": "gmem_b", "fault": "invert_rlast_on_nonfinal_or_final_beat",
        "diagnostic": "feature=protocol.gmem_b.read_last_matches_length",
    },
    "b_nonexclusive_exokay": {
        "group": "gmem_b", "fault": "return_exokay_for_nonexclusive_request",
        "diagnostic": "feature=protocol.gmem_b.exclusive_response_consistency",
    },
    "c_response_before_request": {
        "group": "gmem_c", "fault": "present_response_before_request",
        "diagnostic": "feature=protocol.gmem_c.response_after_request",
    },
    "c_response_id_mismatch": {
        "group": "gmem_c", "fault": "return_nonmatching_id",
        "diagnostic": "feature=protocol.gmem_c.response_id_matches_request",
    },
    "c_nonexclusive_exokay": {
        "group": "gmem_c", "fault": "return_exokay_for_nonexclusive_request",
        "diagnostic": "feature=protocol.gmem_c.exclusive_response_consistency",
    },
}


def driver_fault_plan(name: str) -> tuple[dict[str, Any], str]:
    if name not in DRIVER_FAULTS:
        raise ValueError(f"unknown driver fault {name!r}")
    spec = DRIVER_FAULTS[name]
    plan = validate_protocol_fault_plan({
        "schema_version": 1,
        "profile": "axi4",
        "group": spec["group"],
        "fault": spec["fault"],
        "occurrence": 1,
    })
    return plan, str(spec["diagnostic"])


def qualify_driver_fault(
    name: str,
    output_dir: Path,
    *,
    baseline_dir: Path,
    baseline_generated: Path,
) -> dict[str, Any]:
    plan, diagnostic = driver_fault_plan(name)
    generated = output_dir / "generated"
    materialize_baseline_generated_pair(baseline_generated, generated)
    baseline = validate_positive_baseline(
        baseline_dir, baseline_generated, generated
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / "protocol_fault_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    fault = _simulate(
        RTL_DIR,
        generated,
        output_dir / "fault",
        simulation_env={FAULT_PLAN_ENV: str(plan_path.resolve())},
    )
    precise_failure = (
        fault["status"] == "SIMULATION_FAILURE"
        and diagnostic.lower() in fault["stdout"].lower()
    )
    summary = {
        "name": name,
        "status": "QUALIFIED" if precise_failure else "UNQUALIFIED",
        "fault_plan": plan,
        "expected_diagnostic": diagnostic,
        "fault_precise_failure": precise_failure,
        "baseline_complete": baseline["complete"],
        "baseline_dir": str(baseline_dir),
        "generated_test_sha256": sha256(generated / "test_gemm_automatic.py"),
        "fault": {key: value for key, value in fault.items() if key != "stdout"},
    }
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=sorted(DRIVER_FAULTS))
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--baseline-generated", type=Path, required=True)
    args = parser.parse_args()
    result = qualify_driver_fault(
        args.name,
        args.output_dir,
        baseline_dir=args.baseline_dir,
        baseline_generated=args.baseline_generated,
    )
    print(json.dumps(result, indent=2))
