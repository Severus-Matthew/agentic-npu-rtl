"""Real-RTL, contract-generated coverage-bin evidence for the AXI4-Lite
write/read coverage-bin cluster that no existing fixture exercises:
`axi_lite_write_channel_order` (address_first/data_first/same_cycle),
`axi_lite_write_strobe` (all_zero/sparse/full), `axi_lite_address_partition`
(zero/aligned/unaligned/page_edge), and `axi_lite_read_write_concurrency`
(write_only_cycle/read_only_cycle/simultaneous).

This is a minimal, independently-created AXI4-Lite *subordinate* (register
file) with combinational AWREADY/WREADY/ARREADY=1, so the TB has full,
direct control over exact per-cycle AW/W/AR arrival timing without any RTL
backpressure to coordinate around -- the coverage bins above are entirely
about *when* AW/W/AR are driven relative to each other, not about a
correctness property of the register file itself.

Two runs: a 'thorough' TB drives every documented arrival pattern and must
hit every bin in all four templates (positive evidence for all of them at
once). A 'narrow' TB deliberately never drives AW and AR on the same cycle,
proving the coverage plan correctly reports
`channel_group.*.axi_lite_read_write_concurrency.simultaneous` as a required,
reachable, but *unhit* bin when that one exact arrival pattern never occurs
-- the coverage_obligation_not_hit evidence this task's evidence flow calls
for, applied to a coverage-only feature rather than an assertion.
"""

from __future__ import annotations

import json
import shutil

import pytest

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import build_interface_coverage_plan, render_contract_generated_block


pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")


_RTL = """module axi_lite_write_coverage_probe (
    input logic clk, rst,
    input logic awvalid, output logic awready, input logic [31:0] awaddr,
    input logic wvalid, output logic wready, input logic [31:0] wdata, input logic [3:0] wstrb,
    output logic bvalid, input logic bready, output logic [1:0] bresp,
    input logic arvalid, output logic arready, input logic [31:0] araddr,
    output logic rvalid, input logic rready, output logic [31:0] rdata, output logic [1:0] rresp
);
    assign awready = 1'b1;
    assign wready = 1'b1;
    assign arready = 1'b1;
    assign bresp = 2'd0;
    assign rresp = 2'd0;
    assign rdata = 32'hA5A5_A5A5;

    logic aw_seen, w_seen;
    logic b_pending, r_pending;

    assign bvalid = b_pending;
    assign rvalid = r_pending;

    always_ff @(posedge clk) begin
        if (rst) begin
            aw_seen <= 1'b0;
            w_seen <= 1'b0;
            b_pending <= 1'b0;
            r_pending <= 1'b0;
        end else begin
            if (b_pending && bready) b_pending <= 1'b0;
            if (r_pending && rready) r_pending <= 1'b0;
            if (awvalid && awready) aw_seen <= 1'b1;
            if (wvalid && wready) w_seen <= 1'b1;
            // Fire the write response exactly once both sides of this one
            // outstanding write have been seen (on the same cycle or not).
            if (!b_pending) begin
                if ((aw_seen || (awvalid && awready)) && (w_seen || (wvalid && wready))) begin
                    b_pending <= 1'b1;
                    aw_seen <= 1'b0;
                    w_seen <= 1'b0;
                end
            end
            if (arvalid && arready && !r_pending) r_pending <= 1'b1;
        end
    end
endmodule
"""


