"""Evaluate the cached 115-case run with the paper-level upstream reconstruction.

This is deliberately a new output path.  It never modifies the retained
provider-pinned predictions, never calls RPC/cast/models, and keeps all 115
ground-truth files in the denominator.  Because the upstream repository did
not publish its evaluator, the ``upstream_reconstruction`` metric is the
evidence-bounded function-name-only rule: raw candidate function identifiers
are compared with labeled function names without selector lookup or address
requirements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import (  # noqa: E402
    LocalizationTarget,
    _parse_location_entry,
    _register_fn_names,
    rank_of_first_hit,
)
from benchmark.upstream_compat_ranker import UPSTREAM_COMMIT  # noqa: E402


DEFAULT_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
DEFAULT_RAW = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
DEFAULT_OUT = ROOT / "reports/original_benchmark/upstream-compatible-cached-20261019"
PAPER_TARGETS = {"recall_at_1": 58, "recall_at_3": 85, "recall_at_5": 88}


def _write_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tx_hash(raw: dict[str, Any], path: Path) -> str:
    values = raw.get("transaction_hash") or []
    if isinstance(values, str):
        values = [values]
    return str(values[0] if values else path.stem).strip().lower()


def _raw_function(prediction: dict[str, Any]) -> str:
    return str(
        prediction.get("function_name")
        or prediction.get("name")
        or prediction.get("function")
        or ""
    ).strip().split("(")[0].lower()


def _target(path: Path) -> LocalizationTarget:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    target = LocalizationTarget(txn_hash=_tx_hash(raw, path), name=str(raw.get("name") or ""))
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
    return target


def _raw_selector_rank(target: LocalizationTarget, predictions: list[dict[str, Any]]) -> int | None:
    expected = {function for _address, function in target.functions}
    for index, prediction in enumerate(predictions, start=1):
        if _raw_function(prediction) in expected:
            return index
    return None


def _current_rank(target: LocalizationTarget, predictions: list[dict[str, Any]]) -> int | None:
    return rank_of_first_hit(target, predictions, match="function")


def _failure_stage(row: dict[str, Any], upstream_rank: int | None) -> str:
    if row.get("status") != "ok":
        kind = str(row.get("failure_kind") or "").lower()
        if "timeout" in kind or "runtime" in kind or "trace" in kind:
            return "data_collection_or_trace_replay"
        return "orchestration_or_trace_parsing"
    if not row.get("predictions_count"):
        return "candidate_generation"
    if upstream_rank is None:
        return "final_ranking_or_ground_truth_mismatch"
    return "none"


def _metric(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    hits = sum(bool(row["metrics"][field]) for row in rows)
    n = len(rows)
    return {"hits": hits, "n": n, "percentage": round(100 * hits / n, 6) if n else 0.0}


def evaluate(gt_dir: Path, raw_dir: Path, output_dir: Path) -> dict[str, Any]:
    gt_paths = sorted(gt_dir.glob("*.json"))
    if len(gt_paths) != 115:
        raise ValueError(f"expected 115 ground-truth files, found {len(gt_paths)}")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    rows = []
    for gt_path in gt_paths:
        case_id = gt_path.stem
        raw_path = raw_dir / f"{case_id}.json"
        target = _target(gt_path)
        row: dict[str, Any] = {
            "case_id": case_id,
            "ground_truth_sha256": _sha256(gt_path),
            "raw_path": raw_path.as_posix(),
            "status": "missing_cached_row",
            "failure_kind": "MissingCachedRow",
            "predictions_count": 0,
            "current_rank": None,
            "upstream_reconstruction_rank": None,
            "target_function_count": len(target.functions),
            "metrics": {"current": {}, "upstream_reconstruction": {}},
        }
        if raw_path.is_file():
            saved = json.loads(raw_path.read_text(encoding="utf-8"))
            predictions = list(saved.get("predictions") or [])
            upstream_rank = _raw_selector_rank(target, predictions) if saved.get("status") == "ok" else None
            current_rank = _current_rank(target, predictions) if saved.get("status") == "ok" else None
            row.update({
                "status": saved.get("status"),
                "failure_kind": saved.get("failure_kind"),
                "failure_message": saved.get("failure_message"),
                "chain": saved.get("chain"),
                "predictions_count": len(predictions),
                "current_rank": current_rank,
                "upstream_reconstruction_rank": upstream_rank,
                "replay_mismatch": bool(saved.get("replay_mismatch")),
            })
        upstream_rank = row["upstream_reconstruction_rank"]
        current_rank = row["current_rank"]
        row["metrics"] = {
            "current": {
                "recall_at_1": bool(current_rank is not None and current_rank <= 1),
                "recall_at_3": bool(current_rank is not None and current_rank <= 3),
                "recall_at_5": bool(current_rank is not None and current_rank <= 5),
            },
            "upstream_reconstruction": {
                "recall_at_1": bool(upstream_rank is not None and upstream_rank <= 1),
                "recall_at_3": bool(upstream_rank is not None and upstream_rank <= 3),
                "recall_at_5": bool(upstream_rank is not None and upstream_rank <= 5),
            },
        }
        row["failure_stage"] = _failure_stage(row, upstream_rank)
        rows.append(row)

    upstream_rows = [{
        "metrics": row["metrics"]["upstream_reconstruction"],
    } for row in rows]
    current_rows = [{"metrics": row["metrics"]["current"]} for row in rows]
    aggregate = {
        "n_total": len(rows),
        "n_ok": sum(row.get("status") == "ok" for row in rows),
        "n_failed": sum(row.get("status") != "ok" for row in rows),
        "cached_prediction_rows": sum(row.get("predictions_count", 0) > 0 for row in rows),
        "upstream_reconstruction": {
            field: _metric(upstream_rows, field)
            for field in ("recall_at_1", "recall_at_3", "recall_at_5")
        },
        "current_address_aware": {
            field: _metric(current_rows, field)
            for field in ("recall_at_1", "recall_at_3", "recall_at_5")
        },
        "failure_stages": {
            stage: sum(row["failure_stage"] == stage for row in rows)
            for stage in sorted({row["failure_stage"] for row in rows})
        },
        "paper_target_counts": PAPER_TARGETS,
        "paper_target_percentages": {
            field: round(100 * count / 115, 6) for field, count in PAPER_TARGETS.items()
        },
    }
    report = {
        "scope": {
            "ground_truth_files": len(gt_paths),
            "raw_dir": raw_dir.as_posix(),
            "rpc_calls": 0,
            "cast_calls": 0,
            "model_calls": 0,
            "predictions_reused": True,
            "frozen_batches_touched": [],
        },
        "upstream": {
            "source_commit": UPSTREAM_COMMIT,
            "ranking_formula": "descending count of distinct stringified depth paths; stable equal-count order",
            "ranking_output": "functions_to_be_inspected insertion order; no numeric rank field in upstream RankingResult",
            "metric_definition": "evidence-bounded function-name-only top-k reconstruction; raw selectors are not resolved; address is not required",
            "evaluator_status": "not published by upstream; this is a reconstruction, not an authors-side scorer",
        },
        "aggregate": aggregate,
        "rows": rows,
    }
    output_dir.mkdir(parents=True)
    _write_lf(output_dir / "evaluation.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Cached original-benchmark upstream-compatible evaluation",
        "",
        f"Source commit: `{UPSTREAM_COMMIT}`",
        "",
        "This report reuses saved provider-pinned predictions and never calls RPC, cast, or models.",
        "The upstream evaluator was not published; the primary reconstruction compares raw function identifiers by name only.",
        "",
        "| Metric | Hits | N | Percentage |",
        "|---|---:|---:|---:|",
    ]
    for label, key in (("Upstream reconstruction R@1", "recall_at_1"), ("Upstream reconstruction R@3", "recall_at_3"), ("Upstream reconstruction R@5", "recall_at_5"), ("Current address-aware R@1", "recall_at_1"), ("Current address-aware R@3", "recall_at_3"), ("Current address-aware R@5", "recall_at_5")):
        group = "upstream_reconstruction" if label.startswith("Upstream") else "current_address_aware"
        metric = aggregate[group][key]
        lines.append(f"| {label} | {metric['hits']} | {metric['n']} | {metric['percentage']:.2f}% |")
    lines += [
        "",
        "## Paper comparison",
        "",
        "| Metric | Reconstructed hits | Paper target hits | Difference |",
        "|---|---:|---:|---:|",
    ]
    for field, target_count in PAPER_TARGETS.items():
        actual = aggregate["upstream_reconstruction"][field]["hits"]
        lines.append(f"| {field} | {actual} | {target_count} | {actual - target_count} |")
    lines += [
        "",
        "## Failure-stage counts",
        "",
        "```json",
        json.dumps(aggregate["failure_stages"], indent=2, sort_keys=True),
        "```",
    ]
    _write_lf(output_dir / "REPORT.md", "\n".join(lines) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-dir", type=Path, default=DEFAULT_GT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    report = evaluate(args.gt_dir, args.raw_dir, args.output_dir)
    aggregate = report["aggregate"]["upstream_reconstruction"]
    print(f"n_total={report['aggregate']['n_total']}")
    print(f"n_ok={report['aggregate']['n_ok']}")
    print(f"n_failed={report['aggregate']['n_failed']}")
    for field in ("recall_at_1", "recall_at_3", "recall_at_5"):
        print(f"{field}_hits={aggregate[field]['hits']}")
        print(f"{field}_percentage={aggregate[field]['percentage']:.6f}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
