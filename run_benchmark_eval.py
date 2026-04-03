"""
FaultSeeker++ Benchmarking & Evaluation Script (Task C)
=========================================================
Auto-runs the FaultSeeker++ pipeline on a sample of benchmark transactions
and produces a structured metrics CSV + JSON for the implementation paper.

Usage (on friend's laptop):
    python run_benchmark_eval.py --limit 10 --chains eth bsc arbitrum
    python run_benchmark_eval.py --limit 5 --cloud-only
    python run_benchmark_eval.py --full   # all 246 entries (slow!)
"""

import csv
import json
import time
import argparse
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys
import os

# Add project root to path so faultseeker can be imported
sys.path.insert(0, str(Path(__file__).parent))
from faultseeker.core.auto_model_selector import auto_select_models, print_model_selection

CSV_PATH   = Path("benchmark/benchmark_classification_fixed.csv")
REPORT_DIR = Path("reports/eval")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_CHAINS = ["eth", "bsc", "arbitrum", "optimism", "base",
                    "polygon", "avalanche", "zksync"]


# ── Metric accumulator ────────────────────────────────────────────────
class EvalMetrics:
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed  = 0
        self.timeout = 0
        self.latencies: list = []
        self.confidence_scores: list = []
        self.per_chain: dict = defaultdict(lambda: {
            "total":0,"success":0,"failed":0,"latencies":[],"confidence":[]
        })
        self.per_complexity: dict = defaultdict(lambda: {"total":0,"success":0})
        self.per_vuln: dict = defaultdict(lambda: {"total":0,"success":0})
        self.results: list = []

    def record(self, txn_hash, chain, vuln_type, complexity,
               success, latency_s, confidence, error=None):
        self.total += 1
        if success:
            self.success += 1
            self.latencies.append(latency_s)
            self.confidence_scores.append(confidence)
        else:
            self.failed += 1

        self.per_chain[chain]["total"] += 1
        if success:
            self.per_chain[chain]["success"] += 1
            self.per_chain[chain]["latencies"].append(latency_s)
            self.per_chain[chain]["confidence"].append(confidence)
        else:
            self.per_chain[chain]["failed"] = self.per_chain[chain].get("failed", 0) + 1

        self.per_complexity[complexity]["total"] += 1
        if success:
            self.per_complexity[complexity]["success"] += 1

        self.per_vuln[vuln_type]["total"] += 1
        if success:
            self.per_vuln[vuln_type]["success"] += 1

        self.results.append({
            "txn_hash":   txn_hash,
            "chain":      chain,
            "vuln_type":  vuln_type,
            "complexity": complexity,
            "success":    success,
            "latency_s":  round(latency_s, 2),
            "confidence": round(confidence, 3),
            "error":      str(error) if error else "",
        })

    def summary(self) -> dict:
        avg_latency    = round(sum(self.latencies)/len(self.latencies), 2) if self.latencies else 0
        avg_confidence = round(sum(self.confidence_scores)/len(self.confidence_scores), 3) if self.confidence_scores else 0
        success_rate   = round(self.success / max(self.total, 1) * 100, 1)

        per_chain_summary = {}
        for ch, d in self.per_chain.items():
            per_chain_summary[ch] = {
                "total":       d["total"],
                "success":     d["success"],
                "success_rate": round(d["success"] / max(d["total"],1)*100, 1),
                "avg_latency": round(sum(d["latencies"])/len(d["latencies"]),2) if d["latencies"] else 0,
                "avg_confidence": round(sum(d["confidence"])/len(d["confidence"]),3) if d["confidence"] else 0,
            }

        per_complexity_summary = {
            cmp: {
                "total":   d["total"],
                "success": d["success"],
                "success_rate": round(d["success"]/max(d["total"],1)*100, 1)
            }
            for cmp, d in self.per_complexity.items()
        }

        return {
            "total_transactions":   self.total,
            "successful":           self.success,
            "failed":               self.failed,
            "success_rate_pct":     success_rate,
            "avg_latency_s":        avg_latency,
            "avg_confidence_score": avg_confidence,
            "per_chain":            per_chain_summary,
            "per_complexity":       per_complexity_summary,
        }


