"""The Architect can now declare `lifecycle_control_plane_sequence`; the tool enforces it.

Until now the declaration field was absent from the Architect's schema
(`additionalProperties: false`) while the policy enum was exposed, so an Architect
could select `control_plane_sequence` and had no way to supply what it requires: the
operation silently vanished. These tests cover the schema exposure (provider-safe:
`anyOf`, never `oneOf`), the exact conditions under which the declaration is required
or forbidden, every malformed shape, and that acceptance of a declaration did not
change when the action schema moved from `oneOf` to `anyOf`.
"""
from __future__ import annotations

import itertools
import json
import random
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA, ArchitectAgent, ContractValidationError
from multigent.verifier_tool import (
    build_architect_operation_metadata,
    render_architect_metadata_format,
    validate_operation_compilation,
    with_lifecycle_policy_schema,
)
from multigent.verifier_tool.pool.lifecycle_policy_pool import (
    ControlPlaneSequenceError,
    control_plane_sequence_schema,
    validate_control_plane_sequence,
)

REPO = Path(__file__).resolve().parents[1]
HLS_DIR = REPO / "verifier_tool" / "benchmark" / "int8_gemm_hls_golden"
OBJECTS = {"A_matrix", "B_matrix", "Y_matrix"}


def _hls():
    return (
        yaml.safe_load((HLS_DIR / "architecture_contract.yaml").read_text()),
        yaml.safe_load((HLS_DIR / "interface_contract.yaml").read_text()),
    )


def _sequence() -> dict:
    return deepcopy(_hls()[0]["operations"][0]["lifecycle_control_plane_sequence"])


def _with(mutate):
    architecture, interface = _hls()
    mutate(architecture["operations"][0])
    return architecture, interface


def _codes(architecture, interface) -> list[str]:
    metadata = build_architect_operation_metadata(architecture, interface)
    return [item["reason_code"] for entry in metadata["unrepresentable_operations"] for item in entry["diagnostics"]]


def _effective_schema():
    return ArchitectAgent().load_output_schema(ARCHITECT_OUTPUT_SCHEMA)


def _operation_schema(schema=None):
    return (schema or _effective_schema())["properties"]["architecture_contract"]["properties"]["operations"]["items"]