_TB = """
import cocotb
from cocotb.triggers import Timer
from multigent.verifier_tool import InterfaceCoverageTracker, build_interface_coverage_plan, capture_contract_snapshot

TARGETS = %s
MODE = %r

@cocotb.test(timeout_time=100, timeout_unit="us")
async def verify_axi_lite_write_coverage_cluster(dut):
    plan = build_interface_coverage_plan(CONTRACT_PROTOCOL_STIMULUS_PLAN["interface_contract"])
    tracker = InterfaceCoverageTracker(plan)
    dut.clk.value = 0
    dut.rst.value = 1
    for name in ("awvalid", "awaddr", "wvalid", "wdata", "wstrb", "bready", "arvalid", "araddr", "rready"):
        getattr(dut, name).value = 0

    async def sample():
        await Timer(1, unit="ns")
        snapshot = capture_contract_snapshot(dut, tracker.signal_names)
        tracker.sample_snapshot(snapshot, _check_contract_assertions)
        return snapshot

    async def tick():
        dut.clk.value = 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
        await Timer(5, unit="ns")

    dut.bready.value = 1
    dut.rready.value = 1
    for _ in range(2):
        await sample()
        await tick()
    dut.rst.value = 0

    async def drain(cycles):
        for _ in range(cycles):
            await sample()
            await tick()

    async def write_same_cycle(addr, data, strb):
        dut.awvalid.value = 1
        dut.awaddr.value = addr
        dut.wvalid.value = 1
        dut.wdata.value = data
        dut.wstrb.value = strb
        await sample()
        await tick()
        dut.awvalid.value = 0
        dut.wvalid.value = 0
        await drain(3)

    async def write_address_first(addr, data, strb):
        dut.awvalid.value = 1
        dut.awaddr.value = addr
        await sample()
        await tick()
        dut.awvalid.value = 0
        await drain(2)
        dut.wvalid.value = 1
        dut.wdata.value = data
        dut.wstrb.value = strb
        await sample()
        await tick()
        dut.wvalid.value = 0
        await drain(3)

    async def write_data_first(addr, data, strb):
        dut.wvalid.value = 1
        dut.wdata.value = data
        dut.wstrb.value = strb
        await sample()
        await tick()
        dut.wvalid.value = 0
        await drain(2)
        dut.awvalid.value = 1
        dut.awaddr.value = addr
        await sample()
        await tick()
        dut.awvalid.value = 0
        await drain(3)

    async def read(addr):
        dut.arvalid.value = 1
        dut.araddr.value = addr
        await sample()
        await tick()
        dut.arvalid.value = 0
        await drain(3)

    # Address partition bins: zero, aligned (nonzero, multiple-of-4), unaligned
    # (nonzero low bits), page_edge (first/last word of a 4-KiB page).
    await write_address_first(0x000, 0x11111111, 0xF)   # zero + address_first + full strobe

    if MODE == "no_data_first":
        # Same aligned address + all_zero strobe, but via address_first
        # ordering instead of data_first -- only the data_first channel-order
        # bin is removed, nothing else in this run is affected.
        await write_address_first(0x010, 0x22222222, 0x0)
    else:
        await write_data_first(0x010, 0x22222222, 0x0)   # aligned + data_first + all_zero strobe

    unaligned_addr = 0x018 if MODE == "no_unaligned" else 0x013
    sparse_strb = 0xF if MODE == "no_sparse_strobe" else 0x5
    await write_same_cycle(unaligned_addr, 0x33333333, sparse_strb)  # (unaligned + sparse) unless suppressed above

    await write_same_cycle(0xFFC, 0x44444444, 0xF)       # page_edge (last word of first 4K page)

    if MODE != "no_read_only":
        await read(0x000)  # read_only_cycle

    if MODE != "no_simultaneous":
        # simultaneous: AW and AR transfer on the very same clock edge.
        dut.awvalid.value = 1
        dut.awaddr.value = 0x020
        dut.wvalid.value = 1
        dut.wdata.value = 0x55555555
        dut.wstrb.value = 0xF
        dut.arvalid.value = 1
        dut.araddr.value = 0x004
        await sample()
        await tick()
        dut.awvalid.value = 0
        dut.wvalid.value = 0
        dut.arvalid.value = 0
        await drain(3)
    else:
        # write_only_cycle only, deliberately never overlapped with a read.
        await write_same_cycle(0x020, 0x55555555, 0xF)

    await drain(4)
    _finalize_contract_assertions()
    report = tracker.report()
    assert report["assertion_failures"] == [], report["assertion_failures"]
    for target in TARGETS:
        assert target in report["covered_bins"], f"missing required feature bin {target}"
"""


_ARCHITECTURE = None


