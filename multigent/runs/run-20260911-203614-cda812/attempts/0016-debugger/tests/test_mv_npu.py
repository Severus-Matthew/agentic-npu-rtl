import random
import cocotb
from cocotb.triggers import Timer
from cocotb.triggers import SimTimeoutError

from reference.mv_npu_ref import golden_outputs, pack_cmd, pack_mat_beat_lanes

SEED = 12345

async def cycle(dut):
    dut.clk.value = 0
    await Timer(1, units='ns')
    pre = {
        'cmd_ready': int(dut.cmd_ready.value), 'vec_ready': int(dut.vec_ready.value),
        'mat_ready': int(dut.mat_ready.value), 'bias_ready': int(dut.bias_ready.value),
        'out_valid': int(dut.out_valid.value), 'out_data': int(dut.out_data.value.signed_integer),
        'busy': int(dut.status_busy.value), 'err': int(dut.status_error.value),
    }
    dut.clk.value = 1
    await Timer(1, units='ns')
    post = {
        'out_valid': int(dut.out_valid.value), 'out_data': int(dut.out_data.value.signed_integer),
        'busy': int(dut.status_busy.value), 'err': int(dut.status_error.value),
    }
    return pre, post

async def reset(dut):
    dut.cmd_valid.value = 0; dut.vec_valid.value = 0; dut.mat_valid.value = 0; dut.bias_valid.value = 0; dut.out_ready.value = 0
    dut.cmd_data.value = 0; dut.vec_data.value = 0; dut.mat_data.value = 0; dut.bias_data.value = 0
    dut.rst_n.value = 0
    for _ in range(3):
        await cycle(dut)
    dut.rst_n.value = 1
    for _ in range(3):
        await cycle(dut)

async def send_beat(dut, valid_sig, ready_sig, data_sig, data, max_wait=500):
    valid_sig.value = 1
    data_sig.value = data
    for _ in range(max_wait):
        pre, _ = await cycle(dut)
        if pre[ready_sig] == 1:
            valid_sig.value = 0
            return
    raise SimTimeoutError(f'timeout waiting {ready_sig}')

@cocotb.test()
async def test_directed_basic(dut):
    await reset(dut)
    M, N = 2, 5
    vec = [1, -2, 3, -4, 5]
    mat = [[1,1,1,1,1], [-1,2,-3,4,-5]]
    exp = golden_outputs(M, N, vec, mat, 0, 0, [])
    await send_beat(dut, dut.cmd_valid, 'cmd_ready', dut.cmd_data, pack_cmd(M, N, 0, 0))
    for x in vec:
        await send_beat(dut, dut.vec_valid, 'vec_ready', dut.vec_data, x & 0xFF)
    chunks = (N + 15)//16
    for r in range(M):
        for c in range(chunks):
            base = 16*c
            lanes = [mat[r][base+i] if base+i < N else 0 for i in range(16)]
            await send_beat(dut, dut.mat_valid, 'mat_ready', dut.mat_data, pack_mat_beat_lanes(lanes))
    dut.out_ready.value = 1
    got = []
    for _ in range(5000):
        pre, _ = await cycle(dut)
        if pre['out_valid'] and int(dut.out_ready.value):
            got.append(pre['out_data'])
            if len(got) == M:
                break
    assert got == exp

@cocotb.test()
async def test_randomized_100_jobs(dut):
    rng = random.Random(SEED)
    await reset(dut)
    jobs = 100
    for j in range(jobs):
        M = rng.randint(1, 16)
        N = rng.randint(1, 31)
        bias_en = rng.randint(0,1)
        relu_en = rng.randint(0,1)
        vec = [rng.randint(-128,127) for _ in range(N)]
        mat = [[rng.randint(-128,127) for _ in range(N)] for _ in range(M)]
        bias = [rng.randint(-(1<<31),(1<<31)-1) for _ in range(M)] if bias_en else []
        exp = golden_outputs(M,N,vec,mat,bias_en,relu_en,bias)
        await send_beat(dut, dut.cmd_valid, 'cmd_ready', dut.cmd_data, pack_cmd(M,N,bias_en,relu_en))
        for x in vec: await send_beat(dut, dut.vec_valid, 'vec_ready', dut.vec_data, x & 0xFF)
        for r in range(M):
            for c in range((N+15)//16):
                lanes = [mat[r][16*c+i] if 16*c+i < N else 0 for i in range(16)]
                await send_beat(dut, dut.mat_valid, 'mat_ready', dut.mat_data, pack_mat_beat_lanes(lanes))
        if bias_en:
            for b in bias: await send_beat(dut, dut.bias_valid, 'bias_ready', dut.bias_data, b & 0xFFFFFFFF)
        got=[]
        for _ in range(20000):
            dut.out_ready.value = rng.randint(0,1)
            pre,_=await cycle(dut)
            if pre['out_valid'] and int(dut.out_ready.value):
                got.append(pre['out_data'])
                if len(got)==M: break
        assert got==exp, f'job={j} seed={SEED}'
