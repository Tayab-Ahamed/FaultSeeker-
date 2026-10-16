"""Standard-library-only readers and comparison against the scoped final report."""
import argparse
import csv
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT / "reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8f/benchmark/benchmark_classification_fixed.csv"
COST = ROOT / "reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json"
REPORT = ROOT / "reports/reproducibility/FINAL_REPORT.md"


def describe(path, rows, detail=""):
    print(f"Input: {path.resolve()} | rows={rows} {detail} | sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    describe(path, len(rows))
    return rows


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(compute, provenance_writer=None):
    parser = argparse.ArgumentParser(description=compute.__doc__)
    parser.add_argument("--report", type=Path, default=REPORT,
                        help="Expected-value report (default: reports/reproducibility/FINAL_REPORT.md)")
    if provenance_writer:
        parser.add_argument("--write-provenance", action="store_true")
    args = parser.parse_args()
    try:
        expected = {}
        for line in args.report.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) == 6 and cells[1] != "Metric" and cells[3].isdigit():
                if cells[1] in expected:
                    raise ValueError(f"Duplicate expected metric: {cells[1]}")
                expected[cells[1]] = (Decimal(cells[2]), int(cells[3]))
        print(f"Expected values: {args.report.resolve()}")
        values = compute()
        failed = False
        for key, value in values.items():
            target, places = expected[key]
            rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
            passed = rounded == target
            failed |= not passed
            print(f"{key}: raw={value}; expected={target}; reproduced={rounded}; {'PASS' if passed else 'FAIL'}")
        if not failed and provenance_writer and args.write_provenance:
            provenance_writer()
        return int(failed)
    except (OSError, ValueError, KeyError, ArithmeticError, TypeError) as exc:
        print(f"FAIL: {exc}")
        return 1
