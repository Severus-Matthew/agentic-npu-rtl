"""Runtime functional coverage collected from DUT signal observations.

Generated cocotb tests use :func:`contract_coverage` as a decorator. The saved
TB owns the single clock observer and visible protocol assertions. This module
only turns its immutable snapshots into cocotb-coverage samples and reports.
"""

from __future__ import annotations

import atexit
import ast
import functools
import hashlib
import itertools
import json
import os
import re
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from cocotb_coverage.coverage import coverage_db

from multigent.verifier_tool.coverage.cocotb_model import ContractCocotbCoverageModel
from multigent.verifier_tool.coverage.operation.sampling import OperationSamplingError, OperationSamplingMonitor


_TRACKER_IDS = itertools.count()


class CoverageRuntimeError(AssertionError):
    """A monitored contract assertion failed or coverage setup is invalid."""


@dataclass(frozen=True)
class ContractSnapshot(Mapping[str, int]):
    """One immutable, same-event observation of the declared DUT interface."""

    data: Mapping[str, int]
    signal_widths: Mapping[str, int]

    def __getitem__(self, key: str) -> int:
        return self.data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    @property
    def widths(self) -> Mapping[str, int]:
        return self.signal_widths


def _integer(handle: Any, signal_name: str) -> int:
    try:
        value = handle.value
        if hasattr(value, "to_unsigned"):
            return int(value.to_unsigned())
        return int(value)
    except Exception as exc:
        raise CoverageRuntimeError(
            f"Cannot read a definite integer from signal {signal_name!r}: {exc}"
        ) from exc


def capture_contract_snapshot(
    dut: Any, signal_names: tuple[str, ...] | list[str]
) -> ContractSnapshot:
    """Read each declared top-level signal exactly once at the caller's event."""

    values: dict[str, int] = {}
    widths: dict[str, int] = {}
    for raw_name in signal_names:
        name = str(raw_name)
        if not hasattr(dut, name):
            raise CoverageRuntimeError(
                f"Contract snapshot references missing top-level signal {name!r}"
            )
        handle = getattr(dut, name)
        values[name] = _integer(handle, name)
        try:
            width = len(handle)
        except (TypeError, AttributeError):
            width = 0
        widths[name] = int(width) if isinstance(width, int) and width > 0 else 0
    return ContractSnapshot(
        data=MappingProxyType(values), signal_widths=MappingProxyType(widths)
    )


def _evidence_snapshot(snapshot: Mapping[str, int] | None) -> dict[str, Any]:
    """Keep exact small values and bounded-prompt-friendly wide values on disk."""

    if snapshot is None:
        return {}
    result: dict[str, Any] = {}
    for name, value in snapshot.items():
        integer = int(value)
        if integer.bit_length() <= 128:
            result[str(name)] = integer
        else:
            # The complete hexadecimal value remains in the run artifact. The
            # Debugger's string bounder can shorten it without losing its ends.
            result[str(name)] = f"0x{integer:x}"
    return result


