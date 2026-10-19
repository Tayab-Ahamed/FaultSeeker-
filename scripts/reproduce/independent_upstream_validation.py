"""Independently calculate the reproducible part of the upstream evaluation.

This command is deliberately narrower than the upstream paper.  It reads the
byte-preserved 115-row benchmark, ground-truth files, and the retained
provider-pinned ranker outputs.  It does not contact RPCs, invoke the upstream
ranker, call an LLM, or infer missing predictions.  Failed provider rows stay
in the requested 115-row denominator as zero hits; a second valid-trace view is
also reported for transparency.

The command additionally emits a claim-by-claim comparison assembled from the
existing claim ledger.  The ledger status is not upgraded by the diagnostic
calculation: the retained outputs are an independent calculation on a
partially successful LLM-free run, not an exact reproduction of the paper's
multi-agent evaluation.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reproduce.audit_original_scorer_strictness import (  # noqa: E402
    GT_DIR,
    RAW_DIR,
    current_hit,
    load_valid_rows,
    original_function_only_hit,
)


CLASSIFICATION = ROOT / "benchmark/original_faultseeker/benchmark_classification.csv"
RUN_MANIFEST = RAW_DIR.parent / "manifest.json"
CLAIM_LEDGER = ROOT / "reports/claim_closure/local_snapshot/claim_ledger.json"
OUTPUT_DIR = ROOT / "reports/reproducibility/upstream_validation"
PER_EXAMPLE = OUTPUT_DIR / "localization_per_example.jsonl"
RESULT_JSON = OUTPUT_DIR / "claim_comparison.json"
RESULT_MD = OUTPUT_DIR / "CLAIM_COMPARISON.md"
INPUT_MANIFEST = OUTPUT_DIR / "input_manifest.json"

PUBLISHED_LOCALIZATION = {
    "recall_at_1": {"percentage": 50.43, "hits_inferred_from_reported_percentage": 58, "denominator": 115},
    "recall_at_3": {"percentage": 73.91, "hits_inferred_from_reported_percentage": 85, "denominator": 115},
    "recall_at_5": {"percentage": 76.52, "hits_inferred_from_reported_percentage": 88, "denominator": 115},
}


# The upstream PDF is not present in this working tree.  These locations are
# stable paper-level references, while the URL and pinned source commit bind
# the external source that was inspected for the reconstruction.
UPSTREAM_SOURCE = {
    "repository": "https://github.com/kairanskrr/FaultSeeker",
    "commit": "72753bd833554449efa8499f0d1775a97fb5c696",
    "paper_pdf": "full_paper/FaultSeeker LLM-Empowered Framework for Blockchain Transaction.pdf",
}


CLAIM_SOURCE_LOCATIONS = {
    1: "upstream repository README/license; publication claim",
    2: "upstream repository benchmark/tests and current reproduction entrypoint",
    3: "upstream paper dataset description; 246-row cohort claim",
    4: "upstream paper dataset methodology; transaction/source/annotation claim",
    5: "upstream paper dataset distribution; ten chains and Ethereum share",
    6: "upstream paper vulnerability taxonomy/dataset description",
    7: "upstream paper dataset class-distribution paragraph",
    8: "upstream paper dataset reentrancy-count paragraph",
    9: "current paper Sections IV/VI; storage-aware detector implementation claim",
    10: "current paper detector design; storage signal weights",
    11: "current paper confidence-tier design",
    12: "current paper fallback/structural detector design",
    13: "upstream paper empirical detector-results table; precision/recall/F1",
    14: "upstream paper paired baseline-gain result",
    15: "upstream paper Compound case-study section",
    16: "current paper query-routing design and theta gate",
    17: "upstream paper provider/model configuration claim",
    18: "upstream paper runtime/cost and 100-transaction study claim",
    19: "current paper Stage 1 architecture",
    20: "current paper control-flow/routing design",
    21: "upstream paper benign prefilter and latency result",
    22: "upstream paper function-localization result and multi-agent architecture",
    23: "current paper Equation 4 confidence scoring",
    24: "current paper evidence-card/HITL design",
    25: "current paper RPC resilience design",
    26: "current paper replay/storage extraction implementation",
    27: "upstream paper WAF recovery result",
    28: "upstream paper Table VI category averages",
    29: "upstream paper simulated-guidance result",
    30: "upstream paper reproducibility claim and artifact availability",
    31: "current repository runtime/reproducibility package",
}


CLAIM_PUBLISHED = {
    3: {"target_rows": 246, "accepted_rows_reported": 246},
    5: {"target_chains": 10, "ethereum_share_pct": 47.6, "denominator": 246},
    6: {"label_count": ">80", "denominator": 246},
    7: {"class_percentages": [6.5, 33.3, 32.5, 27.6], "denominator": 246},
    8: {"reentrant_rows": 18, "denominator": 246},
    13: {"metric": "precision/recall/F1 and baselines", "denominator": "paper evaluation cohort; exact integer confusion counts unavailable"},
    14: {"gain_percentage_points": [17, 29], "denominator": "paired paper evaluation cohort"},
    18: {"cost_saving_pct": 58, "study_transactions": 100, "tier_mix": "50/30/20"},
    21: {"benign_prefilter_pct": 40, "latency_reduction": "reported with prefilter study", "denominator": "paper production workload"},
    22: {"metric": "Recall@1/3/5 function localization", "published_values": PUBLISHED_LOCALIZATION, "denominator": 115},
    27: {"waf_recovery_pct": 23, "denominator": "authorized challenge sample not retained"},
    28: {"metric": "Table VI category averages", "denominator": "paper study categories"},
    29: {"before_pct": 68, "after_pct": 81, "study_transactions": 20},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_lf(path: Path, text: str) -> None:
    """Write deterministic LF bytes on Windows and Linux."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def load_classification() -> list[dict[str, str]]:
    with CLASSIFICATION.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["txn_hash"].strip().lower() for row in rows]
    if len(rows) != 115 or len(set(ids)) != len(ids):
        raise AssertionError(f"classification must contain 115 unique rows, got {len(rows)}")
    return rows


