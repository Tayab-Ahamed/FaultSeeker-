"""Render the immutable Batch B phase-2 run summary."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE = ROOT / "reports/new_batches/batchB/phase2"
LABEL = "Batch B, pre-registered, one-shot, ETH only, DeFiHackLabs-sourced"


def main() -> int:
    runs = sorted(path for path in PHASE.glob("run_*") if path.is_dir())
    run = runs[-1]
    verification = json.loads((run / "verification_summary.json").read_text(encoding="utf-8"))
    scoring = json.loads((run / "replay/scoring.json").read_text(encoding="utf-8"))
    lines = [
        "# Batch B phase 2 report",
        "",
        f"**{LABEL}**",
        "",
        "Tracing used only the configured HTTPS dRPC endpoint with one attempt per method, approximately two requests per second, and the three pre-authorized JSON-RPC methods. No publicnode, account creation, key output, retry, tuning, or partial-result peeking was used.",
        "",
        f"Frozen Batch B SHA-256: `{verification['frozen_batch_sha256']}`",
        f"Producer commit: `{verification['producer_commit']}`",
        f"Run directory: `{run.name}`",
        "",
        "## Verification",
        "",
        f"- Rows attempted: **{verification['rows_attempted']}**",
        f"- Verified: **{verification['verified_count']}**",
        f"- Excluded: **{verification['excluded_count']}**",
        f"- Paid-plan/limit stop: **{verification['paid_plan_stop']}**",
        "",
        "| Transaction | Incident | Status | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for row in verification["verification_rows"]:
        status = "verified" if row["verified"] else "excluded"
        reason = "; ".join(row["exclusion_reasons"]) or "—"
        lines.append(f"| `{row['transaction_hash'][:12]}…` | {row['incident_name']} | {status} | {reason} |")
    lines += [
        "",
        "The excluded Li.Fi trace request returned the exact dRPC error text `transaction not found`; its transaction and receipt were also not verified, so it was not scored.",
        "",
        "## One-shot replay and scoring",
        "",
        f"- Verified scoring N: **{scoring['verified_n']}**",
        f"- Producer-era ranker invocations: **{scoring['ranker_invocations']}**",
        f"- Scoring passes: **{scoring['scoring_passes']}**",
        f"- Tuning: **{scoring['tuning']}**",
        f"- Partial-result peeking: **{scoring['partial_result_peeking']}**",
        "",
        "| Key | R@1 | R@3 | R@5 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, label in (("address_selector_primary", "Address + selector (primary)"), ("address_only_sensitivity", "Address-only sensitivity"), ("selector_only_sensitivity", "Selector-only sensitivity")):
        metric = scoring["metrics"][key]
        lines.append(f"| {label} | {metric['R@1']['hits']}/{metric['R@1']['n']} ({metric['R@1']['recall']:.6f}) | {metric['R@3']['hits']}/{metric['R@3']['n']} ({metric['R@3']['recall']:.6f}) | {metric['R@5']['hits']}/{metric['R@5']['n']} ({metric['R@5']['recall']:.6f}) |")
    lines += [
        "",
        f"Candidate counts: N={scoring['candidate_counts']['n']}, min={scoring['candidate_counts']['min']}, max={scoring['candidate_counts']['max']}, mean={scoring['candidate_counts']['mean']:.6f}.",
        "",
        "| Tx prefix | Candidates | Address+selector | Address-only | Selector-only |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in scoring["rows"]:
        lines.append(f"| `{row['transaction_hash'][:12]}…` | {row['candidate_count']} | {row['address_selector_rank']} | {row['address_only_rank']} | {row['selector_only_rank']} |")
    lines += [
        "",
        "Raw responses, attempts, stderr, verification rows, and full saved candidate lists are under the run directory. No production ranker/scorer/weights, frozen Batch B data, existing results, or Batch A artifacts were modified.",
        "",
    ]
    (PHASE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
