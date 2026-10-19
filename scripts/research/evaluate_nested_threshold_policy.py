"""Leakage-safe nested threshold experiment for the legacy 115 diagnostic.

Hypothesis: the current calibrated scores are conservative because the training
prevalence is roughly 10%; selecting the decision threshold inside training
folds may improve F1 without changing features or labels.  The outer test rows
are never used to select a threshold.  This is a diagnostic on the legacy
115-row population plus 1,000 benign traces, not the original 246-row claim.
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
THRESHOLDS = tuple(round(0.05 * i, 2) for i in range(1, 20))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit(rows, labels):
    model = LogisticConfidenceCalibrator()
    model.fit(
        [honest._extract_calibrator_payload(row) for row in rows],
        labels,
        epochs=1000,
        learning_rate=0.05,
        l2=0.001,
    )
    return model


def f1_at(labels, scores, threshold):
    tp = fp = fn = 0
    for label, score in zip(labels, scores):
        predicted = score >= threshold
        if predicted and label:
            tp += 1
        elif predicted and not label:
            fp += 1
        elif not predicted and label:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def confusion(labels, decisions):
    tp = sum(y and p for y, p in zip(labels, decisions))
    fp = sum((not y) and p for y, p in zip(labels, decisions))
    tn = sum((not y) and (not p) for y, p in zip(labels, decisions))
    fn = sum(y and (not p) for y, p in zip(labels, decisions))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "n": len(labels),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "fpr": round(fpr, 6),
    }


def fold_of(txn_hash: str, salt: str | None = None) -> int:
    key = str(txn_hash) if salt is None else f"{salt}:{txn_hash}"
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % FOLDS


def nested_threshold(rows, labels):
    outer_ids = [fold_of(row.txn_hash) for row in rows]
    base_scores = [None] * len(rows)
    candidate_decisions = [None] * len(rows)
    chosen = []

    for outer in range(FOLDS):
        train_idx = [i for i, fold in enumerate(outer_ids) if fold != outer]
        test_idx = [i for i, fold in enumerate(outer_ids) if fold == outer]

        inner_oof_scores = [None] * len(train_idx)
        for inner in range(FOLDS):
            inner_train = [pos for pos, idx in enumerate(train_idx) if fold_of(rows[idx].txn_hash, "inner") != inner]
            inner_test = [pos for pos, idx in enumerate(train_idx) if fold_of(rows[idx].txn_hash, "inner") == inner]
            model = fit([feature_dict(rows[train_idx[pos]]) for pos in inner_train], [labels[train_idx[pos]] for pos in inner_train])
            for pos in inner_test:
                inner_oof_scores[pos] = model.predict_proba(honest._extract_calibrator_payload(feature_dict(rows[train_idx[pos]])))

        inner_labels = [labels[idx] for idx in train_idx]
        threshold = max(
            THRESHOLDS,
            key=lambda candidate: (f1_at(inner_labels, inner_oof_scores, candidate), -abs(candidate - 0.5), -candidate),
        )
        chosen.append({"outer_fold": outer, "threshold": threshold, "train_n": len(train_idx), "test_n": len(test_idx)})

        model = fit([feature_dict(rows[i]) for i in train_idx], [labels[i] for i in train_idx])
        for i in test_idx:
            score = model.predict_proba(honest._extract_calibrator_payload(feature_dict(rows[i])))
            base_scores[i] = score
            candidate_decisions[i] = score >= threshold

    baseline_decisions = [score >= 0.5 for score in base_scores]
    return base_scores, baseline_decisions, candidate_decisions, chosen


def main() -> int:
    exploit_path = ROOT / "benchmark/benchmark_classification.csv"
    benign_path = ROOT / "benchmark/imported/benign_traces.csv"
    output = ROOT / "reports/reproducibility/legacy_115_diagnostic/nested_threshold_policy"
    rows = load_exploit_rows(str(exploit_path)) + load_benign_rows()
    usable = [row for row in rows if row.has_trace_features]
    labels = [row.label for row in usable]
    payloads = [feature_dict(row) for row in usable]

    scores, baseline_decisions, candidate_decisions, chosen = nested_threshold(usable, labels)
    baseline = confusion(labels, baseline_decisions)
    candidate = confusion(labels, candidate_decisions)
    baseline_ci = bootstrap_f1_ci(labels, scores, 0.5, resamples=1000)
    candidate_binary_scores = [1.0 if decision else 0.0 for decision in candidate_decisions]
    candidate_ci = bootstrap_f1_ci(labels, candidate_binary_scores, 0.5, resamples=1000)

    output.mkdir(parents=True, exist_ok=True)
    with (output / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row, label, score, base, improved in zip(usable, labels, scores, baseline_decisions, candidate_decisions):
            handle.write(
                json.dumps(
                    {
                        "txn_hash": row.txn_hash,
                        "chain": row.chain,
                        "label": label,
                        "score": score,
                        "baseline_threshold": 0.5,
                        "nested_threshold": improved,
                        "baseline_prediction": base,
                        "candidate_prediction": improved,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    report = {
        "schema_version": 1,
        "status": "LEGACY_115_NESTED_THRESHOLD_DIAGNOSTIC_ONLY",
        "hypothesis": "nested training-fold threshold selection may improve F1 over the fixed 0.5 decision threshold",
        "n": len(usable),
        "exploit_rows": len([row for row in usable if row.label]),
        "benign_rows": len([row for row in usable if not row.label]),
        "baseline": {**baseline, "f1_ci": baseline_ci},
        "candidate": {**candidate, "f1_ci": candidate_ci},
        "chosen_thresholds": chosen,
        "threshold_grid": list(THRESHOLDS),
        "leakage_control": "outer test rows never used for threshold selection; threshold selected from inner OOF predictions within each outer training fold",
        "raw_predictions": str((output / "predictions.jsonl").relative_to(ROOT)).replace("\\", "/"),
        "input_sha256": {"exploit": sha256(exploit_path), "benign_traces": sha256(benign_path)},
        "original_246_row_claim": "not evaluated; legacy 115-row diagnostic only",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"baseline": baseline, "candidate": candidate, "thresholds": chosen}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
