def test_upstream_ranker_counts_distinct_depths_and_stable_ties():
    from benchmark.upstream_compat_ranker import rank_upstream_candidates

    result = rank_upstream_candidates(
        functions_to_be_inspected={"first": [
            {"function": "attack", "address": "0x1", "gas": 1, "params": "", "depth": [0]},
            {"function": "attack", "address": "0x1", "gas": 2, "params": "", "depth": [0]},
            {"function": "attack", "address": "0x1", "gas": 3, "params": "", "depth": [0, 1]},
            {"function": "other", "address": "0x2", "gas": 4, "params": "", "depth": [0]},
        ]}
    )
    assert result["ordered_keys"] == ["attack_0x1", "other_0x2"]
    assert result["functions_to_be_inspected"]["attack_0x1"]["count"] == 2
    assert result["fallback_used"] is False


def test_upstream_ranker_filters_extended_created_calls_but_not_normal_fallback():
    from benchmark.upstream_compat_ranker import rank_upstream_candidates

    result = rank_upstream_candidates(
        functions_to_be_inspected={"none": []},
        address_calls_with_created_contract=[
            {"function": "transferUnderlyingTo", "address": "0x1", "gas": 1, "params": "", "depth": [0]},
            {"function": "mint", "address": "0x2", "gas": 1, "params": "", "depth": [0]},
        ],
        function_call_loc_memo={
            "fallback::0x3": [{"gas": 1, "params": "", "depth": [0]}, {"gas": 2, "params": "", "depth": [0]}]
        },
    )
    assert result["fallback_used"] is True
    assert result["ordered_keys"] == ["fallback_0x3"]
    assert result["functions_to_be_inspected"]["fallback_0x3"]["count"] == 2
    assert list(result["address_calls_with_created_contract_in_params"]) == ["mint"]


def test_upstream_ranker_uses_count_not_current_tie_policy():
    from benchmark.upstream_compat_ranker import rank_upstream_candidates

    result = rank_upstream_candidates(
        functions_to_be_inspected={
            "first": [{"function": "a", "address": "0x1", "gas": 1, "params": "", "depth": [0]}],
            "second": [{"function": "b", "address": "0x2", "gas": 1, "params": "", "depth": [0]}],
        }
    )
    assert result["ordered_keys"] == ["a_0x1", "b_0x2"]
