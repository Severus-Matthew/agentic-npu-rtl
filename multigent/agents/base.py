"""Shared API runtime used by every LLM agent in the NPU workflow.

The runtime is intentionally accelerator-agnostic. Role-specific agents provide
technical instructions and JSON schemas; this module only handles API transport,
structured-output requests, validation, retry policy, and trace logging.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, cast

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from openai import OpenAI, OpenAIError


REPO_ROOT = Path(__file__).resolve().parents[2]
MULTIGENT_ROOT = REPO_ROOT / "multigent"
WORKSPACE_ROOT = MULTIGENT_ROOT / "workspace"
SCHEMA_ROOT = MULTIGENT_ROOT / "schemas"
SKILL_ROOT = REPO_ROOT / "Skills" / "npu_multiagent_skills" / "skills"

DEFAULT_AGENT_MODEL = os.getenv("NPU_AGENT_MODEL", "gpt-5.3-codex")
DEFAULT_API_MODE = os.getenv("NPU_AGENT_API_MODE", "responses")
DEFAULT_VERBOSITY = os.getenv("NPU_AGENT_VERBOSITY", "low")


class AgentRuntimeError(RuntimeError):
    """Raised when an API-backed agent cannot produce a usable structured result."""


CodexRuntimeError = AgentRuntimeError


@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration shared by all role-specific agents."""

    name: str
    role_skill: str
    model: str = DEFAULT_AGENT_MODEL
    api_mode: str = DEFAULT_API_MODE
    timeout_seconds: int = 1800
    structured_attempts: int = 2


