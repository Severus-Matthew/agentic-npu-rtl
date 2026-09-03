import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.result import SimTimeoutError
from cocotb.triggers import with_timeout

from reference.gemm_ref import gemm_bias_relu_ref, pack_cmd, s8, s32

SEED = 12345
MAX_DIM = 64


async def reset_dut(dut, cycles=3):
    dut.cmd_valid.value = 0
    dut.a_valid.value = 0
    dut.b_valid.value = 0
    dut.bias_valid.value = 0
    dut.out_ready.value = 0
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def send_stream(dut, valid_sig, ready_sig, data_sig, values, rng, stall_prob=0.0):
    valid_sig.value = 0
    await RisingEdge(dut.clk)
    for v in values:
        data_sig.value = int(v) & ((1 << len(data_sig)) - 1)
        valid_sig.value = 1
        while True:
            if stall_prob > 0 and rng.random() < stall_prob:
                valid_sig.value = 0
            else:
                valid_sig.value = 1
            await RisingEdge(dut.clk)
            if int(valid_sig.value) == 1 and int(ready_sig.value) == 1:
                break
    valid_sig.value = 0


async def recv_stream(dut, count, rng, backpressure_prob=0.0):
    out = []
    while len(out) < count:
        dut.out_ready.value = 0 if (backpressure_prob > 0 and rng.random() < backpressure_prob) else 1
        await RisingEdge(dut.clk)
        if int(dut.out_valid.value) == 1 and int(dut.out_ready.value) == 1:
            out.append(s32(int(dut.out_data.value)))
    dut.out_ready.value = 0
    return out


async def run_job(dut, M, N, K, bias_enable, A, B, bias, rng, in_stall=0.0, out_bp=0.0):
    dut.cmd_data.value = pack_cmd(M, N, K, bias_enable)
    dut.cmd_valid.value = 1
    while True:
        await RisingEdge(dut.clk)
        if int(dut.cmd_ready.value) == 1:
            break
    dut.cmd_valid.value = 0

    expected = gemm_bias_relu_ref(M, N, K, A, B, bias_enable, bias)

    await cocotb.start(send_stream(dut, dut.a_valid, dut.a_ready, dut.a_data, A, rng, in_stall))
    await cocotb.start(send_stream(dut, dut.b_valid, dut.b_ready, dut.b_data, B, rng, in_stall))
    if bias_enable:
        await cocotb.start(send_stream(dut, dut.bias_valid, dut.bias_ready, dut.bias_data, bias, rng, in_stall))

    got = await recv_stream(dut, M * N, rng, out_bp)
    assert got == expected, f"Mismatch M={M} N={N} K={K} bias={bias_enable} exp={expected[:8]} got={got[:8]}"


@cocotb.test()
async def smoke_minimal(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    rng = random.Random(SEED)
    await reset_dut(dut)
    M, N, K = 1, 1, 1
    A = [1]
    B = [-2]
    bias = [3]
    await with_timeout(run_job(dut, M, N, K, True, A, B, bias, rng), 2, 'ms')


@cocotb.test()
async def directed_partial_tile_and_no_bias(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    rng = random.Random(SEED + 1)
    await reset_dut(dut)
    M, N, K = 2, 10, 3
    A = [s8((i * 7) - 9) for i in range(M * K)]
    B = [s8((i * 5) - 11) for i in range(K * N)]
    bias = [123 for _ in range(N)]
    await with_timeout(run_job(dut, M, N, K, False, A, B, bias, rng), 5, 'ms')


@cocotb.test()
async def reset_idle_and_mid_output(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    rng = random.Random(SEED + 2)
    await reset_dut(dut)
    await reset_dut(dut)

    M, N, K = 4, 9, 8
    A = [rng.randint(-128, 127) for _ in range(M * K)]
    B = [rng.randint(-128, 127) for _ in range(K * N)]
    bias = [rng.randint(-2**31, 2**31 - 1) for _ in range(N)]

    dut.cmd_data.value = pack_cmd(M, N, K, True)
    dut.cmd_valid.value = 1
    while True:
        await RisingEdge(dut.clk)
        if int(dut.cmd_ready.value):
            break
    dut.cmd_valid.value = 0

    cocotb.start_soon(send_stream(dut, dut.a_valid, dut.a_ready, dut.a_data, A, rng, 0.2))
    cocotb.start_soon(send_stream(dut, dut.b_valid, dut.b_ready, dut.b_data, B, rng, 0.2))
    cocotb.start_soon(send_stream(dut, dut.bias_valid, dut.bias_ready, dut.bias_data, bias, rng, 0.2))

    seen = 0
    for _ in range(3000):
        dut.out_ready.value = 1
        await RisingEdge(dut.clk)
        if int(dut.out_valid.value) and int(dut.out_ready.value):
            seen += 1
            if seen >= 3:
                break
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    assert int(dut.status_error.value) == 0


@cocotb.test()
async def randomized_regression_100(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    rng = random.Random(SEED + 3)
    await reset_dut(dut)

    jobs = 100
    for j in range(jobs):
        if j < 6:
            M = [1, MAX_DIM, 1, MAX_DIM, 2, 3][j]
            N = [1, MAX_DIM, 10, MAX_DIM - 1, 8, 9][j]
            K = [1, MAX_DIM, 3, MAX_DIM, 2, 7][j]
        else:
            M = rng.randint(1, 8)
            N = rng.randint(1, 16)
            K = rng.randint(1, 16)
        bias_enable = bool(rng.getrandbits(1))
        A = [rng.randint(-128, 127) for _ in range(M * K)]
        B = [rng.randint(-128, 127) for _ in range(K * N)]
        bias = [rng.randint(-2**31, 2**31 - 1) for _ in range(N)]
        await with_timeout(run_job(dut, M, N, K, bias_enable, A, B, bias, rng, in_stall=0.3, out_bp=0.3), 20, 'ms')
