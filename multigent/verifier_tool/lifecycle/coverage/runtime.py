"""Observed-event coverage for command, job, reset-abort, and recovery lifecycle."""

from __future__ import annotations

import math
from typing import Any, Mapping


class LifecycleCoverageMonitor:
    """Classify lifecycle events without trusting stimulus labels."""

    def __init__(self, plan: Mapping[str, Any]) -> None:
        self.obligations = {
            str(item["id"]): dict(item)
            for item in plan.get("obligations", [])
            if item.get("template")
            in {"busy_behavior", "command_legality", "job_lifecycle", "reset_abort_phase", "post_reset_purity"}
        }
        self.operation_metadata = {
            str(item.get("operation_name", "")): dict(item)
            for item in plan.get("operation_metadata", {}).get("operations", [])
            if isinstance(item, Mapping)
        }
        self.state: dict[str, Any] = {}

    def reset(self) -> None:
        self.state.clear()

    @staticmethod
    def _read(snapshot: Mapping[str, Any], name: str) -> int:
        if name not in snapshot:
            raise ValueError(f"lifecycle coverage snapshot is missing {name!r}")
        return int(snapshot[name])

    def _transfer(self, snapshot: Mapping[str, Any], signals: Mapping[str, Any]) -> bool:
        return bool(self._read(snapshot, str(signals["valid"]))) and bool(
            self._read(snapshot, str(signals["ready"]))
        )

    @staticmethod
    def _expected_elements(binding: Mapping[str, Any], dimensions: Mapping[str, Any]) -> int:
        values = [dimensions.get(str(axis)) for axis in binding.get("dimensions", [])]
        return math.prod(map(int, values)) if values and all(isinstance(value, int) for value in values) else 1

    @classmethod
    def _expected_transfers(
        cls, binding: Mapping[str, Any], dimensions: Mapping[str, Any]
    ) -> int:
        elements = cls._expected_elements(binding, dimensions)
        mapping = binding.get("memory_mapping", {})
        per_word = mapping.get("elements_per_word") if isinstance(mapping, Mapping) else None
        return (
            (elements + int(per_word) - 1) // int(per_word)
            if isinstance(per_word, int) and per_word > 0
            else elements
        )

    def _obligation(self, template: str, operation_name: str | None = None) -> str | None:
        matches = [
            identity
            for identity, item in self.obligations.items()
            if item.get("template") == template
            and (
                operation_name is None
                or item.get("bindings", {}).get("operation_name") == operation_name
            )
        ]
        return matches[0] if len(matches) == 1 else None

    def _phase(self, operation: Mapping[str, Any], current: Mapping[str, Any]) -> str:
        counts = current.get("counts", {})
        dimensions = operation.get("dimensions", {})
        for binding in operation.get("inputs", []):
            object_name = str(binding.get("data_object", ""))
            if int(counts.get(object_name, 0)) < self._expected_transfers(binding, dimensions):
                return f"input_{str(binding.get('data_object', '')).lower()}"
        if any(
            int(counts.get(str(item.get("data_object", "")), 0))
            for item in operation.get("outputs", [])
        ):
            return "output"
        return "compute"

    def sample(
        self, snapshot: Mapping[str, Any], *, reset_active: bool
    ) -> list[tuple[str, str]]:
        hits: list[tuple[str, str]] = []
        if reset_active:
            for name, current in self.state.get("operations", {}).items():
                abort_id = self._obligation("reset_abort_phase", name)
                job_id = self._obligation("job_lifecycle", name)
                if abort_id:
                    hits.append((abort_id, self._phase(self.operation_metadata[name], current) if current.get("active") else "idle"))
                if job_id and current.get("active"):
                    hits.append((job_id, "aborted"))
                if current.get("active"):
                    current["awaiting_clean_recovery"] = True
                    current["ghost_output"] = False
                    current["ghost_completion"] = False
                    current["recovery_job_started"] = False
                current["active"] = False
                current["counts"] = {}
            return hits

        for obligation_id, obligation in self.obligations.items():
            if obligation.get("template") != "busy_behavior":
                continue
            signal = str(obligation.get("bindings", {}).get("signal", ""))
            value = bool(self._read(snapshot, signal))
            previous = self.state.setdefault("busy", {}).get(signal)
            hits.append((obligation_id, "active" if value else "idle"))
            if previous and not value:
                hits.append((obligation_id, "retired"))
            self.state["busy"][signal] = value

        operation_states = self.state.setdefault("operations", {})
        for name, operation in self.operation_metadata.items():
            current = operation_states.setdefault(
                name,
                {"active": False, "counts": {}, "awaiting_clean_recovery": False},
            )
            lifecycle = operation.get("lifecycle", {})
            job_id = self._obligation("job_lifecycle", name)
            for command in lifecycle.get("job_accept_channels", []):
                signals = command.get("signals", {})
                if not self._transfer(snapshot, signals):
                    continue
                payload = self._read(snapshot, str(signals["payload"]))
                legal = payload in set(map(int, command.get("legal_values", [])))
                for obligation_id, obligation in self.obligations.items():
                    if obligation.get("template") != "command_legality":
                        continue
                    bindings = obligation.get("bindings", {})
                    if bindings.get("valid") == signals.get("valid") and bindings.get("ready") == signals.get("ready"):
                        hits.append((obligation_id, "legal" if legal else "illegal"))
                if legal:
                    current["active"] = True
                    current["counts"] = {}
                    if current.get("awaiting_clean_recovery"):
                        current["recovery_job_started"] = True
                    if job_id:
                        hits.extend(((job_id, "accepted"), (job_id, "active")))
            seen_input_channels: set[str] = set()
            for binding in operation.get("inputs", []):
                channel = str(binding.get("channel", ""))
                if channel in seen_input_channels:
                    continue
                seen_input_channels.add(channel)
                signals = binding.get("signals", {})
                if not {"valid", "ready"} <= set(signals) or not self._transfer(snapshot, signals):
                    continue
                candidates = [
                    item
                    for item in operation.get("inputs", [])
                    if str(item.get("channel", "")) == channel
                    and int(current["counts"].get(str(item.get("data_object", "")), 0))
                    < self._expected_transfers(item, operation.get("dimensions", {}))
                ]
                if candidates:
                    object_name = str(candidates[0].get("data_object", ""))
                    current["counts"][object_name] = int(
                        current["counts"].get(object_name, 0)
                    ) + 1
            seen_output_channels: set[str] = set()
            for binding in operation.get("outputs", []):
                channel = str(binding.get("channel", ""))
                if channel in seen_output_channels:
                    continue
                seen_output_channels.add(channel)
                signals = binding.get("signals", {})
                if not {"valid", "ready"} <= set(signals) or not self._transfer(snapshot, signals):
                    continue
                object_name = str(binding.get("data_object", ""))
                current["counts"][object_name] = int(
                    current["counts"].get(object_name, 0)
                ) + 1
                if current.get("awaiting_clean_recovery") and not current.get("active"):
                    current["ghost_output"] = True
            completion_names = tuple(map(str, lifecycle.get("status_bindings", {}).get("completion", ())))
            if any(bool(self._read(snapshot, signal)) for signal in completion_names):
                if current.get("awaiting_clean_recovery") and not current.get("recovery_job_started"):
                    current["ghost_completion"] = True
                if current.get("active"):
                    current["active"] = False
                    if job_id:
                        hits.append((job_id, "retired"))
        return hits

    def record_checked_job(self, operation_name: str) -> list[tuple[str, str]]:
        current = self.state.get("operations", {}).get(str(operation_name))
        obligation_id = self._obligation("post_reset_purity", str(operation_name))
        if not current or not obligation_id or not current.get("awaiting_clean_recovery"):
            return []
        hits = [(obligation_id, "clean_recovery_job")]
        if not current.get("ghost_output"):
            hits.append((obligation_id, "no_ghost_output"))
        if not current.get("ghost_completion"):
            hits.append((obligation_id, "no_ghost_completion"))
        current["awaiting_clean_recovery"] = False
        current["recovery_job_started"] = False
        return hits


__all__ = ["LifecycleCoverageMonitor"]
