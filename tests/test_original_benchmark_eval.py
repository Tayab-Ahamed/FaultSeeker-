from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "benchmark/original_benchmark_eval.py"


def _load():
    spec = importlib.util.spec_from_file_location("original_benchmark_eval", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_imported_original_benchmark_has_115_cases():
    module = _load()
    assert len(list(module.DEFAULT_GT.glob("*.json"))) == 115


def test_protocol_runner_records_failures_as_zero(tmp_path, monkeypatch):
    module = _load()
    gt = sorted(module.DEFAULT_GT.glob("*.json"))[0]

    def fail(*args, **kwargs):
        raise RuntimeError("controlled failure")

    monkeypatch.setattr(module, "ForensicsOrchestrator", fail)
    result = module.run(gt.parent, tmp_path, limit=1)
    assert result["aggregate"]["n_total"] == 1
    assert result["aggregate"]["n_failed"] == 1
    assert result["aggregate"]["recall_at_1"] == 0.0
    raw = next((tmp_path / "llm-free").glob("*/raw/*.json"))
    assert json.loads(raw.read_text())["failure_kind"] == "RuntimeError"


def test_protocol_does_not_accept_wrong_full_benchmark_size(tmp_path):
    module = _load()
    copied = tmp_path / "ground_truth"
    copied.mkdir()
    source = sorted(module.DEFAULT_GT.glob("*.json"))[0]
    (copied / source.name).write_bytes(source.read_bytes())
    try:
        module.run(copied, tmp_path / "out", limit=None)
    except ValueError as exc:
        assert "expected 115 files, found 1" in str(exc)
    else:
        raise AssertionError("wrong-size benchmark was accepted")