def _keywords(value, keyword, path="$"):
    hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == keyword:
                hits.append(f"{path}.{key}")
            hits.extend(_keywords(child, keyword, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_keywords(child, keyword, f"{path}[{index}]"))
    return hits


# ---------------------------------------------------------------------------
# Schema exposure
# ---------------------------------------------------------------------------

def test_effective_architect_schema_exposes_an_optional_control_plane_declaration():
    schema = _effective_schema()
    Draft202012Validator.check_schema(schema)
    operation = _operation_schema(schema)
    declared = operation["properties"]["lifecycle_control_plane_sequence"]
    assert {k: v for k, v in declared.items() if k != "description"} == control_plane_sequence_schema()
    assert "control_plane_sequence" in declared["description"] and "omit" in declared["description"].lower()
    # Optional: JSON Schema cannot express "required iff a policy field equals X" in a
    # provider-safe way, so the semantic validator owns that rule.
    assert "lifecycle_control_plane_sequence" not in operation["required"]
    assert "lifecycle_policy" in operation["required"]
    assert operation.get("additionalProperties") is False


def test_provider_schema_stays_free_of_oneof_after_exposure():
    assert _keywords(_effective_schema(), "oneOf") == []
    assert _keywords(control_plane_sequence_schema(), "oneOf") == []
    assert _keywords(control_plane_sequence_schema(), "anyOf"), "the action variants are expressed with anyOf"


def _schema_keywords(node, found=None, names=False):
    found = found if found is not None else set()
    if isinstance(node, dict):
        for key, child in node.items():
            if not names:
                found.add(key)
            # children of `properties` / `$defs` are field names, not keywords
            _schema_keywords(child, found, names=(key in {"properties", "$defs"} and not names))
    elif isinstance(node, list):
        for child in node:
            _schema_keywords(child, found)
    return found


def test_the_exposed_declaration_adds_no_json_schema_keyword_the_schema_did_not_already_use():
    """The provider call is `strict`; every keyword the rest of the effective schema already
    sends is known to be accepted, so the new fragment must stay inside that vocabulary."""

    schema = _effective_schema()
    without = deepcopy(schema)
    del _operation_schema(without)["properties"]["lifecycle_control_plane_sequence"]
    introduced = _schema_keywords(schema) - _schema_keywords(without)
    assert introduced == set(), introduced
    assert "const" not in _schema_keywords(control_plane_sequence_schema())


@pytest.mark.parametrize("required", [True, False])
def test_composition_is_idempotent_pure_and_present_on_both_composers(required):
    base = json.loads(ARCHITECT_OUTPUT_SCHEMA.read_text())
    before = deepcopy(base)
    once = with_lifecycle_policy_schema(base, required=required)
    assert base == before, "the base schema must not be mutated"
    assert with_lifecycle_policy_schema(once, required=required) == once
    operation = once["properties"]["architecture_contract"]["properties"]["operations"]["items"]
    assert "lifecycle_control_plane_sequence" in operation["properties"]
    assert ("lifecycle_policy" in operation["required"]) is required
    assert "lifecycle_control_plane_sequence" not in operation["required"]


def test_the_checked_in_hls_operation_now_validates_against_the_architect_schema():
    architecture, _ = _hls()
    errors = list(Draft202012Validator(_operation_schema()).iter_errors(architecture["operations"][0]))
    assert errors == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.pop("job_complete"),
        lambda s: s.pop("job_start"),
        lambda s: s.pop("registers"),
        lambda s: s.update(registers={}),
        lambda s: s["job_start"].update(actions=[]),
        lambda s: s["job_complete"].update(actions=[]),
        lambda s: s.update(extra_key=1),
        lambda s: s["job_start"]["actions"].insert(0, {"op": "toggle", "register": "control"}),
        lambda s: s["job_start"]["actions"][1].update(field="ap_start"),
        lambda s: s["job_start"]["actions"][1].pop("value_from"),
        lambda s: s["job_start"]["actions"][1]["value_from"].update(half="middle"),
        lambda s: s["job_start"]["actions"][1]["value_from"].update(address_role="limit"),
        lambda s: s["job_start"]["actions"][1]["value_from"].update(extra=1),
        lambda s: s["registers"]["a_low"].update(address=-1),
        lambda s: s["registers"]["a_low"].update(address=1.5),
        lambda s: s["registers"]["a_low"].update(address="16"),
        lambda s: s["registers"]["a_low"].update(address=True),
        lambda s: s["registers"]["a_low"].update(fields={}),
        lambda s: s["registers"]["control"]["fields"]["ap_done"].update(bit=-1),
        lambda s: s["registers"]["control"]["fields"]["ap_done"].update(bit="1"),
        lambda s: s["job_start"]["actions"][0].update(value=-1),
        lambda s: s["job_start"]["actions"][0].update(value=True),
        lambda s: s["job_complete"]["actions"][-1].update(expected=-1),
        lambda s: s["job_start"]["actions"].append("not an object"),
        lambda s: s["registers"]["a_low"].update(extra=1),
    ],
)
def test_the_effective_schema_and_the_semantic_validator_both_reject_malformed_shapes(mutate):
    architecture, interface = _hls()
    operation = architecture["operations"][0]
    mutate(operation["lifecycle_control_plane_sequence"])
    assert list(Draft202012Validator(_operation_schema()).iter_errors(operation)), "structural: schema rejects"
    codes = _codes(architecture, interface)
    assert codes == ["control_plane_sequence_schema_violation"], codes


