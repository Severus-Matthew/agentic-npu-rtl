"""Small actual-signal coverage smoke test; no LLM/golden generation involved."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from multigent.verifier_tool.coverage.runtime import contract_coverage, record_stimulus, sample_operation

OPERATION_SAMPLING_BINDINGS = [{
    "operation": "compute", "point": "sum_boundary", "template": "custom",
    "observer": "observe_sum_boundary", "event": "clock",
    "fields": {"a": {"signal": "left"}, "b": {"signal": "right"}},
}]

def observe_sum_boundary(values, state):
    return values["a"] + values["b"] > 15


@cocotb.test()
@contract_coverage()
async def observed_inputs_not_claimed_fields(dut):
    dut.left.value, dut.right.value = 0, 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for a, b in [(value, 15 - value) for value in range(16)] + [(15, 15)]:
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        dut.left.value, dut.right.value = a, b
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        expected = (a + b) & 15
        assert int(dut.result.value) == expected
        stimulus_id = record_stimulus("directed", {"a": a, "b": b}, {"result": expected})
        # Intentionally false claims: these fields cannot feed runtime-owned points.
        sample_operation("compute", {"left_values": 999, "right_values": 999, "overflow": True, "sum_boundary": True}, "directed", stimulus_id)
