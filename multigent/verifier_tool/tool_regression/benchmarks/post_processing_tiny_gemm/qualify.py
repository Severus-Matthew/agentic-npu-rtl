"""Generate the verifier-tool TB for post_processing_tiny_gemm and run it
against a chosen RTL directory. No external API call.

Unlike ready_valid_tiny_gemm's qualify.py, this does NOT use the automatic
verification campaign (`run_code_owned_verification_campaign`): that sweep
also injects reset-abort scenarios whose completion bookkeeping is not
applicable to this fixture's ready_valid + completion_style=pulse +
reset_behavior=abort_inflight policy. Instead this drives a fixed, hand-picked sequence of
directed jobs one at a time via `run_code_owned_operation_case` (the same
single-job runner the campaign itself calls per case, minus the surrounding
reset-abort/error-injection sweep), with no resets between jobs. This stays
entirely outside BUG-003's blast radius while still exercising the real
per-job golden check, coverage sampling, and lifecycle/protocol assertions
through the exact same code paths.

The first 10 directed jobs were derived by calling this fixture's own
canonical.py classifier/evaluator directly on candidate (A, B, bias) triples
until their
union covered all 17 target operation_bin rows: accumulation's 4
boundary/overflow classes, all 5 bias classes, all 3 activation regions, and
all 5 quantization classes -- none of which any other fixture in this pool's
declares at once.

3 more jobs (`stall_one_cycle`/`stall_short`/`stall_long`) were added later to
also close the pool's `stall_stability`/`handshake_states`/
`handshake_arrival_order` protocol-feature bins: each passes
`output_initial_stall_cycles` straight through to
`run_code_owned_operation_case` -> `collect_protocol_transfers`, holding this
fixture's own y_ready low for an exact, chosen number of cycles after y_valid
asserts. This single, tiny addition happens to also produce every required
handshake_states/handshake_arrival_order combination on every channel
(a/b/bias/cmd/y) as a side effect of driving 3 more real jobs through the
same K=4 load/compute/store FSM -- confirmed directly via covered_bins, not
assumed. `run_restricted_stall_variant()` below drives a strict subset of
just these 3 jobs to prove the coverage plan correctly reports a stall-length
bin as missing when that exact stall length is never presented, the
`coverage_obligation_not_hit` isolation this ledger's rubric asks for.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
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
TOP_MODULE = "post_processing_tiny_gemm_top"

# label, A (len 4), B (len 4), bias, extra run_code_owned_operation_case
# kwargs -> the first 10 were verified via canonical.py directly (see
# notes.md) to jointly cover all 17 target operation_bin rows; the last 3
# add stall_stability/handshake_states/handshake_arrival_order coverage
# (see the module docstring).
JOBS: list[tuple[str, list[int], list[int], int, dict]] = [
    ("accum_positive_boundary", [1, -128, -128, 0], [-1, -128, -128, 0], 0, {}),
    ("accum_negative_boundary", [-128, -128, 2, 0], [127, 127, -128, 0], 0, {}),
    ("accum_positive_overflow", [-128, -128, 0, 0], [-128, -128, 0, 0], 0, {}),
    ("accum_negative_overflow", [-128, -127, 3, 0], [127, 127, -128, 0], 0, {}),
    ("bias_zero_quant_exact", [0, 0, 0, 0], [0, 0, 0, 0], 0, {}),
    ("bias_positive_quant_rounded", [0, 0, 0, 0], [0, 0, 0, 0], 100, {}),
    ("bias_negative_activation_negative", [0, 0, 0, 0], [0, 0, 0, 0], -100, {}),
    ("bias_minimum_quant_negsat", [0, 0, 0, 0], [0, 0, 0, 0], -32768, {}),
    ("bias_maximum_quant_possat", [0, 0, 0, 0], [0, 0, 0, 0], 32767, {}),
    ("quant_zero_region", [0, 0, 0, 0], [0, 0, 0, 0], -80, {}),
    ("stall_one_cycle", [0, 0, 0, 0], [0, 0, 0, 0], 0, {"output_initial_stall_cycles": 1}),
    ("stall_short", [0, 0, 0, 0], [0, 0, 0, 0], 0, {"output_initial_stall_cycles": 3}),
    ("stall_long", [0, 0, 0, 0], [0, 0, 0, 0], 0, {"output_initial_stall_cycles": 6}),
]


def _load_contracts() -> tuple[dict, dict]:
    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    return architecture, interface


def _tb_body(jobs: list[tuple] | None = None) -> str:
    jobs_literal = json.dumps(jobs if jobs is not None else JOBS)
    return f"""
from multigent.verifier_tool.operation.stimulus.stimulus_generator import evaluate_canonical_operation
from multigent.verifier_tool.orchestration.campaign import (
    initialize_testbench_owned_signals as _pp_initialize_testbench_owned_signals,
    run_code_owned_operation_case as _pp_run_code_owned_operation_case,
)

_PP_JOBS = {jobs_literal}

