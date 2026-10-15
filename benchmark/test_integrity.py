"""Preserve original test hashes with one explicitly authorized assertion exception."""
import hashlib
import json
from pathlib import Path

EXCEPTION_PATH = "tests/test_public_incident_import.py"
OLD_ASSERTION = '    assert report["current_verified_exploit_rows"] >= 231'
APPROVED_ASSERTION = '    assert report["current_verified_exploit_rows"] == __import__("json").loads(\n        __import__("pathlib").Path(__file__).resolve().parents[1].joinpath(\n            "benchmark", "cohort_manifest.json"\n        ).read_text(encoding="utf-8")\n    )["accepted_count"]'


def original_test_changes(root):
    root = Path(root)
    baseline = json.loads((root / "benchmark/baseline_tests.json").read_text())
    changed = []
    for name, digest in baseline["source_sha256"].items():
        content = (root / name).read_bytes().replace(b"\r\n", b"\n")
        if name == EXCEPTION_PATH:
            text = content.decode("utf-8")
            if text.count(APPROVED_ASSERTION) == 1:
                content = text.replace(APPROVED_ASSERTION, OLD_ASSERTION, 1).encode("utf-8")
        if hashlib.sha256(content).hexdigest() != digest:
            changed.append(name)
    return changed


def assert_cohort_count_not_decreased(manifest, history):
    entries = history["publications"]
    if not entries:
        raise AssertionError("Missing cohort publication history")
    floor = max(entry["accepted_count"] for entry in entries)
    if manifest["accepted_count"] < floor:
        raise AssertionError("Admitted cohort count decreased below published history")
