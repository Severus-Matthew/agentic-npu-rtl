import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, with_timeout, SimTimeoutError

from reference.gemm_bias_relu_ref import (
    gemm_bias_relu_ref,
    pack_cmd,
    to_s8,
    to_s32,
    INT8_MIN,
    INT8_MAX,
    INT32_MIN,
    INT32_MAX,
)

SEED = 20260904


async def reset_dut(dut, cycles=3):
    dut.cmd_valid.value = 0
    dut.a_valid.value = 0
    dut.b_valid.value = 0
    dut.bias_valid.value = 0
    dut.out_ready.value = 0
    dut.cmd_data.value = 0
    dut.a_data.value = 0
    dut.b_data.value = 0
    dut.bias_data.value = 0

    dut.rst_n.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def source_send_beats(dut, valid_sig, ready_sig, data_sig, beats, rng, pre_idle_max=3):
    for beat in beats:
        idle = rng.randint(0, pre_idle_max)
        for _ in range(idle):
            valid_sig.value = 0
            await RisingEdge(dut.clk)
        data_sig.value = beat & ((1 << len(data_sig)) - 1)
        valid_sig.value = 1
        while True:
            await RisingEdge(dut.clk)
            if int(ready_sig.value) == 1:
                break
        valid_sig.value = 0


async def sink_capture_beats(dut, valid_sig, ready_sig, data_sig, expected_count, rng, backpressure=True, max_cycles=200000):
    got = []
    cycles = 0
    while len(got) < expected_count:
        if backpressure:
            ready_sig.value = rng.randint(0, 1)
        else:
            ready_sig.value = 1
        await RisingEdge(dut.clk)
        cycles += 1
        if int(valid_sig.value) and int(ready_sig.value):
            got.append(to_s32(int(data_sig.value)))
        if cycles > max_cycles:
            raise SimTimeoutError(f"sink timeout expected_count={expected_count} got={len(got)}")
    ready_sig.value = 0
    return got


async def wait_done_pulse(dut, max_cycles=200000):
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if int(dut.status_done.value) == 1:
            return
    raise SimTimeoutError("status_done pulse timeout")


async def run_job(dut, M, N, K, bias_enable, A, B, bias, rng, input_throttle=True, out_backpressure=True):
    assert int(dut.status_error.value) == 0, "status_error set before legal job"
    cmd = pack_cmd(M, N, K, bias_enable)

    cmd_idle_rng = rng if input_throttle else random.Random(0)
    data_rng = rng if input_throttle else random.Random(0)

    async def send_cmd():
        await source_send_beats(dut, dut.cmd_valid, dut.cmd_ready, dut.cmd_data, [cmd], cmd_idle_rng)

    async def send_a():
        await source_send_beats(dut, dut.a_valid, dut.a_ready, dut.a_data, [(x & 0xFF) for x in A], data_rng)

    async def send_b():
        await source_send_beats(dut, dut.b_valid, dut.b_ready, dut.b_data, [(x & 0xFF) for x in B], data_rng)

    async def send_bias():
        if bias_enable:
            await source_send_beats(dut, dut.bias_valid, dut.bias_ready, dut.bias_data, [(x & 0xFFFFFFFF) for x in bias], data_rng)

    exp = gemm_bias_relu_ref(M, N, K, A, B, bias, bias_enable)

    tasks = [
        cocotb.start_soon(send_cmd()),
        cocotb.start_soon(send_a()),
        cocotb.start_soon(send_b()),
    ]
    if bias_enable:
        tasks.append(cocotb.start_soon(send_bias()))

    cap_task = cocotb.start_soon(
        sink_capture_beats(dut, dut.out_valid, dut.out_ready, dut.out_data, M * N, rng, backpressure=out_backpressure)
    )

    for t in tasks:
        await with_timeout(t, 50, "ms")
    got = await with_timeout(cap_task, 200, "ms")
    await with_timeout(wait_done_pulse(dut), 50, "ms")

    assert got == exp, f"output mismatch M={M} N={N} K={K} bias_enable={bias_enable} exp={exp} got={got}"
    assert int(dut.status_error.value) == 0, "status_error unexpectedly set after legal job"


