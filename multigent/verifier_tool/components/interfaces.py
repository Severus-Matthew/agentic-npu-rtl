"""Stable ABI vocabulary for reusable and contract-local components.

The catalog stores an ABI name instead of teaching the resolver about each
driver or checker.  New components may be registered without changing core
selection code when they implement one of these existing invocation shapes.
Adding a genuinely new execution model still requires defining and qualifying a
new ABI here; a manifest cannot make an incompatible callable safe by itself.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


KNOWN_COMPONENT_TYPES = frozenset({
    "protocol_source_driver",
    "protocol_sink_driver",
    "protocol_memory_driver",
    "lifecycle_driver",
    "memory_model",
    "memory_adapter",
    "serialization_adapter",
    "assertion_checker",
    "event_correlation_checker",
    "transaction_completion_checker",
    "coverage_sampler",
    "runtime_monitor",
    "stimulus_strategy",
    "golden_operation",
    "formula_compiler",
    "constraint_solver",
})

KNOWN_EXECUTION_OWNERS = frozenset({
    "verifier_extension",
    "pipeline",
})

KNOWN_ABIS = frozenset({
    "role_bound_channel_source_v1",
    "role_bound_channel_sink_v1",
    "contract_event_source_v1",
    "contract_event_trace_v1",
    "contract_event_traces_v1",
    "transaction_completion_payload_v1",
    "axi4_protocol_responder_v1",
    "axi4_memory_job_v1",
    "axi4_lite_memory_job_v1",
    "custom_mmio_read_job_v1",
    "custom_mmio_write_job_v1",
    "accepted_command_v1",
    "control_plane_sequence_v1",
    "byte_addressable_memory_v1",
    "operation_memory_adapter_v1",
    "canonical_pack_v1",
    "canonical_unpack_v1",
    "snapshot_checker_v1",
    "plan_coverage_monitor_v1",
    "operation_sampling_monitor_v1",
    "runtime_monitor_v1",
    "feature_plan_strategy_v1",
    "canonical_golden_v1",
    "solver_targeted_stimulus_v1",
    "scalar_formula_compiler_v1",
    "contract_local_assertion_v1",
    "contract_local_coverage_v1",
    "contract_local_stimulus_v1",
})


# Required parameter names are deliberately the smallest stable call boundary.
# Optional tuning parameters may grow without invalidating a component. A new
# incompatible execution shape receives a new ABI rather than a resolver branch.
ABI_REQUIRED_PARAMETERS = {
    "role_bound_channel_source_v1": ("dut", "clock_name", "channel", "beats"),
    "role_bound_channel_sink_v1": ("dut", "clock_name", "channel"),
    "contract_event_source_v1": ("dut", "profile", "transaction", "beats"),
    "contract_event_trace_v1": ("dut", "profile", "transaction", "stimulus"),
    "contract_event_traces_v1": ("dut", "bindings", "stimulus"),
    "transaction_completion_payload_v1": (
        "transaction_trace",
        "expected_payloads",
        "payload_signal",
    ),
    "axi4_protocol_responder_v1": ("dut", "clock_name", "group", "request_counts"),
    "axi4_memory_job_v1": ("dut", "clock_name", "group", "operation", "case", "bases"),
    "axi4_lite_memory_job_v1": ("dut", "clock_name", "group", "operation", "case"),
    "custom_mmio_read_job_v1": ("dut", "clock_name", "group", "operation", "case", "bases"),
    "custom_mmio_write_job_v1": ("dut", "clock_name", "group", "operation", "memory"),
    "accepted_command_v1": ("dut", "clock_name", "command", "value"),
    "control_plane_sequence_v1": (
        "dut",
        "clock_name",
        "control_group",
        "sequence",
        "actions",
    ),
    "byte_addressable_memory_v1": ("size",),
    "operation_memory_adapter_v1": ("size",),
    "canonical_pack_v1": ("values", "binding"),
    "canonical_unpack_v1": ("words", "binding", "expected_count"),
    "snapshot_checker_v1": ("snapshot", "plan", "state"),
    "plan_coverage_monitor_v1": ("plan",),
    "operation_sampling_monitor_v1": ("plan", "read_signal", "read_width"),
    "runtime_monitor_v1": ("plan",),
    "feature_plan_strategy_v1": ("operation_metadata",),
    "canonical_golden_v1": ("operation_metadata", "stimulus"),
    "solver_targeted_stimulus_v1": ("operation_metadata", "concept", "bin_spec"),
    "scalar_formula_compiler_v1": ("formula",),
    # Contract-local branch arguments are defined by frozen required_observations
    # and bundle parameters, then checked by extensions.authoring rather than a
    # fixed global Python signature.
    "contract_local_assertion_v1": (),
    "contract_local_coverage_v1": (),
    "contract_local_stimulus_v1": (),
}


# Static invocation requirements that make selected checker calls meaningful.
# These live with the ABI rather than in a benchmark prompt or resolver branch,
# so every future component implementing the same execution shape inherits the
# same anti-vacuity contract.
ABI_CALL_CONSTRAINTS = {
    "transaction_completion_payload_v1": {
        "nonempty_arguments": ("expected_payloads",),
        "forbid_false_arguments": ("require_activity", "require_all_completed"),
        "assert_result_field": "passed",
    },
}


@runtime_checkable
class CallableComponent(Protocol):
    """The minimal loader boundary shared by functions and callable classes."""

    def __call__(self, *args: object, **kwargs: object) -> object: ...


__all__ = [
    "ABI_CALL_CONSTRAINTS",
    "ABI_REQUIRED_PARAMETERS",
    "CallableComponent",
    "KNOWN_ABIS",
    "KNOWN_COMPONENT_TYPES",
    "KNOWN_EXECUTION_OWNERS",
]
