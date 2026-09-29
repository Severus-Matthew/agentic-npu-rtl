"""Validate and instantiate operation functional coverage.

The catalog fixes minimum concepts for known accelerators. Architect may explicitly
extend it for a novel family in the frozen contract. The Verifier chooses static
DUT connections for reusable templates, or custom observation functions/bins for
new semantics. Every executable point uses the same observer pipeline.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Mapping

from multigent.verifier_tool.pool.feature_plans.catalog import (
    OPERATION_FEATURES_PATH,
    load_operation_feature_catalog,
    operation_feature_groups,
    operation_feature_selections,
    operation_optional_concepts,
)
OPERATION_COVERAGE_FAMILIES_PATH = OPERATION_FEATURES_PATH
_PREDICATE_OPS = {
    "eq", "neq", "lt", "lte", "gt", "gte", "between", "one_of",
    "mod_eq", "mod_ne", "truthy", "falsy",
}


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _safe_id(value: object) -> str:
    return _normalize(value) or "unnamed"


def _formula_stage_concepts(operation: Mapping[str, Any]) -> set[str]:
    arithmetic = operation.get("arithmetic", {})
    stages = arithmetic.get("post_operations", {}) if isinstance(arithmetic, Mapping) else {}
    if not isinstance(stages, Mapping):
        return set()
    return {
        str(name)
        for name, stage in stages.items()
        if isinstance(stage, Mapping) and stage.get("kind") == "llm_defined"
    }


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
    raw = load_operation_feature_catalog()
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
        optional = operation_optional_concepts(spec)
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
    lines = [
        "Feature groups are organizational only, not selectable coverpoints. "
        "Put applicable child names in feature_extensions; never select all "
        "children merely because the group exists. Legacy frozen group markers "
        "create no standalone obligation. Arithmetic order comes from the "
        "contract, not this catalog's grouping. Formula-defined arithmetic DAG "
        "stage names are additional required concepts: the Verifier chooses their "
        "bins and declarative predicates with source=architect_extension, while "
        "verifier_tool samples the solver-compiled stage output from the checked "
        "canonical golden trace; no custom observer is needed."
    ]
    for family, spec in load_operation_coverage_families()["families"].items():
        lines.append(f"- {family}: aliases={','.join(spec['aliases'])}")
        for concept in spec["baseline_concepts"]:
            lines.append(
                f"  - {concept}: starter_bins="
                f"{','.join(spec['starter_bins'][concept])}"
            )
        for group_name, group in spec.get("feature_groups", {}).items():
            lines.append(
                f"  - group {group_name} (no standalone bins/assertions/stimulus): "
                f"{group['description']}"
            )
            for concept, optional_spec in group["optional_concepts"].items():
                lines.append(
                    f"    - optional {concept}: applies_when={optional_spec['applies_when']} "
                    f"starter_bins={','.join(optional_spec['starter_bins'])}"
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
            unknown = sorted(selected - allowed - set(operation_feature_groups(operation)))
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
        groups = operation_feature_groups(operations[operation_name])

        concept_sources: dict[str, set[str]] = {}
        for point in spec.get("coverpoints", []):
            point_id = str(point.get("id", ""))
            concept = str(point.get("concept", ""))
            if concept in groups:
                errors.append(
                    f"operation {operation_name} concept {concept!r} is a feature group, "
                    "not a coverpoint; select its applicable leaf concepts"
                )
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
            predicate_owners: dict[str, str] = {}
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
                        predicate_key = json.dumps(dict(predicate), sort_keys=True)
                        prior_name = predicate_owners.get(predicate_key)
                        if prior_name is not None:
                            errors.append(
                                f"operation coverpoint {full_id} bins {prior_name!r} and "
                                f"{bin_spec.get('name')!r} use the identical predicate; "
                                "distinct semantic bins must not be credited by the same observation"
                            )
                        else:
                            predicate_owners[predicate_key] = str(bin_spec.get("name", ""))
                        errors.extend(_validate_predicate(predicate, f"{full_id}.{bin_spec.get('name')}"))

        enforced_family = contract_family or expected_family or (family if family in known_families else None)
        if enforced_family:
            baseline_names, extension_names = operation_feature_selections(operations[operation_name])
            baseline = set(baseline_names)
            if not operations[operation_name].get("features") and enforced_family in known_families:
                baseline = set(known_families[enforced_family]["baseline_concepts"])
            architect_extensions = set(extension_names)
            formula_stages = _formula_stage_concepts(operations[operation_name])
            required = baseline | architect_extensions | formula_stages
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
                    if concept in architect_extensions or concept in formula_stages
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


def validate_frozen_operation_scope(
    architecture_contract: Mapping[str, Any], specs: list[Mapping[str, Any]]
) -> list[str]:
    """Reject operation obligations added after the Architect scope was frozen.

    Novel checker implementation remains LLM-owned when Architect declares a
    feature extension.  A Verifier-proposed risk may be reported diagnostically,
    but it cannot silently become a required release bin during the campaign.
    """

    declared = {
        str(operation.get("name", "")): {
            concept for selection in operation_feature_selections(operation)
            for concept in selection
        } | _formula_stage_concepts(operation)
        for operation in architecture_contract.get("operations", [])
        if isinstance(operation, Mapping)
    }
    errors: list[str] = []
    for spec in specs:
        operation_name = str(spec.get("operation_name", ""))
        allowed = declared.get(operation_name)
        if allowed is None:
            continue
        unexpected = sorted(
            {
                str(point.get("concept", ""))
                for point in spec.get("coverpoints", [])
                if isinstance(point, Mapping)
            }
            - allowed
        )
        if unexpected:
            errors.append(
                f"operation {operation_name} adds post-freeze release concepts "
                f"{unexpected}; required operation coverage is exactly Architect "
                f"leaf features+feature_extensions={sorted(allowed)}. Keep proposed risks "
                "diagnostic, and use existing interface/protocol obligations for "
                "handshake, stall, reset, completion, or error behavior."
            )
    return errors


def synthesize_code_owned_operation_coverage(
    specs: list[Mapping[str, Any]],
    architecture_contract: Mapping[str, Any],
    operation_metadata: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Replace known-operation declarations with deterministic canonical points.

    Structured output still carries ``operation_coverage`` for compatibility with
    the existing Verifier schema.  For concepts whose classifier, bins, stimulus,
    and sampler are owned by :mod:`verifier_tool`, however, the LLM declaration is
    not authoritative.  This compiler derives those points from the frozen
    Architect feature list and preserves only genuinely non-code-owned points for
    the LLM-extension path.
    """

    from multigent.verifier_tool.pool.operation_metadata import supported_code_owned_concepts
    from multigent.verifier_tool.operation.stimulus import canonical_bin_dispositions

    supplied = {
        str(spec.get("operation_name", "")): spec
        for spec in specs
        if isinstance(spec, Mapping)
    }
    metadata_by_name = {
        str(item.get("operation_name", "")): item
        for item in operation_metadata.get("operations", [])
        if isinstance(item, Mapping)
    }
    supported = supported_code_owned_concepts(operation_metadata)
    result: list[dict[str, Any]] = []

    for operation in architecture_contract.get("operations", []):
        if not isinstance(operation, Mapping):
            continue
        operation_name = str(operation.get("name", ""))
        family = str(operation.get("coverage_family", ""))
        baseline, extensions = operation_feature_selections(operation)
        groups = operation_feature_groups(operation)
        selected = [*baseline, *extensions]
        code_owned = supported.get(operation_name, set()).intersection(selected)
        previous = supplied.get(operation_name, {})
        preserved = [
            dict(point)
            for point in previous.get("coverpoints", [])
            if isinstance(point, Mapping)
            and str(point.get("concept", "")) not in code_owned
            and str(point.get("concept", "")) not in groups
        ]

        metadata = metadata_by_name.get(operation_name, {})
        generated: list[dict[str, Any]] = []
        for concept in selected:
            if concept not in code_owned:
                continue
            dispositions = canonical_bin_dispositions(metadata, concept)
            if dispositions is None:
                raise ValueError(
                    f"Code-owned operation concept {operation_name}.{concept} "
                    "has no canonical bin compiler"
                )
            unresolved = [
                item
                for item in dispositions
                if item.get("status")
                not in {"required_reachable", "proven_unreachable", "inapplicable"}
            ]
            if unresolved:
                raise ValueError(
                    f"Code-owned operation concept {operation_name}.{concept} has "
                    f"unresolved canonical bins: {unresolved!r}"
                )
            bins = [
                {
                    "name": str(item["bin"]["name"]),
                    "intent": str(item["bin"]["intent"]),
                    "predicate": dict(item["bin"]["predicate"]),
                }
                for item in dispositions
                if item.get("status") == "required_reachable"
            ]
            if not bins:
                raise ValueError(
                    f"Code-owned operation concept {operation_name}.{concept} has "
                    "no reachable canonical bin"
                )
            generated.append(
                {
                    "id": concept,
                    "concept": concept,
                    "field": f"canonical_job.{concept}",
                    "source": (
                        "baseline" if concept in baseline else "architect_extension"
                    ),
                    "description": (
                        f"Tool-owned canonical {concept} classification for "
                        f"checked operation {operation_name}."
                    ),
                    "bins": bins,
                }
            )

        result.append(
            {
                "operation_name": operation_name,
                "family": family or str(previous.get("family", "")),
                "coverpoints": [*generated, *preserved],
            }
        )
    return result


