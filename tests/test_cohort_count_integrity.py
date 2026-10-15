"""Count metadata checks do not evaluate held-out labels or outcomes."""
import copy
import json
from pathlib import Path
import pytest
from benchmark.test_integrity import (
    APPROVED_ASSERTION, EXCEPTION_PATH, assert_cohort_count_not_decreased,
    original_test_changes,
)

ROOT = Path(__file__).resolve().parents[1]


def test_admitted_manifest_count_never_silently_decreases():
    manifest = json.loads((ROOT / "benchmark/cohort_manifest.json").read_text())
    history = json.loads((ROOT / "benchmark/cohort_admission_history.json").read_text())
    assert_cohort_count_not_decreased(manifest, history)
    assert manifest["accepted_count"] == len(manifest["records"])
    reduced = copy.deepcopy(manifest)
    reduced["accepted_count"] = max(p["accepted_count"] for p in history["publications"]) - 1
    with pytest.raises(AssertionError, match="decreased"):
        assert_cohort_count_not_decreased(reduced, history)


def test_original_source_exception_rejects_any_additional_edit(tmp_path):
    baseline = json.loads((ROOT / "benchmark/baseline_tests.json").read_text())
    for name in baseline["source_sha256"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    (tmp_path / "benchmark").mkdir()
    (tmp_path / "benchmark/baseline_tests.json").write_text(json.dumps(baseline))
    assert original_test_changes(tmp_path) == []
    target = tmp_path / EXCEPTION_PATH
    target.write_bytes(target.read_bytes() + b"\n# unauthorized edit\n")
    assert original_test_changes(tmp_path) == [EXCEPTION_PATH]
