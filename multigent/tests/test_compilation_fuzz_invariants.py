"""Randomized structural damage to real contracts: the invariants must hold every time.

Whatever is done to a contract -- extra channels, dropped signals, flipped directions,
corrupted control-plane declarations, internal objects, broken policies -- compiling it
must never lose or duplicate an operation, must classify every defect, must be
deterministic and JSON-plain, and every planner and report built from the result must
keep working. Set MULTIGENT_FUZZ_ITERATIONS for a deeper local run; the default keeps
the suite fast while still exercising every mutation operator.
"""
from __future__ import annotations

import json
import os
import random
import traceback
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from multigent.tests.test_architect import FakeArchitectAgent
from multigent.tests.test_canonical_operation import axi_lite_contracts, contracts
from multigent.verifier_tool import (
    automatic_campaign_support,
    build_architect_operation_metadata,
    build_lifecycle_feature_plan,
    review_contract_deterministically,
    validate_operation_compilation,
)
from multigent.verifier_tool.benchmark.u55c_inspired_int8_gemm_4x4x4 import build_contract_and_tb
from multigent.verifier_tool.pool import diagnostics as diag
from multigent.verifier_tool.pool.operation_metadata.architect_metadata import (
    blocking_compilation_errors,
    compilation_capability_notes,
)

HLS_DIR = Path(__file__).resolve().parents[1] / "verifier_tool" / "benchmark" / "int8_gemm_hls_golden"
ITERATIONS = int(os.environ.get("MULTIGENT_FUZZ_ITERATIONS", "25"))
SEED_OFFSET = int(os.environ.get("MULTIGENT_FUZZ_SEED_OFFSET", "0"))
ROLES = ["valid", "ready", "payload", "metadata", "last", "keep", "busy", "completion", "error"]
FRAGMENT_STATES = {"compiled", "partial", "failed"}


def _bases():
    hls = (
        yaml.safe_load((HLS_DIR / "architecture_contract.yaml").read_text()),
        yaml.safe_load((HLS_DIR / "interface_contract.yaml").read_text()),
    )
    fake = FakeArchitectAgent().run_structured()
    u55c = build_contract_and_tb.build_architecture_contract()[:2]
    return {
        "axi_lite": deepcopy(axi_lite_contracts()),
        "ready_valid": deepcopy(contracts()),
        "hls": hls,
        "u55c": u55c,
        "fake_architect": (fake["architecture_contract"], fake["interface_contract"]),
    }


BASES = _bases()


# ---- mutation operators: each takes (architecture, interface, rng) and edits in place ----------

def _pick(rng, items):
    items = list(items)
    return rng.choice(items) if items else None


def m_duplicate_object_on_channel(arch, iface, rng):
    obj, channel = _pick(rng, arch.get("data_objects", [])), _pick(rng, iface.get("channels", []))
    if obj and channel and obj["name"] not in channel.setdefault("data_objects", []):
        channel["data_objects"].append(obj["name"])


def m_drop_object_from_channel(arch, iface, rng):
    channel = _pick(rng, [c for c in iface.get("channels", []) if c.get("data_objects")])
    if channel:
        channel["data_objects"].remove(rng.choice(channel["data_objects"]))


def m_flip_channel_direction(arch, iface, rng):
    channel = _pick(rng, iface.get("channels", []))
    if channel:
        channel["direction"] = "input" if channel.get("direction") == "output" else "output"


def m_drop_signal(arch, iface, rng):
    signal = _pick(rng, iface.get("signals", []))
    if signal:
        iface["signals"].remove(signal)


def m_duplicate_channel_signal(arch, iface, rng):
    signal = _pick(rng, [s for s in iface.get("signals", []) if s.get("channel")])
    if signal:
        iface["signals"].append({**deepcopy(signal), "name": signal["name"] + "_dup"})


def m_change_role(arch, iface, rng):
    signal = _pick(rng, iface.get("signals", []))
    if signal:
        signal["role"] = rng.choice(ROLES)