def build_operation_coverage_plan(
    specs: list[Mapping[str, Any]], *, sampling_bindings: list[Mapping[str, Any]] | None = None,
    architecture: Mapping[str, Any] | None = None, interface: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    obligations: list[dict[str, Any]] = []
    for spec in specs:
        operation_name = str(spec["operation_name"])
        groups = operation_feature_groups({"coverage_family": spec["family"]})
        parents = {
            concept: group_name
            for group_name, group in groups.items()
            for concept in group["optional_concepts"]
        }
        for point in spec["coverpoints"]:
            if str(point["concept"]) in groups:
                raise ValueError(
                    f"operation feature group {point['concept']!r} cannot create coverage bins"
                )
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
                        **({"feature_group": parents[str(point["concept"])]}
                           if str(point["concept"]) in parents else {}),
                    },
                    "bins": [dict(item) for item in point["bins"]],
                    "checks": [],
                }
            )
    obligations.sort(key=lambda item: item["id"])
    plan = {"schema_version": 1, "source": "verifier operation coverage", "obligations": obligations}
    if sampling_bindings:
        from multigent.verifier_tool.operation.coverage.sampling import attach_operation_sampling
        plan = attach_operation_sampling(plan, sampling_bindings, architecture or {}, interface or {})
    return plan


