import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

from multigent.verifier_tool.coverage.runtime import contract_coverage, sample_operation
from reference.uadd8_ref import uadd8_uadd8_to_u9

COVERAGE_OBLIGATIONS = {
    "channel.in_chan.handshake_states",
    "channel.in_chan.stall_stability",
    "channel.out_chan.handshake_states",
    "channel.out_chan.stall_stability",
    "signal.rst_n.reset_behavior",
    "operation.uadd_pair.opcode",
    "operation.uadd_pair.vector_length",
    "operation.uadd_pair.operand_classes",
    "operation.uadd_pair.numeric_behavior",
    "operation.uadd_pair.predication",
    "operation.uadd_pair.fixed_opcode_add_only",
    "operation.uadd_pair.scalar_single_element_per_transaction",
    "operation.uadd_pair.no_predication_supported",
    "operation.uadd_pair.in_chan_stall",
    "operation.uadd_pair.out_chan_stall",
}


OPERATION_SAMPLING_BINDINGS = [{'operation': 'uadd_pair', 'point': 'operation.uadd_pair.opcode', 'template': 'custom', 'observer': 'observe_const_one', 'event': 'clock', 'fields': {'v': {'signal': 'in_valid'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.vector_length', 'template': 'custom', 'observer': 'observe_const_one', 'event': 'clock', 'fields': {'v': {'signal': 'in_valid'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.operand_classes', 'template': 'integer_operand', 'event': 'transfer', 'channel': 'in_chan', 'fields': {'value': {'signal': 'in_op_a'}}, 'data_type': 'u8'}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.numeric_behavior', 'template': 'custom', 'observer': 'observe_sum_class', 'event': 'transfer', 'channel': 'in_chan', 'fields': {'a': {'signal': 'in_op_a'}, 'b': {'signal': 'in_op_b'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.predication', 'template': 'custom', 'observer': 'observe_const_one', 'event': 'clock', 'fields': {'v': {'signal': 'in_valid'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.fixed_opcode_add_only', 'template': 'custom', 'observer': 'observe_const_one', 'event': 'clock', 'fields': {'v': {'signal': 'in_valid'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.scalar_single_element_per_transaction', 'template': 'custom', 'observer': 'observe_const_one', 'event': 'clock', 'fields': {'v': {'signal': 'in_valid'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.no_predication_supported', 'template': 'custom', 'observer': 'observe_const_one', 'event': 'clock', 'fields': {'v': {'signal': 'in_valid'}}}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.in_chan_stall', 'template': 'channel_stall', 'event': 'transfer', 'channel': 'in_chan'}, {'operation': 'uadd_pair', 'point': 'operation.uadd_pair.out_chan_stall', 'template': 'channel_stall', 'event': 'transfer', 'channel': 'out_chan'}]

def observe_const_one(values, state):
    return 1

def observe_sum_class(values, state):
    return int(values["a"]) + int(values["b"])

# === LLM-GENERATED OPERATION ASSERTIONS ===

async def do_reset(dut):
    dut.in_valid.value = 0
    dut.out_ready.value = 0
    dut.in_op_a.value = 0
    dut.in_op_b.value = 0
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    # LLM-GENERATED OPERATION ASSERTION [reset_state]
    assert int(dut.out_valid.value) == 0, f"reset expected out_valid=0 got {int(dut.out_valid.value)} from dut.out_valid"
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test(timeout_time=200000, timeout_unit="ns")
@contract_coverage()
async def test_rv_uadd8(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    rng = random.Random(424242)
    await do_reset(dut)

    accepted = []

    async def send_one(a, b, hold_ready_low_cycles=0):
        while True:
            await FallingEdge(dut.clk)
            dut.in_valid.value = 1
            dut.in_op_a.value = a
            dut.in_op_b.value = b
            await Timer(1, unit="ns")
            ir = int(dut.in_ready.value)
            await RisingEdge(dut.clk)
            if int(dut.rst_n.value) == 1 and ir == 1:
                dut.in_valid.value = 0
                return

    async def recv_one(stall_cycles=0):
        dut.out_ready.value = 0 if stall_cycles > 0 else 1
        stalled = stall_cycles
        while True:
            await FallingEdge(dut.clk)
            if stalled == 0:
                dut.out_ready.value = 1
            await Timer(1, unit="ns")
            ov = int(dut.out_valid.value)
            ory = int(dut.out_ready.value)
            val = int(dut.out_sum.value)
            await RisingEdge(dut.clk)
            if int(dut.rst_n.value) == 1 and ov and ory:
                return val
            if stalled > 0:
                stalled -= 1

    vectors = [((0, 0), "boundary_00"), ((255, 0), "boundary_ff00"), ((255, 255), "boundary_ffff")]
    for (a, b), label in vectors:
        exp = uadd8_uadd8_to_u9(a, b)
        await send_one(a, b)
        got = await recv_one(0)
        # LLM-GENERATED OPERATION ASSERTION [oracle_match]
        assert got == exp, f"oracle mismatch a={a} b={b} expected={exp} observed={got} dut.out_sum"
        if label == "boundary_00":
            # STIMULUS [boundary_00] targets=('operation.uadd_pair.operand_classes', 'operation.uadd_pair.numeric_behavior', 'channel.in_chan.handshake_states', 'channel.out_chan.handshake_states')
            stimulus_id = _contract_record_checked_stimulus("directed", {"a": a, "b": b}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="boundary_00")
        elif label == "boundary_ff00":
            # STIMULUS [boundary_ff00] targets=('operation.uadd_pair.operand_classes', 'operation.uadd_pair.numeric_behavior')
            stimulus_id = _contract_record_checked_stimulus("directed", {"a": a, "b": b}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="boundary_ff00")
        else:
            # STIMULUS [boundary_ffff] targets=('operation.uadd_pair.numeric_behavior', 'operation.uadd_pair.operand_classes')
            stimulus_id = _contract_record_checked_stimulus("directed", {"a": a, "b": b}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="boundary_ffff")
        sample_operation("uadd_pair", {}, "directed", stimulus_id)

    for stall, label in [(1, "one_cycle_stall"), (3, "short_stall"), (6, "long_stall")]:
        a = rng.randrange(256)
        b = rng.randrange(256)
        exp = uadd8_uadd8_to_u9(a, b)
        await send_one(a, b)
        got = await recv_one(stall)
        # LLM-GENERATED OPERATION ASSERTION [stall_oracle_match]
        assert got == exp, f"stall mismatch a={a} b={b} expected={exp} observed={got} dut.out_sum stall={stall}"
        if label == "one_cycle_stall":
            # STIMULUS [one_cycle_stall] targets=('channel.in_chan.stall_stability', 'channel.out_chan.stall_stability', 'operation.uadd_pair.in_chan_stall', 'operation.uadd_pair.out_chan_stall')
            stimulus_id = _contract_record_checked_stimulus("directed", {"a": a, "b": b, "stall": stall}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="one_cycle_stall")
        elif label == "short_stall":
            # STIMULUS [short_stall] targets=('channel.in_chan.stall_stability', 'channel.out_chan.stall_stability', 'operation.uadd_pair.in_chan_stall', 'operation.uadd_pair.out_chan_stall')
            stimulus_id = _contract_record_checked_stimulus("directed", {"a": a, "b": b, "stall": stall}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="short_stall")
        else:
            # STIMULUS [long_stall] targets=('channel.in_chan.stall_stability', 'channel.out_chan.stall_stability', 'operation.uadd_pair.in_chan_stall', 'operation.uadd_pair.out_chan_stall')
            stimulus_id = _contract_record_checked_stimulus("directed", {"a": a, "b": b, "stall": stall}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="long_stall")
        sample_operation("uadd_pair", {}, "directed", stimulus_id)

    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    # LLM-GENERATED OPERATION ASSERTION [reset_idle_check]
    assert int(dut.out_valid.value) == 0, f"reset idle expected out_valid=0 got {int(dut.out_valid.value)} dut.out_valid"
    # STIMULUS [reset_idle] targets=('signal.rst_n.reset_behavior',)
    stimulus_id = _contract_record_checked_stimulus("directed", {"reset": "idle"}, {"outputs": []}, {"outputs": []}, operations=("uadd_pair",), label="reset_idle")
    sample_operation("uadd_pair", {}, "directed", stimulus_id)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    await send_one(10, 20)
    dut.out_ready.value = 0
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    # LLM-GENERATED OPERATION ASSERTION [reset_pending_check]
    assert int(dut.out_valid.value) == 0, f"reset pending expected out_valid=0 got {int(dut.out_valid.value)} dut.out_valid"
    # STIMULUS [reset_during_pending] targets=('signal.rst_n.reset_behavior', 'channel.out_chan.handshake_states')
    stimulus_id = _contract_record_checked_stimulus("directed", {"reset": "during_pending"}, {"outputs": []}, {"outputs": []}, operations=("uadd_pair",), label="reset_during_pending")
    sample_operation("uadd_pair", {}, "directed", stimulus_id)
    dut.rst_n.value = 1
    dut.out_ready.value = 1
    await RisingEdge(dut.clk)

    for i in range(100):
        a = rng.randrange(256)
        b = rng.randrange(256)
        exp = uadd8_uadd8_to_u9(a, b)
        await send_one(a, b)
        got = await recv_one(rng.randrange(0, 4))
        # LLM-GENERATED OPERATION ASSERTION [random_oracle_match]
        assert got == exp, f"random mismatch seed=424242 idx={i} a={a} b={b} expected={exp} observed={got} dut.out_sum"
        # STIMULUS [randomized_100] targets=('operation.uadd_pair.opcode', 'operation.uadd_pair.vector_length', 'operation.uadd_pair.predication', 'operation.uadd_pair.fixed_opcode_add_only', 'operation.uadd_pair.scalar_single_element_per_transaction', 'operation.uadd_pair.no_predication_supported', 'channel.in_chan.handshake_states', 'channel.out_chan.handshake_states')
        stimulus_id = _contract_record_checked_stimulus("randomized", {"a": a, "b": b, "idx": i}, {"accepted_inputs": [[a, b]], "outputs": [exp]}, {"accepted_inputs": [[a, b]], "outputs": [got]}, operations=("uadd_pair",), label="randomized_100")
        sample_operation("uadd_pair", {}, "randomized", stimulus_id)

# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ===
# This literal and the following comments are emitted by my_v.
# The Verifier chooses semantic label-to-target mappings; code owns syntax.
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{'label': 'boundary_00', 'targets': ['operation.uadd_pair.operand_classes', 'operation.uadd_pair.numeric_behavior', 'channel.in_chan.handshake_states', 'channel.out_chan.handshake_states']}, {'label': 'boundary_ff00', 'targets': ['operation.uadd_pair.operand_classes', 'operation.uadd_pair.numeric_behavior']}, {'label': 'boundary_ffff', 'targets': ['operation.uadd_pair.numeric_behavior', 'operation.uadd_pair.operand_classes']}, {'label': 'one_cycle_stall', 'targets': ['channel.in_chan.stall_stability', 'channel.out_chan.stall_stability', 'operation.uadd_pair.in_chan_stall', 'operation.uadd_pair.out_chan_stall']}, {'label': 'short_stall', 'targets': ['channel.in_chan.stall_stability', 'channel.out_chan.stall_stability', 'operation.uadd_pair.in_chan_stall', 'operation.uadd_pair.out_chan_stall']}, {'label': 'long_stall', 'targets': ['channel.in_chan.stall_stability', 'channel.out_chan.stall_stability', 'operation.uadd_pair.in_chan_stall', 'operation.uadd_pair.out_chan_stall']}, {'label': 'reset_idle', 'targets': ['signal.rst_n.reset_behavior']}, {'label': 'reset_during_pending', 'targets': ['signal.rst_n.reset_behavior', 'channel.out_chan.handshake_states']}, {'label': 'randomized_100', 'targets': ['operation.uadd_pair.opcode', 'operation.uadd_pair.vector_length', 'operation.uadd_pair.predication', 'operation.uadd_pair.fixed_opcode_add_only', 'operation.uadd_pair.scalar_single_element_per_transaction', 'operation.uadd_pair.no_predication_supported', 'channel.in_chan.handshake_states', 'channel.out_chan.handshake_states']}]
# === END PIPELINE-GENERATED VERIFIER ANNOTATIONS ===

# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ===
# This block is emitted by my_v from the frozen interface contract.
# It is not authored or repaired by the LLM.
from multigent.verifier_tool.coverage.runtime import (
    capture_contract_snapshot,
    observe_contract_reset_snapshot,
    sample_contract_snapshot,
    normalize_verification_value as _contract_normalize_verification_value,
    record_stimulus as _contract_runtime_record_stimulus,
)
from cocotb.triggers import Edge, ReadOnly

CONTRACT_SIGNAL_NAMES = ('clk', 'rst_n', 'in_valid', 'in_ready', 'in_op_a', 'in_op_b', 'out_valid', 'out_ready', 'out_sum')
CONTRACT_PROTOCOL_ASSERTION_FEATURES = ('channel.in_chan.stall_stability', 'channel.out_chan.stall_stability')
CONTRACT_OPERATION_ASSERTION_FEATURES = {'uadd_pair': ('operation.uadd_pair.opcode', 'operation.uadd_pair.vector_length', 'operation.uadd_pair.operand_classes', 'operation.uadd_pair.numeric_behavior', 'operation.uadd_pair.predication')}
_CONTRACT_PROTOCOL_STATE = {}

def _contract_record_checked_stimulus(stimulus_kind, stimulus, expected, observed, *, operations, label):
    """Apply taxonomy-owned assertions for catalog operation features."""
    expected_value = _contract_normalize_verification_value(expected, 'expected')
    observed_value = _contract_normalize_verification_value(observed, 'observed')
    if 'uadd_pair' in operations:
        # CATALOG OPERATION [uadd_pair]
        # OPERATION ASSERTION [operation.uadd_pair.opcode]
        assert observed_value == expected_value, (
            'taxonomy-owned operation assertion failed; feature=operation.uadd_pair.opcode; '
            + 'label=' + repr(label) + '; expected=' + repr(expected_value)
            + '; observed=' + repr(observed_value)
        )
        # OPERATION ASSERTION [operation.uadd_pair.vector_length]
        assert observed_value == expected_value, (
            'taxonomy-owned operation assertion failed; feature=operation.uadd_pair.vector_length; '
            + 'label=' + repr(label) + '; expected=' + repr(expected_value)
            + '; observed=' + repr(observed_value)
        )
        # OPERATION ASSERTION [operation.uadd_pair.operand_classes]
        assert observed_value == expected_value, (
            'taxonomy-owned operation assertion failed; feature=operation.uadd_pair.operand_classes; '
            + 'label=' + repr(label) + '; expected=' + repr(expected_value)
            + '; observed=' + repr(observed_value)
        )
        # OPERATION ASSERTION [operation.uadd_pair.numeric_behavior]
        assert observed_value == expected_value, (
            'taxonomy-owned operation assertion failed; feature=operation.uadd_pair.numeric_behavior; '
            + 'label=' + repr(label) + '; expected=' + repr(expected_value)
            + '; observed=' + repr(observed_value)
        )
        # OPERATION ASSERTION [operation.uadd_pair.predication]
        assert observed_value == expected_value, (
            'taxonomy-owned operation assertion failed; feature=operation.uadd_pair.predication; '
            + 'label=' + repr(label) + '; expected=' + repr(expected_value)
            + '; observed=' + repr(observed_value)
        )
    return _contract_runtime_record_stimulus(
        stimulus_kind, stimulus, expected_value, label=label
    )

def _check_contract_protocol_assertions(snapshot):
    """Run protocol assertions and return completed temporal observations."""
    completed_stalls = {}
    if int(bool(snapshot['rst_n'])) == 0:
        _CONTRACT_PROTOCOL_STATE.clear()
        return completed_stalls

    # PROTOCOL ASSERTION [channel.in_chan.stall_stability]
    _p0_valid = int(bool(snapshot['in_valid']))
    _p0_ready = int(bool(snapshot['in_ready']))
    _p0_content = tuple(snapshot[name] for name in ('in_op_a', 'in_op_b'))
    _p0_previous = _CONTRACT_PROTOCOL_STATE.get('channel.in_chan.stall_stability')
    if _p0_previous is not None:
        assert _p0_valid == 1, (
            "protocol valid was withdrawn before stalled transfer completed; feature=channel.in_chan.stall_stability; related_signals=('in_valid', 'in_ready', 'in_op_a', 'in_op_b'); observed="
            + repr({name: snapshot[name] for name in ('in_valid', 'in_ready', 'in_op_a', 'in_op_b')})
        )
        assert _p0_content == _p0_previous['content'], (
            "producer-owned content changed during stall or release; feature=channel.in_chan.stall_stability; related_signals=('in_valid', 'in_ready', 'in_op_a', 'in_op_b'); previous="
            + repr(_p0_previous['content']) + '; observed='
            + repr(_p0_content)
        )
    if _p0_valid and not _p0_ready:
        if _p0_previous is None:
            _CONTRACT_PROTOCOL_STATE['channel.in_chan.stall_stability'] = {
                'content': _p0_content, 'length': 1
            }
        else:
            _p0_previous['length'] += 1
    else:
        if _p0_previous is not None:
            completed_stalls['channel.in_chan.stall_stability'] = _p0_previous['length']
        _CONTRACT_PROTOCOL_STATE.pop('channel.in_chan.stall_stability', None)

    # PROTOCOL ASSERTION [channel.out_chan.stall_stability]
    _p1_valid = int(bool(snapshot['out_valid']))
    _p1_ready = int(bool(snapshot['out_ready']))
    _p1_content = tuple(snapshot[name] for name in ('out_sum',))
    _p1_previous = _CONTRACT_PROTOCOL_STATE.get('channel.out_chan.stall_stability')
    if _p1_previous is not None:
        assert _p1_valid == 1, (
            "protocol valid was withdrawn before stalled transfer completed; feature=channel.out_chan.stall_stability; related_signals=('out_valid', 'out_ready', 'out_sum'); observed="
            + repr({name: snapshot[name] for name in ('out_valid', 'out_ready', 'out_sum')})
        )
        assert _p1_content == _p1_previous['content'], (
            "producer-owned content changed during stall or release; feature=channel.out_chan.stall_stability; related_signals=('out_valid', 'out_ready', 'out_sum'); previous="
            + repr(_p1_previous['content']) + '; observed='
            + repr(_p1_content)
        )
    if _p1_valid and not _p1_ready:
        if _p1_previous is None:
            _CONTRACT_PROTOCOL_STATE['channel.out_chan.stall_stability'] = {
                'content': _p1_content, 'length': 1
            }
        else:
            _p1_previous['length'] += 1
    else:
        if _p1_previous is not None:
            completed_stalls['channel.out_chan.stall_stability'] = _p1_previous['length']
        _CONTRACT_PROTOCOL_STATE.pop('channel.out_chan.stall_stability', None)
    return completed_stalls

async def _contract_generated_monitor(dut):
    """Observe the interface once and share it with assertions and coverage."""
    clock = getattr(dut, 'clk')
    while True:
        await Edge(clock)
        await ReadOnly()
        if int(clock.value) != 0:
            reset_snapshot = capture_contract_snapshot(dut, ('rst_n',))
            if reset_snapshot:
                observe_contract_reset_snapshot(
                    reset_snapshot, _check_contract_protocol_assertions
                )
            continue
        snapshot = capture_contract_snapshot(dut, CONTRACT_SIGNAL_NAMES)
        sample_contract_snapshot(snapshot, _check_contract_protocol_assertions)

# === END CONTRACT-GENERATED PROTOCOL MONITOR ===
