import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from multigent.verifier_tool.coverage.runtime import contract_coverage, sample_operation
from reference.adder_model import add_unsigned, sanity_check

COVERAGE_OBLIGATIONS = {
    "channel.input_operands.handshake_states",
    "channel.input_operands.stall_stability",
    "channel.output_sum.handshake_states",
    "channel.output_sum.stall_stability",
    "signal.rst_n.reset_behavior",
    "operation.add_unsigned.accepted_sum",
    "operation.add_unsigned.transferred_sum",
    "operation.add_unsigned.registered_latency",
    "operation.add_unsigned.output_buffer_stall",
}



def observe_accepted_sum(values, state):
    if not int(values["rst_n"]):
        return None
    if int(values["in_valid"]) and int(values["in_ready"]):
        p = int(values["in_payload"])
        return (p & 255) + ((p >> 8) & 255)
    return None


def observe_transferred_sum(values, state):
    if int(values["rst_n"]) and int(values["out_valid"]) and int(values["out_ready"]):
        return int(values["out_payload"])
    return None


def observe_registered_latency(values, state):
    if not int(values["rst_n"]):
        state.clear()
        return None
    result = None
    pending = bool(state.get("pending", False))
    age = int(state.get("age", 0))
    if pending:
        age += 1
        if int(values["out_valid"]) and int(values["out_ready"]):
            result = age
            pending = False
    if int(values["in_valid"]) and int(values["in_ready"]):
        pending = True
        age = 0
    state["pending"] = pending
    state["age"] = age
    return result


OPERATION_SAMPLING_BINDINGS = [{'operation': 'add_unsigned', 'point': 'operation.add_unsigned.accepted_sum', 'template': 'custom', 'observer': 'observe_accepted_sum', 'event': 'clock', 'fields': {'rst_n': {'signal': 'rst_n'}, 'in_valid': {'signal': 'in_valid'}, 'in_ready': {'signal': 'in_ready'}, 'in_payload': {'signal': 'in_payload'}}}, {'operation': 'add_unsigned', 'point': 'operation.add_unsigned.transferred_sum', 'template': 'custom', 'observer': 'observe_transferred_sum', 'event': 'clock', 'fields': {'rst_n': {'signal': 'rst_n'}, 'out_valid': {'signal': 'out_valid'}, 'out_ready': {'signal': 'out_ready'}, 'out_payload': {'signal': 'out_payload'}}}, {'operation': 'add_unsigned', 'point': 'operation.add_unsigned.registered_latency', 'template': 'custom', 'observer': 'observe_registered_latency', 'event': 'clock', 'fields': {'rst_n': {'signal': 'rst_n'}, 'in_valid': {'signal': 'in_valid'}, 'in_ready': {'signal': 'in_ready'}, 'out_valid': {'signal': 'out_valid'}, 'out_ready': {'signal': 'out_ready'}}}, {'operation': 'add_unsigned', 'point': 'operation.add_unsigned.output_buffer_stall', 'template': 'channel_stall', 'event': 'transfer', 'channel': 'output_sum', 'fields': {}}]

# === LLM-GENERATED OPERATION ASSERTIONS ===


def check(condition, message):
    # LLM-GENERATED OPERATION ASSERTION [external_contract_checker]
    assert condition, message


