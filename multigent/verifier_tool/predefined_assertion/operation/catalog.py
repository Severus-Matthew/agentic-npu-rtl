"""Load and render predefined correctness guidance separately from coverage bins."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


OPERATION_ASSERTION_CATALOG_PATH = Path(__file__).with_name("assertions.yaml")


@lru_cache(maxsize=1)
def load_operation_assertion_catalog() -> dict[str, Any]:
    raw = yaml.safe_load(OPERATION_ASSERTION_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("families"), dict):
        raise ValueError("Operation assertion taxonomy must contain families")
    for family, spec in raw["families"].items():
        if not isinstance(spec.get("feature_checks", {}), dict):
            raise ValueError(f"Operation assertion family {family!r} has invalid feature_checks")
        for feature, checks in spec.get("feature_checks", {}).items():
            if not isinstance(checks, list) or not checks or not all(str(x).strip() for x in checks):
                raise ValueError(f"Operation assertion feature {family}.{feature} is incomplete")
        for property_name, property_spec in spec.get("required_properties", {}).items():
            if (
                not isinstance(property_spec, dict)
                or not str(property_spec.get("applies_when", "")).strip()
                or not str(property_spec.get("check", "")).strip()
            ):
                raise ValueError(f"Operation assertion property {family}.{property_name} is incomplete")
    return raw


def render_operation_assertion_catalog() -> str:
    lines: list[str] = []
    for family, spec in load_operation_assertion_catalog()["families"].items():
        lines.append(f"- {family} predefined assertions:")
        for feature, checks in spec.get("feature_checks", {}).items():
            lines.append(f"  - {feature}: checks={' | '.join(checks)}")
        for name, property_spec in spec.get("required_properties", {}).items():
            lines.append(
                f"  - property {name}: applies_when={property_spec['applies_when']}; "
                f"check={property_spec['check']}"
            )
    return "\n".join(lines)
