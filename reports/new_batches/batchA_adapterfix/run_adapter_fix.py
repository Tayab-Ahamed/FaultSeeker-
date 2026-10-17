"""One-shot gate and exploratory measurement for the patched Batch A adapter."""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import (  # noqa: E402
    LocalizationTarget,
    _parse_location_entry,
    _prediction_keys,
    _register_fn_names,
    _norm_addr,
    _norm_fn,
    rank_of_first_hit,
)
from scripts.research.evaluate_batch_a_ranker_once import (  # noqa: E402
    _first_rank,
    _rank_one,
)
from reports.new_batches.batchA_diagnostic.run_diagnostic import (  # noqa: E402
    classify,
    format_diagnostic,
)
from faultseeker.data_collection.txn_info_collector import TransactionInfoCollector  # noqa: E402

BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
VALID_SET = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
EXPECTED_BATCH_SHA = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
EXPECTED_VALID_SHA = "fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785"
CONTROL_IDS = [
    "0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb",
    "0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c",
    "0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa",
    "0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def target_from_gt(path: Path) -> LocalizationTarget:
    raw = load(path)
    target = LocalizationTarget(txn_hash=path.stem, name=str(raw.get("name") or ""))
    names = []
    for key, values in (raw.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parsed = _parse_location_entry(entry)
            if not parsed:
                continue
            address, member, is_line = parsed
            if not is_line:
                target.functions.add((address, member))
                names.append(member)
    _register_fn_names(names)
    return target


def load_control(tx: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    trace_path = ROOT / f"reports/cohort_rebuild_v2/traces/eth/{tx}.json.gz"
    rpc_path = ROOT / f"reports/cohort_rebuild_v2/rpc/eth/{tx}.json"
    known_path = ROOT / f"reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw/{tx}.json"
    gt_path = ROOT / f"benchmark/original_faultseeker/ground_truth/{tx}.json"
    with gzip.open(trace_path, "rt", encoding="utf-8") as handle:
        captured = json.load(handle)
    rpc = load(rpc_path)
    txn_info = TransactionInfoCollector.from_rpc(rpc["transaction"], rpc["receipt"], tx)
    record = {"transaction_hash": tx, "chain": captured["chain"], "trace": captured["raw_trace"]["call"]}
    return record, txn_info, {"known": load(known_path), "target": target_from_gt(gt_path), "trace_path": str(trace_path.relative_to(ROOT)).replace("\\", "/")}


def first_address_rank(predictions: list[dict[str, Any]], address: str) -> int | None:
    target = _norm_addr(address)
    for index, prediction in enumerate(predictions, start=1):
        key, _ = _prediction_keys(prediction)
        if key and key[0] == target:
            return index
    return None


def controls() -> dict[str, Any]:
    rows = []
    for tx in CONTROL_IDS:
        record, txn_info, meta = load_control(tx)
        predictions = _rank_one(record, txn_info=txn_info)
        adapter_rank = rank_of_first_hit(meta["target"], predictions, match="function")
        known_rank = meta["known"].get("score", {}).get("first_hit_rank")
        rows.append({
            "transaction_hash": tx,
            "known_rank": known_rank,
            "adapter_rank": adapter_rank,
            "rank_reproduced": known_rank == adapter_rank,
            "known_prediction_count": len(meta["known"].get("predictions", [])),
            "adapter_prediction_count": len(predictions),
            "trace_artifact": meta["trace_path"],
        })
    return {
        "requested": 4,
        "executed": len(rows),
        "all_passed": all(row["rank_reproduced"] for row in rows),
        "rows": rows,
    }


def batch_measurement(labels: dict[str, dict[str, Any]], valid: dict[str, Any]) -> dict[str, Any]:
    rows = []
    primary = []
    functions = []
    addresses = []
    for record in valid["records"]:
        tx = str(record["transaction_hash"]).lower()
        label = labels[tx]
        predictions = _rank_one(record)
        address = str(label["vulnerable_contract"])
        function = str(label["vulnerable_function"])
        primary_rank = _first_rank(predictions, address, function, address_sensitive=True)
        function_rank = _first_rank(predictions, address, function, address_sensitive=False)
        address_rank = first_address_rank(predictions, address)
        primary.append(primary_rank)
        functions.append(function_rank)
        addresses.append(address_rank)
        diag = format_diagnostic(label, record["trace"], predictions)
        diag["classification"] = classify(diag)
        diag.update({"transaction_hash": tx, "chain": record["chain"], "candidate_count": len(predictions)})
        rows.append(diag)

    def metric(ranks: list[int | None]) -> dict[str, Any]:
        return {
            "n": len(ranks),
            "hits_at_1": sum(rank is not None and rank <= 1 for rank in ranks),
            "hits_at_3": sum(rank is not None and rank <= 3 for rank in ranks),
            "hits_at_5": sum(rank is not None and rank <= 5 for rank in ranks),
            "full_list_missing": sum(rank is None for rank in ranks),
        }

    counts = Counter(row["classification"] for row in rows)
    return {
        "label": "post-diagnostic adapter fix, exploratory",
        "metrics": {
            "primary_address_function": metric(primary),
            "function_only_sensitivity": metric(functions),
            "address_only_sensitivity": metric(addresses),
        },
        "counts_per_chain": dict(sorted(Counter(row["chain"] for row in rows).items())),
        "classification_counts": dict(sorted(counts.items())),
        "rows": rows,
    }


def main() -> int:
    batch = load(BATCH)
    valid = load(VALID_SET)
    assert batch["artifact_sha256"] == EXPECTED_BATCH_SHA
    assert sha256(VALID_SET) == EXPECTED_VALID_SHA
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    _register_fn_names(str(row["vulnerable_function"]) for row in labels.values())

    control = controls()
    changelog = """# Batch A adapter-fix changelog

Label: `post-diagnostic adapter fix, exploratory`.

## Differences found and addressed

1. The old adapter ran `TransactionSequencer.from_structured` and `TraceAnalyzer`, then passed an empty `functions_to_be_inspected` map directly to `FunctionRanker`. The original benchmark path runs `AddressClassifier.run` first and uses its normalized address filtering and candidate map.
2. The old adapter omitted the original orchestration hooks: `check_flashloan_fallback_execution`, `check_function_name_with_hash`, `check_call_with_created_contract`, `get_other_functions_to_be_inspected`, and `AdaptiveFailureAwareController.apply`.
3. The old adapter did not construct the production `ForensicsResult` with address-classifier fields, fund-flow fields, candidate fields, and adaptive-fallback metadata.
4. The patched adapter reuses `ForensicsOrchestrator`, `AddressClassifier`, `AdaptiveFailureAwareController`, `ForensicsResult`, `TraceAnalyzer`, `TransactionSequencer`, and the existing localization selector/name normalization rather than duplicating candidate-building logic.
5. CallTracer conversion was already field-equivalent to `TransactionSequencer._canonical_to_legacy_trace`: `from`, `to`, `input[:10]`, `input[10:]`, `type`, `value`, `gas`, `gasUsed`, and recursive calls. No change was required there.
6. Address normalization remains the original lowercase normalization. EIP-55 checksum casing is not used by the original rank scorer; no checksum behavior was added to scoring.

## Gate policy

The four original controls are a hard gate. Batch A is not measured unless every saved rank reproduces exactly.
"""
    (OUT / "adapter_changelog.md").write_text(changelog, encoding="utf-8", newline="\n")
    control_report = {
        "label": "post-diagnostic adapter fix, exploratory",
        "batch_canonical_sha256": EXPECTED_BATCH_SHA,
        "valid_set_sha256": EXPECTED_VALID_SHA,
        "control": control,
        "ranker_or_scorer_changed": False,
        "network_calls": False,
    }
    if not control["all_passed"]:
        control_report["status"] = "STOPPED_CONTROL_GATE_FAILED"
        (OUT / "control_report.json").write_text(json.dumps(control_report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (OUT / "control_report.md").write_text(
            "# Batch A adapter-fix control gate\n\n**Label: post-diagnostic adapter fix, exploratory**\n\n"
            "The gate failed. Batch A was not re-run.\n\n"
            + "\n".join(f"- `{row['transaction_hash']}`: known={row['known_rank']}, adapter={row['adapter_rank']}, reproduced={row['rank_reproduced']}" for row in control["rows"])
            + "\n",
            encoding="utf-8", newline="\n",
        )
        print(json.dumps(control_report, indent=2, sort_keys=True))
        return 2

    measurement = batch_measurement(labels, valid)
    result = {
        "status": "COMPLETE",
        "label": "post-diagnostic adapter fix, exploratory",
        "batch_canonical_sha256": EXPECTED_BATCH_SHA,
        "valid_set_sha256": EXPECTED_VALID_SHA,
        "control": control,
        "measurement": measurement,
        "ranker_or_scorer_changed": False,
        "network_calls": False,
    }
    (OUT / "adapterfix_measurement.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (OUT / "adapterfix_measurement.md").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
