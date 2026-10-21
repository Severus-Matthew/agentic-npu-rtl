"""Code-owned protocol stimulus plans."""

from .stimulus_generator import (
    ProtocolStimulusGenerationError,
    build_protocol_stimulus_plan,
    generate_random_protocol_scenarios,
    resolved_control_plane_probe_plan,
    resolved_operation_transport_variants,
)
from .cocotb import (
    ProtocolDriveError,
    collect_protocol_field_values,
    collect_protocol_transfers,
    drive_protocol_event_transactions,
    drive_protocol_field_values,
    drive_protocol_reset,
    drive_protocol_transfers,
)
from .drivers import (
    AxiLiteMemoryDriveError,
    Axi4OutstandingDriveError,
    CustomMmioDriveError,
    RandomCompletionScheduler,
    default_axi_lite_memory_bases,
    execute_axi4_memory_job,
    execute_axi_lite_memory_job,
    execute_custom_mmio_read_job,
    execute_custom_mmio_write_job,
)
from .adapter import (
    OperationMemoryAdapter,
    OperationMemoryAdapterError,
)
from .memory import Memory
from ..evidence import (
    ProtocolEvidenceError,
    ProtocolEventTraceRecorder,
    capture_protocol_event_trace,
)

__all__ = [
    "AxiLiteMemoryDriveError",
    "Axi4OutstandingDriveError",
    "CustomMmioDriveError",
    "Memory",
    "OperationMemoryAdapter",
    "OperationMemoryAdapterError",
    "ProtocolStimulusGenerationError",
    "RandomCompletionScheduler",
    "build_protocol_stimulus_plan",
    "generate_random_protocol_scenarios",
    "resolved_control_plane_probe_plan",
    "resolved_operation_transport_variants",
    "ProtocolDriveError",
    "ProtocolEvidenceError",
    "ProtocolEventTraceRecorder",
    "capture_protocol_event_trace",
    "collect_protocol_field_values",
    "collect_protocol_transfers",
    "default_axi_lite_memory_bases",
    "drive_protocol_event_transactions",
    "drive_protocol_field_values",
    "drive_protocol_reset",
    "drive_protocol_transfers",
    "execute_axi4_memory_job",
    "execute_axi_lite_memory_job",
    "execute_custom_mmio_read_job",
    "execute_custom_mmio_write_job",
]