@cocotb.test()
async def test_directed_basic_bias_relu(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    rng = random.Random(SEED + 1)
    await reset_dut(dut)

    M, N, K = 2, 3, 2
    A = [1, -2, 3, 4]
    B = [5, -6, 7, -8, 9, -10]
    bias = [100, -100, 1]
    await run_job(dut, M, N, K, 1, A, B, bias, rng, input_throttle=False, out_backpressure=False)


@cocotb.test()
async def test_partial_tile_and_no_bias(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    rng = random.Random(SEED + 2)
    await reset_dut(dut)

    M, N, K = 3, 10, 4
    A = [to_s8((i * 7) % 256) for i in range(M * K)]
    B = [to_s8((i * 11 + 3) % 256) for i in range(K * N)]
    bias = []
    await run_job(dut, M, N, K, 0, A, B, bias, rng, input_throttle=True, out_backpressure=True)


@cocotb.test()
async def test_reset_idle_and_mid_output(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    rng = random.Random(SEED + 3)
    await reset_dut(dut)

    assert int(dut.status_error.value) == 0

    M, N, K = 4, 8, 8
    A = [rng.randint(INT8_MIN, INT8_MAX) for _ in range(M * K)]
    B = [rng.randint(INT8_MIN, INT8_MAX) for _ in range(K * N)]
    bias = [rng.randint(INT32_MIN, INT32_MAX) for _ in range(N)]

    job_task = cocotb.start_soon(run_job(dut, M, N, K, 1, A, B, bias, rng, input_throttle=True, out_backpressure=True))
    for _ in range(60):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    try:
        await with_timeout(job_task, 2, "ms")
    except SimTimeoutError:
        pass

    A2 = [1]
    B2 = [2]
    bias2 = [3]
    await run_job(dut, 1, 1, 1, 1, A2, B2, bias2, rng, input_throttle=False, out_backpressure=False)


@cocotb.test()
async def test_illegal_command_sets_sticky_error(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    rng = random.Random(SEED + 4)
    await reset_dut(dut)

    bad_cmd = pack_cmd(0, 1, 1, 0)
    await source_send_beats(dut, dut.cmd_valid, dut.cmd_ready, dut.cmd_data, [bad_cmd], rng)

    seen_error = False
    for _ in range(50):
        await RisingEdge(dut.clk)
        if int(dut.status_error.value) == 1:
            seen_error = True
    assert seen_error, "status_error did not assert for illegal command"

    for _ in range(20):
        await RisingEdge(dut.clk)
        assert int(dut.status_error.value) == 1, "status_error not sticky"

    await reset_dut(dut)
    assert int(dut.status_error.value) == 0, "status_error not cleared by reset"


@cocotb.test()
async def test_randomized_regression_100_jobs(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    rng = random.Random(SEED + 5)
    await reset_dut(dut)

    jobs = 100
    for j in range(jobs):
        M = rng.choice([1, 2, 3, 7, 8, 16, 31, 64])
        N = rng.choice([1, 2, 5, 8, 9, 15, 32, 64])
        K = rng.choice([1, 2, 4, 7, 16, 33, 64])
        bias_enable = rng.randint(0, 1)

        A = [rng.randint(INT8_MIN, INT8_MAX) for _ in range(M * K)]
        B = [rng.randint(INT8_MIN, INT8_MAX) for _ in range(K * N)]
        bias = [rng.randint(INT32_MIN, INT32_MAX) for _ in range(N)] if bias_enable else []

        await run_job(dut, M, N, K, bias_enable, A, B, bias, rng, input_throttle=True, out_backpressure=True)
