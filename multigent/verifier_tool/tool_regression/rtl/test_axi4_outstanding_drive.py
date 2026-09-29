"""Real-simulator proof that `axi4_outstanding.execute_axi4_memory_job` drives
genuinely out-of-order AXI4 read completions -- not just that final results
end up correct (which strict in-order completion would also achieve), but
that the response for an ID issued *second* is observed on the wire
*before* the response for the ID issued first.

Uses `cocotbext-axi`'s own channel sink/source classes bound to an
independently-issued little RTL AXI4 manager (issues AR id=0 then AR id=1
back-to-back, then waits for both R responses, tracking each by RID) --
this is a real Verilator simulation, not a mock.
"""
from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_RTL = """
module axi4_manager_stub (
    input  logic        clk,
    input  logic        rst,

    output logic [3:0]  arid,
    output logic [31:0] araddr,
    output logic [7:0]  arlen,
    output logic [2:0]  arsize,
    output logic [1:0]  arburst,
    output logic        arvalid,
    input  logic        arready,

    input  logic [3:0]  rid,
    input  logic [31:0] rdata,
    input  logic [1:0]  rresp,
    input  logic        rlast,
    input  logic        rvalid,
    output logic        rready,

    output logic [3:0]  awid,
    output logic [31:0] awaddr,
    output logic [7:0]  awlen,
    output logic [2:0]  awsize,
    output logic [1:0]  awburst,
    output logic        awvalid,
    input  logic        awready,

    output logic [31:0] wdata,
    output logic [3:0]  wstrb,
    output logic        wlast,
    output logic        wvalid,
    input  logic        wready,

    input  logic [3:0]  bid,
    input  logic [1:0]  bresp,
    input  logic        bvalid,
    output logic        bready,

    output logic [31:0] result_a,
    output logic [31:0] result_b,
    output logic        done_a,
    output logic        done_b
);
    typedef enum logic [1:0] {S_IDLE, S_AR0, S_AR1, S_WAIT} state_t;
    state_t state;

    assign awvalid = 1'b0;
    assign awid = '0;
    assign awaddr = '0;
    assign awlen = '0;
    assign awsize = '0;
    assign awburst = '0;
    assign wvalid = 1'b0;
    assign wdata = '0;
    assign wstrb = '0;
    assign wlast = 1'b0;
    assign bready = 1'b1;

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            arvalid <= 1'b0;
            rready <= 1'b0;
            done_a <= 1'b0;
            done_b <= 1'b0;
            result_a <= '0;
            result_b <= '0;
            arid <= '0;
            araddr <= '0;
            arlen <= '0;
            arsize <= '0;
            arburst <= '0;
        end else begin
            case (state)
                S_IDLE: begin
                    arvalid <= 1'b1;
                    arid <= 4'd0;
                    araddr <= 32'h0000_1000;
                    arlen <= 8'd0;
                    arsize <= 3'd2;
                    arburst <= 2'd1;
                    state <= S_AR0;
                end
                S_AR0: begin
                    if (arvalid && arready) begin
                        arid <= 4'd1;
                        araddr <= 32'h0000_2000;
                        state <= S_AR1;
                    end
                end
                S_AR1: begin
                    if (arvalid && arready) begin
                        arvalid <= 1'b0;
                        rready <= 1'b1;
                        state <= S_WAIT;
                    end
                end
                S_WAIT: begin
                    if (rvalid && rready) begin
                        if (rid == 4'd0) begin
                            result_a <= rdata;
                            done_a <= 1'b1;
                        end else if (rid == 4'd1) begin
                            result_b <= rdata;
                            done_b <= 1'b1;
                        end
                    end
                end
            endcase
        end
    end
endmodule
"""


def test_two_outstanding_reads_complete_out_of_order_and_attribute_correctly(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "axi4_manager_stub.sv").write_text(_RTL)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.drivers.axi4_outstanding import execute_axi4_memory_job
from test_fixture import interface, group, operation, case, bases

@cocotb.test(timeout_time=200, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    completion_order = []

    progress = {"read_words": 999}
    job = cocotb.start_soon(execute_axi4_memory_job(
        dut, "clk", group, operation, case, bases,
        seed=6, max_extra_cycles=4, progress_state=progress,
        timeout_cycles=2000,
    ))

    # Independently observe RID at each accepted R beat, from the TB side,
    # to record the true wire-level completion order (not just final state).
    async def _monitor():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.rvalid.value) and int(dut.rready.value):
                completion_order.append(int(dut.rid.value))
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
    assert progress == {
        "read_words": 2,
        "write_words": 0,
        "write_bytes": 0,
        "write_requests": 0,
        "write_responses": 0,
    }, progress

    # A second job on the same wires must not be driven by the first job's
    # cocotbext-axi sink/source background tasks. Before per-job cleanup,
    # stale AR sinks forced READY high and defeated the requested long stall.
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    stalled = 0
    async def _measure_stall():
        nonlocal stalled
        while not (int(dut.done_a.value) and int(dut.done_b.value)):
            await RisingEdge(dut.clk)
            if int(dut.arvalid.value) and not int(dut.arready.value):
                stalled += 1
    measure = cocotb.start_soon(_measure_stall())
    await execute_axi4_memory_job(
        dut, "clk", group, operation, case, bases,
        seed=6, max_extra_cycles=4, initial_sink_stall_cycles=7,
        timeout_cycles=2000,
    )
    await measure
    assert stalled >= 5, f"second job's AR stall was shortened to {stalled} cycles"
