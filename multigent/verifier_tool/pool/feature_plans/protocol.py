"""Protocol Feature Plan: resolve channel and standardized-bus behavior."""

from __future__ import annotations

from typing import Any, Mapping

from multigent.verifier_tool.pool.role_pool.interface_semantics import (
    derive_interface_coverage_seed,
)
from multigent.verifier_tool.pool.lifecycle_policy_pool import (
    resolve_reset_channel_policies,
)

from .catalog import load_protocol_feature_catalog
from .common import (
    coverage_branch,
    feature_record,
    interface_parts,
    resolved_reset,
    safe_id,
)
from .schema import validate_resolved_feature_plan


def _standard_rule_applies(group: Mapping[str, Any], rule_name: str) -> bool:
    """Reject topology-inapplicable or channel-checker-alias group rules."""

    channels = group.get("channels", {})
    if not isinstance(channels, Mapping):
        return False
    present = set(map(str, channels))
    if rule_name.startswith("write_"):
        required = {"write_address", "write_data"}
        if rule_name == "write_response_after_address_and_data":
            required.add("write_response")
        if not required <= present:
            return False
    if rule_name.startswith("read_") and not {
        "read_address", "read_data"
    } <= present:
        return False
    if rule_name == "optional_id_return_and_in_order_completion":
        return any(
            "id" in channels.get(kind, {}).get("fields", {})
            for kind in ("write_response", "read_data")
            if isinstance(channels.get(kind), Mapping)
        )
    return True


