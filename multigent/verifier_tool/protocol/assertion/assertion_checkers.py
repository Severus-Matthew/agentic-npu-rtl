"""Executable assertion checkers for ready/valid and standardized AXI profiles."""

from __future__ import annotations

import re
from typing import Any, Mapping, MutableMapping

from .axi import axi_burst_crosses_4k, axi_lane_mask, axi_transfer_windows


def _safe(value: object) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", str(value)).strip("_").lower() or "unnamed"


def _read(snapshot: Mapping[str, Any], name: str) -> int:
    if name not in snapshot:
        raise AssertionError(f"protocol snapshot is missing bound signal {name!r}")
    return int(snapshot[name])


def _transfer(snapshot: Mapping[str, Any], channel: Mapping[str, Any]) -> bool:
    ready = channel.get("ready")
    return bool(_read(snapshot, str(channel["valid"]))) and (
        True if ready in {None, ""} else bool(_read(snapshot, str(ready)))
    )


def _presented(snapshot: Mapping[str, Any], channel: Mapping[str, Any]) -> bool:
    return bool(_read(snapshot, str(channel["valid"])))


def _field(snapshot: Mapping[str, Any], channel: Mapping[str, Any], field: str, default: int = 0) -> int:
    name = channel.get("fields", {}).get(field)
    return _read(snapshot, str(name)) if name else default


def _fail(feature: str, detail: str, signals: list[str], snapshot: Mapping[str, Any]) -> None:
    observed = {name: int(snapshot[name]) for name in signals if name in snapshot}
    raise AssertionError(
        f"feature={feature}; {detail}; related_signals={tuple(signals)!r}; observed={observed!r}"
    )


def check_stall_stability(
    snapshot: Mapping[str, Any], plan: Mapping[str, Any], state: MutableMapping[str, Any]
) -> dict[str, int]:
    completed: dict[str, int] = {}
    stalls = state.setdefault("stalls", {})
    for obligation in plan.get("stalls", []):
        feature = str(obligation["id"])
        valid_name = str(obligation["valid"])
        ready_name = str(obligation["ready"])
        content_names = tuple(map(str, obligation.get("content", ())))
        valid = int(bool(_read(snapshot, valid_name)))
        ready = int(bool(_read(snapshot, ready_name)))
        content = tuple(_read(snapshot, name) for name in content_names)
        previous = stalls.get(feature)
        related = [valid_name, ready_name, *content_names]
        if previous is not None:
            if not valid:
                _fail(feature, "valid was withdrawn before a stalled transfer completed", related, snapshot)
            if content != tuple(previous["content"]):
                _fail(
                    feature,
                    f"producer-owned content changed during stall or release; previous={tuple(previous['content'])!r}",
                    related,
                    snapshot,
                )
        if valid and not ready:
            if previous is None:
                stalls[feature] = {"content": content, "length": 1}
            else:
                previous["length"] = int(previous["length"]) + 1
        else:
            if previous is not None:
                completed[feature] = int(previous["length"])
            stalls.pop(feature, None)
    return completed


def _data_bytes(
    group: Mapping[str, Any], kind: str, snapshot: Mapping[str, Any] | None = None
) -> int | None:
    width = group.get("channels", {}).get(kind, {}).get("widths", {}).get("data")
    if not isinstance(width, int) and snapshot is not None:
        signal = group.get("channels", {}).get(kind, {}).get("fields", {}).get("data")
        observed_widths = getattr(snapshot, "widths", {})
        width = observed_widths.get(signal) if signal else None
    return int(width) // 8 if isinstance(width, int) and width > 0 and width % 8 == 0 else None


