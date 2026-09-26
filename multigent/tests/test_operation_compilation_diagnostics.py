"""Operation-metadata compilation diagnostics: classification, early blocking, shell.

`build_architect_operation_metadata` no longer loses an operation silently. Every
defect is recorded with a reason code decided at its raise site, a category
(contract_error / extension_required / tool_capability) and an owner; only the
defects an Architect can fix (and that no earlier validator already reports) go back
to the Architect. These tests attack the boundaries: classification per raise site,
multi-defect operations, legal-looking shapes that must NOT block, malformed input
that must not crash, and the exact guarantees older callers rely on.
"""
from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from multigent.agents.architect import ArchitectAgent, ContractValidationError
from multigent.tests.test_architect import FakeArchitectAgent
from multigent.tests.test_canonical_operation import axi_lite_contracts, contracts
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    review_contract_deterministically,
    validate_operation_compilation,
)
from multigent.verifier_tool.benchmark.u55c_inspired_int8_gemm_4x4x4 import build_contract_and_tb
from multigent.verifier_tool.pool import diagnostics as diag
from multigent.verifier_tool.pool.operation_metadata.architect_metadata import (
    ArchitectMetadataError,
    blocking_compilation_errors,
    compilation_capability_notes,
)

REPO = Path(__file__).resolve().parents[1]
HLS_DIR = REPO / "verifier_tool" / "benchmark" / "int8_gemm_hls_golden"


def _hls():
    return (
        yaml.safe_load((HLS_DIR / "architecture_contract.yaml").read_text()),
        yaml.safe_load((HLS_DIR / "interface_contract.yaml").read_text()),
    )


def _u55c():
    architecture, interface, *_ = build_contract_and_tb.build_architecture_contract()
    return architecture, interface


def _axi():
    return deepcopy(axi_lite_contracts())


def _rv():
    return deepcopy(contracts())


def _diagnostics(architecture, interface):
    metadata = build_architect_operation_metadata(architecture, interface)
    return metadata, [
        item for entry in metadata["unrepresentable_operations"] for item in entry["diagnostics"]
    ]


def _codes(architecture, interface) -> list[str]:
    return [item["reason_code"] for item in _diagnostics(architecture, interface)[1]]


def _channel(interface, name):
    return next(item for item in interface["channels"] if item["name"] == name)


def _signal(interface, name):
    return next(item for item in interface["signals"] if item["name"] == name)


# ---------------------------------------------------------------------------
# Fully compiled contracts are untouched
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("build", [_u55c, _hls, _axi, _rv], ids=["u55c", "hls", "axi_lite", "ready_valid"])
def test_valid_contracts_compile_whole_and_never_block(build):
    architecture, interface = build()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    assert set(metadata) == {"schema_version", "operations", "unrepresentable_operations"}
    assert metadata["operations"]
    for operation in metadata["operations"]:
        # Whole operations keep the exact shape older consumers read; no shell or
        # diagnostics leak into them.
        assert "shell" not in operation and "diagnostics" not in operation
        assert operation["lifecycle"]["policy_source"] == "explicit_contract"
    assert validate_operation_compilation(architecture, interface) == []
    assert compilation_capability_notes(metadata) == []


def test_fake_architect_fixture_is_a_complete_implementable_contract():
    result = FakeArchitectAgent().run_structured()
    architecture, interface = result["architecture_contract"], result["interface_contract"]
    assert validate_operation_compilation(architecture, interface) == []
    ArchitectAgent._validate_contract_references(result)


def test_metadata_is_deterministic_and_never_mutates_or_aliases_its_inputs():
    for build in (_axi, _hls):
        architecture, interface = build()
        before = (deepcopy(architecture), deepcopy(interface))
        first = build_architect_operation_metadata(architecture, interface)
        second = build_architect_operation_metadata(architecture, interface)
        assert first == second
        assert (architecture, interface) == before
        # Mutating one result must not leak into the next build or the inputs.
        first["operations"][0]["lifecycle"]["policy"]["error_style"] = "corrupted"
        first["operations"][0]["dimensions"]["M"] = -1
        assert build_architect_operation_metadata(architecture, interface) == second
        assert (architecture, interface) == before


def test_broken_contract_is_deterministic_and_input_preserving():
    architecture, interface = _axi()
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]
    before = (deepcopy(architecture), deepcopy(interface))
    first = build_architect_operation_metadata(architecture, interface)
    assert first == build_architect_operation_metadata(architecture, interface)
    assert (architecture, interface) == before
    json.dumps(first)  # the whole structure, shell included, is plain JSON data


