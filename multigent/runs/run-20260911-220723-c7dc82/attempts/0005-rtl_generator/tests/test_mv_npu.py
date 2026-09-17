import random
import cocotb
from cocotb.triggers import Timer, SimTimeoutError
from reference.mv_npu_ref import mv_job, s8, s32, sanity_checks

TYPE_CFG = 0
TYPE_X = 1
TYPE_A = 2
TYPE_B = 3

MAX_M = 256
MAX_N = 256
SEED = 20260911


def pack_cfg(m, n, bias_en, relu_en):
    # cfg_word on 32-bit ingress beat per frozen contract usage
    return ((relu_en & 1) << 17) | ((bias_en & 1) << 16) | ((n & 0xFF) << 8) | (m & 0xFF)


async def cycle(dut, in_drive=None, out_ready=1):
    dut.clk.value = 0
    if in_drive is None:
        dut.in_valid.value = 0
        dut.in_data.value = 0
        dut.in_type.value = 0
        dut.in_last.value = 0
    else:
        dut.in_valid.value = in_drive["valid"]
        dut.in_data.value = in_drive["data"]
        dut.in_type.value = in_drive["type"]
        dut.in_last.value = in_drive["last"]
    dut.out_ready.value = out_ready
    await Timer(1, units="ns")
    in_hs = int(dut.in_valid.value) and int(dut.in_ready.value)
    out_hs = int(dut.out_valid.value) and int(dut.out_ready.value)
    out_data = s32(int(dut.out_data.value)) if int(dut.out_valid.value) else None
    out_last = int(dut.out_last.value) if int(dut.out_valid.value) else 0
    dut.clk.value = 1
    await Timer(1, units="ns")
    dut.clk.value = 0
    await Timer(1, units="ns")
    return in_hs, out_hs, out_data, out_last, int(dut.status_err.value), int(dut.busy.value)


async def apply_reset(dut, cycles=3):
    dut.rst_n.value = 0
    for _ in range(cycles):
        await cycle(dut, None, 0)
    dut.rst_n.value = 1
    await cycle(dut, None, 1)


async def send_beat_hold_until_hs(dut, beat, out_ready_fn):
    while True:
        _, _, _, _, _, _ = await cycle(dut, beat, out_ready_fn())
        if int(dut.in_ready.value) and beat["valid"]:
            break


async def run_job(dut, cfg, x, a, b, out_ready_fn, src_idle_rng):
    beats = []
    beats.append({"valid": 1, "data": pack_cfg(cfg['M'], cfg['N'], cfg['bias_en'], cfg['relu_en']), "type": TYPE_CFG, "last": 1})
    for i, xv in enumerate(x):
        beats.append({"valid": 1, "data": (s8(xv) & 0xFF), "type": TYPE_X, "last": 1 if i == len(x)-1 else 0})
    flat_a = [v for row in a for v in row]
    for i, av in enumerate(flat_a):
        beats.append({"valid": 1, "data": (s8(av) & 0xFF), "type": TYPE_A, "last": 1 if i == len(flat_a)-1 else 0})
    if cfg["bias_en"]:
        for i, bv in enumerate(b):
            beats.append({"valid": 1, "data": (s32(bv) & 0xFFFFFFFF), "type": TYPE_B, "last": 1 if i == len(b)-1 else 0})

    exp = mv_job(cfg, x, a, b if cfg["bias_en"] else None)

    out = []
    idx = 0
    wait_cycles = 0
    while idx < len(beats) or len(out) < cfg["M"]:
        if idx < len(beats) and src_idle_rng.randint(0, 3) == 0:
            in_drive = None
        elif idx < len(beats):
            in_drive = beats[idx]
        else:
            in_drive = None

        in_hs, out_hs, out_data, out_last, _, _ = await cycle(dut, in_drive, out_ready_fn())
        if in_drive is not None and in_hs:
            idx += 1
        if out_hs:
            out.append((out_data, out_last))

        wait_cycles += 1
        if wait_cycles > 50000:
            raise SimTimeoutError("job timeout")

    assert len(out) == cfg["M"], f"output count mismatch exp={cfg['M']} got={len(out)}"
    for i, (d, l) in enumerate(out):
        assert d == exp[i], f"row {i} mismatch exp={exp[i]} got={d}"
        assert l == (1 if i == cfg["M"]-1 else 0), f"out_last mismatch row={i}"


