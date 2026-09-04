"""API-backed independent Verifier Agent.

The Verifier creates a specification-derived Python reference model and cocotb
regression environment from the original request and frozen Architect artifacts.
Generated RTL is deliberately excluded from its context. Deterministic tool nodes
later compile the RTL and execute these tests.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context

from .base import APIAgent, AgentConfig, AgentRuntimeError, SCHEMA_ROOT


VERIFIER_OUTPUT_SCHEMA = SCHEMA_ROOT / "verifier_output.schema.json"
_FORBIDDEN_IMPORT_ROOTS = {
    "subprocess", "socket", "requests", "urllib", "http", "pathlib", "glob", "importlib"
}
_FORBIDDEN_CALL_NAMES = {"open", "exec", "eval", "compile", "__import__"}
_FORBIDDEN_CALL_ATTRIBUTES = {
    "system", "popen", "run", "call", "check_call", "check_output",
    "read_text", "read_bytes", "write_text", "write_bytes", "open", "glob", "rglob"
}


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
        if not self.role_skill_path.is_file():
            raise FileNotFoundError(self.role_skill_path)
        return "# INDEPENDENT VERIFIER TECHNICAL SKILL\n\n" + self.role_skill_path.read_text(encoding="utf-8") + "\n"

    def run(
        self,
        context: Mapping[str, Any],
        *,
        workspace_dir: Path | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
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
                self._write_python(reference_dir, item, owned_root="reference")
            for item in result["test_files"]:
                self._write_python(tests_dir, item, owned_root="tests")
            (verification_dir / "verification_plan.yaml").write_text(
                yaml.safe_dump(result["verification_plan"], sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
            (verification_dir / "verifier_result.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
        return result

    def run_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        context = state.get("verification_context")
        if not isinstance(context, Mapping):
            user_request = state.get("user_request")
            if not isinstance(user_request, str) or not user_request.strip():
                raise AgentRuntimeError("Verifier node requires verification_context or user_request")
            context = build_verification_context(
                user_request=user_request,
                architecture_dir=Path(state.get("architecture_dir", WORKSPACE_ROOT / "architecture")),
            )

        run_id = str(state.get("run_id", "langgraph"))
        architecture_version = int(state.get("architecture_version", 0))
        repair_iteration = int(state.get("repair_iteration", 0))
        result = self.run(
            context,
            run_id=f"{run_id}-verify-av{architecture_version}-r{repair_iteration}",
        )
        return {
            "verifier_status": result["status"],
            "verifier_result": result,
            "verification_plan": result["verification_plan"],
            "architecture_conflict": result["architecture_conflict"],
            "verification_context": dict(context),
        }

    @staticmethod
    def _validate_context(context: Mapping[str, Any]) -> None:
        required = {"user_request", "verification_policy", "frozen_architecture", "provenance"}
        missing = sorted(required - set(context))
        if missing:
            raise AgentRuntimeError(f"Verifier context missing required fields: {missing}")
        provenance = context["provenance"]
        if not isinstance(provenance, Mapping):
            raise AgentRuntimeError("Verifier provenance must be a mapping")
        if provenance.get("includes_generated_rtl") is not False:
            raise AgentRuntimeError("Independent Verifier context must exclude generated RTL")
        if provenance.get("includes_rtl_generator_output") is not False:
            raise AgentRuntimeError("Independent Verifier context must exclude RTL Generator output")
        frozen = context["frozen_architecture"]
        if not isinstance(frozen, Mapping):
            raise AgentRuntimeError("Verifier frozen_architecture must be a mapping")
        needed = {"architecture_contract", "interface_contract", "module_manifest", "acceptance_criteria"}
        missing_artifacts = sorted(needed - set(frozen))
        if missing_artifacts:
            raise AgentRuntimeError(f"Verifier context missing frozen artifacts: {missing_artifacts}")

    @staticmethod
    def _safe_python_filename(raw: str, *, owned_root: str | None = None) -> str:
        path = Path(str(raw))
        if path.is_absolute() or ".." in path.parts:
            raise AgentRuntimeError(f"Unsafe verification Python path: {raw!r}")
        parts = path.parts
        if len(parts) == 1:
            filename = parts[0]
        elif len(parts) == 2 and owned_root is not None and parts[0] == owned_root:
            filename = parts[1]
        else:
            expected = f"{owned_root}/<file>.py" if owned_root else "<file>.py"
            raise AgentRuntimeError(f"Verification Python path {raw!r} is outside its owned root; expected {expected}")
        normalized = Path(filename)
        if normalized.suffix != ".py" or normalized.name.startswith("."):
            raise AgentRuntimeError(f"Invalid verification Python filename: {raw!r}")
        return normalized.name

    @staticmethod
    def _canonical_test_module(raw: str) -> str:
        """Normalize verifier plan references to a cocotb Python module stem.

        Accepted forms include ``test_core``, ``test_core.py``,
        ``tests/test_core.py``, ``tests.test_core``, and pytest-style selectors such
        as ``tests/test_core.py::test_backpressure``. Cocotb's runner consumes test
        *modules*, so any ``::...`` selector is intentionally reduced to its owning
        module. The generated test file remains the authority for which cocotb tests
        exist inside that module.
        """

        value = str(raw).strip()
        if not value:
            raise AgentRuntimeError("Empty verification test module reference")

        if "::" in value:
            module_part, selector = value.split("::", 1)
            if not module_part.strip() or not selector.strip():
                raise AgentRuntimeError(
                    f"Malformed verification test selector: {raw!r}"
                )
            value = module_part.strip()

        if value.startswith("tests."):
            value = value[len("tests."):]

        if "/" in value or "\\" in value:
            value = value.replace("\\", "/")
            filename = VerifierAgent._safe_python_filename(value, owned_root="tests")
            value = Path(filename).stem
        elif value.endswith(".py"):
            if Path(value).name != value:
                raise AgentRuntimeError(f"Unsafe verification test module reference: {raw!r}")
            value = Path(value).stem

        if not value.isidentifier():
            raise AgentRuntimeError(
                f"Verification test module reference {raw!r} is not a flat importable Python module"
            )
        return value

    @classmethod
    def _write_python(cls, target: Path, item: Mapping[str, Any], *, owned_root: str) -> None:
        filename = cls._safe_python_filename(str(item["path"]), owned_root=owned_root)
        content = str(item["content"])
        (target / filename).write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")

    @classmethod
    def _normalize_plan_test_modules(cls, plan: Mapping[str, Any]) -> None:
        """Canonicalize test-module references before semantic validation/write.

        ``test_modules`` itself must contain unique modules. Regression groups may
        enumerate individual pytest-style selectors from the same generated file;
        those collapse to a single owning cocotb module while preserving first-seen
        order. Every group is constrained to declared ``test_modules``.
        """

        if not isinstance(plan, dict):
            raise AgentRuntimeError("verification_plan must be a mutable mapping")

        modules = [cls._canonical_test_module(item) for item in plan["test_modules"]]
        if len(modules) != len(set(modules)):
            raise AgentRuntimeError("verification_plan.test_modules contains duplicate module references")
        plan["test_modules"] = modules
        declared = set(modules)

        groups = plan.get("regression_groups")
        if not isinstance(groups, dict):
            raise AgentRuntimeError("verification_plan.regression_groups must be a mapping")
        for group_name in ("smoke", "targeted", "full"):
            normalized: list[str] = []
            seen: set[str] = set()
            for item in groups[group_name]:
                module = cls._canonical_test_module(item)
                if module not in seen:
                    normalized.append(module)
                    seen.add(module)
            unknown = sorted(seen - declared)
            if unknown:
                raise AgentRuntimeError(
                    f"verification_plan.regression_groups.{group_name} references undeclared test modules: {unknown}"
                )
            groups[group_name] = normalized

    @classmethod
    def _validate_result(cls, *, result: Mapping[str, Any], context: Mapping[str, Any]) -> None:
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
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT must not emit verification Python files")
            if not isinstance(conflict, Mapping):
                raise AgentRuntimeError("ARCHITECTURE_CONFLICT requires structured conflict details")
            unknown = sorted(set(conflict["affected_modules"]) - module_names)
            if unknown:
                raise AgentRuntimeError(f"Verifier conflict references undeclared modules: {unknown}")
            return

        if status != "VERIFICATION_READY":
            raise AgentRuntimeError(f"Unknown verifier status: {status!r}")
        if conflict is not None:
            raise AgentRuntimeError("VERIFICATION_READY cannot also contain architecture_conflict")
        if not references or not tests:
            raise AgentRuntimeError("VERIFICATION_READY requires reference model and cocotb tests")
        if str(plan["top_module"]) != top:
            raise AgentRuntimeError(f"Verification plan top={plan['top_module']!r} does not match manifest top={top!r}")

        reference_names: set[str] = set()
        for item in references:
            name = cls._safe_python_filename(str(item["path"]), owned_root="reference")
            if name in reference_names:
                raise AgentRuntimeError(f"Duplicate reference filename: {name}")
            reference_names.add(name)
            cls._validate_python_content(name, str(item["content"]), cocotb_required=False)

        test_names: set[str] = set()
        test_modules: set[str] = set()
        test_contents: list[str] = []
        for item in tests:
            name = cls._safe_python_filename(str(item["path"]), owned_root="tests")
            if name in test_names:
                raise AgentRuntimeError(f"Duplicate test filename: {name}")
            test_names.add(name)
            test_modules.add(Path(name).stem)
            if "full" not in set(item["regression_groups"]):
                raise AgentRuntimeError(f"Initial verifier test file {name} must belong to full regression")
            content = str(item["content"])
            cls._validate_python_content(name, content, cocotb_required=True)
            test_contents.append(content)

        cls._normalize_plan_test_modules(plan)
        normalized_plan_modules = set(map(str, plan["test_modules"]))
        if normalized_plan_modules != test_modules:
            raise AgentRuntimeError(
                "verification_plan.test_modules must reference exactly the generated test files"
            )

        policy = context["verification_policy"]
        minimum_randomized = int(policy.get("randomized_transactions_minimum", 0))
        if int(plan["randomized_test_count"]) < minimum_randomized:
            raise AgentRuntimeError(
                f"Verifier randomized_test_count={plan['randomized_test_count']} is below policy minimum {minimum_randomized}"
            )
        minimum_wall_timeout = int(policy.get("regression_wall_timeout_seconds_minimum", 1))
        if int(plan["timeout_seconds"]) < minimum_wall_timeout:
            raise AgentRuntimeError(
                f"Verifier timeout_seconds={plan['timeout_seconds']} is below full-regression wall-clock policy minimum {minimum_wall_timeout}"
            )
        if set(map(str, plan["regression_groups"]["full"])) != test_modules:
            raise AgentRuntimeError("Initial full regression group must contain every generated test module")

        cls._validate_ready_valid_driver_safety(test_contents, context)
        cls._validate_required_signal_coverage(test_contents, context)

    @staticmethod
    def _validate_python_content(filename: str, content: str, *, cocotb_required: bool) -> None:
        if not content.strip():
            raise AgentRuntimeError(f"Generated Python file {filename} is empty")
        if "```" in content:
            raise AgentRuntimeError(f"Generated Python file {filename} contains Markdown fences")
        try:
            tree = ast.parse(content, filename=filename, mode="exec")
        except SyntaxError as exc:
            raise AgentRuntimeError(f"Generated Python file {filename} has syntax error: {exc.msg}") from exc

        imported_cocotb = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    imported_cocotb = imported_cocotb or root == "cocotb"
                    if root in _FORBIDDEN_IMPORT_ROOTS:
                        raise AgentRuntimeError(f"Generated verification file {filename} imports forbidden capability {root}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".", 1)[0]
                imported_cocotb = imported_cocotb or root == "cocotb"
                if root in _FORBIDDEN_IMPORT_ROOTS:
                    raise AgentRuntimeError(f"Generated verification file {filename} imports forbidden capability {root}")
                if module == "cocotb.result" and any(alias.name == "SimTimeoutError" for alias in node.names):
                    raise AgentRuntimeError(
                        f"Generated test file {filename} uses obsolete cocotb 2.x API: import SimTimeoutError from cocotb.triggers, not cocotb.result"
                    )
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALL_NAMES:
                    raise AgentRuntimeError(f"Generated verification file {filename} calls forbidden capability {node.func.id}")
                if isinstance(node.func, ast.Attribute) and node.func.attr in _FORBIDDEN_CALL_ATTRIBUTES:
                    raise AgentRuntimeError(f"Generated verification file {filename} calls forbidden capability {node.func.attr}")
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "cocotb"
                    and node.func.attr == "start"
                ):
                    raise AgentRuntimeError(
                        f"Generated test file {filename} uses obsolete cocotb API cocotb.start(); use cocotb.start_soon()"
                    )
        if cocotb_required and not imported_cocotb:
            raise AgentRuntimeError(f"Generated test file {filename} does not import cocotb")

    @classmethod
    def _validate_ready_valid_driver_safety(
        cls, test_contents: list[str], context: Mapping[str, Any]
    ) -> None:
        interface = context["frozen_architecture"]["interface_contract"]
        if "ready_valid" not in str(interface.get("protocol", "")).lower():
            return

        for content in test_contents:
            tree = ast.parse(content, mode="exec")
            for loop in (node for node in ast.walk(tree) if isinstance(node, ast.While)):
                for node in ast.walk(loop):
                    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                        continue
                    value = node.value
                    if not (isinstance(value, ast.Constant) and value.value in {0, False}):
                        continue
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        base_name = cls._assigned_value_base_name(target)
                        if base_name and "valid" in base_name.lower():
                            raise AgentRuntimeError(
                                "Generated ready/valid source driver deasserts valid inside a handshake wait loop; source stalls must occur before presenting a beat and valid/payload must remain stable until handshake"
                            )

    @staticmethod
    def _assigned_value_base_name(target: ast.AST) -> str | None:
        if not isinstance(target, ast.Attribute) or target.attr != "value":
            return None
        base = target.value
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        return None

    @classmethod
    def _validate_required_signal_coverage(
        cls, test_contents: list[str], context: Mapping[str, Any]
    ) -> None:
        interface = context["frozen_architecture"]["interface_contract"]
        policy = context["verification_policy"]
        signals = list(interface.get("signals", []))

        referenced: set[str] = set()
        for content in test_contents:
            tree = ast.parse(content, mode="exec")
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "dut"
                ):
                    referenced.add(node.attr)

        required: set[str] = set()
        if policy.get("require_completion_behavior_tests_when_defined"):
            required |= cls._signals_matching_semantics(signals, {"done", "complete", "completion"})
        if policy.get("require_error_behavior_tests_when_defined"):
            required |= cls._signals_matching_semantics(signals, {"error", "fault"})

        missing = sorted(required - referenced)
        if missing:
            raise AgentRuntimeError(
                "Verifier claims readiness without referencing required contract-visible completion/error signals: "
                + ", ".join(missing)
            )

    @staticmethod
    def _signals_matching_semantics(signals: list[Any], tokens: set[str]) -> set[str]:
        matched: set[str] = set()
        for item in signals:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("name", ""))
            text = f"{name} {item.get('semantic', '')}".lower()
            if any(token in text for token in tokens):
                matched.add(name)
        return matched

    @staticmethod
    def _build_task(context: Mapping[str, Any]) -> str:
        serialized = yaml.safe_dump(dict(context), sort_keys=False, default_flow_style=False)
        return f"""Create an independent executable verification environment for the frozen hardware contract.

