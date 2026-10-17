"""One-shot frozen holdout evaluation for the ranker upgrade."""
from __future__ import annotations

import hashlib
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
OUTPUT = ROOT / "reports/original_benchmark/ranker_upgrade/holdout_new_measurement_20261017.json"
RANKER = ROOT / "faultseeker/function_analysis/function_ranker.py"


def _function_only_rank(target_names: set[str], predictions: list[dict]) -> int | None:
    for index, prediction in enumerate(predictions, start=1):
        fn_key, _ = _prediction_keys(prediction)
        if fn_key and _norm_fn(fn_key[1]) in target_names:
            return index
    return None


def _metric(rows: list[dict], targets: dict) -> dict:
    results = {}
    for name in ("primary_address_function", "function_only_sensitivity"):
        ranks = []
        for row in rows:
            predictions = rerank_saved_predictions(row.get("predictions") or [])
            target = targets[row["txn_hash"]]
            if name == "primary_address_function":
                rank = rank_of_first_hit(target, predictions, match="function")
            else:
                rank = _function_only_rank({fn for _, fn in target.functions}, predictions)
            ranks.append(rank)
        results[name] = {
            "n": len(ranks),
            "hits_at_1": sum(rank is not None and rank <= 1 for rank in ranks),
            "hits_at_3": sum(rank is not None and rank <= 3 for rank in ranks),
            "hits_at_5": sum(rank is not None and rank <= 5 for rank in ranks),
        }
        for k in (1, 3, 5):
            results[name][f"recall_at_{k}"] = results[name][f"hits_at_{k}"] / len(ranks) if ranks else 0.0
    return results


def run() -> dict:
    if OUTPUT.exists():
        raise SystemExit(f"one-shot output already exists: {OUTPUT}")
    holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    holdout_ids = set(holdout["transaction_ids"])
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    rows = [row for row in manifest["rows"] if row.get("status") == "ok" and row["txn_hash"] in holdout_ids]
    if len(rows) != 20 or {row["txn_hash"] for row in rows} != holdout_ids:
        raise SystemExit("frozen holdout population mismatch")
    targets = {target.txn_hash: target for target in load_ground_truth(str(ROOT / "benchmark/original_faultseeker/ground_truth"))}
    result = {
        "label": "new measurement",
        "scope": "one-shot frozen 20-transaction holdout",
        "holdout_manifest": str(HOLDOUT.relative_to(ROOT)).replace("\\", "/"),
        "holdout_id_list_sha256": holdout["id_list_sha256"],
        "seed": holdout["seed"],
        "n": len(rows),
        "ranker_sha256": hashlib.sha256(RANKER.read_bytes()).hexdigest(),
        "metrics": _metric(rows, targets),
        "retuning_after_holdout": False,
        "network_calls": False,
        "synthetic": False,
        "interpretation": "Exploratory only: all 110 source rows were inspected earlier; this is not a clean generalization claim.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
