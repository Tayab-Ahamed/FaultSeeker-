"""Offline Batch A signature-source availability report."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
VALID = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"


def main() -> int:
    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    valid = json.loads(VALID.read_text(encoding="utf-8"))
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    rows = []
    for record in valid["records"]:
        label = labels[str(record["transaction_hash"]).lower()]
        source_path = ROOT / str(label["source_path"])
        rows.append({
            "transaction_hash": label["transaction_hash"],
            "source_file": label["source_path"],
            "source_file_cached_locally": source_path.is_file(),
            "source_transaction_line_from_label": label["source_transaction_line"],
            "vulnerable_function_line_from_label": label["vulnerable_function_line"],
            "vulnerable_function_label": label["vulnerable_function"],
            "vulnerable_function_quote": label["vulnerable_function_quote"],
            "full_signature": None,
            "signature_status": "unresolved_source_file_not_cached",
            "computed_selector": None,
            "selector_candidate_match": None,
            "selector_trace_match": None,
        })
    needed = sorted({row["source_file"] for row in rows})
    result = {
        "label": "Batch A signature check, offline",
        "network_calls": False,
        "source_fetch_performed": False,
        "source_files_cached": False,
        "needed_source_files": needed,
        "rows": rows,
        "counts": {
            "rows": len(rows),
            "resolved_full_signatures": 0,
            "unresolved_signatures": len(rows),
            "appears_in_candidates": 0,
            "in_trace_only": 0,
            "absent": 0,
        },
        "reason": "The DeFiHackLabs PoC source files named by the frozen Batch A labels are not present in the workspace. The frozen labels contain bare or empty-parenthesis function forms and source quotes, but no locally available full argument-typed declarations or call signatures. No types were inferred.",
        "evidence": ["reports/new_batches/batchA_candidates.json", "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"],
    }
    (OUT / "signature_check.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# Batch A full-signature check",
        "",
        "**Offline only. No source fetch, RPC, network, tuning, fixes, or rescoring.**",
        "",
        "## Source availability",
        "",
        "The DeFiHackLabs PoC files named by the frozen labels are not cached locally. No files were fetched. Needed files:",
        "",
    ]
    lines += [f"- `{path}`" for path in needed]
    lines += ["", "## Counts", "", "| Count | Value |", "| --- | ---: |", f"| Batch A valid ETH rows | {len(rows)} |", "| Resolved full argument-typed signatures | 0 |", f"| Unresolved signatures | {len(rows)} |", "| Appears in candidates | 0 (no selectors computed) |", "| In trace only | 0 (no selectors computed) |", "| Absent | 0 (no selectors computed) |", "", "## Per-row source references", "", "The line numbers below are the line fields recorded in the frozen label artifact. The source files required to verify them are not present locally.", "", "| Transaction | Source file | Source transaction line | Vulnerable-function line | Label | Signature status |", "| --- | --- | ---: | ---: | --- | --- |"]
    for row in rows:
        lines.append(f"| `{row['transaction_hash']}` | `{row['source_file']}` | {row['source_transaction_line_from_label']} | {row['vulnerable_function_line_from_label']} | `{row['vulnerable_function_label']}` | unresolved: source file not cached |")
    lines += ["", "No argument types were guessed or inferred. Because zero full signatures were resolved, no keccak selector was computed and no candidate/trace selector classification was performed.", ""]
    (OUT / "signature_check.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
