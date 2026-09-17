import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from multigent.verifier_tool.coverage.runtime import contract_coverage, sample_operation
from reference.adder_model import add, sanity

SEED = 21843
COVERAGE_OBLIGATIONS = {
    'channel.input_pair.handshake_states',
    'channel.input_pair.stall_stability',
    'channel.output_sum.handshake_states',
    'channel.output_sum.stall_stability',
    'signal.rst_n.reset_behavior',
    'operation.add.operand_a',
    'operation.add.operand_b',
    'operation.add.exact_widened_sum',
    'operation.add.carry_boundary',
    'operation.add.single_entry_elastic_output',
    'operation.add.simultaneous_consume_replace',
    'operation.add.reset_abort',
}
OPERATION_SAMPLING_BINDINGS = [{'operation': 'add', 'point': 'operation.add.operand_a', 'template': 'integer_operand', 'event': 'transfer', 'channel': 'input_pair', 'fields': {'value': {'signal': 'in_a'}}, 'data_type': 'uint8'}, {'operation': 'add', 'point': 'operation.add.operand_b', 'template': 'integer_operand', 'event': 'transfer', 'channel': 'input_pair', 'fields': {'value': {'signal': 'in_b'}}, 'data_type': 'uint8'}, {'operation': 'add', 'point': 'operation.add.exact_widened_sum', 'template': 'custom', 'observer': 'observe_sum', 'event': 'transfer', 'channel': 'output_sum', 'fields': {'sum': {'signal': 'out_sum'}}}, {'operation': 'add', 'point': 'operation.add.carry_boundary', 'template': 'custom', 'observer': 'observe_carry', 'event': 'transfer', 'channel': 'input_pair', 'fields': {'a': {'signal': 'in_a'}, 'b': {'signal': 'in_b'}}}, {'operation': 'add', 'point': 'operation.add.single_entry_elastic_output', 'template': 'custom', 'observer': 'observe_slot', 'event': 'clock', 'fields': {'reset': {'signal': 'rst_n'}, 'valid': {'signal': 'out_valid'}, 'ready': {'signal': 'out_ready'}}}, {'operation': 'add', 'point': 'operation.add.simultaneous_consume_replace', 'template': 'custom', 'observer': 'observe_replace', 'event': 'transfer', 'channel': 'input_pair', 'fields': {'valid': {'signal': 'out_valid'}, 'ready': {'signal': 'out_ready'}}}, {'operation': 'add', 'point': 'operation.add.reset_abort', 'template': 'custom', 'observer': 'observe_reset', 'event': 'clock', 'fields': {'reset': {'signal': 'rst_n'}, 'valid': {'signal': 'out_valid'}, 'sum': {'signal': 'out_sum'}}}]


def observe_sum(values, state):
    return int(values['sum'])


def observe_carry(values, state):
    return int(values['a']) + int(values['b'])


def observe_slot(values, state):
    if not values['reset']:
        return None
    if not values['valid']:
        return 0
    return 2 if values['ready'] else 1


def observe_replace(values, state):
    return int(bool(values['valid'] and values['ready']))


def observe_reset(values, state):
    if not values['reset']:
        return int(bool(values['valid']))
    return None


