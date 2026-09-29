"""Proves `automatic_campaign_support`'s per-operation breakdown: one
operation with an unrecognized protocol should not poison another,
otherwise-fine operation in the same contract's automatic campaign.

Before this, `run_code_owned_verification_campaign` had exactly one global
on/off switch (`include_automatic_campaign`), decided from a single
`supported` boolean covering every operation combined -- so a contract with
two operations, one on a known protocol and one on something this tool does
not recognize, got *zero* automatic coverage for either, not just the one
that actually needed hand-written source.
"""
from __future__ import annotations

from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import axi_lite_contracts
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    build_interface_coverage_plan,
)
from multigent.verifier_tool.operation.coverage.plan import (
    merge_coverage_plans,
    operation_plan_for_tests,
)
from multigent.verifier_tool.orchestration.campaign import (
    _operation_campaign_reasons,
    _operation_protocol_lifecycle_reasons,
    automatic_campaign_support,
    code_owned_obligations_for_supported_operations,
)


def _scalar_binding(data_object: str, *, protocol_profile: str) -> dict:
    return {
        "data_object": data_object,
        "dimensions": [],
        "data_type": {"width_bits": 8, "signed": True},
        "protocol_profile": protocol_profile,
        "serialization": {"kind": "scalar", "index_order": []},
    }


def _operation(name: str, *, protocol_profile: str) -> dict:
    return {
        "operation_name": name,
        "arithmetic": {"classifier_profile": "integer_matrix_multiply"},
        "inputs": [_scalar_binding(f"{name}_in", protocol_profile=protocol_profile)],
        "outputs": [_scalar_binding(f"{name}_out", protocol_profile=protocol_profile)],
        "lifecycle": {
            "job_accept_channels": [{"channel": "cmd", "legal_values": [1]}],
        },
    }


def test_one_unsupported_operation_does_not_poison_a_supported_sibling():
    good = _operation("good_op", protocol_profile="ready_valid")
    bad = _operation("bad_op", protocol_profile="some_protocol_this_tool_does_not_know")
    metadata = {"schema_version": 2, "operations": [good, bad]}

    report = automatic_campaign_support(metadata)

    assert report["supported"] is False, "aggregate view: not every operation qualifies"
    assert report["any_operation_supported"] is True, "but at least one does"
    assert report["operations"]["good_op"]["supported"] is True
    assert report["operations"]["good_op"]["reasons"] == []
    assert report["operations"]["bad_op"]["supported"] is False
    assert any(
        "operation_io_profile_not_executable" in reason
        for reason in report["operations"]["bad_op"]["reasons"]
    )
    # Every reason in the aggregate list is attributable back to one
    # operation's own per-operation breakdown -- nothing is lost by going
    # through the per-operation view instead of the flat aggregate one.
    assert set(report["reasons"]) == set(report["operations"]["bad_op"]["reasons"])


def test_operation_campaign_reasons_is_what_the_runtime_loop_skips_on():
    good = _operation("good_op", protocol_profile="ready_valid")
    bad = _operation("bad_op", protocol_profile="some_protocol_this_tool_does_not_know")

    assert _operation_campaign_reasons(good, "good_op") == []
    assert _operation_campaign_reasons(bad, "bad_op") != []


def test_axi4_campaign_support_requires_the_drivers_id_fields() -> None:
    capabilities = {
        "max_outstanding": 2,
        "read_write_concurrency": True,
        "address_bins": "aligned",
        "write_strobe_bins": "full",
        "protection_bins": "none",
        "write_order_bins": "address_first",
    }
    fields = {
        "write_address": ["addr", "len", "size", "burst"],
        "write_data": ["data", "strb", "last"],
        "write_response": ["resp"],
        "read_address": ["addr", "len", "size", "burst"],
        "read_data": ["data", "resp", "last"],
    }
    binding = {
        "protocol_profile": "axi4",
        "serialization": {"kind": "scalar", "index_order": []},
        "dimensions": [],
        "memory_mapping": {
            "protocol_capabilities": capabilities,
            "protocol_fields": fields,
        },
    }
    operation = {
        "inputs": [binding],
        "outputs": [binding],
        "lifecycle": {"job_accept_channels": [{"legal_values": [1]}]},
    }
    reasons = _operation_protocol_lifecycle_reasons(operation, "job")
    assert any("axi4_outstanding_requires_id_fields" in reason for reason in reasons)
    for kind in ("write_address", "write_response", "read_address", "read_data"):
        fields[kind].append("id")
    assert _operation_protocol_lifecycle_reasons(operation, "job") == []


