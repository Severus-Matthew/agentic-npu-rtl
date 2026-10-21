"""Materialize pinned public benchmark sources into the ignored local cache.

Large repositories can be checked out sparsely.  Sparse mode keeps Git
provenance and the exact pinned revision while populating only paths referenced
by benchmark cases.  The checkout can therefore be expanded later if a source
target needs shared packages or build collateral.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .validate_manifest import MANIFEST, validate_manifest


DEFAULT_CACHE = MANIFEST.parent / ".cache" / "sources"


def _run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def _case_targets(manifest: dict, source_id: str) -> list[str]:
    """Return minimal cone-mode checkout roots for one source."""

    roots: set[str] = set()
    for case in manifest["cases"]:
        if case["source"] != source_id:
            continue
        target = Path(case["source_target"])
        # Cone mode accepts directories.  For a single source file, retaining
        # its parent also keeps nearby packages commonly needed during audit.
        root = target.parent if target.suffix else target
        roots.add(root.as_posix())
    return sorted(roots)


def materialize(source_id: str, cache: Path, *, sparse: bool = False) -> Path:
    manifest = validate_manifest()
    source = manifest["sources"][source_id]
    destination = cache / source_id
    revision = source["revision"]

    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        _run(
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            source["url"],
            str(destination),
        )

    _run("git", "fetch", "--depth", "1", "origin", revision, cwd=destination)
    if sparse:
        sparse_roots = _case_targets(manifest, source_id)
        if not sparse_roots:
            raise RuntimeError(f"{source_id}: no benchmark case targets")
        _run("git", "sparse-checkout", "init", "--cone", cwd=destination)
        _run("git", "sparse-checkout", "set", *sparse_roots, cwd=destination)
    _run("git", "checkout", "--detach", revision, cwd=destination)
    actual = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=destination,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if actual != revision:
        raise RuntimeError(f"{source_id}: expected {revision}, checked out {actual}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--sparse",
        action="store_true",
        help="populate only benchmark source-target roots while retaining Git provenance",
    )
    args = parser.parse_args()

    manifest = validate_manifest()
    sources = manifest["sources"]
    if args.list:
        for source_id, source in sources.items():
            print(f"{source_id} {source['revision']} {source['url']}")
        return

    requested = list(sources) if args.all else args.source
    if not requested:
        parser.error("select at least one --source or pass --all")
    unknown = sorted(set(requested) - set(sources))
    if unknown:
        parser.error(f"unknown source IDs: {', '.join(unknown)}")

    for source_id in requested:
        print(f"materializing {source_id}")
        print(materialize(source_id, args.cache, sparse=args.sparse))


if __name__ == "__main__":
    main()
