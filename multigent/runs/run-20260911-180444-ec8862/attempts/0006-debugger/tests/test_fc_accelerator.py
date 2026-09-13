import random
import cocotb
from cocotb.triggers import Timer

from reference.fc_reference import (
    gemm_relu,
    pack_command,
    pack_int8,
    pack_int32,
    reference_sanity_checks,
)

SEED = 0x5A17C0DE


class Driver:
    def __init__(self, dut):
        self.dut = dut
        self.cycles = 0

    async def initialize(self):
        d = self.dut
        d.clk.value = 0
        d.rst_n.value = 1
        d.cmd_valid.value = 0
        d.cmd_data.value = 0
        d.a_valid.value = 0
        d.a_data.value = 0
        d.w_valid.value = 0
        d.w_data.value = 0
        d.bias_valid.value = 0
        d.bias_data.value = 0
        d.out_ready.value = 0
        d.status_ready.value = 0
        await Timer(1, unit="ns")

    async def cycle(self):
        d = self.dut
        await Timer(1, unit="ns")
        pre = {
            "cmd_ready": int(d.cmd_ready.value),
            "a_ready": int(d.a_ready.value),
            "w_ready": int(d.w_ready.value),
            "bias_ready": int(d.bias_ready.value),
            "out_valid": int(d.out_valid.value),
            "out_data": int(d.out_data.value),
            "status_valid": int(d.status_valid.value),
            "status_code": int(d.status_code.value),
        }
        d.clk.value = 1
        await Timer(1, unit="ns")
        post = {
            "cmd_ready": int(d.cmd_ready.value),
            "out_valid": int(d.out_valid.value),
            "status_valid": int(d.status_valid.value),
        }
        d.clk.value = 0
        await Timer(1, unit="ns")
        self.cycles += 1
        return pre, post

    async def reset(self):
        d = self.dut
        d.rst_n.value = 0
        pre, post = await self.cycle()
        assert post["cmd_ready"] == 1, "cmd_ready not asserted after reset edge"
        assert post["out_valid"] == 0, "out_valid survived reset"
        assert post["status_valid"] == 0, "status_valid survived reset"
        d.rst_n.value = 1
        await self.cycle()


async def idle_cycles(driver, count):
    driver.dut.cmd_valid.value = 0
    driver.dut.a_valid.value = 0
    driver.dut.w_valid.value = 0
    driver.dut.bias_valid.value = 0
    for _ in range(count):
        await driver.cycle()


async def send_beat(driver, valid_name, ready_name, data_name, data, rng=None, context=""):
    d = driver.dut
    if rng is not None:
        for _ in range(rng.randrange(4)):
            setattr(d, valid_name, 0)
            await driver.cycle()
    getattr(d, data_name).value = data
    getattr(d, valid_name).value = 1
    for waited in range(1000):
        pre, _ = await driver.cycle()
        if pre[ready_name]:
            getattr(d, valid_name).value = 0
            return
        assert int(getattr(d, valid_name).value) == 1, context + ": valid withdrawn"
        assert int(getattr(d, data_name).value) == data, context + ": payload changed"
    raise AssertionError(context + ": handshake timeout")


async def send_command(driver, m, n, k, rng=None):
    await send_beat(driver, "cmd_valid", "cmd_ready", "cmd_data",
                    pack_command(m, n, k), rng, "command")


async def load_operands(driver, a, w, bias, rng=None):
    for index, beat in enumerate(pack_int8(a)):
        await send_beat(driver, "a_valid", "a_ready", "a_data", beat, rng,
                        "activation beat %d" % index)
    for index, beat in enumerate(pack_int8(w)):
        await send_beat(driver, "w_valid", "w_ready", "w_data", beat, rng,
                        "weight beat %d" % index)
    for index, beat in enumerate(pack_int32(bias)):
        await send_beat(driver, "bias_valid", "bias_ready", "bias_data", beat, rng,
                        "bias beat %d" % index)


