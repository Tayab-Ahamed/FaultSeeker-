"""Run the original 115-case benchmark with one pinned RPC per chain.

This runner is deliberately separate from the production failover registry:
Ethereum uses the dRPC endpoint supplied through RUN_ETH_RPC_URL and BSC uses
the BlockPI endpoint supplied through RUN_BSC_RPC_URL.  It preserves every
case, writes a raw row after each case, and stops after five consecutive
rate-limit/server-unavailable responses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
DEFAULT_OUT = ROOT / "reports/original_benchmark/provider-pinned"
SEED = 20261017
RETRY_WAIT_BASE = 30
RETRY_WAIT_MAX = 600
BETWEEN_TX_SECONDS = 4.0
RATE_LIMIT_MAX_CONSECUTIVE = 5


class RateLimitAbort(BaseException):
    """Abort the current case without allowing provider failover."""

    def __init__(self, provider: str, code: str):
        self.provider = provider
        self.code = code
        super().__init__(f"{provider} returned {code}")


def _safe_label(url: str) -> str:
    parsed = urlparse(url)
    digest = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"{parsed.scheme}://{parsed.hostname}/…#{digest}"


def _read_dotenv_value(name: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"").strip("'")
    return ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metadata(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    value = str(raw.get("platform") or raw.get("chain") or "eth").strip().lower()
    chain = {
        "ethereum": "eth", "mainnet": "eth", "bnbchain": "bsc",
        "binance": "bsc", "binancesmartchain": "bsc",
    }.get(value, value)
    values = raw.get("transaction_hash") or []
    if isinstance(values, str):
        values = [values]
    txn_hash = str(values[0] if values else path.stem).strip().lower()
    return {"case_id": path.stem, "txn_hash": txn_hash,
            "chain": chain, "filename": path.name}


def _atomic_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    # Windows can briefly deny a rename while an antivirus/indexer has the
    # destination open.  Keep checkpointing durable: retry the replace, then
    # fall back to a direct write of the target instead of losing progress.
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    for attempt in range(5):
        try:
            temp.write_text(payload, encoding="utf-8")
            os.replace(temp, path)
            return
        except PermissionError:
            time.sleep(0.5 * (attempt + 1))
    path.write_text(payload, encoding="utf-8")


def _score(gt_path: Path, predictions: list[dict[str, Any]]) -> dict[str, Any]:
    from benchmark.honest_eval.localization import (
        LocalizationTarget, _parse_location_entry, _register_fn_names,
        rank_of_first_hit,
    )

    raw = json.loads(gt_path.read_text(encoding="utf-8-sig"))
    values = raw.get("transaction_hash") or []
    if isinstance(values, str):
        values = [values]
    target = LocalizationTarget(
        txn_hash=str(values[0] if values else gt_path.stem),
        name=str(raw.get("name") or ""),
    )
    names: list[str] = []
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


def _failure_score() -> dict[str, Any]:
    return {
        "target_function_count": None,
        "first_hit_rank": None,
        "recall_at_1": False,
        "recall_at_3": False,
        "recall_at_5": False,
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    ok = sum(row.get("status") == "ok" for row in rows)
    return {
        "n_total": total,
        "n_ok": ok,
        "n_failed": total - ok,
        "recall_at_1": sum(bool(row["score"]["recall_at_1"]) for row in rows) / total if total else 0.0,
        "recall_at_3": sum(bool(row["score"]["recall_at_3"]) for row in rows) / total if total else 0.0,
        "recall_at_5": sum(bool(row["score"]["recall_at_5"]) for row in rows) / total if total else 0.0,
        "failure_kinds": {
            kind: sum(row.get("failure_kind") == kind for row in rows)
            for kind in sorted({row.get("failure_kind") for row in rows if row.get("failure_kind")})
        },
        "mismatch_count": sum(bool(row.get("replay_mismatch")) for row in rows),
        "denominator_includes_failures": True,
    }


def _configure_runtime(eth_url: str, bsc_url: str) -> tuple[Any, Any]:
    """Import the runtime, then remove every fallback except the two pinned URLs."""
    os.environ["ETH_RPC_URL"] = eth_url
    os.environ["BSC_RPC_URL"] = bsc_url
    os.environ["FOUNDRY_BIN"] = str(ROOT / "tools/foundry/bin")

    from benchmark.original_benchmark_eval import _predictions
    from faultseeker.utils import rpc_provider as rpc

    rpc._PUBLIC["eth"] = []
    rpc._PUBLIC["bsc"] = []
    rpc._registry._chains.clear()
    os.environ.pop("DRPC_RPC_URL", None)
    os.environ.pop("DRPC_API_KEY", None)
    return rpc, _predictions


def _install_guards(rpc: Any, eth_url: str, bsc_url: str,
                    request_counts: dict[str, int], cast_counts: dict[str, int],
                    cast_context: dict[str, Any]) -> None:
    """Add pacing and hard-stop handling around all direct RPC/cast calls."""
    original_post = rpc._http_post
    last_request = {"eth": 0.0, "bsc": 0.0}

    def paced_post(url: str, body: bytes, timeout: int = 5) -> Any:
        chain = "eth" if url == eth_url else "bsc"
        now = time.monotonic()
        wait = 0.2 - (now - last_request[chain])
        if wait > 0:
            time.sleep(wait)
        last_request[chain] = time.monotonic()
        request_counts[chain] += 1
        try:
            return original_post(url, body, timeout=timeout)
        except Exception as exc:
            message = str(exc)
            if isinstance(exc, rpc._RateLimitError) or "429" in message:
                raise RateLimitAbort("dRPC" if chain == "eth" else "BlockPI", "429")
            if "503" in message:
                raise RateLimitAbort("dRPC" if chain == "eth" else "BlockPI", "503")
            raise

    rpc._http_post = paced_post

    from faultseeker.data_collection import txn_replayer

    def pinned_cast(txn_hash: str, rpc_url: str) -> str | None:
        chain = "eth" if rpc_url == eth_url else "bsc"
        provider = "dRPC" if chain == "eth" else "BlockPI"
        cast_counts[chain] += 1
        binary = os.path.join(os.environ["FOUNDRY_BIN"], "cast.exe")
        command = [
            binary, "run", "--quick", txn_hash, "--rpc-url", rpc_url,
            "--rpc-timeout", "45", "--compute-units-per-second",
            "20" if chain == "eth" else "5", "--threads", "1",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=False, timeout=90)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"cast timeout after 90s: {txn_hash}") from exc
        stdout = (result.stdout or b"").decode("utf-8", errors="replace")
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")
        combined = stdout + "\n" + stderr
        if re.search(r"(?:HTTP\s*)?(?:429|503)\b|rate limit|too many requests", combined, re.I):
            raise RateLimitAbort(provider, "429/503")
        cast_context["last"] = {
            "provider": provider,
            "exit_code": result.returncode,
            "mismatch": "replay does not match" in combined.lower(),
            "output_tail": combined[-1200:],
        }
        if result.returncode:
            return None
        ansi_escape = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
        clean = ansi_escape.sub("", stdout)
        return clean if clean.strip() else None

    txn_replayer.TransactionReplayer._run_cast = staticmethod(pinned_cast)


def run(args: argparse.Namespace) -> dict[str, Any]:
    eth_url = os.environ.get("RUN_ETH_RPC_URL") or _read_dotenv_value("DRPC_RPC_URL")
    bsc_url = os.environ.get("RUN_BSC_RPC_URL", "")
    if not eth_url or not bsc_url:
        raise RuntimeError("RUN_ETH_RPC_URL and RUN_BSC_RPC_URL are required")

    rpc, predictions_fn = _configure_runtime(eth_url, bsc_url)
    request_counts = {"eth": 0, "bsc": 0}
    cast_counts = {"eth": 0, "bsc": 0}
    cast_context: dict[str, Any] = {"last": {}}
    _install_guards(rpc, eth_url, bsc_url, request_counts, cast_counts, cast_context)

    paths = sorted(args.ground_truth.glob("*.json"))
    if len(paths) != 115:
        raise ValueError(f"original benchmark expected 115 files, found {len(paths)}")
    run_dir = args.output_dir / args.run_id
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    prior_state = run_dir / "state.json"
    if prior_state.is_file():
        try:
            saved = json.loads(prior_state.read_text(encoding="utf-8"))
            for chain in request_counts:
                request_counts[chain] = int(saved.get("request_counts", {}).get(chain, 0))
                cast_counts[chain] = int(saved.get("cast_process_counts", {}).get(chain, 0))
        except (OSError, ValueError, TypeError):
            pass
    mismatch_path = run_dir / "mismatches.jsonl"
    rows: list[dict[str, Any]] = []
    consecutive_limited = 0
    last_network_tx = False

    for index, path in enumerate(paths):
        metadata = _metadata(path)
        raw_path = raw_dir / f"{metadata['case_id']}.json"
        if raw_path.is_file():
            try:
                existing = json.loads(raw_path.read_text(encoding="utf-8"))
                if (existing.get("txn_hash") == metadata["txn_hash"]
                        and existing.get("run_config_hash") == args.run_config_hash):
                    rows.append(existing)
                    last_network_tx = False
                    continue
            except (OSError, ValueError):
                pass

        if last_network_tx:
            time.sleep(BETWEEN_TX_SECONDS)
        provider = "dRPC" if metadata["chain"] == "eth" else "BlockPI"
        attempts: list[dict[str, Any]] = []
        started = time.perf_counter()
        while True:
            attempt_started = time.time()
            cast_context["last"] = {}
            try:
                from faultseeker.forensics.orchestrator import ForensicsOrchestrator
                from faultseeker.function_analysis.function_ranker import FunctionRanker

                result = ForensicsOrchestrator(model=args.model).run(
                    metadata["txn_hash"], metadata["chain"])
                if isinstance(result, tuple):
                    result = result[0]
                if not result:
                    raise RuntimeError("orchestrator returned no result")
                tx_analysis = {
                    "repeated_patterns": result.repeated_patterns,
                    "function_call_loc_memo": result.function_call_loc_memo,
                }
                predictions = [dict(item) for item in FunctionRanker().rank(
                    result, tx_analysis).ranked_functions]
                row = {
                    **metadata,
                    "run_config_hash": args.run_config_hash,
                    "provider": provider,
                    "variant": "llm-free",
                    "model": args.model,
                    "status": "ok",
                    "predictions": predictions,
                    "score": _score(path, predictions),
                    "replay_mismatch": bool(cast_context.get("last", {}).get("mismatch")),
                    "cast": cast_context.get("last", {}),
                    "attempts": attempts + [{"attempt": len(attempts) + 1, "status": "ok"}],
                    "failure_kind": None,
                    "failure_message": None,
                    "latency_seconds": round(time.perf_counter() - started, 6),
                }
                consecutive_limited = 0
                break
            except RateLimitAbort as exc:
                consecutive_limited += 1
                attempts.append({
                    "attempt": len(attempts) + 1,
                    "status": "rate_limited_or_unavailable",
                    "provider": exc.provider,
                    "code": exc.code,
                    "backoff_seconds": min(RETRY_WAIT_BASE * (2 ** (consecutive_limited - 1)), RETRY_WAIT_MAX),
                })
                if consecutive_limited >= RATE_LIMIT_MAX_CONSECUTIVE:
                    state = {
                        "run_id": args.run_id, "state": "PAUSED_RATE_LIMIT",
                        "next_transaction_index": index, "completed_n": len(rows),
                        "target_n": len(paths), "consecutive_rate_limit_failures": consecutive_limited,
                    }
                    _atomic_json(run_dir / "state.json", state)
                    raise RuntimeError("five consecutive 429/503 responses; run paused") from exc
                wait = min(RETRY_WAIT_BASE * (2 ** (consecutive_limited - 1)), RETRY_WAIT_MAX)
                print(f"rate-limit provider={provider} tx={metadata['txn_hash']} wait={wait}s", flush=True)
                time.sleep(wait)
                continue
            except BaseException as exc:
                row = {
                    **metadata,
                    "run_config_hash": args.run_config_hash,
                    "provider": provider,
                    "variant": "llm-free",
                    "model": args.model,
                    "status": "failed",
                    "predictions": [],
                    "score": _failure_score(),
                    "replay_mismatch": bool(cast_context.get("last", {}).get("mismatch")),
                    "cast": cast_context.get("last", {}),
                    "attempts": attempts + [{"attempt": len(attempts) + 1, "status": "failed"}],
                    "failure_kind": type(exc).__name__,
                    "failure_message": str(exc)[:500],
                    "latency_seconds": round(time.perf_counter() - started, 6),
                }
                break

        rows.append(row)
        _atomic_json(raw_path, row)
        if row.get("replay_mismatch"):
            with mismatch_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "index": index, "case_id": row["case_id"],
                    "txn_hash": row["txn_hash"], "chain": row["chain"],
                    "provider": row["provider"], "cast": row.get("cast", {}),
                }, sort_keys=True) + "\n")
        _atomic_json(run_dir / "state.json", {
            "run_id": args.run_id, "state": "RUNNING",
            "next_transaction_index": index + 1,
            "completed_n": len(rows), "target_n": len(paths),
            "request_counts": request_counts, "cast_process_counts": cast_counts,
            "mismatch_count": sum(bool(item.get("replay_mismatch")) for item in rows),
        })
        print(f"case={index + 1}/{len(paths)} chain={metadata['chain']} provider={provider} "
              f"status={row['status']} mismatch={row.get('replay_mismatch', False)}", flush=True)
        last_network_tx = True

    manifest = {
        "protocol": "benchmark/protocols/original_benchmark_function_localization_v1.md",
        "seed": SEED, "run_id": args.run_id, "variant": "llm-free",
        "model": args.model, "provider_policy": {"eth": "dRPC", "bsc": "BlockPI"},
        "ground_truth_file_count": len(paths),
        "ground_truth_sha256": {path.name: _sha256(path) for path in paths},
        "request_counts": request_counts,
        "cast_process_counts": cast_counts,
        "rate_policy": {
            "between_transactions_seconds": BETWEEN_TX_SECONDS,
            "direct_rpc_min_interval_seconds": 0.2,
            "backoff_seconds": [30, 60, 120, 240, 480, 600],
            "max_consecutive_rate_limit_failures": RATE_LIMIT_MAX_CONSECUTIVE,
        },
        "rows": rows,
        "aggregate": _aggregate(rows),
    }
    _atomic_json(run_dir / "manifest.json", manifest)
    _atomic_json(run_dir / "state.json", {
        "run_id": args.run_id, "state": "COMPLETE",
        "next_transaction_index": len(rows), "completed_n": len(rows),
        "target_n": len(paths), "request_counts": request_counts,
        "cast_process_counts": cast_counts,
    })
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", default="llm-free-function-ranker")
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.run_config_hash = hashlib.sha256(json.dumps({
        "run_id": args.run_id, "model": args.model,
        "provider_policy": {"eth": "dRPC", "bsc": "BlockPI"},
        "between_transactions_seconds": BETWEEN_TX_SECONDS,
    }, sort_keys=True).encode()).hexdigest()
    result = run(args)
    aggregate = result["aggregate"]
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
