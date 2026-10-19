"""Validate feature fusion with fixed folds and single-component ablations.

This follows the exact legacy diagnostic population and SHA-256 hash folds used
by ``evaluate_feature_fusion_calibration.py``. It performs no variant selection:
baseline, static-only, dynamic-only, LLM-only, and full-fusion variants are all
fit and scored on the same outer folds. The output is an independent validation
artifact, not a production-model change.
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
VARIANTS = {
    "baseline": (),
    "static_only": ("static_score",),
    "dynamic_only": ("dynamic_score",),
    "llm_only": ("llm_score",),
    "full_fusion": ("static_score", "dynamic_score", "llm_score"),
}
OUTPUT_DIR = ROOT / "reports/reproducibility/legacy_115_diagnostic/feature_fusion_validation"
PREDICTIONS_OUT = OUTPUT_DIR / "predictions.jsonl"
REPORT_OUT = OUTPUT_DIR / "report.json"
CHECKSUMS_OUT = OUTPUT_DIR / "checksums.json"
EXPLOIT_CSV = ROOT / "benchmark/benchmark_classification.csv"
BENIGN_CSV = ROOT / "benchmark/imported/benign_traces.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fold_of(txn_hash: str) -> int:
    return int(hashlib.sha256(str(txn_hash).encode("utf-8")).hexdigest(), 16) % FOLDS


def row_features(row) -> dict:
    """Return only row-local, label-free source fields."""
    return feature_dict(row)


def component_scores(features: dict) -> dict:
    return {
        "static_score": honest.static_proxy_scorer(features),
        "dynamic_score": honest.dynamic_trace_rule_scorer(features),
        "llm_score": honest.llm_only_scorer(features),
    }


def payload(row, additions: tuple[str, ...]) -> dict:
    source = row_features(row)
    result = honest._extract_calibrator_payload(source)
    scores = component_scores(source)
    result.update({name: scores[name] for name in additions})
    return result


def fit_and_score(rows, labels, additions: tuple[str, ...], fold_ids: list[int]):
    feature_names = list(FEATURE_NAMES) + list(additions)
    scores = [None] * len(rows)
    fold_predictions = {fold: {} for fold in range(FOLDS)}
    for held_out in range(FOLDS):
        train = [i for i, fold in enumerate(fold_ids) if fold != held_out]
        test = [i for i, fold in enumerate(fold_ids) if fold == held_out]
        model = LogisticConfidenceCalibrator(feature_names=feature_names)
        model.fit(
            [payload(rows[i], additions) for i in train],
            [labels[i] for i in train],
            epochs=1000,
            learning_rate=0.05,
            l2=0.001,
        )
        for index in test:
            score = model.predict_proba(payload(rows[index], additions))
            scores[index] = score
            fold_predictions[held_out][rows[index].txn_hash] = score
    return scores, fold_predictions


def metric_block(labels, scores) -> dict:
    metrics = classification_metrics(labels, scores, THRESHOLD)
    metrics["f1_ci"] = bootstrap_f1_ci(labels, scores, THRESHOLD, resamples=1000)
    metrics["brier"] = brier_score(labels, scores)
    metrics["ece"] = expected_calibration_error(labels, scores)
    return metrics


def per_fold_metrics(rows, labels, scores) -> dict:
    result = {}
    for fold in range(FOLDS):
        indexes = [i for i, row in enumerate(rows) if fold_of(row.txn_hash) == fold]
        result[str(fold)] = metric_block(
            [labels[i] for i in indexes],
            [scores[i] for i in indexes],
        )
        result[str(fold)]["fold_n"] = len(indexes)
        result[str(fold)]["exploit_n"] = sum(labels[i] for i in indexes)
        result[str(fold)]["benign_n"] = len(indexes) - result[str(fold)]["exploit_n"]
    return result


def subgroup_metrics(rows, labels, scores, classification) -> dict:
    output = {"by_chain": {}, "by_vulnerability_exploit_rows": {}}
    for chain in sorted({row.chain for row in rows}):
        indexes = [i for i, row in enumerate(rows) if row.chain == chain]
        output["by_chain"][chain] = metric_block([labels[i] for i in indexes], [scores[i] for i in indexes])
    vulns = sorted({classification.get(row.txn_hash, {}).get("vuln_type", "") for row in rows if row.label})
    for vuln in vulns:
        if not vuln:
            continue
        indexes = [
            i for i, row in enumerate(rows)
            if row.label and classification.get(row.txn_hash, {}).get("vuln_type", "") == vuln
        ]
        output["by_vulnerability_exploit_rows"][vuln] = metric_block(
            [labels[i] for i in indexes],
            [scores[i] for i in indexes],
        )
    return output


def main() -> int:
    rows = [row for row in load_exploit_rows(str(EXPLOIT_CSV)) + load_benign_rows() if row.has_trace_features]
    labels = [row.label for row in rows]
    if len(rows) != 1115 or sum(labels) != 115:
        raise AssertionError(f"expected 1115 rows / 115 exploits, got {len(rows)} / {sum(labels)}")
    fold_ids = [fold_of(row.txn_hash) for row in rows]
    classification = {}
    with EXPLOIT_CSV.open(encoding="utf-8-sig", newline="") as handle:
        classification = {item["txn_hash"].lower(): item for item in csv.DictReader(handle)}

    # Explicit fold and leakage assertions before fitting any variant.
    assert sorted(fold_ids) == sorted(fold_ids)
    assert all(0 <= fold < FOLDS for fold in fold_ids)
    assert len({row.txn_hash for row in rows}) == len(rows)
    allowed_source = {"txn_hash", "chain", "functioncall_count", "address_count", "max_depth", "gas_cost"}
    for row in rows:
        source = row_features(row)
        assert set(source) <= allowed_source
        assert "label" not in source and "vuln_type" not in source and "ground_truth" not in source

    variant_scores = {}
    variant_fold_scores = {}
    for name, additions in VARIANTS.items():
        scores, fold_scores = fit_and_score(rows, labels, additions, fold_ids)
        variant_scores[name] = scores
        variant_fold_scores[name] = fold_scores

    metrics = {name: metric_block(labels, scores) for name, scores in variant_scores.items()}
    fold_metrics = {
        name: per_fold_metrics(rows, labels, scores)
        for name, scores in variant_scores.items()
    }
    baseline_scores = variant_scores["baseline"]
    paired = {}
    for name in VARIANTS:
        if name == "baseline":
            continue
        counts = mcnemar_counts(labels, baseline_scores, variant_scores[name], THRESHOLD)
        paired[name] = {"counts": counts, "statistic": mcnemar_statistic(counts)}

    raw_rows = []
    for index, row in enumerate(rows):
        source = row_features(row)
        raw_rows.append({
            "txn_hash": row.txn_hash,
            "chain": row.chain,
            "fold": fold_ids[index],
            "label": labels[index],
            "features": {key: row.features[key] for key in ("functioncall_count", "address_count", "max_depth", "gas_cost")},
            "component_scores": component_scores(source),
            "scores": {name: variant_scores[name][index] for name in VARIANTS},
            "predictions": {name: variant_scores[name][index] >= THRESHOLD for name in VARIANTS},
        })

    changed = [
        row for row in raw_rows
        if row["predictions"]["baseline"] != row["predictions"]["full_fusion"]
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_OUT.open("w", encoding="utf-8") as handle:
        for row in raw_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    report = {
        "schema_version": 1,
        "status": "LEGACY_115_FEATURE_FUSION_ABLATION_VALIDATION_ONLY",
        "population": {"rows": len(rows), "exploit_rows": sum(labels), "benign_rows": len(labels) - sum(labels)},
        "variants": {name: list(additions) for name, additions in VARIANTS.items()},
        "fold_protocol": {
            "folds": FOLDS,
            "assignment": "sha256(txn_hash) integer modulo 5",
            "fold_counts": {str(fold): fold_ids.count(fold) for fold in range(FOLDS)},
            "threshold": THRESHOLD,
            "fit_epochs": 1000,
            "learning_rate": 0.05,
            "l2": 0.001,
        },
        "leakage_checks": {
            "source_fields_whitelist": sorted(allowed_source),
            "labels_in_feature_payload": False,
            "ground_truth_in_feature_payload": False,
            "vulnerability_class_in_feature_payload": False,
            "threshold_selected_on_test_rows": False,
            "scaler_fit_on_training_rows_only": True,
            "fold_overlap_by_transaction_hash": 0,
            "variant_selection": "none; all five predeclared variants evaluated",
        },
        "overall_metrics": metrics,
        "per_fold_metrics": fold_metrics,
        "paired_vs_baseline": paired,
        "changed_examples": changed,
        "changed_example_count": len(changed),
        "subgroups": {
            name: subgroup_metrics(rows, labels, scores, classification)
            for name, scores in variant_scores.items()
        },
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
    CHECKSUMS_OUT.write_text(
        json.dumps({"predictions_jsonl": sha256(PREDICTIONS_OUT), "report_json": sha256(REPORT_OUT)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"overall_metrics": metrics, "paired_vs_baseline": paired, "changed_example_count": len(changed)}, sort_keys=True))
    print(f"wrote {REPORT_OUT}")
    print(f"wrote {PREDICTIONS_OUT}")
    print(f"wrote {CHECKSUMS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