# ---------------------------------------------------------------------------
# Structure of one unrepresentable entry
# ---------------------------------------------------------------------------

def test_entry_keeps_legacy_keys_and_adds_structured_ones():
    architecture, interface = _axi()
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["operations"] == []
    (entry,) = metadata["unrepresentable_operations"]
    # Legacy consumers read name/reason and expect the first defect's exact text.
    assert entry["name"] == "gemm_core"
    assert entry["reason"] == "Data object 'Y_matrix' needs one output channel; found 2"
    assert entry["reason"] == entry["message"]
    assert entry["operation_name"] == "gemm_core"
    assert entry["reason_code"] == "ambiguous_transport_binding"
    assert entry["category"] == diag.CONTRACT_ERROR
    assert entry["owner"] == "architect_contract"
    assert entry["affected_domains"] == ["operation_io"]
    assert entry["blocked_by"] == ["gemm_core:ambiguous_transport_binding"]
    assert entry["resolution_hint"]
    assert entry["affected_feature_ids"]
    assert entry["affected_feature_ids"] == sorted(set(entry["affected_feature_ids"]))
    (primary,) = entry["diagnostics"]
    assert primary["details"]["channels"] == ["aw", "w"]
    assert primary["details"]["hint_variant"] == "memory_mapped"
    assert "data channel" in entry["resolution_hint"]


def test_owner_and_status_follow_category():
    assert diag.OWNER_BY_CATEGORY == {
        "contract_error": "architect_contract",
        "extension_required": "verifier_extension",
        "tool_capability": "verifier_tool",
    }
    assert set(diag.AUTOMATION_STATUS_BY_CATEGORY) == set(diag.CATEGORIES)
    assert set(diag.AUTOMATION_STATUS_BY_CATEGORY.values()) | {diag.CODE_OWNED} == set(diag.AUTOMATION_STATUSES)
    for code, spec in diag.REASONS.items():
        assert spec.category in diag.CATEGORIES, code
        assert spec.domains and set(spec.domains) <= set(diag.DOMAINS), code
        assert spec.hint.strip(), code
        if spec.architect_blocking:
            assert spec.category == diag.CONTRACT_ERROR, code
    # Nothing an Architect cannot fix, or that the tool merely cannot automate, may block.
    assert not [
        code for code, spec in diag.REASONS.items()
        if spec.category != diag.CONTRACT_ERROR and spec.architect_blocking
    ]


def test_blocking_reason_codes_are_exactly_the_reviewed_set():
    assert diag.ARCHITECT_BLOCKING_REASON_CODES == frozenset({
        "data_object_channel_direction_mismatch",
        "ambiguous_transport_binding",
        "ambiguous_channel_signal_role",
        "missing_ready_valid_signal_roles",
        "ambiguous_base_pointer",
        "memory_channel_kind_mismatch",
        "ambiguous_status_binding",
        "conflicting_semantic_tags",
        "control_plane_sequence_required_but_missing",
        "control_plane_sequence_unused",
        "control_plane_sequence_schema_violation",
        "control_plane_sequence_address_collision",
        "control_plane_sequence_unknown_reference",
        "control_plane_sequence_bad_start_action",
        "control_plane_sequence_bad_completion_poll",
        "control_plane_requires_axi4_lite_subordinate",
    })