def test_axi4_lite_campaign_does_not_claim_unimplemented_memory_variants() -> None:
    capabilities = {
        "max_outstanding": 2,
        "read_write_concurrency": True,
        "address_bins": ("zero", "aligned", "page_edge"),
        "write_strobe_bins": "full",
        "protection_bins": ("zero", "nonzero"),
        "write_order_bins": ("address_first", "data_first", "same_cycle"),
    }
    binding = {
        "protocol_profile": "axi4_lite",
        "serialization": {"kind": "scalar", "index_order": []},
        "dimensions": [],
        "memory_mapping": {"protocol_capabilities": capabilities},
    }
    operation = {
        "inputs": [binding],
        "outputs": [binding],
        "lifecycle": {"job_accept_channels": [{"legal_values": [1]}]},
    }
    assert _operation_protocol_lifecycle_reasons(operation, "job") == []

    capabilities["write_strobe_bins"] = ("full", "sparse", "all_zero")
    reasons = _operation_protocol_lifecycle_reasons(operation, "job")
    assert any("write_strobe_bins_not_executable=['all_zero', 'sparse']" in reason for reason in reasons)
    capabilities["write_strobe_bins"] = "full"

    capabilities["address_bins"] = "aligned|unaligned"
    reasons = _operation_protocol_lifecycle_reasons(operation, "job")
    assert any("unaligned_address_not_executable" in reason for reason in reasons)


def test_code_owned_obligations_split_by_operation_and_shared_channel():
    metadata = {
        "schema_version": 2,
        "operations": [
            {
                "operation_name": "good_op",
                "inputs": [{"channel": "shared_chan"}, {"channel": "good_only_chan"}],
                "outputs": [],
            },
            {
                "operation_name": "bad_op",
                "inputs": [{"channel": "shared_chan"}, {"channel": "bad_only_chan"}],
                "outputs": [],
            },
        ],
    }
    obligations = [
        {"id": "op.good", "scope": "operation", "scope_name": "good_op"},
        {"id": "op.bad", "scope": "operation", "scope_name": "bad_op"},
        {"id": "chan.good_only", "scope": "channel", "scope_name": "good_only_chan"},
        {"id": "chan.bad_only", "scope": "channel", "scope_name": "bad_only_chan"},
        {"id": "chan.shared", "scope": "channel", "scope_name": "shared_chan"},
        {"id": "sig.untraceable", "scope": "signal", "scope_name": "some_bare_signal"},
    ]

    owned = code_owned_obligations_for_supported_operations(
        obligations, metadata, {"good_op"}
    )

    assert owned == {"op.good", "chan.good_only"}
    # Explicitly not owned, and why:
    assert "op.bad" not in owned  # its own operation is not supported
    assert "chan.bad_only" not in owned  # only the unsupported operation uses it
    assert "chan.shared" not in owned  # the unsupported operation ALSO uses this channel
    assert "sig.untraceable" not in owned  # cannot be traced to any operation's bindings


def test_code_owned_obligations_covers_command_and_status_channels_and_reset():
    """Regression test: the first implementation only indexed inputs/outputs,
    which wrongly left a fully-supported operation's own command-channel and
    status-signal obligations (and the interface-global reset obligation)
    off the code-owned set -- caught by
    test_lifecycle_automation.py::test_minimal_llm_host_becomes_a_complete_deterministic_tb
    failing on exactly those IDs."""

    metadata = {
        "schema_version": 2,
        "operations": [
            {
                "operation_name": "good_op",
                "inputs": [],
                "outputs": [],
                "lifecycle": {
                    "job_accept_channels": [{"channel": "cmd_chan", "legal_values": [1]}],
                    "status_bindings": {"busy": ["busy"], "completion": ["completion"], "error": []},
                },
            }
        ],
    }
    obligations = [
        {"id": "channel.cmd_chan.handshake_states", "scope": "channel", "scope_name": "cmd_chan"},
        {"id": "signal.busy.busy_behavior", "scope": "signal", "scope_name": "busy"},
        {"id": "signal.completion.completion_behavior", "scope": "signal", "scope_name": "completion"},
        {"id": "signal.rst_n.reset_behavior", "scope": "signal", "scope_name": "rst_n"},
    ]

    owned = code_owned_obligations_for_supported_operations(
        obligations, metadata, {"good_op"}, reset_signal_name="rst_n"
    )

    assert owned == {
        "channel.cmd_chan.handshake_states",
        "signal.busy.busy_behavior",
        "signal.completion.completion_behavior",
        "signal.rst_n.reset_behavior",
    }

    # And reset is owned even with zero supported operations removed from
    # the set, as long as at least one operation is supported elsewhere in
    # the contract -- it is interface-global, not this operation's alone.
    owned_none_of_this_op = code_owned_obligations_for_supported_operations(
        obligations, metadata, set(), reset_signal_name="rst_n"
    )
    assert "signal.rst_n.reset_behavior" not in owned_none_of_this_op


