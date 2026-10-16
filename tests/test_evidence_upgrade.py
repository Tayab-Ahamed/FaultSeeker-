"""Tests for the evidence-separated synthetic and historical replay lane."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from benchmark.evidence_upgrade import (
    build_report,
    load_replay_accounting,
    run_compiled_fixture_cases,
    run_synthetic_cases,
    synthetic_cases,
)


ROOT = Path(__file__).resolve().parents[1]


def test_hand_authored_cases_are_deterministic_and_ineligible():
    first = run_synthetic_cases()
    second = run_synthetic_cases()
    assert first == second
    assert len(first) == 4
    assert {row["case_id"] for row in first} == {
        "recursive_same_function",
        "recursive_cross_function",
        "guarded_callback",
        "plain_external_call",
    }
    assert all(row["synthetic"] for row in first)
    assert all(row["metric_eligible"] is False for row in first)
    assert all(row["result_sha256"] == hashlib.sha256(
        json.dumps({key: value for key, value in row.items() if key != "result_sha256"},
                   sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest() for row in first)


def test_hand_authored_cases_cover_positive_and_negative_mechanisms():
    rows = {row["case_id"]: row for row in run_synthetic_cases()}
    assert rows["recursive_same_function"]["predicted_exploit"] is True
    assert rows["recursive_same_function"]["tier"] == "HIGH_RISK_REENTRANCY"
    assert rows["recursive_cross_function"]["tier"] == "POSSIBLE_REENTRANCY"
    assert rows["recursive_cross_function"]["predicted_exploit"] is False
    assert rows["guarded_callback"]["predicted_exploit"] is False
    assert rows["plain_external_call"]["predicted_exploit"] is False


def test_compiled_fixture_is_real_execution_but_not_population_evidence():
    rows = run_compiled_fixture_cases()
    assert {row["case_id"] for row in rows} == {"reentrant", "guarded", "delegatecall"}
    assert all(row["source_kind"] == "compiled_evm_fixture" for row in rows)
    assert all(row["synthetic"] is True for row in rows)
    assert all(row["metric_eligible"] is False for row in rows)
    assert next(row for row in rows if row["case_id"] == "reentrant")["predicted_exploit"] is True


def _write_summary(tmp_path: Path, *, receipt_matches=True, duplicate=False, token=None):
    artifact_name = "capture.json.gz"
    artifact_path = tmp_path / artifact_name
    with gzip.open(artifact_path, "wt", encoding="utf-8") as handle:
        json.dump({"raw_trace": {"call": {}}}, handle)
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    txn_hash = "0x" + (token or ("b" if duplicate else "a")) * 64
    summary = {
        "status": "CAPTURED",
        "scope": "test historical replay",
        "cases": [{
            "transaction_hash": txn_hash,
            "artifact": artifact_name,
            "artifact_sha256": digest,
            "normalization_complete": True,
            "storage_owners_verified": True,
            "receipt_matches": receipt_matches,
            "opcode_count": 10,
            "sload_count": 2,
            "sstore_count": 1,
        }],
        "rpc_usage": {"outbound_rpc_requests": 3, "estimated_cost_usd": 0.001,
                      "billing_confirmed": False},
    }
    summary_path = tmp_path / ("summary-duplicate.json" if duplicate else "summary.json")
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    return summary_path


def test_valid_capture_is_counted_but_not_incident_metric_eligible(tmp_path):
    summary_path = _write_summary(tmp_path)
    report = load_replay_accounting([summary_path])
    row = report["captures"][0]
    assert row["status"] == "CAPTURED"
    assert row["artifact_valid"] is True
    assert row["receipt_matches"] is True
    assert row["metric_eligible"] is False
    assert row["metric_ineligibility_reason"] == "independent_incident_adjudication_absent"
    assert report["summary"]["valid_captures"] == 1
    assert report["summary"]["metric_eligible_captures"] == 0


def test_receipt_mismatch_is_not_a_valid_capture(tmp_path):
    summary_path = _write_summary(tmp_path, receipt_matches=False)
    row = load_replay_accounting([summary_path])["captures"][0]
    assert row["status"] == "INVALID_CAPTURE"
    assert row["metric_eligible"] is False


def test_duplicate_identity_is_rejected(tmp_path):
    first = _write_summary(tmp_path)
    second_dir = tmp_path / "second"
    second_dir.mkdir()
    second = _write_summary(second_dir, token="c")
    report = load_replay_accounting([first, second])
    assert [row["duplicate"] for row in report["captures"]] == [False, False]

    third_dir = tmp_path / "third"
    third_dir.mkdir()
    third = _write_summary(third_dir, duplicate=True, token="a")
    report = load_replay_accounting([first, third])
    assert report["captures"][1]["duplicate"] is True
    assert report["captures"][1]["status"] == "INVALID_CAPTURE"


def test_report_separates_synthetic_and_real_denominators():
    report = build_report()
    assert report["evaluation_contract"] == {
        "synthetic_metric_eligible": False,
        "real_metric_requires_independent_adjudication": True,
        "paper_files_modified": False,
    }
    assert report["synthetic"]["case_count"] == 7
    assert report["real_replay"]["summary"]["valid_captures"] == 2
    assert report["real_replay"]["summary"]["metric_eligible_captures"] == 0
    assert report["claim_gate"]["real_population_metrics"] == "BLOCKED"


@pytest.mark.parametrize("case", synthetic_cases())
def test_synthetic_case_catalog_has_explicit_ground_truth(case):
    assert case.case_id
    assert isinstance(case.label, bool)
    assert case.mechanism
    assert case.expected["detector_variant"] == "structural"