'''
    (tests / "test_check.py").write_text(code)

    fixture = '''from multigent.verifier_tool.pool.role_pool.standard_protocols import compile_standard_protocol_plan

channels = []
signals = [
    {"name": "clk", "role": "clock", "direction": "input", "channel": None},
    {"name": "rst", "role": "reset", "direction": "input", "channel": None,
     "semantic": "synchronous active-high reset"},
]

def add_channel(name, kind, direction, fields):
    channels.append({
        "name": name, "direction": direction, "protocol_profile": "axi4",
        "data_objects": [], "ordering": "any completion order", "framing": "burst",
        "metadata": [f"protocol_group=mem protocol_channel={kind}"],
    })
    signals.append({"name": f"{name}valid", "role": "valid", "direction": direction,
                     "channel": name, "width": "1"})
    signals.append({"name": f"{name}ready", "role": "ready",
                     "direction": "input" if direction == "output" else "output",
                     "channel": name, "width": "1"})
    for field, (role, semantic_class, width) in fields.items():
        signals.append({
            "name": f"{name}{field}", "role": role, "semantic_class": semantic_class,
            "direction": direction, "channel": name, "width": str(width),
            "semantic": f"protocol_field={field}",
        })

add_channel("ar", "read_address", "output", {
    "addr": ("payload", "address", 32), "len": ("metadata", "length", 8),
    "size": ("metadata", "size", 3), "burst": ("metadata", "burst_type", 2),
    "id": ("transaction_id", "identifier", 4),
})
add_channel("r", "read_data", "input", {
    "data": ("payload", "data", 32), "resp": ("metadata", "response_code", 2),
    "last": ("last", "framing", 1), "id": ("transaction_id", "identifier", 4),
})
add_channel("aw", "write_address", "output", {
    "addr": ("payload", "address", 32), "len": ("metadata", "length", 8),
    "size": ("metadata", "size", 3), "burst": ("metadata", "burst_type", 2),
    "id": ("transaction_id", "identifier", 4),
})
add_channel("w", "write_data", "output", {
    "data": ("payload", "data", 32), "strb": ("metadata", "byte_enable", 4),
    "last": ("last", "framing", 1),
})
add_channel("b", "write_response", "input", {
    "resp": ("metadata", "response_code", 2), "id": ("transaction_id", "identifier", 4),
})

interface = {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}
group = compile_standard_protocol_plan(interface)["groups"][0]

def _mapping():
    return {
        "base_signal": "unused", "word_stride_bytes": 4, "elements_per_word": 1,
        "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
    }

def _binding(name):
    return {
        "data_object": name, "direction": "input", "dimensions": [],
        "data_type": {"width_bits": 32, "signed": True},
        "memory_mapping": _mapping(),
    }

operation = {
    "dimensions": {},
    "inputs": [_binding("A_matrix"), _binding("B_matrix")],
    "outputs": [],
}
case = {"stimulus": {"A_matrix": [111], "B_matrix": [100]}}
bases = {"A_matrix": 0x1000, "B_matrix": 0x2000}
'''
    (tests / "test_fixture.py").write_text(fixture)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="axi4_manager_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result

    coverage_code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge
from multigent.verifier_tool import (
    InterfaceCoverageTracker, build_interface_coverage_plan,
    capture_contract_snapshot, render_contract_generated_block,
)
from multigent.verifier_tool.protocol.stimulus.drivers.axi4_outstanding import execute_axi4_memory_job
from test_fixture import interface, group, operation, case, bases

@cocotb.test(timeout_time=200, timeout_unit="us")
async def check_outstanding_bin(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    plan = build_interface_coverage_plan(interface)
    namespace = {}
    exec(render_contract_generated_block(plan), namespace)
    tracker = InterfaceCoverageTracker(plan)
    async def observe():
        while True:
            await FallingEdge(dut.clk)
            snapshot = capture_contract_snapshot(dut, tracker.signal_names)
            tracker.sample_snapshot(snapshot, namespace["_check_contract_protocol_assertions"])
    monitor = cocotb.start_soon(observe())
    dut.rst.value = 0
    await execute_axi4_memory_job(
        dut, "clk", group, operation, case, bases,
        seed=6, max_extra_cycles=4, timeout_cycles=2000,
    )
    await RisingEdge(dut.clk)
    monitor.cancel()
    report = tracker.report()
    assert report["assertion_failures"] == [], report["assertion_failures"]
    target = "protocol_group.mem.axi4_outstanding_depth.multiple_ids"
    assert target in report["covered_bins"], f"missing required feature bin {target}"
'''
    (tests / "test_check.py").write_text(coverage_code)
    source = (rtl / "axi4_manager_stub.sv").read_text()
    assert "arid <= 4'd1;" in source
    for variant, modified in (
        ("same_id_mutant", source.replace("arid <= 4'd1;", "arid <= 4'd0;")),
        ("distinct_id_corrected", source),
    ):
        (rtl / "axi4_manager_stub.sv").write_text(modified)
        paired = run_cocotb_regression(
            rtl_dir=rtl, top_module="axi4_manager_stub", tests_dir=tests,
            reference_dir=ref, test_modules=["test_check"], seed=1,
            build_dir=tmp_path / variant,
            report_path=tmp_path / f"{variant}.json", timeout_seconds=120,
        )
        if variant == "same_id_mutant":
            assert paired["status"] == "SIMULATION_FAILURE", paired
            assert "protocol_group.mem.axi4_outstanding_depth.multiple_ids" in paired["stdout"]
        else:
            assert paired["status"] == "PASS", paired
