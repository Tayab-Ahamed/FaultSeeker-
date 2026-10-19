"""Test positive-class weighting as a leakage-safe calibration hypothesis.

Training-only positive oversampling is evaluated with the same deterministic
five-fold OOF protocol and fixed 0.5 decision threshold as the current legacy
diagnostic.  No evaluation-row labels are used during fitting.  This is a
legacy 115-row experiment, not a 246-row paper result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.features import feature_dict, load_benign_rows, load_exploit_rows
from benchmark.honest_eval.metrics import bootstrap_f1_ci
from benchmark import run_honest_experiments as honest
from faultseeker.research.calibration import LogisticConfidenceCalibrator


FOLDS = 5
WEIGHTS = (1, 2, 3, 4)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fold_of(txn_hash: str) -> int:
    return int(hashlib.sha256(str(txn_hash).encode()).hexdigest(), 16) % FOLDS


def fit(rows, labels, positive_weight):
    training_rows = []
    training_labels = []
    for row, label in zip(rows, labels):
        repetitions = positive_weight if label else 1
        training_rows.extend([row] * repetitions)
        training_labels.extend([label] * repetitions)
    model = LogisticConfidenceCalibrator()
    model.fit(
        [honest._extract_calibrator_payload(row) for row in training_rows],
        training_labels,
        epochs=1000,
        learning_rate=0.05,
        l2=0.001,
    )
    return model


def confusion(labels, decisions):
    tp = sum(y and p for y, p in zip(labels, decisions))
    fp = sum((not y) and p for y, p in zip(labels, decisions))
    tn = sum((not y) and (not p) for y, p in zip(labels, decisions))
    fn = sum(y and (not p) for y, p in zip(labels, decisions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {"n": len(labels), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(precision, 6), "recall": round(recall, 6),
            "f1": round(f1, 6), "fpr": round(fpr, 6)}


def evaluate(rows, labels, positive_weight):
    fold_ids = [fold_of(row.txn_hash) for row in rows]
    scores = [None] * len(rows)
    for held_out in range(FOLDS):
        train = [i for i, fold in enumerate(fold_ids) if fold != held_out]
        test = [i for i, fold in enumerate(fold_ids) if fold == held_out]
        model = fit([feature_dict(rows[i]) for i in train], [labels[i] for i in train], positive_weight)
        for i in test:
            scores[i] = model.predict_proba(honest._extract_calibrator_payload(feature_dict(rows[i])))
    decisions = [score >= 0.5 for score in scores]
    metrics = confusion(labels, decisions)
    metrics["f1_ci"] = bootstrap_f1_ci(labels, scores, 0.5, resamples=1000)
    return scores, decisions, metrics


def main() -> int:
    exploit_path = ROOT / "benchmark/benchmark_classification.csv"
    benign_path = ROOT / "benchmark/imported/benign_traces.csv"
    output = ROOT / "reports/reproducibility/legacy_115_diagnostic/class_weighted_calibration"
    rows = load_exploit_rows(str(exploit_path)) + load_benign_rows()
    rows = [row for row in rows if row.has_trace_features]
    labels = [row.label for row in rows]
    results = {}
    raw = {}
    for weight in WEIGHTS:
        scores, decisions, metrics = evaluate(rows, labels, weight)
        results[str(weight)] = metrics
        raw[str(weight)] = [
            {"txn_hash": row.txn_hash, "label": label, "score": score, "prediction": decision}
            for row, label, score, decision in zip(rows, labels, scores, decisions)
        ]

    output.mkdir(parents=True, exist_ok=True)
    (output / "predictions.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "LEGACY_115_CLASS_WEIGHTED_CALIBRATION_DIAGNOSTIC_ONLY",
        "hypothesis": "positive-class oversampling during training may recover low-score exploit false negatives",
        "weights": list(WEIGHTS),
        "results": results,
        "leakage_control": "positive weighting is applied only to outer-fold training rows; test rows are scored once with fixed threshold 0.5",
        "input_sha256": {"exploit": sha256(exploit_path), "benign_traces": sha256(benign_path)},
        "raw_predictions": str((output / "predictions.json").relative_to(ROOT)).replace("\\", "/"),
        "original_246_row_claim": "not evaluated; legacy 115-row diagnostic only",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
