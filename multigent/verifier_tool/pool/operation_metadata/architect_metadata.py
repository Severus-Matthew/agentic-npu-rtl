"""Compile frozen Architect contracts into a canonical operation-I/O mapping.

The format is deliberately owned by ``verifier_tool`` so a future branch can add
``operation.verification_metadata`` to Architect output without moving runtime
code or changing generated TB call sites. Missing declarations are contract errors,
including for old frozen contracts; arithmetic is never inferred from prose.
"""

from __future__ import annotations

from functools import lru_cache
from copy import deepcopy
from math import prod
from pathlib import Path
import re
from textwrap import indent
from typing import Any, Callable, Mapping

import yaml

from multigent.verifier_tool.pool.diagnostics import (
    ARCHITECT_BLOCKING_REASON_CODES,
    DOMAINS,
    diagnostic_from_error,
)
from multigent.verifier_tool.pool.lifecycle_policy_pool import (
    LifecyclePolicyError,
    control_plane_sequence_schema,
    render_lifecycle_policy_pool,
    resolve_lifecycle_policy,
    validate_lifecycle_policy,
)
from .arithmetic_metadata import (
    ArithmeticMetadataError,
    compile_operation_arithmetic,
    operation_arithmetic_schema,
    validate_resolved_arithmetic,
)
from .io_metadata import declared_serialization, serialization_schema


FORMAT_PATH = Path(__file__).with_name("architect_metadata_format.yaml")


