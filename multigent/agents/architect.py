"""API-backed generic Hardware Architect Agent.

The user-facing input is intentionally minimal natural language. A deterministic
intake layer adds only fixed technical policy. The Architect chooses unspecified
microarchitecture details and freezes them into contracts for independent RTL
generation and verification. The Architect never writes RTL.
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
    """Produce frozen architecture contracts from minimal hardware intent."""

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
        """Load only the Architect's technical skill."""

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
                "Legacy structured hardware specification supplied by the caller."
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
        return f"""Design and freeze a synthesizable RTL microarchitecture from the intake envelope below.

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

This is a GENERIC hardware architecture task. Do not assume GEMM, matrix
multiplication, M/N/K dimensions, activation/weight/bias terminology, a MAC array,
systolic execution, a particular interface, or any benchmark-specific structure
unless the user request itself requires it.

Your output is a CONTRACT, not RTL. Do not generate SystemVerilog. Synthesis/PPA
metrics are valid only when supplied by deterministic Synopsys reports; do not
infer or fabricate timing, area, power, frequency, or utilization values.

Required design work:
1. Define all requested operations with exact functional semantics and named inputs/outputs.
2. Define every relevant data type/intermediate representation, including width,
   signedness where meaningful, conversions, overflow, and rounding behavior.
3. Define every runtime-varying dimension as a named dimension with concrete
   integer minimum/maximum bounds. Never emit placeholders or unresolved text in
   numeric bound fields.
4. Define all compile-time parameters with concrete defaults, legality constraints,
   and purposes.
5. Choose compute organization, dataflow, parallelism, and scheduling appropriate
   for the requested workload rather than copying benchmark examples.
6. Close all storage/reuse semantics. Storage capacity and read/write/banking/port
   requirements must sustain the stated compute schedule under the declared bounds.
7. Define pipeline stages, valid behavior, and stall behavior.
8. Define control strategy, state progression, counters/indices, and illegal-input behavior.
9. Fully define logical channels and top-level signals, including framing, ordering,
   backpressure, widths, and reset behavior. No interface behavior may depend on
   unstated environment behavior.
10. Define module decomposition with explicit responsibilities, dependencies,
    parameters, and statefulness.
11. Define deterministic functional, verification, RTL, and Synopsys-handoff
    acceptance criteria from the technical project policy.
12. Before returning READY, cross-check operations, data types, runtime bounds,
    parameters, compute schedule, storage bandwidth/capacity, pipeline, interface,
    control, reset, module manifest, and acceptance criteria. The RTL Generator
    must not need to guess architectural facts.

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
        raise TypeError("Hardware specification must decode to a mapping/object.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hardware Architect Agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--request",
        type=str,
        help="Minimal natural-language hardware accelerator request",
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
