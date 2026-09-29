"""Regression coverage for deep HLS-generated shift-register elaboration."""

from __future__ import annotations

import inspect
import multigent.tools.cocotb_runner as cocotb_runner
from multigent.verifier_tool.tool_regression.paths import REPOSITORY_ROOT


def test_runner_raises_verilator_unroll_limits() -> None:
    source = inspect.getsource(cocotb_runner._worker)
    assert '"--unroll-count"' in source
    assert '"4096"' in source
    assert '"--unroll-stmts"' in source
    assert '"500000"' in source


def test_hls_golden_contains_the_deep_array_shift_pattern() -> None:
    source = (REPOSITORY_ROOT / "gemm_golden" / "int8_gemm_gmem_a_m_axi.v").read_text()
    assert "mem[i+1] <= mem[i];" in source
    assert "RBUFF_DEPTH     = NUM_READ_OUTSTANDING * MAX_READ_BURST_LENGTH" in source
