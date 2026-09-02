"""Shared API runtime used by every LLM agent in the NPU workflow.

Design principles
-----------------
* Every role uses the same configured model/backend for controlled experiments.
* Every role loads the global project contract followed by its role skill.
* The model returns schema-constrained JSON; Python owns filesystem writes.
* Agents do not receive unrestricted write access to the repository.
* API credentials are read only from environment variables and are never logged.
* The backend supports both the OpenAI Responses API and Chat Completions API so
  the project can run against OpenAI-hosted models or compatible university
  gateways.

Required environment variables
------------------------------
OPENAI_API_KEY
    API key supplied by the configured provider/university gateway.

Optional environment variables
------------------------------
OPENAI_BASE_URL
    Provider base URL. Leave unset for the standard OpenAI API.
NPU_AGENT_MODEL
    Model/deployment name used by every agent.
NPU_AGENT_API_MODE
    ``responses`` (default) or ``chat_completions``.
NPU_AGENT_REASONING_EFFORT
    Optional reasoning effort for Responses API requests when supported.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from openai import OpenAI
from openai import OpenAIError


REPO_ROOT = Path(__file__).resolve().parents[2]
MULTIGENT_ROOT = REPO_ROOT / "multigent"
WORKSPACE_ROOT = MULTIGENT_ROOT / "workspace"
SCHEMA_ROOT = MULTIGENT_ROOT / "schemas"
SKILL_ROOT = REPO_ROOT / "Skills" / "npu_multiagent_skills" / "skills"

DEFAULT_AGENT_MODEL = os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex")
DEFAULT_API_MODE = os.getenv("NPU_AGENT_API_MODE", "responses")


class AgentRuntimeError(RuntimeError):
    """Raised when an API-backed agent cannot produce a valid structured result."""


# Backwards-compatible name for code written during the initial CLI scaffold.
CodexRuntimeError = AgentRuntimeError


@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration shared by all role-specific agents."""

    name: str
    role_skill: str
    model: str = DEFAULT_AGENT_MODEL
    api_mode: str = DEFAULT_API_MODE
    timeout_seconds: int = 1800


class APIAgent:
    """Base class for a role-specialized agent backed by an OpenAI-style API."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        if self.config.api_mode not in {"responses", "chat_completions"}:
            raise ValueError(
                "NPU_AGENT_API_MODE must be 'responses' or 'chat_completions'."
            )

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
        """Create the complete role prompt passed to the configured model."""

        return (
            f"{self.load_instructions()}\n\n"
            "# RUNTIME RULES\n\n"
            "You are running as one node inside a LangGraph workflow.\n"
            "Return only the structured result requested by the runtime.\n"
            "Do not claim that any compiler, simulator, Synopsys synthesis, timing, "
            "power, or area tool ran unless deterministic evidence was explicitly "
            "supplied in the task.\n"
            "Do not change requirements to make the task easier.\n\n"
            "# CURRENT TASK\n\n"
            f"{task}\n"
        )

    def _client(self) -> OpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AgentRuntimeError(
                "OPENAI_API_KEY is not set. Export your university/provider API key "
                "before running an agent."
            )

        base_url = os.getenv("OPENAI_BASE_URL")
        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "timeout": float(self.config.timeout_seconds),
        }
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/") + "/"
        return OpenAI(**kwargs)

    @staticmethod
    def _structured_format(schema: Mapping[str, Any], name: str) -> dict[str, Any]:
        """Build a Structured Outputs format accepted by modern OpenAI APIs."""

        # `$schema` is useful in repository files but is not needed by the model.
        normalized = dict(schema)
        normalized.pop("$schema", None)
        return {
            "type": "json_schema",
            "name": name.replace("-", "_")[:64],
            "schema": normalized,
            "strict": True,
        }

    def run_structured(
        self,
        *,
        task: str,
        schema_path: Path,
        log_name: str | None = None,
    ) -> dict[str, Any]:
        """Call the configured API and return schema-constrained JSON output."""

        if not schema_path.is_file():
            raise FileNotFoundError(f"Output schema does not exist: {schema_path}")

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        prompt = self.build_prompt(task)
        client = self._client()

        logs_dir = WORKSPACE_ROOT / "logs" / "agent_traces"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / (log_name or f"{self.config.name}.json")

        try:
            if self.config.api_mode == "responses":
                request: dict[str, Any] = {
                    "model": self.config.model,
                    "input": prompt,
                    "text": {
                        "format": self._structured_format(
                            schema, f"{self.config.name}_output"
                        )
                    },
                    "store": False,
                }
                effort = os.getenv("NPU_AGENT_REASONING_EFFORT")
                if effort:
                    request["reasoning"] = {"effort": effort}

                response = client.responses.create(**request)
                raw_output = response.output_text
                trace = {
                    "agent": self.config.name,
                    "api_mode": self.config.api_mode,
                    "model_requested": self.config.model,
                    "response_id": getattr(response, "id", None),
                    "model_returned": getattr(response, "model", None),
                    "status": getattr(response, "status", None),
                    "usage": (
                        response.usage.model_dump()
                        if getattr(response, "usage", None) is not None
                        and hasattr(response.usage, "model_dump")
                        else None
                    ),
                    "output_text": raw_output,
                }
            else:
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        key: value
                        for key, value in self._structured_format(
                            schema, f"{self.config.name}_output"
                        ).items()
                        if key != "type"
                    },
                }
                response = client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=response_format,
                )
                message = response.choices[0].message
                raw_output = message.content or ""
                trace = {
                    "agent": self.config.name,
                    "api_mode": self.config.api_mode,
                    "model_requested": self.config.model,
                    "response_id": getattr(response, "id", None),
                    "model_returned": getattr(response, "model", None),
                    "finish_reason": response.choices[0].finish_reason,
                    "usage": (
                        response.usage.model_dump()
                        if getattr(response, "usage", None) is not None
                        and hasattr(response.usage, "model_dump")
                        else None
                    ),
                    "output_text": raw_output,
                }
        except OpenAIError as exc:
            raise AgentRuntimeError(
                f"{self.config.name} API request failed using mode "
                f"'{self.config.api_mode}' and model '{self.config.model}': {exc}"
            ) from exc

        log_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")

        if not raw_output.strip():
            raise AgentRuntimeError(
                f"{self.config.name} returned no text output. See {log_path}."
            )

        try:
            return json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise AgentRuntimeError(
                f"{self.config.name} returned invalid JSON despite the structured "
                f"output request. See {log_path}: {exc}"
            ) from exc


# Keep the original class name as an alias so existing role wrappers/tests do not
# need an all-at-once rename. New code should import APIAgent.
CodexAgent = APIAgent


def load_json_schema(name: str) -> Mapping[str, Any]:
    """Load one schema from ``multigent/schemas``."""

    path = SCHEMA_ROOT / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))