def test_every_raise_site_classifies_its_defect_and_every_code_is_registered():
    """A raise site with no reason code would fall back to 'unclassified'; a typo'd
    code would silently become 'unclassified' too. Both are caught statically."""

    root = REPO / "verifier_tool" / "pool"
    sources = {
        root / "operation_metadata" / "architect_metadata.py": {"ArchitectMetadataError"},
        root / "lifecycle_policy_pool" / "policies.py": {"LifecyclePolicyError"},
        root / "lifecycle_policy_pool" / "control_plane_sequence.py": {"ControlPlaneSequenceError"},
    }
    literals: set[str] = set()
    for path, classes in sources.items():
        tree = ast.parse(path.read_text())
        # The catalog loaders validate the tool's own YAML, not a contract.
        skipped = {
            id(node)
            for function in ast.walk(tree)
            if isinstance(function, ast.FunctionDef)
            and function.name in {"_pool", "load_architect_metadata_format"}
            for node in ast.walk(function)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in diag.REASONS:
                literals.add(node.value)
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            func = node.exc.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name not in classes or id(node) in skipped:
                continue
            keywords = {item.arg: item.value for item in node.exc.keywords}
            assert "reason_code" in keywords, f"{path.name}:{node.lineno} raises {name} without reason_code"
            value = keywords["reason_code"]
            if isinstance(value, ast.Constant):
                assert value.value in diag.REASONS, f"{path.name}:{node.lineno}: unknown code {value.value!r}"
    # No dead registry rows: each code is produced by some raise site.
    assert set(diag.REASONS) - literals == set(), set(diag.REASONS) - literals


# ---------------------------------------------------------------------------
# Channel binding: classification per raise site
# ---------------------------------------------------------------------------

def test_same_object_on_two_same_direction_channels_is_ambiguous_and_blocks():
    architecture, interface = _rv()
    _channel(interface, "b")["data_objects"].append("A_matrix")
    metadata, found = _diagnostics(architecture, interface)
    (item,) = found
    assert item["reason_code"] == "ambiguous_transport_binding"
    assert item["details"]["channels"] == ["a", "b"]
    assert "hint_variant" not in item["details"], "ready_valid is not a memory-mapped profile"
    assert "split it into separately declared data objects" in item["resolution_hint"]
    (message,) = validate_operation_compilation(architecture, interface)
    assert "[ambiguous_transport_binding]" in message and "'A_matrix'" in message


def test_object_on_one_input_and_one_output_channel_is_legal_and_not_ambiguous():
    # Direction, not mere presence, selects the channel: an object read by one
    # operation and produced by another legitimately sits on both an input and an
    # output channel. Counting channels regardless of direction would reject it.
    architecture, interface = _rv()
    _channel(interface, "y")["data_objects"].append("A_matrix")
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    assert validate_operation_compilation(architecture, interface) == []


def test_object_only_on_the_opposite_direction_channel_is_a_direction_mismatch():
    architecture, interface = _rv()
    _channel(interface, "a")["data_objects"] = []
    _channel(interface, "y")["data_objects"].append("A_matrix")
    _, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["data_object_channel_direction_mismatch"]
    assert found[0]["details"]["channels"] == ["y"]
    assert validate_operation_compilation(architecture, interface)


@pytest.mark.parametrize(
    "external,expected,category,blocking",
    [
        (True, "data_object_not_carried_by_channel", diag.CONTRACT_ERROR, False),
        (False, "internal_data_object_not_channel_bound", diag.TOOL_CAPABILITY, False),
        (None, "internal_data_object_not_channel_bound", diag.TOOL_CAPABILITY, False),
    ],
    ids=["external", "internal", "flag_absent"],
)
def test_object_on_no_channel_is_classified_by_whether_it_is_external(external, expected, category, blocking):
    architecture, interface = _rv()
    _channel(interface, "a")["data_objects"] = []
    obj = next(item for item in architecture["data_objects"] if item["name"] == "A_matrix")
    if external is not None:
        obj["external"] = external
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == [expected]
    assert found[0]["category"] == category
    assert found[0]["owner"] == diag.OWNER_BY_CATEGORY[category]
    # Even the contract error is not reported here: the Architect's own validator
    # ("not carried by any interface channel") already owns it, exactly once.
    assert blocking_compilation_errors(metadata) == []
    assert validate_operation_compilation(architecture, interface) == []


@pytest.mark.parametrize("role", ["valid", "ready", "payload"])
def test_duplicate_handshake_or_payload_role_blocks(role):
    architecture, interface = _rv()
    template = _signal(interface, f"a_{role}")
    interface["signals"].append({**template, "name": f"a_{role}_second"})
    _, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["ambiguous_channel_signal_role"]
    assert found[0]["details"] == {"channel": "a", "role": role}
    assert validate_operation_compilation(architecture, interface)


@pytest.mark.parametrize("role", ["metadata", "last", "keep"])
def test_duplicate_sideband_role_is_a_tool_limit_not_an_architect_error(role):
    architecture, interface = _rv()
    for suffix in ("one", "two"):
        interface["signals"].append(
            {"name": f"a_{role}_{suffix}", "channel": "a", "role": role, "width": "1"}
        )
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["multi_signal_role_on_data_channel"]
    assert found[0]["category"] == diag.TOOL_CAPABILITY
    assert found[0]["owner"] == "verifier_tool"
    assert validate_operation_compilation(architecture, interface) == []
    assert [note["reason_code"] for note in compilation_capability_notes(metadata)] == [
        "multi_signal_role_on_data_channel"
    ]


@pytest.mark.parametrize(
    "missing",
    [("valid",), ("ready",), ("payload",), ("valid", "ready"), ("valid", "payload"),
     ("ready", "payload"), ("valid", "ready", "payload")],
)
def test_ready_valid_channel_missing_any_required_role_blocks(missing):
    architecture, interface = _rv()
    interface["signals"] = [
        item for item in interface["signals"]
        if not (item.get("channel") == "a" and item.get("role") in missing)
    ]
    _, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["missing_ready_valid_signal_roles"]
    assert found[0]["details"] == {"channel": "a", "missing_roles": sorted(missing)}
    assert validate_operation_compilation(architecture, interface)


def test_missing_roles_are_only_required_of_ready_valid_channels():
    # Only the ready_valid capture path needs valid/ready/payload; another profile is
    # judged by its own protocol rules, so dropping its payload role must not raise
    # this defect.
    architecture, interface = _rv()
    _channel(interface, "a")["protocol_profile"] = "custom"
    interface["signals"] = [
        item for item in interface["signals"]
        if not (item.get("channel") == "a" and item.get("role") == "payload")
    ]
    assert "missing_ready_valid_signal_roles" not in _codes(architecture, interface)


def test_a_channel_with_no_signals_at_all_blocks():
    architecture, interface = _rv()
    interface["signals"] = [item for item in interface["signals"] if item.get("channel") != "y"]
    _, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["missing_ready_valid_signal_roles"]
    assert found[0]["details"]["missing_roles"] == ["payload", "ready", "valid"]


def test_unknown_data_object_and_unknown_type_are_owned_by_other_validators():
    architecture, interface = _rv()
    architecture["operations"][0]["inputs"].append("ghost")
    next(item for item in architecture["data_objects"] if item["name"] == "B_matrix")["data_type"] = "s99"
    metadata, found = _diagnostics(architecture, interface)
    codes = [item["reason_code"] for item in found]
    assert {"unknown_or_duplicate_data_object", "unknown_or_duplicate_data_type"} <= set(codes)
    assert all(item["category"] == diag.CONTRACT_ERROR for item in found)
    # The Architect's own reference validators report these; the compile validator must not repeat them.
    assert blocking_compilation_errors(metadata) == []


# ---------------------------------------------------------------------------
# Several defects at once: all are reported, the first is the legacy reason
# ---------------------------------------------------------------------------

def test_every_independent_defect_is_reported_in_the_order_the_old_code_raised_them():
    architecture, interface = _axi()
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]                 # ambiguous output binding
    interface["signals"].append({"name": "busy_b", "role": "busy", "direction": "output", "channel": None})
    architecture["operations"][0]["arithmetic"]["post_output"] = "nonexistent"
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == [
        "ambiguous_transport_binding",
        "ambiguous_status_binding",
        "invalid_arithmetic_declaration",
    ]
    (entry,) = metadata["unrepresentable_operations"]
    assert entry["reason_code"] == "ambiguous_transport_binding"
    assert entry["reason"] == found[0]["message"]
    assert entry["affected_domains"] == ["operation_io", "arithmetic", "lifecycle"]
    assert entry["blocked_by"] == sorted({
        "gemm_core:ambiguous_transport_binding",
        "gemm_core:ambiguous_status_binding",
        "gemm_core:invalid_arithmetic_declaration",
    })
    assert entry["shell"]["fragments"] == {
        "operation_io": "partial", "lifecycle": "partial", "arithmetic": "failed",
    }
    # Only the two Architect-owned, not-otherwise-validated defects go back.
    messages = validate_operation_compilation(architecture, interface)
    assert len(messages) == 2
    assert any("[ambiguous_transport_binding]" in item for item in messages)
    assert any("[ambiguous_status_binding]" in item for item in messages)


