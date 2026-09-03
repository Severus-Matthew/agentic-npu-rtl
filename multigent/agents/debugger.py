"""API-backed generic Debugger / repair-planning agent.

The Debugger consumes frozen contracts, current RTL, frozen verifier artifacts, and
authoritative deterministic failure evidence. It never edits RTL. Its structured
repair plan is routed by LangGraph to the existing RTL Generator in
``FUNCTIONAL_REPAIR`` mode.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator

from multigent.intake.request_builder import WORKSPACE_ROOT

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


DEBUGGER_OUTPUT_SCHEMA = SCHEMA_ROOT / "debugger_output.schema.json"
DIAGNOSIS_SCHEMA = SCHEMA_ROOT / "diagnosis.schema.json"
REPAIR_PLAN_SCHEMA = SCHEMA_ROOT / "repair_plan.schema.json"


class DebuggerAgent(APIAgent):
    """Diagnose deterministic RTL failures and emit constrained repair plans."""

    def __init__(self, *, model: str | None = None, api_mode: str | None = None) -> None:
        super().__init__(
            AgentConfig(
                name="debugger",
                role_skill="debugger",
                model=model or os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex"),
                api_mode=api_mode or os.getenv("NPU_AGENT_API_MODE", "responses"),
            )
        )

    def load_instructions(self) -> str:
        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        return (
            "# DEBUGGER TECHNICAL SKILL\n\n"
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
        self._validate_context(context)
        root = workspace_dir or WORKSPACE_ROOT
        diagnostics_dir = root / "diagnostics"
        diagnostics_dir.mkdir(parents=True, exist_ok=True)

        result = self.run_structured(
            task=self._build_task(context),
            schema_path=DEBUGGER_OUTPUT_SCHEMA,
            log_name=f"debugger-{run_id}.json",
        )
        self._validate_result(result=result, context=context)

        diagnosis = dict(result["diagnosis"])
        (diagnostics_dir / "diagnosis.json").write_text(
            json.dumps(diagnosis, indent=2) + "\n", encoding="utf-8"
        )
        if result["repair_plan"] is not None:
            repair_plan = dict(result["repair_plan"])
            (diagnostics_dir / "repair_plan.json").write_text(
                json.dumps(repair_plan, indent=2) + "\n", encoding="utf-8"
            )
        return result

    def run_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        context = self.build_context_from_state(state)
        run_id = str(state.get("run_id", "langgraph"))
        architecture_version = int(state.get("architecture_version", 0))
        current_repair = int(state.get("repair_iteration", 0))
        node_run_id = f"{run_id}-debug-av{architecture_version}-r{current_repair}"
        result = self.run(context, run_id=node_run_id)

        update: dict[str, Any] = {
            "debugger_status": result["status"],
            "diagnosis": result["diagnosis"],
            "repair_plan": result["repair_plan"],
            "architecture_conflict": result["architecture_conflict"],
        }

        if result["status"] == "REPAIR_PLAN_READY":
            next_repair = current_repair + 1
            update.update(
                {
                    "repair_iteration": next_repair,
                    "rtl_task_type": "FUNCTIONAL_REPAIR",
                    "rtl_feedback": {
                        "source": "debugger",
                        "repair_iteration": next_repair,
                        "diagnosis": result["diagnosis"],
                        "repair_plan": result["repair_plan"],
                        "verification_evidence": context["verification_evidence"],
                        "frozen_verifier": True,
                    },
                    "needs_regression": True,
                }
            )
        return update

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
        if not isinstance(value, dict):
            raise AgentRuntimeError(f"Expected mapping artifact at {path}")
        return value

    @classmethod
    def build_context_from_state(cls, state: Mapping[str, Any]) -> dict[str, Any]:
        evidence = state.get("verification_evidence")
        if not isinstance(evidence, Mapping):
            raise AgentRuntimeError(
                "Debugger requires authoritative state['verification_evidence']"
            )
        failure_class = state.get("failure_class")
        if not isinstance(failure_class, str) or not failure_class.strip():
            raise AgentRuntimeError("Debugger requires state['failure_class']")

        architecture_dir = Path(
            state.get("architecture_dir", WORKSPACE_ROOT / "architecture")
        )
        frozen = {
            "architecture_contract": cls._load_mapping(
                architecture_dir / "architecture_contract.yaml"
            ),
            "interface_contract": cls._load_mapping(
                architecture_dir / "interface_contract.yaml"
            ),
            "module_manifest": cls._load_mapping(
                architecture_dir / "module_manifest.json"
            ),
            "acceptance_criteria": cls._load_mapping(
                architecture_dir / "acceptance_criteria.yaml"
            ),
        }

        rtl_dir = WORKSPACE_ROOT / "rtl"
        rtl = {
            path.relative_to(rtl_dir).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(rtl_dir.rglob("*.sv"))
        }
        if not rtl:
            raise AgentRuntimeError("Debugger requires existing RTL source")

        reference_dir = WORKSPACE_ROOT / "reference"
        tests_dir = WORKSPACE_ROOT / "tests"
        reference = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(reference_dir.glob("*.py"))
        }
        tests = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(tests_dir.glob("*.py"))
        }

        return {
            "user_request": str(state.get("user_request", "")),
            "architecture_version": int(state.get("architecture_version", 0)),
            "repair_iteration": int(state.get("repair_iteration", 0)),
            "failure_class": failure_class,
            "verification_status": str(state.get("verification_status", "")),
            "verification_evidence": dict(evidence),
            "frozen_architecture": frozen,
            "current_rtl": rtl,
            "frozen_reference": reference,
            "frozen_tests": tests,
            "prior_diagnosis": state.get("diagnosis"),
            "prior_repair_plan": state.get("repair_plan"),
            "history": list(state.get("history", [])),
            "provenance": {
                "deterministic_evidence_authoritative": True,
                "tests_frozen_during_functional_repair": True,
                "debugger_may_edit_rtl": False,
            },
        }

    @staticmethod
    def _manifest_modules(context: Mapping[str, Any]) -> set[str]:
        manifest = context["frozen_architecture"]["module_manifest"]
        return {str(item["name"]) for item in manifest["modules"]}

    @staticmethod
    def _interface_signals(context: Mapping[str, Any]) -> set[str]:
        interface = context["frozen_architecture"]["interface_contract"]
        return {str(item["name"]) for item in interface.get("signals", [])}

    @classmethod
    def _validate_context(cls, context: Mapping[str, Any]) -> None:
        required = {
            "failure_class",
            "verification_status",
            "verification_evidence",
            "frozen_architecture",
            "current_rtl",
            "frozen_reference",
            "frozen_tests",
            "provenance",
        }
        missing = sorted(required - set(context))
        if missing:
            raise AgentRuntimeError(f"Debugger context missing fields: {missing}")
        if context["verification_status"] not in {
            "COMPILE_FAILURE",
            "SIMULATION_FAILURE",
            "SIMULATION_TIMEOUT",
        }:
            raise AgentRuntimeError(
                "Debugger may run only after a deterministic verification failure"
            )
        provenance = context["provenance"]
        if not isinstance(provenance, Mapping):
            raise AgentRuntimeError("Debugger provenance must be a mapping")
        if provenance.get("deterministic_evidence_authoritative") is not True:
            raise AgentRuntimeError("Debugger context must mark tool evidence authoritative")
        if provenance.get("tests_frozen_during_functional_repair") is not True:
            raise AgentRuntimeError("Functional repair must preserve frozen verifier artifacts")

    @classmethod
    def _validate_result(
        cls, *, result: Mapping[str, Any], context: Mapping[str, Any]
    ) -> None:
        diagnosis = result["diagnosis"]
        repair_plan = result["repair_plan"]
        conflict = result["architecture_conflict"]
        status = result["status"]

        Draft202012Validator(
            json.loads(DIAGNOSIS_SCHEMA.read_text(encoding="utf-8"))
        ).validate(diagnosis)
        if repair_plan is not None:
            Draft202012Validator(
                json.loads(REPAIR_PLAN_SCHEMA.read_text(encoding="utf-8"))
            ).validate(repair_plan)

        manifest_modules = cls._manifest_modules(context)
        diagnosed_modules = set(map(str, diagnosis["affected_modules"]))
        unknown = sorted(diagnosed_modules - manifest_modules)
        if unknown:
            raise AgentRuntimeError(f"Debugger diagnosed undeclared modules: {unknown}")
        if str(diagnosis["failure_class"]) != str(context["failure_class"]):
            raise AgentRuntimeError(
                "Debugger failure_class must preserve deterministic tool classification"
            )
        if not diagnosis["evidence"]:
            raise AgentRuntimeError("Debugger diagnosis requires concrete evidence")

        if status == "REPAIR_PLAN_READY":
            if not isinstance(repair_plan, Mapping):
                raise AgentRuntimeError("REPAIR_PLAN_READY requires repair_plan")
            if conflict is not None or diagnosis["architecture_change_required"]:
                raise AgentRuntimeError(
                    "RTL repair cannot simultaneously require an architecture change"
                )
            affected = set(map(str, repair_plan["affected_modules"]))
            if not affected:
                raise AgentRuntimeError("Repair plan requires at least one affected module")
            if affected != diagnosed_modules:
                raise AgentRuntimeError(
                    "repair_plan.affected_modules must match diagnosed affected_modules"
                )
            expected_protected = manifest_modules - affected
            if set(map(str, repair_plan["protected_modules"])) != expected_protected:
                raise AgentRuntimeError(
                    "repair_plan must protect every unaffected manifest module"
                )
            if set(map(str, repair_plan["protected_interfaces"])) != cls._interface_signals(context):
                raise AgentRuntimeError(
                    "functional repair must protect every frozen top-level interface signal"
                )
            if float(diagnosis["confidence"]) < 0.60:
                raise AgentRuntimeError(
                    "Low-confidence diagnosis may not authorize an RTL repair"
                )
            if repair_plan["regression_required"] != "FULL":
                raise AgentRuntimeError("Functional RTL repair requires FULL regression")

        elif status == "ARCHITECTURE_ESCALATION":
            if repair_plan is not None:
                raise AgentRuntimeError(
                    "ARCHITECTURE_ESCALATION must not authorize an RTL patch"
                )
            if not diagnosis["architecture_change_required"]:
                raise AgentRuntimeError(
                    "Architecture escalation requires architecture_change_required=true"
                )
            if not isinstance(conflict, Mapping):
                raise AgentRuntimeError(
                    "ARCHITECTURE_ESCALATION requires structured architecture_conflict"
                )
            unknown_conflict = sorted(
                set(map(str, conflict["affected_modules"])) - manifest_modules
            )
            if unknown_conflict:
                raise AgentRuntimeError(
                    f"Architecture conflict names undeclared modules: {unknown_conflict}"
                )

        elif status == "EVIDENCE_INSUFFICIENT":
            if repair_plan is not None or conflict is not None:
                raise AgentRuntimeError(
                    "EVIDENCE_INSUFFICIENT must not authorize repair or architecture change"
                )
            if not diagnosis["additional_evidence_requested"]:
                raise AgentRuntimeError(
                    "EVIDENCE_INSUFFICIENT must request specific deterministic evidence"
                )
        else:
            raise AgentRuntimeError(f"Unknown Debugger status: {status!r}")

    @staticmethod
    def _build_task(context: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(dict(context), sort_keys=False, default_flow_style=False)
        return f"""Diagnose the deterministic RTL failure and produce a constrained repair decision.

