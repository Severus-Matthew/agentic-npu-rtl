"""API-backed generic RTL Generator Agent.

Implements frozen architecture artifacts as synthesizable SystemVerilog and applies
only explicitly authorized repair/optimization feedback. Runtime logic remains
accelerator-agnostic.
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
        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        return "# RTL GENERATOR TECHNICAL SKILL\n\n" + self.role_skill_path.read_text(encoding="utf-8") + "\n"

    def run(
        self,
        context: Mapping[str, Any],
        *,
        task_type: str = "INITIAL_GENERATION",
        feedback: Mapping[str, Any] | None = None,
        output_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
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

        result = self.run_structured(
            task=self._build_task(
                context=context,
                task_type=task_type,
                feedback=feedback,
                existing_rtl=existing_rtl,
            ),
            schema_path=RTL_GENERATOR_OUTPUT_SCHEMA,
            log_name=f"rtl-generator-{run_id}.json",
        )
        self._validate_result(
            result=result,
            context=context,
            task_type=task_type,
            existing_rtl=existing_rtl,
            authorized_feedback=feedback,
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
                path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
        return result

    def run_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        context = state.get("rtl_context")
        if not isinstance(context, Mapping):
            user_request = state.get("user_request")
            if not isinstance(user_request, str) or not user_request.strip():
                raise AgentRuntimeError("RTL LangGraph node requires rtl_context or user_request")
            context = build_rtl_context(
                user_request=user_request,
                architecture_dir=Path(state.get("architecture_dir", WORKSPACE_ROOT / "architecture")),
            )

        task_type = str(state.get("rtl_task_type", "INITIAL_GENERATION"))
        feedback = state.get("rtl_feedback")
        if feedback is not None and not isinstance(feedback, Mapping):
            raise AgentRuntimeError("state['rtl_feedback'] must be a mapping when supplied")

        result = self.run(
            context,
            task_type=task_type,
            feedback=feedback,
            run_id=str(state.get("run_id", "langgraph")),
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
        required = {"user_request", "fixed_rtl_constraints", "synthesis_policy", "frozen_architecture"}
        missing = sorted(required - set(context))
        if missing:
            raise AgentRuntimeError(f"RTL context missing required fields: {missing}")
        frozen = context["frozen_architecture"]
        if not isinstance(frozen, Mapping):
            raise AgentRuntimeError("frozen_architecture must be a mapping")
        required_artifacts = {"architecture_contract", "interface_contract", "module_manifest", "acceptance_criteria"}
        missing_artifacts = sorted(required_artifacts - set(frozen))
        if missing_artifacts:
            raise AgentRuntimeError(f"RTL context missing frozen Architect artifacts: {missing_artifacts}")
        manifest = frozen["module_manifest"]
        if not isinstance(manifest, Mapping) or not manifest.get("modules"):
            raise AgentRuntimeError("Frozen module manifest is empty or invalid")

    @staticmethod
    def _load_existing_rtl(target: Path) -> dict[str, str]:
        return {
            path.relative_to(target).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(target.rglob("*.sv"))
        }

    @staticmethod
    def _safe_relative_sv_path(raw: str) -> Path:
        path = Path(str(raw))
        if path.is_absolute() or ".." in path.parts:
            raise AgentRuntimeError(f"Unsafe RTL output path: {raw!r}")
        if path.suffix.lower() != ".sv":
            raise AgentRuntimeError(f"RTL Generator may write only .sv files, got {raw!r}")
        if not path.parts or path.parts[0] in {"rtl", "."}:
            raise AgentRuntimeError(f"RTL file paths must be relative to the RTL root, got {raw!r}")
        return path

    @staticmethod
    def _manifest_modules(context: Mapping[str, Any]) -> set[str]:
        return {
            str(item["name"])
            for item in context["frozen_architecture"]["module_manifest"]["modules"]
        }

    @classmethod
    def _validate_result(
        cls,
        *,
        result: Mapping[str, Any],
        context: Mapping[str, Any],
        task_type: str,
        existing_rtl: Mapping[str, str],
        authorized_feedback: Mapping[str, Any] | None = None,
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
            raise AgentRuntimeError(f"RTL Generator attempted undeclared modules: {unknown_changed}")

        if result["architecture_changed"] or result["interface_changed"] or result["latency_changed"]:
            raise AgentRuntimeError(
                "RTL Generator may not enact frozen architecture/interface/latency changes; return ARCHITECTURE_CONFLICT instead"
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
                str(check["requirement"])
                for check in result["contract_checks"]
                if not check["satisfied"]
            ]
            if failed_checks:
                raise AgentRuntimeError("RTL_GENERATED contains unsatisfied contract checks: " + ", ".join(failed_checks))

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
                    raise AgentRuntimeError(f"RTL file {normalized} implements undeclared module {module!r}")
                if module in file_modules:
                    raise AgentRuntimeError(f"Module {module!r} is emitted by more than one RTL file")
                file_modules.add(module)
                content = str(item["content"])
                if not content.strip() or "```" in content:
                    raise AgentRuntimeError(f"RTL file {normalized} has invalid/empty content")
                declaration = re.compile(rf"\bmodule\s+(?:automatic\s+)?{re.escape(module)}\b")
                if declaration.search(content) is None or re.search(r"\bendmodule\b", content) is None:
                    raise AgentRuntimeError(f"RTL file {normalized} does not contain complete expected module {module!r}")

            if set(changed_modules) != file_modules:
                raise AgentRuntimeError("changed_modules must exactly match modules emitted in files")

            if task_type == "INITIAL_GENERATION":
                if file_modules != manifest_modules:
                    missing = sorted(manifest_modules - file_modules)
                    extra = sorted(file_modules - manifest_modules)
                    raise AgentRuntimeError(
                        f"Initial RTL must implement exactly the frozen manifest; missing={missing}, extra={extra}"
                    )
                if result["regression_required"] != "FULL":
                    raise AgentRuntimeError("Initial RTL generation requires FULL regression")
            else:
                cls._validate_authorized_change_scope(
                    changed_modules=file_modules,
                    task_type=task_type,
                    feedback=authorized_feedback,
                )
                if task_type in {"FUNCTIONAL_REPAIR", "PPA_OPTIMIZATION"} and result["regression_required"] != "FULL":
                    raise AgentRuntimeError(f"{task_type} RTL changes require FULL regression")

        elif status == "ARCHITECTURE_CONFLICT":
            if files or changed_modules:
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT must not emit or modify RTL files")
            conflict = result["architecture_conflict"]
            if not isinstance(conflict, Mapping):
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT requires architecture_conflict details")
            unknown = sorted(set(conflict["affected_modules"]) - manifest_modules)
            if unknown:
                raise AgentRuntimeError(f"Architecture conflict references undeclared modules: {unknown}")
            if result["regression_required"] != "NONE":
                raise AgentRuntimeError("No RTL changed during ARCHITECTURE_CONFLICT; regression must be NONE")

        elif status == "REPAIR_BLOCKED":
            if task_type == "INITIAL_GENERATION":
                raise AgentRuntimeError("INITIAL_GENERATION cannot return REPAIR_BLOCKED")
            if files or changed_modules:
                raise AgentRuntimeError("REPAIR_BLOCKED must not emit RTL changes")
            if not str(result["blocked_reason"]).strip():
                raise AgentRuntimeError("REPAIR_BLOCKED requires blocked_reason")
            if result["regression_required"] != "NONE":
                raise AgentRuntimeError("No RTL changed during REPAIR_BLOCKED; regression must be NONE")
        else:
            raise AgentRuntimeError(f"Unknown RTL Generator status: {status!r}")

    @staticmethod
    def _validate_authorized_change_scope(
        *,
        changed_modules: set[str],
        task_type: str,
        feedback: Mapping[str, Any] | None,
    ) -> None:
        if not isinstance(feedback, Mapping):
            raise AgentRuntimeError(f"{task_type} requires structured authorized feedback")

        if task_type == "FUNCTIONAL_REPAIR":
            repair_plan = feedback.get("repair_plan")
            if not isinstance(repair_plan, Mapping):
                raise AgentRuntimeError("FUNCTIONAL_REPAIR requires debugger repair_plan feedback")
            authorized = set(map(str, repair_plan.get("affected_modules", [])))
            if not authorized:
                raise AgentRuntimeError("FUNCTIONAL_REPAIR repair_plan has no authorized affected_modules")
            unauthorized = sorted(changed_modules - authorized)
            if unauthorized:
                raise AgentRuntimeError(
                    f"FUNCTIONAL_REPAIR attempted modules outside Debugger authorization: {unauthorized}"
                )
            protected = set(map(str, repair_plan.get("protected_modules", [])))
            touched_protected = sorted(changed_modules & protected)
            if touched_protected:
                raise AgentRuntimeError(
                    f"FUNCTIONAL_REPAIR attempted protected modules: {touched_protected}"
                )
            if feedback.get("frozen_verifier") is not True:
                raise AgentRuntimeError("FUNCTIONAL_REPAIR must preserve the frozen verifier")

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
- Architect artifacts are frozen technical decisions. Do not silently reinterpret or
  change them; return ARCHITECTURE_CONFLICT when a new architecture decision is needed.
- LangGraph supplies deterministic repair/optimization feedback. Do not simulate
  free-form agent conversations.

GENERIC RULES
-------------
1. Derive operations, types, widths, dimensions, parameters, storage, scheduling,
   protocols, reset, and module names only from supplied frozen contracts.
2. INITIAL_GENERATION emits exactly one .sv file per manifest module.
3. Preserve the interface, latency semantics, arithmetic, storage, and control contract.
4. Generate synthesizable SystemVerilog and never claim deterministic tool PASS.
5. For repair modes, use existing RTL and authorized feedback. Emit only modules that
   actually need modification; untouched files remain in the workspace.
6. FUNCTIONAL_REPAIR may change only modules listed in
   feedback.repair_plan.affected_modules, must not change protected_modules or any
   frozen interface/test/reference behavior, and requires FULL regression.
7. If authorized evidence cannot support a coherent patch, return REPAIR_BLOCKED; if
   a new Architect decision is needed, return ARCHITECTURE_CONFLICT.
8. Populate contract_checks as textual self-review only.

FILE PATH RULE
--------------
Paths are relative to multigent/workspace/rtl, without rtl/ prefix, absolute paths,
or traversal.

RTL TASK ENVELOPE
-----------------
{serialized}
"""


