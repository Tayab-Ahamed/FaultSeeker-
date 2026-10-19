"""Inventory all nine bounded-run rows against already-present local evidence.

This does not make requests or score localization.  It distinguishes external
dRPC capture failures from pre-existing local cohort artifacts and records
whether those artifacts contain a usable call tree and independently bound
function-level targets.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "reports/external_runs/phase2/20261017T011500Z/drpc/manifest.json"
CURRENT_MANIFEST = ROOT / "benchmark/cohort_manifest.json"
CURRENT_GT = ROOT / "benchmark/ground_truth"
LOCAL_RPC = ROOT / "reports/cohort_rebuild_v2/rpc"
LOCAL_TRACES = ROOT / "reports/cohort_rebuild_v2/traces"
INTEGRATED_TRACES = ROOT / "reports/cohort_rebuild_v2/chain_trace_probe/integrated"
OUTPUT_JSON = ROOT / "reports/reconciliation/recovered_trace_inventory_20261019.json"
OUTPUT_MD = ROOT / "reports/reconciliation/RECOVERED_TRACE_INVENTORY_20261019.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _gt_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False}
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    location = raw.get("location") or {}
    return {
        "present": True,
        "sha256": _sha256(path),
        "schema": raw.get("schema"),
        "independent_human_review": raw.get("independent_human_review"),
        "localization_status": raw.get("localization_status"),
        "location_keys": len(location) if isinstance(location, dict) else 0,
        "source_supported_functions": len(raw.get("source_supported_functions") or []),
    }


def _trace_info(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        raw = json.load(handle)
    call = ((raw.get("raw_trace") or {}).get("call") or {}) if isinstance(raw, dict) else {}
    return {
        "present": True,
        "sha256": _sha256(path),
        "capture_version": raw.get("capture_version"),
        "provider_capture": raw.get("provider_capture"),
        "has_call_tree": isinstance(call, dict) and bool(call),
        "storage_trace_complete": raw.get("storage_trace_complete"),
        "historical_code_present": bool(raw.get("historical_code")),
    }


def _find_trace(chain: str, txn: str) -> tuple[Path | None, str]:
    normal = LOCAL_TRACES / chain / f"{txn}.json.gz"
    if normal.is_file():
        return normal, "cohort_rebuild_v2_trace"
    integrated = INTEGRATED_TRACES / f"{chain}-{txn}.json.gz"
    if integrated.is_file():
        return integrated, "integrated_chain_trace_probe"
    return None, "none"


def _failure_classification(attempts: list[dict[str, Any]]) -> list[str]:
    causes: set[str] = set()
    for attempt in attempts:
        for failure in attempt.get("failure_causes") or []:
            if failure.get("status") == 429 or failure.get("rate_limited"):
                causes.add("provider_rate_limit_429")
            if failure.get("rpc_code") == -32000:
                causes.add("provider_trace_method_error_-32000")
            if failure.get("method") == "eth_getTransactionByHash" and failure.get("status") == 200:
                causes.add("transaction_lookup_missing_or_null")
            if failure.get("cause") == "wrong_or_missing_chain":
                causes.add("chain_identity_not_observed")
    return sorted(causes)


def run() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    current_manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
    current_records = {
        f"{_norm(item.get('chain'))}:{_norm(item.get('txn_hash'))}": item
        for item in current_manifest.get("records", [])
    }
    rows: list[dict[str, Any]] = []
    for chain, group in sorted((manifest.get("chains") or {}).items()):
        for attempt in group.get("attempts") or []:
            txn = _norm(attempt.get("transaction_hash"))
            if attempt.get("status") == "CAPTURED":
                external_raw = ROOT / "reports/external_runs/phase2/20261017T011500Z/drpc/raw" / chain / f"{txn}.attempt1.json"
            else:
                external_raw = None
            rpc_path = LOCAL_RPC / chain / f"{txn}.json"
            trace_path, trace_kind = _find_trace(chain, txn)
            gt_path = CURRENT_GT / f"{txn}.json"
            current_record = current_records.get(f"{chain}:{txn}", {})
            local_gt = _gt_status(gt_path)
            if attempt.get("status") == "CAPTURED" and trace_path and local_gt.get("location_keys", 0) == 0:
                recovery_class = "captured_trace_recovered_but_function_gt_unavailable"
            elif attempt.get("status") != "CAPTURED" and trace_path and local_gt.get("location_keys", 0) == 0:
                recovery_class = "external_capture_failed_local_trace_recovered_but_function_gt_unavailable"
            elif attempt.get("status") != "CAPTURED" and not trace_path:
                recovery_class = "externally_blocked_no_local_call_tree"
            else:
                recovery_class = "captured_with_local_trace"
            rows.append({
                "stable_id": f"{chain}:{txn}",
                "chain": chain,
                "transaction_hash": txn,
                "external_status": attempt.get("status"),
                "external_raw_present": bool(external_raw and external_raw.is_file()),
                "external_raw_sha256": _sha256(external_raw) if external_raw and external_raw.is_file() else None,
                "external_failure_causes": _failure_classification(group.get("attempts") or []) if attempt.get("status") != "CAPTURED" else [],
                "local_rpc": {
                    "present": rpc_path.is_file(),
                    "path": rpc_path.relative_to(ROOT).as_posix() if rpc_path.is_file() else None,
                    "sha256": _sha256(rpc_path) if rpc_path.is_file() else None,
                },
                "local_trace_kind": trace_kind,
                "local_trace": _trace_info(trace_path) if trace_path else {"present": False},
                "current_ground_truth": local_gt,
                "current_manifest_membership": bool(current_record),
                "current_manifest_membership_value": current_record.get("membership"),
                "recovery_class": recovery_class,
                "safe_next_action": (
                    "Use existing local call tree only for exploratory evidence; acquire independently source-bound function targets before localization scoring."
                    if trace_path and local_gt.get("location_keys", 0) == 0
                    else "No safe local localization action; provider trace capability or independently bound targets are missing."
                ),
            })
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["recovery_class"]] = counts.get(row["recovery_class"], 0) + 1
    result = {
        "schema_version": 1,
        "scope": "Previously captured dRPC rows cross-checked against already-present cohort RPC, trace, and ground-truth artifacts; no new retrievals.",
        "source_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": _sha256(MANIFEST),
        "current_cohort_manifest_sha256": _sha256(CURRENT_MANIFEST),
        "rows": rows,
        "recovery_class_counts": counts,
        "conclusion": "Local call trees exist for all nine rows, but current-cohort ground truth provides no independently source-bound function locations for the five non-original rows and three failed external rows. The BSC failed attempt has no local call-tree artifact; its dRPC retries are blocked by provider rate limits.",
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Recovered trace inventory",
        "",
        "Cross-check of the nine bounded-run rows against already-present local evidence. No new requests or scores were run.",
        "",
        "| Recovery class | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines += ["", "| Stable ID | External | Local trace | Function-level GT | Recovery class |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append(
            f"| `{row['stable_id']}` | {row['external_status']} | {row['local_trace_kind']} | "
            f"{row['current_ground_truth'].get('location_keys', 0)} location keys | `{row['recovery_class']}` |"
        )
    lines += ["", result["conclusion"], "", f"Machine-readable artifact: `{OUTPUT_JSON.relative_to(ROOT).as_posix()}`."]
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
