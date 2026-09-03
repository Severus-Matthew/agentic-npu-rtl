"""Build machine-owned context around a minimal hardware-accelerator request.

The user supplies computational/behavioral intent only. This module does not
invent architecture. It adds fixed technical project constraints and records
which unspecified choices belong to the Architect. Downstream context is
assembled deterministically from the original request, those fixed constraints,
and the frozen Architect artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
MULTIGENT_ROOT = REPO_ROOT / "multigent"
PROJECT_CONSTRAINTS_PATH = MULTIGENT_ROOT / "config" / "project_constraints.yaml"
WORKSPACE_ROOT = MULTIGENT_ROOT / "workspace"


def load_project_constraints(path: Path = PROJECT_CONSTRAINTS_PATH) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("Project constraints must decode to a mapping/object.")
    return value


def build_architect_intake(user_request: str) -> dict[str, Any]:
    """Combine raw user intent with fixed technical policy for the Architect.

    No microarchitecture defaults are injected here. Anything under
    ``architect_must_decide_when_unspecified`` is explicitly delegated to the
    Architect unless the user already specified it in natural language.
    """

    request = user_request.strip()
    if not request:
        raise ValueError("User request must not be empty.")

    project = load_project_constraints()
    return {
        "user_request": request,
        "project_constraints": {
            "rtl_constraints": project["rtl_constraints"],
            "verification_policy": project["verification_policy"],
            "synthesis_policy": project["synthesis_policy"],
        },
        "architect_must_decide_when_unspecified": project[
            "architect_must_decide_when_unspecified"
        ],
        "provenance": {
            "user_supplied_fields": ["user_request"],
            "runtime_injected_fields": [
                "project_constraints",
                "architect_must_decide_when_unspecified",
            ],
        },
    }


def persist_intake(
    intake: Mapping[str, Any],
    *,
    run_id: str,
    output_dir: Path | None = None,
) -> Path:
    """Persist the exact Architect input for reproducibility."""

    target = output_dir or (WORKSPACE_ROOT / "specs")
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"request-{run_id}.yaml"
    path.write_text(
        yaml.safe_dump(dict(intake), sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return path


def build_rtl_context(
    *,
    user_request: str,
    architecture_dir: Path | None = None,
) -> dict[str, Any]:
    """Assemble deterministic context for the RTL Generator.

    The RTL Generator receives the original request, fixed RTL/synthesis policy,
    and frozen Architect artifacts. It does not reconstruct or reinterpret the
    user's intent independently.
    """

    architecture_dir = architecture_dir or (WORKSPACE_ROOT / "architecture")
    required = {
        "architecture_contract": architecture_dir / "architecture_contract.yaml",
        "interface_contract": architecture_dir / "interface_contract.yaml",
        "module_manifest": architecture_dir / "module_manifest.json",
        "acceptance_criteria": architecture_dir / "acceptance_criteria.yaml",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Cannot build RTL context before Architect artifacts exist: "
            + ", ".join(missing)
        )

    project = load_project_constraints()
    artifacts: dict[str, Any] = {}
    for name, path in required.items():
        artifacts[name] = yaml.safe_load(path.read_text(encoding="utf-8"))

    return {
        "user_request": user_request.strip(),
        "fixed_rtl_constraints": project["rtl_constraints"],
        "synthesis_policy": project["synthesis_policy"],
        "frozen_architecture": artifacts,
    }
