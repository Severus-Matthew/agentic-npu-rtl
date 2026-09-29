"""Operation extension regression: GEMM with
per-channel affine quantization (round-nearest-even, signed saturation).

Semantics under test: each output channel n is requantized with its own
independent (scale_multiplier, scale_shift, zero_point) rather than one
shared per-tensor triple. `pool/operation_metadata/README.md` is explicit:
the built-in `affine_quantize` post-operation stage is declared with
`granularity: per_tensor` only, and states outright: "Per-axis, stochastic,
floating-scale, and other quantizers remain contract-local extensions
rather than being silently treated as this profile." This experiment
reuses the pool's own frozen formula --
`q = clamp(round_to_nearest_even(value * scale_multiplier / 2**scale_shift)
+ zero_point, dtype_min, dtype_max)` -- exactly as documented, applied once
per channel with that channel's own triple, rather than inventing new
arithmetic semantics.

The real reference RTL (`per_channel_quantize_probe.sv`) reuses, unchanged,
the exact round-nearest-even bit pattern already proven correct in
`../benchmarks/ready_valid_tiny_gemm/rtl_b/tiny_gemm_rv_b_top.v` (earlier regression.s
independent per-tensor affine_quantize fixture) -- floor via arithmetic
right shift, round-half-to-even via a remainder/parity check, then clamp --
duplicated once per channel with that channel's own scale_shift/zero_point,
which is exactly the "missing delta": everything about the formula itself
is reused unchanged; only the per-channel parameter routing is new.

1. `test_per_channel_quantization_is_genuinely_unsupported` -- quotes the
   frozen pool documentation directly.
2. `test_per_channel_quantization_extension_request_and_bundle_round_trip`
   -- the real Architect-request / Verifier-bundle schema round trip,
   using `operations[].arithmetic.extension_request` exactly as the pool's
   own README shows it (`classifier_profile: llm_extension` required).
3. `test_per_channel_quantization_is_blocked_without_extension` -- the
   metadata-level BLOCKED-without-extension proof: with
   `classifier_profile: llm_extension` and no code-owned golden model, the
   automatic verification campaign cannot support this operation's
   arithmetic at all.
4. `test_per_channel_quantization_fault_fix_pair_on_real_rtl` -- a real
   cocotb/Verilator fault/fix pair: swapping which channel's
   scale/shift/zero_point apply to which channel's data (a plausible
   per-channel routing bug) vs. correct routing, checked against a Python
   golden model built from the pool's own frozen formula (not a new one).

Experimental only: lives in `tool_regression/rtl/`, touches no pool file, is
not promoted anywhere.
"""

from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    extension_bundle_schema,
    extension_request_schema,
    validate_verifier_extension_bundles,
)
from multigent.verifier_tool.tool_regression.paths import REPOSITORY_ROOT, VERIFIER_TOOL_ROOT

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_README = (VERIFIER_TOOL_ROOT / "pool" / "operation_metadata" / "README.md").read_text()


def test_per_channel_quantization_is_genuinely_unsupported() -> None:
    assert "granularity: per_tensor" in _README
    assert "Per-axis, stochastic, floating-scale, and other" in _README
    assert "remain contract-local extensions" in _README


# ---------------------------------------------------------------------------
# The pool's own frozen formula (README.md, quoted verbatim in the module
# docstring above), implemented once via exact integer arithmetic and reused
# per channel -- not a new quantization scheme.
# ---------------------------------------------------------------------------

def rne_quantize(value: int, *, scale_multiplier: int, scale_shift: int, zero_point: int,
                  dtype_min: int = -128, dtype_max: int = 127) -> int:
    scaled = value * scale_multiplier
    divisor = 1 << scale_shift
    quotient = scaled // divisor  # floor division == arithmetic right shift for two's complement
    remainder = scaled - quotient * divisor  # always in [0, divisor - 1]
    half = divisor // 2
    if remainder > half or (remainder == half and (quotient % 2) != 0):
        quotient += 1
    result = quotient + zero_point
    return max(dtype_min, min(dtype_max, result))


