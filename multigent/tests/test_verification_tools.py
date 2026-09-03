from __future__ import annotations

from pathlib import Path

from multigent.tools import verilator


def test_verilator_failure_classification_syntax() -> None:
    assert verilator._classify_verilator_failure("%Error: syntax error") == "SV_SYNTAX_ERROR"


def test_verilator_failure_classification_width() -> None:
    assert verilator._classify_verilator_failure("%Warning-WIDTH: width mismatch") == "WIDTH_ERROR"


def test_verilator_failure_classification_elaboration() -> None:
    assert (
        verilator._classify_verilator_failure("Port connection has invalid array dimension")
        == "ELABORATION_ERROR"
    )


def test_verilator_tool_unavailable_is_distinct_from_compile_failure(
    tmp_path: Path, monkeypatch
) -> None:
    rtl_dir = tmp_path / "rtl"
    rtl_dir.mkdir()
    (rtl_dir / "top.sv").write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.setattr(verilator.shutil, "which", lambda _: None)

    result = verilator.run_verilator_lint(
        rtl_dir=rtl_dir,
        top_module="top",
        report_path=tmp_path / "verification" / "lint.json",
    )

    assert result["status"] == "TOOL_UNAVAILABLE"
    assert result["failure_class"] is None
    assert (tmp_path / "verification" / "lint.json").is_file()