def _load_recorded_request(run_id: str) -> str:
    path = WORKSPACE_ROOT / "specs" / f"request-{run_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Architect intake record not found: {path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    request = value.get("user_request") if isinstance(value, Mapping) else None
    if not isinstance(request, str) or not request.strip():
        raise AgentRuntimeError(f"No usable user_request found in {path}")
    return request.strip()


def _load_mapping(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    value = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must decode to a mapping/object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the generic RTL Generator Agent")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-type", choices=sorted(TASK_TYPES), default="INITIAL_GENERATION")
    parser.add_argument("--context", type=Path, default=None)
    parser.add_argument("--feedback", type=Path, default=None)
    parser.add_argument("--architecture-dir", type=Path, default=WORKSPACE_ROOT / "architecture")
    parser.add_argument("--output-dir", type=Path, default=WORKSPACE_ROOT / "rtl")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-mode", choices=["responses", "chat_completions"], default=None)
    args = parser.parse_args()

    context = _load_mapping(args.context) if args.context is not None else build_rtl_context(
        user_request=_load_recorded_request(args.run_id),
        architecture_dir=args.architecture_dir,
    )
    feedback = _load_mapping(args.feedback) if args.feedback is not None else None
    result = RTLGeneratorAgent(model=args.model, api_mode=args.api_mode).run(
        context,
        task_type=args.task_type,
        feedback=feedback,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps({
        "status": result["status"],
        "task_type": result["task_type"],
        "files": [item["path"] for item in result["files"]],
    }, indent=2))


if __name__ == "__main__":
    main()
