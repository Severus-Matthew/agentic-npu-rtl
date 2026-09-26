"""Fifteen additional local-only extension compatibility scenarios.

The first scenario matrix proves the normalized request/bundle boundary with
ten representative gaps.  This second matrix deliberately stresses different
axes: dynamic operation metadata, unsupported serialization, catalog families
whose arithmetic is not code-owned yet, four additional protocol profiles,
contract-local role vocabulary, lifecycle replacement/addition, per-operation
isolation, and a mixed multi-domain contract.

These tests do not qualify or promote generated code.  They verify that an
Architect can name an unsupported fragment precisely, that the Verifier can
answer only that fragment, and that supported sibling automation remains
available wherever its own metadata is still executable.
"""

from __future__ import annotations

from copy import deepcopy

from multigent.tests.test_canonical_operation import axi_lite_contracts, contracts
from multigent.tests.test_extension_scenario_matrix import (
    _lifecycle_request,
    _request,
    _round_trip,
)
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_lifecycle_feature_plan,
    build_operation_feature_plan,
    build_protocol_feature_plan,
    interface_vocabulary_extensions,
    validate_architect_extension_requests,
    validate_architecture_operation_features,
    validate_interface_semantics,
    validate_interface_signal_roles,
)


def _freeze_request_behavior(
    request: dict,
    *,
    summary: str,
    trigger: str,
    required: tuple[str, ...],
    end: str,
    forbidden: tuple[str, ...],
    observations: tuple[tuple[str, str], ...],
    parameters: dict | None = None,
) -> None:
    """Replace generic fixture prose with implementable frozen semantics."""

    request["semantics"] = {
        "summary": summary,
        "trigger": trigger,
        "required_behavior": list(required),
        "end_condition": end,
        "forbidden_behavior": list(forbidden),
    }
    request["required_observations"] = [
        {"name": name, "kind": kind, "description": f"Observed {name}."}
        for name, kind in observations
    ]
    request["parameters"] = dict(parameters or {})


def _simple_protocol_interface(
    profile: str,
    *,
    channel_name: str,
    direction: str = "input",
    extra_signals: tuple[dict, ...] = (),
) -> dict:
    """Build a minimal explicit channel without pretending it is executable."""

    opposite = "output" if direction == "input" else "input"
    return {
        "clock": "clk",
        "reset": "rst_n",
        "channels": [
            {
                "name": channel_name,
                "direction": direction,
                "protocol_profile": profile,
                "data_objects": [],
                "ordering": "contract defined",
                "framing": "contract defined",
            }
        ],
        "signals": [
            {
                "name": "clk",
                "role": "clock",
                "direction": "input",
                "channel": None,
            },
            {
                "name": "rst_n",
                "role": "reset",
                "direction": "input",
                "channel": None,
                "semantic": "synchronous active-low reset",
            },
            {
                "name": f"{channel_name}_valid",
                "role": "valid",
                "direction": direction,
                "channel": channel_name,
                "width": "1",
            },
            {
                "name": f"{channel_name}_ready",
                "role": "ready",
                "direction": opposite,
                "channel": channel_name,
                "width": "1",
            },
            {
                "name": f"{channel_name}_data",
                "role": "payload",
                "semantic_class": "data",
                "direction": direction,
                "channel": channel_name,
                "width": "32",
            },
            *deepcopy(list(extra_signals)),
        ],
    }


def _unknown_family_operation(
    family: str,
    features: list[str],
    request_id: str,
) -> tuple[dict, dict, dict]:
    architecture, interface = axi_lite_contracts()
    operation = architecture["operations"][0]
    operation.update(
        {
            "kind": family,
            "coverage_family": family,
            "coverage_family_source": "novel",
            "features": features,
            "feature_extensions": [],
            "semantics": f"Frozen contract semantics for {family}.",
            "arithmetic": {
                "classifier_profile": "llm_extension",
                "reason": f"The code-owned arithmetic pool has no {family} evaluator.",
                "extension_request": request_id,
            },
        }
    )
    request = _request(
        request_id,
        "operation",
        f"{family}_arithmetic",
        {"scope": "operation", "name": "gemm_core"},
        observations=("accepted_inputs", "golden_trace", "observed_output"),
    )
    architecture["verification_extensions"] = [request]
    return architecture, interface, request


