"""Batch B phase-2 dRPC collection and protocol verification.

This script intentionally performs no scoring or ranker invocation. It uses only
the three methods pre-authorized for phase 2 and never prints credentials.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import dotenv_values
except Exception:  # pragma: no cover - fallback for a minimal environment
    dotenv_values = None

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent / "phase2"
BATCH = ROOT / "reports/new_batches/batchB/batchB_candidates.json"
EXPECTED_HASH = "5b66ae6d8c2b6bc23fbdb03f82738ada4684865846f2792d5111edc92cee942a"
METHODS = ("eth_getTransactionByHash", "eth_getTransactionReceipt", "debug_traceTransaction")
PRODUCER_COMMIT = "1b1c7395771663622dd14b9731b4b8b471221960"
PAID_TERMS = ("paid plan", "paid-plan", "billing", "card", "upgrade", "limit", "quota", "subscription")


class StopCollection(RuntimeError):
    def __init__(self, text: str, method: str, tx: str):
        super().__init__(text)
        self.text = text
        self.method = method
        self.tx = tx


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def redact(text: str, secrets: list[str]) -> str:
    result = str(text)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "<REDACTED>")
    return result


def frozen_hash() -> str:
    import hashlib
    payload = load(BATCH)
    body = dict(payload)
    stored = body.pop("artifact_sha256")
    actual = hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()
    if stored != EXPECTED_HASH or actual != EXPECTED_HASH:
        raise RuntimeError(f"frozen hash mismatch: stored={stored} canonical={actual} expected={EXPECTED_HASH}")
    return actual


def config() -> tuple[str, list[str]]:
    values = {}
    if dotenv_values is not None:
        values.update({key: value for key, value in dotenv_values(ROOT / ".env").items() if value is not None})
    values.update({key: value for key, value in os.environ.items() if key in {"DRPC_RPC_URL", "DRPC_API_KEY"}})
    endpoint = str(values.get("DRPC_RPC_URL") or "").strip()
    api_key = str(values.get("DRPC_API_KEY") or "").strip()
    if "{api_key}" in endpoint:
        endpoint = endpoint.replace("{api_key}", urllib.parse.quote(api_key, safe=""))
    if "{chain}" in endpoint:
        endpoint = endpoint.replace("{chain}", "ethereum")
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "https" or "drpc" not in parsed.netloc.lower():
        raise RuntimeError("configured DRPC_RPC_URL is missing or is not an HTTPS dRPC endpoint")
    return endpoint, [endpoint, api_key]


def paid_text(body: bytes) -> str | None:
    text = body.decode("utf-8", errors="replace")
    lowered = text.lower()
    if any(term in lowered for term in PAID_TERMS):
        return text
    return None


def post(endpoint: str, method: str, tx: str, request_id: int, run_dir: Path, secrets: list[str]) -> dict:
    request_dir = run_dir / "raw" / tx
    stderr_dir = run_dir / "stderr" / tx
    attempt_dir = run_dir / "attempts"
    request_dir.mkdir(parents=True, exist_ok=True)
    stderr_dir.mkdir(parents=True, exist_ok=True)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    attempt = 1
    base = f"{request_id:03d}_{method}_attempt{attempt:02d}"
    raw_path = request_dir / f"{base}.json"
    stderr_path = stderr_dir / f"{base}.stderr"
    started = time.time()
    params = [tx, {"tracer": "callTracer"}] if method == "debug_traceTransaction" else [tx]
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}).encode("utf-8")
    record = {"request_id": request_id, "attempt": attempt, "method": method, "transaction_hash": tx, "started_at_utc": now(), "raw_path": str(raw_path.relative_to(run_dir)).replace("\\", "/"), "stderr_path": str(stderr_path.relative_to(run_dir)).replace("\\", "/"), "endpoint_host": urllib.parse.urlparse(endpoint).netloc, "status": "started"}
    try:
        request = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            status = int(response.status)
            body = response.read()
        raw_path.write_bytes(body)
        stderr_path.write_text("", encoding="utf-8", newline="\n")
        record.update({"status": "http_ok" if status < 400 else "http_error", "http_status": status, "elapsed_seconds": round(time.time() - started, 3)})
        paid = paid_text(body)
        if paid is not None:
            error_text = redact(paid, secrets)
            record.update({"status": "paid_plan_or_limit_stop", "error_text": error_text})
            (attempt_dir / f"{tx}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            raise StopCollection(error_text, method, tx)
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            parsed = {"raw_decode_error": str(exc), "raw_text": body.decode("utf-8", errors="replace")}
        record["jsonrpc_error"] = parsed.get("error") if isinstance(parsed, dict) else None
        record["result_present"] = isinstance(parsed, dict) and parsed.get("result") is not None
        (attempt_dir / f"{tx}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        return {"method": method, "raw_path": str(raw_path.relative_to(run_dir)).replace("\\", "/"), "stderr_path": str(stderr_path.relative_to(run_dir)).replace("\\", "/"), "response": parsed, "attempt": record}
    except StopCollection:
        raise
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raw_path.write_bytes(body)
        error_text = redact(body.decode("utf-8", errors="replace"), secrets)
        stderr_path.write_text(error_text, encoding="utf-8", newline="\n")
        record.update({"status": "http_error", "http_status": exc.code, "elapsed_seconds": round(time.time() - started, 3), "error_text": error_text})
        (attempt_dir / f"{tx}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        return {"method": method, "raw_path": str(raw_path.relative_to(run_dir)).replace("\\", "/"), "stderr_path": str(stderr_path.relative_to(run_dir)).replace("\\", "/"), "response": {"error": {"code": exc.code, "message": error_text}}, "attempt": record}
    except Exception as exc:
        error_text = redact(f"{type(exc).__name__}: {exc}", secrets)
        raw_path.write_text(json.dumps({"local_error": error_text}, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        stderr_path.write_text(error_text, encoding="utf-8", newline="\n")
        record.update({"status": "local_or_transport_error", "elapsed_seconds": round(time.time() - started, 3), "error_text": error_text})
        (attempt_dir / f"{tx}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        return {"method": method, "raw_path": str(raw_path.relative_to(run_dir)).replace("\\", "/"), "stderr_path": str(stderr_path.relative_to(run_dir)).replace("\\", "/"), "response": {"error": {"message": error_text}}, "attempt": record}


def verify_row(row: dict, responses: dict[str, dict]) -> dict:
    tx = row["transaction_hash"].lower()
    tx_result = (responses.get("eth_getTransactionByHash", {}).get("response") or {}).get("result")
    receipt_result = (responses.get("eth_getTransactionReceipt", {}).get("response") or {}).get("result")
    trace_response = responses.get("debug_traceTransaction", {}).get("response") or {}
    trace_result = trace_response.get("result")
    reasons = []
    tx_hash = str((tx_result or {}).get("hash") or "").lower()
    receipt_hash = str((receipt_result or {}).get("transactionHash") or "").lower()
    tx_block = (tx_result or {}).get("blockNumber")
    receipt_block = (receipt_result or {}).get("blockNumber")
    if tx_hash != tx:
        reasons.append("transaction.hash_mismatch")
    if receipt_hash != tx:
        reasons.append("receipt.transactionHash_mismatch")
    if tx_block in (None, "", "0x", "0x0") or receipt_block in (None, "", "0x", "0x0"):
        reasons.append("transaction.pending")
    if tx_block != receipt_block:
        reasons.append("transaction_receipt.block_number_mismatch")
    if not isinstance(trace_result, dict):
        reasons.append("trace.invalid_or_missing_callTracer_result")
    if trace_response.get("error") is not None:
        reasons.append("trace.rpc_error")
    return {"transaction_hash": tx, "incident_name": row["incident_name"], "verified": not reasons, "exclusion_reasons": reasons, "transaction_hash_returned": tx_hash, "receipt_transaction_hash_returned": receipt_hash, "transaction_block_number": tx_block, "receipt_block_number": receipt_block, "trace_valid": isinstance(trace_result, dict), "responses": {key: {"raw_path": value.get("raw_path"), "stderr_path": value.get("stderr_path")} for key, value in responses.items()}}


def main() -> int:
    frozen_hash()
    endpoint, secrets = config()
    batch = load(BATCH)
    run_name = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir = PHASE / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "collection_stderr.log").write_text("", encoding="utf-8", newline="\n")
    request_id = 1
    all_verification = []
    paid_stop = None
    for row in batch["rows"]:
        tx = row["transaction_hash"].lower()
        responses = {}
        failed_methods = []
        for method in METHODS:
            result = post(endpoint, method, tx, request_id, run_dir, secrets)
            request_id += 1
            responses[method] = result
            if result["attempt"].get("status") not in {"http_ok"} or (result["response"].get("error") if isinstance(result["response"], dict) else None) is not None:
                failed_methods.append(method)
            if method != METHODS[-1]:
                time.sleep(0.5)
        check = verify_row(row, responses)
        if failed_methods:
            check["exclusion_reasons"].extend(f"request.failed:{method}" for method in failed_methods if f"request.failed:{method}" not in check["exclusion_reasons"])
            check["verified"] = False
        check["request_failed_methods"] = failed_methods
        all_verification.append(check)
        (run_dir / "verification_rows").mkdir(exist_ok=True)
        (run_dir / "verification_rows" / f"{tx}.json").write_text(json.dumps(check, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        if paid_stop:
            break
    verified = sum(item["verified"] for item in all_verification)
    excluded = len(all_verification) - verified
    summary = {"label": "Batch B, pre-registered, one-shot, ETH only, DeFiHackLabs-sourced", "producer_commit": PRODUCER_COMMIT, "frozen_batch_sha256": EXPECTED_HASH, "network_calls": True, "endpoint": "configured dRPC endpoint (URL/key withheld)", "methods": list(METHODS), "request_pacing_seconds": 0.5, "run_directory": str(run_dir.relative_to(PHASE)).replace("\\", "/"), "rows_attempted": len(all_verification), "rows_remaining_after_stop": len(batch["rows"]) - len(all_verification), "verified_count": verified, "excluded_count": excluded, "verification_rows": all_verification, "paid_plan_stop": paid_stop, "scoring_allowed": verified >= 10 and paid_stop is None}
    (run_dir / "verification_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"run_directory": summary["run_directory"], "rows_attempted": summary["rows_attempted"], "verified": verified, "excluded": excluded, "remaining": summary["rows_remaining_after_stop"], "paid_plan_stop": bool(paid_stop), "scoring_allowed": summary["scoring_allowed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
