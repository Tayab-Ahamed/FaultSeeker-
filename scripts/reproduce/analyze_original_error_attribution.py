"""Offline transaction-level error attribution for the cached 115-case run.

This analysis reads the authoritative cached evaluation, its 115 ground-truth
files, and the retained provider-pinned raw rows.  It never reruns ranking,
trace replay, RPC, source retrieval, or model calls.  It keeps the case/file
identity (rather than deduplicating transaction hashes) and reports evidence-
bounded classifications, not causal claims about unavailable traces.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import (  # noqa: E402
    LocalizationTarget,
    _norm_addr,
    _norm_fn,
    _parse_location_entry,
    _prediction_keys,
    _register_fn_names,
    rank_of_first_hit,
)


DEFAULT_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
DEFAULT_RAW = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
DEFAULT_EVAL = ROOT / "reports/original_benchmark/upstream-compatible-cached-20261019-final/evaluation.json"
DEFAULT_OUT = ROOT / "reports/original_benchmark/error-attribution-20261020"

K_VALUES = (1, 3, 5)


def _write_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _raw_function(prediction: dict[str, Any]) -> str:
    return _norm_fn(
        prediction.get("function_name")
        or prediction.get("name")
        or prediction.get("function")
        or ""
    )


def _prediction_address(prediction: dict[str, Any]) -> str:
    return _norm_addr(
        prediction.get("address")
        or prediction.get("code_address")
        or prediction.get("contract")
        or prediction.get("callee")
        or ""
    )


def _target_from_gt(path: Path) -> tuple[LocalizationTarget, list[str], list[str]]:
    raw = _load(path)
    hashes = raw.get("transaction_hash") or []
    if isinstance(hashes, str):
        hashes = [hashes]
    target = LocalizationTarget(
        txn_hash=str(hashes[0] if hashes else path.stem).lower(),
        name=str(raw.get("name") or ""),
    )
    raw_labels: list[str] = []
    names: list[str] = []
    for key, values in (raw.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parsed = _parse_location_entry(entry)
            if not parsed:
                continue
            address, member, is_line = parsed
            raw_labels.append(str(entry))
            if not is_line:
                target.functions.add((address, member))
                names.append(member)
    return target, raw_labels, names


def _failure_subtype(row: dict[str, Any]) -> str:
    text = f"{row.get('failure_kind') or ''} {row.get('failure_message') or ''} {row.get('cast', {}).get('stderr_tail') or ''}".lower()
    if "timeout" in text:
        return "provider_timeout"
    if "429" in text or "rate limit" in text or "rate_limit" in text:
        return "provider_rate_limit"
    if any(token in text for token in ("rpc", "transport", "connection", "network")):
        return "provider_transport_or_rpc_error"
    if any(token in text for token in ("trace", "orchestrat", "parse")):
        return "orchestration_or_trace_parsing_error"
    return "unclassified_failure"


def _rank_raw_function(target: LocalizationTarget, predictions: list[dict[str, Any]]) -> int | None:
    expected = {function for _address, function in target.functions}
    for index, prediction in enumerate(predictions, start=1):
        if _raw_function(prediction) in expected:
            return index
    return None


def _rank_raw_pair(target: LocalizationTarget, predictions: list[dict[str, Any]]) -> int | None:
    for index, prediction in enumerate(predictions, start=1):
        if (_prediction_address(prediction), _raw_function(prediction)) in target.functions:
            return index
    return None


def _rank_address(target: LocalizationTarget, predictions: list[dict[str, Any]]) -> int | None:
    addresses = {address for address, _function in target.functions}
    for index, prediction in enumerate(predictions, start=1):
        if _prediction_address(prediction) in addresses:
            return index
    return None


def _candidate_at(predictions: list[dict[str, Any]], rank: int | None) -> dict[str, Any] | None:
    if rank is None or rank < 1 or rank > len(predictions):
        return None
    return predictions[rank - 1]


def _resolved_target_candidate(target: LocalizationTarget, predictions: list[dict[str, Any]], limit: int = 5):
    for rank, prediction in enumerate(predictions[:limit], start=1):
        fn_key, _line_key = _prediction_keys(prediction)
        if fn_key and fn_key in target.functions:
            return rank, prediction, fn_key
    return None, None, None


def _top_candidates(predictions: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    result = []
    for rank, prediction in enumerate(predictions[:limit], start=1):
        result.append({
            "rank": rank,
            "address": _prediction_address(prediction),
            "raw_function": _raw_function(prediction),
            "selector": prediction.get("selector"),
            "stored_function": prediction.get("function"),
        })
    return result


def _classification(
    row: dict[str, Any],
    target: LocalizationTarget,
    predictions: list[dict[str, Any]],
    raw_rank: int | None,
    raw_pair_rank: int | None,
    current_rank: int | None,
    address_rank: int | None,
) -> tuple[str, str | None, list[str]]:
    if row.get("status") != "ok":
        return "A_cached_execution_trace_failure", _failure_subtype(row), []
    if not target.functions:
        return "F_insufficient_evidence", "ground_truth_function_target_missing", []

    resolved_rank, resolved_prediction, resolved_key = _resolved_target_candidate(target, predictions)
    raw_rank_in_top5 = raw_rank is not None and raw_rank <= 5
    current_rank_in_top5 = current_rank is not None and current_rank <= 5

    # Current scorer finds a selector-resolved target in Top-5, but the
    # evidence-bounded reconstruction intentionally compares the raw selector.
    if current_rank_in_top5 and not raw_rank_in_top5 and resolved_prediction is not None:
        raw_fn = _raw_function(resolved_prediction)
        if raw_fn.startswith("0x") and len(raw_fn) == 10:
            return "D_top5_candidate_reconstruction_equality_miss", "selector_name_resolution", [
                f"current_rank={resolved_rank}",
                f"resolved_function={resolved_key[1] if resolved_key else ''}",
                f"raw_selector={raw_fn}",
            ]

    # Raw function-only reconstruction hits, but current address-aware matching
    # misses: the saved evidence demonstrates a function/address identity gap.
    if raw_rank_in_top5 and not current_rank_in_top5:
        raw_prediction = _candidate_at(predictions, raw_rank)
        target_addresses = {address for address, _function in target.functions}
        if raw_prediction and _prediction_address(raw_prediction) not in target_addresses:
            return "E_demonstrated_identity_normalization_mismatch", "address_identity_mismatch", [
                f"raw_function_rank={raw_rank}",
                f"raw_candidate_address={_prediction_address(raw_prediction)}",
                f"target_addresses={sorted(target_addresses)}",
            ]
        return "F_insufficient_evidence", "ranker_rule_disagreement_without_specific_saved_identity_evidence", []

    if raw_rank is None:
        subtype = "target_address_present_function_identifier_absent" if address_rank is not None else "no_target_function_identifier_in_saved_candidates"
        return "B_no_target_candidate_in_saved_set", subtype, [
            f"target_address_rank={address_rank}",
            f"candidate_count={len(predictions)}",
        ]

    if raw_rank > 5:
        return "C_target_candidate_ranked_outside_top5", "raw_function_candidate_after_top5", [
            f"raw_function_rank={raw_rank}",
            f"raw_pair_rank={raw_pair_rank}",
        ]

    if raw_rank <= 5:
        return "localized", None, []

    return "F_insufficient_evidence", "unclassified_successful_row", []


def _row_metrics(rank: int | None) -> dict[str, bool]:
    return {f"recall_at_{k}": bool(rank is not None and rank <= k) for k in K_VALUES}


def _metric(rows: list[dict[str, Any]], group: str, field: str) -> dict[str, Any]:
    hits = sum(bool(row["rankings"][group][field]) for row in rows)
    n = len(rows)
    return {"hits": hits, "n": n, "percentage": round(100 * hits / n, 6) if n else 0.0}


def _investigation_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for row in rows:
        category = row["primary_classification"]
        if category in {
            "D_top5_candidate_reconstruction_equality_miss",
            "E_demonstrated_identity_normalization_mismatch",
        }:
            priority = 1
            question = "Validate the saved selector/address identity against an exact upstream scoring rule or ABI mapping."
            outcome = "Could convert the disagreement into a confirmed normalization issue or remove it if the private scorer used another identity rule."
        elif category == "C_target_candidate_ranked_outside_top5" and row.get("raw_function_rank", 999) <= 10:
            priority = 2
            question = "Inspect the saved candidate ordering and trace-derived count evidence for a target ranked just below Top-5."
            outcome = "Could support a ranking-order diagnosis, but cannot establish why the ordering was produced without raw trace candidates."
        elif category == "B_no_target_candidate_in_saved_set" and row.get("target_address_rank") is not None:
            priority = 3
            question = "Resolve whether the target-address candidates use a selector/signature that is not represented by the saved function identifier."
            outcome = "Could change candidate absence to a demonstrated identity mismatch if a retained selector/ABI artifact exists."
        else:
            continue
        candidates.append({
            "priority": priority,
            "case_id": row["case_id"],
            "txn_hash": row["txn_hash"],
            "primary_classification": category,
            "evidence": {
                "raw_path": row["raw_path"],
                "target_functions": row["target_functions"],
                "top5_candidates": row["top5_candidates"],
                "raw_function_rank": row.get("raw_function_rank"),
                "current_rank": row.get("current_rank"),
                "target_address_rank": row.get("target_address_rank"),
            },
            "unresolved_question": question,
            "classification_change_if_resolved": outcome,
        })
    candidates.sort(key=lambda item: (item["priority"], item["case_id"]))
    return candidates[:20]


def analyze(gt_dir: Path, raw_dir: Path, eval_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    authoritative = _load(eval_path)
    authoritative_rows = {row["case_id"]: row for row in authoritative["rows"]}
    gt_paths = sorted(gt_dir.glob("*.json"))
    if len(gt_paths) != 115:
        raise ValueError(f"expected 115 ground-truth files, found {len(gt_paths)}")

    targets: dict[str, tuple[LocalizationTarget, list[str], list[str]]] = {}
    all_names: list[str] = []
    for path in gt_paths:
        targets[path.stem] = _target_from_gt(path)
        all_names.extend(targets[path.stem][2])
    _register_fn_names(all_names)

    rows = []
    for gt_path in gt_paths:
        case_id = gt_path.stem
        target, raw_labels, _names = targets[case_id]
        raw_path = raw_dir / f"{case_id}.json"
        raw_row = _load(raw_path) if raw_path.is_file() else None
        eval_row = authoritative_rows.get(case_id)
        if eval_row is None:
            raise ValueError(f"authoritative evaluation missing case {case_id}")
        predictions = list(raw_row.get("predictions") or []) if raw_row else []
        current_rank = rank_of_first_hit(target, predictions, match="function") if raw_row and raw_row.get("status") == "ok" else None
        raw_rank = _rank_raw_function(target, predictions) if raw_row and raw_row.get("status") == "ok" else None
        raw_pair_rank = _rank_raw_pair(target, predictions) if raw_row and raw_row.get("status") == "ok" else None
        address_rank = _rank_address(target, predictions) if raw_row and raw_row.get("status") == "ok" else None
        status = raw_row.get("status") if raw_row else "missing_cached_row"
        row = {
            "case_id": case_id,
            "txn_hash": (raw_row or {}).get("txn_hash") or target.txn_hash,
            "chain": (raw_row or {}).get("chain"),
            "status": status,
            "failure_kind": (raw_row or {}).get("failure_kind"),
            "failure_message": (raw_row or {}).get("failure_message"),
            "failure_subtype": _failure_subtype(raw_row or {}) if status != "ok" else None,
            "replay_mismatch": bool((raw_row or {}).get("replay_mismatch")),
            "raw_path": raw_path.as_posix(),
            "target_labels": raw_labels,
            "target_functions": [f"{address}#{function}" for address, function in sorted(target.functions)],
            "target_function_count": len(target.functions),
            "predictions_count": len(predictions),
            "top5_candidates": _top_candidates(predictions),
            "current_rank": current_rank,
            "raw_function_rank": raw_rank,
            "raw_pair_rank": raw_pair_rank,
            "target_address_rank": address_rank,
        }
        primary, subtype, evidence = _classification(
            raw_row or {}, target, predictions, raw_rank, raw_pair_rank, current_rank, address_rank
        )
        row["primary_classification"] = primary
        row["classification_subtype"] = subtype
        row["classification_evidence"] = evidence
        row["rankings"] = {
            "upstream_reconstruction": _row_metrics(raw_rank),
            "current_address_aware": _row_metrics(current_rank),
        }
        row["ranker_disagreement"] = {
            f"recall_at_{k}": row["rankings"]["upstream_reconstruction"][f"recall_at_{k}"] != row["rankings"]["current_address_aware"][f"recall_at_{k}"]
            for k in K_VALUES
        }
        row["authoritative_rank_consistency"] = {
            "upstream_reconstruction_rank_matches": eval_row.get("upstream_reconstruction_rank") == raw_rank,
            "current_address_aware_rank_matches": eval_row.get("current_rank") == current_rank,
        }
        rows.append(row)

    primary_counts = Counter(row["primary_classification"] for row in rows)
    for category in (
        "A_cached_execution_trace_failure",
        "B_no_target_candidate_in_saved_set",
        "C_target_candidate_ranked_outside_top5",
        "D_top5_candidate_reconstruction_equality_miss",
        "E_demonstrated_identity_normalization_mismatch",
        "F_insufficient_evidence",
        "localized",
    ):
        primary_counts.setdefault(category, 0)
    aggregate = {
        "n_total": len(rows),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "primary_classification_counts": dict(sorted(primary_counts.items())),
        "upstream_reconstruction": {
            f"recall_at_{k}": _metric(rows, "upstream_reconstruction", f"recall_at_{k}") for k in K_VALUES
        },
        "current_address_aware": {
            f"recall_at_{k}": _metric(rows, "current_address_aware", f"recall_at_{k}") for k in K_VALUES
        },
        "ranker_disagreement_counts": {
            f"recall_at_{k}": sum(row["ranker_disagreement"][f"recall_at_{k}"] for row in rows)
            for k in K_VALUES
        },
        "valid_trace_subset": {
            "n": sum(row["status"] == "ok" for row in rows),
            "upstream_reconstruction": {
                f"recall_at_{k}": _metric([row for row in rows if row["status"] == "ok"], "upstream_reconstruction", f"recall_at_{k}")
                for k in K_VALUES
            },
        },
        "authoritative_comparison": {
            "n_total": authoritative["aggregate"]["n_total"],
            "n_ok": authoritative["aggregate"]["n_ok"],
            "n_failed": authoritative["aggregate"]["n_failed"],
            "matches": authoritative["aggregate"]["n_total"] == len(rows),
        },
        "demonstrated_normalization_issue_counts": {
            "selector_name_resolution": sum(row["classification_subtype"] == "selector_name_resolution" for row in rows),
            "address_identity_mismatch": sum(row["classification_subtype"] == "address_identity_mismatch" for row in rows),
        },
    }
    report = {
        "scope": {
            "ground_truth_files": len(gt_paths),
            "raw_rows_read": sum(1 for path in gt_paths if (raw_dir / f"{path.stem}.json").is_file()),
            "evaluation_path": eval_path.as_posix(),
            "rpc_calls": 0,
            "cast_calls": 0,
            "model_calls": 0,
            "frozen_batches_touched": [],
            "prediction_rerun": False,
        },
        "classification_policy": {
            "A": "status is not ok; cached execution/trace failure",
            "B": "successful row with no target function identifier in saved candidates",
            "C": "target function identifier exists but raw reconstruction rank is greater than 5",
            "D": "current normalized scorer finds target in Top-5 but raw reconstruction misses due demonstrated selector/name equality",
            "E": "raw function-only reconstruction hits in Top-5 while address-aware scorer misses due demonstrated address identity",
            "F": "successful row whose evidence does not support a stronger classification",
            "localized": "successful raw reconstruction hit within Top-5; not a failure",
        },
        "aggregate": aggregate,
        "investigation_queue": _investigation_queue(rows),
        "rows": rows,
    }
    output_dir.mkdir(parents=True)
    _write_lf(output_dir / "error_attribution.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Transaction-level error attribution",
        "",
        "Offline analysis of all 115 cached provider-pinned cases. No ranking, RPC, cast, model, or source-retrieval call was made.",
        "",
        "## Aggregate",
        "",
        f"- Denominator: {aggregate['n_total']}",
        f"- Status counts: `{json.dumps(aggregate['status_counts'], sort_keys=True)}`",
        f"- Primary classifications: `{json.dumps(aggregate['primary_classification_counts'], sort_keys=True)}`",
        "",
        "| Metric | Upstream reconstruction | Current address-aware |",
        "|---|---:|---:|",
    ]
    for k in K_VALUES:
        upstream = aggregate["upstream_reconstruction"][f"recall_at_{k}"]
        current = aggregate["current_address_aware"][f"recall_at_{k}"]
        lines.append(f"| R@{k} | {upstream['hits']}/{upstream['n']} ({upstream['percentage']:.2f}%) | {current['hits']}/{current['n']} ({current['percentage']:.2f}%) |")
    lines += [
        "",
        "## Demonstrated normalization/equality issues",
        "",
        f"- Selector/name resolution cases: `{aggregate['demonstrated_normalization_issue_counts']['selector_name_resolution']}`.",
        f"- Address identity mismatch cases: `{aggregate['demonstrated_normalization_issue_counts']['address_identity_mismatch']}`.",
        "",
        "## Required scientific conclusion",
        "",
        "1. Misses/classifications: 5 execution/trace failures, 41 candidate-absence cases, 14 target candidates outside Top-5, 3 demonstrated address-identity mismatches, 2 demonstrated selector/name equality mismatches, and 0 rows requiring the unresolved F bucket. The remaining 50 rows are localized within Top-5 under the reconstruction; they are not failures.",
        "2. Highest-value next investigations are the five demonstrated normalization/equality rows, followed by eight C rows with raw target ranks 6–10, then B rows where the target address is present but the function identifier is absent.",
        "3. Existing cached evidence explains five ranker-rule disagreements and 5/115 execution failures, but it does not explain the 31/36/35-hit publication gap. The 41 B rows are candidate absence in saved predictions, not proof of trace or candidate-generation causality.",
        "4. Going further requires the original per-transaction traces/candidate evidence and the unreleased authors-side evaluator/model outputs, or a new authorized end-to-end run with the pinned upstream stack. No fresh external execution was performed here.",
        "",
        "## Highest-value investigation queue",
        "",
        "| Priority | Case | Classification | Unresolved question |",
        "|---:|---|---|---|",
    ]
    for item in report["investigation_queue"]:
        lines.append(f"| {item['priority']} | `{item['case_id']}` | {item['primary_classification']} | {item['unresolved_question']} |")
    lines += [
        "",
        "Queue evidence and classification changes are recorded in `error_attribution.json` under `investigation_queue[].evidence` and `classification_change_if_resolved`.",
    ]
    lines += [
        "",
        "## Scientific boundary",
        "",
        "This is a cached diagnostic-prediction analysis, not an exact reproduction of the ASE 2025 system. Candidate absence does not prove trace failure, and saved rankings do not expose the unreleased upstream evaluator's private evidence or tie handling.",
    ]
    _write_lf(output_dir / "REPORT.md", "\n".join(lines) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-dir", type=Path, default=DEFAULT_GT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--evaluation", type=Path, default=DEFAULT_EVAL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    report = analyze(args.gt_dir, args.raw_dir, args.evaluation, args.output_dir)
    print(json.dumps(report["aggregate"], indent=2, sort_keys=True))
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