def _interface() -> dict:
    channels = [
        {"name": "aw", "direction": "input", "protocol_profile": "axi4_lite", "protocol_group": "ctrl",
         "protocol_channel": "write_address", "data_objects": [], "ordering": "one register", "framing": "one beat"},
        {"name": "w", "direction": "input", "protocol_profile": "axi4_lite", "protocol_group": "ctrl",
         "protocol_channel": "write_data", "data_objects": [], "ordering": "one register", "framing": "one beat"},
        {"name": "b", "direction": "output", "protocol_profile": "axi4_lite", "protocol_group": "ctrl",
         "protocol_channel": "write_response", "data_objects": [], "ordering": "one register", "framing": "one beat"},
        {"name": "ar", "direction": "input", "protocol_profile": "axi4_lite", "protocol_group": "ctrl",
         "protocol_channel": "read_address", "data_objects": [], "ordering": "one register", "framing": "one beat"},
        {"name": "r", "direction": "output", "protocol_profile": "axi4_lite", "protocol_group": "ctrl",
         "protocol_channel": "read_data", "data_objects": [], "ordering": "one register", "framing": "one beat"},
    ]
    signals = [
        {"name": "clk", "role": "clock", "direction": "input", "channel": None},
        {"name": "rst", "role": "reset", "direction": "input", "channel": None, "semantic": "active-high reset"},
        {"name": "awvalid", "role": "valid", "direction": "input", "channel": "aw"},
        {"name": "awready", "role": "ready", "direction": "output", "channel": "aw"},
        {"name": "awaddr", "role": "payload", "semantic_class": "address", "direction": "input",
         "channel": "aw", "width": "32", "protocol_field": "addr"},
        {"name": "wvalid", "role": "valid", "direction": "input", "channel": "w"},
        {"name": "wready", "role": "ready", "direction": "output", "channel": "w"},
        {"name": "wdata", "role": "payload", "semantic_class": "data", "direction": "input",
         "channel": "w", "width": "32", "protocol_field": "data"},
        {"name": "wstrb", "role": "payload", "semantic_class": "byte_enable", "direction": "input",
         "channel": "w", "width": "4", "protocol_field": "strb"},
        {"name": "bvalid", "role": "valid", "direction": "output", "channel": "b"},
        {"name": "bready", "role": "ready", "direction": "input", "channel": "b"},
        {"name": "bresp", "role": "payload", "semantic_class": "response_code", "direction": "output",
         "channel": "b", "width": "2", "protocol_field": "resp"},
        {"name": "arvalid", "role": "valid", "direction": "input", "channel": "ar"},
        {"name": "arready", "role": "ready", "direction": "output", "channel": "ar"},
        {"name": "araddr", "role": "payload", "semantic_class": "address", "direction": "input",
         "channel": "ar", "width": "32", "protocol_field": "addr"},
        {"name": "rvalid", "role": "valid", "direction": "output", "channel": "r"},
        {"name": "rready", "role": "ready", "direction": "input", "channel": "r"},
        {"name": "rdata", "role": "payload", "semantic_class": "data", "direction": "output",
         "channel": "r", "width": "32", "protocol_field": "data"},
        {"name": "rresp", "role": "payload", "semantic_class": "response_code", "direction": "output",
         "channel": "r", "width": "2", "protocol_field": "resp"},
    ]
    return {"clock": "clk", "reset": "rst", "channels": channels, "signals": signals}


def _run(tmp_path, mode: str, targets: list[str]) -> dict:
    path = tmp_path / mode
    rtl, tests, reference = path / "rtl", path / "tests", path / "reference"
    for directory in (rtl, tests, reference):
        directory.mkdir(parents=True)
    (rtl / "axi_lite_write_coverage_probe.sv").write_text(_RTL)
    (reference / "model.py").write_text("")
    interface = _interface()
    source = render_contract_generated_block(build_interface_coverage_plan(interface), _ARCHITECTURE)
    (tests / "test_axi_lite_write_coverage_cluster.py").write_text(
        source + _TB % (json.dumps(targets), mode)
    )
    return run_cocotb_regression(
        rtl_dir=rtl,
        top_module="axi_lite_write_coverage_probe",
        tests_dir=tests,
        reference_dir=reference,
        test_modules=["test_axi_lite_write_coverage_cluster"],
        seed=23,
        build_dir=path / "build",
        report_path=path / "report.json",
        timeout_seconds=120,
    )


