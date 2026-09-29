"""Executable assertion checkers for reset, jobs, busy, completion, and error."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def _read(snapshot: Mapping[str, Any], name: str) -> int:
    if name not in snapshot:
        raise AssertionError(f"lifecycle snapshot is missing bound signal {name!r}")
    return int(snapshot[name])


def _transfer(snapshot: Mapping[str, Any], signals: Mapping[str, Any]) -> bool:
    return bool(_read(snapshot, str(signals["valid"]))) and bool(
        _read(snapshot, str(signals["ready"]))
    )


def _status_signal(status: Mapping[str, Any], role: str) -> str:
    names = tuple(map(str, status.get(role, ())))
    return names[0] if len(names) == 1 else ""


def _fail(feature: str, detail: str) -> None:
    raise AssertionError(f"feature={feature}; {detail}")


def is_lifecycle_reset_active(
    snapshot: Mapping[str, Any], reset: Mapping[str, Any]
) -> bool:
    """Return whether the bound lifecycle reset is active in this snapshot."""

    reset_name = str(reset.get("signal", ""))
    active_value = reset.get("active_value")
    return bool(
        reset_name
        and active_value in {0, 1}
        and int(bool(_read(snapshot, reset_name))) == int(active_value)
    )


def check_reset_outputs(
    snapshot: Mapping[str, Any], reset_outputs: Mapping[str, Any]
) -> None:
    """Check the contract-declared output values while reset is active."""

    for signal, expected in reset_outputs.items():
        if signal not in snapshot:
            continue
        observed = _read(snapshot, str(signal))
        if observed != int(expected):
            _fail(
                "lifecycle.reset.outputs_match_declared_reset_values",
                f"signal={signal} expected={expected} observed={observed}",
            )


def check_lifecycle_operations(
    snapshot: Mapping[str, Any],
    operations: list[Mapping[str, Any]],
    state: MutableMapping[str, Any],
    enabled_by_operation: Mapping[str, set[str]] | None = None,
    job_start_by_operation: Mapping[str, bool] | None = None,
    job_complete_by_operation: Mapping[str, bool] | None = None,
) -> None:
    """Check command, job, status, completion, and error assertions.

    `job_start_by_operation`/`job_complete_by_operation` carry this cycle's
    already-abstracted JOB_START/JOB_COMPLETE events for operations whose
    `job_acceptance`/`completion_style` is `control_plane_sequence` (see
    `control_plane_sequence_tracker.py`) -- everything below (busy tracking,
    completion-timing, reset-abort) only ever consumes the resulting
    `current["active"]` state, never how it was produced, exactly like it
    already never cared whether `_transfer()` came from a real ready/valid
    command or a smoke-driven one.
    """

    for operation in operations:
        name = str(operation["operation_name"])
        root = f"lifecycle.{name}"
        enabled_checkers = (
            set(enabled_by_operation.get(name, set()))
            if enabled_by_operation is not None
            else {
                "busy_tracks_active_job",
                "completion_matches_final_output",
                "illegal_command_errors_without_start",
                "response_error_follows_nonokay",
                "accepted_command_starts_job",
                "single_inflight_job_enforced",
                "no_output_without_active_job",
                "reset_aborts_pending_job",
                "status_pulses_are_one_cycle",
            }
        )
        # Preserve execution of already-generated TBs while giving the legacy
        # feature its precise implemented meaning: overlap rejection.
        if "legal_command_starts_one_job" in enabled_checkers:
            enabled_checkers.discard("legal_command_starts_one_job")
            enabled_checkers.add("single_inflight_job_enforced")

        def enabled(checker: str) -> bool:
            return checker in enabled_checkers

        current = state.setdefault("operations", {}).setdefault(name, {})
        for key, default in {
                "active": False,
                "completion_due": False,
                "previous_completion": 0,
                "previous_error": 0,
                "error_due": False,
                "error_due_sources": set(),
                "error_seen": False,
                "last_error_source": "",
                "start_pending": False,
                "retirement_count": 0,
                "outstanding_write_requests": 0,
                "final_output_retired": False,
                "reset_aborted_pending": name
                in set(state.get("_reset_aborted_operations", ())),
                "enabled_checkers": tuple(sorted(enabled_checkers)),
        }.items():
            current.setdefault(key, default)
        # The control-bus transaction tracker initializes this same state
        # entry before the generic lifecycle checker sees it.
        status = operation.get("status", {})
        busy_name = _status_signal(status, "busy")
        completion_name = _status_signal(status, "completion")
        error_name = _status_signal(status, "error")
        completion = _read(snapshot, completion_name) if completion_name else 0
        error = _read(snapshot, error_name) if error_name else 0
        raw_error_style = operation["policy"]["error_style"]
        error_style = raw_error_style if isinstance(raw_error_style, str) else "verifier_extension"
        raw_completion_style = operation["policy"]["completion_style"]
        completion_style = (
            raw_completion_style
            if isinstance(raw_completion_style, str)
            else "verifier_extension"
        )
        active_before = bool(current["active"])
        if (
            enabled("status_pulses_are_one_cycle")
            and completion_style == "pulse"
            and completion
            and current["previous_completion"]
        ):
            _fail(f"{root}.status_pulses_are_one_cycle", "completion remained high for multiple samples")
        if enabled("status_pulses_are_one_cycle") and error_style == "pulse" and error and current["previous_error"]:
            _fail(f"{root}.status_pulses_are_one_cycle", "error remained high for multiple samples")
        if enabled("completion_matches_final_output") and current["completion_due"] and not completion:
            _fail(
                f"{root}.completion_matches_final_output",
                "final output was not followed by completion"
                f" (retirement_count={current['retirement_count']}, "
                f"outstanding_write_requests={current['outstanding_write_requests']})",
            )
        if enabled("completion_matches_final_output") and completion and not current["completion_due"]:
            _fail(f"{root}.completion_matches_final_output", "completion occurred without a preceding final output transfer")
        current["completion_due"] = False
        due_sources = set(current.get("error_due_sources", ()))
        if current["error_due"] and not error:
            if "response" in due_sources and enabled("response_error_follows_nonokay"):
                _fail(f"{root}.response_error_follows_nonokay", "non-OKAY response was not followed by error")
            if "illegal" in due_sources and enabled("illegal_command_errors_without_start"):
                _fail(f"{root}.illegal_command_errors_without_start", "illegal command was not followed by error")
        if (enabled("illegal_command_errors_without_start") or enabled("response_error_follows_nonokay")) and error and not due_sources and not (
            error_style == "sticky_until_reset" and current.get("error_seen")
        ):
            feature = (
                "illegal_command_errors_without_start"
                if enabled("illegal_command_errors_without_start")
                else "response_error_follows_nonokay"
            )
            _fail(f"{root}.{feature}", "error occurred without an accepted illegal command or non-OKAY response")
        if (
            (enabled("illegal_command_errors_without_start") or enabled("response_error_follows_nonokay"))
            and
            error_style == "sticky_until_reset"
            and current.get("error_seen")
            and not error
        ):
            feature = (
                "response_error_follows_nonokay"
                if current.get("last_error_source") == "response"
                else "illegal_command_errors_without_start"
            )
            _fail(
                f"{root}.{feature}",
                "sticky error deasserted without reset",
            )
        if error:
            current["error_seen"] = True
            if due_sources:
                current["last_error_source"] = (
                    "response" if "response" in due_sources else "illegal"
                )
        current["error_due"] = False
        current["error_due_sources"] = set()

        accepted_legal = False
        job_start_fired = bool((job_start_by_operation or {}).get(name, False))
        job_complete_fired = bool((job_complete_by_operation or {}).get(name, False))
        command_tracking_enabled = bool(enabled_checkers & {
            "accepted_command_starts_job",
            "single_inflight_job_enforced",
            "illegal_command_errors_without_start",
            "no_output_without_active_job",
            "busy_tracks_active_job",
            "reset_aborts_pending_job",
        })
        for command in operation.get("commands", []) if command_tracking_enabled else ():
            signals = command.get("signals", {})
            if not _transfer(snapshot, signals):
                continue
            value = _read(snapshot, str(signals["payload"]))
            legal = set(map(int, command.get("legal_values", [])))
            if not legal and (
                enabled("accepted_command_starts_job")
                or enabled("single_inflight_job_enforced")
            ):
                _fail(
                    f"{root}.accepted_command_starts_job",
                    "command legal values are unresolved",
                )
            if value in legal:
                invalid_addresses = [
                    item
                    for item in command.get("metadata_fields", [])
                    if item.get("address_role") == "base"
                    and isinstance(item.get("word_stride_bytes"), int)
                    and _read(snapshot, str(item.get("signal", "")))
                    % int(item["word_stride_bytes"])
                ]
                if invalid_addresses:
                    current["error_due"] |= bool(error_name) and enabled("illegal_command_errors_without_start")
                    current["error_due_sources"].add("illegal")
                    current["active"] = False
                elif active_before and enabled("single_inflight_job_enforced"):
                    _fail(
                        f"{root}.single_inflight_job_enforced",
                        "a second legal command was accepted while a job was active",
                    )
                else:
                    accepted_legal = True
            else:
                if active_before and enabled("illegal_command_errors_without_start"):
                    _fail(f"{root}.illegal_command_errors_without_start", "illegal command was accepted while a job was active")
                current["error_due"] |= bool(error_name) and enabled("illegal_command_errors_without_start")
                current["error_due_sources"].add("illegal")

        any_input = False
        for operation_input in operation.get("inputs", []):
            signals = operation_input.get("signals", {})
            if {"valid", "ready"} <= set(signals):
                any_input |= _transfer(snapshot, signals)

        any_output = False
        for output in operation.get("outputs", []):
            signals = output.get("signals", {})
            if not {"valid", "ready"} <= set(signals):
                continue
            transfer = _transfer(snapshot, signals)
            any_output |= transfer
        retirement_activity = False
        for retirement in operation.get("retirements", []):
            count_mode = retirement.get("count_mode")
            if count_mode not in {
                "accepted_data_beats_after_all_write_responses",
                "accepted_data_bytes_after_all_write_responses",
            }:
                continue
            if _transfer(snapshot, retirement.get("request_signals", {})):
                retirement_activity = True
                current["outstanding_write_requests"] = int(
                    current.get("outstanding_write_requests", 0)
                ) + 1
            if _transfer(snapshot, retirement.get("data_signals", {})):
                retirement_activity = True
                increment = 1
                if count_mode == "accepted_data_bytes_after_all_write_responses":
                    strobe_name = str(retirement.get("data_signals", {}).get("strobe", ""))
                    increment = _read(snapshot, strobe_name).bit_count()
                current["retirement_count"] = int(current["retirement_count"]) + increment
                expected_count = retirement.get("expected_count")
                if isinstance(expected_count, int) and current["retirement_count"] > expected_count:
                    if enabled("completion_matches_final_output"):
                        _fail(
                            f"{root}.completion_matches_final_output",
                            f"retirement count exceeded {expected_count}",
                        )
        final_transfer = False
        for retirement in operation.get("retirements", []):
            signals = retirement.get("signals", {})
            if not {"valid", "ready"} <= set(signals) or not all(
                str(signals.get(role, "")) for role in ("valid", "ready")
            ):
                continue
            if not _transfer(snapshot, signals):
                continue
            if retirement.get("count_mode") in {
                "accepted_data_beats_after_all_write_responses",
                "accepted_data_bytes_after_all_write_responses",
            }:
                current["outstanding_write_requests"] = max(
                    0, int(current.get("outstanding_write_requests", 0)) - 1
                )
                expected_count = retirement.get("expected_count")
                response_signal = str(retirement.get("response_signal", ""))
                if response_signal and _read(snapshot, response_signal) != 0:
                    continue
                final_transfer |= (
                    isinstance(expected_count, int)
                    and current["retirement_count"] == expected_count
                    and current["outstanding_write_requests"] == 0
                )
                continue
            current["retirement_count"] = int(current.get("retirement_count", 0)) + 1
            expected_count = retirement.get("expected_count")
            if isinstance(expected_count, int) and current["retirement_count"] > expected_count:
                if enabled("completion_matches_final_output"):
                    _fail(
                        f"{root}.completion_matches_final_output",
                        f"retirement count exceeded {expected_count}",
                    )
            if "last" in signals:
                last = bool(_read(snapshot, str(signals["last"])))
                if last and isinstance(expected_count, int) and current["retirement_count"] != expected_count:
                    if enabled("completion_matches_final_output"):
                        _fail(
                            f"{root}.completion_matches_final_output",
                            f"LAST retired element {current['retirement_count']} of {expected_count}",
                        )
                final_transfer |= last
            elif isinstance(expected_count, int):
                final_transfer |= current["retirement_count"] == expected_count
        if (
            enabled("reset_aborts_pending_job")
            and current.get("reset_aborted_pending")
            and (any_output or final_transfer or completion or job_complete_fired)
        ):
            _fail(
                f"{root}.reset_aborts_pending_job",
                "work aborted by reset produced output or completion before a new legal job",
            )
        if enabled("no_output_without_active_job") and any_output and not active_before:
            _fail(f"{root}.no_output_without_active_job", "accepted output has no active legal job")
        busy = bool(_read(snapshot, busy_name)) if busy_name else False
        if busy_name and enabled("busy_tracks_active_job"):
            if active_before and not busy:
                _fail(f"{root}.busy_tracks_active_job", "busy is low while a legal job is active")
            if not active_before and busy:
                _fail(f"{root}.busy_tracks_active_job", "busy is high without an active legal job")
        if accepted_legal or job_start_fired:
            current["retirement_count"] = 0
            current["outstanding_write_requests"] = 0
            current["final_output_retired"] = False
            current["reset_aborted_pending"] = False
            remaining = set(state.get("_reset_aborted_operations", ()))
            remaining.discard(name)
            if remaining:
                state["_reset_aborted_operations"] = tuple(sorted(remaining))
            else:
                state.pop("_reset_aborted_operations", None)
        if accepted_legal and enabled("accepted_command_starts_job"):
            current["start_pending"] = True
        current["active"] = active_before or accepted_legal or job_start_fired
        for response in operation.get("error_responses", []):
            if not _transfer(snapshot, response):
                continue
            if _read(snapshot, str(response["resp"])) != 0:
                current["error_due"] |= bool(error_name) and enabled("response_error_follows_nonokay")
                current["error_due_sources"].add("response")
                current["active"] = False
        if final_transfer:
            current["final_output_retired"] = True
        uses_control_plane = isinstance(operation.get("control_plane_sequence"), Mapping)
        if (
            job_complete_fired
            and uses_control_plane
            and operation.get("retirements")
            and enabled("completion_matches_final_output")
            and not current["final_output_retired"]
        ):
            _fail(
                f"{root}.completion_matches_final_output",
                "control-plane completion was observed before final output retirement"
                f" (retirement_count={current['retirement_count']}, "
                f"outstanding_write_requests={current['outstanding_write_requests']})",
            )
        if (final_transfer and not uses_control_plane) or job_complete_fired:
            current["active"] = False
            current["completion_due"] = bool(completion_name) and enabled("completion_matches_final_output")
        if current.get("start_pending") and (
            busy
            or any_input
            or any_output
            or retirement_activity
            or final_transfer
            or completion
            or job_complete_fired
        ):
            current["start_pending"] = False
        current["previous_completion"] = int(bool(completion))
        current["previous_error"] = int(bool(error))


def finalize_lifecycle_checker_state(
    plan: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    pending = []
    for name, current in state.get("operations", {}).items():
        enabled = set(current.get("enabled_checkers", ()))
        if current.get("start_pending") and "accepted_command_starts_job" in enabled:
            _fail(
                f"lifecycle.{name}.accepted_command_starts_job",
                "an accepted legal command produced no observable job progress",
            )
        if current.get("active") and enabled & {
            "accepted_command_starts_job", "single_inflight_job_enforced",
            "no_output_without_active_job",
            "busy_tracks_active_job", "completion_matches_final_output",
            "reset_aborts_pending_job",
        }:
            pending.append(f"{name}:active_job")
        if current.get("completion_due"):
            pending.append(f"{name}:completion_due")
        if current.get("error_due"):
            pending.append(f"{name}:error_due")
    if pending:
        raise AssertionError(
            "feature=runtime.lifecycle_finalization; finite test ended with " + ", ".join(pending)
        )


__all__ = [
    "check_lifecycle_operations",
    "check_reset_outputs",
    "finalize_lifecycle_checker_state",
    "is_lifecycle_reset_active",
]
