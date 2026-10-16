"""Offline checks of saved historical aggregates, never research observations."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "reproduce"


@pytest.mark.parametrize("name,key", [
    ("honest_f1", "honest_f1"),
    ("modeled_cost", "modeled_cost_saving_pct"),
    ("localization", "localization_top1_pct"),
    ("reentrancy_count", "reentrancy_label_count"),
    ("vulnerability_count", "vulnerability_label_count"),
    ("cohort", "cohort_rows"),
])
def test_reproduction_and_report_mismatch(name, key, tmp_path):
    command = [sys.executable, str(SCRIPTS / (name + ".py"))]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "Input:" in result.stdout and "rows=" in result.stdout
    report = (ROOT / "reports/reproducibility/FINAL_REPORT.md").read_text(encoding="utf-8")
    lines = report.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| " + key + " |"):
            cells = line.split("|")
            cells[2] = " 999999 "
            lines[i] = "|".join(cells)
            break
    else:
        pytest.fail("Expected metric absent from report")
    changed = tmp_path / "FINAL_REPORT.md"
    changed.write_text("\n".join(lines), encoding="utf-8")
    result = subprocess.run(command + ["--report", str(changed)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "FAIL" in result.stdout


def test_provenance_exactly_covers_frozen_cohort():
    frozen = ROOT / "reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8f/benchmark/benchmark_classification_fixed.csv"
    with frozen.open(encoding="utf-8-sig", newline="") as handle:
        cohort = list(csv.DictReader(handle))
    with (ROOT / "reports/reproducibility/cohort_provenance.csv").open(encoding="utf-8", newline="") as handle:
        provenance = list(csv.DictReader(handle))
    assert [(r["tx_hash"], r["chain"]) for r in provenance] == [(r["txn_hash"], r["chain"]) for r in cohort]
    import json
    for source, row in zip(cohort, provenance):
        try:
            links = [v for v in json.loads(source["analysis"]) if isinstance(v, str) and v.startswith(("https://", "http://"))]
        except ValueError:
            # Explicitly check the one malformed historical record, without
            # duplicating the generator's URL-extraction implementation.
            assert source["analysis"] == "['https://medium.com/coinmonks/technical-analysis-of-ape-attack-events-2c624d56c42d]"
            links = ["https://medium.com/coinmonks/technical-analysis-of-ape-attack-events-2c624d56c42d"]
        assert row["source_link"] == (" ; ".join(links) if links else "no source")
        assert row["label_source"] == str(frozen.relative_to(ROOT)).replace("\\", "/") + ":vuln_type"
