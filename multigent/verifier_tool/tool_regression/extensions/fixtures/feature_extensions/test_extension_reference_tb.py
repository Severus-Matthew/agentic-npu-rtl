"""Executable semantic TBs for extension scenarios 11-25.

Each case has three explicit branches named exactly as an extension bundle would
reference them: ``assert_case_N``, ``cover_case_N``, and
``stimulate_case_N``.  Stimulus drives real simulator signals, assertions read
actual DUT outputs, coverage is classified from that observed evidence, and
every test includes a corrupted-evidence negative control proving its checker
does not pass merely because the scenario ran.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer


INPUTS = (
    "op_a", "op_b", "op_bias", "shape_m",
    "matrix_a00", "matrix_a01", "matrix_a10", "matrix_a11",
    "matrix_a20", "matrix_a21", "matrix_a30", "matrix_a31",
    "matrix_b0", "matrix_b1", "sparse_idx0", "sparse_idx1",
    "sparse_val0", "sparse_val1", "dense0", "dense1", "dense2", "dense3",
    "conv_x0", "conv_x1", "conv_x2", "conv_k0", "conv_k1", "conv_k2",
    "attention_q", "attention_k", "attention_mask", "attention_k0",
    "attention_k1", "attention_v0", "attention_v1", "attention_mask0",
    "attention_mask1", "round_shift",
    "req_valid", "req_data", "req_id", "req_last", "req_empty", "req_len",
    "req_delay", "reverse_responses", "rsp_ready", "four_req", "start",
    "wb_cyc", "wb_stb", "wb_we", "wb_addr", "wb_wdata", "wb_delay",
    "tl_a_valid", "tl_a_source", "tl_a_data", "tl_d_ready",
    "avmm_read", "avmm_address", "avmm_burstcount", "avmm_delay",
    "avst_in_valid", "avst_in_data", "avst_in_startofpacket",
    "avst_in_endofpacket", "avst_in_empty", "avst_out_ready",
    "x_arvalid", "x_araddr", "x_arepoch", "x_force_retry", "x_rready",
    "cancel", "software_ack", "illegal_command", "sticky_completion",
    "queue_enable", "checkpoint_reset", "work_cycles", "job_id",
)


async def _setup(dut):
    for name in INPUTS:
        getattr(dut, name).value = 0
    dut.round_shift.value = 1
    dut.rst_n.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def _drive_before_edge(dut, **values):
    await FallingEdge(dut.clk)
    for name, value in values.items():
        getattr(dut, name).value = value
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def _idle_cycle(dut):
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


def _signed(signal):
    return signal.value.to_signed()


def _must_reject(checker, evidence):
    try:
        checker(evidence)
    except AssertionError:
        return
    raise AssertionError("negative-control evidence was incorrectly accepted")


def _expect_equal(evidence):
    assert evidence["observed"] == evidence["expected"], evidence


async def _send_request(
    dut, *, data, identity=0, last=0, empty=0, length=1, delay=0, reverse=0,
):
    await FallingEdge(dut.clk)
    dut.req_valid.value = 1
    dut.req_data.value = data
    dut.req_id.value = identity
    dut.req_last.value = last
    dut.req_empty.value = empty
    dut.req_len.value = length
    dut.req_delay.value = delay
    dut.reverse_responses.value = reverse
    await Timer(1, unit="ns")
    # Acceptance is the stable pre-active-edge VALID/READY state. Checking
    # READY after the edge is wrong: a legal receiver may lower it immediately
    # after accepting the beat.
    assert int(dut.req_ready.value) == 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.req_valid.value = 0
    await Timer(1, unit="ns")


async def _receive_response(dut, *, watchdog=20):
    dut.rsp_ready.value = 1
    for elapsed in range(1, watchdog + 1):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if int(dut.rsp_valid.value):
            evidence = {
                "elapsed": elapsed,
                "data": int(dut.rsp_data.value),
                "id": int(dut.rsp_id.value),
                "last": int(dut.rsp_last.value),
                "empty": int(dut.rsp_empty.value),
                "length": int(dut.rsp_len.value),
            }
            await RisingEdge(dut.clk)
            await Timer(1, unit="ns")
            return evidence
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
    raise AssertionError("response watchdog expired")


async def _axi_extension_attempt(dut, *, address, epoch, retry):
    await FallingEdge(dut.clk)
    dut.x_arvalid.value = 1
    dut.x_araddr.value = address
    dut.x_arepoch.value = epoch
    dut.x_force_retry.value = retry
    await Timer(1, unit="ns")
    assert int(dut.x_arready.value) == 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.x_arvalid.value = 0
    dut.x_rready.value = 1
    for _ in range(8):
        await Timer(1, unit="ns")
        if int(dut.x_rvalid.value):
            evidence = {
                "data": int(dut.x_rdata.value),
                "response": int(dut.x_rresp.value),
                "epoch": int(dut.x_repoch.value),
            }
            await RisingEdge(dut.clk)
            return evidence
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
    raise AssertionError("AXI extension response watchdog expired")


# Case 11: runtime-selectable GEMM shape.
def assert_case_11(evidence):
    assert {item["m"] for item in evidence} == {1, 2, 4}
    for item in evidence:
        assert item["observed"] == item["expected"], item
        assert len(item["observed"]) == item["m"]
        assert item["valid_mask"] == (1 << item["m"]) - 1


def cover_case_11(evidence):
    return {
        "minimum_shape": any(item["m"] == 1 for item in evidence),
        "interior_shape": any(item["m"] == 2 for item in evidence),
        "maximum_shape": any(item["m"] == 4 for item in evidence),
    }


async def stimulate_case_11(dut):
    matrix_a = [[1, 2], [-3, 4], [5, -6], [-7, -8]]
    matrix_b = [3, -2]
    for row, values in enumerate(matrix_a):
        for column, value in enumerate(values):
            getattr(dut, f"matrix_a{row}{column}").value = value
    dut.matrix_b0.value, dut.matrix_b1.value = matrix_b
    await Timer(1, unit="ns")
    all_expected = [sum(a * b for a, b in zip(row, matrix_b)) for row in matrix_a]
    evidence = []
    for m in (1, 2, 4):
        dut.shape_m.value = m
        await Timer(1, unit="ns")
        all_observed = [
            _signed(dut.matrix_c0), _signed(dut.matrix_c1),
            _signed(dut.matrix_c2), _signed(dut.matrix_c3),
        ]
        evidence.append({
            "m": m,
            "expected": all_expected[:m],
            "observed": all_observed[:m],
            "valid_mask": int(dut.matrix_result_valid.value),
        })
    return evidence


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_11_runtime_shape(dut):
    await _setup(dut)
    evidence = await stimulate_case_11(dut)
    assert_case_11(evidence)
    assert all(cover_case_11(evidence).values())
    bad = [dict(item) for item in evidence]
    bad[-1]["observed"] = list(bad[-1]["observed"])
    bad[-1]["observed"][-1] += 1
    _must_reject(assert_case_11, bad)
    bad_mask = [dict(item) for item in evidence]
    bad_mask[1]["valid_mask"] = 0b1111
    _must_reject(assert_case_11, bad_mask)


# Case 12: block-sparse index/value serialization.
def assert_case_12(evidence):
    _expect_equal(evidence)
    assert evidence["accepted_indices"] == [0, 3]


def cover_case_12(evidence):
    return {
        "nonadjacent_blocks": evidence["accepted_indices"][1] - evidence["accepted_indices"][0] > 1,
        "signed_values": min(evidence["accepted_values"]) < 0 < max(evidence["accepted_values"]),
    }


async def stimulate_case_12(dut):
    dut.sparse_idx0.value = 0
    dut.sparse_idx1.value = 3
    dut.sparse_val0.value = -2
    dut.sparse_val1.value = 4
    for name, value in zip(("dense0", "dense1", "dense2", "dense3"), (7, 8, 9, -3)):
        getattr(dut, name).value = value
    await Timer(1, unit="ns")
    return {
        "accepted_indices": [int(dut.sparse_idx0.value), int(dut.sparse_idx1.value)],
        "accepted_values": [_signed(dut.sparse_val0), _signed(dut.sparse_val1)],
        "expected": -2 * 7 + 4 * -3,
        "observed": _signed(dut.sparse_result),
    }


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_12_sparse_layout(dut):
    await _setup(dut)
    evidence = await stimulate_case_12(dut)
    assert_case_12(evidence)
    assert all(cover_case_12(evidence).values())
    _must_reject(assert_case_12, {**evidence, "observed": evidence["observed"] + 1})


# Case 13: signed three-tap convolution arithmetic.
def assert_case_13(evidence):
    _expect_equal(evidence)
    assert len(evidence["samples"]) == len(evidence["kernel"]) == 3


def cover_case_13(evidence):
    products = [a * b for a, b in zip(evidence["samples"], evidence["kernel"])]
    return {
        "signed_mix": min(products) < 0 < max(products),
        "three_tap_kernel": len(products) == 3,
    }


async def stimulate_case_13(dut):
    samples, kernel = [-3, 2, 5], [4, -2, 1]
    for index, value in enumerate(samples):
        getattr(dut, f"conv_x{index}").value = value
    for index, value in enumerate(kernel):
        getattr(dut, f"conv_k{index}").value = value
    await Timer(1, unit="ns")
    accepted_samples = [_signed(getattr(dut, f"conv_x{index}")) for index in range(3)]
    accepted_kernel = [_signed(getattr(dut, f"conv_k{index}")) for index in range(3)]
    return {
        "samples": accepted_samples,
        "kernel": accepted_kernel,
        "expected": sum(a * b for a, b in zip(samples, kernel)),
        "observed": _signed(dut.conv_result),
    }


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_13_convolution(dut):
    await _setup(dut)
    evidence = await stimulate_case_13(dut)
    assert_case_13(evidence)
    assert all(cover_case_13(evidence).values())
    _must_reject(assert_case_13, {**evidence, "observed": 0})


# Case 14: exact two-token sparse linear attention.
def assert_case_14(evidence):
    assert len(evidence) == 2
    for item in evidence:
        _expect_equal(item)


def cover_case_14(evidence):
    return {
        "both_tokens_active": any(item["masks"] == [0, 0] for item in evidence),
        "one_token_masked": any(sum(item["masks"]) == 1 for item in evidence),
    }


async def stimulate_case_14(dut):
    result = []
    q, keys, values = 3, [2, 4], [10, -2]
    for masks in ([0, 0], [0, 1]):
        dut.attention_q.value = q
        dut.attention_k0.value, dut.attention_k1.value = keys
        dut.attention_v0.value, dut.attention_v1.value = values
        dut.attention_mask0.value, dut.attention_mask1.value = masks
        await Timer(1, unit="ns")
        accepted_masks = [int(dut.attention_mask0.value), int(dut.attention_mask1.value)]
        accepted_q = _signed(dut.attention_q)
        accepted_keys = [_signed(dut.attention_k0), _signed(dut.attention_k1)]
        accepted_values = [_signed(dut.attention_v0), _signed(dut.attention_v1)]
        weights = [
            0 if mask else max(accepted_q * key, 0)
            for mask, key in zip(accepted_masks, accepted_keys)
        ]
        expected = sum(weight * value for weight, value in zip(weights, accepted_values)) // sum(weights)
        result.append({
            "masks": accepted_masks,
            "expected": expected,
            "observed": _signed(dut.sparse_attention_result),
        })
    return result


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_14_sparse_attention(dut):
    await _setup(dut)
    evidence = await stimulate_case_14(dut)
    assert_case_14(evidence)
    assert all(cover_case_14(evidence).values())
    bad = [dict(item) for item in evidence]
    bad[1]["observed"] += 1
    _must_reject(assert_case_14, bad)


# Case 15: bounded Wishbone Classic acknowledge delay.
def assert_case_15(evidence):
    assert evidence["rdata"] == (evidence["address"] ^ evidence["wdata"])
    assert 1 <= evidence["ack_cycle"] <= 6
    assert evidence["request_stable"]
    assert evidence["err"] == 0


def cover_case_15(evidence):
    return {
        "wait_state_seen": evidence["ack_cycle"] > 1,
        "within_budget": evidence["ack_cycle"] <= 6,
    }


async def stimulate_case_15(dut):
    address, wdata = 0x100, 0x1234
    await FallingEdge(dut.clk)
    dut.wb_cyc.value = 1
    dut.wb_stb.value = 1
    dut.wb_we.value = 0
    dut.wb_addr.value = address
    dut.wb_wdata.value = wdata
    dut.wb_delay.value = 3
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    stable = True
    for cycle in range(1, 8):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        stable &= (
            int(dut.wb_cyc.value) == 1
            and int(dut.wb_stb.value) == 1
            and int(dut.wb_addr.value) == address
            and int(dut.wb_wdata.value) == wdata
        )
        if int(dut.wb_ack.value):
            evidence = {
                "ack_cycle": cycle,
                "address": address,
                "wdata": wdata,
                "rdata": int(dut.wb_rdata.value),
                "request_stable": stable,
                "err": int(dut.wb_err.value),
            }
            await RisingEdge(dut.clk)
            dut.wb_cyc.value = 0
            dut.wb_stb.value = 0
            return evidence
        await RisingEdge(dut.clk)
    raise AssertionError("Wishbone ACK watchdog expired")


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_15_wishbone_wait(dut):
    await _setup(dut)
    evidence = await stimulate_case_15(dut)
    assert_case_15(evidence)
    assert all(cover_case_15(evidence).values())
    _must_reject(assert_case_15, {**evidence, "ack_cycle": 7})
    _must_reject(assert_case_15, {**evidence, "err": 1})


# Case 16: TileLink A/D source ID correlation under reversed responses.
def assert_case_16(evidence):
    assert [item["id"] for item in evidence] == [9, 2]
    assert [item["data"] for item in evidence] == [0x99, 0x22]


def cover_case_16(evidence):
    return {
        "reordered": [item["id"] for item in evidence] == [9, 2],
        "source_ids_distinct": len({item["id"] for item in evidence}) == 2,
    }


async def stimulate_case_16(dut):
    dut.tl_d_ready.value = 0
    for data, source in ((0x22, 2), (0x99, 9)):
        await FallingEdge(dut.clk)
        dut.tl_a_valid.value = 1
        dut.tl_a_data.value = data
        dut.tl_a_source.value = source
        await Timer(1, unit="ns")
        assert int(dut.tl_a_ready.value) == 1
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        dut.tl_a_valid.value = 0
        await Timer(1, unit="ns")
    dut.tl_d_ready.value = 1
    evidence = []
    for _ in range(12):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if int(dut.tl_d_valid.value):
            evidence.append({
                "id": int(dut.tl_d_source.value),
                "data": int(dut.tl_d_data.value),
            })
        await RisingEdge(dut.clk)
        if len(evidence) == 2:
            return evidence
    raise AssertionError("TileLink D response watchdog expired")


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_16_tilelink_reorder(dut):
    await _setup(dut)
    evidence = await stimulate_case_16(dut)
    assert_case_16(evidence)
    assert all(cover_case_16(evidence).values())
    _must_reject(assert_case_16, list(reversed(evidence)))


# Case 17: Avalon-MM burst returns the declared number of response beats.
def assert_case_17(evidence):
    assert evidence["beats"] == [0x200 + index for index in range(8)]
    assert evidence["responses"] == [0] * 8


def cover_case_17(evidence):
    return {
        "multi_beat_burst": len(evidence["beats"]) > 1,
        "wait_state_seen": evidence["wait_cycles"] > 1,
    }


async def stimulate_case_17(dut):
    await FallingEdge(dut.clk)
    dut.avmm_read.value = 1
    dut.avmm_address.value = 0x200
    dut.avmm_burstcount.value = 8
    dut.avmm_delay.value = 2
    await Timer(1, unit="ns")
    assert int(dut.avmm_waitrequest.value) == 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.avmm_read.value = 0
    wait_cycles = 0
    beats, responses = [], []
    for _ in range(20):
        await Timer(1, unit="ns")
        wait_cycles += int(dut.avmm_waitrequest.value)
        if int(dut.avmm_readdatavalid.value):
            beats.append(int(dut.avmm_readdata.value))
            responses.append(int(dut.avmm_response.value))
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        if len(beats) == 8:
            return {"beats": beats, "responses": responses, "wait_cycles": wait_cycles}
    raise AssertionError("Avalon-MM burst watchdog expired")


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_17_avalon_mm_burst(dut):
    await _setup(dut)
    evidence = await stimulate_case_17(dut)
    assert_case_17(evidence)
    assert all(cover_case_17(evidence).values())
    _must_reject(assert_case_17, {**evidence, "beats": evidence["beats"][:-1]})


# Case 18: Avalon-ST final-beat empty-symbol framing remains stable under stall.
def assert_case_18(evidence):
    assert evidence["samples"] == [(0xDEAD, 1, 1, 3)] * 3
    assert evidence["valid_after_transfer"] == 0


def cover_case_18(evidence):
    return {
        "partial_final_beat": evidence["samples"][0][2:] == (1, 3),
        "stalled_content_stable": len(set(evidence["samples"])) == 1,
        "transferred_after_stall": evidence["valid_after_transfer"] == 0,
    }


async def stimulate_case_18(dut):
    dut.avst_out_ready.value = 0
    await FallingEdge(dut.clk)
    dut.avst_in_valid.value = 1
    dut.avst_in_data.value = 0xDEAD
    dut.avst_in_startofpacket.value = 1
    dut.avst_in_endofpacket.value = 1
    dut.avst_in_empty.value = 3
    await Timer(1, unit="ns")
    assert int(dut.avst_in_ready.value) == 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.avst_in_valid.value = 0
    samples = []
    for _ in range(3):
        await Timer(1, unit="ns")
        assert int(dut.avst_out_valid.value) == 1
        samples.append((
            int(dut.avst_out_data.value),
            int(dut.avst_out_startofpacket.value),
            int(dut.avst_out_endofpacket.value),
            int(dut.avst_out_empty.value),
        ))
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
    dut.avst_out_ready.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    return {
        "samples": samples,
        "valid_after_transfer": int(dut.avst_out_valid.value),
    }


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_18_avalon_stream_framing(dut):
    await _setup(dut)
    evidence = await stimulate_case_18(dut)
    assert_case_18(evidence)
    assert all(cover_case_18(evidence).values())
    bad = {"samples": list(evidence["samples"])}
    bad["samples"][-1] = (0xDEAD, 1, 0, 3)
    bad["valid_after_transfer"] = evidence["valid_after_transfer"]
    _must_reject(assert_case_18, bad)
    _must_reject(assert_case_18, {**evidence, "valid_after_transfer": 1})


# Case 19: custom four-phase request/acknowledge sequence.
def assert_case_19(evidence):
    assert evidence == [(0, 0), (1, 1), (0, 0)]


def cover_case_19(evidence):
    return {
        "request_phase": (1, 1) in evidence,
        "return_to_zero": evidence[-1] == (0, 0),
    }


async def stimulate_case_19(dut):
    evidence = [(int(dut.four_req.value), int(dut.four_ack.value))]
    dut.four_req.value = 1
    await Timer(1, unit="ns")
    evidence.append((int(dut.four_req.value), int(dut.four_ack.value)))
    dut.four_req.value = 0
    await Timer(1, unit="ns")
    evidence.append((int(dut.four_req.value), int(dut.four_ack.value)))
    return evidence


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_19_four_phase(dut):
    await _setup(dut)
    evidence = await stimulate_case_19(dut)
    assert_case_19(evidence)
    assert all(cover_case_19(evidence).values())
    _must_reject(assert_case_19, [(0, 0), (1, 0), (0, 0)])


# Case 20: cancellation drains for exactly two active cycles, then aborts.
def assert_case_20(evidence):
    assert evidence["busy_trace"][:2] == [1, 1]
    assert evidence["busy_trace"][-1] == 0
    assert evidence["completion_trace"] == [0, 0, 0]


def cover_case_20(evidence):
    return {
        "cancel_while_active": evidence["busy_trace"][0] == 1,
        "drain_then_abort": evidence["busy_trace"] == [1, 1, 0],
    }


async def stimulate_case_20(dut):
    dut.work_cycles.value = 8
    trace = {"busy_trace": [], "completion_trace": []}
    await _drive_before_edge(dut, start=1)
    await _drive_before_edge(dut, start=0, cancel=1)
    trace["busy_trace"].append(int(dut.busy.value))
    trace["completion_trace"].append(int(dut.completion.value))
    await _drive_before_edge(dut, cancel=0)
    trace["busy_trace"].append(int(dut.busy.value))
    trace["completion_trace"].append(int(dut.completion.value))
    await _idle_cycle(dut)
    trace["busy_trace"].append(int(dut.busy.value))
    trace["completion_trace"].append(int(dut.completion.value))
    return trace


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_20_cancel_drain(dut):
    await _setup(dut)
    evidence = await stimulate_case_20(dut)
    assert_case_20(evidence)
    assert all(cover_case_20(evidence).values())
    _must_reject(assert_case_20, {**evidence, "completion_trace": [0, 1, 0]})


# Case 21: completion remains asserted until software acknowledgement.
def assert_case_21(evidence):
    assert evidence["held"] == [1, 1, 1]
    assert evidence["after_ack"] == 0


def cover_case_21(evidence):
    return {
        "sticky_level": all(evidence["held"]),
        "software_clear": evidence["after_ack"] == 0,
    }


async def stimulate_case_21(dut):
    dut.sticky_completion.value = 1
    dut.work_cycles.value = 2
    await _drive_before_edge(dut, start=1)
    await _drive_before_edge(dut, start=0)
    while not int(dut.completion.value):
        await _idle_cycle(dut)
    held = []
    for _ in range(3):
        held.append(int(dut.completion.value))
        await _idle_cycle(dut)
    await _drive_before_edge(dut, software_ack=1)
    after_ack = int(dut.completion.value)
    dut.software_ack.value = 0
    return {"held": held, "after_ack": after_ack}


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_21_sticky_completion(dut):
    await _setup(dut)
    evidence = await stimulate_case_21(dut)
    assert_case_21(evidence)
    assert all(cover_case_21(evidence).values())
    _must_reject(assert_case_21, {**evidence, "held": [1, 0, 0]})


# Case 22: one active plus one queued job produces two completions.
def assert_case_22(evidence):
    assert evidence["accepted_jobs"] == 2
    assert evidence["completion_count"] == 2
    assert evidence["completion_ids"] == [5, 9]


def cover_case_22(evidence):
    return {
        "queue_depth_two": evidence["accepted_jobs"] == 2,
        "both_jobs_retired": evidence["completion_count"] == 2,
        "acceptance_order_preserved": evidence["completion_ids"] == [5, 9],
    }


async def stimulate_case_22(dut):
    dut.queue_enable.value = 1
    dut.work_cycles.value = 4
    await _drive_before_edge(dut, start=1, job_id=5)
    await _drive_before_edge(dut, start=0)
    await _drive_before_edge(dut, start=1, job_id=9)
    await _drive_before_edge(dut, start=0)
    completions = 0
    completion_ids = []
    for _ in range(12):
        await _idle_cycle(dut)
        if int(dut.completion.value):
            completions += 1
            completion_ids.append(int(dut.completion_id.value))
        if completions == 2:
            break
    return {
        "accepted_jobs": int(dut.accepted_jobs.value),
        "completion_count": completions,
        "completion_ids": completion_ids,
    }


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_22_two_deep_queue(dut):
    await _setup(dut)
    evidence = await stimulate_case_22(dut)
    assert_case_22(evidence)
    assert all(cover_case_22(evidence).values())
    _must_reject(assert_case_22, {**evidence, "completion_count": 1})
    _must_reject(assert_case_22, {**evidence, "completion_ids": [9, 5]})


# Case 23: checkpoint reset preserves active work; sticky error needs ack.
def assert_case_23(evidence):
    assert evidence["busy_before_reset"] == 1
    assert evidence["busy_during_reset"] == 1
    assert evidence["error_before_ack"] == 1
    assert evidence["error_after_ack"] == 0
    assert evidence["completion_after_resume"] == 1
    assert evidence["busy_after_completion"] == 0


def cover_case_23(evidence):
    return {
        "checkpoint_preserved": evidence["busy_during_reset"] == 1,
        "error_software_clear": evidence["error_before_ack"] == 1 and evidence["error_after_ack"] == 0,
        "checkpoint_resumed": evidence["completion_after_resume"] == 1,
    }


async def stimulate_case_23(dut):
    dut.checkpoint_reset.value = 1
    dut.work_cycles.value = 6
    await _drive_before_edge(dut, start=1)
    await _drive_before_edge(dut, start=0)
    busy_before = int(dut.busy.value)
    await _drive_before_edge(dut, rst_n=0)
    busy_during = int(dut.busy.value)
    await _drive_before_edge(dut, rst_n=1, illegal_command=1)
    await _drive_before_edge(dut, illegal_command=0)
    error_before = int(dut.error.value)
    await _drive_before_edge(dut, software_ack=1)
    error_after = int(dut.error.value)
    dut.software_ack.value = 0
    completion_after_resume = 0
    for _ in range(8):
        await _idle_cycle(dut)
        completion_after_resume += int(dut.completion.value)
        if completion_after_resume:
            break
    return {
        "busy_before_reset": busy_before,
        "busy_during_reset": busy_during,
        "error_before_ack": error_before,
        "error_after_ack": error_after,
        "completion_after_resume": completion_after_resume,
        "busy_after_completion": int(dut.busy.value),
    }


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_23_checkpoint_and_error(dut):
    await _setup(dut)
    evidence = await stimulate_case_23(dut)
    assert_case_23(evidence)
    assert all(cover_case_23(evidence).values())
    _must_reject(assert_case_23, {**evidence, "busy_during_reset": 0})
    _must_reject(assert_case_23, {**evidence, "completion_after_resume": 0})


# Case 24: known GEMM and unknown masked-score operation stay isolated.
def assert_case_24(evidence):
    assert set(evidence) == {"gemm", "attention"}
    _expect_equal(evidence["gemm"])
    _expect_equal(evidence["attention"])


def cover_case_24(evidence):
    return {
        "known_gemm_checked": evidence["gemm"]["observed"] == evidence["gemm"]["expected"],
        "extension_checked": evidence["attention"]["observed"] == evidence["attention"]["expected"],
    }


async def stimulate_case_24(dut):
    dut.shape_m.value = 1
    dut.op_a.value = 3
    dut.op_b.value = -4
    dut.op_bias.value = 5
    dut.attention_q.value = 3
    dut.attention_k0.value = 2
    dut.attention_k1.value = 4
    dut.attention_v0.value = 10
    dut.attention_v1.value = -2
    dut.attention_mask0.value = 0
    dut.attention_mask1.value = 1
    await Timer(1, unit="ns")
    return {
        "gemm": {"expected": -7, "observed": _signed(dut.gemm_result)},
        "attention": {"expected": 10, "observed": _signed(dut.sparse_attention_result)},
    }


@cocotb.test(timeout_time=10000, timeout_unit="ns")
async def test_case_24_multi_operation_isolation(dut):
    await _setup(dut)
    evidence = await stimulate_case_24(dut)
    assert_case_24(evidence)
    assert all(cover_case_24(evidence).values())
    bad = {key: dict(value) for key, value in evidence.items()}
    bad["attention"]["observed"] += 1
    _must_reject(assert_case_24, bad)


# Case 25: arithmetic, protocol, and lifecycle extension evidence in one job.
def assert_case_25(evidence):
    _expect_equal(evidence["rounded"])
    assert [item["response"] for item in evidence["responses"]] == [2, 0]
    assert [item["epoch"] for item in evidence["responses"]] == [3, 3]
    assert [item["data"] for item in evidence["responses"]] == [0x101, 0x101]
    assert evidence["completion_held"] == [1, 1]
    assert evidence["completion_after_ack"] == 0


def cover_case_25(evidence):
    return {
        "rounded_nonzero": evidence["rounded"]["observed"] != 0,
        "retry_then_success": [item["response"] for item in evidence["responses"]] == [2, 0],
        "epoch_preserved": len({item["epoch"] for item in evidence["responses"]}) == 1,
        "sticky_completion": evidence["completion_held"] == [1, 1],
    }


async def stimulate_case_25(dut):
    dut.shape_m.value = 1
    dut.op_a.value = 7
    dut.op_b.value = 3
    dut.op_bias.value = 2
    dut.round_shift.value = 2
    await Timer(1, unit="ns")
    rounded = {"expected": 6, "observed": _signed(dut.rounded_result)}
    responses = [
        await _axi_extension_attempt(dut, address=0x100, epoch=3, retry=1),
        await _axi_extension_attempt(dut, address=0x100, epoch=3, retry=0),
    ]
    dut.sticky_completion.value = 1
    dut.work_cycles.value = 1
    await _drive_before_edge(dut, start=1)
    await _drive_before_edge(dut, start=0)
    while not int(dut.completion.value):
        await _idle_cycle(dut)
    held = [int(dut.completion.value)]
    await _idle_cycle(dut)
    held.append(int(dut.completion.value))
    await _drive_before_edge(dut, software_ack=1)
    after_ack = int(dut.completion.value)
    dut.software_ack.value = 0
    return {
        "rounded": rounded,
        "responses": responses,
        "completion_held": held,
        "completion_after_ack": after_ack,
    }


@cocotb.test(timeout_time=20000, timeout_unit="ns")
async def test_case_25_mixed_domains(dut):
    await _setup(dut)
    evidence = await stimulate_case_25(dut)
    assert_case_25(evidence)
    assert all(cover_case_25(evidence).values())
    bad = dict(evidence)
    bad["rounded"] = {**evidence["rounded"], "observed": evidence["rounded"]["observed"] + 1}
    _must_reject(assert_case_25, bad)
    bad_response = dict(evidence)
    bad_response["responses"] = [dict(item) for item in evidence["responses"]]
    bad_response["responses"][1]["epoch"] = 4
    _must_reject(assert_case_25, bad_response)
    _must_reject(assert_case_25, {**evidence, "completion_after_ack": 1})
