"""Sync FULL_POOL_QUALIFICATION_MATRIX.md's "Strict status" columns from ledger.json.

ledger.json is the source of truth (it carries the full evidence: contract,
generated-TB hash, compliant/mutant RTL, expected/actual diagnostic,
coverage, seed). This script only rewrites the trailing status cell of each
matching table row so the human-readable inventory never silently drifts
from the ledger. It never touches hls_benchmark_qualification_matrix.md, which
tracks resolved (RTL-signal-bound) feature IDs in a different key space and
is kept in sync by hand alongside its own container-provenance notes.

Run after every ledger.json update:
    PYTHONPATH=. .venv/bin/python -m multigent.verifier_tool.tool_regression.qualification.sync_matrices
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER_PATH = HERE / "ledger.json"
DOC_PATH = HERE.parent / "local_reports" / "FULL_POOL_QUALIFICATION_MATRIX.md"

SYMBOL = {
    "STRICT_PASS": "✓",
    "POSITIVE_ONLY": "P",
    "BLOCKED": "B",
    "NOT_STARTED": "—",
    "INAPPLICABLE": "N/A",
}

BACKTICK = re.compile(r"`([^`]*)`")


def _cells(line: str) -> list[str]:
    return [p.strip() for p in line.strip().strip("|").split("|")]


def _backtick_name(cell: str) -> str:
    m = BACKTICK.search(cell)
    return m.group(1) if m else cell.strip()


def main() -> None:
    ledger = json.loads(LEDGER_PATH.read_text())
    rows = ledger["rows"] if isinstance(ledger, dict) and "rows" in ledger else ledger

    rule_lookup: dict[tuple[str, str], str] = {}
    driver_invariant_lookup: dict[tuple[str, str], str] = {}
    featbin_lookup: dict[tuple[str, str], str] = {}
    lifecycle_lookup: dict[tuple[str, str, str], str] = {}
    opbin_lookup: dict[tuple[str, str, str], str] = {}
    tag_lookup: dict[str, str] = {}
    profile_lookup: dict[str, str] = {}
    policy_lookup: dict[tuple[str, str], str] = {}

    for r in rows:
        cat = r.get("category")
        status = r.get("status", "NOT_STARTED")
        if cat == "standard_protocol_rule":
            rule_lookup[(r["profile"], r["rule"])] = status
        elif cat == "protocol_driver_invariant":
            driver_invariant_lookup[(r["profile"], r["invariant"])] = status
        elif cat == "protocol_feature_bin":
            # Human tables render the diagnostic marker outside the backticks;
            # the ledger keeps it in the canonical bin label.
            bin_name = r["bin"].removesuffix(" (diagnostic)")
            featbin_lookup[(r["feature"], bin_name)] = status
        elif cat == "lifecycle_feature_bin":
            lifecycle_lookup[(r["section"], r["feature"], r["bin"])] = status
        elif cat == "operation_bin":
            opbin_lookup[(r["family"], r["concept"], r["bin"])] = status
        elif cat == "tag":
            tag_lookup[r["name"]] = status
        elif cat == "protocol_profile":
            profile_lookup[r["name"]] = status
        elif cat == "lifecycle_policy_choice":
            policy_lookup[(r["field"], r["choice"])] = status

    lines = DOC_PATH.read_text().split("\n")
    section = None
    changed = 0
    missing: list[tuple[str, tuple[str, ...]]] = []

    for i, line in enumerate(lines):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = _cells(line)

        if section == "Verification tags (tag pool)" and len(parts) == 3:
            key = _backtick_name(parts[0])
            if key == "Tag":
                continue
            if key in tag_lookup:
                new_status = SYMBOL[tag_lookup[key]]
                if parts[2] != new_status:
                    parts[2] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("tag", (key,)))

        elif section == "Selectable protocol profiles" and len(parts) == 3:
            key = _backtick_name(parts[0])
            if key == "Profile":
                continue
            if key in profile_lookup:
                new_status = SYMBOL[profile_lookup[key]]
                if parts[2] != new_status:
                    parts[2] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("profile", (key,)))

        elif section == "Lifecycle policy choices" and len(parts) == 3:
            key = (_backtick_name(parts[0]), _backtick_name(parts[1]))
            if key == ("Policy field", "Choice"):
                continue
            if key in policy_lookup:
                new_status = SYMBOL[policy_lookup[key]]
                if parts[2] != new_status:
                    parts[2] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("policy", key))

        elif section == "Standard protocol rules by profile" and len(parts) == 3:
            key = (_backtick_name(parts[0]), _backtick_name(parts[1]))
            if key == ("Profile", "Rule"):
                continue
            if key in rule_lookup:
                new_status = SYMBOL[rule_lookup[key]]
                if parts[2] != new_status:
                    parts[2] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("rule", key))

        elif section == "Protocol driver invariants" and len(parts) == 3:
            key = (_backtick_name(parts[0]), _backtick_name(parts[1]))
            if key == ("Profile", "Invariant"):
                continue
            if key in driver_invariant_lookup:
                new_status = SYMBOL[driver_invariant_lookup[key]]
                if parts[2] != new_status:
                    parts[2] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("driver_invariant", key))

        elif section == "Protocol feature catalog and bins" and len(parts) == 3:
            key = (_backtick_name(parts[0]), _backtick_name(parts[1]))
            if key == ("Feature", "Bin / assertion-only"):
                continue
            if key in featbin_lookup:
                new_status = SYMBOL[featbin_lookup[key]]
                if parts[2] != new_status:
                    parts[2] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("featbin", key))

        elif section == "Lifecycle features and bins" and len(parts) == 4:
            key = (_backtick_name(parts[0]), _backtick_name(parts[1]), _backtick_name(parts[2]))
            if key == ("Catalog section", "Feature", "Bin / assertion-only"):
                continue
            if key in lifecycle_lookup:
                new_status = SYMBOL[lifecycle_lookup[key]]
                if parts[3] != new_status:
                    parts[3] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("lifecycle", key))

        elif section == "Operation families, concepts, and bins" and len(parts) == 4:
            key = (_backtick_name(parts[0]), _backtick_name(parts[1]), _backtick_name(parts[2]))
            if key == ("Family", "Concept", "Bin"):
                continue
            if key in opbin_lookup:
                new_status = SYMBOL[opbin_lookup[key]]
                if parts[3] != new_status:
                    parts[3] = new_status
                    lines[i] = "| " + " | ".join(parts) + " |"
                    changed += 1
            else:
                missing.append(("opbin", key))

    DOC_PATH.write_text("\n".join(lines))
    print(f"changed {changed} status cells")
    if missing:
        print(f"{len(missing)} doc rows have no ledger match (real gaps, investigate):")
        for m in missing:
            print("  ", m)


if __name__ == "__main__":
    main()