def test_a_bad_object_does_not_hide_the_defects_of_the_operations_other_objects():
    architecture, interface = _axi()
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]       # second output channel for Y
    _channel(interface, "bresp")["data_objects"] = ["A_matrix"]    # second input channel for A
    metadata, found = _diagnostics(architecture, interface)
    assert sorted(item["details"]["data_object"] for item in found) == ["A_matrix", "Y_matrix"]
    shell = metadata["unrepresentable_operations"][0]["shell"]
    unbound = sorted(
        item["data_object"] for item in [*shell["inputs"], *shell["outputs"]] if item.get("bound") is False
    )
    assert unbound == ["A_matrix", "Y_matrix"]
    bound = sorted(
        item["data_object"] for item in [*shell["inputs"], *shell["outputs"]] if item.get("bound", True)
    )
    assert bound == ["B_matrix", "bias_vector"]
    # Bound fragments keep their full binding (e.g. the resolved memory mapping).
    assert all("memory_mapping" in item for item in [*shell["inputs"], *shell["outputs"]] if item.get("bound", True))
    assert shell["fragments"]["operation_io"] == "partial"


def test_one_bad_operation_does_not_poison_a_sibling():
    architecture, interface = _axi()
    sibling = deepcopy(architecture["operations"][0])
    sibling["name"] = "second_op"
    architecture["operations"].append(sibling)
    # Break only the second operation: it names an object that does not exist.
    sibling["inputs"] = ["A_matrix", "B_matrix", "bias_vector", "ghost"]
    metadata, found = _diagnostics(architecture, interface)
    assert [item["operation_name"] for item in metadata["operations"]] == ["gemm_core"]
    assert [entry["name"] for entry in metadata["unrepresentable_operations"]] == ["second_op"]
    assert {item["operation_name"] for item in found} == {"second_op"}
    assert found[0]["reason_code"] == "unknown_or_duplicate_data_object"


