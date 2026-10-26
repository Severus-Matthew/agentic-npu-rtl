"""Qualify a real systolic Q*K^T RTL against the code-owned attention_qk pool.

The run has three strict gates:

1. The verifier-tool generator must construct every reachable QK coverage bin.
2. The unmodified RTL must pass all directed, discriminating, randomized, reset,
   completion-pulse, exact-latency, and no-reset-between-jobs checks.
3. Every compile-valid selected RTL mutant must be rejected by that same frozen TB.

Mutants are made only in temporary copies.  The checked-in baseline is never
edited by this runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
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
RTL = HERE / "rtl"
TOP = "tb_qk_systolic_pool"
N = 4
D = 4
DATA_WIDTH = 16
ACC_WIDTH = 16
DEFAULT_RANDOM_CASES = 128
DEFAULT_MUTANTS = 128
DEFAULT_SEED = 0x514B


@dataclass(frozen=True)
class Mutation:
    name: str
    domain: str
    relative_path: str
    anchor: str
    replacement: str


def _serialization(dimensions: list[str]) -> dict[str, Any]:
    return {
        "kind": "dense_tensor",
        "index_order": dimensions,
        "description": "Row-major tensor; the last declared axis varies fastest.",
    }


def build_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the frozen arithmetic contract and its canonical tensor channels."""

    architecture = {
        "design": {
            "name": "qk_systolic_attention_qk",
            "description": (
                "Pinned output-stationary Q*K^T RTL bound through a test adapter to "
                "the independent code-owned attention_qk arithmetic profile."
            ),
        },
        "operations": [
            {
                "name": "qk_score_core",
                "kind": "qk_score",
                "coverage_family": "attention_qk",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "operand_values",
                    "accumulation",
                    "attention_scores",
                ],
                "feature_extensions": [],
                "semantics": (
                    "score[q,s] = sum_d Q[q,d]*K[s,d]; signed int8 operands "
                    "are sign-extended to the RTL input, the signed int16 "
                    "accumulator wraps after every add, and the int16 result is exact."
                ),
                "arithmetic": {
                    "classifier_profile": "integer_qk_score",
                    "score_product_data_type": "s16",
                    "score_accumulator_data_type": "s16",
                    "score_accumulator_initialization": 0,
                    "score_reduction_dimensions": ["D"],
                    "score_reduction_order": (
                        "increasing_declared_reduction_coordinate"
                    ),
                    "score_reduction_conversion": (
                        "wrap_twos_complement_after_each_add"
                    ),
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
                "inputs": ["Q_matrix", "K_matrix"],
                "outputs": ["score_matrix"],
            }
        ],
        "data_types": [
            {"name": "s8", "width_bits": 8, "signed": True},
            {"name": "s16", "width_bits": 16, "signed": True},
        ],
        "data_objects": [
            {
                "name": "Q_matrix",
                "role": "query_matrix",
                "data_type": "s8",
                "dimensions": ["Q", "D"],
                "serialization": _serialization(["Q", "D"]),
            },
            {
                "name": "K_matrix",
                "role": "key_matrix",
                "data_type": "s8",
                "dimensions": ["S", "D"],
                "serialization": _serialization(["S", "D"]),
            },
            {
                "name": "score_matrix",
                "role": "attention_score_matrix",
                "data_type": "s16",
                "dimensions": ["Q", "S"],
                "serialization": _serialization(["Q", "S"]),
            },
        ],
        "dimensions": [
            {
                "name": name,
                "minimum": N if name != "D" else D,
                "maximum": N if name != "D" else D,
                "runtime_configurable": False,
                "bound_parameter": f"{name}_DIM",
            }
            for name in ("Q", "S", "D")
        ],
        "parameters": [
            {
                "name": f"{name}_DIM",
                "default_value": str(N if name != "D" else D),
            }
            for name in ("Q", "S", "D")
        ],
    }

    channels: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    for index, obj in enumerate(architecture["data_objects"]):
        channel = f"tensor_{index}"
        direction = "output" if obj["name"] == "score_matrix" else "input"
        channels.append(
            {
                "name": channel,
                "direction": direction,
                "protocol_profile": "ready_valid",
                "data_objects": [obj["name"]],
                "ordering": "declared dimension order",
                "framing": "exact tensor",
            }
        )
        width = 16 if obj["name"] == "score_matrix" else 8
        signals.extend(
            [
                {"name": f"{channel}_valid", "channel": channel, "role": "valid"},
                {"name": f"{channel}_ready", "channel": channel, "role": "ready"},
                {
                    "name": f"{channel}_payload",
                    "channel": channel,
                    "role": "payload",
                    "width": str(width),
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


def _manual_cases(operation: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = [
        (
            "manual_all_coordinates_signed_asymmetric",
            [
                1, 0, 0, 0,
                0, -1, 0, 0,
                0, 0, 2, 0,
                0, 0, 0, -2,
            ],
            [
                11, -12, 13, -14,
                -21, 22, -23, 24,
                31, 32, -33, -34,
                -41, -42, 43, 44,
            ],
        ),
        (
            "manual_alternating_extremes",
            [127, -128, 127, -128] * N,
            [-128, 127, -1, 1, 1, -1, 127, -128] * 2,
        ),
    ]
    cases = []
    for label, query, key in raw:
        stimulus = {"Q_matrix": query, "K_matrix": key}
        cases.append(
            {
                "operation_name": "qk_score_core",
                "kind": "qualification",
                "label": label,
                "target": None,
                "stimulus": stimulus,
                "expected": evaluate_canonical_operation(operation, stimulus),
            }
        )
    return cases


def _predicate_matches(value: Any, predicate: Mapping[str, Any]) -> bool:
    op = str(predicate.get("op", ""))
    args = list(predicate.get("args", []))
    if op == "eq" and len(args) == 1:
        return value == args[0]
    if op == "neq" and len(args) == 1:
        return value != args[0]
    if op == "lt" and len(args) == 1:
        return value < args[0]
    if op == "lte" and len(args) == 1:
        return value <= args[0]
    if op == "gt" and len(args) == 1:
        return value > args[0]
    if op == "gte" and len(args) == 1:
        return value >= args[0]
    if op == "between" and len(args) == 2:
        return args[0] <= value <= args[1]
    if op == "one_of" and args:
        return value in args
    if op == "truthy" and not args:
        return bool(value)
    if op == "falsy" and not args:
        return not bool(value)
    return False


def _coverage_evidence(
    operation: Mapping[str, Any], cases: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    concepts = ("dimensions", "operand_values", "accumulation", "attention_scores")
    required: set[str] = set()
    hits: set[str] = set()
    for concept in concepts:
        for item in canonical_bins_for_concept(operation, concept) or []:
            required.add(f"operation.qk_score_core.{concept}.{item['name']}")
    for case in cases:
        job = assemble_canonical_job(
            operation,
            case["stimulus"],
            case["expected"],
            case["expected"],
        )
        assert job is not None
        evidence = classify_operation_job(job)
        for concept in concepts:
            for item in canonical_bins_for_concept(operation, concept) or []:
                if any(
                    _predicate_matches(value, item.get("predicate", {}))
                    for value in evidence.get(concept, [])
                ):
                    hits.add(
                        f"operation.qk_score_core.{concept}.{item['name']}"
                    )
    return {
        "required_bins": len(required),
        "hit_bins": len(hits),
        "missing_bins": sorted(required - hits),
        "hit_bin_ids": sorted(hits),
    }


def build_cases(randomized_count: int, seed: int) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    architecture, operation = compiled_operation()
    suite = generate_canonical_stimulus_suite(
        operation, randomized_count=randomized_count, seed=seed
    )
    if suite["exceptions"]:
        raise AssertionError(f"QK stimulus generation exceptions: {suite['exceptions']!r}")
    cases = [
        *suite["directed"],
        *suite["qualification"],
        *_manual_cases(operation),
        *suite["randomized"],
    ]
    for case in cases:
        regenerated = evaluate_canonical_operation(operation, case["stimulus"])
        if regenerated != case["expected"]:
            raise AssertionError(f"non-reproducible golden case {case['label']}")
    coverage = _coverage_evidence(operation, cases)
    if coverage["missing_bins"]:
        raise AssertionError(f"QK coverage not closed: {coverage['missing_bins']}")
    return architecture, cases, coverage


def _hex16(value: int) -> str:
    return f"{value & 0xFFFF:04x}"


def _write_hex(path: Path, values: Iterable[int]) -> None:
    path.write_text("".join(f"{_hex16(value)}\n" for value in values))


def _tb_source(case_count: int) -> str:
    return f"""`timescale 1ns/1ps
module {TOP};
    localparam int N = {N};
    localparam int D = {D};
    localparam int DATA_WIDTH = {DATA_WIDTH};
    localparam int ACC_WIDTH = {ACC_WIDTH};
    localparam int FRAC_BITS = 0;
    localparam int LAT = 2*N + D;
    localparam int FEED_CYCLES = N + D - 1;
    localparam int CASE_COUNT = {case_count};

    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic start = 1'b0;
    logic [DATA_WIDTH-1:0] q_in [0:N-1];
    logic [DATA_WIDTH-1:0] k_in [0:N-1];
    logic [DATA_WIDTH-1:0] s_out [0:N-1][0:N-1];
    logic done;
    logic [15:0] q_mem [0:CASE_COUNT*N*D-1];
    logic [15:0] k_mem [0:CASE_COUNT*N*D-1];
    logic [15:0] score_mem [0:CASE_COUNT*N*N-1];
    int completed_cases = 0;

    always #5 clk = ~clk;

    qk_systolic #(
        .N(N), .D(D), .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH), .FRAC_BITS(FRAC_BITS)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .q_in(q_in), .k_in(k_in), .s_out(s_out), .done(done)
    );

    task automatic fail(input string message);
        $display("QK_TB_FAIL %s", message);
        $fatal(1);
    endtask

    task automatic clear_inputs;
        for (int index = 0; index < N; index++) begin
            q_in[index] = '0;
            k_in[index] = '0;
        end
    endtask

    task automatic drive_feed(input int case_index, input int feed_cycle);
        int depth;
        for (int row = 0; row < N; row++) begin
            depth = feed_cycle - row;
            q_in[row] = (depth >= 0 && depth < D)
                ? q_mem[case_index*N*D + row*D + depth] : '0;
        end
        for (int row = 0; row < N; row++) begin
            depth = feed_cycle - row;
            k_in[row] = (depth >= 0 && depth < D)
                ? k_mem[case_index*N*D + row*D + depth] : '0;
        end
    endtask

    task automatic compare_case(input int case_index);
        logic [15:0] expected;
        for (int row = 0; row < N; row++) begin
            for (int col = 0; col < N; col++) begin
                expected = score_mem[case_index*N*N + row*N + col];
                if (s_out[row][col] !== expected)
                    fail($sformatf(
                        "output_mismatch case=%0d coordinate=(%0d,%0d) expected=0x%04h observed=0x%04h",
                        case_index, row, col, expected, s_out[row][col]
                    ));
            end
        end
    endtask

    task automatic run_case(input int case_index);
        int latency;
        clear_inputs();
        @(negedge clk);
        if (done) fail("ghost_done_before_start");
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;
        drive_feed(case_index, 0);
        latency = 0;
        while (!done) begin
            @(negedge clk);
            latency++;
            if (latency < FEED_CYCLES) drive_feed(case_index, latency);
            else clear_inputs();
            if (latency > LAT + 3)
                fail($sformatf("completion_timeout case=%0d", case_index));
        end
        if (latency != LAT + 1)
            fail($sformatf(
                "done_latency case=%0d expected=%0d observed=%0d",
                case_index, LAT + 1, latency
            ));
        compare_case(case_index);
        completed_cases++;
        @(negedge clk);
        if (done) fail("done_pulse_wider_than_one_cycle");
    endtask

    task automatic check_reset_abort(input int case_index);
        clear_inputs();
        @(negedge clk);
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;
        drive_feed(case_index, 0);
        @(negedge clk);
        drive_feed(case_index, 1);
        @(negedge clk);
        rst_n = 1'b0;
        clear_inputs();
        // One active clock edge is the minimum synchronous-reset contract.
        // Holding reset longer would hide a datapath that incorrectly relies on
        // the following idle cycle rather than the reset edge itself.
        @(negedge clk);
        if (done) fail("ghost_done_during_reset_abort");
        rst_n = 1'b1;
        repeat (LAT + 3) begin
            @(negedge clk);
            if (done) fail("ghost_done_after_reset_abort");
        end
    endtask

    initial begin
        $readmemh("q_vectors.hex", q_mem);
        $readmemh("k_vectors.hex", k_mem);
        $readmemh("score_vectors.hex", score_mem);
        clear_inputs();
        repeat (3) @(negedge clk);
        if (done !== 1'b0) fail("done_not_zero_in_reset");
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        check_reset_abort(0);
        for (int case_index = 0; case_index < CASE_COUNT; case_index++)
            run_case(case_index);

        if (completed_cases != CASE_COUNT)
            fail($sformatf(
                "result_accounting expected=%0d observed=%0d",
                CASE_COUNT, completed_cases
            ));
        $display("QK_TB_PASS cases=%0d scores=%0d", CASE_COUNT, CASE_COUNT*N*N);
        $finish;
    end
endmodule
"""


def render_testbench(
    output_dir: Path, cases: list[Mapping[str, Any]], coverage: Mapping[str, Any]
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    queries = [value for case in cases for value in case["stimulus"]["Q_matrix"]]
    keys = [value for case in cases for value in case["stimulus"]["K_matrix"]]
    scores = [value for case in cases for value in case["expected"]["score_matrix"]]
    _write_hex(output_dir / "q_vectors.hex", queries)
    _write_hex(output_dir / "k_vectors.hex", keys)
    _write_hex(output_dir / "score_vectors.hex", scores)
    tb_path = output_dir / f"{TOP}.sv"
    tb_path.write_text(_tb_source(len(cases)))
    manifest = {
        "schema_version": 1,
        "case_count": len(cases),
        "score_comparisons": len(cases) * N * N,
        "coverage": dict(coverage),
        "cases": [
            {
                "label": case["label"],
                "kind": case["kind"],
                "target": case.get("target"),
                "stimulus": case["stimulus"],
                "expected": case["expected"],
            }
            for case in cases
        ],
    }
    (output_dir / "vector_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _structural_mutations() -> list[Mutation]:
    mac = "mac_pe.sv"
    qk = "qk_systolic.sv"
    return [
        Mutation("multiply_becomes_add", "arithmetic", mac,
                 "            reg_product <= reg_a * reg_b;",
                 "            reg_product <= reg_a + reg_b;"),
        Mutation("multiply_becomes_subtract", "arithmetic", mac,
                 "            reg_product <= reg_a * reg_b;",
                 "            reg_product <= reg_a - reg_b;"),
        Mutation("q_sign_extension_dropped", "signedness", qk,
                 "            assign a_wire[i][0] = q_in[i];",
                 "            assign a_wire[i][0] = {{8{1'b0}}, q_in[i][7:0]};"),
        Mutation("k_sign_extension_dropped", "signedness", qk,
                 "            assign b_wire[0][i] = k_in[i];",
                 "            assign b_wire[0][i] = {{8{1'b0}}, k_in[i][7:0]};"),
        Mutation("multiply_uses_q_twice", "arithmetic", mac,
                 "            reg_product <= reg_a * reg_b;",
                 "            reg_product <= reg_a * reg_a;"),
        Mutation("multiply_uses_k_twice", "arithmetic", mac,
                 "            reg_product <= reg_a * reg_b;",
                 "            reg_product <= reg_b * reg_b;"),
        Mutation("product_negated", "arithmetic", mac,
                 "            reg_product <= reg_a * reg_b;",
                 "            reg_product <= -(reg_a * reg_b);"),
        Mutation("product_off_by_one", "arithmetic", mac,
                 "            reg_product <= reg_a * reg_b;",
                 "            reg_product <= reg_a * reg_b + 1'b1;"),
        Mutation("accumulator_subtracts", "accumulation", mac,
                 "            acc         <= acc + ACC_WIDTH'(reg_product);",
                 "            acc         <= acc - ACC_WIDTH'(reg_product);"),
        Mutation("accumulator_overwrites", "accumulation", mac,
                 "            acc         <= acc + ACC_WIDTH'(reg_product);",
                 "            acc         <= ACC_WIDTH'(reg_product);"),
        Mutation("accumulator_holds", "accumulation", mac,
                 "            acc         <= acc + ACC_WIDTH'(reg_product);",
                 "            acc         <= acc;"),
        Mutation("accumulator_double_counts", "accumulation", mac,
                 "            acc         <= acc + ACC_WIDTH'(reg_product);",
                 "            acc         <= acc + (ACC_WIDTH'(reg_product) <<< 1);"),
        Mutation("sum_omits_latest_product", "pipeline", mac,
                 "            sum_out     <= acc + ACC_WIDTH'(reg_product);",
                 "            sum_out     <= acc;"),
        Mutation("sum_subtracts_latest_product", "pipeline", mac,
                 "            sum_out     <= acc + ACC_WIDTH'(reg_product);",
                 "            sum_out     <= acc - ACC_WIDTH'(reg_product);"),
        Mutation("accumulator_reset_removed", "reset", mac,
                 "            acc         <= '0;",
                 "            acc         <= acc;"),
        Mutation("q_rows_rotated", "routing", qk,
                 "            assign a_wire[i][0] = q_in[i];",
                 "            assign a_wire[i][0] = q_in[(i + 1) % N];"),
        Mutation("k_rows_rotated", "routing", qk,
                 "            assign b_wire[0][i] = k_in[i];",
                 "            assign b_wire[0][i] = k_in[(i + 1) % N];"),
        Mutation("q_and_k_edges_swapped_q", "routing", qk,
                 "            assign a_wire[i][0] = q_in[i];",
                 "            assign a_wire[i][0] = k_in[i];"),
        Mutation("q_and_k_edges_swapped_k", "routing", qk,
                 "            assign b_wire[0][i] = k_in[i];",
                 "            assign b_wire[0][i] = q_in[i];"),
        Mutation("q_shift_stuck_zero", "routing", qk,
                 "                    else     a_wire[i][j+1] <= a_wire[i][j];",
                 "                    else     a_wire[i][j+1] <= '0;"),
        Mutation("k_shift_stuck_zero", "routing", qk,
                 "                    else     b_wire[i+1][j] <= b_wire[i][j];",
                 "                    else     b_wire[i+1][j] <= '0;"),
        Mutation("q_shift_negates", "routing", qk,
                 "                    else     a_wire[i][j+1] <= a_wire[i][j];",
                 "                    else     a_wire[i][j+1] <= -$signed(a_wire[i][j]);"),
        Mutation("k_shift_negates", "routing", qk,
                 "                    else     b_wire[i+1][j] <= b_wire[i][j];",
                 "                    else     b_wire[i+1][j] <= -$signed(b_wire[i][j]);"),
        Mutation("output_transposed", "coordinate", qk,
                 "                    s_out[r][c] <= pe_out[r][c][FRAC_BITS +: DATA_WIDTH];",
                 "                    s_out[r][c] <= pe_out[c][r][FRAC_BITS +: DATA_WIDTH];"),
        Mutation("output_columns_rotated", "coordinate", qk,
                 "                    s_out[r][c] <= pe_out[r][c][FRAC_BITS +: DATA_WIDTH];",
                 "                    s_out[r][c] <= pe_out[r][(c + 1) % N][FRAC_BITS +: DATA_WIDTH];"),
        Mutation("output_rows_rotated", "coordinate", qk,
                 "                    s_out[r][c] <= pe_out[r][c][FRAC_BITS +: DATA_WIDTH];",
                 "                    s_out[r][c] <= pe_out[(r + 1) % N][c][FRAC_BITS +: DATA_WIDTH];"),
        Mutation("capture_one_cycle_early", "lifecycle", qk,
                 "    assign capture = busy && (cnt == CNT_WIDTH'(LAT));",
                 "    assign capture = busy && (cnt == CNT_WIDTH'(LAT - 1));"),
        Mutation("capture_one_cycle_late", "lifecycle", qk,
                 "    assign capture = busy && (cnt == CNT_WIDTH'(LAT));",
                 "    assign capture = busy && (cnt == CNT_WIDTH'(LAT + 1));"),
        Mutation("done_stuck_low", "lifecycle", qk,
                 "            done <= capture;",
                 "            done <= 1'b0;"),
        Mutation("done_sticky", "lifecycle", qk,
                 "            done <= capture;",
                 "            done <= done | capture;"),
        Mutation("start_ignored", "lifecycle", qk,
                 "            if (start) begin",
                 "            if (1'b0 && start) begin"),
        Mutation("counter_steps_by_two", "lifecycle", qk,
                 "                else         cnt  <= cnt + 1'b1;",
                 "                else         cnt  <= cnt + 2'd2;"),
        Mutation("busy_never_retires", "lifecycle", qk,
                 "                if (capture) busy <= 1'b0;",
                 "                if (capture) busy <= 1'b1;"),
        Mutation("idle_clear_removed", "reset", qk,
                 "    assign clr = !rst_n || !busy;",
                 "    assign clr = !rst_n;"),
        Mutation("control_reset_polarity_inverted", "reset", qk,
                 "        if (!rst_n) begin",
                 "        if (rst_n) begin"),
    ]


def _equivalent_exclusions() -> list[dict[str, str]]:
    return [
        {
            "name": "multiply_unsigned_rhs_modulo_2pow16",
            "reason": (
                "Signed and unsigned multiplication have identical low 16 result "
                "bits, and this frozen contract intentionally observes a 16-bit "
                "wrap accumulator/result. The mutation is mathematically equivalent."
            ),
        },
        {
            "name": "global_clear_term_removed",
            "reason": (
                "The control reset forces busy low and !busy clears every PE before "
                "the next legal feed. Removing the redundant !rst_n term from clr "
                "does not change any contract-observable behavior."
            ),
        },
    ]


def _bit_mutations() -> list[Mutation]:
    qk = "qk_systolic.sv"
    result: list[Mutation] = []
    output_anchor = (
        "                    s_out[r][c] <= "
        "pe_out[r][c][FRAC_BITS +: DATA_WIDTH];"
    )
    for row in range(N):
        for col in range(N):
            for bit in range(DATA_WIDTH):
                result.append(
                    Mutation(
                        f"output_r{row}_c{col}_bit{bit}_flip",
                        "output_bit",
                        qk,
                        output_anchor,
                        (
                            "                    s_out[r][c] <= "
                            "pe_out[r][c][FRAC_BITS +: DATA_WIDTH] ^ "
                            f"(((r == {row}) && (c == {col})) ? "
                            f"(DATA_WIDTH'(1) << {bit}) : '0);"
                        ),
                    )
                )
    for operand, anchor, wire in (
        ("q", "            assign a_wire[i][0] = q_in[i];", "q_in"),
        ("k", "            assign b_wire[0][i] = k_in[i];", "k_in"),
    ):
        lhs = "a_wire[i][0]" if operand == "q" else "b_wire[0][i]"
        for row in range(N):
            for bit in range(DATA_WIDTH):
                result.append(
                    Mutation(
                        f"{operand}_row{row}_bit{bit}_flip",
                        "input_bit",
                        qk,
                        anchor,
                        (
                            f"            assign {lhs} = {wire}[i] ^ "
                            f"((i == {row}) ? (DATA_WIDTH'(1) << {bit}) : '0);"
                        ),
                    )
                )
    return result


def select_mutations(count: int, seed: int) -> list[Mutation]:
    structural = _structural_mutations()
    if count <= len(structural):
        chosen = random.Random(seed).sample(structural, count)
    else:
        extra_count = min(count - len(structural), len(_bit_mutations()))
        chosen = [*structural, *random.Random(seed).sample(_bit_mutations(), extra_count)]
    names = [item.name for item in chosen]
    if len(names) != len(set(names)):
        raise AssertionError("mutation names must be unique")
    return chosen


def _apply_mutation(source_dir: Path, destination: Path, mutation: Mutation) -> None:
    shutil.copytree(source_dir, destination)
    path = destination / mutation.relative_path
    text = path.read_text()
    count = text.count(mutation.anchor)
    if count != 1:
        raise AssertionError(
            f"{mutation.name}: anchor count {count}, expected exactly one"
        )
    path.write_text(text.replace(mutation.anchor, mutation.replacement, 1))


_DUT_FAILURE_MARKERS = (
        "output_mismatch",
        "done_latency",
        "completion_timeout",
        "done_pulse_wider_than_one_cycle",
        "ghost_done",
        "done_not_zero_in_reset",
        "result_accounting",
)


def _diagnostic(stdout: str, stderr: str) -> str:
    combined = f"{stdout}\n{stderr}"
    for marker in _DUT_FAILURE_MARKERS:
        if marker in combined:
            return marker
    return "simulation_failure"


def simulate(
    rtl_dir: Path,
    generated_dir: Path,
    work_dir: Path,
    *,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    build = work_dir / "build"
    build.mkdir(parents=True, exist_ok=True)
    compile_cmd = [
        shutil.which("verilator") or "verilator",
        "--binary",
        "--timing",
        "-Wno-fatal",
        "-j",
        "1",
        str(rtl_dir / "mac_pe.sv"),
        str(rtl_dir / "qk_systolic.sv"),
        str(generated_dir / f"{TOP}.sv"),
        "--top-module",
        TOP,
        "--Mdir",
        str(build),
    ]
    try:
        compiled = subprocess.run(
            compile_cmd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "compile_status": "TIMEOUT",
            "simulation_status": "NOT_RUN",
            "diagnostic": "compile_timeout",
            "stdout_tail": str(exc.stdout or "")[-2000:],
            "stderr_tail": str(exc.stderr or "")[-2000:],
        }
    if compiled.returncode != 0:
        return {
            "compile_status": "FAIL",
            "simulation_status": "NOT_RUN",
            "diagnostic": "compile_failure",
            "stdout_tail": compiled.stdout[-2000:],
            "stderr_tail": compiled.stderr[-4000:],
        }
    executable = build / f"V{TOP}"
    try:
        ran = subprocess.run(
            [str(executable)],
            cwd=generated_dir,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "compile_status": "PASS",
            "simulation_status": "FAIL",
            "diagnostic": "simulation_timeout",
            "stdout_tail": str(exc.stdout or "")[-4000:],
            "stderr_tail": str(exc.stderr or "")[-2000:],
        }
    passed = ran.returncode == 0 and "QK_TB_PASS" in ran.stdout
    return {
        "compile_status": "PASS",
        "simulation_status": "PASS" if passed else "FAIL",
        "diagnostic": "pass" if passed else _diagnostic(ran.stdout, ran.stderr),
        "stdout_tail": ran.stdout[-4000:],
        "stderr_tail": ran.stderr[-2000:],
    }


def _run_mutant(
    mutation: Mutation,
    generated_dir: Path,
    root: Path,
) -> dict[str, Any]:
    safe_name = mutation.name.replace("/", "_")
    work_dir = root / safe_name
    mutant_rtl = work_dir / "rtl"
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        _apply_mutation(RTL, mutant_rtl, mutation)
        result = simulate(mutant_rtl, generated_dir, work_dir)
    except Exception as exc:  # preserve an auditable per-mutant result
        result = {
            "compile_status": "HARNESS_ERROR",
            "simulation_status": "NOT_RUN",
            "diagnostic": f"harness_error:{type(exc).__name__}:{exc}",
            "stdout_tail": "",
            "stderr_tail": "",
        }
    compile_valid = result["compile_status"] == "PASS"
    killed = (
        compile_valid and result["simulation_status"] == "FAIL"
        and result["diagnostic"] in _DUT_FAILURE_MARKERS
    )
    infrastructure_failure = (
        compile_valid and result["simulation_status"] != "PASS"
        and result["diagnostic"] not in _DUT_FAILURE_MARKERS
    )
    return {**asdict(mutation), **result, "compile_valid": compile_valid, "killed": killed,
            "infrastructure_failure": infrastructure_failure}


def run_qualification(
    output_dir: Path,
    *,
    randomized_cases: int = DEFAULT_RANDOM_CASES,
    mutant_count: int = DEFAULT_MUTANTS,
    seed: int = DEFAULT_SEED,
    jobs: int = 4,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, cases, coverage = build_cases(randomized_cases, seed)
    generated = output_dir / "generated"
    manifest = render_testbench(generated, cases, coverage)
    (output_dir / "architecture_contract.json").write_text(
        json.dumps(architecture, indent=2)
    )

    baseline = simulate(RTL, generated, output_dir / "baseline")
    if baseline["compile_status"] != "PASS" or baseline["simulation_status"] != "PASS":
        summary = {
            "status": "BASELINE_FAIL",
            "seed": seed,
            "coverage": coverage,
            "vectors": manifest,
            "baseline": baseline,
            "mutations": [],
        }
        (output_dir / "qualification_summary.json").write_text(
            json.dumps(summary, indent=2)
        )
        return summary

    selected = select_mutations(mutant_count, seed ^ 0xA77E17)
    mutation_root = output_dir / "mutants"
    mutation_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(jobs, 4))) as executor:
        futures = {
            executor.submit(_run_mutant, item, generated, mutation_root): item.name
            for item in selected
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["name"])

    compile_valid = [item for item in results if item["compile_valid"]]
    killed = [item for item in compile_valid if item["killed"]]
    survivors = [item for item in compile_valid if not item["killed"]]
    invalid = [item for item in results if not item["compile_valid"]]
    status = (
        "PASS"
        if len(compile_valid) == len(results)
        and len(killed) == len(compile_valid)
        and not coverage["missing_bins"]
        else "MUTATION_GAPS"
    )
    summary = {
        "schema_version": 1,
        "status": status,
        "seed": seed,
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(RTL.glob("*.sv"))
        },
        "coverage": coverage,
        "case_count": len(cases),
        "score_comparisons_per_variant": len(cases) * N * N,
        "baseline": baseline,
        "mutation_campaign": {
            "requested": mutant_count,
            "selected": len(results),
            "compile_valid": len(compile_valid),
            "killed": len(killed),
            "survived": len(survivors),
            "invalid": len(invalid),
            "kill_rate_compile_valid": (
                len(killed) / len(compile_valid) if compile_valid else 0.0
            ),
            "survivor_names": [item["name"] for item in survivors],
            "invalid_names": [item["name"] for item in invalid],
            "simulation_infrastructure_errors": sum(item["infrastructure_failure"] for item in results),
            "simulation_infrastructure_error_names": [item["name"] for item in results if item["infrastructure_failure"]],
            "equivalent_exclusions": _equivalent_exclusions(),
            "by_domain": {
                domain: {
                    "selected": sum(item["domain"] == domain for item in results),
                    "killed": sum(
                        item["domain"] == domain and item["killed"] for item in results
                    ),
                }
                for domain in sorted({item["domain"] for item in results})
            },
        },
        "mutations": results,
    }
    (output_dir / "qualification_summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--randomized-cases", type=int, default=DEFAULT_RANDOM_CASES)
    parser.add_argument("--mutants", type=int, default=DEFAULT_MUTANTS)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 4))
    args = parser.parse_args()
    if args.randomized_cases < 0 or args.mutants < 0:
        parser.error("case and mutant counts must be non-negative")
    summary = run_qualification(
        args.output_dir,
        randomized_cases=args.randomized_cases,
        mutant_count=args.mutants,
        seed=args.seed,
        jobs=args.jobs,
    )
    print(json.dumps({
        "status": summary["status"],
        "coverage": summary["coverage"],
        "case_count": summary.get("case_count"),
        "mutation_campaign": summary.get("mutation_campaign"),
        "report": str((args.output_dir / "qualification_summary.json").resolve()),
    }, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