def test_case_11_runtime_configurable_gemm_links_only_unsupported_arithmetic() -> None:
    architecture, interface = axi_lite_contracts()
    operation = architecture["operations"][0]
    operation["feature_extensions"].append("runtime_shape")
    architecture["dimensions"][0].update(
        {"minimum": 1, "maximum": 4, "runtime_configurable": True}
    )
    architecture["parameters"][0]["default_value"] = "2"
    request = _request(
        "operation.runtime_shape_arithmetic",
        "operation",
        "runtime_shape_arithmetic",
        {"scope": "operation", "name": "gemm_core"},
        observations=("accepted_inputs", "configuration", "golden_trace"),
        related=("operation.matrix_multiply.runtime_shape",),
    )
    _freeze_request_behavior(
        request,
        summary="Compute signed A[M,2] times B[2,1] for runtime M in {1,2,4}.",
        trigger="A legal job accepting M, A, and B completes its input handshakes.",
        required=("Retire exactly M row results in row order.", "Each result is the exact two-term signed dot product."),
        end="The Mth result is accepted.",
        forbidden=("Retire a result for a row index greater than or equal to M.",),
        observations=(("runtime_m", "configuration"), ("accepted_inputs", "logical_value"), ("observed_output", "logical_value")),
        parameters={"legal_m": "1,2,4", "k": 2, "n": 1},
    )
    operation["arithmetic"] = {
        "classifier_profile": "llm_extension",
        "reason": "Runtime-selected M changes tensor extents per accepted job.",
        "extension_request": request["id"],
    }
    operation["semantics"] = "Signed GEMM with runtime-selected M in the range one through four."
    architecture["verification_extensions"] = [request]

    _round_trip(architecture, interface)
    assert validate_architecture_operation_features(architecture) == []
    metadata = build_architect_operation_metadata(architecture, interface)
    compiled = metadata["operations"][0]
    assert compiled["dimensions"]["M"] == 2
    assert compiled["arithmetic"]["extension_request"] == request["id"]
    assert automatic_campaign_support(metadata, architecture)["operations"]["gemm_core"][
        "protocol_lifecycle_supported"
    ] is True
    concepts = {
        item["bindings"]["concept"]
        for item in build_operation_feature_plan(architecture)["features"]
    }
    assert "runtime_shape" not in concepts  # contract-local extension, not code-owned


def test_case_12_block_sparse_layout_isolated_to_one_data_object() -> None:
    architecture, interface = axi_lite_contracts()
    request = _request(
        "operation.block_sparse_a_layout",
        "operation",
        "block_sparse_a_layout",
        {"scope": "data_object", "name": "A_matrix"},
        observations=("accepted_inputs", "configuration"),
        related=("operation.matrix_multiply.sparsity",),
    )
    a_matrix = next(
        item for item in architecture["data_objects"] if item["name"] == "A_matrix"
    )
    a_matrix["serialization"] = {
        "kind": "llm_extension",
        "index_order": ["M", "K"],
        "description": "Block-sparse values and indices use the frozen contract layout.",
        "extension_request": request["id"],
    }
    architecture["operations"][0]["feature_extensions"].append("sparsity")
    _freeze_request_behavior(
        request,
        summary="Deserialize exactly two signed sparse entries as (index,value) pairs and compute their dot product with dense B.",
        trigger="Two index/value pairs and the dense operand are accepted.",
        required=("Each sparse value multiplies B at its accepted index.", "The two products are added exactly once."),
        end="One signed result is accepted.",
        forbidden=("Interpret sparse indices as dense transfer order.",),
        observations=(("accepted_indices", "logical_value"), ("accepted_values", "logical_value"), ("observed_output", "logical_value")),
        parameters={"stored_entries": 2, "dense_length": 4},
    )
    architecture["verification_extensions"] = [request]

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    compiled_a = next(
        item
        for item in metadata["operations"][0]["inputs"]
        if item["data_object"] == "A_matrix"
    )
    assert compiled_a["serialization"]["extension_request"] == request["id"]
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["gemm_core"]["protocol_lifecycle_supported"] is False
    assert any("serialization is not supported" in reason for reason in support["reasons"])


