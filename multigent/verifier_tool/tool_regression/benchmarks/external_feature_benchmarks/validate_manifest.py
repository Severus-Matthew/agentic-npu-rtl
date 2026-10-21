"""Validate the external feature-extension benchmark inventory.

This performs no download, simulation, API call, or qualification. It protects
the intended 10/10/10 domain balance and prevents held-out fault definitions
from leaking into the development-visible manifest.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


MANIFEST = Path(__file__).with_name("benchmark_manifest.json")
DOMAINS = {"protocol": "P", "lifecycle": "L", "operation": "O"}
ALLOWED_STATUS = {
    "selected",
    "materialized",
    "contract_frozen",
    "upstream_pass",
    "generated_tb_pass",
    "qualified",
}


def validate_manifest(path: Path = MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1

    sources = manifest["sources"]
    assert sources
    for source_id, source in sources.items():
        assert source["url"].startswith("https://github.com/"), source_id
        assert re.fullmatch(r"[0-9a-f]{40}", source["revision"]), source_id
        assert source["license_review"] in {"required", "recorded"}, source_id

    cases = manifest["cases"]
    assert len(cases) == 30
    assert len({case["id"] for case in cases}) == 30
    assert Counter(case["domain"] for case in cases) == Counter(
        {"protocol": 10, "lifecycle": 10, "operation": 10}
    )

    expected_ids = {
        f"{prefix}{index:02d}"
        for prefix in DOMAINS.values()
        for index in range(1, 11)
    }
    assert {case["id"] for case in cases} == expected_ids

    forbidden_holdout_keys = {
        "holdout_mutant",
        "holdout_mutants",
        "holdout_description",
        "holdout_descriptions",
        "private_mutants",
    }
    for case in cases:
        assert case["source"] in sources, case["id"]
        assert case["status"] in ALLOWED_STATUS, case["id"]
        assert case["id"].startswith(DOMAINS[case["domain"]]), case["id"]
        assert case["unknown_features"], case["id"]
        assert case["reused_baseline"], case["id"]
        assert len(case["known_mutants"]) >= 2, case["id"]
        assert case["holdout_slots"] >= 1, case["id"]
        assert not (forbidden_holdout_keys & case.keys()), case["id"]

    return manifest


def main() -> None:
    manifest = validate_manifest()
    counts = Counter(case["domain"] for case in manifest["cases"])
    print(
        "external feature benchmark manifest: PASS "
        f"({len(manifest['cases'])} cases; "
        + ", ".join(f"{domain}={counts[domain]}" for domain in DOMAINS)
        + ")"
    )


if __name__ == "__main__":
    main()
