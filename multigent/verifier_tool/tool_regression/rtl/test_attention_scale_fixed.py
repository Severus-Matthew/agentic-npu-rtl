"""Real-Verilator exhaustive qualification for the standalone scale stage."""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.benchmarks.attention_scale_fixed.qualify import (
    RTL,
    _mutation_catalog,
    run_qualification,
)


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
@pytest.mark.skipif(not RTL.is_file(), reason="local attention-scale RTL unavailable")
def test_attention_scale_exhaustive_domain_and_all_mutants(tmp_path):
    catalog_size = len(_mutation_catalog(RTL.read_text(encoding="utf-8")))
    summary = run_qualification(
        randomized_count=32,
        seed=0x5CA1E,
        mutant_limit=None,
        workers=4,
        work_root=tmp_path,
    )

    assert summary["passed"] is True
    assert summary["coverage"]["required_bins"] == 14
    assert summary["coverage"]["hit_bins"] == 14
    assert summary["coverage"]["missing_bins"] == []
    assert summary["stimulus"]["exhaustive_signed16_inputs"] == 65_536
    campaign = summary["mutation_campaign"]
    assert campaign["catalog_size"] == catalog_size == 73
    assert campaign["selected"] == catalog_size
    assert campaign["compile_valid"] == catalog_size
    assert campaign["compile_invalid"] == 0
    assert campaign["killed"] == catalog_size
    assert campaign["survived"] == 0