def test_case_13_convolution_novel_family_uses_only_its_extension() -> None:
    features = [
        "tensor_shapes",
        "kernel",
        "stride_dilation",
        "padding",
        "channel_grouping",
        "numeric_values",
    ]
    architecture, interface, _ = _unknown_family_operation(
        "convolution", features, "operation.convolution_arithmetic"
    )
    request = architecture["verification_extensions"][0]
    architecture["operations"][0]["semantics"] = "One signed three-tap valid convolution output equals sum(x[i]*k[i]) for i=0..2."
    _freeze_request_behavior(
        request,
        summary="Compute one exact signed three-tap convolution output.",
        trigger="Three samples and three kernel coefficients are accepted.",
        required=("Multiply corresponding sample and kernel entries.", "Accumulate all three products in signed integer arithmetic."),
        end="One convolution result retires.",
        forbidden=("Drop or duplicate a tap.",),
        observations=(("accepted_samples", "logical_value"), ("accepted_kernel", "logical_value"), ("observed_output", "logical_value")),
        parameters={"tap_count": 3},
    )

    _round_trip(architecture, interface)
    assert validate_architecture_operation_features(architecture) == []
    plan = build_operation_feature_plan(architecture)
    assert plan["features"] == []
    metadata = build_architect_operation_metadata(architecture, interface)
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["gemm_core"]["arithmetic_reasons"]
    assert support["operations"]["gemm_core"]["protocol_lifecycle_supported"] is True


def test_case_14_sparse_attention_novel_family_uses_only_its_extension() -> None:
    features = [
        "sequence_length",
        "head_count",
        "mask",
        "scaling",
        "numeric_extremes",
    ]
    architecture, interface, request = _unknown_family_operation(
        "attention", features, "operation.sparse_attention_arithmetic"
    )
    architecture["operations"][0]["semantics"] = (
        "Two-token signed integer linear attention: score_i=q*k_i; masked or "
        "negative scores have weight zero; other weights equal score_i; output is "
        "sum(weight_i*v_i) divided by sum(weight_i), with zero when all weights are zero."
    )
    _freeze_request_behavior(
        request,
        summary="Compute the frozen two-token sparse linear-attention result.",
        trigger="One complete q, k[2], v[2], and mask[2] transaction is accepted.",
        required=(
            "Masked or negative-score tokens contribute zero weight.",
            "The observed output equals the declared weighted integer result.",
        ),
        end="Exactly one result for the accepted two-token transaction retires.",
        forbidden=("A masked token contributes to the retired result.",),
        observations=(("accepted_qkv", "logical_value"), ("accepted_mask", "logical_value"), ("observed_output", "logical_value")),
        parameters={"tokens": 2, "negative_score_weight": 0},
    )

    _round_trip(architecture, interface)
    assert validate_architecture_operation_features(architecture) == []
    plan = build_operation_feature_plan(architecture)
    assert plan["features"] == []
    metadata = build_architect_operation_metadata(architecture, interface)
    assert build_lifecycle_feature_plan(interface, metadata)["coverage_obligations"]


def test_case_15_wishbone_timeout_is_a_local_protocol_fragment() -> None:
    interface = _simple_protocol_interface("custom", channel_name="wb_req")
    request = _request(
        "protocol.wishbone_ack_timeout",
        "protocol",
        "wishbone_ack_timeout",
        {"scope": "channel", "name": "wb_req"},
        observations=("request", "acknowledge", "elapsed_cycles"),
        related=(),
    )
    _freeze_request_behavior(
        request,
        summary="A Wishbone Classic request receives ACK within six sampled cycles while CYC, STB, address, and data remain stable.",
        trigger="CYC and STB are sampled high for a new request.",
        required=("ACK is sampled within six cycles.", "The initiator holds request content stable until ACK."),
        end="ACK is sampled high or the sixth cycle expires.",
        forbidden=("ACK is absent for seven cycles.", "Request content changes before ACK."),
        observations=(("request", "transaction"), ("acknowledge", "signal"), ("elapsed_cycles", "event")),
        parameters={"maximum_cycles": 6},
    )
    architecture = {"operations": [], "verification_extensions": [request]}

    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []
    _round_trip(architecture, interface)