@pytest.mark.parametrize(
    "mutate,code",
    [
        (lambda s: s["registers"]["a_low"].update(address=0), "control_plane_sequence_address_collision"),
        (lambda s: s["registers"]["control"]["fields"]["ap_done"].update(bit=0), "control_plane_sequence_address_collision"),
        (lambda s: s["job_start"]["actions"].insert(0, {"op": "read_reg", "register": "nope"}), "control_plane_sequence_unknown_reference"),
        (lambda s: s["job_start"]["actions"].insert(0, {"op": "write_field", "register": "control", "field": "nope", "value": 1}), "control_plane_sequence_unknown_reference"),
        (lambda s: s["job_complete"]["actions"][-1].update(field="nope"), "control_plane_sequence_unknown_reference"),
        (lambda s: s["job_start"]["actions"][1]["value_from"].update(data_object="C_matrix"), "control_plane_sequence_unknown_reference"),
        (lambda s: s["job_start"]["actions"].append({"op": "poll_field", "register": "control", "field": "ap_idle", "expected": 1}), "control_plane_sequence_bad_start_action"),
        (lambda s: s["job_start"].update(actions=[{"op": "read_reg", "register": "control"}]), "control_plane_sequence_bad_start_action"),
        (lambda s: s["job_complete"]["actions"].insert(0, {"op": "poll_field", "register": "control", "field": "ap_idle", "expected": 1}), "control_plane_sequence_bad_completion_poll"),
        (lambda s: s["job_complete"]["actions"].append({"op": "read_reg", "register": "control"}), "control_plane_sequence_bad_completion_poll"),
        (lambda s: s["job_complete"].update(actions=[{"op": "read_reg", "register": "control"}]), "control_plane_sequence_bad_completion_poll"),
    ],
)
def test_rules_json_schema_cannot_express_are_enforced_semantically_with_precise_codes(mutate, code):
    architecture, interface = _hls()
    operation = architecture["operations"][0]
    mutate(operation["lifecycle_control_plane_sequence"])
    # Structurally fine (the schema accepts it): only the tool's semantic rules catch it.
    assert list(Draft202012Validator(_operation_schema()).iter_errors(operation)) == []
    assert _codes(architecture, interface) == [code]
    messages = validate_operation_compilation(architecture, interface)
    assert len(messages) == 1 and f"[{code}]" in messages[0]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["job_start"]["actions"].insert(0, {"op": "read_reg", "register": "control"}),
        lambda s: s["job_start"]["actions"].insert(0, {"op": "poll_field", "register": "control", "field": "ap_idle", "expected": 1}),
        lambda s: s["job_start"]["actions"][1]["value_from"].update(half="whole"),
        lambda s: s["job_complete"]["actions"].insert(0, {"op": "read_reg", "register": "control"}),
        lambda s: s["job_complete"]["actions"][-1].update(expected=0),
        lambda s: s["job_start"]["actions"][0].update(value=0),
        lambda s: s["registers"].update(spare={"address": 0x100}),
        lambda s: s["registers"].update(spare={"address": 0x100, "fields": {"flag": {"bit": 31}}}),
        lambda s: s["registers"].update(spare={"address": 0x104, "fields": {"ap_start": {"bit": 0}}}),
        lambda s: s["registers"]["a_low"].update(address=2 ** 40),
        lambda s: s["job_start"]["actions"][1]["value_from"].update(data_object="Y_matrix"),
    ],
    ids=[
        "read_before_write", "poll_inside_start", "whole_half", "read_before_poll", "expect_zero",
        "value_zero", "register_without_fields", "field_at_bit_31", "same_field_name_other_register",
        "huge_address", "pointer_of_an_output_object",
    ],
)
def test_legal_shapes_that_look_unusual_are_accepted(mutate):
    architecture, interface = _hls()
    mutate(architecture["operations"][0]["lifecycle_control_plane_sequence"])
    assert list(Draft202012Validator(_operation_schema()).iter_errors(architecture["operations"][0])) == []
    assert _codes(architecture, interface) == []
    assert validate_operation_compilation(architecture, interface) == []


