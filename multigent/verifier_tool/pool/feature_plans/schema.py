"""Schema authority for resolved protocol/lifecycle/operation feature plans."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


RESOLVED_FEATURE_PLAN_SCHEMA_PATH = Path(__file__).with_name(
    "resolved_feature_plan.schema.json"
)


@lru_cache(maxsize=1)
def load_resolved_feature_plan_schema() -> dict[str, Any]:
    schema = json.loads(
        RESOLVED_FEATURE_PLAN_SCHEMA_PATH.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return schema


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_value(item) for item in sorted(value, key=str)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(
        f"Resolved Feature Plan contains non-JSON value {type(value).__name__}"
    )


def validate_resolved_feature_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize, schema-check, and semantically validate one resolved plan."""

    normalized = _json_value(plan)
    Draft202012Validator(load_resolved_feature_plan_schema()).validate(normalized)
    from multigent.verifier_tool.pool.tag_pool import load_verification_tag_pool

    tag_pool = load_verification_tag_pool()["tags"]
    domain = str(normalized["domain"])
    identifiers: set[str] = set()
    for feature in normalized["features"]:
        feature_id = str(feature["id"])
        if feature_id in identifiers:
            raise ValueError(f"Resolved Feature Plan contains duplicate id {feature_id!r}")
        identifiers.add(feature_id)
        if feature["domain"] != domain:
            raise ValueError(
                f"feature {feature_id!r} domain {feature['domain']!r} does not match plan {domain!r}"
            )
        for tag in map(str, feature.get("tags", [])):
            if tag not in tag_pool:
                raise ValueError(
                    f"feature {feature_id!r} references unknown verification tag {tag!r}"
                )
            if domain not in set(map(str, tag_pool[tag]["domains"])):
                raise ValueError(
                    f"feature {feature_id!r} tag {tag!r} does not apply to domain {domain!r}"
                )
    return normalized


__all__ = [
    "RESOLVED_FEATURE_PLAN_SCHEMA_PATH",
    "load_resolved_feature_plan_schema",
    "validate_resolved_feature_plan",
]
