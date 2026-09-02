"""Synopsys synthesis/PPA integration boundary.

This module defines the stable technical interface consumed by the multi-agent
workflow. The Synopsys executable adapter is outside this repository.

The integration must:
- accept a functionally verified RTL workspace and synthesis configuration;
- run the configured Synopsys flow;
- emit a JSON report matching ``schemas/synthesis_result.schema.json``;
- preserve raw logs/reports for provenance.

No agent may fabricate synthesis, timing, power, area, frequency, or utilization
values when no real tool-generated report is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


class SynopsysBackend(Protocol):
    """Interface implemented by a configured Synopsys adapter."""

    def run(
        self,
        *,
        rtl_dir: Path,
        output_dir: Path,
        config: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Run Synopsys and return a structured synthesis/PPA result."""
        ...


@dataclass(frozen=True)
class SynopsysRequest:
    """Request passed to the Synopsys integration."""

    rtl_dir: Path
    output_dir: Path
    top_module: str
    clock_period_ns: float | None = None


class SynopsysIntegrationUnavailable(RuntimeError):
    """Raised when no Synopsys backend is configured."""


def run_synopsys(*_: Any, **__: Any) -> Mapping[str, Any]:
    """Placeholder entry point until a Synopsys adapter is configured.

    Failing explicitly prevents missing EDA evidence from being replaced by an
    LLM estimate.
    """

    raise SynopsysIntegrationUnavailable(
        "Synopsys integration is not configured."
    )
