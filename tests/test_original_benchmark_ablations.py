from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reproduce/original_benchmark_ablations.py"


def _load():
    spec = importlib.util.spec_from_file_location("original_benchmark_ablations", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_three_opt_in_features_preserve_prediction_denominator():
    module = _load()
    report = module.run()
    assert report["n_total"] == 115
    assert all(item["prediction_digest_preserved"]
               for item in report["variants"].values())
    assert report["variants"]["evaluation_partition_guard"]["synthetic_rows"] == 0
    assert report["variants"]["evidence_provenance_ledger"]["raw_result_files"] == 115
    assert report["variants"]["trace_capability_gate"]["storage_trace_eligible_rows"] == 0
