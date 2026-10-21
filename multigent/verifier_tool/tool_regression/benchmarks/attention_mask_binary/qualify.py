"""Qualify a standalone binary-keep attention-mask RTL against its pool."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
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
RTL = HERE / "rtl" / "attention_mask_binary.sv"
TOP = "attention_mask_binary"
DEFAULT_RANDOM_CASES = 128
DEFAULT_SEED = 0xA55A
CONCEPTS = (
    "dimensions",
    "score_values",
    "mask_values",
    "sparsity_patterns",
    "masked_values",
    "mask_effects",
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
        "description": "One row-major element per transfer.",
    }


def build_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    architecture = {
        "design": {
            "name": "attention_mask_binary",
            "description": "Standalone binary-keep mask between scale and normalization.",
        },
        "operations": [
            {
                "name": "attention_mask_core",
                "kind": "attention_mask",
                "coverage_family": "attention_mask",
                "coverage_family_source": "catalog",
                "features": list(CONCEPTS),
                "feature_extensions": [],
                "semantics": (
                    "masked_score[q,s] = scaled_score[q,s] if mask[q,s] is one, "
                    "otherwise zero; no softmax or V stage"
                ),
                "arithmetic": {
                    "classifier_profile": "binary_attention_mask",
                    "mask_mode": "binary_keep",
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
                "inputs": ["scaled_score_matrix", "mask_matrix"],
                "outputs": ["masked_score_matrix"],
            }
        ],
        "data_types": [
            {"name": "u1", "width_bits": 1, "signed": False},
            {"name": "s16", "width_bits": 16, "signed": True},
        ],
        "data_objects": [
            {
                "name": "scaled_score_matrix",
                "role": "scaled_attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
            {
                "name": "mask_matrix",
                "role": "attention_mask",
                "data_type": "u1",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
            {
                "name": "masked_score_matrix",
                "role": "masked_attention_score_matrix",
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
            for name, extent in {"Q": 2, "S": 3}.items()
        ],
        "parameters": [
            {"name": "Q_DIM", "default_value": "2"},
            {"name": "S_DIM", "default_value": "3"},
        ],
    }
    channels: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        channels.append(
            {
                "name": channel,
                "direction": "output" if index == 2 else "input",
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
                    "width": "1" if index == 1 else "16",
                    "signed": index != 1,
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
            required.add(f"operation.attention_mask_core.{concept}.{item['name']}")
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
                        f"operation.attention_mask_core.{concept}.{item['name']}"
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
            f"attention-mask stimulus generation exceptions: {suite['exceptions']!r}"
        )
    cases = [*suite["directed"], *suite["qualification"], *suite["randomized"]]
    for case in cases:
        if evaluate_canonical_operation(operation, case["stimulus"]) != case["expected"]:
            raise AssertionError(f"non-reproducible golden case {case['label']}")
    coverage = _coverage_evidence(operation, cases)
    if coverage["missing_bins"]:
        raise AssertionError(
            f"attention-mask coverage not closed: {coverage['missing_bins']}"
        )
    return architecture, cases, coverage


def _write_values(path: Path, values: Iterable[int]) -> None:
    path.write_text("".join(f"{int(value)}\n" for value in values), encoding="utf-8")


def _harness_source(total: int, seed: int) -> str:
    return f'''#include "V{TOP}.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

static int16_t signed16(uint32_t value) {{ return static_cast<int16_t>(value & 0xffffu); }}

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    if (argc != 4) {{ std::cerr << "usage: sim scores masks expected\\n"; return 2; }}
    std::ifstream score_file(argv[1]);
    std::ifstream mask_file(argv[2]);
    std::ifstream expected_file(argv[3]);
    std::vector<int> scores, masks, expected;
    int value = 0;
    while (score_file >> value) scores.push_back(value);
    while (mask_file >> value) masks.push_back(value);
    while (expected_file >> value) expected.push_back(value);
    if (scores.size() != {total} || masks.size() != scores.size() || expected.size() != scores.size()) {{
        std::cerr << "bad vector count " << scores.size() << " " << masks.size()
                  << " " << expected.size() << "\\n";
        return 3;
    }}

    V{TOP} dut;
    uint32_t lfsr = {seed & 0xFFFFFFFF}u;
    auto advance = [&]() {{
        lfsr ^= lfsr << 13; lfsr ^= lfsr >> 17; lfsr ^= lfsr << 5;
    }};
    auto edge = [&]() {{ dut.clk = 0; dut.eval(); dut.clk = 1; dut.eval(); }};

    dut.score_valid = 0; dut.mask_valid = 0; dut.out_ready = 0;
    dut.score_in = 0; dut.mask_keep = 0; dut.rst_n = 0;
    for (int i = 0; i < 3; ++i) edge();
    if (dut.out_valid) {{ std::cerr << "ghost valid during reset\\n"; return 10; }}

    // A score accepted without its mask must be aborted by reset.
    dut.rst_n = 1; dut.score_valid = 1; dut.mask_valid = 0; dut.score_in = 123;
    dut.clk = 0; dut.eval();
    if (!dut.score_ready) {{ std::cerr << "cannot accept score reset probe\\n"; return 11; }}
    dut.clk = 1; dut.eval();
    dut.score_valid = 0; dut.rst_n = 0; edge();
    dut.clk = 0; dut.eval();
    if (dut.out_valid) {{ std::cerr << "pre-reset score survived reset\\n"; return 12; }}

    // A mask accepted without its score must also be aborted by reset.
    dut.rst_n = 1; dut.mask_valid = 1; dut.mask_keep = 1;
    dut.clk = 0; dut.eval();
    if (!dut.mask_ready) {{ std::cerr << "cannot accept mask reset probe\\n"; return 13; }}
    dut.clk = 1; dut.eval();
    dut.mask_valid = 0; dut.rst_n = 0; edge();
    dut.clk = 0; dut.eval();
    if (dut.out_valid) {{ std::cerr << "pre-reset mask survived reset\\n"; return 14; }}

    // Deliberately skew score and mask acceptance, then hold the output stalled.
    dut.rst_n = 1; dut.out_ready = 0; dut.score_valid = 1; dut.score_in = -77;
    dut.mask_valid = 0; edge();
    dut.score_valid = 0; dut.mask_valid = 1; dut.mask_keep = 1; edge();
    dut.mask_valid = 0; edge();
    dut.clk = 0; dut.eval();
    if (!dut.out_valid || signed16(dut.score_out) != -77) {{
        std::cerr << "skewed channel pairing failed\\n"; return 15;
    }}
    int held_probe = signed16(dut.score_out);
    edge(); dut.clk = 0; dut.eval();
    if (!dut.out_valid || signed16(dut.score_out) != held_probe) {{
        std::cerr << "stalled probe changed\\n"; return 16;
    }}
    dut.out_ready = 1; edge(); dut.clk = 0; dut.eval();
    if (dut.out_valid) {{ std::cerr << "probe duplicated\\n"; return 17; }}

    size_t score_sent = 0, mask_sent = 0, received = 0;
    bool score_active = false, mask_active = false;
    bool held = false;
    int held_value = 0;
    const uint64_t max_cycles = static_cast<uint64_t>(scores.size()) * 40u + 2000u;
    for (uint64_t cycle = 0; cycle < max_cycles && received < scores.size(); ++cycle) {{
        advance();
        if (!score_active && score_sent < scores.size())
            score_active = ((lfsr & 3u) != 0u) || (cycle % 11u == 0u);
        if (!mask_active && mask_sent < masks.size())
            mask_active = ((lfsr & 12u) != 0u) || (cycle % 13u == 0u);
        dut.score_valid = score_active;
        dut.score_in = score_sent < scores.size() ? static_cast<uint16_t>(scores[score_sent]) : 0;
        dut.mask_valid = mask_active;
        dut.mask_keep = mask_sent < masks.size() ? masks[mask_sent] : 0;
        dut.out_ready = ((lfsr & 7u) != 0u);
        dut.clk = 0; dut.eval();

        int observed = signed16(dut.score_out);
        if (held && (!dut.out_valid || observed != held_value)) {{
            std::cerr << "output changed while stalled at cycle " << cycle << "\\n";
            return 20;
        }}
        bool score_transfer = dut.score_valid && dut.score_ready;
        bool mask_transfer = dut.mask_valid && dut.mask_ready;
        bool out_transfer = dut.out_valid && dut.out_ready;
        if (out_transfer) {{
            if (received >= expected.size()) {{ std::cerr << "unsolicited output\\n"; return 21; }}
            if (observed != expected[received]) {{
                std::cerr << "mismatch index=" << received << " score=" << scores[received]
                          << " mask=" << masks[received] << " got=" << observed
                          << " expected=" << expected[received] << "\\n";
                return 22;
            }}
            ++received;
        }}
        if (score_transfer) {{ ++score_sent; score_active = false; }}
        if (mask_transfer) {{ ++mask_sent; mask_active = false; }}
        held = dut.out_valid && !dut.out_ready;
        held_value = observed;
        dut.clk = 1; dut.eval();
    }}
    if (score_sent != scores.size() || mask_sent != masks.size() || received != scores.size()) {{
        std::cerr << "accounting failure score=" << score_sent << " mask=" << mask_sent
                  << " received=" << received << "\\n";
        return 23;
    }}
    dut.score_valid = 0; dut.mask_valid = 0; dut.out_ready = 1;
    for (int i = 0; i < 4; ++i) {{
        dut.clk = 0; dut.eval();
        if (dut.out_valid) {{ std::cerr << "extra output after completion\\n"; return 24; }}
        dut.clk = 1; dut.eval();
    }}
    std::cout << "PASS exhaustive_score_mask_pairs={total} independent_input_gaps=1 backpressure=1 reset_abort=2\\n";
    return 0;
}}
'''


def _mutation_catalog(source: str) -> list[Mutation]:
    mutations: list[Mutation] = []
    result_anchor = "score_out <= mask_buffer ? score_buffer : '0;"
    score_anchor = "score_buffer <= score_in;"
    mask_anchor = "mask_buffer <= mask_keep;"
    for bit in range(16):
        mask = 1 << bit
        mutations.append(
            Mutation(
                f"result_bit_flip_{bit}",
                "masked_result",
                result_anchor,
                f"score_out <= (mask_buffer ? score_buffer : '0) ^ 16'h{mask:04x};",
            )
        )
        mutations.append(
            Mutation(
                f"score_input_bit_flip_{bit}",
                "score_decode",
                score_anchor,
                f"score_buffer <= score_in ^ 16'h{mask:04x};",
            )
        )
    mutations.extend(
        [
            Mutation("invert_mask_polarity", "mask_semantics", result_anchor, "score_out <= !mask_buffer ? score_buffer : '0;"),
            Mutation("ignore_mask", "mask_semantics", result_anchor, "score_out <= score_buffer;"),
            Mutation("drop_every_score", "mask_semantics", result_anchor, "score_out <= '0;"),
            Mutation("negate_kept_score", "mask_semantics", result_anchor, "score_out <= mask_buffer ? -score_buffer : '0;"),
            Mutation("increment_kept_score", "mask_semantics", result_anchor, "score_out <= mask_buffer ? score_buffer + 1'b1 : '0;"),
            Mutation("decrement_kept_score", "mask_semantics", result_anchor, "score_out <= mask_buffer ? score_buffer - 1'b1 : '0;"),
            Mutation("invert_captured_mask", "mask_capture", mask_anchor, "mask_buffer <= !mask_keep;"),
            Mutation("captured_mask_stuck_drop", "mask_capture", mask_anchor, "mask_buffer <= 1'b0;"),
            Mutation("captured_mask_stuck_keep", "mask_capture", mask_anchor, "mask_buffer <= 1'b1;"),
            Mutation("negate_captured_score", "score_capture", score_anchor, "score_buffer <= -score_in;"),
            Mutation("zero_captured_score", "score_capture", score_anchor, "score_buffer <= '0;"),
            Mutation("arithmetic_shift_score", "score_capture", score_anchor, "score_buffer <= $signed(score_in) >>> 1;"),
            Mutation(
                "consume_unpaired_input",
                "coordinate_alignment",
                "assign consume_pair = score_pending && mask_pending && output_slot_ready;",
                "assign consume_pair = (score_pending || mask_pending) && output_slot_ready;",
            ),
            Mutation(
                "emit_unpaired_input",
                "coordinate_alignment",
                "out_valid <= score_pending && mask_pending;",
                "out_valid <= score_pending || mask_pending;",
            ),
            Mutation(
                "score_ready_always_high",
                "accepted_input_accounting",
                "assign score_ready = !score_pending || consume_pair;",
                "assign score_ready = 1'b1;",
            ),
            Mutation(
                "mask_ready_always_high",
                "accepted_input_accounting",
                "assign mask_ready  = !mask_pending  || consume_pair;",
                "assign mask_ready  = 1'b1;",
            ),
            Mutation(
                "score_ready_wrong_pair",
                "accepted_input_accounting",
                "assign score_ready = !score_pending || consume_pair;",
                "assign score_ready = !mask_pending || consume_pair;",
            ),
            Mutation(
                "mask_ready_wrong_pair",
                "accepted_input_accounting",
                "assign mask_ready  = !mask_pending  || consume_pair;",
                "assign mask_ready  = !score_pending || consume_pair;",
            ),
            Mutation(
                "ignore_output_stall",
                "output_backpressure",
                "if (output_slot_ready) begin",
                "if (1'b1) begin",
            ),
            Mutation(
                "output_slot_wrong_polarity",
                "output_backpressure",
                "assign output_slot_ready = !out_valid || out_ready;",
                "assign output_slot_ready = !out_valid || !out_ready;",
            ),
            Mutation(
                "output_slot_requires_ready",
                "output_backpressure",
                "assign output_slot_ready = !out_valid || out_ready;",
                "assign output_slot_ready = out_ready;",
            ),
            Mutation(
                "valid_stuck_low",
                "result_accounting",
                "out_valid <= score_pending && mask_pending;",
                "out_valid <= 1'b0;",
            ),
            Mutation(
                "valid_stuck_high",
                "result_accounting",
                "out_valid <= score_pending && mask_pending;",
                "out_valid <= 1'b1;",
            ),
            Mutation(
                "reset_ghost_valid",
                "reset_abort",
                "out_valid     <= 1'b0;",
                "out_valid     <= 1'b1;",
            ),
            Mutation(
                "reset_keeps_score_pending",
                "reset_abort",
                "score_pending <= 1'b0;",
                "score_pending <= 1'b1;",
            ),
            Mutation(
                "reset_keeps_mask_pending",
                "reset_abort",
                "mask_pending  <= 1'b0;",
                "mask_pending  <= 1'b1;",
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
    *,
    source: str,
    work: Path,
    scores: Path,
    masks: Path,
    expected: Path,
    total: int,
    seed: int,
) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    rtl = work / RTL.name
    harness = work / "harness.cpp"
    rtl.write_text(source, encoding="utf-8")
    harness.write_text(_harness_source(total, seed), encoding="utf-8")
    obj = work / "obj"
    compiled = subprocess.run(
        [
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
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if compiled.returncode != 0:
        return {
            "compile_valid": False,
            "passed": False,
            "returncode": compiled.returncode,
            "log": (compiled.stdout + compiled.stderr)[-5000:],
        }
    simulated = subprocess.run(
        [str(obj / f"V{TOP}"), str(scores), str(masks), str(expected)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
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
    pool_scores: list[int] = []
    pool_masks: list[int] = []
    for case in cases:
        scores = list(map(int, case["stimulus"]["scaled_score_matrix"]))
        masks = list(map(int, case["stimulus"]["mask_matrix"]))
        if len(scores) != len(masks):
            raise AssertionError(f"unaligned canonical case {case['label']}")
        pool_scores.extend(scores)
        pool_masks.extend(masks)
    exhaustive_scores: list[int] = []
    exhaustive_masks: list[int] = []
    for score in range(-(1 << 15), 1 << 15):
        exhaustive_scores.extend((score, score))
        exhaustive_masks.extend((0, 1))
    scores = [*pool_scores, *exhaustive_scores]
    masks = [*pool_masks, *exhaustive_masks]
    expected = [score if mask else 0 for score, mask in zip(scores, masks)]

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
        owned_temp = tempfile.TemporaryDirectory(prefix="attention-mask-qualify-")
        root = Path(owned_temp.name)
    else:
        root = work_root
        root.mkdir(parents=True, exist_ok=True)
    score_file = root / "scores.txt"
    mask_file = root / "masks.txt"
    expected_file = root / "expected.txt"
    _write_values(score_file, scores)
    _write_values(mask_file, masks)
    _write_values(expected_file, expected)

    baseline = _run_one(
        source=source,
        work=root / "baseline",
        scores=score_file,
        masks=mask_file,
        expected=expected_file,
        total=len(scores),
        seed=seed,
    )
    if not baseline["passed"]:
        raise AssertionError(f"attention-mask baseline failed: {baseline['log']}")

    def run_mutation(mutation: Mutation) -> dict[str, Any]:
        mutated = source.replace(mutation.anchor, mutation.replacement, 1)
        result = _run_one(
            source=mutated,
            work=root / "mutants" / mutation.name,
            scores=score_file,
            masks=mask_file,
            expected=expected_file,
            total=len(scores),
            seed=seed,
        )
        return {**asdict(mutation), **result, "killed": not result["passed"]}

    mutation_results: list[dict[str, Any]] = []
    if selected:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {executor.submit(run_mutation, item): item for item in selected}
            for future in as_completed(futures):
                mutation_results.append(future.result())
        mutation_results.sort(key=lambda item: item["name"])

    compile_valid = [item for item in mutation_results if item["compile_valid"]]
    compile_invalid = [item for item in mutation_results if not item["compile_valid"]]
    killed = [item for item in compile_valid if item["killed"]]
    survived = [item for item in compile_valid if not item["killed"]]
    if compile_invalid:
        raise AssertionError(
            "attention-mask mutation catalog contains compile-invalid faults: "
            + ", ".join(item["name"] for item in compile_invalid)
        )
    if survived:
        raise AssertionError(
            "attention-mask mutations survived: "
            + ", ".join(item["name"] for item in survived)
        )

    operation = compiled_operation()[1]
    summary = {
        "schema_version": 1,
        "passed": baseline["passed"] and not compile_invalid and not survived,
        "contract": {
            "classifier_profile": operation["arithmetic"]["classifier_profile"],
            "mask_mode": operation["arithmetic"]["mask_mode"],
            "shape": operation["dimensions"],
            "score_type": "s16",
            "mask_type": "u1",
            "result_type": "s16",
        },
        "rtl": {
            "path": str(RTL.relative_to(HERE)),
            "sha256": hashlib.sha256(source.encode()).hexdigest(),
        },
        "stimulus": {
            "directed_and_qualification_cases": len(cases) - randomized_count,
            "randomized_cases": randomized_count,
            "seed": seed,
            "pool_elements": len(pool_scores),
            "exhaustive_signed16_mask_pairs": len(exhaustive_scores),
            "total_comparisons": len(scores),
            "independent_score_mask_valid_gaps": True,
        },
        "coverage": coverage,
        "assertions_exercised": [
            "oracle_equivalence",
            "binary_mask_legality",
            "mask_polarity",
            "coordinate_alignment",
            "accepted_input_accounting",
            "output_stability_under_backpressure",
            "reset_abort_no_ghost_result",
        ],
        "baseline": baseline,
        "mutation_campaign": {
            "catalog_size": len(catalog),
            "selected": len(selected),
            "compile_valid": len(compile_valid),
            "compile_invalid": len(compile_invalid),
            "killed": len(killed),
            "survived": len(survived),
            "results": mutation_results,
        },
    }
    if owned_temp is not None:
        owned_temp.cleanup()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-cases", type=int, default=DEFAULT_RANDOM_CASES)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--mutants", type=int, default=0)
    parser.add_argument("--all-mutants", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    summary = run_qualification(
        randomized_count=args.random_cases,
        seed=args.seed,
        mutant_limit=None if args.all_mutants else args.mutants,
        workers=args.workers,
        work_root=args.work_root,
    )
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
