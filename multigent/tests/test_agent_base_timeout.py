from __future__ import annotations

import signal
import time

import pytest

from multigent.agents.base import _AgentRequestDeadline, _wall_clock_deadline


@pytest.mark.skipif(
    not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"),
    reason="total wall-clock deadlines require POSIX interval timers",
)
def test_wall_clock_deadline_interrupts_active_request() -> None:
    started = time.monotonic()
    with pytest.raises(_AgentRequestDeadline):
        with _wall_clock_deadline(1):
            time.sleep(5)
    assert time.monotonic() - started < 2.5


@pytest.mark.skipif(
    not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"),
    reason="total wall-clock deadlines require POSIX interval timers",
)
def test_wall_clock_deadline_restores_signal_handler_and_timer() -> None:
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    with _wall_clock_deadline(1):
        pass
    assert signal.getsignal(signal.SIGALRM) == previous_handler
    assert signal.getitimer(signal.ITIMER_REAL) == previous_timer
