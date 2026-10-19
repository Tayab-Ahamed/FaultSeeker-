"""Replay saved localization predictions before/after selector identity normalization.

This is a same-input, same-ground-truth evaluation of the production identity
canonicalization change. It does not call a provider, use frozen Batch E, or
use ground truth to create candidates. The candidate side only applies the
new ``canonical_call_label`` to the already-saved candidate identities.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import load_ground_truth, rank_of_first_hit
from faultseeker.function_analysis.candidate_generation import generate_saved_candidates


RAW_DIR = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
GROUND_TRUTH_DIR = ROOT / "benchmark/original_faultseeker/ground_truth"
CLASSIFICATION = ROOT / "benchmark/original_faultseeker/benchmark_classification.csv"
OUTPUT_DIR = ROOT / "reports/reproducibility/localization_candidate_coverage_selector_normalization"
PREDICTIONS_OUT = OUTPUT_DIR / "predictions.jsonl"
REPORT_OUT = OUTPUT_DIR / "report.json"
CHECKSUMS_OUT = OUTPUT_DIR / "checksums.json"
_BARE_SELECTOR = re.compile(r"^[0-9a-fA-F]{8}$")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _aggregate_directory_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _candidate_address(candidate: dict) -> str:
    return str(
        candidate.get("address")
        or candidate.get("code_address")
        or candidate.get("contract")
        or candidate.get("callee")
        or ""
    ).strip().lower()


def _candidate_function(candidate: dict) -> str:
    return str(
        candidate.get("function_name")
        or candidate.get("name")
        or candidate.get("function")
        or ""
    )


def _canonicalize_candidates(candidates: list[dict]) -> list[dict]:
    result = []
    for candidate in candidates:
        item = dict(candidate)
        function = _candidate_function(item)
        if _BARE_SELECTOR.fullmatch(function.strip()):
            function = f"0x{function.strip().lower()}"
            item["function"] = function
            if "function_name" in item:
                item["function_name"] = function
            item["selector"] = function
        result.append(item)
    return result


def _target_status(target) -> str:
    if not target.functions:
        return "invalid_or_ambiguous_ground_truth"
    members = [member for _, member in target.functions]
    if any(not str(member).strip() for member in members):
        return "invalid_or_ambiguous_ground_truth"
    return "valid"


def _metrics(rows: list[dict], side: str) -> dict:
    ranks = [row[f"{side}_rank"] for row in rows]
    return {
        "n": len(rows),
        "address_candidate_recall": sum(row[f"{side}_address_present"] for row in rows) / len(rows),
        "address_candidates": sum(row[f"{side}_address_present"] for row in rows),
        "exact_function_candidate_recall": sum(row[f"{side}_function_present"] for row in rows) / len(rows),
        "exact_function_candidates": sum(row[f"{side}_function_present"] for row in rows),
        "top_1": sum(rank is not None and rank <= 1 for rank in ranks),
        "top_3": sum(rank is not None and rank <= 3 for rank in ranks),
        "top_5": sum(rank is not None and rank <= 5 for rank in ranks),
        "ranking_alone_failures": sum(rank is not None and rank > 5 for rank in ranks),
        "unranked_function_misses": sum(rank is None for rank in ranks),
    }


def _failure_category(row: dict, side: str) -> str:
    if row["ground_truth_status"] != "valid":
        return "invalid_or_ambiguous_ground_truth"
    if not row[f"{side}_address_present"]:
        return "target_address_absent_from_candidates"
    if not row[f"{side}_function_present"]:
        return "target_address_present_target_function_absent"
    if row[f"{side}_rank"] > 5:
        return "correct_target_function_present_but_ranked_too_low"
    return "no_failure"


def main() -> int:
    targets = {target.txn_hash.lower(): target for target in load_ground_truth(str(GROUND_TRUTH_DIR))}
    rows = []
    for raw_path in sorted(RAW_DIR.glob("*.json")):
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        txn_hash = str(payload.get("case_id") or raw_path.stem).lower()
        target = targets.get(txn_hash)
        if target is None or not target.functions:
            continue
        baseline = list(payload.get("predictions") or [])
        candidate = _canonicalize_candidates(baseline)
        trace_augmented = generate_saved_candidates(
            baseline,
            str((payload.get("cast") or {}).get("output_tail") or ""),
        )
        target_addresses = {address.lower() for address, _ in target.functions}

        def evaluate(side: str, predictions: list[dict]) -> tuple[bool, bool, int | None]:
            addresses = {_candidate_address(item) for item in predictions}
            address_present = bool(target_addresses & addresses)
            rank = rank_of_first_hit(target, predictions, match="function")
            return address_present, rank is not None, rank

        baseline_address, baseline_function, baseline_rank = evaluate("baseline", baseline)
        candidate_address, candidate_function, candidate_rank = evaluate("candidate", candidate)
        trace_address, trace_function, trace_rank = evaluate("trace_augmented", trace_augmented)
        row = {
            "transaction_hash": txn_hash,
            "raw_input_sha256": _sha256_file(raw_path),
            "chain": payload.get("chain"),
            "target_functions": sorted(target.functions),
            "ground_truth_status": _target_status(target),
            "baseline_address_present": baseline_address,
            "baseline_function_present": baseline_function,
            "baseline_rank": baseline_rank,
            "baseline_failure_category": None,
            "candidate_address_present": candidate_address,
            "candidate_function_present": candidate_function,
            "candidate_rank": candidate_rank,
            "trace_augmented_address_present": trace_address,
            "trace_augmented_function_present": trace_function,
            "trace_augmented_rank": trace_rank,
            "target_address_in_available_trace_text": any(
                address in str((payload.get("cast") or {}).get("output_tail") or "").lower()
                for address in target_addresses
            ),
            "candidate_failure_category": None,
            "baseline_predictions": baseline,
            "candidate_predictions": candidate,
        }
        row["baseline_failure_category"] = _failure_category(row, "baseline")
        row["candidate_failure_category"] = _failure_category(row, "candidate")
        # The replay is deliberately the identity-format change only. If the
        # baseline evaluator misses a function that becomes an exact hit after
        # adding the canonical selector prefix, classify that baseline failure
        # as an identity-mapping defect rather than as a genuinely absent
        # function.
        if not row["baseline_function_present"] and row["candidate_function_present"]:
            row["baseline_failure_category"] = "evaluation_or_identity_mapping_defect"
        rows.append(row)

    if len(rows) != 114:
        raise AssertionError(f"expected 114 eligible rows, found {len(rows)}")

    transitions = Counter(
        (row["baseline_failure_category"], row["candidate_failure_category"])
        for row in rows
    )
    category_counts = {
        "baseline": dict(Counter(row["baseline_failure_category"] for row in rows)),
        "candidate": dict(Counter(row["candidate_failure_category"] for row in rows)),
    }
    report = {
        "schema_version": 1,
        "status": "SAME_INPUT_SAVED_OUTPUT_REPLAY",
        "experiment": "localization_candidate_coverage_selector_normalization",
        "candidate_change": "Canonicalize exactly-eight-hex-digit function labels to 0x-prefixed selectors.",
        "eligible_rows": len(rows),
        "external_calls": 0,
        "frozen_batch_e_used": False,
        "selection": "No selection; deterministic identity normalization evaluated on every eligible row.",
        "metrics": {
            "baseline": _metrics(rows, "baseline"),
            "candidate": _metrics(rows, "candidate"),
            "trace_augmented_diagnostic": _metrics(rows, "trace_augmented"),
        },
        "deltas": {
            key: _metrics(rows, "candidate")[key] - _metrics(rows, "baseline")[key]
            for key in (
                "address_candidates",
                "exact_function_candidates",
                "top_1",
                "top_3",
                "top_5",
                "ranking_alone_failures",
            )
        },
        "newly_recoverable_targets": [
            row["transaction_hash"]
            for row in rows
            if row["baseline_rank"] is None and row["candidate_rank"] is not None
        ],
        "regressions": {
            f"top_{k}": [
                row["transaction_hash"]
                for row in rows
                if (row["baseline_rank"] is not None and row["baseline_rank"] <= k)
                and not (row["candidate_rank"] is not None and row["candidate_rank"] <= k)
            ]
            for k in (1, 3, 5)
        },
        "paired_comparison": {
            f"top_{k}": {
                "baseline_only": sum(
                    row["baseline_rank"] is not None
                    and row["baseline_rank"] <= k
                    and not (row["candidate_rank"] is not None and row["candidate_rank"] <= k)
                    for row in rows
                ),
                "candidate_only": sum(
                    row["candidate_rank"] is not None
                    and row["candidate_rank"] <= k
                    and not (row["baseline_rank"] is not None and row["baseline_rank"] <= k)
                    for row in rows
                ),
                "both": sum(
                    row["baseline_rank"] is not None
                    and row["baseline_rank"] <= k
                    and row["candidate_rank"] is not None
                    and row["candidate_rank"] <= k
                    for row in rows
                ),
                "neither": sum(
                    not (row["baseline_rank"] is not None and row["baseline_rank"] <= k)
                    and not (row["candidate_rank"] is not None and row["candidate_rank"] <= k)
                    for row in rows
                ),
            }
            for k in (1, 3, 5)
        },
        "failure_category_counts": category_counts,
        "failure_category_transitions": {
            f"{before}->{after}": count
            for (before, after), count in sorted(transitions.items())
        },
        "trace_supplementation_diagnostic": {
            "baseline_address_absent_rows_with_target_address_in_available_trace": sum(
                not row["baseline_address_present"] and row["target_address_in_available_trace_text"]
                for row in rows
            ),
            "baseline_address_absent_rows_recovered_by_trace_candidates": sum(
                not row["baseline_address_present"] and row["trace_augmented_address_present"]
                for row in rows
            ),
            "baseline_address_absent_rows_with_target_address_not_in_available_trace": sum(
                not row["baseline_address_present"] and not row["target_address_in_available_trace_text"]
                for row in rows
            ),
            "event_or_parameter_only_rows_not_recovered_by_call_parser": sum(
                not row["baseline_address_present"]
                and row["target_address_in_available_trace_text"]
                and not row["trace_augmented_address_present"]
                for row in rows
            ),
        },
        "input_sha256": {
            "raw_directory": _aggregate_directory_sha256(RAW_DIR),
            "ground_truth_directory": _aggregate_directory_sha256(GROUND_TRUTH_DIR),
            "classification": _sha256_file(CLASSIFICATION),
            "ranker_source": _sha256_file(ROOT / "faultseeker/function_analysis/function_ranker.py"),
        },
        "commands": [
            "python scripts/research/evaluate_localization_candidate_coverage.py",
            "python -m pytest tests/test_function_identity_normalization.py tests/test_pipeline_prediction_serialization.py tests/test_explicit_function_rank_order.py -q",
        ],
        "evidence_scope": "Saved provider-pinned 115-row population with 114 non-empty function-ground-truth rows; exploratory, not an independent held-out claim.",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_OUT.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    report["output_sha256"] = {
        "predictions_jsonl": _sha256_file(PREDICTIONS_OUT),
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    CHECKSUMS_OUT.write_text(
        json.dumps(
            {
                "predictions_jsonl": _sha256_file(PREDICTIONS_OUT),
                "report_json": _sha256_file(REPORT_OUT),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"metrics": report["metrics"], "deltas": report["deltas"], "newly_recoverable_targets": report["newly_recoverable_targets"]}, sort_keys=True))
    print(f"wrote {REPORT_OUT}")
    print(f"wrote {PREDICTIONS_OUT}")
    print(f"wrote {CHECKSUMS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
