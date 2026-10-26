"""Real-Verilator exhaustive qualification for the standalone mask stage."""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.benchmarks.attention_mask_binary.qualify import (
    RTL,
    _mutation_catalog,
    run_qualification,
)


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
@pytest.mark.skipif(not RTL.is_file(), reason="local attention-mask RTL unavailable")
def test_attention_mask_exhaustive_domain_and_all_mutants(tmp_path):
    catalog_size = len(_mutation_catalog(RTL.read_text(encoding="utf-8")))
    summary = run_qualification(
        randomized_count=32,
        seed=0xA55A,
        mutant_limit=None,
        workers=4,
        work_root=tmp_path,
    )

    assert summary["passed"] is True
    assert summary["coverage"]["required_bins"] == 20
    assert summary["coverage"]["hit_bins"] == 20
    assert summary["coverage"]["missing_bins"] == []
    assert summary["stimulus"]["exhaustive_signed16_mask_pairs"] == 131_072
    assert summary["stimulus"]["independent_score_mask_valid_gaps"] is True
    campaign = summary["mutation_campaign"]
    assert campaign["catalog_size"] == catalog_size == 59
    assert campaign["selected"] == catalog_size
    assert campaign["compile_valid"] == catalog_size
    assert campaign["compile_invalid"] == 0
    assert campaign["killed"] == catalog_size
    assert campaign["survived"] == 0
