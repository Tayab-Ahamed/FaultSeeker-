"""Read-only miner for the frozen Batch A transaction artifact.

This runner deliberately does not import the FaultSeeker analysis pipeline.  It
only sends ``debug_traceTransaction`` JSON-RPC requests, records the complete
responses, and produces evidence that is safe for a later validation step.

The artifact hash is checked before the JSON is parsed or any network request
is made.  Output files are created under a unique run directory and are opened
with exclusive-create semantics so a rerun cannot overwrite evidence.

Usage::

    python scripts/mine_batch_a.py

The default artifact is ``reports/new_batches/batchA_candidates.json``.  The
runner reads existing environment variables and, when present, the local
``.env`` file.  It never prints or writes endpoint URLs containing credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


EXPECTED_ARTIFACT_SHA256 = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
TARGET_ROWS = 40
ALLOWED_CHAINS = {"eth", "base", "polygon", "bsc"}
RPC_METHOD = "debug_traceTransaction"
REQUESTS_PER_SECOND = 2.0
PAYMENT_PROMPT_MARKERS = (
    "paid plan",
    "billing",
    "credit card",
    "payment required",
    "upgrade",
    "add a card",
    "subscribe",
    "payment method",
)


class MinerError(RuntimeError):
    """Expected, user-actionable preflight or transport failure."""


class ArtifactMismatch(MinerError):
    """The supplied artifact is not the frozen artifact."""


class PaymentPromptDetected(MinerError):
    """A provider response contains a paid-plan/payment prompt."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_endpoint_label(url: str) -> str:
    """Return a stable label without query strings, paths, or credentials."""
    parsed = urlparse(url)
    host = parsed.hostname or "unknown-host"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{parsed.scheme or 'unknown'}://{host}/…#{digest}"


def _load_dotenv_without_logging(path: Path) -> None:
    """Load simple KEY=VALUE entries without importing a dotenv package."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _chain_tokens(chain: str) -> tuple[str, str]:
    return chain, {"eth": "ethereum", "bsc": "bsc"}.get(chain, chain)


def _expand_endpoint(template: str, chain: str, credential: str = "") -> str:
    short, network = _chain_tokens(chain)
    result = template.replace("{chain}", short).replace("{network}", network)
    if "{api_key}" in result:
        if not credential:
            raise MinerError("configured RPC template requires a missing API key")
        result = result.replace("{api_key}", quote(credential, safe=""))
    return result


def _configured_blockpi(chain: str) -> str:
    upper = chain.upper()
    names = (
        f"{upper}_BLOCKPI_RPC_URL",
        f"BLOCKPI_{upper}_RPC_URL",
        "BLOCKPI_RPC_URL",
    )
    for name in names:
        value = _env(name)
        if value:
            return _expand_endpoint(value, chain, _env("BLOCKPI_API_KEY"))

    # Some existing configurations put a BlockPI URL in the normal chain slot.
    value = _env(f"{upper}_RPC_URL")
    if value and "blockpi" in value.lower():
        return _expand_endpoint(value, chain, _env("BLOCKPI_API_KEY"))
    return ""


def _configured_drpc(chain: str) -> str:
    upper = chain.upper()
    names = (
        f"{upper}_DRPC_RPC_URL",
        f"{upper}_DRPC_URL",
        "DRPC_RPC_URL",
    )
    for name in names:
        value = _env(name)
        if value:
            return _expand_endpoint(value, chain, _env("DRPC_API_KEY"))
    return ""


def select_endpoints(chains: Iterable[str]) -> dict[str, dict[str, str]]:
    """Select only configured BlockPI/dRPC endpoints for the requested chains."""
    selected: dict[str, dict[str, str]] = {}
    for chain in chains:
        blockpi = _configured_blockpi(chain)
        if chain in {"eth", "bsc"} and blockpi:
            selected[chain] = {"provider": "blockpi", "url": blockpi}
            continue
        drpc = _configured_drpc(chain)
        if drpc:
            selected[chain] = {"provider": "drpc", "url": drpc}
            continue
        raise MinerError(
            f"missing configured {'dRPC' if chain in {'eth', 'bsc'} else 'dRPC or BlockPI'} endpoint for {chain}"
        )
    return selected


def canonical_artifact_sha256(artifact: dict[str, Any]) -> str:
    """Hash the frozen payload using the artifact's canonical JSON convention."""
    payload = dict(artifact)
    payload.pop("artifact_sha256", None)
    canonical = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_and_validate_artifact(path: Path) -> tuple[dict[str, Any], str]:
    """Verify the embedded frozen digest, retaining the raw byte hash as evidence."""
    observed_raw_sha256 = sha256_file(path)
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MinerError(f"cannot read artifact JSON: {type(exc).__name__}") from exc
    if not isinstance(artifact, dict):
        raise ArtifactMismatch("artifact JSON top level is not an object")
    embedded = artifact.get("artifact_sha256")
    canonical = canonical_artifact_sha256(artifact)
    if embedded != EXPECTED_ARTIFACT_SHA256 or canonical != EXPECTED_ARTIFACT_SHA256:
        raise ArtifactMismatch(
            "canonical artifact SHA-256 mismatch: "
            f"expected {EXPECTED_ARTIFACT_SHA256}, embedded {embedded}, computed {canonical}"
        )
    rows = artifact.get("rows") if isinstance(artifact, dict) else None
    if not isinstance(rows, list) or len(rows) != TARGET_ROWS:
        raise MinerError(f"artifact must contain exactly {TARGET_ROWS} rows")
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise MinerError(f"artifact row {index} is not an object")
        chain = str(row.get("chain", "")).lower()
        tx_hash = row.get("transaction_hash")
        if chain not in ALLOWED_CHAINS:
            raise MinerError(f"artifact row {index} has unsupported chain")
        if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
            raise MinerError(f"artifact row {index} has invalid transaction hash")
    return artifact, observed_raw_sha256


