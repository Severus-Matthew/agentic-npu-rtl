"""Instantiate deterministic coverage obligations from an interface contract."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Mapping

from multigent.verifier_tool.pool.role_pool.interface_semantics import (
    derive_interface_coverage_seed,
    load_interface_protocol_taxonomy,
)
from multigent.verifier_tool.pool.role_pool.standard_protocols import (
    STANDARD_PROFILES,
    compile_standard_protocol_plan,
)
from multigent.verifier_tool.pool.role_pool.protocol_semantics import (
    compile_protocol_semantics,
    expression_signals,
)
from multigent.verifier_tool.lifecycle.coverage.plan import (
    load_lifecycle_coverage_templates,
)
from multigent.verifier_tool.feature_plan import build_protocol_feature_plan
from multigent.verifier_tool.pool.feature_plans.compiler import (
    compile_coverage_feature_plan,
)
from multigent.verifier_tool.pool.feature_plans.catalog import (
    PROTOCOL_FEATURES_PATH,
    load_protocol_feature_catalog,
)


INTERFACE_COVERAGE_TEMPLATES_PATH = PROTOCOL_FEATURES_PATH


@lru_cache(maxsize=1)
def load_interface_coverage_templates() -> dict[str, Any]:
    catalog = load_protocol_feature_catalog()
    raw = {
        **catalog,
        "templates": {
            **catalog["features"],
            **load_lifecycle_coverage_templates()["templates"],
        },
    }
    for name, template in raw["templates"].items():
        if not isinstance(template, dict) or template.get("scope") not in {
            "signal",
            "channel",
            "standard_channel",
            "standard_group",
            "standard_field",
        }:
            raise ValueError(f"Coverage template {name!r} has invalid scope")
        if not isinstance(template.get("match"), dict):
            raise ValueError(f"Coverage template {name!r} needs match rules")
        bins = template.get("coverage", {}).get("bins")
        if not isinstance(bins, list) or not bins:
            raise ValueError(f"Coverage template {name!r} needs bins")
    return raw


def _safe_id(value: object) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value)).strip("_").lower()
    return normalized or "unnamed"


def _signal_matches(signal: Mapping[str, Any], match: Mapping[str, Any]) -> bool:
    return all(signal.get(key) == value for key, value in match.items())


def _channel_role_index(
    signals: list[Mapping[str, Any]], channel_name: str
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for signal in signals:
        if signal.get("channel") != channel_name:
            continue
        result.setdefault(str(signal.get("role")), []).append(str(signal.get("name")))
    return result


def _channel_class_index(
    signals: list[Mapping[str, Any]], channel_name: str
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for signal in signals:
        if signal.get("channel") != channel_name or not signal.get("semantic_class"):
            continue
        result.setdefault(str(signal["semantic_class"]), []).append(str(signal.get("name")))
    return result


def _obligation(
    *, template_name: str, template: Mapping[str, Any], scope: str,
    scope_name: str, bindings: Mapping[str, Any]
) -> dict[str, Any]:
    bins = []
    for bin_spec in template["coverage"]["bins"]:
        item = dict(bin_spec)
        item.setdefault("required", True)
        item.setdefault(
            "applicability",
            {
                "status": (
                    "diagnostic_only"
                    if not item["required"]
                    else "required_reachable"
                ),
                "basis": "template_and_resolved_binding",
            },
        )
        item.setdefault("minimum_hits", 1)
        bins.append(item)
    return {
        "id": f"{scope}.{_safe_id(scope_name)}.{template_name}",
        "template": template_name,
        "scope": scope,
        "scope_name": scope_name,
        "description": template["description"],
        "bindings": dict(bindings),
        "sample_unit": str(template.get("sample_unit", scope)),
        "controllability": str(template.get("controllability", "profile_resolved")),
        "bins": bins,
    }


def _reset_active_value(signal: Mapping[str, Any]) -> int | None:
    semantic = str(signal.get("semantic", "")).lower().replace("_", "-")
    if "active-low" in semantic or "active low" in semantic:
        return 0
    if "active-high" in semantic or "active high" in semantic:
        return 1
    return None


def _standard_bindings(
    group: Mapping[str, Any], channel: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    bindings: dict[str, Any] = {
        "protocol_group": str(group["name"]),
        "protocol_profile": str(group["profile"]),
        "endpoint_role": str(group["endpoint_role"]),
        "interface_category": str(group.get("interface_category", "")),
        "native_or_adapted": str(group.get("native_or_adapted", "native")),
        "capabilities": dict(group.get("capabilities", {})),
        "channels": {
            kind: {
                "name": str(item["name"]),
                "direction": str(item["direction"]),
                "valid": str(item["valid"]),
                "ready": (
                    None if item.get("ready") in {None, ""} else str(item["ready"])
                ),
                "effective_defaults": dict(item.get("effective_defaults", {})),
                "fields": dict(item["fields"]),
                "widths": dict(item["widths"]),
            }
            for kind, item in group["channels"].items()
        },
    }
    if channel is not None:
        bindings.update(
            {
                "protocol_channel": str(channel["kind"]),
                "channel_name": str(channel["name"]),
                "valid": str(channel["valid"]),
                "ready": (
                    None
                    if channel.get("ready") in {None, ""}
                    else str(channel["ready"])
                ),
                "effective_defaults": dict(
                    channel.get("effective_defaults", {})
                ),
                "fields": dict(channel["fields"]),
                "widths": dict(channel["widths"]),
            }
        )
    return bindings


def _diagnostic_bin(bin_spec: Mapping[str, Any], basis: str) -> dict[str, Any]:
    return {
        **dict(bin_spec),
        "required": False,
        "applicability": {"status": "inapplicable", "basis": basis},
    }


def _capability_bins(value: Any) -> set[str] | None:
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set)) and all(
        isinstance(item, str) for item in value
    ):
        return set(map(str, value))
    return None


def _channel_field_capability_bins(
    group: Mapping[str, Any], channel: Mapping[str, Any], field: str
) -> tuple[set[str] | None, str]:
    """Resolve a field partition per protocol channel, then fall back to legacy group bins."""

    capabilities = group.get("capabilities", {})
    if not isinstance(capabilities, Mapping):
        capabilities = {}
    by_channel = capabilities.get("sideband_bins_by_channel")
    if by_channel is not None:
        if not isinstance(by_channel, Mapping):
            raise ValueError(
                "AXI4 capability sideband_bins_by_channel must be a mapping"
            )
        channel_key = str(channel.get("kind", ""))
        channel_bins = by_channel.get(channel_key)
        if channel_bins is None:
            channel_bins = by_channel.get(str(channel.get("name", "")))
        if channel_bins is not None:
            if not isinstance(channel_bins, Mapping):
                raise ValueError(
                    "AXI4 capability sideband_bins_by_channel."
                    f"{channel_key} must be a mapping"
                )
            if field in channel_bins:
                return (
                    _capability_bins(channel_bins[field]),
                    "protocol_capability.sideband_bins_by_channel."
                    f"{channel_key}.{field}",
                )
    return (
        _capability_bins(capabilities.get(f"{field}_bins")),
        f"protocol_capability.{field}_bins",
    )


def _restrict_to_capability_bins(
    item: dict[str, Any], allowed: set[str] | None, basis: str
) -> None:
    if allowed is None:
        return
    item["bins"] = [
        bin_spec
        if str(bin_spec["name"]) in allowed
        else _diagnostic_bin(bin_spec, basis)
        for bin_spec in item["bins"]
    ]


def _append_standard_obligations(
    obligations: list[dict[str, Any]],
    templates: Mapping[str, Any],
    standard_plan: Mapping[str, Any],
) -> None:
    for template_name, template in templates.items():
        scope = str(template.get("scope", ""))
        if not scope.startswith("standard_"):
            continue
        match = template["match"]
        for group in standard_plan.get("groups", []):
            if match.get("protocol_profile") != group["profile"]:
                continue
            required_channels = set(match.get("required_channels", []))
            if not required_channels <= set(group["channels"]):
                continue
            if scope == "standard_group":
                item = _obligation(
                    template_name=template_name,
                    template=template,
                    scope="protocol_group",
                    scope_name=str(group["name"]),
                    bindings=_standard_bindings(group),
                )
                if template_name == "axi4_outstanding_depth":
                    has_id = any(
                        "id" in channel["fields"] for channel in group["channels"].values()
                    )
                    if not has_id:
                        item["bins"] = [
                            _diagnostic_bin(
                                bin_spec, "protocol group has no physical ID field"
                            )
                            if bin_spec["name"] == "multiple_ids"
                            else bin_spec
                            for bin_spec in item["bins"]
                        ]
                capabilities = group.get("capabilities", {})
                max_outstanding = capabilities.get("max_outstanding")
                if (
                    template_name in {"axi_lite_outstanding_depth", "axi4_outstanding_depth"}
                    and isinstance(max_outstanding, int)
                    and not isinstance(max_outstanding, bool)
                    and max_outstanding <= 1
                ):
                    _restrict_to_capability_bins(
                        item,
                        {"one"},
                        "protocol_capability.max_outstanding=1",
                    )
                if (
                    template_name == "axi_lite_read_write_concurrency"
                    and capabilities.get("read_write_concurrency") is False
                ):
                    _restrict_to_capability_bins(
                        item,
                        {"write_only_cycle", "read_only_cycle"},
                        "protocol_capability.read_write_concurrency=false",
                    )
                if template_name in {"axi_lite_write_channel_order", "axi4_write_channel_order"}:
                    _restrict_to_capability_bins(
                        item,
                        _capability_bins(capabilities.get("write_order_bins")),
                        "protocol_capability.write_order_bins",
                    )
                obligations.append(item)
                continue

            kinds = set(match.get("protocol_channels", []))
            for channel in group["channels"].values():
                if kinds and channel["kind"] not in kinds:
                    continue
                if (
                    template_name == "axis_stall_position"
                    and channel.get("ready") in {None, ""}
                ):
                    continue
                required_fields = set(match.get("required_fields", []))
                if not required_fields <= set(channel["fields"]):
                    continue
                if scope == "standard_field":
                    for field in match.get("protocol_fields", []):
                        if field not in channel["fields"]:
                            continue
                        bindings = _standard_bindings(group, channel)
                        bindings.update(
                            {
                                "protocol_field": field,
                                "signal": channel["fields"][field],
                            }
                        )
                        item = _obligation(
                                template_name=template_name,
                                template=template,
                                scope="protocol_field",
                                scope_name=f"{group['name']}_{channel['kind']}_{field}",
                                bindings=bindings,
                        )
                        if template_name == "axi_lite_protection_partition":
                            _restrict_to_capability_bins(
                                item,
                                _capability_bins(
                                    group.get("capabilities", {}).get("protection_bins")
                                ),
                                "protocol_capability.protection_bins",
                            )
                        if template_name == "axi4_sideband_partition":
                            allowed, capability_basis = _channel_field_capability_bins(
                                group, channel, field
                            )
                            if allowed is not None:
                                if not allowed or not allowed <= {"zero", "nonzero"}:
                                    raise ValueError(
                                        f"AXI4 capability {capability_basis} must select zero/nonzero"
                                    )
                                _restrict_to_capability_bins(
                                    item, allowed, capability_basis,
                                )
                        obligations.append(item)
                    continue
                bindings = _standard_bindings(group, channel)
                if template_name == "axi4_transfer_size":
                    data_kind = (
                        "write_data"
                        if channel["kind"] == "write_address"
                        else "read_data"
                    )
                    data_width = group["channels"].get(data_kind, {}).get("widths", {}).get("data")
                    bindings["data_width"] = data_width
                item = _obligation(
                    template_name=template_name,
                    template=template,
                    scope="channel",
                    scope_name=str(channel["name"]),
                    bindings=bindings,
                )
                if template_name == "axi4_transfer_size":
                    data_width = bindings.get("data_width")
                    if isinstance(data_width, int) and data_width // 8 <= 2:
                        item["bins"] = [
                            _diagnostic_bin(
                                bin_spec,
                                "data bus has no distinct multi-byte narrow size",
                            )
                            if bin_spec["name"] == "narrow"
                            else bin_spec
                            for bin_spec in item["bins"]
                        ]
                axi4_capability_bins = {
                    "axi4_4k_boundary": "boundary_bins",
                    "axi4_burst_type": "burst_type_bins",
                    "axi4_burst_length": "burst_length_bins",
                    "axi4_transfer_size": "transfer_size_bins",
                    "axi4_alignment": "alignment_bins",
                }
                if template_name in axi4_capability_bins:
                    key = axi4_capability_bins[template_name]
                    allowed = _capability_bins(group.get("capabilities", {}).get(key))
                    if allowed is not None:
                        defined = {str(bin_spec["name"]) for bin_spec in item["bins"]}
                        if not allowed or not allowed <= defined:
                            raise ValueError(
                                f"AXI4 capability {key} must select known {template_name} bins; "
                                f"got {sorted(allowed)}"
                            )
                        _restrict_to_capability_bins(
                            item, allowed, f"protocol_capability.{key}",
                        )
                if template_name == "axi_lite_address_partition":
                    _restrict_to_capability_bins(
                        item,
                        _capability_bins(
                            group.get("capabilities", {}).get("address_bins")
                        ),
                        "protocol_capability.address_bins",
                    )
                if template_name in {"axi_lite_write_strobe", "axi4_write_strobe"}:
                    _restrict_to_capability_bins(
                        item,
                        _capability_bins(
                            group.get("capabilities", {}).get("write_strobe_bins")
                        ),
                        "protocol_capability.write_strobe_bins",
                    )
                if template_name == "axis_stall_position" and "last" not in channel["fields"]:
                    item["bins"] = [
                        _diagnostic_bin(
                            bin_spec, "AXI4-Stream TLAST is absent"
                        )
                        if bin_spec["name"] == "last_beat"
                        else bin_spec
                        for bin_spec in item["bins"]
                    ]
                obligations.append(item)


def build_interface_coverage_plan(
    interface: Mapping[str, Any],
    *,
    role_extensions: Mapping[str, Mapping[str, Any]] | None = None,
    semantic_class_extensions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build stable obligations by applying templates to explicit contract fields."""

    templates = load_interface_coverage_templates()["templates"]
    profiles = load_interface_protocol_taxonomy()["protocol_profiles"]
    signals = [item for item in interface.get("signals", []) if isinstance(item, Mapping)]
    channels = [item for item in interface.get("channels", []) if isinstance(item, Mapping)]
    channels_by_name = {str(item.get("name", "")): item for item in channels}
    obligations: list[dict[str, Any]] = []
    standard_plan = compile_standard_protocol_plan(interface)
    tag_seed = derive_interface_coverage_seed(
        interface,
        role_extensions=role_extensions,
        semantic_class_extensions=semantic_class_extensions,
    )

    for template_name, template in templates.items():
        if str(template.get("scope", "")).startswith("standard_"):
            continue
        match = template["match"]
        if template["scope"] == "signal":
            for signal in signals:
                if _signal_matches(signal, match):
                    # An arbitrary configuration index may legitimately use the
                    # semantic class ``address`` without byte-address alignment
                    # rules.  Instantiate address coverage only when the selected
                    # channel protocol explicitly carries the alignment tag.
                    if template_name == "address_alignment":
                        channel = channels_by_name.get(str(signal.get("channel", "")), {})
                        profile_name = str(channel.get("protocol_profile", ""))
                        # axi4/axi4_lite/axi4_stream get richer, protocol-specific
                        # address coverage elsewhere (4k-boundary, wrap alignment,
                        # burst type) so the generic partition would be redundant.
                        # custom_mmio has no such dedicated coverage of its own,
                        # so it still needs this generic partition -- excluded from
                        # the skip despite being a STANDARD_PROFILES member.
                        if profile_name in STANDARD_PROFILES and profile_name != "custom_mmio":
                            continue
                        # This gate is intentionally profile-owned.  Signal-role
                        # and semantic tags are inherited for generic channel
                        # features, but an ``address`` semantic alone must not
                        # turn an arbitrary configuration index into a byte-
                        # address alignment obligation.
                        profile_tags = set(
                            profiles.get(profile_name, {}).get("coverage_tags", [])
                        )
                        if "alignment" not in profile_tags:
                            continue
                        roles = _channel_role_index(
                            signals, str(signal.get("channel", ""))
                        )
                        if len(roles.get("valid", [])) != 1 or len(roles.get("ready", [])) != 1:
                            # An address value without an unambiguous accepted
                            # transfer cannot receive trustworthy coverage credit.
                            continue
                        address_transfer = {
                            "valid": roles["valid"][0],
                            "ready": roles["ready"][0],
                        }
                    obligations.append(
                        _obligation(
                            template_name=template_name,
                            template=template,
                            scope="signal",
                            scope_name=str(signal.get("name", "")),
                            bindings={
                                "signal": str(signal.get("name", "")),
                                **(
                                    {"active_value": _reset_active_value(signal)}
                                    if template_name == "reset_behavior"
                                    else {}
                                ),
                                **(
                                    {
                                        "width": str(signal.get("width", "")),
                                        **address_transfer,
                                    }
                                    if template_name == "address_alignment"
                                    else {}
                                ),
                            },
                        )
                    )
            continue

        for channel in channels:
            channel_name = str(channel.get("name", ""))
            profile_name = str(channel.get("protocol_profile", ""))
            profile_tags = set(tag_seed["channels"].get(channel_name, []))
            if match.get("coverage_tag") not in {None, *profile_tags}:
                continue
            if match.get("protocol_profile") not in {None, profile_name}:
                continue

            roles = _channel_role_index(signals, channel_name)
            classes = _channel_class_index(signals, channel_name)
            required_roles = list(match.get("required_roles", []))
            required_classes = list(match.get("required_semantic_classes", []))
            if any(not roles.get(role) for role in required_roles):
                continue
            if any(not classes.get(value) for value in required_classes):
                continue

            bindings: dict[str, Any] = {
                role: roles[role][0] for role in required_roles
            }
            for role in match.get("observed_roles", []):
                if roles.get(role):
                    bindings[role] = list(roles[role])
            for semantic_class in required_classes:
                bindings[semantic_class] = list(classes[semantic_class])
            item = _obligation(
                template_name=template_name,
                template=template,
                scope="channel",
                scope_name=channel_name,
                bindings=bindings,
            )
            if channel.get("direction") == "input":
                # The DUT owns READY on an input channel. A compliant sink may
                # keep READY high, wait for VALID before raising it, or apply
                # backpressure; the testbench cannot force any one of those
                # policies from role/profile metadata alone. Observe every
                # bin, but require only a completed transfer. In particular,
                # receiver_ready and ready_before_valid are not universal
                # protocol obligations (including generic ready_valid).
                if template_name == "handshake_states":
                    _restrict_to_capability_bins(
                        item,
                        {"transfer"},
                        "testbench is source; DUT-owned READY timing is not contract-bound",
                    )
                elif template_name == "handshake_arrival_order":
                    _restrict_to_capability_bins(
                        item,
                        set(),
                        "DUT-owned READY may legally precede, follow, or coincide with VALID",
                    )
                elif template_name == "stall_stability":
                    _restrict_to_capability_bins(
                        item,
                        set(),
                        "testbench is source; DUT-owned stall length is not controllable",
                    )
            obligations.append(item)

    # Contract-local protocols reuse the same handshake/stall templates through
    # Contract-Reviewer-compiled event expressions.  No signal-name inference or
    # generated Python is involved.
    semantic_plan = compile_protocol_semantics(interface)
    for profile in semantic_plan.get("profiles", []):
        for transaction in profile.get("transactions", []):
            common_bindings = {
                "valid_expression": transaction["presented"],
                "ready_expression": transaction["ready"],
                "accepted_expression": transaction["accepted"],
                "expression_signals": sorted(
                    set(expression_signals(transaction["presented"]))
                    | set(expression_signals(transaction["ready"]))
                    | set(expression_signals(transaction["accepted"]))
                ),
                "protocol_profile": str(profile["name"]),
                "transaction": str(transaction["name"]),
                "abort_expression": profile.get("cancellation", {}).get("trigger"),
            }
            for template_name in ("handshake_states", "handshake_arrival_order"):
                item = _obligation(
                    template_name=template_name,
                    template=templates[template_name],
                    scope="channel",
                    scope_name=str(transaction["channel"]),
                    bindings=common_bindings,
                )
                item["id"] = (
                    f"protocol_transaction.{_safe_id(profile['name'])}."
                    f"{_safe_id(transaction['name'])}.{template_name}"
                )
                if channels_by_name.get(str(transaction["channel"]), {}).get(
                    "direction"
                ) == "input":
                    _restrict_to_capability_bins(
                        item,
                        {"transfer"} if template_name == "handshake_states" else set(),
                        "testbench is source; DUT-owned backpressure timing is not contract-bound",
                    )
                obligations.append(item)
            stability_rules = list(transaction.get("stability_rules", []))
            if (
                not stability_rules
                and transaction.get("stable_while_stalled")
                and transaction.get("stalled")
            ):
                stability_rules = [{
                    "id": "stall",
                    "while": transaction["stalled"],
                    "signals": transaction.get("content", ()),
                }]
            for stability_rule in stability_rules:
                stall_item = _obligation(
                    template_name="stall_stability",
                    template=templates["stall_stability"],
                    scope="channel",
                    scope_name=str(transaction["channel"]),
                    bindings={
                        **common_bindings,
                        "stalled_expression": stability_rule["while"],
                        "content": list(stability_rule.get("signals", ())),
                    },
                )
                stall_item["id"] = (
                    f"protocol_transaction.{_safe_id(profile['name'])}."
                    f"{_safe_id(transaction['name'])}."
                    f"{_safe_id(stability_rule['id'])}.stall_stability"
                )
                if channels_by_name.get(str(transaction["channel"]), {}).get(
                    "direction"
                ) == "input":
                    _restrict_to_capability_bins(
                        stall_item,
                        set(),
                        "testbench is source; DUT-owned stall length is not controllable",
                    )
                obligations.append(stall_item)

    _append_standard_obligations(obligations, templates, standard_plan)

    obligations.sort(key=lambda item: item["id"])
    clocks = [str(item.get("name")) for item in signals if item.get("role") == "clock"]
    resets = [str(item.get("name")) for item in signals if item.get("role") == "reset"]
    plan = {
        "schema_version": 2,
        "source": "frozen interface contract + protocol_features.yaml",
        # Retained as plain data so verifier_tool can compile canonical operation
        # adapters without making generated TBs or callers pass a second contract.
        "interface_contract": dict(interface),
        "standard_protocol_plan": standard_plan,
        "protocol_semantics_plan": semantic_plan,
        "monitor": {
            "clock": str(interface.get("clock") or (clocks[0] if clocks else "")),
            "reset": str(interface.get("reset") or (resets[0] if resets else "")),
            # The TB captures this complete declared interface once per sampling
            # event. Assertions and coverage then share the same immutable values.
            "signals": [str(item.get("name")) for item in signals],
        },
        "obligations": obligations,
    }
    plan["feature_plan"] = build_protocol_feature_plan(plan)
    plan["compiled_coverage"] = compile_coverage_feature_plan(plan["feature_plan"])
    return plan
