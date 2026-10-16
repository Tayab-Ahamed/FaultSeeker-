"""Build offline evidence artifacts for the 18-claim honesty review.

This script reads the frozen 231-row CSV and existing saved result files only.
It does not replay transactions, call RPCs, call models, or open held-out data.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT / (
    "reports/canonical_history/snapshots/"
    "fca6b998fa0a01f3832be6a0f1aa1d768306da8f/"
    "benchmark/benchmark_classification_fixed.csv"
)
OUT = ROOT / "reports/claim_evidence"
URL_RE = re.compile(r"https?://[^\s\"'\[\]<>]+")
HASH_RE = re.compile(r"0x[0-9a-fA-F]{64}\Z")


FREE_ENDPOINTS = [
    ("eth", "https://eth.llamarpc.com", False, "Configured Ethereum callTracer response exists in reports/claim_closure/rpc_capabilities.json; that observation used a configured endpoint, not a verified built-in free fallback."),
    ("bsc", "https://bsc-dataseed1.binance.org", False, "rpc_provider.py comments say public BSC nodes do not support debug_traceTransaction; no free trace success is recorded."),
    ("polygon", "https://polygon-rpc.com", False, "No free-endpoint trace result is recorded in the repository."),
    ("arbitrum", "https://arb1.arbitrum.io/rpc", False, "No free-endpoint trace result is recorded in the repository."),
    ("optimism", "https://mainnet.optimism.io", False, "No free-endpoint trace result is recorded in the repository."),
    ("avalanche", "https://api.avax.network/ext/bc/C/rpc", False, "No free-endpoint trace result is recorded in the repository."),
    ("base", "https://mainnet.base.org", False, "The recorded demo attempt failed with HTTP 403/auth failure and no trace support."),
    ("fantom", "https://rpc.ftm.tools", False, "No free-endpoint trace result is recorded in the repository."),
    ("gnosis", "https://rpc.gnosischain.com", False, "No free-endpoint trace result is recorded in the repository."),
    ("zksync", "https://mainnet.era.zksync.io", False, "No free-endpoint trace result is recorded in the repository."),
]


def read_rows():
    with COHORT.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name, fieldnames, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build(rows):
    url_gaps = []
    reentrancy = []
    labels = {}
    for row_number, row in enumerate(rows, 2):
        urls = URL_RE.findall(row.get("analysis", ""))
        tx_hash = row.get("txn_hash", "").strip()
        hash_valid = bool(HASH_RE.fullmatch(tx_hash))
        if not urls or not hash_valid:
            url_gaps.append({
                "row_number": row_number,
                "chain": row.get("chain", ""),
                "txn_hash": tx_hash,
                "missing_source_url": str(not bool(urls)).lower(),
                "missing_tx_hash": str(not hash_valid).lower(),
                "vuln_type": row.get("vuln_type", ""),
            })
        if "reentran" in row.get("vuln_type", "").lower():
            reentrancy.append({
                "row_number": row_number,
                "chain": row.get("chain", ""),
                "txn_hash": tx_hash,
                "vuln_type": row.get("vuln_type", ""),
                "swc_registry_classification": row.get("swc_registry_classification", ""),
                "source_url_count": len(urls),
                "hash_valid": str(hash_valid).lower(),
            })
        label = row.get("vuln_type", "").strip()
        if label:
            item = labels.setdefault(label, {"rows": [], "swc": set(), "dasp": set()})
            item["rows"].append(row_number)
            if row.get("swc_registry_classification", "").strip():
                item["swc"].add(row["swc_registry_classification"].strip())
            if row.get("dasp_classification", "").strip():
                item["dasp"].add(row["dasp_classification"].strip())

    write_csv(
        "cohort_provenance_gaps.csv",
        ["row_number", "chain", "txn_hash", "missing_source_url", "missing_tx_hash", "vuln_type"],
        url_gaps,
    )
    write_csv(
        "reentrancy_rows.csv",
        ["row_number", "chain", "txn_hash", "vuln_type", "swc_registry_classification", "source_url_count", "hash_valid"],
        reentrancy,
    )

    mapping_rows = []
    for label in sorted(labels):
        item = labels[label]
        mapping_rows.append({
            "vuln_type": label,
            "row_count": len(item["rows"]),
            "csv_swc_registry_classification": "; ".join(sorted(item["swc"])),
            "csv_dasp_classification": "; ".join(sorted(item["dasp"])),
            "mapping_status": "MAPPED_FROM_EXISTING_CSV" if item["swc"] else "UNMAPPED_IN_EXISTING_CSV",
            "row_numbers": ";".join(map(str, item["rows"])),
        })
    write_csv(
        "vulnerability_swc_mapping.csv",
        ["vuln_type", "row_count", "csv_swc_registry_classification", "csv_dasp_classification", "mapping_status", "row_numbers"],
        mapping_rows,
    )

    chain_counts = Counter(row.get("chain", "") for row in rows)
    write_csv(
        "chain_shares.csv",
        ["chain", "rows", "share_percent", "denominator"],
        [
            {"chain": chain, "rows": count, "share_percent": round(100 * count / len(rows), 4), "denominator": len(rows)}
            for chain, count in sorted(chain_counts.items())
        ],
    )
    class_counts = Counter(row.get("class", "") for row in rows)
    write_csv(
        "class_proportions.csv",
        ["class", "rows", "share_percent", "denominator"],
        [
            {"class": cls, "rows": count, "share_percent": round(100 * count / len(rows), 4), "denominator": len(rows)}
            for cls, count in sorted(class_counts.items())
        ],
    )

    write_csv(
        "chain_capability_matrix.csv",
        ["chain", "free_endpoint", "free_endpoint_trace_support_observed", "evidence_status", "notes"],
        [
            {
                "chain": chain,
                "free_endpoint": endpoint,
                "free_endpoint_trace_support_observed": "YES" if observed else "NO",
                "evidence_status": "NOT_ESTABLISHED_AS_FREE_ENDPOINT" if chain == "eth" else "NOT_OBSERVED",
                "notes": notes,
            }
            for chain, endpoint, observed, notes in FREE_ENDPOINTS
        ],
    )

    baseline_path = ROOT / "reports/honest_results/baseline_comparison.csv"
    with baseline_path.open(encoding="utf-8-sig", newline="") as handle:
        baseline = list(csv.DictReader(handle))
    write_csv(
        "table_v_saved_results.csv",
        ["system", "n", "tp", "fp", "tn", "fn", "precision", "recall", "f1", "false_positive_rate", "status"],
        [dict((key, row.get(key, "")) for key in ["system", "n", "tp", "fp", "tn", "fn", "precision", "recall", "f1", "false_positive_rate"]) | {"status": "SAVED_FEATURE_HARNESS_AGGREGATE"} for row in baseline],
    )

    localization = json.loads((ROOT / "reports/honest_results/localization_metrics.json").read_text())
    (OUT / "localization_summary.json").write_text(json.dumps(localization["metrics"], indent=2) + "\n", encoding="utf-8")

    summary = {
        "source_csv": str(COHORT.relative_to(ROOT)),
        "rows": len(rows),
        "chains": len(chain_counts),
        "ethereum_rows": chain_counts.get("eth", 0),
        "ethereum_share_percent": round(100 * chain_counts.get("eth", 0) / len(rows), 4),
        "class_counts": dict(sorted(class_counts.items())),
        "reentrancy_label_string_count": len(reentrancy),
        "distinct_vulnerability_label_strings": len(labels),
        "rows_missing_source_or_hash": len(url_gaps),
        "labels_with_existing_swc_mapping": sum(bool(item["swc"]) for item in labels.values()),
        "labels_without_existing_swc_mapping": sum(not bool(item["swc"]) for item in labels.values()),
        "baseline_rows_saved": len(baseline),
        "localization_metrics": localization["metrics"],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    summary = build(read_rows())
    print(json.dumps(summary, indent=2))