@cocotb.test()
async def test_smoke_directed(dut):
    sanity_checks()
    await apply_reset(dut)
    cfg = {"M": 2, "N": 3, "bias_en": 1, "relu_en": 1}
    x = [1, -2, 3]
    a = [[4, 5, -6], [-1, -1, -1]]
    b = [7, -100]
    rng = random.Random(SEED)
    await run_job(dut, cfg, x, a, b, out_ready_fn=lambda: 1, src_idle_rng=rng)


@cocotb.test()
async def test_reset_idle_and_active(dut):
    await apply_reset(dut)
    assert int(dut.status_err.value) == 0
    cfg = {"M": 4, "N": 5, "bias_en": 0, "relu_en": 0}
    x = [1, 2, 3, 4, 5]
    a = [[1, 0, 0, 0, 0] for _ in range(4)]
    b = []
    rng = random.Random(SEED + 1)
    await run_job(dut, cfg, x, a, b, out_ready_fn=lambda: 1, src_idle_rng=rng)
    await apply_reset(dut)


@cocotb.test()
async def test_backpressure_in_out(dut):
    await apply_reset(dut)
    cfg = {"M": 8, "N": 17, "bias_en": 1, "relu_en": 0}
    rng = random.Random(SEED + 2)
    x = [rng.randint(-128, 127) for _ in range(cfg["N"])]
    a = [[rng.randint(-128, 127) for _ in range(cfg["N"])] for _ in range(cfg["M"])]
    b = [rng.randint(-(1<<31), (1<<31)-1) for _ in range(cfg["M"])]
    out_rng = random.Random(SEED + 3)
    await run_job(dut, cfg, x, a, b, out_ready_fn=lambda: 1 if out_rng.randint(0, 2) else 0, src_idle_rng=rng)


@cocotb.test()
async def test_illegal_cfg_error_recovery(dut):
    await apply_reset(dut)
    illegal = [pack_cfg(0, 4, 0, 0), pack_cfg(4, 0, 0, 0), pack_cfg(255, 1, 0, 0)]
    for w in illegal:
        beat = {"valid": 1, "data": w, "type": TYPE_CFG, "last": 1}
        await send_beat_hold_until_hs(dut, beat, lambda: 1)
        for _ in range(3):
            _, _, _, _, err, _ = await cycle(dut, None, 1)
        assert err == 1, "status_err must assert for illegal cfg"

    cfg = {"M": 1, "N": 1, "bias_en": 0, "relu_en": 0}
    x = [2]
    a = [[3]]
    await run_job(dut, cfg, x, a, [], out_ready_fn=lambda: 1, src_idle_rng=random.Random(SEED + 4))
    assert int(dut.status_err.value) == 0, "status_err must clear after legal cfg accept"


@cocotb.test()
async def test_randomized_100(dut):
    await apply_reset(dut)
    rng = random.Random(SEED)
    for t in range(100):
        m = rng.randint(1, 16)
        n = rng.randint(1, 32)
        cfg = {
            "M": m,
            "N": n,
            "bias_en": rng.randint(0, 1),
            "relu_en": rng.randint(0, 1),
        }
        x = [rng.randint(-128, 127) for _ in range(n)]
        a = [[rng.randint(-128, 127) for _ in range(n)] for _ in range(m)]
        b = [rng.randint(-(1<<31), (1<<31)-1) for _ in range(m)] if cfg["bias_en"] else []
        out_rng = random.Random(SEED + 1000 + t)
        await run_job(dut, cfg, x, a, b, out_ready_fn=lambda: 1 if out_rng.randint(0, 3) else 0, src_idle_rng=rng)
