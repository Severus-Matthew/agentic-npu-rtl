"""Real-simulator proof that `custom_mmio.execute_custom_mmio_read_job`
drives genuinely out-of-order completion for a non-AXI custom protocol,
reusing `RandomCompletionScheduler` and `OperationMemoryAdapter` completely
unmodified from the full-AXI4 driver -- the concrete payoff of the
memory/adapter/driver split. Channel and signal names below are
deliberately non-AXI (`req_out`/`dat_in`) to prove nothing is matched by
spelling, mirroring `test_axi4_outstanding_drive.py`'s own proof.
"""
from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_RTL = """
module custom_mmio_manager_stub (
    input  logic        clk,
    input  logic        rst,

    output logic [3:0]  req_out_id,
    output logic [31:0] req_out_addr,
    output logic        req_out_valid,
    input  logic        req_out_ready,

    input  logic [3:0]  dat_in_id,
    input  logic [31:0] dat_in_data,
    input  logic        dat_in_last,
    input  logic        dat_in_valid,
    output logic        dat_in_ready,

    output logic [31:0] result_a,
    output logic [31:0] result_b,
    output logic        done_a,
    output logic        done_b
);
    typedef enum logic [1:0] {S_IDLE, S_REQ0, S_REQ1, S_WAIT} state_t;
    state_t state;

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            req_out_valid <= 1'b0;
            dat_in_ready <= 1'b0;
            done_a <= 1'b0;
            done_b <= 1'b0;
            result_a <= '0;
            result_b <= '0;
            req_out_id <= '0;
            req_out_addr <= '0;
        end else begin
            case (state)
                S_IDLE: begin
                    req_out_valid <= 1'b1;
                    req_out_id <= 4'd0;
                    req_out_addr <= 32'h0000_1000;
                    state <= S_REQ0;
                end
                S_REQ0: begin
                    if (req_out_valid && req_out_ready) begin
                        req_out_id <= 4'd1;
                        req_out_addr <= 32'h0000_2000;
                        state <= S_REQ1;
                    end
                end
                S_REQ1: begin
                    if (req_out_valid && req_out_ready) begin
                        req_out_valid <= 1'b0;
                        dat_in_ready <= 1'b1;
                        state <= S_WAIT;
                    end
                end
                S_WAIT: begin
                    if (dat_in_valid && dat_in_ready) begin
                        if (dat_in_id == 4'd0) begin
                            result_a <= dat_in_data;
                            done_a <= 1'b1;
                        end else if (dat_in_id == 4'd1) begin
                            result_b <= dat_in_data;
                            done_b <= 1'b1;
                        end
                    end
                end
            endcase
        end
    end
endmodule
"""


def test_two_outstanding_custom_mmio_reads_complete_out_of_order(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "custom_mmio_manager_stub.sv").write_text(_RTL)

    fixture = '''from multigent.verifier_tool.pool.role_pool.standard_protocols import compile_standard_protocol_plan

channels = []
signals = [
    {"name": "clk", "role": "clock", "direction": "input", "channel": None},
    {"name": "rst", "role": "reset", "direction": "input", "channel": None,
     "semantic": "synchronous active-high reset"},
]

def add_channel(name, kind, direction, fields):
    channels.append({
        "name": name, "direction": direction, "protocol_profile": "custom_mmio",
        "data_objects": [], "ordering": "any completion order", "framing": "burst",
        "metadata": [f"protocol_group=mem protocol_channel={kind}"],
    })
    signals.append({"name": f"{name}_valid", "role": "valid", "direction": direction,
                     "channel": name, "width": "1"})
    signals.append({"name": f"{name}_ready", "role": "ready",
                     "direction": "input" if direction == "output" else "output",
                     "channel": name, "width": "1"})
    for field, (role, semantic_class, width) in fields.items():
        signals.append({
            "name": f"{name}_{field}", "role": role, "semantic_class": semantic_class,
            "direction": direction, "channel": name, "width": str(width),
            "semantic": f"protocol_field={field}",
        })

add_channel("req_out", "request", "output", {
    "addr": ("payload", "address", 32), "id": ("transaction_id", "identifier", 4),
})
add_channel("dat_in", "data", "input", {
    "data": ("payload", "data", 32), "last": ("last", "framing", 1),
    "id": ("transaction_id", "identifier", 4),
})

interface = {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}
group = compile_standard_protocol_plan(interface)["groups"][0]
assert group["profile"] == "custom_mmio"

operation = {
    "dimensions": {},
    "inputs": [
        {
            "data_object": "A_matrix", "direction": "input", "dimensions": [],
            "data_type": {"width_bits": 32, "signed": True},
            "memory_mapping": {
                "base_signal": "unused", "word_stride_bytes": 4, "elements_per_word": 1,
                "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
            },
        },
        {
            "data_object": "B_matrix", "direction": "input", "dimensions": [],
            "data_type": {"width_bits": 32, "signed": True},
            "memory_mapping": {
                "base_signal": "unused", "word_stride_bytes": 4, "elements_per_word": 1,
                "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
            },
        },
    ],
    "outputs": [],
}
case = {"stimulus": {"A_matrix": [111], "B_matrix": [100]}}
bases = {"A_matrix": 0x1000, "B_matrix": 0x2000}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.drivers.custom_mmio import execute_custom_mmio_read_job
from test_fixture import interface, group, operation, case, bases

@cocotb.test(timeout_time=200, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    completion_order = []

    job = cocotb.start_soon(execute_custom_mmio_read_job(
        dut, "clk", group, operation, case, bases,
        seed=6, max_extra_cycles=4, timeout_cycles=2000,
    ))

    async def _monitor():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.dat_in_valid.value) and int(dut.dat_in_ready.value):
                completion_order.append(int(dut.dat_in_id.value))
                if len(completion_order) == 2:
                    return
    monitor = cocotb.start_soon(_monitor())

    await job
    await monitor

    assert completion_order == [1, 0], (
        f"expected id=1 (issued second) to complete before id=0 (issued first) "
        f"with seed=6, got {completion_order!r}"
    )
    assert int(dut.done_a.value) == 1 and int(dut.done_b.value) == 1
    assert int(dut.result_a.value) == 111
    assert int(dut.result_b.value) == 100
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="custom_mmio_manager_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result