def test_case_16_tilelink_source_reordering_is_a_local_protocol_fragment() -> None:
    channel = "tl_a"
    interface = _simple_protocol_interface(
        "custom",
        channel_name=channel,
        extra_signals=(
            {
                "name": "tl_a_source",
                "role": "transaction_id",
                "semantic_class": "identifier",
                "direction": "input",
                "channel": channel,
                "width": "4",
            },
        ),
    )
    request = _request(
        "protocol.tilelink_source_reordering",
        "protocol",
        "tilelink_source_reordering",
        {"scope": "channel", "name": channel},
        observations=("source_id", "request", "response"),
        related=(),
    )
    _freeze_request_behavior(
        request,
        summary="Two TileLink A requests may receive D responses in reverse order, but every response preserves its source ID and data association.",
        trigger="Two A-channel requests with different source IDs are accepted.",
        required=("Return the response for source 9 before source 2 in this directed scenario.", "Preserve each source-to-data association."),
        end="Both D-channel responses are accepted.",
        forbidden=("A D response uses the other request's source ID or data.",),
        observations=(("source_id", "signal"), ("request", "transaction"), ("response", "transaction")),
        parameters={"request_sources": "2,9", "response_order": "9,2"},
    )
    architecture = {"operations": [], "verification_extensions": [request]}

    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []
    _round_trip(architecture, interface)


def test_case_17_avalon_mm_burst_wait_response_is_a_local_fragment() -> None:
    channel = "avmm_req"
    interface = _simple_protocol_interface(
        "custom",
        channel_name=channel,
        extra_signals=(
            {
                "name": "avmm_burstcount",
                "role": "metadata",
                "semantic_class": "length",
                "direction": "input",
                "channel": channel,
                "width": "8",
            },
        ),
    )
    request = _request(
        "protocol.avalon_mm_burst_wait_response",
        "protocol",
        "avalon_mm_burst_wait_response",
        {"scope": "channel", "name": channel},
        observations=("burst_length", "wait_state", "response"),
        related=(),
    )
    _freeze_request_behavior(
        request,
        summary="An accepted Avalon-MM read burst of length eight returns exactly eight ordered response beats after a finite wait.",
        trigger="READ is accepted with BURSTCOUNT equal to eight.",
        required=("Assert READDATAVALID exactly eight times.", "Return beat i as base_address+i with an OK response."),
        end="The eighth response beat is sampled.",
        forbidden=("Return fewer, extra, duplicated, or reordered beats.",),
        observations=(("burst_length", "signal"), ("wait_state", "signal"), ("response", "transaction")),
        parameters={"burstcount": 8},
    )
    architecture = {"operations": [], "verification_extensions": [request]}

    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []
    _round_trip(architecture, interface)


def test_case_18_avalon_stream_empty_symbol_framing_is_a_local_fragment() -> None:
    channel = "avst_packet"
    interface = _simple_protocol_interface(
        "custom",
        channel_name=channel,
        extra_signals=(
            {
                "name": "avst_endofpacket",
                "role": "last",
                "semantic_class": "framing",
                "direction": "input",
                "channel": channel,
                "width": "1",
            },
            {
                "name": "avst_empty",
                "role": "metadata",
                "semantic_class": "length",
                "direction": "input",
                "channel": channel,
                "width": "3",
            },
        ),
    )
    request = _request(
        "protocol.avalon_st_empty_symbols",
        "protocol",
        "avalon_st_empty_symbols",
        {"scope": "channel", "name": channel},
        observations=("packet_end", "empty_symbols", "payload"),
        related=(),
    )
    _freeze_request_behavior(
        request,
        summary="An Avalon-ST final beat with EMPTY=3 preserves DATA, SOP, EOP, and EMPTY while the receiver is stalled.",
        trigger="A final partial beat is accepted from the input side while output READY is low.",
        required=("Hold output VALID and all content stable for three stalled cycles.", "Transfer the same final beat after READY rises."),
        end="The stalled final beat is accepted at the output.",
        forbidden=("Change EMPTY or EOP during the stall.",),
        observations=(("packet_end", "signal"), ("empty_symbols", "signal"), ("payload", "signal")),
        parameters={"empty_symbols": 3, "stall_cycles": 3},
    )
    architecture = {"operations": [], "verification_extensions": [request]}

    assert validate_interface_signal_roles(interface) == []
    assert validate_interface_semantics(interface) == []
    _round_trip(architecture, interface)


