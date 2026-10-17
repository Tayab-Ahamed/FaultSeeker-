"""Replay the producer-era original pipeline against frozen local artifacts.

This is an I/O replay harness only.  It injects the repository's existing
captured sequencer/info readers, then calls the unmodified producer-era
ForensicsOrchestrator.run and FunctionRanker.rank.  It does not construct a
ForensicsResult and does not implement candidate-building or ranking logic.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CONTROL_IDS = [
    "0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c",
    "0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa",
    "0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d",
]
MODEL = "llm-free-function-ranker"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_trace(root: Path, tx: str) -> dict[str, Any]:
    path = root / "reports/cohort_rebuild_v2/traces/eth" / f"{tx}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return load_json_from_text(handle.read())


def load_json_from_text(text: str) -> Any:
    return json.loads(text)


def replay_one(root: Path, tx: str, producer_root: Path) -> dict[str, Any]:
    # These imports intentionally resolve from the producer-era worktree.
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.function_analysis.function_ranker import FunctionRanker
    from faultseeker.utils.rpc_provider import normalize_trace_node
    from scripts.reproduce.run_original_provider_pinned import _score

    trace_path = root / "reports/cohort_rebuild_v2/traces/eth" / f"{tx}.json.gz"
    rpc_path = root / "reports/cohort_rebuild_v2/rpc/eth" / f"{tx}.json"
    gt_path = root / "benchmark/original_faultseeker/ground_truth" / f"{tx}.json"
    saved_path = root / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw" / f"{tx}.json"

    captured = load_trace(root, tx)
    rpc = load_json(rpc_path)
    call = captured["raw_trace"]["call"]
    canonical = normalize_trace_node(call)
    opcode = captured["raw_trace"].get("opcode", {})
    struct_logs = opcode.get("structLogs")
    storage = normalize_opcode_storage_trace(struct_logs, canonical) if isinstance(struct_logs, list) else {}
    structured = {
        "transaction_hash": tx,
        "chain": captured["chain"],
        "trace": canonical,
        "storage_events": storage.get("storage_events", []),
        "storage_reads": storage.get("storage_reads", []),
        "state_diff": {},
        "trace_coverage": {
            "trace_complete": True,
            "storage_trace_complete": isinstance(struct_logs, list),
            "token_flow_complete": False,
            "multi_tx_context_complete": False,
        },
    }
    sequencer = _CapturedSequencer(structured)
    info = _CapturedInfo(rpc["transaction"], rpc["receipt"], tx, captured["chain"])

    # This is the exact producer call path.  No adapter-side candidate or
    # ForensicsResult construction occurs here.
    orchestrator = ForensicsOrchestrator(
        model=MODEL,
        txn_sequencer=sequencer,
        txn_info_collector=info,
    )
    result, _txn_seq, _txn_info = orchestrator.run(tx, captured["chain"])
    tx_analysis = {
        "repeated_patterns": result.repeated_patterns,
        "function_call_loc_memo": result.function_call_loc_memo,
    }
    predictions = [dict(item) for item in FunctionRanker().rank(result, tx_analysis).ranked_functions]
    scored = _score(gt_path, predictions)
    saved = load_json(saved_path)
    return {
        "transaction_hash": tx,
        "chain": captured["chain"],
        "trace_artifact": str(trace_path.relative_to(root)).replace("\\", "/"),
        "rpc_artifact": str(rpc_path.relative_to(root)).replace("\\", "/"),
        "ground_truth_artifact": str(gt_path.relative_to(root)).replace("\\", "/"),
        "saved_artifact": str(saved_path.relative_to(root)).replace("\\", "/"),
        "saved_rank": saved.get("score", {}).get("first_hit_rank"),
        "original_entrypoint_rank": scored.get("first_hit_rank"),
        "saved_candidate_count": len(saved.get("predictions", [])),
        "original_entrypoint_candidate_count": len(predictions),
        "rank_reproduced": saved.get("score", {}).get("first_hit_rank") == scored.get("first_hit_rank"),
        "prediction_sha256": hashlib.sha256(json.dumps(predictions, sort_keys=True).encode()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    producer_root = args.producer_root.resolve()
    if not (producer_root / ".git").exists() and not (producer_root / ".git").is_file():
        raise SystemExit(f"producer worktree not found: {producer_root}")
    if str(producer_root) not in sys.path:
        sys.path.insert(0, str(producer_root))

    rows = [replay_one(root, tx, producer_root) for tx in CONTROL_IDS]
    result = {
        "status": "COMPLETE",
        "label": "post-diagnostic, exploratory",
        "producer_commit": "1b1c7395771663622dd14b9731b4b8b471221960",
        "producer_entrypoint": "scripts/reproduce/run_original_provider_pinned.py",
        "orchestrator_call": "ForensicsOrchestrator(model=MODEL, captured I/O).run(tx_hash, chain)",
        "rank_call": "FunctionRanker().rank(result, {'repeated_patterns': result.repeated_patterns, 'function_call_loc_memo': result.function_call_loc_memo})",
        "model": MODEL,
        "network_calls": False,
        "custom_adapter": False,
        "manual_forensics_result": False,
        "rows": rows,
        "all_ranks_reproduced": all(row["rank_reproduced"] for row in rows),
    }
    out = Path(__file__).resolve().parent
    (out / "original_entrypoint_controls.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# Original-entrypoint control replay",
        "",
        "**Label: post-diagnostic, exploratory**",
        "",
        f"Producer commit: `{result['producer_commit']}`",
        "",
        "| Control | Saved rank | Original-entrypoint rank | Saved candidates | Original candidates | Reproduced |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['transaction_hash']}` | {row['saved_rank']} | {row['original_entrypoint_rank']} | "
            f"{row['saved_candidate_count']} | {row['original_entrypoint_candidate_count']} | {row['rank_reproduced']} |"
        )
    (out / "original_entrypoint_controls.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_ranks_reproduced"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
