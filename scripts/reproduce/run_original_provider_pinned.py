"""Run the original 115-case benchmark with one pinned RPC per chain.

This runner is deliberately separate from the production failover registry:
Ethereum and BSC use the BlockPI endpoints supplied through RUN_ETH_RPC_URL
and RUN_BSC_RPC_URL. dRPC remains a spare and is not used by this run. It preserves every
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
RATE_LIMIT_MAX_ATTEMPTS_PER_CASE = 5
RETRY_PASS_CUPS = 2


class RateLimitAbort(BaseException):
    """Abort the current case without allowing provider failover."""

    def __init__(self, provider: str, code: str, error_text: str = ""):
        self.provider = provider
        self.code = code
        self.error_text = error_text[:1200]
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


def _fatal_provider_text(text: str) -> bool:
    return bool(re.search(
        r"\b(?:ban(?:ned)?|block(?:ed)?|billing|payment|quota|upgrade|plan required|suspend(?:ed)?)\b",
        text or "", re.IGNORECASE))


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
                raise RateLimitAbort("BlockPI", "429", message)
            if "503" in message:
                raise RateLimitAbort("BlockPI", "503", message)
            raise

    rpc._http_post = paced_post

    from faultseeker.data_collection import txn_replayer

    def pinned_cast(txn_hash: str, rpc_url: str) -> str | None:
        chain = "eth" if rpc_url == eth_url else "bsc"
        provider = "BlockPI"
        cast_counts[chain] += 1
        binary = os.path.join(os.environ["FOUNDRY_BIN"], "cast.exe")
        cups = int(cast_context.get("compute_units_per_second", 5))
        command = [
            binary, "run", "--quick", txn_hash, "--rpc-url", rpc_url,
            "--rpc-timeout", "45", "--compute-units-per-second",
            str(cups), "--threads", "1",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=False, timeout=90)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"cast timeout after 90s: {txn_hash}") from exc
        stdout = (result.stdout or b"").decode("utf-8", errors="replace")
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")
        combined = (stdout + "\n" + stderr).replace(rpc_url, "[RPC_REDACTED]")
        if re.search(r"(?:HTTP\s*)?429\b|rate limit|too many requests", combined, re.I):
            raise RateLimitAbort(provider, "429", combined)
        if re.search(r"(?:HTTP\s*)?503\b|service unavailable", combined, re.I):
            raise RateLimitAbort(provider, "503", combined)
        cast_context["last"] = {
            "provider": provider,
            "exit_code": result.returncode,
            "compute_units_per_second": cups,
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
    retry_queue: list[int] = []
    consecutive_failures = 0
    last_network_tx = False

    for index, path in enumerate(paths):
        metadata = _metadata(path)
        raw_path = raw_dir / f"{metadata['case_id']}.json"
        if raw_path.is_file():
            try:
                existing = json.loads(raw_path.read_text(encoding="utf-8"))
                can_reuse_prefix = index < args.resume_from
                if (existing.get("txn_hash") == metadata["txn_hash"]
                        and (can_reuse_prefix or existing.get("run_config_hash") == args.run_config_hash)):
                    rows.append(existing)
                    if existing.get("status") != "ok":
                        retry_queue.append(index)
                    last_network_tx = True
                    continue
            except (OSError, ValueError):
                pass

        if last_network_tx:
            time.sleep(BETWEEN_TX_SECONDS)
        provider = "BlockPI"
        attempts: list[dict[str, Any]] = []
        rate_limit_errors: list[str] = []
        started = time.perf_counter()
        request_counts_before = dict(request_counts)
        cast_counts_before = dict(cast_counts)
        cast_context["compute_units_per_second"] = 5
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
                    "request_count_delta": {
                        chain: request_counts[chain] - request_counts_before[chain]
                        for chain in request_counts
                    },
                    "cast_process_delta": {
                        chain: cast_counts[chain] - cast_counts_before[chain]
                        for chain in cast_counts
                    },
                    "attempts": attempts + [{"attempt": len(attempts) + 1, "status": "ok"}],
                    "failure_kind": None,
                    "failure_message": None,
                    "latency_seconds": round(time.perf_counter() - started, 6),
                }
                consecutive_failures = 0
                break
            except RateLimitAbort as exc:
                error_text = exc.error_text or str(exc)
                rate_limit_errors.append(error_text)
                attempt_number = len(attempts) + 1
                attempts.append({
                    "attempt": attempt_number,
                    "status": "rate_limited_or_unavailable",
                    "provider": exc.provider,
                    "code": exc.code,
                    "error_text": error_text,
                    "backoff_seconds": min(RETRY_WAIT_BASE * (2 ** (attempt_number - 1)), RETRY_WAIT_MAX),
                })
                if _fatal_provider_text(error_text):
                    raise RuntimeError(f"fatal provider warning: {error_text[:500]}") from exc
                if attempt_number < RATE_LIMIT_MAX_ATTEMPTS_PER_CASE:
                    wait = min(RETRY_WAIT_BASE * (2 ** (attempt_number - 1)), RETRY_WAIT_MAX)
                    print(f"rate-limit provider={provider} tx={metadata['txn_hash']} "
                          f"code={exc.code} wait={wait}s error={error_text[-500:]}", flush=True)
                    time.sleep(wait)
                    continue
                row = {
                    **metadata,
                    "run_config_hash": args.run_config_hash,
                    "provider": provider,
                    "variant": "llm-free",
                    "model": args.model,
                    "status": "failed",
                    "predictions": [],
                    "score": _failure_score(),
                    "replay_mismatch": False,
                    "cast": cast_context.get("last", {}),
                    "request_count_delta": {
                        chain: request_counts[chain] - request_counts_before[chain]
                        for chain in request_counts
                    },
                    "cast_process_delta": {
                        chain: cast_counts[chain] - cast_counts_before[chain]
                        for chain in cast_counts
                    },
                    "attempts": attempts,
                    "failure_kind": "ProviderRateLimited",
                    "failure_message": "\n---\n".join(rate_limit_errors)[-2000:],
                    "latency_seconds": round(time.perf_counter() - started, 6),
                }
                break
            except BaseException as exc:
                error_text = str(exc)[:1200]
                if _fatal_provider_text(error_text):
                    raise RuntimeError(f"fatal provider warning: {error_text[:500]}") from exc
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
                    "request_count_delta": {
                        chain: request_counts[chain] - request_counts_before[chain]
                        for chain in request_counts
                    },
                    "cast_process_delta": {
                        chain: cast_counts[chain] - cast_counts_before[chain]
                        for chain in cast_counts
                    },
                    "attempts": attempts + [{"attempt": len(attempts) + 1, "status": "failed",
                                               "error_text": error_text}],
                    "failure_kind": type(exc).__name__,
                    "failure_message": error_text[:500],
                    "latency_seconds": round(time.perf_counter() - started, 6),
                }
                break

        rows.append(row)
        if row.get("status") == "ok":
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            retry_queue.append(index)
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
        if consecutive_failures >= 10:
            _atomic_json(run_dir / "state.json", {
                "run_id": args.run_id, "state": "PAUSED_CONSECUTIVE_FAILURES",
                "next_transaction_index": index + 1, "completed_n": len(rows),
                "target_n": len(paths), "consecutive_failures": consecutive_failures,
                "request_counts": request_counts, "cast_process_counts": cast_counts,
                "mismatch_count": sum(bool(item.get("replay_mismatch")) for item in rows),
            })
            raise RuntimeError("ten consecutive failed cases; run paused")

    # One retry pass for every failed case, at the lower Foundry rate setting.
    retry_results: list[dict[str, Any]] = []
    retry_consecutive_failures = 0
    for index in retry_queue:
        path = paths[index]
        metadata = _metadata(path)
        provider = "BlockPI"
        started = time.perf_counter()
        request_counts_before = dict(request_counts)
        cast_counts_before = dict(cast_counts)
        cast_context["compute_units_per_second"] = RETRY_PASS_CUPS
        try:
            from faultseeker.forensics.orchestrator import ForensicsOrchestrator
            from faultseeker.function_analysis.function_ranker import FunctionRanker

            result = ForensicsOrchestrator(model=args.model).run(
                metadata["txn_hash"], metadata["chain"])
            if isinstance(result, tuple):
                result = result[0]
            if not result:
                raise RuntimeError("orchestrator returned no result on retry pass")
            tx_analysis = {
                "repeated_patterns": result.repeated_patterns,
                "function_call_loc_memo": result.function_call_loc_memo,
            }
            predictions = [dict(item) for item in FunctionRanker().rank(
                result, tx_analysis).ranked_functions]
            retry_row = {
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
                "request_count_delta": {
                    chain: request_counts[chain] - request_counts_before[chain]
                    for chain in request_counts
                },
                "cast_process_delta": {
                    chain: cast_counts[chain] - cast_counts_before[chain]
                    for chain in cast_counts
                },
                "attempts": [{"attempt": 1, "status": "retry_pass", "compute_units_per_second": 2}],
                "failure_kind": None,
                "failure_message": None,
                "retry_pass": True,
                "latency_seconds": round(time.perf_counter() - started, 6),
            }
        except RateLimitAbort as exc:
            retry_row = {
                **metadata, "run_config_hash": args.run_config_hash,
                "provider": provider, "variant": "llm-free", "model": args.model,
                "status": "failed", "predictions": [], "score": _failure_score(),
                "replay_mismatch": False, "cast": cast_context.get("last", {}),
                "request_count_delta": {
                    chain: request_counts[chain] - request_counts_before[chain]
                    for chain in request_counts
                },
                "cast_process_delta": {
                    chain: cast_counts[chain] - cast_counts_before[chain]
                    for chain in cast_counts
                },
                "attempts": [{"attempt": 1, "status": "retry_rate_limited",
                               "code": exc.code, "error_text": exc.error_text}],
                "failure_kind": "ProviderRateLimitedRetryPass",
                "failure_message": exc.error_text,
                "retry_pass": True,
                "latency_seconds": round(time.perf_counter() - started, 6),
            }
        except BaseException as exc:
            error_text = str(exc)[:1200]
            if _fatal_provider_text(error_text):
                raise RuntimeError(f"fatal provider warning during retry pass: {error_text[:500]}") from exc
            retry_row = {
                **metadata, "run_config_hash": args.run_config_hash,
                "provider": provider, "variant": "llm-free", "model": args.model,
                "status": "failed", "predictions": [], "score": _failure_score(),
                "replay_mismatch": False, "cast": cast_context.get("last", {}),
                "request_count_delta": {
                    chain: request_counts[chain] - request_counts_before[chain]
                    for chain in request_counts
                },
                "cast_process_delta": {
                    chain: cast_counts[chain] - cast_counts_before[chain]
                    for chain in cast_counts
                },
                "attempts": [{"attempt": 1, "status": "retry_failed", "error_text": error_text}],
                "failure_kind": type(exc).__name__, "failure_message": error_text,
                "retry_pass": True,
                "latency_seconds": round(time.perf_counter() - started, 6),
            }
        rows[index] = retry_row
        _atomic_json(args.output_dir / args.run_id / "raw" / f"{metadata['case_id']}.json", retry_row)
        if retry_row.get("replay_mismatch"):
            with mismatch_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "index": index, "case_id": metadata["case_id"],
                    "txn_hash": metadata["txn_hash"], "chain": metadata["chain"],
                    "provider": provider, "retry_pass": True,
                    "cast": retry_row.get("cast", {}),
                }, sort_keys=True) + "\n")
        retry_results.append(retry_row)
        retry_consecutive_failures = retry_consecutive_failures + 1 if retry_row["status"] != "ok" else 0
        _atomic_json(args.output_dir / args.run_id / "state.json", {
            "run_id": args.run_id, "state": "RETRY_PASS_RUNNING",
            "next_transaction_index": len(paths), "completed_n": len(rows),
            "target_n": len(paths), "retry_index": len(retry_results),
            "retry_total": len(retry_queue), "request_counts": request_counts,
            "cast_process_counts": cast_counts,
            "mismatch_count": sum(bool(item.get("replay_mismatch")) for item in rows),
        })
        print(f"retry case={index + 1}/{len(paths)} provider={provider} "
              f"status={retry_row['status']} cups=2", flush=True)
        if retry_consecutive_failures >= 10:
            raise RuntimeError("ten consecutive failed retry cases; run paused")

    manifest = {
        "protocol": "benchmark/protocols/original_benchmark_function_localization_v1.md",
        "seed": SEED, "run_id": args.run_id, "variant": "llm-free",
        "model": args.model,
        "provider_policy": {"eth": "BlockPI", "bsc": "BlockPI", "spare": "dRPC-not-used"},
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
    parser.add_argument("--resume-from", type=int, default=0,
                        help="Reuse verified raw rows before this zero-based case index")
    args = parser.parse_args()
    args.run_config_hash = hashlib.sha256(json.dumps({
        "run_id": args.run_id, "model": args.model,
        "provider_policy": {"eth": "BlockPI", "bsc": "BlockPI", "spare": "dRPC-not-used"},
        "between_transactions_seconds": BETWEEN_TX_SECONDS,
        "resume_from": args.resume_from,
    }, sort_keys=True).encode()).hexdigest()
    result = run(args)
    aggregate = result["aggregate"]
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