class Bench:
    def __init__(self, dut):
        self.dut = dut
        self.queue = []
        self.cycle_index = 0
        self.previous_output_stall = None

    async def cycle(self, **drives):
        await FallingEdge(self.dut.clk)
        for name, value in drives.items():
            getattr(self.dut, name).value = value
        await Timer(1, unit="ns")
        pre = {name: int(getattr(self.dut, name).value) for name in
               ("rst_n", "in_valid", "in_ready", "in_payload", "out_valid", "out_ready", "out_payload")}
        expected_ready = int(bool(pre["rst_n"] and (not pre["out_valid"] or pre["out_ready"])))
        check(pre["in_ready"] == expected_ready,
              f"cycle={self.cycle_index} in_ready expected={expected_ready} observed={pre['in_ready']} signals={pre}")
        if self.previous_output_stall is not None and pre["rst_n"]:
            held_valid, held_payload = self.previous_output_stall
            check(pre["out_valid"] == held_valid and pre["out_payload"] == held_payload,
                  f"cycle={self.cycle_index} stalled output changed; held_valid={held_valid} held_payload={held_payload} observed={pre}")
        self.previous_output_stall = (pre["out_valid"], pre["out_payload"]) if pre["rst_n"] and pre["out_valid"] and not pre["out_ready"] else None
        await RisingEdge(self.dut.clk)
        await Timer(1, unit="ns")
        event = {"input": None, "output": None, "reset": not bool(pre["rst_n"]), "cycle": self.cycle_index}
        if not pre["rst_n"]:
            self.queue.clear()
            self.previous_output_stall = None
            check(int(self.dut.out_valid.value) == 0 and int(self.dut.out_payload.value) == 0,
                  f"reset edge failed to clear out_valid/out_payload: valid={int(self.dut.out_valid.value)} payload={int(self.dut.out_payload.value)}")
        else:
            if pre["out_valid"] and pre["out_ready"]:
                check(bool(self.queue), f"cycle={self.cycle_index} unsolicited output transfer payload={pre['out_payload']}")
                expected = self.queue.pop(0)
                check(pre["out_payload"] == expected["sum"],
                      f"cycle={self.cycle_index} output mismatch expected={expected} observed_payload={pre['out_payload']}")
                event["output"] = {"sum": pre["out_payload"], "accepted_cycle": expected["cycle"]}
            if pre["in_valid"] and pre["in_ready"]:
                a = pre["in_payload"] & 255
                b = (pre["in_payload"] >> 8) & 255
                self.queue.append({"sum": add_unsigned(a, b), "cycle": self.cycle_index})
                event["input"] = {"operand_a": a, "operand_b": b}
        self.cycle_index += 1
        return event

    async def single(self, a, b, source_delay=0, ready_pattern=None, require_latency_one=False):
        accepted = []
        outputs = []
        for _ in range(source_delay):
            event = await self.cycle(in_valid=0)
            check(event["input"] is None, f"source-idle cycle unexpectedly accepted input: {event}")
        payload = (b << 8) | a
        while not accepted:
            event = await self.cycle(in_valid=1, in_payload=payload)
            if event["input"] is not None:
                accepted.append(event["input"])
        index = 0
        while not outputs:
            ready = 1 if ready_pattern is None else ready_pattern[min(index, len(ready_pattern) - 1)]
            event = await self.cycle(in_valid=0, out_ready=ready)
            if event["output"] is not None:
                outputs.append(event["output"])
            index += 1
        check(accepted == [{"operand_a": a, "operand_b": b}], f"input accounting expected={[a,b]} observed={accepted}")
        check([x["sum"] for x in outputs] == [add_unsigned(a, b)], f"output accounting expected={add_unsigned(a,b)} observed={outputs}")
        if require_latency_one:
            check(outputs[0]["accepted_cycle"] + 1 == event["cycle"], f"one-cycle latency failed input_cycle={outputs[0]['accepted_cycle']} output_cycle={event['cycle']}")
        guard = await self.cycle(in_valid=0, out_ready=1)
        check(guard["output"] is None, f"extra output after completed job: {guard}")
        return {"accepted_inputs": accepted, "outputs": [x["sum"] for x in outputs], "aborted": False, "reset_edges": 0}

    async def stall_pair(self, first, second, stall_cycles):
        a1, b1 = first
        a2, b2 = second
        accepted = []
        outputs = []
        event = await self.cycle(in_valid=1, in_payload=(b1 << 8) | a1, out_ready=1)
        if event["input"] is not None:
            accepted.append(event["input"])
        for _ in range(stall_cycles):
            event = await self.cycle(in_valid=1, in_payload=(b2 << 8) | a2, out_ready=0)
            check(event["input"] is None, f"input transferred while output stalled: event={event}")
        event = await self.cycle(in_valid=1, in_payload=(b2 << 8) | a2, out_ready=1)
        if event["output"] is not None:
            outputs.append(event["output"])
        if event["input"] is not None:
            accepted.append(event["input"])
        check(event["output"] is not None and event["input"] is not None,
              f"same-edge consume-and-replace missing: event={event} stall_cycles={stall_cycles}")
        event = await self.cycle(in_valid=0, out_ready=1)
        if event["output"] is not None:
            outputs.append(event["output"])
        expected_inputs = [{"operand_a": a1, "operand_b": b1}, {"operand_a": a2, "operand_b": b2}]
        expected_outputs = [add_unsigned(a1, b1), add_unsigned(a2, b2)]
        check(accepted == expected_inputs, f"pair input accounting expected={expected_inputs} observed={accepted}")
        check([x["sum"] for x in outputs] == expected_outputs, f"pair output order expected={expected_outputs} observed={outputs}")
        guard = await self.cycle(in_valid=0, out_ready=1)
        check(guard["output"] is None, f"extra pair output: {guard}")
        return {"accepted_inputs": accepted, "outputs": [x["sum"] for x in outputs], "aborted": False, "reset_edges": 0}

    async def reset_abort(self, a, b, stalled):
        event = await self.cycle(in_valid=1, in_payload=(b << 8) | a, out_ready=0 if stalled else 1)
        check(event["input"] == {"operand_a": a, "operand_b": b}, f"abort job was not accepted: {event}")
        if stalled:
            event = await self.cycle(in_valid=0, out_ready=0)
            check(event["output"] is None, f"stalled abort job transferred unexpectedly: {event}")
        event = await self.cycle(rst_n=0, in_valid=1, out_ready=1)
        check(event["input"] is None and event["output"] is None, f"transfer occurred on reset edge: {event}")
        await self.cycle(rst_n=1, in_valid=0, out_ready=1)
        guard = await self.cycle(in_valid=0, out_ready=1)
        check(guard["output"] is None and not self.queue, f"ghost result after reset: event={guard} queue={self.queue}")
        return {"accepted_inputs": [{"operand_a": a, "operand_b": b}], "outputs": [], "aborted": True, "reset_edges": 1}


