"""Codex-backed Architect Agent.

This is the first executable LLM node in the workflow. It converts an NPU
specification into a frozen implementation contract for downstream RTL and
verification agents. The Architect never writes RTL.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from .base import AgentConfig, CodexAgent, SCHEMA_ROOT, WORKSPACE_ROOT


ARCHITECT_OUTPUT_SCHEMA = SCHEMA_ROOT / "architect_output.schema.json"


class ArchitectAgent(CodexAgent):
    """Produce architecture contracts from a structured NPU specification."""

    def __init__(self, *, model: str = "gpt-5.3-codex") -> None:
        super().__init__(
            AgentConfig(
                name="architect",
                role_skill="architect",
                model=model,
            )
        )

    def run(
        self,
        spec: Mapping[str, Any],
        *,
        output_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Create and persist the architecture contract for ``spec``.

        Files are written by this Python wrapper rather than by Codex itself.
        This enforces the Architect's ownership boundary mechanically.
        """

        target = output_dir or (WORKSPACE_ROOT / "architecture")
        target.mkdir(parents=True, exist_ok=True)

        task = self._build_architecture_task(spec)
        result = self.run_structured(
            task=task,
            schema_path=ARCHITECT_OUTPUT_SCHEMA,
            log_name=f"architect-{run_id}.jsonl",
        )

        if result["status"] == "SPEC_CONFLICT":
            conflict_path = target / "spec_conflict.json"
            self._write_json(conflict_path, result)
            return result

        if result["conflicts"]:
            raise ValueError(
                "Architect returned READY while also reporting specification conflicts."
            )

        self._write_yaml(
            target / "architecture_contract.yaml",
            result["architecture_contract"],
        )
        self._write_yaml(
            target / "interface_contract.yaml",
            result["interface_contract"],
        )
        self._write_json(
            target / "module_manifest.json",
            result["module_manifest"],
        )
        self._write_yaml(
            target / "acceptance_criteria.yaml",
            result["acceptance_criteria"],
        )
        self._write_json(target / "architect_result.json", result)
        return result

    @staticmethod
    def _build_architecture_task(spec: Mapping[str, Any]) -> str:
        serialized_spec = yaml.safe_dump(
            dict(spec),
            sort_keys=False,
            default_flow_style=False,
        )
        return f"""Design the RTL microarchitecture for the NPU specification below.

Your output is a CONTRACT, not RTL. Do not generate SystemVerilog and do not
claim synthesis results. Another team member owns the external Synopsys flow.
Your contract must be sufficiently precise that an independent RTL generator
and an independent verifier can implement the design without discussing hidden
assumptions with each other.

Required design work:
1. Resolve the exact arithmetic equation and signed/width semantics.
2. Choose a simple, synthesizable compute organization appropriate for the spec.
3. Define dataflow, buffering, pipeline stages, control behavior, and reset.
4. Define every external signal and ready/valid behavior precisely.
5. Decompose the design into modules with explicit responsibilities.
6. State architectural invariants that downstream agents may not silently change.
7. Define functional/verification/RTL acceptance criteria and what artifacts must
   be handed to the external Synopsys flow.
8. If two specification requirements are genuinely contradictory, return
   status=SPEC_CONFLICT and describe the conflict instead of weakening either one.
9. Do not invent PPA measurements. Targets may be requirements; measurements are
   only valid when supplied by the deterministic Synopsys integration.

NPU SPECIFICATION
-----------------
{serialized_spec}
"""

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_yaml(path: Path, value: Any) -> None:
        path.write_text(
            yaml.safe_dump(value, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )


def load_spec(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON NPU specification."""

    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(raw)
    else:
        value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise TypeError("NPU specification must decode to a mapping/object.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Codex NPU Architect Agent")
    parser.add_argument("--spec", required=True, type=Path, help="YAML/JSON NPU spec")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
        help="Architect-owned artifact directory",
    )
    parser.add_argument("--run-id", default="manual")
    parser.add_argument("--model", default="gpt-5.3-codex")
    args = parser.parse_args()

    agent = ArchitectAgent(model=args.model)
    result = agent.run(
        load_spec(args.spec),
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps({"status": result["status"]}, indent=2))


if __name__ == "__main__":
    main()
