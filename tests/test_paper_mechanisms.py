import hashlib

import pytest

from faultseeker.core.llm_router import COST_RATES
from faultseeker.research.evaluation_partition import EvaluationPartition, EvaluationSample
from faultseeker.research.evidence_provenance import EvidenceLedger, attach_provenance
from faultseeker.research.paper_mechanisms import (
    PAPER_MECHANISMS,
    mechanism_matrix,
    records_with_status,
    render_markdown,
)
from faultseeker.research.routing_audit import RoutingAudit
from faultseeker.research.trace_capability import TraceCapability, assess_reentrancy_trace


def test_matrix_has_valid_statuses_and_exact_paths():
    assert len(PAPER_MECHANISMS) >= 20
    assert {row["status"] for row in mechanism_matrix()} <= {"EXISTS", "PARTIAL", "MISSING"}
    assert all(row["repository_paths"] for row in mechanism_matrix())
    assert "**MISSING**" in render_markdown()
    assert records_with_status("MISSING")


def test_trace_capability_requires_complete_storage_for_storage_mode():
    capture = {
        "chain": "eth",
        "transaction_hash": "0x1",
        "trace": {"call_type": "CALL"},
        "trace_coverage": {"trace_complete": True, "storage_trace_complete": False},
    }
    structural = assess_reentrancy_trace(capture)
    storage = assess_reentrancy_trace(capture, require_storage=True)
    assert structural.eligible and structural.mode == "structural"
    assert not storage.eligible and storage.mode == "ineligible"
    assert "storage_trace_incomplete" in storage.reasons


def test_trace_capability_can_prove_storage_mode_without_events():
    decision = assess_reentrancy_trace({
        "transaction_hash": "0x2", "canonical_trace": {"call_type": "CALL"},
        "trace_coverage": {"trace_complete": True, "storage_trace_complete": True},
    }, require_storage=True)
    assert decision.eligible and decision.mode == "storage"
    assert decision.capability.storage_event_count == 0


def test_trace_capability_can_require_receipt_identity():
    decision = assess_reentrancy_trace({
        "trace": {"call_type": "CALL"},
        "trace_coverage": {"trace_complete": True, "storage_trace_complete": True},
    }, require_receipt_identity=True)
    assert not decision.eligible
    assert "receipt_identity_unverified" in decision.reasons


def test_evidence_ledger_binds_digest_and_rejects_escape_and_tampering(tmp_path):
    artifact = tmp_path / "trace.json"
    artifact.write_text("original", encoding="utf-8")
    digest = hashlib.sha256(b"original").hexdigest()
    ledger = EvidenceLedger(tmp_path)
    record = ledger.add_artifact("trace", "trace.json", expected_sha256=digest)
    assert record.kind == "observed"
    with pytest.raises(ValueError, match="escapes"):
        ledger.add_artifact("outside", "../outside.json")
    artifact.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        EvidenceLedger(tmp_path).add_artifact("trace", "trace.json", expected_sha256=digest)


def test_evidence_provenance_separates_synthetic_cards(tmp_path):
    path = tmp_path / "synthetic.json"
    path.write_text("synthetic", encoding="utf-8")
    ledger = EvidenceLedger(tmp_path)
    ledger.add_artifact("attack-variant", "synthetic.json", kind="synthetic")
    with pytest.raises(ValueError, match="synthetic"):
        ledger.validate_for_claim()
    card = attach_provenance({"function_signature": {"function": "withdraw"}}, ledger)
    assert card["evidence_provenance"][0]["kind"] == "synthetic"


def test_routing_audit_distinguishes_provider_usage_from_estimates():
    audit = RoutingAudit(COST_RATES, local_models={"llama3:8b"})
    audit.record(tier=1, model="llama3:8b", input_tokens=10, output_tokens=5, usage_source="provider")
    audit.record(tier=3, model="gpt-4o-mini", input_tokens=100, output_tokens=20, usage_source="estimate")
    report = audit.summary("gpt-4o-mini")
    assert report["observed_usage_queries"] == 1
    assert report["estimated_usage_queries"] == 1
    assert report["cost_reduction_is_observed"] is False
    assert report["local_queries"] == 1


def test_routing_audit_rejects_invalid_tier_and_tokens():
    audit = RoutingAudit(COST_RATES)
    with pytest.raises(ValueError):
        audit.record(tier=4, model="gpt-4o-mini", input_tokens=1, output_tokens=1)
    with pytest.raises(ValueError):
        audit.record(tier=1, model="local", input_tokens=-1, output_tokens=0)
    with pytest.raises(ValueError, match="unknown model pricing"):
        audit.record(tier=1, model="unclassified-model", input_tokens=1, output_tokens=0)


def test_evaluation_partition_blocks_adversarial_and_fixture_metrics():
    partition = EvaluationPartition([
        EvaluationSample("real-1", "real_exploit"),
        EvaluationSample("adv-1", "synthetic_adversarial"),
    ])
    assert partition.report()["synthetic_ids"] == ["adv-1"]
    assert len(partition.empirical()) == 1
    with pytest.raises(ValueError, match="non-empirical"):
        partition.metric_samples()
    assert len(partition.metric_samples(allow_synthetic=True)) == 2


def test_evaluation_partition_rejects_duplicate_ids_and_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        EvaluationSample("x", "unknown")
    partition = EvaluationPartition([EvaluationSample("x", "real_benign")])
    with pytest.raises(ValueError, match="duplicate"):
        partition.add(EvaluationSample("x", "real_exploit"))