@cocotb.test(timeout_time=500, timeout_unit="us")
@contract_coverage()
async def verify_u8_registered_adder(dut):
    sanity_check()
    check(len(dut.in_payload) == 16 and len(dut.out_payload) == 9, f"port widths in={len(dut.in_payload)} out={len(dut.out_payload)}")
    dut.rst_n.value = 1
    dut.in_valid.value = 0
    dut.in_payload.value = 0
    dut.out_ready.value = 0
    clock_task = cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    bench = Bench(dut)

    await bench.cycle(rst_n=0, in_valid=0, out_ready=0)
    await bench.cycle(rst_n=1, in_valid=0, out_ready=0)

    observed = await bench.single(0, 0, require_latency_one=True)
    expected = {"accepted_inputs": [{"operand_a": 0, "operand_b": 0}], "outputs": [0], "aborted": False, "reset_edges": 0}
    # STIMULUS [boundary_zero] targets=('channel.input_operands.handshake_states', 'channel.output_sum.handshake_states', 'operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum', 'operation.add_unsigned.registered_latency')
    stimulus_id = _contract_record_checked_stimulus("directed", {"operand_a": 0, "operand_b": 0}, expected, observed, operations=("add_unsigned",), label="boundary_zero")
    sample_operation("add_unsigned", {}, "directed", stimulus_id)

    observed = await bench.single(255, 0, require_latency_one=True)
    expected = {"accepted_inputs": [{"operand_a": 255, "operand_b": 0}], "outputs": [255], "aborted": False, "reset_edges": 0}
    # STIMULUS [boundary_255_0] targets=('operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum')
    stimulus_id = _contract_record_checked_stimulus("directed", {"operand_a": 255, "operand_b": 0}, expected, observed, operations=("add_unsigned",), label="boundary_255_0")
    sample_operation("add_unsigned", {}, "directed", stimulus_id)

    observed = await bench.single(255, 1, require_latency_one=True)
    expected = {"accepted_inputs": [{"operand_a": 255, "operand_b": 1}], "outputs": [256], "aborted": False, "reset_edges": 0}
    # STIMULUS [boundary_255_1] targets=('operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum')
    stimulus_id = _contract_record_checked_stimulus("directed", {"operand_a": 255, "operand_b": 1}, expected, observed, operations=("add_unsigned",), label="boundary_255_1")
    sample_operation("add_unsigned", {}, "directed", stimulus_id)

    observed = await bench.single(255, 255, require_latency_one=True)
    expected = {"accepted_inputs": [{"operand_a": 255, "operand_b": 255}], "outputs": [510], "aborted": False, "reset_edges": 0}
    # STIMULUS [boundary_max] targets=('operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum')
    stimulus_id = _contract_record_checked_stimulus("directed", {"operand_a": 255, "operand_b": 255}, expected, observed, operations=("add_unsigned",), label="boundary_max")
    sample_operation("add_unsigned", {}, "directed", stimulus_id)

    for label, first, second, stalls in (("stall_one", (1, 2), (3, 4), 1), ("stall_short", (5, 6), (7, 8), 3), ("stall_long", (9, 10), (11, 12), 5)):
        observed = await bench.stall_pair(first, second, stalls)
        submitted = {"transactions": [{"operand_a": first[0], "operand_b": first[1]}, {"operand_a": second[0], "operand_b": second[1]}], "stall_cycles": stalls}
        expected = {"accepted_inputs": submitted["transactions"], "outputs": [add_unsigned(*first), add_unsigned(*second)], "aborted": False, "reset_edges": 0}
        if label == "stall_one":
            # STIMULUS [stall_one] targets=('channel.input_operands.stall_stability', 'channel.output_sum.stall_stability', 'operation.add_unsigned.output_buffer_stall')
            stimulus_id = _contract_record_checked_stimulus("directed", submitted, expected, observed, operations=("add_unsigned",), label="stall_one")
        elif label == "stall_short":
            # STIMULUS [stall_short] targets=('channel.input_operands.stall_stability', 'channel.output_sum.stall_stability', 'operation.add_unsigned.output_buffer_stall')
            stimulus_id = _contract_record_checked_stimulus("directed", submitted, expected, observed, operations=("add_unsigned",), label="stall_short")
        else:
            # STIMULUS [stall_long] targets=('channel.input_operands.stall_stability', 'channel.output_sum.stall_stability', 'operation.add_unsigned.output_buffer_stall')
            stimulus_id = _contract_record_checked_stimulus("directed", submitted, expected, observed, operations=("add_unsigned",), label="stall_long")
        sample_operation("add_unsigned", {}, "directed", stimulus_id)

    observed = await bench.reset_abort(21, 22, False)
    expected = {"accepted_inputs": [{"operand_a": 21, "operand_b": 22}], "outputs": [], "aborted": True, "reset_edges": 1}
    # STIMULUS [reset_pending] targets=('signal.rst_n.reset_behavior',)
    stimulus_id = _contract_record_checked_stimulus("directed", {"operand_a": 21, "operand_b": 22, "reset_before_output": True}, expected, observed, operations=("add_unsigned",), label="reset_pending")
    sample_operation("add_unsigned", {}, "directed", stimulus_id)

    observed = await bench.reset_abort(23, 24, True)
    expected = {"accepted_inputs": [{"operand_a": 23, "operand_b": 24}], "outputs": [], "aborted": True, "reset_edges": 1}
    # STIMULUS [reset_stalled] targets=('signal.rst_n.reset_behavior', 'channel.input_operands.handshake_states', 'channel.output_sum.handshake_states')
    stimulus_id = _contract_record_checked_stimulus("directed", {"operand_a": 23, "operand_b": 24, "reset_while_stalled": True}, expected, observed, operations=("add_unsigned",), label="reset_stalled")
    sample_operation("add_unsigned", {}, "directed", stimulus_id)

    rng = random.Random(180417)
    for transaction in range(100):
        a = rng.randrange(256)
        b = rng.randrange(256)
        source_delay = rng.randrange(5)
        stall_count = rng.randrange(7)
        ready_pattern = [0] * stall_count + [1]
        observed = await bench.single(a, b, source_delay=source_delay, ready_pattern=ready_pattern)
        expected = {"accepted_inputs": [{"operand_a": a, "operand_b": b}], "outputs": [add_unsigned(a, b)], "aborted": False, "reset_edges": 0}
        submitted = {"operand_a": a, "operand_b": b, "source_idle_cycles": source_delay, "sink_stall_cycles": stall_count, "transaction": transaction}
        # STIMULUS [randomized_job] targets=('channel.input_operands.handshake_states', 'channel.output_sum.handshake_states', 'operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum', 'operation.add_unsigned.registered_latency')
        stimulus_id = _contract_record_checked_stimulus("randomized", submitted, expected, observed, operations=("add_unsigned",), label="randomized_job")
        sample_operation("add_unsigned", {}, "randomized", stimulus_id)

    for _ in range(3):
        event = await bench.cycle(in_valid=0, out_ready=1)
        check(event["output"] is None, f"late unsolicited output at end of regression: {event}")
    clock_task.cancel()

