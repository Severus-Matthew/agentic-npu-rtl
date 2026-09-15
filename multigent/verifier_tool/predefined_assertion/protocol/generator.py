"""Generate code-owned ready/valid protocol assertions and their TB monitor."""

from __future__ import annotations

from typing import Any, Mapping


def _literal(value: object) -> str:
    return repr(value)


def protocol_assertion_metadata(
    interface_plan: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    obligations = [
        dict(item)
        for item in interface_plan.get("obligations", [])
        if item.get("template") == "stall_stability"
    ]
    return obligations, tuple(str(item["id"]) for item in obligations)


def render_protocol_assertion_lines(
    interface_plan: Mapping[str, Any],
    *,
    reset: str,
    obligations: list[dict[str, Any]],
) -> list[str]:
    """Render deterministic stall-stability assertions from role bindings."""

    lines = [
        "def _check_contract_protocol_assertions(snapshot):",
        "    \"\"\"Run protocol assertions and return completed temporal observations.\"\"\"",
        "    completed_stalls = {}",
    ]
    if reset:
        reset_obligation = next(
            (
                item
                for item in interface_plan.get("obligations", [])
                if item.get("template") == "reset_behavior"
                and str(item.get("bindings", {}).get("signal", "")) == reset
            ),
            None,
        )
        active_value = (
            reset_obligation.get("bindings", {}).get("active_value")
            if isinstance(reset_obligation, Mapping)
            else None
        )
        if active_value in {0, 1}:
            lines += [
                f"    if int(bool(snapshot[{reset!r}])) == {int(active_value)}:",
                "        _CONTRACT_PROTOCOL_STATE.clear()",
                "        return completed_stalls",
            ]
    if not obligations:
        lines.append("    return completed_stalls")
    for index, obligation in enumerate(obligations):
        obligation_id = str(obligation["id"])
        bindings = obligation.get("bindings", {})
        valid = str(bindings["valid"])
        ready = str(bindings["ready"])
        observed: list[str] = []
        for role in ("payload", "metadata", "last", "keep", "transaction_id"):
            names = bindings.get(role, [])
            if isinstance(names, str):
                names = [names]
            observed.extend(map(str, names))
        related = tuple([valid, ready, *observed])
        prefix = f"_p{index}"
        lines += [
            "",
            f"    # PROTOCOL ASSERTION [{obligation_id}]",
            f"    {prefix}_valid = int(bool(snapshot[{valid!r}]))",
            f"    {prefix}_ready = int(bool(snapshot[{ready!r}]))",
            f"    {prefix}_content = tuple(snapshot[name] for name in {_literal(tuple(observed))})",
            f"    {prefix}_previous = _CONTRACT_PROTOCOL_STATE.get({obligation_id!r})",
            f"    if {prefix}_previous is not None:",
            f"        assert {prefix}_valid == 1, (",
            f"            {('protocol valid was withdrawn before stalled transfer completed; feature=' + obligation_id + '; related_signals=' + repr(related) + '; observed=')!r}",
            f"            + repr({{name: snapshot[name] for name in {_literal(related)}}})",
            "        )",
            f"        assert {prefix}_content == {prefix}_previous['content'], (",
            f"            {('producer-owned content changed during stall or release; feature=' + obligation_id + '; related_signals=' + repr(related) + '; previous=')!r}",
            f"            + repr({prefix}_previous['content']) + '; observed='",
            f"            + repr({prefix}_content)",
            "        )",
            f"    if {prefix}_valid and not {prefix}_ready:",
            f"        if {prefix}_previous is None:",
            f"            _CONTRACT_PROTOCOL_STATE[{obligation_id!r}] = {{",
            f"                'content': {prefix}_content, 'length': 1",
            "            }",
            "        else:",
            f"            {prefix}_previous['length'] += 1",
            "    else:",
            f"        if {prefix}_previous is not None:",
            f"            completed_stalls[{obligation_id!r}] = {prefix}_previous['length']",
            f"        _CONTRACT_PROTOCOL_STATE.pop({obligation_id!r}, None)",
        ]
    if obligations:
        lines.append("    return completed_stalls")
    return lines


def render_protocol_monitor_lines(*, clock: str, reset: str) -> list[str]:
    """Render the single clock observer shared by assertions and coverage."""

    reset_tuple = (reset,) if reset else ()
    return [
        "async def _contract_generated_monitor(dut):",
        "    \"\"\"Observe the interface once and share it with assertions and coverage.\"\"\"",
        f"    clock = getattr(dut, {clock!r})",
        "    while True:",
        "        await Edge(clock)",
        "        await ReadOnly()",
        "        if int(clock.value) != 0:",
        f"            reset_snapshot = capture_contract_snapshot(dut, {_literal(reset_tuple)})",
        "            if reset_snapshot:",
        "                observe_contract_reset_snapshot(",
        "                    reset_snapshot, _check_contract_protocol_assertions",
        "                )",
        "            continue",
        "        snapshot = capture_contract_snapshot(dut, CONTRACT_SIGNAL_NAMES)",
        "        sample_contract_snapshot(snapshot, _check_contract_protocol_assertions)",
    ]
