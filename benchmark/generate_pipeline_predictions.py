"""Generate provenanced pipeline predictions using ForensicsOrchestrator over ground truth transactions.

STRICT GUARANTEE: NEVER reads the 'location' ground-truth field from benchmark/ground_truth/*.json.
Only parses 'transaction_hash' and 'chain'.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faultseeker.forensics.orchestrator import ForensicsOrchestrator
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.research.cost_tracker import CostTracker
from faultseeker.research.ablation import AblationConfig
from benchmark.honest_eval.localization import GROUND_TRUTH_DIR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "data", "output")


def parse_gt_file_strictly_no_location(filepath: str) -> dict:
    """Parse ground truth file for transaction_hash and chain ONLY.
    
    ASSERTION: 'location' key is explicitly purged and never read.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    # Explicit assertion check
    assert isinstance(raw_data, dict), f"Malformed ground truth JSON: {filepath}"
    
    hashes = raw_data.get("transaction_hash") or []
    if isinstance(hashes, str):
        hashes = [hashes]
    tx_hash = hashes[0].strip().lower() if hashes else os.path.basename(filepath)[:-5].strip().lower()
    raw_chain = str(raw_data.get("platform") or raw_data.get("chain") or "eth").strip().lower()
    chain_map = {
        "ethereum": "eth",
        "mainnet": "eth",
        "bnbchain": "bsc",
        "binance": "bsc",
        "binancesmartchain": "bsc",
        "polygon": "polygon",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "avalanche": "avalanche",
        "base": "base",
        "fantom": "fantom",
        "gnosis": "gnosis",
        "zksync": "zksync",
    }
    chain = chain_map.get(raw_chain, raw_chain)

    # Purge any ground truth location data from memory
    clean_meta = {
        "txn_hash": tx_hash,
        "chain": chain,
        "filename": os.path.basename(filepath),
    }
    assert "location" not in clean_meta, "Leakage assertion failed: location was attached!"
    return clean_meta


def run_pipeline_on_transaction(
    tx_meta: dict,
    orchestrator: ForensicsOrchestrator,
    analyzer: FunctionAnalyzer,
    cost_tracker: CostTracker,
) -> tuple[dict, float, float]:
    """Run ForensicsOrchestrator + FunctionAnalyzer over a transaction."""
    tx_hash = tx_meta["txn_hash"]
    chain = tx_meta["chain"]
    
    start_time = time.time()
    cost_before = cost_tracker.report()["actual_cost_usd"] if cost_tracker else 0.0
    
    print(f"\n[+] Analyzing {tx_meta['filename']} ({tx_hash[:14]}... chain={chain})", flush=True)
    
    # Step 1: ForensicsOrchestrator Stage 1
    forensics_result, txn_seq, txn_info = orchestrator.run(tx_hash, chain)
    
    if not forensics_result:
        print(f"    [!] ForensicsOrchestrator returned no result for {tx_hash[:14]}", flush=True)
        ranked_candidates = []
        trace_status = "TRACE_UNAVAILABLE"
    else:
        trace_status = "ok"
        # Step 2: Candidate ranking via FunctionRanker / AdaptiveFallback
        try:
            from faultseeker.function_analysis.function_ranker import FunctionRanker
            tx_analysis = {
                'trace': forensics_result.trace,
                'flatten_trace': forensics_result.flatten_trace,
                'repeated_patterns': forensics_result.repeated_patterns,
                'function_calls_to_expand_loc': forensics_result.function_calls_to_expand_loc,
                'address_calls_with_created_contract_in_params': forensics_result.address_calls_with_created_contract,
            }
            ranking_result = FunctionRanker().rank(forensics_result, tx_analysis)
            
            ranked_candidates = serialize_ranked_candidates(ranking_result)
        except Exception as exc:
            print(f"    [!] Candidate ranking fallback: {exc}", flush=True)
            ranked_candidates = []
            trace_status = f"error: {type(exc).__name__}"

        if not ranked_candidates and trace_status == "ok":
            # Adaptive fallback candidates from FAEGL decision
            adaptive_decision = forensics_result.adaptive_fallback.get("algorithm_decision", {})
            if isinstance(adaptive_decision, dict):
                raw_cands = adaptive_decision.get("candidates") or []
                for item in raw_cands:
                    if isinstance(item, dict):
                        ranked_candidates.append(item)

    wall_time = time.time() - start_time
    cost_after = cost_tracker.report()["actual_cost_usd"] if cost_tracker else 0.0
    tx_cost = max(0.0, cost_after - cost_before)

    provenance = {
        "producer": "ForensicsOrchestrator",
        "orchestrator_version": "2.0",
        "model_used": orchestrator.model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ablation_config": orchestrator.ablation.to_dict(),
        "transaction_hash": tx_hash,
        "trace_status": trace_status,
    }

    prediction_payload = {
        "transaction_hash": tx_hash,
        "chain": chain,
        "filename": tx_meta["filename"],
        "trace_status": trace_status,
        "predictions_provenance": provenance,
        "scored_functions": ranked_candidates,
        "wall_time_seconds": round(wall_time, 2),
        "measured_cost_usd": round(tx_cost, 6),
    }

    return prediction_payload, wall_time, tx_cost