# === BEGIN PIPELINE-GENERATED VERIFIER ANNOTATIONS ===
# This literal and the following comments are emitted by my_v.
# The Verifier chooses semantic label-to-target mappings; code owns syntax.
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{'label': 'boundary_zero', 'targets': ['channel.input_operands.handshake_states', 'channel.output_sum.handshake_states', 'operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum', 'operation.add_unsigned.registered_latency']}, {'label': 'boundary_255_0', 'targets': ['operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum']}, {'label': 'boundary_255_1', 'targets': ['operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum']}, {'label': 'boundary_max', 'targets': ['operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum']}, {'label': 'stall_one', 'targets': ['channel.input_operands.stall_stability', 'channel.output_sum.stall_stability', 'operation.add_unsigned.output_buffer_stall']}, {'label': 'stall_short', 'targets': ['channel.input_operands.stall_stability', 'channel.output_sum.stall_stability', 'operation.add_unsigned.output_buffer_stall']}, {'label': 'stall_long', 'targets': ['channel.input_operands.stall_stability', 'channel.output_sum.stall_stability', 'operation.add_unsigned.output_buffer_stall']}, {'label': 'reset_pending', 'targets': ['signal.rst_n.reset_behavior']}, {'label': 'reset_stalled', 'targets': ['signal.rst_n.reset_behavior', 'channel.input_operands.handshake_states', 'channel.output_sum.handshake_states']}, {'label': 'randomized_job', 'targets': ['channel.input_operands.handshake_states', 'channel.output_sum.handshake_states', 'operation.add_unsigned.accepted_sum', 'operation.add_unsigned.transferred_sum', 'operation.add_unsigned.registered_latency']}]
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

