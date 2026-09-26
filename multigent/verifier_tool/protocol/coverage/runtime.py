"""Temporal sampling for protocol coverage obligations."""

from __future__ import annotations

from typing import Any, Mapping

from multigent.verifier_tool.protocol.assertion.axi import axi_transfer_windows


_SPECIAL_TEMPLATES = frozenset(
    {
        "handshake_arrival_order",
        "axi4_4k_boundary",
        "axi4_burst_type",
        "axi4_burst_length",
        "axi4_transfer_size",
        "axi4_alignment",
        "axi4_write_strobe",
        "axi4_write_channel_order",
        "axi4_response_code",
        "axi4_outstanding_depth",
        "axi4_sideband_partition",
        "axi_lite_write_channel_order",
        "axi_lite_write_strobe",
        "axi_lite_response_code",
        "axi_lite_read_write_concurrency",
        "axi_lite_address_partition",
        "axi_lite_protection_partition",
        "axi_lite_outstanding_depth",
        "axis_packet_length",
        "axis_keep_pattern",
        "axis_stall_position",
        "axis_back_to_back_packets",
        "axis_sideband_partition",
    }
)


def protocol_runtime_templates() -> frozenset[str]:
    return _SPECIAL_TEMPLATES


class ProtocolCoverageMonitor:
    """Convert observed transfers and temporal relations into named bin hits."""

    def __init__(self, plan: Mapping[str, Any]) -> None:
        self.obligations = {
            str(item["id"]): dict(item)
            for item in plan.get("obligations", [])
            if item.get("template") in _SPECIAL_TEMPLATES
        }
        self.state: dict[str, Any] = {}
        self.cycle = 0

    def reset(self) -> None:
        self.state.clear()
        self.cycle = 0

    @staticmethod
    def _read(snapshot: Mapping[str, Any], name: str) -> int:
        if name not in snapshot:
            raise ValueError(f"protocol coverage snapshot is missing {name!r}")
        return int(snapshot[name])

    def _transfer(self, snapshot: Mapping[str, Any], channel: Mapping[str, Any]) -> bool:
        ready = channel.get("ready")
        return bool(self._read(snapshot, str(channel["valid"]))) and (
            True if ready in {None, ""} else bool(self._read(snapshot, str(ready)))
        )

    def _field(
        self, snapshot: Mapping[str, Any], channel: Mapping[str, Any], field: str, default: int = 0
    ) -> int:
        name = channel.get("fields", {}).get(field)
        return self._read(snapshot, str(name)) if name else default

    def _handshake_order(
        self,
        obligation_id: str,
        snapshot: Mapping[str, Any],
        obligation: Mapping[str, Any],
    ) -> list[str]:
        bindings = obligation.get("bindings", {})
        event_bins = {
            str(item.get("event", "")): str(item.get("name", ""))
            for item in obligation.get("bins", [])
            if isinstance(item, Mapping)
        }
        required_events = {"simultaneous", "valid_before_ready", "ready_before_valid"}
        if not required_events <= set(event_bins):
            raise ValueError(
                f"{obligation_id} needs machine-readable arrival-order event bins"
            )
        valid = bool(self._read(snapshot, str(bindings["valid"])))
        ready = bool(self._read(snapshot, str(bindings["ready"])))
        key = f"arrival:{obligation_id}"
        previous = self.state.get(key)
        hits: list[str] = []
        if valid and ready:
            event = (
                "valid_before_ready"
                if previous == "valid"
                else "ready_before_valid"
                if previous == "ready"
                else "simultaneous"
            )
            hits.append(event_bins[event])
            self.state.pop(key, None)
        elif valid:
            self.state[key] = "valid"
        elif ready:
            self.state[key] = "ready"
        else:
            self.state.pop(key, None)
        return hits

    def _address_hits(
        self, template: str, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        channel = {
            "valid": bindings["valid"],
            "ready": bindings["ready"],
            "fields": bindings["fields"],
        }
        if not self._transfer(snapshot, channel):
            return []
        address = self._field(snapshot, channel, "addr")
        length = self._field(snapshot, channel, "len")
        size = self._field(snapshot, channel, "size")
        burst = self._field(snapshot, channel, "burst")
        if template == "axi4_burst_type":
            return [{0: "fixed", 1: "incrementing", 2: "wrapping"}[burst]] if burst in {0, 1, 2} else []
        if template == "axi4_burst_length":
            beats = length + 1
            return ["single" if beats == 1 else "two_to_sixteen" if beats <= 16 else "seventeen_to_256"]
        if template == "axi4_transfer_size":
            transfer_bytes = 1 << size
            data_width = bindings.get("data_width")
            if not isinstance(data_width, int):
                data_kind = (
                    "write_data"
                    if bindings.get("protocol_channel") == "write_address"
                    else "read_data"
                )
                data_signal = bindings.get("channels", {}).get(data_kind, {}).get("fields", {}).get("data")
                data_width = getattr(snapshot, "widths", {}).get(data_signal)
            bus_bytes = int(data_width) // 8 if isinstance(data_width, int) and data_width > 0 else None
            hits = ["one_byte"] if transfer_bytes == 1 else []
            if bus_bytes is not None:
                if transfer_bytes < bus_bytes and transfer_bytes > 1:
                    hits.append("narrow")
                if transfer_bytes == bus_bytes:
                    hits.append("full_width")
            return hits
        if template == "axi4_alignment":
            return ["aligned" if address % (1 << size) == 0 else "unaligned"]
        if template == "axi4_4k_boundary":
            windows = axi_transfer_windows(
                {"addr": address, "len": length, "size": size, "burst": burst}
            )
            page = windows[0][0] >> 12
            if any(
                low >> 12 != page or high >> 12 != page
                for low, high in windows
            ):
                return ["would_cross_boundary"]
            last = max(high for _, high in windows)
            return ["ends_at_boundary" if (last & 0xFFF) == 0xFFF else "ends_before_boundary"]
        return []

    def _strobe_hits(
        self, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        channel = {
            "valid": bindings["valid"],
            "ready": bindings["ready"],
            "fields": bindings["fields"],
        }
        if not self._transfer(snapshot, channel):
            return []
        value = self._field(snapshot, channel, "strb")
        width = bindings.get("widths", {}).get("strb")
        if not isinstance(width, int):
            width = getattr(snapshot, "widths", {}).get(bindings.get("fields", {}).get("strb"))
        full = (1 << int(width)) - 1 if isinstance(width, int) and width > 0 else None
        return ["all_zero" if value == 0 else "full" if full is not None and value == full else "sparse"]

    def _field_partition_hits(
        self, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        channel = {
            "valid": bindings["valid"],
            "ready": bindings["ready"],
            "fields": bindings["fields"],
        }
        if not self._transfer(snapshot, channel):
            return []
        value = self._read(snapshot, str(bindings["signal"]))
        return ["zero" if value == 0 else "nonzero"]

    def _lite_address_hits(
        self, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        channel = {
            "valid": bindings["valid"],
            "ready": bindings["ready"],
            "fields": bindings["fields"],
        }
        if not self._transfer(snapshot, channel):
            return []
        value = self._field(snapshot, channel, "addr")
        channels = bindings.get("channels", {})
        data_width = None
        for kind in ("write_data", "read_data"):
            candidate = channels.get(kind, {}).get("widths", {}).get("data")
            if isinstance(candidate, int):
                data_width = candidate
                break
        bus_bytes = data_width // 8 if data_width else 4
        hits = ["zero"] if value == 0 else []
        hits.append("aligned" if value % bus_bytes == 0 else "unaligned")
        if (value & 0xFFF) < bus_bytes or (value & 0xFFF) >= 0x1000 - bus_bytes:
            hits.append("page_edge")
        return hits

    def _write_order(
        self, obligation_id: str, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        channels = bindings["channels"]
        aw, w = channels["write_address"], channels["write_data"]
        state = self.state.setdefault(f"write_order:{obligation_id}", {"aw": [], "w": [], "in_w": False})
        aw_fire = self._transfer(snapshot, aw)
        w_fire = self._transfer(snapshot, w)
        if aw_fire:
            state["aw"].append(self.cycle)
        if w_fire and not state["in_w"]:
            state["w"].append(self.cycle)
        if w_fire:
            last_name = w.get("fields", {}).get("last")
            state["in_w"] = bool(last_name and not self._field(snapshot, w, "last"))
        hits: list[str] = []
        while state["aw"] and state["w"]:
            aw_cycle, w_cycle = state["aw"].pop(0), state["w"].pop(0)
            hits.append("same_cycle" if aw_cycle == w_cycle else "address_first" if aw_cycle < w_cycle else "data_first")
        return hits

    def _response_hits(
        self, snapshot: Mapping[str, Any], bindings: Mapping[str, Any], lite: bool
    ) -> list[str]:
        channel = {
            "valid": bindings["valid"],
            "ready": bindings["ready"],
            "fields": bindings["fields"],
        }
        if not self._transfer(snapshot, channel):
            return []
        value = self._field(snapshot, channel, "resp")
        names = {0: "okay", 2: "slverr", 3: "decerr"}
        if not lite:
            names[1] = "exokay"
        return [names[value]] if value in names else []

    def _outstanding(
        self, obligation_id: str, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        state = self.state.setdefault(f"outstanding:{obligation_id}", [])
        channels = bindings["channels"]
        for kind in ("write_address", "read_address"):
            channel = channels.get(kind)
            if channel and self._transfer(snapshot, channel):
                state.append((kind, self._field(snapshot, channel, "id")))
        b = channels.get("write_response")
        if b and self._transfer(snapshot, b):
            bid = self._field(snapshot, b, "id")
            match = next((i for i, item in enumerate(state) if item == ("write_address", bid)), None)
            if match is not None:
                state.pop(match)
        r = channels.get("read_data")
        if r and self._transfer(snapshot, r) and self._field(snapshot, r, "last"):
            rid = self._field(snapshot, r, "id")
            match = next((i for i, item in enumerate(state) if item == ("read_address", rid)), None)
            if match is not None:
                state.pop(match)
        if len(state) == 1:
            return ["one"]
        if len(state) >= 2:
            ids = {item[1] for item in state}
            return ["multiple_same_id" if len(ids) == 1 else "multiple_ids"]
        return []

    def _lite_outstanding(
        self, obligation_id: str, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        key = f"lite_outstanding:{obligation_id}"
        count = int(self.state.get(key, 0))
        channels = bindings["channels"]
        for kind in ("write_address", "read_address"):
            channel = channels.get(kind)
            if channel and self._transfer(snapshot, channel):
                count += 1
        b = channels.get("write_response")
        if b and self._transfer(snapshot, b):
            count = max(0, count - 1)
        r = channels.get("read_data")
        if r and self._transfer(snapshot, r):
            count = max(0, count - 1)
        self.state[key] = count
        return ["multiple" if count >= 2 else "one"] if count else []

    def _lite_concurrency(
        self, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        aw, ar = bindings["channels"]["write_address"], bindings["channels"]["read_address"]
        aw_fire, ar_fire = self._transfer(snapshot, aw), self._transfer(snapshot, ar)
        if aw_fire and ar_fire:
            return ["simultaneous"]
        if aw_fire:
            return ["write_only_cycle"]
        if ar_fire:
            return ["read_only_cycle"]
        return []

    def _axis_hits(
        self, obligation_id: str, template: str, snapshot: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> list[str]:
        channel = {
            "valid": bindings["valid"],
            "ready": bindings["ready"],
            "fields": bindings["fields"],
        }
        valid = bool(self._read(snapshot, str(channel["valid"])))
        ready_name = channel.get("ready")
        ready = (
            True
            if ready_name in {None, ""}
            else bool(self._read(snapshot, str(ready_name)))
        )
        fire = valid and ready
        identity = self._field(snapshot, channel, "id")
        destination = self._field(snapshot, channel, "dest")
        stream_key = (identity, destination)
        state = self.state.setdefault(
            f"axis:{bindings['protocol_group']}",
            {"beats": {}, "last_cycle": {}},
        )
        if template == "axis_stall_position":
            if not (valid and not ready):
                return []
            if "last" in channel["fields"] and self._field(snapshot, channel, "last"):
                return ["last_beat"]
            beats = int(state["beats"].get(stream_key, 0))
            return ["first_beat" if beats == 0 else "middle_beat"]
        if not fire:
            return []
        if template == "axis_packet_length":
            state["beats"][stream_key] = int(
                state["beats"].get(stream_key, 0)
            ) + 1
            if self._field(snapshot, channel, "last"):
                result = [
                    "single_beat"
                    if state["beats"][stream_key] == 1
                    else "multi_beat"
                ]
                state["beats"].pop(stream_key, None)
                return result
        elif template == "axis_keep_pattern":
            value = self._field(snapshot, channel, "keep")
            width = bindings.get("widths", {}).get("keep")
            full = (1 << int(width)) - 1 if isinstance(width, int) and width > 0 else None
            if value == 0 and self._field(snapshot, channel, "last"):
                return ["empty_last"]
            return ["full" if full is not None and value == full else "partial"]
        elif template == "axis_back_to_back_packets":
            hits: list[str] = []
            last_cycle = state["last_cycle"].get(stream_key)
            if last_cycle is not None:
                hits.append("no_gap" if self.cycle == int(last_cycle) + 1 else "with_gap")
                state["last_cycle"].pop(stream_key, None)
            if self._field(snapshot, channel, "last"):
                state["last_cycle"][stream_key] = self.cycle
            return hits
        elif template == "axis_sideband_partition":
            value = self._read(snapshot, str(bindings["signal"]))
            return ["zero" if value == 0 else "nonzero"]
        return []

    def sample(self, snapshot: Mapping[str, Any]) -> list[tuple[str, str]]:
        self.cycle += 1
        result: list[tuple[str, str]] = []
        for obligation_id, obligation in self.obligations.items():
            template = str(obligation["template"])
            bindings = obligation.get("bindings", {})
            if template == "handshake_arrival_order":
                hits = self._handshake_order(obligation_id, snapshot, obligation)
            elif template in {
                "axi4_4k_boundary",
                "axi4_burst_type",
                "axi4_burst_length",
                "axi4_transfer_size",
                "axi4_alignment",
            }:
                hits = self._address_hits(template, snapshot, bindings)
            elif template in {"axi4_write_strobe", "axi_lite_write_strobe"}:
                hits = self._strobe_hits(snapshot, bindings)
            elif template in {"axi4_write_channel_order", "axi_lite_write_channel_order"}:
                hits = self._write_order(obligation_id, snapshot, bindings)
            elif template in {"axi4_response_code", "axi_lite_response_code"}:
                hits = self._response_hits(snapshot, bindings, template.startswith("axi_lite"))
            elif template == "axi4_outstanding_depth":
                hits = self._outstanding(obligation_id, snapshot, bindings)
            elif template == "axi_lite_read_write_concurrency":
                hits = self._lite_concurrency(snapshot, bindings)
            elif template == "axi_lite_address_partition":
                hits = self._lite_address_hits(snapshot, bindings)
            elif template == "axi_lite_outstanding_depth":
                hits = self._lite_outstanding(obligation_id, snapshot, bindings)
            elif template in {"axi4_sideband_partition", "axi_lite_protection_partition"}:
                hits = self._field_partition_hits(snapshot, bindings)
            elif template.startswith("axis_"):
                hits = self._axis_hits(obligation_id, template, snapshot, bindings)
            else:
                hits = []
            result.extend((obligation_id, hit) for hit in hits)
        return result


__all__ = ["ProtocolCoverageMonitor", "protocol_runtime_templates"]
