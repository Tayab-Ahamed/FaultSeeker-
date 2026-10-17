"""Continue Job 2 with public keyless Ethereum RPC only.

This continuation reuses the two complete dRPC pairs without contacting dRPC.
It fetches the remaining rows from PublicNode, combines one transaction and
receipt response per transaction, verifies identity, and does not replay rows
whose frozen Batch A record lacks the required expected block number.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
VALID = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
EXPECTED_BATCH_SHA = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
EXPECTED_VALID_SHA = "fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785"
ENDPOINT = "https://ethereum.publicnode.com"
RAW_OLD = OUT / "rpc_raw" / "eth"
RAW_PUBLIC = OUT / "rpc_publicnode_raw" / "eth"
METHODS = ("eth_getTransactionByHash", "eth_getTransactionReceipt")
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


def existing_pair(tx: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    tx_path = RAW_OLD / f"{tx}.transaction.json"
    receipt_path = RAW_OLD / f"{tx}.receipt.json"
    if not tx_path.is_file() or not receipt_path.is_file():
        return None
    tx_response = load(tx_path)
    receipt_response = load(receipt_path)
    if tx_response.get("result") is None or receipt_response.get("result") is None:
        return None
    return tx_response, receipt_response


def public_call(method: str, tx: str, request_id: int, last_request: list[float]) -> dict[str, Any]:
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": [tx]}).encode()
    for attempt in range(1, 4):
        wait = 1.0 - (time.monotonic() - last_request[0])
        if wait > 0:
            time.sleep(wait)
        last_request[0] = time.monotonic()
        temp = RAW_PUBLIC / f".{tx}.{method}.response"
        temp.parent.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                ["curl.exe", "-sS", "--max-time", "30", "-H", "Content-Type: application/json",
                 "--data", payload.decode(), "-o", str(temp), "-w", "%{http_code}", ENDPOINT],
                capture_output=True, text=True, timeout=45,
            )
            status_text = (completed.stdout or "").strip()
            status = int(status_text) if status_text.isdigit() else 0
            body = temp.read_bytes() if temp.is_file() else b""
        except (subprocess.SubprocessError, OSError):
            body = temp.read_bytes() if temp.is_file() else b""
            status = 0
        finally:
            if temp.is_file():
                temp.unlink()
        if paid_prompt(body):
            raise StopFetch("paid-plan, signup, billing, API-key, or card prompt received")
        if status == 0:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise StopFetch("public RPC network retry limit reached")
        if paid_prompt(body):
            raise StopFetch("paid-plan, signup, billing, API-key, or card prompt received")
        if status == 429 or status >= 500:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise StopFetch(f"public RPC HTTP status {status}")
        if status >= 400:
            raise StopFetch(f"public RPC HTTP status {status}")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise StopFetch("public RPC returned non-JSON") from exc
        if paid_prompt(json.dumps(parsed).encode()):
            raise StopFetch("paid-plan, signup, billing, API-key, or card prompt received")
        if parsed.get("error") is not None:
            raise StopFetch(f"public RPC returned an error for {method}")
        return parsed
    raise StopFetch("public RPC retry limit reached")


def verify(record: dict[str, Any], tx_response: dict[str, Any], receipt_response: dict[str, Any]) -> dict[str, Any]:
    expected_tx = str(record["transaction_hash"]).lower()
    tx = tx_response.get("result") or {}
    receipt = receipt_response.get("result") or {}
    actual_tx = str(tx.get("hash") or "").lower()
    receipt_tx = str(receipt.get("transactionHash") or "").lower()
    tx_block = tx.get("blockNumber")
    receipt_block = receipt.get("blockNumber")
    expected_block = record.get("block_number", record.get("blockNumber"))
    mismatches = []
    if actual_tx != expected_tx:
        mismatches.append({"field": "transaction.hash", "expected": expected_tx, "actual": actual_tx})
    if receipt_tx != expected_tx:
        mismatches.append({"field": "receipt.transactionHash", "expected": expected_tx, "actual": receipt_tx})
    if tx_block != receipt_block:
        mismatches.append({"field": "transaction/receipt.blockNumber", "expected": tx_block, "actual": receipt_block})
    if expected_block is None:
        mismatches.append({"field": "batch_record.blockNumber", "expected": "present", "actual": "missing from frozen Batch A record"})
    else:
        if tx_block != expected_block:
            mismatches.append({"field": "transaction.blockNumber", "expected": expected_block, "actual": tx_block})
        if receipt_block != expected_block:
            mismatches.append({"field": "receipt.blockNumber", "expected": expected_block, "actual": receipt_block})
    return {"transaction_hash": expected_tx, "expected_block_number": expected_block, "transaction_hash_returned": actual_tx, "receipt_transaction_hash_returned": receipt_tx, "transaction_block_number": tx_block, "receipt_block_number": receipt_block, "mismatches": mismatches, "excluded": bool(mismatches), "exclusion_reason": "; ".join(item["field"] for item in mismatches) if mismatches else None}


def main() -> int:
    valid = load(VALID)
    batch = load(BATCH)
    if sha256(VALID) != EXPECTED_VALID_SHA or batch.get("artifact_sha256") != EXPECTED_BATCH_SHA or canonical_batch_sha(batch) != EXPECTED_BATCH_SHA:
        raise StopFetch("frozen input hash mismatch")
    records = valid.get("records", [])
    if len(records) != 23 or any(str(record.get("chain", "")).lower() != "eth" for record in records):
        raise StopFetch("valid set is not the expected 23 ETH records")
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    last_request = [0.0]
    rows = []
    reused = fetched = 0
    request_id = 1000
    for record in records:
        tx = str(record["transaction_hash"]).lower()
        pair = existing_pair(tx)
        if pair is not None:
            tx_response, receipt_response = pair
            source = "reused_drpc_pair"
            reused += 1
        else:
            source = "publicnode_fetch"
            tx_response = public_call(METHODS[0], tx, request_id, last_request)
            request_id += 1
            receipt_response = public_call(METHODS[1], tx, request_id, last_request)
            request_id += 1
            fetched += 1
            RAW_PUBLIC.mkdir(parents=True, exist_ok=True)
            (RAW_PUBLIC / f"{tx}.json").write_text(json.dumps({"transaction_response": tx_response, "receipt_response": receipt_response}, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        if source == "reused_drpc_pair":
            RAW_PUBLIC.mkdir(parents=True, exist_ok=True)
            (RAW_PUBLIC / f"{tx}.json").write_text(json.dumps({"transaction_response": tx_response, "receipt_response": receipt_response, "source": source}, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        check = verify(record, tx_response, receipt_response)
        check["source"] = source
        check["label_present"] = tx in labels
        rows.append(check)
        print(f"verified {len(rows)}/{len(records)}")
    verification = {"label": "producer-era replay, exploratory", "status": "COMPLETE", "endpoint": ENDPOINT, "methods": list(METHODS), "rate_target_requests_per_second": 1, "reused_complete_pairs": reused, "new_transactions_fetched": fetched, "rows": rows, "replayed_rows": 0, "excluded_rows": sum(row["excluded"] for row in rows), "producer_replay_executed": False, "reason": "Every frozen Batch A record lacks an expected block number field, so every row is excluded rather than adapting the verification rule."}
    (OUT / "publicnode_verification.json").write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (OUT / "job2_continuation_status.json").write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (OUT / "job2_continuation.md").write_text("# Batch A adapter fix 4 — Job 2 continuation\n\n**Label: producer-era replay, exploratory**\n\nFetch completed using only `eth_getTransactionByHash` and `eth_getTransactionReceipt` against the public keyless endpoint. Two complete dRPC pairs were reused; the remaining 21 transaction/receipt pairs were fetched with 1 request/second pacing.\n\nVerification found no expected `block_number` or `blockNumber` field in the frozen Batch A records. Every row was therefore excluded with reason `batch_record.blockNumber` missing. No producer-era replay or scoring run was executed; no verification rule was adapted.\n\nRaw one-file-per-transaction responses: `reports/new_batches/batchA_adapterfix4/rpc_publicnode_raw/eth/`.\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
