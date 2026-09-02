"""Build machine-owned context around a minimal user NPU request.

The user should describe only computational intent, for example:

    design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type

This module does not invent architecture. It adds only fixed project constraints
and records which unspecified choices belong to the Architect. Downstream agent
context is then assembled deterministically from the original request, the fixed
project constraints, and frozen Architect artifacts.
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
    """Combine raw user intent with fixed project policy for the Architect.

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
            "external_synopsys_handoff": project["external_synopsys_handoff"],
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
    """Assemble the complete deterministic context for the future RTL Agent.

    The RTL agent should not require the user to restate any project policy.
    It will receive:
      1. the original natural-language request,
      2. fixed runtime/project constraints, and
      3. the frozen Architect artifacts.
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
        "frozen_architecture": artifacts,
        "external_synopsys_handoff": project["external_synopsys_handoff"],
    }
