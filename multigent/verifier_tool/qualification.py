"""Finite, code-owned qualification catalog for released taxonomy checkers."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


QUALIFICATION_CATALOG_PATH = Path(__file__).with_name(
    "qualification_catalog.yaml"
)


@lru_cache(maxsize=1)
def load_qualification_catalog() -> dict[str, Any]:
    raw = yaml.safe_load(QUALIFICATION_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or not isinstance(raw.get("cases"), list):
        raise ValueError("qualification catalog must contain a cases list")
    cases = raw["cases"]
    ids = [str(item.get("id", "")) for item in cases if isinstance(item, Mapping)]
    nodeids = [
        str(item.get("nodeid", "")) for item in cases if isinstance(item, Mapping)
    ]
    if len(ids) != len(cases) or any(not value for value in ids + nodeids):
        raise ValueError("every qualification case needs id and nodeid")
    if len(ids) != len(set(ids)):
        raise ValueError("qualification case IDs must be unique")
    for item in cases:
        if not str(item.get("requirement", "")).strip() or not str(
            item.get("expected_rule", "")
        ).strip():
            raise ValueError(
                f"qualification case {item.get('id')!r} needs requirement and expected_rule"
            )
        if item.get("polarity") not in {
            "positive",
            "negative",
            "positive_and_negative",
        }:
            raise ValueError(
                f"qualification case {item.get('id')!r} has invalid polarity"
            )
    return dict(raw)


def qualification_catalog_hash() -> str:
    payload = json.dumps(
        load_qualification_catalog(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def qualification_source_hash() -> str:
    """Bind evidence to verifier_tool and every catalog test source."""

    tool_root = Path(__file__).parent
    repository_root = tool_root.parents[1]
    paths = {
        path
        for pattern in ("*.py", "*.yaml")
        for path in tool_root.rglob(pattern)
        if "__pycache__" not in path.parts
    }
    paths.update(
        repository_root / str(item["nodeid"]).split("::", 1)[0]
        for item in load_qualification_catalog()["cases"]
    )
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(repository_root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def qualification_pytest_nodeids() -> tuple[str, ...]:
    """Return the stable executable catalog without duplicate pytest nodes."""

    return tuple(
        dict.fromkeys(str(item["nodeid"]) for item in load_qualification_catalog()["cases"])
    )


def build_qualification_evidence(
    passed_case_ids: Iterable[str],
    *,
    command: str,
    source_revision: str,
) -> dict[str, Any]:
    """Build auditable evidence only for an externally executed catalog run."""

    catalog = load_qualification_catalog()
    expected = {str(item["id"]) for item in catalog["cases"]}
    passed = {str(item) for item in passed_case_ids}
    unknown = sorted(passed - expected)
    if unknown:
        raise ValueError(f"qualification evidence contains unknown cases {unknown}")
    missing = sorted(expected - passed)
    return {
        "schema_version": 1,
        "catalog_version": str(catalog["catalog"]["version"]),
        "catalog_hash": qualification_catalog_hash(),
        "source_hash": qualification_source_hash(),
        "source_revision": str(source_revision),
        "command": str(command),
        "passed_case_ids": sorted(passed),
        "missing_case_ids": missing,
        "status": "PASS" if not missing else "FAIL",
    }


def validate_qualification_evidence(evidence: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(evidence, Mapping):
        return ["finite qualification evidence is missing"]
    catalog = load_qualification_catalog()
    expected = {str(item["id"]) for item in catalog["cases"]}
    passed = set(map(str, evidence.get("passed_case_ids", [])))
    failures: list[str] = []
    if evidence.get("catalog_hash") != qualification_catalog_hash():
        failures.append("qualification catalog hash does not match the released catalog")
    if evidence.get("catalog_version") != catalog["catalog"]["version"]:
        failures.append("qualification catalog version does not match")
    if evidence.get("source_hash") != qualification_source_hash():
        failures.append("qualification evidence was produced from a different source tree")
    if evidence.get("status") != "PASS" or passed != expected:
        failures.append(
            "qualification cases did not all pass: " + repr(sorted(expected - passed))
        )
    if not str(evidence.get("source_revision", "")).strip():
        failures.append("qualification source revision is missing")
    return failures


__all__ = [
    "QUALIFICATION_CATALOG_PATH",
    "build_qualification_evidence",
    "load_qualification_catalog",
    "qualification_catalog_hash",
    "qualification_pytest_nodeids",
    "qualification_source_hash",
    "validate_qualification_evidence",
]
