from __future__ import annotations

from multigent.agents.architect import ArchitectAgent


def test_architect_skill_requires_operand_staging_cycle_accounting() -> None:
    instructions = ArchitectAgent().load_instructions()

    assert "explicitly account for the cycles required to populate its operand staging storage" in instructions
    assert "ping-pong buffering" in instructions
    assert "live-result storage is sufficient" in instructions
    assert "adding optional modes not requested or technically required" in instructions
