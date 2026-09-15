"""Apply review-owned, local operation-coverage metadata corrections.

The Verifier may change its executable coverpoint definitions without returning a
new complete coverage catalog. Existing operation/point identities remain frozen;
the normal full Verifier semantic validator checks the reconstructed result.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


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
    """Mutate only leaves or one appended point/bin in a copied coverage list."""

    changed: set[str] = set()
    for index, edit in enumerate(edits):
        path = edit.get("path")
        op = edit.get("op")
        if not isinstance(path, str) or not path.startswith("/operation_coverage/"):
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} must target /operation_coverage/..."
            )
        repeated_append = op == "add" and path.endswith("/-")
        if op not in {"add", "replace"} or (path in changed and not repeated_append):
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} has invalid operation or duplicate path"
            )
        changed.add(path)
        parts = path.split("/")[1:]
        if len(parts) < 4 or any(not part for part in parts):
            raise VerifierMetadataPatchError(f"Metadata edit {index} needs a point/bin leaf")
        if parts[-1] in _IDENTITY_FIELDS:
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} may not replace a frozen identity field"
            )
        try:
            new_value = json.loads(str(edit.get("value_json", "")))
        except json.JSONDecodeError as exc:
            raise VerifierMetadataPatchError(
                f"Metadata edit {index} value_json is not JSON"
            ) from exc

        value: Any = operation_coverage
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
        if isinstance(value, list):
            if op == "add" and leaf == "-" and parent_key in {"coverpoints", "bins"}:
                if not isinstance(new_value, dict):
                    raise VerifierMetadataPatchError(
                        f"Metadata edit {index} append requires one point/bin object"
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
