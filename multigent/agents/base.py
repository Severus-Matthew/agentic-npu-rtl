"""Shared Codex runtime used by every LLM agent in the NPU workflow.

Design principles
-----------------
* Every role uses the same Codex model/harness for controlled experiments.
* Every role loads the global project contract followed by its role skill.
* Codex returns schema-constrained JSON; Python owns filesystem writes.
* Agents do not receive unrestricted write access to the repository.
* The runtime records the Codex JSONL event stream for provenance.

Authentication is delegated to the Codex CLI. On a development machine run
``codex login`` once before executing the workflow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
MULTIGENT_ROOT = REPO_ROOT / "multigent"
WORKSPACE_ROOT = MULTIGENT_ROOT / "workspace"
SCHEMA_ROOT = MULTIGENT_ROOT / "schemas"
SKILL_ROOT = REPO_ROOT / "Skills" / "npu_multiagent_skills" / "skills"

DEFAULT_CODEX_MODEL = "gpt-5.3-codex"


class CodexRuntimeError(RuntimeError):
    """Raised when a Codex invocation cannot produce a valid agent result."""


@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration shared by all role-specific agents."""

    name: str
    role_skill: str
    model: str = DEFAULT_CODEX_MODEL
    timeout_seconds: int = 1800


class CodexAgent:
    """Base class for a role-specialized agent backed by ``codex exec``."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    @property
    def project_contract_path(self) -> Path:
        return SKILL_ROOT / "project_contract" / "SKILL.md"

    @property
    def role_skill_path(self) -> Path:
        return SKILL_ROOT / self.config.role_skill / "SKILL.md"

    def load_instructions(self) -> str:
        """Load global invariants first and role instructions second."""

        missing = [
            path
            for path in (self.project_contract_path, self.role_skill_path)
            if not path.is_file()
        ]
        if missing:
            raise FileNotFoundError(
                "Missing required skill files: " + ", ".join(map(str, missing))
            )

        project_contract = self.project_contract_path.read_text(encoding="utf-8")
        role_skill = self.role_skill_path.read_text(encoding="utf-8")
        return (
            "# GLOBAL PROJECT CONTRACT\n\n"
            f"{project_contract}\n\n"
            "# ROLE-SPECIFIC SKILL\n\n"
            f"{role_skill}\n"
        )

    def build_prompt(self, task: str) -> str:
        """Create a stable prompt prefix suitable for Codex prompt caching."""

        return (
            f"{self.load_instructions()}\n\n"
            "# RUNTIME RULES\n\n"
            "You are running as one node inside a LangGraph workflow.\n"
            "Return only the schema-constrained final result requested by the runtime.\n"
            "Do not claim that any compiler, simulator, synthesis, timing, power, or area "
            "tool ran unless deterministic evidence was explicitly supplied in the task.\n"
            "Do not change requirements to make the task easier.\n\n"
            "# CURRENT TASK\n\n"
            f"{task}\n"
        )

    def run_structured(
        self,
        *,
        task: str,
        schema_path: Path,
        log_name: str | None = None,
    ) -> dict[str, Any]:
        """Run Codex non-interactively and return its schema-constrained JSON result.

        ``codex exec`` is deliberately invoked with a read-only sandbox. The model
        proposes artifacts; role-specific Python code validates and writes them to
        whitelisted directories. This makes ownership enforceable in code rather
        than relying only on prompt compliance.
        """

        codex = shutil.which("codex")
        if codex is None:
            raise CodexRuntimeError(
                "Codex CLI was not found on PATH. Install Codex and run `codex login`."
            )
        if not schema_path.is_file():
            raise FileNotFoundError(f"Output schema does not exist: {schema_path}")

        logs_dir = WORKSPACE_ROOT / "logs" / "agent_traces"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / (log_name or f"{self.config.name}.jsonl")

        with tempfile.TemporaryDirectory(prefix=f"{self.config.name}-") as tmpdir:
            output_path = Path(tmpdir) / "final.json"
            command = [
                codex,
                "exec",
                "--ephemeral",
                "--json",
                "--model",
                self.config.model,
                "--sandbox",
                "read-only",
                "-C",
                str(REPO_ROOT),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                self.build_prompt(task),
            ]

            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )

            log_path.write_text(completed.stdout, encoding="utf-8")
            if completed.stderr:
                (log_path.with_suffix(".stderr.log")).write_text(
                    completed.stderr, encoding="utf-8"
                )

            if completed.returncode != 0:
                raise CodexRuntimeError(
                    f"{self.config.name} Codex invocation failed with exit code "
                    f"{completed.returncode}. See {log_path}."
                )
            if not output_path.is_file():
                raise CodexRuntimeError(
                    f"{self.config.name} completed without structured output. "
                    f"See {log_path}."
                )

            try:
                result = json.loads(output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CodexRuntimeError(
                    f"{self.config.name} returned invalid JSON: {exc}"
                ) from exc

        return result


def load_json_schema(name: str) -> Mapping[str, Any]:
    """Load one schema from ``multigent/schemas``."""

    path = SCHEMA_ROOT / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))