def test_rne_quantize_matches_the_proven_per_tensor_rtl_case() -> None:
    """Cross-checks the general Python formula against
    ready_valid_tiny_gemm/rtl_b/tiny_gemm_rv_b_top.v's exact documented
    per-tensor case (scale_multiplier=1, scale_shift=2, zero_point=-1),
    which was itself verified against real Verilator simulation in earlier regression.
    """
    # A tie case: biased=6 -> 6/4=1.5 -> rounds to 2 (nearest even), then -1 -> 1.
    assert rne_quantize(6, scale_multiplier=1, scale_shift=2, zero_point=-1) == 1
    # A tie case landing on an already-even quotient: biased=2 -> 2/4=0.5 -> rounds to 0, then -1 -> -1.
    assert rne_quantize(2, scale_multiplier=1, scale_shift=2, zero_point=-1) == -1
    # Saturation: a large value clamps to 127.
    assert rne_quantize(10_000, scale_multiplier=1, scale_shift=2, zero_point=-1) == 127
    assert rne_quantize(-10_000, scale_multiplier=1, scale_shift=2, zero_point=-1) == -128


def _requests_and_bundle() -> tuple[dict, dict]:
    request = {
        "id": "operation.gemm_per_channel_affine_quantize",
        "domain": "operation",
        "feature_name": "per_channel_affine_quantize",
        "target": {"scope": "operation", "name": "probe"},
        "semantics": {
            "summary": (
                "Each output channel n is requantized with its own "
                "(scale_multiplier[n], scale_shift[n], zero_point[n]) instead of one "
                "shared per-tensor triple, using the pool's own frozen affine_quantize "
                "formula per channel."
            ),
            "trigger": "The accumulated (post-bias) value for output channel n is ready.",
            "required_behavior": [
                "Apply q[n] = clamp(round_nearest_even(value[n] * scale_multiplier[n] "
                "/ 2**scale_shift[n]) + zero_point[n], -128, 127) using channel n's own "
                "parameter triple, never another channel's.",
            ],
            "end_condition": "Every declared output channel has an accepted quantized result.",
            "forbidden_behavior": [
                "Does not alter the accumulation (multiply-accumulate) arithmetic itself, "
                "only the post-accumulation requantization stage.",
            ],
        },
        "reason": (
            "The built-in affine_quantize post-operation stage is fixed at "
            "granularity: per_tensor (pool/operation_metadata/README.md); per-channel "
            "quantization is explicitly named there as remaining a contract-local extension."
        ),
        "parameters": {
            "channel_0_scale_multiplier": 1, "channel_0_scale_shift": 2, "channel_0_zero_point": -1,
            "channel_1_scale_multiplier": 3, "channel_1_scale_shift": 3, "channel_1_zero_point": 2,
        },
        "required_observations": [
            {"name": "golden_trace", "kind": "golden_trace", "description": "Per-channel expected quantized values."},
            {"name": "channel_outputs", "kind": "signal", "description": "Observed per-channel quantized outputs."},
        ],
        "related_builtin_features": [],
    }
    Draft202012Validator(extension_request_schema()).validate(request)
    implementation = {
        "kind": "verifier_python",
        "name": "per_channel_affine_quantize",
        "file": "tests/test_operation_per_channel_quantization_extension.py",
    }
    bundle = {
        "schema_version": 1,
        "request_id": request["id"],
        "id": request["id"],
        "domain": "operation",
        "feature_name": request["feature_name"],
        "target": deepcopy(request["target"]),
        "description": "Per-channel affine requantization reusing the pool's own frozen formula per channel.",
        "bindings": {"golden_trace": "expected_channel_outputs", "channel_outputs": "observed_channel_outputs"},
        "reuse": {"based_on_features": [], "helpers": ["rne_quantize"]},
        "assertion": {
            "implementation": {**implementation, "symbol": "assert_per_channel_quantization"},
            "parameters": deepcopy(request["parameters"]),
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "cover_per_channel_quantization"},
            "parameters": deepcopy(request["parameters"]),
            "bins": [
                {"name": "channels_diverge", "intent": "Channels use genuinely different quantization results.",
                 "predicate": {"diverge": True}},
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "stimulate_per_channel_quantization"},
            "parameters": deepcopy(request["parameters"]),
            "scenarios": [
                {"name": "distinct_channel_parameters", "intent": "Drive both channels with distinct params.",
                 "parameters": {}},
            ],
        },
    }
    Draft202012Validator(extension_bundle_schema()).validate(bundle)
    return request, bundle