def test_case_19_four_phase_ack_adds_one_contract_local_role() -> None:
    channel = "four_phase_req"
    interface = _simple_protocol_interface(
        "custom",
        channel_name=channel,
        extra_signals=(
            {
                "name": "req_ack_toggle",
                "role": "ack_toggle",
                "direction": "output",
                "channel": channel,
                "width": "1",
            },
        ),
    )
    request = _request(
        "protocol.four_phase_ack_toggle",
        "protocol",
        "four_phase_ack_toggle",
        {"scope": "signal", "name": "req_ack_toggle"},
        observations=("request", "ack_toggle", "payload"),
        vocabulary={
            "pool": "signal_role",
            "name": "ack_toggle",
            "definition": {
                "description": "Consumer acknowledgement phase for a four-phase transfer.",
                "coverage_tags": ["ack_phase", "recovery"],
                "category": "channel_handshake",
                "channel_binding": "required",
                "direction_relation": "opposite_to_channel",
                "allowed_directions": ["input", "output"],
                "semantic_class_binding": "forbidden",
            },
        },
    )
    _freeze_request_behavior(
        request,
        summary="A four-phase transfer follows request-low/ack-low, request-high/ack-high, then request-low/ack-low.",
        trigger="The requester raises request from the idle phase.",
        required=("Acknowledgement rises only after request rises.", "Acknowledgement returns low after request returns low."),
        end="Both request and acknowledgement return low.",
        forbidden=("Acknowledge remains low during the request phase or high after request clears.",),
        observations=(("request", "signal"), ("ack_toggle", "signal"), ("payload", "logical_value")),
    )
    architecture = {"operations": [], "verification_extensions": [request]}
    role_extensions, semantic_extensions = interface_vocabulary_extensions(architecture)

    assert validate_interface_signal_roles(
        interface, role_extensions=role_extensions
    ) == []
    assert validate_interface_semantics(
        interface,
        role_extensions=role_extensions,
        semantic_class_extensions=semantic_extensions,
    ) == []
    _round_trip(architecture, interface)


def test_case_20_cancel_then_drain_is_additive_lifecycle_behavior() -> None:
    architecture, interface = axi_lite_contracts()
    interface["signals"].append(
        {
            "name": "cancel",
            "role": "cancel",
            "direction": "input",
            "channel": None,
            "width": "1",
        }
    )
    request = _request(
        "lifecycle.cancel_then_drain",
        "lifecycle",
        "cancel_then_drain",
        {"scope": "operation", "name": "gemm_core"},
        observations=("cancel", "lifecycle_event", "observed_output"),
        related=("lifecycle.reset_behavior",),
    )
    _freeze_request_behavior(
        request,
        summary="Canceling an active job drains for two cycles, then clears busy without completion.",
        trigger="CANCEL is sampled while BUSY is high.",
        required=("BUSY remains high for exactly two drain cycles.", "BUSY then clears without a completion event."),
        end="The canceled job becomes inactive.",
        forbidden=("Completion is asserted for the canceled job.",),
        observations=(("cancel", "signal"), ("lifecycle_event", "event"), ("observed_output", "transaction")),
        parameters={"drain_cycles": 2},
    )
    architecture["verification_extensions"] = [request]
    baseline_architecture, baseline_interface = axi_lite_contracts()

    assert validate_interface_signal_roles(interface) == []
    _round_trip(architecture, interface)
    plan = build_lifecycle_feature_plan(
        interface, build_architect_operation_metadata(architecture, interface)
    )
    baseline = build_lifecycle_feature_plan(
        baseline_interface,
        build_architect_operation_metadata(baseline_architecture, baseline_interface),
    )
    assert {item["kind"] for item in plan["features"] if item["scope"] == "operation"} == {
        item["kind"]
        for item in baseline["features"]
        if item["scope"] == "operation"
    }


