"""Evaluate a trace-density calibration feature on the legacy diagnostic.

Hypothesis: the existing calibration sees raw call/address/depth scale but not
address fan-out relative to execution volume. False positives in the retained
error analysis have high address counts for comparatively short traces, so a
single ``address_count / functioncall_count`` feature may improve separation
without changing the fixed decision threshold or using evaluation labels.

This is a deterministic five-fold hash OOF experiment on the legacy 115-row
exploit + 1000-row benign trace diagnostic. It is not a 246-row paper result.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.features import feature_dict, load_benign_rows, load_exploit_rows
from benchmark.honest_eval.metrics import (
    brier_score,
    bootstrap_f1_ci,
    classification_metrics,
    expected_calibration_error,
    mcnemar_counts,
    mcnemar_statistic,
)
from benchmark import run_honest_experiments as honest
from faultseeker.research.calibration import FEATURE_NAMES, LogisticConfidenceCalibrator


FOLDS = 5
THRESHOLD = 0.5
CANDIDATE_FEATURE = "address_fanout_ratio"
OUTPUT_DIR = ROOT / "reports/reproducibility/legacy_115_diagnostic/trace_density_calibration"
PREDICTIONS_OUT = OUTPUT_DIR / "predictions.jsonl"
REPORT_OUT = OUTPUT_DIR / "report.json"
CHECKSUMS_OUT = OUTPUT_DIR / "checksums.json"
EXPLOIT_CSV = ROOT / "benchmark/benchmark_classification.csv"
BENIGN_CSV = ROOT / "benchmark/imported/benign_traces.csv"
CLASSIFICATION_CSV = ROOT / "benchmark/benchmark_classification.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fold_of(txn_hash: str) -> int:
    return int(hashlib.sha256(str(txn_hash).encode("utf-8")).hexdigest(), 16) % FOLDS


def density_payload(row) -> dict:
    payload = honest._extract_calibrator_payload(feature_dict(row))
    calls = float(row.features.get("functioncall_count") or 0.0)
    addresses = float(row.features.get("address_count") or 0.0)
    payload[CANDIDATE_FEATURE] = addresses / max(calls, 1.0)
    return payload


def fit_model(payloads, labels, feature_names):
    model = LogisticConfidenceCalibrator(feature_names=feature_names)
    model.fit(payloads, labels, epochs=1000, learning_rate=0.05, l2=0.001)
    return model


def evaluate(rows, labels, candidate: bool):
    fold_ids = [fold_of(row.txn_hash) for row in rows]
    feature_names = list(FEATURE_NAMES) + ([CANDIDATE_FEATURE] if candidate else [])
    payload_builder = density_payload if candidate else lambda row: honest._extract_calibrator_payload(feature_dict(row))
    scores = [None] * len(rows)
    for held_out in range(FOLDS):
        train_indexes = [i for i, fold in enumerate(fold_ids) if fold != held_out]
        test_indexes = [i for i, fold in enumerate(fold_ids) if fold == held_out]
        model = fit_model(
            [payload_builder(rows[i]) for i in train_indexes],
            [labels[i] for i in train_indexes],
            feature_names,
        )
        for index in test_indexes:
            scores[index] = model.predict_proba(payload_builder(rows[index]))
    metrics = classification_metrics(labels, scores, THRESHOLD)
    metrics["f1_ci"] = bootstrap_f1_ci(labels, scores, THRESHOLD, resamples=1000)
    metrics["brier"] = brier_score(labels, scores)
    metrics["ece"] = expected_calibration_error(labels, scores)
    return scores, [score >= THRESHOLD for score in scores], metrics


def confusion_for(indices, labels, scores):
    subset_labels = [labels[i] for i in indices]
    subset_scores = [scores[i] for i in indices]
    return classification_metrics(subset_labels, subset_scores, THRESHOLD)


def per_group(rows, labels, scores, classification):
    by_chain = {}
    for chain in sorted({row.chain for row in rows}):
        indexes = [i for i, row in enumerate(rows) if row.chain == chain]
        by_chain[chain] = confusion_for(indexes, labels, scores)
    by_vulnerability = {}
    for vuln in sorted({classification.get(row.txn_hash, {}).get("vuln_type", "") for row in rows if row.label}):
        if not vuln:
            continue
        indexes = [
            i for i, row in enumerate(rows)
            if row.label and classification.get(row.txn_hash, {}).get("vuln_type", "") == vuln
        ]
        by_vulnerability[vuln] = confusion_for(indexes, labels, scores)
    return {"by_chain": by_chain, "by_vulnerability_exploit_rows": by_vulnerability}


def main() -> int:
    rows = [row for row in load_exploit_rows(str(EXPLOIT_CSV)) + load_benign_rows() if row.has_trace_features]
    labels = [row.label for row in rows]
    if len(rows) != 1115 or sum(labels) != 115:
        raise AssertionError(f"expected legacy 1115 rows / 115 exploit rows, got {len(rows)} / {sum(labels)}")

    classification = {}
    with CLASSIFICATION_CSV.open(encoding="utf-8-sig", newline="") as handle:
        classification = {row["txn_hash"].lower(): row for row in csv.DictReader(handle)}

    baseline_scores, baseline_decisions, baseline_metrics = evaluate(rows, labels, candidate=False)
    candidate_scores, candidate_decisions, candidate_metrics = evaluate(rows, labels, candidate=True)
    paired = mcnemar_counts(labels, baseline_scores, candidate_scores, THRESHOLD)
    output_rows = []
    for row, label, base_score, candidate_score, base_decision, candidate_decision in zip(
        rows, labels, baseline_scores, candidate_scores, baseline_decisions, candidate_decisions
    ):
        output_rows.append(
            {
                "txn_hash": row.txn_hash,
                "chain": row.chain,
                "label": label,
                "features": {key: row.features[key] for key in ("functioncall_count", "address_count", "max_depth", "gas_cost")},
                "address_fanout_ratio": float(row.features.get("address_count") or 0.0) / max(float(row.features.get("functioncall_count") or 0.0), 1.0),
                "baseline_score": base_score,
                "candidate_score": candidate_score,
                "baseline_prediction": base_decision,
                "candidate_prediction": candidate_decision,
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_OUT.open("w", encoding="utf-8") as handle:
        for item in output_rows:
            handle.write(json.dumps(item, sort_keys=True) + "\n")

    report = {
        "schema_version": 1,
        "status": "LEGACY_115_TRACE_DENSITY_CALIBRATION_DIAGNOSTIC_ONLY",
        "hypothesis": "High address fan-out relative to function-call volume contributes to the observed Ethereum false positives; add one deterministic address_count/functioncall_count calibration feature.",
        "candidate_feature": CANDIDATE_FEATURE,
        "rows": len(rows),
        "exploit_rows": sum(labels),
        "benign_rows": len(labels) - sum(labels),
        "folds": FOLDS,
        "threshold": THRESHOLD,
        "leakage_control": "The ratio is computed from row-local trace features; each fold trains only on the other four hash folds; the threshold is fixed at 0.5.",
        "metrics": {"baseline": baseline_metrics, "candidate": candidate_metrics},
        "paired_mcnemar": {"counts": paired, "statistic": mcnemar_statistic(paired)},
        "breakdowns": {
            "baseline": per_group(rows, labels, baseline_scores, classification),
            "candidate": per_group(rows, labels, candidate_scores, classification),
        },
        "input_sha256": {
            "exploit": sha256(EXPLOIT_CSV),
            "benign_traces": sha256(BENIGN_CSV),
            "calibration": sha256(ROOT / "faultseeker/research/calibration.py"),
            "honest_harness": sha256(ROOT / "benchmark/run_honest_experiments.py"),
        },
        "raw_predictions": str(PREDICTIONS_OUT.relative_to(ROOT)).replace("\\", "/"),
        "original_246_row_claim": "not evaluated; legacy 115-row diagnostic only",
    }
    report["output_sha256"] = {
        "predictions_jsonl": sha256(PREDICTIONS_OUT),
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    CHECKSUMS_OUT.write_text(
        json.dumps(
            {
                "predictions_jsonl": sha256(PREDICTIONS_OUT),
                "report_json": sha256(REPORT_OUT),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["metrics"], sort_keys=True))
    print(json.dumps(report["paired_mcnemar"], sort_keys=True))
    print(f"wrote {REPORT_OUT}")
    print(f"wrote {PREDICTIONS_OUT}")
    print(f"wrote {CHECKSUMS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