def test_protocol_field_attribution_uses_binding_and_respects_shared_channels():
    metadata = {
        "operations": [
            {"operation_name": "good", "inputs": [{"channel": "shared_ar"}], "outputs": []},
            {"operation_name": "bad", "inputs": [{"channel": "shared_ar"}], "outputs": []},
        ]
    }
    obligations = [{
        "id": "protocol_field.fabric_read_address_prot.axi_lite_protection_partition",
        "scope": "protocol_field",
        "scope_name": "fabric_read_address_prot",
        "bindings": {"channel_name": "shared_ar", "protocol_group": "fabric"},
    }]
    assert code_owned_obligations_for_supported_operations(
        obligations, metadata, {"good"}
    ) == set()
    assert code_owned_obligations_for_supported_operations(
        obligations, metadata, {"good", "bad"}
    ) == {obligations[0]["id"]}


def test_code_owned_obligations_against_a_real_axi4_lite_fixture():
    """Regression test for a real gap the hand-built fixtures above cannot
    catch: a memory-mapped binding's top-level `channel` is only its *data*
    channel (AXI4-Lite's "r"/"w") -- the address channel ("ar"/"aw") and, for
    writes, the response channel ("bresp") only ever appear inside
    `memory_mapping`, never as any binding's own `channel`. The first
    implementation missed all of those, silently under-crediting a fully
    supported single-operation contract instead of the full 36/36. The two
    protocol-field obligations have compound IDs, but their coverage-plan
    bindings identify the actual address channels without name parsing.
    """

    architecture, interface = axi_lite_contracts()
    metadata = build_architect_operation_metadata(architecture, interface)
    interface_plan = build_interface_coverage_plan(interface)
    operation_plan = operation_plan_for_tests([], [], architecture, interface)
    plan = merge_coverage_plans(interface_plan, operation_plan)
    obligations = plan["obligations"]
    required = {str(item["id"]) for item in obligations}

    owned = code_owned_obligations_for_supported_operations(
        obligations, metadata, {"gemm_core"}, reset_signal_name="rst_n"
    )

    missing = required - owned
    assert missing == set(), missing
    assert len(owned) == 36
    assert len(required) == 36


def test_protocol_lifecycle_ready_operations_widens_only_the_channel_scope_obligations():
    """`_run_arithmetic_blocked_operation_smoke` drives real protocol/
    lifecycle traffic for an operation blocked only on arithmetic, so its
    channel/command/status obligations should be creditable even though the
    operation itself is not in `supported_operations` -- but its own
    `scope == "operation"` (arithmetic/lifecycle-policy) obligation must
    not be, since nothing smoke-drove or golden-checked that."""

    metadata = {
        "schema_version": 2,
        "operations": [{
            "operation_name": "blocked_op",
            "inputs": [{"channel": "in_chan"}],
            "outputs": [],
            "lifecycle": {
                "job_accept_channels": [{"channel": "cmd_chan"}],
                "status_bindings": {"busy": ["busy"], "completion": ["completion"], "error": []},
            },
        }],
    }
    obligations = [
        {"id": "op.blocked_op.accumulation", "scope": "operation", "scope_name": "blocked_op"},
        {"id": "channel.in_chan.stall_stability", "scope": "channel", "scope_name": "in_chan"},
        {"id": "channel.cmd_chan.handshake_states", "scope": "channel", "scope_name": "cmd_chan"},
        {"id": "signal.busy.busy_behavior", "scope": "signal", "scope_name": "busy"},
        {"id": "signal.rst.reset_behavior", "scope": "signal", "scope_name": "rst"},
    ]

    without_widening = code_owned_obligations_for_supported_operations(
        obligations, metadata, set(), reset_signal_name="rst",
    )
    assert without_widening == set()

    widened = code_owned_obligations_for_supported_operations(
        obligations, metadata, set(), reset_signal_name="rst",
        protocol_lifecycle_ready_operations={"blocked_op"},
    )
    assert widened == {
        "channel.in_chan.stall_stability",
        "channel.cmd_chan.handshake_states",
        "signal.busy.busy_behavior",
        "signal.rst.reset_behavior",
    }
    # The arithmetic/lifecycle-policy obligation is never widened this way.
    assert "op.blocked_op.accumulation" not in widened
