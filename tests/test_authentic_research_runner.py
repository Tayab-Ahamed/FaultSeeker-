"""Experiment plumbing tests use fixtures; they are not empirical paper outcomes."""
import gzip
import json
from pathlib import Path
import pytest
from benchmark.research_protocol import bind, canonical, identity, sha, write_json
from tests.test_authentic_publication import fixture_record


def training_workspace(root):
    row = fixture_record(root, 1)
    row["reentrancy_label"] = True
    a, b = "0x" + "11" * 20, "0x" + "22" * 20
    rpc_path = root / row["rpc"]["path"]
    rpc = json.loads(rpc_path.read_text())
    rpc["transaction"].update({"from": b, "to": a})
    write_json(rpc_path, rpc)
    row["rpc"] = bind(rpc_path, root)
    trace = {"transaction_hash": row["txn_hash"], "chain": "eth", "raw_trace": {"call": {
        "type": "CALL", "from": b, "to": a, "input": "0x11111111", "calls": [{
            "type": "CALL", "from": a, "to": b, "input": "0x22222222", "calls": [{
                "type": "CALL", "from": b, "to": a, "input": "0x11111111"}]}]}}}
    path = root / "trace.json.gz"
    path.write_bytes(gzip.compress(json.dumps(trace).encode(), mtime=0))
    row["trace"] = bind(path, root)
    write_json(root / "benchmark/cohort_manifest.json", {"accepted_count": 2})
    write_json(root / "train.json", [row])
    split = {"status": "FROZEN", "seed": 1729, "train_ids": [identity(row)],
        "heldout_ids": ["eth:0x" + "f" * 64], "manifest_sha256": sha((root / "benchmark/cohort_manifest.json").read_bytes()),
        "partitions": {"train": bind(root / "train.json", root),
                       "heldout": {"path": "DO_NOT_OPEN.json", "sha256": "0" * 64}}}
    write_json(root / "benchmark/eval_split.json", split)
    return row


def test_runner_executes_real_train_detectors_without_heldout_or_label_input(tmp_path, monkeypatch):
    from scripts import run_authentic_research as runner
    row = training_workspace(tmp_path)
    original = runner.detector_observation
    calls = []
    def observe(capture, variant):
        assert "reentrancy_label" not in capture and "annotation_record" not in capture
        calls.append(variant)
        return original(capture, variant)
    monkeypatch.setattr(runner, "detector_observation", observe)
    result = runner.run_train(tmp_path)
    assert calls == ["structural", "repeated"]
    assert result["scope"] == "train-only reentrancy components; not overall system F1"
    assert result["variants"]["structural"]["metrics"]["tp"] == 1
    assert result["variants"]["full"]["metrics"] is None
    assert result["variants"]["full"]["missing"][0]["identity"] == identity(row)
    log = json.loads((tmp_path / "reports/cohort_rebuild_v2/experiments_log.json").read_text())
    assert all(set(event["sample_ids"]) <= {identity(row)} for event in log)
    assert not (tmp_path / "reports/cohort_rebuild_v2/final_exam.json").exists()


def test_runner_records_tampered_trace_as_unscored_not_negative(tmp_path):
    from scripts.run_authentic_research import run_train
    training_workspace(tmp_path)
    (tmp_path / "trace.json.gz").write_bytes(b"tampered")
    result = run_train(tmp_path)
    assert result["variants"]["structural"]["metrics"] is None
    assert result["variants"]["repeated"]["observations"] == []
    assert "digest" in result["variants"]["structural"]["missing"][0]["reason"]


def test_runner_refuses_changed_frozen_manifest(tmp_path):
    from scripts.run_authentic_research import run_train
    training_workspace(tmp_path)
    (tmp_path / "benchmark/cohort_manifest.json").write_bytes(b"changed")
    with pytest.raises(ValueError, match="manifest"):
        run_train(tmp_path)
    assert not (tmp_path / "reports/cohort_rebuild_v2/experiments_log.json").exists()
