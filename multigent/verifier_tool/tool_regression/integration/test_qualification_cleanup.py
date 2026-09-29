import json
from pathlib import Path

from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.batch_qualify_mutants import (
    run_batch,
)
from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.qualification_common import (
    cleanup_simulation_builds,
    compact_completed_qualification,
    diagnostic_excerpt,
    load_completed_qualification,
    reset_qualification_workspace,
    sha256,
)


def test_cleanup_removes_only_regenerable_build_directories(tmp_path: Path) -> None:
    case = tmp_path / "case"
    build = case / "mutant" / "build"
    build.mkdir(parents=True)
    (build / "compiled-object.o").write_bytes(b"cache")
    report = case / "mutant" / "simulation_report.json"
    report.write_text("{}", encoding="utf-8")
    rtl = case / "mutated_rtl" / "dut.v"
    rtl.parent.mkdir(parents=True)
    rtl.write_text("module dut; endmodule\n", encoding="utf-8")

    removed = cleanup_simulation_builds(case)

    assert removed == [str(build)]
    assert not build.exists()
    assert report.is_file()
    assert rtl.is_file()


def test_completed_qualification_requires_current_generated_tb_hash(tmp_path: Path) -> None:
    generated = tmp_path / "baseline-generated"
    generated.mkdir()
    test = generated / "test_gemm_automatic.py"
    test.write_text("# generated A\n", encoding="utf-8")
    report = tmp_path / "qualification.json"
    report.write_text(
        '{"status":"QUALIFIED","baseline_complete":true,'
        f'"generated_test_sha256":"{sha256(test)}"}}',
        encoding="utf-8",
    )
    assert load_completed_qualification(report, baseline_generated=generated) is not None

    test.write_text("# generated B\n", encoding="utf-8")
    assert load_completed_qualification(report, baseline_generated=generated) is None


def test_retry_replaces_only_the_selected_case_workspace(tmp_path: Path) -> None:
    selected = tmp_path / "mutant"
    selected.mkdir()
    (selected / "stale.txt").write_text("stale", encoding="utf-8")
    neighbor = tmp_path / "other-mutant"
    neighbor.mkdir()

    reset_qualification_workspace(selected)

    assert not selected.exists()
    assert neighbor.is_dir()


def test_compaction_keeps_durable_evidence_only_after_qualification(tmp_path: Path) -> None:
    case = tmp_path / "case"
    transient = case / "mutant" / "build"
    transient.mkdir(parents=True)
    (transient / "compiled-object.o").write_bytes(b"cache")
    qualification = case / "qualification.json"
    qualification.write_text('{"status":"QUALIFIED"}', encoding="utf-8")
    plan = case / "protocol_fault_plan.json"
    plan.write_text("{}", encoding="utf-8")

    removed = compact_completed_qualification(case)

    assert removed == [str(case / "mutant")]
    assert qualification.is_file()
    assert plan.is_file()


def test_compaction_preserves_unqualified_debug_artifacts(tmp_path: Path) -> None:
    case = tmp_path / "case"
    build = case / "mutant" / "build"
    build.mkdir(parents=True)
    (case / "qualification.json").write_text(
        '{"status":"UNQUALIFIED"}', encoding="utf-8"
    )

    assert compact_completed_qualification(case) == []
    assert build.is_dir()


def test_diagnostic_excerpt_is_compact_and_case_insensitive() -> None:
    output = "x" * 500 + "Feature=Protocol.GMEM_A.Rule" + "y" * 500

    excerpt = diagnostic_excerpt(output, "feature=protocol.gmem_a.rule", context=20)

    assert excerpt == "x" * 20 + "Feature=Protocol.GMEM_A.Rule" + "y" * 20
    assert diagnostic_excerpt(output, "missing diagnostic") is None


def test_batch_resumes_only_hash_matching_qualified_case(tmp_path: Path) -> None:
    generated = tmp_path / "baseline-generated"
    generated.mkdir()
    test = generated / "test_gemm_automatic.py"
    test.write_text("# generated\n", encoding="utf-8")
    case = tmp_path / "results" / "a_reserved_burst"
    case.mkdir(parents=True)
    qualification = {
        "name": "a_reserved_burst",
        "status": "QUALIFIED",
        "baseline_complete": True,
        "generated_test_sha256": sha256(test),
    }
    (case / "qualification.json").write_text(
        json.dumps(qualification), encoding="utf-8"
    )

    summary = run_batch(
        ["a_reserved_burst"],
        tmp_path / "results",
        baseline_dir=tmp_path / "unused-baseline",
        baseline_generated=generated,
        jobs=1,
    )

    assert summary["requested"] == 1
    assert summary["qualified"] == 1
    assert summary["runner_errors"] == 0
    assert summary["resumed"] == 1
