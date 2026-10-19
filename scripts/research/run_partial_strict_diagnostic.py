"""Run a clearly labelled diagnostic on the currently available strict rows.

The original paper target is not evaluated here: the repository has only 14
strict rows, one of which lacks a retained call trace.  This runner overlays
features recovered by ``audit_missing_exploit_features.py`` onto the 13
trace-complete rows, keeps the fourteenth excluded, and invokes the existing
leakage-safe honest harness against the matched 1,000-row benign trace set.
The output is a partial diagnostic, never a 246-row paper result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.features import load_exploit_rows
from benchmark import run_honest_experiments as honest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audit",
        type=Path,
        default=ROOT / "reports/reproducibility/MISSING_EXPLOIT_FEATURE_AUDIT.json",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "reports/reproducibility/partial_strict_diagnostic",
    )
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    recovered = {
        row["transaction_hash"]: row["derived_features"]
        for row in audit["rows"]
        if row["status"] == "DERIVED_FROM_RETAINED_CALL_TRACE"
    }
    exploit_rows = load_exploit_rows()
    for row in exploit_rows:
        features = recovered.get(row.txn_hash)
        if features:
            row.features.update(features)

    # The existing harness contains the leakage guard, OOF calibration, CIs,
    # and all scorers.  Replace only its exploit-row loader in memory; no source
    # CSV or frozen artifact is changed.
    honest.load_exploit_rows = lambda: exploit_rows
    sys.argv = [
        "run_honest_experiments.py",
        "--results-dir",
        str(args.results_dir),
    ]
    exit_code = honest.main()

    status_path = args.results_dir / "status.json"
    if status_path.is_file():
        harness_status = json.loads(status_path.read_text(encoding="utf-8"))
        harness_status["publication_scope"] = "PARTIAL_DIAGNOSTIC_ONLY"
        harness_status["publishable_for_original_246_row_claim"] = False
        status_path.write_text(json.dumps(harness_status, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "schema_version": 1,
        "status": "PARTIAL_DIAGNOSTIC_NOT_PAPER_RESULT",
        "original_target": "246-row detector F1/FPR",
        "strict_rows_loaded": len(exploit_rows),
        "strict_rows_with_recovered_trace_features": len(recovered),
        "excluded_strict_rows": [
            row["transaction_hash"]
            for row in audit["rows"]
            if row["status"] != "DERIVED_FROM_RETAINED_CALL_TRACE"
        ],
        "benign_source": "benchmark/imported/benign_traces.csv via honest harness",
        "denominator_policy": "13 trace-complete strict rows + 1000 benign traces; no padding and no promotion to original claim",
        "harness_exit_code": exit_code,
        "external_calls": 0,
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "diagnostic_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