class ArchitectMetadataError(ValueError):
    """Frozen contracts cannot be converted into an unambiguous I/O mapping.

    `reason_code` (see `pool/diagnostics.py`) is attached where the defect is
    detected and decides its category and owner; `details` carries the machine-
    readable facts (object/channel names) so nobody parses the message.
    """

    def __init__(
        self,
        message: str = "",
        *,
        reason_code: str = "unclassified_metadata_error",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = dict(details or {})


@lru_cache(maxsize=1)
def load_architect_metadata_format() -> dict[str, Any]:
    value = yaml.safe_load(FORMAT_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format", {}).get("schema_version") != 2:
        raise ArchitectMetadataError("Invalid architect operation metadata format")
    return value


def render_architect_metadata_format() -> str:
    """Return the human-readable format embedded in Architect/Verifier prompts."""

    return (
        FORMAT_PATH.read_text(encoding="utf-8").rstrip()
        + "\n\nlifecycle_policy_pool:\n"
        + indent(render_lifecycle_policy_pool(), "  ")
        + "\nlifecycle_control_plane_sequence_schema:\n"
        + indent(yaml.safe_dump(control_plane_sequence_schema(), sort_keys=False), "  ")
        + "\noperation_arithmetic_schema:\n"
        + indent(yaml.safe_dump(operation_arithmetic_schema(), sort_keys=False), "  ")
        + "\ndata_object_serialization_schema:\n"
        + indent(yaml.safe_dump(serialization_schema(), sort_keys=False), "  ")
    )


def _unique(
    items: list[Mapping[str, Any]], key: str, value: str, *,
    reason_code: str = "unknown_or_duplicate_data_object",
) -> Mapping[str, Any]:
    matches = [item for item in items if str(item.get(key, "")) == value]
    if len(matches) != 1:
        raise ArchitectMetadataError(
            f"Expected one {key}={value!r}, found {len(matches)}",
            reason_code=reason_code,
            details={key: value, "found": len(matches)},
        )
    return matches[0]


def _fixed_dimensions(architecture: Mapping[str, Any]) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    parameters = {
        str(item.get("name")): str(item.get("default_value", ""))
        for item in architecture.get("parameters", [])
        if isinstance(item, Mapping)
    }
    for item in architecture.get("dimensions", []):
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name", ""))
        low, high = item.get("minimum"), item.get("maximum")
        if isinstance(low, int) and isinstance(high, int) and low == high:
            result[name] = low
            continue
        parameter = str(item.get("bound_parameter", ""))
        raw = parameters.get(parameter, "")
        try:
            result[name] = int(raw, 0)
        except ValueError:
            result[name] = None
    return result


def _binding(
    obj: Mapping[str, Any],
    *,
    direction: str,
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> dict[str, Any]:
    object_name = str(obj["name"])
    carriers = [
        item
        for item in interface.get("channels", [])
        if isinstance(item, Mapping) and object_name in item.get("data_objects", [])
    ]
    channels = [item for item in carriers if item.get("direction") == direction]
    if len(channels) != 1:
        raise _channel_count_error(obj, direction, carriers, channels)
    channel = channels[0]
    channel_name = str(channel["name"])
    signals: dict[str, str] = {}
    for signal in interface.get("signals", []):
        if not isinstance(signal, Mapping) or signal.get("channel") != channel_name:
            continue
        role = str(signal.get("role", ""))
        if role in signals:
            # A second valid/ready/payload leaves the handshake ambiguous (a
            # contract defect); a repeated sideband role is legal in the contract
            # but the canonical binding keeps one signal per role.
            raise ArchitectMetadataError(
                f"Channel {channel_name!r} has ambiguous role {role!r}",
                reason_code=(
                    "ambiguous_channel_signal_role"
                    if role in {"valid", "ready", "payload"}
                    else "multi_signal_role_on_data_channel"
                ),
                details={"channel": channel_name, "role": role},
            )
        signals[role] = str(signal.get("name", ""))
    if str(channel.get("protocol_profile")) == "ready_valid":
        missing = sorted({"valid", "ready", "payload"} - set(signals))
        if missing:
            raise ArchitectMetadataError(
                f"Channel {channel_name!r} is missing signal roles {missing}",
                reason_code="missing_ready_valid_signal_roles",
                details={"channel": channel_name, "missing_roles": missing},
            )
    data_type = _unique(
        [item for item in architecture.get("data_types", []) if isinstance(item, Mapping)],
        "name",
        str(obj["data_type"]),
        reason_code="unknown_or_duplicate_data_type",
    )
    dimensions = list(map(str, obj.get("dimensions", [])))
    dimension_extents = {
        str(item["name"]): int(item["minimum"])
        for item in architecture.get("dimensions", [])
        if isinstance(item, Mapping) and item.get("minimum") == item.get("maximum")
    }
    try:
        serialization = declared_serialization(
            obj,
            dimension_extents=dimension_extents,
            element_width_bits=int(data_type["width_bits"]),
        )
    except ValueError as exc:
        raise ArchitectMetadataError(
            str(exc),
            reason_code="invalid_data_object_serialization",
            details={"data_object": object_name},
        ) from exc
    return {
        "data_object": object_name,
        "object_role": str(obj.get("role", "")),
        "direction": direction,
        "data_type": {
            "name": str(data_type["name"]),
            "width_bits": int(data_type["width_bits"]),
            "signed": bool(data_type["signed"]),
        },
        "dimensions": dimensions,
        "channel": channel_name,
        "protocol_profile": str(channel.get("protocol_profile", "")),
        "signals": signals,
        "serialization": serialization,
    }




def _channel_count_error(
    obj: Mapping[str, Any],
    direction: str,
    carriers: list[Mapping[str, Any]],
    matching: list[Mapping[str, Any]],
) -> ArchitectMetadataError:
    """Classify "needs one {direction} channel" once, at the raise site.

    Several matching channels is ambiguous routing (an Architect defect: the tool
    takes no metadata to pick between them). No matching channel splits three
    ways: carried only by the other direction (Architect defect), an external
    object carried by nothing (Architect defect), or an internal intermediate
    object -- valid in the contract, but not something the interface-bound
    canonical model can express (a tool limitation, never an Architect error).
    """

    name = str(obj["name"])
    details: dict[str, Any] = {
        "data_object": name,
        "direction": direction,
        "channels": [str(item.get("name", "")) for item in (matching or carriers)],
    }
    if len(matching) > 1:
        code = "ambiguous_transport_binding"
        if any(
            str(item.get("protocol_profile", "")) in {"axi4", "axi4_lite", "custom_mmio"}
            for item in matching
        ):
            details["hint_variant"] = "memory_mapped"
    elif carriers:
        code = "data_object_channel_direction_mismatch"
    elif bool(obj.get("external")):
        code = "data_object_not_carried_by_channel"
    else:
        code = "internal_data_object_not_channel_bound"
    return ArchitectMetadataError(
        f"Data object {name!r} needs one {direction} channel; found {len(matching)}",
        reason_code=code,
        details=details,
    )


def _bind_lifecycle_metadata(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Compile only exact role/class bindings; do not interpret signal spelling."""

    signals = [
        item for item in interface.get("signals", []) if isinstance(item, Mapping)
    ]
    command_payloads = [
        item
        for item in signals
        if item.get("role") == "payload"
        and item.get("semantic_class") == "command"
        and item.get("channel")
    ]
    command_channels = []
    for payload in command_payloads:
        channel_name = str(payload["channel"])
        attached = [
            item for item in signals
            if str(item.get("channel", "")) == channel_name
        ]
        role_items: dict[str, list[Mapping[str, Any]]] = {}
        for item in attached:
            role_items.setdefault(str(item.get("role", "")), []).append(item)
        role_map = {
            role: str(items[0].get("name", ""))
            for role in ("valid", "ready", "payload")
            for items in [role_items.get(role, [])]
            if len(items) == 1
        }
        if {"valid", "ready", "payload"} <= set(role_map):
            width_raw = payload.get("width")
            width = int(width_raw) if str(width_raw).isdigit() else None
            semantic = str(payload.get("semantic", ""))
            legal_values = _legal_command_values(semantic, width)
            illegal_value = _first_illegal_value(legal_values, width)
            metadata_fields = []
            for item in role_items.get("metadata", []):
                item_width = item.get("width")
                tags = _explicit_semantic_tags(str(item.get("semantic", "")))
                metadata_fields.append(
                    {
                        "signal": str(item.get("name", "")),
                        "semantic_class": str(item.get("semantic_class", "")),
                        "width_bits": (
                            int(item_width) if str(item_width).isdigit() else None
                        ),
                        "signed": bool(item.get("signed", False)),
                        "data_object": tags.get("data_object"),
                        "address_role": tags.get("address_role"),
                        "byte_order": tags.get("byte_order"),
                        "address_sequence": tags.get("address_sequence"),
                        "word_stride_bytes": (
                            int(tags["word_stride_bytes"])
                            if tags.get("word_stride_bytes", "").isdigit()
                            else None
                        ),
                    }
                )
            command_channels.append(
                {
                    "channel": channel_name,
                    "signals": role_map,
                    "metadata_fields": metadata_fields,
                    "acceptance": "valid_and_ready_on_receiving_active_edge",
                    "payload_width": width,
                    "legal_values": legal_values,
                    "illegal_value": illegal_value,
                    "legality_resolution": (
                        "machine_parsed_contract_semantic"
                        if legal_values
                        else "metadata_missing"
                    ),
                }
            )
    status = {
        role: [
            str(item.get("name", ""))
            for item in signals
            if item.get("role") == role
        ]
        for role in ("busy", "completion", "error")
    }
    return {
        "job_accept_channels": command_channels,
        "job_key": ["reset_epoch", "accepted_command_sequence"],
        "configuration_snapshot": "accepted_command_event",
        "result_retirement": "all_declared_output_elements_accepted",
        "reset_disposition": "new_epoch_pending_work_requires_explicit_abort",
        "status_bindings": status,
    }


_VERILOG_LITERAL = re.compile(
    r"(?<![A-Za-z0-9_])(?:(?P<width>\d+)\s*)?'(?P<base>[hHdDbB])(?P<digits>[0-9a-fA-F_xXzZ]+)"
)
_EXPLICIT_SEMANTIC_TAG = re.compile(
    r"(?:^|[\s,;])(?P<key>data_object|address_role|byte_order|address_sequence|word_stride_bytes)="
    r"(?P<value>[A-Za-z_][A-Za-z0-9_.-]*)(?=$|[\s,;])"
)
_EXPLICIT_INTEGER_TAG = re.compile(
    r"(?:^|[\s,;])(?P<key>word_stride_bytes)=(?P<value>[1-9][0-9]*)(?=$|[\s,;])"
)


def _explicit_semantic_tags(semantic: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in _EXPLICIT_SEMANTIC_TAG.finditer(semantic):
        key, value = match.group("key"), match.group("value")
        previous = result.get(key)
        if previous is not None and previous != value:
            raise ArchitectMetadataError(
                f"Command metadata semantic has conflicting {key} tags "
                f"{previous!r} and {value!r}",
                reason_code="conflicting_semantic_tags",
                details={"tag": key},
            )
        result[key] = value
    for match in _EXPLICIT_INTEGER_TAG.finditer(semantic):
        key, value = match.group("key"), match.group("value")
        previous = result.get(key)
        if previous is not None and previous != value:
            raise ArchitectMetadataError(
                f"Command metadata semantic has conflicting {key} tags "
                f"{previous!r} and {value!r}",
                reason_code="conflicting_semantic_tags",
                details={"tag": key},
            )
        result[key] = value
    return result


def _parse_verilog_integer(text: str) -> tuple[int, int | None] | None:
    match = _VERILOG_LITERAL.search(text)
    if match is None or re.search(r"[xXzZ]", match.group("digits")):
        return None
    base = {"h": 16, "d": 10, "b": 2}[match.group("base").lower()]
    value = int(match.group("digits").replace("_", ""), base)
    width = int(match.group("width")) if match.group("width") else None
    return value, width


def _legal_command_values(semantic: str, declared_width: int | None) -> list[int]:
    """Parse only explicit legal-value clauses; never infer an opcode from a name."""

    clauses: list[str] = []
    for pattern in (
        r"(?<![A-Za-z])legal\s+only\s+([^,;]+)",
        r"(?<![A-Za-z])legal\s+values?\s*(?:is|are|:|=)?\s*([^;]+)",
        r"legality\s+is\s+exactly\s*:\s*[^=;]+==\s*([^,;]+)",
    ):
        clauses.extend(re.findall(pattern, semantic, flags=re.IGNORECASE))
    values: list[int] = []
    for clause in clauses:
        for literal in _VERILOG_LITERAL.finditer(clause):
            if re.search(r"[xXzZ]", literal.group("digits")):
                continue
            base = {"h": 16, "d": 10, "b": 2}[literal.group("base").lower()]
            value = int(literal.group("digits").replace("_", ""), base)
            literal_width = int(literal.group("width")) if literal.group("width") else None
            width = declared_width if declared_width is not None else literal_width
            if width is not None and value >= (1 << width):
                continue
            values.append(value)
    return sorted(set(values))


def _first_illegal_value(legal_values: list[int], width: int | None) -> int | None:
    if not legal_values or width is None or width <= 0:
        return None
    legal = set(legal_values)
    for candidate in (0, 1, (1 << width) - 1):
        if candidate not in legal:
            return candidate
    if len(legal) < (1 << width):
        return next(value for value in range(1 << width) if value not in legal)
    return None


def _control_plane_sequence_pointer_fields(
    lifecycle: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Synthesize the same shape `commands[0].metadata_fields` carries, from a
    `control_plane_sequence`'s own `job_start.actions[].value_from` instead --
    there is no command-channel payload to read a base pointer's byte_order/
    address_sequence/word_stride_bytes off of, since this policy has no
    command channel at all. `byte_order`/`address_sequence` are the only
    values this tool ever supports anywhere (`pack_words` hard-requires
    little/contiguous), so they are fixed here, never guessed per contract.
    `word_stride_bytes` is left `None` -- filled in once the caller knows this
    binding's own bus width and serialization kind, since a `packed_encoding`
    object's stride is one full packed word, not one element.
    """

    sequence = lifecycle.get("control_plane_sequence")
    if not isinstance(sequence, Mapping):
        return []
    objects_with_pointers = {
        str(action["value_from"]["data_object"])
        for action in sequence.get("job_start", {}).get("actions", [])
        if str(action.get("op", "")) == "write_reg"
    }
    return [
        {
            "signal": "",
            "data_object": name,
            "address_role": "base",
            "byte_order": "little",
            "address_sequence": "contiguous",
            "word_stride_bytes": None,
        }
        for name in objects_with_pointers
    ]


def _attach_standard_memory_mappings(
    bindings: list[dict[str, Any]],
    lifecycle: Mapping[str, Any],
    interface: Mapping[str, Any],
    *,
    standard_plan: Callable[[], Mapping[str, Any]] | None = None,
) -> None:
    """Attach executable memory serialization only from explicit metadata tags."""

    commands = list(lifecycle.get("job_accept_channels", []))
    if len(commands) == 1:
        metadata_fields = [
            item
            for item in commands[0].get("metadata_fields", [])
            if isinstance(item, Mapping)
        ]
    elif not commands:
        metadata_fields = _control_plane_sequence_pointer_fields(lifecycle)
        if not metadata_fields:
            return
    else:
        return
    standard = (standard_plan or _standard_plan_getter(interface))()
    channels = {
        str(channel["name"]): (group, channel)
        for group in standard.get("groups", [])
        for channel in group.get("channels", {}).values()
    }
    for binding in bindings:
        profile = binding.get("protocol_profile")
        if profile not in {"axi4_lite", "axi4", "custom_mmio"}:
            continue
        object_name = str(binding.get("data_object", ""))
        pointers = [
            item
            for item in metadata_fields
            if str(item.get("data_object", "")) == object_name
            and item.get("address_role") == "base"
        ]
        if not pointers:
            continue
        if len(pointers) != 1:
            raise ArchitectMetadataError(
                f"Data object {object_name!r} has {len(pointers)} explicit base pointers",
                reason_code="ambiguous_base_pointer",
                details={"data_object": object_name, "count": len(pointers)},
            )
        pointer = dict(pointers[0])
        missing_pointer = [
            key
            for key in ("byte_order", "address_sequence")
            if pointer.get(key) in {None, ""}
        ]
        if missing_pointer:
            continue
        channel_name = str(binding.get("channel", ""))
        compiled = channels.get(channel_name)
        if compiled is None:
            continue
        group, data_channel = compiled
        is_input = binding.get("direction") == "input"
        if profile == "custom_mmio":
            expected_kind = "data"
            address_kind = "request"
            # A read completes on its own data channel, like AXI4's RDATA; a
            # write's "response" channel is optional -- a custom protocol may
            # signal write completion by simply accepting onto "data" itself.
            response_kind = "data" if is_input else "response"
        else:
            expected_kind = "read_data" if is_input else "write_data"
            address_kind = "read_address" if expected_kind == "read_data" else "write_address"
            response_kind = "read_data" if expected_kind == "read_data" else "write_response"
        if data_channel.get("kind") != expected_kind:
            raise ArchitectMetadataError(
                f"Data object {object_name!r} uses {data_channel.get('kind')!r}, "
                f"expected {expected_kind!r}",
                reason_code="memory_channel_kind_mismatch",
                details={
                    "data_object": object_name,
                    "channel_kind": str(data_channel.get("kind")),
                    "expected_kind": expected_kind,
                },
            )
        address_channel = group.get("channels", {}).get(address_kind)
        response_channel = group.get("channels", {}).get(response_kind)
        response_may_be_absent = profile == "custom_mmio" and not is_input
        data_width = data_channel.get("widths", {}).get("data")
        element_width = binding.get("data_type", {}).get("width_bits")
        if (
            not isinstance(data_width, int)
            or not isinstance(element_width, int)
            or data_width <= 0
            or element_width <= 0
            or data_width % element_width
            or address_channel is None
            or (response_channel is None and not response_may_be_absent)
        ):
            continue
        # "contiguous" (the only address_sequence this tool supports) means one
        # word occupies exactly one full bus beat with no gaps -- true whether
        # that beat happens to carry 1 dense element or many packed ones, so
        # this never needs a serialization-specific formula, unlike
        # elements_per_word below. Only filled here when not already supplied
        # by an explicit ready-valid command pointer (`_control_plane_sequence_
        # pointer_fields` deliberately leaves it None; nothing else does).
        word_stride_bytes = (
            int(pointer["word_stride_bytes"])
            if pointer.get("word_stride_bytes") is not None
            else data_width // 8
        )
        serialization = binding.get("serialization", {})
        if serialization.get("kind") == "packed_encoding":
            # A packed_encoding word can carry fewer (or, in principle, more)
            # logical elements than a naive data_width/element_width guess --
            # e.g. this session's real B_matrix packs 32 int8 elements into a
            # 512-bit word, not 64, because each 32-bit lane only carries 2 of
            # them. group_size*containers_per_word is the declaration's own
            # answer to "how many logical elements does one word actually
            # carry", already validated against the traversal's field_axis/
            # container_axis extents in `validate_packed_encoding_declaration`.
            elements_per_word = (
                int(serialization["packed_encoding"]["group_size"])
                * int(serialization["traversal"]["containers_per_word"])
            )
        else:
            elements_per_word = data_width // element_width
        binding["memory_mapping"] = {
            "protocol_profile": str(profile),
            "protocol_group": str(group["name"]),
            "base_signal": str(pointer["signal"]),
            "address_channel": str(address_channel["name"]),
            "data_channel": str(data_channel["name"]),
            "response_channel": (
                str(response_channel["name"]) if response_channel is not None else None
            ),
            "byte_order": str(pointer["byte_order"]),
            "address_sequence": str(pointer["address_sequence"]),
            "word_stride_bytes": word_stride_bytes,
            "bus_width_bits": data_width,
            "elements_per_word": elements_per_word,
            "protocol_capabilities": deepcopy(dict(group.get("capabilities", {}))),
            "protocol_fields": {
                str(kind): sorted(map(str, channel.get("fields", {})))
                for kind, channel in group.get("channels", {}).items()
            },
        }


def _standard_plan_getter(interface: Mapping[str, Any]) -> Callable[[], Mapping[str, Any]]:
    """Compile the interface's standard-protocol plan at most once per build."""

    cache: dict[str, Any] = {}

    def get() -> Mapping[str, Any]:
        if "plan" not in cache:
            from multigent.verifier_tool.pool.role_pool.standard_protocols import (
                compile_standard_protocol_plan,
            )

            cache["plan"] = compile_standard_protocol_plan(interface)
        return cache["plan"]

    return get


def _bind_objects(
    names: Any,
    *,
    direction: str,
    objects: Mapping[str, Mapping[str, Any]],
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[ArchitectMetadataError]]:
    """Bind every named object; a failure leaves an unbound placeholder, not a gap."""

    bound: list[dict[str, Any]] = []
    errors: list[ArchitectMetadataError] = []
    for name in map(str, names):
        try:
            obj = _unique(list(objects.values()), "name", name)
            bound.append(
                _binding(obj, direction=direction, architecture=architecture, interface=interface)
            )
        except ArchitectMetadataError as exc:
            errors.append(exc)
            placeholder: dict[str, Any] = {
                "data_object": name,
                "direction": direction,
                "bound": False,
                "reason_code": exc.reason_code,
            }
            # Preserve transport-independent object shape in a failed shell.
            # Downstream obligation planning may still decide whether a phase
            # exists, but it must never infer a real channel from this record.
            obj = objects.get(name)
            if isinstance(obj, Mapping):
                placeholder.update(
                    {
                        "object_role": str(obj.get("role", "")),
                        "external": bool(obj.get("external", True)),
                        "dimensions": list(map(str, obj.get("dimensions", []))),
                    }
                )
                fixed = _fixed_dimensions(architecture)
                extents = [fixed.get(axis) for axis in placeholder["dimensions"]]
                if all(isinstance(value, int) and value > 0 for value in extents):
                    placeholder["expected_elements"] = (
                        prod(map(int, extents)) if extents else 1
                    )
            bound.append(placeholder)
    return bound, errors


def _validated_policy(operation: Mapping[str, Any]) -> dict[str, Any] | None:
    """The operation's lifecycle policy iff it is valid on its own, else None."""

    if "lifecycle_policy" not in operation:
        return None
    try:
        return validate_lifecycle_policy(operation["lifecycle_policy"])
    except LifecyclePolicyError:
        return None


def _shell(
    operation: Mapping[str, Any],
    dimensions: Mapping[str, Any],
    *,
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    lifecycle: Mapping[str, Any] | None,
    arithmetic: Mapping[str, Any] | None,
    fragments: Mapping[str, str],
) -> dict[str, Any]:
    """What could be compiled of an operation that could not be compiled whole."""

    return {
        "operation_name": str(operation.get("name", "")),
        "family": str(operation.get("coverage_family", "")),
        "dimensions": dict(dimensions),
        "inputs": inputs,
        "outputs": outputs,
        "lifecycle": dict(lifecycle) if lifecycle is not None else None,
        "arithmetic": dict(arithmetic) if arithmetic is not None else None,
        "fragments": dict(fragments),
    }


def _compile_explicit_operation(
    operation: Mapping[str, Any],
    explicit: Mapping[str, Any],
    interface: Mapping[str, Any],
    standard_plan: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    if "arithmetic" in operation:
        raise ArchitectMetadataError(
            "Declare operation.arithmetic or full verification_metadata, not both",
            reason_code="arithmetic_declaration_conflict",
        )
    item = deepcopy(dict(explicit))
    item.setdefault("schema_version", 2)
    item.setdefault("operation_name", str(operation.get("name", "")))
    item.setdefault("family", str(operation.get("coverage_family", "")))
    lifecycle = item.setdefault("lifecycle", {})
    _attach_lifecycle_policy(lifecycle, operation, interface, standard_plan=standard_plan)
    validate_architect_operation_metadata(item)
    return item


def _later_stage(
    diagnostics: list[dict[str, Any]], call: Callable[[], Any], *, default: Any = None
) -> Any:
    """Run a compile stage that the old sequential compile only reached if every
    earlier stage had succeeded.

    An unexpected error there (an interface-level `ValueError` from the standard-protocol
    plan, a malformed shape) used to be unreachable once an earlier stage had failed, so it
    must not turn a recorded failure into a raise now that later fragments are still
    attempted for the shell. With no earlier failure it propagates exactly as before.
    The errors a stage reports as diagnostics (`ArchitectMetadataError`,
    `ArithmeticMetadataError`) are always re-raised for the stage's own handler.
    """

    try:
        return call()
    except (ArchitectMetadataError, ArithmeticMetadataError):
        raise
    except Exception:
        if diagnostics:
            return default
        raise


_SKIPPED = object()


def _compile_operation(
    operation: Mapping[str, Any],
    *,
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
    objects: Mapping[str, Mapping[str, Any]],
    dimensions: Mapping[str, Any],
    standard_plan: Callable[[], Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Compile one operation as independent fragments.

    Returns ``(metadata, None)`` when every fragment compiled, otherwise
    ``(None, {"diagnostics": [...], "shell": {...}})``. The fragments are the
    operation's I/O bindings (per object), its lifecycle binding and policy, its
    standard-memory mappings, and its arithmetic. A failing fragment does not stop
    the others, so the diagnostics list every defect the contract has (the first is
    what the old single exception reported, in the same order) and the shell keeps
    whatever did compile for downstream planning. Nothing here classifies a
    defect: each raise site attached its own ``reason_code``.
    """

    name = str(operation.get("name", ""))
    # A null inputs/outputs list is "none declared" (the Architect schema requires
    # arrays, so this is hand-built input); normalize it once here instead of at every
    # place the compile reads the operation.
    operation = {
        **operation,
        "inputs": [] if operation.get("inputs") is None else operation["inputs"],
        "outputs": [] if operation.get("outputs") is None else operation["outputs"],
    }
    explicit = operation.get("verification_metadata")
    if isinstance(explicit, Mapping):
        try:
            return _compile_explicit_operation(operation, explicit, interface, standard_plan), None
        except ArchitectMetadataError as exc:
            return None, {
                "diagnostics": [diagnostic_from_error(name, exc)],
                "shell": _shell(
                    operation,
                    dimensions,
                    inputs=[
                        {"data_object": str(item), "direction": "input", "bound": False}
                        for item in operation.get("inputs", [])
                    ],
                    outputs=[
                        {"data_object": str(item), "direction": "output", "bound": False}
                        for item in operation.get("outputs", [])
                    ],
                    lifecycle=None,
                    arithmetic=None,
                    fragments={"operation_io": "failed", "lifecycle": "failed", "arithmetic": "failed"},
                ),
            }

    diagnostics: list[dict[str, Any]] = []

    def record(error: ArchitectMetadataError) -> None:
        diagnostics.append(diagnostic_from_error(name, error))

    inputs, input_errors = _bind_objects(
        operation["inputs"], direction="input",
        objects=objects, architecture=architecture, interface=interface,
    )
    outputs, output_errors = _bind_objects(
        operation["outputs"], direction="output",
        objects=objects, architecture=architecture, interface=interface,
    )
    io_errors = [*input_errors, *output_errors]
    for error in io_errors:
        record(error)

    lifecycle: dict[str, Any] | None = None
    shell_lifecycle: dict[str, Any] | None = None
    lifecycle_state = "failed"
    try:
        bound_lifecycle = _later_stage(
            diagnostics, lambda: _bind_lifecycle_metadata(interface), default=_SKIPPED
        )
    except ArchitectMetadataError as exc:
        record(exc)
    else:
        if bound_lifecycle is not _SKIPPED:
            # The shell keeps the command/status binding but never an unvalidated
            # policy or control-plane declaration, so planners cannot trust bad input.
            shell_lifecycle = deepcopy(bound_lifecycle)
            candidate = deepcopy(bound_lifecycle)
            try:
                attached = _later_stage(
                    diagnostics,
                    lambda: _attach_lifecycle_policy(
                        candidate, operation, interface, standard_plan=standard_plan
                    ) or True,
                    default=_SKIPPED,
                )
            except ArchitectMetadataError as exc:
                record(exc)
                lifecycle_state = "partial"
                policy = _validated_policy(operation)
                if policy is not None:
                    shell_lifecycle["policy"] = policy
                    shell_lifecycle["policy_source"] = "explicit_contract"
            else:
                if attached is _SKIPPED:
                    lifecycle_state = "partial"
                else:
                    lifecycle = candidate
                    shell_lifecycle = candidate
                    lifecycle_state = "compiled"

    mapping_failed = False
    bound_bindings = [item for item in [*inputs, *outputs] if item.get("bound", True)]
    if shell_lifecycle is not None:
        # Attempted on the bindings that did bind, even when a sibling did not: the
        # shell then keeps their memory mappings (and the response channels the
        # planner derives error features from). It also runs with no bindings at all,
        # exactly as the sequential compile did, because compiling the interface's
        # standard-protocol plan is what surfaces an interface-level defect.
        try:
            _later_stage(
                diagnostics,
                lambda: _attach_standard_memory_mappings(
                    bound_bindings, shell_lifecycle, interface, standard_plan=standard_plan
                ),
            )
        except ArchitectMetadataError as exc:
            record(exc)
            mapping_failed = True

    arithmetic: dict[str, Any] | None = None
    try:
        arithmetic = _later_stage(
            diagnostics, lambda: compile_operation_arithmetic(operation, architecture)
        )
    except ArithmeticMetadataError as exc:
        record(
            ArchitectMetadataError(
                f"operation {name!r}.arithmetic: {exc}",
                reason_code=(
                    "missing_arithmetic_declaration"
                    if "arithmetic" not in operation
                    else "invalid_arithmetic_declaration"
                ),
            )
        )

    bound_count = sum(1 for item in [*inputs, *outputs] if item.get("bound", True))
    # Memory mappings are only attachable once the command/pointer binding exists; a
    # memory-mapped binding left unmapped because the lifecycle binding failed is not
    # a fully compiled I/O fragment.
    mapping_skipped = shell_lifecycle is None and any(
        item.get("bound", True)
        and item.get("protocol_profile") in {"axi4", "axi4_lite", "custom_mmio"}
        for item in [*inputs, *outputs]
    )
    if io_errors or mapping_failed or mapping_skipped:
        io_state = "partial" if bound_count else "failed"
    else:
        io_state = "compiled"
    fragments = {
        "operation_io": io_state,
        "lifecycle": lifecycle_state,
        "arithmetic": "compiled" if arithmetic is not None else "failed",
    }
    item: dict[str, Any] | None = None
    if not diagnostics:
        item = {
            "schema_version": 2,
            "operation_name": name,
            "family": str(operation.get("coverage_family", "")),
            "dimensions": dimensions,
            "inputs": inputs,
            "outputs": outputs,
            "arithmetic": arithmetic,
            "lifecycle": lifecycle,
        }
        try:
            validate_architect_operation_metadata(item)
        except ArchitectMetadataError as exc:
            record(exc)
            item = None
    if item is not None:
        return item, None
    return None, {
        "diagnostics": diagnostics,
        "shell": _shell(
            operation, dimensions,
            inputs=inputs, outputs=outputs,
            lifecycle=shell_lifecycle, arithmetic=arithmetic, fragments=fragments,
        ),
    }


def _affected_feature_ids(
    name: str,
    shell: Mapping[str, Any],
    architecture: Mapping[str, Any],
    standard_plan: Callable[[], Mapping[str, Any]],
) -> list[str]:
    """Feature IDs that cannot be code-owned because this operation failed to compile.

    An annotation only: if resolving it fails for any reason the entry is still
    emitted, because losing the diagnostic would be worse than losing the list.
    """

    try:
        from multigent.verifier_tool.pool.feature_plans.lifecycle import (
            blocked_lifecycle_feature_ids,
        )
        from multigent.verifier_tool.pool.feature_plans.operation import (
            build_operation_feature_plan,
        )

        ids = blocked_lifecycle_feature_ids(shell, standard_plan().get("groups", []))
        ids.extend(
            str(feature["id"])
            for feature in build_operation_feature_plan(architecture)["features"]
            if str(feature.get("scope_name", "")) == name
        )
    except (ValueError, KeyError, TypeError, AssertionError):
        return []
    return sorted(set(ids))


def _unrepresentable_entry(
    operation: Mapping[str, Any],
    failure: Mapping[str, Any],
    architecture: Mapping[str, Any],
    standard_plan: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    name = str(operation.get("name", ""))
    diagnostics = list(failure["diagnostics"])
    primary = diagnostics[0]
    domains = {domain for item in diagnostics for domain in item["affected_domains"]}
    return {
        # Legacy keys first: callers and tests read entry["name"] / entry["reason"].
        "name": name,
        "reason": primary["message"],
        "operation_name": name,
        "reason_code": primary["reason_code"],
        "category": primary["category"],
        "owner": primary["owner"],
        "affected_domains": [item for item in DOMAINS if item in domains],
        "affected_feature_ids": _affected_feature_ids(
            name, failure["shell"], architecture, standard_plan
        ),
        "blocked_by": sorted({str(item["blocked_by"]) for item in diagnostics}),
        "message": primary["message"],
        "resolution_hint": primary["resolution_hint"],
        "diagnostics": diagnostics,
        "shell": failure["shell"],
    }


def build_architect_operation_metadata(
    architecture: Mapping[str, Any], interface: Mapping[str, Any]
) -> dict[str, Any]:
    """Return versioned machine-readable metadata for every operation.

    Contracts declare operation.arithmetic explicitly. Full canonical metadata
    remains an external input form. Older contracts must supply missing declarations.

    Each operation is compiled independently. `"operations"` holds exactly the
    operations that compiled *whole* (their entries are unchanged, so every
    runtime/campaign consumer can trust them). An operation that could not be
    compiled is not raised and not dropped: it is recorded in
    `"unrepresentable_operations"` with

    * legacy `name` / `reason` (the first defect, as the old exception reported it);
    * `reason_code`, `category` (`contract_error` | `extension_required` |
      `tool_capability`), `owner`, `affected_domains`, `affected_feature_ids`,
      `blocked_by`, `message`, `resolution_hint` for the primary defect, and
      `diagnostics` with every defect found (see `pool/diagnostics.py`);
    * `shell`: whatever fragments (operation I/O bindings, lifecycle, arithmetic)
      did compile, which the lifecycle planner uses to keep the operation's
      contract-required obligations alive instead of letting them vanish.

    An entry means strictly more than an `automatic_campaign_support` "not
    supported" operation: it has no metadata for the code-owned drivers to read,
    so it needs Verifier-authored evidence (or, for a `tool_capability` cause, an
    engineer adding support to `verifier_tool`), and -- when its category is
    `contract_error` -- an Architect correction. See `validate_operation_compilation`.
    """

    load_architect_metadata_format()
    objects = {
        str(item.get("name")): item
        for item in architecture.get("data_objects") or []
        if isinstance(item, Mapping)
    }
    dimensions = _fixed_dimensions(architecture)
    standard_plan = _standard_plan_getter(interface)
    compiled: list[dict[str, Any]] = []
    unrepresentable: list[dict[str, Any]] = []
    for operation in architecture.get("operations") or []:
        if not isinstance(operation, Mapping):
            continue
        item, failure = _compile_operation(
            operation,
            architecture=architecture,
            interface=interface,
            objects=objects,
            dimensions=dimensions,
            standard_plan=standard_plan,
        )
        if item is not None:
            compiled.append(item)
        else:
            assert failure is not None
            unrepresentable.append(
                _unrepresentable_entry(operation, failure, architecture, standard_plan)
            )
    return {
        "schema_version": 2,
        "operations": compiled,
        "unrepresentable_operations": unrepresentable,
    }


def _diagnostic_message(diagnostic: Mapping[str, Any]) -> str:
    return (
        f"operation {diagnostic['operation_name']!r} [{diagnostic['reason_code']}]: "
        f"{diagnostic['message']} -- {diagnostic['resolution_hint']}"
    )


def blocking_compilation_errors(metadata: Mapping[str, Any]) -> list[str]:
    """One message per Architect-blocking diagnostic in already-built metadata."""

    return [
        _diagnostic_message(diagnostic)
        for entry in metadata.get("unrepresentable_operations", [])
        for diagnostic in entry.get("diagnostics", [])
        if diagnostic["reason_code"] in ARCHITECT_BLOCKING_REASON_CODES
    ]


def compilation_capability_notes(metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Diagnostics that are reported but never sent back to the Architect.

    Tool-capability and extension causes (a valid contract the tool cannot
    automate) plus contract errors another validator already owns.
    """

    return [
        {
            key: diagnostic.get(key)
            for key in (
                "operation_name", "reason_code", "category", "owner",
                "affected_domains", "message", "resolution_hint", "blocked_by",
            )
        }
        for entry in metadata.get("unrepresentable_operations", [])
        for diagnostic in entry.get("diagnostics", [])
        if diagnostic["reason_code"] not in ARCHITECT_BLOCKING_REASON_CODES
    ]


def validate_operation_compilation(
    architecture: Mapping[str, Any], interface: Mapping[str, Any]
) -> list[str]:
    """Contract errors in operation compilation that the Architect can fix.

    Returns one message per defect whose reason code is Architect-blocking
    (see `ARCHITECT_BLOCKING_REASON_CODES`): defects that only the contract's
    author can resolve and that no earlier validator already reports (an object
    on two channels, a control_plane_sequence policy without its declaration, ...).
    Tool-capability and extension causes are deliberately NOT returned -- they are
    valid contracts the tool cannot automate, reported through
    `unrepresentable_operations`/`compilation_capability_notes`, never sent back to
    the Architect. A missing lifecycle_policy/arithmetic declaration is not among the
    blocking codes (its own validator owns it, with the caller's `require_*`
    tolerance), so an older frozen operation under a local revision is not blocked
    here. A contract so malformed that compilation itself raises is reported as one
    error rather than crashing the caller.
    """

    try:
        return blocking_compilation_errors(
            build_architect_operation_metadata(architecture, interface)
        )
    except (ValueError, KeyError, TypeError, AssertionError) as exc:
        return [f"operation metadata could not be compiled: {type(exc).__name__}: {exc}"]


def _require_control_plane_group(
    lifecycle: Mapping[str, Any],
    operation: Mapping[str, Any],
    standard_plan: Callable[[], Mapping[str, Any]] | None,
    interface: Mapping[str, Any],
) -> None:
    """A control_plane_sequence is driven through an AXI4-Lite subordinate group."""

    if lifecycle.get("control_plane_sequence") is None:
        return
    plan = standard_plan() if standard_plan is not None else _standard_plan_getter(interface)()
    if not any(
        isinstance(group, Mapping)
        and group.get("profile") == "axi4_lite"
        and group.get("endpoint_role") == "subordinate"
        for group in plan.get("groups", [])
    ):
        raise ArchitectMetadataError(
            f"operation {operation.get('name')!r}: control_plane_sequence needs an AXI4-Lite "
            "subordinate (control) channel group in the interface to drive and observe it through",
            reason_code="control_plane_requires_axi4_lite_subordinate",
            details={"operation": str(operation.get("name", ""))},
        )


def _attach_lifecycle_policy(
    lifecycle: dict[str, Any],
    operation: Mapping[str, Any],
    interface: Mapping[str, Any],
    *,
    standard_plan: Callable[[], Mapping[str, Any]] | None = None,
) -> None:
    """Accept a small Architect extension without requiring full I/O metadata."""

    if not isinstance(lifecycle, dict):
        raise ArchitectMetadataError(
            "Operation lifecycle metadata must be an object",
            reason_code="invalid_verification_metadata",
        )
    if "lifecycle_policy" in operation:
        supplied = operation["lifecycle_policy"]
        if "policy" in lifecycle and lifecycle["policy"] != supplied:
            raise ArchitectMetadataError(
                "operation.lifecycle_policy and verification_metadata.lifecycle.policy disagree",
                reason_code="lifecycle_policy_conflict",
            )
        lifecycle["policy"] = supplied
        lifecycle["policy_source"] = "explicit_contract"
    if "lifecycle_control_plane_sequence" in operation:
        supplied_sequence = operation["lifecycle_control_plane_sequence"]
        existing_sequence = lifecycle.get("control_plane_sequence")
        if existing_sequence is not None and existing_sequence != supplied_sequence:
            raise ArchitectMetadataError(
                "operation.lifecycle_control_plane_sequence and "
                "verification_metadata.lifecycle.control_plane_sequence disagree",
                reason_code="lifecycle_policy_conflict",
            )
        lifecycle["control_plane_sequence"] = supplied_sequence
    data_object_names = {
        str(name)
        for name in [*operation.get("inputs", []), *operation.get("outputs", [])]
    }
    try:
        lifecycle.update(resolve_lifecycle_policy(
            lifecycle,
            interface.get("signals", []),
            data_object_names=data_object_names,
        ))
    except LifecyclePolicyError as exc:
        raise ArchitectMetadataError(
            f"operation {operation.get('name')!r}: {exc}",
            reason_code=exc.reason_code,
        ) from exc
    _require_control_plane_group(lifecycle, operation, standard_plan, interface)


def validate_architect_operation_metadata(metadata: Mapping[str, Any]) -> None:
    """Validate the merge-facing format without depending on Agent JSON schema."""

    required = {
        "schema_version", "operation_name", "family", "inputs", "outputs",
        "dimensions", "arithmetic", "lifecycle",
    }
    missing = sorted(required - set(metadata))
    if missing:
        raise ArchitectMetadataError(
            f"Operation metadata is missing {missing}", reason_code="invalid_verification_metadata"
        )
    if metadata.get("schema_version") != 2:
        raise ArchitectMetadataError(
            "Operation metadata schema_version must be 2", reason_code="invalid_verification_metadata"
        )
    if not str(metadata.get("operation_name", "")):
        raise ArchitectMetadataError("Operation metadata needs operation_name", reason_code="invalid_verification_metadata")
    lifecycle = metadata.get("lifecycle")
    if not isinstance(lifecycle, Mapping):
        raise ArchitectMetadataError("Operation metadata needs a lifecycle object", reason_code="invalid_verification_metadata")
    try:
        resolve_lifecycle_policy(lifecycle)
    except LifecyclePolicyError as exc:
        raise ArchitectMetadataError(str(exc), reason_code=exc.reason_code) from exc
    for direction in ("inputs", "outputs"):
        if not isinstance(metadata.get(direction), list):
            raise ArchitectMetadataError(
                f"Operation metadata {direction} must be a list", reason_code="invalid_verification_metadata"
            )
        for binding in metadata[direction]:
            if not isinstance(binding, Mapping):
                raise ArchitectMetadataError(
                    f"Operation metadata {direction} entries must be mappings", reason_code="invalid_verification_metadata"
                )
            needed = {
                "data_object", "object_role", "direction", "data_type",
                "dimensions", "channel", "protocol_profile", "signals", "serialization",
            }
            absent = sorted(needed - set(binding))
            if absent:
                raise ArchitectMetadataError(
                    f"Binding {binding.get('data_object')!r} is missing {absent}", reason_code="invalid_verification_metadata"
                )
            try:
                declared_serialization(
                    {"name": binding["data_object"], "dimensions": binding["dimensions"], "serialization": binding["serialization"]},
                    dimension_extents={
                        str(name): int(extent)
                        for name, extent in metadata.get("dimensions", {}).items()
                        # An unresolved extent (None) is unknown, exactly as `_binding`
                        # treats a dimension that is not fixed; it is not an error here.
                        if extent is not None
                    },
                    element_width_bits=int(binding["data_type"]["width_bits"]),
                )
            except ValueError as exc:
                raise ArchitectMetadataError(
                    str(exc), reason_code="invalid_data_object_serialization"
                ) from exc
    arithmetic = metadata.get("arithmetic")
    if not isinstance(arithmetic, Mapping) or "classifier_profile" not in arithmetic:
        raise ArchitectMetadataError(
            "Operation metadata needs arithmetic.classifier_profile",
            reason_code="invalid_arithmetic_declaration",
        )
    try:
        validate_resolved_arithmetic(metadata)
    except (ArithmeticMetadataError, KeyError, TypeError, ValueError) as exc:
        raise ArchitectMetadataError(
            str(exc), reason_code="invalid_arithmetic_declaration"
        ) from exc
    if arithmetic.get("classifier_profile") == "integer_matrix_multiply":
        exact_fields = {
            "accumulator_data_type",
            "product_data_type",
            "accumulator_initialization",
            "reduction_order",
            "reduction_conversion",
            "bias_conversion",
            "result_data_type",
            "stage_order",
            "resolved_stage_order",
            "support_status",
        }
        absent = sorted(exact_fields - set(arithmetic))
        if absent:
            raise ArchitectMetadataError(
                f"integer_matrix_multiply arithmetic metadata is missing {absent}",
                reason_code="invalid_arithmetic_declaration",
            )
