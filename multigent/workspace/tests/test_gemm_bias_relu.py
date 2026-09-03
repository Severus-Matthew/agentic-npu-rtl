import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.triggers import with_timeout, SimTimeoutError

from reference.gemm_ref import gemm_bias_relu_ref, pack_cmd, to_s8, to_s32

SEED = 12345
MAX_DIM_DEFAULT = 64
SIM_TIMEOUT_NS = 2_000_000


async def reset_dut(dut, cycles=3):
    dut.cmd_valid.value = 0
    dut.a_valid.value = 0
    dut.b_valid.value = 0
    dut.bias_valid.value = 0
    dut.out_ready.value = 0
    dut.rst_n.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def handshake_send(dut, valid_sig, ready_sig, data_sig, value):
    valid_sig.value = 1
    data_sig.value = value
    while True:
        await RisingEdge(dut.clk)
        if int(valid_sig.value) == 1 and int(ready_sig.value) == 1:
            break
    valid_sig.value = 0


async def drive_stream(dut, valid_sig, ready_sig, data_sig, payload, stall_prob=0.0, rng=None):
    for v in payload:
        valid_sig.value = 1
        data_sig.value = v
        while True:
            await RisingEdge(dut.clk)
            if rng is not None and stall_prob > 0.0:
                if rng.random() < stall_prob:
                    valid_sig.value = 0
                else:
                    valid_sig.value = 1
                    data_sig.value = v
            if int(valid_sig.value) == 1 and int(ready_sig.value) == 1:
                break
    valid_sig.value = 0


async def collect_outputs(dut, count, stall_prob=0.0, rng=None):
    out = []
    while len(out) < count:
        if rng is not None and stall_prob > 0.0:
            dut.out_ready.value = 0 if rng.random() < stall_prob else 1
        else:
            dut.out_ready.value = 1
        await RisingEdge(dut.clk)
        if int(dut.out_valid.value) and int(dut.out_ready.value):
            out.append(to_s32(int(dut.out_data.value)))
    dut.out_ready.value = 0
    return out


async def run_job(dut, M, N, K, bias_enable, A, B, Bias, in_stall=0.0, out_stall=0.0, rng=None):
    cmd = pack_cmd(M, N, K, 1 if bias_enable else 0)
    await handshake_send(dut, dut.cmd_valid, dut.cmd_ready, dut.cmd_data, cmd)

    ta = cocotb.start_soon(drive_stream(dut, dut.a_valid, dut.a_ready, dut.a_data, A, in_stall, rng))
    tb = cocotb.start_soon(drive_stream(dut, dut.b_valid, dut.b_ready, dut.b_data, B, in_stall, rng))
    if bias_enable:
        tbias = cocotb.start_soon(drive_stream(dut, dut.bias_valid, dut.bias_ready, dut.bias_data, Bias, in_stall, rng))
    else:
        tbias = None

    expected = gemm_bias_relu_ref(M, N, K, A, B, bias_enable, Bias)
    observed = await collect_outputs(dut, M * N, out_stall, rng)

    await ta
    await tb
    if tbias is not None:
        await tbias

    assert observed == expected, f"Mismatch M={M} N={N} K={K} bias={bias_enable}"


@cocotb.test()
async def test_directed_basic_and_partial_tile(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    M, N, K = 2, 10, 3
    A = [to_s8(x) for x in [1, -2, 3, -4, 5, -6]]
    B = [to_s8((i % 7) - 3) for i in range(K * N)]
    Bias = [to_s32((i - 5) * 11) for i in range(N)]

    await with_timeout(run_job(dut, M, N, K, True, A, B, Bias), SIM_TIMEOUT_NS, "ns")


@cocotb.test()
async def test_bias_disable_and_ignore_bias_channel(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    M, N, K = 3, 4, 5
    A = [to_s8((i * 3) - 20) for i in range(M * K)]
    B = [to_s8(40 - i) for i in range(K * N)]
    Bias = [to_s32(0x7FFFFFFF - i) for i in range(N)]

    await with_timeout(run_job(dut, M, N, K, False, A, B, Bias), SIM_TIMEOUT_NS, "ns")


@cocotb.test()
async def test_reset_idle_and_mid_output(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    assert int(dut.status_error.value) == 0
    await reset_dut(dut)

    M, N, K = 4, 8, 8
    A = [to_s8((i % 31) - 15) for i in range(M * K)]
    B = [to_s8((i % 29) - 14) for i in range(K * N)]
    Bias = [to_s32(i - 4) for i in range(N)]

    task = cocotb.start_soon(run_job(dut, M, N, K, True, A, B, Bias))
    for _ in range(80):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    assert int(dut.status_error.value) == 0
    task.kill()


@cocotb.test()
async def test_backpressure_all_channels(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(SEED + 1)
    M, N, K = 5, 9, 7
    A = [to_s8(rng.randint(-128, 127)) for _ in range(M * K)]
    B = [to_s8(rng.randint(-128, 127)) for _ in range(K * N)]
    Bias = [to_s32(rng.randint(-2**31, 2**31 - 1)) for _ in range(N)]

    await with_timeout(run_job(dut, M, N, K, True, A, B, Bias, in_stall=0.35, out_stall=0.35, rng=rng), SIM_TIMEOUT_NS, "ns")


@cocotb.test()
async def test_illegal_command_sets_sticky_error(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    bad_cmd = pack_cmd(0, 1, 1, 0)
    await handshake_send(dut, dut.cmd_valid, dut.cmd_ready, dut.cmd_data, bad_cmd)

    for _ in range(20):
        await RisingEdge(dut.clk)
    assert int(dut.status_error.value) == 1, "status_error must assert on illegal cmd"

    await reset_dut(dut)
    assert int(dut.status_error.value) == 0, "status_error must clear only by reset"


@cocotb.test()
async def test_randomized_100_jobs(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(SEED)
    jobs = 100
    for i in range(jobs):
        M = rng.choice([1, 2, 3, 7, 8, 16, 31, 64])
        N = rng.choice([1, 2, 5, 8, 9, 15, 32, 64])
        K = rng.choice([1, 2, 4, 7, 16, 33, 64])
        bias_enable = bool(rng.getrandbits(1))

        A = [to_s8(rng.randint(-128, 127)) for _ in range(M * K)]
        B = [to_s8(rng.randint(-128, 127)) for _ in range(K * N)]
        Bias = [to_s32(rng.randint(-2**31, 2**31 - 1)) for _ in range(N)]

        try:
            await with_timeout(
                run_job(dut, M, N, K, bias_enable, A, B, Bias, in_stall=0.15, out_stall=0.15, rng=rng),
                SIM_TIMEOUT_NS,
                "ns",
            )
        except SimTimeoutError:
            raise AssertionError(f"Timeout in randomized job {i} seed={SEED} dims=({M},{N},{K}) bias={bias_enable}")