async def collect_result(driver, expected, rng=None, context=""):
    d = driver.dut
    expected_beats = pack_int32(expected)
    observed = []
    status_seen = False
    previous_out_stall = None
    previous_status_stall = None

    for cycle in range(40000):
        d.out_ready.value = 1 if rng is None else rng.randrange(2)
        d.status_ready.value = 1 if rng is None else rng.randrange(2)
        pre, _ = await driver.cycle()

        if previous_out_stall is not None:
            assert pre["out_valid"] == 1 and pre["out_data"] == previous_out_stall, \
                context + ": result changed while stalled"
        previous_out_stall = pre["out_data"] if pre["out_valid"] and not int(d.out_ready.value) else None

        if previous_status_stall is not None:
            assert pre["status_valid"] == 1 and pre["status_code"] == previous_status_stall, \
                context + ": status changed while stalled"
        previous_status_stall = pre["status_code"] if pre["status_valid"] and not int(d.status_ready.value) else None

        if pre["out_valid"] and int(d.out_ready.value):
            observed.append(pre["out_data"])
            index = len(observed) - 1
            assert index < len(expected_beats), context + ": extra result transfer"
            assert observed[index] == expected_beats[index], \
                "%s: beat %d expected 0x%016x observed 0x%016x" % (
                    context, index, expected_beats[index], observed[index])

        if pre["status_valid"] and int(d.status_ready.value):
            assert pre["status_code"] == 0, context + ": nonzero completion status"
            status_seen = True
            break

    assert status_seen, context + ": completion timeout"
    assert observed == expected_beats, "%s: expected %d output beats, observed %d" % (
        context, len(expected_beats), len(observed))
    d.out_ready.value = 0
    d.status_ready.value = 0


async def run_job(driver, m, n, k, a, w, bias, rng=None, context=""):
    expected = gemm_relu(m, n, k, a, w, bias)
    await send_command(driver, m, n, k, rng)
    await load_operands(driver, a, w, bias, rng)
    await collect_result(driver, expected, rng, context)


@cocotb.test()
async def reference_and_directed(dut):
    reference_sanity_checks()
    driver = Driver(dut)
    await driver.initialize()
    await driver.reset()

    cases = [
        (1, 1, 1), (1, 8, 7), (8, 1, 8), (8, 8, 9),
        (7, 9, 3), (9, 7, 11), (9, 9, 8), (16, 8, 1),
        (8, 16, 5), (17, 15, 9), (64, 64, 64),
    ]
    rng = random.Random(SEED)
    for case_index, (m, n, k) in enumerate(cases):
        a = [rng.randrange(-128, 128) for _ in range(m * k)]
        w = [rng.randrange(-128, 128) for _ in range(k * n)]
        bias = [rng.randrange(-0x80000000, 0x80000000) for _ in range(n)]
        if case_index == 0:
            a, w, bias = [0], [0], [0]
        await run_job(driver, m, n, k, a, w, bias, None,
                      "directed case %d dimensions %dx%dx%d" % (case_index, m, n, k))

    await run_job(driver, 1, 3, 1, [1], [1, -1, 0],
                  [0x7FFFFFFF, -0x80000000, 7], None, "bias overflow")


@cocotb.test()
async def randomized_backpressure(dut):
    reference_sanity_checks()
    driver = Driver(dut)
    await driver.initialize()
    await driver.reset()
    rng = random.Random(SEED)

    for transaction in range(100):
        m = rng.randint(1, 12)
        n = rng.randint(1, 12)
        k = rng.randint(1, 12)
        a = [rng.randrange(-128, 128) for _ in range(m * k)]
        w = [rng.randrange(-128, 128) for _ in range(k * n)]
        bias = [rng.randrange(-0x80000000, 0x80000000) for _ in range(n)]
        await run_job(driver, m, n, k, a, w, bias, rng,
                      "seed 0x%x transaction %d dimensions %dx%dx%d" % (
                          SEED, transaction, m, n, k))