@_contract_cocotb.test(timeout_time=120, timeout_unit="sec")
@_contract_coverage()
async def check_post_processing_bins(dut):
    \"\"\"Directed happy-path jobs only -- no reset-abort sweep (BUG-003).\"\"\"
    import cocotb
    from cocotb.clock import Clock

    interface = CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"]
    await _pp_initialize_testbench_owned_signals(dut, interface)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await _contract_drive_protocol_reset(dut, "clk", "rst_n", 0)

    operation = CONTRACT_OPERATION_METADATA["operations"][0]
    for label, a, b, bias, kwargs in _PP_JOBS:
        stimulus = {{"A_matrix": a, "B_matrix": b, "bias_vector": [bias]}}
        expected = evaluate_canonical_operation(CONTRACT_OPERATION_METADATA, stimulus)
        case = {{
            "operation_name": "gemm", "kind": "directed", "label": label,
            "target": None, "qualification_purpose": "post_processing_bin_coverage",
            "stimulus": stimulus, "expected": expected,
        }}
        await _pp_run_code_owned_operation_case(
            dut, "clk", operation, case, **kwargs,
        )
"""


def generate_normal_tb(output_dir: Path, jobs: list[tuple] | None = None) -> dict[str, Any]:
    architecture, interface = _load_contracts()
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

    interface_plan = build_interface_coverage_plan(interface)
    block = render_contract_generated_block(
        interface_plan, architecture, include_automatic_campaign=False,
    )
    module_name = "test_post_processing_tiny_gemm"
    source = block + _tb_body(jobs)
    compile(source, f"{module_name}.py", "exec")
    specs = synthesize_code_owned_operation_coverage([], architecture, metadata)
    operation_plan = operation_plan_for_tests(specs, [], architecture, interface)
    coverage_plan = merge_coverage_plans(interface_plan, operation_plan)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{module_name}.py").write_text(source)
    (output_dir / "functional_coverage_plan.json").write_text(json.dumps(coverage_plan, indent=2))
    return {
        "obligation_count": len(coverage_plan["obligations"]),
        "module_name": module_name,
        "generated_test": str(output_dir / f"{module_name}.py"),
    }


def simulate(rtl_dir: Path, generated: Path, output_dir: Path, *, seed: int = 1) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    module_name = "test_post_processing_tiny_gemm"
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
    }


def run_baseline(output_dir: Path, rtl_dir: Path | None = None) -> dict[str, Any]:
    generated = output_dir / "generated"
    generation = generate_normal_tb(generated)
    original = simulate(rtl_dir or (HERE / "rtl"), generated, output_dir / "original")
    coverage = original["coverage"]
    complete = (
        original["status"] == "PASS"
        and coverage["status"] == "PASS"
        and isinstance(coverage["required_bins"], int)
        and coverage["required_bins"] == coverage["hit_bins"]
        and not coverage["missing_bins"]
        and not coverage["assertion_failures"]
    )
    summary = {
        "status": "BASELINE_PASS" if complete else "BASELINE_FAIL",
        "generation": generation,
        "original": {key: value for key, value in original.items() if key != "stdout"},
        "original_complete": complete,
    }
    if not complete:
        print(original["stdout"][-8000:])
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


_STALL_JOB_LOOKUP = {job[0]: job for job in JOBS if job[0].startswith("stall_")}


def run_restricted_stall_variant(output_dir: Path, *, omit: str, rtl_dir: Path | None = None) -> dict[str, Any]:
    """Drive only the stall jobs NOT named in `omit`, against the same
    compliant RTL, to prove the coverage plan reports the omitted stall
    length's bin as required-but-missing while the others stay hit --
    `coverage_obligation_not_hit` isolation for `stall_stability`, with no
    RTL change at all (the fault here is in the stimulus, not the DUT).
    """

    restricted_jobs = [job for name, job in _STALL_JOB_LOOKUP.items() if name != omit]
    assert len(restricted_jobs) == len(_STALL_JOB_LOOKUP) - 1, omit
    generated = output_dir / "generated"
    generate_normal_tb(generated, jobs=restricted_jobs)
    result = simulate(rtl_dir or (HERE / "rtl"), generated, output_dir / "restricted")
    (output_dir / "restricted_variant.json").write_text(
        json.dumps({key: value for key, value in result.items() if key != "stdout"}, indent=2)
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--rtl-dir", type=Path, default=None)
    parser.add_argument(
        "--restricted-stall-omit", choices=sorted(_STALL_JOB_LOOKUP), default=None,
        help="Run only the isolation check: drive every stall job except this one.",
    )
    args = parser.parse_args()
    if args.restricted_stall_omit:
        result = run_restricted_stall_variant(
            args.output_dir, omit=args.restricted_stall_omit, rtl_dir=args.rtl_dir,
        )
        print(json.dumps({key: value for key, value in result.items() if key != "stdout"}, indent=2))
    else:
        print(json.dumps(run_baseline(args.output_dir, args.rtl_dir), indent=2))