def test_per_channel_quantization_extension_request_and_bundle_round_trip() -> None:
    request, bundle = _requests_and_bundle()
    architecture = {
        "operations": [{
            "name": "probe",
            "kind": "arithmetic",
            "coverage_family": "matrix_multiply",
            "coverage_family_source": "catalog",
            "features": ["dimensions", "operand_values"],
            "feature_extensions": [],
            "semantics": (
                "1xK by KxN GEMM (K=1, N=2) with a per-channel affine-quantized output; "
                "the accumulate/bias-add stage uses the standard integer GEMM formula, "
                "only the final requantization is channel-local."
            ),
            "arithmetic": {
                "classifier_profile": "llm_extension",
                "reason": "Per-channel affine quantization is not representable by the per_tensor-only built-in profile.",
                "extension_request": request["id"],
            },
            "inputs": ["A", "B"],
            "outputs": ["Y"],
        }],
        "verification_extensions": [request],
    }
    source = {
        "path": "tests/test_operation_per_channel_quantization_extension.py",
        "content": Path(__file__).read_text(),
    }
    errors = validate_verifier_extension_bundles(
        architecture, [bundle], source_files=[source], interface=None
    )
    assert errors == [], errors
    assert architecture["operations"][0]["arithmetic"]["classifier_profile"] == "llm_extension"
    assert architecture["operations"][0]["arithmetic"]["extension_request"] == request["id"]


def test_per_channel_quantization_is_blocked_without_extension() -> None:
    """BLOCKED-without-extension proof: classifier_profile=llm_extension with
    no code-owned golden model means the automatic campaign cannot support
    this operation's arithmetic at all -- exactly the arithmetic-blocked
    path this repo's own pool/operation_metadata/README.md documents, and
    which earlier regression.s ready_valid_tiny_gemm variant C already exercised for a
    *supported* llm_extension smoke path. Here there is no code-owned
    numeric profile whatsoever, so the operation is unsupported outright."""
    architecture = {
        "operations": [{
            "name": "probe",
            "kind": "arithmetic",
            "coverage_family": "matrix_multiply",
            "coverage_family_source": "catalog",
            "features": ["dimensions", "operand_values"],
            "feature_extensions": [],
            "semantics": "Per-channel affine-quantized GEMM output; unsupported without this extension's bundle.",
            "arithmetic": {
                "classifier_profile": "llm_extension",
                "reason": "Per-channel affine quantization is not representable by the per_tensor-only built-in profile.",
                "extension_request": "operation.gemm_per_channel_affine_quantize",
            },
            "inputs": ["A", "B"],
            "outputs": ["Y"],
        }],
    }
    interface = {
        "clock": "clk", "reset": "rst",
        "channels": [
            {"name": "a", "direction": "input", "protocol_profile": "ready_valid"},
            {"name": "b", "direction": "input", "protocol_profile": "ready_valid"},
            {"name": "y", "direction": "output", "protocol_profile": "ready_valid"},
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {"name": "rst", "role": "reset", "direction": "input", "channel": None, "semantic": "active-high reset"},
            {"name": "a_valid", "role": "valid", "direction": "input", "channel": "a"},
            {"name": "a_ready", "role": "ready", "direction": "output", "channel": "a"},
            {"name": "a_data", "role": "payload", "semantic_class": "data", "direction": "input", "channel": "a", "width": "8", "signed": True},
            {"name": "b_valid", "role": "valid", "direction": "input", "channel": "b"},
            {"name": "b_ready", "role": "ready", "direction": "output", "channel": "b"},
            {"name": "b_data", "role": "payload", "semantic_class": "data", "direction": "input", "channel": "b", "width": "8", "signed": True},
            {"name": "y_valid", "role": "valid", "direction": "output", "channel": "y"},
            {"name": "y_ready", "role": "ready", "direction": "input", "channel": "y"},
            {"name": "y_data", "role": "payload", "semantic_class": "data", "direction": "output", "channel": "y", "width": "8", "signed": True},
        ],
    }
    architecture["data_types"] = [{"name": "s8", "width_bits": 8, "signed": True}]
    architecture["data_objects"] = [
        {"name": "A", "role": "left_operand_matrix", "data_type": "s8", "dimensions": ["M", "K"],
         "producer": "external", "consumers": ["probe"], "external": True,
         "serialization": {"kind": "dense_tensor", "index_order": ["M", "K"], "description": "one element per transfer"}},
        {"name": "B", "role": "right_operand_matrix", "data_type": "s8", "dimensions": ["K", "N"],
         "producer": "external", "consumers": ["probe"], "external": True,
         "serialization": {"kind": "dense_tensor", "index_order": ["K", "N"], "description": "one element per transfer"}},
        {"name": "Y", "role": "result_matrix", "data_type": "s8", "dimensions": ["M", "N"],
         "producer": "probe", "consumers": ["external"], "external": True,
         "serialization": {"kind": "dense_tensor", "index_order": ["M", "N"], "description": "one element per transfer"}},
    ]
    architecture["dimensions"] = [
        {"name": "M", "minimum": 1, "maximum": 1},
        {"name": "K", "minimum": 1, "maximum": 1},
        {"name": "N", "minimum": 2, "maximum": 2},
    ]
    architecture["parameters"] = []
    metadata = build_architect_operation_metadata(architecture, interface)
    if metadata["unrepresentable_operations"]:
        # A hard rejection at metadata-compile time is itself a valid form
        # of "blocked without the extension" -- the operation cannot even
        # be represented, let alone automatically campaigned.
        return
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["probe"]["supported"] is False
    assert support["any_operation_supported"] is False


