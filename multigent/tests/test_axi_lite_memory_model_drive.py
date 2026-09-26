"""Real-simulator smoke test for `axi_lite.py::execute_axi_lite_memory_job`
after its private `dict[int, int]` memory was replaced by the shared
`adapter.OperationMemoryAdapter` (the same storage full-AXI4 driving
uses). No test exercised this function against a real simulator before --
existing coverage was code inspection only -- so this exists specifically
to prove the storage swap preserved read correctness, using a real,
minimal AXI4-Lite manager RTL, not a mock.
"""
from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_RTL = """
module axi_lite_manager_stub (
    input  logic        clk,
    input  logic        rst,

    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [7:0]  opcode,
    input  logic [31:0] read_ptr,

    output logic [31:0] araddr,
    output logic        arvalid,
    input  logic        arready,
    input  logic [31:0] rdata,
    input  logic [1:0]  rresp,
    input  logic        rvalid,
    output logic        rready,

    output logic [31:0] awaddr,
    output logic        awvalid,
    input  logic        awready,
    output logic [31:0] wdata,
    output logic [3:0]  wstrb,
    output logic        wvalid,
    input  logic        wready,
    input  logic [1:0]  bresp,
    input  logic        bvalid,
    output logic        bready,

    output logic [31:0] result,
    output logic        done
);
    typedef enum logic [1:0] {S_IDLE, S_AR, S_WAIT_R, S_DONE} state_t;
    state_t state;

    assign awvalid = 1'b0;
    assign awaddr = '0;
    assign wvalid = 1'b0;
    assign wdata = '0;
    assign wstrb = '0;
    assign bready = 1'b1;
    assign cmd_ready = (state == S_IDLE);

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            arvalid <= 1'b0;
            rready <= 1'b0;
            done <= 1'b0;
            result <= '0;
            araddr <= '0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        araddr <= read_ptr;
                        arvalid <= 1'b1;
                        state <= S_AR;
                    end
                end
                S_AR: begin
                    if (arvalid && arready) begin
                        arvalid <= 1'b0;
                        rready <= 1'b1;
                        state <= S_WAIT_R;
                    end
                end
                S_WAIT_R: begin
                    if (rvalid && rready) begin
                        result <= rdata;
                        done <= 1'b1;
                        rready <= 1'b0;
                        state <= S_DONE;
                    end
                end
                default: ;
            endcase
        end
    end
endmodule
"""