def test_precise_schema_messages_name_the_actual_problem():
    cases = {
        "job_start.actions.0: unknown action op 'toggle'": lambda s: s["job_start"]["actions"].insert(0, {"op": "toggle", "register": "control"}),
        "write_reg action: Additional properties are not allowed ('field' was unexpected)": lambda s: s["job_start"]["actions"][1].update(field="ap_start"),
        "write_reg action: 'value_from' is a required property": lambda s: s["job_start"]["actions"][1].pop("value_from"),
        "'job_complete' is a required property": lambda s: s.pop("job_complete"),
        "registers: {} should be non-empty": lambda s: s.update(registers={}),
    }
    for expected, mutate in cases.items():
        sequence = _sequence()
        mutate(sequence)
        with pytest.raises(ControlPlaneSequenceError) as raised:
            validate_control_plane_sequence(sequence, known_data_objects=OBJECTS)
        assert expected in str(raised.value), (expected, str(raised.value))
        assert raised.value.reason_code == "control_plane_sequence_schema_violation"


# ---------------------------------------------------------------------------
# oneOf -> anyOf did not change what is accepted
# ---------------------------------------------------------------------------

def _oneof_variant(schema):
    def convert(value):
        if isinstance(value, dict):
            return {("oneOf" if key == "anyOf" else key): convert(child) for key, child in value.items()}
        if isinstance(value, list):
            return [convert(child) for child in value]
        return value
    return convert(schema)


def _fuzz(sequence, rng):
    """Random structural damage to a valid declaration, biased toward the action variants."""

    sequence = deepcopy(sequence)
    actions = sequence["job_start"]["actions"] + sequence["job_complete"]["actions"]
    for _ in range(rng.randint(1, 4)):
        target = rng.choice(actions)
        move = rng.choice(["drop_key", "add_key", "swap_op", "wrong_type", "swap_value_from", "noop"])
        keys = list(target)
        if move == "drop_key" and keys:
            target.pop(rng.choice(keys))
        elif move == "add_key":
            target[rng.choice(["field", "value", "expected", "value_from", "extra", "register"])] = rng.choice([1, "x", None, {"data_object": "A_matrix", "address_role": "base", "half": "low"}])
        elif move == "swap_op":
            target["op"] = rng.choice(["write_reg", "write_field", "read_reg", "poll_field", "bogus", 3, None])
        elif move == "wrong_type" and keys:
            target[rng.choice(keys)] = rng.choice([None, [], {}, 1.5, -1, True, "", "s"])
        elif move == "swap_value_from" and "value_from" in target:
            target["value_from"] = rng.choice([{}, {"data_object": "A_matrix"}, {"data_object": "", "address_role": "base", "half": "low"}])
    if rng.random() < 0.3:
        sequence[rng.choice(["registers", "job_start", "job_complete"])] = rng.choice([None, [], {}, 3])
    return sequence


def test_anyof_accepts_exactly_what_oneof_accepted():
    """The four action variants are mutually exclusive through their `op` const, so the
    move to `anyOf` (provider-safe) must not change acceptance for any input."""

    new_validator = Draft202012Validator(control_plane_sequence_schema())
    old_validator = Draft202012Validator(_oneof_variant(control_plane_sequence_schema()))
    assert _keywords(_oneof_variant(control_plane_sequence_schema()), "oneOf"), "the oracle really uses oneOf"
    rng = random.Random(20260926)
    base = _sequence()
    valid = invalid = 0
    for _ in range(3000):
        candidate = _fuzz(base, rng)
        expected = old_validator.is_valid(candidate)
        assert new_validator.is_valid(candidate) is expected, json.dumps(candidate, sort_keys=True)[:400]
        valid += expected
        invalid += not expected
    assert valid > 100 and invalid > 100, (valid, invalid)  # the corpus exercises both outcomes


def test_every_action_variant_matches_exactly_one_branch():
    branches = control_plane_sequence_schema()["properties"]["job_start"]["properties"]["actions"]["items"]["anyOf"]
    ops = [branch["properties"]["op"]["enum"][0] for branch in branches]
    assert sorted(ops) == ["poll_field", "read_reg", "write_field", "write_reg"]
    sample = {
        "write_reg": {"op": "write_reg", "register": "r", "value_from": {"data_object": "A_matrix", "address_role": "base", "half": "low"}},
        "write_field": {"op": "write_field", "register": "r", "field": "f", "value": 1},
        "read_reg": {"op": "read_reg", "register": "r"},
        "poll_field": {"op": "poll_field", "register": "r", "field": "f", "expected": 1},
    }
    for op, action in sample.items():
        matching = [b for b in branches if Draft202012Validator(b).is_valid(action)]
        assert len(matching) == 1 and matching[0]["properties"]["op"]["enum"][0] == op