# === LLM-GENERATED OPERATION ASSERTIONS ===
class Checker:
    def __init__(self, dut):
        self.dut = dut
        self.pending = None
        self.data = 0
        self.initialized = False
        self.cycle = 0
        self.accepted = 0
        self.consumed = 0
        self.aborted = 0

    async def step(self, pair=None, ready=1, reset=1, kind='directed', exhaustive=False):
        dut = self.dut
        await FallingEdge(dut.clk)
        dut.rst_n.value = reset
        dut.in_valid.value = int(pair is not None)
        a, b = pair if pair is not None else (self.cycle % 256, (255-self.cycle) % 256)
        dut.in_a.value = a
        dut.in_b.value = b
        dut.out_ready.value = ready
        await Timer(1, unit='ns')
        r = int(dut.rst_n.value)
        iv = int(dut.in_valid.value)
        ir = int(dut.in_ready.value)
        ia = int(dut.in_a.value)
        ib = int(dut.in_b.value)
        ov = int(dut.out_valid.value)
        ore = int(dut.out_ready.value)
        value = int(dut.out_sum.value)
        context = f'seed={SEED} cycle={self.cycle} submitted={pair} rst_n={r} in_valid/ready={iv}/{ir} out_valid/ready={ov}/{ore} out_sum={value}'
        expected_ready = int(bool(r and (not ov or ore)))
        # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
        assert ir == expected_ready, f'{context}: in_ready expected={expected_ready} observed={ir}'
        if self.initialized:
            # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
            assert ov == int(self.pending is not None), f'{context}: out_valid expected={int(self.pending is not None)} observed={ov}'
            # LLM-GENERATED OPERATION ASSERTION [exact_widened_sum]
            assert value == self.data, f'{context}: pre-edge out_sum expected={self.data} observed={value}; includes retention and synchronous reset'
        take_in = bool(r and iv and ir)
        take_out = bool(r and ov and ore)
        old = self.pending
        await RisingEdge(dut.clk)
        if not r:
            self.pending = None
            self.data = 0
            self.initialized = True
            self.aborted += int(old is not None)
        else:
            if take_out:
                # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
                assert old is not None, f'{context}: unsolicited out_sum transfer expected pending input, observed none'
                self.pending = None
                self.consumed += 1
            if take_in:
                # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
                assert self.pending is None, f'{context}: input acceptance expected empty or consumed slot, observed pending={self.pending}'
                self.pending = {'submitted': [a, b], 'accepted': [ia, ib],
                                'expected': add(a, b), 'kind': kind,
                                'exhaustive': exhaustive, 'edge': self.cycle}
                self.data = add(a, b)
                self.accepted += 1
        await Timer(1, unit='ns')
        post_valid = int(dut.out_valid.value)
        post_sum = int(dut.out_sum.value)
        # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
        assert post_valid == int(self.pending is not None), f'{context}: post-edge out_valid expected={int(self.pending is not None)} observed={post_valid}'
        # LLM-GENERATED OPERATION ASSERTION [exact_widened_sum]
        assert post_sum == self.data, f'{context}: post-edge out_sum expected={self.data} observed={post_sum}'
        # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
        assert self.accepted-self.consumed-self.aborted == post_valid, f'{context}: occupancy expected={self.accepted-self.consumed-self.aborted} observed out_valid={post_valid}'
        if take_out:
            # LLM-GENERATED OPERATION ASSERTION [exact_widened_sum]
            assert value == old['expected'], f'{context}: accepted in_a/in_b={old["accepted"]} expected sum={old["expected"]} observed out_sum={value}'
            # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
            assert self.cycle > old['edge'], f'{context}: expected registered latency after input edge={old["edge"]}, observed output edge={self.cycle}'
            submitted = {'in_a': old['submitted'][0], 'in_b': old['submitted'][1]}
            expected = {'inputs': [old['submitted']], 'outputs': [old['expected']], 'aborted': 0, 'reset_edges': 0}
            observed = {'inputs': [old['accepted']], 'outputs': [value], 'aborted': 0, 'reset_edges': 0}
            if old['kind'] == 'randomized':
                # STIMULUS [randomized_pairs] targets=('operation.add.operand_a', 'operation.add.operand_b')
                stimulus_id = _contract_record_checked_stimulus('randomized', submitted, expected, observed, operations=('add',), label='randomized_pairs')
                sample_operation('add', {}, 'randomized', stimulus_id)
            elif old['exhaustive']:
                # STIMULUS [exhaustive_pairs] targets=('operation.add.operand_a', 'operation.add.operand_b', 'operation.add.exact_widened_sum', 'operation.add.carry_boundary')
                stimulus_id = _contract_record_checked_stimulus('directed', submitted, expected, observed, operations=('add',), label='exhaustive_pairs')
                sample_operation('add', {}, 'directed', stimulus_id)
            else:
                # STIMULUS [directed_traffic] targets=('channel.input_pair.handshake_states', 'channel.input_pair.stall_stability', 'channel.output_sum.handshake_states', 'channel.output_sum.stall_stability', 'operation.add.operand_a', 'operation.add.operand_b', 'operation.add.exact_widened_sum', 'operation.add.carry_boundary', 'operation.add.single_entry_elastic_output', 'operation.add.simultaneous_consume_replace')
                stimulus_id = _contract_record_checked_stimulus('directed', submitted, expected, observed, operations=('add',), label='directed_traffic')
                sample_operation('add', {}, 'directed', stimulus_id)
        if not r:
            expected_inputs = [] if old is None else [old['submitted']]
            observed_inputs = [] if old is None else [old['accepted']]
            submitted = {'pending_inputs': expected_inputs, 'reset': 0,
                         'presented_in_valid': int(pair is not None), 'in_a': a, 'in_b': b, 'out_ready': ready}
            expected = {'inputs': expected_inputs, 'outputs': [], 'aborted': len(expected_inputs),
                        'reset_edges': 1, 'out_valid': 0, 'out_sum': 0, 'in_ready': 0,
                        'reset_input_transfers': 0, 'reset_output_transfers': 0}
            observed = {'inputs': observed_inputs, 'outputs': [], 'aborted': int(old is not None and post_valid == 0),
                        'reset_edges': int(r == 0), 'out_valid': post_valid, 'out_sum': post_sum, 'in_ready': ir,
                        'reset_input_transfers': int(take_in), 'reset_output_transfers': int(take_out)}
            # STIMULUS [reset_scenarios] targets=('signal.rst_n.reset_behavior', 'operation.add.reset_abort')
            stimulus_id = _contract_record_checked_stimulus('directed', submitted, expected, observed, operations=('add',), label='reset_scenarios')
            sample_operation('add', {}, 'directed', stimulus_id)
        self.cycle += 1
        return take_in


