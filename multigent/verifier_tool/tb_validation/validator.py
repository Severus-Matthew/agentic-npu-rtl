"""Stable, deterministic replacement for the LLM-based TB review stage.

Keep orchestration integration pointed at :func:`review_verifier_artifacts`.  The
facade intentionally lives under ``verifier_tool`` so it can be copied or merged as
one self-contained feature while the underlying validators continue to evolve.

This module performs no model call, network access, simulation, or filesystem write.
It trusts Verifier-owned ``llm_extension`` semantics and enforces only the existing
code-owned artifact, interface, taxonomy, coverage, and assertion rules.
"""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any


PreparedValidator = Callable[[Mapping[str, Any], Mapping[str, Any]], None]


class DeterministicArtifactError(ValueError):
    """A generated artifact violated a code-owned validation rule."""


def _canonical_validator(
    candidate: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    """Reuse the canonical deterministic checks without duplicating their policy."""

    # Imported lazily to keep this facade out of VerifierAgent's import graph.  The
    # validator is code-only despite currently living on the agent class.
    from multigent.agents.verifier import VerifierAgent

    try:
        VerifierAgent._validate_context(context)
        VerifierAgent._validate_prepared_result(result=candidate, context=context)
    except Exception as exc:
        if type(exc).__name__ != "AgentRuntimeError":
            raise
        raise DeterministicArtifactError(str(exc)) from exc


_FINDING_BOUNDARY = re.compile(
    r"; (?=(?:test source \d+|Test source|Every _contract_|Stimulus intent|"
    r"Stimulus |Every Verifier-authored|Verifier must|Stimulus coverage intent|"
    r"STIMULUS_COVERAGE_INTENTS|Verifier-authored operation|Missing |Unknown |"
    r"Operation |Coverage ))"
)


def _finding_for(evidence: str) -> dict[str, str]:
    evidence = evidence.strip() or "unknown deterministic validation error"
    lowered = evidence.lower()
    if "no await since stimulus" in lowered:
        stall_targets = "stall_stability" in lowered
        return {
            "category": "MISSING_STIMULUS",
            "requirement": "Each checked stimulus must correspond to a distinct DUT observation",
            "evidence": evidence,
            "recommended_change": (
                "Keep the existing passing scenario. For the named later stimulus, "
                "drive a genuinely new DUT transaction, await its observed result, "
                "and record those new values under its existing label; do not "
                "reuse the prior checked result or claim a coverage hit"
                + (
                    ". For the listed stall_stability targets, present valid and "
                    "payload before ready, hold them stable while stalled, and "
                    "measure the actual ready/valid cycles on each input channel"
                    if stall_targets else ""
                )
            ),
        }
    if "identical literal values" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "Checked observed values must be measured from the DUT",
            "evidence": evidence,
            "recommended_change": (
                "Replace the copied observed constant with a value actually sampled "
                "from the DUT after stimulus; preserve the independent expected value"
            ),
        }
    if "never reads passed keyword" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "A claimed stimulus-control option must affect real DUT traffic",
            "evidence": evidence,
            "recommended_change": (
                "Make the named helper use this keyword to drive the intended "
                "DUT-input scenario and measure its observed effect. For an input "
                "stall claim, present valid/payload before ready, hold both stable "
                "during the stall, and count actual ready/valid cycles. Preserve "
                "the existing legal jobs and checks; do not merely add a flag "
                "to a stimulus record"
            ),
        }
    if "cocotb time unit" in lowered and "invalid" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "The generated TB must use time units accepted by installed cocotb",
            "evidence": evidence,
            "recommended_change": (
                "Patch only the named cocotb.test or Timer unit literal to an "
                "accepted unit; for seconds use 'sec', not 's'. Preserve all "
                "stimulus, oracle checks, coverage bindings, and RTL"
            ),
        }
    if "may transfer a beat before replay" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Directed stalls must not duplicate an accepted beat",
            "evidence": evidence,
            "recommended_change": (
                "The valid=1 pre-stall loop can handshake whenever ready is high. "
                "Observe ready at every rising edge, count an accepted beat exactly "
                "once, and do not call the normal sender again for that beat. "
                "Create stalls by presenting future-channel valid/payload before "
                "its ready phase and holding both stable until the real handshake; "
                "let measured coverage hits determine which stall lengths occurred"
            ),
        }
    category = (
        "MISSING_STIMULUS"
        if any(word in lowered for word in ("never drives", "missing implementation", "no _contract_record"))
        else "INVALID_STIMULUS_MAPPING"
        if "stimulus" in lowered and any(word in lowered for word in ("mapping", "target", "label"))
        else "MISSING_ASSERTION"
        if "missing" in lowered and any(word in lowered for word in ("assert", "feature comment"))
        else
        "COVERAGE_DEFINITION"
        if any(word in lowered for word in ("coverage", "sampling", "coverpoint", "bin"))
        else "INVALID_ASSERTION"
    )
    return {
        "category": category,
        "requirement": "Generated verification artifacts must satisfy the code-owned deterministic contract",
        "evidence": evidence,
        "recommended_change": "Correct only the artifact named by the deterministic validation error, then rerun validation",
    }


