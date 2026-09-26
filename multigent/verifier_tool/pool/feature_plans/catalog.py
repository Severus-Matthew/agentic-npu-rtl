"""Load and validate declarative domain feature catalogs."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml


FEATURE_PLAN_DIR = Path(__file__).parent
PROTOCOL_FEATURES_PATH = FEATURE_PLAN_DIR / "protocol_features.yaml"
LIFECYCLE_FEATURES_PATH = FEATURE_PLAN_DIR / "lifecycle_features.yaml"
OPERATION_FEATURES_PATH = FEATURE_PLAN_DIR / "operation_features.yaml"

_PROTOCOL_CHECKERS = {None, "stall_stability", "valid_low_during_reset"}
_PROTOCOL_SAMPLERS = {
    None,
    "protocol_runtime",
    "valid_ready_cross",
    "handshake_arrival_order",
    "completed_stall_length",
}
_PROTOCOL_STRATEGIES = {
    "channel_schedule",
    "reset_assert_release",
    "standard_protocol_scenarios",
}
_LIFECYCLE_CHECKERS = {
    None,
    "outputs_match_declared_reset_values",
    "busy_tracks_active_job",
    "completion_matches_final_output",
    "illegal_command_errors_without_start",
    "response_error_follows_nonokay",
    "legal_and_illegal_command_classification",
    "legal_command_starts_one_job",
    "no_output_without_active_job",
    "reset_aborts_pending_job",
    "status_pulses_are_one_cycle",
}
_LIFECYCLE_STRATEGIES = {
    "directed_lifecycle_coverage",
    "reset_assert_release",
    "legal_job_status",
    "back_to_back_legal_jobs",
    "illegal_then_legal_recovery",
    "injected_error_response",
    "legal_illegal_commands",
    "legal_command",
    "legal_job_output",
    "legal_job_retirement",
    "reset_abort_each_phase",
}
_LIFECYCLE_SAMPLERS = {"lifecycle_runtime"}


def _mapping(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{location} must be a mapping")
    return dict(value)


def _load(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("taxonomy"), dict):
        raise ValueError(f"Feature catalog {path.name} needs taxonomy metadata")
    return raw


def _with_defaults(
    raw: Mapping[str, Any], section: str, *, require_match: bool
) -> dict[str, dict[str, Any]]:
    defaults = _mapping(raw.get("feature_defaults", {}), "feature_defaults")
    default_assertion = _mapping(defaults.get("assertion", {}), "feature_defaults.assertion")
    default_coverage = _mapping(defaults.get("coverage", {}), "feature_defaults.coverage")
    default_stimulus = _mapping(defaults.get("stimulus", {}), "feature_defaults.stimulus")
    result: dict[str, dict[str, Any]] = {}
    for name, value in _mapping(raw.get(section), section).items():
        spec = _mapping(value, f"{section}.{name}")
        if not isinstance(spec.get("scope"), str) or not spec["scope"]:
            raise ValueError(f"{section}.{name} needs scope")
        if require_match and not isinstance(spec.get("match"), Mapping):
            raise ValueError(f"{section}.{name} needs match rules")
        assertion = {**default_assertion, **_mapping(spec.get("assertion", {}), f"{section}.{name}.assertion")}
        stimulus = {**default_stimulus, **_mapping(spec.get("stimulus", {}), f"{section}.{name}.stimulus")}
        coverage = {
            **default_coverage,
            **_mapping(spec.get("coverage", {}), f"{section}.{name}.coverage"),
        }
        bins = coverage.get("bins")
        if bins is not None and not isinstance(bins, list):
            raise ValueError(f"{section}.{name}.coverage.bins must be a list")
        result[str(name)] = {
            **spec,
            "assertion": assertion,
            "coverage": coverage,
            "stimulus": stimulus,
        }
    return result


def _validate_references(
    features: Mapping[str, Mapping[str, Any]],
    *,
    checkers: set[str | None],
    samplers: set[str | None],
    strategies: set[str],
    location: str,
) -> None:
    for name, spec in features.items():
        checker = spec["assertion"].get("checker")
        sampler = spec["coverage"].get("sampler")
        strategy = spec["stimulus"].get("strategy")
        if checker not in checkers:
            raise ValueError(f"{location}.{name} references unknown checker {checker!r}")
        if sampler not in samplers:
            raise ValueError(f"{location}.{name} references unknown sampler {sampler!r}")
        if strategy not in strategies:
            raise ValueError(f"{location}.{name} references unknown strategy {strategy!r}")


@lru_cache(maxsize=1)
def load_protocol_feature_catalog() -> dict[str, Any]:
    raw = _load(PROTOCOL_FEATURES_PATH)
    features = _with_defaults(raw, "features", require_match=True)
    for name, spec in features.items():
        if not spec["coverage"].get("bins"):
            raise ValueError(f"protocol feature {name!r} needs coverage bins")
    derived = _with_defaults(raw, "derived_features", require_match=False)
    _validate_references(
        features,
        checkers=_PROTOCOL_CHECKERS,
        samplers=_PROTOCOL_SAMPLERS,
        strategies=_PROTOCOL_STRATEGIES,
        location="protocol.features",
    )
    _validate_references(
        derived,
        checkers=_PROTOCOL_CHECKERS,
        samplers=_PROTOCOL_SAMPLERS,
        strategies=_PROTOCOL_STRATEGIES,
        location="protocol.derived_features",
    )
    return {**raw, "features": features, "derived_features": derived}


@lru_cache(maxsize=1)
def load_lifecycle_feature_catalog() -> dict[str, Any]:
    raw = _load(LIFECYCLE_FEATURES_PATH)
    features = _with_defaults(raw, "features", require_match=True)
    operation_features = _with_defaults(
        raw, "operation_features", require_match=False
    )
    operation_coverage = _mapping(
        raw.get("operation_coverage"), "operation_coverage"
    )
    for name, spec in operation_coverage.items():
        spec = _mapping(spec, f"operation_coverage.{name}")
        if not isinstance(spec.get("bins"), list) or not spec["bins"]:
            raise ValueError(f"operation_coverage.{name} needs bins")
        operation_coverage[name] = spec
    _validate_references(
        features,
        checkers=_LIFECYCLE_CHECKERS,
        samplers=_LIFECYCLE_SAMPLERS,
        strategies=_LIFECYCLE_STRATEGIES,
        location="lifecycle.features",
    )
    _validate_references(
        operation_features,
        checkers=_LIFECYCLE_CHECKERS,
        samplers=_LIFECYCLE_SAMPLERS,
        strategies=_LIFECYCLE_STRATEGIES,
        location="lifecycle.operation_features",
    )
    return {
        **raw,
        "features": features,
        "operation_features": operation_features,
        "operation_coverage": operation_coverage,
    }


def operation_optional_concepts(family: Mapping[str, Any]) -> dict[str, Any]:
    """Index selectable leaves without flattening the catalog's stored hierarchy."""

    result = _mapping(family.get("optional_concepts", {}), "optional_concepts")
    groups = _mapping(family.get("feature_groups", {}), "feature_groups")
    reserved = set(family.get("baseline_concepts", [])) | set(groups)
    for name, value in groups.items():
        group = _mapping(value, f"feature_groups.{name}")
        if not str(group.get("description", "")).strip():
            raise ValueError(f"feature group {name!r} needs a description")
        if set(group) - {"description", "optional_concepts"}:
            raise ValueError(f"feature group {name!r} may only organize optional concepts")
        children = _mapping(group.get("optional_concepts"), f"feature_groups.{name}.optional_concepts")
        if not children:
            raise ValueError(f"feature group {name!r} needs child concepts")
        for concept, spec in children.items():
            if concept in result or concept in reserved:
                raise ValueError(f"duplicate or reserved operation concept {concept!r}")
            result[concept] = spec
    if set(result) & reserved:
        raise ValueError("operation optional concepts overlap baseline concepts or groups")
    if set(family.get("baseline_concepts", [])) & set(groups):
        raise ValueError("operation feature groups cannot be baseline leaf concepts")
    return result


