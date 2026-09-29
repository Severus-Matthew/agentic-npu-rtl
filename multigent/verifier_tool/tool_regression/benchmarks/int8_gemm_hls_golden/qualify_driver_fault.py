"""Qualify environment-owned protocol faults with the generated HLS TB.

Unlike :mod:`qualify_named_mutant`, this runner does not edit RTL.  It gives
the reusable AXI4 memory driver one closed fault plan while leaving the frozen
contract, generated assertions, coverage plan, operation campaign, and golden
model byte-identical to the saved positive baseline.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from .protocol_fault_plan import (
    FAULT_PLAN_ENV,
    validate_protocol_fault_plan,
)

from .generated_mutation_qualification import RTL_DIR, _simulate
from .fault_bootstrap import write_sitecustomize
from .qualification_common import (
    diagnostic_excerpt,
    materialize_baseline_generated_pair,
    sha256,
    validate_positive_baseline,
)


DRIVER_FAULTS: dict[str, dict[str, Any]] = {
    "a_response_before_request": {
        "group": "gmem_a", "fault": "present_response_before_request",
        "diagnostic": "feature=protocol.gmem_a.response_after_request",
    },
    "a_response_id_mismatch": {
        "group": "gmem_a", "fault": "return_nonmatching_id",
        "diagnostic": "feature=protocol.gmem_a.response_id_matches_request",
    },
    "a_read_last_mismatch": {
        "group": "gmem_a", "fault": "invert_rlast_on_nonfinal_or_final_beat",
        "diagnostic": "feature=protocol.gmem_a.read_last_matches_length",
    },
    "a_nonexclusive_exokay": {
        "group": "gmem_a", "fault": "return_exokay_for_nonexclusive_request",
        "diagnostic": "feature=protocol.gmem_a.exclusive_response_consistency",
    },
    "b_response_before_request": {
        "group": "gmem_b", "fault": "present_response_before_request",
        "diagnostic": "feature=protocol.gmem_b.response_after_request",
    },
    "b_response_id_mismatch": {
        "group": "gmem_b", "fault": "return_nonmatching_id",
        "diagnostic": "feature=protocol.gmem_b.response_id_matches_request",
    },
    "b_read_last_mismatch": {
        "group": "gmem_b", "fault": "invert_rlast_on_nonfinal_or_final_beat",
        "diagnostic": "feature=protocol.gmem_b.read_last_matches_length",
    },
    "b_nonexclusive_exokay": {
        "group": "gmem_b", "fault": "return_exokay_for_nonexclusive_request",
        "diagnostic": "feature=protocol.gmem_b.exclusive_response_consistency",
    },
    "c_response_before_request": {
        "group": "gmem_c", "fault": "present_response_before_request",
        "diagnostic": "feature=protocol.gmem_c.response_after_request",
    },
    "c_response_id_mismatch": {
        "group": "gmem_c", "fault": "return_nonmatching_id",
        "diagnostic": "feature=protocol.gmem_c.response_id_matches_request",
    },
    "c_nonexclusive_exokay": {
        "group": "gmem_c", "fault": "return_exokay_for_nonexclusive_request",
        "diagnostic": "feature=protocol.gmem_c.exclusive_response_consistency",
    },
    "a_same_id_response_reorder": {
        "group": "gmem_a", "fault": "attempt_same_id_response_reorder",
        "occurrence": 2,
        "diagnostic": "feature=protocol.gmem_a.response_order_preserved_per_id",
    },
    "b_same_id_response_reorder": {
        "group": "gmem_b", "fault": "attempt_same_id_response_reorder",
        "occurrence": 2,
        "diagnostic": "feature=protocol.gmem_b.response_order_preserved_per_id",
    },
    "c_same_id_response_reorder": {
        "group": "gmem_c", "fault": "attempt_same_id_response_reorder",
        "occurrence": 2,
        "diagnostic": "feature=protocol.gmem_c.response_order_preserved_per_id",
    },
    "control_unpaired_write_channel": {
        "profile": "axi4_lite",
        "group": "control",
        "channel": "write_address",
        "fault": "attempt_unpaired_write_channel",
        "diagnostic": "feature=protocol.control.write_address_and_data_are_independent",
    },
    "a_read_content_changes_on_release": {
        "group": "gmem_a", "fault": "change_content_on_ready_release",
        "diagnostic": "feature=channel.m_axi_gmem_a_r.stall_stability",
        "scenario_edits": [
            (
                "int8_gemm_gmem_a_m_axi.v",
                "//------------------------R channel begin----------------\n//------------------------Instantiation------------------",
                """//------------------------R channel begin----------------
    wire qualification_rready_internal;
    reg [2:0] qualification_r_stall_cycles;
    wire qualification_rready_enable = qualification_r_stall_cycles >= 3;
    assign out_BUS_RREADY = qualification_rready_internal && qualification_rready_enable;
    always @(posedge ACLK) begin
        if (ARESET)
            qualification_r_stall_cycles <= 0;
        else if (in_BUS_RVALID && qualification_r_stall_cycles < 3)
            qualification_r_stall_cycles <= qualification_r_stall_cycles + 1'b1;
    end
