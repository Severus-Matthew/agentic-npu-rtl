"""Real-simulator proof of the operation-independent AXI4 responder ABI."""

from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression


pytestmark = pytest.mark.skipif(
    shutil.which("verilator") is None, reason="Verilator not on PATH"
)


_RTL = r"""
module axi4_read_manager (
    input logic clk, input logic rst,
    output logic [3:0] arid, output logic [31:0] araddr,
    output logic [7:0] arlen, output logic [2:0] arsize,
    output logic [1:0] arburst, output logic arvalid, input logic arready,
    input logic [3:0] rid, input logic [31:0] rdata,
    input logic [1:0] rresp, input logic rlast, input logic rvalid,
    output logic rready, output logic done, output logic [31:0] result
);
    always_ff @(posedge clk) begin
        if (rst) begin
            arid <= 4'd3; araddr <= 32'h1004; arlen <= 0;
            arsize <= 2; arburst <= 1; arvalid <= 0; rready <= 0;
            done <= 0; result <= 0;
        end else begin
            if (!done && !arvalid && !rready) arvalid <= 1;
            if (arvalid && arready) begin arvalid <= 0; rready <= 1; end
            if (rvalid && rready) begin
                assert(rid == 4'd3 && rresp == 0 && rlast);
                result <= rdata; done <= 1; rready <= 0;
            end
        end
    end
endmodule
"""


_FIXTURE = r'''
from multigent.verifier_tool.pool.role_pool.standard_protocols import compile_standard_protocol_plan

channels = []
signals = [
    {"name": "clk", "role": "clock", "direction": "input", "channel": None},
    {"name": "rst", "role": "reset", "direction": "input", "channel": None},
]

def add(name, kind, direction, fields):
    channels.append({
        "name": name, "direction": direction, "protocol_profile": "axi4",
        "data_objects": [], "ordering": "in_order_per_id", "framing": "burst",
        "metadata": [f"protocol_group=mem protocol_channel={kind}"],
    })
    signals.extend([
        {"name": f"{name}valid", "role": "valid", "direction": direction,
         "channel": name, "width": "1"},
        {"name": f"{name}ready", "role": "ready",
         "direction": "input" if direction == "output" else "output",
         "channel": name, "width": "1"},
    ])
    for field, (role, semantic_class, width) in fields.items():
        signals.append({
            "name": f"{name}{field}", "role": role,
            "semantic_class": semantic_class, "direction": direction,
            "channel": name, "width": str(width),
            "semantic": f"protocol_field={field}",
        })

add("ar", "read_address", "output", {
    "addr": ("payload", "address", 32), "len": ("metadata", "length", 8),
    "size": ("metadata", "size", 3), "burst": ("metadata", "burst_type", 2),
    "id": ("transaction_id", "identifier", 4),
})
add("r", "read_data", "input", {
    "data": ("payload", "data", 32), "resp": ("metadata", "response_code", 2),
    "last": ("last", "framing", 1), "id": ("transaction_id", "identifier", 4),
})
interface = {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}
group = compile_standard_protocol_plan(interface)["groups"][0]
'''


_TEST = r'''
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.drivers.axi4_outstanding import serve_axi4_protocol_transactions
from test_fixture import group

@cocotb.test(timeout_time=100, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3): await RisingEdge(dut.clk)
    dut.rst.value = 0

    def read_value(request, beat_index):
        assert request["addr"] == 0x1004
        assert request["id"] == 3
        assert beat_index == 0
        return 0xA5A51234

    evidence = await serve_axi4_protocol_transactions(
        dut, "clk", group, {"read": 1, "write": 0},
        read_data=read_value,
        request_pause_patterns={"read_address": [True, True, False]},
        timeout_cycles=200,
    )
    await RisingEdge(dut.clk)
    assert int(dut.done.value) == 1
    assert int(dut.result.value) == 0xA5A51234
    assert evidence["read_requests"][0]["addr"] == 0x1004
    assert evidence["read_responses"] == [{
        "id": 3, "data": 0xA5A51234, "resp": 0, "last": 1,
    }]
'''


def test_protocol_responder_serves_read_without_operation_metadata(tmp_path):
    rtl = tmp_path / "rtl"
    tests = tmp_path / "tests"
    reference = tmp_path / "reference"
    rtl.mkdir()
    tests.mkdir()
    reference.mkdir()
    (rtl / "axi4_read_manager.sv").write_text(_RTL, encoding="utf-8")
    (tests / "test_fixture.py").write_text(_FIXTURE, encoding="utf-8")
    (tests / "test_responder.py").write_text(_TEST, encoding="utf-8")
    (reference / "model.py").write_text("", encoding="utf-8")

    result = run_cocotb_regression(
        rtl_dir=rtl,
        top_module="axi4_read_manager",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_responder"],
        seed=1,
        build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json",
        timeout_seconds=120,
    )
    assert result["status"] == "PASS", result
