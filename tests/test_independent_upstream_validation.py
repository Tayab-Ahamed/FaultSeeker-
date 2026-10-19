"""Edge-case tests for the independent upstream metric calculation."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reproduce/independent_upstream_validation.py"


def _load():
    spec = importlib.util.spec_from_file_location("independent_upstream_validation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_denominator_keeps_failed_rows_as_zero_hits():
    module = _load()
    rows = [
        {"txn_hash": "0xa", "ground_truth_functions": ["target"], "first_hit_rank": 1},
        {"txn_hash": "0xb", "ground_truth_functions": ["target"], "first_hit_rank": None},
    ]
    result = module.aggregate_ranks(rows, 2)
    assert result["hits"]["recall_at_1"] == 1
    assert result["recall"]["recall_at_1"] == 0.5


def test_duplicate_transaction_ids_are_rejected():
    module = _load()
    rows = [
        {"txn_hash": "0xa", "ground_truth_functions": ["target"], "first_hit_rank": 1},
        {"txn_hash": "0xa", "ground_truth_functions": ["target"], "first_hit_rank": 2},
    ]
    with pytest.raises(ValueError, match="duplicate"):
        module.aggregate_ranks(rows, 2)


def test_missing_function_label_is_not_silently_counted_as_a_miss():
    module = _load()
    rows = [{"txn_hash": "0xa", "ground_truth_functions": [], "first_hit_rank": None}]
    with pytest.raises(ValueError, match="ground-truth"):
        module.aggregate_ranks(rows, 1)


def test_ranking_ties_follow_retained_stable_list_order():
    module = _load()
    predictions = [
        {"function": "other", "rank": 1},
        {"function": "Target", "rank": 1},
    ]
    assert module.first_raw_function_rank(predictions, {"target"}) == 2


def test_upstream_run_has_expected_complete_denominator():
    module = _load()
    classification = module.load_classification()
    rows = module.build_localization_rows(classification)
    assert len(rows) == 115
    assert sum(row["status"] == "ok" for row in rows) == 110
    assert module.aggregate_ranks(rows, 115)["hits"] == {
        "recall_at_1": 27,
        "recall_at_3": 49,
        "recall_at_5": 53,
    }