def _raw_function(prediction: dict[str, Any]) -> str:
    return str(
        prediction.get("function_name")
        or prediction.get("name")
        or prediction.get("function")
        or ""
    ).strip().split("(")[0].lower()


def first_raw_function_rank(
    predictions: list[dict[str, Any]], expected_functions: set[str]
) -> int | None:
    """Return the first list position; stable ties follow retained list order."""
    for position, prediction in enumerate(predictions, start=1):
        if _raw_function(prediction) in expected_functions:
            return position
    return None


def validate_evaluation_rows(rows: Iterable[dict[str, Any]], denominator: int) -> None:
    rows = list(rows)
    ids = [str(row.get("txn_hash") or "").lower() for row in rows]
    if len(rows) != denominator:
        raise ValueError(f"denominator mismatch: expected {denominator}, got {len(rows)}")
    if any(not row_id for row_id in ids):
        raise ValueError("missing transaction identity")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate transaction identity")
    if any(not row.get("ground_truth_functions") for row in rows):
        raise ValueError("missing ground-truth function label")


def aggregate_ranks(rows: Iterable[dict[str, Any]], denominator: int) -> dict[str, Any]:
    rows = list(rows)
    validate_evaluation_rows(rows, denominator)
    result = {"n": len(rows), "hits": {}, "recall": {}}
    for k in (1, 3, 5):
        hits = sum(row["first_hit_rank"] is not None and row["first_hit_rank"] <= k for row in rows)
        result["hits"][f"recall_at_{k}"] = hits
        result["recall"][f"recall_at_{k}"] = round(hits / denominator, 8)
    return result


