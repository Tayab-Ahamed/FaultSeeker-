"""Retain per-example predictions and paired McNemar statistics for legacy 115.

This complements the aggregate legacy diagnostic.  It uses the same leakage-safe
scorers and deterministic five-fold calibrators, writes one prediction record
per row, and computes exact two-sided McNemar binomial p-values.  It remains a
legacy 115-row diagnostic, not the original 246-row result.
"""

from __future__ import annotations

import hashlib
import json
from math import comb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.features import (
    audit_feature_coverage,
    comparable_subset,
    feature_dict,
    load_benign_rows,
    load_exploit_rows,
)
from benchmark.honest_eval.leakage_guard import audit_scorer
from benchmark import run_honest_experiments as honest


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_mcnemar(correct_a: list[bool], correct_b: list[bool]) -> dict:
    b = sum(a and not c for a, c in zip(correct_a, correct_b))
    c = sum(c and not a for a, c in zip(correct_a, correct_b))
    n = b + c
    if not n:
        return {"b": 0, "c": 0, "discordant": 0, "p_two_sided": 1.0}
    smaller = min(b, c)
    tail = sum(comb(n, k) for k in range(smaller + 1)) / (2**n)
    return {"b": b, "c": c, "discordant": n, "p_two_sided": min(1.0, 2.0 * tail)}


def main() -> int:
    output = ROOT / "reports/reproducibility/legacy_115_diagnostic"
    exploit_path = ROOT / "benchmark/benchmark_classification.csv"
    benign_path = ROOT / "benchmark/imported/benign_traces.csv"
    exploit_rows = load_exploit_rows(str(exploit_path))
    benign_rows = load_benign_rows()
    usable = comparable_subset(exploit_rows + benign_rows)
    labels = [row.label for row in usable]
    payloads = [feature_dict(row) for row in usable]

    honest._FOLD_CALIBRATORS = None
    honest._FOLD_CALIBRATORS_NO_TIG = None
    honest._ensure_fold_calibrators(payloads, labels, k=5)

    scores = {}
    for name, scorer in honest.SCORERS.items():
        audit = audit_scorer(scorer, payloads, labels)
        if audit["leaked"] or audit.get("perfectly_separable"):
            raise RuntimeError(f"scorer audit failed for {name}: {audit}")
        scores[name] = [float(scorer(payload)) for payload in payloads]

    prediction_path = output / "predictions.jsonl"
    output.mkdir(parents=True, exist_ok=True)
    with prediction_path.open("w", encoding="utf-8") as handle:
        for row, label, row_scores in zip(usable, labels, zip(*scores.values())):
            payload = {
                "txn_hash": row.txn_hash,
                "chain": row.chain,
                "label": label,
                "scores": dict(zip(scores, row_scores)),
                "predicted_positive": {
                    name: value >= 0.5 for name, value in zip(scores, row_scores)
                },
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    full = scores["FaultSeeker++ (Ours)"]
    full_correct = [(score >= 0.5) == bool(label) for score, label in zip(full, labels)]
    paired = {}
    for name, values in scores.items():
        if name == "FaultSeeker++ (Ours)":
            continue
        baseline_correct = [(score >= 0.5) == bool(label) for score, label in zip(values, labels)]
        paired[name] = exact_mcnemar(full_correct, baseline_correct)

    report = {
        "schema_version": 1,
        "status": "LEGACY_115_PAIRED_DIAGNOSTIC_ONLY",
        "n": len(usable),
        "exploit_rows": len(exploit_rows),
        "benign_rows": len(benign_rows),
        "feature_coverage": audit_feature_coverage(exploit_rows + benign_rows),
        "threshold": 0.5,
        "test": "exact two-sided McNemar binomial test on paired correctness",
        "paired_against_full_system": paired,
        "raw_predictions": str(prediction_path.relative_to(ROOT)).replace("\\", "/"),
        "input_sha256": {
            "exploit": sha256(exploit_path),
            "benign_traces": sha256(benign_path),
        },
        "original_246_row_claim": "not evaluated; this is a legacy 115-row diagnostic",
    }
    (output / "paired_statistics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(paired, sort_keys=True))
    print(f"wrote {prediction_path}")
    print(f"wrote {output / 'paired_statistics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
