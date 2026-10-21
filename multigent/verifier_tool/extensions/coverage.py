"""Compile Verifier-authored extension bins into required runtime obligations.

An extension bundle is contract-local, but its declared coverage is not
diagnostic-only.  Once the bundle passes semantic validation every declared bin
must participate in the same coverage denominator as protocol, lifecycle, and
operation bins.  This module performs that small, deterministic translation;
the Verifier still owns the observed-evidence classifier that reports hits.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


class ExtensionCoverageError(ValueError):
    """A validated extension manifest cannot be represented as coverage."""


def extension_coverage_obligation_id(request_id: object) -> str:
    """Return the stable required-obligation ID for one extension request."""

    identity = str(request_id).strip()
    if not identity:
        raise ExtensionCoverageError("extension coverage request_id must not be empty")
    return f"extension.{identity}"


def build_extension_coverage_plan(
    manifest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build required obligations from a validated feature-extension manifest."""

    entries = [] if manifest is None else manifest.get("entries", [])
    if not isinstance(entries, list):
        raise ExtensionCoverageError("feature extension manifest entries must be a list")
    obligations: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ExtensionCoverageError(
                f"feature extension manifest entries[{index}] must be an object"
            )
        request = entry.get("request", {})
        implementation = entry.get("implementation", {})
        if not isinstance(request, Mapping) or not isinstance(implementation, Mapping):
            raise ExtensionCoverageError(
                f"feature extension manifest entries[{index}] lacks request/implementation"
            )
        request_id = str(request.get("id", ""))
        obligation_id = extension_coverage_obligation_id(request_id)
        if obligation_id in seen_ids:
            raise ExtensionCoverageError(
                f"duplicate extension coverage obligation {obligation_id!r}"
            )
        seen_ids.add(obligation_id)
        coverage = implementation.get("coverage", {})
        if not isinstance(coverage, Mapping):
            raise ExtensionCoverageError(
                f"extension {request_id!r} coverage branch must be an object"
            )
        raw_bins = coverage.get("bins", [])
        if not isinstance(raw_bins, list) or not raw_bins:
            raise ExtensionCoverageError(
                f"extension {request_id!r} must declare at least one coverage bin"
            )
        bins: list[dict[str, Any]] = []
        seen_bins: set[str] = set()
        for bin_index, raw_bin in enumerate(raw_bins):
            if not isinstance(raw_bin, Mapping):
                raise ExtensionCoverageError(
                    f"extension {request_id!r} coverage bin {bin_index} must be an object"
                )
            name = str(raw_bin.get("name", ""))
            if not name or name in seen_bins:
                raise ExtensionCoverageError(
                    f"extension {request_id!r} has duplicate or empty coverage bin {name!r}"
                )
            seen_bins.add(name)
            bins.append(
                {
                    "name": name,
                    "intent": str(raw_bin.get("intent", "")),
                    "predicate": deepcopy(dict(raw_bin.get("predicate", {}))),
                    "required": True,
                    "minimum_hits": 1,
                    "applicability": {
                        "status": "required_reachable",
                        "basis": "validated contract-local extension bundle",
                    },
                }
            )
        branch_implementation = coverage.get("implementation", {})
        obligations.append(
            {
                "id": obligation_id,
                "category": str(implementation.get("domain", request.get("domain", ""))),
                "template": "extension_coverpoint",
                "scope": str(request.get("target", {}).get("scope", "extension")),
                "scope_name": str(request.get("target", {}).get("name", request_id)),
                "description": str(request.get("semantics", {}).get("summary", "")),
                "sample_unit": "simulator_derived_extension_evidence",
                "controllability": "verifier_extension_stimulus",
                "bindings": {
                    "request_id": request_id,
                    "coverage_symbol": (
                        str(branch_implementation.get("symbol", ""))
                        if isinstance(branch_implementation, Mapping)
                        else ""
                    ),
                },
                "bins": bins,
            }
        )
    obligations.sort(key=lambda item: str(item["id"]))
    return {
        "schema_version": 1,
        "source": "validated contract-local feature extensions",
        "obligations": obligations,
    }


__all__ = [
    "ExtensionCoverageError",
    "build_extension_coverage_plan",
    "extension_coverage_obligation_id",
]
