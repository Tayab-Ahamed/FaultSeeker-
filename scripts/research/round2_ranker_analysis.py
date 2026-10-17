"""Round-2 offline analysis on the 90-row development population only."""
from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import _norm_addr, _norm_fn, _prediction_keys, load_ground_truth, rank_of_first_hit
from faultseeker.function_analysis.function_ranker import canonical_call_label, rerank_saved_predictions
from scripts.research.analyze_ranker_misses import classify


RUN = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017"
HOLDOUT = ROOT / "reports/original_benchmark/ranker_upgrade/holdout_20261017.json"
OUTPUT = ROOT / "reports/original_benchmark/ranker_upgrade/round2_miss_analysis_20261017.json"
COMMAND_OUTPUT = ROOT / "reports/original_benchmark/ranker_upgrade/round2_miss_analysis_command_output.txt"


def _target_names(path: Path) -> tuple[set[str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    names, raw_names = set(), set()
    for key, values in (data.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parts = str(entry).split("#")
            if len(parts) < 3:
                continue
            member = parts[-1].strip()
            if ":" in member and member.split(":")[0].isdigit():
                continue
            normalized = _norm_fn(member)
            if normalized and normalized != ":":
                names.add(normalized)
                raw_names.add(canonical_call_label(member).lower())
    return names, raw_names


def _label_audit(row: dict, item: dict) -> dict:
    gt_path = ROOT / "benchmark/original_faultseeker/ground_truth" / f"{row['txn_hash']}.json"
    target_names, raw_names = _target_names(gt_path)
    target_addresses = {address for address, _ in item["target_functions"]}
    predictions = row["predictions"]
    equivalents = []
    target_address_candidates = []
    for index, prediction in enumerate(predictions, start=1):
        fn_key, _ = _prediction_keys(prediction)
        address = _norm_addr(prediction.get("code_address") or prediction.get("address"))
        raw_function = str(prediction.get("function") or prediction.get("function_name") or "")
        normalized = _norm_fn(fn_key[1]) if fn_key else ""
        if normalized in target_names:
            equivalents.append({"rank": index, "address": address, "raw_function": raw_function, "normalized_function": normalized})
        if address in target_addresses:
            target_address_candidates.append({"rank": index, "address": address, "raw_function": raw_function, "normalized_function": normalized})
    if item["cause"] != "label/selector mismatch":
        return {"classification": "not-a-current-label-mismatch", "equivalent_candidates": equivalents, "target_address_candidates": target_address_candidates}
    if not equivalents and not target_address_candidates:
        return {"classification": "true-miss-no-identity-candidate", "equivalent_candidates": [], "target_address_candidates": []}
    selector_equivalent = [candidate for candidate in equivalents if candidate["raw_function"].lower().startswith("0x")]
    overload_equivalent = [candidate for candidate in equivalents if "(" in candidate["raw_function"]]
    renderer_equivalent = [candidate for candidate in equivalents if "{" in candidate["raw_function"]]
    if selector_equivalent:
        classification = "naming-issue-selector-to-name"
    elif overload_equivalent:
        classification = "naming-issue-overload-signature"
    elif renderer_equivalent:
        classification = "naming-issue-renderer-annotation"
    elif equivalents:
        classification = "address-identity-mismatch-function-equivalent"
    else:
        classification = "true-miss-target-address-wrong-label"
    return {
        "classification": classification,
        "equivalent_candidates": equivalents,
        "target_address_candidates": target_address_candidates,
        "target_names": sorted(target_names),
        "target_raw_names": sorted(raw_names),
    }


def run() -> dict:
    holdout_ids = set(json.loads(HOLDOUT.read_text(encoding="utf-8"))["transaction_ids"])
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    rows = [row for row in manifest["rows"] if row.get("status") == "ok" and row["txn_hash"] not in holdout_ids]
    assert len(rows) == 90, len(rows)
    current_rows = []
    targets = {target.txn_hash: target for target in load_ground_truth(str(ROOT / "benchmark/original_faultseeker/ground_truth"))}
    for row in rows:
        current = deepcopy(row)
        current["predictions"] = rerank_saved_predictions(row.get("predictions") or [])
        current["current_primary_rank"] = rank_of_first_hit(targets[row["txn_hash"]], current["predictions"], match="function")
        current["score"] = dict(current.get("score") or {})
        current["score"]["recall_at_5"] = current["current_primary_rank"] is not None and current["current_primary_rank"] <= 5
        current_rows.append(current)
    misses = [row for row in current_rows if not row["score"].get("recall_at_5")]
    assert len(misses) == 45, len(misses)
    classified = []
    for row in misses:
        item = classify(row)
        item["label_audit"] = _label_audit(row, item)
        classified.append(item)
    grouped = defaultdict(list)
    for item in classified:
        grouped[item["cause"]].append(item)
    label_rows = [item for item in classified if item["cause"] == "label/selector mismatch"]
    label_classifications = defaultdict(list)
    for item in label_rows:
        label_classifications[item["label_audit"]["classification"]].append(item)
    result = {
        "label": "development, exploratory",
        "scope": "offline current-ranker analysis of the 90-row development population",
        "holdout_excluded": True,
        "development_rows": len(rows),
        "remaining_top5_misses": len(misses),
        "cause_counts": dict(sorted((key, len(value)) for key, value in grouped.items())),
        "label_mismatch_audit_counts": dict(sorted((key, len(value)) for key, value in label_classifications.items())),
        "classification_rule": "Round-1 canonical label grouping and depth tie-break applied before this analysis; no holdout rows included.",
        "examples": {key: value[:5] for key, value in sorted(grouped.items())},
        "label_audit_examples": {key: value[:5] for key, value in sorted(label_classifications.items())},
        "all_classifications": classified,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [json.dumps({"development_rows": len(rows), "remaining_top5_misses": len(misses), "cause_counts": result["cause_counts"]}, indent=2)]
    for cause, examples in sorted(result["examples"].items()):
        lines.append(f"\nCAUSE: {cause} ({len(grouped[cause])} total; showing {len(examples)})")
        for item in examples:
            lines.append(json.dumps({"txn_hash": item["txn_hash"], "chain": item["chain"], "incident": item["incident"], "primary_rank": item["primary_rank"], "function_only_rank": item["function_only_rank"], "evidence": item["evidence"], "label_audit": item["label_audit"]}, sort_keys=True))
    lines.append("\nLABEL_MISMATCH_AUDIT")
    for classification, examples in sorted(label_classifications.items()):
        lines.append(f"{classification}: {len(label_classifications[classification])}")
        for item in examples[:5]:
            lines.append(json.dumps({"txn_hash": item["txn_hash"], "chain": item["chain"], "incident": item["incident"], "audit": item["label_audit"]}, sort_keys=True))
    COMMAND_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return result


if __name__ == "__main__":
    run()
