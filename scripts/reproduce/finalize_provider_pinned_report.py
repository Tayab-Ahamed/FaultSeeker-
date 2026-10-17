"""Finalize the pinned original-benchmark report without rerunning cases."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017"
RAW_DIR = RUN_DIR / "raw"
MANIFEST = RUN_DIR / "manifest.json"
DIAGNOSTICS = RUN_DIR / "diagnostics.md"


def load_rows() -> list[dict[str, Any]]:
    rows = [json.loads(path.read_text(encoding="utf-8"))
            for path in RAW_DIR.glob("*.json")]
    rows.sort(key=lambda row: row["case_id"])
    if len(rows) != 115:
        raise ValueError(f"expected 115 raw rows, found {len(rows)}")
    return rows


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "n_total": total,
        "n_ok": sum(row.get("status") == "ok" for row in rows),
        "n_failed": sum(row.get("status") != "ok" for row in rows),
        "replay_mismatch": sum(bool(row.get("replay_mismatch")) for row in rows),
        "recall_at_1": sum(bool(row["score"]["recall_at_1"]) for row in rows) / total,
        "recall_at_3": sum(bool(row["score"]["recall_at_3"]) for row in rows) / total,
        "recall_at_5": sum(bool(row["score"]["recall_at_5"]) for row in rows) / total,
    }


def primary_view(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reconstruct the pre-retry view from retained rows.

    Retry rows overwrite their earlier failed row. Their pre-retry score is
    therefore conservatively represented as a zero, which is exactly how the
    frozen protocol scores a failed case. Failure text from overwritten rows is
    not invented; the manifest records that limitation explicitly.
    """
    result = []
    for row in rows:
        if row.get("retry_pass"):
            old = dict(row)
            old["status"] = "failed"
            old["predictions"] = []
            old["score"] = {
                "target_function_count": None,
                "first_hit_rank": None,
                "recall_at_1": False,
                "recall_at_3": False,
                "recall_at_5": False,
            }
            old["replay_mismatch"] = False
            result.append(old)
        else:
            result.append(row)
    return result


def examples(rows: list[dict[str, Any]], predicate, limit: int = 5) -> list[str]:
    return [row["txn_hash"] for row in rows if predicate(row)][:limit]


def cause_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    # Mutually exclusive primary diagnosis, in evidence-priority order.
    categories: dict[str, list[dict[str, Any]]] = {
        "no_trace": [], "mismatch": [], "ranker_miss": [],
        "wrong_chain": [], "label_issue": [],
    }
    for row in rows:
        if row.get("status") != "ok":
            categories["no_trace"].append(row)
        elif row.get("replay_mismatch"):
            categories["mismatch"].append(row)
        elif row.get("score", {}).get("target_function_count") in (None, 0):
            categories["label_issue"].append(row)
        elif row.get("chain") not in {"eth", "bsc"}:
            categories["wrong_chain"].append(row)
        else:
            categories["ranker_miss"].append(row)
    return categories


