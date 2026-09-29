"""Real-simulator proof of `_run_arithmetic_blocked_operation_smoke`: an
operation whose arithmetic has no code-owned golden model (here
`classifier_profile: llm_extension`) but whose protocol (axi4_lite) and
lifecycle (command channel) are both fully resolved should still get real,
well-typed traffic driven through it -- proving the earlier "driving needs a
golden model" framing was wrong. `execute_axi_lite_memory_job` only ever
consumes `case["stimulus"]`; nothing about pushing bytes onto AR/R/AW/W/B or
waiting for the `completion` pulse touches `case["expected"]` at all -- only
the final, now-skipped `_record_case` call would have.

Reuses `test_axi_lite_memory_model_drive.py`'s `_RTL_RW` read-then-write-back
stub and interface/operation shape unmodified, except for the one thing that
actually matters here: `operation["arithmetic"]["classifier_profile"]` is
`llm_extension`, not `integer_matrix_multiply`.
"""
from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.rtl.test_axi_lite_memory_model_drive import _RTL_RW
from multigent.tools.cocotb_runner import run_cocotb_regression

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


def test_arithmetic_blocked_operation_still_gets_protocol_lifecycle_traffic(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "axi_lite_rw_stub.sv").write_text(_RTL_RW)

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
    {"name": "write_ptr", "role": "metadata", "semantic_class": "address",
     "direction": "input", "channel": "cmd", "width": "32",
     "semantic": "data_object=Y_matrix address_role=base byte_order=little "
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

_CAPABILITIES = {
    "max_outstanding": 1,
    "read_write_concurrency": False,
    "address_bins": ["zero", "aligned", "page_edge"],
    "write_strobe_bins": "full",
    "protection_bins": "zero",
    "write_order_bins": ["address_first", "data_first", "same_cycle"],
}

# The one thing that actually matters for this test: arithmetic has NO
# code-owned profile at all, unlike every other axi4_lite fixture this
# session, which all declare integer_matrix_multiply.
operation = {
    "operation_name": "unsupported_op",
    "arithmetic": {"classifier_profile": "llm_extension", "reason": "test", "semantics": "test"},
    "dimensions": {},
    "inputs": [{
        "data_object": "A_matrix", "direction": "input", "dimensions": [],
        "data_type": {"width_bits": 32, "signed": True},
        "protocol_profile": "axi4_lite",
        "serialization": {"kind": "scalar", "index_order": []},
        "memory_mapping": {
            "base_signal": "read_ptr", "protocol_group": "mem", "word_stride_bytes": 4,
            "elements_per_word": 1, "bus_width_bits": 32, "byte_order": "little",
            "address_sequence": "contiguous", "protocol_capabilities": _CAPABILITIES,
        },
    }],
    "outputs": [{
        "data_object": "Y_matrix", "direction": "output", "dimensions": [],
        "data_type": {"width_bits": 32, "signed": True},
        "protocol_profile": "axi4_lite",
        "serialization": {"kind": "scalar", "index_order": []},
        "memory_mapping": {
            "base_signal": "write_ptr", "protocol_group": "mem", "word_stride_bytes": 4,
            "elements_per_word": 1, "bus_width_bits": 32, "byte_order": "little",
            "address_sequence": "contiguous", "protocol_capabilities": _CAPABILITIES,
        },
    }],
    "lifecycle": {"job_accept_channels": [{
        "channel": "cmd", "signals": {"valid": "cmd_valid", "ready": "cmd_ready", "payload": "opcode"},
        "metadata_fields": [
            {"signal": "read_ptr", "data_object": "A_matrix"},
            {"signal": "write_ptr", "data_object": "Y_matrix"},
        ],
        "legal_values": [1],
    }]},
}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.orchestration.campaign import (
    _operation_arithmetic_reasons,
    _operation_protocol_lifecycle_reasons,
    _run_arithmetic_blocked_operation_smoke,
)
from test_fixture import interface, operation

@cocotb.test(timeout_time=50, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Ground the premise: arithmetic IS the only blocker, protocol/lifecycle
    # genuinely are not.
    assert _operation_arithmetic_reasons(operation, "unsupported_op") != []
    assert _operation_protocol_lifecycle_reasons(operation, "unsupported_op") == []

    # This must complete without raising -- in particular, without ever
    # needing a case["expected"], which was never supplied and does not
    # exist for random smoke stimulus.
    result = await _run_arithmetic_blocked_operation_smoke(
        dut, interface, operation, seed=7, timeout_cycles=2000,
    )
    assert result is None  # record=False: nothing was checked or recorded

    # The real proof: actual AXI4-Lite traffic reached the DUT and it
    # completed its own read-then-write-back sequence for real, regardless
    # of what value was driven.
    assert int(dut.done.value) == 1
    assert int(dut.last_rresp.value) == 0
    assert int(dut.last_bresp.value) == 0
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="axi_lite_rw_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=7, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result


_RTL_READY_VALID = """
module ready_valid_smoke_stub (
    input  logic        clk,
    input  logic        rst,

    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [7:0]  opcode,

    input  logic [31:0] in_payload,
    input  logic        in_valid,
    output logic        in_ready,

    output logic [31:0] out_payload,
    output logic        out_valid,
    input  logic        out_ready,

    output logic        busy,
    output logic        completion
);
    typedef enum logic [1:0] {S_IDLE, S_IN, S_OUT} state_t;
    state_t state;

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE;
            cmd_ready <= 1'b1;
            in_ready <= 1'b0;
            out_valid <= 1'b0;
            busy <= 1'b0;
            completion <= 1'b0;
            out_payload <= '0;
        end else begin
            completion <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        cmd_ready <= 1'b0;
                        busy <= 1'b1;
                        in_ready <= 1'b1;
                        state <= S_IN;
                    end
                end
                S_IN: begin
                    if (in_valid && in_ready) begin
                        in_ready <= 1'b0;
                        out_payload <= in_payload;
                        out_valid <= 1'b1;
                        state <= S_OUT;
                    end
                end
                S_OUT: begin
                    if (out_valid && out_ready) begin
                        out_valid <= 1'b0;
                        busy <= 1'b0;
                        completion <= 1'b1;
                        cmd_ready <= 1'b1;
                        state <= S_IDLE;
                    end
                end
                default: ;
            endcase
        end
    end
endmodule
"""


def test_arithmetic_blocked_ready_valid_operation_still_gets_traffic(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "ready_valid_smoke_stub.sv").write_text(_RTL_READY_VALID)

    fixture = '''
interface = {"clock": "clk", "reset": "rst", "channels": [], "signals": []}

operation = {
    "operation_name": "unsupported_rv_op",
    "arithmetic": {"classifier_profile": "llm_extension", "reason": "test", "semantics": "test"},
    "dimensions": {},
    "inputs": [{
        "data_object": "A_matrix", "direction": "input", "dimensions": [],
        "data_type": {"width_bits": 32, "signed": True},
        "protocol_profile": "ready_valid",
        "serialization": {"kind": "scalar", "index_order": []},
        "channel": "in",
        "signals": {"valid": "in_valid", "ready": "in_ready", "payload": "in_payload"},
    }],
    "outputs": [{
        "data_object": "Y_matrix", "direction": "output", "dimensions": [],
        "data_type": {"width_bits": 32, "signed": True},
        "protocol_profile": "ready_valid",
        "serialization": {"kind": "scalar", "index_order": []},
        "channel": "out",
        "signals": {"valid": "out_valid", "ready": "out_ready", "payload": "out_payload"},
    }],
    "lifecycle": {
        "job_accept_channels": [{
            "channel": "cmd",
            "signals": {"valid": "cmd_valid", "ready": "cmd_ready", "payload": "opcode"},
            "metadata_fields": [],
            "legal_values": [1],
        }],
        "status_bindings": {"busy": ["busy"], "completion": ["completion"], "error": []},
    },
}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from multigent.verifier_tool.orchestration.campaign import (
    _operation_arithmetic_reasons,
    _operation_protocol_lifecycle_reasons,
    _run_arithmetic_blocked_operation_smoke,
)
from test_fixture import interface, operation

@cocotb.test(timeout_time=50, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    assert _operation_arithmetic_reasons(operation, "unsupported_rv_op") != []
    assert _operation_protocol_lifecycle_reasons(operation, "unsupported_rv_op") == []

    result = await _run_arithmetic_blocked_operation_smoke(
        dut, interface, operation, seed=7, timeout_cycles=2000,
    )
    assert result is None

    assert int(dut.completion.value) == 1
    assert int(dut.busy.value) == 0
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="ready_valid_smoke_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=7, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=120,
    )
    assert result["status"] == "PASS", result
