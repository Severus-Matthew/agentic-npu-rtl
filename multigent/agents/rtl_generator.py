"""API-backed generic RTL Generator Agent.

The agent implements a frozen architecture contract as synthesizable SystemVerilog.
It is intentionally accelerator-agnostic: operation names, arithmetic formats,
parallelism, interfaces, storage, and module names all come from the Architect
artifacts supplied in the deterministic RTL context.

The ``run_from_state`` method has the standard LangGraph node shape: it accepts a
mapping-like graph state and returns a partial state update. The graph itself is
assembled separately so routing policy remains orchestration-owned.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.intake.request_builder import WORKSPACE_ROOT, build_rtl_context

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


RTL_GENERATOR_OUTPUT_SCHEMA = SCHEMA_ROOT / "rtl_generator_output.schema.json"
TASK_TYPES = {
    "INITIAL_GENERATION",
    "FUNCTIONAL_REPAIR",
    "SYNTHESIS_REPAIR",
    "PPA_OPTIMIZATION",
}


class RTLGeneratorAgent(APIAgent):
    """Generate or modify RTL without changing frozen architectural semantics."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        super().__init__(
            AgentConfig(
                name="rtl_generator",
                role_skill="rtl_generator",
                model=model or os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex"),
                api_mode=api_mode or os.getenv("NPU_AGENT_API_MODE", "responses"),
            )
        )

    def load_instructions(self) -> str:
        """Load only the role's technical skill to avoid benchmark-example bias."""

        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        role_skill = self.role_skill_path.read_text(encoding="utf-8")
        return f"# RTL GENERATOR TECHNICAL SKILL\n\n{role_skill}\n"

    def run(
        self,
        context: Mapping[str, Any],
        *,
        task_type: str = "INITIAL_GENERATION",
        feedback: Mapping[str, Any] | None = None,
        output_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Generate RTL or a structured escalation from a frozen RTL context."""

        if task_type not in TASK_TYPES:
            raise ValueError(f"Unsupported RTL task type: {task_type}")
        self._validate_context(context)

        target = output_dir or (WORKSPACE_ROOT / "rtl")
        target.mkdir(parents=True, exist_ok=True)

        existing_rtl = self._load_existing_rtl(target) if task_type != "INITIAL_GENERATION" else {}
        if task_type != "INITIAL_GENERATION" and not existing_rtl:
            raise AgentRuntimeError(
                f"{task_type} requires existing RTL in {target}; run INITIAL_GENERATION first."
            )
        if task_type != "INITIAL_GENERATION" and feedback is None:
            raise AgentRuntimeError(f"{task_type} requires deterministic/authorized feedback.")

        task = self._build_task(
            context=context,
            task_type=task_type,
            feedback=feedback,
            existing_rtl=existing_rtl,
        )
        result = self.run_structured(
            task=task,
            schema_path=RTL_GENERATOR_OUTPUT_SCHEMA,
            log_name=f"rtl-generator-{run_id}.json",
        )
        self._validate_result(
            result=result,
            context=context,
            task_type=task_type,
            existing_rtl=existing_rtl,
        )

        if result["status"] == "RTL_GENERATED":
            if task_type == "INITIAL_GENERATION":
                for stale in target.rglob("*.sv"):
                    stale.unlink()
            for item in result["files"]:
                relative = self._safe_relative_sv_path(item["path"])
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                content = str(item["content"])
                if not content.endswith("\n"):
                    content += "\n"
                path.write_text(content, encoding="utf-8")

        return result

    def run_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """LangGraph-compatible node entry point.

        LangGraph nodes accept state and return a partial state update. This method
        intentionally contains no routing logic: the orchestrator decides whether an
        ``ARCHITECTURE_CONFLICT`` returns to the Architect, whether verification runs,
        and whether retry budgets are exhausted.
        """

        context = state.get("rtl_context")
        if not isinstance(context, Mapping):
            user_request = state.get("user_request")
            if not isinstance(user_request, str) or not user_request.strip():
                raise AgentRuntimeError(
                    "RTL LangGraph node requires state['rtl_context'] or state['user_request']."
                )
            architecture_dir_raw = state.get(
                "architecture_dir", WORKSPACE_ROOT / "architecture"
            )
            architecture_dir = Path(architecture_dir_raw)
            context = build_rtl_context(
                user_request=user_request,
                architecture_dir=architecture_dir,
            )

        task_type = str(state.get("rtl_task_type", "INITIAL_GENERATION"))
        feedback = state.get("rtl_feedback")
        if feedback is not None and not isinstance(feedback, Mapping):
            raise AgentRuntimeError("state['rtl_feedback'] must be a mapping when supplied")

        run_id = str(state.get("run_id", "langgraph"))
        result = self.run(
            context,
            task_type=task_type,
            feedback=feedback,
            run_id=run_id,
        )
        return {
            "rtl_status": result["status"],
            "rtl_result": result,
            "rtl_files": [item["path"] for item in result["files"]],
            "architecture_conflict": result["architecture_conflict"],
            "needs_regression": result["regression_required"] != "NONE",
        }

    @staticmethod
    def _validate_context(context: Mapping[str, Any]) -> None:
        required = {
            "user_request",
            "fixed_rtl_constraints",
            "synthesis_policy",
            "frozen_architecture",
        }
        missing = sorted(required - set(context))
        if missing:
            raise AgentRuntimeError(f"RTL context missing required fields: {missing}")

        frozen = context["frozen_architecture"]
        if not isinstance(frozen, Mapping):
            raise AgentRuntimeError("frozen_architecture must be a mapping")
        artifact_names = {
            "architecture_contract",
            "interface_contract",
            "module_manifest",
            "acceptance_criteria",
        }
        missing_artifacts = sorted(artifact_names - set(frozen))
        if missing_artifacts:
            raise AgentRuntimeError(
                f"RTL context missing frozen Architect artifacts: {missing_artifacts}"
            )

        manifest = frozen["module_manifest"]
        if not isinstance(manifest, Mapping) or not manifest.get("modules"):
            raise AgentRuntimeError("Frozen module manifest is empty or invalid")

    @staticmethod
    def _load_existing_rtl(target: Path) -> dict[str, str]:
        files: dict[str, str] = {}
        for path in sorted(target.rglob("*.sv")):
            files[path.relative_to(target).as_posix()] = path.read_text(encoding="utf-8")
        return files

    @staticmethod
    def _safe_relative_sv_path(raw: str) -> Path:
        path = Path(str(raw))
        if path.is_absolute() or ".." in path.parts:
            raise AgentRuntimeError(f"Unsafe RTL output path: {raw!r}")
        if path.suffix.lower() != ".sv":
            raise AgentRuntimeError(f"RTL Generator may write only .sv files, got {raw!r}")
        if not path.parts or path.parts[0] in {"rtl", "."}:
            raise AgentRuntimeError(
                f"RTL file paths must be relative to the RTL root, got {raw!r}"
            )
        return path

    @staticmethod
    def _manifest_modules(context: Mapping[str, Any]) -> set[str]:
        modules = context["frozen_architecture"]["module_manifest"]["modules"]
        return {str(module["name"]) for module in modules}

    @classmethod
    def _validate_result(
        cls,
        *,
        result: Mapping[str, Any],
        context: Mapping[str, Any],
        task_type: str,
        existing_rtl: Mapping[str, str],
    ) -> None:
        if result["task_type"] != task_type:
            raise AgentRuntimeError(
                f"RTL Generator returned task_type={result['task_type']!r}, expected {task_type!r}"
            )

        manifest_modules = cls._manifest_modules(context)
        status = result["status"]
        files = list(result["files"])
        changed_modules = [str(name) for name in result["changed_modules"]]

        if len(changed_modules) != len(set(changed_modules)):
            raise AgentRuntimeError("RTL Generator returned duplicate changed_modules")
        unknown_changed = sorted(set(changed_modules) - manifest_modules)
        if unknown_changed:
            raise AgentRuntimeError(
                f"RTL Generator attempted undeclared modules: {unknown_changed}"
            )

        if result["architecture_changed"] or result["interface_changed"]:
            raise AgentRuntimeError(
                "RTL Generator may not report or enact architecture/interface changes; "
                "return ARCHITECTURE_CONFLICT instead."
            )

        if status == "RTL_GENERATED":
            if not files:
                raise AgentRuntimeError("RTL_GENERATED requires at least one RTL file")
            if result["architecture_conflict"] is not None:
                raise AgentRuntimeError("RTL_GENERATED cannot also contain architecture_conflict")
            if str(result["blocked_reason"]).strip():
                raise AgentRuntimeError("RTL_GENERATED cannot contain blocked_reason")
            if not result["contract_checks"]:
                raise AgentRuntimeError("RTL_GENERATED requires explicit contract_checks")
            failed_checks = [
                check["requirement"]
                for check in result["contract_checks"]
                if not check["satisfied"]
            ]
            if failed_checks:
                raise AgentRuntimeError(
                    "RTL_GENERATED contains unsatisfied contract checks: "
                    + ", ".join(map(str, failed_checks))
                )

            paths: set[str] = set()
            file_modules: set[str] = set()
            for item in files:
                relative = cls._safe_relative_sv_path(str(item["path"]))
                normalized = relative.as_posix()
                if normalized in paths:
                    raise AgentRuntimeError(f"Duplicate RTL output path: {normalized}")
                paths.add(normalized)

                module = str(item["module"])
                if module not in manifest_modules:
                    raise AgentRuntimeError(
                        f"RTL file {normalized} implements undeclared module {module!r}"
                    )
                if module in file_modules:
                    raise AgentRuntimeError(
                        f"Module {module!r} is emitted by more than one RTL file"
                    )
                file_modules.add(module)

                content = str(item["content"])
                if not content.strip():
                    raise AgentRuntimeError(f"RTL file {normalized} has empty content")
                if "```" in content:
                    raise AgentRuntimeError(
                        f"RTL file {normalized} contains Markdown code fences"
                    )
                declaration = re.compile(
                    rf"\bmodule\s+(?:automatic\s+)?{re.escape(module)}\b"
                )
                if declaration.search(content) is None:
                    raise AgentRuntimeError(
                        f"RTL file {normalized} does not declare expected module {module!r}"
                    )
                if re.search(r"\bendmodule\b", content) is None:
                    raise AgentRuntimeError(f"RTL file {normalized} has no endmodule")

            if set(changed_modules) != file_modules:
                raise AgentRuntimeError(
                    "changed_modules must exactly match modules emitted in files"
                )

            if task_type == "INITIAL_GENERATION":
                if file_modules != manifest_modules:
                    missing = sorted(manifest_modules - file_modules)
                    extra = sorted(file_modules - manifest_modules)
                    raise AgentRuntimeError(
                        f"Initial RTL must implement exactly the frozen manifest; "
                        f"missing={missing}, extra={extra}"
                    )
                if result["regression_required"] != "FULL":
                    raise AgentRuntimeError("Initial RTL generation requires FULL regression")
            elif task_type == "PPA_OPTIMIZATION" and result["regression_required"] != "FULL":
                raise AgentRuntimeError("PPA RTL changes require FULL regression")

        elif status == "ARCHITECTURE_CONFLICT":
            if files or changed_modules:
                raise AgentRuntimeError(
                    "ARCHITECTURE_CONFLICT must not emit or modify RTL files"
                )
            conflict = result["architecture_conflict"]
            if not isinstance(conflict, Mapping):
                raise AgentRuntimeError(
                    "ARCHITECTURE_CONFLICT requires architecture_conflict details"
                )
            unknown = sorted(set(conflict["affected_modules"]) - manifest_modules)
            if unknown:
                raise AgentRuntimeError(
                    f"Architecture conflict references undeclared modules: {unknown}"
                )
            if result["regression_required"] != "NONE":
                raise AgentRuntimeError(
                    "No RTL changed during ARCHITECTURE_CONFLICT; regression must be NONE"
                )

        elif status == "REPAIR_BLOCKED":
            if task_type == "INITIAL_GENERATION":
                raise AgentRuntimeError("INITIAL_GENERATION cannot return REPAIR_BLOCKED")
            if files or changed_modules:
                raise AgentRuntimeError("REPAIR_BLOCKED must not emit RTL changes")
            if not str(result["blocked_reason"]).strip():
                raise AgentRuntimeError("REPAIR_BLOCKED requires blocked_reason")
            if result["regression_required"] != "NONE":
                raise AgentRuntimeError(
                    "No RTL changed during REPAIR_BLOCKED; regression must be NONE"
                )
        else:
            raise AgentRuntimeError(f"Unknown RTL Generator status: {status!r}")

    @staticmethod
    def _build_task(
        *,
        context: Mapping[str, Any],
        task_type: str,
        feedback: Mapping[str, Any] | None,
        existing_rtl: Mapping[str, str],
    ) -> str:
        envelope = {
            "task_type": task_type,
            "rtl_context": dict(context),
            "feedback": dict(feedback) if feedback is not None else None,
            "existing_rtl": dict(existing_rtl),
        }
        serialized = yaml.safe_dump(envelope, sort_keys=False, default_flow_style=False)
        return f"""Implement the frozen hardware architecture as synthesizable SystemVerilog.

AUTHORITY AND COMMUNICATION
---------------------------
- The original user request is preserved for provenance and requirement authority.
- The Architect artifacts in ``rtl_context.frozen_architecture`` are frozen technical
  decisions. Do not silently reinterpret, repair, optimize, or replace them.
- If those artifacts are internally insufficient or impossible to implement without
  an architectural/interface decision, return ``ARCHITECTURE_CONFLICT``. State the
  exact evidence and the decision required from the Architect. Do not make that
  decision yourself.
- LangGraph will route structured conflicts, verification failures, repair plans, and
  optimization plans. Do not simulate an agent-to-agent conversation in prose.

GENERIC IMPLEMENTATION RULES
----------------------------
1. This runtime is accelerator-agnostic. Derive all operations, data types, widths,
   signedness, dimensions, parameters, storage, scheduling, protocols, reset behavior,
   and module names from the frozen contracts. Never assume GEMM, convolution,
   attention, a MAC array, INT8, INT32, M/N/K, a particular tile shape, or any other
   benchmark structure unless it is present in the supplied architecture.
2. For INITIAL_GENERATION, emit exactly one ``.sv`` file for every module in the
   frozen module manifest and no undeclared helper modules. Each file entry names the
   single manifest module it implements.
3. Preserve the interface contract exactly. Architecture/interface changes are not
   implementation conveniences; escalate them.
4. Use explicit widths and signed conversions where needed. Implement the arithmetic
   semantics in the frozen contract rather than relying on accidental language casts.
5. Implement ready/valid, framing, ordering, stalls, reset, counters, edge conditions,
   storage capacities, banking/ports, and latency sequencing exactly as contracted.
6. Generate synthesizable SystemVerilog only. Do not place Markdown fences in file
   content and do not claim any compiler, simulator, or synthesis tool has run.
7. For repair/optimization modes, use the supplied existing RTL and authorized
   feedback. Modify only necessary manifest modules. Never change tests, golden
   behavior, architecture, or interface to make a failure disappear.
8. For PPA_OPTIMIZATION, deterministic synthesis evidence is authoritative; every RTL
   change requires FULL functional regression afterward.
9. Before returning RTL_GENERATED, perform a textual self-review and populate
   ``contract_checks`` with concise evidence. Self-review is not deterministic PASS.
10. If a requested repair cannot be applied coherently under the frozen architecture,
    return ARCHITECTURE_CONFLICT when a new architecture decision is required, or
    REPAIR_BLOCKED when the authorized repair/evidence is insufficient without any
    architecture change.

FILE PATH RULE
--------------
Every file path is relative to ``multigent/workspace/rtl`` (for example
``controller.sv`` or ``subsystem/controller.sv``). Never prefix it with ``rtl/`` and
never use absolute paths or ``..``.

RTL TASK ENVELOPE
-----------------
{serialized}
"""


def _load_recorded_request(run_id: str) -> str:
    path = WORKSPACE_ROOT / "specs" / f"request-{run_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(
            f"Architect intake record not found: {path}. Run the Architect first."
        )
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    request = value.get("user_request") if isinstance(value, Mapping) else None
    if not isinstance(request, str) or not request.strip():
        raise AgentRuntimeError(f"No usable user_request found in {path}")
    return request.strip()


def _load_mapping(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(raw)
    else:
        value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must decode to a mapping/object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the generic RTL Generator Agent")
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--task-type",
        choices=sorted(TASK_TYPES),
        default="INITIAL_GENERATION",
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="Optional prepared RTL context YAML/JSON; otherwise build from the frozen workspace architecture.",
    )
    parser.add_argument(
        "--feedback",
        type=Path,
        default=None,
        help="Authorized repair/optimization feedback YAML/JSON for non-initial tasks.",
    )
    parser.add_argument(
        "--architecture-dir",
        type=Path,
        default=WORKSPACE_ROOT / "architecture",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WORKSPACE_ROOT / "rtl",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=None,
    )
    args = parser.parse_args()

    if args.context is not None:
        context = _load_mapping(args.context)
    else:
        context = build_rtl_context(
            user_request=_load_recorded_request(args.run_id),
            architecture_dir=args.architecture_dir,
        )
    feedback = _load_mapping(args.feedback) if args.feedback is not None else None

    agent = RTLGeneratorAgent(model=args.model, api_mode=args.api_mode)
    result = agent.run(
        context,
        task_type=args.task_type,
        feedback=feedback,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "task_type": result["task_type"],
                "files": [item["path"] for item in result["files"]],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
