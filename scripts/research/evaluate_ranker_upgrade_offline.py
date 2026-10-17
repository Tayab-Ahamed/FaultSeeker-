"""Offline before/after evaluation of the two general ranker upgrades."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import (
    _norm_fn,
    _prediction_keys,
    load_ground_truth,
    rank_of_first_hit,
)
from faultseeker.function_analysis.function_ranker import rerank_saved_predictions


RUN = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017"
HOLDOUT = ROOT / "reports/original_benchmark/ranker_upgrade/holdout_20261017.json"
OUTPUT = ROOT / "reports/original_benchmark/ranker_upgrade/dev_rerank_comparison_20261017.json"


def _function_only_rank(target_names: set[str], predictions: list[dict]) -> int | None:
    for index, prediction in enumerate(predictions, start=1):
        fn_key, _ = _prediction_keys(prediction)
        if fn_key and _norm_fn(fn_key[1]) in target_names:
            return index
    return None


def _metrics(rows: list[dict], predictions_by_tx: dict[str, list[dict]], targets: dict) -> dict:
    output = {}
    for metric, rank_fn in {
        "primary_address_function": lambda target, predictions: rank_of_first_hit(target, predictions, match="function"),
        "function_only_sensitivity": lambda target, predictions: _function_only_rank(
            {fn for _, fn in target.functions}, predictions
        ),
    }.items():
        ranks = [rank_fn(targets[row["txn_hash"]], predictions_by_tx[row["txn_hash"]]) for row in rows]
        output[metric] = {
            "n": len(ranks),
            "hits_at_1": sum(rank is not None and rank <= 1 for rank in ranks),
            "hits_at_3": sum(rank is not None and rank <= 3 for rank in ranks),
            "hits_at_5": sum(rank is not None and rank <= 5 for rank in ranks),
        }
        output[metric]["recall_at_1"] = output[metric]["hits_at_1"] / len(ranks) if ranks else 0.0
        output[metric]["recall_at_3"] = output[metric]["hits_at_3"] / len(ranks) if ranks else 0.0
        output[metric]["recall_at_5"] = output[metric]["hits_at_5"] / len(ranks) if ranks else 0.0
    return output


def run() -> dict:
    holdout = set(json.loads(HOLDOUT.read_text(encoding="utf-8"))["transaction_ids"])
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    rows = [row for row in manifest["rows"] if row.get("status") == "ok" and row["txn_hash"] not in holdout]
    assert len(rows) == 90, len(rows)
    targets = {target.txn_hash: target for target in load_ground_truth(str(ROOT / "benchmark/original_faultseeker/ground_truth"))}
    assert all(row["txn_hash"] in targets for row in rows)
    before = {row["txn_hash"]: list(row.get("predictions") or []) for row in rows}
    after = {txn: rerank_saved_predictions(predictions) for txn, predictions in before.items()}
    result = {
        "scope": "offline saved provider-pinned predictions; 20 holdout IDs excluded",
        "holdout_excluded": True,
        "development_rows": len(rows),
        "before": _metrics(rows, before, targets),
        "after": _metrics(rows, after, targets),
        "changed_prediction_rows": sum(before[txn] != after[txn] for txn in before),
        "upgrade_methods": [
            "canonicalize renderer-only value annotations and merge candidates by address plus canonical call label",
            "use maximum supporting call depth as a deterministic tie-break after candidate count",
        ],
        "synthetic": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
