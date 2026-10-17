"""Offline audit of current versus reconstructed original-definition hits.

This script reads only saved provider-pinned rows and imported ground-truth
labels. It never imports the RPC runner, invokes cast, or executes a trace.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RAW_DIR = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
GT_DIR = ROOT / "benchmark/original_faultseeker/ground_truth"

from benchmark.honest_eval.localization import (
    LocalizationTarget,
    _parse_location_entry,
    _prediction_keys,
    _register_fn_names,
    rank_of_first_hit,
)


def load_valid_rows() -> list[tuple[str, dict[str, Any], LocalizationTarget, set[str]]]:
    rows = []
    for raw_path in sorted(RAW_DIR.glob("*.json")):
        row = json.loads(raw_path.read_text(encoding="utf-8"))
        if row.get("status") != "ok":
            continue
        gt = json.loads((GT_DIR / f"{raw_path.stem}.json").read_text(encoding="utf-8-sig"))
        target = LocalizationTarget(txn_hash=raw_path.stem)
        function_names: list[str] = []
        labels: list[str] = []
        for key, values in (gt.get("location") or {}).items():
            for entry in [key] + list(values or []):
                parsed = _parse_location_entry(entry)
                if not parsed:
                    continue
                address, member, is_line = parsed
                labels.append(entry)
                if not is_line:
                    target.functions.add((address, member))
                    function_names.append(member)
        _register_fn_names(function_names)
        rows.append((raw_path.stem, row, target, set(labels)))
    if len(rows) != 110:
        raise ValueError(f"expected 110 valid saved rows, found {len(rows)}")
    return rows


def current_hit(target: LocalizationTarget, predictions: list[dict[str, Any]], k: int) -> bool:
    return rank_of_first_hit(target, predictions[:k], match="function") is not None


def raw_function(prediction: dict[str, Any]) -> str:
    return str(
        prediction.get("function_name")
        or prediction.get("name")
        or prediction.get("function")
        or ""
    ).strip().split("(")[0].lower()


def original_function_only_hit(
    target: LocalizationTarget,
    predictions: list[dict[str, Any]],
    k: int,
) -> bool:
    """Evidence-bounded original reconstruction: function identity only.

    The paper calls the output a ranked list of vulnerable functions, while
    the labels carry address#contract#function. The pinned authors tree does
    not contain a scoring routine. This conservative reconstruction therefore
    ignores the descriptive contract/address fields but does not resolve a
    selector into a human name.
    """
    expected = {function for _address, function in target.functions}
    return any(raw_function(prediction) in expected for prediction in predictions[:k])


def address_aware_without_selector_resolution(
    target: LocalizationTarget,
    predictions: list[dict[str, Any]],
    k: int,
) -> bool:
    expected = target.functions
    for prediction in predictions[:k]:
        address = str(prediction.get("code_address") or "").strip().lower()
        function = raw_function(prediction)
        if address and function and (address, function) in expected:
            return True
    return False


def function_only_with_current_selector_resolution(
    target: LocalizationTarget,
    predictions: list[dict[str, Any]],
    k: int,
) -> bool:
    expected = {function for _address, function in target.functions}
    for prediction in predictions[:k]:
        function_key, _line_key = _prediction_keys(prediction)
        if function_key and function_key[1] in expected:
            return True
    return False


def metrics(rows: list[tuple[str, dict[str, Any], LocalizationTarget, set[str]]], rule) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k in (1, 3, 5):
        hits = sum(rule(target, row.get("predictions", []), k) for _tx, row, target, _labels in rows)
        result[f"recall_at_{k}"] = hits / len(rows)
        result[f"hits_at_{k}"] = hits
    return result


def flips(rows, left_rule, right_rule, k: int = 5) -> dict[str, Any]:
    miss_to_hit = []
    hit_to_miss = []
    for tx, row, target, labels in rows:
        left = left_rule(target, row.get("predictions", []), k)
        right = right_rule(target, row.get("predictions", []), k)
        if not left and right:
            miss_to_hit.append((tx, row, target, labels))
        elif left and not right:
            hit_to_miss.append((tx, row, target, labels))
    return {
        "miss_to_hit_count": len(miss_to_hit),
        "hit_to_miss_count": len(hit_to_miss),
        "miss_to_hit": [example(item) for item in miss_to_hit],
        "hit_to_miss": [example(item) for item in hit_to_miss],
    }


def example(item) -> dict[str, Any]:
    tx, row, target, labels = item
    candidates = []
    for prediction in row.get("predictions", [])[:5]:
        candidates.append({
            key: prediction.get(key)
            for key in ("rank", "code_address", "function", "selector")
            if key in prediction
        })
    return {
        "txn_hash": tx,
        "chain": row.get("chain"),
        "replay_mismatch": bool(row.get("replay_mismatch")),
        "ground_truth_labels": sorted(labels),
        "top5_candidates": candidates,
    }


def main() -> int:
    rows = load_valid_rows()
    current = lambda target, predictions, k: current_hit(target, predictions, k)
    original = lambda target, predictions, k: original_function_only_hit(target, predictions, k)
    no_selector = lambda target, predictions, k: address_aware_without_selector_resolution(target, predictions, k)
    function_only_resolved = lambda target, predictions, k: function_only_with_current_selector_resolution(target, predictions, k)

    output = {
        "scope": {"valid_saved_rows": len(rows), "rpc": False, "cast": False, "rerun": False},
        "current_rule": metrics(rows, current),
        "original_definition_reconstruction": metrics(rows, original),
        "differences": {
            "address_requirement": flips(rows, current, function_only_resolved),
            "selector_name_resolution": flips(rows, current, no_selector),
            "combined_current_vs_original_reconstruction": flips(rows, current, original),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
