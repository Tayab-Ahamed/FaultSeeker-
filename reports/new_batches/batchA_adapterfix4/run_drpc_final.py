"""Offline verification and one producer-era replay using saved dRPC responses."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
VALID = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
OLD = OUT / "rpc_raw/eth"
FINAL = OUT / "rpc_drpc_final/eth"
PRODUCER_ROOT = Path(sys.argv[1]).resolve()
PRODUCER_COMMIT = "1b1c7395771663622dd14b9731b4b8b471221960"
MODEL = "llm-free-function-ranker"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_current_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def responses(tx: str) -> tuple[dict[str, Any], dict[str, Any]]:
    new = FINAL / f"{tx}.json"
    if new.is_file():
        payload = load(new)
        return payload["transaction_response"]["response"], payload["receipt_response"]["response"]
    old = load(OLD / f"{tx}.transaction.json")
    receipt = load(OLD / f"{tx}.receipt.json")
    return old, receipt


def verify(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        expected = str(record["transaction_hash"]).lower()
        tx_response, receipt_response = responses(expected)
        tx = tx_response.get("result") or {}
        receipt = receipt_response.get("result") or {}
        tx_hash = str(tx.get("hash") or "").lower()
        receipt_hash = str(receipt.get("transactionHash") or "").lower()
        tx_block = tx.get("blockNumber")
        receipt_block = receipt.get("blockNumber")
        reasons = []
        if tx_hash != expected:
            reasons.append("transaction.hash_mismatch")
        if receipt_hash != expected:
            reasons.append("receipt.transactionHash_mismatch")
        if tx_block != receipt_block:
            reasons.append("transaction_receipt.blockNumber_mismatch")
        if tx_block in (None, "", "0x"):
            reasons.append("transaction.pending")
        rows.append({"transaction_hash": expected, "transaction_hash_returned": tx_hash, "receipt_transaction_hash_returned": receipt_hash, "transaction_block_number": tx_block, "receipt_block_number": receipt_block, "verified": not reasons, "exclusion_reasons": reasons})
    return {"label": "producer-era replay, exploratory", "rows": rows, "verified_count": sum(row["verified"] for row in rows), "excluded_count": sum(not row["verified"] for row in rows), "excluded_by_reason": {reason: sum(reason in row["exclusion_reasons"] for row in rows) for reason in sorted({reason for row in rows for reason in row["exclusion_reasons"]})}}


def metric(ranks: list[int | None]) -> dict[str, Any]:
    def at(k: int):
        hits = sum(rank is not None and rank <= k for rank in ranks)
        return {"hits": hits, "n": len(ranks), "recall": hits / len(ranks) if ranks else 0.0}
    return {"r_at_1": at(1), "r_at_3": at(3), "r_at_5": at(5)}


def replay(verified_rows: list[dict[str, Any]], records: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # Producer-era orchestration imports from the detached 1b1c739 worktree.
    if str(PRODUCER_ROOT) not in sys.path:
        sys.path.insert(0, str(PRODUCER_ROOT))
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.utils.rpc_provider import normalize_trace_node
    # Current scorer and current scorer-side matching semantics come from the
    # main worktree, not from the producer-era worktree.
    current_ranker_module = load_current_module("current_function_ranker_final", ROOT / "faultseeker/function_analysis/function_ranker.py")
    current_loc = load_current_module("current_localization_final", ROOT / "benchmark/honest_eval/localization.py")
    current_ranker = current_ranker_module.FunctionRanker
    current_loc._register_fn_names(str(row["vulnerable_function"]) for row in labels.values())
    by_tx = {str(record["transaction_hash"]).lower(): record for record in records}
    primary, functions, addresses, output_rows = [], [], [], []
    for item in verified_rows:
        tx = item["transaction_hash"]
        record = by_tx[tx]
        tx_response, receipt_response = responses(tx)
        structured = {"transaction_hash": tx, "chain": "eth", "trace": normalize_trace_node(record["trace"]), "storage_events": [], "storage_reads": [], "state_diff": {}, "trace_coverage": {"trace_complete": True, "storage_trace_complete": False, "token_flow_complete": False, "multi_tx_context_complete": False}}
        orchestrator = ForensicsOrchestrator(model=MODEL, txn_sequencer=_CapturedSequencer(structured), txn_info_collector=_CapturedInfo(tx_response["result"], receipt_response["result"], tx, "eth"))
        forensics_result, _, _ = orchestrator.run(tx, "eth")
        tx_analysis = {"repeated_patterns": forensics_result.repeated_patterns, "function_call_loc_memo": forensics_result.function_call_loc_memo}
        predictions = [dict(item) for item in current_ranker().rank(forensics_result, tx_analysis).ranked_functions]
        label = labels[tx]
        target_address = current_loc._norm_addr(str(label["vulnerable_contract"]))
        target_function = current_loc._norm_fn(str(label["vulnerable_function"]))
        p = f = a = None
        for index, prediction in enumerate(predictions, 1):
            key, _ = current_loc._prediction_keys(prediction)
            if key is None:
                continue
            address, function = key
            if a is None and address == target_address: a = index
            if f is None and function == target_function: f = index
            if p is None and address == target_address and function == target_function: p = index
        primary.append(p); functions.append(f); addresses.append(a)
        output_rows.append({"transaction_hash": tx, "candidate_count": len(predictions), "primary_rank": p, "function_only_rank": f, "address_only_rank": a})
        print(f"REPLAYED {len(output_rows)}/{len(verified_rows)}")
    result = {"status": "COMPLETE", "label": "producer-era replay, exploratory", "producer_commit": PRODUCER_COMMIT, "scorer": "current unchanged FunctionRanker and localization scorer", "verified_count": len(verified_rows), "sample_too_small": len(verified_rows) < 10, "metrics": {"primary_address_function": metric(primary), "function_only_sensitivity": metric(functions), "address_only_sensitivity": metric(addresses)}, "candidate_counts": {"n": len(output_rows), "min": min((row["candidate_count"] for row in output_rows), default=None), "max": max((row["candidate_count"] for row in output_rows), default=None), "mean": sum(row["candidate_count"] for row in output_rows) / len(output_rows) if output_rows else None, "rows": output_rows}}
    (OUT / "producer_batchA_measurement_drpc_final.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    valid = load(VALID); batch = load(BATCH)
    records = valid["records"]
    verification = verify(records)
    verified_rows = [row for row in verification["rows"] if row["verified"]]
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    measurement = replay(verified_rows, records, labels)
    final = {"label": "producer-era replay, exploratory", "verification": verification, "measurement": measurement, "network_calls": False, "raw_source": "reports/new_batches/batchA_adapterfix4/rpc_drpc_final/eth/"}
    (OUT / "job2_drpc_final_report.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines=["# Batch A dRPC final replay", "", "**Label: producer-era replay, exploratory**", "", f"Verified: {verification['verified_count']}; excluded: {verification['excluded_count']}; sample too small to read: {measurement['sample_too_small']}", "", "| Metric | R@1 | R@3 | R@5 | N |", "| --- | ---: | ---: | ---: | ---: |"]
    for name,key in (("Primary address+function","primary_address_function"),("Function-only sensitivity","function_only_sensitivity"),("Address-only sensitivity","address_only_sensitivity")):
        m=measurement['metrics'][key]
        lines.append(f"| {name} | {m['r_at_1']['hits']}/{m['r_at_1']['n']} ({m['r_at_1']['recall']:.6f}) | {m['r_at_3']['hits']}/{m['r_at_3']['n']} ({m['r_at_3']['recall']:.6f}) | {m['r_at_5']['hits']}/{m['r_at_5']['n']} ({m['r_at_5']['recall']:.6f}) | {m['r_at_1']['n']} |")
    lines += ["", f"Candidate counts: n={measurement['candidate_counts']['n']}, min={measurement['candidate_counts']['min']}, max={measurement['candidate_counts']['max']}, mean={measurement['candidate_counts']['mean']}."]
    (OUT / "producer_batchA_measurement_drpc_final.md").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    (OUT / "job2_drpc_verification_final.json").write_text(json.dumps(verification, indent=2, sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"verified":verification['verified_count'],"excluded":verification['excluded_count'],"measurement":measurement['metrics'],"candidate_counts":measurement['candidate_counts']},indent=2,sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
