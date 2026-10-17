"""Validate the frozen Batch A mining artifacts without network access.

This analyzer consumes only the frozen candidate artifact and one completed
mining run.  It deliberately keeps RPC failures separate from malformed trace
payloads and emits a deterministic valid-trace set plus a sidecar SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


CANONICAL_BATCH_SHA256 = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
HEX_RE = re.compile(r"^0x[0-9a-fA-F]*$")
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
FAILURE_LIMIT_MARKERS = ("rate limit", "too many requests", "limit exceeded", "timeout")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dump_json(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def parse_filename(path: Path) -> tuple[int, str, str]:
    match = re.match(
        r"^(\d+)_([^_]+)_(0x[0-9a-fA-F]{64})_attempt\d+\.json$",
        path.name,
    )
    if match is None:
        raise ValueError(f"unexpected attempt filename: {path.name}")
    return int(match.group(1)), match.group(2), match.group(3).lower()


def walk_trace(node: Any, path: str = "root") -> tuple[list[str], int, int]:
    """Return structural issues, node count, and maximum call depth."""

    if not isinstance(node, dict):
        return [f"{path}: node is not an object"], 0, 0

    issues: list[str] = []
    required = ("type", "from", "input", "gas", "gasUsed")
    for field in required:
        if field not in node:
            issues.append(f"{path}: missing {field}")

    if "from" in node and (
        not isinstance(node["from"], str) or not ADDRESS_RE.fullmatch(node["from"])
    ):
        issues.append(f"{path}: malformed from address")
    if "to" in node and (
        not isinstance(node["to"], str) or not ADDRESS_RE.fullmatch(node["to"])
    ):
        issues.append(f"{path}: malformed to address")
    for field in ("input", "output", "gas", "gasUsed", "value"):
        if field in node and (
            not isinstance(node[field], str) or not HEX_RE.fullmatch(node[field])
        ):
            issues.append(f"{path}: malformed hexadecimal {field}")

    calls = node.get("calls", [])
    if not isinstance(calls, list):
        issues.append(f"{path}: calls is not a list")
        calls = []

    count = 1
    max_depth = 0
    for index, child in enumerate(calls):
        child_issues, child_count, child_depth = walk_trace(
            child, f"{path}.calls[{index}]"
        )
        issues.extend(child_issues)
        count += child_count
        max_depth = max(max_depth, child_depth + 1)
    return issues, count, max_depth


def failure_category(reason: str) -> str:
    lowered = reason.lower()
    if any(marker in lowered for marker in FAILURE_LIMIT_MARKERS):
        return "rpc_limited"
    if lowered.startswith("rpc_error:"):
        return "rpc_error"
    return "other_failure"


def validate_success_payload(raw: Any, raw_text: str) -> tuple[str, str, int, int, list[str]]:
    """Return status, reason, node count, max depth, and evidence issues."""

    if not isinstance(raw, dict):
        return "invalid", "malformed: JSON-RPC envelope is not an object", 0, 0, [
            "JSON-RPC envelope is not an object"
        ]
    if raw.get("jsonrpc") != "2.0":
        return "invalid", "malformed: JSON-RPC version is not 2.0", 0, 0, [
            "jsonrpc != 2.0"
        ]
    if "error" in raw:
        return "invalid", "malformed: successful attempt contains an RPC error", 0, 0, [
            "error field present in success attempt"
        ]
    result = raw.get("result")
    if result is None or result == {}:
        return "invalid", "empty: successful attempt returned an empty result", 0, 0, [
            "empty result"
        ]
    if not isinstance(result, dict):
        return "invalid", "malformed: trace result is not an object", 0, 0, [
            "result is not an object"
        ]

    issues, node_count, max_depth = walk_trace(result)
    if "[REDACTED]" in raw_text:
        issues.append("literal [REDACTED] marker present in raw payload")
    if node_count <= 1 or max_depth == 0:
        issues.append("root-only callTracer result; no internal call frames")
    if issues:
        if any("[REDACTED]" in issue or "hexadecimal" in issue for issue in issues):
            reason = "malformed: non-hexadecimal/redacted field in callTracer payload"
        elif any("root-only" in issue for issue in issues):
            reason = "empty: callTracer payload contains only a root frame"
        else:
            reason = "malformed: callTracer tree failed structural validation"
        return "invalid", reason, node_count, max_depth, issues
    return (
        "valid",
        "valid: non-empty, recursively well-formed callTracer payload",
        node_count,
        max_depth,
        [],
    )


def analyze(candidate_path: Path, run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    declared_batch_sha = candidate.get("artifact_sha256")
    canonical_candidate = dict(candidate)
    canonical_candidate.pop("artifact_sha256", None)
    computed_batch_sha = sha256_bytes(dump_json(canonical_candidate))
    if declared_batch_sha != CANONICAL_BATCH_SHA256 or computed_batch_sha != CANONICAL_BATCH_SHA256:
        raise RuntimeError(
            "frozen Batch A canonical SHA-256 mismatch: "
            f"declared={declared_batch_sha} computed={computed_batch_sha}"
        )

    expected = [
        (index, row["chain"], row["transaction_hash"].lower())
        for index, row in enumerate(candidate["rows"], start=1)
    ]
    expected_pairs = {(chain, tx_hash) for _, chain, tx_hash in expected}
    if len(expected) != 40 or len(expected_pairs) != 40:
        raise RuntimeError("frozen Batch A does not contain exactly 40 unique rows")
    if any(not HASH_RE.fullmatch(tx_hash) for _, _, tx_hash in expected):
        raise RuntimeError("frozen Batch A contains a malformed transaction hash")

    attempts_dir = run_dir / "attempts"
    raw_dir = run_dir / "raw"
    attempts = sorted(attempts_dir.glob("*.json"))
    raws = sorted(raw_dir.glob("*.json"))
    if len(attempts) != 40 or len(raws) != 40:
        raise RuntimeError(
            f"expected exactly 40 attempt/raw artifacts, found {len(attempts)}/{len(raws)}"
        )

    expected_by_pair = {(chain, tx_hash): index for index, chain, tx_hash in expected}
    entries: list[dict[str, Any]] = []
    valid_records: list[dict[str, Any]] = []
    for attempt_path in attempts:
        sequence_from_name, chain_from_name, hash_from_name = parse_filename(attempt_path)
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        chain = str(attempt.get("chain", "")).lower()
        tx_hash = str(attempt.get("transaction_hash", "")).lower()
        metadata_issues: list[str] = []
        if sequence_from_name != attempt.get("sequence"):
            metadata_issues.append("attempt sequence does not match filename")
        if chain_from_name != chain or hash_from_name != tx_hash:
            metadata_issues.append("attempt metadata does not match filename")
        if (chain, tx_hash) not in expected_by_pair:
            metadata_issues.append("transaction is outside the frozen Batch A hash set")
        raw_relative = attempt.get("raw_response_path")
        raw_path = run_dir / str(raw_relative)
        if not raw_path.is_file():
            raise RuntimeError(f"attempt references missing raw artifact: {raw_relative}")
        raw_sequence, raw_chain, raw_hash = parse_filename(raw_path)
        if (raw_sequence, raw_chain, raw_hash) != (
            sequence_from_name,
            chain_from_name,
            hash_from_name,
        ):
            metadata_issues.append("raw artifact filename does not match attempt filename")
        raw_text = raw_path.read_text(encoding="utf-8")
        raw_sha = sha256_bytes(raw_text.encode("utf-8"))
        try:
            raw = json.loads(raw_text)
            parse_error = None
        except json.JSONDecodeError as exc:
            raw = None
            parse_error = str(exc)

        base_entry: dict[str, Any] = {
            "sequence": sequence_from_name,
            "chain": chain,
            "transaction_hash": tx_hash,
            "attempt_artifact": str(attempt_path.relative_to(run_dir)).replace("\\", "/"),
            "raw_artifact": str(raw_path.relative_to(run_dir)).replace("\\", "/"),
            "attempt_success": bool(attempt.get("success")),
            "raw_payload_sha256": raw_sha,
        }

        if metadata_issues:
            base_entry.update(
                {
                    "status": "invalid",
                    "classification": "chain_mismatch",
                    "reason": "chain/hash mapping mismatch: " + "; ".join(metadata_issues),
                    "evidence": metadata_issues,
                }
            )
        elif not attempt.get("success"):
            failure_reason = str(attempt.get("failure_cause") or "unspecified mining failure")
            error = raw.get("error") if isinstance(raw, dict) else None
            base_entry.update(
                {
                    "status": "missing_or_failed",
                    "classification": failure_category(failure_reason),
                    "reason": (
                        f"{failure_reason}; no trace payload was returned. "
                        "Preserved separately from invalid trace payloads."
                    ),
                    "rpc_error": error,
                }
            )
        elif parse_error is not None:
            base_entry.update(
                {
                    "status": "invalid",
                    "classification": "truncated",
                    "reason": "truncated: raw success artifact is not valid JSON",
                    "evidence": [parse_error],
                }
            )
        else:
            status, reason, node_count, max_depth, issues = validate_success_payload(
                raw, raw_text
            )
            base_entry.update(
                {
                    "status": status,
                    "classification": "valid_trace_payload" if status == "valid" else "malformed",
                    "reason": reason,
                    "node_count": node_count,
                    "max_depth": max_depth,
                }
            )
            if issues:
                base_entry["evidence"] = issues
            if status == "valid":
                valid_records.append(
                    {
                        "sequence": sequence_from_name,
                        "chain": chain,
                        "transaction_hash": tx_hash,
                        "attempt_artifact": base_entry["attempt_artifact"],
                        "raw_artifact": base_entry["raw_artifact"],
                        "raw_payload_sha256": raw_sha,
                        "node_count": node_count,
                        "max_depth": max_depth,
                        "trace": raw["result"],
                    }
                )
        entries.append(base_entry)

    entries.sort(key=lambda entry: entry["sequence"])
    valid_records.sort(key=lambda record: record["sequence"])
    if {(e["chain"], e["transaction_hash"]) for e in entries} != expected_pairs:
        raise RuntimeError("attempt artifacts do not cover exactly the frozen Batch A hashes")

    counts = Counter(entry["status"] for entry in entries)
    classifications = Counter(entry["classification"] for entry in entries)
    reason_categories = {
        "valid": counts.get("valid", 0),
        "empty": sum(
            1 for entry in entries if entry["status"] == "invalid" and entry["classification"] == "empty"
        ),
        "truncated": sum(
            1
            for entry in entries
            if entry["status"] == "invalid" and entry["classification"] == "truncated"
        ),
        "rpc_limited": classifications.get("rpc_limited", 0),
        "malformed": sum(
            1
            for entry in entries
            if entry["status"] == "invalid" and entry["classification"] == "malformed"
        ),
        "chain_mismatch": classifications.get("chain_mismatch", 0),
        "other": sum(
            1
            for entry in entries
            if entry["status"] == "invalid"
            and entry["classification"] not in {"empty", "truncated", "malformed", "chain_mismatch"}
        ),
    }

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha = sha256_file(manifest_path)
    report = {
        "report_version": "batchA-trace-validity-v1",
        "batch_id": "batchA",
        "status": "COMPLETE",
        "scope": {
            "frozen_hashes": 40,
            "attempt_artifacts": len(attempts),
            "raw_artifacts": len(raws),
            "mining_manifest_processed_rows": manifest.get("processed_rows"),
        },
        "frozen_batch": {
            "artifact_path": str(candidate_path).replace("\\", "/"),
            "canonical_sha256": CANONICAL_BATCH_SHA256,
            "declared_artifact_sha256": declared_batch_sha,
            "file_sha256": sha256_file(candidate_path),
        },
        "mining_manifest": {
            "path": str(manifest_path).replace("\\", "/"),
            "sha256": manifest_sha,
            "status": manifest.get("status"),
            "method": manifest.get("method"),
            "trace_config": manifest.get("trace_config"),
            "raw_file_sha256": manifest.get("raw_file_sha256"),
        },
        "counts": {
            "valid_trace_payloads": counts.get("valid", 0),
            "invalid_trace_payloads": counts.get("invalid", 0),
            "missing_or_failed_traces": counts.get("missing_or_failed", 0),
            "questionable_traces": sum(1 for entry in entries if entry.get("evidence")),
        },
        "reason_counts": reason_categories,
        "entries": entries,
    }

    valid_set = {
        "artifact_type": "batchA_valid_trace_set",
        "artifact_version": "batchA-valid-traces-v1",
        "batch_id": "batchA",
        "selection": {
            "rule": "Include only entries classified valid_trace_payload by the local analyzer.",
            "frozen_hash_count": 40,
            "valid_trace_count": len(valid_records),
            "invalid_trace_payload_count": counts.get("invalid", 0),
            "missing_or_failed_count": counts.get("missing_or_failed", 0),
        },
        "frozen_batch": {
            "artifact_path": str(candidate_path).replace("\\", "/"),
            "canonical_sha256": CANONICAL_BATCH_SHA256,
        },
        "mining_manifest": {
            "path": str(manifest_path).replace("\\", "/"),
            "sha256": manifest_sha,
        },
        "records": valid_records,
    }
    return report, valid_set


def write_markdown(report: dict[str, Any], valid_set_sha256: str) -> str:
    lines = [
        "# Batch A Trace Validity Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Frozen inputs",
        "",
        f"- Canonical Batch A: `{report['frozen_batch']['artifact_path']}`",
        f"- Canonical Batch A SHA-256: `{report['frozen_batch']['canonical_sha256']}`",
        f"- Mining manifest: `{report['mining_manifest']['path']}`",
        f"- Mining manifest SHA-256: `{report['mining_manifest']['sha256']}`",
        "",
        "## Counts",
        "",
        "| Category | Count |",
        "| --- | ---: |",
        f"| Frozen hashes | {report['scope']['frozen_hashes']} |",
        f"| Attempt artifacts | {report['scope']['attempt_artifacts']} |",
        f"| Raw artifacts | {report['scope']['raw_artifacts']} |",
        f"| Valid trace payloads | {report['counts']['valid_trace_payloads']} |",
        f"| Invalid trace payloads | {report['counts']['invalid_trace_payloads']} |",
        f"| Missing/failed traces | {report['counts']['missing_or_failed_traces']} |",
        f"| Questionable traces | {report['counts']['questionable_traces']} |",
        "",
        "## Reason counts",
        "",
        "| Reason | Count |",
        "| --- | ---: |",
    ]
    for reason, count in report["reason_counts"].items():
        lines.append(f"| {reason} | {count} |")
    lines.extend(
        [
            "",
            "## Valid-set freeze",
            "",
            f"- Valid-set artifact SHA-256: `{valid_set_sha256}`",
            "",
            "## Per-artifact decisions",
            "",
            "| Seq | Chain | Transaction hash | Status | Classification | Reason |",
            "| ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in report["entries"]:
        reason = entry["reason"].replace("|", "\\|")
        lines.append(
            f"| {entry['sequence']} | {entry['chain']} | `{entry['transaction_hash']}` | "
            f"{entry['status']} | {entry['classification']} | {reason} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        type=Path,
        default=Path("reports/new_batches/batchA_candidates.json"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path(
            "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0"
        ),
    )
    args = parser.parse_args()
    report, valid_set = analyze(args.candidate, args.run_dir)
    valid_set_path = args.run_dir / "valid_set.json"
    valid_set_bytes = dump_json(valid_set)
    valid_set_path.write_bytes(valid_set_bytes)
    valid_set_sha = sha256_bytes(valid_set_bytes)
    (args.run_dir / "valid_set.sha256").write_text(
        f"{valid_set_sha}  {valid_set_path.name}\n", encoding="utf-8", newline="\n"
    )
    report["valid_set"] = {
        "path": str(valid_set_path).replace("\\", "/"),
        "sha256": valid_set_sha,
        "record_count": len(valid_set["records"]),
    }
    report_path = args.run_dir / "validity_report.json"
    report_path.write_bytes(dump_json(report))
    markdown_path = args.run_dir / "validity_report.md"
    markdown_path.write_text(
        write_markdown(report, valid_set_sha), encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "validity_report": str(report_path),
                "validity_report_markdown": str(markdown_path),
                "valid_set": str(valid_set_path),
                "valid_set_sha256": valid_set_sha,
                "counts": report["counts"],
                "reason_counts": report["reason_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