def test_case_21_sticky_completion_replaces_only_completion_style() -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_request("completion_style", "sticky_completion_until_ack")
    _freeze_request_behavior(
        request,
        summary="Completion remains high after retirement until software acknowledgement.",
        trigger="The final output of a legal job retires.",
        required=("Assert completion after retirement.", "Keep completion high until software_ack is sampled."),
        end="software_ack is sampled and completion clears.",
        forbidden=("Completion clears before software_ack.",),
        observations=(("completion", "signal"), ("software_ack", "signal"), ("retirement", "event")),
    )
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["completion_style"] = {
        "extension_request": request["id"]
    }

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    kinds = {
        item["kind"]
        for item in build_lifecycle_feature_plan(interface, metadata)["features"]
    }
    assert "completion_matches_final_output" not in kinds
    assert "busy_tracks_active_job" in kinds
    assert "illegal_command_errors_without_start" in kinds
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["gemm_core"]["protocol_lifecycle_supported"] is False


def test_case_22_two_deep_job_queue_replaces_only_overlap_policy() -> None:
    architecture, interface = axi_lite_contracts()
    request = _lifecycle_request("job_overlap", "two_deep_job_queue")
    _freeze_request_behavior(
        request,
        summary="Accept one active and one queued legal job and retire both in acceptance order.",
        trigger="A second legal command is presented while one job is active.",
        required=("Accept the second job when the queue is empty.", "Produce exactly two completion events in order."),
        end="The queued job retires.",
        forbidden=("Accept a third in-flight job or lose either accepted job.",),
        observations=(("accepted_jobs", "event"), ("completion", "signal"), ("busy", "signal")),
        parameters={"maximum_inflight": 2},
    )
    architecture["verification_extensions"] = [request]
    architecture["operations"][0]["lifecycle_policy"]["job_overlap"] = {
        "extension_request": request["id"]
    }

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    kinds = {
        item["kind"]
        for item in build_lifecycle_feature_plan(interface, metadata)["features"]
    }
    assert "legal_command_starts_one_job" not in kinds
    assert "busy_tracks_active_job" in kinds
    assert "completion_matches_final_output" in kinds
    support = automatic_campaign_support(metadata, architecture)
    assert support["operations"]["gemm_core"]["protocol_lifecycle_supported"] is True


