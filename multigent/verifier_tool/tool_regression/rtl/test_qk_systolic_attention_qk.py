"""Real-Verilator QK qualification and structural mutation regression.

This lives outside the simulator-free quick suite.  It deliberately compiles
the baseline plus every structural mutant against one frozen generated TB.
"""

from __future__ import annotations

import shutil

import pytest

from multigent.verifier_tool.tool_regression.benchmarks.qk_systolic_attention_qk.qualify import (
    RTL,
    _structural_mutations,
    run_qualification,
)


@pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator unavailable")
@pytest.mark.skipif(not RTL.is_dir(), reason="local QK RTL unavailable")
def test_qk_systolic_closes_pool_and_kills_every_structural_mutant(tmp_path):
    mutant_count = len(_structural_mutations())
    summary = run_qualification(
        tmp_path,
        randomized_cases=32,
        mutant_count=mutant_count,
        seed=0x514B,
        jobs=4,
    )

    assert summary["status"] == "PASS"
    assert summary["coverage"]["required_bins"] == 14
    assert summary["coverage"]["hit_bins"] == 14
    assert summary["coverage"]["missing_bins"] == []
    campaign = summary["mutation_campaign"]
    assert campaign["selected"] == mutant_count
    assert campaign["compile_valid"] == mutant_count
    assert campaign["killed"] == mutant_count
    assert campaign["survived"] == 0
    assert campaign["invalid"] == 0
