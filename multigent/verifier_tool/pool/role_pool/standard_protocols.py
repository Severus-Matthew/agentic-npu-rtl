"""Compile exact, name-independent bindings for standardized protocols.

The current Architect schema does not yet expose these metadata fields.  Keeping
the format and compiler inside verifier_tool lets a later schema merge add the
fields without moving assertion, coverage, or stimulus logic.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Mapping

import yaml


STANDARD_PROTOCOL_CATALOG_PATH = Path(__file__).with_name("standard_protocols.yaml")
STANDARD_PROFILES = frozenset({"axi4", "axi4_lite", "axi4_stream", "custom_mmio"})
_MEMORY_CHANNELS = {
    "write_address",
    "write_data",
    "write_response",
    "read_address",
    "read_data",
}
_MANAGER_CHANNEL_DIRECTIONS = {
    "write_address": "output",
    "write_data": "output",
    "write_response": "input",
    "read_address": "output",
    "read_data": "input",
}
_FIELD_SEMANTICS = {
    "addr": {"address"},
    "len": {"length"},
    "size": {"size"},
    "burst": {"burst_type"},
    "data": {"data"},
    "strb": {"byte_enable"},
    "keep": {"byte_enable"},
    "last": {"framing"},
    "id": {"identifier"},
    "dest": {"identifier"},
    "resp": {"response_code"},
    "prot": {"protection"},
    "qos": {"priority"},
    "user": {"user_metadata"},
}
_FIXED_FIELD_WIDTHS = {
    "axi4": {
        "len": 8,
        "size": 3,
        "burst": 2,
        "lock": 1,
        "cache": 4,
        "prot": 3,
        "qos": 4,
        "region": 4,
        "resp": 2,
        "last": 1,
    },
    "axi4_lite": {"prot": 3, "resp": 2},
    "axi4_stream": {"last": 1},
}
_TAG_VALUE = re.compile(
    r"(?:^|[\s,;])(?P<key>protocol_group|protocol_channel|protocol_field)="
    r"(?P<value>[A-Za-z0-9_]+)(?=$|[\s,;])"
)
_CAPABILITY_TAG = re.compile(
    r"(?:^|[\s,;])protocol_capability\.(?P<key>[a-z][a-z0-9_]*)="
    r"(?P<value>[A-Za-z0-9_.|+-]+)(?=$|[\s,;])"
)


@lru_cache(maxsize=1)
def load_standard_protocol_catalog() -> dict[str, Any]:
    raw = yaml.safe_load(STANDARD_PROTOCOL_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), dict):
        raise ValueError("standard_protocols.yaml must contain profiles")
    for profile_name in STANDARD_PROFILES:
        profile = raw["profiles"].get(profile_name)
        if not isinstance(profile, dict) or not isinstance(profile.get("channels"), dict):
            raise ValueError(f"standard protocol profile {profile_name!r} is incomplete")
        for kind, channel in profile["channels"].items():
            if not isinstance(channel, dict):
                raise ValueError(f"standard protocol channel {profile_name}.{kind} is invalid")
            for key in ("required_fields", "optional_fields"):
                if not isinstance(channel.get(key), list):
                    raise ValueError(f"{profile_name}.{kind}.{key} must be a list")
    return raw


def render_standard_protocol_metadata_format() -> str:
    """Render exact native fields and their current schema-compatible encoding."""

    lines = [
        "Standard protocol machine-readable metadata (verifier_tool-owned):",
        "- channel.protocol_group: identifies one complete protocol interface",
        "- channel.protocol_channel: standardized channel kind",
        "- signal.protocol_field: standardized field within that channel",
        "- current schema adapter: channel metadata entries use protocol_group=<value> and protocol_channel=<value>",
        "- current schema adapter: signal semantic text uses protocol_field=<value>",
        "- current schema adapter: channel metadata may use protocol_capability.<key>=<value>",
        "- bounded value sets use |, for example protocol_capability.write_strobe_bins=full",
        "- valid/ready remain ordinary signal roles and do not need protocol_field",
        "- no signal or channel name is interpreted",
    ]
    for name in sorted(STANDARD_PROFILES):
        profile = load_standard_protocol_catalog()["profiles"][name]
        lines.append(f"- {name}:")
        for kind, spec in profile["channels"].items():
            required = ",".join(spec["required_fields"]) or "none"
            optional = ",".join(spec["optional_fields"]) or "none"
            lines.append(
                f"  - {kind}: required_fields={required}; optional_fields={optional}"
            )
    return "\n".join(lines)


def _tag_values(values: Any, *, location: str) -> dict[str, str]:
    """Parse only explicit key=value tags; surrounding prose is never inferred."""

    sources = values if isinstance(values, list) else [values]
    result: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, str):
            continue
        for match in _TAG_VALUE.finditer(source):
            key = match.group("key")
            value = match.group("value")
            previous = result.get(key)
            if previous is not None and previous != value:
                raise ValueError(
                    f"{location} has conflicting explicit {key} tags "
                    f"{previous!r} and {value!r}"
                )
            result[key] = value
    return result


def declared_protocol_group(channel: Mapping[str, Any]) -> str:
    """Read a channel's exact group name, including the schema-compatible tag."""

    name = str(channel.get("name", ""))
    native = str(channel.get("protocol_group", "")).strip()
    tagged = _tag_values(
        channel.get("metadata", []), location=f"channel {name!r}"
    ).get("protocol_group", "")
    if native and tagged and native != tagged:
        raise ValueError(
            f"channel {name!r} has conflicting native and tagged protocol_group: "
            f"{native!r} != {tagged!r}"
        )
    return native or tagged


