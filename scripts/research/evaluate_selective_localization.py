"""Offline selective-localization experiment.

This experiment tests whether an evidence-sufficiency abstention rule can
remove incorrect top-ranked localization decisions without using labels as
prediction-time features.  It reads only the retained provider-pinned
upstream results and their imported ground-truth files.  It does not contact
RPCs, invoke a model, rerun a ranker, or read Batch B/C/D/E results.

The 110 successful retained rows are split by ground-truth target contract
address only for leakage-resistant partitioning.  The target address is not
used as a feature.  Threshold selection uses validation rows only; the test
rows are untouched until final evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from faultseeker.function_analysis.candidate_generation import (  # noqa: E402
    parse_saved_trace_candidates,
)
from scripts.reproduce.audit_original_scorer_strictness import (  # noqa: E402
    GT_DIR,
    RAW_DIR,
    current_hit,
    load_valid_rows,
)


EXPERIMENT_VERSION = "selective-localization-v1"
SPLIT_SALT = "faultseeker++ selective localization grouped split v1"
RANDOM_SEED = 20261019
BOOTSTRAP_REPLICATES = 10_000
MIN_VALIDATION_COVERAGE = 0.50
OUTPUT_DIR = ROOT / "reports/research/selective_localization"

# Fixed before evaluation.  These are evidence-only features: no target,
# label, rank correctness, or ground-truth-derived value is included.
SCORE_WEIGHTS = {
    "trace_available": 0.20,
    "candidate_available": 0.15,
    "trace_call_strength": 0.20,
    "top1_support_strength": 0.15,
    "top1_observed_in_trace": 0.15,
    "top5_observed_fraction": 0.10,
    "selector_available": 0.05,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_function(prediction: Mapping[str, Any]) -> str:
    return str(
        prediction.get("function_name")
        or prediction.get("name")
        or prediction.get("function")
        or ""
    ).strip().split("(")[0].lower()


def prediction_key(prediction: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(prediction.get("code_address") or prediction.get("address") or "")
        .strip()
        .lower(),
        raw_function(prediction),
    )


def target_group_key(target: Any, txn_hash: str) -> str:
    """Return a conservative related-transaction grouping key.

    Ground-truth target addresses are used only to keep related transactions
    in one split.  They are never passed to feature extraction or scoring.
    """
    addresses = sorted({address.lower() for address, _member in target.functions})
    if not addresses:
        raise ValueError(f"missing target address for {txn_hash}")
    return "|".join(addresses)


def split_for_group(group_key: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{SPLIT_SALT}:{group_key}".encode("utf-8")).hexdigest()
    bucket = int(digest[:2], 16) % 10
    if bucket < 3:
        split = "test"
    elif bucket < 6:
        split = "validation"
    else:
        split = "train"
    return split, digest


def evidence_features(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Extract only prediction-time evidence from one retained raw result."""
    predictions = list(raw.get("predictions") or [])
    trace_text = str((raw.get("cast") or {}).get("output_tail") or "")
    trace_calls = parse_saved_trace_candidates(trace_text)
    observed = {
        (str(call.get("address") or "").lower(), raw_function(call))
        for call in trace_calls
    }
    keys = [prediction_key(prediction) for prediction in predictions]
    top5_count = min(5, len(predictions))
    top5_observed = sum(key in observed for key in keys[:top5_count])
    top1_support = len(predictions[0].get("supporting_call_depths") or []) if predictions else 0

    values = {
        "trace_available": bool(trace_text.strip()),
        "candidate_available": bool(predictions),
        "trace_calls": len(trace_calls),
        "top1_support_count": top1_support,
        "top1_observed_in_trace": bool(keys and keys[0] in observed),
        "top5_observed_count": top5_observed,
        "top5_candidate_count": top5_count,
        "selector_count": sum(bool(prediction.get("selector")) for prediction in predictions),
        "prediction_count": len(predictions),
        "no_trace_output": not bool(trace_text.strip()),
        "no_parsed_trace_calls": not bool(trace_calls),
        "no_predictions": not bool(predictions),
    }
    values["trace_call_strength"] = min(1.0, values["trace_calls"] / 3.0)
    values["top1_support_strength"] = min(1.0, values["top1_support_count"] / 3.0)
    values["top5_observed_fraction"] = (
        values["top5_observed_count"] / values["top5_candidate_count"]
        if values["top5_candidate_count"]
        else 0.0
    )
    values["selector_available"] = values["selector_count"] > 0
    values["score"] = round(
        SCORE_WEIGHTS["trace_available"] * float(values["trace_available"])
        + SCORE_WEIGHTS["candidate_available"] * float(values["candidate_available"])
        + SCORE_WEIGHTS["trace_call_strength"] * values["trace_call_strength"]
        + SCORE_WEIGHTS["top1_support_strength"] * values["top1_support_strength"]
        + SCORE_WEIGHTS["top1_observed_in_trace"] * float(values["top1_observed_in_trace"])
        + SCORE_WEIGHTS["top5_observed_fraction"] * values["top5_observed_fraction"]
        + SCORE_WEIGHTS["selector_available"] * float(values["selector_available"]),
        8,
    )
    return values


