"""Compare the pre-fix and corrected prediction serializers on saved inputs.

This is an adapter-validation experiment, not a new ranker run.  It reads the
already-frozen Batch D candidate JSON files, reconstructs the minimal
``RankingResult`` shape used by the old adapter, and compares that output with
the current serializer.  It never reads ground-truth locations, reruns a
ranker, contacts an RPC/provider, or writes into the frozen batch directory.

The old adapter is reproduced locally so the comparison is byte/input-bound:
it split the ``function_address`` key at every underscore and discarded the
ranker's explicit identity metadata.  The corrected adapter preserves the
saved ``code_address``/``function`` values and rank metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.generate_pipeline_predictions import serialize_ranked_candidates
from benchmark.honest_eval.localization import load_ground_truth, rank_of_first_hit


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_serializer(ranking_result) -> list[dict]:
    """Exact pre-fix adapter behavior from before e47c4c3."""
    candidates = []
    for fn_key, fn_info in ranking_result.functions_to_be_inspected.items():
        parts = fn_key.split("_")
        fn_name = parts[0] if parts else ""
        address = parts[1] if len(parts) > 1 else ""
        candidates.append(
            {
                "address": address,
                "function": fn_name,
                "call_type": "call",
                "depth": 1,
                "_score": 0.95 if fn_name != "others" else 0.5,
            }
        )
    return candidates


def ranking_from_saved_predictions(predictions: list[dict]):
    functions = {}
    ranked = []
    for prediction in predictions:
        address = str(prediction.get("code_address") or prediction.get("address") or "")
        function = str(
            prediction.get("function")
            or prediction.get("function_name")
            or prediction.get("name")
            or ""
        )
        key = f"{function}_{address}"
        depths = prediction.get("supporting_call_depths") or []
        functions[key] = {
            "calls": [{"depth": max(item) if isinstance(item, list) and item else 0} for item in depths]
        }
        ranked.append(dict(prediction))
    return SimpleNamespace(functions_to_be_inspected=functions, ranked_functions=ranked)


def compare(
    candidate_dir: Path,
    candidate_file: Path | None = None,
    ground_truth_dir: Path | None = None,
) -> dict:
    files = [candidate_file] if candidate_file else sorted(candidate_dir.glob("*.json"))
    targets = {}
    if ground_truth_dir:
        targets = {target.txn_hash.lower(): target for target in load_ground_truth(str(ground_truth_dir))}
    rows = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        predictions = payload.get("predictions") or []
        ranking = ranking_from_saved_predictions(predictions)
        old = old_serializer(ranking)
        new = serialize_ranked_candidates(ranking)

        expected = [
            (
                str(item.get("code_address") or item.get("address") or "").lower(),
                str(item.get("function") or item.get("function_name") or ""),
            )
            for item in predictions
        ]
        old_keys = [(item["address"].lower(), item["function"]) for item in old]
        new_keys = [(item["address"].lower(), item["function"]) for item in new]
        txn_hash = str(payload.get("case_id") or payload.get("transaction_hash") or path.stem).lower()
        target = targets.get(txn_hash)
        old_rank = rank_of_first_hit(target, old, match="function") if target else None
        new_rank = rank_of_first_hit(target, new, match="function") if target else None
        rows.append(
            {
                "path": path.as_posix(),
                "sha256": sha256(path),
                "candidate_count": len(predictions),
                "old_exact_identity_count": sum(a == b for a, b in zip(old_keys, expected)),
                "new_exact_identity_count": sum(a == b for a, b in zip(new_keys, expected)),
                "changed_positions": sum(a != b for a, b in zip(old_keys, new_keys)),
                "transaction_hash": txn_hash,
                "ground_truth_available": target is not None,
                "old_function_hit_rank": old_rank,
                "new_function_hit_rank": new_rank,
                "old_first_candidate": old[0] if old else None,
                "new_first_candidate": new[0] if new else None,
            }
        )

    evaluated = [row for row in rows if row["ground_truth_available"]]

    def metric(rows_for_metric, rank_key, k):
        return sum(row[rank_key] is not None and row[rank_key] <= k for row in rows_for_metric)

    return {
        "schema_version": 1,
        "experiment": "localization_serializer_before_after",
        "code_revision": "e47c4c3",
        "input_scope": "read-only saved candidate JSON; no ranker or scorer execution",
        "ground_truth_used": ground_truth_dir is not None,
        "external_calls": 0,
        "frozen_batch_modified": False,
        "performance_metrics": {
            "status": "MEASURED_ON_SAVED_OUTPUTS" if evaluated else "NOT_IDENTIFIABLE_FROM_ADAPTER_FIX_ALONE",
            "reason": "This compares serializers on saved ranked outputs; it does not rerun the ranker or claim a new generalization experiment.",
            "top_k_denominator": len(evaluated) if evaluated else None,
            "old_hits_at_1": metric(evaluated, "old_function_hit_rank", 1) if evaluated else None,
            "old_hits_at_3": metric(evaluated, "old_function_hit_rank", 3) if evaluated else None,
            "old_hits_at_5": metric(evaluated, "old_function_hit_rank", 5) if evaluated else None,
            "new_hits_at_1": metric(evaluated, "new_function_hit_rank", 1) if evaluated else None,
            "new_hits_at_3": metric(evaluated, "new_function_hit_rank", 3) if evaluated else None,
            "new_hits_at_5": metric(evaluated, "new_function_hit_rank", 5) if evaluated else None,
        },
        "summary": {
            "files": len(rows),
            "candidates": sum(row["candidate_count"] for row in rows),
            "old_exact_identity_count": sum(row["old_exact_identity_count"] for row in rows),
            "new_exact_identity_count": sum(row["new_exact_identity_count"] for row in rows),
            "changed_positions": sum(row["changed_positions"] for row in rows),
            "rows_with_changed_positions": sum(bool(row["changed_positions"]) for row in rows),
            "ground_truth_rows": len(evaluated),
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("reports/new_batches/batchD/phase2/candidates"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/reproducibility/LOCALIZATION_SERIALIZER_COMPARISON.json"),
    )
    parser.add_argument("--candidate-file", type=Path, default=None)
    parser.add_argument("--ground-truth-dir", type=Path, default=None)
    args = parser.parse_args()
    result = compare(args.candidate_dir, args.candidate_file, args.ground_truth_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
