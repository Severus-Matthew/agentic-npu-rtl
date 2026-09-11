import random
import cocotb
from cocotb.triggers import Timer, with_timeout, SimTimeoutError
from reference.gemm_ref import (
    gemm8x8x32_bias_relu,
    sanity_check_reference,
    to_s32,
    A_ELEMS,
    B_ELEMS,
    BIAS_ELEMS,
)

CYCLE_NS = 10
MAX_CYCLES_WAIT = 300000
BASE_SEED = 202611


def i32_from_signal(v):
    return to_s32(int(v))


async def cycle(dut):
    dut.clk.value = 0
    await Timer(CYCLE_NS / 2, units="ns")
    snap = {
        "a_ready": int(dut.a_ready.value),
        "b_ready": int(dut.b_ready.value),
        "bias_ready": int(dut.bias_ready.value),
        "y_valid": int(dut.y_valid.value),
        "y_data": i32_from_signal(dut.y_data.value),
        "done": int(dut.done.value),
        "error": int(dut.error.value),
        "a_valid": int(dut.a_valid.value),
        "b_valid": int(dut.b_valid.value),
        "bias_valid": int(dut.bias_valid.value),
        "y_ready": int(dut.y_ready.value),
    }
    snap["a_xfer"] = snap["a_valid"] and snap["a_ready"]
    snap["b_xfer"] = snap["b_valid"] and snap["b_ready"]
    snap["bias_xfer"] = snap["bias_valid"] and snap["bias_ready"]
    snap["y_xfer"] = snap["y_valid"] and snap["y_ready"]
    dut.clk.value = 1
    await Timer(CYCLE_NS / 2, units="ns")
    dut.clk.value = 0
    return snap


async def apply_reset(dut, cycles=2):
    dut.a_valid.value = 0
    dut.b_valid.value = 0
    dut.bias_valid.value = 0
    dut.y_ready.value = 0
    dut.a_data.value = 0
    dut.b_data.value = 0
    dut.bias_data.value = 0
    dut.rst.value = 1
    for _ in range(cycles):
        s = await cycle(dut)
        assert s["done"] == 0
        assert s["error"] == 0
        assert s["y_valid"] == 0
    dut.rst.value = 0
    for _ in range(2):
        s = await cycle(dut)
        assert s["done"] == 0
        assert s["error"] == 0


async def send_stream(dut, v_name, r_name, d_name, data, rng, idle_prob=0.2):
    idx = 0
    while idx < len(data):
        while rng.random() < idle_prob:
            getattr(dut, v_name).value = 0
            await cycle(dut)
        getattr(dut, d_name).value = int(data[idx])
        getattr(dut, v_name).value = 1
        while True:
            s = await cycle(dut)
            if s[r_name] == 1:
                idx += 1
                break
        getattr(dut, v_name).value = 0


async def recv_y(dut, expected, rng, backpressure=True):
    got = []
    stall_tracking = False
    stalled_data = 0
    done_pulse_seen = False

    for cyc in range(MAX_CYCLES_WAIT):
        dut.y_ready.value = 1 if (not backpressure or rng.random() > 0.3) else 0
        s = await cycle(dut)

        if stall_tracking:
            assert s["y_valid"] == 1, f"y_valid dropped under stall cycle={cyc}"
            assert s["y_data"] == stalled_data, f"y_data changed under stall cycle={cyc}"

        if s["y_valid"] and not s["y_ready"]:
            stall_tracking = True
            stalled_data = s["y_data"]
        else:
            stall_tracking = False

        if s["y_xfer"]:
            got.append(s["y_data"])
            if len(got) == len(expected):
                s2 = await cycle(dut)
                assert s2["done"] == 1, "done not high after final accepted y transfer"
                done_pulse_seen = True
                s3 = await cycle(dut)
                assert s3["done"] == 0, "done must be single-cycle pulse"
                break

    assert len(got) == len(expected), f"y count mismatch exp={len(expected)} got={len(got)}"
    assert done_pulse_seen, "done pulse not observed"
    for i, (e, g) in enumerate(zip(expected, got)):
        assert e == g, f"y mismatch idx={i} exp={e} got={g}"


