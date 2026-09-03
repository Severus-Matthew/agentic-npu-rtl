"""Deterministic Verilator lint/elaboration wrapper.

The wrapper never repairs RTL and never asks an LLM to decide tool status. Process
return codes and Verilator output are authoritative evidence consumed by LangGraph.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


FAILURE_CLASSES = {
    "SV_SYNTAX_ERROR",
    "ELABORATION_ERROR",
    "WIDTH_ERROR",
    "UNSYNTHESIZABLE_RTL",
    "UNKNOWN",
}


def _extract_error_diagnostics(text: str) -> list[str]:
    """Return Verilator error headline diagnostics, excluding warnings/notes."""

    return [
        line.strip()
        for line in text.splitlines()
        if line.lstrip().lower().startswith("%error")
    ]


def _classify_verilator_failure(text: str) -> str:
    """Classify deterministic compiler text into the project's coarse taxonomy.

    When Verilator emits both fatal errors and non-fatal warnings, classification is
    based on the error headlines first. This prevents an unrelated WIDTH warning from
    masking a real elaboration failure.
    """

    errors = _extract_error_diagnostics(text)
    diagnostic_text = "\n".join(errors) if errors else text
    lowered = diagnostic_text.lower()

    if "syntax error" in lowered or "%error: syntax" in lowered:
        return "SV_SYNTAX_ERROR"

    unsynth_tokens = ("unsynthesizable", "non-synthesizable")
    if any(token in lowered for token in unsynth_tokens):
        return "UNSYNTHESIZABLE_RTL"

    elaboration_tokens = (
        "constant expression",
        "expression to be constant",
        "isn't const",
        "is not constant",
        "two-state constant",
        "parameter",
        "port connection",
        "unmatched array sizes",
        "dimension",
        "array",
        "cannot find",
        "can't find",
    )
    if any(token in lowered for token in elaboration_tokens):
        return "ELABORATION_ERROR"

    if "width" in lowered or "little bit endian" in lowered or "zero width" in lowered:
        return "WIDTH_ERROR"

    if "unsupported" in lowered:
        return "UNSYNTHESIZABLE_RTL"

    return "UNKNOWN"


def run_verilator_lint(
    *,
    rtl_dir: Path,
    top_module: str,
    report_path: Path | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Lint/elaborate every SystemVerilog file under ``rtl_dir`` with Verilator."""

    rtl_dir = rtl_dir.resolve()
    sources = sorted(rtl_dir.rglob("*.sv"))
    if not sources:
        raise FileNotFoundError(f"No SystemVerilog sources found under {rtl_dir}")

    executable = shutil.which("verilator")
    if executable is None:
        result: dict[str, Any] = {
            "stage": "verilator_lint",
            "status": "TOOL_UNAVAILABLE",
            "failure_class": None,
            "return_code": None,
            "command": ["verilator"],
            "sources": [str(path) for path in sources],
            "stdout": "",
            "stderr": "verilator executable not found on PATH",
            "error_diagnostics": [],
            "top_module": top_module,
        }
        _write_report(report_path, result)
        return result

    command = [
        executable,
        "--lint-only",
        "--sv",
        "-Wno-fatal",
        "--top-module",
        top_module,
        *[str(path) for path in sources],
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=rtl_dir,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result = {
            "stage": "verilator_lint",
            "status": "TIMEOUT",
            "failure_class": "UNKNOWN",
            "return_code": None,
            "command": command,
            "sources": [str(path) for path in sources],
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error_diagnostics": [],
            "top_module": top_module,
        }
        _write_report(report_path, result)
        return result

    combined = f"{completed.stdout}\n{completed.stderr}"
    status = "PASS" if completed.returncode == 0 else "COMPILE_FAILURE"
    result = {
        "stage": "verilator_lint",
        "status": status,
        "failure_class": None
        if status == "PASS"
        else _classify_verilator_failure(combined),
        "return_code": completed.returncode,
        "command": command,
        "sources": [str(path) for path in sources],
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "error_diagnostics": _extract_error_diagnostics(combined),
        "top_module": top_module,
    }
    _write_report(report_path, result)
    return result


def _write_report(path: Path | None, result: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
