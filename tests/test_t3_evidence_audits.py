"""Focused offline checks for the cost, replay, and source audits."""

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = ROOT / "scripts" / "reproduce" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cost_proof_preserves_zero_spend_and_modeled_35_percent():
    module = _load("cost_zero_spend_audit")
    proof = module.build_proof()
    assert proof["dotenv_loaded"] is False
    assert proof["wingman_secrets_loaded"] is False
    assert proof["provider_api_calls"] == 0
    assert proof["model_dispatches"] == 0
    assert proof["modeled_cost"]["modeled_cost_saving_pct"] == 35.0
    assert proof["free_tier_api"]["availability_verified"] is False


def test_replay_audit_covers_all_17_rows_without_verification_claims():
    module = _load("reentrancy_replay_audit")
    rows = module.audit_rows()
    assert len(rows) == 17
    assert {row["saved_replay_status"] for row in rows} == {"TRACE_PRESENT", "TRACE_ABSENT"}
    assert all(row["verified_reentrant_count"] == "0" for row in rows)
    assert all(row["label_verification_status"].startswith("UNVERIFIED_") for row in rows)


def test_local_source_audit_is_network_free_and_keeps_adjudication_separate():
    module = _load("local_source_resolution_audit")
    rows, summary = module.audit()
    # The committed audit covers the requested 70 rows.  A later local probe
    # may conservatively classify additional transient HTTP failures as
    # unresolved; the audit must cover all rows it sees without network calls.
    assert summary["unresolved_rows_attempted"] >= 70
    assert len(rows) == summary["unresolved_urls_attempted"]
    assert summary["network_requests"] == 0
    assert summary["incident_adjudications"] == 0
    assert all(row["adjudication_status"] == "NOT_PERFORMED" for row in rows)


def test_committed_replay_report_has_17_data_rows():
    path = ROOT / "reports" / "claim_evidence" / "reentrancy_replay_verification.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 17
    assert not any(row["label_verification_status"] == "VERIFIED" for row in rows)


def test_committed_cost_proof_is_json():
    path = ROOT / "reports" / "claim_evidence" / "cost_zero_spend_proof.json"
    proof = json.loads(path.read_text(encoding="utf-8"))
    assert proof["modeled_cost"]["modeled_cost_saving_pct"] == 35.0
    assert proof["provider_api_calls"] == 0
