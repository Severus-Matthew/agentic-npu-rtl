from _npu_monitor import diagnostic
import random
import cocotb
from cocotb.triggers import Timer
from reference.gemm8x8x32_ref import M, N, K, sanity_checks, gemm_bias_relu_ref, flatten_row_major, to_s32
CLK_NS = 10
MAX_CYCLES_WAIT = 20000
SEED = 12345
CMD_TYPE = 0
A_TYPE = 1
B_TYPE = 2
BIAS_TYPE = 3
START_OPCODE = 1

def s32_to_u32(x: int) -> int:
    return x & 4294967295

async def cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=1):
    dut.clk.value = 0
    dut.s_valid.value = s_valid
    dut.s_type.value = s_type
    dut.s_data.value = s32_to_u32(s_data)
    dut.m_ready.value = m_ready
    await Timer(CLK_NS // 2, units='ns')
    in_hs = int(dut.s_valid.value) and int(dut.s_ready.value)
    out_hs = int(dut.m_valid.value) and int(dut.m_ready.value)
    out_data_pre = to_s32(int(dut.m_data.value)) if int(dut.m_valid.value) else None
    done_pre = int(dut.done.value)
    err_pre = int(dut.error.value)
    dut.clk.value = 1
    await Timer(CLK_NS // 2, units='ns')
    done_post = int(dut.done.value)
    err_post = int(dut.error.value)
    dut.clk.value = 0
    return {'in_hs': in_hs, 'out_hs': out_hs, 'out_data': out_data_pre, 'done_pre': done_pre, 'done_post': done_post, 'err_pre': err_pre, 'err_post': err_post, 'm_valid': int(dut.m_valid.value)}

async def apply_reset(dut, cycles=2):
    for _ in range(cycles):
        await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=0)
        dut.rst.value = 1
        await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=0)
    dut.rst.value = 0
    for _ in range(2):
        await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=0)

async def send_beat(dut, btype, bdata, rng):
    while True:
        if rng.randint(0, 3) == 0:
            await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=1)
        else:
            break
    while True:
        snap = await cycle(dut, s_valid=1, s_type=btype, s_data=bdata, m_ready=1)
        if snap['in_hs']:
            return

async def run_job(dut, A, B, bias, rng, backpressure=False):
    await send_beat(dut, CMD_TYPE, START_OPCODE, rng)
    for m in range(M):
        for k in range(K):
            await send_beat(dut, A_TYPE, A[m][k], rng)
    for k in range(K):
        for n in range(N):
            await send_beat(dut, B_TYPE, B[k][n], rng)
    for n in range(N):
        await send_beat(dut, BIAS_TYPE, bias[n], rng)
    expected = flatten_row_major(gemm_bias_relu_ref(A, B, bias))
    got = []
    done_count = 0
    stall_data = None
    for cyc in range(MAX_CYCLES_WAIT):
        mr = rng.randint(0, 1) if backpressure else 1
        snap = await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=mr)
        if snap['m_valid'] and (not mr):
            if stall_data is None:
                stall_data = snap['out_data']
            else:
                assert stall_data == snap['out_data'], f'm_data changed under stall at cycle {cyc}'
        else:
            stall_data = None
        if snap['out_hs']:
            got.append(snap['out_data'])
        if snap['done_pre'] or snap['done_post']:
            done_count += (1 if snap['done_pre'] else 0) + (1 if snap['done_post'] else 0)
        if len(got) == 64:
            break
    assert len(got) == 64, f'Expected 64 outputs, got {len(got)}'
    assert got == expected, 'Output mismatch'
    assert done_count >= 1, 'done never observed'

@cocotb.test()
@diagnostic
async def test_directed_basic(dut):
    sanity_checks()
    dut.rst.value = 0
    await apply_reset(dut)
    rng = random.Random(SEED)
    A = [[0 for _ in range(K)] for _ in range(M)]
    B = [[0 for _ in range(N)] for _ in range(K)]
    bias = [0 for _ in range(N)]
    A[0][0] = 1
    B[0][0] = 1
    await run_job(dut, A, B, bias, rng, backpressure=False)

@cocotb.test()
@diagnostic
async def test_randomized_100_jobs_with_backpressure(dut):
    sanity_checks()
    dut.rst.value = 0
    await apply_reset(dut)
    rng = random.Random(SEED)
    for j in range(100):
        A = [[rng.randint(-128, 127) for _ in range(K)] for _ in range(M)]
        B = [[rng.randint(-128, 127) for _ in range(N)] for _ in range(K)]
        bias = [rng.randint(-(1 << 31), (1 << 31) - 1) for _ in range(N)]
        await run_job(dut, A, B, bias, rng, backpressure=True)

@cocotb.test()
@diagnostic
async def test_reset_idle_and_midjob(dut):
    dut.rst.value = 0
    await apply_reset(dut)
    rng = random.Random(SEED + 1)
    await send_beat(dut, CMD_TYPE, START_OPCODE, rng)
    for _ in range(10):
        await send_beat(dut, A_TYPE, 1, rng)
    dut.rst.value = 1
    for _ in range(3):
        snap = await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=0)
        assert snap['m_valid'] == 0
        assert snap['done_pre'] == 0 and snap['done_post'] == 0
        assert snap['err_pre'] == 0 and snap['err_post'] == 0
    dut.rst.value = 0

@cocotb.test()
@diagnostic
async def test_protocol_error_sticky_and_recovery(dut):
    dut.rst.value = 0
    await apply_reset(dut)
    rng = random.Random(SEED + 2)
    await send_beat(dut, CMD_TYPE, START_OPCODE, rng)
    await send_beat(dut, B_TYPE, 5, rng)
    seen_err = False
    for _ in range(50):
        snap = await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=1)
        if snap['err_pre'] or snap['err_post']:
            seen_err = True
    assert seen_err, 'error not asserted'
    for _ in range(20):
        await cycle(dut, s_valid=1, s_type=CMD_TYPE, s_data=START_OPCODE, m_ready=1)
    for _ in range(20):
        snap = await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=1)
        assert snap['err_pre'] or snap['err_post'], 'error not sticky'
    dut.rst.value = 1
    await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=0)
    dut.rst.value = 0
    cleared = False
    for _ in range(10):
        snap = await cycle(dut, s_valid=0, s_type=0, s_data=0, m_ready=0)
        if snap['err_pre'] == 0 and snap['err_post'] == 0:
            cleared = True
    assert cleared, 'error did not clear after reset'