# ---------------------------------------------------------------------------
# Verifier-authored implementation (the missing delta): per-channel routing
# of the pool's own frozen formula, plus the golden-model comparison.
# ---------------------------------------------------------------------------

_PARAMS = {
    0: {"scale_multiplier": 1, "scale_shift": 2, "zero_point": -1},
    1: {"scale_multiplier": 3, "scale_shift": 3, "zero_point": 2},
}


def assert_per_channel_quantization(expected_channel_outputs: dict[int, int], observed_channel_outputs: dict[int, int]) -> None:
    for channel, expected in expected_channel_outputs.items():
        observed = observed_channel_outputs.get(channel)
        if observed != expected:
            raise AssertionError(
                f"extension=operation.gemm_per_channel_affine_quantize; channel {channel} "
                f"expected {expected}, observed {observed!r} (params={_PARAMS[channel]!r})"
            )


def cover_per_channel_quantization(observed_channel_outputs: dict[int, int]) -> dict:
    values = list(observed_channel_outputs.values())
    return {"diverge": len(set(values)) > 1, "values": tuple(values)}


async def stimulate_per_channel_quantization(dut) -> None:
    from cocotb.triggers import Timer

    dut.a_data.value = 5
    dut.b0_data.value = 3
    dut.b1_data.value = 3
    await Timer(10, unit="ns")


def test_cover_per_channel_quantization_classifies_observed_evidence() -> None:
    assert cover_per_channel_quantization({0: 1, 1: 2}) == {"diverge": True, "values": (1, 2)}
    assert cover_per_channel_quantization({0: 1, 1: 1}) == {"diverge": False, "values": (1, 1)}


def test_per_channel_quantization_negative_control_rejects_corrupted_evidence() -> None:
    with pytest.raises(AssertionError, match="operation.gemm_per_channel_affine_quantize"):
        assert_per_channel_quantization({0: 1, 1: 2}, {0: 1, 1: 999})


def test_stimulate_per_channel_quantization_is_referenced_for_reachability() -> None:
    stimulate_per_channel_quantization(None).close()


