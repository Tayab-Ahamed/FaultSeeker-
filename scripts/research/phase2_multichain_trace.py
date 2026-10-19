"""Bounded, low-rate labeled multi-chain RPC trace run.

The runner uses only the configured dRPC free-tier endpoint, selects at most
five labeled transactions per chain, preserves every attempt separately, and
redacts the credential-bearing URL from persisted diagnostics. It does not
infer opcode/storage evidence from a call trace.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import sys

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evidence_manifest import CHAIN_IDS
from scripts.rebuild_authentic_cohort import drpc_url


SOURCE = ROOT / "benchmark/benchmark_classification_fixed.csv"
DEFAULT_OUTPUT = ROOT / "reports/external_runs/phase2/20261017T011500Z"
REQUEST_INTERVAL_SECONDS = 0.5
MAX_ATTEMPTS = 2
MAX_CONSECUTIVE_FAILURES = 10
TIMEOUT_SECONDS = 30
BILLING_PROMPT = re.compile(r"\b(?:upgrade|paid plan|billing|payment|card|credit card)\b", re.IGNORECASE)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _redact(text: str, endpoint: str, key: str) -> str:
    value = str(text)
    if endpoint:
        value = value.replace(endpoint, "[RPC_URL_REDACTED]")
    if key:
        value = value.replace(key, "[API_KEY_REDACTED]")
    return value[:20000]


def _load_endpoint() -> tuple[str, str]:
    values = dotenv_values(ROOT / ".env")
    raw = os.environ.get("DRPC_RPC_URL") or values.get("DRPC_RPC_URL") or ""
    key = os.environ.get("DRPC_API_KEY") or values.get("DRPC_API_KEY") or ""
    if not raw or not key:
        raise RuntimeError("DRPC_API_KEY or DRPC_RPC_URL missing")
    parsed = urlsplit(raw)
    if parsed.scheme != "https" or parsed.hostname != "lb.drpc.live":
        raise RuntimeError("configured endpoint is not the approved dRPC load balancer")
    return raw, key


def _select_rows() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            chain = row["chain"].strip().lower()
            if chain not in CHAIN_IDS:
                continue
            grouped.setdefault(chain, [])
            if len(grouped[chain]) < 5:
                grouped[chain].append({
                    "chain": chain,
                    "txn_hash": row["txn_hash"].strip().lower(),
                    "name": row.get("name", ""),
                    "vuln_type": row.get("vuln_type", ""),
                })
    return dict(sorted(grouped.items()))


def _rpc(endpoint: str, key: str, method: str, params: list[object]) -> tuple[dict, str]:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {"http_status": response.status, "body": json.loads(body)}, ""
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return {"http_status": error.code, "body": body}, body
    except (URLError, TimeoutError, OSError) as error:
        return {"http_status": None, "body": None, "error_type": type(error).__name__}, str(error)


def _attempt(output: Path, endpoint: str, key: str, row: dict[str, str], attempt: int) -> dict:
    chain = row["chain"]
    tx = row["txn_hash"]
    raw_path = output / "drpc" / "raw" / chain / f"{tx}.attempt{attempt}.json"
    stderr_path = output / "drpc" / "stderr" / chain / f"{tx}.attempt{attempt}.txt"
    chain_endpoint = drpc_url(endpoint, chain)
    requests = []
    failure_causes = []
    billing_stop = False
    for method, params in [
        ("eth_chainId", []),
        ("eth_getTransactionByHash", [tx]),
        ("eth_getTransactionReceipt", [tx]),
        ("debug_traceTransaction", [tx, {"tracer": "callTracer", "timeout": "15s"}]),
    ]:
        time.sleep(REQUEST_INTERVAL_SECONDS)
        result, stderr = _rpc(chain_endpoint, key, method, params)
        record = {"method": method, "response": result}
        requests.append(record)
        if stderr:
            safe_stderr = _redact(stderr, chain_endpoint, key)
            failure_causes.append({"method": method, "stderr": safe_stderr})
            if BILLING_PROMPT.search(safe_stderr):
                billing_stop = True
        body = result.get("body")
        if not isinstance(body, dict) or body.get("error") or body.get("result") is None:
            failure_causes.append({
                "method": method,
                "rpc_code": body.get("error", {}).get("code") if isinstance(body, dict) else None,
                "status": result.get("http_status"),
            })
        if billing_stop:
            break
    chain_result = requests[0]["response"].get("body") if requests else None
    observed_chain_id = None
    if isinstance(chain_result, dict) and chain_result.get("result"):
        try:
            observed_chain_id = int(chain_result["result"], 16)
        except (TypeError, ValueError):
            failure_causes.append({"method": "eth_chainId", "cause": "invalid_chain_id"})
    if observed_chain_id != CHAIN_IDS[chain]:
        failure_causes.append({"method": "eth_chainId", "cause": "wrong_or_missing_chain", "observed": observed_chain_id})
    trace_body = requests[-1]["response"].get("body") if requests else None
    success = not failure_causes and isinstance(trace_body, dict) and trace_body.get("result") is not None
    record = {
        "attempt": attempt,
        "chain": chain,
        "transaction_hash": tx,
        "label": {"name": row["name"], "vuln_type": row["vuln_type"]},
        "provider": "dRPC",
        "status": "CAPTURED" if success else "FAILED",
        "billing_prompt_detected": billing_stop,
        "observed_chain_id": observed_chain_id,
        "requests": requests,
        "failure_causes": failure_causes,
        "stderr_artifact": str(stderr_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_artifact": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(raw_path, record)
    stderr_text = "\n".join(
        item["stderr"] for item in failure_causes if "stderr" in item
    )
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.write_text(stderr_text + ("\n" if stderr_text else ""), encoding="utf-8")
    return record


def run(output: Path = DEFAULT_OUTPUT) -> dict:
    endpoint, key = _load_endpoint()
    selected = _select_rows()
    manifest = {
        "run": "phase2-multichain-labeled-traces",
        "provider": "dRPC",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rate_limit": {"request_interval_seconds": REQUEST_INTERVAL_SECONDS, "max_consecutive_failures": MAX_CONSECUTIVE_FAILURES},
        "selection": {chain: [r["txn_hash"] for r in rows] for chain, rows in selected.items()},
        "chains": {},
        "status": "RUNNING",
    }
    output.mkdir(parents=True, exist_ok=True)
    consecutive_failures = 0
    stopped = False
    for chain, rows in selected.items():
        chain_result = {"selected": len(rows), "attempts": [], "successes": 0, "failures": 0}
        for row in rows:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    stopped = True
                    break
                result = _attempt(output, endpoint, key, row, attempt)
                chain_result["attempts"].append({
                    "transaction_hash": row["txn_hash"],
                    "attempt": attempt,
                    "status": result["status"],
                    "failure_causes": result["failure_causes"],
                })
                if result["status"] == "CAPTURED":
                    chain_result["successes"] += 1
                    consecutive_failures = 0
                    break
                if result.get("billing_prompt_detected"):
                    stopped = True
                    manifest["status"] = "STOPPED-BILLING-PROMPT"
                    manifest["billing_prompt"] = True
                    break
                chain_result["failures"] += 1
                consecutive_failures += 1
            if stopped:
                break
        manifest["chains"][chain] = chain_result
        if stopped:
            break
    manifest["consecutive_failures_at_stop"] = consecutive_failures
    manifest["status"] = "STOPPED-10-CONSECUTIVE-FAILURES" if stopped else "COMPLETED"
    _write(output / "drpc" / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    report = run()
    print(json.dumps({"status": report["status"], "chains": report["chains"]}, indent=2))