class APIAgent:
    """Base class for a role-specialized agent backed by an OpenAI-style API."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        if self.config.api_mode not in {"responses", "chat_completions"}:
            raise ValueError(
                "NPU_AGENT_API_MODE must be 'responses' or 'chat_completions'."
            )
        if self.config.structured_attempts < 1:
            raise ValueError("structured_attempts must be at least 1")

    @property
    def project_contract_path(self) -> Path:
        return SKILL_ROOT / "project_contract" / "SKILL.md"

    @property
    def role_skill_path(self) -> Path:
        return SKILL_ROOT / self.config.role_skill / "SKILL.md"

    def load_instructions(self) -> str:
        """Load the shared contract and role skill.

        A role may override this method when it intentionally needs a narrower
        context. The Architect does so to avoid unrelated workflow instructions.
        """

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
        return (
            f"{self.load_instructions()}\n\n"
            "# RUNTIME RULES\n\n"
            "Return only the structured result requested by the runtime.\n"
            "Keep free-text fields concise and implementation-relevant. Do not repeat "
            "the same requirement in multiple fields unless the schema requires it.\n"
            "Do not claim that any compiler, simulator, synthesis, timing, power, "
            "area, or other engineering tool ran unless deterministic evidence was "
            "explicitly supplied in the task.\n"
            "Do not change requirements to make the task easier.\n\n"
            "# CURRENT TASK\n\n"
            f"{task}\n"
        )

    @staticmethod
    def _trust_env() -> bool:
        value = os.getenv("NPU_AGENT_TRUST_ENV", "false").strip().lower()
        return value not in {"0", "false", "no", "off"}

    @staticmethod
    def _base_url() -> str:
        """Return an explicit normalized API base URL.

        Passing the default explicitly prevents an empty OPENAI_BASE_URL environment
        variable from being interpreted as an invalid URL by an SDK transport.
        """

        configured = os.getenv("OPENAI_BASE_URL", "").strip()
        return (configured or "https://api.openai.com/v1").rstrip("/") + "/"

    @staticmethod
    def _optional_positive_int(name: str) -> int | None:
        raw = os.getenv(name, "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError as exc:
            raise AgentRuntimeError(f"{name} must be an integer, got {raw!r}") from exc
        if value < 1:
            raise AgentRuntimeError(f"{name} must be positive, got {value}")
        return value

    def _client(self) -> OpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AgentRuntimeError(
                "OPENAI_API_KEY is not set. Export the provider API key before "
                "running an agent."
            )

        http_client = httpx.Client(
            timeout=float(self.config.timeout_seconds),
            trust_env=self._trust_env(),
            follow_redirects=True,
        )
        return OpenAI(
            api_key=api_key,
            base_url=self._base_url(),
            timeout=float(self.config.timeout_seconds),
            http_client=cast(Any, http_client),
        )

    @staticmethod
    def _structured_format(schema: Mapping[str, Any], name: str) -> dict[str, Any]:
        normalized = dict(schema)
        normalized.pop("$schema", None)
        return {
            "type": "json_schema",
            "name": name.replace("-", "_")[:64],
            "schema": normalized,
            "strict": True,
        }

    @staticmethod
    def _dump_if_possible(value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value

    @staticmethod
    def _parse_and_validate(raw_output: str, schema: Mapping[str, Any]) -> dict[str, Any]:
        """Parse JSON and validate it locally against the declared handoff schema."""

        parsed = json.loads(raw_output)
        if not isinstance(parsed, dict):
            raise ValidationError("Structured agent output must be a JSON object")

        validator = Draft202012Validator(schema)
        validator.validate(parsed)
        return parsed

    def _responses_call(
        self,
        *,
        client: OpenAI,
        prompt: str,
        schema: Mapping[str, Any],
        schema_name: str,
    ) -> tuple[str, dict[str, Any]]:
        request: dict[str, Any] = {
            "model": self.config.model,
            "input": prompt,
            "text": {
                "format": self._structured_format(schema, schema_name),
                "verbosity": os.getenv("NPU_AGENT_VERBOSITY", DEFAULT_VERBOSITY),
            },
            "store": False,
        }

        effort = os.getenv("NPU_AGENT_REASONING_EFFORT", "").strip()
        if effort:
            request["reasoning"] = {"effort": effort}

        max_output_tokens = self._optional_positive_int("NPU_AGENT_MAX_OUTPUT_TOKENS")
        if max_output_tokens is not None:
            request["max_output_tokens"] = max_output_tokens

        response = client.responses.create(**request)
        status = getattr(response, "status", None)
        incomplete_details = self._dump_if_possible(
            getattr(response, "incomplete_details", None)
        )
        raw_output = response.output_text or ""

        metadata = {
            "response_id": getattr(response, "id", None),
            "model_returned": getattr(response, "model", None),
            "status": status,
            "incomplete_details": incomplete_details,
            "usage": self._dump_if_possible(getattr(response, "usage", None)),
            "output_chars": len(raw_output),
            "output_text": raw_output,
        }

        if status not in {None, "completed"}:
            reason = incomplete_details or "no incomplete details returned"
            raise AgentRuntimeError(
                f"{self.config.name} response status was {status!r}: {reason}"
            )

        return raw_output, metadata

    def _chat_call(
        self,
        *,
        client: OpenAI,
        prompt: str,
        schema: Mapping[str, Any],
        schema_name: str,
    ) -> tuple[str, dict[str, Any]]:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                key: value
                for key, value in self._structured_format(schema, schema_name).items()
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
        metadata = {
            "response_id": getattr(response, "id", None),
            "model_returned": getattr(response, "model", None),
            "finish_reason": response.choices[0].finish_reason,
            "usage": self._dump_if_possible(getattr(response, "usage", None)),
            "output_chars": len(raw_output),
            "output_text": raw_output,
        }
        return raw_output, metadata

    def run_structured(
        self,
        *,
        task: str,
        schema_path: Path,
        log_name: str | None = None,
    ) -> dict[str, Any]:
        """Run an agent with strict structured output and local validation.

        Transport/API failures are never retried here. If the API succeeds but the
        returned text is malformed JSON or violates the schema, one concise retry is
        allowed by default. This keeps retries targeted to model-output corruption
        rather than hiding network or configuration failures.
        """

        if not schema_path.is_file():
            raise FileNotFoundError(f"Output schema does not exist: {schema_path}")

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise AgentRuntimeError(
                f"Invalid local JSON schema {schema_path}: {exc.message}"
            ) from exc

        base_prompt = self.build_prompt(task)
        client = self._client()
        logs_dir = WORKSPACE_ROOT / "logs" / "agent_traces"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / (log_name or f"{self.config.name}.json")

        trace: dict[str, Any] = {
            "agent": self.config.name,
            "api_mode": self.config.api_mode,
            "model_requested": self.config.model,
            "schema": str(schema_path),
            "verbosity": os.getenv("NPU_AGENT_VERBOSITY", DEFAULT_VERBOSITY),
            "attempts": [],
        }

        last_error: Exception | None = None
        for attempt in range(1, self.config.structured_attempts + 1):
            retry_note = ""
            if attempt > 1:
                retry_note = (
                    "\n\n# STRUCTURED OUTPUT RETRY\n\n"
                    "The previous API response could not be parsed or validated. "
                    "Recompute the result and return a concise object that strictly "
                    "matches the requested schema. Keep descriptions short; do not "
                    "repeat requirements or add commentary outside the schema.\n"
                )
            prompt = base_prompt + retry_note

            try:
                if self.config.api_mode == "responses":
                    raw_output, metadata = self._responses_call(
                        client=client,
                        prompt=prompt,
                        schema=schema,
                        schema_name=f"{self.config.name}_output",
                    )
                else:
                    raw_output, metadata = self._chat_call(
                        client=client,
                        prompt=prompt,
                        schema=schema,
                        schema_name=f"{self.config.name}_output",
                    )
            except OpenAIError as exc:
                trace["attempts"].append(
                    {"attempt": attempt, "api_error": str(exc)}
                )
                log_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
                raise AgentRuntimeError(
                    f"{self.config.name} API request failed using mode "
                    f"'{self.config.api_mode}' and model '{self.config.model}': {exc}"
                ) from exc
            except AgentRuntimeError as exc:
                trace["attempts"].append(
                    {"attempt": attempt, "runtime_error": str(exc)}
                )
                log_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
                raise

            attempt_trace = {"attempt": attempt, **metadata}
            trace["attempts"].append(attempt_trace)

            if not raw_output.strip():
                last_error = AgentRuntimeError(
                    f"{self.config.name} returned no text output"
                )
                attempt_trace["parse_error"] = str(last_error)
                continue

            try:
                result = self._parse_and_validate(raw_output, schema)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                attempt_trace["parse_error"] = str(exc)
                if isinstance(exc, json.JSONDecodeError):
                    attempt_trace["parse_error_position"] = exc.pos
                continue

            attempt_trace["validated"] = True
            trace["successful_attempt"] = attempt
            log_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
            return result

        log_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        raise AgentRuntimeError(
            f"{self.config.name} failed to produce valid structured output after "
            f"{self.config.structured_attempts} attempt(s). See {log_path}. "
            f"Last validation error: {last_error}"
        ) from last_error


CodexAgent = APIAgent


def load_json_schema(name: str) -> Mapping[str, Any]:
    path = SCHEMA_ROOT / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))