@cocotb.test(timeout_time=2, timeout_unit='ms')
@contract_coverage()
async def exhaustive_and_protocol(dut):
    sanity()
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.in_a.value = 0
    dut.in_b.value = 0
    dut.out_ready.value = 0
    clock_task = cocotb.start_soon(Clock(dut.clk, 10, unit='ns').start())
    checker = Checker(dut)
    try:
        await checker.step(reset=0, ready=0)
        await checker.step(reset=0, ready=1)
        await checker.step(ready=0)
        await checker.step(ready=1)
        for pair in [(0, 0), (255, 0), (255, 1), (255, 255), (128, 128)]:
            await checker.step(pair)
        await checker.step()
        for duration in (1, 3, 6):
            await checker.step((255, duration), ready=0)
            for _ in range(duration):
                await checker.step((duration, 0), ready=0)
            await checker.step((duration, 0), ready=1)
            await checker.step()
        await checker.step((7, 9), ready=0)
        await checker.step(ready=0)
        await checker.step()
        await checker.step()
        # Empty reset with an otherwise eligible input.
        await checker.step((11, 13), reset=0)
        await checker.step()
        # Reset withdraws a held source and aborts a stalled output.
        await checker.step((200, 55), ready=0)
        await checker.step((17, 19), ready=0)
        await checker.step(reset=0, ready=0)
        for _ in range(3):
            await checker.step()
        # Without reset this edge would consume and replace.
        await checker.step((128, 129), ready=0)
        await checker.step((255, 255), ready=1, reset=0)
        for _ in range(3):
            await checker.step()
        await checker.step((1, 2))
        await checker.step()
        # All pairs, continuously valid: every edge after fill consumes and replaces.
        for a in range(256):
            for b in range(256):
                accepted = await checker.step((a, b), exhaustive=True)
                # LLM-GENERATED OPERATION ASSERTION [simultaneous_consume_replace]
                assert accepted, f'seed={SEED} exhaustive in_a={a} in_b={b}: out_ready=1 expected input acceptance, observed in_ready=0'
        await checker.step()
        rng = random.Random(SEED)
        pair = None
        count = 0
        blocked = 0
        for _ in range(3000):
            if pair is None and count < 100 and rng.randrange(4) != 0:
                pair = (rng.randrange(256), rng.randrange(256))
            ready = int(blocked >= 6 or rng.randrange(3) != 0)
            blocked = 0 if ready else blocked + 1
            accepted = await checker.step(pair, ready=ready, kind='randomized')
            if accepted:
                count += 1
                pair = None
            if count == 100 and checker.pending is None:
                break
        # LLM-GENERATED OPERATION ASSERTION [single_entry_elastic_output]
        assert count == 100 and checker.pending is None, f'seed={SEED}: expected 100 completed randomized pairs, observed accepted={count} pending={checker.pending}; DUT in_ready/out_valid'
        # Continue rejecting unsolicited outputs through idle and another job boundary.
        for _ in range(8):
            await checker.step()
        await checker.step((255, 255))
        await checker.step()
        for _ in range(8):
            await checker.step()
    finally:
        clock_task.cancel()

# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ===
# This literal and the following comments are emitted by my_v.
# The Verifier chooses semantic label-to-target mappings; code owns syntax.
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{'label': 'directed_traffic', 'targets': ['channel.input_pair.handshake_states', 'channel.input_pair.stall_stability', 'channel.output_sum.handshake_states', 'channel.output_sum.stall_stability', 'operation.add.operand_a', 'operation.add.operand_b', 'operation.add.exact_widened_sum', 'operation.add.carry_boundary', 'operation.add.single_entry_elastic_output', 'operation.add.simultaneous_consume_replace']}, {'label': 'exhaustive_pairs', 'targets': ['operation.add.operand_a', 'operation.add.operand_b', 'operation.add.exact_widened_sum', 'operation.add.carry_boundary']}, {'label': 'randomized_pairs', 'targets': ['operation.add.operand_a', 'operation.add.operand_b']}, {'label': 'reset_scenarios', 'targets': ['signal.rst_n.reset_behavior', 'operation.add.reset_abort']}]
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

