"""Install HLS-golden-only fault-aware drivers inside a simulator process.

The benchmark writes a tiny ``sitecustomize.py`` beside its generated TB only
for a negative fault run.  Python imports that file before cocotb imports the
test module, allowing this module to replace the clean production drivers with
benchmark-local fault-aware copies.  Normal verifier-tool execution never
imports this module and contains no fault-plan branch.
"""

from __future__ import annotations

from pathlib import Path


def write_sitecustomize(generated_dir: Path) -> Path:
    """Add the benchmark-only bootstrap beside one copied generated TB."""

    target = generated_dir / "sitecustomize.py"
    target.write_text(
        "from multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden."
        "fault_bootstrap import install_fault_drivers\n"
        "install_fault_drivers()\n",
        encoding="utf-8",
    )
    return target


def install_fault_drivers() -> None:
    """Patch only the process executing an explicit HLS fault plan."""

    from .protocol_fault_plan import load_protocol_fault_plan

    if load_protocol_fault_plan() is None:
        return

    from multigent.verifier_tool.orchestration import campaign
    import multigent.verifier_tool.lifecycle.stimulus as lifecycle_stimulus
    import multigent.verifier_tool.lifecycle.stimulus.cocotb as lifecycle_cocotb

    from .fault_axi4_outstanding import execute_axi4_memory_job
    from .fault_lifecycle_cocotb import drive_control_plane_sequence

    campaign.execute_axi4_memory_job = execute_axi4_memory_job
    lifecycle_cocotb.drive_control_plane_sequence = drive_control_plane_sequence
    lifecycle_stimulus.drive_control_plane_sequence = drive_control_plane_sequence


__all__ = ["install_fault_drivers", "write_sitecustomize"]
