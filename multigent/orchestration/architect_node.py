"""LangGraph node adapter for initial and feedback-driven Architect runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent
from multigent.agents.base import AgentRuntimeError
from multigent.intake.request_builder import (
    WORKSPACE_ROOT,
    build_architect_intake,
    build_rtl_context,
    persist_intake,
)

from .state import HardwareDesignState


def _run_architect_revision(
    agent: ArchitectAgent,
    *,
    user_request: str,
    feedback: Mapping[str, Any],
    output_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    """Run Architect with downstream technical evidence without changing user input."""

    intake = build_architect_intake(user_request)
    intake["downstream_revision_feedback"] = dict(feedback)
    intake["provenance"]["runtime_injected_fields"].append(
        "downstream_revision_feedback"
    )

    intake_dir = output_dir.parent / "specs"
    persist_intake(intake, run_id=run_id, output_dir=intake_dir)
    task = agent._build_architecture_task(intake) + """

ARCHITECTURE REVISION FEEDBACK
------------------------------
``downstream_revision_feedback`` is structured technical evidence returned by a
later implementation stage. It is not a new user requirement and does not outrank
the original request. Re-evaluate only the architectural decisions implicated by
that evidence, preserve unaffected decisions when technically coherent, and produce
a complete self-consistent replacement contract. Do not ask the RTL Generator to
silently work around an unresolved architecture defect.
"""
    result = agent.run_structured(
        task=task,
        schema_path=ARCHITECT_OUTPUT_SCHEMA,
        log_name=f"architect-{run_id}.json",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    if result["status"] == "SPEC_CONFLICT":
        agent._write_json(output_dir / "spec_conflict.json", result)
        return result
    if result["conflicts"]:
        raise AgentRuntimeError(
            "Architect returned READY while also reporting specification conflicts."
        )

    agent._validate_contract_references(result)
    agent._write_yaml(
        output_dir / "architecture_contract.yaml", result["architecture_contract"]
    )
    agent._write_yaml(
        output_dir / "interface_contract.yaml", result["interface_contract"]
    )
    agent._write_json(output_dir / "module_manifest.json", result["module_manifest"])
    agent._write_yaml(
        output_dir / "acceptance_criteria.yaml", result["acceptance_criteria"]
    )
    agent._write_json(output_dir / "architect_result.json", result)
    return result


def make_architect_node(agent: ArchitectAgent | None = None):
    """Return an Architect node suitable for ``StateGraph.add_node``."""

    runtime = agent or ArchitectAgent()

    def architect_node(state: HardwareDesignState) -> dict[str, Any]:
        user_request = state.get("user_request")
        if not isinstance(user_request, str) or not user_request.strip():
            raise AgentRuntimeError("Architect LangGraph node requires user_request")

        output_dir = Path(
            state.get("architecture_dir", str(WORKSPACE_ROOT / "architecture"))
        )
        current_version = int(state.get("architecture_version", 0))
        feedback = state.get("architecture_conflict")
        is_revision = isinstance(feedback, Mapping)
        next_version = current_version + 1
        base_run_id = str(state.get("run_id", "langgraph"))
        node_run_id = f"{base_run_id}-arch-v{next_version}"

        if is_revision:
            result = _run_architect_revision(
                runtime,
                user_request=user_request.strip(),
                feedback=feedback,
                output_dir=output_dir,
                run_id=node_run_id,
            )
            revision = int(state.get("architecture_revision", 0)) + 1
        else:
            result = runtime.run(
                user_request.strip(),
                output_dir=output_dir,
                run_id=node_run_id,
            )
            revision = int(state.get("architecture_revision", 0))

        update: dict[str, Any] = {
            "architecture_status": result["status"],
            "architecture_dir": str(output_dir),
            "architecture_revision": revision,
            "history": [
                {
                    "stage": "architect",
                    "status": result["status"],
                    "architecture_version": next_version,
                    "revision": is_revision,
                }
            ],
        }

        if result["status"] == "READY":
            rtl_context = build_rtl_context(
                user_request=user_request.strip(),
                architecture_dir=output_dir,
            )
            update.update(
                {
                    "architecture_version": next_version,
                    "architecture_artifacts": {
                        "architecture_contract": str(
                            output_dir / "architecture_contract.yaml"
                        ),
                        "interface_contract": str(
                            output_dir / "interface_contract.yaml"
                        ),
                        "module_manifest": str(output_dir / "module_manifest.json"),
                        "acceptance_criteria": str(
                            output_dir / "acceptance_criteria.yaml"
                        ),
                    },
                    "architecture_conflict": None,
                    "rtl_context": rtl_context,
                    "rtl_task_type": "INITIAL_GENERATION",
                }
            )
        return update

    return architect_node
