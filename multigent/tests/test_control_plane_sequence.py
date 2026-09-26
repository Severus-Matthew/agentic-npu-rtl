"""Proves the control_plane_sequence closed vocabulary (write_reg/write_field/
read_reg/poll_field) validates the real Vitis HLS ap_ctrl_chain register map
this session reverse-engineered from gemm_hls/int8_gemm_control_s_axi.v, and
rejects the malformed variants a hand-authored declaration could plausibly get
wrong.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from multigent.verifier_tool.pool.lifecycle_policy_pool.control_plane_sequence import (
    ControlPlaneSequenceError,
    validate_control_plane_sequence,
)


def _declaration() -> dict:
    def _ptr_actions(name: str):
        return [
            {"op": "write_reg", "register": f"{name}_low",
             "value_from": {"data_object": {"a": "A_matrix", "b": "B_matrix", "c": "Y_matrix"}[name], "address_role": "base", "half": "low"}},
            {"op": "write_reg", "register": f"{name}_high",
             "value_from": {"data_object": {"a": "A_matrix", "b": "B_matrix", "c": "Y_matrix"}[name], "address_role": "base", "half": "high"}},
        ]

    return {
        "registers": {
            "control": {"address": 0x00, "fields": {"ap_start": {"bit": 0}, "ap_done": {"bit": 1}, "ap_idle": {"bit": 2}}},
            "a_low": {"address": 0x10}, "a_high": {"address": 0x14},
            "b_low": {"address": 0x1c}, "b_high": {"address": 0x20},
            "c_low": {"address": 0x28}, "c_high": {"address": 0x2c},
        },
        "job_start": {
            "actions": [
                *_ptr_actions("a"), *_ptr_actions("b"), *_ptr_actions("c"),
                {"op": "write_field", "register": "control", "field": "ap_start", "value": 1},
            ]
        },
        "job_complete": {
            "actions": [
                {"op": "poll_field", "register": "control", "field": "ap_done", "expected": 1},
            ]
        },
    }


KNOWN_OBJECTS = {"A_matrix", "B_matrix", "Y_matrix"}


def test_real_gemm_ap_ctrl_chain_declaration_is_valid():
    validate_control_plane_sequence(_declaration(), known_data_objects=KNOWN_OBJECTS)


def test_colliding_register_addresses_are_rejected():
    declaration = _declaration()
    declaration["registers"]["a_low"]["address"] = 0x00  # collides with control
    with pytest.raises(ControlPlaneSequenceError, match="collide"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_colliding_field_bits_are_rejected():
    declaration = _declaration()
    declaration["registers"]["control"]["fields"]["ap_idle"]["bit"] = 0  # collides with ap_start
    with pytest.raises(ControlPlaneSequenceError, match="collide"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_unknown_register_reference_is_rejected():
    declaration = _declaration()
    declaration["job_start"]["actions"][0]["register"] = "nope"
    with pytest.raises(ControlPlaneSequenceError, match="unknown register"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_unknown_field_reference_is_rejected():
    declaration = _declaration()
    declaration["job_complete"]["actions"][0]["field"] = "nope"
    with pytest.raises(ControlPlaneSequenceError, match="no field"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_value_from_must_reference_a_real_operation_data_object():
    declaration = _declaration()
    declaration["job_start"]["actions"][0]["value_from"]["data_object"] = "Z_matrix"
    with pytest.raises(ControlPlaneSequenceError, match="not one of"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_job_start_cannot_end_in_a_poll():
    declaration = _declaration()
    declaration["job_start"]["actions"].append(
        {"op": "poll_field", "register": "control", "field": "ap_idle", "expected": 0}
    )
    with pytest.raises(ControlPlaneSequenceError, match="must end in a write_reg or write_field"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_job_complete_must_end_in_exactly_one_poll():
    declaration = _declaration()
    declaration["job_complete"]["actions"].append(
        {"op": "write_field", "register": "control", "field": "ap_start", "value": 0}
    )
    with pytest.raises(ControlPlaneSequenceError, match="exactly one poll_field"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)


def test_job_complete_with_no_poll_is_rejected():
    declaration = _declaration()
    declaration["job_complete"]["actions"] = [
        {"op": "read_reg", "register": "control"},
    ]
    with pytest.raises(ControlPlaneSequenceError, match="exactly one poll_field"):
        validate_control_plane_sequence(declaration, known_data_objects=KNOWN_OBJECTS)
