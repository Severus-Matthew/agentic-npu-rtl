import json
from pathlib import Path

import yaml

from multigent.verifier_tool import build_interface_coverage_plan
from multigent.verifier_tool.pool.role_pool.protocol_event_relations import (
    compile_protocol_event_relations,
)
from multigent.verifier_tool.protocol.assertion.runtime import (
    build_protocol_assertion_plan,
)
from multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.validate_manifest import (
    MANIFEST,
    validate_manifest,
)
from multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.run_external_api import (
    _repair_or_regenerate_context,
    _save_attempt_candidate,
    _self_owned_verifier_conflict,
    _verifier_owned_candidate,
)


def test_external_feature_benchmark_manifest_is_balanced_and_pinned() -> None:
    manifest = validate_manifest()
    assert len(manifest["cases"]) == 30


def test_external_feature_benchmark_evidence_schema_is_json() -> None:
    schema = MANIFEST.with_name("evidence.schema.json")
    document = json.loads(Path(schema).read_text(encoding="utf-8"))
    assert document["title"] == "External feature-extension benchmark evidence"
    assert document["properties"]["verdict"]["enum"] == ["PASS", "FAIL", "BLOCKED"]


def test_external_contract_corpus_tracks_all_thirty_selected_cases() -> None:
    root = MANIFEST.parent / "cases"
    case_dirs = sorted(path for path in root.iterdir() if path.is_dir())
    assert len(case_dirs) == 30
    for case_dir in case_dirs:
        assert {
            "architecture_contract.yaml",
            "interface_contract.yaml",
            "module_manifest.json",
            "acceptance_criteria.yaml",
            "contract_status.yaml",
            "preflight_report.yaml",
        } <= {path.name for path in case_dir.iterdir()}


def test_external_contract_preflight_never_calls_blocked_candidates_frozen() -> None:
    summary = yaml.safe_load(
        (MANIFEST.parent / "contract_preflight_summary.yaml").read_text(encoding="utf-8")
    )
    assert summary["total"] == 30
    assert summary["reviewer_pass_candidates"] == 4
    assert summary["blocked"] == 26
    assert {
        item["case_id"]
        for item in summary["cases"]
        if item["status"] == "reviewer_pass_candidate"
    } == {"P01", "P02", "P03", "P04"}


def test_empty_verifier_draft_retries_without_embedding_previous_output() -> None:
    context = _repair_or_regenerate_context(
        "P01",
        candidate={
            "status": "VERIFICATION_READY",
            "reference_files": [],
            "test_files": [],
            "large_unused_payload": "x" * 10_000,
        },
        findings=[{"category": "INVALID_ASSERTION"}],
        error="VERIFICATION_READY requires reference model and cocotb tests",
    )
    assert "deterministic_validation_review" not in context
    assert "large_unused_payload" not in json.dumps(context)
    assert "Return at least one complete Python reference-model file" in context["user_request"]


def test_rejected_api_candidate_is_preserved_for_source_audit(tmp_path: Path) -> None:
    relative = _save_attempt_candidate(
        tmp_path,
        run_started_at="2026-10-15T19:25:14+00:00",
        attempt=3,
        candidate={"status": "VERIFICATION_READY", "test_files": [{"content": "bad"}]},
    )
    snapshot = tmp_path / relative
    assert snapshot.is_file()
    assert json.loads(snapshot.read_text(encoding="utf-8"))["test_files"] == [
        {"content": "bad"}
    ]


def test_repair_context_removes_pipeline_owned_generated_source() -> None:
    candidate = {
        "status": "VERIFICATION_READY",
        "reference_files": [{"path": "reference/ref.py", "content": "VALUE = 1\n"}],
        "test_files": [
            {
                "path": "tests/test_demo.py",
                "content": (
                    "VALUE = 1\n\n"
                    "# === BEGIN CONTRACT-GENERATED PROTOCOL MONITOR ===\n"
                    "CONTRACT_SIGNAL_NAMES = ('clk',)\n"
                    "# === END CONTRACT-GENERATED PROTOCOL MONITOR ===\n"
                ),
            }
        ],
    }
    cleaned = _verifier_owned_candidate(candidate)
    content = cleaned["test_files"][0]["content"]
    assert content == "VALUE = 1\n"
    assert "CONTRACT_SIGNAL_NAMES" not in content
    assert "CONTRACT_SIGNAL_NAMES" in candidate["test_files"][0]["content"]


def test_self_owned_verifier_conflict_is_not_architect_owned() -> None:
    assert _self_owned_verifier_conflict(
        {
            "category": "missing_input_artifact",
            "issue": "previous_content has a malformed contract-generated monitor",
            "evidence": "validator_error requested a generated marker repair",
            "requested_architect_decision": "provide a verifier source skeleton",
        }
    )
    assert not _self_owned_verifier_conflict(
        {
            "category": "observable_semantic_contradiction",
            "issue": "The frozen contract assigns two meanings to one DUT signal",
            "evidence": "interface signal x is both request and response",
            "requested_architect_decision": "choose the externally observable meaning",
        }
    )


def test_p01_axi_obligations_follow_the_pinned_single_beat_bridge() -> None:
    case = MANIFEST.parent / "cases" / "p01_wishbone_pipelined_to_axi4"
    interface = yaml.safe_load((case / "interface_contract.yaml").read_text())
    obligations = build_interface_coverage_plan(interface)["obligations"]

    def required(template: str) -> set[str]:
        return {
            str(bin_spec["name"])
            for obligation in obligations
            if obligation.get("template") == template
            for bin_spec in obligation.get("bins", [])
            if bin_spec.get("required", True)
        }

    assert required("axi4_burst_length") == {"single"}
    assert required("axi4_burst_type") == {"incrementing"}
    assert required("axi4_transfer_size") == {"narrow"}
    assert required("axi4_alignment") == {"aligned"}
    assert required("axi4_4k_boundary") == {
        "ends_before_boundary",
        "ends_at_boundary",
    }
    assert required("axi4_write_strobe") == {"all_zero", "sparse"}


def test_p01_registered_cross_protocol_timing_is_tool_owned() -> None:
    case = MANIFEST.parent / "cases" / "p01_wishbone_pipelined_to_axi4"
    interface = yaml.safe_load((case / "interface_contract.yaml").read_text())
    relations = compile_protocol_event_relations(interface)["relations"]
    assert {item["id"] for item in relations} == {
        "axi_read_response_to_wishbone_completion",
        "axi_write_response_to_wishbone_completion",
    }
    assert all(item["minimum_latency_cycles"] == 1 for item in relations)
    assert all(item["maximum_latency_cycles"] == 1 for item in relations)
    read = next(item for item in relations if "read" in item["id"])
    assert read["cause"]["signals"] == ("i_axi_rvalid", "o_axi_rready")

    plan = build_protocol_assertion_plan(build_interface_coverage_plan(interface))
    assert len(plan["event_correlations"]) == 2
