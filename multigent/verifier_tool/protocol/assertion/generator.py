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
    clock_domains: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[str]:
    """Render only immutable bindings and one call into verifier_tool."""

    del interface_plan, reset
    lines = [
        f"CONTRACT_PROTOCOL_ASSERTION_PLAN = {_literal(dict(obligations))}",
        f"CONTRACT_PROTOCOL_CLOCK_DOMAINS = {_literal(dict(clock_domains or {}))}",
        "",
    ]
    for feature in obligations.get("features", ()):
        lines.append(f"# PROTOCOL ASSERTION [{feature}]")
    lines += [
        "def _check_contract_protocol_assertions(snapshot, clock_name=None):",
        "    \"\"\"Delegate all protocol state and rules to verifier_tool.\"\"\"",
        "    domain = CONTRACT_PROTOCOL_CLOCK_DOMAINS.get(clock_name)",
        "    plan = domain['assertion_plan'] if domain is not None else CONTRACT_PROTOCOL_ASSERTION_PLAN",
        "    state = _CONTRACT_PROTOCOL_STATE.setdefault(clock_name, {}) if domain is not None else _CONTRACT_PROTOCOL_STATE",
        "    return _contract_check_protocol_assertions(",
        "        snapshot, plan, state",
        "    )",
        "",
        "def _finalize_contract_protocol_assertions():",
        "    \"\"\"Require a terminal disposition for finite protocol work.\"\"\"",
        "    if CONTRACT_PROTOCOL_CLOCK_DOMAINS:",
        "        for clock_name, domain in CONTRACT_PROTOCOL_CLOCK_DOMAINS.items():",
        "            _contract_finalize_protocol_assertions(",
        "                domain['assertion_plan'], _CONTRACT_PROTOCOL_STATE.setdefault(clock_name, {})",
        "            )",
        "        return None",
        "    return _contract_finalize_protocol_assertions(",
        "        CONTRACT_PROTOCOL_ASSERTION_PLAN, _CONTRACT_PROTOCOL_STATE",
        "    )",
    ]
    return lines


def render_protocol_monitor_lines(
    *,
    clock: str,
    reset: str,
    assertion_callback: str = "_check_contract_protocol_assertions",
    clock_domains: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[str]:
    """Render clock-domain observers shared by assertions and coverage."""

    reset_tuple = (reset,) if reset else ()
    domains = dict(clock_domains or {})
    if domains:
        return [
            "async def _contract_generated_clock_monitor(dut, clock_name):",
            "    \"\"\"Sample one protocol domain on its contract-declared clock.\"\"\"",
            "    domain = CONTRACT_PROTOCOL_CLOCK_DOMAINS[clock_name]",
            "    clock = getattr(dut, clock_name)",
            "    def domain_assertions(snapshot):",
            f"        return {assertion_callback}(snapshot, clock_name)",
            "    while True:",
            "        await Edge(clock)",
            "        await Timer(2, unit='ps')",
            "        await ReadOnly()",
            "        if int(clock.value) != 0:",
            f"            if domain['sample_shared_domains']:",
            f"                reset_snapshot = capture_contract_snapshot(dut, {_literal(reset_tuple)})",
            "                if reset_snapshot:",
            "                    observe_contract_reset_snapshot(reset_snapshot, domain_assertions)",
            "            continue",
            "        snapshot = capture_contract_snapshot(dut, CONTRACT_SIGNAL_NAMES)",
            "        sample_contract_snapshot(",
            "            snapshot, domain_assertions,",
            "            protocol_obligation_ids=domain['obligation_ids'],",
            "            sample_shared_domains=domain['sample_shared_domains'],",
            "        )",
            "",
            "async def _contract_generated_monitor(dut):",
            "    \"\"\"Start every contract-declared protocol clock observer.\"\"\"",
            "    tasks = [",
            "        _contract_cocotb.start_soon(_contract_generated_clock_monitor(dut, clock_name))",
            "        for clock_name in CONTRACT_PROTOCOL_CLOCK_DOMAINS",
            "    ]",
            "    try:",
            "        await tasks[0]",
            "    finally:",
            "        for task in tasks:",
            "            task.cancel()",
        ]
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