def _target_functions(txn_hash: str) -> set[str]:
    data = json.loads((GT_DIR / f"{txn_hash}.json").read_text(encoding="utf-8-sig"))
    functions = set()
    for key, values in (data.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parts = str(entry).split("#")
            if len(parts) >= 3:
                member = parts[-1].strip()
                if member and ":" not in member:
                    functions.add(member.split("(")[0].strip().lower())
    if not functions:
        raise ValueError(f"no function-level ground truth for {txn_hash}")
    return functions


def build_localization_rows(classification: list[dict[str, str]]) -> list[dict[str, Any]]:
    valid_by_id = {txn: (row, target, labels) for txn, row, target, labels in load_valid_rows()}
    output = []
    for source in classification:
        txn = source["txn_hash"].strip().lower()
        raw_path = RAW_DIR / f"{txn}.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        functions = sorted(_target_functions(txn))
        predictions = raw.get("predictions") or []
        if raw.get("status") == "ok":
            _saved, target, _labels = valid_by_id[txn]
            current_rank = next(
                (k for k in range(1, len(predictions) + 1) if current_hit(target, predictions, k)), None
            )
            original_rank = first_raw_function_rank(predictions, set(functions))
        else:
            current_rank = None
            original_rank = None
        output.append({
            "txn_hash": txn,
            "chain": source["chain"],
            "status": raw.get("status"),
            "provider": raw.get("provider"),
            "failure_kind": raw.get("failure_kind"),
            "replay_mismatch": bool(raw.get("replay_mismatch")),
            "ground_truth_functions": functions,
            "prediction_count": len(predictions),
            "current_scorer_first_hit_rank": current_rank,
            "original_function_only_first_hit_rank": original_rank,
            "first_hit_rank": original_rank,
        })
    return output


def input_manifest() -> dict[str, Any]:
    files = [CLASSIFICATION, RUN_MANIFEST]
    files.extend(sorted(GT_DIR.glob("*.json")))
    files.extend(sorted(RAW_DIR.glob("*.json")))
    return {
        "repository": UPSTREAM_SOURCE,
        "files": {path.relative_to(ROOT).as_posix(): sha256(path) for path in files},
        "classification_rows": 115,
        "ground_truth_files": len(list(GT_DIR.glob("*.json"))),
        "raw_result_files": len(list(RAW_DIR.glob("*.json"))),
    }


def _claim_rows(localization: dict[str, Any]) -> list[dict[str, Any]]:
    ledger = json.loads(CLAIM_LEDGER.read_text(encoding="utf-8"))
    rows = []
    for claim in sorted(ledger["claims"], key=lambda item: item["id"]):
        claim_id = claim["id"]
        independent = None
        if claim_id == 3:
            independent = {"root_accepted": 14, "root_target": 246, "v4_accepted": 22, "v4_target": 246}
        elif claim_id == 5:
            independent = {"historical_csv_rows": 231, "historical_csv_chains": 8, "historical_eth_rows": 132}
        elif claim_id == 6:
            independent = {"historical_distinct_nonempty_vulnerability_strings": 82, "semantic_adjudication": False}
        elif claim_id == 8:
            independent = {"historical_reentrancy_substring_rows": 17, "target_cohort": 246}
        elif claim_id == 13:
            independent = {"historical_proxy_f1": 0.7586, "scope": "saved aggregate; not authenticated cohort"}
        elif claim_id == 18:
            independent = {"modeled_cost_reduction_pct": 35.0, "measured_100_case_runs": 0}
        elif claim_id == 22:
            independent = localization
        elif claim_id == 26:
            independent = {"historical_replay_samples": 2, "cohort_scale": False}
        rows.append({
            "id": claim_id,
            "original_claim": claim["paper_wording"],
            "source_location": CLAIM_SOURCE_LOCATIONS[claim_id],
            "published_metric": CLAIM_PUBLISHED.get(claim_id),
            "published_denominator": (CLAIM_PUBLISHED.get(claim_id) or {}).get("denominator"),
            "independent_calculation": independent,
            "evidence_references": claim.get("existing_artifacts", []),
            "status": claim["status"],
            "exact_evidence_required_to_change_status": claim.get("missing_prerequisites") or [claim["required_evidence"]],
            "ledger_verdict": claim.get("verification_result", {}).get("paper_verdict"),
        })
    for row in rows:
        if row["id"] in (13, 22):
            row["evidence_references"] += [
                "reports/reproducibility/upstream_validation/localization_per_example.jsonl",
                "reports/reproducibility/upstream_validation/claim_comparison.json",
            ]
    return rows


def write_markdown(result: dict[str, Any]) -> None:
    lines = [
        "# Independent upstream validation",
        "",
        "This is an independent calculation from retained upstream benchmark labels and provider-pinned LLM-free ranker outputs. It is not an exact reproduction of the paper's multi-agent run.",
        "",
        "## Localization calculation",
        "",
        "| View | Denominator | R@1 | R@3 | R@5 | Scope |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, metrics in result["localization"]["independent_localization"].items():
        lines.append(
            f"| {name} | {metrics['n']} | {metrics['hits']['recall_at_1']}/{metrics['n']} ({metrics['recall']['recall_at_1']:.4f}) | "
            f"{metrics['hits']['recall_at_3']}/{metrics['n']} ({metrics['recall']['recall_at_3']:.4f}) | "
            f"{metrics['hits']['recall_at_5']}/{metrics['n']} ({metrics['recall']['recall_at_5']:.4f}) | retained outputs |"
        )
    lines += [
        "",
        "## Evaluation reconstruction",
        "",
        "The upstream README defines a 115-transaction ranked-function task. The pinned upstream ranker filters common safe functions, keys candidates by function plus address, deduplicates repeated calls by depth, and sorts by count. No standalone upstream scorer, original per-example prediction file, original model transcript, complete trace/source bundle, or baseline/ablation output was available. Therefore the calculation below is bounded to the retained 110 successful LLM-free outputs plus five explicit failures.",
        "",
        "Published upstream Table II values are 50.43%, 73.91%, and 76.52% on 115 transactions. Their implied integer hits are 58/115, 85/115, and 88/115. The retained independent function-only calculation produces 27/115, 49/115, and 53/115 because five rows failed and the 110 successful rows are LLM-free ranker outputs. This is an independent calculation, not an exact reproduction.",
        "",
        "## Claim comparison",
        "",
        "| ID | Claim | Status | Independent evidence | Required change |",
        "|---:|---|---|---|---|",
    ]
    for claim in result["claims"]:
        independent = json.dumps(claim["independent_calculation"], sort_keys=True) if claim["independent_calculation"] is not None else "—"
        required = "; ".join(claim["exact_evidence_required_to_change_status"])
        lines.append(f"| {claim['id']} | {claim['original_claim']} | `{claim['status']}` | {independent} | {required} |")
    lines += [
        "",
        "## Provenance and limits",
        "",
        f"- Upstream source commit: `{UPSTREAM_SOURCE['commit']}`.",
        "- Imported classification and ground-truth files are byte-preserved copies of the upstream benchmark.",
        "- Failed rows remain in the 115-row denominator; valid-trace-only views are reported separately.",
        "- No RPC, provider, LLM, or upstream rerun was performed by this calculation.",
        "- Missing original scorer configuration, original predictions, and multi-agent transcripts prevent exact paper reproduction.",
    ]
    write_lf(RESULT_MD, "\n".join(lines) + "\n")


def main() -> int:
    classification = load_classification()
    rows = build_localization_rows(classification)
    validate_evaluation_rows(
        [{"txn_hash": row["txn_hash"], "ground_truth_functions": row["ground_truth_functions"], "first_hit_rank": row["first_hit_rank"]} for row in rows],
        115,
    )
    current_rows = [dict(row, first_hit_rank=row["current_scorer_first_hit_rank"]) for row in rows]
    original_all = aggregate_ranks(rows, 115)
    current_all = aggregate_ranks(current_rows, 115)
    valid_rows = [row for row in rows if row["status"] == "ok"]
    original_valid = aggregate_ranks(valid_rows, 110)
    current_valid = aggregate_ranks([dict(row, first_hit_rank=row["current_scorer_first_hit_rank"]) for row in valid_rows], 110)
    localization = {
        "published_upstream_table_ii": PUBLISHED_LOCALIZATION,
        "independent_localization": {
            "original_function_only_all_115": original_all,
            "current_address_aware_all_115": current_all,
            "original_function_only_valid_110": original_valid,
            "current_address_aware_valid_110": current_valid,
        },
        "exact_reproduction": False,
        "independent_calculation": True,
        "failure_count": sum(row["status"] != "ok" for row in rows),
        "replay_mismatch_count": sum(row["replay_mismatch"] for row in rows),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with PER_EXAMPLE.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = input_manifest()
    write_lf(INPUT_MANIFEST, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    result = {
        "schema_version": 1,
        "status": "INDEPENDENT_CALCULATION_NOT_EXACT_REPRODUCTION",
        "upstream": UPSTREAM_SOURCE,
        "inputs": {
            "classification": CLASSIFICATION.relative_to(ROOT).as_posix(),
            "ground_truth": GT_DIR.relative_to(ROOT).as_posix(),
            "raw_results": RAW_DIR.relative_to(ROOT).as_posix(),
            "run_manifest": RUN_MANIFEST.relative_to(ROOT).as_posix(),
        },
        "evaluation_reconstruction": {
            "task": "ranked function localization",
            "upstream_benchmark_transactions": 115,
            "ground_truth_files": 115,
            "published_metric": "Recall@1, Recall@3, Recall@5",
            "published_denominator": 115,
            "published_values": PUBLISHED_LOCALIZATION,
            "upstream_ranker_observations": [
                "filters common read-only and standard token functions",
                "keys function candidates by function plus address",
                "deduplicates repeated calls by depth",
                "sorts retained candidates by count descending",
            ],
            "missing_for_exact_reproduction": [
                "standalone upstream scorer/evaluator implementation",
                "original per-example predictions and ranking files",
                "original model/provider configuration and transcripts",
                "complete trace/source acquisition inputs for all 115 rows",
                "original baseline and ablation outputs",
            ],
            "available_calculation": "retained provider-pinned LLM-free ranker outputs; 110 status=ok and 5 failed rows",
        },
        "input_manifest": INPUT_MANIFEST.relative_to(ROOT).as_posix(),
        "localization": localization,
        "claims": _claim_rows(localization),
        "per_example": PER_EXAMPLE.relative_to(ROOT).as_posix(),
        "script_sha256": sha256(Path(__file__)),
    }
    write_lf(RESULT_JSON, json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_markdown(result)
    print(json.dumps(localization, indent=2, sort_keys=True))
    print(f"wrote {RESULT_JSON}")
    print(f"wrote {RESULT_MD}")
    print(f"wrote {PER_EXAMPLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