def _capability_value(raw: str) -> Any:
    if "|" in raw:
        return tuple(part for part in raw.split("|") if part)
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    try:
        return int(raw, 0)
    except ValueError:
        return raw


def _capability_tags(values: Any, *, location: str) -> dict[str, Any]:
    sources = values if isinstance(values, list) else [values]
    result: dict[str, Any] = {}
    for source in sources:
        if not isinstance(source, str):
            continue
        for match in _CAPABILITY_TAG.finditer(source):
            key = match.group("key")
            value = _capability_value(match.group("value"))
            if key in result and result[key] != value:
                raise ValueError(
                    f"{location} has conflicting protocol_capability.{key} tags "
                    f"{result[key]!r} and {value!r}"
                )
            result[key] = value
    return result


def enrich_standard_protocol_metadata(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached interface with explicit schema-compatible tags promoted.

    The current Architect schema cannot carry ``protocol_group``,
    ``protocol_channel``, or ``protocol_field`` as native properties.  Until the
    schema is merged, it carries the same data as literal key=value tags in
    existing metadata/semantic fields.  This adapter promotes only those exact
    tags and deliberately performs no signal-name inference.
    """

    enriched = deepcopy(dict(interface))
    channels = [
        item for item in enriched.get("channels", []) if isinstance(item, dict)
    ]
    standard_names: set[str] = set()
    for channel in channels:
        if str(channel.get("protocol_profile", "")) not in STANDARD_PROFILES:
            continue
        channel_name = str(channel.get("name", ""))
        standard_names.add(channel_name)
        tags = _tag_values(
            channel.get("metadata", []), location=f"standard channel {channel_name!r}"
        )
        capability_tags = _capability_tags(
            channel.get("metadata", []), location=f"standard channel {channel_name!r}"
        )
        for key in ("protocol_group", "protocol_channel"):
            tagged = tags.get(key)
            native = str(channel.get(key, "")).strip()
            if tagged and native and tagged != native:
                raise ValueError(
                    f"standard channel {channel_name!r} has conflicting native and "
                    f"tagged {key}: {native!r} != {tagged!r}"
                )
            if tagged and not native:
                channel[key] = tagged
        native_capabilities = channel.get("protocol_capabilities", {})
        if native_capabilities is None:
            native_capabilities = {}
        if not isinstance(native_capabilities, Mapping):
            raise ValueError(
                f"standard channel {channel_name!r} protocol_capabilities must be a mapping"
            )
        merged_capabilities = dict(native_capabilities)
        for key, value in capability_tags.items():
            if key in merged_capabilities and merged_capabilities[key] != value:
                raise ValueError(
                    f"standard channel {channel_name!r} has conflicting native and tagged "
                    f"protocol_capability.{key}"
                )
            merged_capabilities[key] = value
        if merged_capabilities:
            channel["protocol_capabilities"] = merged_capabilities

    for signal in enriched.get("signals", []):
        if not isinstance(signal, dict):
            continue
        channel_name = str(signal.get("channel", ""))
        if channel_name not in standard_names:
            continue
        signal_name = str(signal.get("name", ""))
        tags = _tag_values(
            signal.get("semantic", ""), location=f"standard signal {signal_name!r}"
        )
        tagged = tags.get("protocol_field")
        native = str(signal.get("protocol_field", "")).strip()
        if tagged and native and tagged != native:
            raise ValueError(
                f"standard signal {signal_name!r} has conflicting native and tagged "
                f"protocol_field: {native!r} != {tagged!r}"
            )
        if tagged and not native:
            signal["protocol_field"] = tagged
    return enriched


def _literal_width(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    text = str(value).strip()
    return int(text) if text.isdigit() and int(text) > 0 else None


def _opposite(direction: str) -> str:
    return "input" if direction == "output" else "output"


def _signal_binding(
    channel: Mapping[str, Any],
    signals: list[Mapping[str, Any]],
    profile_spec: Mapping[str, Any],
    errors: list[str],
) -> dict[str, Any] | None:
    channel_name = str(channel.get("name", ""))
    kind = str(channel.get("protocol_channel", ""))
    kind_spec = profile_spec.get("channels", {}).get(kind)
    if not isinstance(kind_spec, Mapping):
        errors.append(
            f"standard channel {channel_name!r} has invalid protocol_channel {kind!r}"
        )
        return None
    attached = [item for item in signals if str(item.get("channel", "")) == channel_name]
    by_role: dict[str, list[Mapping[str, Any]]] = {}
    fields: dict[str, Mapping[str, Any]] = {}
    allowed_fields = set(kind_spec.get("required_fields", [])) | set(
        kind_spec.get("optional_fields", [])
    )
    for signal in attached:
        by_role.setdefault(str(signal.get("role", "")), []).append(signal)
        field_value = signal.get("protocol_field")
        field = str(field_value).strip() if field_value is not None else ""
        if not field:
            if signal.get("role") not in {"valid", "ready"}:
                errors.append(
                    f"standard channel {channel_name!r} signal {signal.get('name')!r} "
                    "requires protocol_field"
                )
            continue
        if field not in allowed_fields:
            errors.append(
                f"standard channel {channel_name!r} field {field!r} is not legal for "
                f"{channel.get('protocol_profile')}.{kind}"
            )
            continue
        if field in fields:
            errors.append(
                f"standard channel {channel_name!r} maps protocol_field {field!r} more than once"
            )
            continue
        fields[field] = signal
        allowed_semantics = _FIELD_SEMANTICS.get(field)
        semantic = str(signal.get("semantic_class", ""))
        if allowed_semantics and semantic not in allowed_semantics:
            errors.append(
                f"standard field {channel_name}.{field} requires semantic_class "
                f"{sorted(allowed_semantics)}, got {semantic!r}"
            )

    optional_roles = set(kind_spec.get("optional_roles", []))
    for role in ("valid", "ready"):
        count = len(by_role.get(role, []))
        if count != 1 and not (role in optional_roles and count == 0):
            errors.append(
                f"standard channel {channel_name!r} requires exactly one {role} role signal"
            )
    channel_direction = str(channel.get("direction", ""))
    expected_ready_direction = _opposite(channel_direction) if channel_direction in {"input", "output"} else ""
    if len(by_role.get("valid", [])) == 1:
        valid = by_role["valid"][0]
        if str(valid.get("direction", "")) != channel_direction:
            errors.append(
                f"standard channel {channel_name!r} VALID direction must equal channel direction {channel_direction!r}"
            )
        valid_width = _literal_width(valid.get("width"))
        if valid_width is not None and valid_width != 1:
            errors.append(f"standard channel {channel_name!r} VALID must be one bit")
    if len(by_role.get("ready", [])) == 1:
        ready = by_role["ready"][0]
        if str(ready.get("direction", "")) != expected_ready_direction:
            errors.append(
                f"standard channel {channel_name!r} READY direction must be {expected_ready_direction!r}"
            )
        ready_width = _literal_width(ready.get("width"))
        if ready_width is not None and ready_width != 1:
            errors.append(f"standard channel {channel_name!r} READY must be one bit")
    for field, signal in fields.items():
        if str(signal.get("direction", "")) != channel_direction:
            errors.append(
                f"standard field {channel_name}.{field} direction must equal channel direction {channel_direction!r}"
            )
    missing = sorted(set(kind_spec.get("required_fields", [])) - set(fields))
    if missing:
        errors.append(
            f"standard channel {channel_name!r} is missing required protocol fields {missing}"
        )
    invalid_roles = any(
        len(by_role.get(role, [])) != 1
        and not (role in optional_roles and not by_role.get(role))
        for role in ("valid", "ready")
    )
    if invalid_roles or missing:
        return None

    field_names = {name: str(signal.get("name", "")) for name, signal in fields.items()}
    widths = {
        name: _literal_width(signal.get("width")) for name, signal in fields.items()
    }
    return {
        "name": channel_name,
        "direction": str(channel.get("direction", "")),
        "kind": kind,
        "valid": str(by_role["valid"][0].get("name", "")),
        "ready": (
            str(by_role["ready"][0].get("name", ""))
            if by_role.get("ready")
            else None
        ),
        "effective_defaults": dict(kind_spec.get("effective_defaults", {})),
        "fields": field_names,
        "widths": widths,
        "capabilities": dict(
            channel.get("protocol_capabilities", {})
            if isinstance(channel.get("protocol_capabilities"), Mapping)
            else {}
        ),
    }


def _validate_widths(profile: str, group: Mapping[str, Any], errors: list[str]) -> None:
    channels = group["channels"]
    data_bindings = [
        channel for channel in channels.values() if channel["kind"] in {"write_data", "read_data", "stream"}
    ]
    for channel in data_bindings:
        data_width = channel["widths"].get("data")
        if data_width is not None:
            invalid_memory_width = (
                profile in {"axi4", "axi4_lite"}
                and (
                    data_width < 8
                    or data_width > 1024
                    or data_width % 8
                    or data_width & (data_width - 1)
                )
            )
            invalid_stream_width = profile == "axi4_stream" and (
                data_width <= 0 or data_width % 8
            )
            if invalid_memory_width:
                errors.append(
                    f"{profile} group {group['name']!r} data width must be a power-of-two byte width from 8 to 1024, got {data_width}"
                )
            elif invalid_stream_width:
                errors.append(
                    f"AXI4-Stream group {group['name']!r} TDATA width must contain an integer number of bytes, got {data_width}"
                )
        if profile == "axi4_lite" and data_width is not None and data_width not in {32, 64}:
            errors.append(
                f"AXI4-Lite group {group['name']!r} data width must be 32 or 64, got {data_width}"
            )
        for mask in ("strb", "keep"):
            mask_width = channel["widths"].get(mask)
            if data_width is not None and mask_width is not None and mask_width * 8 != data_width:
                errors.append(
                    f"{profile} group {group['name']!r} {channel['kind']} {mask} width "
                    f"{mask_width} must equal data bytes {data_width // 8}"
                )
    fixed_widths = _FIXED_FIELD_WIDTHS.get(profile, {})
    for channel in group["channels"].values():
        for field, expected in fixed_widths.items():
            actual = channel["widths"].get(field)
            if actual is not None and actual != expected:
                errors.append(
                    f"{profile} group {group['name']!r} field {channel['kind']}.{field} "
                    f"must be {expected} bits, got {actual}"
                )
    write_width = group["channels"].get("write_data", {}).get("widths", {}).get("data")
    read_width = group["channels"].get("read_data", {}).get("widths", {}).get("data")
    if profile in {"axi4", "axi4_lite"} and None not in {write_width, read_width} and write_width != read_width:
        errors.append(
            f"{profile} group {group['name']!r} write/read data widths must match"
        )
    if profile == "axi4_stream":
        stream_fields = group["channels"].get("stream", {}).get("fields", {})
        if ({"keep", "strb"} & set(stream_fields)) and "data" not in stream_fields:
            errors.append(
                f"AXI4-Stream group {group['name']!r} requires data when keep or strb is mapped"
            )


def compile_standard_protocol_plan(
    interface: Mapping[str, Any], *, require_complete: bool = True
) -> dict[str, Any]:
    """Compile standard groups and raise on an ambiguous or incomplete mapping."""

    interface = enrich_standard_protocol_metadata(interface)
    catalog = load_standard_protocol_catalog()["profiles"]
    signals = [item for item in interface.get("signals", []) if isinstance(item, Mapping)]
    standard_channels = [
        item
        for item in interface.get("channels", [])
        if isinstance(item, Mapping) and str(item.get("protocol_profile", "")) in STANDARD_PROFILES
    ]
    errors: list[str] = []
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for channel in standard_channels:
        name = str(channel.get("name", ""))
        group = str(channel.get("protocol_group", "")).strip()
        kind = str(channel.get("protocol_channel", "")).strip()
        if not group:
            errors.append(f"standard channel {name!r} requires protocol_group")
        if not kind:
            errors.append(f"standard channel {name!r} requires protocol_channel")
        if group and kind:
            grouped.setdefault(group, []).append(channel)

    result_groups: list[dict[str, Any]] = []
    for group_name, raw_channels in sorted(grouped.items()):
        profiles = {str(item.get("protocol_profile", "")) for item in raw_channels}
        if len(profiles) != 1:
            errors.append(f"protocol group {group_name!r} mixes profiles {sorted(profiles)}")
            continue
        profile = next(iter(profiles))
        profile_spec = catalog[profile]
        kinds = [str(item.get("protocol_channel", "")) for item in raw_channels]
        if len(kinds) != len(set(kinds)):
            errors.append(f"protocol group {group_name!r} repeats a protocol_channel")
            continue
        allowed_kinds = set(profile_spec["channels"])
        unknown = sorted(set(kinds) - allowed_kinds)
        if unknown:
            errors.append(f"protocol group {group_name!r} has invalid channels {unknown}")

        if profile in {"axi4", "axi4_lite"}:
            for capability, required_kinds in profile_spec["channel_sets"].items():
                present = set(kinds) & set(required_kinds)
                if present and present != set(required_kinds):
                    errors.append(
                        f"{profile} group {group_name!r} has incomplete {capability} channel set; "
                        f"missing {sorted(set(required_kinds) - present)}"
                    )

        compiled_channels: dict[str, Any] = {}
        for channel in raw_channels:
            binding = _signal_binding(channel, signals, profile_spec, errors)
            if binding is not None:
                compiled_channels[binding["kind"]] = binding

        endpoint_roles: set[str] = set()
        if profile in {"axi4", "axi4_lite"}:
            for kind, binding in compiled_channels.items():
                manager_direction = _MANAGER_CHANNEL_DIRECTIONS[kind]
                endpoint_roles.add(
                    "manager" if binding["direction"] == manager_direction else "subordinate"
                )
            if len(endpoint_roles) > 1:
                errors.append(
                    f"{profile} group {group_name!r} channel directions mix manager and subordinate roles"
                )
            endpoint = next(iter(endpoint_roles), "unknown")
        elif profile == "custom_mmio":
            request = compiled_channels.get("request", {})
            endpoint = "manager" if request.get("direction") == "output" else "subordinate"
        else:
            stream = compiled_channels.get("stream", {})
            endpoint = "source" if stream.get("direction") == "output" else "sink"

        group_capabilities: dict[str, Any] = {}
        for channel in raw_channels:
            capabilities = channel.get("protocol_capabilities", {})
            if not isinstance(capabilities, Mapping):
                continue
            for key, value in capabilities.items():
                if key in group_capabilities and group_capabilities[key] != value:
                    errors.append(
                        f"{profile} group {group_name!r} has conflicting capability {key!r}"
                    )
                else:
                    group_capabilities[str(key)] = value
        group = {
            "name": group_name,
            "profile": profile,
            "endpoint_role": endpoint,
            "interface_category": str(
                raw_channels[0].get(
                    "interface_category",
                    "stream" if profile == "axi4_stream" else "read_write",
                )
            ),
            "native_or_adapted": str(
                raw_channels[0].get("native_or_adapted", "native")
            ),
            "capabilities": group_capabilities,
            "channels": compiled_channels,
            "rules": list(profile_spec.get("rules", [])),
            "coverage": list(profile_spec.get("coverage", [])),
        }
        _validate_widths(profile, group, errors)

        if profile == "axi4":
            aw_channel = compiled_channels.get("write_address", {})
            b_channel = compiled_channels.get("write_response", {})
            ar_channel = compiled_channels.get("read_address", {})
            r_channel = compiled_channels.get("read_data", {})
            aw = aw_channel.get("fields", {})
            b = b_channel.get("fields", {})
            ar = ar_channel.get("fields", {})
            r = r_channel.get("fields", {})
            if bool(aw.get("id")) != bool(b.get("id")):
                errors.append(f"AXI4 group {group_name!r} must map AWID and BID together")
            if bool(ar.get("id")) != bool(r.get("id")):
                errors.append(f"AXI4 group {group_name!r} must map ARID and RID together")
            for label, first, second in (
                ("AWID/BID", aw_channel, b_channel),
                ("ARID/RID", ar_channel, r_channel),
            ):
                first_width = first.get("widths", {}).get("id")
                second_width = second.get("widths", {}).get("id")
                if None not in {first_width, second_width} and first_width != second_width:
                    errors.append(
                        f"AXI4 group {group_name!r} {label} widths must match"
                    )
            awaddr_width = aw_channel.get("widths", {}).get("addr")
            araddr_width = ar_channel.get("widths", {}).get("addr")
            if None not in {awaddr_width, araddr_width} and awaddr_width != araddr_width:
                errors.append(
                    f"AXI4 group {group_name!r} AWADDR/ARADDR widths must match"
                )
        elif profile == "axi4_lite":
            aw_channel = compiled_channels.get("write_address", {})
            b_channel = compiled_channels.get("write_response", {})
            ar_channel = compiled_channels.get("read_address", {})
            r_channel = compiled_channels.get("read_data", {})
            awaddr_width = aw_channel.get("widths", {}).get("addr")
            araddr_width = ar_channel.get("widths", {}).get("addr")
            if None not in {awaddr_width, araddr_width} and awaddr_width != araddr_width:
                errors.append(
                    f"AXI4-Lite group {group_name!r} AWADDR/ARADDR widths must match"
                )
            for label, request, response in (
                ("AWID/BID", aw_channel, b_channel),
                ("ARID/RID", ar_channel, r_channel),
            ):
                request_id = request.get("fields", {}).get("id")
                response_id = response.get("fields", {}).get("id")
                if bool(request_id) != bool(response_id):
                    errors.append(
                        f"AXI4-Lite group {group_name!r} must map optional {label} together"
                    )
                request_width = request.get("widths", {}).get("id")
                response_width = response.get("widths", {}).get("id")
                if None not in {request_width, response_width} and request_width != response_width:
                    errors.append(
                        f"AXI4-Lite group {group_name!r} optional {label} widths must match"
                    )
        result_groups.append(group)

    if errors and require_complete:
        raise ValueError("Invalid standard protocol metadata: " + "; ".join(errors))
    return {
        "schema_version": 1,
        "source": "verifier_tool standard_protocols.yaml + frozen interface contract",
        "groups": result_groups,
        "errors": errors,
    }


def validate_standard_protocol_bindings(interface: Mapping[str, Any]) -> list[str]:
    """Return exact metadata errors without raising."""

    return list(compile_standard_protocol_plan(interface, require_complete=False)["errors"])


__all__ = [
    "STANDARD_PROFILES",
    "STANDARD_PROTOCOL_CATALOG_PATH",
    "compile_standard_protocol_plan",
    "declared_protocol_group",
    "enrich_standard_protocol_metadata",
    "load_standard_protocol_catalog",
    "render_standard_protocol_metadata_format",
    "validate_standard_protocol_bindings",
]
