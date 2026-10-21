"""Materialize source-backed contract candidates for the 30 external cases.

The builder intentionally does not call these files frozen.  A contract becomes
frozen only after its source facts and deterministic preflight have been audited.
Every candidate records the exact pinned source and keeps unsupported behavior as
an explicit ``verification_extensions`` request instead of pretending it is in a
built-in pool.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Mapping

import yaml


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "benchmark_manifest.json"
SOURCE_ROOT = HERE / ".cache" / "sources"
CASES_ROOT = HERE / "cases"


def _safe(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _top_name(case: Mapping[str, Any]) -> str:
    target = Path(str(case["source_target"]))
    if _source_path(case).is_file():
        return target.stem
    request = {
        "L01": "otbn",
        "L02": "dma",
        "L03": "aes",
        "L04": "hmac",
        "L05": "kmac",
        "L06": "csrng",
        "L07": "flash_ctrl",
        "L08": "keymgr_dpe",
        "L09": "entropy_src",
        "L10": "rom_ctrl",
    }[str(case["id"])]


def _source_path(case: Mapping[str, Any]) -> Path:
    return SOURCE_ROOT / str(case["source"]) / str(case["source_target"])


def _extension(case: Mapping[str, Any], feature: str) -> dict[str, Any]:
    domain = str(case["domain"])
    case_id = str(case["id"]).lower()
    feature_id = _safe(feature)
    if domain == "protocol":
        target = {"scope": "interface", "name": "interface"}
        observations = [
            {
                "name": "transaction_trace",
                "kind": "transaction",
                "description": "Accepted request and response events at the real RTL boundary.",
            },
            {
                "name": "cycle_trace",
                "kind": "event",
                "description": "Cycle-ordered protocol state and handshake evidence.",
            },
        ]
    else:
        target = {"scope": "operation", "name": _safe(case["title"])}
        observations = [
            {
                "name": "accepted_inputs",
                "kind": "transaction",
                "description": "Inputs actually accepted by the pinned RTL.",
            },
            {
                "name": "observed_outputs",
                "kind": "transaction",
                "description": "Outputs actually retired by the pinned RTL.",
            },
        ]
        if domain == "lifecycle":
            observations.append(
                {
                    "name": "lifecycle_trace",
                    "kind": "event",
                    "description": "Cycle-ordered command, status, completion, reset, and error evidence.",
                }
            )
        else:
            observations.append(
                {
                    "name": "golden_trace",
                    "kind": "golden_trace",
                    "description": "Intermediate values required to classify operation coverage.",
                }
            )
    request = {
        "id": f"{domain}.{case_id}_{feature_id}",
        "domain": domain,
        "feature_name": feature_id,
        "target": target,
        "semantics": {
            "summary": f"Verify {feature.replace('_', ' ')} exactly as implemented by the pinned upstream design.",
            "trigger": "A legal source-level transaction or job begins.",
            "required_behavior": [
                f"Observe and check the externally visible {feature.replace('_', ' ')} behavior.",
                "Preserve every reusable built-in protocol, lifecycle, and operation check that applies.",
            ],
            "end_condition": "The corresponding response, retirement, or terminal state is observed.",
            "forbidden_behavior": [
                "Credit the feature without observing the required RTL boundary evidence.",
                "Replace an unsupported behavior with an inferred built-in behavior.",
            ],
        },
        "reason": f"{feature} is intentionally absent from the current verifier_tool pools.",
        "required_observations": observations,
        "related_builtin_features": list(map(str, case.get("reused_baseline", []))),
    }
    if str(case["id"]) == "P01" and feature == "wishbone_axi_translation_residuals":
        request["target"] = {"scope": "protocol_group", "name": "wishbone"}
        request["semantics"] = {
            "summary": "Residual cross-protocol data mapping and abort-edge behavior not represented by the reusable Wishbone event model.",
            "trigger": "After the tool-owned protocol_semantics model accepts or completes a Wishbone transaction.",
            "required_behavior": [
                "Select the correct saved 32-bit lane from each matching 128-bit AXI read response and expose it with Wishbone ACK.",
                "Translate Wishbone word addresses to AXI byte addresses, use fixed read/write IDs, and preserve same-direction response association.",
                "Suppress stale source-visible data or completion credit after reset or cycle cancellation.",
            ],
            "end_condition": "The cross-protocol mapping is observed, or cancellation/reset flushes abandoned work without stale source-visible credit.",
            "forbidden_behavior": [
                "Return the wrong read lane or use an incorrect translated address or fixed ID.",
                "Expose a stale response after reset or cycle-cancellation flush.",
            ],
        }
        request["parameters"] = {
            "read_lane_width": 32,
        }
    elif str(case["id"]) == "P02" and feature == "wishbone_outstanding_cdc":
        request["semantics"] = {
            "summary": "Ordered pipelined-Wishbone clock-domain crossing implemented by wbxclk at the pinned revision.",
            "trigger": "On a rising i_wb_clk edge, accept exactly when i_wb_cyc && i_wb_stb && !o_wb_stall.",
            "required_behavior": [
                "While i_wb_cyc && i_wb_stb && o_wb_stall, the source holds i_wb_stb, i_wb_we, i_wb_addr, i_wb_data, and i_wb_sel stable.",
                "Accepted source requests enter the asynchronous request FIFO in order. In the destination domain, o_xclk_stb and its WE/address/data/select payload remain stable while i_xclk_stall is high; a destination request is accepted exactly when o_xclk_cyc && o_xclk_stb && !i_xclk_stall.",
                "Each destination i_xclk_ack or i_xclk_err observed while o_xclk_cyc is active enters the asynchronous return FIFO in order. The source emits the corresponding registered o_wb_ack or o_wb_err only while i_wb_cyc remains active, with o_wb_data equal to the matching returned data.",
                "o_wb_ack and o_wb_err are mutually exclusive, responses never exceed accepted requests, and response order equals source acceptance order.",
                "At default LGFIFO=5, at most 32 source requests may be outstanding. o_wb_stall is asserted when the outstanding-response capacity or request FIFO is full, or while an abort flush is active.",
                "The two clocks may have unrelated rates and phase. A request or response receives credit only on the appropriate domain clock edge, never merely because an asynchronously observed level changed.",
            ],
            "end_condition": "Every non-aborted accepted source request retires once as o_wb_ack or o_wb_err in original order.",
            "forbidden_behavior": [
                "Accept a source request while o_wb_stall is high or change a destination request while stalled.",
                "Duplicate, lose, or reorder a non-aborted request or response across the clock domains.",
                "Assert source ACK and ERR together or expose a return after its source cycle was aborted.",
            ],
        }
        request["parameters"] = {
            "default_lgfifo": 5,
            "maximum_outstanding": 32,
            "source_acceptance": "i_wb_cyc && i_wb_stb && !o_wb_stall",
            "destination_acceptance": "o_xclk_cyc && o_xclk_stb && !i_xclk_stall",
            "destination_response": "o_xclk_cyc && (i_xclk_ack || i_xclk_err)",
        }
    elif str(case["id"]) == "P02" and feature == "wishbone_cycle_cancellation":
        request["semantics"] = {
            "summary": "Wishbone cycle release and outstanding-work abort semantics implemented by wbxclk.",
            "trigger": "After at least one accepted request, i_wb_cyc is deasserted, or a destination error terminates the active cycle.",
            "required_behavior": [
                "When an otherwise completed source cycle drops i_wb_cyc, a FIFO marker with request-strobe zero eventually drops o_xclk_cyc in the destination domain without creating a transaction response.",
                "If i_wb_cyc drops while accepted responses remain outstanding, or if o_wb_err is emitted, bus_abort asynchronously resets both FIFO paths and propagates a reset into the destination domain.",
                "During abort, o_wb_stall is asserted. o_wb_ack and o_wb_err are forced low when reset, abort, inactive i_wb_cyc, or an empty return FIFO applies.",
                "After the abort/reset pipelines settle, a new source cycle starts with no response, request, or data credit inherited from the cancelled cycle.",
                "A destination i_xclk_err drops o_xclk_cyc, prevents further destination strobes for that cycle, and returns exactly one ordered source error before the flush suppresses stale work.",
            ],
            "end_condition": "Both domains have left the cancelled cycle and a subsequent legal request can be accepted without stale activity.",
            "forbidden_behavior": [
                "Return ACK, ERR, or read-data credit from cancelled work into a later source cycle.",
                "Leave o_xclk_cyc asserted indefinitely after a propagated cycle-release marker, abort, reset, or destination error.",
            ],
        }
        request["parameters"] = {
            "abort_sources": "i_reset|i_wb_cyc_drop_with_outstanding|o_wb_err",
            "request_fifo_cycle_release_marker": "req_stb=0",
            "synchronizer_stages": 2,
        }
    elif str(case["id"]) == "P03" and feature == "apb_setup_access_phases":
        request["semantics"] = {
            "summary": "Single-inflight APB request crossing from S_APB_PCLK to M_APB_PCLK with a returned completion pulse.",
            "trigger": "Capture one source APB setup phase when S_APB_PSEL && !S_APB_PENABLE on a rising S_APB_PCLK edge.",
            "required_behavior": [
                "A captured source setup is transferred only after the reset round trip has completed and no prior response acknowledgement remains active.",
                "The destination presents one APB setup phase with M_APB_PSEL=1 and M_APB_PENABLE=0, followed by an access phase with both high.",
                "During destination wait states, M_APB_PSEL, M_APB_PENABLE, address, write direction, write data, byte strobes, and protection remain stable until M_APB_PREADY is sampled high.",
                "Exactly one destination access completion returns as a one-S_APB_PCLK-cycle S_APB_PREADY pulse; no second request begins until the prior acknowledgement has crossed back and cleared.",
                "For default OPT_REGISTERED=0, ancillary request values are direct source-domain values and therefore rely on the APB source holding them stable for the complete source transfer. OPT_REGISTERED=1 instead captures those values before crossing.",
            ],
            "end_condition": "The source observes exactly one S_APB_PREADY completion for the captured setup and the internal request/acknowledgement handshake returns idle.",
            "forbidden_behavior": [
                "Enter destination access without a preceding destination setup phase.",
                "Change destination request content during a wait state, accept overlapping source requests, or emit duplicate source completions.",
            ],
        }
        request["parameters"] = {
            "maximum_inflight": 1,
            "source_setup": "S_APB_PSEL && !S_APB_PENABLE",
            "destination_completion": "M_APB_PSEL && M_APB_PENABLE && M_APB_PREADY",
            "default_opt_registered": 0,
        }
    elif str(case["id"]) == "P03" and feature == "apb_wait_state_and_error":
        request["semantics"] = {
            "summary": "APB wait-state stability and read/error response preservation across the clock domains.",
            "trigger": "The destination APB request enters its access phase.",
            "required_behavior": [
                "If M_APB_PREADY is low, the destination remains in the same APB access phase and all producer-owned request content remains stable.",
                "When M_APB_PREADY is sampled high, M_APB_PRDATA and M_APB_PSLVERR from that same destination completion are captured and associated with the sole in-flight request.",
                "The matching S_APB_PRDATA is presented with the source completion. S_APB_PSLVERR equals the captured destination error only for that completion and is not reused by a later transfer.",
                "Read data, error, and ready are never credited before a completed destination access or more than once for one source setup.",
            ],
            "end_condition": "The captured destination response has been returned once at the source APB boundary.",
            "forbidden_behavior": [
                "Treat M_APB_PREADY outside the destination access phase as a completion.",
                "Lose, duplicate, or associate PRDATA/PSLVERR with a different source request.",
            ],
        }
        request["parameters"] = {
            "wait_state": "M_APB_PSEL && M_APB_PENABLE && !M_APB_PREADY",
            "response_capture": "M_APB_PSEL && M_APB_PENABLE && M_APB_PREADY",
        }
    elif str(case["id"]) == "P03" and feature == "apb_cdc":
        request["semantics"] = {
            "summary": "Two-toggle-style APB request/acknowledgement CDC and bidirectional reset synchronization in apbxclk.",
            "trigger": "S_PRESETn is released or a source setup toggles the request state.",
            "required_behavior": [
                "Asserting S_PRESETn low asynchronously drives M_PRESETn low and clears request, acknowledgement, PSEL, PENABLE, PREADY, and error state.",
                "Deassertion is synchronized: M_PRESETn rises only after two M_APB_PCLK sampling stages, and source-side full_reset rises only after M_PRESETn has crossed back through two S_APB_PCLK stages.",
                "No source request is forwarded before full_reset is established. Each request and acknowledgement passes through the declared two-stage receiving-domain pipelines and is counted only on receiving clock edges.",
                "Arbitrary positive source/destination clock ratios and phase offsets preserve one-request/one-response correspondence.",
            ],
            "end_condition": "The reset round trip is complete or the request and matching acknowledgement have both returned to their idle levels.",
            "forbidden_behavior": [
                "Release a destination or source-domain transaction state directly from an asynchronous deassertion.",
                "Create, lose, or duplicate a transaction solely because the two clock domains sample at different rates.",
            ],
        }
        request["parameters"] = {
            "request_synchronizer_stages": 2,
            "acknowledgement_synchronizer_stages": 2,
            "reset_release_stages_per_direction": 2,
            "reset_assertion": "asynchronous_active_low",
        }
    return request


def _lifecycle_policy() -> dict[str, str]:
    return {
        "job_acceptance": "valid_ready_handshake",
        "job_overlap": "single_inflight",
        "busy_behavior": "tracks_active_job",
        "completion_style": "pulse",
        "completion_timing": "next_cycle_after_retirement",
        "illegal_command_behavior": "error_without_start",
        "error_style": "pulse",
        "error_timing": "next_cycle_after_error_event",
        "reset_behavior": "abort_inflight",
    }


def _architecture(case: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    domain = str(case["domain"])
    operation_name = _safe(case["title"])
    requests = [_extension(case, str(feature)) for feature in case["unknown_features"]]
    operations: list[dict[str, Any]] = []
    if domain in {"lifecycle", "operation"}:
        operation = {
            "name": operation_name,
            "kind": operation_name,
            "coverage_family": operation_name,
            "coverage_family_source": "novel",
            "features": [str(case["unknown_features"][0])],
            "feature_extensions": list(map(str, case["unknown_features"][1:])),
            "semantics": (
                f"Source-backed {domain} scope for {case['title']}; exact behavior is "
                "owned by the listed contract-local extension requests."
            ),
            "inputs": [],
            "outputs": [],
        }
        if domain == "lifecycle":
            operation["lifecycle_policy"] = _lifecycle_policy()
        else:
            operation["arithmetic"] = {
                "classifier_profile": "llm_extension",
                "reason": "The selected upstream arithmetic is not a current code-owned profile.",
                "extension_request": requests[0]["id"],
            }
        operations.append(operation)
    contract = {
        "design": {
            "name": operation_name,
            "description": (
                f"External benchmark {case['id']} over {source['project']} at exact revision "
                f"{source['revision']}, target {case['source_target']}."
            ),
        },
        "operations": operations,
        "data_types": [],
        "data_objects": [],
        "dimensions": [],
        "parameters": [],
        "compute": {"organization": "upstream RTL; not inferred by this contract builder"},
        "storage": [],
        "pipeline": {"stages": "upstream RTL; see pinned source"},
        "control": {"style": "source-specific extension"},
        "reset": {"behavior": "source-specific; must be audited before freezing"},
        "latency_model": {"exact": False, "note": "No latency is inferred from source names."},
        "architectural_invariants": [str(case["isolation"])],
        "open_assumptions": [],
        "verification_extensions": requests,
    }
    if str(case["id"]) == "P01":
        contract["control"] = {"style": "pipelined Wishbone slave bridged to AXI4 master"}
        contract["reset"] = {
            "signal": "i_reset",
            "active_level": "high",
            "sampling": "synchronous_to_i_clk",
            "behavior": "reject requests, clear response visibility, and flush tracked Wishbone work",
        }
    elif str(case["id"]) == "P02":
        contract["control"] = {"style": "ordered pipelined-Wishbone request/response CDC"}
        contract["reset"] = {
            "signal": "i_reset",
            "active_level": "high",
            "source_sampling": "synchronous_to_i_wb_clk",
            "destination_propagation": "asynchronous_assertion_then_two_i_xclk_clk_stages",
            "behavior": "abort pending source work and reset both asynchronous FIFO paths",
        }
    elif str(case["id"]) == "P03":
        contract["control"] = {"style": "single-inflight APB setup/access CDC"}
        contract["reset"] = {
            "signal": "S_PRESETn",
            "active_level": "low",
            "assertion": "asynchronous",
            "release": "two destination stages then two source stages",
            "behavior": "suppress transfers until the bidirectional reset round trip completes",
        }
    if domain == "protocol":
        contract["verification_scope"] = {
            "domains": ["protocol"],
            "operation_coverage_required": False,
            "operation_stimulus_ledger_required": False,
            "reason": "This bridge benchmark isolates transport semantics and declares no accelerator operation.",
        }
    return contract


def _interface(case: Mapping[str, Any]) -> dict[str, Any]:
    case_id = str(case["id"])
    if case_id == "P01":
        return _p01_interface()
    if case_id == "P02":
        return _p02_interface()
    if case_id == "P03":
        return _p03_interface()
    # This is deliberately a source-boundary declaration rather than a guessed
    # bus decomposition.  Exact port binding is a mandatory audit item below.
    return {
        "clock": None,
        "reset": None,
        "channels": [],
        "signals": [],
        "global_handshake_rules": "No rule is inferred before source-port audit.",
        "source_boundary": {
            "top": _top_name(case),
            "target": str(case["source_target"]),
            "binding_status": "requires_manual_port_audit",
        },
    }


def _signal(
    name: str,
    role: str,
    direction: str,
    width: int,
    *,
    channel: str | None = None,
    semantic_class: str | None = None,
    protocol_field: str | None = None,
    semantic: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "role": role,
        "channel": channel,
        "direction": direction,
        "width": width,
        "signed": False,
    }
    if semantic_class is not None:
        result["semantic_class"] = semantic_class
    if protocol_field is not None:
        result["protocol_field"] = protocol_field
        result["semantic"] = f"protocol_field={protocol_field}"
    elif semantic is not None:
        result["semantic"] = semantic
    return result


def _custom_channel(name: str, direction: str, *, group: str) -> dict[str, Any]:
    return {
        "name": name,
        "direction": direction,
        "protocol_profile": "custom",
        "protocol_group": group,
        "data_objects": [],
        "ordering": "source-defined",
        "framing": "source-defined",
    }


def _axi_channel(name: str, direction: str, group: str, kind: str) -> dict[str, Any]:
    return {
        "name": name,
        "direction": direction,
        "protocol_profile": "axi4",
        "data_objects": [],
        "ordering": "in_order_per_id",
        "framing": "single_beat",
        "metadata": [
            f"protocol_group={group} protocol_channel={kind}",
            "protocol_capability.max_outstanding=64",
            "protocol_capability.read_write_concurrency=false",
            "protocol_capability.address_bins=aligned",
            "protocol_capability.boundary_bins=ends_before_boundary|ends_at_boundary",
            "protocol_capability.alignment_bins=aligned",
            "protocol_capability.burst_length_bins=single",
            "protocol_capability.burst_type_bins=incrementing",
            "protocol_capability.transfer_size_bins=narrow",
            "protocol_capability.lock_bins=zero",
            "protocol_capability.cache_bins=nonzero",
            "protocol_capability.prot_bins=nonzero",
            "protocol_capability.qos_bins=zero",
            "protocol_capability.exclusive_access=false",
            "protocol_capability.write_strobe_bins=all_zero|sparse",
            "protocol_capability.protection_bins=none",
            "protocol_capability.write_order_bins=address_first|data_first|same_cycle",
        ],
        "protocol_capabilities": {
            "sideband_bins_by_channel": {
                "write_address": {"id": ["zero"]},
                "write_response": {"id": ["zero"]},
                "read_address": {"id": ["nonzero"]},
                "read_data": {"id": ["nonzero"]},
            }
        },
    }


def _p01_interface() -> dict[str, Any]:
    channels = [
        _axi_channel("axi_aw", "output", "axi", "write_address"),
        _axi_channel("axi_w", "output", "axi", "write_data"),
        _axi_channel("axi_b", "input", "axi", "write_response"),
        _axi_channel("axi_ar", "output", "axi", "read_address"),
        _axi_channel("axi_r", "input", "axi", "read_data"),
        {**_custom_channel("wb_request", "input", group="wishbone"), "protocol_profile": "wishbone_b4_pipelined"},
        {**_custom_channel("wb_response", "output", group="wishbone"), "protocol_profile": "wishbone_b4_pipelined"},
    ]
    s = [
        _signal("i_clk", "clock", "input", 1, semantic="Free-running system clock."),
        _signal("i_reset", "reset", "input", 1, semantic="Active-high synchronous reset."),
    ]
    # Exact default-parameter AXI boundary from rtl/wbm2axisp.v.
    for prefix, channel, direction, fields in (
        ("o_axi_aw", "axi_aw", "output", [("valid", "valid", None, 1), ("id", "transaction_id", "identifier", 1), ("addr", "payload", "address", 28), ("len", "metadata", "length", 8), ("size", "metadata", "size", 3), ("burst", "metadata", "burst_type", 2), ("lock", "metadata", "configuration", 1), ("cache", "metadata", "configuration", 4), ("prot", "metadata", "protection", 3), ("qos", "metadata", "priority", 4)]),
        ("o_axi_w", "axi_w", "output", [("valid", "valid", None, 1), ("data", "payload", "data", 128), ("strb", "keep", "byte_enable", 16), ("last", "last", "framing", 1)]),
        ("i_axi_b", "axi_b", "input", [("valid", "valid", None, 1), ("id", "transaction_id", "identifier", 1), ("resp", "metadata", "response_code", 2)]),
        ("o_axi_ar", "axi_ar", "output", [("valid", "valid", None, 1), ("id", "transaction_id", "identifier", 1), ("addr", "payload", "address", 28), ("len", "metadata", "length", 8), ("size", "metadata", "size", 3), ("burst", "metadata", "burst_type", 2), ("lock", "metadata", "configuration", 1), ("cache", "metadata", "configuration", 4), ("prot", "metadata", "protection", 3), ("qos", "metadata", "priority", 4)]),
        ("i_axi_r", "axi_r", "input", [("valid", "valid", None, 1), ("id", "transaction_id", "identifier", 1), ("data", "payload", "data", 128), ("resp", "metadata", "response_code", 2), ("last", "last", "framing", 1)]),
    ):
        for suffix, role, sem, width in fields:
            s.append(_signal(
                f"{prefix}{suffix}", role, direction, width,
                channel=channel, semantic_class=sem,
                protocol_field=None if role == "valid" else suffix,
            ))
    for name, channel, direction in (
        ("i_axi_awready", "axi_aw", "input"), ("i_axi_wready", "axi_w", "input"),
        ("o_axi_bready", "axi_b", "output"), ("i_axi_arready", "axi_ar", "input"),
        ("o_axi_rready", "axi_r", "output"),
    ):
        s.append(_signal(name, "ready", direction, 1, channel=channel))
    s.extend([
        _signal("i_wb_cyc", "metadata", "input", 1, channel="wb_request", semantic_class="command", semantic="Wishbone cycle qualifier."),
        _signal("i_wb_stb", "valid", "input", 1, channel="wb_request", semantic="Wishbone request strobe."),
        _signal("i_wb_we", "metadata", "input", 1, channel="wb_request", semantic_class="command", semantic="Wishbone write enable."),
        _signal("i_wb_addr", "payload", "input", 26, channel="wb_request", semantic_class="address", semantic="Wishbone word address."),
        _signal("i_wb_data", "payload", "input", 32, channel="wb_request", semantic_class="data", semantic="Wishbone write data."),
        _signal("i_wb_sel", "keep", "input", 4, channel="wb_request", semantic_class="byte_enable", semantic="Wishbone byte select."),
        _signal("o_wb_stall", "metadata", "output", 1, channel="wb_response", semantic_class="configuration", semantic="Active-high Wishbone backpressure; not READY."),
        _signal("o_wb_ack", "valid", "output", 1, channel="wb_response", semantic="Wishbone completion acknowledgement."),
        _signal("o_wb_data", "payload", "output", 32, channel="wb_response", semantic_class="data", semantic="Wishbone read data."),
        _signal("o_wb_err", "metadata", "output", 1, channel="wb_response", semantic_class="response_code", semantic="Wishbone error termination."),
    ])
    protocol_semantics = [{
        "name": "wishbone_b4_pipelined",
        "description": "Wishbone B4 pipelined request and registered response behavior at the audited slave boundary.",
        "protocol_groups": ["wishbone"],
        "clock": {"signal": "i_clk", "edge": "rising"},
        "events": [
            {"name": "request_presented", "expression": "i_wb_cyc && i_wb_stb", "description": "A source presents a request."},
            {"name": "request_ready", "expression": "!o_wb_stall", "description": "The bridge can accept a request."},
            {"name": "request_accepted", "expression": "request_presented && request_ready", "description": "A request is accepted."},
            {"name": "request_stalled", "expression": "request_presented && !request_ready", "description": "A request is backpressured."},
            {"name": "write_request_stalled", "expression": "request_stalled && i_wb_we", "description": "A write request is stalled."},
            {"name": "response_success", "expression": "i_wb_cyc && o_wb_ack", "description": "One request succeeds."},
            {"name": "response_error", "expression": "i_wb_cyc && o_wb_err", "description": "One request errors."},
            {"name": "response_completed", "expression": "response_success || response_error", "description": "One request completes."},
            {"name": "cycle_cancelled", "expression": "!i_wb_cyc", "description": "The source cycle is cancelled."},
        ],
        "transactions": [{
            "name": "wishbone_request", "channel": "wb_request",
            "presented_event": "request_presented", "ready_event": "request_ready",
            "accepted_event": "request_accepted", "stalled_event": "request_stalled",
            "completed_event": "response_completed", "success_event": "response_success",
            "error_event": "response_error",
            "content_signals": ["i_wb_we", "i_wb_addr", "i_wb_data", "i_wb_sel"],
            "stable_while_stalled": True,
            "stability_rules": [
                {"id": "request_control", "while_event": "request_stalled", "signals": ["i_wb_stb", "i_wb_we", "i_wb_addr", "i_wb_sel"]},
                {"id": "write_data", "while_event": "write_request_stalled", "signals": ["i_wb_data"]},
            ],
            "source_drive": {
                "presented_assignments": [{"signal": "i_wb_cyc", "value": 1}, {"signal": "i_wb_stb", "value": 1}],
                "idle_assignments": [{"signal": "i_wb_cyc", "value": 0}, {"signal": "i_wb_stb", "value": 0}],
                "post_accept_assignments": [{"signal": "i_wb_cyc", "value": 1}, {"signal": "i_wb_stb", "value": 0}],
                "driven_fields": ["i_wb_we", "i_wb_addr", "i_wb_data", "i_wb_sel"],
                "completion_mode": "wait_for_all_completions",
            },
        }],
        "flow_control": {"maximum_outstanding": 64, "ordering": "oldest_outstanding", "in_order": True},
        "cancellation": {"supported": True, "trigger_event": "cycle_cancelled", "pending_behavior": "flush"},
        "custom_rules": [
            {"id": "axi_translation_and_read_lane", "description": "Check fixed IDs, address translation, saved read-lane association, and read data.", "required_observations": ["transaction_trace", "cycle_trace"], "extension_request_id": "protocol.p01_wishbone_axi_translation_residuals"},
            {"id": "abort_flush_and_read_data_association", "description": "Check returned read-data association and stale source-visible response suppression after reset/cancel.", "required_observations": ["transaction_trace", "cycle_trace"], "extension_request_id": "protocol.p01_wishbone_axi_translation_residuals"},
        ],
    }]
    relation_common = {
        "effect": {
            "kind": "protocol_event",
            "profile": "wishbone_b4_pipelined",
            "event": "response_completed",
        },
        "minimum_latency_cycles": 1,
        "maximum_latency_cycles": 1,
        "ordering": "fifo",
        "maximum_outstanding": 64,
        "unmatched_effect": "ignore",
        "require_effect_before_test_end": True,
        "cancellation": {
            "event": {
                "kind": "protocol_event",
                "profile": "wishbone_b4_pipelined",
                "event": "cycle_cancelled",
            },
            "pending_behavior": "flush",
        },
    }
    protocol_event_relations = [
        {
            "id": "axi_read_response_to_wishbone_completion",
            "description": "A transferred AXI read response produces its registered Wishbone completion on the following cycle.",
            "clock": {"signal": "i_clk", "edge": "rising"},
            "cause": {
                "kind": "standard_channel_transfer",
                "protocol_group": "axi",
                "protocol_channel": "read_data",
            },
            **relation_common,
        },
        {
            "id": "axi_write_response_to_wishbone_completion",
            "description": "A transferred AXI write response produces its registered Wishbone completion on the following cycle.",
            "clock": {"signal": "i_clk", "edge": "rising"},
            "cause": {
                "kind": "standard_channel_transfer",
                "protocol_group": "axi",
                "protocol_channel": "write_response",
            },
            **relation_common,
        },
    ]
    return {"clock": "i_clk", "reset": "i_reset", "channels": channels, "signals": s, "global_handshake_rules": "AXI4 channels obey AXI4; Wishbone events are defined by protocol_semantics.", "protocol_semantics": protocol_semantics, "protocol_event_relations": protocol_event_relations, "source_boundary": {"top": "wbm2axisp", "target": "rtl/wbm2axisp.v", "binding_status": "audited_default_parameters"}}


def _p02_interface() -> dict[str, Any]:
    channels = [
        _custom_channel("wb_request", "input", group="source_wishbone"),
        _custom_channel("wb_response", "output", group="source_wishbone"),
        _custom_channel("xclk_request", "output", group="destination_wishbone"),
        _custom_channel("xclk_response", "input", group="destination_wishbone"),
    ]
    s = [
        _signal("i_wb_clk", "clock", "input", 1, semantic="Source-domain clock."),
        _signal("i_xclk_clk", "clock", "input", 1, semantic="Destination-domain clock."),
        _signal("i_reset", "reset", "input", 1, semantic="Active-high reset."),
    ]
    for name, role, direction, width, channel, sem in (
        ("i_wb_cyc", "metadata", "input", 1, "wb_request", "command"), ("i_wb_stb", "valid", "input", 1, "wb_request", None),
        ("i_wb_we", "metadata", "input", 1, "wb_request", "command"), ("i_wb_addr", "payload", "input", 32, "wb_request", "address"),
        ("i_wb_data", "payload", "input", 32, "wb_request", "data"), ("i_wb_sel", "keep", "input", 4, "wb_request", "byte_enable"),
        ("o_wb_stall", "metadata", "output", 1, "wb_response", "configuration"), ("o_wb_ack", "valid", "output", 1, "wb_response", None),
        ("o_wb_data", "payload", "output", 32, "wb_response", "data"), ("o_wb_err", "metadata", "output", 1, "wb_response", "response_code"),
        ("o_xclk_cyc", "metadata", "output", 1, "xclk_request", "command"), ("o_xclk_stb", "valid", "output", 1, "xclk_request", None),
        ("o_xclk_we", "metadata", "output", 1, "xclk_request", "command"), ("o_xclk_addr", "payload", "output", 32, "xclk_request", "address"),
        ("o_xclk_data", "payload", "output", 32, "xclk_request", "data"), ("o_xclk_sel", "keep", "output", 4, "xclk_request", "byte_enable"),
        ("i_xclk_stall", "metadata", "input", 1, "xclk_response", "configuration"), ("i_xclk_ack", "valid", "input", 1, "xclk_response", None),
        ("i_xclk_data", "payload", "input", 32, "xclk_response", "data"), ("i_xclk_err", "metadata", "input", 1, "xclk_response", "response_code"),
    ):
        s.append(_signal(name, role, direction, width, channel=channel, semantic_class=sem, semantic=f"Exact {name} port from wbxclk."))
    return {"clock": "i_wb_clk", "reset": "i_reset", "channels": channels, "signals": s, "global_handshake_rules": "Both Wishbone domains are extension-owned; no READY inversion is inferred.", "source_boundary": {"top": "wbxclk", "target": "rtl/wbxclk.v", "binding_status": "audited_default_parameters"}}


def _p03_interface() -> dict[str, Any]:
    channels = [
        _custom_channel("s_apb_request", "input", group="source_apb"),
        _custom_channel("s_apb_response", "output", group="source_apb"),
        _custom_channel("m_apb_request", "output", group="destination_apb"),
        _custom_channel("m_apb_response", "input", group="destination_apb"),
        _custom_channel("m_reset", "output", group="destination_reset"),
    ]
    s = [
        _signal("S_APB_PCLK", "clock", "input", 1, semantic="Source APB clock."),
        _signal("M_APB_PCLK", "clock", "input", 1, semantic="Destination APB clock."),
        _signal("S_PRESETn", "reset", "input", 1, semantic="Source active-low asynchronous reset."),
        _signal("M_PRESETn", "metadata", "output", 1, channel="m_reset", semantic_class="configuration", semantic="Synchronized destination active-low reset."),
    ]
    definitions = [
        ("S_APB_PSEL", "valid", "input", 1, "s_apb_request", None), ("S_APB_PENABLE", "metadata", "input", 1, "s_apb_request", "command"),
        ("S_APB_PADDR", "payload", "input", 12, "s_apb_request", "address"), ("S_APB_PWRITE", "metadata", "input", 1, "s_apb_request", "command"),
        ("S_APB_PWDATA", "payload", "input", 32, "s_apb_request", "data"), ("S_APB_PWSTRB", "keep", "input", 4, "s_apb_request", "byte_enable"),
        ("S_APB_PPROT", "metadata", "input", 3, "s_apb_request", "protection"), ("S_APB_PREADY", "valid", "output", 1, "s_apb_response", None),
        ("S_APB_PRDATA", "payload", "output", 32, "s_apb_response", "data"), ("S_APB_PSLVERR", "metadata", "output", 1, "s_apb_response", "response_code"),
        ("M_APB_PSEL", "valid", "output", 1, "m_apb_request", None), ("M_APB_PENABLE", "metadata", "output", 1, "m_apb_request", "command"),
        ("M_APB_PADDR", "payload", "output", 12, "m_apb_request", "address"), ("M_APB_PWRITE", "metadata", "output", 1, "m_apb_request", "command"),
        ("M_APB_PWDATA", "payload", "output", 32, "m_apb_request", "data"), ("M_APB_PWSTRB", "keep", "output", 4, "m_apb_request", "byte_enable"),
        ("M_APB_PPROT", "metadata", "output", 3, "m_apb_request", "protection"), ("M_APB_PREADY", "valid", "input", 1, "m_apb_response", None),
        ("M_APB_PRDATA", "payload", "input", 32, "m_apb_response", "data"), ("M_APB_PSLVERR", "metadata", "input", 1, "m_apb_response", "response_code"),
    ]
    for name, role, direction, width, channel, sem in definitions:
        s.append(_signal(name, role, direction, width, channel=channel, semantic_class=sem, semantic=f"Exact {name} port from apbxclk."))
    return {"clock": "S_APB_PCLK", "reset": "S_PRESETn", "channels": channels, "signals": s, "global_handshake_rules": "APB setup/access and CDC behavior are extension-owned.", "source_boundary": {"top": "apbxclk", "target": "rtl/apbxclk.v", "binding_status": "audited_default_parameters"}}


def build(*, overwrite: bool = False) -> list[Path]:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    written: list[Path] = []
    for case in document["cases"]:
        case_dir = CASES_ROOT / f"{case['id'].lower()}_{case['title']}"
        case_dir.mkdir(parents=True, exist_ok=True)
        source = document["sources"][case["source"]]
        source_path = _source_path(case)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        files: dict[str, Any] = {
            "architecture_contract.yaml": _architecture(case, source),
            "interface_contract.yaml": _interface(case),
            "module_manifest.json": {
                "top": _top_name(case),
                "modules": [
                    {
                        "name": _top_name(case),
                        "responsibility": str(case["title"]),
                        "dependencies": [],
                        "parameters": [],
                        "stateful": True,
                    }
                ],
            },
            "acceptance_criteria.yaml": {
                "contract": ["All declared behavior is supported by the pinned upstream specification."],
                "verification": [
                    "The generated TB passes pristine RTL and legal positive controls.",
                    "Known and held-out mutants fail for the intended diagnostic cause.",
                ],
            },
            "contract_status.yaml": {
                "schema_version": 1,
                "case_id": str(case["id"]),
                "status": "candidate",
                "freeze_blockers": [
                    "manual_source_port_binding_audit",
                    "deterministic_contract_reviewer_pass",
                    "upstream_build_dependency_audit",
                ],
                "source": {
                    "project": source["project"],
                    "revision": source["revision"],
                    "target": str(case["source_target"]),
                },
                "unknown_features": list(case["unknown_features"]),
            },
        }
        for filename, payload in files.items():
            path = case_dir / filename
            if path.exists() and not overwrite:
                continue
            if filename.endswith(".json"):
                path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            else:
                path.write_text(
                    yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
                    encoding="utf-8",
                )
            written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    written = build(overwrite=args.overwrite)
    print(f"materialized {len(written)} files under {CASES_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