def _check_address(
    profile: str,
    group: Mapping[str, Any],
    channel: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, int]:
    kind = str(channel["kind"])
    feature_root = f"protocol.{_safe(group['name'])}"
    address = _field(snapshot, channel, "addr")
    length = _field(snapshot, channel, "len")
    size = _field(snapshot, channel, "size")
    burst = _field(snapshot, channel, "burst")
    signals = [channel["fields"][name] for name in ("addr", "len", "size", "burst")]
    if burst not in {0, 1, 2}:
        _fail(f"{feature_root}.legal_burst_encoding", f"AxBURST={burst} is reserved", signals, snapshot)
    if burst in {0, 2} and length > 15:
        _fail(
            f"{feature_root}.legal_burst_length",
            f"FIXED/WRAP burst has {length + 1} beats; maximum is 16",
            signals,
            snapshot,
        )
    if burst == 2 and length not in {1, 3, 7, 15}:
        _fail(
            f"{feature_root}.wrap_length_and_alignment",
            f"WRAP AxLEN={length} does not encode 2, 4, 8, or 16 beats",
            signals,
            snapshot,
        )
    data_kind = "write_data" if kind == "write_address" else "read_data"
    bus_bytes = _data_bytes(group, data_kind, snapshot)
    bytes_per_beat = 1 << size
    if bus_bytes is not None and bytes_per_beat > bus_bytes:
        _fail(
            f"{feature_root}.transfer_size_within_data_bus",
            f"transfer bytes {bytes_per_beat} exceed data-bus bytes {bus_bytes}",
            signals,
            snapshot,
        )
    if burst == 2 and address % bytes_per_beat:
        _fail(
            f"{feature_root}.wrap_length_and_alignment",
            f"WRAP address {address:#x} is not aligned to {bytes_per_beat} bytes",
            signals,
            snapshot,
        )
    beats = length + 1
    lock = _field(snapshot, channel, "lock")
    if lock:
        total_bytes = beats * bytes_per_beat
        if (
            beats > 16
            or total_bytes > 128
            or total_bytes & (total_bytes - 1)
            or address % total_bytes
        ):
            _fail(
                f"{feature_root}.exclusive_access_restrictions",
                "exclusive access requires at most 16 beats, a power-of-two total of at most 128 bytes, and total-size alignment",
                [*signals, channel["fields"]["lock"]],
                snapshot,
            )
    descriptor = {
        "addr": address,
        "len": length,
        "size": size,
        "burst": burst,
    }
    if axi_burst_crosses_4k(descriptor):
        windows = axi_transfer_windows(descriptor)
        _fail(
            f"{feature_root}.no_4k_boundary_crossing",
            f"accepted burst spans descriptor windows {windows!r}",
            signals,
            snapshot,
        )
    return {
        "addr": address,
        "len": length,
        "size": size,
        "burst": burst,
        "id": _field(snapshot, channel, "id"),
        "lock": lock,
        "cache": _field(snapshot, channel, "cache"),
        "prot": _field(snapshot, channel, "prot"),
        "region": _field(snapshot, channel, "region"),
    }


def _beat_address(descriptor: Mapping[str, int], beat: int) -> int:
    return axi_transfer_windows(descriptor)[beat][0]


def _check_write_pair(
    group: Mapping[str, Any], snapshot: Mapping[str, Any], descriptor: Mapping[str, int], beats: list[dict[str, int]]
) -> None:
    root = f"protocol.{_safe(group['name'])}"
    expected = int(descriptor["len"]) + 1
    if len(beats) != expected:
        signals = list(group["channels"]["write_address"]["fields"].values()) + list(
            group["channels"]["write_data"]["fields"].values()
        )
        _fail(
            f"{root}.write_last_matches_length",
            f"AWLEN expects {expected} W beats but WLAST closed {len(beats)}",
            signals,
            snapshot,
        )
    w = group["channels"]["write_data"]
    strobe_width = w.get("widths", {}).get("strb")
    observed_widths = getattr(snapshot, "widths", {})
    strobe_signal = w.get("fields", {}).get("strb")
    if not isinstance(strobe_width, int) and strobe_signal:
        strobe_width = observed_widths.get(strobe_signal)
    bus_bytes = int(strobe_width) if isinstance(strobe_width, int) else _data_bytes(
        group, "write_data", snapshot
    )
    if bus_bytes is None:
        return
    windows = axi_transfer_windows(descriptor)
    for index, beat in enumerate(beats):
        allowed = axi_lane_mask(windows[index], bus_bytes)
        strobe = int(beat["strb"])
        if strobe & ~allowed:
            _fail(
                f"{root}.write_strobe_within_active_lanes",
                f"beat {index} WSTRB={strobe:#x} enables lanes outside allowed mask {allowed:#x}",
                [w["fields"]["strb"]],
                snapshot,
            )


