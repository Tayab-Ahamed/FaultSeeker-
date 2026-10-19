"""Create a row-level reconciliation of the original and newer cohorts.

This script is deliberately read-only with respect to source evidence.  It
uses stable ``chain:transaction_hash`` identifiers and reports the function
identities found in each ground-truth corpus without merging or correcting
labels.  The output is suitable for auditing denominators, not for training.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_REPOSITORY = "https://github.com/kairanskrr/FaultSeeker"
UPSTREAM_COMMIT = "72753bd833554449efa8499f0d1775a97fb5c696"
UPSTREAM_MAIN_TREE = "72753bd833554449efa8499f0d1775a97fb5c696"

ORIGINAL_CSV = ROOT / "benchmark/original_faultseeker/benchmark_classification.csv"
ROOT_CSV = ROOT / "benchmark/benchmark_classification.csv"
ORIGINAL_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
CURRENT_GT = ROOT / "benchmark/ground_truth"
CURRENT_MANIFEST = ROOT / "benchmark/cohort_manifest.json"
V4_MANIFEST = ROOT / "benchmark/versions/cohort_v4_20261016/cohort_manifest.json"
CURRENT_LOCALIZATION_REPORT = ROOT / (
    "reports/reproducibility/localization_candidate_coverage_selector_normalization/report.json"
)
PROVIDER_MANIFEST = ROOT / (
    "reports/original_benchmark/provider-pinned/"
    "original-v1-pinned-sequential-20261017/manifest.json"
)
OUTPUT_JSON = ROOT / "reports/reconciliation/original_benchmark_reconciliation.json"
OUTPUT_CSV = ROOT / "reports/reconciliation/row_level_overlap.csv"
RECOMPUTED_JSON = ROOT / "reports/reconciliation/original_evaluation_recomputed.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _chain(value: Any) -> str:
    chain = _norm(value)
    return {
        "ethereum": "eth",
        "mainnet": "eth",
        "bnbchain": "bsc",
        "binance": "bsc",
        "binancesmartchain": "bsc",
    }.get(chain, chain)


def _stable_id(chain: Any, txn_hash: Any) -> str:
    return f"{_chain(chain)}:{_norm(txn_hash)}"


def _read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return {_stable_id(row.get("chain"), row.get("txn_hash")): row for row in rows}


def _parse_location_entry(entry: Any) -> tuple[str, str, bool] | None:
    parts = str(entry or "").split("#")
    if len(parts) < 3:
        return None
    address = _norm(parts[0])
    member = str(parts[-1]).strip()
    if not address or not member:
        return None
    if ":" in member and member.split(":", 1)[0].strip().isdigit():
        return address, member.split(":", 1)[0].strip(), True
    return address, member.lower().split("(", 1)[0], False


def _ground_truth(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    hashes = raw.get("transaction_hash") or []
    if isinstance(hashes, str):
        hashes = [hashes]
    txn_hash = _norm(hashes[0] if hashes else path.stem)
    chain = _chain(raw.get("platform") or raw.get("chain"))
    functions: set[str] = set()
    lines: set[str] = set()
    locations = raw.get("location") or {}
    if isinstance(locations, dict):
        entries: list[Any] = []
        for key, values in locations.items():
            entries.append(key)
            entries.extend(values or [])
        for entry in entries:
            parsed = _parse_location_entry(entry)
            if not parsed:
                continue
            address, member, is_line = parsed
            (lines if is_line else functions).add(f"{address}#{member}")
    return {
        "stable_id": _stable_id(chain, txn_hash),
        "txn_hash": txn_hash,
        "chain": chain,
        "case_id": path.stem,
        "name": str(raw.get("name") or ""),
        "function_identities": sorted(functions),
        "line_identities": sorted(lines),
        "sha256": _sha256(path),
    }


def _ground_truth_dir(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for file in sorted(path.glob("*.json")):
        row = _ground_truth(file)
        row["source_files"] = [file.name]
        if row["stable_id"] not in result:
            result[row["stable_id"]] = row
            continue
        # Preserve duplicate-file evidence under the stable identifier rather
        # than silently treating a filename mismatch as a new transaction.
        previous = result[row["stable_id"]]
        previous["source_files"].append(file.name)
        previous["function_identities"] = sorted(set(previous["function_identities"]) | set(row["function_identities"]))
        previous["line_identities"] = sorted(set(previous["line_identities"]) | set(row["line_identities"]))
    return result


def _manifest_records_from(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = {}
    for item in raw.get("records", []):
        key = _stable_id(item.get("chain"), item.get("txn_hash"))
        records[key] = {
            "stable_id": key,
            "txn_hash": _norm(item.get("txn_hash")),
            "chain": _chain(item.get("chain")),
            "incident_id": item.get("incident_id"),
            "membership": item.get("membership"),
            "vulnerability_class": item.get("vulnerability_class"),
            "complexity_class": item.get("complexity_class"),
            "is_exploit": item.get("is_exploit"),
            "reentrancy_label": item.get("reentrancy_label"),
        }
    return raw, records


def _manifest_records() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    return _manifest_records_from(CURRENT_MANIFEST)


def _provider_status() -> tuple[dict[str, str], int]:
    if not PROVIDER_MANIFEST.is_file():
        return {}, 0
    raw = json.loads(PROVIDER_MANIFEST.read_text(encoding="utf-8"))
    status = {}
    for row in raw.get("rows", []):
        status[_norm(row.get("txn_hash"))] = str(row.get("status") or "")
    return status, len(raw.get("rows", []))


def _recompute_provider_metrics() -> dict[str, Any]:
    """Re-aggregate retained per-example scores without reading manifest totals."""
    if not PROVIDER_MANIFEST.is_file():
        return {"status": "BLOCKED", "reason": "provider-pinned manifest is missing"}
    manifest = json.loads(PROVIDER_MANIFEST.read_text(encoding="utf-8"))
    raw_dir = PROVIDER_MANIFEST.parent / "raw"
    rows = manifest.get("rows", [])

    def aggregate(selected: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(selected)
        ok = sum(row.get("status") == "ok" for row in selected)
        return {
            "n_total": total,
            "n_ok": ok,
            "n_failed": total - ok,
            "recall_at_1": sum(bool(row.get("score", {}).get("recall_at_1")) for row in selected) / total if total else 0.0,
            "recall_at_3": sum(bool(row.get("score", {}).get("recall_at_3")) for row in selected) / total if total else 0.0,
            "recall_at_5": sum(bool(row.get("score", {}).get("recall_at_5")) for row in selected) / total if total else 0.0,
            "replay_mismatch": sum(bool(row.get("replay_mismatch")) for row in selected),
        }

    result = {
        "status": "RECOMPUTED_FROM_RETAINED_PER_EXAMPLE_ROWS",
        "source_manifest": str(PROVIDER_MANIFEST.relative_to(ROOT)),
        "source_raw_directory": str(raw_dir.relative_to(ROOT)),
        "raw_files_present": len(list(raw_dir.glob("*.json"))),
        "manifest_rows": len(rows),
        "all_115_denominator": aggregate(rows),
        "valid_trace_subset": aggregate([row for row in rows if row.get("status") == "ok"]),
        "scoring_boundary": (
            "This independently re-aggregates retained row-level score booleans and replay flags. "
            "It does not claim that the upstream paper's scorer was reproduced; the retained provider run's "
            "score construction uses the current harness and registers ground-truth function names for selector lookup."
        ),
    }
    RECOMPUTED_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _row_overlap() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root_csv = _read_csv(ROOT_CSV)
    original_csv = _read_csv(ORIGINAL_CSV)
    original_gt = _ground_truth_dir(ORIGINAL_GT)
    current_gt = _ground_truth_dir(CURRENT_GT)
    manifest, accepted = _manifest_records()
    v4_manifest, v4_accepted = _manifest_records_from(V4_MANIFEST)
    provider_status, provider_row_count = _provider_status()
    localization_report = json.loads(CURRENT_LOCALIZATION_REPORT.read_text(encoding="utf-8"))

    keys = sorted(set(root_csv) | set(original_csv) | set(original_gt) | set(accepted))
    rows: list[dict[str, Any]] = []
    for key in keys:
        source_row = root_csv.get(key) or original_csv.get(key) or {}
        original = original_gt.get(key, {})
        current = current_gt.get(key, {})
        cohort = accepted.get(key, {})
        txn_hash = _norm(source_row.get("txn_hash") or original.get("txn_hash") or cohort.get("txn_hash"))
        functions = original.get("function_identities", [])
        current_functions = current.get("function_identities", [])
        rows.append({
            "stable_id": key,
            "chain": _chain(source_row.get("chain") or original.get("chain") or cohort.get("chain")),
            "txn_hash": txn_hash,
            "in_root_classification": key in root_csv,
            "in_imported_original_classification": key in original_csv,
            "classification_rows_equal": bool(key in root_csv and key in original_csv and root_csv[key] == original_csv[key]),
            "in_original_ground_truth": key in original_gt,
            "original_gt_source_files": original.get("source_files", []),
            "original_gt_duplicate_file_count": len(original.get("source_files", [])),
            "original_gt_function_count": len(functions),
            "original_gt_line_count": len(original.get("line_identities", [])),
            "original_gt_function_identities": functions,
            "in_faultseekerpp_accepted_manifest": key in accepted,
            "faultseekerpp_membership": cohort.get("membership"),
            "faultseekerpp_vulnerability_class": cohort.get("vulnerability_class"),
            "faultseekerpp_gt_function_count": len(current_functions),
            "faultseekerpp_gt_function_identities": current_functions,
            "current_114_localization_eligible": bool(functions),
            "provider_pinned_status": provider_status.get(txn_hash),
            "overlap_class": (
                "original_and_faultseekerpp" if key in original_gt and key in accepted
                else "original_only" if key in original_gt
                else "faultseekerpp_only"
            ),
        })

    summary = {
        "original_classification_rows": len(original_csv),
        "root_classification_rows": len(root_csv),
        "classification_sets_equal": set(root_csv) == set(original_csv),
        "classification_rows_equal": root_csv == original_csv,
        "original_ground_truth_files": len(list(ORIGINAL_GT.glob("*.json"))),
        "original_ground_truth_unique_stable_ids": len(original_gt),
        "original_ground_truth_function_files": sum(
            bool(_ground_truth(file)["function_identities"])
            for file in ORIGINAL_GT.glob("*.json")
        ),
        "original_ground_truth_duplicate_stable_ids": {
            key: row["source_files"] for key, row in original_gt.items() if len(row.get("source_files", [])) > 1
        },
        "current_faultseekerpp_ground_truth_files": len(list(CURRENT_GT.glob("*.json"))),
        "current_faultseekerpp_ground_truth_unique_stable_ids": len(current_gt),
        "faultseekerpp_accepted_manifest_rows": len(accepted),
        "faultseekerpp_target_count": manifest.get("target_count"),
        "faultseekerpp_remaining_to_target": manifest.get("remaining_to_target"),
        "original_faultseekerpp_transaction_overlap": len(set(original_gt) & set(accepted)),
        "faultseekerpp_v4_manifest": {
            "accepted_count": v4_manifest.get("accepted_count", len(v4_accepted)),
            "target_count": v4_manifest.get("target_count"),
            "remaining_to_target": v4_manifest.get("remaining_to_target"),
            "not_independent_human_review": v4_manifest.get("not_independent_human_review"),
            "accepted_unique_stable_ids": len(v4_accepted),
            "original_transaction_overlap": len(set(original_gt) & set(v4_accepted)),
        },
        "current_114_localization_denominator": localization_report.get("eligible_rows"),
        "current_114_localization_report_scope": localization_report.get("evidence_scope"),
        "provider_pinned_rows": provider_row_count,
        "provider_pinned_unique_transaction_ids": len(provider_status),
        "provider_pinned_ok_rows": sum(value == "ok" for value in provider_status.values()),
        "row_union": len(rows),
    }
    return rows, summary


def run() -> dict[str, Any]:
    rows, summary = _row_overlap()
    recomputed = _recompute_provider_metrics()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, list) else value for key, value in row.items()})

    result = {
        "schema_version": 1,
        "source": {
            "repository": UPSTREAM_REPOSITORY,
            "commit": UPSTREAM_COMMIT,
            "main_tree": UPSTREAM_MAIN_TREE,
            "local_import_attribution": "benchmark/original_faultseeker/ATTRIBUTION.md",
        },
        "inputs": {
            "root_classification": str(ROOT_CSV.relative_to(ROOT)),
            "imported_original_classification": str(ORIGINAL_CSV.relative_to(ROOT)),
            "imported_original_ground_truth": str(ORIGINAL_GT.relative_to(ROOT)),
            "faultseekerpp_ground_truth": str(CURRENT_GT.relative_to(ROOT)),
            "faultseekerpp_manifest": str(CURRENT_MANIFEST.relative_to(ROOT)),
            "faultseekerpp_v4_manifest": str(V4_MANIFEST.relative_to(ROOT)),
            "current_localization_report": str(CURRENT_LOCALIZATION_REPORT.relative_to(ROOT)),
        },
        "summary": summary,
        "original_evaluation_recomputed": recomputed,
        "denominator_definitions": {
            "original_115": "115 original benchmark classification rows and 115 imported original function-ground-truth JSON files; transaction-level attack cases, not a benign-control detector cohort.",
            "current_114": "114 unique stable transaction identifiers used by the current localization report. The imported original ground truth has 115 files, but two filenames carry the same transaction hash; all 115 files contain function identities.",
            "faultseekerpp_246": "A target size in the current FaultSeeker++ cohort specification. The current root manifest admits 14 rows and explicitly leaves 232 unresolved; it is not evidence of 246 accepted attacks.",
            "faultseekerpp_v4_246": "The versioned v4 manifest also targets 246 records, accepts 22 unique stable IDs, leaves 224 unresolved, and is explicitly not independent human review.",
            "faultseekerpp_current_ground_truth": "14 accepted root-cohort ground-truth files, represented by the accepted manifest; this set is not the 246 target and is not independent human review.",
        },
        "rows_path": str(OUTPUT_CSV.relative_to(ROOT)),
        "original_evaluation_recomputed_path": str(RECOMPUTED_JSON.relative_to(ROOT)),
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
