"""Run the read-only 70d1 audit and one producer-era Batch A replay.

The only network calls in this file are the two explicitly requested Ethereum
JSON-RPC methods.  The endpoint is read from the private environment/.env and
is never printed or written to an artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ARCHIVAL = "240fd9fae9cb56a96f45f37d21a90cf094abc467"
RESCORED = "70d1b099c0b1dad524bc89ba4e707ea94b7038b9"
PRODUCER = "1b1c7395771663622dd14b9731b4b8b471221960"
RAW_PREFIX = "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw/"
VALID_SET = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
EXPECTED_BATCH_SHA = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
EXPECTED_VALID_SHA = "fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785"
MODEL = "llm-free-function-ranker"
SCORE_FIELDS = ("first_hit_rank", "recall_at_1", "recall_at_3", "recall_at_5")
RPC_METHODS = ("eth_getTransactionByHash", "eth_getTransactionReceipt")
PAID_TERMS = ("paid plan", "billing", "credit card", "card required", "payment required", "upgrade", "quota exceeded", "credits required")


class PaidPlanPrompt(RuntimeError):
    pass


class FetchFailed(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_batch_sha(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("artifact_sha256", None)
    return hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode()).hexdigest()


def git_archive(commit: str) -> dict[str, dict[str, Any]]:
    proc = subprocess.run(["git", "archive", commit, RAW_PREFIX[:-1]], cwd=ROOT, stdout=subprocess.PIPE, check=True)
    archive = tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:")
    result: dict[str, dict[str, Any]] = {}
    for member in archive.getmembers():
        if member.isfile() and member.name.startswith(RAW_PREFIX):
            result[member.name[len(RAW_PREFIX):]] = json.loads(archive.extractfile(member).read())
    return result


def job1_audit() -> dict[str, Any]:
    old = git_archive(ARCHIVAL)
    new = git_archive(RESCORED)
    affected: list[dict[str, Any]] = []
    for filename, current in sorted(new.items()):
        if current.get("status") != "ok":
            continue
        previous = old[filename]
        old_score = previous.get("score", {})
        new_score = current.get("score", {})
        changed = [field for field in SCORE_FIELDS if old_score.get(field) != new_score.get(field)]
        if not changed:
            continue
        old_prediction_hash = sha256_bytes(json.dumps(previous.get("predictions", []), sort_keys=True, separators=(",", ":")).encode())
        new_prediction_hash = sha256_bytes(json.dumps(current.get("predictions", []), sort_keys=True, separators=(",", ":")).encode())
        affected.append({
            "transaction_hash": filename[:-5],
            "archival_rank_240fd9f": old_score.get("first_hit_rank"),
            "rank_after_70d1b09": new_score.get("first_hit_rank"),
            "changed_fields": changed,
            "prediction_hash_240fd9f": old_prediction_hash,
            "prediction_hash_70d1b09": new_prediction_hash,
            "prediction_list_unchanged": old_prediction_hash == new_prediction_hash,
        })

    return {
        "label": "scope audit, read-only",
        "commit": RESCORED,
        "parent": ARCHIVAL,
        "commit_message": "fix: rescore provider-pinned benchmark offline",
        "diff_summary": {
            "files_changed": 76,
            "insertions": 1135,
            "deletions": 444,
            "source": "git show --stat 70d1b099c0b1dad524bc89ba4e707ea94b7038b9",
        },
        "classification": "offline scoring-rule change applied to stored predictions; prediction lists were not regenerated",
        "scoring_rule_change": {
            "file": "benchmark/honest_eval/localization.py",
            "function": "_prediction_keys",
            "exact_change": "Use prediction['code_address'] as an address fallback when prediction['address'] is absent.",
            "effect_on_stored_score": "rank_of_first_hit can now match provider-pinned predictions that use code_address; recall_at_1/3/5 are then recomputed from that first-hit rank.",
        },
        "offline_application": {
            "file": "scripts/reproduce/finalize_provider_pinned_report.py",
            "function": "rescore_rows",
            "operation": "Recompute target_function_count, first_hit_rank, recall_at_1, recall_at_3, and recall_at_5 from saved predictions and ground truth, then write the score fields back to the raw rows and manifest.",
        },
        "saved_prediction_source": {
            "run_id": "original-v1-pinned-sequential-20261017",
            "script": "scripts/reproduce/run_original_provider_pinned.py",
            "producer_commit": PRODUCER,
            "path_at_archival": "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw/",
        },
        "affected_row_count": len(affected),
        "affected_rows_prediction_hashes_unchanged": all(row["prediction_list_unchanged"] for row in affected),
        "affected_rows": affected,
    }


def read_rpc_url() -> str:
    value = os.environ.get("DRPC_RPC_URL", "").strip()
    if value:
        return value
    dotenv = ROOT / ".env"
    if dotenv.is_file():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DRPC_RPC_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise FetchFailed("DRPC_RPC_URL is not configured")


def response_has_paid_prompt(body: bytes) -> bool:
    text = body.decode("utf-8", errors="replace").lower()
    return any(term in text for term in PAID_TERMS)


def write_raw(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def rpc_call(endpoint: str, method: str, tx: str, raw_path: Path, request_id: int, last_request: list[float]) -> dict[str, Any]:
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": [tx]}).encode()
    for attempt in range(1, 4):
        wait = 0.5 - (time.monotonic() - last_request[0])
        if wait > 0:
            time.sleep(wait)
        last_request[0] = time.monotonic()
        request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                status = int(response.status)
        except HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
            write_raw(raw_path, body)
            if response_has_paid_prompt(body) or status == 402:
                raise PaidPlanPrompt("paid-plan, billing, or card prompt received")
            if status == 429 or status >= 500:
                if attempt < 3:
                    time.sleep(float(attempt))
                    continue
            raise FetchFailed(f"HTTP error status={status} method={method}")
        except (URLError, TimeoutError, OSError):
            if attempt < 3:
                time.sleep(float(attempt))
                continue
            raise FetchFailed(f"network error method={method}")

        write_raw(raw_path, body)
        if response_has_paid_prompt(body) or status == 402:
            raise PaidPlanPrompt("paid-plan, billing, or card prompt received")
        if status >= 400:
            if status == 429 or status >= 500:
                if attempt < 3:
                    time.sleep(float(attempt))
                    continue
            raise FetchFailed(f"HTTP error status={status} method={method}")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise FetchFailed(f"non-JSON response method={method}") from exc
        if response_has_paid_prompt(json.dumps(parsed).encode()):
            raise PaidPlanPrompt("paid-plan, billing, or card prompt received")
        if parsed.get("error") is not None:
            raise FetchFailed(f"JSON-RPC error method={method}")
        if parsed.get("result") is None:
            raise FetchFailed(f"null result method={method}")
        return parsed
    raise FetchFailed(f"network retry limit method={method}")


def batch_preflight(valid: dict[str, Any], batch: dict[str, Any]) -> list[dict[str, Any]]:
    if sha256_file(VALID_SET) != EXPECTED_VALID_SHA:
        raise FetchFailed("valid set SHA-256 mismatch")
    if batch.get("artifact_sha256") != EXPECTED_BATCH_SHA or canonical_batch_sha(batch) != EXPECTED_BATCH_SHA:
        raise FetchFailed("frozen Batch A artifact SHA-256 mismatch")
    records = valid.get("records")
    if not isinstance(records, list) or len(records) != 23:
        raise FetchFailed("valid set does not contain exactly 23 records")
    missing: list[dict[str, Any]] = []
    for record in records:
        trace = record.get("trace") if isinstance(record.get("trace"), dict) else {}
        missing_fields = [key for key in ("transaction_hash", "chain", "trace") if key not in record]
        missing_trace = [key for key in ("from", "to", "type", "input", "calls") if key not in trace]
        if str(record.get("chain", "")).lower() != "eth":
            missing_fields.append("chain=eth")
        if missing_fields or missing_trace:
            missing.append({"transaction_hash": record.get("transaction_hash"), "record": missing_fields, "trace": missing_trace})
    if missing:
        raise FetchFailed("Batch A trace preflight missing required fields")
    return records


def fetch_batch(records: list[dict[str, Any]]) -> dict[str, Any]:
    endpoint = read_rpc_url()
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or "drpc" not in (parsed.hostname or "").lower():
        raise FetchFailed("configured endpoint is not identified as a dRPC endpoint")
    raw_root = OUT / "rpc_raw" / "eth"
    last_request = [0.0]
    rows = []
    request_id = 1
    for record in records:
        tx = str(record["transaction_hash"]).lower()
        tx_path = raw_root / f"{tx}.transaction.json"
        receipt_path = raw_root / f"{tx}.receipt.json"
        tx_response = rpc_call(endpoint, RPC_METHODS[0], tx, tx_path, request_id, last_request)
        request_id += 1
        receipt_response = rpc_call(endpoint, RPC_METHODS[1], tx, receipt_path, request_id, last_request)
        request_id += 1
        rows.append({
            "transaction_hash": tx,
            "transaction_method": RPC_METHODS[0],
            "receipt_method": RPC_METHODS[1],
            "transaction_raw": str(tx_path.relative_to(ROOT)).replace("\\", "/"),
            "receipt_raw": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "transaction_response_sha256": sha256_file(tx_path),
            "receipt_response_sha256": sha256_file(receipt_path),
            "transaction_result_present": tx_response.get("result") is not None,
            "receipt_result_present": receipt_response.get("result") is not None,
        })
        print(f"fetched {len(rows)}/{len(records)}")
    result = {"status": "COMPLETE", "network_calls": len(records) * 2, "methods": list(RPC_METHODS), "rows": rows}
    (OUT / "fetch_manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def load_current_localization():
    path = ROOT / "benchmark/honest_eval/localization.py"
    spec = importlib.util.spec_from_file_location("batchA_current_localization", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rank_metrics(ranks: list[int | None]) -> dict[str, Any]:
    def one(k: int) -> dict[str, Any]:
        hits = sum(rank is not None and rank <= k for rank in ranks)
        return {"hits": hits, "n": len(ranks), "recall": hits / len(ranks) if ranks else 0.0}
    return {"r_at_1": one(1), "r_at_3": one(3), "r_at_5": one(5)}


def producer_replay(records: list[dict[str, Any]], labels: dict[str, dict[str, Any]], producer_root: Path) -> dict[str, Any]:
    output_json = OUT / "producer_batchA_measurement.json"
    output_md = OUT / "producer_batchA_measurement.md"
    if output_json.exists() or output_md.exists():
        raise FetchFailed("producer-era scoring output already exists; refusing a second scoring run")
    import sys
    if str(producer_root) not in sys.path:
        sys.path.insert(0, str(producer_root))
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.function_analysis.function_ranker import FunctionRanker
    from faultseeker.utils.rpc_provider import normalize_trace_node
    loc = load_current_localization()
    loc._register_fn_names(str(row["vulnerable_function"]) for row in labels.values())
    rows = []
    primary: list[int | None] = []
    function_only: list[int | None] = []
    address_only: list[int | None] = []
    for record in records:
        tx = str(record["transaction_hash"]).lower()
        tx_response = json.loads((OUT / "rpc_raw" / "eth" / f"{tx}.transaction.json").read_text(encoding="utf-8"))
        receipt_response = json.loads((OUT / "rpc_raw" / "eth" / f"{tx}.receipt.json").read_text(encoding="utf-8"))
        canonical = normalize_trace_node(record["trace"])
        structured = {
            "transaction_hash": tx,
            "chain": "eth",
            "trace": canonical,
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
            model=MODEL,
            txn_sequencer=_CapturedSequencer(structured),
            txn_info_collector=_CapturedInfo(tx_response["result"], receipt_response["result"], tx, "eth"),
        )
        result, _txn_seq, _txn_info = orchestrator.run(tx, "eth")
        tx_analysis = {"repeated_patterns": result.repeated_patterns, "function_call_loc_memo": result.function_call_loc_memo}
        predictions = [dict(item) for item in FunctionRanker().rank(result, tx_analysis).ranked_functions]
        label = labels[tx]
        target_address = loc._norm_addr(str(label["vulnerable_contract"]))
        target_function = loc._norm_fn(str(label["vulnerable_function"]))
        p_rank = f_rank = a_rank = None
        for index, prediction in enumerate(predictions, start=1):
            key, _ = loc._prediction_keys(prediction)
            if key is None:
                continue
            address, function = key
            if a_rank is None and address == target_address:
                a_rank = index
            if f_rank is None and function == target_function:
                f_rank = index
            if p_rank is None and address == target_address and function == target_function:
                p_rank = index
        primary.append(p_rank)
        function_only.append(f_rank)
        address_only.append(a_rank)
        rows.append({"transaction_hash": tx, "vulnerable_contract": target_address, "vulnerable_function": target_function, "candidate_count": len(predictions), "primary_rank": p_rank, "function_only_rank": f_rank, "address_only_rank": a_rank})
        print(f"replayed {len(rows)}/{len(records)}")
    result = {
        "status": "COMPLETE",
        "label": "producer-era replay, exploratory",
        "producer_commit": PRODUCER,
        "model": MODEL,
        "network_calls": False,
        "ranker_scorer_weights_changed": False,
        "valid_set_sha256": EXPECTED_VALID_SHA,
        "batch_canonical_sha256": EXPECTED_BATCH_SHA,
        "metrics": {"primary_address_function": rank_metrics(primary), "function_only_sensitivity": rank_metrics(function_only), "address_only_sensitivity": rank_metrics(address_only)},
        "candidate_counts": {"n": len(rows), "min": min(row["candidate_count"] for row in rows), "max": max(row["candidate_count"] for row in rows), "mean": sum(row["candidate_count"] for row in rows) / len(rows), "rows": rows},
    }
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Batch A producer-era replay", "", "**Label: producer-era replay, exploratory**", "", f"Producer commit: `{PRODUCER}`", "", "| Metric | R@1 | R@3 | R@5 | N |", "| --- | ---: | ---: | ---: | ---: |"]
    for label, key in (("Primary address+function", "primary_address_function"), ("Function-only sensitivity", "function_only_sensitivity"), ("Address-only sensitivity", "address_only_sensitivity")):
        m = result["metrics"][key]
        lines.append(f"| {label} | {m['r_at_1']['hits']}/{m['r_at_1']['n']} ({m['r_at_1']['recall']:.6f}) | {m['r_at_3']['hits']}/{m['r_at_3']['n']} ({m['r_at_3']['recall']:.6f}) | {m['r_at_5']['hits']}/{m['r_at_5']['n']} ({m['r_at_5']['recall']:.6f}) | {m['r_at_1']['n']} |")
    lines += ["", f"Candidate counts: n={result['candidate_counts']['n']}, min={result['candidate_counts']['min']}, max={result['candidate_counts']['max']}, mean={result['candidate_counts']['mean']:.6f}.", "", "| Transaction | Candidates | Primary | Function-only | Address-only |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| `{row['transaction_hash']}` | {row['candidate_count']} | {row['primary_rank']} | {row['function_only_rank']} | {row['address_only_rank']} |")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer-root", type=Path, required=True)
    args = parser.parse_args()
    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    valid = json.loads(VALID_SET.read_text(encoding="utf-8"))
    audit = job1_audit()
    (OUT / "job1_70d1_facts.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if not all(row["prediction_list_unchanged"] for row in audit["affected_rows"]):
        raise FetchFailed("prediction hash changed in affected rows")
    records = batch_preflight(valid, batch)
    try:
        fetch = fetch_batch(records)
    except (PaidPlanPrompt, FetchFailed) as exc:
        (OUT / "fetch_abort.json").write_text(json.dumps({"status": "ABORTED", "reason": str(exc), "network_calls": True}, indent=2) + "\n", encoding="utf-8", newline="\n")
        print("fetch aborted")
        return 2
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    measurement = producer_replay(records, labels, args.producer_root.resolve())
    report = {
        "job_1": audit,
        "job_2": {"preflight": {"records": 23, "all_eth": True, "required_trace_fields_present": True}, "fetch": fetch, "measurement": measurement},
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "COMPLETE", "affected_rows": audit["affected_row_count"], "batch_rows": 23, "network_calls": fetch["network_calls"], "measurement": measurement["metrics"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
