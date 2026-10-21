"""Audit locally materialized benchmark sources against the checked-in manifest.

This is a provenance and path check only.  It does not claim that upstream RTL
builds, generated testbenches, or mutations have passed.
"""

from __future__ import annotations

import argparse
import subprocess
from collections import defaultdict
from pathlib import Path

from .materialize_sources import DEFAULT_CACHE
from .validate_manifest import validate_manifest


def _head_revision(source_dir: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source_dir,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def audit_sources(cache: Path, selected_sources: list[str] | None = None) -> dict[str, int]:
    manifest = validate_manifest()
    sources = manifest["sources"]
    requested = selected_sources or [
        source_id for source_id in sources if (cache / source_id).is_dir()
    ]
    if not requested:
        raise RuntimeError(f"no materialized sources found under {cache}")

    unknown = sorted(set(requested) - set(sources))
    if unknown:
        raise ValueError(f"unknown source IDs: {', '.join(unknown)}")

    cases_by_source: dict[str, list[dict]] = defaultdict(list)
    for case in manifest["cases"]:
        cases_by_source[case["source"]].append(case)

    audited: dict[str, int] = {}
    for source_id in requested:
        source_dir = cache / source_id
        if not (source_dir / ".git").exists():
            raise RuntimeError(f"{source_id}: source checkout is missing: {source_dir}")

        expected_revision = sources[source_id]["revision"]
        actual_revision = _head_revision(source_dir)
        if actual_revision != expected_revision:
            raise RuntimeError(
                f"{source_id}: expected revision {expected_revision}, found {actual_revision}"
            )

        source_cases = cases_by_source[source_id]
        for case in source_cases:
            target = source_dir / case["source_target"]
            if not target.exists():
                raise RuntimeError(
                    f"{case['id']}: source target does not exist at pinned revision: "
                    f"{case['source_target']}"
                )
        audited[source_id] = len(source_cases)

    return audited


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--source", action="append", default=[])
    args = parser.parse_args()

    audited = audit_sources(args.cache, args.source or None)
    for source_id, case_count in audited.items():
        print(f"{source_id}: PASS ({case_count} case targets at pinned revision)")


if __name__ == "__main__":
    main()