async def run_job(dut, a, b, bias, rng, in_idle_prob=0.2, out_backpressure=True):
    exp = gemm8x8x32_bias_relu(a, b, bias)
    await send_stream(dut, "a_valid", "a_ready", "a_data", a, rng, idle_prob=in_idle_prob)
    await send_stream(dut, "b_valid", "b_ready", "b_data", b, rng, idle_prob=in_idle_prob)
    await send_stream(dut, "bias_valid", "bias_ready", "bias_data", bias, rng, idle_prob=in_idle_prob)
    await recv_y(dut, exp, rng, backpressure=out_backpressure)


@cocotb.test()
async def test_directed_boundaries(dut):
    sanity_check_reference()
    await apply_reset(dut)
    rng = random.Random(BASE_SEED + 1)
    cases = [
        ([0] * A_ELEMS, [0] * B_ELEMS, [0] * BIAS_ELEMS),
        ([127] * A_ELEMS, [127] * B_ELEMS, [0] * BIAS_ELEMS),
        ([-128] * A_ELEMS, [-128] * B_ELEMS, [0] * BIAS_ELEMS),
        ([(-128 if i % 2 == 0 else 127) for i in range(A_ELEMS)],
         [(127 if i % 3 else -128) for i in range(B_ELEMS)],
         [(-1 if i % 2 else 1) for i in range(BIAS_ELEMS)]),
        ([127] * A_ELEMS, [127] * B_ELEMS, [0x7FFFFFFF] * BIAS_ELEMS),
    ]
    for a, b, bias in cases:
        await run_job(dut, a, b, bias, rng, in_idle_prob=0.1, out_backpressure=True)


@cocotb.test()
async def test_randomized_100_jobs(dut):
    sanity_check_reference()
    await apply_reset(dut)
    rng = random.Random(BASE_SEED + 2)
    for j in range(100):
        a = [rng.randint(-128, 127) for _ in range(A_ELEMS)]
        b = [rng.randint(-128, 127) for _ in range(B_ELEMS)]
        bias = [rng.randint(-2147483648, 2147483647) for _ in range(BIAS_ELEMS)]
        try:
            await with_timeout(run_job(dut, a, b, bias, rng, in_idle_prob=0.25, out_backpressure=True), 20, "ms")
        except SimTimeoutError:
            raise AssertionError(f"timeout randomized job={j} seed={BASE_SEED + 2}")


@cocotb.test()
async def test_reset_during_activity(dut):
    await apply_reset(dut)
    rng = random.Random(BASE_SEED + 3)
    a = [rng.randint(-128, 127) for _ in range(A_ELEMS)]
    dut.a_data.value = int(a[0])
    dut.a_valid.value = 1
    for _ in range(10):
        await cycle(dut)
    dut.rst.value = 1
    for _ in range(2):
        s = await cycle(dut)
        assert s["done"] == 0
        assert s["error"] == 0
        assert s["y_valid"] == 0
    dut.a_valid.value = 0
    dut.rst.value = 0
    for _ in range(3):
        s = await cycle(dut)
        assert s["done"] == 0
        assert s["error"] == 0


@cocotb.test()
async def test_error_sticky_wrong_section_until_reset(dut):
    await apply_reset(dut)
    dut.b_valid.value = 1
    dut.b_data.value = 5
    tripped = False
    for _ in range(50):
        s = await cycle(dut)
        if s["error"] == 1:
            tripped = True
            break
    assert tripped, "error did not assert on wrong-section valid traffic"
    dut.b_valid.value = 0
    for _ in range(10):
        s = await cycle(dut)
        assert s["error"] == 1
    dut.rst.value = 1
    for _ in range(2):
        await cycle(dut)
    dut.rst.value = 0
    for _ in range(2):
        s = await cycle(dut)
        assert s["error"] == 0


@cocotb.test()
async def test_done_only_after_final_transfer_with_backpressure(dut):
    await apply_reset(dut)
    rng = random.Random(BASE_SEED + 4)
    a = [1] * A_ELEMS
    b = [1] * B_ELEMS
    bias = [0] * BIAS_ELEMS
    await run_job(dut, a, b, bias, rng, in_idle_prob=0.0, out_backpressure=True)