def build_protocol_feature_plan(interface_plan: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve protocol features independently of coverage-template names."""

    existing = interface_plan.get("feature_plan")
    if isinstance(existing, Mapping) and existing.get("domain") == "protocol":
        return validate_resolved_feature_plan(existing)
    interface, standard_groups = interface_parts(interface_plan)
    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    obligations_by_id = {
        str(item.get("id", "")): item
        for item in interface_plan.get("obligations", [])
        if isinstance(item, Mapping)
    }
    feature_catalog = load_protocol_feature_catalog()
    reset_channel_policies = resolve_reset_channel_policies(interface)
    declared_features = feature_catalog["features"]
    stall_spec = declared_features["stall_stability"]
    stall_match = stall_spec["match"]
    tag_seed = derive_interface_coverage_seed(interface)
    standard_channels = {
        str(channel.get("name", "")): channel
        for group in standard_groups
        for channel in group.get("channels", {}).values()
        if isinstance(channel, Mapping)
    }
    features: list[dict[str, Any]] = []

    # Coverage-only and standardized-bus features use the exact bindings already
    # resolved by the catalog matcher. Assertion applicability is an explicit YAML
    # field, never inferred from the presence of a coverage template name.
    for obligation in obligations_by_id.values():
        feature_name = str(obligation.get("template", ""))
        if feature_name == "stall_stability" or feature_name not in declared_features:
            continue
        spec = declared_features[feature_name]
        stimulus = spec["stimulus"]
        features.append(
            feature_record(
                feature_id=str(obligation["id"]),
                domain="protocol",
                kind=feature_name,
                scope=str(obligation.get("scope", spec["scope"])),
                scope_name=str(obligation.get("scope_name", "")),
                bindings=dict(obligation.get("bindings", {})),
                tags=tuple(
                    filter(
                        None,
                        [str(spec.get("match", {}).get("coverage_tag", ""))],
                    )
                ),
                assertion_checker=spec["assertion"].get("checker"),
                coverage={
                    **spec["coverage"],
                    **coverage_branch(
                        obligations_by_id, [str(obligation["id"])]
                    ),
                },
                stimulus_strategy=str(stimulus["strategy"]),
                stimulus=stimulus,
            )
        )

    for channel in interface.get("channels", []):
        if not isinstance(channel, Mapping):
            continue
        channel_name = str(channel.get("name", ""))
        profile = str(channel.get("protocol_profile", ""))
        tags = set(tag_seed["channels"].get(channel_name, []))
        if stall_match.get("coverage_tag") not in tags:
            continue
        by_role: dict[str, list[str]] = {}
        for signal in signals:
            if str(signal.get("channel", "")) != channel_name:
                continue
            by_role.setdefault(str(signal.get("role", "")), []).append(
                str(signal.get("name", ""))
            )
        required_roles = tuple(map(str, stall_match.get("required_roles", ())))
        if any(not by_role.get(role) for role in required_roles):
            continue
        observed = [
            name
            for role in map(str, stall_match.get("observed_roles", ()))
            for name in by_role.get(role, [])
        ]
        standard_channel = standard_channels.get(channel_name, {})
        observed.extend(
            map(str, standard_channel.get("fields", {}).values())
            if isinstance(standard_channel, Mapping)
            else ()
        )
        feature_id = f"channel.{safe_id(channel_name)}.stall_stability"
        features.append(
            feature_record(
                feature_id=feature_id,
                domain="protocol",
                kind="stall_stability",
                scope="channel",
                scope_name=channel_name,
                bindings={
                    "valid": by_role["valid"][0],
                    "ready": by_role["ready"][0],
                    "content": tuple(dict.fromkeys(observed)),
                },
                tags=("stall_stability",),
                assertion_checker=stall_spec["assertion"].get("checker"),
                coverage={
                    **stall_spec["coverage"],
                    **coverage_branch(obligations_by_id, [feature_id]),
                },
                stimulus_strategy=str(stall_spec["stimulus"]["strategy"]),
                stimulus=stall_spec["stimulus"],
            )
        )

    reset = resolved_reset(interface)
    reset_feature = feature_catalog["derived_features"]["valid_low_during_reset"]
    if reset and reset.get("active_value") in {0, 1}:
        for group in standard_groups:
            group_name = str(group.get("name", ""))
            feature_id = f"protocol.{safe_id(group_name)}.valid_low_during_reset"
            features.append(
                feature_record(
                    feature_id=feature_id,
                    domain="protocol",
                    kind="valid_low_during_reset",
                    scope="protocol_group",
                    scope_name=group_name,
                    bindings={
                        "reset": dict(reset),
                        "valid_signals": tuple(
                            str(channel.get("valid", ""))
                            for channel in group.get("channels", {}).values()
                            if isinstance(channel, Mapping)
                            ),
                    },
                    tags=("reset",),
                    assertion_checker=reset_feature["assertion"].get("checker"),
                    coverage={
                        **reset_feature["coverage"],
                        "obligation_ids": (),
                    },
                    stimulus_strategy=str(reset_feature["stimulus"]["strategy"]),
                    stimulus=reset_feature["stimulus"],
                )
            )

        # Generic ready/valid and custom profiles have no universal reset
        # semantics.  Instantiate the same checker only for channels explicitly
        # selected by the lifecycle reset-channel policy.  Standard groups above
        # remain the sole owner for AXI-family/custom-MMIO diagnostics.
        for policy in reset_channel_policies:
            if policy["behavior"] != "valid_deasserted":
                continue
            channel_name = str(policy["channel"])
            feature_id = (
                f"channel.{safe_id(channel_name)}.valid_low_during_reset"
            )
            features.append(
                feature_record(
                    feature_id=feature_id,
                    domain="protocol",
                    kind="valid_low_during_reset",
                    scope="channel",
                    scope_name=channel_name,
                    bindings={
                        "reset": dict(reset),
                        "valid_signals": tuple(policy["valid_signals"]),
                        "settle_cycles": int(policy["settle_cycles"]),
                    },
                    tags=("reset",),
                    assertion_checker=reset_feature["assertion"].get("checker"),
                    coverage={
                        **reset_feature["coverage"],
                        "obligation_ids": (),
                    },
                    stimulus_strategy=str(
                        reset_feature["stimulus"]["strategy"]
                    ),
                    stimulus=reset_feature["stimulus"],
                )
            )

    standard_rule_feature = feature_catalog["derived_features"][
        "standard_protocol_rule"
    ]
    for group in standard_groups:
        group_name = str(group.get("name", ""))
        for rule in group.get("rules", []):
            rule_name = str(rule)
            # Reset-valid is already emitted above with the concrete reset and
            # complete VALID bindings required by its checker.
            if rule_name == "valid_low_during_reset":
                continue
            if not _standard_rule_applies(group, rule_name):
                continue
            features.append(
                feature_record(
                    feature_id=f"protocol.{safe_id(group_name)}.{rule_name}",
                    domain="protocol",
                    kind="standard_protocol_rule",
                    scope="protocol_group",
                    scope_name=group_name,
                    bindings={"protocol_group": group_name, "rule": rule_name},
                    tags=("contract_defined_protocol",),
                    assertion_checker=rule_name,
                    coverage={
                        **standard_rule_feature["coverage"],
                        "obligation_ids": (),
                    },
                    stimulus_strategy=str(
                        standard_rule_feature["stimulus"]["strategy"]
                    ),
                    stimulus=standard_rule_feature["stimulus"],
                )
            )

    features.sort(key=lambda item: str(item["id"]))
    return validate_resolved_feature_plan({
        "schema_version": 1,
        "domain": "protocol",
        "source": "frozen interface binding + verifier_tool protocol feature catalog",
        "bindings": {
            "reset": reset,
            "standard_groups": standard_groups,
        },
        "features": features,
    })


__all__ = ["build_protocol_feature_plan"]
