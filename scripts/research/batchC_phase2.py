"""Batch C phase-2 trace and one-shot scoring runner.

This module is deliberately scoped to the frozen Batch C artifact.  ``trace``
uses only the configured dRPC load balancer, records a pre-scoring verification
ledger, and never imports or reads any other batch artifact.  ``score`` consumes
only that ledger's saved transaction/receipt/trace responses, invokes the
current frozen ranker once per verified row, and writes one scoring result.

Credentials are loaded into memory from the process environment or the local
``.env`` file.  They are never printed or persisted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from statistics import mean
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evidence_manifest import CHAIN_IDS
from faultseeker.data_collection.txn_info_collector import TransactionInfoCollector
from faultseeker.data_collection.txn_sequencer import TransactionSequencer
from faultseeker.function_analysis.function_ranker import FunctionRanker
from faultseeker.utils.rpc_provider import normalize_trace_node


BATCH_PATH = ROOT / "reports/new_batches/batchC/batchC_candidates.json"
PHASE_ROOT = ROOT / "reports/new_batches/batchC/phase2"
EXPECTED_BATCH_SHA256 = "3ab15ab445e00613b1fb7a48e32c94f22f7a03f451182ff2fac5912b3aaa2dc2"
EXPECTED_RANKER_COMMIT = "e6f8da0271f00223346a74ffcf32bb34b54383dd"
RPC_METHODS = (
    "eth_chainId",
    "eth_getTransactionByHash",
    "eth_getTransactionReceipt",
    "debug_traceTransaction",
)
CHAIN_ID_ETH = 1
REQUEST_INTERVAL_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_SECONDS = (2.0, 4.0, 8.0)
BILLING_PROMPT = re.compile(
    r"\b(?:upgrade|paid\s+plan|billing|payment|credit\s+card|add\s+(?:a\s+)?card)\b",
    re.IGNORECASE,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_hash(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("artifact_sha256", None)
    return hashlib.sha256(
        (json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest()


def _verify_frozen_inputs() -> dict[str, str]:
    import subprocess

    batch = _load_json(BATCH_PATH)
    stored = str(batch.get("artifact_sha256", ""))
    recomputed = _artifact_hash(batch)
    ranker = subprocess.check_output(
        ["git", "rev-parse", EXPECTED_RANKER_COMMIT], cwd=ROOT, text=True
    ).strip()
    if ranker != EXPECTED_RANKER_COMMIT:
        raise RuntimeError("frozen ranker commit changed")
    if stored != recomputed or recomputed != EXPECTED_BATCH_SHA256:
        raise RuntimeError("frozen Batch C artifact hash changed")
    return {"ranker_commit": ranker, "batch_sha256": recomputed}


def _credentials() -> tuple[str, str]:
    values = dotenv_values(ROOT / ".env")
    endpoint = os.environ.get("DRPC_RPC_URL") or str(values.get("DRPC_RPC_URL") or "")
    api_key = os.environ.get("DRPC_API_KEY") or str(values.get("DRPC_API_KEY") or "")
    if not endpoint or not api_key:
        raise RuntimeError("DRPC_RPC_URL or DRPC_API_KEY is not set")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or parsed.hostname != "lb.drpc.live":
        raise RuntimeError("configured endpoint is not the approved dRPC load balancer")
    return endpoint, api_key


def _redact(value: Any, endpoint: str, api_key: str) -> Any:
    if isinstance(value, str):
        return value.replace(endpoint, "[RPC_URL_REDACTED]").replace(
            api_key, "[API_KEY_REDACTED]"
        )[:20000]
    if isinstance(value, dict):
        return {str(k): _redact(v, endpoint, api_key) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, endpoint, api_key) for v in value]
    return value


def _contains_billing(value: Any) -> bool:
    if isinstance(value, str):
        return bool(BILLING_PROMPT.search(value))
    if isinstance(value, dict):
        return any(_contains_billing(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_billing(v) for v in value)
    return False


def _billing_preview(value: Any) -> str:
    if isinstance(value, str):
        return value[:500]
    try:
        return json.dumps(value, sort_keys=True, default=str)[:500]
    except (TypeError, ValueError):
        return str(value)[:500]


def _is_rate_limited(http_status: int | None, body: Any) -> bool:
    if http_status == 429:
        return True
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        code = body["error"].get("code")
        message = str(body["error"].get("message", ""))
        return code in {429, -32005, -32016} or "rate limit" in message.lower()
    return False


def _rpc_once(endpoint: str, method: str, params: list[Any]) -> tuple[dict[str, Any], str]:
    request = Request(
        endpoint,
        data=json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {"http_status": response.status, "body": json.loads(raw)}, ""
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            body: Any = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return {"http_status": error.code, "body": body}, raw
    except (OSError, TimeoutError, URLError) as error:
        return {
            "http_status": None,
            "body": None,
            "error_type": type(error).__name__,
        }, str(error)


def _rpc(
    endpoint: str,
    method: str,
    params: list[Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        if state["request_count"]:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        state["request_count"] += 1
        response, stderr = _rpc_once(endpoint, method, params)
        body = response.get("body")
        if _contains_billing(stderr) or _contains_billing(body):
            state["billing_prompt_detected"] = True
            error = body.get("error") if isinstance(body, dict) else None
            trigger = {
                "http_status": response.get("http_status"),
                "json_error_code": error.get("code") if isinstance(error, dict) else None,
                "json_error_message": error.get("message") if isinstance(error, dict) else None,
                "stderr_preview": _billing_preview(stderr),
                "body_preview": _billing_preview(body),
                "method": method,
                "row_index": state.get("row_index"),
            }
            _write_json(
                Path(state["run_dir"]) / "billing_trigger.json",
                _redact(trigger, endpoint, state.get("api_key", "")),
            )
            raise RuntimeError("dRPC billing/upgrade prompt or error detected")
        if not _is_rate_limited(response.get("http_status"), body):
            response["stderr"] = stderr[:20000]
            return response
        state["rate_limit_hits"] += 1
        if attempt >= RATE_LIMIT_RETRIES:
            response["stderr"] = stderr[:20000]
            return response
        delay = RATE_LIMIT_BACKOFF_SECONDS[attempt]
        state["backoff_seconds"] += delay
        time.sleep(delay)
    raise AssertionError("unreachable")


def _batch_rows() -> list[dict[str, Any]]:
    batch = _load_json(BATCH_PATH)
    rows = list(batch.get("rows") or [])
    if len(rows) != 30:
        raise RuntimeError(f"expected 30 Batch C rows, found {len(rows)}")
    return rows


def _valid_trace(result: Any) -> bool:
    return isinstance(result, dict) and bool(
        result.get("type") or result.get("callType") or result.get("action")
    )


def _trace_row(endpoint: str, label: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    tx = str(label["transaction_hash"]).lower()
    responses: dict[str, dict[str, Any]] = {}
    failure_reasons: list[str] = []
    for method, params in (
        ("eth_chainId", []),
        ("eth_getTransactionByHash", [tx]),
        ("eth_getTransactionReceipt", [tx]),
        ("debug_traceTransaction", [tx, {"tracer": "callTracer", "timeout": "15s"}]),
    ):
        try:
            response = _rpc(endpoint, method, params, state)
        except RuntimeError:
            raise
        responses[method] = response
        body = response.get("body")
        if not isinstance(body, dict) or body.get("error") or body.get("result") is None:
            failure_reasons.append(f"request_failed:{method}")

    chain_body = responses["eth_chainId"].get("body")
    if not isinstance(chain_body, dict) or chain_body.get("result") != "0x1":
        failure_reasons.append("wrong_or_missing_chain_id")

    tx_body = responses["eth_getTransactionByHash"].get("body")
    tx_result = tx_body.get("result") if isinstance(tx_body, dict) else None
    receipt_body = responses["eth_getTransactionReceipt"].get("body")
    receipt_result = receipt_body.get("result") if isinstance(receipt_body, dict) else None
    trace_body = responses["debug_traceTransaction"].get("body")
    trace_result = trace_body.get("result") if isinstance(trace_body, dict) else None

    if not isinstance(tx_result, dict):
        failure_reasons.append("transaction_lookup_failed")
    else:
        if str(tx_result.get("hash", "")).lower() != tx:
            failure_reasons.append("transaction_hash_mismatch")
        if not tx_result.get("blockNumber"):
            failure_reasons.append("transaction_pending")

    if not isinstance(receipt_result, dict):
        failure_reasons.append("receipt_lookup_failed")
    else:
        if str(receipt_result.get("transactionHash", "")).lower() != tx:
            failure_reasons.append("receipt_transaction_hash_mismatch")

    if isinstance(tx_result, dict) and isinstance(receipt_result, dict):
        if tx_result.get("blockNumber") != receipt_result.get("blockNumber"):
            failure_reasons.append("block_number_mismatch")

    if not _valid_trace(trace_result):
        failure_reasons.append("trace_invalid_or_missing_callTracer_result")

    return {
        "transaction_hash": tx,
        "incident_name": label["incident_name"],
        "verified": not failure_reasons,
        "exclusion_reasons": sorted(set(failure_reasons)),
        "responses": responses,
        "transaction": tx_result,
        "receipt": receipt_result,
        "trace": trace_result,
    }


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")


def trace(run_dir: Path) -> int:
    frozen = _verify_frozen_inputs()
    endpoint, _api_key = _credentials()
    run_dir.mkdir(parents=True, exist_ok=False)
    state = {
        "request_count": 0,
        "rate_limit_hits": 0,
        "backoff_seconds": 0.0,
        "billing_prompt_detected": False,
        "run_dir": run_dir,
        "api_key": _api_key,
    }
    rows = _batch_rows()
    verification_rows: list[dict[str, Any]] = []
    try:
        for row_index, label in enumerate(rows, start=1):
            state["row_index"] = row_index
            result = _trace_row(endpoint, label, state)
            safe_responses = _redact(result["responses"], endpoint, _api_key)
            result["responses"] = safe_responses
            raw_path = run_dir / "trace_raw" / f"{result['transaction_hash']}.json"
            _write_json(raw_path, result)
            verification_rows.append(
                {
                    "transaction_hash": result["transaction_hash"],
                    "incident_name": result["incident_name"],
                    "verified": result["verified"],
                    "exclusion_reasons": result["exclusion_reasons"],
                    "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
    except RuntimeError:
        # Do not turn a billing stop into an ordinary row exclusion.
        manifest = {
            "status": "STOPPED_BILLING_PROMPT" if state["billing_prompt_detected"] else "STOPPED_ERROR",
            "frozen": frozen,
            "provider": "dRPC",
            "rpc_methods": list(RPC_METHODS),
            "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
            "verification_rows": verification_rows,
            "rows_attempted": len(verification_rows),
            "rows_total": len(rows),
            "rate_limit_hits": state["rate_limit_hits"],
            "backoff_seconds": state["backoff_seconds"],
            "billing_prompt_detected": state["billing_prompt_detected"],
        }
        _write_json(run_dir / "verification.json", manifest)
        raise

    manifest = {
        "status": "COMPLETED",
        "frozen": frozen,
        "provider": "dRPC",
        "rpc_methods": list(RPC_METHODS),
        "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
        "verification_rows": verification_rows,
        "rows_attempted": len(verification_rows),
        "rows_total": len(rows),
        "verified_count": sum(row["verified"] for row in verification_rows),
        "excluded_count": sum(not row["verified"] for row in verification_rows),
        "rate_limit_hits": state["rate_limit_hits"],
        "backoff_seconds": state["backoff_seconds"],
        "billing_prompt_detected": state["billing_prompt_detected"],
        "scoring_allowed": True,
    }
    _write_json(run_dir / "verification.json", manifest)
    print(json.dumps({
        "status": manifest["status"],
        "provider": manifest["provider"],
        "requests_used": manifest["rpc_methods"],
        "rows_attempted": manifest["rows_attempted"],
        "verified_count": manifest["verified_count"],
        "excluded_count": manifest["excluded_count"],
        "rate_limit_hits": manifest["rate_limit_hits"],
        "backoff_seconds": manifest["backoff_seconds"],
        "billing_prompt_detected": manifest["billing_prompt_detected"],
    }, sort_keys=True))
    return 0


class _CapturedSequencer(TransactionSequencer):
    def __init__(self, structured: dict[str, Any]):
        super().__init__()
        self.structured = structured

    def run(self, txn_hash: str, chain: str):
        if txn_hash != self.structured["transaction_hash"] or chain != "eth":
            raise ValueError("captured sequence identity mismatch")
        return self.from_structured(deepcopy(self.structured))


class _CapturedInfo:
    def __init__(self, transaction: dict[str, Any], receipt: dict[str, Any], tx: str):
        self.transaction = transaction
        self.receipt = receipt
        self.tx = tx

    def run(self, txn_hash: str, chain: str):
        if txn_hash != self.tx or chain != "eth":
            raise ValueError("captured RPC identity mismatch")
        info = TransactionInfoCollector.from_rpc(
            self.transaction, self.receipt, txn_hash
        )
        if not info:
            raise ValueError("captured RPC normalization failed")
        return deepcopy(info)


def _rank_from_trace(row: dict[str, Any]) -> list[dict[str, Any]]:
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator

    trace = normalize_trace_node(row["trace"])
    structured = {
        "transaction_hash": row["transaction_hash"],
        "chain": "eth",
        "trace": trace,
        "storage_events": [],
        "storage_reads": [],
        "state_diff": {},
        "trace_coverage": {
            "trace_complete": True,
            "storage_trace_complete": False,
            "token_flow_complete": False,
            "multi_tx_context_complete": False,
        },
    }
    orchestrator = ForensicsOrchestrator(
        model="llm-free-function-ranker",
        txn_sequencer=_CapturedSequencer(structured),
        txn_info_collector=_CapturedInfo(
            row["transaction"], row["receipt"], row["transaction_hash"]
        ),
    )
    forensics_result, _, _ = orchestrator.run(row["transaction_hash"], "eth")
    tx_analysis = {
        "repeated_patterns": forensics_result.repeated_patterns,
        "function_call_loc_memo": forensics_result.function_call_loc_memo,
    }
    return [dict(item) for item in FunctionRanker().rank(
        forensics_result, tx_analysis
    ).ranked_functions]


def _rank_metrics(ranks: list[int | None]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for k in (1, 3, 5):
        hits = sum(rank is not None and rank <= k for rank in ranks)
        result[f"R@{k}"] = {
            "hits": hits,
            "n": len(ranks),
            "recall": hits / len(ranks) if ranks else 0.0,
            "wilson_95": _wilson(hits, len(ranks)),
        }
    return result


def _wilson(hits: int, n: int) -> dict[str, float]:
    if not n:
        return {"lower": 0.0, "upper": 0.0}
    z = 1.959963984540054
    p = hits / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    half = z * ((p * (1.0 - p) / n) + (z * z / (4.0 * n * n))) ** 0.5 / denominator
    return {"lower": max(0.0, center - half), "upper": min(1.0, center + half)}


def _ranks(predictions: list[dict[str, Any]], label: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    target_address = str(label["vulnerable_contract_address"]).lower()
    target_selector = str(label["selector"]).lower()
    address_rank = selector_rank = pair_rank = None
    for index, prediction in enumerate(predictions, 1):
        address = str(prediction.get("code_address") or prediction.get("address") or "").lower()
        value = str(prediction.get("selector") or prediction.get("function") or "").lower()
        selector = value if value.startswith("0x") and len(value) == 10 else ""
        if address_rank is None and address == target_address:
            address_rank = index
        if selector_rank is None and selector == target_selector:
            selector_rank = index
        if pair_rank is None and address == target_address and selector == target_selector:
            pair_rank = index
    return pair_rank, address_rank, selector_rank


def score(run_dir: Path) -> int:
    frozen = _verify_frozen_inputs()
    verification = _load_json(run_dir / "verification.json")
    if verification.get("status") != "COMPLETED":
        raise RuntimeError("verification did not complete; scoring is blocked")
    if verification.get("billing_prompt_detected"):
        raise RuntimeError("billing prompt was detected; scoring is blocked")
    scoring_path = run_dir / "scoring.json"
    if scoring_path.exists():
        raise RuntimeError("scoring.json already exists; the one-shot score cannot be rerun")

    labels = {
        str(row["transaction_hash"]).lower(): row for row in _batch_rows()
    }
    verified = [row for row in verification["verification_rows"] if row["verified"]]
    all_predictions: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    score_rows: list[dict[str, Any]] = []
    for verification_row in verified:
        raw = _load_json(ROOT / verification_row["raw_path"])
        predictions = _rank_from_trace(raw)
        all_predictions.append((verification_row, predictions))
        pair_rank, address_rank, selector_rank = _ranks(
            predictions, labels[verification_row["transaction_hash"]]
        )
        score_rows.append({
            "transaction_hash": verification_row["transaction_hash"],
            "incident_name": verification_row["incident_name"],
            "candidate_count": len(predictions),
            "address_selector_rank": pair_rank,
            "address_only_rank": address_rank,
            "selector_only_rank": selector_rank,
        })

    primary = [row["address_selector_rank"] for row in score_rows]
    addresses = [row["address_only_rank"] for row in score_rows]
    selectors = [row["selector_only_rank"] for row in score_rows]
    scoring = {
        "status": "SCORED_ONCE",
        "label": "Batch C, pre-registered, one-shot, Ethereum mainnet, DeFiHackLabs-sourced",
        "frozen": frozen,
        "provider": "dRPC",
        "verified_n": len(score_rows),
        "scoring_passes": 1,
        "ranker_invocations": len(score_rows),
        "tuning": False,
        "partial_result_peeking": False,
        "metrics": {
            "address_selector_primary": _rank_metrics(primary),
            "address_only_sensitivity": _rank_metrics(addresses),
            "selector_only_sensitivity": _rank_metrics(selectors),
        },
        "rows": score_rows,
    }

    # Persist candidate lists only after every verified row has been processed,
    # preventing a partial score artifact from being mistaken for the final pass.
    for verification_row, predictions in all_predictions:
        _write_json(
            run_dir / "candidates" / f"{verification_row['transaction_hash']}.json",
            {
                "transaction_hash": verification_row["transaction_hash"],
                "candidate_count": len(predictions),
                "predictions": predictions,
            },
        )
    _write_json(scoring_path, scoring)
    _write_results(run_dir, verification, scoring)
    print(json.dumps({
        "status": scoring["status"],
        "verified_n": scoring["verified_n"],
        "ranker_invocations": scoring["ranker_invocations"],
        "scoring_passes": scoring["scoring_passes"],
        "metrics": scoring["metrics"],
        "excluded_count": verification["excluded_count"],
    }, sort_keys=True))
    return 0


def _fmt_metric(metric: dict[str, Any]) -> str:
    return " ".join(
        f"{key}={metric[key]['hits']}/{metric[key]['n']} "
        f"({metric[key]['recall'] * 100:.2f}%; "
        f"Wilson95% {metric[key]['wilson_95']['lower'] * 100:.2f}-{metric[key]['wilson_95']['upper'] * 100:.2f}%)"
        for key in ("R@1", "R@3", "R@5")
    )


def _write_results(run_dir: Path, verification: dict[str, Any], scoring: dict[str, Any]) -> None:
    lines = [
        "# Batch C phase 2 results",
        "",
        "**Pre-registered, scored once. Batch C is spent after this run.**",
        "",
        "No ranker, scorer, weight, threshold, label, or frozen artifact was changed. No result was used to tune or rerun scoring.",
        "",
        f"- Frozen ranker commit: `{scoring['frozen']['ranker_commit']}`",
        f"- Frozen Batch C artifact SHA-256: `{scoring['frozen']['batch_sha256']}`",
        f"- Provider: `{scoring['provider']}`",
        f"- Verified scoring N: **{scoring['verified_n']}**",
        f"- Excluded before scoring: **{verification['excluded_count']}**",
        f"- Scoring passes: **{scoring['scoring_passes']}**",
        "",
        "## Metrics",
        "",
        "Wilson intervals are two-sided 95% Wilson score intervals.",
        "",
        "| Key | R@1 | R@3 | R@5 |",
        "| --- | --- | --- | --- |",
    ]
    for key, label in (
        ("address_selector_primary", "Address + selector (primary)"),
        ("address_only_sensitivity", "Address-only sensitivity"),
        ("selector_only_sensitivity", "Selector-only sensitivity"),
    ):
        metric = scoring["metrics"][key]
        cells = []
        for k in ("R@1", "R@3", "R@5"):
            item = metric[k]
            cells.append(
                f"{item['hits']}/{item['n']} ({item['recall'] * 100:.2f}%; "
                f"{item['wilson_95']['lower'] * 100:.2f}-{item['wilson_95']['upper'] * 100:.2f}%)"
            )
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", "## Pre-scoring exclusions", "", "| Transaction | Incident | Reason |", "| --- | --- | --- |"]
    for row in verification["verification_rows"]:
        if not row["verified"]:
            lines.append(
                f"| `{row['transaction_hash']}` | {row['incident_name']} | "
                f"{'; '.join(row['exclusion_reasons'])} |"
            )
    if verification["excluded_count"] == 0:
        lines.append("| — | — | None |")
    lines += ["", "Batch C is spent and sealed after this single final scoring pass.", ""]
    (run_dir / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    trace_parser = sub.add_parser("trace")
    trace_parser.add_argument("--run-dir", type=Path, default=None)
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "trace":
        run_dir = args.run_dir or PHASE_ROOT / _run_id()
        return trace(run_dir.resolve())
    return score(args.run_dir.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