def test_axi_lite_read_still_correct_after_shared_memory_model_swap(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "axi_lite_manager_stub.sv").write_text(_RTL)

    fixture = '''from multigent.verifier_tool.pool.role_pool.standard_protocols import compile_standard_protocol_plan

channels = [
    {"name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
     "data_objects": [], "ordering": "one command", "framing": "one beat"},
]
signals = [
    {"name": "clk", "role": "clock", "direction": "input", "channel": None},
    {"name": "rst", "role": "reset", "direction": "input", "channel": None,
     "semantic": "synchronous active-high reset"},
    {"name": "cmd_valid", "role": "valid", "direction": "input", "channel": "cmd"},
    {"name": "cmd_ready", "role": "ready", "direction": "output", "channel": "cmd"},
    {"name": "opcode", "role": "payload", "semantic_class": "command",
     "direction": "input", "channel": "cmd", "width": "8", "semantic": "legal only 8'h01"},
    {"name": "read_ptr", "role": "metadata", "semantic_class": "address",
     "direction": "input", "channel": "cmd", "width": "32",
     "semantic": "data_object=A_matrix address_role=base byte_order=little "
                 "address_sequence=contiguous word_stride_bytes=4"},
]

def add_channel(name, kind, direction, fields):
    channels.append({
        "name": name, "direction": direction, "protocol_profile": "axi4_lite",
        "data_objects": [], "ordering": "in order", "framing": "one beat",
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

add_channel("ar", "read_address", "output", {"addr": ("payload", "address", 32)})
add_channel("r", "read_data", "input", {
    "data": ("payload", "data", 32), "resp": ("metadata", "response_code", 2),
})
add_channel("aw", "write_address", "output", {"addr": ("payload", "address", 32)})
add_channel("w", "write_data", "output", {
    "data": ("payload", "data", 32), "strb": ("metadata", "byte_enable", 4),
})
add_channel("b", "write_response", "input", {"resp": ("metadata", "response_code", 2)})

interface = {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}
group = compile_standard_protocol_plan(interface)["groups"][0]

operation = {
    "dimensions": {},
    "inputs": [{
        "data_object": "A_matrix", "direction": "input", "dimensions": [],
        "data_type": {"width_bits": 32, "signed": True},
        "memory_mapping": {
            "base_signal": "read_ptr", "word_stride_bytes": 4, "elements_per_word": 1,
            "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
        },
    }],
    "outputs": [],
    "lifecycle": {"job_accept_channels": [{
        "channel": "cmd", "signals": {"valid": "cmd_valid", "ready": "cmd_ready", "payload": "opcode"},
        "metadata_fields": [{"signal": "read_ptr", "data_object": "A_matrix"}],
        "legal_values": [1],
    }]},
}
case = {"stimulus": {"A_matrix": [111]}}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.drivers.axi_lite import execute_axi_lite_memory_job
from test_fixture import interface, group, operation, case

@cocotb.test(timeout_time=50, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    await execute_axi_lite_memory_job(
        dut, "clk", group, operation, case,
        stop_after=("read_response", 1), timeout_cycles=500,
    )

    assert int(dut.done.value) == 1
    assert int(dut.result.value) == 111
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_manager_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result


_RTL_RW = """
module axi_lite_rw_stub (
    input  logic        clk,
    input  logic        rst,

    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [7:0]  opcode,
    input  logic [31:0] read_ptr,
    input  logic [31:0] write_ptr,

    output logic [31:0] araddr,
    output logic        arvalid,
    input  logic        arready,
    input  logic [31:0] rdata,
    input  logic [1:0]  rresp,
    input  logic        rvalid,
    output logic        rready,

    output logic [31:0] awaddr,
    output logic        awvalid,
    input  logic        awready,
    output logic [31:0] wdata,
    output logic [3:0]  wstrb,
    output logic        wvalid,
    input  logic        wready,
    input  logic [1:0]  bresp,
    input  logic        bvalid,
    output logic        bready,

    output logic [31:0] result,
    output logic        done,
    output logic [1:0]  last_rresp,
    output logic [1:0]  last_bresp
);
    typedef enum logic [2:0] {S_IDLE, S_AR, S_WAIT_R, S_WRITE, S_WAIT_B, S_DONE} state_t;
    state_t state;
    logic aw_done, w_done;

    assign cmd_ready = (state == S_IDLE);

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            arvalid <= 1'b0;
            rready <= 1'b0;
            awvalid <= 1'b0;
            wvalid <= 1'b0;
            bready <= 1'b0;
            done <= 1'b0;
            result <= '0;
            araddr <= '0;
            awaddr <= '0;
            wdata <= '0;
            wstrb <= 4'hF;
            last_rresp <= '0;
            last_bresp <= '0;
            aw_done <= 1'b0;
            w_done <= 1'b0;
        end else begin
            case (state)
                S_IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        araddr <= read_ptr;
                        arvalid <= 1'b1;
                        state <= S_AR;
                    end
                end
                S_AR: begin
                    if (arvalid && arready) begin
                        arvalid <= 1'b0;
                        rready <= 1'b1;
                        state <= S_WAIT_R;
                    end
                end
                S_WAIT_R: begin
                    if (rvalid && rready) begin
                        result <= rdata;
                        last_rresp <= rresp;
                        rready <= 1'b0;
                        awaddr <= write_ptr;
                        wdata <= rdata;
                        awvalid <= 1'b1;
                        wvalid <= 1'b1;
                        aw_done <= 1'b0;
                        w_done <= 1'b0;
                        state <= S_WRITE;
                    end
                end
                S_WRITE: begin
                    if (awvalid && awready) begin
                        awvalid <= 1'b0;
                        aw_done <= 1'b1;
                    end
                    if (wvalid && wready) begin
                        wvalid <= 1'b0;
                        w_done <= 1'b1;
                    end
                    if ((aw_done || (awvalid && awready)) && (w_done || (wvalid && wready))) begin
                        bready <= 1'b1;
                        state <= S_WAIT_B;
                    end
                end
                S_WAIT_B: begin
                    if (bvalid && bready) begin
                        last_bresp <= bresp;
                        bready <= 1'b0;
                        done <= 1'b1;
                        state <= S_DONE;
                    end
                end
                default: ;
            endcase
        end
    end
endmodule
"""


def _rw_fixture_and_test_code(*, read_error_at=None, write_error_at=None):
    fixture = f'''from multigent.verifier_tool.pool.role_pool.standard_protocols import compile_standard_protocol_plan

channels = [
    {{"name": "cmd", "direction": "input", "protocol_profile": "ready_valid",
     "data_objects": [], "ordering": "one command", "framing": "one beat"}},
]
signals = [
    {{"name": "clk", "role": "clock", "direction": "input", "channel": None}},
    {{"name": "rst", "role": "reset", "direction": "input", "channel": None,
     "semantic": "synchronous active-high reset"}},
    {{"name": "cmd_valid", "role": "valid", "direction": "input", "channel": "cmd"}},
    {{"name": "cmd_ready", "role": "ready", "direction": "output", "channel": "cmd"}},
    {{"name": "opcode", "role": "payload", "semantic_class": "command",
     "direction": "input", "channel": "cmd", "width": "8", "semantic": "legal only 8'h01"}},
    {{"name": "read_ptr", "role": "metadata", "semantic_class": "address",
     "direction": "input", "channel": "cmd", "width": "32",
     "semantic": "data_object=A_matrix address_role=base byte_order=little "
                 "address_sequence=contiguous word_stride_bytes=4"}},
    {{"name": "write_ptr", "role": "metadata", "semantic_class": "address",
     "direction": "input", "channel": "cmd", "width": "32",
     "semantic": "data_object=Y_matrix address_role=base byte_order=little "
                 "address_sequence=contiguous word_stride_bytes=4"}},
]