CONTRACT_SIGNAL_NAMES = ('clk', 'rst_n', 'in_valid', 'in_ready', 'in_payload', 'out_valid', 'out_ready', 'out_payload')
CONTRACT_PROTOCOL_ASSERTION_FEATURES = ('channel.input_operands.stall_stability', 'channel.output_sum.stall_stability')
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

    # PROTOCOL ASSERTION [channel.input_operands.stall_stability]
    _p0_valid = int(bool(snapshot['in_valid']))
    _p0_ready = int(bool(snapshot['in_ready']))
    _p0_content = tuple(snapshot[name] for name in ('in_payload',))
    _p0_previous = _CONTRACT_PROTOCOL_STATE.get('channel.input_operands.stall_stability')
    if _p0_previous is not None:
        assert _p0_valid == 1, (
            "protocol valid was withdrawn before stalled transfer completed; feature=channel.input_operands.stall_stability; related_signals=('in_valid', 'in_ready', 'in_payload'); observed="
            + repr({name: snapshot[name] for name in ('in_valid', 'in_ready', 'in_payload')})
        )
        assert _p0_content == _p0_previous['content'], (
            "producer-owned content changed during stall or release; feature=channel.input_operands.stall_stability; related_signals=('in_valid', 'in_ready', 'in_payload'); previous="
            + repr(_p0_previous['content']) + '; observed='
            + repr(_p0_content)
        )
    if _p0_valid and not _p0_ready:
        if _p0_previous is None:
            _CONTRACT_PROTOCOL_STATE['channel.input_operands.stall_stability'] = {
                'content': _p0_content, 'length': 1
            }
        else:
            _p0_previous['length'] += 1
    else:
        if _p0_previous is not None:
            completed_stalls['channel.input_operands.stall_stability'] = _p0_previous['length']
        _CONTRACT_PROTOCOL_STATE.pop('channel.input_operands.stall_stability', None)

    # PROTOCOL ASSERTION [channel.output_sum.stall_stability]
    _p1_valid = int(bool(snapshot['out_valid']))
    _p1_ready = int(bool(snapshot['out_ready']))
    _p1_content = tuple(snapshot[name] for name in ('out_payload',))
    _p1_previous = _CONTRACT_PROTOCOL_STATE.get('channel.output_sum.stall_stability')
    if _p1_previous is not None:
        assert _p1_valid == 1, (
            "protocol valid was withdrawn before stalled transfer completed; feature=channel.output_sum.stall_stability; related_signals=('out_valid', 'out_ready', 'out_payload'); observed="
            + repr({name: snapshot[name] for name in ('out_valid', 'out_ready', 'out_payload')})
        )
        assert _p1_content == _p1_previous['content'], (
            "producer-owned content changed during stall or release; feature=channel.output_sum.stall_stability; related_signals=('out_valid', 'out_ready', 'out_payload'); previous="
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
