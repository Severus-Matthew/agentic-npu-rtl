"""Generate a small TB wrapper around tool-owned protocol assertion logic."""

from __future__ import annotations

from typing import Any, Mapping

from .runtime import build_protocol_assertion_plan


def _literal(value: object) -> str:
    return repr(value)


def protocol_assertion_metadata(
    interface_plan: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    assertion_plan = build_protocol_assertion_plan(interface_plan)
    return assertion_plan, tuple(map(str, assertion_plan["features"]))


def render_protocol_assertion_lines(
    interface_plan: Mapping[str, Any],
    *,
    reset: str,
    obligations: Mapping[str, Any],
) -> list[str]:
    """Render only immutable bindings and one call into verifier_tool."""

    del interface_plan, reset
    lines = [
        f"CONTRACT_PROTOCOL_ASSERTION_PLAN = {_literal(dict(obligations))}",
        "",
    ]
    for feature in obligations.get("features", ()):
        lines.append(f"# PROTOCOL ASSERTION [{feature}]")
    lines += [
        "def _check_contract_protocol_assertions(snapshot):",
        "    \"\"\"Delegate all protocol state and rules to verifier_tool.\"\"\"",
        "    return _contract_check_protocol_assertions(",
        "        snapshot, CONTRACT_PROTOCOL_ASSERTION_PLAN, _CONTRACT_PROTOCOL_STATE",
        "    )",
        "",
        "def _finalize_contract_protocol_assertions():",
        "    \"\"\"Require a terminal disposition for finite protocol work.\"\"\"",
        "    return _contract_finalize_protocol_assertions(",
        "        CONTRACT_PROTOCOL_ASSERTION_PLAN, _CONTRACT_PROTOCOL_STATE",
        "    )",
    ]
    return lines


def render_protocol_monitor_lines(
    *, clock: str, reset: str, assertion_callback: str = "_check_contract_protocol_assertions"
) -> list[str]:
    """Render the single clock observer shared by assertions and coverage."""

    reset_tuple = (reset,) if reset else ()
    return [
        "async def _contract_generated_monitor(dut):",
        "    \"\"\"Observe the interface once and share it with assertions and coverage.\"\"\"",
        f"    clock = getattr(dut, {clock!r})",
        "    while True:",
        "        await Edge(clock)",
        "        # Drivers update READY/VALID just after the falling edge. Sample",
        "        # after their one-picosecond settling step, before the next edge.",
        "        await Timer(2, unit='ps')",
        "        await ReadOnly()",
        "        if int(clock.value) != 0:",
        f"            reset_snapshot = capture_contract_snapshot(dut, {_literal(reset_tuple)})",
        "            if reset_snapshot:",
        "                observe_contract_reset_snapshot(",
        f"                    reset_snapshot, {assertion_callback}",
        "                )",
        "            continue",
        "        snapshot = capture_contract_snapshot(dut, CONTRACT_SIGNAL_NAMES)",
        f"        sample_contract_snapshot(snapshot, {assertion_callback})",
    ]