def findings_from_validation_error(error: object) -> list[dict[str, str]]:
    """Turn one aggregated validator error into independently patchable findings.

    The structural validator intentionally reports every defect it can prove in one
    pass.  Preserve that batching here so one Verifier patch can address all defects
    and a partial patch retry can retain the findings it already fixed.
    """

    evidence = str(error).strip() or type(error).__name__
    prefix = "Generated test file "
    # Keep the useful filename wrapper on the first item, but split the validator's
    # semicolon-joined findings only at known finding starts, not at prose clauses.
    parts = [part.strip() for part in _FINDING_BOUNDARY.split(evidence) if part.strip()]
    return [_finding_for(part) for part in parts]


def findings_from_coverage(coverage: Mapping[str, Any]) -> list[dict[str, str]]:
    """Create concrete local findings, grouped by coverage obligation.

    A large interface can have dozens of bins.  Grouping sibling bins keeps one
    conceptual defect together and stays within the bounded patch schema while
    retaining every exact missing bin as evidence.
    """

    findings = []
    grouped: dict[str, list[str]] = {}
    for bin_id in map(str, coverage.get("missing_bins", [])):
        if bin_id in {"runtime_report_missing", "invalid_runtime_report"}:
            findings.append(
                {
                    "category": "COVERAGE_DEFINITION",
                    "requirement": "The full regression must emit a valid measured functional-coverage hit report",
                    "evidence": f"coverage hit report unavailable: {bin_id}; {coverage.get('error', '')}",
                    "recommended_change": (
                        "Repair verifier-owned coverage instrumentation or report emission; "
                        "do not infer missing stimulus or claim any bin hits without a report"
                    ),
                }
            )
            continue
        obligation = bin_id.rsplit(".", 1)[0] if "." in bin_id else bin_id
        grouped.setdefault(obligation, []).append(bin_id)
    for obligation, bins in grouped.items():
        findings.append(
            {
                "category": "MISSING_STIMULUS",
                "requirement": f"Runtime coverage obligation {obligation} must close",
                "evidence": f"functional coverage hit count is 0 for bins={bins}",
                "recommended_change": (
                    "Preserve all existing tests and add the smallest legal DUT stimulus/check "
                    "needed to exercise this exact bin; do not synthesize a hit"
                ),
            }
        )
    for failure in map(str, coverage.get("assertion_failures", [])):
        findings.append(
            {
                "category": "INVALID_ASSERTION",
                "requirement": "All deterministic runtime assertions must pass",
                "evidence": failure,
                "recommended_change": "Repair only the verifier-owned stimulus or checker implicated by this failure",
            }
        )
    if not findings:
        findings.append(
            {
                "category": "COVERAGE_DEFINITION",
                "requirement": "Functional coverage must be exactly 100 percent",
                "evidence": f"coverage status={coverage.get('status')!r}, percent={coverage.get('coverage_percent')!r}",
                "recommended_change": "Repair the smallest verifier-owned coverage or stimulus defect and rerun",
            }
        )
    return findings