# ---------------------------------------------------------------------------
# Lifecycle fragment
# ---------------------------------------------------------------------------

def test_two_status_signals_of_one_kind_block(subtests=None):
    for role in ("busy", "completion", "error"):
        architecture, interface = _axi()
        interface["signals"].append({"name": f"{role}_b", "role": role, "direction": "output", "channel": None})
        _, found = _diagnostics(architecture, interface)
        assert [item["reason_code"] for item in found] == ["ambiguous_status_binding"], role
        assert validate_operation_compilation(architecture, interface), role


def test_conflicting_command_metadata_tags_block_and_leave_lifecycle_failed():
    architecture, interface = _axi()
    _signal(interface, "left_ptr")["semantic"] += " data_object=B_matrix"
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["conflicting_semantic_tags"]
    shell = metadata["unrepresentable_operations"][0]["shell"]
    # The memory-mapped bindings bound, but with no lifecycle binding their memory
    # mappings could not be attached, so the I/O fragment is honestly only partial.
    assert shell["fragments"] == {"operation_io": "partial", "lifecycle": "failed", "arithmetic": "compiled"}
    assert shell["lifecycle"] is None
    assert not any("memory_mapping" in item for item in [*shell["inputs"], *shell["outputs"]])
    assert validate_operation_compilation(architecture, interface)


def test_two_base_pointers_for_one_object_block():
    architecture, interface = _axi()
    interface["signals"].append({
        "name": "left_ptr_dup", "role": "metadata", "semantic_class": "address",
        "direction": "input", "channel": "cmd", "width": "32",
        "semantic": (
            "data_object=A_matrix address_role=base byte_order=little "
            "address_sequence=contiguous word_stride_bytes=4"
        ),
    })
    _, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["ambiguous_base_pointer"]
    assert found[0]["details"] == {"data_object": "A_matrix", "count": 2}
    assert validate_operation_compilation(architecture, interface)


@pytest.mark.parametrize(
    "moved,onto",
    [("A_matrix", "bresp"), ("Y_matrix", "aw")],
    ids=["input_on_write_response", "output_on_write_address"],
)
def test_object_on_the_wrong_kind_of_memory_channel_blocks(moved, onto):
    # A channel can have the right direction and still be the wrong protocol kind:
    # `bresp` is an input channel but carries write responses, not read data; `aw`
    # is an output channel but carries write addresses, not write data.
    architecture, interface = _axi()
    for channel in interface["channels"]:
        if moved in channel["data_objects"]:
            channel["data_objects"] = [item for item in channel["data_objects"] if item != moved]
    _channel(interface, onto)["data_objects"].append(moved)
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["memory_channel_kind_mismatch"]
    assert found[0]["details"]["data_object"] == moved
    assert found[0]["details"]["channel_kind"] != found[0]["details"]["expected_kind"]
    assert "[memory_channel_kind_mismatch]" in "\n".join(validate_operation_compilation(architecture, interface))
    assert metadata["unrepresentable_operations"][0]["shell"]["fragments"]["operation_io"] == "partial"


