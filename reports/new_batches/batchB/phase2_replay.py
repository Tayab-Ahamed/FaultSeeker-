"""One producer-era Batch B replay and one selector-based scoring pass."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]
PHASE = ROOT / "reports/new_batches/batchB/phase2"
BATCH = ROOT / "reports/new_batches/batchB/batchB_candidates.json"
EXPECTED_HASH = "5b66ae6d8c2b6bc23fbdb03f82738ada4684865846f2792d5111edc92cee942a"
PRODUCER_COMMIT = "1b1c7395771663622dd14b9731b4b8b471221960"
LABEL = "Batch B, pre-registered, one-shot, ETH only, DeFiHackLabs-sourced"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rank_metrics(ranks: list[int | None]) -> dict[str, dict[str, int | float]]:
    result = {}
    for k in (1, 3, 5):
        hits = sum(rank is not None and rank <= k for rank in ranks)
        result[f"R@{k}"] = {"hits": hits, "n": len(ranks), "recall": hits / len(ranks) if ranks else 0.0}
    return result


def normalize_address(value) -> str:
    return str(value or "").lower()


def normalize_selector(prediction: dict) -> str:
    value = prediction.get("selector") or prediction.get("function") or ""
    value = str(value).lower()
    return value if value.startswith("0x") and len(value) == 10 else ""


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: phase2_replay.py <producer-root>")
    producer_root = Path(sys.argv[1]).resolve()
    batch = load(BATCH)
    if batch.get("artifact_sha256") != EXPECTED_HASH:
        raise RuntimeError("frozen Batch B hash changed; refusing replay")
    run_name = sorted(path.name for path in PHASE.glob("run_*") if path.is_dir())[-1]
    run_dir = PHASE / run_name
    verification = load(run_dir / "verification_summary.json")
    verified_rows = [row for row in verification["verification_rows"] if row["verified"]]
    if len(verified_rows) < 10:
        raise RuntimeError(f"verified rows below protocol minimum: {len(verified_rows)}")
    raw_dir = run_dir / "raw"
    replay_dir = run_dir / "replay"
    candidate_dir = replay_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=False)

    # The detached tree is exactly the producer commit. All transaction input
    # is supplied through captured local objects; no provider path is touched.
    sys.path.insert(0, str(producer_root))
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.function_analysis.function_ranker import FunctionRanker
    from faultseeker.utils.rpc_provider import normalize_trace_node

    batch_rows = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    by_tx = {str(row["transaction_hash"]).lower(): row for row in verification["verification_rows"]}
    score_rows = []
    invocations = 0
    for verified in verified_rows:
        tx = verified["transaction_hash"].lower()
        label = batch_rows[tx]
        trace_path = run_dir / verified["responses"]["debug_traceTransaction"]["raw_path"]
        tx_path = run_dir / verified["responses"]["eth_getTransactionByHash"]["raw_path"]
        receipt_path = run_dir / verified["responses"]["eth_getTransactionReceipt"]["raw_path"]
        trace_response = load(trace_path)
        tx_response = load(tx_path)
        receipt_response = load(receipt_path)
        trace = trace_response.get("result")
        tx_result = tx_response.get("result")
        receipt_result = receipt_response.get("result")
        structured = {
            "transaction_hash": tx,
            "chain": "eth",
            "trace": normalize_trace_node(trace),
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
            txn_info_collector=_CapturedInfo(tx_result, receipt_result, tx, "eth"),
        )
        forensics_result, _, _ = orchestrator.run(tx, "eth")
        tx_analysis = {
            "repeated_patterns": forensics_result.repeated_patterns,
            "function_call_loc_memo": forensics_result.function_call_loc_memo,
        }
        predictions = [dict(item) for item in FunctionRanker().rank(forensics_result, tx_analysis).ranked_functions]
        invocations += 1
        (candidate_dir / f"{tx}.json").write_text(
            json.dumps({"transaction_hash": tx, "candidate_count": len(predictions), "predictions": predictions}, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        target_address = normalize_address(label["vulnerable_contract_address"])
        target_selector = str(label["selector"]).lower()
        address_rank = None
        selector_rank = None
        pair_rank = None
        for index, prediction in enumerate(predictions, 1):
            address = normalize_address(prediction.get("code_address") or prediction.get("address"))
            selector = normalize_selector(prediction)
            if address_rank is None and address == target_address:
                address_rank = index
            if selector_rank is None and selector == target_selector:
                selector_rank = index
            if pair_rank is None and address == target_address and selector == target_selector:
                pair_rank = index
        score_rows.append({
            "transaction_hash": tx,
            "incident_name": label["incident_name"],
            "candidate_count": len(predictions),
            "address_selector_rank": pair_rank,
            "address_only_rank": address_rank,
            "selector_only_rank": selector_rank,
            "target_address": target_address,
            "target_selector": target_selector,
        })

    primary = [row["address_selector_rank"] for row in score_rows]
    addresses = [row["address_only_rank"] for row in score_rows]
    selectors = [row["selector_only_rank"] for row in score_rows]
    scoring = {
        "label": LABEL,
        "producer_commit": PRODUCER_COMMIT,
        "frozen_batch_sha256": EXPECTED_HASH,
        "verified_n": len(score_rows),
        "ranker_invocations": invocations,
        "scoring_passes": 1,
        "tuning": False,
        "partial_result_peeking": False,
        "metrics": {
            "address_selector_primary": rank_metrics(primary),
            "address_only_sensitivity": rank_metrics(addresses),
            "selector_only_sensitivity": rank_metrics(selectors),
        },
        "candidate_counts": {
            "n": len(score_rows),
            "min": min(row["candidate_count"] for row in score_rows),
            "max": max(row["candidate_count"] for row in score_rows),
            "mean": mean(row["candidate_count"] for row in score_rows),
        },
        "rows": score_rows,
    }
    (replay_dir / "scoring.json").write_text(json.dumps(scoring, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verified_n": len(score_rows), "ranker_invocations": invocations, "scoring_passes": 1, "metrics": scoring["metrics"], "candidate_counts": scoring["candidate_counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
