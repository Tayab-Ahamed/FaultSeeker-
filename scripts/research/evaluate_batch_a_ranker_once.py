"""One-shot, offline exploratory ranker measurement for Batch A.

This adapter consumes the frozen local callTracer valid set and the frozen
Batch A source labels.  It converts callTracer nodes through the existing
``TransactionSequencer`` structured-trace adapter, then invokes the existing
``FunctionRanker`` once per valid trace.  No provider, RPC, or prior ranker
output is read.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import (  # noqa: E402
    _norm_addr,
    _norm_fn,
    _prediction_keys,
    _register_fn_names,
)
from faultseeker.data_collection.txn_sequencer import TransactionSequencer  # noqa: E402
from faultseeker.forensics.trace_analyzer import TraceAnalyzer  # noqa: E402
from faultseeker.function_analysis.function_ranker import FunctionRanker  # noqa: E402


VALID_SET = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
CANDIDATES = ROOT / "reports/new_batches/batchA_candidates.json"
OUTPUT = ROOT / "reports/new_batches/batchA_ranker_measurement_20261017.json"
MARKDOWN = ROOT / "reports/new_batches/batchA_ranker_measurement_20261017.md"
EXPECTED_VALID_SHA256 = "fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785"
EXPECTED_BATCH_SHA256 = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
EXPECTED_RECORD_COUNT = 23


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_batch_sha256(payload: dict[str, Any]) -> str:
    body = dict(payload)
    declared = body.pop("artifact_sha256", None)
    del declared
    return hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode()).hexdigest()


def _canonical_node(node: dict[str, Any]) -> dict[str, Any]:
    """Translate the frozen callTracer shape to TransactionSequencer's shape."""
    if not isinstance(node, dict):
        raise ValueError("trace node must be an object")
    input_data = node.get("input", "0x")
    if not isinstance(input_data, str) or not input_data.startswith("0x"):
        raise ValueError("trace node input must be a 0x-prefixed string")
    call_type = str(node.get("type") or "CALL").upper()
    callee = str(node.get("to") or "").strip()
    if not callee:
        raise ValueError("trace call is missing to")
    return {
        "callee": callee,
        "caller": str(node.get("from") or "").strip(),
        "function_selector": input_data[:10] if len(input_data) >= 10 else "0x",
        "input": input_data,
        "call_type": call_type,
        "value": node.get("value"),
        "gas": node.get("gas"),
        "gas_used": node.get("gasUsed"),
        "children": [_canonical_node(child) for child in node.get("calls", [])],
    }


def _rank_one(record: dict[str, Any]) -> list[dict[str, Any]]:
    canonical = _canonical_node(record["trace"])
    structured = {
        "transaction_hash": record["transaction_hash"],
        "chain": record["chain"],
        "trace": canonical,
    }
    txn_seq = TransactionSequencer().from_structured(structured)
    analysis = TraceAnalyzer(txn_seq, {}).run()
    if not analysis:
        raise ValueError("TraceAnalyzer returned no analysis")

    # The production ranker consumes classifier-selected candidates when they
    # exist and otherwise uses its existing function_call_loc_memo fallback.
    # This local, deterministic adapter has no classifier/provider output, so
    # it intentionally leaves that candidate map empty and does not add data.
    forensics_result = SimpleNamespace(
        address_calls_with_created_contract=analysis.get(
            "address_calls_with_created_contract_in_params", []
        ),
        functions_to_be_inspected={},
    )
    ranking = FunctionRanker().rank(
        forensics_result,
        {
            "repeated_patterns": analysis.get("repeated_patterns", {}),
            "function_call_loc_memo": analysis.get("function_call_loc_memo", {}),
        },
    )
    return [dict(item) for item in ranking.ranked_functions]


def _first_rank(predictions: list[dict[str, Any]], address: str, function: str, *, address_sensitive: bool) -> int | None:
    target_address = _norm_addr(address)
    target_function = _norm_fn(function)
    for index, prediction in enumerate(predictions, start=1):
        key, _ = _prediction_keys(prediction)
        if key is None:
            continue
        predicted_address, predicted_function = key
        if predicted_function != target_function:
            continue
        if not address_sensitive or predicted_address == target_address:
            return index
    return None


def _metric(ranks: list[int | None]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(ranks), "misses": sum(rank is None for rank in ranks)}
    for cutoff in (1, 3, 5):
        hits = sum(rank is not None and rank <= cutoff for rank in ranks)
        result[f"hits_at_{cutoff}"] = hits
        result[f"recall_at_{cutoff}"] = hits / len(ranks) if ranks else 0.0
    return result