def test_missing_lifecycle_policy_and_arithmetic_do_not_block_relaxed_callers():
    architecture, interface = _axi()
    operation = architecture["operations"][0]
    operation.pop("lifecycle_policy")
    operation.pop("arithmetic")
    metadata, found = _diagnostics(architecture, interface)
    assert {item["reason_code"] for item in found} == {
        "missing_lifecycle_policy", "missing_arithmetic_declaration",
    }
    # Owned by validate_architecture_*: reported there (with the callers' require_*
    # tolerance), never duplicated -- or wrongly enforced on an older frozen operation
    # under a local revision -- by the compile validator.
    assert blocking_compilation_errors(metadata) == []
    assert validate_operation_compilation(architecture, interface) == []
    assert {note["reason_code"] for note in compilation_capability_notes(metadata)} == {
        "missing_lifecycle_policy", "missing_arithmetic_declaration",
    }


def test_an_invalid_lifecycle_policy_is_owned_by_the_policy_validator():
    architecture, interface = _axi()
    architecture["operations"][0]["lifecycle_policy"]["completion_style"] = "sticky_until_clear"
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["invalid_lifecycle_policy"]
    assert "completion_style" in found[0]["message"]
    assert blocking_compilation_errors(metadata) == []
    fragments = metadata["unrepresentable_operations"][0]["shell"]["fragments"]
    assert fragments == {"operation_io": "compiled", "lifecycle": "partial", "arithmetic": "compiled"}


# ---------------------------------------------------------------------------
# Real-world shapes: internal stages and non-Architect-fixable limits
# ---------------------------------------------------------------------------

def _multi_stage_contracts():
    """Two operations joined by an internal (non-external) intermediate object -- the
    shape real Architect runs produce for staged designs."""

    architecture, interface = _axi()
    first = architecture["operations"][0]
    first["name"] = "stage_one"
    first["inputs"] = ["A_matrix", "B_matrix", "bias_vector"]
    first["outputs"] = ["Y_matrix"]
    architecture["data_objects"].append({
        "name": "T_matrix", "role": "intermediate", "data_type": "s32", "dimensions": ["M", "N"],
        "external": False, "producer": "stage_one", "consumers": ["stage_two"],
        "serialization": {"kind": "dense_tensor", "index_order": ["M", "N"], "description": "row-major"},
    })
    first["outputs"] = ["T_matrix"]
    second = deepcopy(first)
    second["name"] = "stage_two"
    second["inputs"] = ["T_matrix"]
    second["outputs"] = ["Y_matrix"]
    second["arithmetic"] = {"classifier_profile": "llm_extension", "reason": "post-processing stage"}
    second["semantics"] = "Post-process the intermediate result."
    first["arithmetic"] = {"classifier_profile": "llm_extension", "reason": "first stage"}
    first["semantics"] = "Compute the intermediate result."
    architecture["operations"].append(second)
    return architecture, interface


def test_internal_intermediate_objects_are_a_tool_limit_and_never_block_the_architect():
    architecture, interface = _multi_stage_contracts()
    metadata, found = _diagnostics(architecture, interface)
    assert metadata["operations"] == []
    assert {entry["name"] for entry in metadata["unrepresentable_operations"]} == {"stage_one", "stage_two"}
    assert {item["reason_code"] for item in found} == {"internal_data_object_not_channel_bound"}
    assert {item["category"] for item in found} == {diag.TOOL_CAPABILITY}
    assert {item["owner"] for item in found} == {"verifier_tool"}
    assert {item["details"]["data_object"] for item in found} == {"T_matrix"}
    # Valid contract: nothing goes back to the Architect, preflight passes and only notes it.
    assert validate_operation_compilation(architecture, interface) == []
    report = review_contract_deterministically(architecture, interface)
    assert not [item for item in report["findings"] if item["check_id"] == "operation_compilation"]
    assert {note["reason_code"] for note in report["capability_notes"]} == {
        "internal_data_object_not_channel_bound"
    }
    assert "is what the tool can bind" in found[0]["resolution_hint"]


