"""Protocol-specific wire drivers -- the thin layer of the memory/adapter/
driver split, sitting on top of the shared `../adapter/` (operation-aware
address windows and value packing) and `../memory/` (raw byte storage)
packages.

- `axi_lite.py` -- AXI4-Lite (single-outstanding, strict in-order).
- `axi4_outstanding.py` -- full AXI4 (multi-outstanding, ID-correlated,
  genuinely out-of-order-completing, via `RandomCompletionScheduler`).
- `custom_mmio.py` -- an LLM-declared custom memory-like protocol
  (`protocol_profile: custom_mmio`), reusing `RandomCompletionScheduler` and
  `OperationMemoryAdapter` unmodified. Both directions (multi-beat read via
  an optional `len` field, and write with an optional response channel) are
  implemented and wired into `../../../orchestration/campaign.py`'s
  automatic campaign.

All three import `OperationMemoryAdapter` from `../adapter` rather than
keeping private address-window/packing logic, so none of them carries its
own copy of that logic.
"""

from .axi_lite import (
    AxiLiteMemoryDriveError,
    default_axi_lite_memory_bases,
    execute_axi_lite_memory_job,
)
from ._completion_scheduler import RandomCompletionScheduler
from .axi4_outstanding import Axi4OutstandingDriveError, execute_axi4_memory_job
from .custom_mmio import (
    CustomMmioDriveError,
    execute_custom_mmio_read_job,
    execute_custom_mmio_write_job,
)

__all__ = [
    "AxiLiteMemoryDriveError",
    "Axi4OutstandingDriveError",
    "CustomMmioDriveError",
    "RandomCompletionScheduler",
    "default_axi_lite_memory_bases",
    "execute_axi4_memory_job",
    "execute_axi_lite_memory_job",
    "execute_custom_mmio_read_job",
    "execute_custom_mmio_write_job",
]
