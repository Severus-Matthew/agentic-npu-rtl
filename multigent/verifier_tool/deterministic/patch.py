"""Deterministic, local corrections for Verifier-owned artifacts.

The Verifier may change its executable coverpoint definitions without returning a
new complete coverage catalog. Existing operation/point identities remain frozen;
the normal full Verifier semantic validator checks the reconstructed result.  This
code deliberately lives in ``verifier_tool`` rather than an LLM reviewer module so
the same exact patch rules serve semantic validation, coverage closure, and runtime
testbench failures.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Mapping

from multigent.agents.base import AgentRuntimeError


class ReviewPatchPartialFailure(AgentRuntimeError):
    """Local patch rejection carrying valid edits and resolved finding indices."""

    def __init__(
        self,
        message: str,
        *,
        partial_result: Mapping[str, Any],
        addressed_findings: set[int],
    ) -> None:
        super().__init__(message)
        self.partial_result = dict(partial_result)
        self.addressed_findings = set(addressed_findings)


def finding_scope(review: Mapping[str, Any]) -> tuple[list[Any], set[int], set[int]]:
    """Return all, already-resolved, and still-required finding indices."""

    findings = list(review.get("findings", []))
    already = set(map(int, review.get("already_addressed_findings", [])))
    invalid = already - set(range(len(findings)))
    if invalid:
        raise AgentRuntimeError(
            f"already_addressed_findings contains unknown indices={sorted(invalid)}"
        )
    return findings, already, set(range(len(findings))) - already


class VerifierMetadataPatchError(ValueError):
    """A metadata edit is non-local, ambiguous, or does not match prior data."""


_IDENTITY_FIELDS = {"operation_name", "family", "id", "concept", "source", "name"}
_SELECTORS = {"operation_coverage": "operation_name", "coverpoints": "id", "bins": "name"}


def _selected(value: Any, segment: str, parent_key: str) -> Any:
    if not isinstance(value, list):
        raise VerifierMetadataPatchError(f"Expected list at {parent_key!r}")
    selector_key = _SELECTORS.get(parent_key)
    if selector_key is not None:
        prefix = f"{selector_key}="
        if not segment.startswith(prefix):
            raise VerifierMetadataPatchError(
                f"{parent_key} requires stable {prefix}<value> selector"
            )
        matches = [item for item in value if isinstance(item, Mapping)
                   and item.get(selector_key) == segment[len(prefix):]]
        if len(matches) != 1:
            raise VerifierMetadataPatchError(
                f"{parent_key} selector {segment!r} matched {len(matches)} items"
            )
        return matches[0]
    if not segment.isdigit() or int(segment) >= len(value):
        raise VerifierMetadataPatchError(f"List index {segment!r} does not exist")
    return value[int(segment)]


def apply_operation_coverage_metadata_edits(
    operation_coverage: list[dict[str, Any]], edits: list[Mapping[str, Any]],
) -> None:
    """Mutate only leaves or one appended point/bin in a copied coverage list.

    All edits are applied to a private deep copy first; the caller's list is
    only overwritten once every edit in this batch has succeeded. A batch that
    fails partway must never leave a torn intermediate mutation (e.g. one
    edit's predicate.op changed but a sibling predicate.args edit in the same
    batch rejected) visible in the caller's data, since that data becomes the
    next retry's starting draft.
    """

    working = copy.deepcopy(operation_coverage)
    changed: set[str] = set()
    for index, edit in enumerate(edits):
        path = edit.get("path")
        op = edit.get("op")
        if not isinstance(path, str) or not path.startswith("/operation_coverage/"):
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} must target /operation_coverage/..."
            )
        repeated_append = op == "add" and path.endswith("/-")
        if op not in {"add", "replace", "remove"} or (path in changed and not repeated_append):
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} has invalid operation or duplicate path"
            )
        changed.add(path)
        parts = path.split("/")[1:]
        if len(parts) < 4 or any(not part for part in parts):
            raise VerifierMetadataPatchError(f"Metadata edit {index} needs a point/bin leaf")
        if op != "remove" and parts[-1] in _IDENTITY_FIELDS:
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} may not replace frozen identity field "
                f"'{parts[-1]}' at {path!r}. A coverpoint or bin's name/id can never "
                "change, even to correct its meaning. To fix what a bin means, "
                "leave this same path's 'name' unchanged and instead submit a "
                "metadata edit targeting its sibling 'predicate' and/or 'intent' "
                "field so the existing identity now matches the corrected behavior."
            )
        if op == "remove":
            new_value = None
        else:
            try:
                new_value = json.loads(str(edit.get("value_json", "")))
            except json.JSONDecodeError as exc:
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} value_json is not JSON"
                ) from exc

        value: Any = working
        parent_key = "operation_coverage"
        for segment in parts[1:-1]:
            if isinstance(value, list):
                value = _selected(value, segment, parent_key)
            elif isinstance(value, dict) and segment in value:
                value = value[segment]
            else:
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} has missing parent at {segment!r}"
                )
            parent_key = segment
        leaf = parts[-1]
        if op == "remove":
            selector_key = _SELECTORS.get(parent_key)
            prefix = f"{selector_key}=" if selector_key else None
            if not isinstance(value, list) or parent_key not in {"coverpoints", "bins"} \
                    or prefix is None or not leaf.startswith(prefix):
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} remove must target one existing "
                    f"{{coverpoints,bins}} item by its id=/name= selector, e.g. "
                    ".../bins/name=<bin-name>, not a field beneath it"
                )
            matches = [item for item in value if isinstance(item, Mapping)
                       and item.get(selector_key) == leaf[len(prefix):]]
            if len(matches) != 1:
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} remove selector {leaf!r} matched {len(matches)} items"
                )
            if len(value) <= 1:
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} would remove the last {parent_key[:-1]}; "
                    f"a coverpoint always needs at least one bin, and an operation "
                    "always needs at least one coverpoint. Add a replacement first, "
                    "in this same batch or a prior one, before removing the last one."
                )
            value.remove(matches[0])
            continue
        if isinstance(value, list):
            if op == "add" and leaf == "-" and parent_key in {"coverpoints", "bins"}:
                if not isinstance(new_value, dict):
                    raise VerifierMetadataPatchError(
                        f"Metadata edit {index} append requires one point/bin object"
                    )
                selector_key = _SELECTORS[parent_key]
                new_identity = new_value.get(selector_key)
                if any(isinstance(item, Mapping) and item.get(selector_key) == new_identity
                       for item in value):
                    raise VerifierMetadataPatchError(
                        f"Metadata edit {index} appends a {parent_key[:-1]} whose "
                        f"{selector_key}={new_identity!r} already exists; a "
                        f"{parent_key[:-1]}'s {selector_key} must be unique within its "
                        "parent. Pick a new, not-yet-used name/id, or if you meant to "
                        "correct the existing one, use 'replace' on its own field "
                        "instead of adding a second one with the same identity."
                    )
                value.append(new_value)
            elif op == "replace" and parent_key not in _SELECTORS and leaf.isdigit() and int(leaf) < len(value):
                prior = value[int(leaf)]
                if isinstance(prior, (dict, list)) or isinstance(new_value, (dict, list)):
                    raise VerifierMetadataPatchError(
                        f"Metadata edit {index} cannot replace a composite list value"
                    )
                if prior == new_value:
                    raise VerifierMetadataPatchError(f"Metadata edit {index} is a no-op")
                value[int(leaf)] = new_value
            else:
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} may only append a point/bin or replace a scalar array leaf"
                )
        elif isinstance(value, dict) and op == "replace" and leaf in value:
            prior = value[leaf]
            if isinstance(prior, (dict, list)) or isinstance(new_value, (dict, list)):
                raise VerifierMetadataPatchError(
                    f"Metadata edit {index} cannot replace a composite section"
                )
            if prior == new_value:
                raise VerifierMetadataPatchError(f"Metadata edit {index} is a no-op")
            value[leaf] = new_value
        else:
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} does not target an existing scalar leaf"
            )

    operation_coverage[:] = working