def test_architect_validator_accepts_a_valid_contract_the_tool_cannot_automate():
    result = FakeArchitectAgent().run_structured()
    architecture = result["architecture_contract"]
    architecture["data_objects"].append({
        "name": "scratch", "role": "intermediate", "data_type": architecture["data_types"][0]["name"],
        "dimensions": [], "producer": "filter", "consumers": ["filter"], "external": False,
        "serialization": {"kind": "scalar", "index_order": [], "description": "one value"},
    })
    architecture["operations"][0]["inputs"].append("scratch")
    architecture["operations"][0]["outputs"].append("scratch")
    metadata = build_architect_operation_metadata(architecture, result["interface_contract"])
    assert [d["reason_code"] for e in metadata["unrepresentable_operations"] for d in e["diagnostics"]] == [
        "internal_data_object_not_channel_bound", "internal_data_object_not_channel_bound",
    ]
    ArchitectAgent._validate_contract_references(result)  # must not raise


# ---------------------------------------------------------------------------
# The Architect validator and preflight
# ---------------------------------------------------------------------------

def test_architect_validator_rejects_an_ambiguous_binding_with_a_precise_message():
    result = FakeArchitectAgent().run_structured()
    channel = next(item for item in result["interface_contract"]["channels"] if item["name"] == "coefficients")
    channel["data_objects"].append("sample_stream")
    with pytest.raises(ContractValidationError) as raised:
        ArchitectAgent._validate_contract_references(result)
    text = str(raised.value)
    assert "[ambiguous_transport_binding]" in text and "'sample_stream'" in text
    assert text.count("ambiguous_transport_binding") == 1, "reported once, not once per validator"
    assert "found 2" in text


@pytest.mark.parametrize("require", [True, False])
def test_relaxed_revision_flags_do_not_hide_an_architect_blocking_defect(require):
    result = FakeArchitectAgent().run_structured()
    next(item for item in result["interface_contract"]["channels"] if item["name"] == "coefficients")[
        "data_objects"
    ].append("sample_stream")
    with pytest.raises(ContractValidationError, match="ambiguous_transport_binding"):
        ArchitectAgent._validate_contract_references(
            result, require_lifecycle_policy=require, require_operation_arithmetic=require,
        )


def test_preflight_blocks_only_architect_owned_defects_and_reports_the_rest_as_notes():
    architecture, interface = _axi()
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]
    report = review_contract_deterministically(architecture, interface)
    assert report["status"] == "BLOCKED"
    findings = [item for item in report["findings"] if item["check_id"] == "operation_compilation"]
    assert len(findings) == 1
    assert findings[0]["owner"] == "architect_contract" and findings[0]["severity"] == "blocking"
    assert "ambiguous_transport_binding" in findings[0]["message"]

    clean_architecture, clean_interface = _axi()
    clean = review_contract_deterministically(clean_architecture, clean_interface)
    assert clean["status"] == "PASS" and clean["capability_notes"] == []

    staged_architecture, staged_interface = _multi_stage_contracts()
    staged = review_contract_deterministically(staged_architecture, staged_interface)
    assert staged["status"] == "PASS", staged["findings"]
    assert staged["capability_notes"]


def test_preflight_does_not_double_report_a_defect_another_validator_owns():
    architecture, interface = _axi()
    architecture["operations"][0]["arithmetic"]["post_output"] = "nonexistent"
    report = review_contract_deterministically(architecture, interface)
    assert report["status"] == "BLOCKED"
    assert [item["check_id"] for item in report["findings"]] == ["operation_arithmetic"]
    assert [note["reason_code"] for note in report["capability_notes"]] == ["invalid_arithmetic_declaration"]


def test_a_malformed_interface_is_reported_not_raised():
    architecture, interface = _axi()
    _channel(interface, "r")["metadata"] = ["protocol_group=mem protocol_channel=not_a_real_kind"]
    errors = validate_operation_compilation(architecture, interface)
    assert errors and all(isinstance(item, str) for item in errors)
    assert "could not be compiled" in errors[0] or "[" in errors[0]


@pytest.mark.parametrize("broken", [{}, {"operations": None}, {"operations": [None, 3, "x"]}])
def test_degenerate_architectures_never_crash_the_validator(broken):
    _, interface = _axi()
    assert validate_operation_compilation(broken, interface) == []
    metadata = build_architect_operation_metadata(broken, interface)
    assert metadata["operations"] == [] and metadata["unrepresentable_operations"] == []