CONTRACT_SIGNAL_NAMES = ('clk', 'rst_n', 'in_valid', 'in_ready', 'in_a', 'in_b', 'out_valid', 'out_ready', 'out_sum')
CONTRACT_PROTOCOL_ASSERTION_FEATURES = ('channel.input_pair.stall_stability', 'channel.output_sum.stall_stability')
CONTRACT_OPERATION_ASSERTION_FEATURES = {}
_CONTRACT_PROTOCOL_STATE = {}

def _contract_record_checked_stimulus(stimulus_kind, stimulus, expected, observed, *, operations, label):
    """Apply taxonomy-owned assertions for catalog operation features."""
    expected_value = _contract_normalize_verification_value(expected, 'expected')
    observed_value = _contract_normalize_verification_value(observed, 'observed')
    return _contract_runtime_record_stimulus(
        stimulus_kind, stimulus, expected_value, label=label
    )

def _check_contract_protocol_assertions(snapshot):
    """Run protocol assertions and return completed temporal observations."""
    completed_stalls = {}
    if int(bool(snapshot['rst_n'])) == 0:
        _CONTRACT_PROTOCOL_STATE.clear()
        return completed_stalls

    # PROTOCOL ASSERTION [channel.input_pair.stall_stability]
    _p0_valid = int(bool(snapshot['in_valid']))
    _p0_ready = int(bool(snapshot['in_ready']))
    _p0_content = tuple(snapshot[name] for name in ('in_a', 'in_b'))
    _p0_previous = _CONTRACT_PROTOCOL_STATE.get('channel.input_pair.stall_stability')
    if _p0_previous is not None:
        assert _p0_valid == 1, (
            "protocol valid was withdrawn before stalled transfer completed; feature=channel.input_pair.stall_stability; related_signals=('in_valid', 'in_ready', 'in_a', 'in_b'); observed="
            + repr({name: snapshot[name] for name in ('in_valid', 'in_ready', 'in_a', 'in_b')})
        )
        assert _p0_content == _p0_previous['content'], (
            "producer-owned content changed during stall or release; feature=channel.input_pair.stall_stability; related_signals=('in_valid', 'in_ready', 'in_a', 'in_b'); previous="
            + repr(_p0_previous['content']) + '; observed='
            + repr(_p0_content)
        )
    if _p0_valid and not _p0_ready:
        if _p0_previous is None:
            _CONTRACT_PROTOCOL_STATE['channel.input_pair.stall_stability'] = {
                'content': _p0_content, 'length': 1
            }
        else:
            _p0_previous['length'] += 1
    else:
        if _p0_previous is not None:
            completed_stalls['channel.input_pair.stall_stability'] = _p0_previous['length']
        _CONTRACT_PROTOCOL_STATE.pop('channel.input_pair.stall_stability', None)

    # PROTOCOL ASSERTION [channel.output_sum.stall_stability]
    _p1_valid = int(bool(snapshot['out_valid']))
    _p1_ready = int(bool(snapshot['out_ready']))
    _p1_content = tuple(snapshot[name] for name in ('out_sum',))
    _p1_previous = _CONTRACT_PROTOCOL_STATE.get('channel.output_sum.stall_stability')
    if _p1_previous is not None:
        assert _p1_valid == 1, (
            "protocol valid was withdrawn before stalled transfer completed; feature=channel.output_sum.stall_stability; related_signals=('out_valid', 'out_ready', 'out_sum'); observed="
            + repr({name: snapshot[name] for name in ('out_valid', 'out_ready', 'out_sum')})
        )
        assert _p1_content == _p1_previous['content'], (
            "producer-owned content changed during stall or release; feature=channel.output_sum.stall_stability; related_signals=('out_valid', 'out_ready', 'out_sum'); previous="
            + repr(_p1_previous['content']) + '; observed='
            + repr(_p1_content)
        )
    if _p1_valid and not _p1_ready:
        if _p1_previous is None:
            _CONTRACT_PROTOCOL_STATE['channel.output_sum.stall_stability'] = {
                'content': _p1_content, 'length': 1
            }
        else:
            _p1_previous['length'] += 1
    else:
        if _p1_previous is not None:
            completed_stalls['channel.output_sum.stall_stability'] = _p1_previous['length']
        _CONTRACT_PROTOCOL_STATE.pop('channel.output_sum.stall_stability', None)
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