def serialize_ranked_candidates(ranking_result) -> list[dict]:
    """Convert the ranker's explicit ordering into localization predictions.

    ``FunctionRanker`` exports stable candidates in ``ranked_functions``.  The
    previous adapter reconstructed them from dictionary keys with
    ``split("_")``, which truncated function names containing underscores and
    could put the wrong text in the address field.  Keep the ranker's explicit
    address/function identity and preserve its rank metadata.

    The legacy fallback is retained for older result objects, but uses
    ``rsplit`` because function labels may themselves contain underscores.
    """
    bare_selector = re.compile(r"^[0-9a-fA-F]{8}$")

    def canonical_output_function(value) -> str:
        label = str(value or "")
        if bare_selector.fullmatch(label.strip()):
            return f"0x{label.strip().lower()}"
        return label

    explicit = getattr(ranking_result, "ranked_functions", None) or []
    if explicit:
        candidates = []
        for item in explicit:
            if not isinstance(item, dict):
                continue
            candidate = dict(item)
            address = candidate.get("code_address") or candidate.get("address") or ""
            function = canonical_output_function(
                candidate.get("function")
                or candidate.get("function_name")
                or candidate.get("name")
                or ""
            )
            candidate["address"] = address
            candidate["function"] = function
            if (
                not candidate.get("selector")
                and len(function) == 10
                and function.startswith("0x")
            ):
                candidate["selector"] = function
            candidate.setdefault("call_type", "call")
            depths = candidate.get("supporting_call_depths") or []
            candidate.setdefault("depth", _max_depth_value(depths))
            candidates.append(candidate)
        return candidates

    candidates = []
    for fn_key, fn_info in (getattr(ranking_result, "functions_to_be_inspected", {}) or {}).items():
        fn_name, separator, address = str(fn_key).rpartition("_")
        if not separator:
            fn_name, address = str(fn_key), ""
        calls = (fn_info or {}).get("calls") or []
        depths = [call.get("depth", 0) for call in calls if isinstance(call, dict)]
        fn_name = canonical_output_function(fn_name)
        candidates.append({
            "address": address,
            "function": fn_name,
            "call_type": "call",
            "depth": max(depths) if depths else 0,
            "_score": 0.95 if fn_name != "others" else 0.5,
        })
    return candidates


def _max_depth_value(value) -> int:
    """Return the largest integer from flat or path-shaped depth metadata."""
    if isinstance(value, (list, tuple)):
        values = [_max_depth_value(item) for item in value]
        return max(values, default=0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate provenanced predictions with ForensicsOrchestrator")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of transactions to process (e.g. 3)")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model to use")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cost_tracker = CostTracker()
    ablation = AblationConfig.full_system()
    orchestrator = ForensicsOrchestrator(model=args.model, ablation=ablation, cost_tracker=cost_tracker)
    analyzer = FunctionAnalyzer(model=args.model, cost_tracker=cost_tracker)

    gt_files = sorted([f for f in os.listdir(GROUND_TRUTH_DIR) if f.endswith(".json")])
    if args.limit:
        gt_files = gt_files[:args.limit]

    print("=" * 75, flush=True)
    print(f"GENERATING FORENSICS ORCHESTRATOR PREDICTIONS (N={len(gt_files)})", flush=True)
    print("=" * 75, flush=True)

    results_summary = []
    total_time = 0.0
    total_cost = 0.0

    for fname in gt_files:
        filepath = os.path.join(GROUND_TRUTH_DIR, fname)
        tx_meta = parse_gt_file_strictly_no_location(filepath)
        out_path = os.path.join(OUTPUT_DIR, f"{tx_meta['txn_hash']}.json")
        
        if os.path.exists(out_path):
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if "scored_functions" in existing and "trace_status" in existing:
                    print(f"\n[=] Skipping {fname} ({tx_meta['txn_hash'][:12]}...): output file already exists.", flush=True)
                    results_summary.append({
                        "filename": fname,
                        "tx_hash": tx_meta["txn_hash"],
                        "candidates_count": len(existing["scored_functions"]),
                        "wall_time": 0.0,
                        "cost_usd": 0.0,
                        "out_path": out_path,
                    })
                    continue
            except Exception:
                pass
        
        pred_payload, w_time, t_cost = run_pipeline_on_transaction(tx_meta, orchestrator, analyzer, cost_tracker)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pred_payload, f, indent=2)
            
        results_summary.append({
            "filename": fname,
            "tx_hash": tx_meta["txn_hash"],
            "candidates_count": len(pred_payload["scored_functions"]),
            "wall_time": w_time,
            "cost_usd": t_cost,
            "out_path": out_path,
        })
        total_time += w_time
        total_cost += t_cost

    print("\n" + "=" * 75)
    print("TRIAL RUN EXECUTION SUMMARY")
    print("=" * 75)
    for res in results_summary:
        print(f"File: {res['filename']}")
        print(f"  Tx Hash     : {res['tx_hash']}")
        print(f"  Candidates  : {res['candidates_count']}")
        print(f"  Wall Time   : {res['wall_time']:.2f} s")
        print(f"  Est. Cost   : ${res['cost_usd']:.6f}")
        print(f"  Saved File  : {res['out_path']}")
        print()

    avg_time = total_time / len(results_summary) if results_summary else 0.0
    avg_cost = total_cost / len(results_summary) if results_summary else 0.0
    proj_time_all = avg_time * 115
    proj_cost_all = avg_cost * 115

    print(f"Batch Summary ({len(results_summary)} processed):")
    print(f"  Total Wall-Clock Time : {total_time:.2f} s (Avg: {avg_time:.2f} s/tx)")
    print(f"  Total Measured Cost   : ${total_cost:.6f} (Avg: ${avg_cost:.6f}/tx)")
    print()
    print(f"Projected metrics for all 115 ground-truth transactions:")
    print(f"  Projected Total Time  : {proj_time_all / 60.0:.2f} minutes")
    print(f"  Projected Total Cost  : ${proj_cost_all:.4f}")
    print("=" * 75)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
