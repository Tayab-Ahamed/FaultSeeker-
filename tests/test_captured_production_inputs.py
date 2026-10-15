"""Actual RPC captures enter production collectors and forensics, without result mocks."""
import json
import socket
from pathlib import Path
import pytest
from faultseeker.data_collection.txn_info_collector import TransactionInfoCollector
from faultseeker.data_collection.txn_sequencer import TransactionSequencer

ROOT = Path(__file__).resolve().parents[1]
REVEST = "0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428"


def test_rpc_normalizer_preserves_receipt_and_created_contract_identity():
    tx = {"hash": "0x" + "a" * 64, "from": "0x" + "11" * 20, "to": None, "blockNumber": "0x10"}
    receipt = {"transactionHash": tx["hash"], "status": "0x1", "gasUsed": "0x100", "logs": [],
               "contractAddress": "0x" + "22" * 20}
    info = TransactionInfoCollector.from_rpc(tx, receipt, tx["hash"])
    assert info["address_info"]["to_address"] == [receipt["contractAddress"]]
    assert info["receipt_identity_verified"] is True
    assert info["receipt_logs"] == []
    assert TransactionInfoCollector.from_rpc(tx, dict(receipt, transactionHash="wrong"), tx["hash"]) == {}


def test_structured_sequence_retains_actual_creation_and_call_metadata():
    created, called = "0x" + "11" * 20, "0x" + "22" * 20
    structured = {"transaction_hash": "0x" + "a" * 64, "chain": "eth", "trace": {
        "callee": created, "call_type": "CREATE", "function_selector": "0x", "input": "0x6000", "children": [
            {"callee": called, "call_type": "CALL", "function_selector": "0x11111111", "input": "0x11111111", "children": []}]},
        "storage_events": [], "storage_reads": [], "trace_coverage": {"storage_trace_complete": False}}
    result = TransactionSequencer().from_structured(structured)
    assert result["trace"]["type"] == "create"
    assert result["created_address"] == [created]
    assert result["address_calls"][called] == ["0x11111111"]
    assert result["trace_coverage"]["storage_trace_complete"] is False


def test_real_train_capture_runs_production_stage_one_without_network_or_llm(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    def forbidden(*args, **kwargs):
        raise AssertionError("Captured production inputs must not dispatch network I/O")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    inputs = load_train_inputs(ROOT, "eth:" + REVEST)
    orchestrator = inputs.orchestrator(tmp_path / "forensics")
    result, sequence, info = orchestrator.run(REVEST, "eth")
    assert result.transaction_hash == REVEST
    assert result.signals["reentrancy"]["signals"]["state_slot_reentry"] is True
    assert result.signals["reentrancy"]["context"]["fallback_mode"] is False
    assert sequence["trace_coverage"]["storage_trace_complete"] is True
    assert len(sequence["storage_events"]) == 113
    assert info["receipt_identity_verified"] is True
    assert info["receipt_logs"]
    assert result.signals["coverage"]["token_flow_complete"] is False
    assert result.signals["coverage"]["multi_tx_context_complete"] is False
    assert orchestrator.address_classifier.agent is None
    assert result.address_to_be_inspected


def test_capture_loader_rejects_non_train_identity_before_opening_evidence():
    from benchmark.captured_inputs import load_train_inputs
    with pytest.raises(ValueError, match="train"):
        load_train_inputs(ROOT, "eth:0x" + "f" * 64)


def test_real_stage_one_runner_executes_production_ranker_without_claiming_stage_two(tmp_path):
    from scripts.run_train_production import observe_stage_one
    record = observe_stage_one(ROOT, "eth:" + REVEST, tmp_path / "stage_one")
    assert record["pipeline_stage"] == "production-stage-one-and-ranker"
    assert record["stage2_executed"] is False
    assert record["network_attempts"] == 0
    assert record["ranking"]["address_list"]
    assert record["forensics"]["signals"]["reentrancy"]["signals"]["state_slot_reentry"] is True
    assert record["coverage"]["multi_tx_context_complete"] is False
