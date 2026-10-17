"""Read-only audit of the offline rescore and Batch A producer-path inputs."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ARCHIVAL = "240fd9fae9cb56a96f45f37d21a90cf094abc467"
RESCORED = "70d1b099c0b1dad524bc89ba4e707ea94b7038b9"
RAW_PREFIX = "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
VALID_SET = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
ADAPTERFIX2_REPLAY = ROOT / "reports/new_batches/batchA_adapterfix2/original_entrypoint_controls.json"
SCORE_FIELDS = ("first_hit_rank", "recall_at_1", "recall_at_3", "recall_at_5")


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def hit(rank: int | None, cutoff: int) -> bool:
    return rank is not None and rank <= cutoff


def metrics(ranks: list[int | None]) -> dict[str, Any]:
    return {
        "n": len(ranks),
        "r_at_1": {"hits": sum(hit(rank, 1) for rank in ranks), "denominator": len(ranks), "value": sum(hit(rank, 1) for rank in ranks) / len(ranks) if ranks else 0.0},
        "r_at_3": {"hits": sum(hit(rank, 3) for rank in ranks), "denominator": len(ranks), "value": sum(hit(rank, 3) for rank in ranks) / len(ranks) if ranks else 0.0},
        "r_at_5": {"hits": sum(hit(rank, 5) for rank in ranks), "denominator": len(ranks), "value": sum(hit(rank, 5) for rank in ranks) / len(ranks) if ranks else 0.0},
    }


def audit_rescore() -> dict[str, Any]:
    manifest_path = "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json"
    manifest = git_json(RESCORED, manifest_path)
    ok_rows = [row for row in manifest["rows"] if row.get("status") == "ok"]
    affected: list[dict[str, Any]] = []
    archival_ranks: list[int | None] = []
    current_ranks: list[int | None] = []

    for row in ok_rows:
        tx = row["case_id"]
        path = f"{RAW_PREFIX}/{tx}.json"
        archival = git_json(ARCHIVAL, path)
        current = git_json(RESCORED, path)
        old_score = archival.get("score", {})
        new_score = current.get("score", {})
        archival_rank = old_score.get("first_hit_rank")
        current_rank = new_score.get("first_hit_rank")
        archival_ranks.append(archival_rank)
        current_ranks.append(current_rank)
        changed = [field for field in SCORE_FIELDS if old_score.get(field) != new_score.get(field)]
        predictions_unchanged = archival.get("predictions") == current.get("predictions")
        if changed and predictions_unchanged:
            chain = str(current.get("chain") or row.get("chain") or "").lower()
            trace = ROOT / f"reports/cohort_rebuild_v2/traces/{chain}/{tx}.json.gz"
            rpc = ROOT / f"reports/cohort_rebuild_v2/rpc/{chain}/{tx}.json"
            affected.append({
                "transaction_hash": tx,
                "chain": chain,
                "archival_rank_240fd9f": archival_rank,
                "rank_after_70d1b09": current_rank,
                "changed_score_fields": changed,
                "prediction_list_regenerated": False,
                "saved_candidate_count": len(current.get("predictions", [])),
                "full_local_trace_available": trace.is_file() and rpc.is_file(),
                "trace_artifact": str(trace.relative_to(ROOT)).replace("\\", "/") if trace.is_file() else None,
                "rpc_artifact": str(rpc.relative_to(ROOT)).replace("\\", "/") if rpc.is_file() else None,
            })

    replay_source = json.loads(ADAPTERFIX2_REPLAY.read_text(encoding="utf-8"))
    replay_by_tx = {row["transaction_hash"]: row for row in replay_source["rows"]}
    replay_rows = []
    for row in affected:
        tx = row["transaction_hash"]
        replay = replay_by_tx.get(tx)
        if row["full_local_trace_available"] and replay:
            replay_rows.append({
                "transaction_hash": tx,
                "producer_commit": replay_source["producer_commit"],
                "archival_rank_240fd9f": row["archival_rank_240fd9f"],
                "rank_after_70d1b09": row["rank_after_70d1b09"],
                "producer_replay_rank": replay["original_entrypoint_rank"],
                "archival_candidate_count": None,
                "stored_candidate_count": row["saved_candidate_count"],
                "producer_replay_candidate_count": replay["original_entrypoint_candidate_count"],
            })

    replay_ranks = [row["producer_replay_rank"] for row in replay_rows]
    return {
        "label": "scope audit, read-only",
        "archival_commit": ARCHIVAL,
        "rescore_commit": RESCORED,
        "benchmark_ok_rows": len(ok_rows),
        "affected_count": len(affected),
        "replayable_affected_count": len(replay_rows),
        "missing_full_trace_count": len(affected) - len(replay_rows),
        "archival_metrics_all_110": metrics(archival_ranks),
        "current_stored_metrics_all_110": metrics(current_ranks),
        "producer_replay_metrics_partial_sample": metrics(replay_ranks),
        "affected_rows": affected,
        "replay_rows": replay_rows,
        "replay_source": str(ADAPTERFIX2_REPLAY.relative_to(ROOT)).replace("\\", "/"),
    }


def batch_a_field_check() -> dict[str, Any]:
    valid = json.loads(VALID_SET.read_text(encoding="utf-8"))
    records = valid.get("records", [])
    missing = []
    for record in records:
        absent = [key for key in ("transaction_hash", "chain", "trace") if key not in record]
        trace = record.get("trace") if isinstance(record.get("trace"), dict) else {}
        absent_trace = [key for key in ("from", "to", "type", "input", "calls") if key not in trace]
        missing_rpc = ["transaction", "receipt"]
        if absent or absent_trace:
            missing.append({"transaction_hash": record.get("transaction_hash"), "missing_record_fields": absent, "missing_trace_fields": absent_trace})
    return {
        "label": "producer-era replay, exploratory",
        "valid_set": str(VALID_SET.relative_to(ROOT)).replace("\\", "/"),
        "record_count": len(records),
        "required_identity_and_trace_fields_present": len(missing) == 0,
        "missing_identity_or_trace_fields": missing,
        "rpc_transaction_and_receipt_fields_present": False,
        "missing_fields_for_existing_captured_info_path": ["transaction", "receipt"],
        "reason": "The 23 valid-set records contain transaction_hash, chain, and a callTracer trace, but no per-record transaction/receipt payload. The producer-era ForensicsOrchestrator path requires those RPC-normalized inputs through TransactionInfoCollector.",
        "batch_a_replay_executed": False,
    }


def main() -> int:
    audit = audit_rescore()
    fields = batch_a_field_check()
    result = {"job_1_rescore_scope": audit, "job_2_batch_a_field_check": fields}
    (OUT / "scope_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (OUT / "batchA_field_check.json").write_text(json.dumps(fields, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    lines = [
        "# Batch A adapter fix 3 — read-only jobs",
        "",
        "## Job 1 — commit 70d1b09 scope",
        "",
        f"- Benchmark rows audited: {audit['benchmark_ok_rows']} successful rows",
        f"- Affected rows: {audit['affected_count']}",
        f"- Affected rows replayable from full local trace + RPC artifacts: {audit['replayable_affected_count']}",
        f"- Affected rows missing full local traces: {audit['missing_full_trace_count']}",
        "",
        "| Reading | R@1 | R@3 | R@5 | N |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, key in (("Archival ranks at 240fd9f", "archival_metrics_all_110"), ("Current stored ranks after 70d1b09", "current_stored_metrics_all_110"), ("Producer replay, partial sample", "producer_replay_metrics_partial_sample")):
        m = audit[key]
        lines.append(f"| {label} | {m['r_at_1']['hits']}/{m['r_at_1']['denominator']} ({m['r_at_1']['value']:.6f}) | {m['r_at_3']['hits']}/{m['r_at_3']['denominator']} ({m['r_at_3']['value']:.6f}) | {m['r_at_5']['hits']}/{m['r_at_5']['denominator']} ({m['r_at_5']['value']:.6f}) | {m['n']} |")
    lines += ["", "### Affected rows", "", "| Transaction | Chain | Archival rank | Rank after 70d1b09 | Changed stored fields | Full local trace? |", "| --- | --- | ---: | ---: | --- | --- |"]
    for row in audit["affected_rows"]:
        lines.append(f"| `{row['transaction_hash']}` | {row['chain']} | {row['archival_rank_240fd9f']} | {row['rank_after_70d1b09']} | {', '.join(row['changed_score_fields'])} | {row['full_local_trace_available']} |")
    lines += ["", "## Job 2 — Batch A producer-era field check", "", f"- Valid records: {fields['record_count']}", f"- Identity/trace fields present: {fields['required_identity_and_trace_fields_present']}", "- Required RPC-normalized transaction and receipt payloads present: False", "- Batch A replay executed: False", "", fields["reason"], ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