def _markdown(result: dict[str, Any]) -> str:
    primary = result["metrics"]["primary_address_function"]
    sensitivity = result["metrics"]["function_only_sensitivity"]
    lines = [
        "# Batch A frozen-ranker measurement",
        "",
        "**Label: new measurement, exploratory**",
        "",
        "This one-shot offline measurement uses the frozen valid trace set and "
        "frozen Batch A source labels. It was not used for tuning.",
        "",
        "## Frozen inputs",
        "",
        f"- Valid set: `{result['valid_set_path']}`",
        f"- Valid-set SHA-256: `{result['valid_set_sha256']}`",
        f"- Frozen Batch A: `{result['batch_path']}`",
        f"- Frozen Batch canonical SHA-256: `{result['batch_canonical_sha256']}`",
        f"- Ranker: `{result['ranker_path']}`",
        f"- Ranker SHA-256: `{result['ranker_sha256']}`",
        "- Network/RPC/credentials: none",
        "- Prior ranker outputs: not read",
        "- Ranker invocations: 23 (exactly once per valid trace)",
        "",
        "## Metrics — new measurement, exploratory",
        "",
        "| Metric | R@1 | R@3 | R@5 | N |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Primary address+function | {primary['hits_at_1']}/{primary['n']} ({primary['recall_at_1']:.4f}) | "
        f"{primary['hits_at_3']}/{primary['n']} ({primary['recall_at_3']:.4f}) | "
        f"{primary['hits_at_5']}/{primary['n']} ({primary['recall_at_5']:.4f}) | {primary['n']} |",
        f"| Function-only sensitivity | {sensitivity['hits_at_1']}/{sensitivity['n']} ({sensitivity['recall_at_1']:.4f}) | "
        f"{sensitivity['hits_at_3']}/{sensitivity['n']} ({sensitivity['recall_at_3']:.4f}) | "
        f"{sensitivity['hits_at_5']}/{sensitivity['n']} ({sensitivity['recall_at_5']:.4f}) | {sensitivity['n']} |",
        "",
        "Address matching is case-insensitive. Function matching uses the existing "
        "localization semantics: normalized function names and the existing selector "
        "resolution table; no network lookup was performed.",
        "",
        "## Counts per chain — new measurement, exploratory",
        "",
        "| Chain | Scored rows |",
        "| --- | ---: |",
    ]
    for chain, count in sorted(result["counts_per_chain"].items()):
        lines.append(f"| {chain} | {count} |")
    lines.extend(["", "## Skipped/blocked cases", "", "- None. All 23 valid traces had a matching frozen Batch A label.", ""])
    return "\n".join(lines)


def run() -> dict[str, Any]:
    if OUTPUT.exists() or MARKDOWN.exists():
        raise SystemExit("one-shot output already exists; refusing to rerun")
    if sha256_file(VALID_SET) != EXPECTED_VALID_SHA256:
        raise SystemExit("valid-set SHA-256 mismatch")

    valid_set = json.loads(VALID_SET.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    if valid_set.get("frozen_batch", {}).get("canonical_sha256") != EXPECTED_BATCH_SHA256:
        raise SystemExit("valid set does not bind the expected frozen Batch A SHA-256")
    if candidates.get("artifact_sha256") != EXPECTED_BATCH_SHA256:
        raise SystemExit("candidate artifact declared SHA-256 mismatch")
    if canonical_batch_sha256(candidates) != EXPECTED_BATCH_SHA256:
        raise SystemExit("candidate artifact canonical SHA-256 mismatch")
    records = valid_set.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_RECORD_COUNT:
        raise SystemExit("valid-set record count/schema mismatch")

    labels = {
        str(row.get("transaction_hash", "")).lower(): row
        for row in candidates.get("rows", [])
        if isinstance(row, dict)
    }
    if len(labels) != len(candidates.get("rows", [])):
        raise SystemExit("duplicate candidate transaction hashes")
    label_names = []
    for record in records:
        tx = str(record.get("transaction_hash", "")).lower()
        label = labels.get(tx)
        if not label or not label.get("vulnerable_contract") or not label.get("vulnerable_function"):
            raise SystemExit(f"missing Batch A label for valid trace {tx}")
        if not isinstance(record.get("trace"), dict):
            raise SystemExit(f"missing trace payload for valid trace {tx}")
        label_names.append(str(label["vulnerable_function"]))
    _register_fn_names(label_names)

    row_results = []
    primary_ranks: list[int | None] = []
    function_ranks: list[int | None] = []
    for record in records:
        tx = str(record["transaction_hash"]).lower()
        label = labels[tx]
        predictions = _rank_one(record)
        primary = _first_rank(
            predictions,
            str(label["vulnerable_contract"]),
            str(label["vulnerable_function"]),
            address_sensitive=True,
        )
        function_only = _first_rank(
            predictions,
            str(label["vulnerable_contract"]),
            str(label["vulnerable_function"]),
            address_sensitive=False,
        )
        primary_ranks.append(primary)
        function_ranks.append(function_only)
        row_results.append(
            {
                "sequence": record.get("sequence"),
                "chain": record["chain"],
                "transaction_hash": tx,
                "label_address": _norm_addr(str(label["vulnerable_contract"])),
                "label_function": _norm_fn(str(label["vulnerable_function"])),
                "primary_first_hit_rank": primary,
                "function_only_first_hit_rank": function_only,
                "prediction_count": len(predictions),
                "predictions": predictions,
            }
        )

    result: dict[str, Any] = {
        "label": "new measurement, exploratory",
        "scope": "one-shot existing frozen ranker on 23 frozen Batch A valid traces",
        "valid_set_path": str(VALID_SET.relative_to(ROOT)).replace("\\", "/"),
        "valid_set_sha256": sha256_file(VALID_SET),
        "batch_path": str(CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
        "batch_canonical_sha256": EXPECTED_BATCH_SHA256,
        "ranker_path": "faultseeker/function_analysis/function_ranker.py",
        "ranker_sha256": sha256_file(ROOT / "faultseeker/function_analysis/function_ranker.py"),
        "ranker_invocations": len(records),
        "metrics": {
            "primary_address_function": _metric(primary_ranks),
            "function_only_sensitivity": _metric(function_ranks),
        },
        "counts_per_chain": dict(sorted(Counter(str(record["chain"]).lower() for record in records).items())),
        "skipped": [],
        "network_calls": False,
        "retuning": False,
        "rows": row_results,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    MARKDOWN.write_text(_markdown(result), encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUTPUT), "markdown": str(MARKDOWN), "metrics": result["metrics"], "counts_per_chain": result["counts_per_chain"]}, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