_GROUP = "protocol_group.ctrl"

_ALL_TARGETS = [
    f"{_GROUP}.axi_lite_write_channel_order.address_first",
    f"{_GROUP}.axi_lite_write_channel_order.data_first",
    f"{_GROUP}.axi_lite_write_channel_order.same_cycle",
    "channel.w.axi_lite_write_strobe.all_zero",
    "channel.w.axi_lite_write_strobe.sparse",
    "channel.w.axi_lite_write_strobe.full",
    "channel.aw.axi_lite_address_partition.zero",
    "channel.aw.axi_lite_address_partition.aligned",
    "channel.aw.axi_lite_address_partition.unaligned",
    "channel.aw.axi_lite_address_partition.page_edge",
    f"{_GROUP}.axi_lite_read_write_concurrency.write_only_cycle",
    f"{_GROUP}.axi_lite_read_write_concurrency.read_only_cycle",
    f"{_GROUP}.axi_lite_read_write_concurrency.simultaneous",
]


def test_axi_lite_write_coverage_cluster_thorough_run_hits_every_bin(tmp_path):
    good = _run(tmp_path, "thorough", _ALL_TARGETS)
    assert good["status"] == "PASS", good


def test_axi_lite_read_write_concurrency_simultaneous_is_not_hit_when_never_driven(tmp_path):
    narrow = _run(
        tmp_path, "no_simultaneous", [f"{_GROUP}.axi_lite_read_write_concurrency.simultaneous"]
    )
    assert narrow["status"] == "SIMULATION_FAILURE", narrow
    assert (
        f"missing required feature bin {_GROUP}.axi_lite_read_write_concurrency.simultaneous"
        in narrow["stdout"]
    ), narrow["stdout"][-3000:]


def test_axi_lite_write_channel_order_data_first_is_not_hit_when_never_driven(tmp_path):
    narrow = _run(tmp_path, "no_data_first", [f"{_GROUP}.axi_lite_write_channel_order.data_first"])
    assert narrow["status"] == "SIMULATION_FAILURE", narrow
    assert (
        f"missing required feature bin {_GROUP}.axi_lite_write_channel_order.data_first"
        in narrow["stdout"]
    ), narrow["stdout"][-3000:]


def test_axi_lite_write_strobe_sparse_is_not_hit_when_never_driven(tmp_path):
    narrow = _run(tmp_path, "no_sparse_strobe", ["channel.w.axi_lite_write_strobe.sparse"])
    assert narrow["status"] == "SIMULATION_FAILURE", narrow
    assert (
        "missing required feature bin channel.w.axi_lite_write_strobe.sparse" in narrow["stdout"]
    ), narrow["stdout"][-3000:]


def test_axi_lite_address_partition_unaligned_is_not_hit_when_never_driven(tmp_path):
    narrow = _run(tmp_path, "no_unaligned", ["channel.aw.axi_lite_address_partition.unaligned"])
    assert narrow["status"] == "SIMULATION_FAILURE", narrow
    assert (
        "missing required feature bin channel.aw.axi_lite_address_partition.unaligned"
        in narrow["stdout"]
    ), narrow["stdout"][-3000:]


def test_axi_lite_read_write_concurrency_read_only_cycle_is_not_hit_when_never_driven(tmp_path):
    narrow = _run(
        tmp_path, "no_read_only", [f"{_GROUP}.axi_lite_read_write_concurrency.read_only_cycle"]
    )
    assert narrow["status"] == "SIMULATION_FAILURE", narrow
    assert (
        f"missing required feature bin {_GROUP}.axi_lite_read_write_concurrency.read_only_cycle"
        in narrow["stdout"]
    ), narrow["stdout"][-3000:]
