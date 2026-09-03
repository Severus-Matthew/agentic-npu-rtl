from __future__ import annotations

import json
from pathlib import Path

import pytest

from multigent.agents.architect import ARCHITECT_OUTPUT_SCHEMA
from multigent.agents.rtl_generator import RTL_GENERATOR_OUTPUT_SCHEMA
from multigent.agents.verifier import VERIFIER_OUTPUT_SCHEMA


PROVIDER_STRUCTURED_SCHEMAS = [
    ARCHITECT_OUTPUT_SCHEMA,
    RTL_GENERATOR_OUTPUT_SCHEMA,
    VERIFIER_OUTPUT_SCHEMA,
]


def _find_keyword(value: object, keyword: str, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == keyword:
                hits.append(child_path)
            hits.extend(_find_keyword(child, keyword, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_find_keyword(child, keyword, f"{path}[{index}]"))
    return hits


@pytest.mark.parametrize("schema_path", PROVIDER_STRUCTURED_SCHEMAS)
def test_provider_structured_schema_does_not_use_oneof(schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    hits = _find_keyword(schema, "oneOf")
    assert not hits, (
        f"{schema_path} uses provider-incompatible oneOf at {hits}; "
        "use a supported nullable type union such as type: ['object', 'null'] instead"
    )