def test_explicit_full_metadata_failure_is_classified_and_shelled():
    architecture, interface = _axi()
    operation = architecture["operations"][0]
    explicit = build_architect_operation_metadata(architecture, interface)["operations"][0]
    operation["verification_metadata"] = deepcopy(explicit)
    # Declaring both forms is a contract error the Architect can fix.
    metadata, found = _diagnostics(architecture, interface)
    assert [item["reason_code"] for item in found] == ["arithmetic_declaration_conflict"]
    entry = metadata["unrepresentable_operations"][0]
    assert entry["shell"]["fragments"] == {
        "operation_io": "failed", "lifecycle": "failed", "arithmetic": "failed",
    }
    assert all(item.get("bound") is False for item in [*entry["shell"]["inputs"], *entry["shell"]["outputs"]])
    # Hand-authored form only: never sent to the Architect.
    assert validate_operation_compilation(architecture, interface) == []


def test_error_carrying_no_reason_code_is_reported_as_unclassified_not_lost():
    error = ArchitectMetadataError("plain message")
    item = diag.diagnostic_from_error("op", error)
    assert item["reason_code"] == diag.UNCLASSIFIED
    assert item["category"] == diag.CONTRACT_ERROR
    assert item["reason_code"] not in diag.ARCHITECT_BLOCKING_REASON_CODES
    unknown = ArchitectMetadataError("x", reason_code="not_a_registered_code")
    assert diag.diagnostic_from_error("op", unknown)["reason_code"] == diag.UNCLASSIFIED
    assert diag.diagnostic_from_error("op", ValueError("bare"))["reason_code"] == diag.UNCLASSIFIED


def test_operation_names_with_odd_characters_still_produce_stable_ids():
    architecture, interface = _axi()
    architecture["operations"][0]["name"] = "gemm core.v2"
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]
    (entry,) = build_architect_operation_metadata(architecture, interface)["unrepresentable_operations"]
    assert entry["blocked_by"] == ["gemm core.v2:ambiguous_transport_binding"]
    assert all(item.startswith("lifecycle.gemm core.v2.") or item.startswith("operation.") for item in entry["affected_feature_ids"])
    json.dumps(entry)


# ---------------------------------------------------------------------------
# Robustness: shapes that used to crash the compile
# ---------------------------------------------------------------------------

def test_a_dimension_with_no_resolvable_extent_is_unknown_not_a_crash():
    """`bound_parameter` naming an undeclared parameter leaves the extent unresolved. The
    final metadata validation used to `int(None)` it; an unknown extent is simply unknown
    (as it already is while binding), and the operation still compiles."""

    result = FakeArchitectAgent().run_structured()
    architecture, interface = result["architecture_contract"], result["interface_contract"]
    architecture["dimensions"][0].update(minimum=1, maximum=16, bound_parameter="no_such_parameter")
    metadata = build_architect_operation_metadata(architecture, interface)
    assert [item["operation_name"] for item in metadata["operations"]] == ["filter"]
    assert metadata["operations"][0]["dimensions"] == {"tap_count": None}
    assert metadata["unrepresentable_operations"] == []
    # The Architect's own relational validator is what rejects the dangling parameter.
    with pytest.raises(ContractValidationError, match="unknown parameter no_such_parameter"):
        ArchitectAgent._validate_contract_references(result)
    assert validate_operation_compilation(architecture, interface) == []


@pytest.mark.parametrize("key", ["inputs", "outputs"])
def test_null_operation_io_lists_are_treated_as_empty_not_a_crash(key):
    architecture, interface = _axi()
    architecture["operations"][0][key] = None
    metadata = build_architect_operation_metadata(architecture, interface)
    accounted = [item["operation_name"] for item in metadata["operations"]] + [
        item["name"] for item in metadata["unrepresentable_operations"]
    ]
    assert accounted == ["gemm_core"]
    json.dumps(metadata)
    assert isinstance(validate_operation_compilation(architecture, interface), list)


def test_the_taxonomy_release_refuses_an_uncompilable_operation_with_a_concise_reason(tmp_path):
    from multigent.scripts.build_taxonomy_release import build_release

    architecture, interface = _axi()
    _channel(interface, "aw")["data_objects"] = ["Y_matrix"]
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    (frozen / "architecture_contract.yaml").write_text(yaml.safe_dump(architecture))
    (frozen / "interface_contract.yaml").write_text(yaml.safe_dump(interface))
    with pytest.raises(ValueError) as raised:
        build_release(
            frozen, tmp_path / "out", intended_trials=1,
            randomized_transactions_minimum=1, qualification_command="x", source_revision="test",
        )
    text = str(raised.value)
    assert "gemm_core [ambiguous_transport_binding; contract_error; owner=architect_contract]" in text
    assert "found 2" in text
    assert "shell" not in text and len(text) < 600, "a summary, not the whole diagnostic structure"
