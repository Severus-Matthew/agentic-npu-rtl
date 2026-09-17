"""Durable, cumulative stimulus history for coverage-closure iterations."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


HISTORY_FILE = "stimulus-history.json"
LEDGER_GLOB = "stimulus-ledger-*.json"


def rebuild_stimulus_history(verification_dir: Path) -> dict[str, Any]:
    """Merge every versioned run ledger without deleting duplicate executions."""

    verification_dir.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    unique_digests: set[str] = set()
    for ledger_path in sorted(verification_dir.glob(LEDGER_GLOB)):
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if not isinstance(ledger, Mapping):
            continue
        ledger_records = ledger.get("records", [])
        if not isinstance(ledger_records, list):
            continue
        run_number = len(runs) + 1
        runs.append(
            {
                "run": run_number,
                "ledger_path": str(ledger_path),
                "tag": ledger_path.stem.removeprefix("stimulus-ledger-"),
                "seed": ledger.get("seed"),
                "top_module": ledger.get("top_module"),
                "test_modules": ledger.get("test_modules", []),
                "status": ledger.get("status"),
                "stimulus_count": len(ledger_records),
            }
        )
        for index, raw_record in enumerate(ledger_records, start=1):
            if not isinstance(raw_record, Mapping):
                continue
            record = dict(raw_record)
            digest = str(record.get("digest", ""))
            if digest:
                unique_digests.add(digest)
            record["history_id"] = f"run{run_number:04d}:{index:06d}"
            record["source_ledger"] = str(ledger_path)
            record["source_tag"] = runs[-1]["tag"]
            records.append(record)
    history = {
        "schema_version": 1,
        "run_count": len(runs),
        "stimulus_count": len(records),
        "unique_stimulus_count": len(unique_digests),
        "duplicate_execution_count": max(0, len(records) - len(unique_digests)),
        "runs": runs,
        "records": records,
    }
    path = verification_dir / HISTORY_FILE
    path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    return history


def verifier_stimulus_history_view(
    history: Mapping[str, Any],
    *,
    history_path: Path,
) -> dict[str, Any]:
    """Return coverage-oriented statistics; never place exact payloads in a prompt."""

    records = list(history.get("records", []))
    kind_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    covered_bin_counts: Counter[str] = Counter()
    operation_fields: dict[str, dict[str, list[Any]]] = defaultdict(
        lambda: defaultdict(list)
    )
    operation_sample_counts: Counter[str] = Counter()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        kind_counts[str(record.get("kind", "unknown"))] += 1
        if record.get("label") is not None:
            label_counts[str(record["label"])] += 1
        for bin_id in set(map(str, record.get("covered_bins", []))):
            covered_bin_counts[bin_id] += 1
        for sample in record.get("operation_samples", []):
            if not isinstance(sample, Mapping):
                continue
            operation_name = str(sample.get("operation_name", "unknown"))
            operation_sample_counts[operation_name] += 1
            fields = sample.get("fields", {})
            if not isinstance(fields, Mapping):
                continue
            for field, value in fields.items():
                operation_fields[operation_name][str(field)].append(value)

    return {
        "history_path": str(history_path),
        "payload_mode": "SUMMARY_ONLY",
        "exact_payloads_in_prompt": False,
        "exact_payload_note": (
            "Exact stimulus and expected payloads remain only in history_path for "
            "audit/replay; they are intentionally excluded from LLM context."
        ),
        "run_count": int(history.get("run_count", 0)),
        "stimulus_count": int(history.get("stimulus_count", 0)),
        "unique_stimulus_count": int(history.get("unique_stimulus_count", 0)),
        "duplicate_execution_count": int(
            history.get("duplicate_execution_count", 0)
        ),
        "runs": [
            {
                "tag": run.get("tag"),
                "seed": run.get("seed"),
                "status": run.get("status"),
                "stimulus_count": run.get("stimulus_count", 0),
            }
            for run in history.get("runs", [])
            if isinstance(run, Mapping)
        ],
        "kind_counts": dict(sorted(kind_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "covered_bin_execution_counts": dict(sorted(covered_bin_counts.items())),
        "operation_samples": {
            operation_name: {
                "sample_count": operation_sample_counts[operation_name],
                "fields": {
                    field: _summarize_values(values)
                    for field, values in sorted(fields.items())
                },
            }
            for operation_name, fields in sorted(operation_fields.items())
        },
    }


def _summarize_values(values: list[Any]) -> dict[str, Any]:
    """Summarize scalar coverage fields without leaking bulk transaction payloads."""

    scalar_values = [
        value
        for value in values
        if value is None or isinstance(value, (str, int, float, bool))
    ]
    composite_count = len(values) - len(scalar_values)
    encoded = [
        json.dumps(value, sort_keys=True, separators=(",", ":"))
        for value in scalar_values
    ]
    counts = Counter(encoded)
    result: dict[str, Any] = {
        "observations": len(values),
        "scalar_observations": len(scalar_values),
        "composite_observations": composite_count,
        "unique_scalar_values": len(counts),
        "value_counts": [
            {"value": json.loads(value), "count": count}
            for value, count in counts.most_common(16)
        ],
        "value_counts_truncated": len(counts) > 16,
    }
    numeric = [
        float(value)
        for value in scalar_values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if numeric:
        result["numeric_min"] = min(numeric)
        result["numeric_max"] = max(numeric)
    return result
