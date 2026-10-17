"""Offline one-at-a-time scoring-signal trials on the 90-row development set."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import _norm_fn, _prediction_keys, load_ground_truth, rank_of_first_hit
from faultseeker.function_analysis.function_ranker import rerank_saved_predictions


RUN = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017"
HOLDOUT = ROOT / "reports/original_benchmark/ranker_upgrade/holdout_20261017.json"
OUTPUT = ROOT / "reports/original_benchmark/ranker_upgrade/round2_signal_trials_20261017.json"


def _max_depth(item: dict) -> int:
    return max((len(depth) for depth in item.get("supporting_call_depths", []) if isinstance(depth, list)), default=0)


def _depth_span(item: dict) -> int:
    depths = [len(depth) for depth in item.get("supporting_call_depths", []) if isinstance(depth, list)]
    return max(depths, default=0) - min(depths, default=0)


def _variant(predictions: list[dict], signal: str) -> list[dict]:
    current = rerank_saved_predictions(predictions)
    indexed = list(enumerate(current))
    if signal == "current_count_then_max_depth":
        return current
    if signal == "max_depth_then_count":
        key = lambda pair: (-_max_depth(pair[1]), -int(pair[1].get("count") or 0), pair[0])
    elif signal == "depth_span_then_count":
        key = lambda pair: (-_depth_span(pair[1]), -int(pair[1].get("count") or 0), pair[0])
    elif signal == "count_then_depth_span":
        key = lambda pair: (-int(pair[1].get("count") or 0), -_depth_span(pair[1]), pair[0])
    elif signal == "frequency_only":
        key = lambda pair: (-int(pair[1].get("count") or 0), pair[0])
    else:
        raise ValueError(signal)
    ordered = [item for _, item in sorted(indexed, key=key)]
    for rank, item in enumerate(ordered, start=1):
        item["rank"] = rank
        item["tie_policy"] = signal
    return ordered


def _function_only_rank(target_names: set[str], predictions: list[dict]) -> int | None:
    for index, prediction in enumerate(predictions, start=1):
        fn_key, _ = _prediction_keys(prediction)
        if fn_key and _norm_fn(fn_key[1]) in target_names:
            return index
    return None


def _metrics(rows: list[dict], targets: dict, signal: str) -> dict:
    ranks = {"primary": [], "function_only": []}
    for row in rows:
        predictions = _variant(row.get("predictions") or [], signal)
        target = targets[row["txn_hash"]]
        ranks["primary"].append(rank_of_first_hit(target, predictions, match="function"))
        ranks["function_only"].append(_function_only_rank({fn for _, fn in target.functions}, predictions))
    result = {}
    for metric, values in ranks.items():
        result[metric] = {f"hits_at_{k}": sum(rank is not None and rank <= k for rank in values) for k in (1, 3, 5)}
        result[metric]["n"] = len(values)
        for k in (1, 3, 5):
            result[metric][f"recall_at_{k}"] = result[metric][f"hits_at_{k}"] / len(values)
    return result


def run() -> dict:
    holdout_ids = set(json.loads(HOLDOUT.read_text(encoding="utf-8"))["transaction_ids"])
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    rows = [row for row in manifest["rows"] if row.get("status") == "ok" and row["txn_hash"] not in holdout_ids]
    assert len(rows) == 90, len(rows)
    targets = {target.txn_hash: target for target in load_ground_truth(str(ROOT / "benchmark/original_faultseeker/ground_truth"))}
    signals = ["current_count_then_max_depth", "max_depth_then_count", "depth_span_then_count", "count_then_depth_span", "frequency_only"]
    metrics = {signal: _metrics(rows, targets, signal) for signal in signals}
    prediction_keys = sorted({key for row in rows for prediction in row.get("predictions") or [] for key in prediction})
    result = {
        "label": "development, exploratory",
        "scope": "offline one-at-a-time scoring-signal trials on 90 development rows",
        "holdout_excluded": True,
        "development_rows": len(rows),
        "signals": metrics,
        "available_prediction_fields": prediction_keys,
        "storage_write_signal_available": any("storage" in key.lower() or "sstore" in key.lower() for key in prediction_keys),
        "value_flow_signal_available": any("value" in key.lower() or "flow" in key.lower() for key in prediction_keys),
        "trial_decision": {
            "max_depth_then_count": "DROP unless it improves the current primary development Recall@5",
            "depth_span_then_count": "DROP unless it improves the current primary development Recall@5",
            "count_then_depth_span": "DROP unless it improves the current primary development Recall@5",
            "frequency_only": "DROP if it is not better than the current count-plus-depth ordering",
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
