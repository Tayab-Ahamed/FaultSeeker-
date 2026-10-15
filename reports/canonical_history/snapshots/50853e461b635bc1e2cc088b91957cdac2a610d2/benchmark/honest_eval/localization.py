"""Fault-localization evaluation against the curated ground-truth corpus.

Each file in ``benchmark/ground_truth/*.json`` contains a ``location`` map of
the form::

    "location": {
      "0xd286...#StaxLPStaking.sol#241:3": [
        "0xd286...#StaxLPStaking#migrateStake",
        "0xd286...#StaxLPStaking#241:3"
      ]
    }

This gives genuine contract/function/line targets, enabling Top-k accuracy and
MRR -- the metrics that actually match the paper's localization thesis.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GROUND_TRUTH_DIR = os.path.join(ROOT, "benchmark", "ground_truth")


@dataclass
class LocalizationTarget:
    """Normalized ground-truth targets for one transaction."""

    txn_hash: str
    name: str = ""
    functions: Set[Tuple[str, str]] = field(default_factory=set)
    lines: Set[Tuple[str, str]] = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not self.functions and not self.lines


def _norm_addr(value: str) -> str:
    return str(value or "").strip().lower()


def _norm_fn(value: str) -> str:
    return str(value or "").strip().lower().split("(")[0]


def _parse_location_entry(entry: str) -> Optional[Tuple[str, str, bool]]:
    """Parse ``address#Contract#member`` -> (address, member, is_line)."""
    parts = [p for p in str(entry or "").split("#")]
    if len(parts) < 3:
        return None
    address = _norm_addr(parts[0])
    member = parts[-1].strip()
    if not address or not member:
        return None
    is_line = ":" in member and member.split(":")[0].strip().isdigit()
    if is_line:
        return (address, member.split(":")[0].strip(), True)
    return (address, _norm_fn(member), False)


def load_ground_truth(directory: str = GROUND_TRUTH_DIR) -> List[LocalizationTarget]:
    targets: List[LocalizationTarget] = []
    if not os.path.isdir(directory):
        return targets
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        hashes = data.get("transaction_hash") or []
        if isinstance(hashes, str):
            hashes = [hashes]
        txn = _norm_addr(hashes[0]) if hashes else _norm_addr(filename[:-5])
        target = LocalizationTarget(txn_hash=txn, name=str(data.get("name") or ""))
        location = data.get("location") or {}
        if isinstance(location, dict):
            for key, values in location.items():
                for entry in [key] + list(values or []):
                    parsed = _parse_location_entry(entry)
                    if not parsed:
                        continue
                    address, member, is_line = parsed
                    if is_line:
                        target.lines.add((address, member))
                    else:
                        target.functions.add((address, member))
        if not target.is_empty:
            targets.append(target)
    return targets


def _prediction_keys(prediction: Dict[str, Any]) -> Tuple[Optional[Tuple[str, str]], Optional[Tuple[str, str]]]:
    address = _norm_addr(
        prediction.get("address")
        or prediction.get("contract")
        or prediction.get("callee")
        or ""
    )
    function = _norm_fn(
        prediction.get("function")
        or prediction.get("function_name")
        or prediction.get("name")
        or ""
    )
    line = prediction.get("line") or prediction.get("line_number")
    fn_key = (address, function) if address and function else None
    line_key = (address, str(line).strip()) if address and line not in (None, "") else None
    return fn_key, line_key


def rank_of_first_hit(
    target: LocalizationTarget,
    predictions: Sequence[Dict[str, Any]],
    match: str = "function",
) -> Optional[int]:
    """1-based rank of the first correct prediction, or ``None`` if absent."""
    for index, prediction in enumerate(predictions, start=1):
        fn_key, line_key = _prediction_keys(prediction)
        if match in ("function", "either") and fn_key and fn_key in target.functions:
            return index
        if match in ("line", "either") and line_key and line_key in target.lines:
            return index
    return None


def localization_metrics(
    targets: Iterable[LocalizationTarget],
    predictions_by_tx: Dict[str, Sequence[Dict[str, Any]]],
    ks: Sequence[int] = (1, 3, 5, 10),
    match: str = "function",
) -> Dict[str, Any]:
    """Top-k accuracy and MRR over transactions that have predictions."""
    targets = list(targets)
    evaluated = 0
    missing_predictions = 0
    reciprocal_total = 0.0
    hits = {k: 0 for k in ks}

    for target in targets:
        predictions = predictions_by_tx.get(target.txn_hash)
        if predictions is None:
            missing_predictions += 1
            continue
        evaluated += 1
        rank = rank_of_first_hit(target, predictions, match=match)
        if rank is not None:
            reciprocal_total += 1.0 / rank
            for k in ks:
                if rank <= k:
                    hits[k] += 1

    result: Dict[str, Any] = {
        "ground_truth_transactions": len(targets),
        "evaluated": evaluated,
        "missing_predictions": missing_predictions,
        "match_mode": match,
        "mrr": round(reciprocal_total / evaluated, 4) if evaluated else 0.0,
    }
    for k in ks:
        result[f"top_{k}_accuracy"] = (
            round(hits[k] / evaluated, 4) if evaluated else 0.0
        )
        result[f"top_{k}_hits"] = hits[k]
    if evaluated == 0:
        result["blocker"] = (
            "No pipeline predictions were supplied, so no localization metric "
            "can be reported. Run the analyzer over the ground-truth "
            "transactions and pass the output directory via --predictions-dir."
        )
    return result


def load_predictions(directory: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load ranked candidates from pipeline output JSON files."""
    predictions: Dict[str, List[Dict[str, Any]]] = {}
    if not os.path.isdir(directory):
        return predictions
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, filename), encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        txn = _norm_addr(
            data.get("transaction_hash") or data.get("txn_hash") or filename[:-5]
        )
        ranked = (
            data.get("scored_functions")
            or data.get("ranked_candidates")
            or data.get("candidates")
            or []
        )
        if isinstance(ranked, list):
            predictions[txn] = [item for item in ranked if isinstance(item, dict)]
    return predictions
