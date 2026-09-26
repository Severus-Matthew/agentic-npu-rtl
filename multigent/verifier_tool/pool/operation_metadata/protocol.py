"""Code-owned protocol adapters that capture accepted logical values."""

from __future__ import annotations

from collections import deque
from math import prod
from typing import Any, Mapping
from .io_metadata import require_supported_serialization
from .packed_encoding import pack_words

from multigent.verifier_tool.protocol.assertion.axi import (
    axi_lane_mask,
    axi_transfer_windows,
)
from multigent.verifier_tool.pool.role_pool.standard_protocols import (
    compile_standard_protocol_plan,
    enrich_standard_protocol_metadata,
)


class ProtocolAdapterError(AssertionError):
    """Machine-readable interface roles do not form a usable protocol adapter."""


class ReadyValidCaptureAdapter:
    """Capture payloads on role-bound ready/valid transfers.

    The shared contract monitor calls this at its pre-active-edge snapshot. Under
    the enforced TB driving discipline, those stable values are the transfer seen
    at the following active edge. Reset clears every partial job.
    """

    def __init__(self, interface: Mapping[str, Any]) -> None:
        interface = enrich_standard_protocol_metadata(interface)
        signals = [item for item in interface.get("signals", []) if isinstance(item, Mapping)]
        signals_by_name = {str(item.get("name", "")): item for item in signals}
        self.channels: dict[str, dict[str, Any]] = {}
        for channel in interface.get("channels", []):
            if not isinstance(channel, Mapping) or channel.get("protocol_profile") != "ready_valid":
                continue
            name = str(channel.get("name", ""))
            role_items: dict[str, list[Mapping[str, Any]]] = {}
            for signal in signals:
                if signal.get("channel") == name:
                    role_items.setdefault(str(signal.get("role", "")), []).append(signal)
            if any(len(role_items.get(role, [])) != 1 for role in ("valid", "ready")):
                raise ProtocolAdapterError(
                    f"ready_valid channel {name!r} needs one valid and one ready role"
                )
            payloads = role_items.get("payload", [])
            if len(payloads) > 1:
                raise ProtocolAdapterError(
                    f"ready_valid channel {name!r} has multiple payload signals"
                )
            fields: dict[str, Mapping[str, Any]] = {}
            if payloads:
                fields["payload"] = payloads[0]
            for role in ("last", "keep", "strb", "transaction_id", "metadata"):
                items = role_items.get(role, [])
                if len(items) == 1:
                    fields[role] = items[0]
                elif len(items) > 1:
                    for item in items:
                        fields[str(item.get("name", ""))] = item
            self.channels[name] = {
                "direction": str(channel.get("direction", "")),
                "valid": str(role_items["valid"][0]["name"]),
                "ready": str(role_items["ready"][0]["name"]),
                "profile": "ready_valid",
                "kind": name,
                "protocol_group": "contract_ready_valid",
                "fields": fields,
                "primary_field": "payload" if payloads else None,
            }
        standard = compile_standard_protocol_plan(interface)
        for group in standard.get("groups", []):
            for channel in group.get("channels", {}).values():
                name = str(channel.get("name", ""))
                if name in self.channels:
                    raise ProtocolAdapterError(
                        f"protocol channel {name!r} is compiled more than once"
                    )
                fields = {
                    str(field): signals_by_name[str(signal_name)]
                    for field, signal_name in channel.get("fields", {}).items()
                    if str(signal_name) in signals_by_name
                }
                primary = next(
                    (
                        field for field in ("data", "addr", "resp")
                        if field in fields
                    ),
                    None,
                )
                self.channels[name] = {
                    "direction": str(channel.get("direction", "")),
                    "valid": str(channel.get("valid", "")),
                    "ready": str(channel.get("ready", "")),
                    "profile": str(group.get("profile", "")),
                    "kind": str(channel.get("kind", "")),
                    "protocol_group": str(group.get("name", "")),
                    "fields": fields,
                    "primary_field": primary,
                }
        self.values: dict[str, list[int]] = {}
        self.events: dict[str, list[dict[str, Any]]] = {}

    def reset(self) -> None:
        self.values.clear()
        self.events.clear()

    @staticmethod
    def _decode(value: int, signal: Mapping[str, Any]) -> int:
        width_raw = str(signal.get("width", ""))
        if not width_raw.isdigit():
            return int(value)
        width = int(width_raw)
        decoded = int(value) & ((1 << width) - 1)
        if bool(signal.get("signed")) and decoded & (1 << (width - 1)):
            decoded -= 1 << width
        return decoded

    def observe(
        self,
        snapshot: Mapping[str, int],
        *,
        event_sequence: int = 0,
        reset_epoch: int = 0,
    ) -> None:
        for name, channel in self.channels.items():
            if not (
                bool(snapshot.get(channel["valid"], 0))
                and bool(snapshot.get(channel["ready"], 0))
            ):
                continue
            field_values: dict[str, int] = {}
            signal_values: dict[str, int] = {}
            for field, signal in channel["fields"].items():
                signal_name = str(signal.get("name", ""))
                if signal_name not in snapshot:
                    raise ProtocolAdapterError(
                        f"Snapshot is missing {field} signal {signal_name!r} for {name!r}"
                    )
                value = self._decode(int(snapshot[signal_name]), signal)
                field_values[str(field)] = value
                signal_values[signal_name] = value
            primary = channel.get("primary_field")
            if primary is not None:
                self.values.setdefault(name, []).append(field_values[str(primary)])
            event: dict[str, Any] = {
                "channel": name,
                "acceptance_event_sequence": int(event_sequence),
                "reset_epoch": int(reset_epoch),
                "signal_values": signal_values,
                **field_values,
            }
            if primary is not None:
                event["value"] = field_values[str(primary)]
            self.events.setdefault(name, []).append(event)

    @staticmethod
    def _expected_elements(
        binding: Mapping[str, Any], dimensions: Mapping[str, Any]
    ) -> int:
        extents = [dimensions.get(str(axis)) for axis in binding.get("dimensions", [])]
        if extents and all(isinstance(value, int) and value > 0 for value in extents):
            return prod(map(int, extents))
        if not extents:
            return 1
        raise ProtocolAdapterError(
            f"binding {binding.get('data_object')!r} has unresolved dimensions {extents!r}"
        )

    def _command_event(self, operation: Mapping[str, Any]) -> Mapping[str, Any]:
        commands = list(operation.get("lifecycle", {}).get("job_accept_channels", []))
        if len(commands) != 1:
            raise ProtocolAdapterError("memory operation needs one command channel")
        events = self.events.get(str(commands[0].get("channel", "")), [])
        if len(events) != 1:
            raise ProtocolAdapterError(
                f"memory operation needs exactly one accepted command, found {len(events)}"
            )
        return events[0]

    def _control_plane_object_bases(self, operation: Mapping[str, Any]) -> dict[str, int]:
        """Recover base pointers from accepted register writes, never planned values."""

        sequence = operation.get("lifecycle", {}).get("control_plane_sequence")
        if not isinstance(sequence, Mapping):
            raise ProtocolAdapterError("control-plane job has no register sequence")
        groups = {
            str(channel["protocol_group"])
            for channel in self.channels.values()
            if channel.get("profile") == "axi4_lite"
            and channel.get("kind") == "write_address"
            and channel.get("direction") == "input"
        }
        if len(groups) != 1:
            raise ProtocolAdapterError(
                f"control-plane job needs one AXI4-Lite subordinate group, found {len(groups)}"
            )
        group = next(iter(groups))

        def events(kind: str) -> list[dict[str, Any]]:
            matches = [
                self.events.get(name, [])
                for name, channel in self.channels.items()
                if channel.get("protocol_group") == group and channel.get("kind") == kind
            ]
            if len(matches) != 1:
                raise ProtocolAdapterError(f"control-plane group {group!r} lacks one {kind} channel")
            return matches[0]

        addresses = events("write_address")
        data = events("write_data")
        responses = events("write_response")
        actions = list(sequence.get("job_start", {}).get("actions", []))
        if len(addresses) != len(actions) or len(data) != len(actions) or len(responses) != len(actions):
            raise ProtocolAdapterError(
                "control-plane job needs one accepted AW, W, and B per declared start action"
            )
        registers = sequence.get("registers", {})
        halves: dict[str, dict[str, int]] = {}
        for index, action in enumerate(actions):
            register = registers[str(action["register"])]
            address = int(register["address"])
            if int(addresses[index].get("addr", -1)) != address:
                raise ProtocolAdapterError(
                    f"control-plane write {index} did not target declared register {address:#x}"
                )
            if int(responses[index].get("resp", -1)) != 0:
                raise ProtocolAdapterError("control-plane register write returned non-OKAY response")
            value = int(data[index].get("data", -1))
            if action["op"] == "write_reg":
                source = action["value_from"]
                if source.get("address_role") != "base" or source.get("half") not in {"low", "high"}:
                    raise ProtocolAdapterError("unsupported control-plane pointer write")
                object_name = str(source["data_object"])
                halves.setdefault(object_name, {})[str(source["half"])] = value
            elif action["op"] == "write_field":
                bit = int(register["fields"][str(action["field"])]["bit"])
                if ((value >> bit) & 1) != (int(action["value"]) & 1):
                    raise ProtocolAdapterError("control-plane start field was not accepted as declared")
            else:
                raise ProtocolAdapterError(f"unsupported control-plane start action {action['op']!r}")
        if any(set(parts) != {"low", "high"} for parts in halves.values()):
            raise ProtocolAdapterError("control-plane pointer lacks an accepted high or low half")
        return {
            name: int(parts["low"]) | (int(parts["high"]) << 32)
            for name, parts in halves.items()
        }

    @staticmethod
    def _decode_words(
        words: list[int], binding: Mapping[str, Any], expected_elements: int
    ) -> list[int]:
        mapping = binding.get("memory_mapping", {})
        width = int(binding.get("data_type", {}).get("width_bits", 0))
        signed = bool(binding.get("data_type", {}).get("signed"))
        per_word = int(mapping.get("elements_per_word", 0))
        if width <= 0 or per_word <= 0 or mapping.get("byte_order") != "little":
            raise ProtocolAdapterError(
                f"binding {binding.get('data_object')!r} lacks supported little-endian packing"
            )
        mask = (1 << width) - 1
        result: list[int] = []
        for word in words:
            for lane in range(per_word):
                value = (int(word) >> (lane * width)) & mask
                if signed and value & (1 << (width - 1)):
                    value -= 1 << width
                result.append(value)
        return result[:expected_elements]

    def _consume_memory_objects(
        self, operation: Mapping[str, Any], direction: str,
        planned_inputs: Mapping[str, Any] | None = None,
    ) -> dict[str, list[int]]:
        all_bindings = [
            item
            for item in operation.get("inputs" if direction == "input" else "outputs", [])
            if item.get("protocol_profile") in {"axi4_lite", "axi4", "custom_mmio"}
        ]
        if not all_bindings:
            return {}
        if any(not isinstance(item.get("memory_mapping"), Mapping) for item in all_bindings):
            raise ProtocolAdapterError("memory-mapped operation binding lacks memory_mapping")
        control_plane = (
            operation.get("lifecycle", {}).get("policy", {}).get("job_acceptance")
            == "control_plane_sequence"
        )
        object_bases = self._control_plane_object_bases(operation) if control_plane else None
        command_values = {} if control_plane else self._command_event(operation).get("signal_values", {})
        dimensions = operation.get("dimensions", {})
        result: dict[str, list[int]] = {}
        lite_bindings = [b for b in all_bindings if b["protocol_profile"] == "axi4_lite"]
        burst_bindings = [
            b for b in all_bindings if b["protocol_profile"] in {"axi4", "custom_mmio"}
        ]
        if lite_bindings:
            result.update(
                self._consume_axi4_lite_objects(lite_bindings, command_values, dimensions, direction)
            )
        if burst_bindings:
            # One operation may use several independent AXI4 manager ports
            # (HLS GEMM has separate gmem_a/gmem_b reads). Requests and data
            # must be attributed within their own physical protocol group;
            # only objects sharing a bus may be reassembled together.
            by_bus: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
            for binding in burst_bindings:
                mapping = binding["memory_mapping"]
                key = (
                    str(mapping["address_channel"]),
                    str(mapping["data_channel"]),
                    str(mapping.get("response_channel", "")),
                )
                by_bus.setdefault(key, []).append(binding)
            for bus_bindings in by_bus.values():
                result.update(
                    self._consume_burst_memory_objects(
                        bus_bindings, command_values, dimensions, direction,
                        object_bases=object_bases,
                    )
                )
        if direction == "input":
            for binding in all_bindings:
                name = str(binding["data_object"])
                if binding.get("serialization", {}).get("kind") != "packed_encoding":
                    continue
                if planned_inputs is None or name not in planned_inputs:
                    raise ProtocolAdapterError(f"packed input {name!r} lacks planned canonical values")
                planned = list(map(int, planned_inputs[name]))
                physical = pack_words(
                    binding["serialization"], binding["dimensions"], dimensions, planned,
                )
                if result[name] != physical:
                    raise ProtocolAdapterError(
                        f"accepted packed input {name!r} differs from its canonical stimulus encoding"
                    )
                result[name] = planned
        return result

    def _consume_axi4_lite_objects(
        self,
        bindings: list[Mapping[str, Any]],
        command_values: Mapping[str, int],
        dimensions: Mapping[str, Any],
        direction: str,
    ) -> dict[str, list[int]]:
        """Single-outstanding, strict-request-order AXI4-Lite capture.

        AXI4-Lite has no ID and no burst LAST; the only way to know which
        word belongs to which object is that every object's addresses are
        issued back-to-back, in the exact order objects were bound, with
        nothing else interleaved. This is unchanged from before ``axi4``
        (multi-outstanding, ID-correlated) support was added.
        """
        result: dict[str, list[int]] = {}
        expected_address_sequence: list[int] = []
        segments: list[tuple[Mapping[str, Any], int, int]] = []
        for binding in bindings:
            mapping = binding["memory_mapping"]
            base_signal = str(mapping["base_signal"])
            if base_signal not in command_values:
                raise ProtocolAdapterError(
                    f"accepted command is missing base pointer {base_signal!r}"
                )
            expected_elements = self._expected_elements(binding, dimensions)
            per_word = int(mapping["elements_per_word"])
            word_count = (expected_elements + per_word - 1) // per_word
            stride = int(mapping["word_stride_bytes"])
            start = len(expected_address_sequence)
            expected_address_sequence.extend(
                int(command_values[base_signal]) + stride * index
                for index in range(word_count)
            )
            segments.append((binding, start, word_count))

        first_mapping = bindings[0]["memory_mapping"]
        if direction == "input":
            address_events = self.events.get(str(first_mapping["address_channel"]), [])
            data_events = self.events.get(str(first_mapping["data_channel"]), [])
            if len(address_events) != len(data_events):
                raise ProtocolAdapterError(
                    f"AXI read address/data counts differ: {len(address_events)} != {len(data_events)}"
                )
            observed_addresses = [int(item.get("addr", -1)) for item in address_events]
            if observed_addresses != expected_address_sequence:
                raise ProtocolAdapterError(
                    "AXI read addresses differ from exact object mapping; "
                    f"expected={expected_address_sequence!r} observed={observed_addresses!r}"
                )
            if any(int(item.get("resp", -1)) != 0 for item in data_events):
                raise ProtocolAdapterError("successful checked job contains a non-OKAY RRESP")
            words = [int(item.get("data", 0)) for item in data_events]
        else:
            address_events = self.events.get(str(first_mapping["address_channel"]), [])
            data_events = self.events.get(str(first_mapping["data_channel"]), [])
            response_events = self.events.get(str(first_mapping["response_channel"]), [])
            if not (len(address_events) == len(data_events) == len(response_events)):
                raise ProtocolAdapterError(
                    "AXI write AW/W/B counts differ: "
                    f"{len(address_events)}/{len(data_events)}/{len(response_events)}"
                )
            observed_addresses = [int(item.get("addr", -1)) for item in address_events]
            if observed_addresses != expected_address_sequence:
                raise ProtocolAdapterError(
                    "AXI write addresses differ from exact object mapping; "
                    f"expected={expected_address_sequence!r} observed={observed_addresses!r}"
                )
            full_strobe = (1 << (int(first_mapping["bus_width_bits"]) // 8)) - 1
            if any(int(item.get("strb", -1)) != full_strobe for item in data_events):
                raise ProtocolAdapterError("checked AXI output contains a non-full WSTRB")
            if any(int(item.get("resp", -1)) != 0 for item in response_events):
                raise ProtocolAdapterError("successful checked job contains a non-OKAY BRESP")
            words = [int(item.get("data", 0)) for item in data_events]

        for binding, start, word_count in segments:
            expected_elements = self._expected_elements(binding, dimensions)
            result[str(binding["data_object"])] = self._decode_words(
                words[start : start + word_count], binding, expected_elements
            )
        return result

    def _decode_axi4_bursts(
        self,
        bindings: list[Mapping[str, Any]],
        windows: list[tuple[int, int, Mapping[str, Any], int]],
        bursts: list[tuple[Mapping[str, Any], list[Mapping[str, Any]]]],
        dimensions: Mapping[str, Any],
        direction: str,
    ) -> dict[str, list[int]]:
        """Reassemble AXI4 bytes from accepted AxSIZE/STRB-selected lanes."""

        images: dict[str, bytearray] = {}
        visited: dict[str, bytearray] = {}
        for low, high, binding, stride in windows:
            name = str(binding["data_object"])
            bus_bytes = int(binding["memory_mapping"]["bus_width_bits"]) // 8
            if stride != bus_bytes:
                raise ProtocolAdapterError(
                    f"AXI4 object {name!r} needs one bus-width canonical word per stride"
                )
            images[name] = bytearray(high - low)
            visited[name] = bytearray(high - low)

        for request, beats in bursts:
            address = int(request.get("addr", -1))
            match = next(
                ((low, high, binding) for low, high, binding, _stride in windows
                 if low <= address < high),
                None,
            )
            if match is None:
                raise ProtocolAdapterError(
                    f"AXI4 {direction} request address {address} is not inside any bound data object"
                )
            low, high, binding = match
            name = str(binding["data_object"])
            bus_bytes = int(binding["memory_mapping"]["bus_width_bits"]) // 8
            size = int(request.get("size", bus_bytes.bit_length() - 1))
            transfer_bytes = 1 << size
            if transfer_bytes > bus_bytes:
                raise ProtocolAdapterError(
                    f"AXI4 {direction} transfer size {transfer_bytes} exceeds bus width {bus_bytes}"
                )
            length = int(request.get("len", len(beats) - 1)) + 1
            if length != len(beats):
                raise ProtocolAdapterError(
                    f"AXI4 {direction} length declares {length} beats but {len(beats)} were accepted"
                )
            try:
                windows_for_burst = axi_transfer_windows(
                    {"addr": address, "len": length - 1, "size": size,
                     "burst": int(request.get("burst", 1))}
                )
            except ValueError as exc:
                raise ProtocolAdapterError(str(exc)) from exc
            for window, beat in zip(windows_for_burst, beats):
                beat_address, beat_last = window
                active_bytes = beat_last - beat_address + 1
                if beat_address < low or beat_last >= high:
                    raise ProtocolAdapterError(
                        f"AXI4 {direction} beat at {beat_address} crosses object {name!r} window"
                    )
                lane = beat_address % bus_bytes
                active_strobe = axi_lane_mask(window, bus_bytes)
                if direction == "output" and int(beat.get("strb", -1)) != active_strobe:
                    raise ProtocolAdapterError(
                        f"AXI4 output WSTRB at {beat_address} does not select active lanes "
                        f"{active_strobe:#x}"
                    )
                data = int(beat.get("data", 0)).to_bytes(bus_bytes, "little")
                for offset in range(active_bytes):
                    position = beat_address + offset - low
                    if visited[name][position]:
                        raise ProtocolAdapterError(
                            f"AXI4 {direction} duplicated byte {low + position} of {name!r}"
                        )
                    visited[name][position] = 1
                    images[name][position] = data[lane + offset]

        result: dict[str, list[int]] = {}
        for low, high, binding, _stride in windows:
            name = str(binding["data_object"])
            if not all(visited[name]):
                missing = [low + index for index, hit in enumerate(visited[name]) if not hit]
                captured_addresses = [
                    int(request.get("addr", -1))
                    for request, _beats in bursts
                    if low <= int(request.get("addr", -1)) < high
                ]
                raise ProtocolAdapterError(
                    f"AXI4 {direction} omitted bytes of {name!r}: {missing[:8]!r}; "
                    f"captured_requests={len(captured_addresses)} "
                    f"first_addresses={captured_addresses[:8]!r}"
                )
            bus_bytes = int(binding["memory_mapping"]["bus_width_bits"]) // 8
            words = [
                int.from_bytes(images[name][index : index + bus_bytes], "little")
                for index in range(0, high - low, bus_bytes)
            ]
            result[name] = (
                words if binding.get("serialization", {}).get("kind") == "packed_encoding"
                else self._decode_words(words, binding, self._expected_elements(binding, dimensions))
            )
        return result

    def _consume_burst_memory_objects(
        self,
        bindings: list[Mapping[str, Any]],
        command_values: Mapping[str, int],
        dimensions: Mapping[str, Any],
        direction: str,
        *,
        object_bases: Mapping[str, int] | None = None,
    ) -> dict[str, list[int]]:
        """Multi-outstanding, ID-correlated, burst-aware memory capture.

        Shared by full AXI4 (``protocol_profile: axi4``) and any
        LLM-declared custom memory-like protocol (``protocol_profile:
        custom_mmio``). Address and response attribution uses role-decoded
        event keys, never channel or signal spelling. AXI4 write data needs
        one profile-specific pairing rule: W has no ID, so W bursts pair with
        AW requests in issue order; B responses still pair by BID.

        Unlike AXI4-Lite, this permits several simultaneously outstanding
        requests whose responses may complete in a different order than they
        were issued; requests sharing the same ID are guaranteed to complete
        in issue order relative to each other, and each request's data may
        span multiple beats terminated by LAST. This never assumes overall
        arrival order matches issue order or that word N belongs to object X
        merely because it was the Nth response observed. Instead it: (1)
        pairs each completed read burst (a run of same-ID beats ending in LAST)
        with the oldest still-unmatched request carrying that same ID, using
        the request's own captured address, not response position; then (2)
        attributes that burst to whichever bound object's declared address
        window contains that address. A design that never issues more than
        one outstanding request, or never sets ID at all (captured as a
        single ``None`` id group), degenerates to the same strict in-order
        behavior as AXI4-Lite through this same code path. A write binding
        whose ``memory_mapping`` has no ``response_channel`` (a custom
        protocol declaring no separate completion-ack channel) treats
        acceptance onto the data channel itself, plus that beat's own
        optional ``resp`` field, as the completion signal.
        """
        windows: list[tuple[int, int, Mapping[str, Any], int]] = []
        next_expected: dict[str, int] = {}
        for binding in bindings:
            mapping = binding["memory_mapping"]
            object_name = str(binding["data_object"])
            if object_bases is None:
                base_signal = str(mapping["base_signal"])
                if base_signal not in command_values:
                    raise ProtocolAdapterError(
                        f"accepted command is missing base pointer {base_signal!r}"
                    )
                base = int(command_values[base_signal])
            else:
                if object_name not in object_bases:
                    raise ProtocolAdapterError(f"control-plane job lacks base pointer for {object_name!r}")
                base = int(object_bases[object_name])
            expected_elements = self._expected_elements(binding, dimensions)
            per_word = int(mapping["elements_per_word"])
            word_count = (expected_elements + per_word - 1) // per_word
            stride = int(mapping["word_stride_bytes"])
            windows.append((base, base + stride * word_count, binding, stride))
            next_expected[str(binding["data_object"])] = base

        first_mapping = bindings[0]["memory_mapping"]
        request_channel = str(first_mapping["address_channel"])
        data_channel = str(first_mapping["data_channel"])
        requests = self.events.get(request_channel, [])
        data_beats = self.events.get(data_channel, [])

        bursts: list[tuple[Mapping[str, Any], list[Mapping[str, Any]]]] = []
        if direction == "output" and first_mapping.get("protocol_profile") == "axi4":
            # AXI4 deliberately has no WID. W bursts follow AW issue order,
            # even when B responses later complete out of order by BID.
            pending_aw = deque(requests)
            current_w: list[Mapping[str, Any]] = []
            for beat in data_beats:
                if not pending_aw:
                    raise ProtocolAdapterError(
                        f"burst channel {data_channel!r} has W data without a matching AW request"
                    )
                current_w.append(beat)
                if bool(beat.get("last", 1)):
                    bursts.append((pending_aw.popleft(), current_w))
                    current_w = []
            if current_w or pending_aw:
                raise ProtocolAdapterError(
                    f"write requests without completed W bursts: pending_aw={len(pending_aw)}, "
                    f"partial_w_beats={len(current_w)}"
                )
        else:
            pending: dict[Any, deque[Mapping[str, Any]]] = {}
            for event in requests:
                pending.setdefault(event.get("id"), deque()).append(event)

            accumulating: dict[Any, list[Mapping[str, Any]]] = {}
            for beat in data_beats:
                beat_id = beat.get("id")
                group = accumulating.setdefault(beat_id, [])
                group.append(beat)
                # A channel with no bound LAST field (should not happen for a
                # real "read_data"/"write_data" AXI4 channel, both of which
                # require it) is treated as single-beat, i.e. always-last.
                if bool(beat.get("last", 1)):
                    queue = pending.get(beat_id)
                    if not queue:
                        raise ProtocolAdapterError(
                            f"burst channel {data_channel!r} completed a transfer for id={beat_id!r} "
                            "with no matching outstanding request"
                        )
                    bursts.append((queue.popleft(), accumulating.pop(beat_id)))

            unmatched = {key: len(queue) for key, queue in pending.items() if queue}
            if unmatched:
                raise ProtocolAdapterError(
                    f"{'read' if direction == 'input' else 'write'} requests without a "
                    f"completed response: {unmatched}"
                )

        if direction == "input":
            for _request, beats in bursts:
                if any(int(beat.get("resp", 0)) != 0 for beat in beats):
                    raise ProtocolAdapterError("successful checked job contains a non-OKAY RRESP")
        else:
            response_channel = first_mapping.get("response_channel")
            full_strobe = (1 << (int(first_mapping["bus_width_bits"]) // 8)) - 1
            b_queues: dict[Any, deque[Mapping[str, Any]]] = {}
            if response_channel is not None:
                for event in self.events.get(str(response_channel), []):
                    b_queues.setdefault(event.get("id"), deque()).append(event)
            for request, beats in bursts:
                if response_channel is not None:
                    queue = b_queues.get(request.get("id"))
                    if not queue:
                        raise ProtocolAdapterError(
                            f"write request id={request.get('id')!r} has no matching "
                            "write-response event"
                        )
                    if int(queue.popleft().get("resp", 0)) != 0:
                        raise ProtocolAdapterError(
                            "successful checked job contains a non-OKAY write response"
                        )
                elif any(int(beat.get("resp", 0)) != 0 for beat in beats):
                    raise ProtocolAdapterError(
                        "successful checked job contains a non-OKAY write response"
                    )
                if first_mapping.get("protocol_profile") != "axi4" and any(
                    int(beat.get("strb", full_strobe)) != full_strobe for beat in beats
                ):
                    raise ProtocolAdapterError("checked output contains a non-full write-strobe")

        if first_mapping.get("protocol_profile") == "axi4":
            return self._decode_axi4_bursts(
                bindings, windows, bursts, dimensions, direction
            )

        per_object_words: dict[str, list[int]] = {
            str(binding["data_object"]): [] for binding in bindings
        }
        for request, beats in sorted(bursts, key=lambda item: int(item[0].get("addr", -1))):
            address = int(request.get("addr", -1))
            match = next(
                ((lo, hi, binding, stride) for lo, hi, binding, stride in windows if lo <= address < hi),
                None,
            )
            if match is None:
                raise ProtocolAdapterError(
                    f"{'read' if direction == 'input' else 'write'} address {address} "
                    "is not inside any bound data object's expected range"
                )
            _lo, _hi, binding, stride = match
            object_name = str(binding["data_object"])
            if address != next_expected[object_name]:
                raise ProtocolAdapterError(
                    f"burst base address {address} is not the next expected word for "
                    f"{object_name!r} (expected {next_expected[object_name]})"
                )
            next_expected[object_name] = address + stride * len(beats)
            per_object_words[object_name].extend(int(beat.get("data", 0)) for beat in beats)

        result: dict[str, list[int]] = {}
        for binding in bindings:
            object_name = str(binding["data_object"])
            expected_elements = self._expected_elements(binding, dimensions)
            result[object_name] = self._decode_words(
                per_object_words[object_name], binding, expected_elements
            )
        return result

    def consume_operation_inputs(
        self, operation_metadata: Mapping[str, Any],
        planned_inputs: Mapping[str, Any] | None = None,
    ) -> dict[str, list[int]]:
        """Return captured input objects for one operation without guessing names."""

        self._validate_serialization(operation_metadata.get("inputs", []))
        result: dict[str, list[int]] = {}
        for binding in operation_metadata.get("inputs", []):
            if binding.get("protocol_profile") in {"axi4_lite", "axi4", "custom_mmio"}:
                return self._consume_memory_objects(operation_metadata, "input", planned_inputs)
            channel = str(binding.get("channel", ""))
            values = self.values.get(channel)
            if values:
                result[str(binding["data_object"])] = list(values)
        return result

    def consume_operation_outputs(
        self, operation_metadata: Mapping[str, Any]
    ) -> dict[str, list[int]]:
        """Return role-bound accepted output objects without trusting TB values."""

        self._validate_serialization(operation_metadata.get("outputs", []))
        result: dict[str, list[int]] = {}
        for binding in operation_metadata.get("outputs", []):
            if binding.get("protocol_profile") in {"axi4_lite", "axi4", "custom_mmio"}:
                return self._consume_memory_objects(operation_metadata, "output")
            channel = str(binding.get("channel", ""))
            if channel in self.values:
                result[str(binding["data_object"])] = list(self.values[channel])
        return result

    @staticmethod
    def _validate_serialization(bindings: list[Mapping[str, Any]]) -> None:
        for binding in bindings:
            try:
                require_supported_serialization(binding)
            except ValueError as exc:
                raise ProtocolAdapterError(str(exc)) from exc

    def snapshot(self) -> dict[str, list[int]]:
        return {name: list(values) for name, values in self.values.items()}

    def event_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {
            name: [dict(event) for event in events]
            for name, events in self.events.items()
        }