def main() -> int:
    rows = load_rows()
    primary = primary_view(rows)
    final_all = metrics(rows)
    before_all = metrics(primary)
    valid = [row for row in rows if row.get("status") == "ok"]
    before_valid = [row for row in primary if row.get("status") == "ok"]
    retry_rows = [row for row in rows if row.get("retry_pass")]
    retry_recovered = sum(row.get("status") == "ok" for row in retry_rows)
    failures = [row for row in rows if row.get("status") != "ok"]
    categories = cause_rows(rows)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["primary_pass"] = {
        "metrics_all_115": before_all,
        "metrics_valid_trace_subset": metrics(before_valid),
        "failed_case_count": 20,
        "mismatch_count": 12,
        "failure_reason_evidence": {
            "case_9_provider_rate_limit": {
                "classification": "429",
                "evidence": "provider-pinned-run.log; the original row was overwritten by the retry pass",
            },
            "other_overwritten_failures": {
                "classification": "not_reconstructable_without_inventing stderr",
                "count": 19,
            },
        },
    }
    manifest["retry_pass"] = {
        "label": "second pass over genuinely failed primary cases",
        "compute_units_per_second": 2,
        "attempted": len(retry_rows),
        "recovered": retry_recovered,
        "remaining_failed": len(failures),
        "metrics_all_115": final_all,
        "metrics_valid_trace_subset": metrics(valid),
    }
    manifest["final_reporting"] = {
        "all_115_denominator": final_all,
        "valid_trace_definition": "status=ok; replay mismatches remain valid trace results, not failures",
        "valid_trace_subset": {
            "n_total": len(valid),
            "metrics": metrics(valid),
        },
        "failure_details": [
            {
                "txn_hash": row["txn_hash"],
                "chain": row["chain"],
                "provider": row["provider"],
                "failure_kind": row.get("failure_kind"),
                "exit_code": row.get("cast", {}).get("exit_code"),
                "stderr": (
                    row.get("failure_message")
                    if row.get("failure_kind") == "TimeoutError"
                    else row.get("cast", {}).get("stderr_tail") or row.get("failure_message")
                ),
            }
            for row in failures
        ],
        "provider_request_counts": manifest.get("request_counts", {}),
        "provider_cast_process_counts": manifest.get("cast_process_counts", {}),
    }
    manifest["diagnostic_categories"] = {
        name: {"count": len(items), "examples": [row["txn_hash"] for row in items[:5]]}
        for name, items in categories.items()
    }
    manifest["limitations"] = [
        "The retry pass overwrote primary failed raw rows; primary failure stderr is reported only where retained (case 9 is documented as 429).",
        "No wrong-chain or label-issue examples were observed; five examples are not applicable for zero-count categories.",
    ]
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Provider-pinned original-benchmark diagnosis",
        "",
        "This is diagnosis only. No detector, ranker, threshold, case selection, or paper file was changed.",
        "",
        "## Before and after the labelled retry pass",
        "",
        "| View | Before retry Recall@1/3/5 | After retry Recall@1/3/5 |",
        "|---|---:|---:|",
        f"| All 115 cases | {before_all['recall_at_1']:.6f} / {before_all['recall_at_3']:.6f} / {before_all['recall_at_5']:.6f} | {final_all['recall_at_1']:.6f} / {final_all['recall_at_3']:.6f} / {final_all['recall_at_5']:.6f} |",
        f"| Valid trace subset ({len(before_valid)} → {len(valid)}) | {metrics(before_valid)['recall_at_1']:.6f} / {metrics(before_valid)['recall_at_3']:.6f} / {metrics(before_valid)['recall_at_5']:.6f} | {metrics(valid)['recall_at_1']:.6f} / {metrics(valid)['recall_at_3']:.6f} / {metrics(valid)['recall_at_5']:.6f} |",
        "",
        f"Primary pass: 95 ok, 20 failed, 12 replay mismatches. Retry pass: {len(retry_rows)} attempted, {retry_recovered} recovered, {len(failures)} remained failed.",
        "",
        "## Final result views",
        "",
        f"- All 115 denominator: n_ok={final_all['n_ok']}, n_failed={final_all['n_failed']}, mismatches={final_all['replay_mismatch']}, Recall@1/3/5={final_all['recall_at_1']:.6f}/{final_all['recall_at_3']:.6f}/{final_all['recall_at_5']:.6f}.",
        f"- Valid trace subset: n={len(valid)}, mismatches included as valid results, Recall@1/3/5={metrics(valid)['recall_at_1']:.6f}/{metrics(valid)['recall_at_3']:.6f}/{metrics(valid)['recall_at_5']:.6f}.",
        "",
        "## Missed-case diagnosis",
        "",
        "Categories are mutually exclusive and prioritized: no trace, mismatch, label issue, wrong chain, then ranker miss.",
        "",
        "| Cause category | Count | Five examples (or N/A for zero count) |",
        "|---|---:|---|",
    ]
    labels = {
        "no_trace": "No trace",
        "mismatch": "Mismatch",
        "ranker_miss": "Ranker miss",
        "wrong_chain": "Wrong chain",
        "label_issue": "Label issue",
    }
    for key in ("no_trace", "mismatch", "ranker_miss", "wrong_chain", "label_issue"):
        items = categories[key]
        sample = ", ".join(row["txn_hash"] for row in items[:5]) or "N/A (zero cases)"
        lines.append(f"| {labels[key]} | {len(items)} | {sample} |")
    lines += [
        "",
        "### Failure details",
        "",
        "| Transaction | Chain | Failure kind | Exit code | stderr / retained reason |",
        "|---|---|---|---:|---|",
    ]
    for row in failures:
        stderr = (
            row.get("failure_message")
            if row.get("failure_kind") == "TimeoutError"
            else row.get("cast", {}).get("stderr_tail") or row.get("failure_message") or "(none retained)"
        )
        lines.append(f"| {row['txn_hash']} | {row['chain']} | {row.get('failure_kind')} | {row.get('cast', {}).get('exit_code', 'N/A')} | {stderr.replace(chr(10), ' ')[:240]} |")
    lines += [
        "",
        "Raw per-transaction rows remain under `raw/`; the final manifest is `manifest.json`.",
    ]
    DIAGNOSTICS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "before_all": before_all,
        "after_all": final_all,
        "before_valid_trace": metrics(before_valid),
        "after_valid_trace": metrics(valid),
        "retry_attempted": len(retry_rows),
        "retry_recovered": retry_recovered,
        "remaining_failed": len(failures),
        "diagnostics": str(DIAGNOSTICS.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