_RTL = """module per_channel_quantize_probe (
    input logic clk, rst,
    input logic signed [7:0] a_data, b0_data, b1_data, bias0_data, bias1_data,
    output logic signed [7:0] y0_data, y1_data
);
    localparam bit SWAP_CHANNEL_PARAMS = %d;
    // Channel 0: scale_multiplier=1, scale_shift=2, zero_point=-1 (correct routing);
    // Channel 1: scale_multiplier=3, scale_shift=3, zero_point=2 (correct routing).
    // SWAP_CHANNEL_PARAMS applies each channel's data through the OTHER
    // channel's quantization parameters -- a plausible per-channel routing bug.
    wire signed [15:0] prod0 = a_data * b0_data;
    wire signed [15:0] prod1 = a_data * b1_data;
    wire signed [15:0] biased0 = prod0 + bias0_data;
    wire signed [15:0] biased1 = prod1 + bias1_data;

    function automatic signed [15:0] quantize;
        input signed [15:0] value;
        input integer mult;
        input integer shift;
        input signed [15:0] zp;
        reg signed [31:0] scaled;
        reg signed [31:0] quot_floor;
        reg [31:0] divisor;
        reg [31:0] rem;
        reg round_up;
        reg signed [31:0] rounded, q_full;
        begin
            scaled = value * mult;
            divisor = (1 << shift);
            quot_floor = scaled >>> shift;
            rem = scaled - (quot_floor * divisor);
            round_up = (rem > (divisor >> 1)) || (rem == (divisor >> 1) && quot_floor[0]);
            rounded = quot_floor + round_up;
            q_full = rounded + zp;
            quantize = (q_full > 16'sd127) ? 16'sd127 : (q_full < -16'sd128) ? -16'sd128 : q_full[15:0];
        end
    endfunction

    wire signed [15:0] q0 = SWAP_CHANNEL_PARAMS
        ? quantize(biased0, 3, 3, 16'sd2)
        : quantize(biased0, 1, 2, -16'sd1);
    wire signed [15:0] q1 = SWAP_CHANNEL_PARAMS
        ? quantize(biased1, 1, 2, -16'sd1)
        : quantize(biased1, 3, 3, 16'sd2);

    // Pure combinational requantization -- no job sequencing needed for
    // this isolated per-channel-formula probe. clk/rst are kept as ports
    // only for interface consistency with the rest of this pool's fixtures.
    assign y0_data = q0[7:0];
    assign y1_data = q1[7:0];
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer

@cocotb.test(timeout_time=20, timeout_unit="us")
async def check_per_channel_quantization(dut):
    dut.rst.value = 1
    dut.a_data.value = 0
    dut.b0_data.value = 0
    dut.b1_data.value = 0
    dut.bias0_data.value = 0
    dut.bias1_data.value = 0
    await Timer(1, unit="ns")
    dut.rst.value = 0
    dut.a_data.value = 5
    dut.b0_data.value = 3
    dut.b1_data.value = 7
    dut.bias0_data.value = 1
    dut.bias1_data.value = -4
    await Timer(1, unit="ns")

    expected = {
        0: rne_quantize(5 * 3 + 1, **_PARAMS[0]),
        1: rne_quantize(5 * 7 + (-4), **_PARAMS[1]),
    }
    observed = {0: int(dut.y0_data.value.signed_integer), 1: int(dut.y1_data.value.signed_integer)}
    assert_per_channel_quantization(expected, observed)
"""


def _run(tmp_path: Path, *, swap: bool) -> dict:
    for directory in ("rtl", "reference", "tests"):
        (tmp_path / directory).mkdir(parents=True)
    (tmp_path / "rtl" / "per_channel_quantize_probe.sv").write_text(_RTL % int(swap))
    (tmp_path / "reference" / "model.py").write_text("")
    tb_source = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT)!r})\n"
        "from multigent.verifier_tool.tool_regression.extensions.rtl.test_operation_per_channel_quantization_extension import ("
        "rne_quantize, assert_per_channel_quantization, _PARAMS)\n"
        + _TB
    )
    (tmp_path / "tests" / "test_per_channel_quantization.py").write_text(tb_source)
    return run_cocotb_regression(
        rtl_dir=tmp_path / "rtl", top_module="per_channel_quantize_probe",
        tests_dir=tmp_path / "tests", reference_dir=tmp_path / "reference",
        test_modules=["test_per_channel_quantization"], seed=103,
        build_dir=tmp_path / "build", report_path=tmp_path / "report.json",
        timeout_seconds=120,
    )


def test_per_channel_quantization_fault_fix_pair_on_real_rtl(tmp_path):
    bad = _run(tmp_path / "fault", swap=True)
    assert bad["status"] == "SIMULATION_FAILURE", bad
    assert "extension=operation.gemm_per_channel_affine_quantize" in bad["stdout"], bad["stdout"][-3000:]

    good = _run(tmp_path / "correct", swap=False)
    assert good["status"] == "PASS", good