def operation_plan_for_tests(
    specs: list[Mapping[str, Any]], contents: list[str], architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
) -> dict[str, Any]:
    from multigent.verifier_tool.operation.coverage.sampling import extract_operation_sampling_bindings
    from multigent.verifier_tool.operation.coverage.sampling import OperationSamplingError, operation_observer_views
    from multigent.verifier_tool.pool.operation_metadata import build_architect_operation_metadata
    from multigent.verifier_tool.pool.operation_metadata import solver_compiled_formula_concepts
    from multigent.verifier_tool.pool.operation_metadata import supported_code_owned_concepts
    from multigent.verifier_tool.operation.stimulus import (
        CanonicalStimulusGenerationError,
        canonical_bin_dispositions,
        generate_solver_compiled_stimulus_for_bin,
    )

    metadata = build_architect_operation_metadata(architecture, interface)
    code_owned = supported_code_owned_concepts(metadata)
    formula_owned = solver_compiled_formula_concepts(metadata)
    metadata_by_operation = {
        str(item["operation_name"]): item for item in metadata["operations"]
    }
    canonical_ids = {
        canonical_operation_obligation_id(spec["operation_name"], point["id"])
        for spec in specs
        for point in spec["coverpoints"]
        if str(point.get("concept", ""))
        in (
            code_owned.get(str(spec.get("operation_name", "")), set())
            | formula_owned.get(str(spec.get("operation_name", "")), set())
        )
    }
    raw_bindings = extract_operation_sampling_bindings(contents)
    llm_bindings = [
        item for item in raw_bindings
        if canonical_operation_obligation_id(item.get("operation"), item.get("point"))
        not in canonical_ids
    ]
    plan = build_operation_coverage_plan(
        specs, sampling_bindings=llm_bindings,
        architecture=architecture, interface=interface,
    )
    for point in plan["obligations"]:
        operation_name = str(point["bindings"]["operation_name"])
        concept = str(point["bindings"]["concept"])
        if concept in formula_owned.get(operation_name, set()):
            resolved_bins: list[dict[str, Any]] = []
            invalid_bins: list[dict[str, str]] = []
            for item in point["bins"]:
                try:
                    witness = generate_solver_compiled_stimulus_for_bin(
                        metadata_by_operation[operation_name], concept, item
                    )
                except CanonicalStimulusGenerationError as exc:
                    invalid_bins.append(
                        {
                            "bin": str(item.get("name", "")),
                            "status": exc.code,
                            "reason": exc.reason,
                        }
                    )
                    continue
                resolved_bins.append(
                    {
                        **dict(item),
                        "required": True,
                        "minimum_hits": 1,
                        "applicability": {
                            "status": "required_reachable",
                            "basis": (
                                "Verifier predicate has a deterministic solver witness "
                                "through the Contract Reviewer-compiled formula DAG"
                            ),
                            "witness": {
                                "label": witness["label"],
                                "digest_input": witness["stimulus"],
                            },
                        },
                    }
                )
            if invalid_bins:
                raise OperationSamplingError(
                    "Verifier formula-stage coverage contains a bin without a legal "
                    "solver witness; revise the bin predicate instead of declaring "
                    "unreachable coverage required: "
                    + repr(
                        {
                            "operation": operation_name,
                            "concept": concept,
                            "bins": invalid_bins,
                        }
                    )
                )
            point["bins"] = resolved_bins
            point["bindings"]["sampling"] = {
                "template": "canonical_job",
                "origin": "verifier_tool_solver_compiled_formula",
            }
            continue
        if concept not in code_owned.get(operation_name, set()):
            continue
        dispositions = canonical_bin_dispositions(
            metadata_by_operation[operation_name], concept
        )
        if dispositions is None:
            continue
        unresolved = [
            item
            for item in dispositions
            if item["status"]
            not in {"required_reachable", "proven_unreachable", "inapplicable"}
        ]
        if unresolved:
            raise OperationSamplingError(
                "Known operation coverage has unresolved obligations: "
                + repr(
                    [
                        {
                            "operation": operation_name,
                            "concept": concept,
                            "bin": item["bin"]["name"],
                            "status": item["status"],
                            "reason": item["reason"],
                        }
                        for item in unresolved
                    ]
                )
            )
        point["bins"] = [
            {
                **dict(item["bin"]),
                "required": item["status"] == "required_reachable",
                "minimum_hits": 1,
                "applicability": {
                    "status": item["status"],
                    "basis": item["reason"],
                    "witness": item["witness"],
                },
            }
            for item in dispositions
        ]
        point["bindings"]["sampling"] = {
            "template": "canonical_job",
            "origin": "verifier_tool",
        }
    operation_observer_views(
        contents, ignored_ids=canonical_ids
    )  # Validate only LLM-owned observer bodies without executing sources.
    missing = [item["id"] for item in plan["obligations"] if not item["bindings"].get("sampling")]
    if missing:
        raise OperationSamplingError(f"Missing operation sampling bindings: {sorted(missing)}; use a reusable template or custom observer")
    plan["operation_metadata"] = metadata
    return plan


