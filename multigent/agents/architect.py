"""API-backed Architect Agent.

The normal user-facing input is intentionally minimal natural language, e.g.:

    design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type

A deterministic intake layer adds fixed technical policy. The Architect chooses
unspecified microarchitecture details and freezes them into contracts for
independent RTL generation and verification. The Architect never writes RTL.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.intake.request_builder import build_architect_intake, persist_intake

from .base import APIAgent, AgentConfig, SCHEMA_ROOT, WORKSPACE_ROOT


ARCHITECT_OUTPUT_SCHEMA = SCHEMA_ROOT / "architect_output.schema.json"


class ArchitectAgent(APIAgent):
    """Produce frozen architecture contracts from minimal user intent."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        super().__init__(
            AgentConfig(
                name="architect",
                role_skill="architect",
                model=model or os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex"),
                api_mode=api_mode or os.getenv("NPU_AGENT_API_MODE", "responses"),
            )
        )

    def load_instructions(self) -> str:
        """Load only the Architect's technical skill.

        Shared workflow details for Debugger/PPA/other agents are intentionally
        excluded from the Architect prompt. Fixed cross-stage technical constraints
        are already supplied through the deterministic intake envelope.
        """

        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        role_skill = self.role_skill_path.read_text(encoding="utf-8")
        return f"# ARCHITECT TECHNICAL SKILL\n\n{role_skill}\n"

    def run(
        self,
        request: str | Mapping[str, Any],
        *,
        output_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Create and persist architecture contracts for ``request``."""

        target = output_dir or (WORKSPACE_ROOT / "architecture")
        target.mkdir(parents=True, exist_ok=True)

        if isinstance(request, str):
            intake = build_architect_intake(request)
        else:
            intake = build_architect_intake(
                "Legacy structured NPU specification supplied by the caller."
            )
            intake["legacy_user_specification"] = dict(request)
            intake["provenance"]["user_supplied_fields"].append(
                "legacy_user_specification"
            )

        intake_dir = WORKSPACE_ROOT / "specs" if output_dir is None else target.parent / "specs"
        persist_intake(intake, run_id=run_id, output_dir=intake_dir)
        task = self._build_architecture_task(intake)
        result = self.run_structured(
            task=task,
            schema_path=ARCHITECT_OUTPUT_SCHEMA,
            log_name=f"architect-{run_id}.json",
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
    def _build_architecture_task(intake: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(
            dict(intake),
            sort_keys=False,
            default_flow_style=False,
        )
        return f"""Design and freeze an RTL microarchitecture from the intake envelope below.

INPUT AUTHORITY
---------------
1. ``user_request`` (and only for legacy runs, ``legacy_user_specification``)
   contains explicit user requirements.
2. ``project_constraints`` contains mandatory technical runtime policy.
3. ``architect_must_decide_when_unspecified`` lists architecture choices you must
   resolve when the user leaves them unspecified.

Do not treat a short request as an error. Choose simple, technically justified,
synthesizable defaults for unspecified architecture choices and record them in
``open_assumptions``. Return ``SPEC_CONFLICT`` only for genuinely contradictory
explicit requirements.

Your output is a CONTRACT, not RTL. Do not generate SystemVerilog. Synthesis/PPA
metrics are valid only when supplied by the deterministic Synopsys integration;
do not infer or fabricate timing, area, power, frequency, or utilization values.

Required design work:
1. Resolve the exact operation, tensor shapes, signedness, product width,
   accumulation width, bias semantics, activation semantics, overflow behavior,
   extension rules, and output datatype.
2. Choose compute organization, array dimensions, parameterization, supported
   runtime dimension bounds, and dataflow when unspecified. Every compile-time
   parameter must have a concrete default value and a stated legality constraint.
3. Close operand-reuse semantics. For every operand, state whether it is supplied
   once per job, once per tile, or repeatedly. If an operand is reused, define the
   storage/replay mechanism that makes that reuse possible.
4. Make buffer capacities consistent with dimension bounds and reuse strategy.
   Do not introduce arbitrary fixed depths unless the corresponding supported
   dimension bound makes them sufficient.
5. Define pipeline stages, exact valid/stall behavior, control, reset, and any
   flush/drain behavior.
6. Fully define the external interface, ordering, framing, and ready/valid
   semantics. No interface behavior may depend on unstated host behavior.
7. Decompose the design into modules with explicit responsibilities/dependencies.
8. State architectural invariants downstream agents may not silently change.
9. Build deterministic functional, verification, RTL, and Synopsys handoff
   acceptance criteria from the technical project policy.
10. Check parameter edge cases. Signal widths and counters must remain legal for
    minimum supported parameter values; avoid zero-width ``$clog2`` expressions.
11. Reset control/state deterministically without requiring bulk memory clearing
    unless the computation actually depends on cleared memory contents.
12. Before returning READY, perform a consistency pass across arithmetic,
    dimensions, dataflow, storage, interface, module manifest, and acceptance
    criteria. The RTL Generator must not need to guess missing architectural facts.

ARCHITECT INTAKE ENVELOPE
-------------------------
{serialized}
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


def load_legacy_spec(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(raw)
    else:
        value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise TypeError("NPU specification must decode to a mapping/object.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NPU Architect Agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--request",
        type=str,
        help=(
            "Minimal natural-language NPU request, e.g. 'design a GEMM_BIAS_RELU "
            "NPU of int8 x int8 x int32 type'"
        ),
    )
    source.add_argument(
        "--request-file",
        type=Path,
        help="Text file containing only the user's natural-language request",
    )
    source.add_argument(
        "--spec",
        type=Path,
        help="Legacy YAML/JSON structured specification",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
        help="Architect artifact directory",
    )
    parser.add_argument("--run-id", default="manual")
    parser.add_argument("--model", default=None, help="Override NPU_AGENT_MODEL")
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=None,
        help="Override NPU_AGENT_API_MODE",
    )
    args = parser.parse_args()

    if args.request is not None:
        request: str | Mapping[str, Any] = args.request
    elif args.request_file is not None:
        request = args.request_file.read_text(encoding="utf-8").strip()
    else:
        request = load_legacy_spec(args.spec)

    agent = ArchitectAgent(model=args.model, api_mode=args.api_mode)
    result = agent.run(
        request,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps({"status": result["status"]}, indent=2))


if __name__ == "__main__":
    main()
