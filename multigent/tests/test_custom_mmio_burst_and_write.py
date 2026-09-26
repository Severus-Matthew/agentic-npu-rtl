"""Real-simulator proof of the two new custom_mmio driver capabilities:
multi-beat read bursts (`len` on `request`) and write-direction driving
(`execute_custom_mmio_write_job`), including out-of-order write completion
via the same `RandomCompletionScheduler` the read side and full AXI4 both
use unmodified.
"""
from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_READ_BURST_RTL = """
module custom_mmio_burst_read_stub (
    input  logic        clk,
    input  logic        rst,

    output logic [31:0] req_out_addr,
    output logic [7:0]  req_out_len,
    output logic        req_out_valid,
    input  logic        req_out_ready,

    input  logic [31:0] dat_in_data,
    input  logic        dat_in_last,
    input  logic        dat_in_valid,
    output logic        dat_in_ready,

    output logic [31:0] result0,
    output logic [31:0] result1,
    output logic        done
);
    typedef enum logic [1:0] {S_IDLE, S_REQ, S_WAIT, S_DONE} state_t;
    state_t state;
    logic beat_index;

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            req_out_valid <= 1'b0;
            dat_in_ready <= 1'b0;
            done <= 1'b0;
            result0 <= '0;
            result1 <= '0;
            req_out_addr <= '0;
            req_out_len <= '0;
            beat_index <= 1'b0;
        end else begin
            case (state)
                S_IDLE: begin
                    req_out_valid <= 1'b1;
                    req_out_addr <= 32'h0000_1000;
                    req_out_len <= 8'd1;
                    state <= S_REQ;
                end
                S_REQ: begin
                    if (req_out_valid && req_out_ready) begin
                        req_out_valid <= 1'b0;
                        dat_in_ready <= 1'b1;
                        beat_index <= 1'b0;
                        state <= S_WAIT;
                    end
                end
                S_WAIT: begin
                    if (dat_in_valid && dat_in_ready) begin
                        if (beat_index == 1'b0) result0 <= dat_in_data;
                        else result1 <= dat_in_data;
                        beat_index <= beat_index + 1'b1;
                        if (dat_in_last) begin
                            dat_in_ready <= 1'b0;
                            done <= 1'b1;
                            state <= S_DONE;
                        end
                    end
                end
                default: ;
            endcase
        end
    end
endmodule
"""


def test_custom_mmio_read_burst_via_len_field(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "custom_mmio_burst_read_stub.sv").write_text(_READ_BURST_RTL)

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
    "addr": ("payload", "address", 32), "len": ("metadata", "length", 8),
})
add_channel("dat_in", "data", "input", {
    "data": ("payload", "data", 32), "last": ("last", "framing", 1),
})

interface = {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}
group = compile_standard_protocol_plan(interface)["groups"][0]

operation = {
    "dimensions": {"k": 2},
    "inputs": [{
        "data_object": "A_matrix", "direction": "input", "dimensions": ["k"],
        "data_type": {"width_bits": 32, "signed": True},
        "memory_mapping": {
            "base_signal": "unused", "word_stride_bytes": 4, "elements_per_word": 1,
            "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
        },
    }],
    "outputs": [],
}
case = {"stimulus": {"A_matrix": [111, 222]}}
bases = {"A_matrix": 0x1000}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.drivers.custom_mmio import execute_custom_mmio_read_job
from test_fixture import interface, group, operation, case, bases

