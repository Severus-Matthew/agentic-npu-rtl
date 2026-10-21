"""Run deterministic preflight over every external contract candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from multigent.verifier_tool import review_contract_deterministically


HERE = Path(__file__).resolve().parent
CASES_ROOT = HERE / "cases"


def review_all(*, persist: bool = True) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case_dir in sorted(path for path in CASES_ROOT.iterdir() if path.is_dir()):
        case_id = case_dir.name[:3].upper()
        domain = {"P": "protocol", "L": "lifecycle", "O": "operation"}[case_id[0]]
        architecture = yaml.safe_load((case_dir / "architecture_contract.yaml").read_text(encoding="utf-8"))
        interface = yaml.safe_load((case_dir / "interface_contract.yaml").read_text(encoding="utf-8"))
        manifest = json.loads((case_dir / "module_manifest.json").read_text(encoding="utf-8"))
        criteria = yaml.safe_load((case_dir / "acceptance_criteria.yaml").read_text(encoding="utf-8"))
        report = review_contract_deterministically(
            architecture,
            interface,
            manifest,
            criteria,
            require_lifecycle_policy=domain != "protocol",
            require_operation_arithmetic=domain == "operation",
        )
        source_status = yaml.safe_load((case_dir / "contract_status.yaml").read_text(encoding="utf-8"))
        manual_binding_complete = (
            interface.get("source_boundary", {}).get("binding_status")
            == "audited_default_parameters"
        )
        status = "reviewer_pass_candidate" if report["status"] == "PASS" and manual_binding_complete else "blocked"
        blockers = []
        if not manual_binding_complete:
            blockers.append("manual_source_port_binding_audit")
        if report["status"] != "PASS":
            blockers.append("deterministic_contract_reviewer_pass")
        blockers.append("upstream_build_dependency_audit")
        source_status.update(
            {
                "status": status,
                "freeze_blockers": blockers,
                "preflight_status": report["status"],
                "preflight_finding_count": len(report["findings"]),
            }
        )
        compact = {
            "schema_version": 1,
            "case_id": case_id,
            "domain": domain,
            "status": report["status"],
            "findings": report["findings"],
            "capability_notes": report.get("capability_notes", []),
            "automatic_campaign_support": report.get("automatic_campaign_support"),
        }
        if persist:
            (case_dir / "preflight_report.yaml").write_text(
                yaml.safe_dump(compact, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
            (case_dir / "contract_status.yaml").write_text(
                yaml.safe_dump(source_status, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
        cases.append(
            {
                "case_id": case_id,
                "domain": domain,
                "status": status,
                "preflight_status": report["status"],
                "findings": len(report["findings"]),
                "manual_binding_complete": manual_binding_complete,
            }
        )
    summary = {
        "schema_version": 1,
        "total": len(cases),
        "reviewer_pass_candidates": sum(item["status"] == "reviewer_pass_candidate" for item in cases),
        "blocked": sum(item["status"] == "blocked" for item in cases),
        "cases": cases,
    }
    if persist:
        (HERE / "contract_preflight_summary.yaml").write_text(
            yaml.safe_dump(summary, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
    return summary


def main() -> int:
    summary = review_all()
    print(yaml.safe_dump(summary, sort_keys=False, default_flow_style=False).rstrip())
    return 0 if summary["total"] == 30 else 1


if __name__ == "__main__":
    raise SystemExit(main())
