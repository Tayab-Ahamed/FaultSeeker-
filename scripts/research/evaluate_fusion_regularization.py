"""Predeclared stronger-regularization check for the full fusion variant.

The ablation validation showed a small, three-row full-fusion gain spread over
three folds. This experiment tests one stability hypothesis only: with 11
calibration inputs and 115 positive rows, stronger L2 regularization may reduce
small-sample coefficient variance. It uses the identical rows, folds, feature
construction, and fixed threshold as the validated baseline/fusion experiment.
No hyperparameter search or held-out selection is performed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.features import load_benign_rows, load_exploit_rows
from benchmark.honest_eval.metrics import (
    brier_score,
    bootstrap_f1_ci,
    classification_metrics,
    expected_calibration_error,
    mcnemar_counts,
    mcnemar_statistic,
)
from faultseeker.research.calibration import FEATURE_NAMES, LogisticConfidenceCalibrator
from scripts.research.validate_feature_fusion_ablation import (
    EXPLOIT_CSV,
    BENIGN_CSV,
    FOLDS,
    THRESHOLD,
    fold_of,
    payload,
)


BASELINE_L2 = 0.001
CANDIDATE_L2 = 0.01
FUSION_FEATURES = ("static_score", "dynamic_score", "llm_score")
OUTPUT_DIR = ROOT / "reports/reproducibility/legacy_115_diagnostic/fusion_regularization"
PREDICTIONS_OUT = OUTPUT_DIR / "predictions.jsonl"
REPORT_OUT = OUTPUT_DIR / "report.json"
CHECKSUMS_OUT = OUTPUT_DIR / "checksums.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(rows, labels, l2: float):
    fold_ids = [fold_of(row.txn_hash) for row in rows]
    names = list(FEATURE_NAMES) + list(FUSION_FEATURES)
    scores = [None] * len(rows)
    for held_out in range(FOLDS):
        train = [i for i, fold in enumerate(fold_ids) if fold != held_out]
        test = [i for i, fold in enumerate(fold_ids) if fold == held_out]
        model = LogisticConfidenceCalibrator(feature_names=names)
        model.fit(
            [payload(rows[i], FUSION_FEATURES) for i in train],
            [labels[i] for i in train],
            epochs=1000,
            learning_rate=0.05,
            l2=l2,
        )
        for i in test:
            scores[i] = model.predict_proba(payload(rows[i], FUSION_FEATURES))
    return scores


def metrics(labels, scores):
    result = classification_metrics(labels, scores, THRESHOLD)
    result["f1_ci"] = bootstrap_f1_ci(labels, scores, THRESHOLD, resamples=1000)
    result["brier"] = brier_score(labels, scores)
    result["ece"] = expected_calibration_error(labels, scores)
    return result


def main() -> int:
    rows = [row for row in load_exploit_rows(str(EXPLOIT_CSV)) + load_benign_rows() if row.has_trace_features]
    labels = [row.label for row in rows]
    if len(rows) != 1115 or sum(labels) != 115:
        raise AssertionError("legacy population changed")
    baseline_scores = score(rows, labels, BASELINE_L2)
    candidate_scores = score(rows, labels, CANDIDATE_L2)
    baseline_metrics = metrics(labels, baseline_scores)
    candidate_metrics = metrics(labels, candidate_scores)
    paired = mcnemar_counts(labels, baseline_scores, candidate_scores, THRESHOLD)
    raw = []
    for row, label, base, candidate in zip(rows, labels, baseline_scores, candidate_scores):
        raw.append({
            "txn_hash": row.txn_hash,
            "chain": row.chain,
            "label": label,
            "features": {key: row.features[key] for key in ("functioncall_count", "address_count", "max_depth", "gas_cost")},
            "baseline_score": base,
            "candidate_score": candidate,
            "baseline_prediction": base >= THRESHOLD,
            "candidate_prediction": candidate >= THRESHOLD,
        })
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_OUT.open("w", encoding="utf-8") as handle:
        for row in raw:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    report = {
        "schema_version": 1,
        "status": "LEGACY_115_FUSION_REGULARIZATION_DIAGNOSTIC_ONLY",
        "hypothesis": "Stronger fixed L2 regularization may stabilize the 11-feature full-fusion calibrator on a small positive class.",
        "population": {"rows": len(rows), "exploit_rows": sum(labels), "benign_rows": len(labels) - sum(labels)},
        "folds": FOLDS,
        "threshold": THRESHOLD,
        "baseline_l2": BASELINE_L2,
        "candidate_l2": CANDIDATE_L2,
        "metrics": {"baseline": baseline_metrics, "candidate": candidate_metrics},
        "paired_mcnemar": {"counts": paired, "statistic": mcnemar_statistic(paired)},
        "changed_examples": [row for row in raw if row["baseline_prediction"] != row["candidate_prediction"]],
        "input_sha256": {"exploit": sha256(EXPLOIT_CSV), "benign_traces": sha256(BENIGN_CSV)},
        "raw_predictions": str(PREDICTIONS_OUT.relative_to(ROOT)).replace("\\", "/"),
        "original_246_row_claim": "not evaluated; legacy 115-row diagnostic only",
    }
    report["output_sha256"] = {"predictions_jsonl": sha256(PREDICTIONS_OUT)}
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    CHECKSUMS_OUT.write_text(json.dumps({"predictions_jsonl": sha256(PREDICTIONS_OUT), "report_json": sha256(REPORT_OUT)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": report["metrics"], "paired": report["paired_mcnemar"], "changed": len(report["changed_examples"])}, sort_keys=True))
    print(f"wrote {REPORT_OUT}")
    print(f"wrote {PREDICTIONS_OUT}")
    print(f"wrote {CHECKSUMS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