def test_case_23_error_and_reset_extensions_remove_only_dependent_checks() -> None:
    architecture, interface = axi_lite_contracts()
    error_request = _lifecycle_request("error_style", "error_until_software_clear")
    reset_request = _lifecycle_request("reset_behavior", "checkpoint_and_resume")
    _freeze_request_behavior(
        error_request,
        summary="Error remains asserted after an illegal command until software acknowledgement.",
        trigger="An illegal command is accepted.",
        required=("Assert error and hold it high until software_ack.",),
        end="software_ack clears error.",
        forbidden=("Error self-clears before software_ack.",),
        observations=(("error", "signal"), ("software_ack", "signal")),
    )
    _freeze_request_behavior(
        reset_request,
        summary="Checkpoint reset preserves an active job and resumes it after reset release.",
        trigger="Reset is asserted while busy is high and checkpoint mode is enabled.",
        required=("Preserve active-job state throughout reset.", "Resume the preserved countdown after release."),
        end="The resumed job retires or is explicitly canceled.",
        forbidden=("Reset silently aborts the checkpointed job.",),
        observations=(("reset", "signal"), ("busy", "signal"), ("retirement", "event")),
    )
    architecture["verification_extensions"] = [error_request, reset_request]
    policy = architecture["operations"][0]["lifecycle_policy"]
    policy["error_style"] = {"extension_request": error_request["id"]}
    policy["reset_behavior"] = {"extension_request": reset_request["id"]}

    _round_trip(architecture, interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    plan = build_lifecycle_feature_plan(interface, metadata)
    kinds = {item["kind"] for item in plan["features"]}
    assert "illegal_command_errors_without_start" not in kinds
    assert "reset_aborts_pending_job" not in kinds
    assert "busy_tracks_active_job" in kinds
    assert "completion_matches_final_output" in kinds
    coverage_ids = {item["id"] for item in plan["coverage_obligations"]}
    assert "operation.gemm_core.reset_abort_phase" not in coverage_ids
    assert "operation.gemm_core.post_reset_purity" not in coverage_ids


def test_case_24_unknown_attention_does_not_disable_known_gemm_sibling() -> None:
    architecture, interface = axi_lite_contracts()
    known = architecture["operations"][0]
    unknown = deepcopy(known)
    unknown.update(
        {
            "name": "attention_core",
            "kind": "attention",
            "coverage_family": "attention",
            "coverage_family_source": "novel",
            "features": [
                "sequence_length",
                "head_count",
                "mask",
                "scaling",
                "numeric_extremes",
            ],
            "feature_extensions": [],
            "semantics": "Sparse multi-head attention over the accepted logical tensors.",
            "arithmetic": {
                "classifier_profile": "llm_extension",
                "reason": "Attention arithmetic is not code-owned.",
                "extension_request": "operation.attention_core_arithmetic",
            },
        }
    )
    architecture["operations"].append(unknown)
    request = _request(
        "operation.attention_core_arithmetic",
        "operation",
        "attention_core_arithmetic",
        {"scope": "operation", "name": "attention_core"},
        observations=("accepted_inputs", "golden_trace", "observed_output"),
    )
    _freeze_request_behavior(
        request,
        summary="The attention sibling computes the same two-token sparse linear-attention equation used by case 14 without changing the known GEMM sibling.",
        trigger="An attention or GEMM job is accepted for its exact operation target.",
        required=("Use the extension oracle only for attention.", "Keep the code-owned GEMM result comparison active."),
        end="The selected operation's result retires.",
        forbidden=("The attention extension replaces or disables the GEMM oracle.",),
        observations=(("accepted_inputs", "logical_value"), ("golden_trace", "golden_trace"), ("observed_output", "logical_value")),
    )
    architecture["verification_extensions"] = [request]

    _round_trip(architecture, interface)
    assert validate_architecture_operation_features(architecture) == []
    metadata = build_architect_operation_metadata(architecture, interface)
    assert {item["operation_name"] for item in metadata["operations"]} == {
        "gemm_core",
        "attention_core",
    }
    support = automatic_campaign_support(metadata, architecture)
    assert support["supported"] is False
    assert support["any_operation_supported"] is True
    assert support["operations"]["gemm_core"]["supported"] is True
    assert support["operations"]["attention_core"]["supported"] is False
    assert support["operations"]["attention_core"]["protocol_lifecycle_supported"] is True


def test_case_25_large_mixed_contract_preserves_exact_fragment_ownership() -> None:
    architecture, interface = axi_lite_contracts()
    operation = architecture["operations"][0]
    arithmetic_request = _request(
        "operation.learned_rounding",
        "operation",
        "learned_rounding",
        {"scope": "operation", "name": "gemm_core"},
        observations=("accepted_inputs", "golden_trace", "observed_output"),
        related=("operation.matrix_multiply.rounding_mode",),
    )
    _freeze_request_behavior(
        arithmetic_request,
        summary="Round signed GEMM+bias by adding 2^(shift-1) and arithmetic-shifting right by shift.",
        trigger="A job with operands, bias, and round_shift is accepted.",
        required=("Compute GEMM+bias before rounding.", "Use the accepted shift for the rounding offset and right shift."),
        end="The rounded result retires.",
        forbidden=("Apply rounding before accumulation or use planned rather than accepted shift.",),
        observations=(("accepted_inputs", "logical_value"), ("golden_trace", "golden_trace"), ("observed_output", "logical_value")),
        parameters={"shift": 2},
    )
    operation["arithmetic"] = {
        "classifier_profile": "llm_extension",
        "reason": "Learned rounding is outside the closed formula grammar.",
        "extension_request": arithmetic_request["id"],
    }
    operation["semantics"] = "Signed GEMM followed by a frozen learned rounding function."
    operation["feature_extensions"].append("rounding_mode")

    protocol_request = _request(
        "protocol.axi_epoch_retry",
        "protocol",
        "axi_epoch_retry",
        {"scope": "protocol_group", "name": "mem"},
        observations=("response_code", "transaction_epoch"),
        related=("axi_lite_response_code",),
    )
    _freeze_request_behavior(
        protocol_request,
        summary="A retry response may cause one repeat request; the second response must complete and retain the same transaction epoch.",
        trigger="The first response for an epoch-tagged request reports retry.",
        required=("Repeat the request at most once.", "Preserve the epoch on retry and successful response."),
        end="The repeated request receives a successful response.",
        forbidden=("Issue more than one retry or change epoch across attempts.",),
        observations=(("response_code", "signal"), ("transaction_epoch", "signal")),
        parameters={"retry_budget": 1},
    )
    vocabulary_request = _request(
        "protocol.transaction_epoch_semantic",
        "protocol",
        "transaction_epoch_semantic",
        {"scope": "signal", "name": "cmd_epoch"},
        observations=("transaction_epoch",),
        vocabulary={
            "pool": "semantic_class",
            "name": "transaction_epoch",
            "definition": {
                "description": "Generation of command state used to partition retries.",
                "coverage_tags": ["epoch_partition", "recovery"],
                "allowed_roles": ["metadata"],
            },
        },
    )
    _freeze_request_behavior(
        vocabulary_request,
        summary="transaction_epoch partitions command and retry evidence by the accepted four-bit epoch value.",
        trigger="An epoch-tagged command or retry transfer is accepted.",
        required=("Associate every response with the exact accepted epoch.",),
        end="The response carrying that epoch is accepted.",
        forbidden=("Correlate a response to a different epoch.",),
        observations=(("transaction_epoch", "signal"),),
        parameters={"width_bits": 4},
    )
    interface["signals"].append(
        {
            "name": "cmd_epoch",
            "role": "metadata",
            "semantic_class": "transaction_epoch",
            "direction": "input",
            "channel": "cmd",
            "width": "4",
        }
    )
    lifecycle_request = _lifecycle_request(
        "completion_style", "completion_level_until_ack"
    )
    _freeze_request_behavior(
        lifecycle_request,
        summary="Completion remains high after the mixed job retires until software acknowledgement.",
        trigger="The mixed job's final result retires.",
        required=("Hold completion high until software_ack.",),
        end="software_ack clears completion.",
        forbidden=("Completion self-clears before acknowledgement.",),
        observations=(("completion", "signal"), ("software_ack", "signal")),
    )
    operation["lifecycle_policy"]["completion_style"] = {
        "extension_request": lifecycle_request["id"]
    }
    architecture["verification_extensions"] = [
        arithmetic_request,
        protocol_request,
        vocabulary_request,
        lifecycle_request,
    ]
    role_extensions, semantic_extensions = interface_vocabulary_extensions(architecture)

    assert validate_interface_signal_roles(
        interface, role_extensions=role_extensions
    ) == []
    assert validate_interface_semantics(
        interface,
        role_extensions=role_extensions,
        semantic_class_extensions=semantic_extensions,
    ) == []
    manifest = _round_trip(architecture, interface)
    assert len(manifest["entries"]) == 4
    assert {item["request"]["id"] for item in manifest["entries"]} == {
        request["id"] for request in architecture["verification_extensions"]
    }
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["operations"][0]["arithmetic"]["extension_request"] == arithmetic_request["id"]
    lifecycle_kinds = {
        item["kind"]
        for item in build_lifecycle_feature_plan(interface, metadata)["features"]
    }
    assert "completion_matches_final_output" not in lifecycle_kinds
    assert build_protocol_feature_plan(interface)["features"]
    assert validate_architect_extension_requests(architecture, interface) == []