def _signal_names_from_bindings(
    obligations: Any,
) -> tuple[str, ...]:
    """Derive only actual signal references for small plans without a monitor."""

    names: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str) and value:
            names.add(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                add(item)

    for obligation in obligations:
        bindings = obligation.get("bindings", {})
        if obligation.get("template") != "operation_coverpoint":
            for key in (
                "signal",
                "valid",
                "ready",
                "payload",
                "metadata",
                "last",
                "keep",
                "transaction_id",
                "address",
                "length",
                "size",
            ):
                add(bindings.get(key))
            continue
        sampling = bindings.get("sampling", {})
        for field in sampling.get("fields", {}).values():
            if isinstance(field, Mapping):
                add(field.get("signal"))
        for guard in sampling.get("guards", []):
            if isinstance(guard, Mapping) and isinstance(guard.get("field"), Mapping):
                add(guard["field"].get("signal"))
        channel = sampling.get("channel", {})
        if isinstance(channel, Mapping):
            add(channel.get("valid"))
            add(channel.get("ready"))
    return tuple(sorted(names))


def _related_signal_names(
    detail: str, snapshot: ContractSnapshot | None
) -> list[str]:
    match = re.search(r"related_signals=(\([^;]+\));", detail)
    if match:
        try:
            names = ast.literal_eval(match.group(1))
        except (SyntaxError, ValueError):
            names = ()
        if isinstance(names, tuple) and all(isinstance(name, str) for name in names):
            return list(names)
    return sorted(snapshot.keys()) if snapshot else []


class InterfaceCoverageTracker:
    """Evaluate machine-generated interface bins from sampled DUT signals."""

    def __init__(
        self,
        plan: Mapping[str, Any],
        report_path: Path | None = None,
        stimulus_ledger_path: Path | None = None,
    ) -> None:
        self.plan = dict(plan)
        self.report_path = report_path
        self.stimulus_ledger_path = stimulus_ledger_path
        self.obligations = {
            str(item["id"]): dict(item) for item in self.plan.get("obligations", [])
        }
        self.coverage_namespace = f"contract_runtime_{next(_TRACKER_IDS)}"
        # This is the direct equivalent of elaborating SystemVerilog covergroups:
        # the frozen plan creates concrete cocotb-coverage CoverPoint/CoverCross
        # objects before simulation starts.
        self.coverage_model = ContractCocotbCoverageModel(
            self.plan, self.coverage_namespace
        )
        try:
            self.operation_monitor = OperationSamplingMonitor(self.plan, self._signal, self._signal_width)
        except OperationSamplingError as exc:
            raise CoverageRuntimeError(str(exc)) from exc
        stall_pairs = {
            (
                str(item.get("bindings", {}).get("valid", "")),
                str(item.get("bindings", {}).get("ready", "")),
            )
            for item in self.plan.get("obligations", [])
            if item.get("template") == "stall_stability"
        }
        missing_stall_pairs = sorted(
            {
                (
                    str(point["bindings"]["sampling"]["channel"]["valid"]),
                    str(point["bindings"]["sampling"]["channel"]["ready"]),
                )
                for point in self.operation_monitor.points.values()
                if point["bindings"]["sampling"]["template"] == "channel_stall"
            }
            - stall_pairs
        )
        if missing_stall_pairs:
            raise CoverageRuntimeError(
                "channel_stall operation coverage requires the matching code-owned "
                f"stall_stability channel: {missing_stall_pairs}"
            )
        self.samples = 0
        self.operation_samples = 0
        self.directed_operation_samples = 0
        self.randomized_operation_samples = 0
        self.stimulus_records: list[dict[str, Any]] = []
        self.directed_stimuli = 0
        self.randomized_stimuli = 0
        self._stimulus_by_id: dict[str, dict[str, Any]] = {}
        self._stimulus_sequence = 0
        self._current_test = "unknown_test"
        self._bin_hits_at_last_stimulus: dict[str, int] = {}
        self.assertion_failures: list[str] = []
        self._previous_values: dict[str, int] = {}
        self._stall_observations: dict[str, list[int]] = {}
        self._completion_events: dict[str, int] = {}
        self._error_seen: set[str] = set()
        self.signal_names = tuple(map(str, self.plan.get("monitor", {}).get("signals", [])))
        if not self.signal_names:
            self.signal_names = _signal_names_from_bindings(self.obligations.values())
        self._recent_snapshots: deque[dict[str, Any]] = deque(maxlen=8)
        self._last_snapshot: ContractSnapshot | None = None
        self.failure_records: list[dict[str, Any]] = []
        self._closed = False

    def begin_test(self, test_name: str | None = None) -> None:
        """Reset monitor history that must never leak across cocotb tests.

        Coverage hits and operation counts intentionally remain process-wide.  Stall,
        edge, and recovery state describe one continuous test waveform, however, so
        carrying them into the next independently reset test creates false protocol
        failures.
        """

        self.operation_monitor.reset()
        self._previous_values.clear()
        self._error_seen.clear()
        self._recent_snapshots.clear()
        self._last_snapshot = None
        if test_name:
            self._current_test = str(test_name)

    def end_test(self) -> None:
        """Discard unfinished temporal observations at a test boundary."""

        self.operation_monitor.reset()
        self._previous_values.clear()
        self._error_seen.clear()

    def _hit(self, obligation_id: str, bin_name: str) -> None:
        self.coverage_model.sample_bin(obligation_id, bin_name)

    @staticmethod
    def _signal(snapshot: ContractSnapshot, name: str) -> int:
        if name not in snapshot:
            raise CoverageRuntimeError(
                f"Coverage plan references signal {name!r} absent from the TB snapshot"
            )
        return int(snapshot[name])

    @staticmethod
    def _signal_width(snapshot: ContractSnapshot, name: str, declared_width: Any = 0) -> int:
        """Resolve a signal width without interpreting SystemVerilog expressions.

        Contracts intentionally preserve parameterized widths such as
        ``$clog2(FIR_TAPS)``.  At simulation time the elaborated DUT handle is the
        authority for the concrete width; a literal contract width is only a
        fallback for lightweight unit-test handles that do not implement len().
        """

        if name not in snapshot:
            raise CoverageRuntimeError(
                f"Coverage plan references signal {name!r} absent from the TB snapshot"
            )
        width = int(snapshot.widths.get(name, 0))
        if isinstance(width, int) and width > 0:
            return width
        if isinstance(declared_width, int) and not isinstance(declared_width, bool):
            return max(0, declared_width)
        if isinstance(declared_width, str) and declared_width.strip().isdigit():
            return int(declared_width.strip())
        return 0

    def sample_snapshot(
        self,
        snapshot: ContractSnapshot,
        protocol_assertions: Callable[[Mapping[str, int]], Mapping[str, int]] | None,
    ) -> None:
        """Sample every obligation from one immutable TB-captured observation."""

        self.samples += 1
        self._last_snapshot = snapshot
        self._recent_snapshots.append(
            {"sample": self.samples, "signals": _evidence_snapshot(snapshot)}
        )
        if protocol_assertions is None and any(
            item.get("template") == "stall_stability"
            for item in self.obligations.values()
        ):
            raise CoverageRuntimeError(
                "TB did not provide its contract-generated protocol assertion function"
            )
        completed_stalls: Mapping[str, int] = {}
        if protocol_assertions is not None:
            try:
                completed_stalls = protocol_assertions(snapshot) or {}
            except AssertionError as exc:
                self._assertion_failure(
                    "tb.contract_generated_protocol", str(exc), snapshot=snapshot
                )
            if not isinstance(completed_stalls, Mapping):
                raise CoverageRuntimeError(
                    "TB protocol assertion callback must return completed stall lengths"
                )
        reset_active = self._reset_is_active(snapshot)
        if reset_active:
            # Ready/valid assertions are conventionally disabled during reset.
            # The frozen reset contract may abort an in-flight transaction, so a
            # source is allowed to withdraw valid and payload without completing
            # the pre-reset handshake.
            self.operation_monitor.reset()
        completed_by_channel = {
            (
                str(self.obligations[obligation_id]["bindings"]["valid"]),
                str(self.obligations[obligation_id]["bindings"]["ready"]),
            ): int(length)
            for obligation_id, length in completed_stalls.items()
            if obligation_id in self.obligations
            and self.obligations[obligation_id].get("template") == "stall_stability"
        }
        for obligation_id, obligation in self.obligations.items():
            template = str(obligation["template"])
            bindings = obligation.get("bindings", {})
            if reset_active and template in {"handshake_states", "stall_stability"}:
                continue
            if template == "handshake_states":
                valid = int(bool(self._signal(snapshot, str(bindings["valid"]))))
                ready = int(bool(self._signal(snapshot, str(bindings["ready"]))))
                self.coverage_model.sample_handshake(obligation_id, valid, ready)
            elif template == "stall_stability":
                if obligation_id in completed_stalls:
                    length = int(completed_stalls[obligation_id])
                    if length <= 0:
                        raise CoverageRuntimeError(
                            f"Invalid completed stall length for {obligation_id}: {length}"
                        )
                    self._stall_observations.setdefault(obligation_id, []).append(length)
                    self.coverage_model.sample_stall_length(obligation_id, length)
            elif template == "reset_behavior":
                self._sample_reset(snapshot, obligation_id, bindings)
            elif template == "completion_behavior":
                self._sample_completion(snapshot, obligation_id, bindings)
            elif template == "error_behavior":
                self._sample_error(snapshot, obligation_id, bindings)
            elif template == "address_alignment":
                self._sample_address(snapshot, obligation_id, bindings)
            elif template == "axi4_4k_boundary":
                self._sample_axi_boundary(snapshot, obligation_id, bindings)
        try:
            self.operation_monitor.sample(
                snapshot,
                self.coverage_model.sample_operation,
                reset_active=reset_active,
                completed_stalls=completed_by_channel,
            )
        except OperationSamplingError as exc:
            self._assertion_failure("runtime.operation_sampling", str(exc), snapshot=snapshot)

    def observe_reset_snapshot(
        self,
        snapshot: ContractSnapshot,
        protocol_assertions: Callable[[Mapping[str, int]], Mapping[str, int]] | None,
    ) -> None:
        """Do not miss a legal synchronous reset pulse between half-cycle samples.

        Only reset input is read here, not post-edge output data. Ordinary stall
        checking stays in the generated TB's pre-active-edge sampling coroutine.
        """
        if not self._reset_is_active(snapshot):
            return
        if protocol_assertions is not None:
            try:
                protocol_assertions(snapshot)
            except AssertionError as exc:
                self._assertion_failure(
                    "tb.contract_generated_protocol", str(exc), snapshot=snapshot
                )
        self.operation_monitor.reset()
        for obligation_id, obligation in self.obligations.items():
            if obligation.get("template") == "reset_behavior":
                self._sample_reset(snapshot, obligation_id, obligation["bindings"])

    def _reset_is_active(self, snapshot: ContractSnapshot) -> bool:
        for obligation in self.obligations.values():
            if obligation.get("template") != "reset_behavior":
                continue
            bindings = obligation.get("bindings", {})
            active_value = bindings.get("active_value")
            if active_value not in {0, 1}:
                continue
            signal = str(bindings.get("signal", ""))
            return int(bool(self._signal(snapshot, signal))) == int(active_value)
        return False

    def sample_operation(
        self,
        operation_name: str,
        fields: Mapping[str, Any],
        stimulus_kind: str,
        stimulus_id: str | None = None,
    ) -> None:
        """Associate a checked job with its ledger. Supplied fields never hit bins."""

        if stimulus_kind not in {"directed", "randomized"}:
            raise CoverageRuntimeError(
                "sample_operation stimulus_kind must be directed or randomized"
            )
        stimulus_record: dict[str, Any] | None = None
        if stimulus_id is not None:
            stimulus_record = self._stimulus_by_id.get(str(stimulus_id))
            if stimulus_record is None:
                raise CoverageRuntimeError(
                    f"sample_operation references unknown stimulus_id {stimulus_id!r}"
                )
            if stimulus_record["kind"] != stimulus_kind:
                raise CoverageRuntimeError(
                    "sample_operation stimulus_kind must match its recorded stimulus"
                )

        matched = any(point["bindings"]["operation_name"] == operation_name
                      for point in self.operation_monitor.points.values())
        matched_bins: list[str] = []
        if not matched:
            raise CoverageRuntimeError(
                f"No operation coverage is registered for {operation_name!r}"
            )
        self.operation_samples += 1
        if stimulus_kind == "randomized":
            self.randomized_operation_samples += 1
        else:
            self.directed_operation_samples += 1
        if stimulus_record is not None:
            stimulus_record["operation_samples"].append(
                {
                    "operation_name": operation_name,
                    "fields": {},
                    "ignored_runtime_fields": sorted(fields),
                    "matched_bins": sorted(set(matched_bins)),
                    "runtime_sampled_points": sorted(
                        identity for identity, point in self.operation_monitor.points.items()
                        if point["bindings"]["operation_name"] == operation_name
                    ),
                }
            )
            stimulus_record["covered_bins"] = sorted(
                set(stimulus_record["covered_bins"]) | set(matched_bins)
            )
            self._bin_hits_at_last_stimulus = self._bin_hit_counts()
            self.write_stimulus_ledger()

    def record_stimulus(
        self,
        stimulus_kind: str,
        stimulus: Mapping[str, Any],
        expected: Mapping[str, Any],
        label: str | None = None,
    ) -> str:
        """Persist one real DUT job after its independent oracle check succeeds.

        Generated tests call this after the DUT output has matched ``expected``.
        Operation samples for a composed job then reference the returned ID.
        """

        if stimulus_kind not in {"directed", "randomized"}:
            raise CoverageRuntimeError(
                "record_stimulus stimulus_kind must be directed or randomized"
            )
        if not isinstance(stimulus, Mapping) or not isinstance(expected, Mapping):
            raise CoverageRuntimeError(
                "record_stimulus stimulus and expected must be mappings"
            )
        stimulus_value = _json_value(stimulus, "stimulus")
        expected_value = _json_value(expected, "expected")
        self._stimulus_sequence += 1
        safe_test_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", self._current_test)
        stimulus_id = f"{safe_test_name}:{self._stimulus_sequence:06d}"
        current_hits = self._bin_hit_counts()
        newly_covered = sorted(
            bin_id
            for bin_id, count in current_hits.items()
            if count > 0 and self._bin_hits_at_last_stimulus.get(bin_id, 0) == 0
        )
        digest_source = {
            "kind": stimulus_kind,
            "stimulus": stimulus_value,
            "expected": expected_value,
        }
        record = {
            "id": stimulus_id,
            "digest": hashlib.sha256(
                json.dumps(
                    digest_source, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest(),
            "test": self._current_test,
            "kind": stimulus_kind,
            "label": None if label is None else str(label),
            "stimulus": stimulus_value,
            "expected": expected_value,
            "covered_bins": newly_covered,
            "operation_samples": [],
        }
        self.stimulus_records.append(record)
        self._stimulus_by_id[stimulus_id] = record
        self._bin_hits_at_last_stimulus = current_hits
        if stimulus_kind == "randomized":
            self.randomized_stimuli += 1
        else:
            self.directed_stimuli += 1
        # Flush every checked job so a later simulation timeout does not erase
        # already completed stimulus evidence.
        self.write_stimulus_ledger()
        return stimulus_id

    def _bin_hit_counts(self) -> dict[str, int]:
        hits: dict[str, int] = {}
        for obligation_id, obligation in self.obligations.items():
            detailed = self.coverage_model.detailed_coverage(obligation_id)
            for spec in obligation["bins"]:
                name = str(spec["name"])
                hits[f"{obligation_id}.{name}"] = int(detailed.get(name, 0))
        return hits

    def _sample_reset(
        self, dut: Any, obligation_id: str, bindings: Mapping[str, Any]
    ) -> None:
        signal = str(bindings["signal"])
        value = int(bool(self._signal(dut, signal)))
        active_value = bindings.get("active_value")
        if active_value not in {0, 1}:
            raise CoverageRuntimeError(
                f"Reset {signal!r} needs explicit active-high/active-low semantics"
            )
        self._hit(
            obligation_id, "asserted" if value == int(active_value) else "deasserted"
        )
        if signal in self._previous_values:
            previous = self._previous_values[signal]
            if previous == int(active_value) and value != int(active_value):
                self._hit(obligation_id, "release")
        self._previous_values[signal] = value

    def _sample_completion(
        self, dut: Any, obligation_id: str, bindings: Mapping[str, Any]
    ) -> None:
        signal = str(bindings["signal"])
        value = int(bool(self._signal(dut, signal)))
        previous = self._previous_values.get(signal, 0)
        if value and not previous:
            count = self._completion_events.get(obligation_id, 0) + 1
            self._completion_events[obligation_id] = count
            self._hit(obligation_id, "observed")
            if count >= 2:
                self._hit(obligation_id, "back_to_back")
        self._previous_values[signal] = value

    def _sample_error(
        self, dut: Any, obligation_id: str, bindings: Mapping[str, Any]
    ) -> None:
        signal = str(bindings["signal"])
        value = int(bool(self._signal(dut, signal)))
        if value:
            self._error_seen.add(obligation_id)
            self._hit(obligation_id, "asserted")
        else:
            self._hit(obligation_id, "inactive")
            if obligation_id in self._error_seen:
                self._hit(obligation_id, "recovered")

    def _sample_address(
        self, dut: Any, obligation_id: str, bindings: Mapping[str, Any]
    ) -> None:
        signal = str(bindings["signal"])
        value = self._signal(dut, signal)
        width = self._signal_width(dut, signal, bindings.get("width", 0))
        if value == 0:
            self._hit(obligation_id, "minimum")
        if value > 0 and value % 4 == 0:
            self._hit(obligation_id, "aligned_interior")
        if width > 0 and value == (1 << width) - 1:
            self._hit(obligation_id, "maximum")
        if (value & 0xFFF) in {0, 1, 0xFFE, 0xFFF}:
            self._hit(obligation_id, "boundary_neighbor")

    def _sample_axi_boundary(
        self, dut: Any, obligation_id: str, bindings: Mapping[str, Any]
    ) -> None:
        address = self._signal(dut, str(bindings["address"][0]))
        length = self._signal(dut, str(bindings["length"][0]))
        size = self._signal(dut, str(bindings["size"][0]))
        end = address + ((length + 1) << size) - 1
        end_offset = end & 0xFFF
        if (address >> 12) != (end >> 12):
            self._hit(obligation_id, "would_cross_boundary")
        elif end_offset == 0xFFF:
            self._hit(obligation_id, "ends_at_boundary")
        else:
            self._hit(obligation_id, "ends_before_boundary")

    def _assertion_failure(
        self,
        obligation_id: str,
        detail: str,
        *,
        snapshot: ContractSnapshot | None = None,
    ) -> None:
        message = f"{obligation_id}: {detail}"
        self.assertion_failures.append(message)
        self.failure_records.append(
            {
                "test": self._current_test,
                "check": obligation_id,
                "detail": detail,
                "related_signal_names": _related_signal_names(detail, snapshot),
                "current_snapshot": _evidence_snapshot(snapshot) if snapshot else {},
                "recent_snapshots": list(self._recent_snapshots),
            }
        )
        self.write_report()
        raise CoverageRuntimeError(message)

    def report(self) -> dict[str, Any]:
        obligations: list[dict[str, Any]] = []
        missing: list[str] = []
        covered: list[str] = []
        bin_hits: dict[str, int] = {}
        hit_bins = 0
        total_bins = 0
        for obligation_id, obligation in self.obligations.items():
            bin_rows = []
            detailed = self.coverage_model.detailed_coverage(obligation_id)
            for spec in obligation["bins"]:
                name = str(spec["name"])
                required = bool(spec.get("required", True))
                count = int(detailed.get(name, 0))
                bin_id = f"{obligation_id}.{name}"
                bin_hits[bin_id] = count
                if count > 0:
                    covered.append(bin_id)
                total_bins += int(required)
                hit_bins += int(required and count > 0)
                if required and count == 0:
                    missing.append(f"{obligation_id}.{name}")
                bin_rows.append({"name": name, "required": required, "hits": count})
            obligations.append({"id": obligation_id, "bins": bin_rows})
        minimum_randomized = int(
            self.plan.get("requirements", {}).get(
                "randomized_transactions_minimum", 0
            )
        )
        randomized_transactions = (
            self.randomized_stimuli
            if self.stimulus_ledger_path is not None
            else self.randomized_operation_samples
        )
        if randomized_transactions < minimum_randomized:
            missing.append(
                f"runtime.randomized_transactions.minimum_{minimum_randomized}"
            )
        return {
            "schema_version": 1,
            "coverage_engine": "cocotb-coverage",
            "coverage_namespace": self.coverage_namespace,
            "coverage_model": self.coverage_model.manifest(),
            "operation_sampling": self.operation_monitor.report(),
            "status": "PASS" if not missing and not self.assertion_failures else "FAIL",
            "samples": self.samples,
            "operation_samples": self.operation_samples,
            "directed_operation_samples": self.directed_operation_samples,
            "randomized_operation_samples": self.randomized_operation_samples,
            "stimulus_count": len(self.stimulus_records),
            "directed_stimuli": self.directed_stimuli,
            "randomized_stimuli": self.randomized_stimuli,
            "randomized_transactions_observed": randomized_transactions,
            "stimulus_ledger_enabled": self.stimulus_ledger_path is not None,
            "randomized_transactions_minimum": minimum_randomized,
            "required_bins": total_bins,
            "hit_bins": hit_bins,
            "coverage_percent": 100.0 if not total_bins else 100.0 * hit_bins / total_bins,
            "missing_bins": missing,
            "covered_bins": sorted(covered),
            "bin_hits": dict(sorted(bin_hits.items())),
            "assertion_failures": list(self.assertion_failures),
            "failure_records": list(self.failure_records),
            "last_observed_snapshot": (
                _evidence_snapshot(self._last_snapshot)
                if self._last_snapshot is not None
                else {}
            ),
            "stall_lengths_observed": {
                obligation_id: list(lengths)
                for obligation_id, lengths in sorted(
                    self._stall_observations.items()
                )
            },
            "obligations": obligations,
        }

    def write_report(self) -> None:
        if self.report_path is None:
            return
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(self.report(), indent=2) + "\n", encoding="utf-8"
        )
        coverage_db.export_to_yaml(
            filename=str(self.report_path.with_suffix(".cocotb-coverage.yml"))
        )

    def write_stimulus_ledger(self) -> None:
        if self.stimulus_ledger_path is None:
            return
        self.stimulus_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.stimulus_ledger_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "stimulus_count": len(self.stimulus_records),
                    "directed_stimuli": self.directed_stimuli,
                    "randomized_stimuli": self.randomized_stimuli,
                    "records": self.stimulus_records,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.write_report()
        self.write_stimulus_ledger()


_TRACKER: InterfaceCoverageTracker | None = None


def _json_value(value: Any, description: str) -> Any:
    """Return a detached JSON value or fail before producing a partial ledger."""

    if isinstance(value, Mapping):
        normalized = {str(key): _json_value(item, description) for key, item in value.items()}
    elif isinstance(value, (list, tuple)):
        normalized = [_json_value(item, description) for item in value]
    elif value is None or isinstance(value, (str, int, float, bool)):
        normalized = value
    elif hasattr(value, "tolist"):
        normalized = _json_value(value.tolist(), description)
    elif hasattr(value, "item"):
        normalized = _json_value(value.item(), description)
    else:
        raise CoverageRuntimeError(
            f"record_stimulus {description} contains non-JSON value {type(value).__name__}"
        )
    try:
        json.dumps(normalized, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CoverageRuntimeError(
            f"record_stimulus {description} is not finite JSON data: {exc}"
        ) from exc
    return normalized


def normalize_verification_value(value: Any, description: str) -> Any:
    """Return the same finite JSON form used by the stimulus evidence ledger."""

    return _json_value(value, str(description))


def get_coverage_tracker() -> InterfaceCoverageTracker:
    """Load runner-owned configuration and return the process-wide tracker."""

    global _TRACKER
    if _TRACKER is not None:
        return _TRACKER
    config_raw = os.environ.get("NPU_FUNCTIONAL_COVERAGE_CONFIG", "").strip()
    report_raw = os.environ.get("NPU_FUNCTIONAL_COVERAGE_REPORT", "").strip()
    ledger_raw = os.environ.get("NPU_STIMULUS_LEDGER_REPORT", "").strip()
    if not config_raw or not report_raw:
        raise CoverageRuntimeError(
            "Functional coverage environment was not supplied by the runner"
        )
    plan = json.loads(Path(config_raw).read_text(encoding="utf-8"))
    _TRACKER = InterfaceCoverageTracker(
        plan,
        Path(report_raw),
        Path(ledger_raw) if ledger_raw else None,
    )
    atexit.register(_TRACKER.close)
    return _TRACKER


def sample_contract_snapshot(
    snapshot: ContractSnapshot,
    protocol_assertions: Callable[[Mapping[str, int]], Mapping[str, int]],
) -> None:
    """Apply visible TB assertions and functional coverage to one observation."""

    if not isinstance(snapshot, ContractSnapshot):
        raise CoverageRuntimeError("sample_contract_snapshot requires ContractSnapshot")
    if not callable(protocol_assertions):
        raise CoverageRuntimeError("TB protocol assertion callback is missing")
    get_coverage_tracker().sample_snapshot(snapshot, protocol_assertions)


def observe_contract_reset_snapshot(
    snapshot: ContractSnapshot,
    protocol_assertions: Callable[[Mapping[str, int]], Mapping[str, int]],
) -> None:
    """Preserve a short synchronous reset seen at the active edge."""

    if not isinstance(snapshot, ContractSnapshot):
        raise CoverageRuntimeError(
            "observe_contract_reset_snapshot requires ContractSnapshot"
        )
    get_coverage_tracker().observe_reset_snapshot(snapshot, protocol_assertions)


def sample_operation(
    operation_name: str,
    fields: Mapping[str, Any],
    stimulus_kind: str,
    stimulus_id: str | None = None,
) -> None:
    """Associate a checked operation with a stimulus record; fields never hit coverage.

    The name/signature are retained for source compatibility. New TBs pass {}.
    All coverage values come from reusable or custom DUT observers.
    """

    if not isinstance(fields, Mapping):
        raise CoverageRuntimeError("sample_operation fields must be a mapping")
    get_coverage_tracker().sample_operation(
        str(operation_name), fields, str(stimulus_kind), stimulus_id
    )


def record_stimulus(
    stimulus_kind: str,
    stimulus: Mapping[str, Any],
    expected: Mapping[str, Any],
    label: str | None = None,
) -> str:
    """Record a checked DUT stimulus and return its operation-coverage link ID."""

    return get_coverage_tracker().record_stimulus(
        str(stimulus_kind), stimulus, expected, label
    )


def contract_coverage():
    """Run the code-owned monitor visibly embedded in the generated TB."""

    def decorate(test_function):
        @functools.wraps(test_function)
        async def monitored(dut, *args, **kwargs):
            import cocotb

            tracker = get_coverage_tracker()
            tracker.begin_test(test_function.__name__)
            try:
                tracker.operation_monitor.bind_observers(test_function.__globals__)
            except OperationSamplingError as exc:
                raise CoverageRuntimeError(str(exc)) from exc
            monitor_function = test_function.__globals__.get(
                "_contract_generated_monitor"
            )
            if not callable(monitor_function):
                raise CoverageRuntimeError(
                    "Generated TB is missing _contract_generated_monitor"
                )
            declared_names = test_function.__globals__.get("CONTRACT_SIGNAL_NAMES")
            if tuple(declared_names or ()) != tracker.signal_names:
                raise CoverageRuntimeError(
                    "TB CONTRACT_SIGNAL_NAMES differs from the runner-owned contract plan"
                )
            protocol_state = test_function.__globals__.get("_CONTRACT_PROTOCOL_STATE")
            if not isinstance(protocol_state, dict):
                raise CoverageRuntimeError(
                    "Generated TB is missing _CONTRACT_PROTOCOL_STATE"
                )
            protocol_state.clear()
            monitor_task = cocotb.start_soon(monitor_function(dut))
            try:
                return await test_function(dut, *args, **kwargs)
            finally:
                monitor_task.cancel()
                protocol_state.clear()
                tracker.end_test()
                tracker.write_report()

        return monitored

    return decorate