@cocotb.test(timeout_time=50, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    await execute_custom_mmio_read_job(
        dut, "clk", group, operation, case, bases, timeout_cycles=500,
    )

    assert int(dut.done.value) == 1
    assert dut.result0.value.to_signed() == 111
    assert dut.result1.value.to_signed() == 222
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="custom_mmio_burst_read_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result


_WRITE_RTL = """
module custom_mmio_write_stub (
    input  logic        clk,
    input  logic        rst,

    output logic [3:0]  wreq_id,
    output logic [31:0] wreq_addr,
    output logic        wreq_valid,
    input  logic        wreq_ready,

    output logic [31:0] wdat_data,
    output logic        wdat_valid,
    input  logic        wdat_ready,

    input  logic [3:0]  ack_id,
    input  logic [1:0]  ack_resp,
    input  logic        ack_valid,
    output logic        ack_ready,

    output logic        done_a,
    output logic        done_b
);
    typedef enum logic [2:0] {S_IDLE, S_REQ0, S_DAT0, S_REQ1, S_DAT1, S_WAIT} state_t;
    state_t state;

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            wreq_valid <= 1'b0;
            wdat_valid <= 1'b0;
            ack_ready <= 1'b0;
            done_a <= 1'b0;
            done_b <= 1'b0;
            wreq_id <= '0;
            wreq_addr <= '0;
            wdat_data <= '0;
        end else begin
            case (state)
                S_IDLE: begin
                    wreq_valid <= 1'b1;
                    wreq_id <= 4'd0;
                    wreq_addr <= 32'h0000_3000;
                    state <= S_REQ0;
                end
                S_REQ0: begin
                    if (wreq_valid && wreq_ready) begin
                        wreq_valid <= 1'b0;
                        wdat_valid <= 1'b1;
                        wdat_data <= 32'd11;
                        state <= S_DAT0;
                    end
                end
                S_DAT0: begin
                    if (wdat_valid && wdat_ready) begin
                        wdat_valid <= 1'b0;
                        wreq_valid <= 1'b1;
                        wreq_id <= 4'd1;
                        wreq_addr <= 32'h0000_4000;
                        state <= S_REQ1;
                    end
                end
                S_REQ1: begin
                    if (wreq_valid && wreq_ready) begin
                        wreq_valid <= 1'b0;
                        wdat_valid <= 1'b1;
                        wdat_data <= 32'd22;
                        state <= S_DAT1;
                    end
                end
                S_DAT1: begin
                    if (wdat_valid && wdat_ready) begin
                        wdat_valid <= 1'b0;
                        ack_ready <= 1'b1;
                        state <= S_WAIT;
                    end
                end
                S_WAIT: begin
                    if (ack_valid && ack_ready) begin
                        if (ack_id == 4'd0) done_a <= 1'b1;
                        else if (ack_id == 4'd1) done_b <= 1'b1;
                    end
                end
                default: ;
            endcase
        end
    end
endmodule
"""


def test_custom_mmio_two_outstanding_writes_complete_out_of_order(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "custom_mmio_write_stub.sv").write_text(_WRITE_RTL)

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

add_channel("wreq", "request", "output", {
    "addr": ("payload", "address", 32), "id": ("transaction_id", "identifier", 4),
})
add_channel("wdat", "data", "output", {
    "data": ("payload", "data", 32),
})
add_channel("ack", "response", "input", {
    "resp": ("metadata", "response_code", 2), "id": ("transaction_id", "identifier", 4),
})

interface = {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}
group = compile_standard_protocol_plan(interface)["groups"][0]

operation = {
    "dimensions": {},
    "inputs": [],
    "outputs": [
        {
            "data_object": "Y0_matrix", "direction": "output", "dimensions": [],
            "data_type": {"width_bits": 32, "signed": True},
            "memory_mapping": {
                "base_signal": "unused", "word_stride_bytes": 4, "elements_per_word": 1,
                "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
            },
        },
        {
            "data_object": "Y1_matrix", "direction": "output", "dimensions": [],
            "data_type": {"width_bits": 32, "signed": True},
            "memory_mapping": {
                "base_signal": "unused", "word_stride_bytes": 4, "elements_per_word": 1,
                "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
            },
        },
    ],
}
bases = {"Y0_matrix": 0x3000, "Y1_matrix": 0x4000}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.adapter import OperationMemoryAdapter
from multigent.verifier_tool.protocol.stimulus.drivers.custom_mmio import execute_custom_mmio_write_job
from test_fixture import interface, group, operation, bases

@cocotb.test(timeout_time=200, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    completion_order = []

    memory = OperationMemoryAdapter.load(operation, {"stimulus": {}}, bases)
    job = cocotb.start_soon(execute_custom_mmio_write_job(
        dut, "clk", group, operation, memory,
        seed=6, max_extra_cycles=4, timeout_cycles=2000,
    ))

    async def _monitor():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.ack_valid.value) and int(dut.ack_ready.value):
                completion_order.append(int(dut.ack_id.value))
                if len(completion_order) == 2:
                    return
    monitor = cocotb.start_soon(_monitor())

    output_beats = await job
    await monitor
    # `done_a`/`done_b` are the DUT's own registered outputs, updated by its
    # `always_ff` in response to the same edge the monitor above observed;
    # give that one more edge to settle before reading them back, the same
    # discipline `axi_lite`'s own RTL fixtures already rely on elsewhere.
    await RisingEdge(dut.clk)

    assert completion_order == [1, 0], (
        f"expected id=1 (issued second) to ack before id=0 (issued first) "
        f"with seed=6, got {completion_order!r}"
    )
    assert int(dut.done_a.value) == 1 and int(dut.done_b.value) == 1
    assert [b["payload"] for b in output_beats] == [11, 22]

    outputs = {b["data_object"]: b for b in operation["outputs"]}
    assert memory.read_output_values(outputs["Y0_matrix"], {}, bases) == [11]
    assert memory.read_output_values(outputs["Y1_matrix"], {}, bases) == [22]
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="custom_mmio_write_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result