def _matching_index(items: list[dict[str, Any]], identifier: int, has_id: bool) -> int | None:
    for index, item in enumerate(items):
        if not has_id or int(item.get("id", 0)) == identifier:
            return index
    return None


def check_standard_signal_widths(
    snapshot: Mapping[str, Any], group: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    if state.get("widths_checked"):
        return
    widths = getattr(snapshot, "widths", {})
    if not widths:
        return
    profile = str(group["profile"])
    root = f"protocol.{_safe(group['name'])}.standard_signal_widths"
    fixed = {
        "axi4": {"len": 8, "size": 3, "burst": 2, "lock": 1, "cache": 4, "prot": 3, "qos": 4, "region": 4, "resp": 2, "last": 1},
        "axi4_lite": {"prot": 3, "resp": 2},
        "axi4_stream": {"last": 1},
        # custom_mmio imposes no fixed field widths -- the LLM defines its
        # own field widths for a protocol this tool does not natively know.
        "custom_mmio": {},
    }.get(profile, {})
    data_widths: list[tuple[str, int]] = []
    for channel in group["channels"].values():
        for control in ("valid", "ready"):
            raw_name = channel.get(control)
            if raw_name in {None, ""}:
                continue
            name = str(raw_name)
            if int(widths.get(name, 0)) != 1:
                _fail(root, f"{name} must be one bit, got {widths.get(name)!r}", [name], snapshot)
        for field, name in channel["fields"].items():
            width = int(widths.get(name, 0))
            if field in fixed and width != fixed[field]:
                _fail(root, f"{field} must be {fixed[field]} bits, got {width}", [name], snapshot)
            if field == "data":
                if profile == "axi4_stream":
                    if width <= 0 or width % 8:
                        _fail(root, f"AXI4-Stream TDATA width must contain an integer number of bytes, got {width}", [name], snapshot)
                elif width < 8 or width > 1024 or width % 8 or width & (width - 1):
                    _fail(root, f"data width must be a power-of-two byte width from 8 to 1024, got {width}", [name], snapshot)
                data_widths.append((str(channel["kind"]), width))
                for mask in ("strb", "keep"):
                    mask_name = channel["fields"].get(mask)
                    if mask_name and int(widths.get(mask_name, 0)) * 8 != width:
                        _fail(root, f"{mask} width must equal data bytes {width // 8}", [name, mask_name], snapshot)
    memory_widths = [width for kind, width in data_widths if kind in {"write_data", "read_data"}]
    if profile in {"axi4", "axi4_lite"} and len(set(memory_widths)) > 1:
        _fail(root, f"read/write data widths differ: {memory_widths}", [], snapshot)
    if profile == "axi4_lite" and any(width not in {32, 64} for width in memory_widths):
        _fail(root, f"AXI4-Lite data width must be 32 or 64: {memory_widths}", [], snapshot)
    state["widths_checked"] = True


def check_axi4(
    snapshot: Mapping[str, Any], group: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    channels = group["channels"]
    root = f"protocol.{_safe(group['name'])}"
    aw = channels.get("write_address")
    w = channels.get("write_data")
    b = channels.get("write_response")
    ar = channels.get("read_address")
    r = channels.get("read_data")
    pending_b: list[dict[str, Any]] = state.setdefault("pending_b", [])
    reads: list[dict[str, Any]] = state.setdefault("reads", [])

    # Responses may depend only on transfers completed on earlier active edges.
    if b and _presented(snapshot, b):
        response = _field(snapshot, b, "resp")
        if response not in {0, 1, 2, 3}:
            _fail(f"{root}.legal_response_encoding", f"BRESP={response} is reserved", [b["fields"]["resp"]], snapshot)
        bid = _field(snapshot, b, "id")
        index = _matching_index(pending_b, bid, "id" in b["fields"])
        if index is None:
            feature = (
                f"{root}.response_id_matches_request"
                if pending_b and "id" in b["fields"]
                else f"{root}.response_after_request"
            )
            _fail(
                feature,
                (
                    f"BID={bid} does not match a pending write response"
                    if pending_b
                    else "BVALID was presented before a completed AW plus WLAST transaction"
                ),
                [b["valid"], *b["fields"].values()],
                snapshot,
            )
        if response == 1 and not pending_b[index].get("lock"):
            _fail(
                f"{root}.exclusive_response_consistency",
                "EXOKAY write response was returned for a non-exclusive write",
                [b["fields"]["resp"]],
                snapshot,
            )
        if _transfer(snapshot, b):
            pending_b.pop(index)
    if r and _presented(snapshot, r):
        response = _field(snapshot, r, "resp")
        if response not in {0, 1, 2, 3}:
            _fail(f"{root}.legal_response_encoding", f"RRESP={response} is reserved", [r["fields"]["resp"]], snapshot)
        rid = _field(snapshot, r, "id")
        index = _matching_index(reads, rid, "id" in r["fields"])
        if index is None:
            feature = (
                f"{root}.response_id_matches_request"
                if reads and "id" in r["fields"]
                else f"{root}.response_after_request"
            )
            _fail(
                feature,
                (
                    f"RID={rid} does not match a pending read request"
                    if reads
                    else "RVALID was presented without an earlier matching AR transfer"
                ),
                [r["valid"], *r["fields"].values()],
                snapshot,
            )
        if response == 1 and not reads[index].get("lock"):
            _fail(
                f"{root}.exclusive_response_consistency",
                "EXOKAY read response was returned for a non-exclusive read",
                [r["fields"]["resp"]],
                snapshot,
            )
        if _transfer(snapshot, r):
            request = reads[index]
            expected_last = int(request["remaining"]) == 1
            actual_last = bool(_field(snapshot, r, "last"))
            if actual_last != expected_last:
                _fail(
                    f"{root}.read_last_matches_length",
                    f"RLAST={int(actual_last)} with {request['remaining']} beats remaining",
                    [r["fields"]["last"]],
                    snapshot,
                )
            request["remaining"] = int(request["remaining"]) - 1
            if not request["remaining"]:
                if request.get("lock"):
                    state.setdefault("exclusive_reads", []).append(dict(request))
                reads.pop(index)

    if aw and _transfer(snapshot, aw):
        descriptor = _check_address("axi4", group, aw, snapshot)
        if descriptor.get("lock"):
            exclusive_reads = state.setdefault("exclusive_reads", [])
            comparable = ("id", "addr", "len", "size", "burst", "lock", "cache", "prot", "region")
            match = next(
                (
                    index
                    for index, read in enumerate(exclusive_reads)
                    if all(int(read.get(key, 0)) == int(descriptor.get(key, 0)) for key in comparable)
                ),
                None,
            )
            if match is None:
                _fail(
                    f"{root}.exclusive_access_restrictions",
                    "exclusive write did not follow a completed matching exclusive read",
                    list(aw["fields"].values()),
                    snapshot,
                )
            exclusive_reads.pop(match)
        state.setdefault("aw", []).append(descriptor)
    if ar and _transfer(snapshot, ar):
        descriptor = _check_address("axi4", group, ar, snapshot)
        reads.append({**descriptor, "remaining": int(descriptor["len"]) + 1})
    if w and _transfer(snapshot, w):
        current: list[dict[str, int]] = state.setdefault("w_current", [])
        current.append(
            {
                "strb": _field(snapshot, w, "strb"),
                "last": _field(snapshot, w, "last"),
            }
        )
        pending_aw = state.setdefault("aw", [])
        if pending_aw and len(current) >= int(pending_aw[0]["len"]) + 1 and not current[-1]["last"]:
            _fail(
                f"{root}.write_last_matches_length",
                "WLAST was not asserted on the AWLEN-defined final beat",
                [w["fields"]["last"]],
                snapshot,
            )
        if current[-1]["last"]:
            state.setdefault("w_bursts", []).append(list(current))
            current.clear()
    pending_aw = state.setdefault("aw", [])
    w_bursts = state.setdefault("w_bursts", [])
    while pending_aw and w_bursts:
        descriptor = pending_aw.pop(0)
        beats = w_bursts.pop(0)
        _check_write_pair(group, snapshot, descriptor, beats)
        pending_b.append(
            {"id": descriptor.get("id", 0), "lock": descriptor.get("lock", 0)}
        )


def check_axi4_lite(
    snapshot: Mapping[str, Any], group: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    channels = group["channels"]
    root = f"protocol.{_safe(group['name'])}"
    aw, w = channels.get("write_address"), channels.get("write_data")
    b, ar, r = channels.get("write_response"), channels.get("read_address"), channels.get("read_data")
    pending_b: list[int] = state.setdefault("pending_b", [])
    pending_r: list[int] = state.setdefault("pending_r", [])
    if b and _presented(snapshot, b):
        response = _field(snapshot, b, "resp")
        if response not in {0, 2, 3}:
            _fail(f"{root}.legal_lite_response_encoding", f"BRESP={response} is not legal AXI4-Lite", [b["fields"]["resp"]], snapshot)
        if not pending_b:
            _fail(f"{root}.write_response_after_address_and_data", "BVALID preceded a paired AW and W transfer", [b["valid"]], snapshot)
        bid = _field(snapshot, b, "id")
        if "id" in b["fields"] and bid != pending_b[0]:
            _fail(
                f"{root}.optional_id_return_and_in_order_completion",
                f"BID={bid} does not match oldest AWID={pending_b[0]}",
                [b["fields"]["id"]],
                snapshot,
            )
        if _transfer(snapshot, b):
            pending_b.pop(0)
    if r and _presented(snapshot, r):
        response = _field(snapshot, r, "resp")
        if response not in {0, 2, 3}:
            _fail(f"{root}.legal_lite_response_encoding", f"RRESP={response} is not legal AXI4-Lite", [r["fields"]["resp"]], snapshot)
        if not pending_r:
            _fail(f"{root}.read_response_after_address", "RVALID preceded an AR transfer", [r["valid"]], snapshot)
        rid = _field(snapshot, r, "id")
        if "id" in r["fields"] and rid != pending_r[0]:
            _fail(
                f"{root}.optional_id_return_and_in_order_completion",
                f"RID={rid} does not match oldest ARID={pending_r[0]}",
                [r["fields"]["id"]],
                snapshot,
            )
        if _transfer(snapshot, r):
            pending_r.pop(0)
    if aw and _transfer(snapshot, aw):
        state.setdefault("aw_ids", []).append(_field(snapshot, aw, "id"))
    if w and _transfer(snapshot, w):
        state["w_count"] = int(state.get("w_count", 0)) + 1
    paired = min(len(state.setdefault("aw_ids", [])), int(state.get("w_count", 0)))
    if paired:
        for _ in range(paired):
            pending_b.append(int(state["aw_ids"].pop(0)))
        state["w_count"] -= paired
    if ar and _transfer(snapshot, ar):
        pending_r.append(_field(snapshot, ar, "id"))


def check_axi4_stream(
    snapshot: Mapping[str, Any], group: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    channel = group["channels"]["stream"]
    root = f"protocol.{_safe(group['name'])}"
    data_bytes = _data_bytes(group, "stream", snapshot)
    full_keep = (1 << data_bytes) - 1 if data_bytes else 0
    if _presented(snapshot, channel):
        keep = _field(snapshot, channel, "keep", full_keep)
        strobe = _field(snapshot, channel, "strb", keep)
        if strobe & ~keep:
            related = [
                name
                for name in (
                    channel.get("fields", {}).get("strb"),
                    channel.get("fields", {}).get("keep"),
                )
                if name
            ]
            _fail(
                f"{root}.strobe_is_subset_of_keep",
                f"TSTRB={strobe:#x} marks bytes whose TKEEP={keep:#x} bit is clear",
                related,
                snapshot,
            )
    if not _transfer(snapshot, channel):
        return
    fields = channel["fields"]
    if "last" not in fields:
        return
    identity = _field(snapshot, channel, "id")
    destination = _field(snapshot, channel, "dest")
    key = (identity, destination)
    open_packets = state.setdefault("open_packets", {})
    open_packets[key] = int(open_packets.get(key, 0)) + 1

    capabilities = group.get("capabilities", {})
    if capabilities.get("continuous_packets") is True:
        active_key = state.setdefault("continuous_packet_key", key)
        if key != tuple(active_key):
            _fail(
                f"{root}.continuous_packet_constraints_when_declared",
                f"stream key changed from {active_key!r} to {key!r} inside a continuous packet",
                [name for name in (fields.get("id"), fields.get("dest"), fields.get("last")) if name],
                snapshot,
            )
        if keep != full_keep and not _field(snapshot, channel, "last"):
            _fail(
                f"{root}.continuous_packet_constraints_when_declared",
                "a nonterminal continuous-packet beat must keep every data byte",
                [name for name in (fields.get("keep"), fields.get("last")) if name],
                snapshot,
            )
        if strobe != keep:
            _fail(
                f"{root}.continuous_packet_constraints_when_declared",
                "a continuous-packet transfer cannot contain position bytes; effective TSTRB must equal TKEEP",
                [name for name in (fields.get("strb"), fields.get("keep")) if name],
                snapshot,
            )
        if _field(snapshot, channel, "last") and keep & (keep + 1):
            _fail(
                f"{root}.continuous_packet_constraints_when_declared",
                f"terminal continuous-packet TKEEP={keep:#x} is not a contiguous low-byte prefix",
                [name for name in (fields.get("keep"), fields.get("last")) if name],
                snapshot,
            )
    if _field(snapshot, channel, "last"):
        open_packets.pop(key, None)
        if capabilities.get("continuous_packets") is True:
            state.pop("continuous_packet_key", None)


def finalize_protocol_checker_state(
    plan: Mapping[str, Any], state: MutableMapping[str, Any]
) -> None:
    """Reject a finite test that exits with undisposed protocol work."""

    pending: list[str] = []
    stalls = state.get("stalls", {})
    if stalls:
        pending.append(f"stalled_presentations={sorted(stalls)}")
    for group in plan.get("standard_groups", []):
        name = str(group["name"])
        profile = str(group["profile"])
        current = state.get("groups", {}).get(name, {})
        if profile == "axi4":
            keys = ("aw", "w_current", "w_bursts", "pending_b", "reads")
        elif profile == "axi4_lite":
            keys = ("aw_ids", "pending_b", "pending_r")
        else:
            keys = ("open_packets",)
        values = {
            key: current.get(key)
            for key in keys
            if current.get(key)
        }
        if profile == "axi4_lite" and current.get("w_count"):
            values["w_count"] = current["w_count"]
        if values:
            pending.append(f"{name}={values!r}")
    if pending:
        raise AssertionError(
            "feature=runtime.protocol_finalization; finite test ended with pending "
            + "; ".join(pending)
        )


def check_valid_low_during_reset(
    snapshot: Mapping[str, Any],
    reset: str,
    valid_signals: tuple[str, ...],
    feature_ids: Mapping[str, Any],
) -> None:
    """Require every bound VALID signal to remain low during active reset."""

    for valid in valid_signals:
        if valid in snapshot and int(bool(snapshot[valid])):
            _fail(
                str(
                    feature_ids.get(
                        valid, f"protocol.{_safe(valid)}.valid_low_during_reset"
                    )
                ),
                "VALID must be low while reset is active",
                [reset, valid],
                snapshot,
            )


__all__ = [
    "check_axi4",
    "check_axi4_lite",
    "check_axi4_stream",
    "check_stall_stability",
    "check_standard_signal_widths",
    "check_valid_low_during_reset",
    "finalize_protocol_checker_state",
]
