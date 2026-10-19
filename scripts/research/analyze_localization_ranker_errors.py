"""Analyze saved provider-pinned localization misses without reranking."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import load_ground_truth, rank_of_first_hit


RAW = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
GROUND_TRUTH = ROOT / "benchmark/original_faultseeker/ground_truth"
CLASSIFICATION = ROOT / "benchmark/original_faultseeker/benchmark_classification.csv"
OUTPUT = ROOT / "reports/reproducibility/LOCALIZATION_RANKER_ERROR_ANALYSIS.json"


def main() -> int:
    targets = {target.txn_hash.lower(): target for target in load_ground_truth(str(GROUND_TRUTH))}
    with CLASSIFICATION.open(encoding="utf-8-sig", newline="") as handle:
        labels = {row["txn_hash"].lower(): row for row in csv.DictReader(handle)}

    rows = []
    for path in sorted(RAW.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        txn = str(payload.get("case_id") or path.stem).lower()
        target = targets.get(txn)
        if not target:
            continue
        predictions = payload.get("predictions") or []
        rank = rank_of_first_hit(target, predictions, match="function")
        target_addresses = {address.lower() for address, _ in target.functions}
        target_functions = {(address.lower(), function.lower()) for address, function in target.functions}
        candidate_addresses = {
            str(item.get("code_address") or item.get("address") or "").lower()
            for item in predictions
        }
        candidate_functions = {
            (
                str(item.get("code_address") or item.get("address") or "").lower(),
                str(item.get("function_name") or item.get("function") or item.get("name") or "").lower(),
            )
            for item in predictions
        }
        if rank is None:
            if not target_addresses & candidate_addresses:
                cause = "target_address_absent"
            elif not target_functions & candidate_functions:
                cause = "target_address_present_function_identity_absent"
            else:
                cause = "target_pair_ranked_below_available_top_k"
        else:
            cause = "hit"
        rows.append(
            {
                "transaction_hash": txn,
                "chain": payload.get("chain") or labels.get(txn, {}).get("chain"),
                "vulnerability_type": labels.get(txn, {}).get("vuln_type"),
                "candidate_count": len(predictions),
                "function_rank": rank,
                "target_addresses": sorted(target_addresses),
                "target_functions": sorted(target_functions),
                "cause": cause,
            }
        )

    evaluated = [row for row in rows]
    misses = [row for row in rows if row["cause"] != "hit"]
    report = {
        "schema_version": 1,
        "status": "SAVED_RANKER_ERROR_ANALYSIS_ONLY",
        "input_scope": "read-only provider-pinned raw predictions and original function-level ground truth",
        "ranker_executed": False,
        "external_calls": 0,
        "evaluated": len(evaluated),
        "top_k": {
            f"top_{k}": sum(row["function_rank"] is not None and row["function_rank"] <= k for row in evaluated)
            for k in (1, 3, 5)
        },
        "miss_count": len(misses),
        "misses_by_cause": Counter(row["cause"] for row in misses),
        "misses_by_chain": Counter(row["chain"] for row in misses),
        "misses_by_vulnerability": Counter(row["vulnerability_type"] for row in misses),
        "rows": evaluated,
        "original_246_row_claim": "not evaluated; saved 115-row localization analysis only",
    }
    # Counters are converted for JSON serialization.
    for key in ("misses_by_cause", "misses_by_chain", "misses_by_vulnerability"):
        report[key] = dict(report[key])
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evaluated": len(evaluated), "top_k": report["top_k"], "misses_by_cause": report["misses_by_cause"]}, sort_keys=True))
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
