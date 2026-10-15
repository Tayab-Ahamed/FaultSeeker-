"""Depth is not ancestry: sequential branches cannot prove nested state access."""
import gzip
import json
from pathlib import Path
from benchmark.detector_experiments import detector_observation
from faultseeker.forensics.signal_extractor import SignalExtractor
from faultseeker.utils.rpc_provider import normalize_trace_node

A, B, C = ("0x" + b * 40 for b in "123")


def write(call_id, depth, value):
    return {"address": A, "slot": "0x1", "depth": depth, "call_id": call_id,
            "event_index": depth, "pc": depth, "value_after": hex(value), "after_external_call": False}


def observed(root, writes):
    canonical = normalize_trace_node(root)
    return SignalExtractor(txn_seq={"trace_coverage": {"storage_trace_complete": True}},
        tx_analysis={"canonical_trace": canonical, "storage_events": writes}, paper_mode=True).run().raw


def test_sequential_writes_in_different_branches_are_not_nested():
    root = {"type": "CALL", "to": B, "input": "0x11111111", "calls": [
        {"type": "CALL", "to": A, "input": "0x22222222"},
        {"type": "CALL", "to": C, "input": "0x33333333", "calls": [
            {"type": "CALL", "to": B, "input": "0x44444444", "calls": [
                {"type": "CALL", "to": A, "input": "0x22222222"}]}]}]}
    result = observed(root, [write("0.0", 2, 10), write("0.1.0.0", 4, 9)])
    assert result["debug"]["state_reentry"] is False
    assert result["reentrancy_score"] == 0.1


def test_actual_ancestor_callback_keeps_nested_slot_signal():
    root = {"type": "CALL", "to": A, "input": "0x11111111", "calls": [
        {"type": "CALL", "to": B, "input": "0x22222222", "calls": [
            {"type": "CALL", "to": A, "input": "0x11111111"}]}]}
    result = observed(root, [write("0", 1, 10), write("0.0.0", 3, 9)])
    assert result["debug"]["state_reentry"] is True


def test_nested_delegate_frames_without_an_external_boundary_are_not_reentry():
    root = {"type": "CALL", "to": A, "input": "0x11111111", "calls": [
        {"type": "DELEGATECALL", "to": B, "input": "0x22222222", "calls": [
            {"type": "DELEGATECALL", "to": C, "input": "0x33333333"}]}]}
    result = observed(root, [write("0", 1, 10), write("0.0.0", 3, 9)])
    assert result["debug"]["state_reentry"] is False


def test_actual_euler_sequential_token_transfers_do_not_fire_nested_rewrite():
    root = Path(__file__).resolve().parents[1]
    path = root / "reports/cohort_rebuild_v2/opcodes/0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d.json.gz"
    capture = json.loads(gzip.decompress(path.read_bytes()))
    result = detector_observation({"raw_trace": capture["raw_trace"]}, "full")
    assert result["detector_result"]["signals"]["state_slot_reentry"] is False
    assert result["predicted_exploit"] is False


def test_actual_revest_callback_keeps_positive_after_ancestry_fix():
    from scripts.replay_historical_opcodes import validate_recorded_capture
    root = Path(__file__).resolve().parents[1]
    tx = "0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428"
    path = root / "reports/cohort_rebuild_v2/opcodes" / (tx + ".json.gz")
    proof = validate_recorded_capture(path, tx)
    assert (proof["sload_count"], proof["sstore_count"]) == (326, 113)
    capture = json.loads(gzip.decompress(path.read_bytes()))
    assert len(capture["replayed_prefix_hashes"]) == 5
    result = detector_observation({"raw_trace": capture["raw_trace"]}, "full")
    assert result["detector_result"]["signals"]["state_slot_reentry"] is True
    assert result["predicted_exploit"] is True
