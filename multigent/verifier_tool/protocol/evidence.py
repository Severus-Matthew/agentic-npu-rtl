"""Reusable runtime evidence capture for contract-defined protocol events.

The Architect owns event meaning and signal bindings.  This module owns the
mechanical act of sampling those bindings from a running DUT.  Contract-local
Verifier code may classify the returned evidence, but it must never reconstruct
an equivalent-looking trace from planned stimulus.
"""

from __future__ import annotations

from collections.abc import Awaitable, Mapping, Sequence
from typing import Any

from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
    evaluate_protocol_expression,
    expression_signals,
)


class ProtocolEvidenceError(AssertionError):
    """A contract-defined runtime trace cannot be captured safely."""


def _handle(dut: Any, name: str) -> Any:
    try:
        return getattr(dut, name)
    except AttributeError as exc:
        raise ProtocolEvidenceError(
            f"DUT is missing protocol-evidence signal {name!r}"
        ) from exc


def _transaction_expressions(transaction: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for name in (
        "presented", "ready", "accepted", "stalled", "completed", "success", "error"
    ):
        expression = transaction.get(name)
        if isinstance(expression, Mapping):
            result[name] = expression
    return result


class ProtocolEventTraceRecorder:
    """Classify real per-cycle snapshots using one compiled transaction model."""

    def __init__(
        self,
        profile: Mapping[str, Any],
        transaction: Mapping[str, Any],
        signal_names: Sequence[str] = (),
    ) -> None:
        expressions = _transaction_expressions(transaction)
        if "accepted" not in expressions:
            raise ProtocolEvidenceError("compiled transaction lacks an accepted expression")
        self.profile = profile
        self.transaction = transaction
        self.expressions = expressions
        cancellation = profile.get("cancellation", {})
        cancellation_expression = (
            cancellation.get("trigger") if isinstance(cancellation, Mapping) else None
        )
        self.cancellation_expression = (
            cancellation_expression
            if isinstance(cancellation_expression, Mapping)
            else None
        )
        required = {
            name
            for expression in (
                *expressions.values(),
                *(
                    (self.cancellation_expression,)
                    if self.cancellation_expression is not None
                    else ()
                ),
            )
            for name in expression_signals(expression)
        }
        required.update(map(str, transaction.get("content", ())))
        required.update(map(str, signal_names))
        self.signal_names = tuple(sorted(required))
        self.cycle_trace: list[dict[str, Any]] = []
        self.transaction_trace: list[dict[str, Any]] = []
        self.outstanding = 0

    def sample(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        """Record one simulator-derived snapshot and return its cycle record."""

        missing = sorted(set(self.signal_names) - set(snapshot))
        if missing:
            raise ProtocolEvidenceError(
                f"runtime protocol snapshot omits required signal(s) {missing}"
            )
        signals = {name: int(snapshot[name]) for name in self.signal_names}
        events = {
            name: bool(evaluate_protocol_expression(expression, signals))
            for name, expression in self.expressions.items()
        }
        cancelled = bool(
            self.cancellation_expression is not None
            and evaluate_protocol_expression(self.cancellation_expression, signals)
        )
        events["cancelled"] = cancelled
        cycle = len(self.cycle_trace)
        record = {"cycle": cycle, "signals": signals, "events": events}
        self.cycle_trace.append(record)

        before = self.outstanding
        if events.get("accepted"):
            self.outstanding += 1
            self.transaction_trace.append(
                {
                    "cycle": cycle,
                    "event": "accepted",
                    "signals": dict(signals),
                    "outstanding_before": before,
                    "outstanding_after": self.outstanding,
                }
            )
            before = self.outstanding
        if events.get("completed"):
            self.outstanding = max(0, self.outstanding - 1)
            outcome = (
                "error" if events.get("error") else "success"
                if events.get("success") else "completed"
            )
            self.transaction_trace.append(
                {
                    "cycle": cycle,
                    "event": outcome,
                    "signals": dict(signals),
                    "outstanding_before": before,
                    "outstanding_after": self.outstanding,
                }
            )
            before = self.outstanding
        if cancelled and self.outstanding:
            self.outstanding = 0
            self.transaction_trace.append(
                {
                    "cycle": cycle,
                    "event": "cancelled",
                    "signals": dict(signals),
                    "outstanding_before": before,
                    "outstanding_after": 0,
                }
            )
        return record

    def evidence(self, *, stimulus_result: Any = None) -> dict[str, Any]:
        """Return the stable extension-facing evidence object."""

        return {
            "cycle_trace": list(self.cycle_trace),
            "transaction_trace": list(self.transaction_trace),
            "stimulus_result": stimulus_result,
        }


async def capture_protocol_event_trace(
    dut: Any,
    profile: Mapping[str, Any],
    transaction: Mapping[str, Any],
    stimulus: Awaitable[Any],
    *,
    signal_names: Sequence[str] = (),
    tail_cycles: int = 1,
    settle_timer_ps: int = 2,
) -> dict[str, Any]:
    """Run stimulus while collecting real cycle and transaction evidence.

    The caller starts the clock.  This function starts its observer before the
    supplied stimulus coroutine, samples after every falling edge, waits a small
    tail window, and then returns both trace forms required by extension bundles.
    ``signal_names`` may include cross-protocol fields in addition to the event
    model's own dependencies.
    """

    evidence = await capture_protocol_event_traces(
        dut,
        {"default": (profile, transaction)},
        stimulus,
        signal_names=signal_names,
        tail_cycles=tail_cycles,
        settle_timer_ps=settle_timer_ps,
    )
    return evidence["default"]


async def capture_protocol_event_traces(
    dut: Any,
    bindings: Mapping[
        str, tuple[Mapping[str, Any], Mapping[str, Any]]
    ],
    stimulus: Awaitable[Any],
    *,
    signal_names: Sequence[str] = (),
    tail_cycles: int = 1,
    settle_timer_ps: int = 2,
) -> dict[str, dict[str, Any]]:
    """Capture several contract bindings concurrently around one stimulus.

    This is the multi-clock counterpart of :func:`capture_protocol_event_trace`.
    Every recorder starts before the single shared stimulus, samples on its own
    contract-declared clock, and receives the same stimulus result.  It prevents
    a CDC or bridge checker from replaying traffic once per domain and then
    incorrectly correlating observations from different transactions.
    """

    if not isinstance(bindings, Mapping) or not bindings:
        raise ProtocolEvidenceError("protocol evidence bindings must be nonempty")
    if any(not isinstance(name, str) or not name for name in bindings):
        raise ProtocolEvidenceError("protocol evidence binding names must be nonempty strings")
    if tail_cycles < 0:
        raise ProtocolEvidenceError("tail_cycles must be nonnegative")
    if settle_timer_ps < 1:
        raise ProtocolEvidenceError("settle_timer_ps must be positive")

    prepared: dict[str, tuple[Any, ProtocolEventTraceRecorder]] = {}
    for name, binding in bindings.items():
        if not isinstance(binding, tuple) or len(binding) != 2:
            raise ProtocolEvidenceError(
                f"protocol evidence binding {name!r} must be a (profile, transaction) tuple"
            )
        profile, transaction = binding
        clock = profile.get("clock", {})
        if not isinstance(clock, Mapping) or str(clock.get("edge", "")) != "rising":
            raise ProtocolEvidenceError(
                f"protocol evidence binding {name!r} requires a rising-edge clock"
            )
        prepared[name] = (
            _handle(dut, str(clock.get("signal", ""))),
            ProtocolEventTraceRecorder(profile, transaction, signal_names),
        )

    import cocotb
    from cocotb.triggers import Event, FallingEdge, ReadOnly, Timer

    done = Event()

    async def observe(clock_signal: Any, recorder: ProtocolEventTraceRecorder) -> None:
        remaining_tail: int | None = None
        while True:
            await FallingEdge(clock_signal)
            await Timer(settle_timer_ps, unit="ps")
            await ReadOnly()
            recorder.sample(
                {name: int(_handle(dut, name).value) for name in recorder.signal_names}
            )
            if done.is_set():
                if remaining_tail is None:
                    remaining_tail = max(1, tail_cycles)
                remaining_tail -= 1
                if remaining_tail == 0:
                    return

    observers = [
        cocotb.start_soon(observe(clock_signal, recorder))
        for clock_signal, recorder in prepared.values()
    ]
    try:
        stimulus_result = await stimulus
        done.set()
        for observer in observers:
            await observer
    except BaseException:
        done.set()
        for observer in observers:
            if hasattr(observer, "kill"):
                observer.kill()
        raise
    return {
        name: recorder.evidence(stimulus_result=stimulus_result)
        for name, (_, recorder) in prepared.items()
    }


__all__ = [
    "ProtocolEvidenceError",
    "ProtocolEventTraceRecorder",
    "capture_protocol_event_trace",
    "capture_protocol_event_traces",
]