//------------------------Instantiation------------------""",
                1,
            ),
            (
                "int8_gemm_gmem_a_m_axi.v",
                "        .s_valid        (in_BUS_RVALID),\n        .s_ready        (out_BUS_RREADY),",
                "        .s_valid        (in_BUS_RVALID && qualification_rready_enable),\n        .s_ready        (qualification_rready_internal),",
                1,
            ),
        ],
    },
    "b_read_content_changes_on_release": {
        "group": "gmem_b", "fault": "change_content_on_ready_release",
        "diagnostic": "feature=channel.m_axi_gmem_b_r.stall_stability",
        "scenario_edits": [
            (
                "int8_gemm_gmem_b_m_axi.v",
                "//------------------------R channel begin----------------\n//------------------------Instantiation------------------",
                """//------------------------R channel begin----------------
    wire qualification_rready_internal;
    reg [2:0] qualification_r_stall_cycles;
    wire qualification_rready_enable = qualification_r_stall_cycles >= 3;
    assign out_BUS_RREADY = qualification_rready_internal && qualification_rready_enable;
    always @(posedge ACLK) begin
        if (ARESET)
            qualification_r_stall_cycles <= 0;
        else if (in_BUS_RVALID && qualification_r_stall_cycles < 3)
            qualification_r_stall_cycles <= qualification_r_stall_cycles + 1'b1;
    end
//------------------------Instantiation------------------""",
                1,
            ),
            (
                "int8_gemm_gmem_b_m_axi.v",
                "        .s_valid        (in_BUS_RVALID),\n        .s_ready        (out_BUS_RREADY),",
                "        .s_valid        (in_BUS_RVALID && qualification_rready_enable),\n        .s_ready        (qualification_rready_internal),",
                1,
            ),
        ],
    },
    "c_write_response_content_changes_on_release": {
        "group": "gmem_c", "fault": "change_content_on_ready_release",
        "diagnostic": "feature=channel.m_axi_gmem_c_b.stall_stability",
        "scenario_edits": [
            (
                "int8_gemm_gmem_c_m_axi.v",
                "//------------------------B channel begin----------------\n//------------------------Instantiation------------------",
                """//------------------------B channel begin----------------
    wire qualification_bready_internal;
    reg [2:0] qualification_b_stall_cycles;
    wire qualification_bready_enable = qualification_b_stall_cycles >= 3;
    assign out_BUS_BREADY = qualification_bready_internal && qualification_bready_enable;
    always @(posedge ACLK) begin
        if (ARESET)
            qualification_b_stall_cycles <= 0;
        else if (in_BUS_BVALID && qualification_b_stall_cycles < 3)
            qualification_b_stall_cycles <= qualification_b_stall_cycles + 1'b1;
    end
//------------------------Instantiation------------------""",
                1,
            ),
            (
                "int8_gemm_gmem_c_m_axi.v",
                "        .s_valid        (in_BUS_BVALID),\n        .s_ready        (out_BUS_BREADY),",
                "        .s_valid        (in_BUS_BVALID && qualification_bready_enable),\n        .s_ready        (qualification_bready_internal),",
                1,
            ),
        ],
    },
    "control_read_address_changes_on_release": {
        "profile": "axi4_lite",
        "group": "control",
        "channel": "read_address",
        "fault": "change_content_on_ready_release",
        "diagnostic": "feature=channel.s_axi_control_ar.stall_stability",
        "scenario_edits": [
            (
                "int8_gemm_control_s_axi.v",
                "assign ARREADY = (rstate == RDIDLE);",
                """reg [2:0] qualification_ar_stall_cycles;
wire qualification_arready_enable = qualification_ar_stall_cycles >= 3;
always @(posedge ACLK) begin
    if (ARESET)
        qualification_ar_stall_cycles <= 0;
    else if (ARVALID && qualification_ar_stall_cycles < 3)
        qualification_ar_stall_cycles <= qualification_ar_stall_cycles + 1'b1;
end
assign ARREADY = (rstate == RDIDLE) && qualification_arready_enable;""",
                1,
            ),
            (
                "int8_gemm_control_s_axi.v",
                """        RDIDLE:
            if (ARVALID)
                rnext = RDDATA;""",
                """        RDIDLE:
            if (ar_hs)
                rnext = RDDATA;""",
                1,
            ),
        ],
    },
    "control_write_address_changes_on_release": {
        "profile": "axi4_lite",
        "group": "control",
        "channel": "write_address",
        "fault": "change_content_on_ready_release",
        "diagnostic": "feature=channel.s_axi_control_aw.stall_stability",
        "scenario_edits": [
            (
                "int8_gemm_control_s_axi.v",
                "assign AWREADY = (wstate == WRIDLE);",
                """reg [2:0] qualification_aw_stall_cycles;
wire qualification_awready_enable = qualification_aw_stall_cycles >= 3;
always @(posedge ACLK) begin
    if (ARESET)
        qualification_aw_stall_cycles <= 0;
    else if (AWVALID && qualification_aw_stall_cycles < 3)
        qualification_aw_stall_cycles <= qualification_aw_stall_cycles + 1'b1;
end
assign AWREADY = (wstate == WRIDLE) && qualification_awready_enable;""",
                1,
            ),
            (
                "int8_gemm_control_s_axi.v",
                """        WRIDLE:
            if (AWVALID)
                wnext = WRDATA;""",
                """        WRIDLE:
            if (aw_hs)
                wnext = WRDATA;""",
                1,
            ),
        ],
    },
    "control_write_data_changes_on_release": {
        "profile": "axi4_lite",
        "group": "control",
        "channel": "write_data",
        "fault": "change_content_on_ready_release",
        "diagnostic": "feature=channel.s_axi_control_w.stall_stability",
        "scenario_edits": [
            (
                "int8_gemm_control_s_axi.v",
                "assign WREADY  = (wstate == WRDATA);",
                """reg [2:0] qualification_w_stall_cycles;
wire qualification_wready_enable = qualification_w_stall_cycles >= 3;
always @(posedge ACLK) begin
    if (ARESET)
        qualification_w_stall_cycles <= 0;
    else if (WVALID && qualification_w_stall_cycles < 3)
        qualification_w_stall_cycles <= qualification_w_stall_cycles + 1'b1;
end
assign WREADY  = (wstate == WRDATA) && qualification_wready_enable;""",
                1,
            ),
            (
                "int8_gemm_control_s_axi.v",
                """        WRDATA:
            if (WVALID)
                wnext = WRRESP;""",
                """        WRDATA:
            if (w_hs)
                wnext = WRRESP;""",
                1,
            ),
        ],
    },
}