# ── Main evaluator ────────────────────────────────────────────────────
def load_benchmark(chains=None, limit=None, complexities=None):
    entries = []
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            txn = row.get("txn_hash","").strip()
            if not txn:
                continue
            chain = row.get("chain","").strip().lower()
            if chains and chain not in chains:
                continue
            complexity = row.get("class","").strip()
            if complexities and complexity not in complexities:
                continue
            entries.append({
                "txn_hash":   txn,
                "chain":      chain,
                "vuln_type":  row.get("vuln_type","Unknown").strip(),
                "complexity": complexity,
                "loss_usd":   row.get("loss_usd","0").strip(),
            })
    if limit:
        # Stratified: sample evenly across chains
        per_chain = defaultdict(list)
        for e in entries:
            per_chain[e["chain"]].append(e)
        sampled = []
        for ch_entries in per_chain.values():
            sampled.extend(ch_entries[:limit])
        return sampled
    return entries


def run_faultseeker(txn_hash: str, chain: str, model: str,
                    local_model: str, timeout: int = 300):
    """
    Invoke FaultSeeker++ via subprocess (isolates memory per TXN).
    Returns (success, confidence, error).
    """
    cmd = [
        "python", "-m", "faultseeker",
        "--txn", txn_hash,
        "--chain", chain,
        "--model", model,
    ]
    if local_model:
        cmd += ["--local-model", local_model]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            # Try to extract confidence from stdout JSON
            confidence = _extract_confidence_from_output(result.stdout)
            return True, confidence, None
        else:
            return False, 0.0, result.stderr[-500:]
    except subprocess.TimeoutExpired:
        return False, 0.0, f"Timeout after {timeout}s"
    except Exception as e:
        return False, 0.0, str(e)