# ---------------------------------------------------------------------------
# When the declaration is required, forbidden, and satisfied
# ---------------------------------------------------------------------------

EXTENSION = {"extension_request": "lifecycle.custom_behavior"}
ACCEPTANCE = {"handshake": "valid_ready_handshake", "cps": "control_plane_sequence", "ext": EXTENSION}
COMPLETION = {"pulse": "pulse", "cps": "control_plane_sequence", "ext": EXTENSION}


@pytest.mark.parametrize("acceptance,completion,declared", list(itertools.product(ACCEPTANCE, COMPLETION, [False, True])))
def test_declaration_is_required_exactly_when_a_policy_field_is_control_plane_sequence(acceptance, completion, declared):
    def mutate(operation):
        policy = operation["lifecycle_policy"]
        policy["job_acceptance"] = ACCEPTANCE[acceptance]
        policy["completion_style"] = COMPLETION[completion]
        if not declared:
            operation.pop("lifecycle_control_plane_sequence")

    architecture, interface = _with(mutate)
    required = "cps" in (acceptance, completion)     # the exact string only; an extension sentinel is not it
    codes = _codes(architecture, interface)
    if required and not declared:
        assert codes == ["control_plane_sequence_required_but_missing"]
    elif declared and not required:
        assert codes == ["control_plane_sequence_unused"]
    else:
        assert codes == []
    blocking = validate_operation_compilation(architecture, interface)
    assert bool(blocking) is (required != declared)


def test_a_policy_extension_reference_never_satisfies_or_demands_the_declaration():
    # `{extension_request: ...}` is a different value from the string
    # 'control_plane_sequence': the contract-local extension owns that behavior.
    architecture, interface = _with(lambda op: (
        op["lifecycle_policy"].update(job_acceptance=EXTENSION, completion_style="pulse"),
        op.pop("lifecycle_control_plane_sequence"),
    ))
    assert _codes(architecture, interface) == []


def test_declaration_needs_an_axi4_lite_subordinate_group_in_the_interface():
    architecture, interface = _hls()
    interface["channels"] = [
        item for item in interface["channels"] if item["protocol_profile"] != "axi4_lite"
    ]
    names = {item["name"] for item in interface["channels"]}
    interface["signals"] = [
        item for item in interface["signals"] if item.get("channel") in names or item.get("channel") is None
    ]
    codes = _codes(architecture, interface)
    assert codes == ["control_plane_requires_axi4_lite_subordinate"]
    (message,) = validate_operation_compilation(architecture, interface)
    assert "AXI4-Lite subordinate" in message and "declare one in the interface" in message


def test_a_manager_group_is_not_a_control_interface():
    from multigent.tests.test_canonical_operation import axi_lite_contracts

    architecture, interface = deepcopy(axi_lite_contracts())
    operation = architecture["operations"][0]
    operation["lifecycle_policy"].update(
        job_acceptance="control_plane_sequence", completion_style="control_plane_sequence",
        completion_timing="observed_via_poll",
    )
    hls_operation = _hls()[0]["operations"][0]
    operation["lifecycle_control_plane_sequence"] = deepcopy(hls_operation["lifecycle_control_plane_sequence"])
    assert "control_plane_requires_axi4_lite_subordinate" in _codes(architecture, interface)


def test_compact_and_full_metadata_forms_may_not_disagree():
    architecture, interface = _hls()
    operation = architecture["operations"][0]
    compiled = build_architect_operation_metadata(architecture, interface)["operations"][0]
    operation["verification_metadata"] = deepcopy(compiled)
    operation.pop("arithmetic")
    operation["lifecycle_control_plane_sequence"]["registers"]["a_low"]["address"] = 0x200
    assert _codes(architecture, interface) == ["lifecycle_policy_conflict"]
    # A hand-authored form is never sent back to the Architect.
    assert validate_operation_compilation(architecture, interface) == []


