"""API-backed Architect Agent.

The normal user-facing input is intentionally minimal natural language, e.g.:

    design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type

A deterministic intake layer adds fixed project policy. The Architect itself
chooses unspecified microarchitecture details and freezes them into contracts for
independent RTL-generation and verification agents. The Architect never writes RTL.
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

    def run(
        self,
        request: str | Mapping[str, Any],
        *,
        output_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Create and persist architecture contracts for ``request``.

        ``request`` should normally be a natural-language string. Mapping input is
        retained for legacy benchmarks/tests, but is wrapped as user-provided legacy
        input rather than treated as project policy.
        """

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

        persist_intake(intake, run_id=run_id)
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
The envelope deliberately separates three things:

1. ``user_request`` (and, only for legacy runs, ``legacy_user_specification``)
   contains what the USER actually requested.
2. ``project_constraints`` contains fixed runtime policy injected by software.
   These are mandatory but are not evidence that the user chose an architecture.
3. ``architect_must_decide_when_unspecified`` lists choices that YOU own whenever
   the user did not specify them.

Do not turn unspecified architecture choices into SPEC_CONFLICT merely because
only a short natural-language request was supplied. Make technically justified,
simple, synthesizable baseline decisions and record them in the contract and
``open_assumptions`` where appropriate. A true contradiction between explicit
requirements should still produce SPEC_CONFLICT.

Your output is a CONTRACT, not RTL. Do not generate SystemVerilog and do not
claim synthesis/PPA results. Another team member owns the external Synopsys flow.
The contract must be precise enough that an independent RTL Generator and an
independent Verifier can consume it without hidden side conversations.

Required design work:
1. Interpret the requested operation and datatypes; resolve exact arithmetic,
   signedness, product width, accumulation width, bias/activation semantics, and
   overflow behavior.
2. Choose the compute organization, array dimensions, parameterization, and
   dataflow when the user leaves them unspecified.
3. Choose and define buffering, pipeline stages, control behavior, and reset.
4. Choose and fully specify the external interface/handshake when unspecified.
5. Decompose the design into modules with explicit responsibilities/dependencies.
6. State architectural invariants downstream agents may not silently change.
7. Build acceptance criteria that incorporate the fixed project RTL and
   verification policies.
8. Define exactly what verified artifacts are handed to the external Synopsys flow.
9. Never invent timing, area, power, frequency, utilization, or other PPA values.

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
    """Load the old YAML/JSON benchmark format for backwards compatibility."""

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
        help="Legacy YAML/JSON structured specification (not recommended for new runs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
        help="Architect-owned artifact directory",
    )
    parser.add_argument("--run-id", default="manual")
    parser.add_argument(
        "--model",
        default=None,
        help="Override NPU_AGENT_MODEL for this run",
    )
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=None,
        help="Override NPU_AGENT_API_MODE for this run",
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