def _extract_confidence_from_output(stdout: str) -> float:
    """Parse confidence score from stdout JSON lines."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            pvf = data.get("potentially_vulnerable_functions", {})
            scores = []
            for v in pvf.values():
                if isinstance(v, dict):
                    cs = v.get("confidence_score", [])
                    if isinstance(cs, list):
                        scores.extend(float(x) for x in cs if x)
                    elif cs:
                        scores.append(float(cs))
            if scores:
                return round(sum(scores)/len(scores), 3)
        except Exception:
            continue
    return 0.0


def run_evaluation(chains=None, limit=None, model=None,
                   local_model=None, cloud_only=False,
                   complexities=None, txn_timeout=300):
    """Main evaluation loop."""
    # Auto-detect models if not specified
    if not model:
        model_config = auto_select_models()
        print_model_selection(model_config)
        model       = model_config['cloud_model']
        local_model = local_model or model_config['local_model']

    entries = load_benchmark(chains=chains, limit=limit, complexities=complexities)
    print(f"\n{'='*60}")
    print(f"  FaultSeeker++ Benchmark Evaluation")
    print(f"  Transactions: {len(entries)}")
    print(f"  Model: {model} | Local: {local_model}")
    print(f"{'='*60}\n")

    metrics = EvalMetrics()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, entry in enumerate(entries, 1):
        txn  = entry["txn_hash"]
        chain = entry["chain"]
        print(f"  [{i:>3}/{len(entries)}] {chain.upper():<10} {txn[:20]}...  ", end="", flush=True)

        t0 = time.time()
        success, confidence, error = run_faultseeker(
            txn_hash=txn,
            chain=chain,
            model=model,
            local_model=None if cloud_only else local_model,
            timeout=txn_timeout,
        )
        elapsed = time.time() - t0

        status = "✓" if success else "✗"
        print(f"{status}  conf={confidence:.3f}  {elapsed:.1f}s")

        metrics.record(
            txn_hash=txn,
            chain=chain,
            vuln_type=entry["vuln_type"],
            complexity=entry["complexity"],
            success=success,
            latency_s=elapsed,
            confidence=confidence,
            error=error,
        )

    # ── Save results ──────────────────────────────────────────────────
    summary = metrics.summary()

    # JSON report
    json_path = REPORT_DIR / f"eval_results_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": metrics.results}, f, indent=2)

    # CSV per-transaction log
    csv_path = REPORT_DIR / f"eval_results_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        if metrics.results:
            writer = csv.DictWriter(f, fieldnames=metrics.results[0].keys())
            writer.writeheader()
            writer.writerows(metrics.results)

    # Text summary (for paper table)
    txt_path = REPORT_DIR / f"eval_summary_{ts}.txt"
    _write_paper_table(summary, txt_path)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  Total:          {summary['total_transactions']}")
    print(f"  Success Rate:   {summary['success_rate_pct']}%")
    print(f"  Avg Confidence: {summary['avg_confidence_score']}")
    print(f"  Avg Latency:    {summary['avg_latency_s']}s")
    print(f"\n  Per-chain breakdown:")
    for ch, d in summary["per_chain"].items():
        print(f"    {ch:<12} {d['success_rate']}% success  "
              f"conf={d['avg_confidence']}  lat={d['avg_latency']}s")
    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {csv_path}")
    print(f"  Saved: {txt_path}")
    print(f"{'='*60}\n")
    return summary


def _write_paper_table(summary: dict, path: Path):
    """Write a LaTeX-ready table for the paper."""
    lines = [
        "% ── FaultSeeker++ Evaluation Results Table ──────────────────",
        "% Auto-generated by run_benchmark_eval.py",
        "",
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{FaultSeeker++ Cross-Chain Benchmark Results}",
        r"\label{tab:eval_results}",
        r"\begin{tabular}{lcccc}",
        r"\hline",
        r"\textbf{Chain} & \textbf{TXNs} & \textbf{Success \%} & "
        r"\textbf{Avg Confidence} & \textbf{Avg Latency (s)} \\",
        r"\hline",
    ]
    for ch, d in summary["per_chain"].items():
        lines.append(
            f"{ch.upper()} & {d['total']} & {d['success_rate']}\\% & "
            f"{d['avg_confidence']:.3f} & {d['avg_latency']:.1f} \\\\"
        )
    lines += [
        r"\hline",
        f"\\textbf{{Total}} & {summary['total_transactions']} & "
        f"{summary['success_rate_pct']}\\% & "
        f"{summary['avg_confidence_score']:.3f} & "
        f"{summary['avg_latency_s']:.1f} \\\\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaultSeeker++ Benchmark Evaluator")
    parser.add_argument("--chains", nargs="+", choices=SUPPORTED_CHAINS, default=None)
    parser.add_argument("--limit",  type=int, default=None,
                        help="Max TXNs per chain (for quick test)")
    parser.add_argument("--full",   action="store_true",
                        help="Run all 246 entries")
    parser.add_argument("--model",  default=None,
                        help="Cloud model (auto-detected from .env if not set)")
    parser.add_argument("--local-model", default=None,
                        help="Local Ollama model (auto-detected if not set)")
    parser.add_argument("--cloud-only", action="store_true")
    parser.add_argument("--complexity", nargs="+",
                        choices=["Simple","Moderate","Complex","Exceptionally Complex"],
                        default=None)
    parser.add_argument("--timeout", type=int, default=300,
                        help="Per-transaction timeout in seconds")
    args = parser.parse_args()

    limit = None if args.full else (args.limit or 5)

    run_evaluation(
        chains=args.chains,
        limit=limit,
        model=args.model,
        local_model=args.local_model,
        cloud_only=args.cloud_only,
        complexities=args.complexity,
        txn_timeout=args.timeout,
    )