def test_every_declared_object_pointer_reaches_the_compiled_memory_mapping():
    architecture, interface = _hls()
    metadata = build_architect_operation_metadata(architecture, interface)
    assert metadata["unrepresentable_operations"] == []
    (operation,) = metadata["operations"]
    assert operation["lifecycle"]["control_plane_sequence"] == architecture["operations"][0]["lifecycle_control_plane_sequence"]
    for binding in [*operation["inputs"], *operation["outputs"]]:
        assert binding["memory_mapping"]["base_signal"] == "", "control-plane pointers have no command signal"
        assert binding["memory_mapping"]["word_stride_bytes"] == binding["memory_mapping"]["bus_width_bits"] // 8


# ---------------------------------------------------------------------------
# The Architect validator end to end
# ---------------------------------------------------------------------------

def _hls_result(mutate=None):
    architecture, interface = _hls()
    if mutate:
        mutate(architecture["operations"][0])
    return {
        "status": "READY", "conflicts": [],
        "architecture_contract": architecture, "interface_contract": interface,
        "module_manifest": {"top": "top", "modules": [
            {"name": "top", "dependencies": [], "parameters": [], "ports": []},
        ]},
        "acceptance_criteria": {},
    }


def test_architect_validator_accepts_a_correct_declaration_and_rejects_each_defect_precisely():
    ArchitectAgent._validate_contract_references(_hls_result())
    cases = {
        "control_plane_sequence_required_but_missing": lambda op: op.pop("lifecycle_control_plane_sequence"),
        "control_plane_sequence_unused": lambda op: op["lifecycle_policy"].update(
            job_acceptance="valid_ready_handshake", completion_style="pulse"),
        "control_plane_sequence_address_collision": lambda op: op["lifecycle_control_plane_sequence"]["registers"]["a_low"].update(address=0),
        "control_plane_sequence_bad_completion_poll": lambda op: op["lifecycle_control_plane_sequence"]["job_complete"]["actions"].append({"op": "read_reg", "register": "control"}),
    }
    for code, mutate in cases.items():
        with pytest.raises(ContractValidationError) as raised:
            ArchitectAgent._validate_contract_references(_hls_result(mutate))
        assert f"[{code}]" in str(raised.value), code
        assert str(raised.value).count(f"[{code}]") == 1


def test_all_declaration_defects_are_reported_together_not_one_per_round_trip():
    def mutate(operation):
        sequence = operation["lifecycle_control_plane_sequence"]
        sequence["registers"]["a_low"]["address"] = 0
        sequence["job_complete"]["actions"].append({"op": "read_reg", "register": "control"})

    # The compile stops at the first sequence defect (validation is one pass over one
    # declaration), so this pins that the reported one is the earliest rule.
    architecture, interface = _with(mutate)
    assert _codes(architecture, interface) == ["control_plane_sequence_address_collision"]


def test_prompt_documents_the_declaration_and_its_schema():
    text = render_architect_metadata_format()
    assert "lifecycle_control_plane_sequence_extension:" in text
    assert "lifecycle_control_plane_sequence_schema:" in text
    assert "operations[].lifecycle_control_plane_sequence" in text
    assert "observed_via_poll" in text
    assert "job_complete.actions (exactly one" in text.replace("\n    ", " ")


def test_fully_declared_operation_round_trips_through_the_effective_schema_as_a_whole_result():
    """The HLS contract, wrapped as an Architect response, validates end to end."""

    architecture, interface = _hls()
    schema = _effective_schema()
    operation_schema = _operation_schema(schema)
    operation = architecture["operations"][0]
    assert Draft202012Validator(operation_schema).is_valid(operation)
    without = deepcopy(operation)
    without.pop("lifecycle_control_plane_sequence")
    assert Draft202012Validator(operation_schema).is_valid(without), "optional in the schema"
