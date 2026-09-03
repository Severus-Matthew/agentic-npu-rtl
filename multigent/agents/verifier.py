"""API-backed independent Verifier Agent.

The Verifier creates a specification-derived Python reference model and cocotb
regression environment from the original request and frozen Architect artifacts.
Generated RTL source is deliberately excluded from its context. Deterministic tool
nodes later compile the RTL and execute these tests.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.intake.request_builder import (
    WORKSPACE_ROOT,
    build_verification_context,
)

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


VERIFIER_OUTPUT_SCHEMA = SCHEMA_ROOT / "verifier_output.schema.json"


class VerifierAgent(APIAgent):
    """Generate independent verification artifacts without reading generated RTL."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        super().__init__(
            AgentConfig(
                name="verifier",
                role_skill="verifier",
                model=model or os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex"),
                api_mode=api_mode or os.getenv("NPU_AGENT_API_MODE", "responses"),
            )
        )

    def load_instructions(self) -> str:
        """Load only independent Verifier technical instructions."""

        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        return (
            "# INDEPENDENT VERIFIER TECHNICAL SKILL\n\n"
            + self.role_skill_path.read_text(encoding="utf-8")
            + "\n"
        )

    def run(
        self,
        context: Mapping[str, Any],
        *,
        workspace_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Generate reference/tests/plan or return an architecture conflict."""

        self._validate_context(context)
        root = workspace_dir or WORKSPACE_ROOT
        reference_dir = root / "reference"
        tests_dir = root / "tests"
        verification_dir = root / "verification"
        for directory in (reference_dir, tests_dir, verification_dir):
            directory.mkdir(parents=True, exist_ok=True)

        result = self.run_structured(
            task=self._build_task(context),
            schema_path=VERIFIER_OUTPUT_SCHEMA,
            log_name=f"verifier-{run_id}.json",
        )
        self._validate_result(result=result, context=context)

        if result["status"] == "VERIFICATION_READY":
            for directory in (reference_dir, tests_dir):
                for stale in directory.glob("*.py"):
                    stale.unlink()

            for item in result["reference_files"]:
                self._write_python(reference_dir, item)
            for item in result["test_files"]:
                self._write_python(tests_dir, item)

            (verification_dir / "verification_plan.yaml").write_text(
                yaml.safe_dump(
                    result["verification_plan"],
                    sort_keys=False,
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )
            (verification_dir / "verifier_result.json").write_text(
                json.dumps(result, indent=2, sort_keys=False) + "\n",
                encoding="utf-8",
            )

        return result

    def run_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """LangGraph-compatible Verifier node entry point."""

        context = state.get("verification_context")
        if not isinstance(context, Mapping):
            user_request = state.get("user_request")
            if not isinstance(user_request, str) or not user_request.strip():
                raise AgentRuntimeError(
                    "Verifier node requires state['verification_context'] or user_request"
                )
            architecture_dir = Path(
                state.get("architecture_dir", WORKSPACE_ROOT / "architecture")
            )
            context = build_verification_context(
                user_request=user_request,
                architecture_dir=architecture_dir,
            )

        run_id = str(state.get("run_id", "langgraph"))
        architecture_version = int(state.get("architecture_version", 0))
        rtl_iteration = int(state.get("repair_iteration", 0))
        node_run_id = f"{run_id}-verify-av{architecture_version}-r{rtl_iteration}"
        result = self.run(context, run_id=node_run_id)
        return {
            "verifier_status": result["status"],
            "verifier_result": result,
            "verification_plan": result["verification_plan"],
            "architecture_conflict": result["architecture_conflict"],
            "verification_context": dict(context),
        }

    @staticmethod
    def _validate_context(context: Mapping[str, Any]) -> None:
        required = {
            "user_request",
            "verification_policy",
            "frozen_architecture",
            "provenance",
        }
        missing = sorted(required - set(context))
        if missing:
            raise AgentRuntimeError(f"Verifier context missing required fields: {missing}")

        provenance = context["provenance"]
        if not isinstance(provenance, Mapping):
            raise AgentRuntimeError("Verifier provenance must be a mapping")
        if provenance.get("includes_generated_rtl") is not False:
            raise AgentRuntimeError("Independent Verifier context must exclude generated RTL")
        if provenance.get("includes_rtl_generator_output") is not False:
            raise AgentRuntimeError(
                "Independent Verifier context must exclude RTL Generator output"
            )

        frozen = context["frozen_architecture"]
        if not isinstance(frozen, Mapping):
            raise AgentRuntimeError("Verifier frozen_architecture must be a mapping")
        needed = {
            "architecture_contract",
            "interface_contract",
            "module_manifest",
            "acceptance_criteria",
        }
        missing_artifacts = sorted(needed - set(frozen))
        if missing_artifacts:
            raise AgentRuntimeError(
                f"Verifier context missing frozen artifacts: {missing_artifacts}"
            )

    @staticmethod
    def _safe_python_filename(raw: str) -> str:
        path = Path(str(raw))
        if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
            raise AgentRuntimeError(
                f"Verification Python files must be flat safe filenames, got {raw!r}"
            )
        if path.suffix != ".py" or path.name.startswith("."):
            raise AgentRuntimeError(f"Invalid verification Python filename: {raw!r}")
        return path.name

    @classmethod
    def _write_python(cls, target: Path, item: Mapping[str, Any]) -> None:
        filename = cls._safe_python_filename(str(item["path"]))
        content = str(item["content"])
        if not content.endswith("\n"):
            content += "\n"
        (target / filename).write_text(content, encoding="utf-8")

    @classmethod
    def _validate_result(
        cls,
        *,
        result: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> None:
        status = result["status"]
        references = list(result["reference_files"])
        tests = list(result["test_files"])
        plan = result["verification_plan"]
        conflict = result["architecture_conflict"]

        manifest = context["frozen_architecture"]["module_manifest"]
        top = str(manifest["top"])
        module_names = {str(item["name"]) for item in manifest["modules"]}

        if status == "ARCHITECTURE_CONFLICT":
            if references or tests:
                raise AgentRuntimeError(
                    "ARCHITECTURE_CONFLICT must not emit verification Python files"
                )
            if not isinstance(conflict, Mapping):
                raise AgentRuntimeError(
                    "ARCHITECTURE_CONFLICT requires structured conflict details"
                )
            unknown = sorted(set(conflict["affected_modules"]) - module_names)
            if unknown:
                raise AgentRuntimeError(
                    f"Verifier conflict references undeclared modules: {unknown}"
                )
            return

        if status != "VERIFICATION_READY":
            raise AgentRuntimeError(f"Unknown verifier status: {status!r}")
        if conflict is not None:
            raise AgentRuntimeError(
                "VERIFICATION_READY cannot also contain architecture_conflict"
            )
        if not references:
            raise AgentRuntimeError("VERIFICATION_READY requires a reference model")
        if not tests:
            raise AgentRuntimeError("VERIFICATION_READY requires cocotb tests")
        if str(plan["top_module"]) != top:
            raise AgentRuntimeError(
                f"Verification plan top={plan['top_module']!r} does not match manifest top={top!r}"
            )

        reference_names: set[str] = set()
        for item in references:
            name = cls._safe_python_filename(str(item["path"]))
            if name in reference_names:
                raise AgentRuntimeError(f"Duplicate reference filename: {name}")
            reference_names.add(name)
            cls._validate_python_content(name, str(item["content"]), cocotb_required=False)

        test_names: set[str] = set()
        test_modules: set[str] = set()
        for item in tests:
            name = cls._safe_python_filename(str(item["path"]))
            if name in test_names:
                raise AgentRuntimeError(f"Duplicate test filename: {name}")
            test_names.add(name)
            test_modules.add(Path(name).stem)
            groups = set(item["regression_groups"])
            if "full" not in groups:
                raise AgentRuntimeError(
                    f"Initial verifier test file {name} must belong to full regression"
                )
            cls._validate_python_content(name, str(item["content"]), cocotb_required=True)

        if set(map(str, plan["test_modules"])) != test_modules:
            raise AgentRuntimeError(
                "verification_plan.test_modules must exactly match generated test filenames"
            )

        minimum = int(
            context["verification_policy"].get("randomized_transactions_minimum", 0)
        )
        if int(plan["randomized_test_count"]) < minimum:
            raise AgentRuntimeError(
                f"Verifier randomized_test_count={plan['randomized_test_count']} is below policy minimum {minimum}"
            )

        full_group = set(map(str, plan["regression_groups"]["full"]))
        if full_group != test_modules:
            raise AgentRuntimeError(
                "Initial full regression group must contain every generated test module"
            )

    @staticmethod
    def _validate_python_content(
        filename: str,
        content: str,
        *,
        cocotb_required: bool,
    ) -> None:
        if not content.strip():
            raise AgentRuntimeError(f"Generated Python file {filename} is empty")
        if "```" in content:
            raise AgentRuntimeError(f"Generated Python file {filename} contains Markdown fences")
        try:
            compile(content, filename, "exec")
        except SyntaxError as exc:
            raise AgentRuntimeError(
                f"Generated Python file {filename} has syntax error: {exc.msg}"
            ) from exc
        lowered = content.lower()
        forbidden = [
            "subprocess.",
            "os.system(",
            "requests.",
            "urllib.request",
            "workspace/rtl",
            "open(\"multigent/workspace/rtl",
            "open('multigent/workspace/rtl",
        ]
        hit = [token for token in forbidden if token in lowered]
        if hit:
            raise AgentRuntimeError(
                f"Generated verification file {filename} uses forbidden capability: {hit[0]}"
            )
        if cocotb_required and "cocotb" not in lowered:
            raise AgentRuntimeError(f"Generated test file {filename} does not use cocotb")

    @staticmethod
    def _build_task(context: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(dict(context), sort_keys=False, default_flow_style=False)
        return f"""Create an independent executable verification environment for the frozen hardware contract.

INDEPENDENCE BOUNDARY
---------------------
- The envelope below contains the original request, fixed verification policy, and
  frozen Architect artifacts only.
- Generated RTL source and RTL Generator output are intentionally absent. Do not ask
  for them and do not infer expected behavior from likely implementation choices.
- Deterministic Verilator/cocotb nodes will later execute your artifacts against RTL.
  You create the oracle and tests; you do not declare PASS/FAIL.

OUTPUT RULES
------------
1. Return VERIFICATION_READY with Python reference/test file contents and a complete
   plan, or ARCHITECTURE_CONFLICT if an executable oracle cannot be defined without
   a new architectural/interface decision.
2. Reference and test paths are flat filenames relative to their owned roots, e.g.
   ``model.py`` and ``test_contract.py``. Do not include ``reference/`` or ``tests/``
   prefixes and do not create subdirectories.
3. ``verification_plan.test_modules`` contains Python module names (filename without
   ``.py``) and must exactly match generated test files.
4. The initial ``full`` regression group contains every generated test module.
5. Honor at least the fixed randomized transaction minimum. Use a deterministic seed.
6. Use cocotb 2.x public APIs. Every test must be bounded by finite timeout/cycle waits.
7. Tests interact through contract-declared top-level signals only. Do not inspect
   internal RTL implementation state unless explicitly exposed by the contract.
8. Keep generated Python concise enough for structured output while still covering
   functional, boundary, reset, protocol/backpressure, and randomized requirements
   that actually apply to this contract.

VERIFIER CONTEXT
----------------
{serialized}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the independent Verifier Agent")
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--architecture-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=None,
    )
    args = parser.parse_args()

    context = build_verification_context(
        user_request=args.request,
        architecture_dir=args.architecture_dir,
    )
    result = VerifierAgent(model=args.model, api_mode=args.api_mode).run(
        context,
        run_id=args.run_id,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "top_module": result["verification_plan"].get("top_module"),
                "test_modules": result["verification_plan"].get("test_modules", []),
                "randomized_test_count": result["verification_plan"].get(
                    "randomized_test_count", 0
                ),
                "architecture_conflict": result["architecture_conflict"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