def _validate_basic_shape(candidate: Mapping[str, Any]) -> None:
    if candidate.get("status") != "VERIFICATION_READY":
        raise DeterministicArtifactError(
            "Deterministic TB review requires VERIFICATION_READY artifacts"
        )
    for field in ("reference_files", "test_files"):
        items = candidate.get(field)
        if not isinstance(items, list) or not items:
            raise DeterministicArtifactError(f"{field} must be a non-empty list")
        for item in items:
            if not isinstance(item, Mapping) or not str(item.get("content", "")).strip():
                path = item.get("path", "<unknown>") if isinstance(item, Mapping) else "<unknown>"
                raise DeterministicArtifactError(
                    f"Generated {field} artifact {path} is empty"
                )


def coverage_obligation_mapping_diff(
    artifact_obligations: Iterable[str], source_obligations: Iterable[str]
) -> dict[str, list[str]]:
    """Return the exact auditable difference between JSON and source claims."""

    artifact = set(map(str, artifact_obligations))
    source = set(map(str, source_obligations))
    return {
        "missing_in_source_constant": sorted(artifact - source),
        "unexpected_in_source_constant": sorted(source - artifact),
    }


def extract_literal_coverage_obligations(
    filename: str, content: str
) -> set[str]:
    """Read one inert module-level COVERAGE_OBLIGATIONS declaration."""

    tree = ast.parse(content, filename=filename, mode="exec")
    declarations: list[ast.AST] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(
            isinstance(target, ast.Name)
            and target.id == "COVERAGE_OBLIGATIONS"
            for target in targets
        ):
            declarations.append(node.value)
    if len(declarations) != 1:
        raise ValueError(
            f"Generated test file {filename} must define exactly one module-level "
            "COVERAGE_OBLIGATIONS literal"
        )
    try:
        value = ast.literal_eval(declarations[0])
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Generated test file {filename} COVERAGE_OBLIGATIONS must be literal"
        ) from exc
    if not isinstance(value, (list, tuple, set)) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(
            f"Generated test file {filename} COVERAGE_OBLIGATIONS must contain strings"
        )
    if len(value) != len(set(value)):
        raise ValueError(
            f"Generated test file {filename} COVERAGE_OBLIGATIONS contains duplicates"
        )
    return set(value)


def synchronize_test_coverage_metadata(
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild redundant test-artifact obligation metadata from Python source.

    ``coverage_obligations`` is a structured copy of the inert module-level
    ``COVERAGE_OBLIGATIONS`` declaration, not an independent semantic input. A
    local Verifier source patch can therefore make only this duplicate stale.
    Rebuilding the JSON copy is deterministic and leaves the authored Python TB
    byte-for-byte unchanged. The canonical validator still compares the source
    claims with the frozen coverage plan, so this cannot invent or hide a hit.
    """

    prepared = copy.deepcopy(dict(candidate))
    if prepared.get("status") != "VERIFICATION_READY":
        return prepared
    tests = prepared.get("test_files")
    if not isinstance(tests, list):
        return prepared
    for item in tests:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("path", "<unknown>"))
        item["coverage_obligations"] = sorted(
            extract_literal_coverage_obligations(
                filename, str(item.get("content", ""))
            )
        )
    return prepared


def review_verifier_artifacts(
    context: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    validator: PreparedValidator | None = None,
) -> dict[str, Any]:
    """Validate one Verifier candidate and return the legacy review-shaped result.

    The return shape deliberately remains compatible with the existing orchestration
    state and routing.  This lets callers replace the old reviewer with one function
    call without renaming graph nodes or migrating saved state.
    """

    validate = validator or _canonical_validator
    prepared = copy.deepcopy(dict(candidate))
    try:
        _validate_basic_shape(prepared)
        validate(prepared, context)
    except (SyntaxError, TypeError, ValueError) as exc:
        return {
            "status": "VERIFIER_REPAIR_REQUIRED",
            "summary": "Deterministic TB validation rejected the generated artifacts",
            "findings": findings_from_validation_error(exc),
        }
    return {
        "status": "APPROVED",
        "summary": (
            "Code-owned interface, taxonomy, coverage, sampling, and base assertion "
            "checks passed; Verifier-owned llm_extension semantics were trusted"
        ),
        "findings": [],
    }


__all__ = [
    "coverage_obligation_mapping_diff",
    "extract_literal_coverage_obligations",
    "findings_from_coverage",
    "findings_from_validation_error",
    "review_verifier_artifacts",
    "synchronize_test_coverage_metadata",
]
