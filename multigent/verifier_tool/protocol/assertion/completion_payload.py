"""Protocol-independent accepted-request/completion-payload reconciliation."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any


class CompletionPayloadError(ValueError):
    """Runtime transaction evidence cannot prove completion payload correctness."""


def check_transaction_completion_payloads(
    transaction_trace: Sequence[Mapping[str, Any]],
    expected_payloads: Sequence[Any],
    payload_signal: str,
    *,
    payload_required: Sequence[bool] | None = None,
    request_event: str = "accepted",
    completion_events: Sequence[str] = ("success",),
    request_key_signal: str | None = None,
    completion_key_signal: str | None = None,
    require_activity: bool = True,
    require_all_completed: bool = True,
) -> dict[str, Any]:
    """FIFO-match accepted requests to completions and compare completion payloads.

    The helper deliberately knows no protocol spelling.  ``transaction_trace``
    comes from the code-owned protocol event recorder, and ``payload_signal`` is
    the frozen contract binding sampled in the *same record/cycle* as the
    completion event.  ``expected_payloads`` must come from an independent
    reference model or memory model in request order.  For protocols that mix
    payload-bearing requests (for example reads) with payload-free requests
    (for example write acknowledgements), ``payload_required`` supplies one
    boolean per accepted request.  A false entry still requires a matching
    completion, but skips payload presence and comparison for that request.
    With no key bindings, pairing is FIFO.  When both key-signal names are
    supplied, completions may arrive out of order across keys while remaining
    FIFO within each key.
    """

    if isinstance(transaction_trace, (str, bytes)) or not isinstance(
        transaction_trace, Sequence
    ):
        raise CompletionPayloadError("transaction_trace must be a sequence of records")
    if isinstance(expected_payloads, (str, bytes)) or not isinstance(
        expected_payloads, Sequence
    ):
        raise CompletionPayloadError("expected_payloads must be a sequence")
    if payload_required is not None and (
        isinstance(payload_required, (str, bytes))
        or not isinstance(payload_required, Sequence)
    ):
        raise CompletionPayloadError("payload_required must be a sequence")
    signal = str(payload_signal).strip()
    if not signal:
        raise CompletionPayloadError("payload_signal must not be empty")
    completion_names = tuple(map(str, completion_events))
    if not completion_names:
        raise CompletionPayloadError("completion_events must not be empty")
    request_key = str(request_key_signal or "").strip()
    completion_key = str(completion_key_signal or "").strip()
    if bool(request_key) != bool(completion_key):
        raise CompletionPayloadError(
            "request_key_signal and completion_key_signal must be supplied together"
        )

    pending: deque[int] = deque()
    pending_by_key: dict[Any, deque[int]] = defaultdict(deque)
    errors: list[str] = []
    observed_payloads: list[Any] = []
    accepted_count = 0
    completion_count = 0
    expected = list(expected_payloads)
    required = (
        [True] * len(expected)
        if payload_required is None
        else [bool(item) for item in payload_required]
    )
    if len(required) != len(expected):
        raise CompletionPayloadError(
            "payload_required count must match expected_payloads count"
        )
    checked_payload_count = 0

    for index, raw_record in enumerate(transaction_trace):
        if not isinstance(raw_record, Mapping):
            errors.append(f"trace[{index}] is not a transaction record")
            continue
        event = str(raw_record.get("event", ""))
        if event == request_event:
            if request_key:
                signals = raw_record.get("signals", {})
                if not isinstance(signals, Mapping) or request_key not in signals:
                    errors.append(
                        f"accepted request at trace[{index}] lacks key signal "
                        f"{request_key!r}"
                    )
                else:
                    pending_by_key[signals[request_key]].append(accepted_count)
            else:
                pending.append(accepted_count)
            accepted_count += 1
            continue
        if event not in completion_names:
            continue
        completion_count += 1
        signals = raw_record.get("signals", {})
        if request_key:
            if not isinstance(signals, Mapping) or completion_key not in signals:
                errors.append(
                    f"completion at trace[{index}] lacks key signal "
                    f"{completion_key!r}"
                )
                continue
            key = signals[completion_key]
            keyed_pending = pending_by_key.get(key)
            if not keyed_pending:
                errors.append(
                    f"completion at trace[{index}] for key {key!r} has no accepted request"
                )
                continue
            request_index = keyed_pending.popleft()
            if not keyed_pending:
                pending_by_key.pop(key, None)
        else:
            if not pending:
                errors.append(
                    f"completion at trace[{index}] has no accepted request"
                )
                continue
            request_index = pending.popleft()
        if request_index >= len(expected):
            errors.append(
                f"accepted request {request_index} has no independent expected payload"
            )
            continue
        if not required[request_index]:
            continue
        checked_payload_count += 1
        if not isinstance(signals, Mapping) or signal not in signals:
            errors.append(
                f"completion at trace[{index}] lacks same-cycle payload signal {signal!r}"
            )
            continue
        actual = signals[signal]
        observed_payloads.append(actual)
        if actual != expected[request_index]:
            errors.append(
                f"completion payload mismatch for request {request_index}: "
                f"expected={expected[request_index]!r}, observed={actual!r}"
            )

    if require_activity and accepted_count == 0:
        errors.append("no accepted request was observed")
    if require_activity and completion_count == 0:
        errors.append("no completion was observed")
    if len(expected) != accepted_count:
        errors.append(
            f"expected payload count {len(expected)} does not match accepted request "
            f"count {accepted_count}"
        )
    pending_count = (
        sum(len(indices) for indices in pending_by_key.values())
        if request_key
        else len(pending)
    )
    if require_all_completed and pending_count:
        errors.append(
            f"{pending_count} accepted request(s) remain without completion"
        )

    return {
        "passed": not errors,
        "errors": errors,
        "accepted_count": accepted_count,
        "completion_count": completion_count,
        "pending_count": pending_count,
        "checked_payload_count": checked_payload_count,
        "expected_payloads": expected,
        "payload_required": required,
        "observed_payloads": observed_payloads,
    }


__all__ = ["CompletionPayloadError", "check_transaction_completion_payloads"]
