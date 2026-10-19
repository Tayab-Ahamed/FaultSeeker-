"""Freeze, collect free-tier RPC evidence, then score fresh Batch D once.

No LLM or Foundry invocation. Working-file hashes bind uncommitted reviewed code.
Research inputs are cached public PoCs and actual RPC responses, never fixtures.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.research import batchC_phase2 as base

BATCH_DIR = ROOT / "reports/new_batches/batchD"
BATCH = BATCH_DIR / "batchD_candidates.json"
CONFIG = BATCH_DIR / "deployment_config.json"
FREEZE = BATCH_DIR / "freeze.json"
RUN = BATCH_DIR / "phase2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    base._write_json(path, value)


def redact_exact(value, endpoint: str, key: str):
    """Redact credentials without clipping any captured public evidence."""
    if isinstance(value, str):
        result = value.replace(endpoint, "[RPC_URL_REDACTED]") if endpoint else value
        return result.replace(key, "[API_KEY_REDACTED]") if key else result
    if isinstance(value, dict):
        return {k: redact_exact(v, endpoint, key) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_exact(v, endpoint, key) for v in value]
    return value


def verify_code(manifest: dict) -> None:
    for relative, digest in manifest.items():
        if sha256(ROOT / relative) != digest:
            raise RuntimeError(f"Frozen file changed: {relative}")


def acquire_score_lock(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "score_started.json").open("x", encoding="utf-8") as handle:
        json.dump({"started_at_utc": datetime.now(timezone.utc).isoformat(),
                   "policy": "exclusive single scoring attempt; no automatic retry"}, handle)


def trace_text(node: dict, depth: int = 0) -> str:
    """Serialize only observed call identities; target labels are never inputs."""
    address = str(node.get("to") or "").lower()
    data = str(node.get("input") or "").lower()
    selector = data[:10] if data.startswith("0x") and len(data) >= 10 else "fallback"
    kind = str(node.get("type") or node.get("callType") or "CALL").lower()
    prefix = "    " * depth + ("└─ " if depth else "")
    lines = [f"{prefix}[0] {address}::{selector}() [{kind}]"] if address else []
    for child in node.get("calls") or []:
        lines.append(trace_text(child, depth + 1))
    return "\n".join(lines)


def safe_rpc(endpoint: str, method: str, params: list, state: dict) -> dict:
    if state["request_count"]:
        time.sleep(1.0)
    state["request_count"] += 1
    try:
        response, stderr = base._rpc_once(endpoint, method, params)
    except Exception as exc:
        event = {"request": state["request_count"], "method": method, "row": state.get("row_index"),
                 "transport_error": type(exc).__name__, "free_tier_only": True,
                 "conservative_paid_spend_estimate_usd": 0}
        with (Path(state["run_dir"]) / "requests.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        raise RuntimeError("STOPPED_TRANSPORT_ERROR") from None
    body = response.get("body")
    billing = response.get("http_status") == 402 or base._contains_billing(body) or base._contains_billing(stderr)
    rate = base._is_rate_limited(response.get("http_status"), body)
    state["billing_prompt_detected"] |= billing
    state["rate_limit_hits"] += int(rate)
    error = body.get("error") if isinstance(body, dict) else None
    event = {"request": state["request_count"], "method": method,
             "http_status": response.get("http_status"), "row": state.get("row_index"),
             "billing_prompt_detected": billing, "rate_limited": rate,
             "rpc_error": error, "paid_calls_authorized": False,
             "conservative_paid_spend_estimate_usd": 0,
             "free_tier_only": True}
    safe = base._redact(event, endpoint, state["api_key"])
    with (Path(state["run_dir"]) / "requests.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, sort_keys=True) + "\n")
    if billing:
        raise RuntimeError("STOPPED_BILLING_PROMPT")
    if rate:
        raise RuntimeError("STOPPED_RATE_LIMIT; no automatic retries")
    response["stderr"] = base._redact(stderr, endpoint, state["api_key"])
    return response


def freeze() -> None:
    if FREEZE.exists() or BATCH.exists():
        raise RuntimeError("Batch D is already frozen")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if not branch or branch in {"main", "master"}:
        raise RuntimeError("A non-main branch is required")
    draft = base._load_json(BATCH_DIR / "draft_source_rows.json")
    rows = deepcopy(draft["rows"])
    if not rows or len({r["transaction_hash"] for r in rows}) != len(rows):
        raise RuntimeError("Empty or duplicate cohort")
    from eth_utils import keccak
    for row in rows:
        if sha256(ROOT / row["local_source_file"]) != row["source_content_sha256"]:
            raise RuntimeError("Cached source hash mismatch")
        row["selector"] = "0x" + keccak(text=row["full_signature"])[:4].hex()
    config = base._load_json(CONFIG)
    if config.get("training_population") != "original110-development-only":
        raise RuntimeError("Deployment configuration lacks development-only provenance")
    payload = {"batch_id": "batchD", "status": "FROZEN_BEFORE_RPC_AND_SCORING", "chain": "eth",
               "row_count": len(rows), "rows": rows, "draft_sha256": sha256(BATCH_DIR / "draft_source_rows.json"),
               "selection_policy": draft["selection_policy"],
               "limitations": ["Convenience sample of cached DeFiHackLabs PoC targets, not independently adjudicated root causes.",
                               "Cached source bytes are SHA-256 pinned; upstream commit was not recorded.",
                               "110 development records contain 109 unique transactions; OOF was exploratory."]}
    payload["artifact_sha256"] = base._artifact_hash(payload)
    write(BATCH, payload)
    files = list((ROOT / "faultseeker").rglob("*.py")) + [Path(__file__), Path(base.__file__),
            ROOT / "scripts/research/evaluate_candidate_generation_cv.py",
            ROOT / "benchmark/evidence_manifest.py", CONFIG, BATCH_DIR / "PROTOCOL.md"]
    files += list((ROOT / "data/models").glob("*.json"))
    manifest = {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(set(files))}
    frozen = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "branch": branch,
              "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "batch_sha256": payload["artifact_sha256"], "code_and_config_sha256": manifest,
              "committed": False, "scoring_passes_at_freeze": 0, "rpc_requests_at_freeze": 0}
    write(FREEZE, frozen)
    print(json.dumps({"frozen_rows": len(rows), "batch_sha256": payload["artifact_sha256"], "pinned_files": len(manifest)}))


def verify_frozen() -> tuple[dict, dict]:
    frozen, batch = base._load_json(FREEZE), base._load_json(BATCH)
    verify_code(frozen["code_and_config_sha256"])
    if base._artifact_hash(batch) != frozen["batch_sha256"] or batch["artifact_sha256"] != frozen["batch_sha256"]:
        raise RuntimeError("Frozen Batch D changed")
    for row in batch["rows"]:
        if sha256(ROOT / row["local_source_file"]) != row["source_content_sha256"]:
            raise RuntimeError("Frozen source changed")
    return frozen, batch


def collect() -> None:
    frozen, batch = verify_frozen()
    endpoint, key = base._credentials()
    RUN.mkdir(parents=True, exist_ok=False)
    state = {"request_count": 0, "run_dir": RUN, "api_key": key,
             "rate_limit_hits": 0, "billing_prompt_detected": False}
    verification = {"status": "RUNNING", "batch_sha256": frozen["batch_sha256"], "rows": []}
    base._rpc = safe_rpc
    try:
        for index, label in enumerate(batch["rows"], 1):
            state["row_index"] = index
            # Collection receives identity only, never expected function/address.
            identity = {"transaction_hash": label["transaction_hash"], "incident_name": label["incident_name"]}
            result = base._trace_row(endpoint, identity, state)
            path = RUN / "raw" / (label["transaction_hash"] + ".json")
            write(path, redact_exact(result, endpoint, key))
            verification["rows"].append({"transaction_hash": result["transaction_hash"], "verified": result["verified"],
                                          "exclusion_reasons": result["exclusion_reasons"],
                                          "raw_path": path.relative_to(ROOT).as_posix(), "raw_sha256": sha256(path)})
            write(RUN / "verification.json", verification)
        verification["status"] = "COMPLETED"
    except Exception as exc:
        verification["status"] = ("STOPPED_BILLING_PROMPT" if state["billing_prompt_detected"] else
                                  "STOPPED_RATE_LIMIT" if state["rate_limit_hits"] else "STOPPED_ERROR")
        verification["error_type"] = type(exc).__name__
        raise
    finally:
        verification.update({"request_count": state["request_count"], "rate_limit_hits": state["rate_limit_hits"],
                             "billing_prompt_detected": state["billing_prompt_detected"],
                             "verified_count": sum(r["verified"] for r in verification["rows"]),
                             "excluded_count": sum(not r["verified"] for r in verification["rows"]),
                             "free_tier_only": True, "paid_spend_estimate_usd": 0})
        write(RUN / "verification.json", verification)
        print(json.dumps({k: v for k, v in verification.items() if k != "rows"}))


def score() -> None:
    frozen, batch = verify_frozen()
    verification = base._load_json(RUN / "verification.json")
    if verification["status"] != "COMPLETED" or verification.get("billing_prompt_detected"):
        raise RuntimeError("Collection stopped; scoring prohibited")
    if verification["batch_sha256"] != frozen["batch_sha256"]:
        raise RuntimeError("Verification batch mismatch")
    if (RUN / "scoring.json").exists() or (RUN / "score_started.json").exists():
        raise RuntimeError("One-shot scoring already started or completed")
    from scripts.research.evaluate_candidate_generation_cv import prepare_row, rank_prepared
    config = base._load_json(CONFIG)["config"]
    # Produce ALL predictions before reading target identities for any score.
    predictions = []
    for row in verification["rows"]:
        if not row["verified"]:
            continue
        path = ROOT / row["raw_path"]
        if sha256(path) != row["raw_sha256"]:
            raise RuntimeError("Captured RPC evidence changed")
        raw = base._load_json(path)
        ranked = base._rank_from_trace(raw)
        prepared = prepare_row({"predictions": ranked, "cast": {"output_tail": trace_text(raw["trace"])}})
        predictions.append((row["transaction_hash"], rank_prepared(prepared, config)))
    if not predictions:
        raise RuntimeError("No verified transactions; no scoring attempt")
    verify_frozen()
    acquire_score_lock(RUN)
    labels = {r["transaction_hash"]: r for r in batch["rows"]}
    scored_rows = []
    for tx, ranked in predictions:
        pair, address, selector = base._ranks(ranked, labels[tx])
        scored_rows.append({"transaction_hash": tx, "address_selector_rank": pair,
                            "address_only_rank": address, "selector_only_rank": selector,
                            "candidate_count": len(ranked)})
        write(RUN / "candidates" / (tx + ".json"), {"transaction_hash": tx, "predictions": ranked})
    result = {"status": "SCORED_ONCE", "scoring_passes": 1, "verified_n": len(scored_rows),
              "batch_sha256": frozen["batch_sha256"], "deployment_config": config,
              "ranker_base_commit": frozen["base_commit"], "working_code_hashes": frozen["code_and_config_sha256"],
              "tuning_after_freeze": False, "rows": scored_rows,
              "metrics": {name: base._rank_metrics([r[field] for r in scored_rows]) for name, field in [
                  ("address_selector_primary", "address_selector_rank"),
                  ("address_only_sensitivity", "address_only_rank"),
                  ("selector_only_sensitivity", "selector_only_rank")]}}
    write(RUN / "scoring.json", result)
    print(json.dumps({k: result[k] for k in ["status", "scoring_passes", "verified_n", "metrics"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "collect", "score"])
    args = parser.parse_args()
    {"freeze": freeze, "collect": collect, "score": score}[args.command]()
