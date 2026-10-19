"""Compare saved localization with generic recovered call-trace candidates.

This experiment is deliberately restricted to the four rows that have both
the newly audited dRPC callTracer evidence and imported original function
ground truth.  It does not read Batch B/C, use the five current-cohort rows
whose localization status is unavailable, or make network requests.

The trace-aware treatment extracts only observed call addresses and raw
calldata selectors.  It never reads target labels while constructing or
ordering candidates.  A fixed, preregistered trace-evidence weight is used;
there is no parameter fitting on these four rows.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval import localization
from benchmark.honest_eval.localization import load_ground_truth, rank_of_first_hit
from faultseeker.function_analysis.candidate_generation import generate_saved_candidates
from scripts.research.evaluate_candidate_generation_cv import prepare_row, rank_prepared


AUDIT = ROOT / "reports/reconciliation/recovered_trace_audit.json"
PROVIDER_RAW = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
TRACE_RAW = ROOT / "reports/external_runs/phase2/20261017T011500Z/drpc/raw"
ORIGINAL_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
OUTPUT_JSON = ROOT / "reports/research_results/recovered_trace_localization_20261019.json"
OUTPUT_MD = ROOT / "reports/research_results/RECOVERED_TRACE_LOCALIZATION_20261019.md"

# Fixed before evaluating the rows.  The treatment rewards observed trace
# evidence, while preserving a deterministic encounter tie-break.  Other
# feature weights remain zero to keep this a minimal adapter experiment.
TRACE_CONFIG = {
    "trace_evidence": 1.0,
    "count": 0.0,
    "depth": 0.0,
    "proxy": 0.0,
    "saved_rank": 0.0,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _iter_calls(node: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(node, dict):
        return
    yield node
    for child in node.get("calls") or []:
        yield from _iter_calls(child)


def _trace_result(raw: dict[str, Any]) -> dict[str, Any]:
    for request in raw.get("requests") or []:
        if request.get("method") != "debug_traceTransaction":
            continue
        body = (request.get("response") or {}).get("body") or {}
        result = body.get("result") if isinstance(body, dict) else None
        if isinstance(result, dict):
            return result
    raise ValueError("captured artifact has no callTracer result")


def trace_text_from_calltree(trace: dict[str, Any]) -> str:
    """Render observed calls as parser-compatible address::selector lines."""
    lines: list[str] = []

    def visit(node: dict[str, Any], depth: int) -> None:
        address = _norm(node.get("to"))
        data = _norm(node.get("input"))
        selector = data[:10] if data.startswith("0x") and len(data) >= 10 else "fallback"
        call_type = _norm(node.get("type") or node.get("callType") or "call")
        if address:
            prefix = "    " * depth + ("└─ " if depth else "")
            lines.append(f"{prefix}{address}::{selector}() [{call_type}]")
        for child in node.get("calls") or []:
            visit(child, depth + 1)

    visit(trace, 0)
    return "\n".join(lines)


def _load_targets(txns: set[str]) -> dict[str, Any]:
    """Load original targets while disabling GT-derived selector registration."""
    localization._SELECTOR_TO_NAMES.clear()
    localization._load_api_selector_cache()
    original_register = localization._register_fn_names
    localization._register_fn_names = lambda names: None
    try:
        targets = load_ground_truth(str(ORIGINAL_GT))
    finally:
        localization._register_fn_names = original_register
    return {target.txn_hash.lower(): target for target in targets if target.txn_hash.lower() in txns}


def _metrics(rows: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    def ranks(key: str) -> list[int | None]:
        return [row[prefix][key] for row in rows]

    result: dict[str, Any] = {"n": len(rows)}
    for k in (1, 3, 5):
        result[f"address_coverage_at_{k}"] = sum(
            rank is not None and rank <= k for rank in ranks("address_rank")
        )
        result[f"exact_function_hits_at_{k}"] = sum(
            rank is not None and rank <= k for rank in ranks("function_rank")
        )
    result["address_coverage_n"] = sum(rank is not None for rank in ranks("address_rank"))
    result["exact_function_coverage_n"] = sum(rank is not None for rank in ranks("function_rank"))
    for k in (1, 3, 5):
        result[f"address_recall_at_{k}"] = result[f"address_coverage_at_{k}"] / len(rows) if rows else 0.0
        result[f"exact_function_recall_at_{k}"] = result[f"exact_function_hits_at_{k}"] / len(rows) if rows else 0.0
    return result


def _first_address_rank(target: Any, predictions: list[dict[str, Any]]) -> int | None:
    target_addresses = {address for address, _ in target.functions}
    for index, prediction in enumerate(predictions, 1):
        address = _norm(
            prediction.get("address")
            or prediction.get("code_address")
            or prediction.get("contract")
            or prediction.get("callee")
        )
        if address in target_addresses:
            return index
    return None


def run() -> dict[str, Any]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    eligible = [
        row for row in audit["rows"]
        if row["ground_truth_available"] and row["exact_function_identity_status"] == "ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE"
    ]
    if len(eligible) != 4:
        raise AssertionError(f"expected four previously identified overlap rows, found {len(eligible)}")
    txns = {row["transaction_hash"].lower() for row in eligible}
    targets = _load_targets(txns)
    rows: list[dict[str, Any]] = []
    for audit_row in eligible:
        txn = audit_row["transaction_hash"].lower()
        provider_path = PROVIDER_RAW / f"{txn}.json"
        trace_path = TRACE_RAW / audit_row["chain"] / f"{txn}.attempt1.json"
        provider = json.loads(provider_path.read_text(encoding="utf-8"))
        trace_raw = json.loads(trace_path.read_text(encoding="utf-8"))
        trace_text = trace_text_from_calltree(_trace_result(trace_raw))
        baseline_predictions = list(provider.get("predictions") or [])
        generated = generate_saved_candidates(baseline_predictions, trace_text)
        prepared = prepare_row({"predictions": baseline_predictions, "cast": {"output_tail": trace_text}})
        trace_predictions = rank_prepared(prepared, TRACE_CONFIG)
        target = targets[txn]
        rows.append({
            "stable_id": audit_row["stable_id"],
            "transaction_hash": txn,
            "overlap_group": "preexisting_four_original_overlap",
            "newly_recovered": False,
            "provider_raw_path": provider_path.relative_to(ROOT).as_posix(),
            "provider_raw_sha256": _sha256(provider_path),
            "trace_raw_path": trace_path.relative_to(ROOT).as_posix(),
            "trace_raw_sha256": _sha256(trace_path),
            "trace_text_sha256": hashlib.sha256(trace_text.encode("utf-8")).hexdigest(),
            "baseline_prediction_sha256": _json_sha256(baseline_predictions),
            "trace_candidate_count": len(generated),
            "trace_calls_parsed": len([line for line in trace_text.splitlines() if "::" in line]),
            "baseline": {
                "address_rank": _first_address_rank(target, baseline_predictions),
                "function_rank": rank_of_first_hit(target, baseline_predictions, match="function"),
                "predictions": baseline_predictions,
            },
            "trace_aware": {
                "address_rank": _first_address_rank(target, trace_predictions),
                "function_rank": rank_of_first_hit(target, trace_predictions, match="function"),
                "predictions": trace_predictions,
            },
            "changed": {
                "address_rank_delta": (
                    (_first_address_rank(target, trace_predictions) or 10**9)
                    - (_first_address_rank(target, baseline_predictions) or 10**9)
                ),
                "function_rank_delta": (
                    (rank_of_first_hit(target, trace_predictions, match="function") or 10**9)
                    - (rank_of_first_hit(target, baseline_predictions, match="function") or 10**9)
                ),
            },
        })

    baseline_metrics = _metrics(rows, "baseline")
    trace_metrics = _metrics(rows, "trace_aware")
    result = {
        "schema_version": 1,
        "hypothesis": "Adding generic observed call-tree address/selector candidates and a fixed trace-evidence-only rank will improve exact localization coverage without using target labels.",
        "falsification": "No coverage gain, any target-label leakage, or a regression larger than the coverage gain rejects production adoption; this four-row sample cannot establish generalization.",
        "scope": "Four preexisting original-benchmark overlap rows with typed public function evidence and captured dRPC callTracer responses; no new RPC requests.",
        "eligibility": {
            "rows": len(rows),
            "ground_truth_source": "benchmark/original_faultseeker/ground_truth",
            "trace_source": "reports/external_runs/phase2/20261017T011500Z/drpc",
            "newly_recovered_rows": 0,
            "batch_b_c_read": False,
            "batch_e_read": False,
            "trace_config": TRACE_CONFIG,
            "selector_lookup": "public selector cache only; ground-truth function registration disabled",
        },
        "baseline_metrics": baseline_metrics,
        "trace_aware_metrics": trace_metrics,
        "rows": rows,
        "decision": "EXPLORATORY_ONLY_NOT_PRODUCTION_ADOPTED",
        "limitations": [
            "All four eligible rows were already identified overlap cases; no newly recovered row has exact imported function ground truth.",
            "The four rows are not an independent held-out population and do not support generalization.",
            "The treatment uses raw observed selectors and public selector lookup, not original paper predictions or scorer behavior.",
        ],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# Recovered-trace localization experiment",
        "",
        "Exploratory four-row paired comparison. No new RPC requests were made; no Batch B/C or Batch E results were read.",
        "",
        "## Preregistered experiment",
        "",
        result["hypothesis"],
        "",
        "Treatment candidates are generated generically from observed call addresses and raw calldata selectors. Ground-truth function registration is disabled; only the public selector cache is available.",
        "",
        "| System | N | Address coverage | Exact-function coverage | R@1 | R@3 | R@5 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, metrics in (("Baseline saved predictions", baseline_metrics), ("Trace-aware fixed weight", trace_metrics)):
        md.append(
            f"| {label} | {metrics['n']} | {metrics['address_coverage_n']}/{metrics['n']} | {metrics['exact_function_coverage_n']}/{metrics['n']} | "
            f"{metrics['exact_function_hits_at_1']}/{metrics['n']} | {metrics['exact_function_hits_at_3']}/{metrics['n']} | {metrics['exact_function_hits_at_5']}/{metrics['n']} |"
        )
    md += ["", "## Per-row changes", "", "| Stable ID | Baseline function rank | Trace-aware function rank | Baseline address rank | Trace-aware address rank |", "|---|---:|---:|---:|---:|"]
    for row in rows:
        md.append(
            f"| `{row['stable_id']}` | {row['baseline']['function_rank'] or 'absent'} | {row['trace_aware']['function_rank'] or 'absent'} | "
            f"{row['baseline']['address_rank'] or 'absent'} | {row['trace_aware']['address_rank'] or 'absent'} |"
        )
    md += ["", "Decision: **exploratory only; not production adopted and not a generalization claim**.", "", "Machine-readable artifact: `reports/research_results/recovered_trace_localization_20261019.json`."]
    OUTPUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