@cocotb.test()
async def illegal_commands(dut):
    driver = Driver(dut)
    await driver.initialize()
    await driver.reset()
    cases = [(0, 1, 1), (1, 0, 1), (1, 1, 0),
             (65, 1, 1), (1, 65, 1), (1, 1, 65)]

    for m, n, k in cases:
        await send_command(driver, m, n, k)
        dut.a_valid.value = 1
        dut.a_data.value = 0x0101010101010101
        dut.w_valid.value = 1
        dut.w_data.value = 0x0202020202020202
        dut.bias_valid.value = 1
        dut.bias_data.value = 3
        dut.out_ready.value = 1
        dut.status_ready.value = 0

        found = False
        for _ in range(20):
            pre, _ = await driver.cycle()
            assert not pre["a_ready"] and not pre["w_ready"] and not pre["bias_ready"], \
                "illegal command accepted operand data"
            assert not pre["out_valid"], "illegal command emitted result"
            if pre["status_valid"]:
                assert pre["status_code"] == 1, "illegal command status was not 1"
                held = pre["status_code"]
                for _ in range(3):
                    nxt, _ = await driver.cycle()
                    assert nxt["status_valid"] and nxt["status_code"] == held, \
                        "error status not held under backpressure"
                dut.status_ready.value = 1
                transfer, _ = await driver.cycle()
                assert transfer["status_valid"] and transfer["status_code"] == 1
                found = True
                break
        assert found, "missing illegal-dimension status for %r" % ((m, n, k),)
        dut.a_valid.value = 0
        dut.w_valid.value = 0
        dut.bias_valid.value = 0
        dut.out_ready.value = 0
        dut.status_ready.value = 0


async def abort_and_check(driver, phase):
    await driver.reset()
    for _ in range(3):
        pre, _ = await driver.cycle()
        assert pre["cmd_ready"] == 1, phase + ": did not recover to idle"
        assert pre["out_valid"] == 0, phase + ": stale output after reset"
        assert pre["status_valid"] == 0, phase + ": stale status after reset"


async def launch_small(driver):
    await send_command(driver, 1, 1, 4)
    await load_operands(driver, [1, 2, 3, 4], [4, 3, 2, 1], [0])


@cocotb.test()
async def reset_every_phase(dut):
    driver = Driver(dut)
    await driver.initialize()

    await abort_and_check(driver, "IDLE")

    await send_command(driver, 1, 1, 4)
    await abort_and_check(driver, "LOAD_A")

    await send_command(driver, 1, 1, 4)
    await send_beat(driver, "a_valid", "a_ready", "a_data", pack_int8([1, 2, 3, 4])[0])
    await abort_and_check(driver, "LOAD_W")

    await send_command(driver, 1, 1, 4)
    await send_beat(driver, "a_valid", "a_ready", "a_data", pack_int8([1, 2, 3, 4])[0])
    await send_beat(driver, "w_valid", "w_ready", "w_data", pack_int8([4, 3, 2, 1])[0])
    await abort_and_check(driver, "LOAD_BIAS")

    await launch_small(driver)
    await abort_and_check(driver, "TILE_INIT")

    await launch_small(driver)
    await driver.cycle()
    await abort_and_check(driver, "COMPUTE")

    await launch_small(driver)
    for _ in range(1 + 4):
        await driver.cycle()
    await abort_and_check(driver, "FINALIZE")

    await launch_small(driver)
    dut.out_ready.value = 0
    for _ in range(100):
        pre, _ = await driver.cycle()
        if pre["out_valid"]:
            break
    else:
        raise AssertionError("OUTPUT phase not reached")
    await abort_and_check(driver, "OUTPUT")

    await launch_small(driver)
    dut.out_ready.value = 1
    dut.status_ready.value = 0
    for _ in range(100):
        pre, _ = await driver.cycle()
        if pre["status_valid"]:
            assert pre["status_code"] == 0
            break
    else:
        raise AssertionError("STATUS phase not reached")
    await abort_and_check(driver, "STATUS")
