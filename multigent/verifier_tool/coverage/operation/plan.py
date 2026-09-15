"""Validate and instantiate operation functional coverage.

The catalog fixes minimum concepts for known accelerators. Architect may explicitly
extend it for a novel family in the frozen contract. The Verifier chooses static
DUT connections for reusable templates, or custom observation functions/bins for
new semantics. Every executable point uses the same observer pipeline.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml


OPERATION_COVERAGE_FAMILIES_PATH = Path(__file__).with_name("families.yaml")
_PREDICATE_OPS = {
    "eq", "neq", "lt", "lte", "gt", "gte", "between", "one_of",
    "mod_eq", "mod_ne", "truthy", "falsy",
}


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _safe_id(value: object) -> str:
    return _normalize(value) or "unnamed"


def canonical_operation_obligation_id(
    operation_name: object, point_or_claim_id: object
) -> str:
    """Return the code-owned ID for an operation coverpoint.

    Structured-output models sometimes copy the fully qualified operation prefix
    into the local coverpoint ID, then add it again on a semantic retry. Strip any
    number of those redundant local prefixes so retries cannot recursively change
    the deterministic obligation ID.
    """

    operation_id = _safe_id(operation_name)
    local_id = _safe_id(point_or_claim_id)
    redundant_prefix = f"operation_{operation_id}_"
    while local_id.startswith(redundant_prefix):
        local_id = local_id[len(redundant_prefix) :]
    return f"operation.{operation_id}.{local_id or 'unnamed'}"


def canonicalize_operation_obligation_claim(
    claim: object, operation_names: list[str]
) -> str:
    value = str(claim)
    for operation_name in operation_names:
        dotted_prefix = f"operation.{_safe_id(operation_name)}."
        if value.startswith(dotted_prefix):
            return canonical_operation_obligation_id(
                operation_name, value[len(dotted_prefix) :]
            )
    return value


@lru_cache(maxsize=1)
def load_operation_coverage_families() -> dict[str, Any]:
    raw = yaml.safe_load(OPERATION_COVERAGE_FAMILIES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("families"), dict):
        raise ValueError("Operation coverage taxonomy must contain families")
    for family, spec in raw["families"].items():
        aliases = spec.get("aliases")
        concepts = spec.get("baseline_concepts")
        if not isinstance(aliases, list) or not aliases:
            raise ValueError(f"Operation family {family!r} needs aliases")
        if not isinstance(concepts, list) or not concepts or len(concepts) != len(set(concepts)):
            raise ValueError(f"Operation family {family!r} has invalid baseline_concepts")
        starter_bins = spec.get("starter_bins")
        if not isinstance(starter_bins, dict) or set(starter_bins) != set(concepts):
            raise ValueError(f"Operation family {family!r} has invalid starter_bins")
        if any(
            not isinstance(bins, list) or not bins or len(bins) != len(set(bins))
            for bins in starter_bins.values()
        ):
            raise ValueError(f"Operation family {family!r} has empty or duplicate starter bins")
        optional = spec.get("optional_concepts", {})
        if not isinstance(optional, dict) or set(optional) & set(concepts):
            raise ValueError(f"Operation family {family!r} has invalid optional_concepts")
        for concept, optional_spec in optional.items():
            if not isinstance(optional_spec, dict):
                raise ValueError(
                    f"Operation family {family!r} optional concept {concept!r} must be a mapping"
                )
            bins = optional_spec.get("starter_bins")
            if (
                not str(optional_spec.get("applies_when", "")).strip()
                or not isinstance(bins, list)
                or not bins
                or len(bins) != len(set(bins))
            ):
                raise ValueError(
                    f"Operation family {family!r} optional concept {concept!r} is incomplete"
                )
    return raw


def render_operation_coverage_catalog() -> str:
    lines: list[str] = []
    for family, spec in load_operation_coverage_families()["families"].items():
        lines.append(f"- {family}: aliases={','.join(spec['aliases'])}")
        for concept in spec["baseline_concepts"]:
            lines.append(
                f"  - {concept}: starter_bins="
                f"{','.join(spec['starter_bins'][concept])}"
            )
        for concept, optional_spec in spec.get("optional_concepts", {}).items():
            lines.append(
                f"  - optional {concept}: applies_when={optional_spec['applies_when']} "
                f"starter_bins={','.join(optional_spec['starter_bins'])}"
            )
    return "\n".join(lines)


def operation_family(kind: object) -> str | None:
    normalized = _normalize(kind)
    for family, spec in load_operation_coverage_families()["families"].items():
        if normalized in {_normalize(alias) for alias in spec["aliases"]}:
            return family
    return None


def validate_architecture_operation_features(
    architecture_contract: Mapping[str, Any],
) -> list[str]:
    """Enforce catalog baselines while allowing explicit novel-family extensions."""

    errors: list[str] = []
    families = load_operation_coverage_families()["families"]
    for operation in architecture_contract.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        name = str(operation.get("name", ""))
        family = str(operation.get("coverage_family", ""))
        family_source = str(operation.get("coverage_family_source", ""))
        features = list(map(str, operation.get("features", [])))
        extensions = list(map(str, operation.get("feature_extensions", [])))
        if not family:
            errors.append(f"operation {name} must declare a coverage_family")
            continue
        if family_source not in {"catalog", "novel"}:
            errors.append(
                f"operation {name} must declare coverage_family_source catalog or novel"
            )
        elif family_source == "catalog" and family not in families:
            errors.append(
                f"operation {name} marks unknown family {family!r} as catalog"
            )
        elif family_source == "novel" and family in families:
            errors.append(
                f"operation {name} marks catalog family {family!r} as novel"
            )
        inferred = operation_family(operation.get("kind"))
        if inferred and inferred != family:
            errors.append(
                f"operation {name} kind {operation.get('kind')!r} requires "
                f"coverage_family {inferred!r}"
            )
        if inferred and family_source != "catalog":
            errors.append(
                f"operation {name} kind {operation.get('kind')!r} must use a catalog family"
            )
        selected = set(features)
        extension_set = set(extensions)
        if len(features) != len(selected):
            errors.append(f"operation {name} features contains duplicates")
        if len(extensions) != len(extension_set):
            errors.append(f"operation {name} feature_extensions contains duplicates")
        overlap = sorted(selected & extension_set)
        if overlap:
            errors.append(
                f"operation {name} feature_extensions duplicate baseline features {overlap}"
            )
        if not selected:
            errors.append(f"operation {name} must declare at least one feature")
        if family in families:
            allowed = set(families[family]["baseline_concepts"])
            missing = sorted(allowed - selected)
            unknown = sorted(selected - allowed)
            if missing or unknown:
                errors.append(
                    f"operation {name} feature selection mismatch for family {family}; "
                    f"missing={missing}, unknown={unknown}"
                )
    return errors


def _validate_predicate(predicate: Mapping[str, Any], location: str) -> list[str]:
    errors: list[str] = []
    op = predicate.get("op")
    args = predicate.get("args")
    if op not in _PREDICATE_OPS:
        return [f"{location} uses unsupported predicate op {op!r}"]
    if not isinstance(args, list):
        return [f"{location} predicate requires args array"]
    expected_lengths = {
        "eq": 1, "neq": 1, "lt": 1, "lte": 1, "gt": 1, "gte": 1,
        "between": 2, "mod_eq": 2, "mod_ne": 2, "truthy": 0, "falsy": 0,
    }
    if op in expected_lengths and len(args) != expected_lengths[op]:
        errors.append(
            f"{location} predicate {op} requires {expected_lengths[op]} args"
        )
    if op == "one_of" and not args:
        errors.append(f"{location} predicate one_of requires at least one arg")
    if op in {"mod_eq", "mod_ne"}:
        divisor = args[0] if len(args) == 2 else None
        if not isinstance(divisor, int) or isinstance(divisor, bool) or divisor <= 0:
            errors.append(f"{location} predicate {op} requires positive integer divisor")
        if len(args) != 2 or not isinstance(args[1], int):
            errors.append(f"{location} predicate {op} requires integer remainder")
    return errors


def validate_operation_coverage(
    architecture_contract: Mapping[str, Any], specs: list[Mapping[str, Any]]
) -> list[str]:
    """Validate coverage specs and enforce family baseline completeness."""

    errors: list[str] = []
    operations = {
        str(item.get("name")): item
        for item in architecture_contract.get("operations", [])
        if isinstance(item, Mapping)
    }
    seen_operations: set[str] = set()
    seen_ids: set[str] = set()
    by_operation: dict[str, list[Mapping[str, Any]]] = {}
    for spec in specs:
        operation_name = str(spec.get("operation_name", ""))
        family = str(spec.get("family", ""))
        if operation_name not in operations:
            errors.append(f"operation coverage references unknown operation {operation_name!r}")
            continue
        if operation_name in seen_operations:
            errors.append(f"duplicate operation coverage entry for {operation_name}")
        seen_operations.add(operation_name)
        contract_family = str(operations[operation_name].get("coverage_family", ""))
        expected_family = operation_family(operations[operation_name].get("kind"))
        known_families = load_operation_coverage_families()["families"]
        if family not in known_families and family != contract_family:
            errors.append(
                f"operation {operation_name} selects unknown coverage family {family!r}"
            )
        if expected_family and family != expected_family:
            errors.append(
                f"operation {operation_name} kind {operations[operation_name].get('kind')!r} "
                f"requires coverage family {expected_family!r}"
            )
        if contract_family and family != contract_family:
            errors.append(
                f"operation {operation_name} coverage must use contract family "
                f"{contract_family!r}, not {family!r}"
            )
        by_operation[operation_name] = list(spec.get("coverpoints", []))

        concept_sources: dict[str, set[str]] = {}
        for point in spec.get("coverpoints", []):
            point_id = str(point.get("id", ""))
            concept = str(point.get("concept", ""))
            source = str(point.get("source", ""))
            field = str(point.get("field", ""))
            full_id = canonical_operation_obligation_id(operation_name, point_id)
            if full_id in seen_ids:
                errors.append(f"duplicate operation coverpoint id {full_id}")
            seen_ids.add(full_id)
            if not point_id or not concept or not field:
                errors.append(f"operation {operation_name} has incomplete coverpoint identity")
            concept_sources.setdefault(concept, set()).add(source)
            bins = point.get("bins", [])
            names = [str(item.get("name", "")) for item in bins if isinstance(item, Mapping)]
            if not bins or len(names) != len(set(names)) or any(not name for name in names):
                errors.append(f"operation coverpoint {full_id} has invalid bins")
            for bin_spec in bins:
                if isinstance(bin_spec, Mapping):
                    intent = str(bin_spec.get("intent", "")).lower()
                    noncoverable_markers = (
                        "inapplicable",
                        "not sampled",
                        "unreachable",
                        "impossible",
                        "placeholder",
                    )
                    if any(marker in intent for marker in noncoverable_markers):
                        errors.append(
                            f"operation coverpoint {full_id}.{bin_spec.get('name')} "
                            "declares a non-coverable bin; every bin must represent "
                            "at least one legal concrete contract transaction"
                        )
                    predicate = bin_spec.get("predicate")
                    if isinstance(predicate, Mapping):
                        errors.extend(_validate_predicate(predicate, f"{full_id}.{bin_spec.get('name')}"))

        enforced_family = contract_family or expected_family or (family if family in known_families else None)
        if enforced_family:
            baseline = set(operations[operation_name].get("features", []))
            if not baseline and enforced_family in known_families:
                baseline = set(known_families[enforced_family]["baseline_concepts"])
            architect_extensions = set(
                operations[operation_name].get("feature_extensions", [])
            )
            required = baseline | architect_extensions
            implemented = {
                concept
                for concept, sources in concept_sources.items()
                if sources.intersection({"baseline", "architect_extension"})
            }
            missing = sorted(required - implemented)
            wrong_sources: list[str] = []
            for concept, sources in concept_sources.items():
                expected_source = (
                    "baseline"
                    if concept in baseline
                    else "architect_extension"
                    if concept in architect_extensions
                    else "llm_extension"
                )
                if sources != {expected_source}:
                    wrong_sources.append(
                        f"{concept}: expected {expected_source}, got {sorted(sources)}"
                    )
            if missing or wrong_sources:
                errors.append(
                    f"operation {operation_name} baseline concepts mismatch; "
                    f"missing={missing}, wrong_sources={wrong_sources}"
                )

    missing_operations = sorted(set(operations) - set(by_operation))
    if missing_operations:
        errors.append(
            "missing operation coverage for contract operations: "
            + ", ".join(missing_operations)
        )
    return errors


def build_operation_coverage_plan(
    specs: list[Mapping[str, Any]], *, sampling_bindings: list[Mapping[str, Any]] | None = None,
    architecture: Mapping[str, Any] | None = None, interface: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    obligations: list[dict[str, Any]] = []
    for spec in specs:
        operation_name = str(spec["operation_name"])
        for point in spec["coverpoints"]:
            obligations.append(
                {
                    "id": canonical_operation_obligation_id(
                        operation_name, point["id"]
                    ),
                    "template": "operation_coverpoint",
                    "scope": "operation",
                    "scope_name": operation_name,
                    "kind": "coverpoint",
                    "description": str(point["description"]),
                    "bindings": {
                        "operation_name": operation_name,
                        "family": str(spec["family"]),
                        "field": str(point["field"]),
                        "concept": str(point["concept"]),
                        "source": str(point["source"]),
                    },
                    "bins": [dict(item) for item in point["bins"]],
                    "checks": [],
                }
            )
    obligations.sort(key=lambda item: item["id"])
    plan = {"schema_version": 1, "source": "verifier operation coverage", "obligations": obligations}
    if sampling_bindings:
        from multigent.verifier_tool.coverage.operation.sampling import attach_operation_sampling
        plan = attach_operation_sampling(plan, sampling_bindings, architecture or {}, interface or {})
    return plan


def operation_plan_for_tests(
    specs: list[Mapping[str, Any]], contents: list[str], architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> dict[str, Any]:
    from multigent.verifier_tool.coverage.operation.sampling import extract_operation_sampling_bindings
    from multigent.verifier_tool.coverage.operation.sampling import OperationSamplingError, operation_observer_views
    plan = build_operation_coverage_plan(
        specs, sampling_bindings=extract_operation_sampling_bindings(contents),
        architecture=architecture, interface=interface,
    )
    operation_observer_views(contents)  # Validate local callable definitions without executing sources.
    missing = [item["id"] for item in plan["obligations"] if not item["bindings"].get("sampling")]
    if missing:
        raise OperationSamplingError(f"Missing operation sampling bindings: {sorted(missing)}; use a reusable template or custom observer")
    return plan


def merge_coverage_plans(interface_plan: Mapping[str, Any], operation_plan: Mapping[str, Any]) -> dict[str, Any]:
    obligations = [
        *[dict(item) for item in interface_plan.get("obligations", [])],
        *[dict(item) for item in operation_plan.get("obligations", [])],
    ]
    ids = [str(item["id"]) for item in obligations]
    if len(ids) != len(set(ids)):
        raise ValueError("Combined coverage plan contains duplicate obligation IDs")
    obligations.sort(key=lambda item: str(item["id"]))
    return {
        "schema_version": 3,
        "source": "interface taxonomy + verifier operation coverage",
        "monitor": dict(interface_plan.get("monitor", {})),
        "obligations": obligations,
    }