def _write_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")


def _new_run_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        candidate = root / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:10]}"
        try:
            candidate.mkdir()
            (candidate / "raw").mkdir()
            (candidate / "attempts").mkdir()
            (candidate / "checkpoints").mkdir()
            (candidate / "diagnostics").mkdir()
            return candidate
        except FileExistsError:
            continue
    raise MinerError("could not allocate a unique output directory")


def _safe_text(text: str, secrets: Iterable[str]) -> str:
    result = str(text)
    for secret in secrets:
        if secret and len(secret) >= 4:
            result = result.replace(secret, "[REDACTED]")
    return result


def _path_label(path: Path) -> str:
    """Prefer a workspace-relative path in persisted reports."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _payment_prompt(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PAYMENT_PROMPT_MARKERS)


def _json_or_text(body: str, secrets: Iterable[str]) -> Any:
    scrubbed = _safe_text(body, secrets)
    try:
        return json.loads(scrubbed)
    except json.JSONDecodeError:
        return {"raw_text": scrubbed}


def _failure_cause(response: Any, status: int | None, error: str | None = None) -> str | None:
    if error:
        return error
    if isinstance(response, dict) and isinstance(response.get("error"), dict):
        rpc_error = response["error"]
        code = rpc_error.get("code")
        message = str(rpc_error.get("message", "RPC error"))
        return f"rpc_error:{code}:{message[:240]}"
    if status is not None and not 200 <= status < 300:
        return f"http_status:{status}"
    if not isinstance(response, dict) or "result" not in response:
        return "malformed_json_rpc_response"
    return None


def _request(endpoint: str, tx_hash: str, request_id: int, timeout: float) -> tuple[int | None, str, str | None]:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": RPC_METHOD,
        "params": [tx_hash, {"tracer": "callTracer"}],
    }).encode("utf-8")
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace"), None
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), None
    except (TimeoutError, URLError, OSError) as exc:
        return None, "", type(exc).__name__


class RateLimiter:
    def __init__(self, requests_per_second: float = REQUESTS_PER_SECOND) -> None:
        self.interval = 1.0 / requests_per_second
        self.last_dispatch = 0.0

    def wait(self) -> None:
        delay = self.interval - (time.monotonic() - self.last_dispatch)
        if delay > 0:
            time.sleep(delay)
        self.last_dispatch = time.monotonic()


def _summary(chain_rows: dict[str, list[dict[str, Any]]], endpoints: dict[str, dict[str, str]]) -> dict[str, Any]:
    per_chain = {}
    for chain, rows in chain_rows.items():
        failures: dict[str, int] = {}
        for row in rows:
            cause = row.get("failure_cause")
            if cause:
                failures[cause] = failures.get(cause, 0) + 1
        per_chain[chain] = {
            "provider": endpoints[chain]["provider"],
            "endpoint": safe_endpoint_label(endpoints[chain]["url"]),
            "attempted": len(rows),
            "successes": sum(row["success"] is True for row in rows),
            "failures": sum(row["success"] is not True for row in rows),
            "failure_causes": failures,
        }
    return per_chain


def run(artifact_path: Path, output_root: Path, timeout: float = 30.0) -> tuple[Path, dict[str, Any]]:
    """Mine Batch A, returning the unique run directory and final manifest."""
    run_dir = _new_run_dir(output_root)
    diagnostics_path = run_dir / "diagnostics" / "stderr.log"
    diagnostics = diagnostics_path.open("x", encoding="utf-8", newline="\n")
    started = utc_now()
    try:
        _load_dotenv_without_logging(artifact_path.parents[2] / ".env")
        try:
            artifact, observed_raw_sha256 = load_and_validate_artifact(artifact_path)
            endpoints = select_endpoints(sorted({row["chain"] for row in artifact["rows"]}))
        except Exception as exc:
            message = _safe_text(str(exc), os.environ.values())
            diagnostics.write(f"{utc_now()} {type(exc).__name__}: {message}\n")
            manifest = {
                "status": "BLOCKED",
                "reason": type(exc).__name__,
                "message": message,
                "artifact_path": _path_label(artifact_path),
                "expected_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
                "observed_artifact_sha256": sha256_file(artifact_path) if artifact_path.is_file() else None,
                "started_at": started,
                "finished_at": utc_now(),
                "network_requests": 0,
            }
            _write_exclusive(run_dir / "manifest.json", manifest)
            return run_dir, manifest

        secrets = [value for value in os.environ.values() if value and len(value) >= 4]
        rows_by_chain: dict[str, list[dict[str, Any]]] = {chain: [] for chain in endpoints}
        limiter = RateLimiter()
        stopped_reason = None
        for sequence, row in enumerate(artifact["rows"], 1):
            chain = row["chain"]
            tx_hash = row["transaction_hash"]
            endpoint = endpoints[chain]
            limiter.wait()
            attempt_started = utc_now()
            status, body, transport_error = _request(endpoint["url"], tx_hash, sequence, timeout)
            scrubbed_body = _safe_text(body, secrets)
            response = _json_or_text(scrubbed_body, ())
            raw_name = f"{sequence:03d}_{chain}_{tx_hash}_attempt01.json"
            raw_path = run_dir / "raw" / raw_name
            _write_exclusive(raw_path, scrubbed_body)
            prompt = _payment_prompt(scrubbed_body)
            cause = _failure_cause(response, status, transport_error)
            success = cause is None and status is not None and 200 <= status < 300
            if prompt:
                success = False
                cause = "payment_prompt_detected"
                stopped_reason = "PAYMENT_PROMPT_DETECTED"
            attempt = {
                "sequence": sequence,
                "chain": chain,
                "transaction_hash": tx_hash,
                "attempt": 1,
                "method": RPC_METHOD,
                "provider": endpoint["provider"],
                "endpoint": safe_endpoint_label(endpoint["url"]),
                "started_at": attempt_started,
                "finished_at": utc_now(),
                "http_status": status,
                "success": success,
                "failure_cause": _safe_text(cause, secrets) if cause else None,
                "payment_prompt_detected": prompt,
                "raw_response_path": raw_path.relative_to(run_dir).as_posix(),
            }
            attempt_path = run_dir / "attempts" / f"{sequence:03d}_{chain}_{tx_hash}_attempt01.json"
            _write_exclusive(attempt_path, attempt)
            rows_by_chain[chain].append(attempt)
            if sequence % 10 == 0 or stopped_reason:
                checkpoint = {
                    "status": "STOPPED" if stopped_reason else "IN_PROGRESS",
                    "processed": sequence,
                    "target": TARGET_ROWS,
                    "artifact_sha256": artifact["artifact_sha256"],
                    "raw_file_sha256": observed_raw_sha256,
                    "per_chain": _summary(rows_by_chain, endpoints),
                    "last_attempt": attempt_path.relative_to(run_dir).as_posix(),
                    "created_at": utc_now(),
                }
                _write_exclusive(run_dir / "checkpoints" / f"checkpoint_{sequence:03d}.json", checkpoint)
            if stopped_reason:
                diagnostics.write(f"{utc_now()} payment prompt detected at sequence {sequence}; stopped\n")
                break

        processed = sum(len(rows) for rows in rows_by_chain.values())
        manifest = {
            "status": "BLOCKED" if stopped_reason else "COMPLETE",
            "stop_reason": stopped_reason,
            "artifact_path": _path_label(artifact_path),
            "artifact_sha256": artifact["artifact_sha256"],
            "raw_file_sha256": observed_raw_sha256,
            "target_rows": TARGET_ROWS,
            "processed_rows": processed,
            "network_requests": processed,
            "method": RPC_METHOD,
            "trace_config": {"tracer": "callTracer"},
            "rate_limit_requests_per_second": REQUESTS_PER_SECOND,
            "providers": {
                chain: {
                    "provider": selected["provider"],
                    "endpoint": safe_endpoint_label(selected["url"]),
                }
                for chain, selected in endpoints.items()
            },
            "per_chain": _summary(rows_by_chain, endpoints),
            "started_at": started,
            "finished_at": utc_now(),
            "raw_response_directory": "raw",
            "attempt_artifact_directory": "attempts",
            "checkpoint_directory": "checkpoints",
            "diagnostics_directory": "diagnostics",
        }
        _write_exclusive(run_dir / "manifest.json", manifest)
        return run_dir, manifest
    finally:
        diagnostics.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only frozen Batch A trace miner")
    parser.add_argument("--artifact", type=Path, default=Path("reports/new_batches/batchA_candidates.json"))
    parser.add_argument("--output-root", type=Path, default=Path("reports/new_batches/batchA_mining"))
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    artifact = args.artifact.resolve()
    output_root = args.output_root.resolve()
    try:
        run_dir, manifest = run(artifact, output_root, timeout=args.timeout)
    except Exception as exc:  # keep CLI diagnostics concise and credential-free
        print(f"runner failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"run directory: {run_dir}")
    print(f"status: {manifest['status']}")
    if manifest["status"] == "BLOCKED":
        print(f"reason: {manifest.get('reason') or manifest.get('stop_reason')}")
        return 2
    print(f"processed: {manifest['processed_rows']}/{manifest['target_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
