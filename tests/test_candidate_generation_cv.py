from types import SimpleNamespace

from scripts.research.evaluate_candidate_generation_cv import (
    assign_folds,
    grouped_rows,
    rank_prepared,
)


def _target(txn, address):
    return SimpleNamespace(txn_hash=txn, functions={(address, "withdraw")})


def test_grouped_cv_keeps_incident_and_contract_components_together(tmp_path, monkeypatch):
    import scripts.research.evaluate_candidate_generation_cv as evaluator

    classification = tmp_path / "classification.csv"
    classification.write_text(
        "txn_hash,analysis\n"
        "0x1,\"['https://incident.example/a']\"\n"
        "0x2,\"['https://incident.example/a']\"\n"
        "0x3,\"[]\"\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluator, "CLASSIFICATION", classification)
    rows = [{"txn_hash": "0x1"}, {"txn_hash": "0x2"}, {"txn_hash": "0x3"}]
    targets = {
        "0x1": _target("0x1", "0x" + "11" * 20),
        "0x2": _target("0x2", "0x" + "22" * 20),
        "0x3": _target("0x3", "0x" + "33" * 20),
    }
    groups = grouped_rows(rows, targets)
    assert sorted(sorted(indexes) for indexes in groups.values()) == [[0, 1], [2]]
    folds = assign_folds(groups)
    assert folds[0] == folds[1]
    assert folds[0] != folds[2]


def test_rank_prepared_reports_the_score_used_for_saved_rank():
    candidate = {"code_address": "0x" + "11" * 20, "function": "withdraw"}
    features = {
        "trace_evidence": 0.0,
        "count": 0.0,
        "depth": 0.0,
        "proxy": 0.0,
        "saved_rank": 0.5,
    }
    ranked = rank_prepared(
        [(candidate, features, 2)],
        {
            "trace_evidence": 0.0,
            "count": 0.0,
            "depth": 0.0,
            "proxy": 0.0,
            "saved_rank": 1.0,
        },
    )
    assert ranked[0]["candidate_generation_score"] == 0.5


def test_grouping_unions_each_shared_address_url_and_name(tmp_path, monkeypatch):
    import scripts.research.evaluate_candidate_generation_cv as evaluator
    classification = tmp_path / "classification.csv"
    classification.write_text(
        "txn_hash,analysis\n"
        "0x1,\"['https://source/a', 'https://source/b']\"\n"
        "0x2,\"['https://source/b']\"\n"
        "0x3,\"[]\"\n"
        "0x4,\"[]\"\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluator, "CLASSIFICATION", classification)
    targets = {
        "0x1": SimpleNamespace(functions={("a", "f"), ("b", "g")}, lines=set(), name="one"),
        "0x2": SimpleNamespace(functions={("c", "f")}, lines=set(), name="two"),
        "0x3": SimpleNamespace(functions=set(), lines={("b", "10")}, name="three"),
        "0x4": SimpleNamespace(functions={("d", "f")}, lines=set(), name="Three"),
    }
    groups = grouped_rows([{"txn_hash": f"0x{i}"} for i in range(1, 5)], targets)
    assert list(groups.values()) == [[0, 1, 2, 3]]


def test_target_loading_does_not_register_label_derived_selectors(tmp_path, monkeypatch):
    import json
    import scripts.research.evaluate_candidate_generation_cv as evaluator
    from benchmark.honest_eval import localization

    address = "0x" + "ab" * 20
    (tmp_path / "target.json").write_text(json.dumps({
        "transaction_hash": ["0x1"],
        "location": {f"{address}#Contract#1:1": [f"{address}#Contract#privateLabelOnlyFunction"]},
    }), encoding="utf-8")
    cache = tmp_path / "public-cache.json"
    cache.write_text('{"0x12345678": "publicFunction"}', encoding="utf-8")
    monkeypatch.setattr(evaluator, "GROUND_TRUTH", tmp_path)
    monkeypatch.setattr(localization, "_SELECTOR_CACHE_PATH", str(cache))
    monkeypatch.setattr(localization, "_SELECTOR_TO_NAMES", {"0xffffffff": {"staleLabel"}})
    targets = evaluator._load_targets()
    assert "0x1" in targets
    assert localization._SELECTOR_TO_NAMES == {"0x12345678": {"publicfunction"}}
