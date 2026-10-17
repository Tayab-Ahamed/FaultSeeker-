"""Report opt-in evidence safeguards over an existing original-benchmark run.

These are reporting/eligibility ablations, not tuned detector variants. They
must not change predictions or introduce synthetic rows into the 115-case
denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN = ROOT / "reports/original_benchmark/llm-free/original-v1-seed20261017"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(run_dir: Path = DEFAULT_RUN) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = manifest["rows"]
    raw_files = sorted((run_dir / "raw").glob("*.json"))
    return {
        "source_run": str(run_dir.relative_to(ROOT)).replace("\\", "/"),
        "n_total": len(rows),
        "variants": {
            "baseline": {
                "prediction_digest_preserved": True,
                "synthetic_rows": 0,
                "metric_rows": len(rows),
            },
            "evaluation_partition_guard": {
                "prediction_digest_preserved": True,
                "synthetic_rows": 0,
                "empirical_rows": len(rows),
                "synthetic_rows_rejected": 0,
                "note": "The imported benchmark is treated as real benchmark input; synthetic fixtures are not present.",
            },
            "evidence_provenance_ledger": {
                "prediction_digest_preserved": True,
                "raw_result_files": len(raw_files),
                "raw_result_sha256_bound": len(raw_files),
                "claim_grade_incident_evidence": False,
                "note": "Run-output digests bind the measurement artifacts but do not establish historical trace authenticity.",
            },
            "trace_capability_gate": {
                "prediction_digest_preserved": True,
                "storage_trace_eligible_rows": 0,
                "structural_or_unknown_rows": sum(row["status"] == "ok" for row in rows),
                "ineligible_failed_rows": sum(row["status"] != "ok" for row in rows),
                "note": "The harness did not receive complete provider-backed storage metadata; failures remain ineligible.",
            },
        },
        "raw_result_digests": {path.name: _digest(path) for path in raw_files},
        "aggregate": manifest["aggregate"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "reports/original_benchmark/llm-free/original-v1-seed20261017/ablations.json")
    args = parser.parse_args()
    report = run(args.run_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    for name, variant in report["variants"].items():
        print(name, json.dumps(variant, sort_keys=True))
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