def driver_fault_plan(name: str) -> tuple[dict[str, Any], str]:
    if name not in DRIVER_FAULTS:
        raise ValueError(f"unknown driver fault {name!r}")
    spec = DRIVER_FAULTS[name]
    raw_plan = {
        "schema_version": 1,
        "profile": spec.get("profile", "axi4"),
        "group": spec["group"],
        "fault": spec["fault"],
        "occurrence": int(spec.get("occurrence", 1)),
    }
    if "channel" in spec:
        raw_plan["channel"] = spec["channel"]
    plan = validate_protocol_fault_plan(raw_plan)
    return plan, str(spec["diagnostic"])


def qualify_driver_fault(
    name: str,
    output_dir: Path,
    *,
    baseline_dir: Path,
    baseline_generated: Path,
) -> dict[str, Any]:
    plan, diagnostic = driver_fault_plan(name)
    generated = output_dir / "generated"
    materialize_baseline_generated_pair(baseline_generated, generated)
    baseline = validate_positive_baseline(
        baseline_dir, baseline_generated, generated
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / "protocol_fault_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    write_sitecustomize(generated)
    rtl_dir = RTL_DIR
    scenario_edits = DRIVER_FAULTS[name].get("scenario_edits", [])
    if scenario_edits:
        rtl_dir = output_dir / "scenario_rtl"
        shutil.copytree(RTL_DIR, rtl_dir)
        for file_name, anchor, replacement, expected_count in scenario_edits:
            target = rtl_dir / str(file_name)
            source = target.read_text(encoding="utf-8")
            if source.count(str(anchor)) != int(expected_count):
                raise AssertionError(
                    f"{name} scenario anchor is absent or ambiguous in {file_name}"
                )
            target.write_text(
                source.replace(str(anchor), str(replacement)), encoding="utf-8"
            )
    fault = _simulate(
        rtl_dir,
        generated,
        output_dir / "fault",
        simulation_env={FAULT_PLAN_ENV: str(plan_path.resolve())},
    )
    scenario_positive = None
    if scenario_edits:
        scenario_positive = _simulate(
            rtl_dir, generated, output_dir / "scenario_positive"
        )
    precise_failure = (
        fault["status"] == "SIMULATION_FAILURE"
        and diagnostic.lower() in fault["stdout"].lower()
    )
    scenario_positive_complete = True
    if scenario_positive is not None:
        coverage = scenario_positive["coverage"]
        scenario_positive_complete = bool(
            scenario_positive["status"] == "PASS"
            and coverage["status"] == "PASS"
            and coverage["required_bins"] == coverage["hit_bins"]
            and not coverage["missing_bins"]
            and not coverage["assertion_failures"]
            and scenario_positive["ledger"]["status"] == "PASS"
        )
    summary = {
        "name": name,
        "status": (
            "QUALIFIED"
            if precise_failure and scenario_positive_complete
            else "UNQUALIFIED"
        ),
        "fault_plan": plan,
        "scenario_edits": [
            {
                "rtl_file": str(file_name),
                "anchor": str(anchor),
                "replacement": str(replacement),
                "expected_anchor_count": int(expected_count),
            }
            for file_name, anchor, replacement, expected_count in scenario_edits
        ],
        "expected_diagnostic": diagnostic,
        "fault_precise_failure": precise_failure,
        "observed_diagnostic_excerpt": diagnostic_excerpt(
            fault["stdout"], diagnostic
        ),
        "baseline_complete": baseline["complete"],
        "scenario_positive_complete": scenario_positive_complete,
        "baseline_dir": str(baseline_dir),
        "generated_test_sha256": sha256(generated / "test_gemm_automatic.py"),
        "fault": {
            key: value
            for key, value in fault.items()
            if key not in {"stdout", "report_dir"}
        },
    }
    if scenario_positive is not None:
        summary["scenario_positive"] = {
            key: value
            for key, value in scenario_positive.items()
            if key not in {"stdout", "report_dir"}
        }
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=sorted(DRIVER_FAULTS))
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--baseline-generated", type=Path, required=True)
    args = parser.parse_args()
    result = qualify_driver_fault(
        args.name,
        args.output_dir,
        baseline_dir=args.baseline_dir,
        baseline_generated=args.baseline_generated,
    )
    print(json.dumps(result, indent=2))