INDEPENDENCE BOUNDARY
---------------------
- The envelope contains the original request, fixed verification policy, and frozen
  Architect artifacts only. Generated RTL and RTL Generator output are absent.
- Do not ask for RTL or infer expected behavior from implementation conventions.
- Generated Python may not use filesystem, subprocess, dynamic-import, or network
  capabilities. Deterministic Verilator/cocotb nodes execute your artifacts later.

OUTPUT RULES
------------
1. Return VERIFICATION_READY with reference/test contents and a complete plan, or
   ARCHITECTURE_CONFLICT when an executable oracle requires a new Architect decision.
2. Reference paths may be foo.py or reference/foo.py; test paths may be bar.py or
   tests/bar.py. No nested/cross-owned paths.
3. verification_plan.test_modules and regression_groups identify generated cocotb
   Python modules. Bare module names are preferred. If a pytest-style ``::test``
   selector is emitted, the runtime canonicalizes it to its owning cocotb module.
4. Full regression contains every generated test module and meets the randomized
   transaction minimum with a deterministic seed.
5. verification_plan.timeout_seconds is the wall-clock budget for the whole
   regression and must satisfy the policy minimum; tests need separate simulation
   timeouts/bounded waits.
6. Use cocotb 2.x APIs: cocotb.start_soon(), and SimTimeoutError from cocotb.triggers.
7. For ready/valid input sources, randomized throttling may delay presenting a beat,
   but once valid=1 for a beat, keep valid=1 and payload stable until ready&&valid.
   Do not toggle/deassert valid inside the handshake wait loop.
8. If completion/error behavior is defined and required by policy, generated tests
   must actually reference and check those external signal names.
9. Use only contract-declared top-level signals and preserve verifier independence.

VERIFIER CONTEXT
----------------
{serialized}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the independent Verifier Agent")
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--architecture-dir", type=Path, default=WORKSPACE_ROOT / "architecture")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-mode", choices=["responses", "chat_completions"], default=None)
    args = parser.parse_args()
    context = build_verification_context(
        user_request=args.request,
        architecture_dir=args.architecture_dir,
    )
    result = VerifierAgent(model=args.model, api_mode=args.api_mode).run(context, run_id=args.run_id)
    print(json.dumps({
        "status": result["status"],
        "top_module": result["verification_plan"].get("top_module"),
        "test_modules": result["verification_plan"].get("test_modules", []),
        "randomized_test_count": result["verification_plan"].get("randomized_test_count", 0),
        "architecture_conflict": result["architecture_conflict"],
    }, indent=2))


if __name__ == "__main__":
    main()
