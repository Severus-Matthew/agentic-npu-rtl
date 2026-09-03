from __future__ import annotations

import json

import pytest
from jsonschema.exceptions import ValidationError

from multigent.agents.base import APIAgent


TEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "value"],
    "properties": {
        "status": {"type": "string", "enum": ["READY"]},
        "value": {"type": "integer"},
    },
}


def test_parse_and_validate_accepts_valid_object() -> None:
    result = APIAgent._parse_and_validate(
        json.dumps({"status": "READY", "value": 7}),
        TEST_SCHEMA,
    )
    assert result == {"status": "READY", "value": 7}


def test_parse_and_validate_rejects_malformed_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        APIAgent._parse_and_validate(
            '{"status":"READY","value":7',
            TEST_SCHEMA,
        )


def test_parse_and_validate_rejects_schema_violation() -> None:
    with pytest.raises(ValidationError):
        APIAgent._parse_and_validate(
            json.dumps({"status": "READY", "value": "not-an-integer"}),
            TEST_SCHEMA,
        )