RULES
-----
1. Treat deterministic verification evidence as authoritative. Establish the fatal
   failure before reading current RTL and separate fatal errors from warnings.
2. Expected behavior comes from the frozen architecture/interface and frozen
   independent verifier artifacts. Never weaken or edit tests/reference behavior.
3. Return REPAIR_PLAN_READY only for a coherent RTL-only patch. The plan must name
   exactly the affected manifest modules, protect every other manifest module, list
   every frozen top-level interface signal in protected_interfaces, and require FULL
   regression.
4. Return ARCHITECTURE_ESCALATION only if the frozen contract itself requires a new
   Architect decision; implementation mistakes are not architecture conflicts.
5. Return EVIDENCE_INSUFFICIENT rather than proposing a broad speculative rewrite
   when the available deterministic evidence is inadequate.
6. Do not emit RTL code. Describe the conceptual repair precisely enough for the RTL
   Generator to implement while preserving all unaffected behavior.
7. Preserve the deterministic failure_class supplied in the context.

DEBUGGER CONTEXT
----------------
{serialized}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run generic RTL Debugger Agent")
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--api-mode", choices=["responses", "chat_completions"], default=None
    )
    args = parser.parse_args()
    context = DebuggerAgent._load_mapping(args.context)
    result = DebuggerAgent(model=args.model, api_mode=args.api_mode).run(
        context, run_id=args.run_id
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "failure_class": result["diagnosis"]["failure_class"],
                "affected_modules": result["diagnosis"]["affected_modules"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
