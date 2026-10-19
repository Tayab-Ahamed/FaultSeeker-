"""Run the leakage-safe harness on the retained 115-row legacy cohort.

The 115-row source/ground-truth population is complete for its own historical
scope and has all four trace features.  It is not the current authenticated
246-row cohort and must not be presented as that target.  This diagnostic is
useful for measuring the current scorer on a fully trace-comparable local
population without modifying the strict cohort or frozen batches.
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
        "--results-dir",
        type=Path,
        default=ROOT / "reports/reproducibility/legacy_115_diagnostic",
    )
    args = parser.parse_args()

    exploit_rows = load_exploit_rows(str(ROOT / "benchmark/benchmark_classification.csv"))
    honest.load_exploit_rows = lambda: exploit_rows
    sys.argv = ["run_honest_experiments.py", "--results-dir", str(args.results_dir)]
    exit_code = honest.main()

    status_path = args.results_dir / "status.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status["publication_scope"] = "LEGACY_115_DIAGNOSTIC_ONLY"
        status["publishable_for_original_246_row_claim"] = False
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "schema_version": 1,
        "status": "LEGACY_DIAGNOSTIC_NOT_246_ROW_RESULT",
        "input": "benchmark/benchmark_classification.csv",
        "exploit_rows": len(exploit_rows),
        "benign_source": "benchmark/imported/benign_traces.csv via honest harness",
        "denominator_policy": "115 legacy exploit rows + 1000 benign traces; no padding and no promotion to original claim",
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
