"""Independent real-Verilator mutations of the frozen Vitis-HLS GEMM RTL.

Every variant starts from a fresh temporary copy of gemm_golden/. The same
contract-bound operation driver, golden result, protocol monitor, and
lifecycle monitor from test_int8_gemm_hls_golden run against each copy.
No production RTL or Architect/Verifier agent is changed or invoked.
"""

from __future__ import annotations

import pytest

from multigent.verifier_tool.tool_regression.rtl.test_int8_gemm_hls_golden import (
    GEMM_GOLDEN_RTL,
    run_hls_gemm_case,
)


# (name, domain, relative RTL file, exact original, replacement, expected signal)
MUTANTS = [
    (
        "multiply_becomes_add", "operation", "int8_gemm_mul_27s_8s_35_3_1.v",
        "assign tmp_product = $signed(din0_reg) * $signed(din1_reg);",
        "assign tmp_product = $signed(din0_reg) + $signed(din1_reg);",
        "mismatch at first diff index",
    ),
    (
        "multiply_unsigned_rhs", "operation", "int8_gemm_mul_27s_8s_35_3_1.v",
        "assign tmp_product = $signed(din0_reg) * $signed(din1_reg);",
        "assign tmp_product = $signed(din0_reg) * $unsigned(din1_reg);",
        "mismatch at first diff index",
    ),
    (
        "a_read_payload_bit_flip", "operation", "int8_gemm_gmem_a_m_axi.v",
        "assign out_HLS_RDATA  = tmp_data;",
        "assign out_HLS_RDATA  = {tmp_data[BUS_DATA_WIDTH-1:1], ~tmp_data[0]};",
        "mismatch at first diff index",
    ),
    (
        "b_read_payload_bit_flip", "operation", "int8_gemm_gmem_b_m_axi.v",
        "assign out_HLS_RDATA  = tmp_data;",
        "assign out_HLS_RDATA  = {tmp_data[BUS_DATA_WIDTH-1:1], ~tmp_data[0]};",
        "mismatch at first diff index",
    ),
    (
        "output_lane_rotation", "operation", "int8_gemm.v",
        ".I_WDATA(grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA),",
        ".I_WDATA({grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA[479:0], "
        "grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA[511:480]}),",
        "mismatch at first diff index",
    ),
    (
        "output_upper_lanes_zero", "operation", "int8_gemm.v",
        ".I_WDATA(grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA),",
        ".I_WDATA({256'd0, grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA[255:0]}),",
        "mismatch at first diff index",
    ),
    (
        "start_ignored", "lifecycle", "int8_gemm_control_s_axi.v",
        "assign ap_start      = int_ap_start;",
        "assign ap_start      = 1'b0;",
        "accepted_command_starts_job",
    ),
    (
        "a_pointer_aliases_b", "lifecycle", "int8_gemm_control_s_axi.v",
        "assign a             = int_a;",
        "assign a             = int_b;",
        "expected range",
    ),
    (
        "b_pointer_aliases_a", "lifecycle", "int8_gemm_control_s_axi.v",
        "assign b             = int_b;",
        "assign b             = int_a;",
        "expected range",
    ),
    (
        "read_reserved_burst", "protocol", "int8_gemm_gmem_a_m_axi.v",
        "assign out_BUS_ARBURST  = 2'b01;",
        "assign out_BUS_ARBURST  = 2'b11;",
        "legal_burst_encoding",
    ),
    (
        "write_reserved_burst", "protocol", "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWBURST  = 2'b01;",
        "assign out_BUS_AWBURST  = 2'b11;",
        "legal_burst_encoding",
    ),
    (
        "write_transfer_size_exceeds_bus", "protocol", "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWSIZE   = BUS_ADDR_ALIGN;",
        "assign out_BUS_AWSIZE   = 3'b111;",
        "transfer_size_within_data_bus",
    ),
    (
        "write_length_off_by_one", "protocol", "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWLEN  = rs_req_out[ADDR_WIDTH+7 : ADDR_WIDTH];",
        "assign out_BUS_AWLEN  = rs_req_out[ADDR_WIDTH+7 : ADDR_WIDTH] + 1'b1;",
        "no_4k_boundary_crossing",
    ),
    (
        "write_last_missing", "protocol", "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_WLAST = data_out[DATA_WIDTH+DATA_WIDTH/8];",
        "assign out_BUS_WLAST  = 1'b0;",
        "write_last_matches_length",
    ),
    (
        "write_strobes_zero", "protocol", "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_WSTRB = data_out[DATA_WIDTH+DATA_WIDTH/8-1 : DATA_WIDTH];",
        "assign out_BUS_WSTRB = '0;",
        "DUT emitted WSTRB=0x0",
    ),
    (
        "accumulator_subtracts_product", "operation",
        "int8_gemm_p_anonymous_namespace_compute_tile_0_Pipeline_systolic_cycles.v",
        "assign even_accum_fu_60476_p2 = ($signed(sext_ln105_fu_60473_p1) + $signed(empty_fu_3306));",
        "assign even_accum_fu_60476_p2 = ($signed(sext_ln105_fu_60473_p1) - $signed(empty_fu_3306));",
        "mismatch at first diff index",
    ),
    (
        "ap_done_stuck_low", "lifecycle", "int8_gemm_control_s_axi.v",
        "rdata[1] <= int_task_ap_done;",
        "rdata[1] <= 1'b0;",
        "SimTimeoutError",
    ),
    (
        "spurious_start", "lifecycle", "int8_gemm_control_s_axi.v",
        "assign ap_start      = int_ap_start;",
        "assign ap_start      = 1'b1;",
        "expected range",
    ),
    (
        "read_transfer_size_exceeds_bus", "protocol", "int8_gemm_gmem_a_m_axi.v",
        "assign out_BUS_ARSIZE   = BUS_ADDR_ALIGN;",
        "assign out_BUS_ARSIZE   = 3'b111;",
        "transfer_size_within_data_bus",
    ),
    (
        "write_address_shift", "protocol", "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWADDR = rs_req_out[ADDR_WIDTH-1 : 0];",
        "assign out_BUS_AWADDR = rs_req_out[ADDR_WIDTH-1 : 0] + 64;",
        "no_4k_boundary_crossing",
    ),
]


@pytest.mark.skipif(not GEMM_GOLDEN_RTL.is_dir(), reason="real gemm_golden RTL not present")
@pytest.mark.parametrize(
    "name,domain,relative_path,anchor,replacement,expected",
    MUTANTS,
    ids=[item[0] for item in MUTANTS],
)
def test_real_hls_gemm_mutant_is_rejected(
    tmp_path, name, domain, relative_path, anchor, replacement, expected,
):
    result = run_hls_gemm_case(tmp_path, (relative_path, anchor, replacement))
    diagnostic = result.get("stdout", "") + result.get("stderr", "")
    assert result["status"] == "SIMULATION_FAILURE", (
        f"{name} ({domain}) unexpectedly got {result['status']}; "
        f"report={tmp_path / 'report.json'}; tail={diagnostic[-3000:]}"
    )
    assert expected.lower() in diagnostic.lower(), (
        f"{name} ({domain}) failed for the wrong reason; "
        f"expected={expected!r}; report={tmp_path / 'report.json'}; "
        f"tail={diagnostic[-5000:]}"
    )
