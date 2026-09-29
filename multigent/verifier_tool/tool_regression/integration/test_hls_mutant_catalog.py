from __future__ import annotations

from pathlib import Path

from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.batch_qualify_mutants import (
    validate_registry,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.prepare_qualification_catalog import (
    build_catalog,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.qualify_driver_fault import (
    DRIVER_FAULTS,
    driver_fault_plan,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.qualify_exclusive_variant import (
    EXCLUSIVE_VARIANTS,
    matched_exclusive_interface,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.qualify_named_mutant import (
    MUTANTS,
    diagnostic_evidence_class,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.qualify_positive_coverage import (
    qualify_positive_coverage,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.qualify_coverage_evidence import (
    qualify_coverage_evidence,
)


def test_every_named_hls_mutant_has_exact_reviewable_anchors() -> None:
    findings = validate_registry(sorted(MUTANTS))
    assert len(findings) >= 40
    assert {item["status"] for item in findings} == {"READY"}
    assert all(item["edits"] for item in findings)
    assert all(
        edit["anchor_count"] == edit["expected_anchor_count"]
        for item in findings
        for edit in item["edits"]
    )


def test_hls_qualification_catalog_covers_every_matrix_target_once() -> None:
    catalog = build_catalog()
    cases = catalog["cases"]
    identities = [(item["target_type"], item["feature_id"]) for item in cases]
    assert len(cases) == 134
    assert len(identities) == len(set(identities))
    assert catalog["summary"]["registry_ready"] == len(MUTANTS)

    allowed_preparation = {
        "qualified",
        "evidence_qualified",
        "named_registry",
        "recipe_prepared",
        "topology_excluded",
        "checker_alias_review",
        "requires_harness_support",
    }
    assert {
        item["preparation"] for item in cases
    } <= allowed_preparation
    assert all(item.get("recipe") for item in cases)
    coverage_cases = [
        item for item in cases if item["target_type"] == "coverage_obligation"
    ]
    assert len(coverage_cases) == 71
    assert all(item["required_bins"] for item in coverage_cases)
    assert {
        item["strict_status"] for item in coverage_cases
    } == {"evidence_qualified"}
    assert all(
        "`" not in bin_name
        for item in coverage_cases
        for bin_name in item["required_bins"]
    )
    boundary = next(
        item for item in coverage_cases
        if item["feature_id"] == "channel.m_axi_gmem_a_ar.axi4_4k_boundary"
    )
    assert boundary["required_bins"] == ["ends_before_boundary", "ends_at_boundary"]


def test_positive_coverage_qualification_rejects_a_zero_hit() -> None:
    catalog = build_catalog()
    obligations = []
    for case in catalog["cases"]:
        if case["target_type"] != "coverage_obligation":
            continue
        obligations.append({
            "id": case["feature_id"],
            "bins": [
                {"name": name, "required": True, "hits": 1}
                for name in case["required_bins"]
            ],
        })
    required = sum(len(item["bins"]) for item in obligations)
    report = {
        "status": "PASS",
        "required_bins": required,
        "hit_bins": required,
        "missing_bins": [],
        "assertion_failures": [],
        "obligations": obligations,
    }
    assert qualify_positive_coverage(report)["status"] == "QUALIFIED"
    obligations[0]["bins"][0]["hits"] = 0
    assert qualify_positive_coverage(report)["status"] == "UNQUALIFIED"


def test_coverage_evidence_ablation_rejects_each_bin_individually() -> None:
    catalog = build_catalog()
    obligations = []
    for case in catalog["cases"]:
        if case["target_type"] != "coverage_obligation":
            continue
        obligations.append({
            "id": case["feature_id"],
            "bins": [
                {"name": name, "required": True, "hits": 1}
                for name in case["required_bins"]
            ],
        })
    required = sum(len(item["bins"]) for item in obligations)
    report = {
        "status": "PASS",
        "required_bins": required,
        "hit_bins": required,
        "missing_bins": [],
        "assertion_failures": [],
        "obligations": obligations,
    }
    result = qualify_coverage_evidence(report)
    assert result["status"] == "QUALIFIED"
    assert result["required_bins"] == required == 152
    assert result["qualified_ablation_mutants"] == 152


def test_named_mutant_diagnostics_preserve_evidence_attribution() -> None:
    assert diagnostic_evidence_class(
        "feature=protocol.gmem_c.no_4k_boundary_crossing"
    ) == "named_assertion"
    assert diagnostic_evidence_class(
        "role-bound accepted DUT outputs differ from the code-owned numeric profile for gemm"
    ) == "operation_golden"
    assert diagnostic_evidence_class("DUT emitted WSTRB=0x0") == "deterministic_driver"


def test_environment_owned_response_stall_faults_are_closed_and_precise() -> None:
    expected = {
        "a_read_content_changes_on_release": "feature=channel.m_axi_gmem_a_r.stall_stability",
        "b_read_content_changes_on_release": "feature=channel.m_axi_gmem_b_r.stall_stability",
        "c_write_response_content_changes_on_release": "feature=channel.m_axi_gmem_c_b.stall_stability",
        "control_read_address_changes_on_release": "feature=channel.s_axi_control_ar.stall_stability",
        "control_write_address_changes_on_release": "feature=channel.s_axi_control_aw.stall_stability",
        "control_write_data_changes_on_release": "feature=channel.s_axi_control_w.stall_stability",
    }
    for name, diagnostic in expected.items():
        assert DRIVER_FAULTS[name]["scenario_edits"]
        plan, actual = driver_fault_plan(name)
        assert plan["fault"] == "change_content_on_ready_release"
        if name.startswith("control_"):
            assert plan["profile"] == "axi4_lite"
            assert plan["channel"] in {
                "read_address", "write_address", "write_data",
            }
        assert actual == diagnostic


def test_exclusive_variants_use_truthful_physical_lock_metadata() -> None:
    assert set(EXCLUSIVE_VARIANTS) == {
        "gmem_a_reserved_lock_bit_high",
        "gmem_a_illegal_exclusive_read",
        "gmem_b_illegal_exclusive_read",
        "gmem_c_illegal_exclusive_write",
    }
    for spec in EXCLUSIVE_VARIANTS.values():
        interface = matched_exclusive_interface(spec)
        signal = next(
            item for item in interface["signals"] if item["name"] == spec["signal"]
        )
        assert signal["physical_encoding"] == "legacy_hls_2bit"
        assert signal["logical_bit"] == 0
        assert signal["reserved_zero_bits"] == [1]
        assert ".exclusive_access_restrictions" in spec["diagnostic"]


def test_hls_protocol_fault_helpers_are_benchmark_local() -> None:
    from multigent.verifier_tool.tool_regression.paths import BENCHMARKS_ROOT, VERIFIER_TOOL_ROOT

    root = VERIFIER_TOOL_ROOT
    core_files = (
        root / "protocol/stimulus/drivers/axi4_outstanding.py",
        root / "protocol/stimulus/drivers/axi_lite_control.py",
        root / "protocol/stimulus/drivers/__init__.py",
        root / "lifecycle/stimulus/cocotb.py",
    )
    forbidden = (
        "NPU_PROTOCOL_FAULT_PLAN",
        "qualification_fault",
        "fault_injection",
        "resolved_axi4_fault",
        "resolved_protocol_fault",
    )
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        assert not any(marker in source for marker in forbidden), path

    benchmark = BENCHMARKS_ROOT / "int8_gemm_hls_golden"
    assert (benchmark / "protocol_fault_plan.py").is_file()
    assert (benchmark / "fault_axi4_outstanding.py").is_file()
    assert (benchmark / "fault_axi_lite_control.py").is_file()
    assert (benchmark / "fault_lifecycle_cocotb.py").is_file()
    assert (benchmark / "fault_bootstrap.py").is_file()