def build_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build labeled eligible rows and unlabeled run-failure records."""
    raw_by_txn = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(RAW_DIR.glob("*.json"))
    }
    eligible: list[dict[str, Any]] = []
    for txn_hash, _saved, target, _labels in load_valid_rows():
        raw = raw_by_txn[txn_hash]
        predictions = list(raw.get("predictions") or [])
        group_key = target_group_key(target, txn_hash)
        split, group_digest = split_for_group(group_key)
        features = evidence_features(raw)
        first_hit_rank = next(
            (
                rank
                for rank in range(1, len(predictions) + 1)
                if current_hit(target, predictions, rank)
            ),
            None,
        )
        eligible.append(
            {
                "txn_hash": txn_hash,
                "chain": raw.get("chain"),
                "provider": raw.get("provider"),
                "split": split,
                "split_group_sha256": group_digest,
                "prediction_time_features": features,
                "baseline_prediction_available": bool(predictions),
                "baseline_first_hit_rank": first_hit_rank,
                "replay_mismatch": bool(raw.get("replay_mismatch")),
                "status": raw.get("status"),
            }
        )
    failures = []
    for txn_hash, raw in sorted(raw_by_txn.items()):
        if raw.get("status") == "ok":
            continue
        features = evidence_features(raw)
        failures.append(
            {
                "txn_hash": txn_hash,
                "chain": raw.get("chain"),
                "provider": raw.get("provider"),
                "status": raw.get("status"),
                "failure_kind": raw.get("failure_kind"),
                "failure_message": raw.get("failure_message"),
                "evidence_failure": features,
            }
        )
    if len(eligible) != 110 or len(failures) != 5:
        raise ValueError(f"expected 110 eligible and 5 failed rows, got {len(eligible)} and {len(failures)}")
    return eligible, failures


def wilson_interval(hits: int, total: int) -> list[float]:
    if total <= 0:
        return [None, None]
    z = 1.959963984540054
    p = hits / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [round(center - half, 8), round(center + half, 8)]


def selected_rows(rows: Iterable[dict[str, Any]], threshold: float | None) -> list[dict[str, Any]]:
    rows = list(rows)
    if threshold is None:
        return rows
    return [row for row in rows if row["prediction_time_features"]["score"] >= threshold]


def aggregate_metrics(rows: Iterable[dict[str, Any]], threshold: float | None) -> dict[str, Any]:
    rows = list(rows)
    predicted = selected_rows(rows, threshold)
    n = len(rows)
    count = len(predicted)
    hits = {
        str(k): sum(
            row["baseline_first_hit_rank"] is not None
            and row["baseline_first_hit_rank"] <= k
            for row in predicted
        )
        for k in (1, 3, 5)
    }
    recall = {str(k): (hits[str(k)] / count if count else None) for k in (1, 3, 5)}
    return {
        "eligible_n": n,
        "predicted_n": count,
        "abstained_n": n - count,
        "coverage": count / n if n else None,
        "coverage_wilson95": wilson_interval(count, n),
        "hits": hits,
        "recall": recall,
        "recall_wilson95": {str(k): wilson_interval(hits[str(k)], count) for k in (1, 3, 5)},
        "top1_accuracy": recall["1"],
        "top1_error_rate": (1 - recall["1"] if recall["1"] is not None else None),
        "top1_error_wilson95": (
            wilson_interval(count - hits["1"], count) if count else [None, None]
        ),
    }


def choose_threshold(validation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    thresholds = sorted(
        {
            row["prediction_time_features"]["score"]
            for row in validation_rows
        }
    )
    candidates = []
    for threshold in thresholds:
        metrics = aggregate_metrics(validation_rows, threshold)
        if metrics["coverage"] is None or metrics["coverage"] < MIN_VALIDATION_COVERAGE:
            continue
        candidates.append(
            {
                "threshold": threshold,
                "metrics": metrics,
                "selection_key": (
                    metrics["top1_error_rate"],
                    metrics["coverage"],
                    -threshold,
                ),
            }
        )
    if not candidates:
        raise ValueError("no validation threshold satisfies minimum coverage")
    selected = min(candidates, key=lambda item: item["selection_key"])
    return {
        "threshold": selected["threshold"],
        "minimum_validation_coverage": MIN_VALIDATION_COVERAGE,
        "selection_rule": "minimize validation top-1 error; tie-break by lower coverage while retaining the minimum floor, then larger threshold",
        "validation_candidates": candidates,
        "selected_validation_metrics": selected["metrics"],
    }


def bootstrap_metrics(
    test_rows: list[dict[str, Any]],
    threshold: float,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Grouped bootstrap uncertainty, resampling target-contract groups."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in test_rows:
        groups[row["split_group_sha256"]].append(row)
    group_rows = list(groups.values())
    if not group_rows:
        raise ValueError("cannot bootstrap an empty test set")
    rng = random.Random(seed)
    samples: dict[str, list[float]] = defaultdict(list)
    for _ in range(replicates):
        sampled = [group_rows[rng.randrange(len(group_rows))] for _ in group_rows]
        rows = [row for group in sampled for row in group]
        baseline = aggregate_metrics(rows, None)
        selective = aggregate_metrics(rows, threshold)
        if selective["predicted_n"] == 0:
            continue
        samples["baseline_top1_error"].append(baseline["top1_error_rate"])
        samples["selective_top1_error"].append(selective["top1_error_rate"])
        samples["error_rate_delta_selective_minus_baseline"].append(
            selective["top1_error_rate"] - baseline["top1_error_rate"]
        )
        samples["selective_coverage"].append(selective["coverage"])
        for k in (1, 3, 5):
            samples[f"baseline_recall_at_{k}"].append(baseline["recall"][str(k)])
            samples[f"selective_recall_at_{k}"].append(selective["recall"][str(k)])

    def percentile(values: list[float], fraction: float) -> float:
        ordered = sorted(values)
        position = (len(ordered) - 1) * fraction
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return {
        "seed": seed,
        "replicates_requested": replicates,
        "replicates_used": len(samples["selective_top1_error"]),
        "resampling_unit": "target-contract group",
        "percentile_95": {
            name: [round(percentile(values, 0.025), 8), round(percentile(values, 0.975), 8)]
            for name, values in sorted(samples.items())
        },
    }


def threshold_curve(
    development_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    thresholds = sorted({row["prediction_time_features"]["score"] for row in development_rows})
    curve = [{"threshold": None, "baseline": aggregate_metrics(test_rows, None)}]
    curve.extend(
        {
            "threshold": threshold,
            "test": aggregate_metrics(test_rows, threshold),
        }
        for threshold in thresholds
    )
    return curve


def removed_counts(rows: list[dict[str, Any]], threshold: float) -> dict[str, dict[str, int]]:
    removed = [row for row in rows if row["prediction_time_features"]["score"] < threshold]
    return {
        str(k): {
            "correct_predictions_removed": sum(
                row["baseline_first_hit_rank"] is not None
                and row["baseline_first_hit_rank"] <= k
                for row in removed
            ),
            "incorrect_predictions_removed": sum(
                row["baseline_first_hit_rank"] is None
                or row["baseline_first_hit_rank"] > k
                for row in removed
            ),
        }
        for k in (1, 3, 5)
    }


def input_manifest() -> dict[str, Any]:
    files = sorted(list(GT_DIR.glob("*.json")) + list(RAW_DIR.glob("*.json")))
    return {
        "experiment_version": EXPERIMENT_VERSION,
        "repository_commit": "c19b2f06187865c5c6475a19cefd162ade99d89d",
        "inputs": {path.relative_to(ROOT).as_posix(): sha256(path) for path in files},
        "ground_truth_files": len(list(GT_DIR.glob("*.json"))),
        "raw_result_files": len(list(RAW_DIR.glob("*.json"))),
        "prohibited_inputs": ["Batch B", "Batch C", "Batch D", "Batch E"],
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_report(result: dict[str, Any]) -> None:
    test_baseline = result["evaluation"]["test"]["baseline"]
    test_selective = result["evaluation"]["test"]["selective"]
    selected = result["threshold_selection"]
    lines = [
        "# Selective localization experiment",
        "",
        "## Verdict",
        "",
        f"**{result['verdict']}** — this result is held-out evidence for the fixed grouped split, not a generalization claim.",
        "",
        "H1 asks whether abstention can remove incorrect high-confidence localization decisions while retaining useful coverage. The fixed baseline always returns the retained ranked prediction list. The selective policy abstains when the fixed evidence-sufficiency score is below the validation-selected threshold.",
        "",
        "## Dataset and leakage controls",
        "",
        f"- Full retained universe: {result['dataset']['total_retained_rows']} rows.",
        f"- Run-level evidence failures: {result['dataset']['run_failure_rows']} rows; these are outside the ranked-prediction evaluation.",
        f"- Eligible ranked-prediction rows: {result['dataset']['eligible_rows']}.",
        f"- Grouping: target-contract address, used only for partitioning; group overlap is {result['dataset']['group_overlap']}.",
        f"- Split counts: train={result['dataset']['split_counts']['train']}, validation={result['dataset']['split_counts']['validation']}, test={result['dataset']['split_counts']['test']}.",
        f"- Validation minimum coverage constraint: {selected['minimum_validation_coverage']:.0%}.",
        "- No ground-truth label, target address, or rank correctness enters the score features.",
        "",
        "## Evidence failures",
        "",
        f"- Failed retained runs: {result['dataset']['run_failure_rows']}.",
        f"- Eligible rows with no saved trace text: {result['dataset']['eligible_no_trace_output']}.",
        f"- Eligible rows with no parsed trace calls: {result['dataset']['eligible_no_parsed_trace_calls']}.",
        f"- Eligible rows with no selector metadata: {result['dataset']['eligible_no_selector']}.",
        "",
        "## Fixed score",
        "",
        "The score uses only saved prediction-time evidence: trace availability, non-empty candidates, parsed trace-call strength, top-ranked supporting-path strength, whether the top candidate appears in the saved trace, the fraction of top-five candidates observed in the trace, and selector metadata availability.",
        "",
        f"- Weights: `{json.dumps(SCORE_WEIGHTS, sort_keys=True)}`",
        f"- Selected threshold: `{selected['threshold']}`",
        f"- Selection rule: {selected['selection_rule']}",
        "",
        "## Held-out test results",
        "",
        "| Policy | Predictions | Coverage | R@1 | R@3 | R@5 | Top-1 error |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Always return ranking | {test_baseline['predicted_n']}/{test_baseline['eligible_n']} | {test_baseline['coverage']:.4f} | {test_baseline['hits']['1']}/{test_baseline['eligible_n']} ({test_baseline['recall']['1']:.4f}) | {test_baseline['hits']['3']}/{test_baseline['eligible_n']} ({test_baseline['recall']['3']:.4f}) | {test_baseline['hits']['5']}/{test_baseline['eligible_n']} ({test_baseline['recall']['5']:.4f}) | {test_baseline['top1_error_rate']:.4f} |",
        f"| Abstain below threshold | {test_selective['predicted_n']}/{test_selective['eligible_n']} | {test_selective['coverage']:.4f} | {test_selective['hits']['1']}/{test_selective['predicted_n']} ({test_selective['recall']['1']:.4f}) | {test_selective['hits']['3']}/{test_selective['predicted_n']} ({test_selective['recall']['3']:.4f}) | {test_selective['hits']['5']}/{test_selective['predicted_n']} ({test_selective['recall']['5']:.4f}) | {test_selective['top1_error_rate']:.4f} |",
        "",
        f"- Test abstention coverage: {test_selective['abstained_n']}/{test_selective['eligible_n']} abstained.",
        f"- Removed predictions: {json.dumps(result['evaluation']['test']['removed_counts'], sort_keys=True)}",
        f"- Grouped bootstrap 95% intervals: {json.dumps(result['evaluation']['test']['bootstrap']['percentile_95'], sort_keys=True)}",
        "",
        "## Coverage versus error",
        "",
        "The complete validation-derived threshold curve is stored in `metrics.json` under `threshold_curve`. It is descriptive; the final threshold was selected on validation only and then evaluated once on test.",
        "",
        "## Limitations",
        "",
        "- This is a small 110-row retained, provider-pinned, LLM-free evaluation, not the original 246-row paper cohort.",
        "- The five failed rows cannot be evaluated as ranked predictions and are reported separately rather than silently dropped from the retained-universe accounting.",
        "- Target-contract grouping is a conservative split control derived from ground truth; it is not a prediction feature.",
        "- The fixed score was not learned. The threshold is selected from validation, while weights and the 50% minimum-coverage rule are fixed in the experiment configuration.",
        "- Results are exploratory/held-out evidence for this retained dataset and do not establish generalization.",
    ]
    (OUTPUT_DIR / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    eligible, failures = build_rows()
    by_split = {
        split: [row for row in eligible if row["split"] == split]
        for split in ("train", "validation", "test")
    }
    selected = choose_threshold(by_split["validation"])
    threshold = selected["threshold"]
    test_baseline = aggregate_metrics(by_split["test"], None)
    test_selective = aggregate_metrics(by_split["test"], threshold)
    test_bootstrap = bootstrap_metrics(by_split["test"], threshold)
    test_removed = removed_counts(by_split["test"], threshold)
    development = by_split["train"] + by_split["validation"]
    group_sets = {
        split: {row["split_group_sha256"] for row in by_split[split]}
        for split in by_split
    }
    overlaps = [
        f"{left}-{right}"
        for index, left in enumerate(group_sets)
        for right in list(group_sets)[index + 1 :]
        if group_sets[left] & group_sets[right]
    ]
    if overlaps:
        raise AssertionError(f"group leakage detected: {overlaps}")

    for row in eligible:
        row["abstained_at_selected_threshold"] = row["prediction_time_features"]["score"] < threshold
        row["selected_policy_prediction"] = not row["abstained_at_selected_threshold"]
        row["baseline_top1_correct"] = row["baseline_first_hit_rank"] == 1

    result = {
        "schema_version": 1,
        "experiment_version": EXPERIMENT_VERSION,
        "hypothesis": "H1: evidence-sufficiency abstention can reduce incorrect high-confidence localization decisions while retaining useful coverage",
        "verdict": (
            "INCONCLUSIVE_NO_TEST_ABSTENTIONS"
            if test_selective["abstained_n"] == 0
            else "SUPPORTED_ON_HELD_OUT_RETAINED_TEST"
            if test_selective["top1_error_rate"] < test_baseline["top1_error_rate"]
            and test_selective["coverage"] >= MIN_VALIDATION_COVERAGE
            else "REJECTED_ON_HELD_OUT_RETAINED_TEST"
        ),
        "dataset": {
            "total_retained_rows": len(eligible) + len(failures),
            "run_failure_rows": len(failures),
            "eligible_rows": len(eligible),
            "split_counts": {split: len(rows) for split, rows in by_split.items()},
            "split_group_counts": {split: len(group_sets[split]) for split in by_split},
            "group_overlap": overlaps,
            "eligible_no_trace_output": sum(
                row["prediction_time_features"]["no_trace_output"] for row in eligible
            ),
            "eligible_no_parsed_trace_calls": sum(
                row["prediction_time_features"]["no_parsed_trace_calls"] for row in eligible
            ),
            "eligible_no_selector": sum(
                not row["prediction_time_features"]["selector_available"] for row in eligible
            ),
        },
        "baseline": {
            "policy": "always_return_retained_ranked_predictions",
            "evaluation_rows": len(eligible),
            "metrics_by_split": {
                split: aggregate_metrics(rows, None) for split, rows in by_split.items()
            },
        },
        "score_configuration": {
            "weights": SCORE_WEIGHTS,
            "features": sorted(SCORE_WEIGHTS),
            "random_seed": RANDOM_SEED,
            "min_validation_coverage": MIN_VALIDATION_COVERAGE,
            "threshold_candidates_source": "validation rows only",
        },
        "threshold_selection": selected,
        "evaluation": {
            split: {
                "baseline": aggregate_metrics(by_split[split], None),
                "selective": aggregate_metrics(by_split[split], threshold),
            }
            for split in ("train", "validation")
        },
        "test_evaluation": {
            "baseline": test_baseline,
            "selective": test_selective,
            "removed_counts": test_removed,
            "bootstrap": test_bootstrap,
        },
        "threshold_curve": threshold_curve(development, by_split["test"]),
        "input_manifest": input_manifest(),
        "provenance": {
            "ranker": "retained provider-pinned raw prediction ordering/current scorer evaluation",
            "trace_parser": "faultseeker.function_analysis.candidate_generation.parse_saved_trace_candidates",
            "labels_used_only_for": ["evaluation", "target-contract grouped split assignment"],
            "labels_not_used_for": ["prediction-time features", "score weights", "threshold candidates"],
        },
    }
    # Keep the public evaluation shape compact and stable while retaining the
    # richer per-split values in the JSON artifact.
    result["evaluation"]["test"] = result.pop("test_evaluation")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / "metrics.json", result)
    write_json(OUTPUT_DIR / "config.json", {
        "experiment_version": EXPERIMENT_VERSION,
        "score_weights": SCORE_WEIGHTS,
        "split_salt": SPLIT_SALT,
        "random_seed": RANDOM_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "minimum_validation_coverage": MIN_VALIDATION_COVERAGE,
        "prohibited_inputs": ["Batch B", "Batch C", "Batch D", "Batch E"],
    })
    write_json(OUTPUT_DIR / "input_manifest.json", result["input_manifest"])
    write_jsonl(OUTPUT_DIR / "per_example.jsonl", sorted(eligible, key=lambda row: row["txn_hash"]))
    write_jsonl(OUTPUT_DIR / "run_failures.jsonl", failures)
    write_jsonl(
        OUTPUT_DIR / "failure_cases.jsonl",
        [
            row
            for row in sorted(eligible, key=lambda item: item["txn_hash"])
            if row["split"] == "test" and row["abstained_at_selected_threshold"]
        ],
    )
    write_report(result)
    print(json.dumps({
        "verdict": result["verdict"],
        "eligible": len(eligible),
        "run_failures": len(failures),
        "split_counts": result["dataset"]["split_counts"],
        "threshold": threshold,
        "test_baseline": test_baseline,
        "test_selective": test_selective,
        "removed_counts": test_removed,
        "output_dir": OUTPUT_DIR.relative_to(ROOT).as_posix(),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
