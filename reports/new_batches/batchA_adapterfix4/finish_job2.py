"""Correct the Job 2 gate, refetch missing receipts, and replay verified rows."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
VALID = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
OLD_RAW = OUT / "rpc_publicnode_raw/eth"
REFETCH_RAW = OUT / "rpc_publicnode_receipt_refetch/eth"
ENDPOINT = "https://ethereum.publicnode.com"
PRODUCER = "1b1c7395771663622dd14b9731b4b8b471221960"
MODEL = "llm-free-function-ranker"
EXPECTED_VALID = "fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785"
EXPECTED_BATCH = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
PROMPT_TERMS = ("paid plan", "signup", "sign up", "billing", "api key", "card", "credit", "upgrade", "payment")


class StopFetch(RuntimeError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_batch_sha(payload: dict[str, Any]) -> str:
    import hashlib
    body = dict(payload)
    body.pop("artifact_sha256", None)
    return hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode()).hexdigest()


def paid_prompt(body: bytes) -> bool:
    text = body.decode("utf-8", errors="replace").lower()
    return any(term in text for term in PROMPT_TERMS)


def curl_call(method: str, tx: str, request_id: int, last: list[float], raw_path: Path) -> tuple[dict[str, Any], int]:
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": [tx]})
    for attempt in range(1, 4):
        wait = 1.0 - (time.monotonic() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.monotonic()
        temp = raw_path.with_name(f".{raw_path.name}.tmp")
        temp.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(["curl.exe", "-sS", "--max-time", "30", "-H", "Content-Type: application/json", "--data", payload, "-o", str(temp), "-w", "%{http_code}", ENDPOINT], capture_output=True, text=True, timeout=45)
            status_text = (proc.stdout or "").strip()
            status = int(status_text) if status_text.isdigit() else 0
            body = temp.read_bytes() if temp.is_file() else b""
        except (OSError, subprocess.SubprocessError):
            status, body = 0, temp.read_bytes() if temp.is_file() else b""
        finally:
            if temp.is_file():
                temp.unlink()
        if paid_prompt(body):
            raise StopFetch("paid-plan, signup, billing, API-key, or card prompt received")
        raw_path.write_bytes(body)
        if status == 429 or status >= 500 or status == 0:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise StopFetch(f"public RPC retry limit status={status} method={method}")
        if status >= 400:
            raise StopFetch(f"public RPC HTTP status={status} method={method}")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise StopFetch(f"public RPC non-JSON method={method}") from exc
        if paid_prompt(json.dumps(parsed).encode()):
            raise StopFetch("paid-plan, signup, billing, API-key, or card prompt received")
        if parsed.get("error") is not None:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return parsed, attempt
        return parsed, attempt
    raise StopFetch(f"public RPC retry limit method={method}")


def old_receipt_status(tx: str) -> str:
    path = OLD_RAW / f"{tx}.json"
    if not path.is_file():
        return "missing_file"
    response = load(path).get("receipt_response", {})
    if response.get("error") is not None:
        return "error"
    if response.get("result") is None:
        return "null"
    return "ok"


def refetch_receipts(records: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [str(record["transaction_hash"]).lower() for record in records if old_receipt_status(str(record["transaction_hash"]).lower()) != "ok"]
    rows = []
    last = [0.0]
    request_id = 3000
    for tx in missing:
        path = REFETCH_RAW / f"{tx}.json"
        if path.is_file():
            response, attempts = load(path), 0
        else:
            response, attempts = curl_call("eth_getTransactionReceipt", tx, request_id, last, path)
            request_id += 1
        result = response.get("result")
        rows.append({"transaction_hash": tx, "attempts": attempts, "response_sha256": sha256(path), "status": "ok" if result is not None else ("error" if response.get("error") else "null")})
        print(f"receipt refetch {len(rows)}/{len(missing)}")
    summary = {"label": "producer-era replay, exploratory", "endpoint": ENDPOINT, "method": "eth_getTransactionReceipt", "rate_target_requests_per_second": 1, "missing_before_refetch": len(missing), "rows": rows, "cause_before_refetch": {"null": sum(old_receipt_status(str(record["transaction_hash"]).lower()) == "null" for record in records), "error": sum(old_receipt_status(str(record["transaction_hash"]).lower()) == "error" for record in records), "missing_file": sum(old_receipt_status(str(record["transaction_hash"]).lower()) == "missing_file" for record in records), "ok": sum(old_receipt_status(str(record["transaction_hash"]).lower()) == "ok" for record in records)}}
    (OUT / "receipt_refetch_report.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return summary


def response_for(tx: str) -> tuple[dict[str, Any], dict[str, Any]]:
    combined = load(OLD_RAW / f"{tx}.json")
    tx_response = combined["transaction_response"]
    refetched = REFETCH_RAW / f"{tx}.json"
    receipt_response = load(refetched) if refetched.is_file() else combined["receipt_response"]
    return tx_response, receipt_response


def verify(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        expected = str(record["transaction_hash"]).lower()
        tx_response, receipt_response = response_for(expected)
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
        rows.append({"transaction_hash": expected, "transaction_hash_returned": tx_hash, "receipt_transaction_hash_returned": receipt_hash, "transaction_block_number": tx_block, "receipt_block_number": receipt_block, "verified": not reasons, "excluded": bool(reasons), "exclusion_reasons": reasons})
    result = {"label": "producer-era replay, exploratory", "rows": rows, "verified_count": sum(row["verified"] for row in rows), "excluded_count": sum(row["excluded"] for row in rows), "excluded_by_reason": {reason: sum(reason in row["exclusion_reasons"] for row in rows) for reason in sorted({reason for row in rows for reason in row["exclusion_reasons"]})}}
    (OUT / "job2_final_verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def current_localization():
    module_name = "batchA_current_localization_final"
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "benchmark/honest_eval/localization.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def metrics(ranks: list[int | None]) -> dict[str, Any]:
    def one(k: int) -> dict[str, Any]:
        hits = sum(rank is not None and rank <= k for rank in ranks)
        return {"hits": hits, "n": len(ranks), "recall": hits / len(ranks) if ranks else 0.0}
    return {"r_at_1": one(1), "r_at_3": one(3), "r_at_5": one(5)}


def replay(verified_rows: list[dict[str, Any]], records: list[dict[str, Any]], labels: dict[str, dict[str, Any]], producer_root: Path) -> dict[str, Any]:
    output = OUT / "producer_batchA_measurement_final.json"
    if output.exists():
        raise RuntimeError("scoring output already exists; refusing a second scoring run")
    sys.path.insert(0, str(producer_root))
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.function_analysis.function_ranker import FunctionRanker
    from faultseeker.utils.rpc_provider import normalize_trace_node
    loc = current_localization()
    loc._register_fn_names(str(row["vulnerable_function"]) for row in labels.values())
    record_by_tx = {str(record["transaction_hash"]).lower(): record for record in records}
    primary, functions, addresses, out_rows = [], [], [], []
    for verified in verified_rows:
        tx = verified["transaction_hash"]
        record = record_by_tx[tx]
        tx_response, receipt_response = response_for(tx)
        structured = {"transaction_hash": tx, "chain": "eth", "trace": normalize_trace_node(record["trace"]), "storage_events": [], "storage_reads": [], "state_diff": {}, "trace_coverage": {"trace_complete": True, "storage_trace_complete": False, "token_flow_complete": False, "multi_tx_context_complete": False}}
        orchestrator = ForensicsOrchestrator(model=MODEL, txn_sequencer=_CapturedSequencer(structured), txn_info_collector=_CapturedInfo(tx_response["result"], receipt_response["result"], tx, "eth"))
        result, _, _ = orchestrator.run(tx, "eth")
        tx_analysis = {"repeated_patterns": result.repeated_patterns, "function_call_loc_memo": result.function_call_loc_memo}
        predictions = [dict(item) for item in FunctionRanker().rank(result, tx_analysis).ranked_functions]
        label = labels[tx]
        target_address = loc._norm_addr(str(label["vulnerable_contract"]))
        target_function = loc._norm_fn(str(label["vulnerable_function"]))
        p = f = a = None
        for index, prediction in enumerate(predictions, 1):
            key, _ = loc._prediction_keys(prediction)
            if key is None:
                continue
            address, function = key
            if a is None and address == target_address: a = index
            if f is None and function == target_function: f = index
            if p is None and address == target_address and function == target_function: p = index
        primary.append(p); functions.append(f); addresses.append(a)
        out_rows.append({"transaction_hash": tx, "candidate_count": len(predictions), "primary_rank": p, "function_only_rank": f, "address_only_rank": a})
        print(f"producer replay {len(out_rows)}/{len(verified_rows)}")
    result = {"status": "COMPLETE", "label": "producer-era replay, exploratory", "producer_commit": PRODUCER, "verified_count": len(verified_rows), "sample_too_small": len(verified_rows) < 10, "metrics": {"primary_address_function": metrics(primary), "function_only_sensitivity": metrics(functions), "address_only_sensitivity": metrics(addresses)}, "candidate_counts": {"n": len(out_rows), "min": min((row["candidate_count"] for row in out_rows), default=None), "max": max((row["candidate_count"] for row in out_rows), default=None), "mean": sum(row["candidate_count"] for row in out_rows) / len(out_rows) if out_rows else None, "rows": out_rows}}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Batch A producer-era replay", "", "**Label: producer-era replay, exploratory**", "", f"Verified rows: {len(verified_rows)}; sample too small to read: {result['sample_too_small']}", "", "| Metric | R@1 | R@3 | R@5 | N |", "| --- | ---: | ---: | ---: | ---: |"]
    for name, key in (("Primary address+function", "primary_address_function"), ("Function-only sensitivity", "function_only_sensitivity"), ("Address-only sensitivity", "address_only_sensitivity")):
        m = result["metrics"][key]
        lines.append(f"| {name} | {m['r_at_1']['hits']}/{m['r_at_1']['n']} ({m['r_at_1']['recall']:.6f}) | {m['r_at_3']['hits']}/{m['r_at_3']['n']} ({m['r_at_3']['recall']:.6f}) | {m['r_at_5']['hits']}/{m['r_at_5']['n']} ({m['r_at_5']['recall']:.6f}) | {m['r_at_1']['n']} |")
    lines += ["", f"Candidate counts: n={result['candidate_counts']['n']}, min={result['candidate_counts']['min']}, max={result['candidate_counts']['max']}, mean={result['candidate_counts']['mean']}.", "", "| Transaction | Candidates | Primary | Function-only | Address-only |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in out_rows: lines.append(f"| `{row['transaction_hash']}` | {row['candidate_count']} | {row['primary_rank']} | {row['function_only_rank']} | {row['address_only_rank']} |")
    (OUT / "producer_batchA_measurement_final.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    producer_root = Path(sys.argv[1]).resolve()
    valid = load(VALID); batch = load(BATCH)
    if sha256(VALID) != EXPECTED_VALID or batch.get("artifact_sha256") != EXPECTED_BATCH or canonical_batch_sha(batch) != EXPECTED_BATCH:
        raise RuntimeError("frozen input hash mismatch")
    records = valid["records"]
    refetch = refetch_receipts(records)
    verified = verify(records)
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    verified_records = [row for row in verified["rows"] if row["verified"]]
    measurement = replay(verified_records, records, labels, producer_root)
    final = {"label": "producer-era replay, exploratory", "refetch": refetch, "verification": verified, "measurement": measurement, "network_calls": True}
    (OUT / "job2_final_report.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
