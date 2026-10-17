"""Offline, holdout-excluding diagnosis of saved Top-5 localization misses."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import _norm_addr, _norm_fn, _prediction_keys


RUN = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017"
MANIFEST = RUN / "manifest.json"
GROUND_TRUTH = ROOT / "benchmark/original_faultseeker/ground_truth"
HOLDOUT = ROOT / "reports/original_benchmark/ranker_upgrade/holdout_20261017.json"
OUTPUT = ROOT / "reports/original_benchmark/ranker_upgrade/dev_miss_analysis_20261017.json"


def _target(path: Path) -> tuple[set[tuple[str, str]], set[str], str]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    functions: set[tuple[str, str]] = set()
    names: set[str] = set()
    for key, values in (data.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parts = str(entry).split("#")
            if len(parts) < 3:
                continue
            member = parts[-1].strip()
            if ":" in member and member.split(":")[0].isdigit():
                continue
            address = _norm_addr(parts[0])
            function = _norm_fn(member)
            if address and function and function != ":":
                functions.add((address, function))
                names.add(function)
    return functions, names, str(data.get("name") or "")


def _prediction_function(prediction: dict) -> str:
    fn_key, _ = _prediction_keys(prediction)
    return fn_key[1] if fn_key else ""


def _function_only_rank(names: set[str], predictions: list[dict]) -> int | None:
    for index, prediction in enumerate(predictions, start=1):
        if _prediction_function(prediction) in names:
            return index
    return None


def _primary_rank(target: set[tuple[str, str]], predictions: list[dict]) -> int | None:
    for index, prediction in enumerate(predictions, start=1):
        fn_key, _ = _prediction_keys(prediction)
        if fn_key in target:
            return index
    return None


def _trace_text(row: dict) -> str:
    cast = row.get("cast") or {}
    return str(cast.get("output_tail") or "").lower()


def classify(row: dict) -> dict:
    gt_path = GROUND_TRUTH / f"{row['txn_hash']}.json"
    target, names, incident = _target(gt_path)
    predictions = list(row.get("predictions") or [])
    primary_rank = _primary_rank(target, predictions)
    function_rank = _function_only_rank(names, predictions)
    target_addresses = {address for address, _ in target}
    address_candidate_rank = next(
        (
            index
            for index, prediction in enumerate(predictions, start=1)
            if _norm_addr(prediction.get("code_address") or prediction.get("address")) in target_addresses
        ),
        None,
    )
    matched_prediction = next(
        (
            {
                "rank": prediction.get("rank"),
                "address": prediction.get("code_address"),
                "function": prediction.get("function"),
                "count": prediction.get("count"),
                "supporting_call_depths": prediction.get("supporting_call_depths"),
            }
            for prediction in predictions
            if _prediction_function(prediction) in names
        ),
        None,
    )
    text = _trace_text(row)
    trace_name_evidence = sorted(name for name in names if len(name) > 2 and name in text)
    if (
        (function_rank is not None and function_rank <= 5 and (primary_rank is None or primary_rank > 5))
        or (address_candidate_rank is not None and function_rank is None)
    ):
        cause = "label/selector mismatch"
        evidence = (
            "function-only Top-5 hit but primary address+function did not hit"
            if function_rank is not None
            else "target address candidate exists but its function label did not match"
        )
    elif function_rank is not None:
        cause = "produced but ranked low"
        evidence = f"function candidate first appears at rank {function_rank}"
    elif trace_name_evidence:
        cause = "candidate never produced"
        evidence = "target function text retained in cast output tail but absent from predictions"
    else:
        cause = "trace too shallow"
        evidence = "no target function text retained in cast output tail or predictions"
    return {
        "txn_hash": row["txn_hash"],
        "chain": row["chain"],
        "incident": incident,
        "cause": cause,
        "primary_rank": primary_rank,
        "function_only_rank": function_rank,
        "address_candidate_rank": address_candidate_rank,
        "matched_prediction": matched_prediction,
        "target_functions": sorted(target),
        "top5": [
            {"rank": p.get("rank"), "address": p.get("code_address"), "function": p.get("function"), "selector": p.get("selector")}
            for p in predictions[:5]
        ],
        "trace_name_evidence": trace_name_evidence,
        "evidence": evidence,
    }


def run() -> dict:
    holdout = set(json.loads(HOLDOUT.read_text(encoding="utf-8"))["transaction_ids"])
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = [row for row in manifest["rows"] if row.get("status") == "ok"]
    development = [row for row in rows if row["txn_hash"] not in holdout]
    assert len(development) == 90, len(development)
    misses = [row for row in development if not row["score"].get("recall_at_5")]
    classified = [classify(row) for row in misses]
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in classified:
        groups[item["cause"]].append(item)
    result = {
        "scope": "offline saved provider-pinned rows only",
        "holdout_excluded": True,
        "development_rows": len(development),
        "development_top5_misses": len(misses),
        "cause_counts": dict(sorted((key, len(value)) for key, value in groups.items())),
        "classification_rule": {
            "label_selector_mismatch": "function-only rank <= 5 while primary address+function rank is absent",
            "produced_but_ranked_low": "function-only candidate exists but first appears after rank 5",
            "candidate_never_produced": "target function text is retained in cast output tail but absent from predictions",
            "trace_too_shallow": "target function text is absent from retained cast output tail and predictions",
        },
        "examples": {key: value[:5] for key, value in sorted(groups.items())},
        "all_development_classifications": classified,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "development_rows": result["development_rows"],
        "development_top5_misses": result["development_top5_misses"],
        "cause_counts": result["cause_counts"],
    }, indent=2))
    for cause, examples in sorted(result["examples"].items()):
        print(f"\nCAUSE: {cause} ({len(groups[cause])} total; showing {len(examples)})")
        for item in examples:
            print(json.dumps({
                "txn_hash": item["txn_hash"],
                "chain": item["chain"],
                "incident": item["incident"],
                "primary_rank": item["primary_rank"],
                "function_only_rank": item["function_only_rank"],
                "target_functions": item["target_functions"],
                "top5": item["top5"],
                "evidence": item["evidence"],
            }, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
