"""Real-simulator proof that `orchestration/campaign.py`'s custom_mmio
wiring (`_custom_mmio_group`, `run_code_owned_custom_mmio_operation_case`,
`_run_custom_mmio_operation_campaign`) actually drives a DUT end to end:
one command accepted, three inputs read back genuinely out of order over
one custom_mmio group, one output written over a second custom_mmio group,
completion observed, and the final value read back through the shared
`OperationMemoryAdapter` in logical order.

`record_stimulus`/`sample_operation` are stubbed for this test only: they
belong to the pre-existing, protocol-agnostic coverage-tracker/capture-
adapter machinery (already proven for axi4/axi4_lite elsewhere), not to
the new custom_mmio orchestration this test targets. Stubbing them lets
this test inspect exactly the `observed` values that orchestration
produced, without also having to stand up that unrelated machinery.
"""
from __future__ import annotations

import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_RTL = """
module custom_mmio_campaign_stub (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [7:0]  opcode,
    input  logic [31:0] left_ptr,
    input  logic [31:0] right_ptr,
    input  logic [31:0] bias_ptr,
    input  logic [31:0] result_ptr,

    output logic [31:0] req_out_addr,
    output logic [3:0]  req_out_id,
    output logic        req_out_valid,
    input  logic        req_out_ready,

    input  logic [31:0] dat_in_data,
    input  logic        dat_in_last,
    input  logic [3:0]  dat_in_id,
    input  logic        dat_in_valid,
    output logic        dat_in_ready,

    output logic [31:0] wreq_out_addr,
    output logic [3:0]  wreq_out_id,
    output logic        wreq_out_valid,
    input  logic        wreq_out_ready,

    output logic [31:0] wdat_out_data,
    output logic        wdat_out_last,
    output logic [3:0]  wdat_out_id,
    output logic        wdat_out_valid,
    input  logic        wdat_out_ready,

    input  logic [1:0]  ack_in_resp,
    input  logic [3:0]  ack_in_id,
    input  logic        ack_in_valid,
    output logic        ack_in_ready,

    output logic        busy,
    output logic        completion,
    output logic        error
);
    typedef enum logic [3:0] {
        S_IDLE, S_REQ_A, S_REQ_B, S_REQ_BIAS, S_WAIT_DATA,
        S_COMPUTE, S_WREQ, S_WDAT, S_WAIT_ACK
    } state_t;
    state_t state;

    logic signed [7:0]  a_reg, b_reg;
    logic signed [31:0] bias_reg, y_reg;
    logic [2:0]  got_mask;
    logic [31:0] right_ptr_r, bias_ptr_r, result_ptr_r;

    wire signed [31:0] product = 32'(a_reg) * 32'(b_reg);
    wire signed [31:0] biased  = product + bias_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            cmd_ready <= 1'b1;
            req_out_valid <= 1'b0;
            dat_in_ready <= 1'b0;
            wreq_out_valid <= 1'b0;
            wdat_out_valid <= 1'b0;
            ack_in_ready <= 1'b0;
            busy <= 1'b0;
            completion <= 1'b0;
            error <= 1'b0;
            got_mask <= 3'b000;
            a_reg <= '0; b_reg <= '0; bias_reg <= '0; y_reg <= '0;
            req_out_addr <= '0; req_out_id <= '0;
            wreq_out_addr <= '0; wreq_out_id <= '0;
            wdat_out_data <= '0; wdat_out_last <= 1'b0; wdat_out_id <= '0;
            right_ptr_r <= '0; bias_ptr_r <= '0; result_ptr_r <= '0;
        end else begin
            completion <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        // Latch every command field on the one cycle it is
                        // guaranteed valid -- the command driver clears them
                        // right after this beat is accepted, so anything not
                        // captured here (right_ptr/bias_ptr/result_ptr) would
                        // read back as zero on a later cycle.
                        cmd_ready <= 1'b0;
                        busy <= 1'b1;
                        right_ptr_r <= right_ptr;
                        bias_ptr_r <= bias_ptr;
                        result_ptr_r <= result_ptr;
                        got_mask <= 3'b000;
                        req_out_addr <= left_ptr;
                        req_out_id <= 4'd0;
                        req_out_valid <= 1'b1;
                        dat_in_ready <= 1'b1;
                        state <= S_REQ_A;
                    end
                end
                S_REQ_A: begin
                    if (req_out_valid && req_out_ready) begin
                        req_out_addr <= right_ptr_r;
                        req_out_id <= 4'd1;
                        state <= S_REQ_B;
                    end
                end
                S_REQ_B: begin
                    if (req_out_valid && req_out_ready) begin
                        req_out_addr <= bias_ptr_r;
                        req_out_id <= 4'd2;
                        state <= S_REQ_BIAS;
                    end
                end
                S_REQ_BIAS: begin
                    if (req_out_valid && req_out_ready) begin
                        req_out_valid <= 1'b0;
                        state <= S_WAIT_DATA;
                    end
                end
                S_WAIT_DATA: begin
                    if (dat_in_valid && dat_in_ready) begin
                        case (dat_in_id)
                            4'd0: a_reg <= dat_in_data[7:0];
                            4'd1: b_reg <= dat_in_data[7:0];
                            4'd2: bias_reg <= dat_in_data;
                            default: ;
                        endcase
                        got_mask <= got_mask | (3'b001 << dat_in_id);
                        if ((got_mask | (3'b001 << dat_in_id)) == 3'b111) begin
                            dat_in_ready <= 1'b0;
                            state <= S_COMPUTE;
                        end
                    end
                end
                S_COMPUTE: begin
                    y_reg <= biased[31] ? 32'sd0 : biased;
                    wreq_out_addr <= result_ptr_r;
                    wreq_out_id <= 4'd0;
                    wreq_out_valid <= 1'b1;
                    state <= S_WREQ;
                end
                S_WREQ: begin
                    if (wreq_out_valid && wreq_out_ready) begin
                        wreq_out_valid <= 1'b0;
                        wdat_out_data <= y_reg;
                        wdat_out_last <= 1'b1;
                        wdat_out_id <= 4'd0;
                        wdat_out_valid <= 1'b1;
                        state <= S_WDAT;
                    end
                end
                S_WDAT: begin
                    if (wdat_out_valid && wdat_out_ready) begin
                        wdat_out_valid <= 1'b0;
                        ack_in_ready <= 1'b1;
                        state <= S_WAIT_ACK;
                    end
                end
                S_WAIT_ACK: begin
                    if (ack_in_valid && ack_in_ready) begin
                        ack_in_ready <= 1'b0;
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


def test_custom_mmio_campaign_reads_writes_and_completes_out_of_order(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "model.py").write_text("")
    (rtl / "custom_mmio_campaign_stub.sv").write_text(_RTL)

    fixture = '''
def _binding(name, direction, width, group, base_signal):
    return {
        "data_object": name, "direction": direction, "dimensions": [],
        "data_type": {"width_bits": width, "signed": True},
        "memory_mapping": {
            "base_signal": base_signal, "protocol_group": group,
            "word_stride_bytes": 4, "elements_per_word": 1, "bus_width_bits": 32,
            "byte_order": "little", "address_sequence": "contiguous",
        },
    }

operation = {
    "operation_name": "gemm_scalar",
    "dimensions": {},
    "inputs": [
        _binding("A_matrix", "input", 8, "my_mem_r", "left_ptr"),
        _binding("B_matrix", "input", 8, "my_mem_r", "right_ptr"),
        _binding("bias_vector", "input", 32, "my_mem_r", "bias_ptr"),
    ],
    "outputs": [
        _binding("Y_matrix", "output", 32, "my_mem_w", "result_ptr"),
    ],
    "lifecycle": {
        "job_accept_channels": [{
            "channel": "cmd",
            "signals": {"valid": "cmd_valid", "ready": "cmd_ready", "payload": "opcode"},
            "metadata_fields": [
                {"signal": "left_ptr"}, {"signal": "right_ptr"},
                {"signal": "bias_ptr"}, {"signal": "result_ptr"},
            ],
            "legal_values": [1],
        }],
        "status_bindings": {"completion": ["completion"], "busy": ["busy"], "error": ["error"]},
    },
}

case = {"stimulus": {"A_matrix": [5], "B_matrix": [6], "bias_vector": [100]}}

def add_channel(channels, signals, name, kind, direction, fields, *, group):
    channels.append({
        "name": name, "direction": direction, "protocol_profile": "custom_mmio",
        "data_objects": [], "ordering": "any completion order", "framing": "burst",
        "metadata": [f"protocol_group={group} protocol_channel={kind}"],
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

channels = []
signals = [
    {"name": "clk", "role": "clock", "direction": "input", "channel": None},
    {"name": "rst_n", "role": "reset", "direction": "input", "channel": None,
     "semantic": "synchronous active-low reset"},
]
add_channel(channels, signals, "req_out", "request", "output", {
    "addr": ("payload", "address", 32), "id": ("transaction_id", "identifier", 4),
}, group="my_mem_r")
add_channel(channels, signals, "dat_in", "data", "input", {
    "data": ("payload", "data", 32), "last": ("last", "framing", 1),
    "id": ("transaction_id", "identifier", 4),
}, group="my_mem_r")
add_channel(channels, signals, "wreq_out", "request", "output", {
    "addr": ("payload", "address", 32), "id": ("transaction_id", "identifier", 4),
}, group="my_mem_w")
add_channel(channels, signals, "wdat_out", "data", "output", {
    "data": ("payload", "data", 32), "last": ("last", "framing", 1),
    "id": ("transaction_id", "identifier", 4),
}, group="my_mem_w")
add_channel(channels, signals, "ack_in", "response", "input", {
    "resp": ("payload", "response_code", 2), "id": ("transaction_id", "identifier", 4),
}, group="my_mem_w")

interface = {"clock": "clk", "channels": channels, "signals": signals}
'''
    (tests / "test_fixture.py").write_text(fixture)

    code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from multigent.verifier_tool.orchestration import campaign
from test_fixture import interface, operation, case

captured = []

def _stub_record_stimulus(kind, stimulus, expected, label=None, operation_evidence=None,
                           operation_metadata=None, operations=(), observed=None):
    captured.append({"stimulus": dict(stimulus), "observed": dict(observed or {})})
    return f"stub-{len(captured)}"

def _stub_sample_operation(*args, **kwargs):
    return None

campaign.record_stimulus = _stub_record_stimulus
campaign.sample_operation = _stub_sample_operation

@cocotb.test(timeout_time=500, timeout_unit="us")
async def check(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await campaign.initialize_testbench_owned_signals(dut, interface)
    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)

    completed = await campaign._run_custom_mmio_operation_campaign(
        dut, interface, operation, [case], timeout_cycles=5000,
    )

    # One regular case (seed=0) plus the explicit seed=6 out-of-order close,
    # since this operation has 3 (>= 2) inputs -- matching
    # `_run_axi4_operation_campaign`'s own closing-case convention.
    assert completed == 2, completed
    assert len(captured) == 2, captured

    expected_y = 5 * 6 + 100  # product=30, +bias=100 -- no wrap/relu clamp needed
    for entry in captured:
        assert entry["observed"] == {"Y_matrix": [expected_y]}, entry
'''
    (tests / "test_check.py").write_text(code)

    result = run_cocotb_regression(
        rtl_dir=rtl, top_module="custom_mmio_campaign_stub", tests_dir=tests, reference_dir=ref,
        test_modules=["test_check"], seed=1, build_dir=tmp_path / "build",
        report_path=tmp_path / "report.json", timeout_seconds=180,
    )
    assert result["status"] == "PASS", result