def merge_coverage_plans(interface_plan: Mapping[str, Any], operation_plan: Mapping[str, Any]) -> dict[str, Any]:
    from multigent.verifier_tool.manifest import compile_verification_manifest
    from multigent.verifier_tool.lifecycle.coverage import build_lifecycle_coverage_plan

    lifecycle_plan = build_lifecycle_coverage_plan(
        interface_plan.get("interface_contract", {}),
        operation_plan.get("operation_metadata", {}),
    )

    obligations = [
        *[dict(item) for item in interface_plan.get("obligations", [])],
        *[dict(item) for item in operation_plan.get("obligations", [])],
        *[dict(item) for item in lifecycle_plan.get("obligations", [])],
    ]
    ids = [str(item["id"]) for item in obligations]
    if len(ids) != len(set(ids)):
        raise ValueError("Combined coverage plan contains duplicate obligation IDs")
    obligations.sort(key=lambda item: str(item["id"]))
    manifest = compile_verification_manifest(
        interface_plan, operation_plan, lifecycle_plan
    )
    return {
        "schema_version": 3,
        "source": "interface taxonomy + verifier operation coverage",
        "interface_contract": dict(interface_plan.get("interface_contract", {})),
        "standard_protocol_plan": dict(
            interface_plan.get("standard_protocol_plan", {})
        ),
        "operation_metadata": dict(
            operation_plan.get("operation_metadata", {})
        ),
        "lifecycle_plan": lifecycle_plan,
        "verification_manifest": manifest,
        "verification_manifest_hash": manifest["manifest_hash"],
        "monitor": dict(interface_plan.get("monitor", {})),
        "obligations": obligations,
    }
