"""Software-only fixtures, excluded from research results."""
from copy import deepcopy
import pytest

from scripts.research import address_ranking_phase1 as experiment


def test_distinct_address_baseline_has_equal_address_budget():
    predictions = [
        {"code_address": "0x" + "11" * 20, "function": "a", "count": 1},
        {"code_address": "0x" + "11" * 20, "function": "b", "count": 1},
        {"code_address": "0x" + "22" * 20, "function": "c", "count": 1},
    ]
    evidence = experiment.extract_evidence(predictions, "")
    assert len(evidence) == 2
    assert len(set(x["address"] for x in evidence)) == 2


def test_labels_and_expected_fields_do_not_affect_features():
    pred = [{"code_address": "0x" + "11" * 20, "function": "a", "count": 3,
             "supporting_call_depths": [[0, 1], [0, 2]]}]
    before = experiment.extract_evidence(pred, "")
    changed = deepcopy(pred)
    changed[0].update(label=True, target=True, expected_rank=1, score=999999)
    assert experiment.extract_evidence(changed, "") == before


def test_connected_groups_union_each_contract_url_and_duplicate():
    rows = [
        {"tx": "a", "incident": "one", "targets": ["A"], "urls": ["u", "v"]},
        {"tx": "b", "incident": "two", "targets": ["B"], "urls": ["v"]},
        {"tx": "c", "incident": "three", "targets": ["B", "C"], "urls": []},
        {"tx": "d", "incident": "four", "targets": ["D"], "urls": []},
        {"tx": "d", "incident": "five", "targets": ["E"], "urls": []},
    ]
    groups = experiment.connected_groups(rows)
    assert sorted(sorted(g) for g in groups) == [[0, 1, 2], [3, 4]]


def test_delegate_context_never_adds_target_alias_or_unseen_address():
    proxy, implementation, unknown = ["0x" + x * 40 for x in "123"]
    predictions = [{"code_address": proxy, "function": "a", "count": 1},
                   {"code_address": implementation, "function": "b", "count": 1}]
    text = f"[1] {proxy}::a()\n    └─ [1] {implementation}::b() [delegatecall]\n        └─ [1] {unknown}::c() [delegatecall]"
    evidence = experiment.extract_evidence(predictions, text)
    assert {r["address"] for r in evidence} == {proxy, implementation}
    assert all(r["delegate_neighbor"] > 0 for r in evidence)


def test_training_selection_ignores_validation_labels():
    features = [{"address": "A", "best_reciprocal": 1., "reciprocal_sum": 1.,
                 "structural": 0., "terminal_fanout": 0., "delegate_neighbor": 0.}]
    rows = [{"targets": ["A"], "evidence": features}, {"targets": ["B"], "evidence": features}]
    before = experiment.choose_config(rows, [0], "structural_grid")
    rows[1]["targets"] = ["A"]
    assert experiment.choose_config(rows, [0], "structural_grid") == before


def test_guard_blocks_any_new_batch_path_without_opening_it():
    with pytest.raises(RuntimeError):
        experiment.guard_event("open", ("/workspace/reports/new_batches/batchZ/example.json", "r"))
