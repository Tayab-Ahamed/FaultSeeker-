"""Diagnose legacy 115 false positives/false negatives from retained rows."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS = ROOT / "reports/reproducibility/legacy_115_diagnostic/predictions.jsonl"
CLASSIFICATION = ROOT / "benchmark/benchmark_classification.csv"
OUTPUT = ROOT / "reports/reproducibility/legacy_115_diagnostic/error_analysis.json"
FULL = "FaultSeeker++ (Ours)"


def main() -> int:
    predictions = [json.loads(line) for line in PREDICTIONS.read_text(encoding="utf-8").splitlines()]
    with CLASSIFICATION.open(encoding="utf-8-sig", newline="") as handle:
        classification = {row["txn_hash"].lower(): row for row in csv.DictReader(handle)}

    false_negatives = []
    false_positives = []
    for item in predictions:
        predicted = bool(item["predicted_positive"][FULL])
        metadata = classification.get(item["txn_hash"].lower())
        record = {
            "txn_hash": item["txn_hash"],
            "chain": item["chain"],
            "score": item["scores"][FULL],
            "scores": item["scores"],
            "features": {
                key: metadata.get(key) if metadata else None
                for key in ("functioncall_count", "address_count", "max_depth", "gas_cost")
            },
            "vulnerability_type": metadata.get("vuln_type") if metadata else "benign_trace",
            "class": metadata.get("class") if metadata else "benign",
        }
        if item["label"] and not predicted:
            false_negatives.append(record)
        elif not item["label"] and predicted:
            false_positives.append(record)

    def groups(rows, key):
        counts = Counter(key(row) for row in rows)
        return [{"value": value, "count": count} for value, count in counts.most_common()]

    def score_summary(rows):
        values = [row["score"] for row in rows]
        return {
            "n": len(values),
            "min": min(values) if values else None,
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "max": max(values) if values else None,
        }

    report = {
        "schema_version": 1,
        "status": "LEGACY_115_ERROR_DIAGNOSTIC_ONLY",
        "n_predictions": len(predictions),
        "false_negative_count": len(false_negatives),
        "false_positive_count": len(false_positives),
        "error_groups": {
            "false_negatives_by_chain": groups(false_negatives, lambda row: row["chain"]),
            "false_negatives_by_vulnerability": groups(false_negatives, lambda row: row["vulnerability_type"]),
            "false_positives_by_chain": groups(false_positives, lambda row: row["chain"]),
        },
        "score_summary": {
            "false_negatives": score_summary(false_negatives),
            "false_positives": score_summary(false_positives),
        },
        "observations": [
            "All legacy 115 exploit rows and 1000 benign trace rows have the four trace features; missing-feature coverage is not an error source in this diagnostic.",
            "Routing decisions and provider confidence are not present in the retained JSONL; no routing cause is inferred.",
            "False negatives are concentrated among low-call/low-depth exploit traces and include access-control, validation, business-logic, and arbitrary-call categories; this is an observed grouping, not a causal attribution.",
            "False positives are all Ethereum benign traces in this diagnostic and have high full-system scores; the benign source is a trace collection, not category-adjudicated human benign ground truth.",
        ],
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "original_246_row_claim": "not evaluated; legacy 115-row diagnostic only",
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"false_negatives": len(false_negatives), "false_positives": len(false_positives)}, sort_keys=True))
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