def operation_feature_groups(operation: Mapping[str, Any]) -> dict[str, Any]:
    """Return catalog groups only for a catalog-backed family, never a novel one."""

    if operation.get("coverage_family_source") == "novel":
        return {}
    family = load_operation_feature_catalog()["families"].get(
        str(operation.get("coverage_family", "")), {}
    )
    return dict(family.get("feature_groups", {}))


def operation_feature_selections(
    operation: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    """Select executable leaves; old frozen group markers are inert, not features.

    Selecting a parent does not select all its children. Only the explicitly
    declared leaves become obligations; the caller's contract is never mutated.
    """

    groups = operation_feature_groups(operation)
    return (
        [str(item) for item in operation.get("features", []) if str(item) not in groups],
        [str(item) for item in operation.get("feature_extensions", []) if str(item) not in groups],
    )


@lru_cache(maxsize=1)
def load_operation_feature_catalog() -> dict[str, Any]:
    raw = _load(OPERATION_FEATURES_PATH)
    defaults = _mapping(raw.get("feature_defaults"), "feature_defaults")
    assertion = _mapping(defaults.get("assertion"), "feature_defaults.assertion")
    stimulus = _mapping(defaults.get("stimulus"), "feature_defaults.stimulus")
    coverage = _mapping(defaults.get("coverage"), "feature_defaults.coverage")
    if not assertion.get("checker") or not coverage.get("sampler") or not stimulus.get("strategy"):
        raise ValueError("operation feature defaults need checker, sampler, and stimulus strategy")
    if assertion["checker"] != "central_golden_equivalence":
        raise ValueError("operation feature checker must use the code-owned central golden oracle")
    if stimulus["strategy"] != "canonical_discriminating_stimuli":
        raise ValueError("operation feature stimulus must use the canonical generator")
    if coverage["sampler"] != "canonical_classifier":
        raise ValueError("operation feature coverage must use the canonical classifier")
    if not isinstance(raw.get("families"), Mapping):
        raise ValueError("operation feature catalog needs families")
    for family in raw["families"].values():
        operation_optional_concepts(_mapping(family, "operation family"))
    return raw


__all__ = [
    "LIFECYCLE_FEATURES_PATH",
    "OPERATION_FEATURES_PATH",
    "PROTOCOL_FEATURES_PATH",
    "load_lifecycle_feature_catalog",
    "load_operation_feature_catalog",
    "load_protocol_feature_catalog",
    "operation_feature_groups",
    "operation_feature_selections",
    "operation_optional_concepts",
]
