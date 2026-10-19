"""OOF experiment for explicit static/dynamic/LLM score fusion.

The current full-system calibrator is fit from trace-derived features, while
the repository also computes static, dynamic, and LLM-style component scores.
Those components are deterministic functions of the same row-local trace
features, but their clipping and low-call branch create nonlinear transforms
that the current linear calibration does not expose explicitly.

This fixed, non-selected candidate adds the three component scores to the
existing calibration payload and evaluates it with the same five-fold hash OOF
protocol and threshold as the legacy baseline. It is diagnostic-only and does
not change production or the original 246-row claim.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark import run_honest_experiments as honest
from benchmark.honest_eval.features import feature_dict, load_benign_rows, load_exploit_rows
from benchmark.honest_eval.metrics import (
    brier_score,
    bootstrap_f1_ci,
    classification_metrics,
    expected_calibration_error,
    mcnemar_counts,
    mcnemar_statistic,
)
from faultseeker.research.calibration import FEATURE_NAMES, LogisticConfidenceCalibrator


FOLDS = 5
THRESHOLD = 0.5
FUSION_FEATURES = ("static_score", "dynamic_score", "llm_score")
OUTPUT_DIR = ROOT / "reports/reproducibility/legacy_115_diagnostic/feature_fusion_calibration"
PREDICTIONS_OUT = OUTPUT_DIR / "predictions.jsonl"
REPORT_OUT = OUTPUT_DIR / "report.json"
CHECKSUMS_OUT = OUTPUT_DIR / "checksums.json"
EXPLOIT_CSV = ROOT / "benchmark/benchmark_classification.csv"
BENIGN_CSV = ROOT / "benchmark/imported/benign_traces.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fold_of(txn_hash: str) -> int:
    return int(hashlib.sha256(str(txn_hash).encode("utf-8")).hexdigest(), 16) % FOLDS


def payload(row, fused: bool) -> dict:
    source = feature_dict(row)
    result = honest._extract_calibrator_payload(source)
    if fused:
        result.update(
            static_score=honest.static_proxy_scorer(source),
            dynamic_score=honest.dynamic_trace_rule_scorer(source),
            llm_score=honest.llm_only_scorer(source),
        )
    return result


def evaluate(rows, labels, fused: bool):
    folds = [fold_of(row.txn_hash) for row in rows]
    feature_names = list(FEATURE_NAMES) + (list(FUSION_FEATURES) if fused else [])
    scores = [None] * len(rows)
    for held_out in range(FOLDS):
        train = [i for i, fold in enumerate(folds) if fold != held_out]
        test = [i for i, fold in enumerate(folds) if fold == held_out]
        model = LogisticConfidenceCalibrator(feature_names=feature_names)
        model.fit([payload(rows[i], fused) for i in train], [labels[i] for i in train], epochs=1000, learning_rate=0.05, l2=0.001)
        for index in test:
            scores[index] = model.predict_proba(payload(rows[index], fused))
    metrics = classification_metrics(labels, scores, THRESHOLD)
    metrics["f1_ci"] = bootstrap_f1_ci(labels, scores, THRESHOLD, resamples=1000)
    metrics["brier"] = brier_score(labels, scores)
    metrics["ece"] = expected_calibration_error(labels, scores)
    return scores, [score >= THRESHOLD for score in scores], metrics


def subgroup_metrics(rows, labels, scores, classification):
    result = {"by_chain": {}, "by_vulnerability_exploit_rows": {}}
    for chain in sorted({row.chain for row in rows}):
        indexes = [i for i, row in enumerate(rows) if row.chain == chain]
        result["by_chain"][chain] = classification_metrics([labels[i] for i in indexes], [scores[i] for i in indexes], THRESHOLD)
    for vuln in sorted({classification.get(row.txn_hash, {}).get("vuln_type", "") for row in rows if row.label}):
        if not vuln:
            continue
        indexes = [i for i, row in enumerate(rows) if row.label and classification.get(row.txn_hash, {}).get("vuln_type", "") == vuln]
        result["by_vulnerability_exploit_rows"][vuln] = classification_metrics([labels[i] for i in indexes], [scores[i] for i in indexes], THRESHOLD)
    return result


def main() -> int:
    rows = [row for row in load_exploit_rows(str(EXPLOIT_CSV)) + load_benign_rows() if row.has_trace_features]
    labels = [row.label for row in rows]
    if len(rows) != 1115 or sum(labels) != 115:
        raise AssertionError(f"expected 1115 rows / 115 exploits, got {len(rows)} / {sum(labels)}")
    classification = {}
    with EXPLOIT_CSV.open(encoding="utf-8-sig", newline="") as handle:
        classification = {item["txn_hash"].lower(): item for item in csv.DictReader(handle)}

    baseline_scores, baseline_decisions, baseline_metrics = evaluate(rows, labels, fused=False)
    candidate_scores, candidate_decisions, candidate_metrics = evaluate(rows, labels, fused=True)
    paired = mcnemar_counts(labels, baseline_scores, candidate_scores, THRESHOLD)
    raw_rows = []
    for row, label, base_score, candidate_score, base_decision, candidate_decision in zip(rows, labels, baseline_scores, candidate_scores, baseline_decisions, candidate_decisions):
        source = feature_dict(row)
        raw_rows.append({
            "txn_hash": row.txn_hash,
            "chain": row.chain,
            "label": label,
            "features": {key: row.features[key] for key in ("functioncall_count", "address_count", "max_depth", "gas_cost")},
            "component_scores": {
                "static_score": honest.static_proxy_scorer(source),
                "dynamic_score": honest.dynamic_trace_rule_scorer(source),
                "llm_score": honest.llm_only_scorer(source),
            },
            "baseline_score": base_score,
            "candidate_score": candidate_score,
            "baseline_prediction": base_decision,
            "candidate_prediction": candidate_decision,
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_OUT.open("w", encoding="utf-8") as handle:
        for item in raw_rows:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    report = {
        "schema_version": 1,
        "status": "LEGACY_115_FEATURE_FUSION_CALIBRATION_DIAGNOSTIC_ONLY",
        "hypothesis": "Explicitly fusing the existing static, dynamic, and LLM-style component scores may recover nonlinear evidence that the current trace-only linear calibrator leaves unused.",
        "candidate_features": list(FUSION_FEATURES),
        "rows": len(rows),
        "exploit_rows": sum(labels),
        "benign_rows": len(labels) - sum(labels),
        "folds": FOLDS,
        "threshold": THRESHOLD,
        "leakage_control": "Component scores use only row-local trace features; each fold trains only on the other four hash folds; threshold remains fixed at 0.5.",
        "metrics": {"baseline": baseline_metrics, "candidate": candidate_metrics},
        "paired_mcnemar": {"counts": paired, "statistic": mcnemar_statistic(paired)},
        "breakdowns": {"baseline": subgroup_metrics(rows, labels, baseline_scores, classification), "candidate": subgroup_metrics(rows, labels, candidate_scores, classification)},
        "input_sha256": {
            "exploit": sha256(EXPLOIT_CSV),
            "benign_traces": sha256(BENIGN_CSV),
            "honest_harness": sha256(ROOT / "benchmark/run_honest_experiments.py"),
            "calibration": sha256(ROOT / "faultseeker/research/calibration.py"),
        },
        "raw_predictions": str(PREDICTIONS_OUT.relative_to(ROOT)).replace("\\", "/"),
        "original_246_row_claim": "not evaluated; legacy 115-row diagnostic only",
    }
    report["output_sha256"] = {"predictions_jsonl": sha256(PREDICTIONS_OUT)}
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    CHECKSUMS_OUT.write_text(json.dumps({"predictions_jsonl": sha256(PREDICTIONS_OUT), "report_json": sha256(REPORT_OUT)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], sort_keys=True))
    print(json.dumps(report["paired_mcnemar"], sort_keys=True))
    print(f"wrote {REPORT_OUT}")
    print(f"wrote {PREDICTIONS_OUT}")
    print(f"wrote {CHECKSUMS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
