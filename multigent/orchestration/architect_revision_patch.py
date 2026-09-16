"""Apply bounded Architect edits to the previous complete contract.

The model never returns a replacement contract on a revision. This module owns
the patch operation and rejects broad structural redesign before artifacts move.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Mapping


ARTIFACT_ROOTS = frozenset({
    "architecture_contract", "interface_contract", "module_manifest",
    "acceptance_criteria",
})
PROTECTED_SUFFIXES = frozenset({
    ("architecture_contract", "design", "name"),
    ("module_manifest", "top"),
})
IDENTITY_FIELDS = {
    "operations": {"name", "kind", "coverage_family", "coverage_family_source"},
    "data_types": {"name", "width_bits", "signed"},
    "data_objects": {"name", "data_type"},
    "dimensions": {"name", "bound_parameter"},
    "parameters": {"name"},
    "modules": {"name"},
    "signals": {"name", "role", "channel", "direction", "width"},
    "channels": {"name", "direction", "protocol_profile"},
    "pipeline": {"stage"},
}


class RevisionPatchError(ValueError):
    """An Architect revision tried to replace unrelated frozen design structure."""


def _parts(path: str) -> list[str]:
    if not path.startswith("/"):
        raise RevisionPatchError(f"Patch path must be a JSON pointer: {path!r}")
    raw = path.split("/")[1:]
    if not raw or raw[0] not in ARTIFACT_ROOTS or len(raw) < 2:
        raise RevisionPatchError(f"Patch must target a leaf below a contract artifact: {path!r}")
    parts: list[str] = []
    for segment in raw:
        if not segment or "~" in segment.replace("~0", "").replace("~1", ""):
            raise RevisionPatchError(f"Invalid JSON pointer segment: {path!r}")
        parts.append(segment.replace("~1", "/").replace("~0", "~"))
    return parts


def _parent(document: Any, parts: list[str]) -> Any:
    value = document
    for segment in parts[:-1]:
        if isinstance(value, dict):
            if segment not in value:
                raise RevisionPatchError(f"Missing parent key {segment!r}")
            value = value[segment]
        elif isinstance(value, list):
            selector_key = next(
                (
                    key for key in ("name", "stage")
                    if value and all(
                        isinstance(item, Mapping) and isinstance(item.get(key), str)
                        for item in value
                    )
                ),
                None,
            )
            if selector_key is not None:
                prefix = f"{selector_key}="
                if not segment.startswith(prefix):
                    raise RevisionPatchError(
                        f"Named collection requires stable {prefix}<value> selector, not {segment!r}"
                    )
                selected_name = segment[len(prefix):]
                matches = [item for item in value if item.get(selector_key) == selected_name]
                if len(matches) != 1:
                    raise RevisionPatchError(
                        f"Named selector {segment!r} matched {len(matches)} items"
                    )
                value = matches[0]
            elif segment.isdigit() and int(segment) < len(value):
                value = value[int(segment)]
            else:
                raise RevisionPatchError(f"Patch list element does not exist at {segment!r}")
        else:
            raise RevisionPatchError(f"Patch parent does not exist at {segment!r}")
    return value


def _check_scope(parts: list[str], op: str, prior: Any, new_value: Any,
                 feedback: Mapping[str, Any]) -> None:
    if tuple(parts) in PROTECTED_SUFFIXES:
        raise RevisionPatchError("Design identity/top module cannot change in a local revision")
    if parts[1] in IDENTITY_FIELDS and len(parts) == 3:
        raise RevisionPatchError(
            f"A local revision cannot {op} a whole item in the named collection "
            f"'{parts[1]}' (only leaf fields inside an existing named item may be "
            "added/replaced). Adding, removing, or wholesale-replacing a module, "
            "operation, channel, signal, data type, or parameter object is a "
            "structural change; return SPEC_CONFLICT instead of another patch "
            "attempt if the frozen contract genuinely needs one."
        )
    for index, segment in enumerate(parts[:-1]):
        if segment in IDENTITY_FIELDS and index + 2 < len(parts):
            if parts[index + 2] in IDENTITY_FIELDS[segment]:
                raise RevisionPatchError(f"Frozen {segment} identity field cannot change")
    if op in {"replace", "remove"} and isinstance(prior, (dict, list)):
        raise RevisionPatchError("Composite contract sections cannot be replaced or removed")
    if op == "add" and isinstance(new_value, (dict, list)):
        raise RevisionPatchError("New whole sections/list items cannot be added in a local revision")
    if "features" in parts and op != "remove":
        feature = str(new_value)
        evidence = json.dumps(dict(feedback), sort_keys=True).lower()
        if feature.lower() not in evidence:
            raise RevisionPatchError(f"Feature {feature!r} is not named in revision feedback")
    if "parameters" in parts and parts[-1] == "default_value":
        evidence = json.dumps(dict(feedback), sort_keys=True).lower()
        if not any(word in evidence for word in ("bound", "dimension", "encoding", "parameter")):
            raise RevisionPatchError("Parameter default change is unrelated to feedback")


def apply_architect_revision_patch(
    previous: Mapping[str, Any], feedback: Mapping[str, Any], patch: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a new complete contract by applying only audited leaf-level edits."""
    if patch.get("status") != "PATCH_READY":
        raise RevisionPatchError("Only PATCH_READY can update a frozen contract")
    edits = patch.get("edits")
    if not isinstance(edits, list) or not edits or len(edits) > 32:
        raise RevisionPatchError("A local revision needs 1..32 explicit edits")
    candidate = copy.deepcopy(dict(previous))
    changed: set[str] = set()
    for edit in edits:
        if not isinstance(edit, Mapping):
            raise RevisionPatchError("Patch edits must be objects")
        op = edit.get("op")
        path = edit.get("path")
        if op not in {"add", "replace", "remove"} or not isinstance(path, str):
            raise RevisionPatchError("Invalid patch operation/path")
        if path in changed:
            raise RevisionPatchError(f"Duplicate patch path {path!r}")
        changed.add(path)
        parts = _parts(path)
        parent = _parent(candidate, parts)
        key = parts[-1]
        try:
            new_value = json.loads(str(edit.get("value_json", "null")))
        except json.JSONDecodeError as exc:
            raise RevisionPatchError(f"Invalid value_json at {path!r}") from exc
        if isinstance(parent, dict):
            exists = key in parent
            if op == "add" and exists or op != "add" and not exists:
                raise RevisionPatchError(f"Patch {op} does not match existing key at {path!r}")
            prior = parent.get(key)
        elif isinstance(parent, list):
            if op == "add":
                if key != "-":
                    raise RevisionPatchError("List additions must append; no index shifting")
                prior = None
            elif not key.isdigit() or int(key) >= len(parent):
                raise RevisionPatchError(f"Patch list index does not exist at {path!r}")
            else:
                prior = parent[int(key)]
        else:
            raise RevisionPatchError(f"Patch parent is not a collection at {path!r}")
        _check_scope(parts, op, prior, new_value, feedback)
        if op == "replace" and prior == new_value:
            raise RevisionPatchError(f"No-op replacement at {path!r}")
        if isinstance(parent, dict):
            if op == "remove":
                del parent[key]
            else:
                parent[key] = new_value
        elif op == "add":
            parent.append(new_value)
        elif op == "remove":
            raise RevisionPatchError("List removal would shift unrelated frozen entries")
        else:
            parent[int(key)] = new_value
    return candidate
