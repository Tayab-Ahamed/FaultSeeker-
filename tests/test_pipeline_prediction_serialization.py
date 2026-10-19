from types import SimpleNamespace

from benchmark.generate_pipeline_predictions import serialize_ranked_candidates


def test_serialization_preserves_explicit_ranker_identity_and_rank_metadata():
    ranking = SimpleNamespace(
        ranked_functions=[
            {
                "rank": 1,
                "code_address": "0x" + "ab" * 20,
                "function": "withdraw_all_funds",
                "selector": None,
                "supporting_call_depths": [[0, 2], [0, 5]],
            }
        ],
        functions_to_be_inspected={},
    )

    candidates = serialize_ranked_candidates(ranking)

    assert candidates == [
        {
            "rank": 1,
            "code_address": "0x" + "ab" * 20,
            "function": "withdraw_all_funds",
            "selector": None,
            "supporting_call_depths": [[0, 2], [0, 5]],
            "address": "0x" + "ab" * 20,
            "call_type": "call",
            "depth": 5,
        }
    ]


def test_legacy_serialization_splits_only_at_final_separator():
    ranking = SimpleNamespace(
        ranked_functions=[],
        functions_to_be_inspected={
            "withdraw_all_funds_0x" + "cd" * 20: {
                "calls": [{"depth": 3}],
            }
        },
    )

    candidates = serialize_ranked_candidates(ranking)

    assert candidates[0]["function"] == "withdraw_all_funds"
    assert candidates[0]["address"] == "0x" + "cd" * 20
    assert candidates[0]["depth"] == 3
