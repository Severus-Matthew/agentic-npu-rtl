"""Run a named HLS mutant through the normal generated TB and a saved PASS baseline.

This is local-only qualification: no agent/API call and no production RTL edit.
The positive baseline must contain the identical generated test and plan.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .generated_mutation_qualification import RTL_DIR, _simulate
from .qualification_common import (
    materialize_baseline_generated_pair,
    sha256,
    validate_positive_baseline,
)
from multigent.verifier_tool.protocol.stimulus.drivers.fault_injection import (
    FAULT_PLAN_ENV,
)


# Exact RTL substitutions keep mutant intent reviewable and reject source drift.
MUTANTS = {
    "a_reserved_burst": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_BUS_ARBURST  = 2'b01;",
        "assign out_BUS_ARBURST  = 2'b11;",
        "feature=protocol.gmem_a.legal_burst_encoding",
    ),
    "b_reserved_burst": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_BUS_ARBURST  = 2'b01;",
        "assign out_BUS_ARBURST  = 2'b11;",
        "feature=protocol.gmem_b.legal_burst_encoding",
    ),
    "c_reserved_burst": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWBURST  = 2'b01;",
        "assign out_BUS_AWBURST  = 2'b11;",
        "feature=protocol.gmem_c.legal_burst_encoding",
    ),
    "a_oversize_transfer": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_BUS_ARSIZE   = BUS_ADDR_ALIGN;",
        "assign out_BUS_ARSIZE   = 3'b111;",
        "feature=protocol.gmem_a.transfer_size_within_data_bus",
    ),
    "b_oversize_transfer": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_BUS_ARSIZE   = BUS_ADDR_ALIGN;",
        "assign out_BUS_ARSIZE   = 3'b111;",
        "feature=protocol.gmem_b.transfer_size_within_data_bus",
    ),
    "c_oversize_transfer": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWSIZE   = BUS_ADDR_ALIGN;",
        "assign out_BUS_AWSIZE   = 3'b111;",
        "feature=protocol.gmem_c.transfer_size_within_data_bus",
    ),
    "c_missing_wlast": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_WLAST = data_out[DATA_WIDTH+DATA_WIDTH/8];",
        "assign out_BUS_WLAST  = 1'b0;",
        "feature=protocol.gmem_c.write_last_matches_length",
    ),
    "c_write_length_off_by_one": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWLEN  = rs_req_out[ADDR_WIDTH+7 : ADDR_WIDTH];",
        "assign out_BUS_AWLEN  = rs_req_out[ADDR_WIDTH+7 : ADDR_WIDTH] + 1'b1;",
        "feature=protocol.gmem_c.no_4k_boundary_crossing",
    ),
    "a_fixed_burst_over_16": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_BUS_ARBURST  = 2'b01;",
        "assign out_BUS_ARBURST  = 2'b00;",
        "feature=protocol.gmem_a.legal_burst_length",
    ),
    "b_fixed_burst_over_16": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_BUS_ARBURST  = 2'b01;",
        "assign out_BUS_ARBURST  = 2'b00;",
        "feature=protocol.gmem_b.legal_burst_length",
    ),
    "c_fixed_burst_over_16": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWBURST  = 2'b01;",
        "assign out_BUS_AWBURST  = 2'b00;",
        "feature=protocol.gmem_c.legal_burst_length",
    ),
    "c_narrow_transfer_full_strobe": {
        "diagnostic": "feature=protocol.gmem_c.write_strobe_within_active_lanes",
        "edits": [(
            "int8_gemm_gmem_c_m_axi.v",
            "assign out_BUS_AWSIZE   = BUS_ADDR_ALIGN;",
            "assign out_BUS_AWSIZE   = 3'b101;",
            1,
        )],
        "simulation_fault_plan": {
            "schema_version": 1,
            "profile": "axi4",
            "group": "gmem_c",
            "fault": "accept_invalid_write_strobe_for_checker",
            "occurrence": 1,
        },
    },
    "a_read_crosses_4k": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_BURST_ADDR  = addr_buf;",
        "assign out_BURST_ADDR  = {addr_buf[ADDR_WIDTH-1:12], 12'hfe0};",
        "feature=protocol.gmem_a.no_4k_boundary_crossing",
    ),
    "b_read_crosses_4k": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_BURST_ADDR  = sect_addr_buf;",
        "assign out_BURST_ADDR  = {sect_addr_buf[ADDR_WIDTH-1:12], 12'hfe0};",
        "feature=protocol.gmem_b.no_4k_boundary_crossing",
    ),
    "a_ar_content_changes_during_stall": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_BURST_ADDR  = addr_buf;",
        """reg [ADDR_WIDTH-1:0] mutant_stall_counter;
        always @(posedge clk) begin
            if (reset)
                mutant_stall_counter <= 0;
            else if (clk_en && burst_valid && !in_BURST_READY)
                mutant_stall_counter <= mutant_stall_counter + 1'b1;
        end
        assign out_BURST_ADDR  = addr_buf +
            ((burst_valid && !in_BURST_READY) ? mutant_stall_counter : {ADDR_WIDTH{1'b0}});""",
        "feature=channel.m_axi_gmem_a_ar.stall_stability",
    ),
    "b_ar_content_changes_during_stall": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_BURST_ADDR  = sect_addr_buf;",
        """reg [ADDR_WIDTH-1:0] mutant_stall_counter;
        always @(posedge clk) begin
            if (reset)
                mutant_stall_counter <= 0;
            else if (burst_valid && !in_BURST_READY)
                mutant_stall_counter <= mutant_stall_counter + 1'b1;
        end
        assign out_BURST_ADDR  = sect_addr_buf +
            ((burst_valid && !in_BURST_READY) ? mutant_stall_counter : {ADDR_WIDTH{1'b0}});""",
        "feature=channel.m_axi_gmem_b_ar.stall_stability",
    ),
    "c_aw_content_changes_during_stall": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_AWADDR = rs_req_out[ADDR_WIDTH-1 : 0];",
        """reg [ADDR_WIDTH-1:0] mutant_stall_counter;
        always @(posedge clk) begin
            if (reset)
                mutant_stall_counter <= 0;
            else if (out_BUS_AWVALID && !in_BUS_AWREADY)
                mutant_stall_counter <= mutant_stall_counter + 1'b1;
        end
        assign out_BUS_AWADDR = rs_req_out[ADDR_WIDTH-1 : 0] +
            ((out_BUS_AWVALID && !in_BUS_AWREADY) ? mutant_stall_counter : {ADDR_WIDTH{1'b0}});""",
        "feature=channel.m_axi_gmem_c_aw.stall_stability",
    ),
    "c_w_content_changes_during_stall": (
        "int8_gemm_gmem_c_m_axi.v",
        "assign out_BUS_WDATA = data_out[DATA_WIDTH-1 : 0];",
        """reg [DATA_WIDTH-1:0] mutant_w_stall_counter;
        always @(posedge clk) begin
            if (reset)
                mutant_w_stall_counter <= 0;
            else if (clk_en && fifo_valid && data_en && flying_req && !in_BUS_WREADY)
                mutant_w_stall_counter <= mutant_w_stall_counter + 1'b1;
        end
        assign out_BUS_WDATA = data_out[DATA_WIDTH-1 : 0] + mutant_w_stall_counter;""",
        "feature=channel.m_axi_gmem_c_w.stall_stability",
    ),
    "multiply_becomes_add": (
        "int8_gemm_mul_27s_8s_35_3_1.v",
        "assign tmp_product = $signed(din0_reg) * $signed(din1_reg);",
        "assign tmp_product = $signed(din0_reg) + $signed(din1_reg);",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "multiply_unsigned_rhs": (
        "int8_gemm_mul_27s_8s_35_3_1.v",
        "assign tmp_product = $signed(din0_reg) * $signed(din1_reg);",
        "assign tmp_product = $signed(din0_reg) * $unsigned(din1_reg);",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "a_read_payload_bit_flip": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_HLS_RDATA  = tmp_data;",
        "assign out_HLS_RDATA  = {tmp_data[BUS_DATA_WIDTH-1:1], ~tmp_data[0]};",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "b_read_payload_bit_flip": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_HLS_RDATA  = tmp_data;",
        "assign out_HLS_RDATA  = {tmp_data[BUS_DATA_WIDTH-1:1], ~tmp_data[0]};",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "output_lane_rotation": (
        "int8_gemm.v",
        ".I_WDATA(grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA),",
        ".I_WDATA({grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA[479:0], "
        "grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA[511:480]}),",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "output_upper_lanes_zero": (
        "int8_gemm.v",
        ".I_WDATA(grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA),",
        ".I_WDATA({256'd0, grp_int8_gemm_Pipeline_store_rows_store_tiles_store_words_fu_1337_m_axi_gmem_c_WDATA[255:0]}),",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "accumulator_subtracts_product": (
        "int8_gemm_p_anonymous_namespace_compute_tile_0_Pipeline_systolic_cycles.v",
        "assign even_accum_fu_60476_p2 = ($signed(sext_ln105_fu_60473_p1) + $signed(empty_fu_3306));",
        "assign even_accum_fu_60476_p2 = ($signed(sext_ln105_fu_60473_p1) - $signed(empty_fu_3306));",
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm",
    ),
    "early_ap_done": (
        "int8_gemm_control_s_axi.v",
        "rdata[1] <= int_task_ap_done;",
        "rdata[1] <= 1'b1;",
        "feature=lifecycle.gemm.completion_matches_final_output",
    ),
    "control_b_reserved_response": (
        "int8_gemm_control_s_axi.v",
        "assign BRESP   = 2'b00;  // OKAY",
        "assign BRESP   = ARESET ? 2'b00 : 2'b01;  // AXI4-Lite forbids EXOKAY",
        "feature=protocol.control.legal_lite_response_encoding",
    ),
    "control_r_reserved_response": (
        "int8_gemm_control_s_axi.v",
        "assign RRESP   = 2'b00;  // OKAY",
        "assign RRESP   = ARESET ? 2'b00 : 2'b01;  // AXI4-Lite forbids EXOKAY",
        "feature=protocol.control.legal_lite_response_encoding",
    ),
    "control_b_before_aw_w": (
        "int8_gemm_control_s_axi.v",
        "assign BVALID  = (wstate == WRRESP);",
        "assign BVALID  = ARESET ? 1'b0 : 1'b1;  // Response without AW and W",
        "feature=protocol.control.write_response_after_address_and_data",
    ),
    "control_r_before_ar": (
        "int8_gemm_control_s_axi.v",
        "assign RVALID  = (rstate == RDDATA);",
        "assign RVALID  = ARESET ? 1'b0 : 1'b1;  // Response without AR",
        "feature=protocol.control.read_response_after_address",
    ),
    "control_b_content_changes_during_stall": (
        "int8_gemm_control_s_axi.v",
        "assign BRESP   = 2'b00;  // OKAY",
        """reg mutant_b_stall_toggle;
always @(posedge ACLK) begin
    if (ARESET)
        mutant_b_stall_toggle <= 1'b0;
    else if (ACLK_EN && BVALID && !BREADY)
        mutant_b_stall_toggle <= ~mutant_b_stall_toggle;
end
assign BRESP   = mutant_b_stall_toggle ? 2'b10 : 2'b00;""",
        "feature=channel.s_axi_control_b.stall_stability",
    ),
    "control_r_content_changes_during_stall": (
        "int8_gemm_control_s_axi.v",
        "assign RDATA   = rdata;",
        """reg mutant_r_stall_toggle;
always @(posedge ACLK) begin
    if (ARESET)
        mutant_r_stall_toggle <= 1'b0;
    else if (ACLK_EN && RVALID && !RREADY)
        mutant_r_stall_toggle <= ~mutant_r_stall_toggle;
end
assign RDATA   = rdata ^ {32{mutant_r_stall_toggle}};""",
        "feature=channel.s_axi_control_r.stall_stability",
    ),
    "a_arvalid_during_reset": (
        "int8_gemm_gmem_a_m_axi.v",
        "assign out_BURST_VALID = burst_valid;",
        "assign out_BURST_VALID = reset ? 1'b1 : burst_valid;",
        "feature=protocol.gmem_a.valid_low_during_reset",
        2,
    ),
    "b_arvalid_during_reset": (
        "int8_gemm_gmem_b_m_axi.v",
        "assign out_BURST_VALID = burst_valid;",
        "assign out_BURST_VALID = reset ? 1'b1 : burst_valid;",
        "feature=protocol.gmem_b.valid_low_during_reset",
        2,
    ),
    "c_awvalid_during_reset": {
        "diagnostic": "feature=protocol.gmem_c.valid_low_during_reset",
        "edits": [
            (
                "int8_gemm_gmem_c_m_axi.v",
                ".out_BUS_AWVALID (out_BUS_AWVALID),",
                ".out_BUS_AWVALID (mutant_awvalid_internal),",
                1,
            ),
            (
                "int8_gemm_gmem_c_m_axi.v",
                "    // burst converter\n    assign out_BUS_AWID     = 0;",
                """    // Qualification mutant: violate VALID-low-during-reset at the external AXI boundary.
    wire mutant_awvalid_internal;
    assign out_BUS_AWVALID = ARESET ? 1'b1 : mutant_awvalid_internal;

    // burst converter
    assign out_BUS_AWID     = 0;""",
                1,
            ),
        ],
    },
    "control_bvalid_during_reset": (
        "int8_gemm_control_s_axi.v",
        "assign BVALID  = (wstate == WRRESP);",
        """reg [3:0] mutant_reset_cycles;
reg [3:0] mutant_reset_epoch;
always @(posedge ACLK) begin
    if (ARESET) begin
        mutant_reset_cycles <= mutant_reset_cycles + 1'b1;
    end else begin
        if (mutant_reset_cycles != 0)
            mutant_reset_epoch <= mutant_reset_epoch + 1'b1;
        mutant_reset_cycles <= 4'd0;
    end
end
assign BVALID  = (ARESET && mutant_reset_epoch != 0) ? 1'b1 : (wstate == WRRESP);""",
        "feature=protocol.control.valid_low_during_reset",
    ),
    "control_bresp_nonzero_during_reset": (
        "int8_gemm_control_s_axi.v",
        "assign BRESP   = 2'b00;  // OKAY",
        "assign BRESP   = ARESET ? 2'b10 : 2'b00;  // Legal SLVERR, wrong declared reset value",
        "feature=lifecycle.reset.outputs_match_declared_reset_values",
    ),
    "a_invalid_wrap_length": {
        "diagnostic": "feature=protocol.gmem_a.wrap_length_and_alignment",
        "edits": [
            ("int8_gemm_gmem_a_m_axi.v", "assign out_BUS_ARBURST  = 2'b01;", "assign out_BUS_ARBURST  = 2'b10;", 1),
            ("int8_gemm_gmem_a_m_axi.v", "assign out_BURST_LEN   = len_buf;", "assign out_BURST_LEN   = 8'd2;", 1),
        ],
    },
    "b_invalid_wrap_length": {
        "diagnostic": "feature=protocol.gmem_b.wrap_length_and_alignment",
        "edits": [
            ("int8_gemm_gmem_b_m_axi.v", "assign out_BUS_ARBURST  = 2'b01;", "assign out_BUS_ARBURST  = 2'b10;", 1),
            ("int8_gemm_gmem_b_m_axi.v", "assign out_BURST_LEN   = sect_len_buf;", "assign out_BURST_LEN   = 8'd2;", 1),
        ],
    },
    "c_invalid_wrap_length": {
        "diagnostic": "feature=protocol.gmem_c.wrap_length_and_alignment",
        "edits": [
            ("int8_gemm_gmem_c_m_axi.v", "assign out_BUS_AWBURST  = 2'b01;", "assign out_BUS_AWBURST  = 2'b10;", 1),
            ("int8_gemm_gmem_c_m_axi.v", "assign out_BURST_LEN   = sect_len_buf;", "assign out_BURST_LEN   = 8'd2;", 1),
        ],
    },
}


def mutant_parts(spec: tuple) -> tuple[str, str, str, str, int]:
    """Normalize legacy four-field and counted five-field mutant specs."""

    if len(spec) == 4:
        file_name, anchor, replacement, diagnostic = spec
        return file_name, anchor, replacement, diagnostic, 1
    file_name, anchor, replacement, diagnostic, expected_count = spec
    return file_name, anchor, replacement, diagnostic, int(expected_count)


def mutant_definition(spec: object) -> tuple[list[tuple[str, str, str, int]], str]:
    """Return all exact edits plus the required diagnostic for one mutant."""

    if isinstance(spec, dict):
        edits = [
            (str(file_name), str(anchor), str(replacement), int(expected_count))
            for file_name, anchor, replacement, expected_count in spec["edits"]
        ]
        return edits, str(spec["diagnostic"])
    file_name, anchor, replacement, diagnostic, expected_count = mutant_parts(spec)
    return [(file_name, anchor, replacement, expected_count)], diagnostic


def qualify_named_mutant(
    name: str, output_dir: Path, *, baseline_dir: Path, baseline_generated: Path,
) -> dict[str, object]:
    if name not in MUTANTS:
        raise ValueError(f"unknown benchmark mutant {name!r}")
    generated = output_dir / "generated"
    materialize_baseline_generated_pair(baseline_generated, generated)
    baseline = validate_positive_baseline(
        baseline_dir, baseline_generated, generated
    )

    edits, diagnostic = mutant_definition(MUTANTS[name])
    mutant_rtl = output_dir / "mutated_rtl"
    shutil.copytree(RTL_DIR, mutant_rtl)
    for file_name, anchor, replacement, expected_count in edits:
        target = mutant_rtl / file_name
        source = target.read_text()
        if source.count(anchor) != expected_count:
            raise AssertionError(f"{name} mutation anchor is absent or ambiguous in {file_name}")
        target.write_text(source.replace(anchor, replacement))
    simulation_env = None
    spec = MUTANTS[name]
    if isinstance(spec, dict) and spec.get("simulation_fault_plan"):
        fault_plan_path = output_dir / "protocol_fault_plan.json"
        fault_plan_path.write_text(
            json.dumps(spec["simulation_fault_plan"], indent=2), encoding="utf-8"
        )
        simulation_env = {FAULT_PLAN_ENV: str(fault_plan_path.resolve())}
    mutant = _simulate(
        mutant_rtl,
        generated,
        output_dir / "mutant",
        simulation_env=simulation_env,
    )
    precise_failure = (
        mutant["status"] == "SIMULATION_FAILURE"
        and diagnostic.lower() in mutant["stdout"].lower()
    )
    summary = {
        "name": name,
        "status": "QUALIFIED" if precise_failure else "UNQUALIFIED",
        "expected_diagnostic": diagnostic,
        "mutant_precise_failure": precise_failure,
        "baseline_complete": baseline["complete"],
        "baseline_dir": str(baseline_dir),
        "generated_test_sha256": sha256(generated / "test_gemm_automatic.py"),
        "mutant": {key: value for key, value in mutant.items() if key != "stdout"},
    }
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=sorted(MUTANTS))
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--baseline-generated", type=Path, required=True)
    args = parser.parse_args()
    summary = qualify_named_mutant(
        args.name, args.output_dir,
        baseline_dir=args.baseline_dir,
        baseline_generated=args.baseline_generated,
    )
    print(json.dumps({key: summary[key] for key in (
        "name", "status", "expected_diagnostic", "mutant_precise_failure",
        "baseline_complete", "generated_test_sha256",
    )}, indent=2))