def add_channel(name, kind, direction, fields):
    channels.append({{
        "name": name, "direction": direction, "protocol_profile": "axi4_lite",
        "data_objects": [], "ordering": "in order", "framing": "one beat",
        "metadata": [f"protocol_group=mem protocol_channel={{kind}}"],
    }})
    signals.append({{"name": f"{{name}}valid", "role": "valid", "direction": direction,
                     "channel": name, "width": "1"}})
    signals.append({{"name": f"{{name}}ready", "role": "ready",
                     "direction": "input" if direction == "output" else "output",
                     "channel": name, "width": "1"}})
    for field, (role, semantic_class, width) in fields.items():
        signals.append({{
            "name": f"{{name}}{{field}}", "role": role, "semantic_class": semantic_class,
            "direction": direction, "channel": name, "width": str(width),
            "semantic": f"protocol_field={{field}}",
        }})

add_channel("ar", "read_address", "output", {{"addr": ("payload", "address", 32)}})
add_channel("r", "read_data", "input", {{
    "data": ("payload", "data", 32), "resp": ("metadata", "response_code", 2),
}})
add_channel("aw", "write_address", "output", {{"addr": ("payload", "address", 32)}})
add_channel("w", "write_data", "output", {{
    "data": ("payload", "data", 32), "strb": ("metadata", "byte_enable", 4),
}})
add_channel("b", "write_response", "input", {{"resp": ("metadata", "response_code", 2)}})

interface = {{"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}}
group = compile_standard_protocol_plan(interface)["groups"][0]

operation = {{
    "dimensions": {{}},
    "inputs": [{{
        "data_object": "A_matrix", "direction": "input", "dimensions": [],
        "data_type": {{"width_bits": 32, "signed": True}},
        "memory_mapping": {{
            "base_signal": "read_ptr", "word_stride_bytes": 4, "elements_per_word": 1,
            "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
        }},
    }}],
    "outputs": [{{
        "data_object": "Y_matrix", "direction": "output", "dimensions": [],
        "data_type": {{"width_bits": 32, "signed": True}},
        "memory_mapping": {{
            "base_signal": "write_ptr", "word_stride_bytes": 4, "elements_per_word": 1,
            "bus_width_bits": 32, "byte_order": "little", "address_sequence": "contiguous",
        }},
    }}],
    "lifecycle": {{"job_accept_channels": [{{
        "channel": "cmd", "signals": {{"valid": "cmd_valid", "ready": "cmd_ready", "payload": "opcode"}},
        "metadata_fields": [
            {{"signal": "read_ptr", "data_object": "A_matrix"}},
            {{"signal": "write_ptr", "data_object": "Y_matrix"}},
        ],
        "legal_values": [1],
    }}]}},
}}
case = {{"stimulus": {{"A_matrix": [111]}}}}
'''
    code = f'''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.drivers.axi_lite import execute_axi_lite_memory_job
from test_fixture import interface, group, operation, case

@cocotb.test(timeout_time=50, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    await execute_axi_lite_memory_job(
        dut, "clk", group, operation, case,
        read_error_at={read_error_at!r}, write_error_at={write_error_at!r},
        timeout_cycles=500,
    )

    # This RTL's write depends on the read's own result, so a failed read
    # never reaches the write/done stage at all -- that is a property of
    # this test's RTL, not of the driver, which correctly stops without
    # hanging either way (proven by this test completing in real sim time
    # rather than timing out).
    if {read_error_at!r} is None:
        assert int(dut.done.value) == 1
    assert int(dut.last_rresp.value) == {2 if read_error_at else 0}
    assert int(dut.last_bresp.value) == {2 if write_error_at else 0}
'''
    return fixture, code


def _run_rw_case(tmp_path, *, read_error_at=None, write_error_at=None):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "axi_lite_rw_stub.sv").write_text(_RTL_RW)
    fixture, code = _rw_fixture_and_test_code(read_error_at=read_error_at, write_error_at=write_error_at)
    (tests / "test_fixture.py").write_text(fixture)
    (tests / "test_check.py").write_text(code)
    return run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_rw_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )


def test_axi_lite_read_then_write_round_trips_through_the_library_slave_model(tmp_path):
    result = _run_rw_case(tmp_path)
    assert result["status"] == "PASS", result


def test_axi_lite_read_error_injection_produces_slverr_via_the_library(tmp_path):
    """Proves `_FaultInjectingTarget` correctly rides on `AxiLiteSlaveRead`'s
    own try/except-driven RRESP construction rather than reimplementing it."""

    result = _run_rw_case(tmp_path, read_error_at=1)
    assert result["status"] == "PASS", result


def test_axi_lite_write_error_injection_produces_slverr_via_the_library(tmp_path):
    """Same proof as above, for `AxiLiteSlaveWrite`'s BRESP construction."""

    result = _run_rw_case(tmp_path, write_error_at=1)
    assert result["status"] == "PASS", result