def m_add_status_signal(arch, iface, rng):
    iface.setdefault("signals", []).append(
        {"name": f"extra_{rng.randint(0, 999)}", "role": rng.choice(["busy", "completion", "error"]),
         "direction": "output", "channel": None}
    )


def m_corrupt_policy(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if operation and isinstance(operation.get("lifecycle_policy"), dict) and operation["lifecycle_policy"]:
        key = rng.choice(list(operation["lifecycle_policy"]))
        move = rng.choice(["drop", "bogus", "extension", "control_plane"])
        if move == "drop":
            operation["lifecycle_policy"].pop(key)
        elif move == "bogus":
            operation["lifecycle_policy"][key] = "bogus_choice"
        elif move == "extension":
            operation["lifecycle_policy"][key] = {"extension_request": "lifecycle.fuzz_ext"}
        else:
            operation["lifecycle_policy"][rng.choice(["job_acceptance", "completion_style"])] = "control_plane_sequence"


def m_drop_policy(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if operation:
        operation.pop("lifecycle_policy", None)


def m_corrupt_control_plane(arch, iface, rng):
    operation = _pick(rng, [o for o in arch.get("operations", []) if o.get("lifecycle_control_plane_sequence")])
    if not operation:
        # Give any operation a declaration to exercise "unused" / "no subordinate" paths.
        operation = _pick(rng, arch.get("operations", []))
        if operation:
            operation["lifecycle_control_plane_sequence"] = rng.choice(
                [{}, {"registers": {}}, {"registers": {"r": {"address": 0}}, "job_start": {"actions": []}, "job_complete": {"actions": []}}]
            )
        return
    sequence = operation["lifecycle_control_plane_sequence"]
    move = rng.choice(["drop_key", "collide", "unknown_register", "empty_actions", "extra_poll", "null", "type"])
    try:
        if move == "drop_key":
            sequence.pop(rng.choice(list(sequence)))
        elif move == "collide":
            registers = list(sequence["registers"].values())
            registers[0]["address"] = registers[-1]["address"]
        elif move == "unknown_register":
            sequence["job_start"]["actions"].insert(0, {"op": "read_reg", "register": "nope"})
        elif move == "empty_actions":
            sequence[rng.choice(["job_start", "job_complete"])]["actions"] = []
        elif move == "extra_poll":
            sequence["job_complete"]["actions"].append({"op": "poll_field", "register": "control", "field": "ap_done", "expected": 1})
        elif move == "null":
            sequence[rng.choice(list(sequence))] = None
        else:
            operation["lifecycle_control_plane_sequence"] = rng.choice([[], "text", 3])
    except (KeyError, IndexError, TypeError):
        pass


def m_internalize_object(arch, iface, rng):
    obj = _pick(rng, arch.get("data_objects", []))
    if obj:
        obj["external"] = False


def m_add_internal_object(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if not operation:
        return
    name = f"internal_{rng.randint(0, 99)}"
    arch.setdefault("data_objects", []).append({
        "name": name, "role": "intermediate", "data_type": (arch.get("data_types") or [{"name": "s32"}])[0]["name"],
        "dimensions": [], "external": False,
        "serialization": {"kind": "scalar", "index_order": [], "description": "one"},
    })
    operation.setdefault(rng.choice(["inputs", "outputs"]), []).append(name)


def m_break_arithmetic(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if not operation:
        return
    move = rng.choice(["drop", "profile", "field"])
    if move == "drop":
        operation.pop("arithmetic", None)
    elif move == "profile":
        operation["arithmetic"] = {"classifier_profile": rng.choice(["llm_extension", "nonsense"])}
    elif isinstance(operation.get("arithmetic"), dict) and operation["arithmetic"]:
        operation["arithmetic"].pop(rng.choice(list(operation["arithmetic"])))


def _unique_name(arch, stem):
    """Operation names stay unique: identical names are an Architect-level error that the
    planners (compiled or not) have always rejected with a duplicate-id error."""

    taken = {str(item.get("name")) for item in arch.get("operations", []) if isinstance(item, dict)}
    index = 0
    while f"{stem}_{index}" in taken:
        index += 1
    return f"{stem}_{index}"


def m_duplicate_operation(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if operation:
        copy = deepcopy(operation)
        copy["name"] = _unique_name(arch, rng.choice([operation["name"], "x y", "B"]))
        arch["operations"].append(copy)


def m_rename_operation(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if operation:
        operation["name"] = _unique_name(arch, rng.choice(["odd name", "a.b", "UPPER", "with-dash", "x" * 40]))


def m_drop_operation_io(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if operation:
        operation[rng.choice(["inputs", "outputs"])] = []


def m_remove_channel(arch, iface, rng):
    channel = _pick(rng, iface.get("channels", []))
    if channel:
        iface["channels"].remove(channel)


def m_swap_profile(arch, iface, rng):
    channel = _pick(rng, iface.get("channels", []))
    if channel:
        channel["protocol_profile"] = rng.choice(["ready_valid", "axi4_lite", "axi4", "custom", "custom_mmio"])


def m_unknown_object_or_type(arch, iface, rng):
    operation = _pick(rng, arch.get("operations", []))
    if operation and rng.random() < 0.5:
        operation.setdefault("inputs", []).append("ghost_object")
    else:
        obj = _pick(rng, arch.get("data_objects", []))
        if obj:
            obj["data_type"] = "ghost_type"


def m_corrupt_dimension(arch, iface, rng):
    dimension = _pick(rng, arch.get("dimensions", []))
    if not dimension:
        return
    move = rng.choice(["range", "zero", "drop_bound", "drop_all"])
    if move == "range":
        dimension["minimum"], dimension["maximum"] = 1, rng.randint(2, 9)
    elif move == "zero":
        dimension["minimum"] = dimension["maximum"] = 0
    elif move == "drop_bound":
        dimension["bound_parameter"] = "no_such_parameter"
    else:
        arch["dimensions"] = []


def m_corrupt_serialization(arch, iface, rng):
    obj = _pick(rng, arch.get("data_objects", []))
    if not obj:
        return
    move = rng.choice(["drop", "kind", "order", "extra"])
    if move == "drop":
        obj.pop("serialization", None)
    elif move == "kind":
        obj["serialization"] = {"kind": rng.choice(["llm_extension", "nonsense", "packed_encoding"]), "index_order": [], "description": "x"}
    elif move == "order" and isinstance(obj.get("serialization"), dict):
        obj["serialization"]["index_order"] = list(reversed(obj.get("dimensions", []))) or ["Q"]
    elif isinstance(obj.get("serialization"), dict):
        obj["serialization"]["surprise"] = 1


def m_corrupt_command_metadata(arch, iface, rng):
    signal = _pick(rng, [s for s in iface.get("signals", []) if "address_role" in str(s.get("semantic", "")) or s.get("role") == "metadata"])
    if not signal:
        return
    signal["semantic"] = str(signal.get("semantic", "")) + rng.choice([
        " data_object=ghost", " address_role=base", " byte_order=big", " address_sequence=strided", " word_stride_bytes=0",
    ])


def m_dangling_signal_channel(arch, iface, rng):
    signal = _pick(rng, [s for s in iface.get("signals", []) if s.get("channel")])
    if signal:
        signal["channel"] = rng.choice(["no_such_channel", None, ""])


def m_collide_channel_names(arch, iface, rng):
    channels = iface.get("channels", [])
    if len(channels) >= 2:
        channels[-1]["name"] = channels[0]["name"]


MUTATIONS = [value for name, value in sorted(globals().items()) if name.startswith("m_")]


# ---- invariants -----------------------------------------------------------------------------

def _check_entry(entry):
    diagnostics = entry["diagnostics"]
    assert diagnostics, entry
    primary = diagnostics[0]
    assert entry["name"] == entry["operation_name"]
    assert entry["reason"] == entry["message"] == primary["message"]
    assert entry["reason_code"] == primary["reason_code"]
    assert entry["category"] == primary["category"] and entry["owner"] == primary["owner"]
    assert entry["resolution_hint"] == primary["resolution_hint"]
    assert entry["blocked_by"] == sorted({item["blocked_by"] for item in diagnostics})
    assert entry["affected_domains"] == [
        d for d in diag.DOMAINS if any(d in item["affected_domains"] for item in diagnostics)
    ]
    assert entry["affected_feature_ids"] == sorted(set(entry["affected_feature_ids"]))
    for item in diagnostics:
        # Every raise site is classified: 'unclassified' would mean a site lost its code.
        assert item["reason_code"] in diag.REASONS and item["reason_code"] != diag.UNCLASSIFIED, item
        assert item["category"] in diag.CATEGORIES
        assert item["owner"] == diag.OWNER_BY_CATEGORY[item["category"]]
        assert item["blocked_by"] == f"{entry['name']}:{item['reason_code']}"
    shell = entry["shell"]
    assert set(shell["fragments"]) == set(diag.DOMAINS)
    assert set(shell["fragments"].values()) <= FRAGMENT_STATES
    assert shell["operation_name"] == entry["name"]
    for binding in [*shell["inputs"], *shell["outputs"]]:
        assert isinstance(binding["data_object"], str)
        assert binding.get("bound", True) in (True, False)


def _check_contract(name, architecture, interface):
    architecture_before, interface_before = deepcopy(architecture), deepcopy(interface)
    metadata = build_architect_operation_metadata(architecture, interface)
    assert (architecture, interface) == (architecture_before, interface_before), "inputs mutated"
    assert metadata == build_architect_operation_metadata(architecture, interface), "non-deterministic"
    json.dumps(metadata)

    # No operation is ever lost or duplicated.
    declared = [str(item["name"]) for item in architecture.get("operations", []) if isinstance(item, dict)]
    accounted = [item["operation_name"] for item in metadata["operations"]] + [
        item["name"] for item in metadata["unrepresentable_operations"]
    ]
    assert sorted(accounted) == sorted(declared), (declared, accounted)

    for entry in metadata["unrepresentable_operations"]:
        _check_entry(entry)
    for operation in metadata["operations"]:
        assert "shell" not in operation and "diagnostics" not in operation

    blocking = blocking_compilation_errors(metadata)
    expected = sum(
        1 for entry in metadata["unrepresentable_operations"] for item in entry["diagnostics"]
        if item["reason_code"] in diag.ARCHITECT_BLOCKING_REASON_CODES
    )
    assert len(blocking) == expected
    assert validate_operation_compilation(architecture, interface) == blocking
    notes = compilation_capability_notes(metadata)
    assert len(notes) + expected == sum(len(entry["diagnostics"]) for entry in metadata["unrepresentable_operations"])

    support = automatic_campaign_support(metadata, architecture)
    for entry in metadata["unrepresentable_operations"]:
        info = support["operations"][entry["name"]]
        assert info["supported"] is False and info["compile_blocked"] is True
        assert info["reason_code"] == entry["reason_code"]
    if metadata["unrepresentable_operations"]:
        assert support["supported"] is False and "blocked_operations" in support
    else:
        assert "blocked_operations" not in support

    plan = build_lifecycle_feature_plan(interface, metadata)
    blocked_names = {entry["name"] for entry in metadata["unrepresentable_operations"]}
    planned = {record["operation_name"] for record in plan["bindings"].get("blocked_operations", [])}
    assert planned <= blocked_names
    assert {item["scope_name"] for item in plan["features"] if item.get("automation")} <= blocked_names
    assert not [item for item in plan["bindings"]["operations"] if item["operation_name"] in blocked_names]
    ids = [item["id"] for item in plan["coverage_obligations"]]
    assert len(ids) == len(set(ids)) or len({n.lower().replace(" ", "_") for n in blocked_names}) < len(blocked_names)
    for obligation in plan["coverage_obligations"]:
        if obligation.get("automation"):
            assert all(b["required"] is True and b["applicability"]["status"] == "required_reachable" for b in obligation["bins"])
    # JSON round trip gives the same plans.
    restored = json.loads(json.dumps(metadata))
    assert build_lifecycle_feature_plan(interface, restored) == plan
    assert automatic_campaign_support(restored, architecture) == support

    report = review_contract_deterministically(architecture, interface)
    assert report["status"] == ("PASS" if not report["findings"] else "BLOCKED")
    assert isinstance(report["capability_notes"], list)
    for finding in report["findings"]:
        assert finding["owner"] == "architect_contract"
    return metadata


@pytest.mark.parametrize("base", sorted(BASES))
def test_compilation_invariants_hold_under_random_structural_damage(base):
    seen_blocked = seen_ok = 0
    for seed in range(SEED_OFFSET, SEED_OFFSET + ITERATIONS):
        rng = random.Random(f"{base}:{seed}")
        architecture, interface = deepcopy(BASES[base])
        applied = []
        for _ in range(rng.randint(1, 3)):
            mutation = rng.choice(MUTATIONS)
            applied.append(mutation.__name__)
            mutation(architecture, interface, rng)
        try:
            metadata = _check_contract(base, architecture, interface)
        except ValueError as exc:
            # The interface itself no longer compiles as a standard protocol group; that is
            # interface-level validation the compile has always surfaced as a raise (and the
            # validator/preflight convert to a message). It must never be anything else.
            assert "standard protocol" in str(exc).lower() or "protocol" in str(exc).lower(), (
                f"{base}:{seed}:{applied}: {exc}\n{traceback.format_exc()}"
            )
            assert all(isinstance(item, str) for item in validate_operation_compilation(architecture, interface))
            report = review_contract_deterministically(architecture, interface)
            assert report["status"] == "BLOCKED"
            continue
        except Exception as exc:  # noqa: BLE001 - name the mutation sequence that broke it
            raise AssertionError(f"{base}:{seed}:{applied}: {type(exc).__name__}: {exc}") from exc
        seen_blocked += bool(metadata["unrepresentable_operations"])
        seen_ok += not metadata["unrepresentable_operations"]
    assert seen_blocked + seen_ok > 0


# ---- real (LLM-generated) contracts ----------------------------------------------------------------

RUNS = Path(__file__).resolve().parents[1] / "runs"
CORPUS_STRIDE = int(os.environ.get("MULTIGENT_CORPUS_STRIDE", "40"))


def _corpus(stride):
    paths = sorted(RUNS.rglob("architecture_contract.yaml")) if RUNS.is_dir() else []
    return [
        (path, path.with_name("interface_contract.yaml"))
        for path in paths[::stride]
        if path.with_name("interface_contract.yaml").is_file()
    ]


@pytest.mark.skipif(not RUNS.is_dir(), reason="no recorded Architect runs in this checkout")
def test_recorded_architect_contracts_compile_classify_and_plan_without_error():
    """Real Architect output -- including older contracts that predate the lifecycle-policy
    and arithmetic declarations -- must never crash compilation or any planner built on it,
    and every defect found in it must carry a registered reason code."""

    checked = blocked = 0
    for architecture_path, interface_path in _corpus(CORPUS_STRIDE):
        architecture = yaml.safe_load(architecture_path.read_text())
        interface = yaml.safe_load(interface_path.read_text())
        try:
            metadata = _check_contract(architecture_path.parent.parent.name, architecture, interface)
        except ValueError as exc:
            assert "protocol" in str(exc).lower(), f"{architecture_path}: {exc}"
            continue
        checked += 1
        blocked += bool(metadata["unrepresentable_operations"])
    assert checked, "the corpus sample compiled nothing"
    assert blocked >= 0  # how many carry diagnostics depends on which runs are kept on disk


# ---- differential test against the sequential (one error per operation) compile ---------------------

def _sequential_reference(architecture, interface):
    """The pre-refactor semantics, rebuilt from the same building blocks: stages run in order
    (I/O bindings, lifecycle binding, policy, memory mappings, arithmetic, final validation)
    and the first failure ends the operation."""

    from multigent.verifier_tool.pool.operation_metadata import architect_metadata as am
    from multigent.verifier_tool.pool.operation_metadata.arithmetic_metadata import (
        ArithmeticMetadataError,
        compile_operation_arithmetic,
    )

    objects = {str(i.get("name")): i for i in architecture.get("data_objects") or [] if isinstance(i, dict)}
    dimensions = am._fixed_dimensions(architecture)
    plan = am._standard_plan_getter(interface)

    def compile_one(operation):
        explicit = operation.get("verification_metadata")
        if isinstance(explicit, dict):
            if "arithmetic" in operation:
                raise am.ArchitectMetadataError("Declare operation.arithmetic or full verification_metadata, not both")
            item = deepcopy(dict(explicit))
            item.setdefault("schema_version", 2)
            item.setdefault("operation_name", str(operation.get("name", "")))
            item.setdefault("family", str(operation.get("coverage_family", "")))
            lifecycle = item.setdefault("lifecycle", {})
            am._attach_lifecycle_policy(lifecycle, operation, interface, standard_plan=plan)
            am.validate_architect_operation_metadata(item)
            return item
        inputs = [
            am._binding(am._unique(list(objects.values()), "name", n), direction="input",
                        architecture=architecture, interface=interface)
            for n in map(str, operation["inputs"])
        ]
        outputs = [
            am._binding(am._unique(list(objects.values()), "name", n), direction="output",
                        architecture=architecture, interface=interface)
            for n in map(str, operation["outputs"])
        ]
        lifecycle = am._bind_lifecycle_metadata(interface)
        am._attach_lifecycle_policy(lifecycle, operation, interface, standard_plan=plan)
        am._attach_standard_memory_mappings([*inputs, *outputs], lifecycle, interface, standard_plan=plan)
        try:
            arithmetic = compile_operation_arithmetic(operation, architecture)
        except ArithmeticMetadataError as exc:
            raise am.ArchitectMetadataError(f"operation {operation.get('name')!r}.arithmetic: {exc}") from exc
        item = {
            "schema_version": 2, "operation_name": str(operation.get("name", "")),
            "family": str(operation.get("coverage_family", "")), "dimensions": dimensions,
            "inputs": inputs, "outputs": outputs, "arithmetic": arithmetic, "lifecycle": lifecycle,
        }
        am.validate_architect_operation_metadata(item)
        return item

    results = []
    for operation in architecture.get("operations") or []:
        if not isinstance(operation, dict):
            continue
        normalized = {
            **operation,
            "inputs": operation.get("inputs") or [],
            "outputs": operation.get("outputs") or [],
        }
        try:
            results.append(("ok", compile_one(normalized)))
        except am.ArchitectMetadataError as exc:
            results.append(("fail", str(operation.get("name", "")), str(exc)))
    return results


def m_explicit_metadata(arch, iface, rng):
    """Turn one operation into the full external verification_metadata form, sometimes damaged."""

    operations = [o for o in arch.get("operations", []) if isinstance(o, dict)]
    if not operations:
        return
    operation = rng.choice(operations)
    try:
        good = build_architect_operation_metadata({**arch, "operations": [operation]}, iface)["operations"]
    except ValueError:
        return
    if not good:
        return
    operation["verification_metadata"] = deepcopy(good[0])
    if rng.random() < 0.7:
        operation.pop("arithmetic", None)
    move = rng.choice(["keep", "drop_field", "bad_policy", "bad_version"])
    full = operation["verification_metadata"]
    if move == "drop_field":
        full.pop(rng.choice(["inputs", "outputs", "dimensions", "arithmetic", "lifecycle", "family"]), None)
    elif move == "bad_policy":
        full["lifecycle"].pop("policy", None)
    elif move == "bad_version":
        full["schema_version"] = 3


@pytest.mark.parametrize("base", sorted(BASES))
def test_fragment_compile_agrees_with_the_sequential_reference(base):
    """Whatever damage a contract has, the fragment-based compile must: return exactly the
    operations the sequential compile produced, keep the sequential compile's first error as
    the entry's legacy `reason`, invent no failure of its own (bar the new AXI4-Lite
    subordinate check), and never raise where the sequential compile returned -- a later
    stage that the old compile never reached must not turn a recorded failure into a raise."""

    mutations = MUTATIONS + [m_explicit_metadata]
    new_check = "control_plane_requires_axi4_lite_subordinate"
    for seed in range(SEED_OFFSET, SEED_OFFSET + ITERATIONS):
        rng = random.Random(f"diff:{base}:{seed}")
        architecture, interface = deepcopy(BASES[base])
        applied = []
        for _ in range(rng.randint(1, 3)):
            mutation = rng.choice(mutations)
            applied.append(mutation.__name__)
            mutation(architecture, interface, rng)
        tag = f"{base}:{seed}:{applied}"
        try:
            old = _sequential_reference(architecture, interface)
        except Exception as exc:  # noqa: BLE001
            old = exc
        try:
            new = build_architect_operation_metadata(architecture, interface)
        except Exception as exc:  # noqa: BLE001
            new = exc
        if isinstance(old, Exception) or isinstance(new, Exception):
            assert type(old) is type(new), (tag, repr(old)[:160], repr(new)[:160])
            continue
        entries = {}
        for entry in new["unrepresentable_operations"]:
            entries.setdefault(entry["name"], []).append(entry)
        for record in old:
            if record[0] == "ok":
                assert record[1] in new["operations"], (tag, "sequential success missing or different", record[1]["operation_name"])
                continue
            _, name, message = record
            assert entries.get(name), (tag, "sequential failure has no entry", name, message)
            entry = entries[name].pop(0)
            if any(item["reason_code"] == new_check for item in entry["diagnostics"]):
                continue
            assert entry["reason"] == message == entry["diagnostics"][0]["message"], (tag, name, entry["reason"], message)
        for name, rest in entries.items():
            for entry in rest:
                assert any(item["reason_code"] == new_check for item in entry["diagnostics"]), (
                    tag, name, "an entry the sequential compile did not produce", entry["reason"],
                )


def test_a_failure_in_an_early_stage_is_never_turned_into_a_raise_by_a_later_one():
    """The contract's write channel set is incomplete (an interface-level defect the standard
    protocol plan rejects), but the operation already fails at its I/O binding. The sequential
    compile stopped there and returned the operation as unrepresentable; the fragment compile,
    which still attempts later fragments for the shell, must return the same rather than raise."""

    architecture, interface = deepcopy(axi_lite_contracts())
    interface["channels"] = [c for c in interface["channels"] if c["name"] != "w"]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") != "w"]
    metadata = build_architect_operation_metadata(architecture, interface)
    (entry,) = metadata["unrepresentable_operations"]
    assert entry["reason"] == "Data object 'Y_matrix' needs one output channel; found 0"

    # With the I/O bindings intact the same interface defect is reached and raises, as before.
    architecture_b, interface_b = deepcopy(axi_lite_contracts())
    interface_b["channels"] = [c for c in interface_b["channels"] if c["name"] != "aw"]
    interface_b["signals"] = [s for s in interface_b["signals"] if s.get("channel") != "aw"]
    with pytest.raises(ValueError, match="incomplete write channel set"):
        build_architect_operation_metadata(architecture_b, interface_b)
    (message,) = validate_operation_compilation(architecture_b, interface_b)
    assert "could not be compiled" in message and "write channel set" in message


def test_an_operation_with_no_io_still_surfaces_an_interface_level_defect():
    """Compiling the interface's standard-protocol plan is what rejects an incomplete channel
    set, and the sequential compile did it for every operation that got past its I/O stage --
    including one with nothing to bind. The fragment compile must keep raising there."""

    architecture, interface = deepcopy(axi_lite_contracts())
    operation = architecture["operations"][0]
    operation.update(inputs=[], outputs=[], semantics="An operation with no external I/O.")
    operation["arithmetic"] = {"classifier_profile": "llm_extension", "reason": "no data path"}
    metadata = build_architect_operation_metadata(architecture, interface)
    assert [item["operation_name"] for item in metadata["operations"]] == ["gemm_core"]

    interface["channels"] = [c for c in interface["channels"] if c["name"] != "aw"]
    interface["signals"] = [s for s in interface["signals"] if s.get("channel") != "aw"]
    with pytest.raises(ValueError, match="incomplete write channel set"):
        build_architect_operation_metadata(architecture, interface)
