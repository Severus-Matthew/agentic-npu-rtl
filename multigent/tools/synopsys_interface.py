"""External Synopsys synthesis/PPA integration boundary.

The multi-agent team does not own the Synopsys implementation. Another project
member will provide the executable integration. This module defines the stable
contract that the LangGraph workflow will consume.

Expected responsibility of the external implementation:
- accept a verified RTL workspace and synthesis configuration;
- run the agreed Synopsys flow;
- emit a JSON report matching ``schemas/synthesis_result.schema.json``;
- preserve raw logs/reports for provenance.

No agent may fabricate synthesis, timing, power, or area values when this
interface has not returned a real tool-generated report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


class SynopsysBackend(Protocol):
    """Protocol implemented by the externally owned Synopsys adapter."""

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
    """Tool-independent request passed to the external Synopsys implementation."""

    rtl_dir: Path
    output_dir: Path
    top_module: str
    clock_period_ns: float | None = None


class SynopsysIntegrationUnavailable(RuntimeError):
    """Raised when the externally owned Synopsys backend is not configured."""


def run_synopsys(*_: Any, **__: Any) -> Mapping[str, Any]:
    """Placeholder entry point until the external Synopsys adapter is supplied.

    Failing explicitly is intentional: the workflow must never replace missing
    EDA evidence with an LLM estimate.
    """

    raise SynopsysIntegrationUnavailable(
        "Synopsys integration is externally owned and has not been configured."
    )
