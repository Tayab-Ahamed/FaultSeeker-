"""Evaluate FaultSeeker localization on the imported original benchmark.

This is a new measurement on the original FaultSeeker benchmark.  It never
uses ground-truth locations while constructing predictions: location fields
are loaded only after the transaction run has completed, for scoring.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import random
import time
from typing import Any

from faultseeker.forensics.orchestrator import ForensicsOrchestrator
from faultseeker.function_analysis.function_ranker import FunctionRanker
from benchmark.honest_eval.localization import (
    LocalizationTarget,
    _norm_addr,
    _parse_location_entry,
    _register_fn_names,
    rank_of_first_hit,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
DEFAULT_OUT = ROOT / "reports/original_benchmark"
SEED = 20261017
DEFAULT_RUN_ID = "original-v1-seed20261017"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chain(raw: dict[str, Any]) -> str:
    value = str(raw.get("platform") or raw.get("chain") or "eth").strip().lower()
    return {
        "ethereum": "eth", "mainnet": "eth", "bnbchain": "bsc",
        "binance": "bsc", "binancesmartchain": "bsc",
    }.get(value, value)


def _tx_hash(raw: dict[str, Any], path: Path) -> str:
    values = raw.get("transaction_hash") or []
    if isinstance(values, str):
        values = [values]
    return str(values[0] if values else path.stem).strip().lower()


def _metadata(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("ground-truth file must be an object")
    return {"case_id": path.stem, "txn_hash": _tx_hash(raw, path),
            "chain": _chain(raw), "filename": path.name}


def _predictions(result: Any) -> list[dict[str, Any]]:
    tx_analysis = {
        "repeated_patterns": result.repeated_patterns,
        "function_call_loc_memo": result.function_call_loc_memo,
    }
    ranked = FunctionRanker().rank(result, tx_analysis)
    return [dict(item) for item in ranked.ranked_functions]


def _score(gt_path: Path, predictions: list[dict[str, Any]]) -> dict[str, Any]:
    raw = json.loads(gt_path.read_text(encoding="utf-8-sig"))
    target = LocalizationTarget(txn_hash=_tx_hash(raw, gt_path), name=str(raw.get("name") or ""))
    names = []
    for key, values in (raw.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parsed = _parse_location_entry(entry)
            if not parsed:
                continue
            address, member, is_line = parsed
            if not is_line:
                target.functions.add((address, member))
                names.append(member)
    _register_fn_names(names)
    rank = rank_of_first_hit(target, predictions, match="function")
    return {
        "target_function_count": len(target.functions),
        "first_hit_rank": rank,
        "recall_at_1": bool(rank is not None and rank <= 1),
        "recall_at_3": bool(rank is not None and rank <= 3),
        "recall_at_5": bool(rank is not None and rank <= 5),
    }


def _run_one(path: Path, variant: str, model: str) -> dict[str, Any]:
    metadata = _metadata(path)
    started = time.perf_counter()
    row: dict[str, Any] = {
        **metadata,
        "variant": variant,
        "model": model,
        "provider": "none" if variant == "llm-free" else "configured-runtime",
        "status": "failed",
        "failure_kind": None,
        "predictions": [],
        "token_usage": {"input": 0, "output": 0, "source": "not-dispatched"},
        "actual_cost_usd": 0.0,
        "list_price_equivalent_usd": None,
    }
    try:
        # This variant intentionally exercises only the deterministic
        # orchestrator/ranker path. It never constructs a provider client.
        result = ForensicsOrchestrator(model=model).run(
            metadata["txn_hash"], metadata["chain"])
        if isinstance(result, tuple):
            result = result[0]
        if not result:
            raise RuntimeError("orchestrator returned no result")
        predictions = _predictions(result)
        row["predictions"] = predictions
        row["status"] = "ok"
        row["score"] = _score(path, predictions)
    except Exception as exc:  # retain every benchmark case as a result row
        row["failure_kind"] = type(exc).__name__
        row["failure_message"] = str(exc)[:400]
        row["score"] = {
            "target_function_count": None,
            "first_hit_rank": None,
            "recall_at_1": False,
            "recall_at_3": False,
            "recall_at_5": False,
        }
    row["latency_seconds"] = round(time.perf_counter() - started, 6)
    return row


def _run_one_worker(queue: Any, path_text: str, variant: str, model: str) -> None:
    try:
        queue.put(_run_one(Path(path_text), variant, model))
    except BaseException as exc:
        queue.put({
            "txn_hash": Path(path_text).stem,
            "variant": variant,
            "model": model,
            "provider": "none" if variant == "llm-free" else "configured-runtime",
            "status": "failed",
            "failure_kind": type(exc).__name__,
            "failure_message": str(exc)[:400],
            "predictions": [],
            "token_usage": {"input": 0, "output": 0, "source": "not-dispatched"},
            "actual_cost_usd": 0.0,
            "list_price_equivalent_usd": None,
            "score": {"target_function_count": None, "first_hit_rank": None,
                      "recall_at_1": False, "recall_at_3": False, "recall_at_5": False},
            "latency_seconds": None,
        })


def _run_one_bounded(path: Path, variant: str, model: str,
                     timeout_seconds: int | None) -> dict[str, Any]:
    if timeout_seconds is None:
        return _run_one(path, variant, model)
    queue = mp.Queue()
    process = mp.Process(target=_run_one_worker,
                         args=(queue, str(path), variant, model))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        metadata = _metadata(path)
        return {
            **metadata,
            "variant": variant,
            "model": model,
            "provider": "none" if variant == "llm-free" else "configured-runtime",
            "status": "failed",
            "failure_kind": "TimeoutError",
            "failure_message": f"per-transaction timeout after {timeout_seconds}s",
            "predictions": [],
            "token_usage": {"input": 0, "output": 0, "source": "not-dispatched"},
            "actual_cost_usd": 0.0,
            "list_price_equivalent_usd": None,
            "score": {"target_function_count": None, "first_hit_rank": None,
                      "recall_at_1": False, "recall_at_3": False, "recall_at_5": False},
            "latency_seconds": timeout_seconds,
        }
    if not queue.empty():
        return queue.get()
    return _run_one(path, variant, model)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    ok = sum(row["status"] == "ok" for row in rows)
    return {
        "n_total": total,
        "n_ok": ok,
        "n_failed": total - ok,
        "recall_at_1": sum(row["score"]["recall_at_1"] for row in rows) / total if total else 0.0,
        "recall_at_3": sum(row["score"]["recall_at_3"] for row in rows) / total if total else 0.0,
        "recall_at_5": sum(row["score"]["recall_at_5"] for row in rows) / total if total else 0.0,
        "failure_kinds": {
            kind: sum(row.get("failure_kind") == kind for row in rows)
            for kind in sorted({row.get("failure_kind") for row in rows if row.get("failure_kind")})
        },
        "actual_cost_usd": sum(row["actual_cost_usd"] for row in rows),
        "list_price_equivalent_usd": None,
        "token_totals": {"input": 0, "output": 0},
    }


def run(gt_dir: Path = DEFAULT_GT, output_dir: Path = DEFAULT_OUT,
        variant: str = "llm-free", model: str = "llm-free-function-ranker",
        limit: int | None = None, run_id: str = DEFAULT_RUN_ID,
        timeout_seconds: int | None = None) -> dict[str, Any]:
    random.seed(SEED)
    paths = sorted(gt_dir.glob("*.json"))
    if limit is not None:
        paths = paths[:limit]
    if len(paths) != 115 and limit is None:
        raise ValueError(f"original benchmark expected 115 files, found {len(paths)}")
    run_dir = output_dir / variant / run_id
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in paths:
        metadata = _metadata(path)
        raw_path = raw_dir / f"{metadata['case_id']}.json"
        if raw_path.is_file():
            try:
                row = json.loads(raw_path.read_text(encoding="utf-8"))
                if row.get("txn_hash") == metadata["txn_hash"]:
                    rows.append(row)
                    continue
            except (OSError, ValueError):
                pass
        row = _run_one_bounded(path, variant, model, timeout_seconds)
        rows.append(row)
        raw_path = raw_dir / f"{row['case_id']}.json"
        raw_path.write_text(
            json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        state = {
            "run_id": run_id,
            "variant": variant,
            "next_transaction_index": len(rows),
            "completed_n": len(rows),
            "target_n": len(paths),
            "state": "RUNNING",
        }
        (run_dir / "state.json").write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "protocol": "benchmark/protocols/original_benchmark_function_localization_v1.md",
        "seed": SEED,
        "variant": variant,
        "model": model,
        "run_id": run_id,
        "provider": "none" if variant == "llm-free" else "configured-runtime",
        "ground_truth_dir": gt_dir.relative_to(ROOT).as_posix(),
        "ground_truth_file_count": len(paths),
        "ground_truth_sha256": {path.name: _sha256(path) for path in paths},
        "rows": rows,
        "aggregate": _aggregate(rows),
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "state.json").write_text(json.dumps({
        "run_id": run_id, "variant": variant,
        "next_transaction_index": len(rows), "completed_n": len(rows),
        "target_n": len(paths), "state": "COMPLETE",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["llm-free"], default="llm-free")
    parser.add_argument("--model", default="llm-free-function-ranker")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--per-tx-timeout", type=int, default=90)
    args = parser.parse_args()
    result = run(output_dir=args.output_dir, variant=args.variant,
                 model=args.model, limit=args.limit, run_id=args.run_id,
                 timeout_seconds=args.per_tx_timeout)
    aggregate = result["aggregate"]
    print(f"variant={result['variant']}")
    print(f"n_total={aggregate['n_total']}")
    print(f"n_ok={aggregate['n_ok']}")
    print(f"n_failed={aggregate['n_failed']}")
    print(f"recall_at_1={aggregate['recall_at_1']:.6f}")
    print(f"recall_at_3={aggregate['recall_at_3']:.6f}")
    print(f"recall_at_5={aggregate['recall_at_5']:.6f}")
    print(f"actual_cost_usd={aggregate['actual_cost_usd']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
