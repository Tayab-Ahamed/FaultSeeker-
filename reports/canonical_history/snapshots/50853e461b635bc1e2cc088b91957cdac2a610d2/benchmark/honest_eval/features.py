"""Dataset loading and feature-coverage auditing for the honest harness.

Critically, this module also detects the *feature-availability* leak: the
exploit CSV carries measured trace statistics (functioncall_count,
address_count, max_depth, gas_cost) while the HuggingFace benign CSV carries
none of them. Any classifier evaluated across both files can separate the
classes purely by noticing which columns are populated, which would be a second
form of leakage independent of reading ``label``. The harness refuses to emit
comparison tables until trace coverage is balanced.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPLOIT_CSV = os.path.join(ROOT, "benchmark", "benchmark_classification_fixed.csv")
BENIGN_CSV = os.path.join(
    ROOT, "benchmark", "imported", "hf_ethereum_benign_transactions.csv"
)
BENIGN_TRACE_CSV = os.path.join(ROOT, "benchmark", "imported", "benign_traces.csv")

# Trace-derived numeric features. These are the only inputs a scorer may use.
TRACE_FEATURES = (
    "functioncall_count",
    "address_count",
    "max_depth",
    "gas_cost",
)


@dataclass
class EvalRow:
    """A single evaluation transaction."""

    txn_hash: str
    chain: str
    label: int
    features: Dict[str, float] = field(default_factory=dict)
    provenance: str = ""

    @property
    def has_trace_features(self) -> bool:
        return all(
            self.features.get(name) is not None for name in TRACE_FEATURES
        ) and any(float(self.features.get(name) or 0) > 0 for name in TRACE_FEATURES)


def _clean_key(key: Optional[str]) -> str:
    return str(key or "").strip().lstrip("\ufeff").strip('"').strip().lower()


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _read_csv(path: str) -> List[Dict[str, Any]]:
    """Read a CSV, tolerating the UTF-8 BOM present in the benchmark files."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = []
        for raw in csv.DictReader(handle):
            rows.append({_clean_key(k): v for k, v in raw.items()})
        return rows


def load_exploit_rows(path: str = EXPLOIT_CSV) -> List[EvalRow]:
    rows = []
    for raw in _read_csv(path):
        txn = str(raw.get("txn_hash") or "").strip().strip('"')
        if not txn:
            continue
        features = {name: _to_float(raw.get(name)) for name in TRACE_FEATURES}
        rows.append(
            EvalRow(
                txn_hash=txn.lower(),
                chain=str(raw.get("chain") or "").strip().strip('"').lower(),
                label=1,
                features=features,
                provenance="benchmark_classification_fixed.csv",
            )
        )
    return rows


def load_benign_rows(
    path: str = BENIGN_CSV, trace_path: str = BENIGN_TRACE_CSV, limit: Optional[int] = None, only_traces: bool = True
) -> List[EvalRow]:
    """Load benign rows, joining collected traces when available.

    ``benign_traces.csv`` is produced by ``benchmark/collect_benign_traces.py``
    and is absent until the user runs that collector against an archive RPC.
    """
    traces: Dict[str, Dict[str, Optional[float]]] = {}
    for raw in _read_csv(trace_path):
        txn = str(raw.get("txn_hash") or "").strip().lower()
        status = str(raw.get("collection_status") or "").strip().lower()
        if txn and status == "ok":
            traces[txn] = {name: _to_float(raw.get(name)) for name in TRACE_FEATURES}

    rows = []
    for raw in _read_csv(path):
        txn = str(raw.get("txn_hash") or "").strip().lower()
        if not txn:
            continue
        if only_traces and traces and txn not in traces:
            continue
        features = traces.get(txn, {name: None for name in TRACE_FEATURES})
        rows.append(
            EvalRow(
                txn_hash=txn,
                chain=str(raw.get("chain") or "").strip().lower(),
                label=0,
                features=dict(features),
                provenance="hf_ethereum_benign_transactions.csv",
            )
        )
        if limit is not None and len(rows) >= limit:
            break
    return rows


def audit_feature_coverage(rows: Iterable[EvalRow]) -> Dict[str, Any]:
    """Report per-class trace-feature coverage and whether comparison is valid."""
    rows = list(rows)
    summary: Dict[str, Any] = {}
    for label, name in ((1, "exploit"), (0, "benign")):
        subset = [r for r in rows if r.label == label]
        with_trace = [r for r in subset if r.has_trace_features]
        summary[name] = {
            "rows": len(subset),
            "rows_with_trace_features": len(with_trace),
            "coverage": round(len(with_trace) / len(subset), 4) if subset else 0.0,
        }

    exploit_cov = summary["exploit"]["coverage"]
    benign_cov = summary["benign"]["coverage"]
    gap = abs(exploit_cov - benign_cov)
    comparable = bool(
        summary["exploit"]["rows_with_trace_features"] > 0
        and summary["benign"]["rows_with_trace_features"] > 0
        and gap <= 0.10
    )

    summary["coverage_gap"] = round(gap, 4)
    summary["comparable"] = comparable
    if not comparable:
        summary["blocker"] = (
            "Trace-feature coverage is unbalanced across classes "
            f"(exploit={exploit_cov:.2f}, benign={benign_cov:.2f}). A classifier "
            "evaluated on this split could separate classes by feature "
            "availability alone, so cross-class comparison tables are invalid. "
            "Run benchmark/collect_benign_traces.py to populate benign traces."
        )
    return summary


def comparable_subset(rows: Iterable[EvalRow]) -> List[EvalRow]:
    """Restrict to rows that actually carry trace features."""
    return [r for r in rows if r.has_trace_features]


def feature_dict(row: EvalRow) -> Dict[str, Any]:
    """Scorer-visible payload. Deliberately excludes every label-bearing field."""
    payload: Dict[str, Any] = {"txn_hash": row.txn_hash, "chain": row.chain}
    for name in TRACE_FEATURES:
        payload[name] = row.features.get(name)
    return payload
