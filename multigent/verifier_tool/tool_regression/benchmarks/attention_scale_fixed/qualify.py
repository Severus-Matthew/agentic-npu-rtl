"""Qualify standalone signed fixed-point attention scaling against its pool."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from ..mutation_outcomes import cpp_dut_failure
import random
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

from multigent.verifier_tool import (
    build_architect_operation_metadata,
    canonical_bins_for_concept,
    classify_operation_job,
    evaluate_canonical_operation,
    generate_canonical_stimulus_suite,
)
from multigent.verifier_tool.pool.operation_metadata import assemble_canonical_job


HERE = Path(__file__).resolve().parent
RTL = HERE / "rtl" / "attention_scale_fixed.sv"
TOP = "attention_scale_fixed"
DEFAULT_RANDOM_CASES = 128
DEFAULT_SEED = 0x5CA1E
CONCEPTS = (
    "dimensions",
    "score_values",
    "rounding",
    "scaled_values",
    "attenuation",
)


@dataclass(frozen=True)
class Mutation:
    name: str
    domain: str
    anchor: str
    replacement: str


def _serialization(dimensions: list[str]) -> dict[str, Any]:
    return {
        "kind": "dense_tensor",
        "index_order": dimensions,
        "description": "One signed score per transfer in row-major order.",
    }


def build_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    architecture = {
        "design": {
            "name": "attention_scale_fixed",
            "description": "Standalone signed QK-score scaling before mask/softmax.",
        },
        "operations": [
            {
                "name": "attention_scale_core",
                "kind": "attention_scale",
                "coverage_family": "attention_scale",
                "coverage_family_source": "catalog",
                "features": list(CONCEPTS),
                "feature_extensions": [],
                "semantics": (
                    "scaled_score=floor(score*32/256), where 32 is "
                    "round(256/sqrt(64)); no mask, softmax, or V stage"
                ),
                "arithmetic": {
                    "classifier_profile": "fixed_point_attention_scale",
                    "head_dimension": "D",
                    "coefficient_derivation": "round_inverse_sqrt",
                    "scale_multiplier": 32,
                    "scale_shift": 8,
                    "rounding": "arithmetic_floor",
                    "product_data_type": "s32",
                    "result_data_type": "s16",
                    "result_conversion": "exact",
                },
                "lifecycle_policy": {
                    "job_acceptance": "valid_ready_handshake",
                    "job_overlap": "single_inflight",
                    "busy_behavior": "tracks_active_job",
                    "completion_style": "pulse",
                    "completion_timing": "next_cycle_after_retirement",
                    "illegal_command_behavior": "error_without_start",
                    "error_style": "sticky_until_reset",
                    "error_timing": "next_cycle_after_error_event",
                    "reset_behavior": "abort_inflight",
                },
                "inputs": ["score_matrix"],
                "outputs": ["scaled_score_matrix"],
            }
        ],
        "data_types": [
            {"name": "s16", "width_bits": 16, "signed": True},
            {"name": "s32", "width_bits": 32, "signed": True},
        ],
        "data_objects": [
            {
                "name": "score_matrix",
                "role": "attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
            {
                "name": "scaled_score_matrix",
                "role": "scaled_attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
        ],
        "dimensions": [
            {
                "name": name,
                "minimum": extent,
                "maximum": extent,
                "runtime_configurable": False,
                "bound_parameter": f"{name}_DIM",
            }
            for name, extent in {"Q": 2, "S": 3, "D": 64}.items()
        ],
        "parameters": [
            {"name": "Q_DIM", "default_value": "2"},
            {"name": "S_DIM", "default_value": "3"},
            {"name": "D_DIM", "default_value": "64"},
        ],
    }
    channels = []
    signals = []
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        channels.append(
            {
                "name": channel,
                "direction": "output" if index else "input",
                "protocol_profile": "ready_valid",
                "data_objects": [obj["name"]],
                "ordering": "declared dimension order",
                "framing": "exact tensor",
            }
        )
        signals.extend(
            [
                {"name": f"{channel}_valid", "channel": channel, "role": "valid"},
                {"name": f"{channel}_ready", "channel": channel, "role": "ready"},
                {
                    "name": f"{channel}_payload",
                    "channel": channel,
                    "role": "payload",
                    "width": "16",
                    "signed": True,
                },
            ]
        )
    return architecture, {"channels": channels, "signals": signals}


def compiled_operation() -> tuple[dict[str, Any], dict[str, Any]]:
    architecture, interface = build_contract()
    metadata = build_architect_operation_metadata(architecture, interface)
    if metadata["unrepresentable_operations"]:
        raise AssertionError(metadata["unrepresentable_operations"])
    return architecture, metadata["operations"][0]


def _predicate_matches(value: Any, predicate: Mapping[str, Any]) -> bool:
    op = str(predicate.get("op", ""))
    args = list(predicate.get("args", []))
    if op == "eq" and len(args) == 1:
        return value == args[0]
    if op == "between" and len(args) == 2:
        return args[0] <= value <= args[1]
    return False


def _coverage_evidence(
    operation: Mapping[str, Any], cases: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    required: set[str] = set()
    hits: set[str] = set()
    for concept in CONCEPTS:
        for item in canonical_bins_for_concept(operation, concept) or []:
            required.add(
                f"operation.attention_scale_core.{concept}.{item['name']}"
            )
    for case in cases:
        job = assemble_canonical_job(
            operation, case["stimulus"], case["expected"], case["expected"]
        )
        assert job is not None
        evidence = classify_operation_job(job)
        for concept in CONCEPTS:
            for item in canonical_bins_for_concept(operation, concept) or []:
                if any(
                    _predicate_matches(value, item.get("predicate", {}))
                    for value in evidence.get(concept, [])
                ):
                    hits.add(
                        f"operation.attention_scale_core.{concept}.{item['name']}"
                    )
    return {
        "required_bins": len(required),
        "hit_bins": len(hits),
        "missing_bins": sorted(required - hits),
        "hit_bin_ids": sorted(hits),
    }


def build_cases(
    randomized_count: int, seed: int
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    architecture, operation = compiled_operation()
    suite = generate_canonical_stimulus_suite(
        operation, randomized_count=randomized_count, seed=seed
    )
    if suite["exceptions"]:
        raise AssertionError(
            f"attention-scale stimulus generation exceptions: {suite['exceptions']!r}"
        )
    cases = [*suite["directed"], *suite["qualification"], *suite["randomized"]]
    for case in cases:
        if evaluate_canonical_operation(operation, case["stimulus"]) != case["expected"]:
            raise AssertionError(f"non-reproducible golden case {case['label']}")
    coverage = _coverage_evidence(operation, cases)
    if coverage["missing_bins"]:
        raise AssertionError(
            f"attention-scale coverage not closed: {coverage['missing_bins']}"
        )
    return architecture, cases, coverage


def _write_values(path: Path, values: Iterable[int]) -> None:
    path.write_text("".join(f"{int(value)}\n" for value in values), encoding="utf-8")


def _harness_source(total: int, seed: int) -> str:
    return f'''#include "V{TOP}.h"
#include "verilated.h"
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static int16_t signed16(uint32_t value) {{ return static_cast<int16_t>(value & 0xffffu); }}

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    if (argc != 3) {{ std::cerr << "usage: sim scores expected\\n"; return 2; }}
    std::ifstream score_file(argv[1]);
    std::ifstream expected_file(argv[2]);
    std::vector<int> scores, expected;
    int value = 0;
    while (score_file >> value) scores.push_back(value);
    while (expected_file >> value) expected.push_back(value);
    if (scores.size() != {total} || expected.size() != scores.size()) {{
        std::cerr << "bad vector count " << scores.size() << " " << expected.size() << "\\n";
        return 3;
    }}

    V{TOP} dut;
    uint32_t lfsr = {seed & 0xFFFFFFFF}u;
    auto advance = [&]() {{
        lfsr ^= lfsr << 13; lfsr ^= lfsr >> 17; lfsr ^= lfsr << 5;
    }};
    auto edge = [&]() {{ dut.clk = 0; dut.eval(); dut.clk = 1; dut.eval(); }};

    dut.in_valid = 0; dut.out_ready = 0; dut.score_in = 0; dut.rst_n = 0;
    for (int i = 0; i < 3; ++i) edge();
    if (dut.out_valid) {{ std::cerr << "ghost valid during reset\\n"; return 10; }}

    // Accept one value while the output is blocked, then reset it away.
    dut.rst_n = 1; dut.in_valid = 1; dut.out_ready = 0; dut.score_in = 123;
    dut.clk = 0; dut.eval();
    if (!dut.in_ready) {{ std::cerr << "cannot accept reset-abort probe\\n"; return 11; }}
    dut.clk = 1; dut.eval();
    dut.in_valid = 0; dut.rst_n = 0; edge();
    dut.clk = 0; dut.eval();
    if (dut.out_valid) {{ std::cerr << "pre-reset output survived reset\\n"; return 12; }}
    dut.rst_n = 1;

    // A sink may withhold READY while the empty stage must still accept input.
    // This distinguishes input readiness from output readiness and then checks
    // that the captured value remains stable through a full stall cycle.
    dut.in_valid = 1; dut.score_in = 80; dut.out_ready = 0;
    dut.clk = 0; dut.eval();
    if (!dut.in_ready) {{ std::cerr << "empty stage incorrectly depends on out_ready\\n"; return 13; }}
    dut.clk = 1; dut.eval();
    dut.in_valid = 0; dut.clk = 0; dut.eval();
    if (!dut.out_valid || signed16(dut.score_out) != 10) {{
        std::cerr << "decoupled acceptance probe was lost\\n"; return 14;
    }}
    dut.clk = 1; dut.eval();
    dut.clk = 0; dut.eval();
    if (!dut.out_valid || signed16(dut.score_out) != 10) {{
        std::cerr << "decoupled probe changed while stalled\\n"; return 15;
    }}
    dut.out_ready = 1; dut.clk = 1; dut.eval();
    dut.clk = 0; dut.eval();
    if (dut.out_valid) {{ std::cerr << "decoupled probe duplicated\\n"; return 16; }}

    size_t sent = 0, received = 0;
    std::deque<int> queue;
    bool held = false;
    int held_value = 0;
    const uint64_t max_cycles = static_cast<uint64_t>(scores.size()) * 12u + 1000u;
    for (uint64_t cycle = 0; cycle < max_cycles && received < scores.size(); ++cycle) {{
        advance();
        dut.in_valid = sent < scores.size();
        dut.score_in = sent < scores.size() ? static_cast<uint16_t>(scores[sent]) : 0;
        dut.out_ready = ((lfsr & 7u) != 0u); // deterministic backpressure
        dut.clk = 0; dut.eval();

        int observed = signed16(dut.score_out);
        if (held && (!dut.out_valid || observed != held_value)) {{
            std::cerr << "output changed while stalled at cycle " << cycle << "\\n";
            return 20;
        }}
        bool out_transfer = dut.out_valid && dut.out_ready;
        bool in_transfer = dut.in_valid && dut.in_ready;
        if (out_transfer) {{
            if (queue.empty()) {{ std::cerr << "unsolicited output\\n"; return 21; }}
            int wanted = queue.front(); queue.pop_front();
            if (observed != wanted) {{
                std::cerr << "mismatch index=" << received << " input=" << scores[received]
                          << " got=" << observed << " expected=" << wanted << "\\n";
                return 22;
            }}
            ++received;
        }}
        if (in_transfer) {{ queue.push_back(expected[sent]); ++sent; }}
        held = dut.out_valid && !dut.out_ready;
        held_value = observed;
        dut.clk = 1; dut.eval();
    }}
    if (sent != scores.size() || received != scores.size() || !queue.empty()) {{
        std::cerr << "accounting failure sent=" << sent << " received=" << received
                  << " pending=" << queue.size() << "\\n";
        return 23;
    }}
    dut.in_valid = 0; dut.out_ready = 1;
    for (int i = 0; i < 4; ++i) {{
        dut.clk = 0; dut.eval();
        if (dut.out_valid) {{ std::cerr << "extra output after completion\\n"; return 24; }}
        dut.clk = 1; dut.eval();
    }}
    std::cout << "PASS exhaustive_inputs={total} reset_abort=1 backpressure=1\\n";
    return 0;
}}
'''


def _mutation_catalog(source: str) -> list[Mutation]:
    mutations: list[Mutation] = []
    product_anchor = "assign scaled_product = $signed(score_in) * SCALE_CONST;"
    result_anchor = "score_out <= scaled_product >>> FRAC_BITS;"
    # Flipping score bits 0..2 is functionally invisible for this exact /8
    # profile, so those are excluded rather than counted as surviving faults.
    for bit in range(3, 16):
        mask = 1 << bit
        mutations.append(
            Mutation(
                f"input_bit_flip_{bit}",
                "signed_input_decode",
                product_anchor,
                f"assign scaled_product = $signed(score_in ^ 16'h{mask:04x}) * SCALE_CONST;",
            )
        )
    for bit in range(16):
        mask = 1 << bit
        mutations.append(
            Mutation(
                f"output_bit_flip_{bit}",
                "result_conversion",
                result_anchor,
                f"score_out <= (scaled_product >>> FRAC_BITS) ^ 16'h{mask:04x};",
            )
        )
    for coefficient in (1, 2, 4, 8, 16, 31, 33, 48, 64, 127, 255, 256):
        mutations.append(
            Mutation(
                f"coefficient_{coefficient}",
                "inverse_sqrt_coefficient",
                product_anchor,
                f"assign scaled_product = $signed(score_in) * {coefficient};",
            )
        )
    for shift in (*range(0, 8), *range(9, 16)):
        mutations.append(
            Mutation(
                f"shift_{shift}",
                "fixed_point_shift",
                result_anchor,
                f"score_out <= scaled_product >>> {shift};",
            )
        )
    mutations.extend(
        [
            Mutation(
                "unsigned_input",
                "signed_input_decode",
                product_anchor,
                "assign scaled_product = $unsigned(score_in) * SCALE_CONST;",
            ),
            Mutation(
                "logical_right_shift",
                "rounding_semantics",
                result_anchor,
                "score_out <= $unsigned(scaled_product[15:0]) >> FRAC_BITS;",
            ),
            Mutation(
                "negative_round_toward_zero",
                "rounding_semantics",
                result_anchor,
                "score_out <= (scaled_product < 0) ? -((-scaled_product) >>> FRAC_BITS) : (scaled_product >>> FRAC_BITS);",
            ),
            Mutation(
                "round_nearest_bias",
                "rounding_semantics",
                result_anchor,
                "score_out <= (scaled_product + (1 << (FRAC_BITS-1))) >>> FRAC_BITS;",
            ),
            Mutation(
                "negate_scaled_result",
                "stage_arithmetic",
                result_anchor,
                "score_out <= -(scaled_product >>> FRAC_BITS);",
            ),
            Mutation(
                "bypass_scaling",
                "stage_arithmetic",
                result_anchor,
                "score_out <= score_in;",
            ),
            Mutation(
                "add_coefficient",
                "stage_arithmetic",
                product_anchor,
                "assign scaled_product = $signed(score_in) + SCALE_CONST;",
            ),
            Mutation(
                "subtract_coefficient",
                "stage_arithmetic",
                product_anchor,
                "assign scaled_product = $signed(score_in) - SCALE_CONST;",
            ),
            Mutation(
                "ready_always_high",
                "ready_valid_protocol",
                "assign in_ready = !out_valid || out_ready;",
                "assign in_ready = 1'b1;",
            ),
            Mutation(
                "ready_wrong_polarity",
                "ready_valid_protocol",
                "assign in_ready = !out_valid || out_ready;",
                "assign in_ready = !out_valid || !out_ready;",
            ),
            Mutation(
                "ignore_stall_for_state",
                "ready_valid_protocol",
                "end else if (in_ready) begin",
                "end else begin",
            ),
            Mutation(
                "update_only_when_output_ready",
                "ready_valid_protocol",
                "end else if (in_ready) begin",
                "end else if (out_ready) begin",
            ),
            Mutation(
                "drop_valid_when_stalled",
                "ready_valid_protocol",
                "out_valid <= in_valid;",
                "out_valid <= in_valid && out_ready;",
            ),
            Mutation(
                "valid_stuck_low",
                "accepted_output_accounting",
                "out_valid <= in_valid;",
                "out_valid <= 1'b0;",
            ),
            Mutation(
                "valid_stuck_high_after_accept",
                "accepted_output_accounting",
                "out_valid <= in_valid;",
                "out_valid <= 1'b1;",
            ),
            Mutation(
                "reset_leaves_ghost_valid",
                "reset_abort",
                "out_valid <= 1'b0;",
                "out_valid <= 1'b1;",
            ),
            Mutation(
                "reset_wrong_polarity",
                "reset_abort",
                "if (!rst_n) begin",
                "if (rst_n) begin",
            ),
        ]
    )
    for mutation in mutations:
        if source.count(mutation.anchor) != 1:
            raise AssertionError(
                f"mutation anchor {mutation.name!r} occurs {source.count(mutation.anchor)} times"
            )
    return mutations


def _run_one(
    *, source: str, work: Path, scores: Path, expected: Path, total: int, seed: int
) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    rtl = work / RTL.name
    harness = work / "harness.cpp"
    rtl.write_text(source, encoding="utf-8")
    harness.write_text(_harness_source(total, seed), encoding="utf-8")
    obj = work / "obj"
    compile_cmd = [
        "verilator",
        "--cc",
        "--exe",
        "--build",
        "-Wno-fatal",
        "--top-module",
        TOP,
        "--Mdir",
        str(obj),
        str(rtl),
        str(harness),
        "-CFLAGS",
        "-std=c++17",
    ]
    compiled = subprocess.run(
        compile_cmd, cwd=work, text=True, capture_output=True, check=False
    )
    if compiled.returncode:
        return {
            "compile_valid": False,
            "passed": False,
            "returncode": compiled.returncode,
            "log": (compiled.stdout + compiled.stderr)[-5000:],
        }
    executable = obj / f"V{TOP}"
    simulated = subprocess.run(
        [str(executable), str(scores), str(expected)],
        cwd=work,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return {
        "compile_valid": True,
        "passed": simulated.returncode == 0 and "PASS" in simulated.stdout,
        "returncode": simulated.returncode,
        "log": (simulated.stdout + simulated.stderr)[-5000:],
    }


def run_qualification(
    *,
    randomized_count: int = DEFAULT_RANDOM_CASES,
    seed: int = DEFAULT_SEED,
    mutant_limit: int | None = 0,
    workers: int = 1,
    work_root: Path | None = None,
) -> dict[str, Any]:
    architecture, cases, coverage = build_cases(randomized_count, seed)
    pool_scores = [
        int(value)
        for case in cases
        for value in case["stimulus"]["score_matrix"]
    ]
    exhaustive_scores = list(range(-(1 << 15), 1 << 15))
    scores = [*pool_scores, *exhaustive_scores]
    # This oracle is deliberately host integer math: Python // with a positive
    # denominator is the same floor rule as the contract's signed >>>.
    expected = [value * 32 // 256 for value in scores]
    source = RTL.read_text(encoding="utf-8")
    catalog = _mutation_catalog(source)
    if mutant_limit is None:
        selected = catalog
    elif mutant_limit <= 0:
        selected = []
    else:
        rng = random.Random(seed ^ 0xA771)
        selected = rng.sample(catalog, min(mutant_limit, len(catalog)))

    owned_temp = None
    if work_root is None:
        owned_temp = tempfile.TemporaryDirectory(prefix="attention-scale-qualify-")
        root = Path(owned_temp.name)
    else:
        root = work_root
        root.mkdir(parents=True, exist_ok=True)
    score_file = root / "scores.txt"
    expected_file = root / "expected.txt"
    _write_values(score_file, scores)
    _write_values(expected_file, expected)

    baseline = _run_one(
        source=source,
        work=root / "baseline",
        scores=score_file,
        expected=expected_file,
        total=len(scores),
        seed=seed,
    )
    if not baseline["passed"]:
        raise AssertionError(f"attention-scale baseline failed: {baseline['log']}")

    def run_mutation(mutation: Mutation) -> dict[str, Any]:
        mutated = source.replace(mutation.anchor, mutation.replacement, 1)
        result = _run_one(
            source=mutated,
            work=root / "mutants" / mutation.name,
            scores=score_file,
            expected=expected_file,
            total=len(scores),
            seed=seed,
        )
        killed = cpp_dut_failure("scale", result)
        return {
            **asdict(mutation),
            **result,
            "killed": killed,
            "survived": bool(result["compile_valid"] and not killed),
            "infrastructure_failure": bool(result["compile_valid"] and not result["passed"] and not killed),
        }

    mutation_results: list[dict[str, Any]] = []
    if selected:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {executor.submit(run_mutation, item): item for item in selected}
            for future in as_completed(futures):
                mutation_results.append(future.result())
        mutation_results.sort(key=lambda item: item["name"])

    compile_valid = [item for item in mutation_results if item["compile_valid"]]
    invalid = [item for item in mutation_results if not item["compile_valid"]]
    survivors = [item for item in compile_valid if item["survived"]]
    summary = {
        "schema_version": 1,
        "benchmark": "attention_scale_fixed",
        "source_provenance": {
            "repository": "https://github.com/Abhinav-Avasarala/TRANSFORMER-ATTENTION-ACCELERATOR",
            "commit": "3054e9a5324da438a78937049f656abc413c2750",
            "source_path": "src/softmax_unit.sv",
            "adaptation": "isolated embedded coefficient multiply/shift as signed standalone stage",
        },
        "contract_digest": hashlib.sha256(
            json.dumps(architecture, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "rtl_digest": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "coverage": coverage,
        "stimulus": {
            "pool_cases": len(cases),
            "pool_elements": len(pool_scores),
            "exhaustive_signed16_inputs": len(exhaustive_scores),
            "total_elements": len(scores),
            "randomized_cases": randomized_count,
            "seed": seed,
        },
        "assertions_exercised": [
            "oracle_equivalence",
            "coefficient_derivation",
            "arithmetic_shift_semantics",
            "stage_order",
            "accepted_input_accounting",
            "output_stability_under_backpressure",
            "reset_abort_no_ghost_result",
        ],
        "baseline": baseline,
        "mutation_campaign": {
            "catalog_size": len(catalog),
            "selected": len(selected),
            "compile_valid": len(compile_valid),
            "compile_invalid": len(invalid),
            "killed": sum(bool(item["killed"]) for item in mutation_results),
            "survived": len(survivors),
            "survivor_names": [item["name"] for item in survivors],
            "invalid_names": [item["name"] for item in invalid],
            "results": mutation_results,
        },
        "passed": (
            baseline["passed"]
            and not coverage["missing_bins"]
            and not survivors
            and not invalid
        ),
    }
    if owned_temp is not None:
        owned_temp.cleanup()
    return summary


def _parse_mutants(value: str) -> int | None:
    if value == "all":
        return None
    result = int(value, 0)
    if result < 0:
        raise argparse.ArgumentTypeError("mutant count must be nonnegative or 'all'")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--random-cases", type=int, default=DEFAULT_RANDOM_CASES)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--mutants", type=_parse_mutants, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    summary = run_qualification(
        randomized_count=args.random_cases,
        seed=args.seed,
        mutant_limit=args.mutants,
        workers=args.workers,
        work_root=args.work_root,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
